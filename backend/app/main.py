import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.adapters.mcp_flight_service import flight_service
from app.api.routes import router as api_router
from app.db import init_db

logger = logging.getLogger("kompass.main")

# Configure standard logging to show agent steps
logging.basicConfig(level=logging.INFO)
logging.getLogger("pydantic_ai").setLevel(logging.INFO)
logging.getLogger("kompass.agent").setLevel(logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure the persistence schema exists and the flights MCP client
    # subprocess is connected.
    await init_db()
    try:
        await flight_service.start()
    except Exception as e:
        # The agent's flight tools degrade gracefully, so a failed MCP startup
        # should not prevent the API from serving.
        logger.error(f"Flights MCP client failed to start: {e}")
    yield
    # Shutdown: tear down the flights MCP client subprocess.
    await flight_service.stop()

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

