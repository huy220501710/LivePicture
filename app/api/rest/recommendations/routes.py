from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.celery.tasks import make_user_recommendations
from app.postgresql.models import UsersOrm

from app.api.rest.dependencies import db, filter, user_id
from app.postgresql.models import (
    PinsOrm,
    UsersOrm,
    UsersRecommendationsPinsOrm,
)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("/check")
async def check_user_recommendations(user_id: user_id, db: db):
    result = await db.execute(select(UsersOrm).where(UsersOrm.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    today = datetime.now(timezone.utc).date()

    if user.recommendation_created_at and user.recommendation_created_at.date() == today:
        return {"make_recommendations": False}

    # 🔥 TRIGGER CELERY DUY NHẤT Ở ĐÂY
    make_user_recommendations.delay(user_id)

    return {"make_recommendations": True}


@router.get("/{update_id}")
async def get_recommendation_pins(update_id: int, user_id: user_id, db: db, filter: filter):
    result = await db.execute(
        select(UsersRecommendationsPinsOrm).where(
            (UsersRecommendationsPinsOrm.user_id == user_id)
            & (UsersRecommendationsPinsOrm.update_id == update_id)
        )
    )

    # Get results
    pins_recommendations = result.scalars().all()

    result_pins = []
    for row in pins_recommendations:
        pin_id = row.pin_id
        pin_db = await db.scalar(select(PinsOrm).where(PinsOrm.id == pin_id))
        result_pins.append(pin_db)

    return result_pins[filter.offset : filter.offset + filter.limit]
