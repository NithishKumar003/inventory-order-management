
from fastapi import FastAPI

from .database import Base, engine
from . import models
from .routes import router as notification_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Inventory Management - Notification Service",
    version="1.0.0",
)

app.include_router(notification_router)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "notification-service",
    }
