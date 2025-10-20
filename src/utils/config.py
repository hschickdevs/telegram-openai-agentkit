"""Configuration management."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration."""

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    DATA_DIRECTORY: Path = Path(os.getenv("DATA_DIRECTORY", "data"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Accepted file extensions for workflow uploads
    ACCEPTED_FILE_TYPES: tuple = (".py", ".txt")

    @classmethod
    def validate(cls) -> None:
        """Validate required configuration."""
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required")
        if not cls.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")

        # Ensure directories exist
        cls.DATA_DIRECTORY.mkdir(parents=True, exist_ok=True)
