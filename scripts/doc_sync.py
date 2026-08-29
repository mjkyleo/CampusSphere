#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CampusSphere 文档自动比对与同步工具（纯标准库，零外部依赖）。

目标
----
把「代码现状」与「现有文档」对齐，自动发现并报告二者之间的漂移（drift），
并生成可供人工或 CI 消费的产物：

1. ``docs/_generated/PROJECT_STATUS.md``   —— 由代码实时抽取的项目状态快照
                                              （目录结构 / 核心模块 / 依赖 / 测试 / 配置清单），
                                              头部标注「自动生成，勿手改」。
2. ``docs/_generated/DOC_DRIFT_REPORT.md`` —— 文档与代码的不一致清单，便于人工修正。
3. ``--sync-env-example``                   —— 把 config.py 中存在、但 backend/.env.example
                                              缺失的部署相关配置键（含默认值）自动补全到
                                              .env.example 的标记段内（幂等，不覆盖已有键）。
4. ``--check``                              —— 存在 warn 级漂移时退出码 1（适合 CI 卡点）。

用法
----
    python scripts/doc_sync.py                  # 分析并写出 _generated 文档
    python scripts/doc_sync.py --sync-env-example   # 补全 backend/.env.example
    python scripts/doc_sync.py --check          # CI：有 warn 级漂移则 exit 1
    python scripts/doc_sync.py --json out.json  # 额外导出结构化 JSON

设计说明
--------
- 配置项的「事实来源」是 ``backend/app/core/config.py`` 的 ``Settings`` 类与
  各 ``.env.example``；文档中出现的 ``UPPER_SNAKE`` 令牌与之比对即可发现过期引用。
- 全程只读解析文本，不 import 项目代码、不引入 PyYAML 等第三方库，保证可移植。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# --------------------------------------------------------------------------- #
# 路径常量
# --------------------------------------------------------------------------- #
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
BACKEND = REPO_ROOT / "backend"
FRONTEND = REPO_ROOT / "frontend"
DOCS = REPO_ROOT / "docs"
GEN_DIR = DOCS / "_generated"
CONFIG_PY = BACKEND / "app" / "core" / "config.py"
PYPROJECT = BACKEND / "pyproject.toml"
ENV_EXAMPLE = BACKEND / ".env.example"

# 目录树扫描时忽略的目录 / 文件（避免 node_modules、缓存、构建产物、日志污染快照）
TREE_EXCLUDES_DIRS = {
    ".git", ".venv", "node_modules", "__pycache__", ".ruff_cache",
    ".worktrees", ".codebuddy", ".workbuddy", ".run", "dist", "build",
    ".github", ".idea", ".vscode", "coverage", "pytest-cache-files-trjnhvje",
    ".pytest_cache", "__pycache__",
}
TREE_EXCLUDES_SUFFIXES = {".pyc", ".map", ".mjs", ".tsbuildinfo", ".log", ".db", ".egg-info"}

# 库自动消费 / 运行时变量，不在本项目 config.py 中声明但合法，避免误报
KNOWN_LIB_TOKENS = {
    "OTEL_EXPORTER_OTLP_ENDPOINT", "OTEL_EXPORTER_OTLP_INSECURE",
    "OTEL_SERVICE_NAME", "GEMINI_API_KEY", "API_KEY", "NODE_ENV",
    "PORT", "HOST", "GATEWAY_TOKEN", "INITIAL_MOCK_DATA",
    "QQ_APP_ID", "QQ_APP_SECRET", "WECHAT_APP_ID", "WECHAT_APP_SECRET",
    "SMTP_SSL",
}
KNOWN_PREFIXES = ("VITE_", "OTEL_")

# 单大写词（非 snake_case 配置）直接忽略，减少散文/代码噪声
NOISE_WORDS = {
    "GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS",
    "HTTP", "HTTPS", "REST", "CRUD", "ASGI", "WSGI", "ORM", "DTO", "DAO",
    "RPC", "GRPC", "JWT", "CORS", "CSRF", "XSS", "SQL", "SQLITE", "POSTGRES",
    "REDIS", "SMTP", "YAML", "JSON", "HTML", "CSS", "JS", "TS", "URL", "URI",
    "API", "WS", "TLS", "SSL", "TCP", "UDP", "IP", "DNS", "DB", "OTP",
    "UTC", "GMT", "ID", "UUID", "OK", "CI", "CD", "QA", "ML", "AI", "GPU",
    "CPU", "RAM", "CLI", "GUI", "TTY", "SSH", "FTP", "SFTP", "GIT", "NPM",
    "PIP", "ENV", "LOG", "ERR", "TMP", "DEV", "PROD", "STAG", "TEST", "BAK",
    "OLD", "NEW", "ISO8601", "EACCES", "README", "TRANSITIONS", "PUBLIC_PATHS",
    "LIKE", "ITEM", "ON_SALE", "OFF_SHELF", "PENDING", "ASYNC", "SYNC",
}

