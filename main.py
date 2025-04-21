from contextlib import asynccontextmanager
import uvicorn
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Request
import logging
from app.core.create_super_admin import create_admin_user
from app.database import Base, engine
from app.routes import router
from app.security.rate_limiter import GlobalRateLimitMiddleware, limiter
from app.socket_routes.websockets import ws_router
from app.utils.custom_http_exceptions import custom_http_exception_handler, validation_exception_handler
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(application: FastAPI):
    await create_admin_user()
    yield
    pass

Base.metadata.create_all(bind=engine)
app = FastAPI(
    debug=True,
    title="Avrioc",
    version="0.0.5",
    license_info={
        "name": "All Right Reserved",
    },
    lifespan=lifespan
)

# Register limiter with app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

origins = [
    "http://localhost:3000",
    "http://localhost:3001"
]

app.include_router(router, prefix="/api")
app.include_router(ws_router)

app.add_exception_handler(HTTPException, custom_http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)


app.add_middleware(SlowAPIMiddleware)
app.add_middleware(GlobalRateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
@limiter.limit("10/minute")
def root(request: Request):
    return {"message": "please visit http://localhost:8000/docs for api documentation"}

if __name__=='__main__':
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)