import json
import mimetypes
import uuid
from os.path import exists

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import delete, desc, insert, or_, select, update

from app.api.rest.dependencies import db, filter, filter_with_value, user_id
from app.api.rest.tags.routes import get_all_tags
from app.api.rest.utils import extract_first_frame, get_primary_color, save_file
from app.config import settings
from app.postgresql.models import (
    LikesOrm,
    PinsOrm,
    TagsOrm,
    UsersOrm,
    pins_tags,
    users_pins,
)

from .schemas import PinIn, PinOut

mimetypes.add_type("image/webp", ".webp")

from app.celery.tasks import (
    make_update_pin_created_for_followers,
    make_update_save_pin,
    user_view_pin,
)

router = APIRouter(prefix="/pins", tags=["pins"])


@router.get("/", response_model=list[PinOut])
async def get_pins(user_id: user_id, db: db, filter: filter):
    pins = await db.scalars(
        select(PinsOrm).offset(filter.offset).limit(filter.limit).order_by(desc(PinsOrm.id))
    )

    return pins


@router.get("/tag/{tag_name}", response_model=list[PinOut])
async def get_pins_by_tag(tag_name: str, user_id: user_id, db: db, filter: filter):
    tag = await db.scalar(select(TagsOrm).where(TagsOrm.name == tag_name))
    if tag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tag not found")

    result = await db.execute(select(pins_tags).where(pins_tags.c.tag_id == tag.id))
    rows = result.all()
    pins = []
    for row in rows:
        pin_id = row[0]
        pin = await db.scalar(select(PinsOrm).where(PinsOrm.id == pin_id))
        pins.append(pin)
    return pins[filter.offset : filter.offset + filter.limit]


@router.get("/search", response_model=list[PinOut])
async def search_pins(filter_with_value: filter_with_value, user_id: user_id, db: db):
    result = {}

    split_and_clean = [part for part in filter_with_value.value.split(" ") if part.strip()]
    tags = await get_all_tags(db, user_id)
    tag_list = tags.all()
    for value in split_and_clean:
        pins = await db.scalars(
            select(PinsOrm).where(
                or_(PinsOrm.title.ilike(f"%{value}%"), PinsOrm.description.ilike(f"%{value}%"))
            )
        )
        pin_list = pins.all()
        for pin in pin_list:
            if pin.id not in result:
                result[pin.id] = pin

        for tag in tag_list:
            if value in tag.name:
                tag = await db.scalar(select(TagsOrm).where(TagsOrm.name == tag.name))
                result_table = await db.execute(
                    select(pins_tags).where(pins_tags.c.tag_id == tag.id)
                )
                rows = result_table.all()
                for row in rows:
                    pin_by_tag_id = row[0]
                    if pin_by_tag_id not in result:
                        pin_by_tag = await db.scalar(
                            select(PinsOrm).where(PinsOrm.id == pin_by_tag_id)
                        )
                        result[pin_by_tag.id] = pin_by_tag

    return [pin for pin in result.values()][
        filter_with_value.offset : filter_with_value.offset + filter_with_value.limit
    ]


@router.post("/", response_model=PinOut, status_code=status.HTTP_201_CREATED)
async def create_pin(user_id: user_id, db: db, pin_model: PinIn):
    pin = await db.scalar(
        insert(PinsOrm).values(**pin_model.model_dump(), user_id=user_id).returning(PinsOrm)
    )
    await db.commit()
    return pin


