from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "change-me"

    # Database
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "riskalerts"
    POSTGRES_PASSWORD: str = "riskalerts_dev_password"
    POSTGRES_DB: str = "riskalerts"
    DATABASE_URL: str = ""

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_URL: str = "redis://redis:6379/0"

    # JWT Auth
    JWT_SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # LLM
    LLM_PROVIDER: str = "openai"
    LLM_MODEL: str = "gpt-4o"
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    LLM_REQUEST_TIMEOUT_SECONDS: float = 30.0
    DEDUP_SIMILARITY_THRESHOLD: float = 0.9
    DEDUP_EMBEDDING_DIMENSIONS: int = 256
    DEDUP_ALERT_LOOKBACK_HOURS: int = 72

    # News Sources
    NEWSAPI_KEY: str = ""
    GDELT_BASE_URL: str = "https://api.gdeltproject.org/api/v2"
    RELIEFWEB_BASE_URL: str = "https://api.reliefweb.int/v1"
    USGS_EARTHQUAKE_FEED_URL: str = (
        "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"
    )
    RSS_FEED_URLS: str = (
        "https://www.reutersagency.com/feed/?best-topics=natural-disasters,"
        "https://feeds.bbci.co.uk/news/world/rss.xml"
    )
    REQUEST_TIMEOUT_SECONDS: float = 20.0
    NEWS_FETCH_INTERVAL_MINUTES: int = 5
    ENABLE_NEWS_SCHEDULER: bool = True
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 120
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    RATE_LIMIT_EXEMPT_PATHS: str = "/health,/health/db,/docs,/openapi.json,/redoc"

    # Email / SMTP
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "alerts@example.com"
    SENDGRID_API_KEY: str = ""

    # Celery
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    # Reports
    REPORT_OUTPUT_DIR: str = "generated_reports"

    @property
    def database_url(self) -> str:
        """Build the database URL from components if not explicitly set."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def sync_database_url(self) -> str:
        """Synchronous database URL for Alembic migrations."""
        return self.database_url.replace("+asyncpg", "")

    @property
    def rss_feed_urls_list(self) -> list[str]:
        return [feed_url.strip() for feed_url in self.RSS_FEED_URLS.split(",") if feed_url.strip()]

    @property
    def rate_limit_exempt_paths_list(self) -> list[str]:
        return [path.strip() for path in self.RATE_LIMIT_EXEMPT_PATHS.split(",") if path.strip()]


settings = Settings()
