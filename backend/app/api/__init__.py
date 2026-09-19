from fastapi import APIRouter

from app.api import assess, health, learner, parking, review, sessions, skills, tutor

api_router = APIRouter(prefix="/api")
for r in (health, learner, skills, sessions, tutor, assess, review, parking):
    api_router.include_router(r.router)
