from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import relationship

from app.dependencies.database import Base


class UserSettingsClass(Base, AsyncAttrs):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("user_table.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    currency = Column(String(10), nullable=True)
    monthly_budget = Column(Float, nullable=True)

    email_notifications = Column(Boolean, default=True)
    push_notifications = Column(Boolean, default=False)
    budget_alerts = Column(Boolean, default=True)

    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    user = relationship("UserTableClass", back_populates="settings")
