from fastapi import APIRouter

from app.api import (
    assess,
    challenge,
    health,
    learner,
    parking,
    plan,
    preferences,
    representations,
    review,
    sessions,
    skills,
    tutor,
)

api_router = APIRouter(prefix="/api")
for r in (
    health,
    learner,
    skills,
    sessions,
    plan,
    preferences,
    representations,
    challenge,
    tutor,
    assess,
    review,
    parking,
):
    api_router.include_router(r.router)
