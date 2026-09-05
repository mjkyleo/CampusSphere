#!/usr/bin/env python3
"""CampusSphere 一键启停控制脚本（跨平台，仅依赖标准库）。

解决的问题
----------
原先只有 Windows 专用的 ``deploy/start_dev.bat``，且没有配套的关闭脚本，
开发结束后残留的 uvicorn / node 进程会继续占用 8000、5173 端口。本脚本提供
统一的启停入口，并对每一次启停做健康探测与端口释放校验。

子命令
------
up       启动服务（默认后端 + 前端），等待健康检查通过后退出
down     停止服务，优雅终止优先，超时强杀，并校验端口已释放
status   查看各服务监听状态与 PID
restart  等价于 down + up

幂等行为（up）
--------------
- 服务已在运行且健康：跳过启动并打印 PID；若是先前会话遗留、未被本脚本
  管理的进程，会把其 PID 采纳进 .run/<name>.pid，便于后续 down/status 接管。
- 端口被占但健康检查不通过：视为残留进程，需 ``--force`` 清理后才重启。
- 因此重复执行 up / 忘记已启动时不会重复拉起进程或报错。

常用参数
--------
--backend-only / --frontend-only   只操作其中一个服务
--mode local|docker                local 直起进程（默认）；docker 走 compose
--no-wait                          up 时不等待健康检查
--wait-timeout N                   健康检查最长等待秒数（默认 90）
--foreground                       前台驻留（类似 compose up）：任一子进程退出即结束，
                                   配合 Ctrl+C 或另开终端执行 down 停止。适合在进程
                                   会被回收的托管环境（如沙箱/CI 后台任务）使用。
--force                            up：清理端口上健康检查未通过的残留进程后重启；
                                   down：直接强杀
--purge-logs                       down 时一并删除本次运行日志

示例
----
python scripts/devctl.py up
python scripts/devctl.py up --backend-only --wait-timeout 120
python scripts/devctl.py up --foreground      # 前台驻留（沙箱内请用后台任务托管）
python scripts/devctl.py down --force
python scripts/devctl.py status
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUN_DIR = ROOT / ".run"
LOG_DIR = RUN_DIR / "logs"
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"

BACKEND_PORT = 8000
FRONTEND_PORT = 5173
BACKEND_HEALTH_URL = f"http://127.0.0.1:{BACKEND_PORT}/health"
FRONTEND_HEALTH_URL = f"http://127.0.0.1:{FRONTEND_PORT}/"

IS_WINDOWS = os.name == "nt"


# --------------------------------------------------------------------------
# 基础工具
# --------------------------------------------------------------------------
def _log(msg: str) -> None:
    print(f"[devctl] {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"[devctl]   OK  {msg}", flush=True)


def _warn(msg: str) -> None:
    print(f"[devctl] WARN  {msg}", flush=True)


def _fail(msg: str) -> None:
    print(f"[devctl] FAIL  {msg}", flush=True)


def _port_in_use(port: int) -> bool:
    """判断 127.0.0.1:<port> 是否可连通（即已被监听）。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _pids_on_port(port: int) -> set[int]:
    """返回正在监听指定端口的进程 PID 集合。

    Windows 走 netstat；POSIX 优先 lsof，缺失时返回空集（由调用方降级处理）。
    """
    pids: set[int] = set()
    try:
        if IS_WINDOWS:
            # errors="replace"：中文 Windows 的 netstat 含本地编码字符，
            # 严格 UTF-8 解码会让整段输出不可用（PID 提取本身只依赖数字）。
            out = subprocess.run(
                ["netstat", "-ano", "-p", "TCP"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
                check=False,
            ).stdout
            for line in out.splitlines():
                if f":{port}" not in line or "LISTENING" not in line.upper():
                    continue
                parts = line.split()
                if len(parts) >= 5:
                    with contextlib.suppress(ValueError):
                        pids.add(int(parts[-1]))
        else:
            lsof = shutil.which("lsof")
            if lsof:
                out = subprocess.run(
                    [lsof, f"-ti:tcp:{port}"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                    check=False,
                ).stdout
                pids.update(int(tok) for tok in out.split() if tok.isdigit())
    except Exception as exc:  # noqa: BLE001 - 探测失败不应中断主流程
        _warn(f"端口 {port} 占用探测失败：{exc}")
    return pids


def _pid_alive(pid: int) -> bool:
    """跨平台判断进程是否仍在运行。

    Windows 下不走 tasklist：中文系统的 tasklist 输出为本地编码（GBK），
    以 UTF-8 解码会抛 UnicodeDecodeError 并使 stdout 变成 None。
    改用 Win32 API 直接查询，既无编码问题也更快。
    """
    if pid <= 0:
        return False
    if IS_WINDOWS:
        return _pid_alive_windows(pid)
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


if IS_WINDOWS:  # pragma: no cover - 仅 Windows 生效
    import ctypes
    from ctypes import wintypes

    _PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    _STILL_ACTIVE = 259
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    _kernel32.OpenProcess.restype = wintypes.HANDLE
    _kernel32.GetExitCodeProcess.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.DWORD),
    ]
    _kernel32.GetExitCodeProcess.restype = wintypes.BOOL
    _kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    _kernel32.CloseHandle.restype = wintypes.BOOL

    def _pid_alive_windows(pid: int) -> bool:
        """用 OpenProcess + GetExitCodeProcess 判断进程存活。"""
        handle = _kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        try:
            exit_code = wintypes.DWORD()
            if not _kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return False
            return int(exit_code.value) == _STILL_ACTIVE
        finally:
            _kernel32.CloseHandle(handle)
