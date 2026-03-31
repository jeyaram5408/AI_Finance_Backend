from sqlalchemy import Column, ForeignKey, Integer, String, Float, Date
from app.dependencies.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), index=True, nullable=False)
    amount = Column(Float, nullable=False)
    type = Column(String(10), nullable=False)  # income / expense
    budget_id = Column(Integer, ForeignKey("budgets.id"), nullable=True)
    category = Column(String(100), nullable=False)
    date = Column(Date, nullable=False)
    user_id = Column(Integer, ForeignKey("user_table.id", ondelete="CASCADE"), nullable=False, index=True)
