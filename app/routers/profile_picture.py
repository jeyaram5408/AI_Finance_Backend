from fastapi import UploadFile, File, APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.auth_dependency import get_current_user
from app.dependencies.db import get_db
from app.models.user_table_model import UserTableClass

import os
import uuid


router = APIRouter(prefix="/profile", tags=["Profile"])

UPLOAD_DIR = "uploads/profile"

# ✅ Create folder if not exists
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload_profile_picture")
async def upload_profile_picture(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: UserTableClass = Depends(get_current_user)
):
    # ✅ Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/jpg"]

    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only image files allowed")

    # ✅ Read file ONCE
    file_content = await file.read()

    # ✅ Validate file size (2MB)
    if len(file_content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Max 2MB allowed")

    # ✅ Generate unique filename
    file_ext = file.filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{file_ext}"

    # ✅ Full path (for saving)
    save_path = os.path.join(UPLOAD_DIR, filename)

    # ✅ Delete old image (if exists)
    if current_user.profile_picture:
        old_path = os.path.join("uploads", current_user.profile_picture)

        if os.path.exists(old_path):
            os.remove(old_path)

    # ✅ Save new file
    with open(save_path, "wb") as buffer:
        buffer.write(file_content)

    # ✅ Store only relative path in DB (BEST PRACTICE)
    current_user.profile_picture = f"profile/{filename}"

    await db.commit()
    await db.refresh(current_user)

    return {
        "success": True,
        "message": "Profile picture uploaded successfully",
        "data": current_user.profile_picture
    }