from fastapi import FastAPI
from tortoise import Tortoise
from tortoise.contrib.fastapi import register_tortoise
from app.core.config import settings

# This is the configuration dictionary for Tortoise ORM.
# It uses the DATABASE_URL from the global settings.
# The `models` list will point to the application's model modules.
TORTOISE_ORM_CONFIG = {
    "connections": {"default": settings.DATABASE_URL},
    "apps": {
        "models": { # 'models' is a conventional name for the app in Tortoise
            "models": settings.DB_MODELS, # e.g., ["app.models.user_model", "aerich.models"]
            "default_connection": "default",
        }
    },
    "use_tz": False, # Set to True if you want timezone-aware datetimes
    "timezone": "UTC" # Relevant if use_tz is True
}

async def init_db(app: FastAPI):
    """
    Initializes Tortoise ORM and registers it with the FastAPI application.
    This function should be called on application startup.
    """
    register_tortoise(
        app,
        config=TORTOISE_ORM_CONFIG,
        generate_schemas=True,  # Creates tables if they don't exist (good for dev, use migrations for prod)
        add_exception_handlers=True, # Adds Tortoise ORM exception handlers to FastAPI
    )
    print(f"Tortoise-ORM started, connected to: {settings.DATABASE_URL} with models: {settings.DB_MODELS}")

async def close_db():
    """
    Closes Tortoise ORM connections.
    register_tortoise handles this on shutdown, so this might not be explicitly needed
    if register_tortoise is used.
    """
    await Tortoise.close_connections()
    print("Tortoise-ORM connections closed.")

# For Aerich (migration tool for Tortoise ORM)
# Aerich needs to be able to import this TORTOISE_ORM_CONFIG.
# We will create an `aerich.ini` file later that points to this config.
