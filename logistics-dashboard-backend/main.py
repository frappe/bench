from fastapi import FastAPI
from app.core.config import settings # Updated import
from app.db.config import init_db

# Settings instance is now created in app.core.config

app = FastAPI(
    title="Logistics Dashboard API",
    version="0.1.0",
    description="API for the Advanced Logistics Dashboard",
)

@app.on_event("startup")
async def startup_event():
    """
    Initialize database connections when the application starts.
    """
    print("Starting up and initializing DB...")
    await init_db(app) # This will connect Tortoise ORM
    # The print statement from init_db will confirm initialization

@app.on_event("shutdown")
async def shutdown_event():
    """
    Close database connections when the application shuts down.
    """
    print("Shutting down.")


@app.get("/")
async def read_root():
    return {"message": "Welcome to the Logistics Dashboard API!"}

# Include authentication router
from app.routers import auth_router
from app.core.config import settings # To use API_V1_STR

app.include_router(auth_router.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"])


# Placeholder for other future routers
# from app.routers import items_router
# app.include_router(items_router.router, prefix=f"{settings.API_V1_STR}/items", tags=["Items"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
