"""
Configuration module for SetlistFM Agent
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Azure AI Foundry settings
    project_endpoint: str = os.getenv("PROJECT_ENDPOINT", "")
    model_deployment_name: str = os.getenv("MODEL_DEPLOYMENT_NAME", "")
    azure_client_id: str = os.getenv("AZURE_CLIENT_ID", "")

    # Application Insights
    applicationinsights_connection_string: Optional[str] = os.getenv(
        "APPLICATIONINSIGHTS_CONNECTION_STRING")

    # Setlist.fm API
    setlistfm_api_key: str = os.getenv("SETLISTFM_API_KEY", "")

    # FastAPI settings
    host: str = "0.0.0.0"
    port: int = 80
    log_level: str = os.getenv("AZURE_LOG_LEVEL", "INFO").upper()

    # Telemetry settings
    azure_monitor_enabled: bool = os.getenv(
        "AZURE_MONITOR_OPENTELEMETRY_ENABLED", "true").lower() == "true"
    azure_tracing_content_recording: bool = os.getenv(
        "AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED", "true").lower() == "true"

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from environment


# Global settings instance
settings = Settings()


def validate_required_settings():
    """Validate that all required settings are present."""
    required_vars = [
        "project_endpoint",
        "model_deployment_name",
        # "azure_client_id"
    ]

    missing_vars = []
    for var in required_vars:
        if not getattr(settings, var):
            missing_vars.append(var.upper())

    if missing_vars:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_vars)}")