# 后端模块目录 -> 文档中应出现的中文别名（用于模块覆盖度核查）
MODULE_ALIASES = {
    "auth": "认证", "user": "用户", "item": "二手", "course": "课程",
    "canteen": "食堂", "job": "兼职", "share": "分享", "teammate": "组队",
    "message": "消息", "report": "举报", "admin": "管理后台", "ai": "AI",
    "launcher": "启动器", "storage": "对象存储",
}

# 部署相关、缺失时应提示补全进 .env.example 的配置键关键词
DEPLOY_RELEVANT = (
    "SECRET", "SMTP", "ADMIN", "MINIO", "MEILI", "CACHE", "CAPTCHA",
    "CODE", "DB_POOL", "REDIS", "CORS", "RATE_LIMIT", "DEBUG", "APP_NAME",
)

ENV_TOKEN_RE = re.compile(r"\b([A-Z][A-Z0-9_]{3,})\b")
FIELD_RE = re.compile(r"^\s*(?P<name>[a-z_][a-z0-9_]*)\s*:\s*(?P<typ>[^\=]+?)\s*=\s*(?P<val>.+?)\s*$")
METHOD_PATH_RE = re.compile(r"^#{2,4}\s+(?:GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+`?/", re.MULTILINE)
ROUTE_DECORATOR_RE = re.compile(r"@router\.(get|post|put|patch|delete)\(")
REQ_PY_RE = re.compile(r'requires-python\s*=\s*["\']([^"\']+)["\']')
ENV_EXAMPLE_MARKER = "# ===== 以下由 scripts/doc_sync.py --sync-env-example 自动补全（请勿手改此段）====="


# --------------------------------------------------------------------------- #
# 工具函数
# --------------------------------------------------------------------------- #
def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _paren_depth(s: str) -> int:
    return s.count("(") - s.count(")")


def clean_default(raw: str) -> str:
    """化简默认值表达式：剥离行内注释、展开 Field(default_factory=...)。"""
    raw = re.sub(r"\s+#.*$", "", raw).strip()
    if "default_factory=lambda:" in raw:
        m = re.search(r"lambda:\s*(.+)", raw)
        if m:
            return m.group(1).strip().rstrip(")").strip()
    if "default_factory=dict" in raw:
        return "{}"
    if "default_factory=list" in raw:
        return "[]"
    m = re.search(r"default\s*=\s*([^,\)]+)", raw)
    if m:
        return m.group(1).strip()
    return raw


# --------------------------------------------------------------------------- #
# 1. 目录结构扫描
# --------------------------------------------------------------------------- #
def scan_tree(root: Path, prefix: str = "", depth: int = 0, max_depth: int = 3) -> list[str]:
    lines: list[str] = []
    if depth > max_depth:
        return lines
    try:
        entries = sorted(
            p for p in root.iterdir()
            if p.name not in TREE_EXCLUDES_DIRS
            and not p.name.startswith(".")
            and not (p.is_file() and p.suffix in TREE_EXCLUDES_SUFFIXES)
            and not (p.is_dir() and p.name.startswith("pytest"))
        )
    except OSError:
        return lines

    # 前端为巨型目录：仅列一级 + 计数，避免刷屏
    if root == FRONTEND and depth >= 1:
        return lines

    for p in entries:
        if p.is_dir():
            lines.append(f"{prefix}{p.name}/")
            if p.name == "frontend":
                sub = [q for q in p.iterdir()
                       if q.name not in TREE_EXCLUDES_DIRS and not q.name.startswith(".")]
                for s in sub[:14]:
                    lines.append(f"{prefix}  {s}/")
                if len(sub) > 14:
                    lines.append(f"{prefix}  … (+{len(sub) - 14} 项)")
            else:
                lines.extend(scan_tree(p, prefix + "  ", depth + 1, max_depth))
        else:
            lines.append(f"{prefix}{p.name}")
    return lines


