import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import select, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth_dependency import require_admin
from app.dependencies.db import get_db
from app.models.media_model import MediaAsset
from app.models.user_table_model import UserTableClass


router = APIRouter(prefix="/admin/media", tags=["Admin Media"])

UPLOAD_DIR = os.path.join("uploads", "admin_media")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_TYPES = {
    "image/jpeg": "image",
    "image/jpg": "image",
    "image/png": "image",
    "image/webp": "image",
    "video/mp4": "video",
    "video/webm": "video",
    "video/quicktime": "video",
    "application/pdf": "document",
}

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB


@router.post("/upload")
async def upload_admin_media(
    title: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_admin: UserTableClass = Depends(require_admin),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, PNG, WEBP, MP4, WEBM, MOV, PDF files are allowed"
        )

    file_content = await file.read()

    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Max 20MB allowed")

    ext = os.path.splitext(file.filename)[1].lower()
    stored_name = f"{uuid.uuid4()}{ext}"
    save_path = os.path.join(UPLOAD_DIR, stored_name)

    with open(save_path, "wb") as buffer:
        buffer.write(file_content)

    media_type = ALLOWED_TYPES[file.content_type]
    relative_path = f"admin_media/{stored_name}"

    media = MediaAsset(
        title=title.strip(),
        original_name=file.filename,
        stored_name=stored_name,
        file_path=relative_path,
        file_url="",
        media_type=media_type,
        mime_type=file.content_type,
        file_size=len(file_content),
        uploaded_by=current_admin.id,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(media)
    await db.commit()
    await db.refresh(media)

    media.file_url = f"/admin/media/{media.id}/file"
    await db.commit()
    await db.refresh(media)

    return {
        "success": True,
        "message": "Media uploaded successfully",
        "data": {
            "id": media.id,
            "title": media.title,
            "file_url": media.file_url,
            "media_type": media.media_type,
            "mime_type": media.mime_type,
            "file_size": media.file_size,
        }
    }


@router.get("")
async def get_admin_media(
    search: str | None = Query(None),
    media_type: str | None = Query(None),
    is_active: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_admin: UserTableClass = Depends(require_admin),
):
    stmt = select(MediaAsset).order_by(desc(MediaAsset.id))

    if search:
        like = f"%{search.lower()}%"
        stmt = stmt.where(
            or_(
                MediaAsset.title.ilike(like),
                MediaAsset.original_name.ilike(like),
            )
        )

    if media_type:
        stmt = stmt.where(MediaAsset.media_type == media_type)

    if is_active is not None:
        stmt = stmt.where(MediaAsset.is_active == is_active)

    result = await db.execute(stmt)
    items = result.scalars().all()

    return {
        "items": [
            {
                "id": item.id,
                "title": item.title,
                "original_name": item.original_name,
                "file_url": f"/admin/media/{item.id}/file",
                "file_path": item.file_path,
                "media_type": item.media_type,
                "mime_type": item.mime_type,
                "file_size": item.file_size,
                "is_active": item.is_active,
                "created_at": item.created_at,
            }
            for item in items
        ]
    }


@router.get("/{media_id}/file")
async def get_admin_media_file(
    media_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: UserTableClass = Depends(require_admin),
):
    media = await db.get(MediaAsset, media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    full_path = os.path.join("uploads", media.file_path)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=full_path,
        media_type=media.mime_type,
        filename=media.original_name
    )


@router.patch("/{media_id}/status")
async def update_media_status(
    media_id: int,
    is_active: bool = Form(...),
    db: AsyncSession = Depends(get_db),
    current_admin: UserTableClass = Depends(require_admin),
):
    media = await db.get(MediaAsset, media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    media.is_active = is_active
    media.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(media)

    return {
        "success": True,
        "message": "Media status updated",
        "data": {
            "id": media.id,
            "is_active": media.is_active
        }
    }


@router.delete("/{media_id}")
async def delete_admin_media(
    media_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: UserTableClass = Depends(require_admin),
):
    media = await db.get(MediaAsset, media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    full_path = os.path.join("uploads", media.file_path)
    if os.path.exists(full_path):
        os.remove(full_path)

    await db.delete(media)
    await db.commit()

    return {
        "success": True,
        "message": "Media deleted successfully"
    }
