from fastapi import APIRouter
from .endpoints import astream

api_router = APIRouter()
api_router.include_router(astream.router, prefix="", tags=["core"])
