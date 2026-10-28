"""Configuration objects loaded by the application factory."""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
_INSTANCE = BASE_DIR / "instance"


def _env_int(key: str, default: int) -> int:
    raw = os.environ.get(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


class BaseConfig:
    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY")  # required; validated in create_app
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{_INSTANCE / 'nkokonono.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Storage
    STORAGE_ROOT = os.environ.get("STORAGE_ROOT", str(BASE_DIR / "storage"))

    # Limits
    MAX_CONTENT_LENGTH = _env_int("MAX_CONTENT_LENGTH", 100 * 1024 * 1024)
    MAX_FILES_PER_JOB = _env_int("MAX_FILES_PER_JOB", 20)
    MAX_PDF_PAGES = _env_int("MAX_PDF_PAGES", 500)
    JOB_TIMEOUT_SECONDS = _env_int("JOB_TIMEOUT_SECONDS", 300)
    FILE_RETENTION_SECONDS = _env_int("FILE_RETENTION_SECONDS", 3600)

    # Logging
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

    # Public project link shown in the navbar and About section.
    GITHUB_URL = os.environ.get(
        "GITHUB_URL", "https://github.com/YOUR_ORG/nkokonono-pdf"
    )

    # Shown on the Contact page and footer. Overridable per environment.
    SUPPORT_EMAIL = os.environ.get(
        "SUPPORT_EMAIL", "support@nalaneindustries.co.za"
    )

    # CSRF
    WTF_CSRF_TIME_LIMIT = 3600

    # Rate limiting
    RATELIMIT_ENABLED = os.environ.get("RATELIMIT_ENABLED", "1") == "1"
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_JOB_CREATE = os.environ.get("RATELIMIT_JOB_CREATE", "10 per minute")
    RATELIMIT_UPLOAD = os.environ.get("RATELIMIT_UPLOAD", "30 per minute")

    # Concurrency and timeouts
    MAX_CONCURRENT_JOBS_PER_IP = _env_int("MAX_CONCURRENT_JOBS_PER_IP", 3)
    # JOB_TIMEOUT_SECONDS already exists in BaseConfig

    # Logging format: "json" or "text"
    LOG_FORMAT = os.environ.get("LOG_FORMAT", "text")


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    # Dev-only fallback key: never used in production.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-key-change-me")


class TestingConfig(BaseConfig):
    TESTING = True
    DEBUG = True
    SECRET_KEY = "test-key"
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    STORAGE_ROOT = str(BASE_DIR / "storage-test")
    LOG_LEVEL = "WARNING"
    RATELIMIT_ENABLED = False
    MAX_CONCURRENT_JOBS_PER_IP = 100
    JOB_TIMEOUT_SECONDS = 30
    LOG_FORMAT = "text"


class ProductionConfig(BaseConfig):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Strict"
    LOG_FORMAT = "json"
    RATELIMIT_ENABLED = True


config_map = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}