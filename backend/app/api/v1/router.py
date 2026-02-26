"""API v1 router aggregator."""
from fastapi import APIRouter
from app.api.v1.endpoints import auth, pharmacy, ceye, or_module, ai

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(pharmacy.router)
api_router.include_router(ceye.router)
api_router.include_router(or_module.router)
api_router.include_router(ai.router)