# --------------------------------------------------------------------------- #
# 2. 核心模块抽取
# --------------------------------------------------------------------------- #
def discover_backend_modules() -> list[dict]:
    modules_dir = BACKEND / "app" / "modules"
    out: list[dict] = []
    if not modules_dir.is_dir():
        return out
    for d in sorted(modules_dir.iterdir()):
        if not d.is_dir() or d.name.startswith("__"):
            continue
        router = d / "router.py"
        routes = len(ROUTE_DECORATOR_RE.findall(read_text(router))) if router.is_file() else 0
        out.append({
            "name": d.name, "routes": routes,
            "has_router": router.is_file(),
            "has_service": (d / "service.py").is_file(),
            "has_schemas": (d / "schemas.py").is_file(),
            "alias": MODULE_ALIASES.get(d.name, ""),
        })
    return out


def frontend_pages() -> list[str]:
    pages_dir = FRONTEND / "pages"
    if not pages_dir.is_dir():
        return []
    return sorted(p.stem for p in pages_dir.glob("*.tsx") if not p.name.startswith("__"))


def collect_dependencies() -> dict:
    deps: dict = {"backend": [], "frontend": {}}
    txt = read_text(PYPROJECT)
    in_block = False
    for line in txt.splitlines():
        if re.match(r"\s*dependencies\s*=\s*\[", line):
            in_block = True
            continue
        if in_block:
            if line.strip() == "]":
                break
            m = re.match(r'\s*"([^"]+)"', line)
            if m:
                deps["backend"].append(m.group(1))
    pkg = FRONTEND / "package.json"
    try:
        deps["frontend"] = json.loads(read_text(pkg) or "{}").get("dependencies", {})
    except (json.JSONDecodeError, OSError):
        deps["frontend"] = {}
    return deps


def collect_tests() -> list[str]:
    tests_dir = BACKEND / "tests"
    if not tests_dir.is_dir():
        return []
    return sorted(p.name for p in tests_dir.glob("test_*.py"))


def count_api_endpoints() -> int:
    return len(METHOD_PATH_RE.findall(read_text(DOCS / "API_Reference.md")))


# --------------------------------------------------------------------------- #
# 3. 配置项抽取（事实来源：config.py + .env.example + school.yaml 顶层）
# --------------------------------------------------------------------------- #
def extract_config_fields() -> list[dict]:
    txt = read_text(CONFIG_PY)
    cls_idx = txt.find("class Settings")
    if cls_idx == -1:
        return []
    seg = txt[cls_idx:]
    lines = seg.splitlines()
    fields: list[dict] = []
    pending: list[str] = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if re.match(r"^#\s*[-=*]{3,}", stripped):       # 章节横幅：清空上下文
            pending = []
        elif stripped.startswith("#"):
            pending.append(stripped.lstrip("# ").strip())
        elif not stripped:
            pending = []
        else:
            m = FIELD_RE.match(lines[i])
            if m:
                name = m.group("name")
                val = m.group("val")
                depth = _paren_depth(val)
                j = i
                while depth != 0 and j + 1 < len(lines):   # 续读跨行 RHS
                    j += 1
                    val += " " + lines[j].strip()
                    depth += _paren_depth(lines[j])
                inline_m = re.search(r"#\s*(.*)$", lines[i])
                inline = inline_m.group(1).strip() if inline_m else ""
                purpose = (inline or " ".join(pending))[:160]
                fields.append({
                    "name": name.upper(),
                    "type": m.group("typ").strip(),
                    "default": clean_default(val),
                    "purpose": purpose,
                })
                pending = []
                i = j + 1
                continue
            pending = []
        i += 1
    return fields


def extract_env_example_keys() -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for p in REPO_ROOT.rglob(".env.example"):
        if "node_modules" in str(p):
            continue
        keys: set[str] = set()
        for line in read_text(p).splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                keys.add(line.split("=", 1)[0].strip())
        result[str(p.relative_to(REPO_ROOT)).replace(os.sep, "/")] = keys
    return result