@router.post("/create-pin-entity", response_model=PinOut, status_code=status.HTTP_201_CREATED)
async def create_pin_entity(
    user_id: user_id,
    db: db,
    pin_model: str = Form(...),
    file: UploadFile = File(...),
):
    ALLOWED_FILE_TYPES = [
        "image/jpeg",
        "image/jpg",
        "image/gif",
        "image/webp",
        "image/png",
        "image/bmp",
        "video/mp4",
        "video/webm",
    ]

    if file.content_type not in ALLOWED_FILE_TYPES:
        raise HTTPException(status_code=415, detail="Invalid file type")

    # 1️⃣ Parse pin data
    pin_data = json.loads(pin_model)
    pin = await db.scalar(
        insert(PinsOrm)
        .values(**pin_data, user_id=user_id)
        .returning(PinsOrm)
    )

    # 2️⃣ Media root + folder
    media_root = Path(settings.MEDIA_PATH)
    pins_dir = media_root / "pins"
    pins_dir.mkdir(parents=True, exist_ok=True)

    # 3️⃣ Save main file
    filename = f"{uuid.uuid4()}{Path(file.filename).suffix}"
    full_path = pins_dir / filename
    await save_file(file, str(full_path))

    rgb = None
    video_preview = None

    # 4️⃣ Image case
    if file.content_type.startswith("image/"):
        rgb_tuple = await get_primary_color(str(full_path))
        rgb = f"rgb({rgb_tuple[0]}, {rgb_tuple[1]}, {rgb_tuple[2]})"

    # 5️⃣ Video case
    elif file.content_type.startswith("video/"):
        preview_name = f"{uuid.uuid4()}.jpg"
        preview_path = pins_dir / preview_name

        await extract_first_frame(str(full_path), str(preview_path))
        rgb_tuple = await get_primary_color(str(preview_path))
        rgb = f"rgb({rgb_tuple[0]}, {rgb_tuple[1]}, {rgb_tuple[2]})"
        video_preview = f"pins/{preview_name}"

    # 6️⃣ Update pin – LƯU RELATIVE PATH
    pin = await db.scalar(
        update(PinsOrm)
        .where(PinsOrm.id == pin.id)
        .values(
            image=f"pins/{filename}",
            rgb=rgb,
            videoPreview=video_preview,
        )
        .returning(PinsOrm)
    )
    await db.commit()

    make_update_pin_created_for_followers.delay(user_id, pin.id)

    return pin


@router.delete("/{pin_id}", status_code=status.HTTP_204_NO_CONTENT)
async def user_delete_created_pin(pin_id: int, user_id: user_id, db: db):
    pin = await db.scalar(select(PinsOrm).where(PinsOrm.id == pin_id))
    if pin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="pin not found")

    await db.execute(delete(PinsOrm).where(PinsOrm.user_id == user_id, PinsOrm.id == pin_id))
    await db.commit()
    return {"status", "ok"}


from pathlib import Path

# reload-test
@router.post("/upload/{id}", response_model=PinOut)
async def upload_image(user_id: user_id, id: int, db: db, file: UploadFile):
    pin = await db.scalar(select(PinsOrm).where(PinsOrm.id == id))
    if pin is None:
        raise HTTPException(status_code=404, detail="pin not found")

    # 1️⃣ Tạo tên file
    filename = f"{uuid.uuid4()}{Path(file.filename).suffix}"

    # 2️⃣ Media root
    media_root = Path(settings.MEDIA_PATH)
    pins_dir = media_root / "pins"
    pins_dir.mkdir(parents=True, exist_ok=True)

    # 3️⃣ Full path để ghi file
    full_path = pins_dir / filename
    await save_file(file, str(full_path))

    # 4️⃣ Xử lý màu / video
    rgb = None
    video_preview = None

    if file.content_type.startswith("image/"):
        rgb_tuple = await get_primary_color(str(full_path))
        rgb = f"rgb({rgb_tuple[0]}, {rgb_tuple[1]}, {rgb_tuple[2]})"

    elif file.content_type.startswith("video/"):
        preview_name = f"{uuid.uuid4()}.jpg"
        preview_path = pins_dir / preview_name

        await extract_first_frame(str(full_path), str(preview_path))
        rgb_tuple = await get_primary_color(str(preview_path))
        rgb = f"rgb({rgb_tuple[0]}, {rgb_tuple[1]}, {rgb_tuple[2]})"
        video_preview = f"pins/{preview_name}"

    # 5️⃣ Lưu RELATIVE PATH vào DB
    db_image_path = f"pins/{filename}"

    pin = await db.scalar(
        update(PinsOrm)
        .where(PinsOrm.id == id)
        .values(
            image=db_image_path,
            rgb=rgb,
            videoPreview=video_preview,
        )
        .returning(PinsOrm)
    )
    await db.commit()

    return pin



import mimetypes

