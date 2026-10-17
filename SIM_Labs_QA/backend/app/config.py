from dataclasses import dataclass
from pathlib import Path
import os
from dotenv import load_dotenv

_process_env = os.getenv("APP_ENV", "").strip().lower()
load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=_process_env not in {"test", "prod", "production"})


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "local")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./sim_labs.db")
    auto_init_db: bool = _bool("AUTO_INIT_DB", False)
    supabase_jwt_secret: str = os.getenv("SUPABASE_JWT_SECRET", "")
    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:8000")
    feedback_ingest_token: str = os.getenv("FEEDBACK_INGEST_TOKEN", "")

    local_admin_password_hash: str = os.getenv("LOCAL_ADMIN_PASSWORD_HASH", "")
    session_signing_key: str = os.getenv("SESSION_SIGNING_KEY", "")
    allow_dev_actors: bool = _bool("ALLOW_DEV_ACTORS", False)
    storage_dir: str = os.getenv("STORAGE_DIR", "../data/private")
    ingest_product_slug: str = os.getenv("INGEST_PRODUCT_SLUG", "nexgrana")

    @property
    def is_dev(self) -> bool:
        return self.app_env.lower() in {"dev", "test", "local"}


settings = Settings()
