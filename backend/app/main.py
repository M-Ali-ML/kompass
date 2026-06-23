import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router as api_router

# Configure standard logging to show agent steps
logging.basicConfig(level=logging.INFO)
logging.getLogger("pydantic_ai").setLevel(logging.INFO)
logging.getLogger("kompass.agent").setLevel(logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup placeholder (MCP clients will be initialized here in later phases)
    yield
    # Shutdown placeholder

app = FastAPI(title="Kompass Backend API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(api_router)