else:

    def _pid_alive_windows(pid: int) -> bool:  # pragma: no cover - 非 Windows 占位
        raise NotImplementedError("Win32 API 仅在 Windows 可用")


def _python_executable() -> str:
    """返回可运行 uvicorn 的解释器路径；找不到时返回空串。

    候选顺序：backend/.venv → 当前解释器 → PATH 中的 python。
    注意：venv 可能已创建但并未安装依赖（例如只装了 pip），
    因此逐个实际探测 ``import uvicorn``，避免选中跑不起来的解释器。
    """
    venv_dir = BACKEND_DIR / ".venv" / ("Scripts" if IS_WINDOWS else "bin")
    venv_py = venv_dir / ("python.exe" if IS_WINDOWS else "python")
    candidates = [str(venv_py), sys.executable]
    path_py = shutil.which("python") or shutil.which("python3")
    if path_py:
        candidates.append(path_py)

    for cand in candidates:
        if not cand or not Path(cand).is_file():
            continue
        try:
            probe = subprocess.run(
                [cand, "-c", "import uvicorn"],
                capture_output=True,
                timeout=30,
                check=False,
            )
        except Exception:  # noqa: BLE001, S112 - 探测失败即静默换下一个候选
            continue
        if probe.returncode == 0:
            return cand
    return ""


# --------------------------------------------------------------------------
# 服务定义
# --------------------------------------------------------------------------
@dataclass
class Service:
    """一个可启停的本地服务。"""

    name: str
    port: int
    cwd: Path
    health_url: str
    log_name: str

    @property
    def pid_file(self) -> Path:
        return RUN_DIR / f"{self.name}.pid"

    @property
    def log_file(self) -> Path:
        return LOG_DIR / self.log_name

    def build_command(self) -> tuple[list[str] | str, bool]:
        """返回 ``(命令, 是否需要 shell)``。

        Windows 下 npm 入口是 .cmd，无法被 CreateProcess 直接执行，需借助 shell。
        """
        if self.name == "backend":
            python = _python_executable()
            if not python:
                raise RuntimeError(
                    "未找到已安装 uvicorn 的 Python 解释器。"
                    f"请在 {BACKEND_DIR} 下执行：pip install -e \".[dev]\""
                )
            return [
                python,
                "-m",
                "uvicorn",
                "app.asgi:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(self.port),
            ], False

        npm = shutil.which("npm")
        if npm is None:
            raise RuntimeError("未找到 npm，请先安装 Node.js 并将其加入 PATH")
        if IS_WINDOWS:
            # .cmd 需要 shell 才能启动；引号保证含空格的路径不出错
            return f'"{npm}" run dev', True
        return [npm, "run", "dev"], False

    def check_health(self, timeout: float = 2.0) -> tuple[bool, str]:
        """探测服务健康状态，返回 ``(是否健康, 说明)``。"""
        try:
            with urllib.request.urlopen(self.health_url, timeout=timeout) as resp:
                status = resp.status
                body = resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            # 前端根路径可能返回 3xx/4xx，只要进程在响应即视为已启动
            if exc.code in (301, 302, 401, 403, 404):
                return True, f"HTTP {exc.code}（服务已响应）"
            return False, f"HTTP {exc.code}"
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)

        if status != 200:
            return False, f"HTTP {status}"

        # 后端 /health 返回 JSON，进一步校验业务状态位
        if self.name == "backend":
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                return False, "响应不是合法 JSON"
            health = payload.get("status")
            if health not in ("ok", "degraded"):
                return False, f"health status={health!r}"
            return True, f"status={health} db={payload.get('database')}"
        return True, "HTTP 200"


