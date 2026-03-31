from pydantic import BaseModel


class FeatureBase(BaseModel):
    title: str
    description: str
    icon_color: str | None = None


class FeatureCreate(FeatureBase):
    pass


class FeatureUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    icon_color: str | None = None


class FeatureResponse(FeatureBase):
    id: int

    class Config:
        from_attributes = True