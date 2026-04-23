from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_ENV: str = "development"
    SECRET_KEY: str

    DATABASE_URL: str
    DATABASE_URL_SYNC: str

    REDIS_URL: str
    REDIS_PASSWORD: str = ""

    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    SESSION_TOKEN_LENGTH: int = 48
    SESSION_ROTATE_SECONDS: int = 3600
    SESSION_MAX_AGE_SECONDS: int = 86400
    CSRF_TOKEN_LENGTH: int = 48


settings = Settings()