BACKEND = Service("backend", BACKEND_PORT, BACKEND_DIR, BACKEND_HEALTH_URL, "backend.log")
FRONTEND = Service("frontend", FRONTEND_PORT, FRONTEND_DIR, FRONTEND_HEALTH_URL, "frontend.log")
SERVICES = [BACKEND, FRONTEND]


# --------------------------------------------------------------------------
# 进程管理
# --------------------------------------------------------------------------
def _spawn(service: Service) -> int | None:
    """启动单个服务，返回子进程 PID；失败返回 None。"""
    cmd, needs_shell = service.build_command()
    service.log_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        handle = open(service.log_file, "ab", buffering=0)  # noqa: SIM115
    except OSError as exc:
        _fail(f"{service.name} 日志文件打开失败：{exc}")
        return None

    popen_kwargs: dict = {
        "cwd": str(service.cwd),
        "stdout": handle,
        "stderr": subprocess.STDOUT,
    }
    if IS_WINDOWS:
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True

    try:
        # shell=needs_shell 仅用于 Windows 下启动 npm.cmd（.cmd 无法被 CreateProcess 直接执行）
        proc = subprocess.Popen(cmd, shell=needs_shell, **popen_kwargs)
    except Exception as exc:  # noqa: BLE001
        handle.close()
        _fail(f"{service.name} 启动失败：{exc}")
        return None

    service.pid_file.write_text(str(proc.pid), encoding="utf-8")
    _log(f"{service.name} 已启动 PID={proc.pid}，日志：{service.log_file}")
    return proc.pid


def _terminate(pid: int, graceful_timeout: float, force: bool) -> bool:
    """终止进程树。

    Windows 用 taskkill /T 覆盖整棵进程树（cmd → npm → node）；
    POSIX 用进程组信号（spawn 时已 start_new_session）。
    优雅失败后强杀，返回最终是否已不存在。
    """
    if not _pid_alive(pid):
        return True

    if not force:
        try:
            if IS_WINDOWS:
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/T"],
                    capture_output=True,
                    timeout=15,
                    check=False,
                )
            else:
                with contextlib.suppress(ProcessLookupError, PermissionError):
                    os.killpg(os.getpgid(pid), signal.SIGTERM)
        except Exception as exc:  # noqa: BLE001
            _warn(f"PID {pid} 优雅终止异常：{exc}")

        deadline = time.time() + graceful_timeout
        while time.time() < deadline:
            if not _pid_alive(pid):
                return True
            time.sleep(0.3)

    # 兜底强杀
    try:
        if IS_WINDOWS:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True,
                timeout=15,
                check=False,
            )
        else:
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.killpg(os.getpgid(pid), signal.SIGKILL)
    except Exception as exc:  # noqa: BLE001
        _warn(f"PID {pid} 强制终止异常：{exc}")

    for _ in range(10):
        if not _pid_alive(pid):
            return True
        time.sleep(0.3)
    return not _pid_alive(pid)


