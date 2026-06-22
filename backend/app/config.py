from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://jobscout:jobscout_dev@localhost:5432/jobscout"
    database_url_sync: str = "postgresql://jobscout:jobscout_dev@localhost:5432/jobscout"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60
    jwt_refresh_expiration_days: int = 7
    anthropic_api_key: str = ""
    serpapi_key: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    google_refresh_token: str = ""
    admin_email: str = ""
    app_url: str = "http://localhost:3000"
    upload_dir: str = "/app/uploads"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
