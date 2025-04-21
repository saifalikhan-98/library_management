import asyncio
import json
from typing import Dict, Any, List
from fastapi import WebSocket, WebSocketDisconnect

from app.core.redis_cache_service import RedisCacheService


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_personal_message(self, message: str, user_id: int):
        if user_id in self.active_connections:
            disconnected_websockets = []
            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_text(message)
                except WebSocketDisconnect:
                    disconnected_websockets.append(websocket)

            for ws in disconnected_websockets:
                self.active_connections[user_id].remove(ws)

            if not self.active_connections[user_id]:
                del self.active_connections[user_id]


class NotificationService:
    def __init__(self):
        self.redis_service = RedisCacheService()
        self.connection_manager = ConnectionManager()
        self.redis_client = self.redis_service.redis_client

    def notify_book_available(self, user_id: int, book_id: int, request_id: int) -> None:
        book_details = self._get_book_details(book_id)
        notification = {
            "type": "BOOK_AVAILABLE",
            "user_id": user_id,
            "book_id": book_id,
            "request_id": request_id,
            "book_title": book_details.get("title", "Unknown"),
            "message": f"The book '{book_details.get('title', 'Unknown')}' is now available for borrowing.",
        }

        user_channel = f"user:{user_id}:notifications"
        self.redis_client.publish(user_channel, json.dumps(notification))

        notification_key = f"notifications:{user_id}"
        self.redis_client.lpush(notification_key, json.dumps(notification))
        self.redis_client.ltrim(notification_key, 0, 99)
        asyncio.create_task(self._send_websocket_notification(user_id, notification))

    async def _send_websocket_notification(self, user_id: int, notification: Dict[str, Any]):
        await self.connection_manager.send_personal_message(
            json.dumps(notification),
            user_id
        )

    def _get_book_details(self, book_id: int) -> Dict[str, Any]:
        book_key = f"book_request:{book_id}"
        cached_book = self.redis_client.hgetall(book_key)

        if cached_book:
            return cached_book

        return {"title": "Unknown Book"}

    def get_user_notifications(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        notification_key = f"notifications:{user_id}"
        notifications_json = self.redis_client.lrange(notification_key, 0, limit - 1)
        return [json.loads(n) for n in notifications_json]

    def mark_notification_read(self, user_id: int, notification_id: str) -> bool:
        read_key = f"notifications:{user_id}:read"
        return self.redis_client.sadd(read_key, notification_id) > 0