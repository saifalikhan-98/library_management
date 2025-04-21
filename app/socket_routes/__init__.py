from fastapi import APIRouter
from app.socket_routes.websockets import ws_router as websocket_routers

router=APIRouter()

router.include_router(websocket_routers, prefix="/ws", tags=["websocket"])