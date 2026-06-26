import os
from typing import Optional
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# Determine absolute path to the backend/.env file to guarantee it loads regardless of the runtime CWD.
current_dir = os.path.dirname(os.path.abspath(__file__))
env_file_path = os.path.abspath(os.path.join(current_dir, "..", ".env"))

# Default SQLite database location: backend/data/kompass.db (resolved absolutely).
default_db_path = os.path.abspath(os.path.join(current_dir, "..", "data", "kompass.db"))
default_database_url = f"sqlite+aiosqlite:///{default_db_path}"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=env_file_path,
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Secret fields use SecretStr so they auto-mask in any repr / model_dump
    # (e.g. the DEBUG settings dump). Read the raw value with .get_secret_value().
    google_api_key: SecretStr = Field(alias="GOOGLE_API_KEY")
    llm_model: str = Field("google:gemini-2.5-pro", alias="LLM_MODEL")

    # Flights provider (SerpApi Google Flights). Optional: when unset, the
    # flight tools degrade to the grounded search_web tool.
    serpapi_api_key: Optional[SecretStr] = Field(None, alias="SERPAPI_API_KEY")

    # Data MCP mode. "live" calls SerpApi (costs money); "mock" returns
    # deterministic, clearly-flagged fake data with NO network calls / no key
    # (handy for dev so you don't burn the shared SerpApi quota).
    mcp_mode: str = Field("live", alias="MCP_MODE")
    # Optional path; when set, every MCP tool call's request/response is
    # appended as a JSON line for inspection.
    mcp_log_file: Optional[str] = Field(None, alias="MCP_LOG_FILE")
    
    # Langfuse telemetry configuration
    langfuse_secret_key: Optional[SecretStr] = Field(None, alias="LANGFUSE_SECRET_KEY")
    langfuse_public_key: Optional[SecretStr] = Field(None, alias="LANGFUSE_PUBLIC_KEY")
    langfuse_base_url: str = Field("https://cloud.langfuse.com", alias="LANGFUSE_BASE_URL")
    
    # Persistence configuration
    database_url: str = Field(default_database_url, alias="DATABASE_URL")

    # Server configuration
    port: int = Field(8000, alias="PORT")
    host: str = Field("127.0.0.1", alias="HOST")

    # Application log level (DEBUG, INFO, WARNING, ERROR). At DEBUG the app logs
    # the effective settings at startup (SecretStr fields auto-mask).
    log_level: str = Field("INFO", alias="LOG_LEVEL")

# Singleton settings instance
settings = Settings()

# Export settings to os.environ for third-party SDKs (Gemini, Langfuse, etc.)
# SecretStr fields are unwrapped via .get_secret_value() at the boundary.
if settings.google_api_key:
    os.environ["GOOGLE_API_KEY"] = settings.google_api_key.get_secret_value()
if settings.serpapi_api_key:
    # Exported so the data MCP subprocesses (inherit os.environ) can read it.
    os.environ["SERPAPI_API_KEY"] = settings.serpapi_api_key.get_secret_value()
# Exported so the data MCP subprocesses pick up the mode / log file.
if settings.mcp_mode:
    os.environ["MCP_MODE"] = settings.mcp_mode
if settings.mcp_log_file:
    os.environ["MCP_LOG_FILE"] = settings.mcp_log_file
if settings.langfuse_secret_key:
    os.environ["LANGFUSE_SECRET_KEY"] = settings.langfuse_secret_key.get_secret_value()
if settings.langfuse_public_key:
    os.environ["LANGFUSE_PUBLIC_KEY"] = settings.langfuse_public_key.get_secret_value()
if settings.langfuse_base_url:
    os.environ["LANGFUSE_BASE_URL"] = settings.langfuse_base_url
# Exported so the data MCP subprocesses can match the app's log verbosity.
if settings.log_level:
    os.environ["LOG_LEVEL"] = settings.log_level

