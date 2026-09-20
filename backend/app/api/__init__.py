from fastapi import APIRouter

from app.api import (
    adaptations,
    assess,
    challenge,
    corpus,
    experiments,
    health,
    learner,
    models_admin,
    parking,
    plan,
    practice,
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
    corpus,
    adaptations,
    models_admin,
    experiments,
    practice,
):
    api_router.include_router(r.router)
