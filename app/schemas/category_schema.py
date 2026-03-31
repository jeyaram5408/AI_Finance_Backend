from pydantic import BaseModel


class CategoryBase(BaseModel):
    name: str
    type: str


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = None
    type: str | None = None


class CategoryResponse(CategoryBase):
    id: int

    class Config:
        from_attributes = True