def extract_school_yaml_sections() -> list[str]:
    txt = read_text(REPO_ROOT / "config" / "school.yaml")
    return [m.group(1) for m in re.finditer(r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*:", txt)]


def extract_requires_python() -> str:
    m = REQ_PY_RE.search(read_text(PYPROJECT))
    return m.group(1) if m else ""


def format_env_value(field: dict) -> str:
    """把 config.py 默认值转成 .env 行右侧的字面量。"""
    t = field["type"]
    d = field["default"]
    if "bool" in t:
        return "true" if d.lower() in ("true", "1", "yes", "on") else "false"
    if "int" in t or "float" in t:
        return d
    if "list" in t.lower() or d.startswith("[") or d == "{}":
        return d
    if d == "":
        return ""
    return d


# --------------------------------------------------------------------------- #
# 4. 文档扫描
# --------------------------------------------------------------------------- #
def read_docs() -> dict[str, str]:
    docs: dict[str, str] = {}
    for p in DOCS.glob("*.md"):
        docs[p.name] = read_text(p)
    docs["README.md"] = read_text(REPO_ROOT / "README.md")
    return docs


def extract_readme_feature_names(readme: str) -> list[str]:
    names: list[str] = []
    in_table = False
    for line in readme.splitlines():
        if "功能特性" in line:
            in_table = True
            continue
        if in_table:
            if line.strip().startswith("|") and "模块" not in line and "---" not in line:
                cell = line.split("|")[1].strip()
                if cell:
                    names.append(cell)
            elif line.strip().startswith("## ") and "功能特性" not in line:
                break
    return names


def scan_env_tokens_in_docs(docs: dict[str, str]) -> set[str]:
    tokens: set[str] = set()
    for text in docs.values():
        tokens.update(ENV_TOKEN_RE.findall(text))
    return tokens


# --------------------------------------------------------------------------- #
# 5. 漂移检测
# --------------------------------------------------------------------------- #
def detect_drift(state: dict, docs: dict[str, str]) -> list[dict]:
    drift: list[dict] = []
    cfg_fields = {f["name"] for f in state["config_fields"]}
    all_env_keys: set[str] = set()
    for keys in state["env_examples"].values():
        all_env_keys |= keys
    known = cfg_fields | all_env_keys | KNOWN_LIB_TOKENS

    # (a) 文档引用了不存在/过期的环境变量令牌（启发式，归为 info 级「请核对」）
    for tok in sorted(scan_env_tokens_in_docs(docs)):
        if any(tok.startswith(p) for p in KNOWN_PREFIXES):
            continue
        if "_" not in tok or tok.endswith("_"):          # 仅关注 snake_case；排除通配符 MINIO_*
            continue
        if tok in NOISE_WORDS or tok in known:
            continue
        if any(tok + "_" == k[:len(tok) + 1] for k in known):   # 是某已知键的前缀（如 ACCESS_TOKEN_EXPIRE）
            continue
        drift.append({
            "severity": "info", "kind": "stale_env_var",
            "detail": f"文档引用了未在 config.py / .env.example 中定义的环境变量 `{tok}`，"
                      f"可能为过期配置键或拼写错误，请核对。",
        })

    # (b) backend/.env.example 缺失可在 .env 覆盖的部署相关字段（排除 Dict 嵌套配置）
    backend_env = state["env_examples"].get("backend/.env.example", set())
    missing: list[str] = []
    for f in state["config_fields"]:
        if f["name"] in backend_env:
            continue
        if "Dict" in f["type"]:                 # 嵌套配置走 school.yaml，不应作为扁平 env 键
            continue
        if any(k in f["name"] for k in DEPLOY_RELEVANT):
            missing.append(f["name"])
    if missing:
        drift.append({
            "severity": "warn", "kind": "env_example_incomplete",
            "detail": "backend/.env.example 缺失以下可在 .env 中覆盖的配置键（建议补全以便部署者对照）："
                      + "、".join(missing),
        })

    # (c) 后端模块未被文档覆盖
    covered_doc = docs.get("README.md", "") + docs.get("usage.md", "")
    for mod in state["modules"]:
        alias = mod["alias"]
        if not ((mod["name"] in covered_doc) or (alias and alias in covered_doc)):
            drift.append({
                "severity": "info", "kind": "module_undocumented",
                "detail": f"后端模块 `{mod['name']}`（别名：{alias or '无'}）未在 README/usage.md 中提及。",
            })

    # (d) Python 版本声明不一致
    req = state["requires_python"]
    if req:
        base = req.lstrip(">=").lstrip("^").split(".")
        for fname, text in docs.items():
            for m in re.finditer(r"Python\s*\|\s*([0-9]+\.[0-9]+)\+", text):
                if m.group(1) != ".".join(base[:2]):
                    drift.append({
                        "severity": "warn", "kind": "version_mismatch",
                        "detail": f"{fname} 写「Python {m.group(1)}+」，但 pyproject 要求 `{req}`，请统一。",
                    })

    # (e) API 文档接口数声明与实际不符
    claimed = None
    for m in re.finditer(r"(\d+)\s*个接口", docs.get("README.md", "")):
        claimed = int(m.group(1))
    actual = state["api_endpoints"]
    if claimed and actual and claimed != actual:
        drift.append({
            "severity": "warn", "kind": "api_count_mismatch",
            "detail": f"README 声明 {claimed} 个接口，API_Reference.md 实际抽取到 {actual} 个，请核对更新。",
        })

    return drift


# --------------------------------------------------------------------------- #
# 6. .env.example 自动补全（幂等）
# --------------------------------------------------------------------------- #
def sync_env_example(state: dict) -> list[str]:
    """把 backend/.env.example 缺失的部署相关配置键补全到标记段。返回新增的键列表。"""
    if not ENV_EXAMPLE.is_file():
        return []
    text = read_text(ENV_EXAMPLE)
    existing = {line.split("=", 1)[0].strip()
                for line in text.splitlines() if line.strip() and not line.startswith("#") and "=" in line}
    backend_env = state["env_examples"].get("backend/.env.example", set())
    missing = [f for f in state["config_fields"]
               if f["name"] not in existing and f["name"] not in backend_env
               and "Dict" not in f["type"]
               and any(k in f["name"] for k in DEPLOY_RELEVANT)]

    if ENV_EXAMPLE_MARKER in text:           # 已同步过，避免重复追加
        return []
    if not missing:
        return []

    block = ["", ENV_EXAMPLE_MARKER]
    for f in missing:
        if f["purpose"] and f["purpose"] != "—":
            block.append(f"# {f['purpose']}")
        block.append(f"{f['name']}={format_env_value(f)}")
    block.append("")
    ENV_EXAMPLE.write_text(text.rstrip() + "\n" + "\n".join(block), encoding="utf-8")
    return [f["name"] for f in missing]


# --------------------------------------------------------------------------- #
# 7. 产物生成
# --------------------------------------------------------------------------- #
def build_state() -> dict:
    return {
        "generated_at": now_iso(),
        "tree": scan_tree(REPO_ROOT),
        "modules": discover_backend_modules(),
        "frontend_pages": frontend_pages(),
        "dependencies": collect_dependencies(),
        "tests": collect_tests(),
        "config_fields": extract_config_fields(),
        "env_examples": extract_env_example_keys(),
        "school_sections": extract_school_yaml_sections(),
        "requires_python": extract_requires_python(),
        "api_endpoints": count_api_endpoints(),
        "readme_features": extract_readme_feature_names(read_docs().get("README.md", "")),
    }


def render_project_status(state: dict) -> str:
    s = state
    L: list[str] = []
    L.append("<!-- 本文件由 scripts/doc_sync.py 自动生成，请勿手工编辑 -->")
    L.append("# 项目状态快照（自动生成）\n")
    L.append(f"> 生成时间：{s['generated_at']}  ｜  来源：`scripts/doc_sync.py`")
    L.append("> 本文件由代码实时抽取，反映当前仓库真实状态；如需修改内容，请改代码后重跑工具。\n")

    L.append("## 目录结构（节选）\n")
    L.append("```text")
    L.append("CampusSphere/")
    for ln in s["tree"]:
        L.append("  " + ln)
    L.append("```\n")

    L.append("## 核心后端模块\n")
    L.append("| 模块 | 路由数 | router | service | schemas | 文档别名 |")
    L.append("| --- | ---: | --- | --- | --- | --- |")
    for m in s["modules"]:
        L.append(f"| `{m['name']}` | {m['routes']} | {'✅' if m['has_router'] else '—'} | "
                 f"{'✅' if m['has_service'] else '—'} | {'✅' if m['has_schemas'] else '—'} | {m['alias'] or '—'} |")
    L.append(f"\n共 {len(s['modules'])} 个业务模块。\n")

    L.append("## 前端页面\n")
    pages = s["frontend_pages"]
    L.append(f"共 {len(pages)} 个页面：`" + "`、`".join(pages) + "`\n")

    L.append("## 依赖\n")
    L.append(f"- Python 运行时要求：`{s['requires_python'] or '未声明'}`")
    L.append(f"- 后端依赖（{len(s['dependencies']['backend'])} 项）：`"
             + "`、`".join(s['dependencies']['backend'][:12]) + "` 等")
    fe = s["dependencies"]["frontend"]
    n = len(fe) if isinstance(fe, dict) else 0
    L.append(f"- 前端依赖：{n} 项（React / Vite / Express 等，详见 frontend/package.json）\n")

    L.append("## 测试\n")
    tests = s["tests"]
    L.append(f"后端测试文件 {len(tests)} 个：`" + "`、`".join(tests) + "`\n")

    L.append("## 配置项清单（来自 config.py）\n")
    L.append("> 完整「初次部署/启动配置」见 [docs/DEPLOYMENT.md](DEPLOYMENT.md)。\n")
    L.append("| 配置键（环境变量） | 类型 | 默认值 | 用途 |")
    L.append("| --- | --- | --- | --- |")
    for f in s["config_fields"]:
        default = f["default"].replace("|", "\\|")
        purpose = f["purpose"].replace("|", "\\|") or "—"
        L.append(f"| `{f['name']}` | {f['type']} | `{default}` | {purpose} |")
    L.append("")

    L.append("## 多校配置（config/school.yaml 顶层区块）\n")
    L.append("`" + "`、`".join(s["school_sections"]) + "`\n")

    L.append("## 接口文档\n")
    L.append(f"- API_Reference.md 抽取接口数：**{s['api_endpoints']}**")
    return "\n".join(L) + "\n"


def render_drift_report(state: dict, drift: list[dict]) -> str:
    L: list[str] = []
    L.append("<!-- 本文件由 scripts/doc_sync.py 自动生成，请勿手工编辑 -->")
    L.append("# 文档漂移报告（自动生成）\n")
    L.append(f"> 生成时间：{state['generated_at']}  ｜  来源：`scripts/doc_sync.py`\n")
    if not drift:
        L.append("✅ 未检测到明显漂移，文档与代码现状一致。\n")
        return "\n".join(L) + "\n"
    order = {"warn": 0, "info": 1}
    drift.sort(key=lambda d: order.get(d["severity"], 2))
    warns = [d for d in drift if d["severity"] == "warn"]
    infos = [d for d in drift if d["severity"] == "info"]
    L.append(f"共发现 **{len(drift)}** 处漂移（⚠️ 需关注 {len(warns)} 项，ℹ️ 提示 {len(infos)} 项）。\n")
    L.append("## ⚠️ 需关注\n")
    for d in warns:
        L.append(f"- **[{d['kind']}]** {d['detail']}")
    L.append("\n## ℹ️ 提示\n")
    for d in infos:
        L.append(f"- **[{d['kind']}]** {d['detail']}")
    L.append("\n---\n建议：修正文档后重跑 `python scripts/doc_sync.py --check`，"
             "待无 warn 级漂移即可合入。")
    return "\n".join(L) + "\n"


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="CampusSphere 文档自动比对与同步工具")
    ap.add_argument("--sync-env-example", action="store_true", help="补全 backend/.env.example 缺失的部署配置键")
    ap.add_argument("--check", action="store_true", help="存在 warn 级漂移时退出码 1（CI 卡点）")
    ap.add_argument("--json", metavar="PATH", help="额外导出结构化 JSON")
    args = ap.parse_args(argv)

    state = build_state()
    docs = read_docs()
    drift = detect_drift(state, docs)

    if args.sync_env_example:
        added = sync_env_example(state)
        if added:
            print(f"[doc_sync] 已补全 backend/.env.example：{', '.join(added)}")
        else:
            print("[doc_sync] backend/.env.example 无需补全（或无缺失键）")

    GEN_DIR.mkdir(parents=True, exist_ok=True)
    (GEN_DIR / "PROJECT_STATUS.md").write_text(render_project_status(state), encoding="utf-8")
    (GEN_DIR / "DOC_DRIFT_REPORT.md").write_text(render_drift_report(state, drift), encoding="utf-8")

    if args.json:
        jp = Path(args.json)
        jp.parent.mkdir(parents=True, exist_ok=True)
        jp.write_text(json.dumps({"state": _json_safe(state), "drift": drift},
                                 ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[doc_sync] modules={len(state['modules'])} pages={len(state['frontend_pages'])} "
          f"config_fields={len(state['config_fields'])} tests={len(state['tests'])} "
          f"api_endpoints={state['api_endpoints']}")
    print(f"[doc_sync] drift={len(drift)} -> docs/_generated/")

    warns = [d for d in drift if d["severity"] == "warn"]
    if args.check and warns:
        print(f"[doc_sync] ⚠️ {len(warns)} 处需关注漂移，exit 1")
        return 1
    return 0


def _json_safe(state: dict) -> dict:
    s = dict(state)
    s["env_examples"] = {k: sorted(v) for k, v in state["env_examples"].items()}
    return s


if __name__ == "__main__":
    sys.exit(main())
