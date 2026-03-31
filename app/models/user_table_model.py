from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, Date, Float
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import relationship
from app.dependencies.database import Base


class UserTableClass(Base, AsyncAttrs):
    __tablename__ = "user_table"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    role = Column(String(100), nullable=True, default="user")
    user_id = Column(String(100), nullable=True, unique=True)
    profile_picture = Column(String(500), nullable=True)

    name = Column(String(100), nullable=False)
    phone_number = Column(String(15), nullable=True, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    password = Column(String(255), nullable=True)
    provider = Column(String(255), default="local")

    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    otp_code = Column(String(10), nullable=True)
    otp_expiry = Column(DateTime, nullable=True)

    monthly_income = Column(Float, nullable=True)
    occupation = Column(String(50), nullable=True)
    savings_goal = Column(Float, nullable=True)

    personal = relationship(
        "PersonalDetailsClass",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )

    settings = relationship(
        "UserSettingsClass",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )

    goals = relationship(
        "SavingsGoal",
        cascade="all, delete-orphan"
    )


class PersonalDetailsClass(Base, AsyncAttrs):
    __tablename__ = "personaldetails_table"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    usertable_id = Column(Integer, ForeignKey("user_table.id", ondelete="CASCADE"), nullable=False, unique=True)

    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(15), nullable=True)
    address = Column(JSON, nullable=True)
    nationality = Column(String(50), nullable=True)
    favnum = Column(String(15), nullable=True)
    emergencynumber = Column(Integer, nullable=True, unique=True)

    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    user = relationship("UserTableClass", back_populates="personal")
