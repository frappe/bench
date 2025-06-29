import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env file variables
load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "Logistics Dashboard API"
    API_V1_STR: str = "/api/v1"

    # Database configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgres://user:password@localhost:5432/logistics_db")

    # For Tortoise ORM, define the models paths
    # This needs to be a list of strings pointing to the modules containing your models.
    # "aerich.models" is required for Aerich to work.
    # Other models will be added as they are created.
    DB_MODELS: list[str] = ["app.models.user_model", "aerich.models"]

    # JWT settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "a_very_secret_key_that_should_be_changed") # CHANGE IN PRODUCTION
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))


    class Config:
        case_sensitive = True
        env_file = ".env" # Specifies to load from .env if not already loaded by dotenv

settings = Settings()
