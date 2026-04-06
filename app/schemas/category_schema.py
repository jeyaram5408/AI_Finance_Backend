from pydantic import BaseModel, Field
from typing import Literal


class CategoryBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    type: Literal["income", "expense"]


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=100)
    type: Literal["income", "expense"] | None = None


class CategoryResponse(CategoryBase):
    id: int
    user_id: int
    user_code: str

    class Config:
        from_attributes = True