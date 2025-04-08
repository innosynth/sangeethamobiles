import sys
from pathlib import Path
from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings

# import pytz


def get_env_file():
    project_root = Path(__file__).parent.parent.parent
    if "pytest" in sys.modules:
        return project_root / ".env.test"
    else:
        return project_root / ".env"


class TenantSettings(BaseSettings):
    DATABASE_URL: str
    S3_ACCESS_KEY: str
    S3_SECRET_KEY: str
    S3_BUCKET_NAME: str
    S3_ENDPOINT: str
    S3_CDN: str
    VERIFY_TOKEN: str
    DEBUG: bool
    tz_NY: str
    BASE_UPLOAD_FOLDER: str
    GEMINI_API_KEY: str
    class Config:
        env_file = get_env_file()
        env_file_encoding = "utf-8"
