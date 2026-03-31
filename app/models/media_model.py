from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.asyncio import AsyncAttrs
from app.dependencies.database import Base


class MediaAsset(Base, AsyncAttrs):
    __tablename__ = "media_assets"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    stored_name = Column(String(255), nullable=False, unique=True)

    file_path = Column(String(500), nullable=False)   # admin_media/abc.jpg
    file_url = Column(String(500), nullable=False)    # /uploads/admin_media/abc.jpg

    media_type = Column(String(50), nullable=False)   # image / video / document
    mime_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)

    is_active = Column(Boolean, default=True)

    uploaded_by = Column(Integer, ForeignKey("user_table.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