@router.get("/upload/{id}")
async def get_image(user_id: user_id, id: int, db: db):
    pin = await db.scalar(select(PinsOrm).where(PinsOrm.id == id))
    if pin is None:
        raise HTTPException(status_code=404, detail="pin not found")

    media_root = Path(settings.MEDIA_PATH)
    default_image = media_root / "notauth" / "1.jpg"

    # 1️⃣ Không có ảnh → fallback
    if not pin.image:
        return FileResponse(default_image, media_type="image/jpeg")

    # 2️⃣ pin.image là RELATIVE PATH (pins/xxx.jpg)
    full_path = media_root / pin.image

    if not full_path.exists():
        return FileResponse(default_image, media_type="image/jpeg")

    # 3️⃣ Guess mime type từ full path
    mime_type, _ = mimetypes.guess_type(str(full_path))
    if mime_type is None:
        mime_type = "application/octet-stream"

    return FileResponse(full_path, media_type=mime_type)


@router.get("/{id}", response_model=PinOut)
async def get_pin_by_id(user_id: user_id, id: int, db: db):
    pin = await db.scalar(select(PinsOrm).where(PinsOrm.id == id))
    if pin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="pin not found")

    user_view_pin.delay(user_id, id)

    return pin


@router.get("/user_created_pins/{id}", response_model=list[PinOut])
async def get_user_created_pins(id: int, user_id: user_id, db: db, filter: filter):
    user = await db.scalar(select(UsersOrm).where(UsersOrm.id == id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

    pins = await db.scalars(
        select(PinsOrm)
        .where(PinsOrm.user_id == id)
        .offset(filter.offset)
        .limit(filter.limit)
        .order_by(desc(PinsOrm.id))
    )
    return pins


@router.post("/user_saved_pins/{pin_id}", status_code=status.HTTP_201_CREATED)
async def user_save_pin(pin_id: int, user_id: user_id, db: db):
    pin = await db.scalar(select(PinsOrm).where(PinsOrm.id == pin_id))
    if pin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="pin not found")

    query = select(users_pins).where(users_pins.c.user_id == user_id, users_pins.c.pin_id == pin_id)
    result = await db.execute(query)
    user_pin = result.fetchone()  # Use `.fetchone()` to get a single result

    if user_pin:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="User already saved this pin"
        )

    await db.execute(insert(users_pins).values(user_id=user_id, pin_id=pin_id))
    await db.commit()

    if pin.user_id != user_id:
        make_update_save_pin.delay(pin.user_id, user_id, pin_id, "Profile")

    return {"status", "ok"}


@router.delete("/user_saved_pins/{pin_id}", status_code=status.HTTP_204_NO_CONTENT)
async def user_delete_saved_pin(pin_id: int, user_id: user_id, db: db):
    pin = await db.scalar(select(PinsOrm).where(PinsOrm.id == pin_id))
    if pin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="pin not found")

    await db.execute(
        delete(users_pins).where(users_pins.c.user_id == user_id, users_pins.c.pin_id == pin_id)
    )
    await db.commit()
    return {"status", "ok"}


@router.get("/user_saved_pins/{id}", response_model=list[PinOut])
async def get_user_saved_pins(id: int, user_id: user_id, db: db, filter: filter):
    user = await db.scalar(select(UsersOrm).where(UsersOrm.id == id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

    result = await db.execute(
        select(users_pins)
        .where(users_pins.c.user_id == id)
        .offset(filter.offset)
        .limit(filter.limit)
    )
    rows = result.all()
    pins = []
    for row in rows:
        pin_id = row[1]
        pin = await db.scalar(select(PinsOrm).where(PinsOrm.id == pin_id))
        pins.append(pin)
    return pins


@router.get("/user_liked_pins/{id}", response_model=list[PinOut])
async def get_user_liked_pins(id: int, user_id: user_id, db: db, filter: filter):
    user = await db.scalar(select(UsersOrm).where(UsersOrm.id == id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

    result = await db.execute(
        select(PinsOrm)
        .join(LikesOrm, PinsOrm.id == LikesOrm.pin_id)
        .where(LikesOrm.user_id == id)
        .offset(filter.offset)
        .limit(filter.limit)
    )
    pins = result.scalars().all()

    return pins
