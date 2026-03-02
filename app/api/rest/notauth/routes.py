from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import settings

router = APIRouter(prefix="/notauth", tags=["notauth"])


@router.get("/images/{id}")
async def get_image(id: int):
    media_root = Path(settings.MEDIA_PATH)
    notauth_dir = media_root / "notauth"

    target = notauth_dir / f"{id}.jpg"
    fallback = notauth_dir / "1.jpg"

    if target.exists():
        return FileResponse(str(target))

    if fallback.exists():
        return FileResponse(str(fallback))

    raise HTTPException(status_code=404, detail="Default notauth image (1.jpg) not found")
