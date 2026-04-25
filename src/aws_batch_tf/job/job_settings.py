from pydantic_settings import BaseSettings


class JobSettings(BaseSettings):
    """Settings for the job. Will be loaded from environment variables or a .env file."""

    region_name: str = "us-east-1"
    messages_queue_url: str | None = None

