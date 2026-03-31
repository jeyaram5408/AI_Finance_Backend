from sqlalchemy import Column, Integer, Float, String, ForeignKey
from app.dependencies.database import Base


class Budget(Base):
    __tablename__ = "budgets"   # ⚠️ MUST match ForeignKey

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_table.id"), nullable=False)

    category = Column(String(100), nullable=False)
    limit_amount = Column(Float, nullable=False)