"""Streak, daily goal and achievement endpoints."""

from fastapi import APIRouter, Query

from backend.services import achievement_service, streak_service


router = APIRouter(prefix="/api", tags=["motivation"])


@router.get("/streak")
def get_streak(heatmap_days: int = Query(default=182, ge=7, le=730)):
    return streak_service.get_summary(heatmap_days=heatmap_days)


@router.get("/achievements")
def get_achievements():
    return achievement_service.evaluate()
