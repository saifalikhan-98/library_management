import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import ValidationError
from typing import Any, Dict

ROOT_DIR = Path(__file__).parent.parent

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    ADMIN_INITIAL_PASSWORD: str
    ADMIN_EMAIL: str
    ADMIN_USERNAME: str
    REDIS_HOST: str
    REDIS_PORT: int

    class Config:
        env_file = os.path.join(ROOT_DIR, ".env")
        env_file_encoding = 'utf-8'
        validate_assignment = True

    @classmethod
    def validate_env(cls, env_vars: Dict[str, Any]):
        defined_vars = cls.__annotations__.keys()
        extra_vars = set(env_vars.keys()) - set(defined_vars)
        missing_vars = set(defined_vars) - set(env_vars.keys())

        if extra_vars:
            raise ValueError(f"Extra environment variables found: {extra_vars}")
        if missing_vars:
            raise ValueError(f"Missing environment variables: {missing_vars}")

# Initialize settings
try:
    settings = Settings()
    settings.validate_env(settings.model_dump())
except ValidationError as e:
    print(f"Error validating settings: {e}")
except ValueError as e:
    print(f"Strict environment validation error: {e}")