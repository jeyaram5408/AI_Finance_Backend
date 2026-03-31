from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.dependencies.database import Base


class SavingsGoal(Base):
    __tablename__ = "savings_goals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_table.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(255), nullable=False)
    target_amount = Column(Float, nullable=False)
    saved_amount = Column(Float, default=0)

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    duration_days = Column(Integer, nullable=False)

    status = Column(String(50), default="in_progress")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    contributions = relationship(
        "GoalContribution",
        back_populates="goal",
        cascade="all, delete-orphan"
    )


class GoalContribution(Base):
    __tablename__ = "goal_contributions"

    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(Integer, ForeignKey("savings_goals.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("user_table.id", ondelete="CASCADE"), nullable=False)

    amount = Column(Float, nullable=False)
    contribution_date = Column(Date, nullable=False)
    note = Column(String(255), nullable=True)
    frequency_type = Column(String(50), nullable=True, default="manual")

    created_at = Column(DateTime, default=datetime.utcnow)

    goal = relationship("SavingsGoal", back_populates="contributions")
