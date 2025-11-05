from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database settings
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str

    # Redis settings
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int

    # Security settings
    TOKEN_EXPIRY_MINUTES: int
    MAX_VOTES_PER_DEVICE: int
    MAX_VOTES_PER_IP: int
    MAX_IP_CHANGES_ALLOWED: int
    RATE_LIMIT_VOTES_PER_MINUTE: int

    # Contestants
    ALLOWED_CONTESTANTS: str

    ALLOWED_ORIGINS: str = ""

    # reCAPTCHA settings (required)
    RECAPTCHA_SITE_KEY: str
    RECAPTCHA_SECRET_KEY: str

    @property
    def database_url(self) -> str:
        """Construct PostgreSQL database URL from components"""
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def allowed_contestants_list(self) -> List[str]:
        return [
            name.strip().lower()
            for name in self.ALLOWED_CONTESTANTS.split(",")
        ]

    class Config:
        env_file = ".env"  # Tells Pydantic to load from .env


# Instantiate settings once
settings = Settings()
