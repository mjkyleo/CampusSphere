"""WebSocket 实时通信。

- 连接鉴权：建立连接后客户端须在超时窗口内发送首帧
  ``{"event": "auth", "token": <access>}``（token 走 WS 帧，不再走 URL
  查询串——查询串会被 nginx / 反代访问日志原样记录，等于把长期有效的
  登录凭证写进日志文件）
- user_id -> {websocket} 映射（支持多端）
- Redis Pub/Sub 多实例广播（单实例/无 Redis 时降级为内存直发）
- 心跳（ping/pong）、断线重连消息补偿（conv/last_seq/since 仍走查询串，
  均为非敏感游标参数）
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.common.enums import UserStatus
from app.core.database import SessionLocal
from app.core.exceptions import BizError, ErrorCode
from app.core.logging import get_logger
from app.core.redis import redis_psubscribe, redis_publish
from app.core.security import decode_token, is_token_revoked
from app.modules.auth.models import User
from app.modules.message.models import Message, Participant
from app.modules.message.seq import seq_store
from app.modules.message.service import send_message

_logger = get_logger("message.ws")

_WS_CHANNEL = "conv"

# 本进程实例标识：随消息广播给其他实例，监听器据此跳过自己发布的消息，
# 否则发布实例的本地接收者会被「本地直发 + 自身监听」重复投递。
# 多 worker 部署时每个 worker 进程各自持有唯一值，恰好符合语义。
_INSTANCE_ID = uuid.uuid4().hex


class ConnectionManager:
    """管理所有在线 WebSocket 连接。"""

    def __init__(self) -> None:
        # user_id -> set(websocket)
        self._connections: dict[str, set[WebSocket]] = {}
        self._listener_task: asyncio.Task | None = None

    async def connect(self, user_id: str, ws: WebSocket) -> None:
        # 注意：accept 由 websocket_endpoint 统一调用，此处只注册连接，避免重复 accept
        self._connections.setdefault(user_id, set()).add(ws)
        _logger.info("ws_connected", user_id=user_id, online=len(self._connections[user_id]))

    def disconnect(self, user_id: str, ws: WebSocket) -> None:
        conns = self._connections.get(user_id)
        if conns and ws in conns:
            conns.discard(ws)
            if not conns:
                self._connections.pop(user_id, None)

    async def send_to_user(self, user_id: str, payload: dict) -> None:
        for ws in list(self._connections.get(user_id, set())):
            try:
                await ws.send_json(payload)
            except Exception:
                self.disconnect(user_id, ws)

    async def publish(self, conversation_id: str, payload: dict) -> None:
        """本地直发 + Redis 广播（多实例）。

        投递收敛为**单一路径**：本实例连接只走本地直发；Redis 广播供其他
        实例的监听器消费。广播体携带 ``origin``（发布实例标识）与
        ``recipients``（全体参与者，含发送者——多端登录时发送者的其他
        设备同样要收到回显），监听器跳过自己实例发布的消息，防止
        「本地直发 + 自身监听」对本地用户重复投递。
        """
        async with SessionLocal() as db:
            parts = (await db.scalars(
                select(Participant.user_id).where(
                    Participant.conversation_id == conversation_id
                )
            )).all()
        str_parts = [str(p) for p in parts]
        # 本地直发：直接推送给本实例连接（发送者本人也收到，与在线多端回显一致）
        for uid in str_parts:
            await self.send_to_user(uid, payload)
        # 跨实例广播：recipients 为权威投递名单，origin 供监听器去重
        payload["recipients"] = str_parts
        payload["origin"] = _INSTANCE_ID
        await redis_publish(f"{_WS_CHANNEL}:{conversation_id}", json.dumps(payload, default=str))

    async def start_listener(self) -> None:
        # 已结束的任务（如无 Redis 时立即返回）不阻塞重启，只有存活任务才跳过。
        if self._listener_task is not None and not self._listener_task.done():
            return
        self._listener_task = asyncio.create_task(self._redis_listen())

    async def stop_listener(self) -> None:
        """取消 Redis 广播监听任务（应用关闭期调用）。

        幂等：重复调用或从未启动均安全返回；取消过程中产生的
        ``CancelledError`` 属预期，不上抛以免阻断关闭流程。
        """
        task, self._listener_task = self._listener_task, None
        if task is None:
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            _logger.warning("ws_listener_stop_error", error=str(exc))

    async def _redis_listen(self) -> None:
        # P2-10：监听循环带自愈——启动失败或运行中异常都会带退避重启，
        # 而不是静默退出（多实例部署的跨实例投递曾会因此永久失效）。
        # 仅 stop_listener 主动取消（CancelledError）才真正退出。
        backoff = 1
        while True:
            try:
                pubsub = await redis_psubscribe(f"{_WS_CHANNEL}:*")
                if pubsub is None:
                    # 无 Redis（降级内存直发）：单实例语义完整，无需重试
                    _logger.info("ws_redis_listener_unavailable_no_redis")
                    return
                _logger.info("ws_redis_listener_started")
                backoff = 1
                async for message in pubsub.listen():
                    # psubscribe 的数据消息类型是 pmessage（message 仅精确订阅产生）
                    if message.get("type") != "pmessage":
                        continue
                    try:
                        payload = json.loads(message["data"])
                    except Exception:
                        continue
                    if payload.get("origin") == _INSTANCE_ID:
                        # 自己实例发布的消息已由 publish() 本地直发，跳过防重复
                        continue
                    recipients = payload.get("recipients", [])
                    for uid in recipients:
                        await self.send_to_user(uid, payload)
            except asyncio.CancelledError:
                # stop_listener 的主动取消：正常退出路径
                return
            except Exception as exc:
                backoff = min(backoff * 2, 30)
                _logger.error(
                    "ws_redis_listener_error_restarting", error=str(exc), backoff_seconds=backoff
                )
                try:
                    await asyncio.sleep(backoff)
                except asyncio.CancelledError:
                    return


manager = ConnectionManager()


async def _authenticate(token: str | None) -> str | None:
    if not token:
        return None
    try:
        payload = decode_token(token)
    except Exception:
        return None
    if payload.get("type") != "access" or await is_token_revoked(token):
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    # P2-9：REST 侧会拒绝封禁账号，WS 通道此前漏查 User.status——
    # 被封禁用户保留完整收发能力。连接层统一拦截。
    async with SessionLocal() as db:
        user = await db.get(User, user_id)
    if user is None or user.status == UserStatus.BANNED.value:
        return None
    return user_id


# 首帧鉴权超时：给足慢网络握手余量，同时压短未授权连接的资源占用窗口
_WS_AUTH_TIMEOUT_SECONDS = 10


async def _authenticate_first_frame(websocket: WebSocket) -> str | None:
    """等待并校验鉴权首帧 ``{"event": "auth", "token": <access>}``。

    token 经 WS 帧传递而非 URL 查询串（查询串会进反代访问日志）。超时、
    首帧不是 auth、或 token 校验失败均返回 None，由调用方统一拒绝。
    """
    try:
        raw = await asyncio.wait_for(
            websocket.receive_text(), timeout=_WS_AUTH_TIMEOUT_SECONDS
        )
    except (TimeoutError, WebSocketDisconnect):
        return None
    try:
        data = json.loads(raw)
    except Exception:
        return None
    if not isinstance(data, dict) or data.get("event") != "auth":
        return None
    return await _authenticate(data.get("token"))


# ---------------------------------------------------------------------------
# P2-9：WS 发送节流与内容上限
# ---------------------------------------------------------------------------
# 每用户每分钟最多发送的消息条数（进程内滑动窗口；多实例时各实例独立计数，
# 攻击者需要连接多个实例才能放大，显著抬高滥用成本）。
_WS_SEND_RATE_LIMIT = 30
# 单条消息内容长度上限（与 REST 发送侧约束保持一致的量级）
_WS_MAX_CONTENT_LEN = 2000
# user_id -> 最近发送时间戳（monotonic 秒）
_send_timestamps: dict[str, list[float]] = {}


def _allow_send(user_id: str) -> bool:
    now = time.monotonic()
    window = _send_timestamps.setdefault(user_id, [])
    while window and now - window[0] > 60:
        window.pop(0)
    if len(window) >= _WS_SEND_RATE_LIMIT:
        return False
    window.append(now)
    return True


async def _is_participant(conversation_id: str, user_id: str) -> bool:
    """校验 user_id 是否为该会话的参与者。

    ``conv`` 参数来自客户端查询串，在用于任何历史读取（断线补发）前必须
    校验归属：否则任意登录用户可凭合法渠道泄露的会话 ID（如
    ``TradeSessionOut.conversation_id``）拉取他人私聊历史（P0-2）。
    REST 侧 ``get_messages`` 一直有此校验，WS 路径此前漏掉了。
    """
    async with SessionLocal() as db:
        row = await db.scalar(
            select(Participant.user_id).where(
                Participant.conversation_id == conversation_id,
                Participant.user_id == user_id,
            )
        )
    return row is not None


async def _compensate(ws: WebSocket, conversation_id: str, since: str | None) -> None:
    """断线补偿（**旧的时间戳口径**）：推送 since 之后的增量消息。

    .. deprecated::
        时间戳在同一刻度内的多条消息间无法区分游标，会**丢消息或重复推**。
        新客户端应改用 ``_compensate_by_seq``（携带 ``last_seq``）。
        本函数保留仅为兼容未升级的旧客户端。
    """
    async with SessionLocal() as db:
        stmt = select(Message).where(
            Message.conversation_id == conversation_id
        )
        if since:
            try:
                since_dt = datetime.fromisoformat(since)
                stmt = stmt.where(Message.created_at > since_dt)
            except ValueError:
                pass
        stmt = stmt.order_by(Message.created_at.asc()).limit(100)
        rows = (await db.scalars(stmt)).all()
    for m in rows:
        await ws.send_json(_message_event(m))


async def _compensate_by_seq(
    ws: WebSocket, conversation_id: str, last_seq: int
) -> int:
    """断线补偿（**LocalSeq 口径**）：仅补发 seq > last_seq 的消息。

    这是**应用层 Ack 机制**：客户端上报"我已收到第 N 条"，服务端据此精确
    算出缺失区间 ``(N, +inf]``，只推缺的那几条 —— 不重、不漏。

    :return: 实际补发的消息条数。
    """
    rows = await seq_store.since(conversation_id, last_seq=last_seq)
    for seq, payload in rows:
        # 补发的消息必须携带 seq，客户端才能继续推进游标
        await ws.send_json({**payload, "seq": seq})
    if rows:
        _logger.info(
            "ws_compensated",
            conversation_id=conversation_id,
            last_seq=last_seq,
            count=len(rows),
        )
    return len(rows)


def _message_event(m: Message) -> dict:
    return {
        "event": "message:new",
        "data": {
            "id": str(m.id),
            "conversation_id": m.conversation_id,
            "sender_id": m.sender_id,
            "type": m.type,
            "content": m.content,
            "created_at": m.created_at.isoformat() if m.created_at else "",
        },
    }


async def websocket_endpoint(
    websocket: WebSocket,
    since: str = "",
    conv: str = "",
    last_seq: int | None = None,
):
    """WebSocket 入口（注册于 /ws）。

    鉴权采用**首帧模式**：连接建立后客户端须立即发送
    ``{"event": "auth", "token": <access>}``，超时未发或校验失败即断开
    （token 不走 URL 查询串，避免被反代访问日志记录）。

    断线重连的补发口径（按优先级，均为查询串游标参数）:

    1. ``/ws?conv=<会话ID>&last_seq=<N>`` —— **推荐**。
       基于 LocalSeq 的精确补发，只推 seq > N 的缺失消息（见 seq.py）。
    2. ``/ws?conv=<会话ID>&since=<ISO 时间>`` —— 兼容旧客户端，
       按时间戳补发（同刻度消息可能丢失或重复，已废弃）。

    .. note::
       重构前 ``_compensate`` 定义了却**从未被调用**，等于断线重连后
       什么也没补 —— 这是本次修复的一个真实缺陷。
    """
    await websocket.accept()
    user_id = await _authenticate_first_frame(websocket)
    if not user_id:
        await websocket.send_json({"event": "error", "data": {"code": 40100, "message": "未授权"}})
        await websocket.close()
        return
    await websocket.send_json({"event": "auth:ok", "data": {"user_id": user_id}})

    await manager.connect(user_id, websocket)
    try:
        # 断线补偿：连接建立后立即补齐离线期间错过的消息
        try:
            if conv:
                # 参与者校验：非会话成员拒绝补发（防越权读取他人私聊历史）。
                # 校验失败只拒绝补发，不断开连接，实时收发能力不受影响。
                if not await _is_participant(conv, user_id):
                    await websocket.send_json(
                        {"event": "error", "data": {"code": 40300, "message": "无权读取该会话"}}
                    )
                elif last_seq is not None:
                    # last_seq=0 是合法游标，表示"我从第 0 条开始，请全量补发"；
                    # 不能写成 `if last_seq:`（0 为假值会跳过补偿，与 seq.py
                    # "0 表示全量补发" 的契约冲突）。仅当参数缺省（None）时才不补偿。
                    await _compensate_by_seq(websocket, conv, last_seq)
                elif since:
                    await _compensate(websocket, conv, since)
        except Exception as exc:
            # 补偿失败不应断开连接：最坏情况是消息没补上，
            # 但实时收发能力必须保住。
            _logger.warning("ws_compensate_failed", error=str(exc))

        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except Exception:
                await websocket.send_json({"event": "error", "data": {"code": 42200, "message": "JSON 格式错误"}})
                continue
            event = data.get("event")
            if event == "ping":
                await websocket.send_json({"event": "pong", "data": {}})
                continue
            if event == "message:read":
                conv_id = data.get("conversation_id")
                # P2-9：已读回执此前无参与者校验——可对任意会话伪造"我已读"。
                # 仅会话成员的已读事件才广播。
                if conv_id and await _is_participant(conv_id, user_id):
                    await manager.publish(
                        conv_id,
                        {
                            "event": "message:read_ack",
                            "data": {"conversation_id": conv_id, "user_id": user_id},
                            "recipients": [],
                        },
                    )
                continue
            if event == "message:send":
                conv_id = data.get("conversation_id")
                content = data.get("content", "")
                try:
                    mtype = int(data.get("type", 0))
                except (TypeError, ValueError):
                    mtype = 0
                if not conv_id:
                    await websocket.send_json({"event": "error", "data": {"code": 42200, "message": "缺少 conversation_id"}})
                    continue
                # P2-9：内容必须是非空字符串且不超过长度上限
                if (
                    not isinstance(content, str)
                    or not content.strip()
                    or len(content) > _WS_MAX_CONTENT_LEN
                ):
                    await websocket.send_json(
                        {
                            "event": "error",
                            "data": {"code": 42200, "message": f"消息内容需为 1-{_WS_MAX_CONTENT_LEN} 个字符"},
                        }
                    )
                    continue
                # P2-9：每用户发送节流（滑动窗口），防脚本刷屏拖垮广播
                if not _allow_send(user_id):
                    await websocket.send_json(
                        {
                            "event": "error",
                            "data": {"code": ErrorCode.TOO_MANY_REQUESTS, "message": "发送过于频繁，请稍后再试"},
                        }
                    )
                    continue
                try:
                    # 持久化（会话校验：非会话成员/会话不存在将抛出 BizError）
                    async with SessionLocal() as db:
                        msg = await send_message(
                            db,
                            conversation_id=conv_id,
                            sender_id=user_id,
                            type=mtype,
                            content=content,
                        )
                except BizError as exc:
                    await websocket.send_json(
                        {
                            "event": "error",
                            "data": {"code": exc.code, "message": exc.message},
                        }
                    )
                    continue
                payload = _message_event(msg)
                # 分配会话内递增序号并写入补发缓冲（ZSet），供断线重连精确补发。
                # 注意顺序：先 append 拿到 seq 再放进 payload，
                # 这样在线推送与离线补发携带的是**同一个** seq，游标才能对齐。
                seq = await seq_store.append(conv_id, payload)
                payload["seq"] = seq
                # recipients（全体参与者，含发送者多端回显）由 publish() 统一
                # 查询并写入广播体，此处不再重复查库。
                await manager.publish(conv_id, payload)
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
        _send_timestamps.pop(user_id, None)  # 节流窗口随连接释放，防字典无界增长
        _logger.info("ws_disconnected", user_id=user_id)
    except Exception as exc:
        _logger.error("ws_error", error=str(exc))
        manager.disconnect(user_id, websocket)
        _send_timestamps.pop(user_id, None)
