from pydantic_settings import BaseSettings


class LauncherSettings(BaseSettings):
    """Settings for the launcher. Will be loaded from environment variables or a .env file."""

    region_name: str = "us-east-1"
    job_queue: str | None = None
    job_definition: str | None = None
    messages_queue_url: str | None = None
    poll_interval: int = 30
    poll_timeout: int = 3600
