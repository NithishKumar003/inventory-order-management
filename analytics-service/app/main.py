from fastapi import FastAPI

from app.config import ANALYTICS_SERVICE_NAME, ANALYTICS_SERVICE_VERSION
from app.reports import router as analytics_router

app = FastAPI(
    title="Inventory and Order Management - Analytics Service",
    description="Admin analytics and business reporting API",
    version=ANALYTICS_SERVICE_VERSION,
)

app.include_router(analytics_router)

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": ANALYTICS_SERVICE_NAME,
        "version": ANALYTICS_SERVICE_VERSION,
    }


@app.get("/")
def root():
    return {
        "message": "Analytics Service is running",
        "docs": "/docs",
    }
