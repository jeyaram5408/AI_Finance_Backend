from pydantic import BaseModel
import datetime


class TransactionBase(BaseModel):
    type: str
    title: str
    category: str
    amount: float
    date: datetime.date


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    type: str | None = None
    title: str | None = None
    category: str | None = None
    amount: float | None = None
    date: datetime.date | None = None


class TransactionResponse(TransactionBase):
    id: int

    class Config:
        from_attributes = True