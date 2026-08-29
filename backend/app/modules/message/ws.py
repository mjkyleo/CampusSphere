"""WebSocket 实时通信。

- 连接鉴权：``/ws?token=<access>&since=<iso>``
- user_id -> {websocket} 映射（支持多端）
- Redis Pub/Sub 多实例广播（单实例/无 Redis 时降级为内存直发）
- 心跳（ping/pong）、断线重连消息补偿（since）
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Dict, Set

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.exceptions import BizError
from app.core.logging import get_logger
from app.core.redis import redis_publish, redis_subscribe
from app.core.security import decode_token, is_token_revoked
from app.modules.message.models import Message, Participant
from app.modules.message.service import send_message

_logger = get_logger("message.ws")

_WS_CHANNEL = "conv"


class ConnectionManager:
    """管理所有在线 WebSocket 连接。"""

    def __init__(self) -> None:
        # user_id -> set(websocket)
        self._connections: Dict[str, Set[WebSocket]] = {}
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
            except Exception:  # noqa: BLE001
                self.disconnect(user_id, ws)

    async def publish(self, conversation_id: str, payload: dict) -> None:
        """本地直发 + Redis 广播（多实例）。"""
        # 本地直发：直接推送给本实例连接
        async with SessionLocal() as db:
            parts = (await db.scalars(
                select(Participant.user_id).where(
                    Participant.conversation_id == conversation_id
                )
            )).all()
        str_parts = [str(p) for p in parts]
        for uid in str_parts:
            await self.send_to_user(uid, payload)
        # 跨实例广播
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
        except Exception as exc:  # noqa: BLE001 - 关闭期异常不应阻断
            _logger.warning("ws_listener_stop_error", error=str(exc))

    async def _redis_listen(self) -> None:
        pubsub = await redis_subscribe(f"{_WS_CHANNEL}:*")
        if pubsub is None:
            return
        _logger.info("ws_redis_listener_started")
        try:
            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                try:
                    payload = json.loads(message["data"])
                except Exception:  # noqa: BLE001
                    continue
                recipients = payload.get("recipients", [])
                for uid in recipients:
                    await self.send_to_user(uid, payload)
        except asyncio.CancelledError:  # noqa: BLE001
            return


manager = ConnectionManager()


async def _authenticate(token: str | None) -> str | None:
    if not token:
        return None
    try:
        payload = decode_token(token)
    except Exception:  # noqa: BLE001
        return None
    if payload.get("type") != "access" or await is_token_revoked(token):
        return None
    return payload.get("sub")


async def _compensate(ws: WebSocket, conversation_id: str, since: str | None) -> None:
    """断线补偿：推送 since 之后的增量消息。"""
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


async def websocket_endpoint(websocket: WebSocket, token: str = "", since: str = ""):
    """WebSocket 入口（注册于 /ws）。"""
    await websocket.accept()
    user_id = await _authenticate(token)
    if not user_id:
        await websocket.send_json({"event": "error", "data": {"code": 40100, "message": "未授权"}})
        await websocket.close()
        return

    await manager.connect(user_id, websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except Exception:  # noqa: BLE001
                await websocket.send_json({"event": "error", "data": {"code": 42200, "message": "JSON 格式错误"}})
                continue
            event = data.get("event")
            if event == "ping":
                await websocket.send_json({"event": "pong", "data": {}})
                continue
            if event == "message:read":
                conv_id = data.get("conversation_id")
                if conv_id:
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
                        parts = (await db.scalars(
                            select(Participant.user_id).where(
                                Participant.conversation_id == conv_id
                            )
                        )).all()
                except BizError as exc:
                    await websocket.send_json(
                        {
                            "event": "error",
                            "data": {"code": exc.code, "message": exc.message},
                        }
                    )
                    continue
                payload = _message_event(msg)
                # parts 为 UUID 对象，user_id 为 str，统一转 str 后再比较与组装
                payload["recipients"] = [str(p) for p in parts if str(p) != user_id]
                await manager.publish(conv_id, payload)
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
        _logger.info("ws_disconnected", user_id=user_id)
    except Exception as exc:  # noqa: BLE001
        _logger.error("ws_error", error=str(exc))
        manager.disconnect(user_id, websocket)
