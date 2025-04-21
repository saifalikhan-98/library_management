import traceback
import asyncio
import json
import threading
from queue import Queue
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.security.middleware_helper import MiddlewareHelper
from app.services.notification_service import NotificationService

ws_router = APIRouter()
notification_service = NotificationService()


@ws_router.websocket("/ws/notifications")
async def websocket_endpoint(websocket: WebSocket):
    print("Connection attempt")
    await websocket.accept()
    print("Connection accepted")

    # Message queue for communication between Redis thread and WebSocket
    message_queue = Queue()
    # Flag to signal the Redis listener thread to stop
    stop_thread = False
    # List to store the thread for cleanup
    redis_thread = None

    try:
        print("Waiting for authentication")
        auth_data = await websocket.receive_json()

        token = auth_data.get("token")

        if not token:
            await websocket.send_json({"error": "Authentication required"})
            await websocket.close(code=1008)
            return

        try:
            # Remove Bearer prefix if present
            clean_token = token.replace("Bearer ", "") if token.startswith("Bearer ") else token
            user = MiddlewareHelper().current_user(clean_token)
            user_id = user.user_id
            await websocket.send_json({"status": "authenticated", "user_id": user_id})
        except Exception as e:
            traceback.print_exc()
            await websocket.send_json({"error": f"Invalid authentication: {str(e)}"})
            await websocket.close(code=1008)
            return
        pending_notifications = notification_service.get_user_notifications(user_id)
        if pending_notifications:
            for notification in pending_notifications:
                await websocket.send_json(notification)


        def redis_listener_thread():
            pubsub = notification_service.redis_client.pubsub()
            user_channel = f"user:{user_id}:notifications"
            pubsub.subscribe(user_channel)

            for message in pubsub.listen():
                if stop_thread:
                    pubsub.unsubscribe(user_channel)
                    break

                if message["type"] == "message":
                    message_queue.put(message["data"])


        redis_thread = threading.Thread(target=redis_listener_thread)
        redis_thread.daemon = True
        redis_thread.start()

        while True:
            if not message_queue.empty():
                message_data = message_queue.get()
                await websocket.send_text(message_data)

            try:

                data = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)

                client_message = json.loads(data)
                if client_message.get("action") == "mark_read":
                    notification_id = client_message.get("notification_id")
                    if notification_id:
                        notification_service.mark_notification_read(user_id, notification_id)
                        await websocket.send_json({
                            "type": "action_result",
                            "action": "mark_read",
                            "success": True,
                            "notification_id": notification_id
                        })

            except asyncio.TimeoutError:

                await asyncio.sleep(0.01)
                pass
            except WebSocketDisconnect:
                print(f"WebSocket disconnected for user {user_id}")
                break

    except WebSocketDisconnect:
        traceback.print_exc()
    except Exception as e:
        print(f"WebSocket error: {str(e)}")
        traceback.print_exc()
        try:
            await websocket.send_json({"error": str(e)})
            await websocket.close()
        except:
            pass
    finally:
        if 'user_id' in locals():
            notification_service.connection_manager.disconnect(websocket, user_id)

        # Signal the Redis listener thread to stop
        stop_thread = True

        # Wait for the thread to finish
        if redis_thread and redis_thread.is_alive():
            print("Waiting for Redis thread to complete...")
            redis_thread.join(timeout=1.0)
            print("Redis thread cleanup completed")