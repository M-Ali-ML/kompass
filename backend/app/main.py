import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router as api_router
from app.db import init_db

# Configure standard logging to show agent steps
logging.basicConfig(level=logging.INFO)
logging.getLogger("pydantic_ai").setLevel(logging.INFO)
logging.getLogger("kompass.agent").setLevel(logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure the persistence schema exists.
    # (MCP clients will also be initialized here in later phases.)
    await init_db()
    yield
    # Shutdown placeholder

app = FastAPI(title="Kompass Backend API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    # Allow any localhost origin (any port) for local dev and E2E test servers.
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(api_router)

