from typing import List, Optional
from pydantic import computed_field, SecretStr,model_validator,field_validator
import json
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App Config
    PROJECT_NAME: str = "BusGo API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Security & JWT
    # SecretStr ကို အသုံးပြုခြင်းဖြင့် Console / Log ထဲတွင် Plaintext Secret များ မတော်တဆ Print မထွက်အောင် ကာကွယ်ပေးသည်
    SECRET_KEY: str 
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database Settings
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: SecretStr
    POSTGRES_DB: str

    # Redis Settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_URL : str

    ALLOWED_ORIGINS: str
    ALLOWED_HOSTS: str

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 1440

    # Computed Property for Async PostgreSQL Connection URI
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD.get_secret_value()}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


    @property
    def allowed_origins(self) -> List[str]:
        value = self.ALLOWED_ORIGINS.strip()
        if value.startswith("["):
            return json.loads(value)
        return [origin.strip() for origin in value.split(",") if origin.strip()]

    @property
    def allowed_hosts(self) -> List[str]:
        value = self.ALLOWED_HOSTS.strip()
        if value.startswith("["):
            return json.loads(value)
        return [host.strip() for host in value.split(",") if host.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in {"prod", "production"}

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return value

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production"}:
                return False
            if normalized in {"debug", "dev", "development"}:
                return True
        return value

    @model_validator(mode="after")
    def validate_production_settings(self):
        if not self.is_production:
            return self

        if self.DEBUG:
            raise ValueError("DEBUG must be false in production")

        if "*" in self.allowed_origins:
            raise ValueError("ALLOWED_ORIGINS cannot contain '*' in production")

        if "*" in self.allowed_hosts:
            raise ValueError("ALLOWED_HOSTS cannot contain '*' in production")

        return self
    # Pydantic Configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


# Application တစ်ခုလုံးတွင် Import ပြုလုပ်၍ ပြန်လည်အသုံးပြုနိုင်ရန် Singleton Instance ဖန်တီးခြင်း
settings = Settings()