from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncAttrs

from app.dependencies.database import Base


class Feature(Base):
    __tablename__ = "features"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    icon_color = Column(String(50), nullable=True)