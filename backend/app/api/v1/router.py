from fastapi import APIRouter

from app.api.v1 import (
    favorites, 
    guardrails, 
    health, 
    mcp, 
    memory, 
    users,
    restaurants,
    ranking,
    agent,
    workflow
)
api_router = APIRouter()

api_router.include_router(favorites.router)
api_router.include_router(health.router)
api_router.include_router(users.router)
api_router.include_router(memory.router)
api_router.include_router(guardrails.router)
api_router.include_router(mcp.router)
api_router.include_router(restaurants.router)
api_router.include_router(ranking.router)
api_router.include_router(agent.router)
api_router.include_router(workflow.router)