"""配置热更新：Redis Pub/Sub 驱动的 school.yaml 原地刷新。

要解决的问题
------------
``config/school.yaml`` 中的静态配置（学校名称、域名白名单、业务规则阈值等）
在进程启动时被一次性读入 ``Settings`` 单例，此后只存在于内存。运维改了 YAML
必须**重启服务**才生效 —— 对"改个白名单就要中断全校服务"的校园运维场景
是不可接受的。

方案：lifespan 中启动一个长驻后台 Task 订阅 Redis ``config:reload`` 频道；
管理员改完配置后调用一次发布接口，所有实例在毫秒级内各自重读 YAML 并
**原地刷新 Settings 单例**（不重建对象，因此所有持有 ``settings`` 引用的
模块自动看到新值）。

为什么是"原地刷新"而不是"重建单例"
------------------------------------
``settings`` 由 ``lru_cache`` 缓存并以 ``from app.core.config import settings``
的形式被数十个模块**在导入期绑定**。若重建一个新对象，那些模块持有的仍是
旧引用，热更新会**静默失效**（最危险的一类 bug：看起来生效了，实际没生效）。
``load_school_config()`` 是原地 ``setattr``，天然规避这个问题。

优雅降级
--------
Redis 不可用时本模块**只打印日志并退化为"无热更新"**，绝不阻断主进程启动：
后台 Task 在订阅失败时进入慢速重试（不抛异常、不退出），配置依旧可以在
下次重启时生效。这满足"配置热更新是增强能力，不是启动依赖"的定位。

注意：本模块**只负责 school.yaml 静态配置**。
邮箱注册规则（``auth.email_register``）等后台可改配置走 DB 的 ``app_config``
表，每次请求实时读取，本来就无需热更新。
"""

from __future__ import annotations

import asyncio

from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis import redis_publish, redis_subscribe

_logger = get_logger("core.config_reload")

# 配置重载广播频道。所有实例订阅同一频道，实现"一次发布、全集群生效"。
CONFIG_RELOAD_CHANNEL = "config:reload"

# Redis 不可用时的重订阅间隔（秒）。
# 取较大值：配置热更新不是高频路径，过度重试只会刷日志并持续消耗连接超时。
# 做成模块常量以便测试 monkeypatch 缩短等待。
RETRY_INTERVAL_SECONDS = 30.0

_task: asyncio.Task | None = None


async def publish_config_reload(reason: str = "manual") -> int:
    """广播配置重载消息，返回接收到该消息的订阅者数量。

    :param reason: 触发原因，仅用于审计日志（如 ``admin:email-config``）。
    :return: 接收者数量；Redis 不可用时为 0（**不抛异常**，调用方无需降级处理）。
    """
    try:
        return await redis_publish(CONFIG_RELOAD_CHANNEL, reason)
    except Exception as exc:
        # 发布失败不应让"改配置"这个主操作失败：配置已落库，
        # 最坏情况只是热更新没广播出去，重启后依然生效。
        _logger.warning("config_reload_publish_failed", error=str(exc), reason=reason)
        return 0


async def reload_settings(reason: str = "") -> None:
    """重读 school.yaml 并原地刷新 Settings 单例（供后台 Task 与测试调用）。

    YAML 读取是同步文件 IO，用 ``to_thread`` 委派，避免热更新这个低频操作
    反过来造成事件循环抖动。
    """
    await asyncio.to_thread(settings.load_school_config)
    _logger.info(
        "config_reloaded",
        reason=reason,
        school=settings.school_name,
    )


async def _listen() -> None:
    """长驻监听循环：订阅频道 → 收到消息 → 原地刷新配置。

    任一轮循环内的异常都不会终止本 Task：Redis 抖动是常态，
    监听器必须能自愈，否则热更新会"用着用着就没了"。
    """
    while True:
        pubsub = None
        try:
            pubsub = await redis_subscribe(CONFIG_RELOAD_CHANNEL)
            if pubsub is None:
                # 优雅降级：Redis 不可用。不打 error（这不是故障），
                # 记录 warning 后慢速重试，等待 Redis 恢复。
                _logger.warning(
                    "config_reload_unavailable_fallback",
                    reason="redis unavailable, hot-reload disabled until it recovers",
                    retry_in_seconds=RETRY_INTERVAL_SECONDS,
                )
                await asyncio.sleep(RETRY_INTERVAL_SECONDS)
                continue

            _logger.info("config_reload_listener_started", channel=CONFIG_RELOAD_CHANNEL)
            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                reason = message.get("data") or ""
                try:
                    await reload_settings(reason=str(reason))
                except Exception as exc:
                    # 单次刷新失败（如 YAML 语法错误）绝不能杀掉监听器：
                    # 否则一次手误改错配置，就把热更新能力永久弄丢了。
                    _logger.error("config_reload_failed", error=str(exc), reason=str(reason))
        except asyncio.CancelledError:
            # 关闭信号：向上抛，由 stop() 统一收敛
            raise
        except Exception as exc:
            _logger.warning("config_reload_listener_error", error=str(exc))
        finally:
            if pubsub is not None:
                try:
                    await pubsub.aclose()
                except Exception:
                    pass
        # 连接断开后稍等再重连，避免 Redis 宕机期间的紧密重试风暴
        await asyncio.sleep(RETRY_INTERVAL_SECONDS)


async def start_config_reloader() -> None:
    """在 lifespan 中启动配置热更新监听（幂等）。"""
    global _task
    # 已结束的任务（如 Redis 不可用导致立即退出）不阻塞重启，
    # 只有存活任务才跳过 —— 与 ws.manager.start_listener 保持一致。
    if _task is not None and not _task.done():
        return
    _task = asyncio.create_task(_listen())


async def stop_config_reloader() -> None:
    """取消监听任务（应用关闭期调用）。幂等，可重复调用。"""
    global _task
    task, _task = _task, None
    if task is None:
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    except Exception as exc:
        _logger.warning("config_reload_stop_error", error=str(exc))
