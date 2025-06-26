from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from .security import get_secure_jwt_secret


class Settings(BaseSettings):
    # === App ===
    app_name: str = "File Upload Insights"
    debug: bool = False
    # === JWT ===
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60
    # === AWS ===
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    s3_bucket: str = ""
    dynamodb_uploads_table: str = "file-insights-uploads"
    dynamodb_users_table: str = "file-insights-users"
    sqs_queue_url: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    
    @property
    def jwt_secret_key(self) -> str:
        """Get secure JWT secret key"""
        return get_secure_jwt_secret()


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