def _read_pid(service: Service) -> int | None:
    if not service.pid_file.is_file():
        return None
    try:
        return int(service.pid_file.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        return None


def _clear_pid(service: Service) -> None:
    with contextlib.suppress(OSError):
        service.pid_file.unlink()


def _stop_service(service: Service, graceful_timeout: float, force: bool) -> bool:
    """停止单个服务并校验端口释放，返回端口是否已空闲。"""
    pid = _read_pid(service)
    if pid is not None:
        if _pid_alive(pid):
            _log(f"停止 {service.name}（PID={pid}）...")
            _terminate(pid, graceful_timeout, force)
        else:
            _log(f"{service.name} 的 PID={pid} 已不存在，跳过终止")
    else:
        _log(f"{service.name} 无 PID 记录，按端口 {service.port} 兜底清理")

    # 端口兜底：PID 文件丢失或子进程脱离进程组时，仍按监听端口清理
    for stray in _pids_on_port(service.port):
        if stray == os.getpid():
            continue
        _warn(f"端口 {service.port} 仍被 PID {stray} 占用，清理中...")
        _terminate(stray, graceful_timeout, force)

    _clear_pid(service)

    released = not _port_in_use(service.port)
    if released:
        _ok(f"{service.name} 已停止，端口 {service.port} 已释放")
    else:
        _fail(f"{service.name} 停止后端口 {service.port} 仍被占用")
    return released


# --------------------------------------------------------------------------
# 子命令
# --------------------------------------------------------------------------
def cmd_up(args: argparse.Namespace) -> int:
    targets = _targets(args)
    RUN_DIR.mkdir(parents=True, exist_ok=True)

    if args.mode == "docker":
        return _docker_up(args)

    # 幂等启动：已运行且健康的服务直接跳过（含“先前会话遗留但未被本脚本管理”的进程，
    # 会顺手把其 PID 采纳进 pid 文件，后续 down/status 可统一管理）；
    # 端口被占但健康检查不通过 → 视为残留进程，清理后重启。
    to_start: list[Service] = []
    for svc in targets:
        if not _port_in_use(svc.port):
            to_start.append(svc)
            continue
        healthy, detail = svc.check_health()
        if healthy:
            _skip_running(svc, detail)
            continue
        holders = sorted(_pids_on_port(svc.port))
        if not args.force:
            _fail(
                f"端口 {svc.port} 被占用（PID {holders or '未知'}）且健康检查未通过"
                f"（{detail}）。请先执行 down，或使用 --force 清理残留后重启。"
            )
            return 1
        _warn(
            f"端口 {svc.port} 被占用（PID {holders}）但健康检查未通过（{detail}），"
            f"--force 清理残留进程后重启"
        )
        for stray in holders:
            _terminate(stray, args.graceful_timeout, force=True)
        deadline = time.time() + args.graceful_timeout
        while time.time() < deadline and _port_in_use(svc.port):
            time.sleep(0.3)
        if _port_in_use(svc.port):
            _fail(f"端口 {svc.port} 清理失败，放弃启动")
            return 1
        to_start.append(svc)

    if not to_start:
        _log("所有目标服务均已在运行，无需重复启动")
        return 0

    for svc in to_start:
        if _spawn(svc) is None:
            # 启动失败时回滚本次新拉起的服务，避免半成品状态残留
            for started in to_start[: to_start.index(svc)]:
                _stop_service(started, args.graceful_timeout, force=True)
            return 1

    if args.no_wait:
        _log("--no-wait：跳过健康检查")
    else:
        failed = False
        for svc in targets:
            healthy, detail = _wait_healthy(svc, args.wait_timeout)
            if healthy:
                _ok(f"{svc.name} 健康检查通过（{detail}）")
            else:
                _fail(f"{svc.name} 在 {args.wait_timeout}s 内未通过健康检查：{detail}")
                _fail(f"请查看日志：{svc.log_file}")
                failed = True

        if failed:
            _log("健康检查未通过，回滚本次启动的服务")
            for svc in to_start:
                _stop_service(svc, args.graceful_timeout, force=True)
            return 1

    _print_ready(targets)

    if args.foreground:
        return _supervise(args, targets)
    return 0


def _skip_running(service: Service, detail: str) -> None:
    """服务端口已被健康进程占用时的幂等处理：优先采纳 PID 以便统一管理。"""
    recorded = _read_pid(service)
    owner = next((p for p in _pids_on_port(service.port) if p != os.getpid()), None)
    if recorded and _pid_alive(recorded):
        _ok(f"{service.name} 已在运行（PID={recorded}），健康检查通过（{detail}），跳过启动")
    elif owner:
        # 先前实例不在本脚本 PID 文件内：写入 PID，让 down/status 能接管
        service.pid_file.write_text(str(owner), encoding="utf-8")
        _ok(
            f"{service.name} 已在运行（PID={owner}，先前实例），已记录 PID，"
            f"跳过启动（{detail}）"
        )
    else:
        _ok(f"{service.name} 已在运行，健康检查通过（{detail}），跳过启动")


def _supervise(args: argparse.Namespace, targets: list[Service]) -> int:
    """前台驻留：任一子进程退出即结束，返回其退出码对应状态。

    供真实终端（Ctrl+C 停止）与本沙箱环境（后台任务托管，避免子进程被回收）使用。
    另开终端执行 ``devctl down`` 也可停止全部服务并让本驻留自然退出。
    """
    _log("前台驻留模式：按 Ctrl+C 停止，或另开终端执行 devctl down")
    _log(f"运行日志目录：{LOG_DIR}")
    try:
        while True:
            for svc in targets:
                pid = _read_pid(svc)
                if not (pid and _pid_alive(pid)):
                    _warn(
                        f"{svc.name} 进程已退出（PID={pid}），驻留结束。"
                        f"日志：{svc.log_file}"
                    )
                    return 1
            time.sleep(2)
    except KeyboardInterrupt:
        _log("收到 Ctrl+C，正在停止服务...")
        return cmd_down(args)


def cmd_down(args: argparse.Namespace) -> int:
    if args.mode == "docker":
        return _docker_down(args)

    targets = _targets(args)
    all_released = True
    for svc in targets:
        if not _stop_service(svc, args.graceful_timeout, args.force):
            all_released = False

    if args.purge_logs and LOG_DIR.is_dir():
        shutil.rmtree(LOG_DIR, ignore_errors=True)
        _log("运行日志已清除")

    if all_released:
        _ok("所有服务已停止，端口资源已释放")
        return 0
    _fail("仍有端口未释放，请手动检查残留进程")
    return 1


def cmd_status(args: argparse.Namespace) -> int:
    if args.mode == "docker":
        return _docker_ps()

    any_down = False
    for svc in SERVICES:
        pid = _read_pid(svc)
        pid_state = f"PID={pid}（存活）" if pid and _pid_alive(pid) else (
            f"PID={pid}（已退出）" if pid else "无 PID 记录"
        )
        if _port_in_use(svc.port):
            healthy, detail = svc.check_health()
            state = f"监听中 · 健康检查{'通过' if healthy else '失败'}（{detail}）"
        else:
            state = "未运行"
            any_down = True
        print(f"[devctl] {svc.name:<9} 端口 {svc.port}  {state:<40} {pid_state}", flush=True)
    return 1 if any_down else 0


def cmd_restart(args: argparse.Namespace) -> int:
    if cmd_down(args) != 0:
        _warn("关闭阶段存在未释放端口，继续尝试启动")
    return cmd_up(args)


# --------------------------------------------------------------------------
# Docker compose 模式
# --------------------------------------------------------------------------
def _compose_base() -> list[str]:
    return [
        "docker",
        "compose",
        "-f",
        str(ROOT / "deploy" / "docker-compose.yml"),
        "--env-file",
        str(ROOT / "deploy" / ".env.example"),
    ]


def _require_docker() -> bool:
    if shutil.which("docker") is None:
        _fail("未找到 docker，请先安装 Docker Desktop 或改用 --mode local")
        return False
    return True


def _docker_up(args: argparse.Namespace) -> int:
    if not _require_docker():
        return 1
    _log("以 docker compose 方式启动全部服务（首次会构建镜像，耗时较长）...")
    proc = subprocess.run(
        _compose_base() + ["up", "-d", "--build"], cwd=str(ROOT), check=False
    )
    if proc.returncode != 0:
        _fail("docker compose up 失败")
        return 1
    _ok("compose 已启动；可用 `docker compose ps` 查看详情")
    _log(f"后端健康地址：{BACKEND_HEALTH_URL}")
    return 0


def _docker_down(args: argparse.Namespace) -> int:
    if not _require_docker():
        return 1
    proc = subprocess.run(_compose_base() + ["down"], cwd=str(ROOT), check=False)
    if proc.returncode != 0:
        _fail("docker compose down 失败")
        return 1
    _ok("compose 已停止并移除容器")
    return 0


def _docker_ps() -> int:
    if not _require_docker():
        return 1
    return subprocess.run(_compose_base() + ["ps"], cwd=str(ROOT), check=False).returncode


# --------------------------------------------------------------------------
# 辅助
# --------------------------------------------------------------------------
def _targets(args: argparse.Namespace) -> list[Service]:
    if getattr(args, "backend_only", False):
        return [BACKEND]
    if getattr(args, "frontend_only", False):
        return [FRONTEND]
    return list(SERVICES)


def _wait_healthy(service: Service, timeout: float) -> tuple[bool, str]:
    deadline = time.time() + timeout
    detail = "未探测"
    while time.time() < deadline:
        healthy, detail = service.check_health()
        if healthy:
            return True, detail
        time.sleep(0.6)
    return False, detail


def _print_ready(targets: list[Service]) -> None:
    print(flush=True)
    print("=" * 62, flush=True)
    print("  CampusSphere 已就绪", flush=True)
    for svc in targets:
        if svc.name == "backend":
            print(f"    后端 API  : http://127.0.0.1:{BACKEND_PORT}  (文档 /docs)")
        else:
            print(f"    前端站点  : http://127.0.0.1:{FRONTEND_PORT}")
    print(f"    运行日志  : {LOG_DIR}", flush=True)
    print(f"    停止服务  : python scripts{os.sep}devctl.py down", flush=True)
    print("=" * 62, flush=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="devctl",
        description="CampusSphere 一键启动 / 关闭 / 状态查看",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def _common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--backend-only", action="store_true", help="只操作后端服务")
        p.add_argument("--frontend-only", action="store_true", help="只操作前端服务")
        p.add_argument("--mode", choices=("local", "docker"), default="local",
                       help="local=直接起进程（默认）；docker=使用 compose")
        p.add_argument("--graceful-timeout", type=float, default=10.0,
                       help="优雅停止等待秒数，超时后强杀（默认 10）")

    p_up = sub.add_parser("up", help="启动服务并等待健康检查")
    p_up.add_argument("--no-wait", action="store_true", help="不等待健康检查")
    p_up.add_argument("--wait-timeout", type=float, default=90.0,
                      help="健康检查最长等待秒数（默认 90）")
    p_up.add_argument("--force", action="store_true",
                      help="清理端口上健康检查未通过的残留进程后重启")
    p_up.add_argument("--foreground", action="store_true",
                      help="前台驻留：任一子进程退出即结束（配合 Ctrl+C 或另开终端 down）")
    _common(p_up)
    p_up.set_defaults(func=cmd_up)

    p_down = sub.add_parser("down", help="停止服务并校验端口释放")
    p_down.add_argument("--force", action="store_true", help="跳过优雅终止直接强杀")
    p_down.add_argument("--purge-logs", action="store_true", help="同时删除运行日志")
    _common(p_down)
    p_down.set_defaults(func=cmd_down)

    p_status = sub.add_parser("status", help="查看服务状态")
    _common(p_status)
    p_status.set_defaults(func=cmd_status)

    p_restart = sub.add_parser("restart", help="先关闭再启动")
    p_restart.add_argument("--no-wait", action="store_true", help="不等待健康检查")
    p_restart.add_argument("--wait-timeout", type=float, default=90.0,
                           help="健康检查最长等待秒数（默认 90）")
    p_restart.add_argument("--force", action="store_true",
                           help="清理端口上健康检查未通过的残留进程后重启")
    p_restart.add_argument("--foreground", action="store_true",
                           help="前台驻留：任一子进程退出即结束（配合 Ctrl+C 或另开终端 down）")
    p_restart.add_argument("--purge-logs", action="store_true", help="同时删除运行日志")
    _common(p_restart)
    p_restart.set_defaults(func=cmd_restart)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if getattr(args, "backend_only", False) and getattr(args, "frontend_only", False):
        _fail("--backend-only 与 --frontend-only 不能同时使用")
        return 2
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        _warn("已中断")
        return 130


if __name__ == "__main__":
    sys.exit(main())
