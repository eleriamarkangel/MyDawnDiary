from dataclasses import dataclass
from functools import lru_cache
import os


@dataclass(frozen=True)
class Settings:
    database_url: str
    jwt_secret: str
    token_minutes: int
    resend_api_key: str
    resend_from_email: str


@lru_cache
def get_settings() -> Settings:
    secret = os.getenv("JWT_SECRET", "")
    if len(secret) < 32 or secret == "replace-with-a-random-secret":
        raise RuntimeError("JWT_SECRET must be a random value of at least 32 characters")
    return Settings(
        database_url=os.getenv("DATABASE_URL", "sqlite:///./mydawndiary.db"),
        jwt_secret=secret,
        token_minutes=int(os.getenv("TOKEN_MINUTES", "60")),
        resend_api_key=os.getenv("RESEND_API_KEY", ""),
        resend_from_email=os.getenv("RESEND_FROM_EMAIL", ""),
    )
