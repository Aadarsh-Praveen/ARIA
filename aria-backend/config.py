import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field

# Points to the ROOT .env file (one level above aria-backend/)
ROOT_DIR = Path(__file__).parent.parent
ENV_FILE = ROOT_DIR / ".env"


class Settings(BaseSettings):
    # ─── Google Cloud ─────────────────────────────────────
    google_cloud_project: str = Field(alias="GOOGLE_CLOUD_PROJECT")
    google_cloud_location: str = Field(default="us-central1", alias="GOOGLE_CLOUD_LOCATION")
    google_application_credentials: str = Field(alias="GOOGLE_APPLICATION_CREDENTIALS")

    # ─── Gemini ───────────────────────────────────────────
    gemini_api_key: str = Field(alias="GEMINI_API_KEY")
    gemini_pro_model: str = "gemini-2.5-pro"
    gemini_flash_model: str = "gemini-2.5-flash"

    # ─── AlloyDB ──────────────────────────────────────────
    alloydb_connection_string: str = Field(alias="ALLOYDB_CONNECTION_STRING")
    alloydb_database: str = Field(default="aria", alias="ALLOYDB_DATABASE")
    alloydb_user: str = Field(default="postgres", alias="ALLOYDB_USER")
    alloydb_password: str = Field(alias="ALLOYDB_PASSWORD")
    alloydb_instance: str = Field(alias="ALLOYDB_INSTANCE")

    # ─── Slack ────────────────────────────────────────────
    slack_bot_token: str = Field(alias="SLACK_BOT_TOKEN")
    slack_default_channel: str = Field(default="#general", alias="SLACK_DEFAULT_CHANNEL")

    # ─── Vertex AI ────────────────────────────────────────
    vertex_ai_location: str = Field(default="us-central1", alias="VERTEX_AI_LOCATION")
    vertex_ai_memory_bank_id: str = Field(default="aria-memory", alias="VERTEX_AI_MEMORY_BANK_ID")

    # ─── MCP Servers ──────────────────────────────────────
    task_mcp_url: str = Field(default="http://localhost:8001", alias="TASK_MCP_URL")
    task_mcp_port: int = Field(default=8001, alias="TASK_MCP_PORT")

    # ─── FastAPI ──────────────────────────────────────────
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    debug: bool = Field(default=True, alias="DEBUG")

    # ─── Demo User ────────────────────────────────────────
    demo_user_id: str = "user-aadarsh-001"
    demo_user_email: str = "aada17101.ec@rmkec.ac.in"

    class Config:
        env_file = str(ENV_FILE)
        env_file_encoding = "utf-8"
        populate_by_name = True
        extra = "ignore"


# Single instance used across the entire app
settings = Settings()