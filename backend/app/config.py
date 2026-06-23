import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Determine absolute path to the backend/.env file to guarantee it loads regardless of the runtime CWD.
current_dir = os.path.dirname(os.path.abspath(__file__))
env_file_path = os.path.abspath(os.path.join(current_dir, "..", ".env"))

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=env_file_path,
        env_file_encoding="utf-8",
        extra="ignore"
    )

    google_api_key: str = Field(alias="GOOGLE_API_KEY")
    llm_model: str = Field("google:gemini-2.5-pro", alias="LLM_MODEL")
    
    # Langfuse telemetry configuration
    langfuse_secret_key: Optional[str] = Field(None, alias="LANGFUSE_SECRET_KEY")
    langfuse_public_key: Optional[str] = Field(None, alias="LANGFUSE_PUBLIC_KEY")
    langfuse_base_url: str = Field("https://cloud.langfuse.com", alias="LANGFUSE_BASE_URL")
    
    # Server configuration
    port: int = Field(8000, alias="PORT")
    host: str = Field("127.0.0.1", alias="HOST")

# Singleton settings instance
settings = Settings()

# Export settings to os.environ for third-party SDKs (Gemini, Langfuse, etc.)
if settings.google_api_key:
    os.environ["GOOGLE_API_KEY"] = settings.google_api_key
if settings.langfuse_secret_key:
    os.environ["LANGFUSE_SECRET_KEY"] = settings.langfuse_secret_key
if settings.langfuse_public_key:
    os.environ["LANGFUSE_PUBLIC_KEY"] = settings.langfuse_public_key
if settings.langfuse_base_url:
    os.environ["LANGFUSE_BASE_URL"] = settings.langfuse_base_url

