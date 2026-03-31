from datetime import date, datetime
from pydantic import BaseModel, EmailStr, field_validator, field_serializer, ConfigDict

from app.utils.time_utils import format_date, format_datetime


class AddressSchema(BaseModel):
    door_no: str | None = None
    street_name: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    pincode: str | None = None

    @field_validator("*", mode="before")
    @classmethod
    def clean_strings(cls, v):
        if isinstance(v, str):
            v = v.strip()
            return v if v else None
        return v


class PersonalDetailsCreate(BaseModel):
    gender: str
    date_of_birth: date
    address: AddressSchema | None = None
    nationality: str | None = None
    favnum: str | None = None
    emergencynumber: int | None = None

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: str):
        v = v.strip()
        if not v:
            raise ValueError("gender cannot be empty")
        return v


class UserCreate(BaseModel):
    user_id: str | None = None
    role: str | None = "user"
    name: str
    email: EmailStr
    phone_number: str | None = None
    password: str
    personal: PersonalDetailsCreate | None = None

    monthly_income: float | None = None
    occupation: str | None = None
    savings_goal: float | None = None

    @field_validator("user_id", "role", "phone_number", "occupation", mode="before")
    @classmethod
    def clean_optional_strings(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            v = v.strip()
            return v if v else None
        return v

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, v):
        if not isinstance(v, str) or not v.strip():
            raise ValueError("name cannot be empty")
        return " ".join(v.strip().split())

    @field_validator("password", mode="before")
    @classmethod
    def validate_password_required(cls, v):
        if not isinstance(v, str) or not v.strip():
            raise ValueError("password cannot be empty")
        return v.strip()

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v):
        if v is None:
            return v
        if len(v) < 10:
            raise ValueError("Phone number must be at least 10 digits")
        return v

    @field_validator("password")
    @classmethod
    def check_password_strength(cls, v):
        if len(v) < 5:
            raise ValueError("Password must be at least 5 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError("Password must contain at least one special character")
        return v


class OTPVerify(BaseModel):
    email: EmailStr
    otp: str


class PersonalDetailsRead(BaseModel):
    id: int
    gender: str | None = None
    date_of_birth: date | None = None
    address: AddressSchema | None = None
    emergencynumber: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_serializer("date_of_birth", when_used="json")
    def serialize_dob(self, value: date | None, _info):
        return format_date(value)

    @field_serializer("created_at", "updated_at", when_used="json")
    def serialize_datetime(self, value: datetime | None, _info):
        return format_datetime(value)

    model_config = ConfigDict(from_attributes=True)


class UserRead(BaseModel):
    id: int
    user_id: str | None = None
    role: str | None = None
    name: str
    email: EmailStr
    phone_number: str | None = None
    is_active: bool
    monthly_income: float | None = None
    occupation: str | None = None
    savings_goal: float | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    personal: PersonalDetailsRead | None = None

    @field_serializer("created_at", "updated_at", when_used="json")
    def serialize_datetime(self, value: datetime | None, _info):
        return format_datetime(value)

    model_config = ConfigDict(from_attributes=True)


class PersonalDetailsUpdate(BaseModel):
    gender: str | None = None
    date_of_birth: date | None = None
    address: AddressSchema | None = None
    emergencynumber: int | None = None

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v):
        if v is None:
            return None
        v = v.strip()
        return v if v else None


class UserUpdate(BaseModel):
    personal: PersonalDetailsUpdate | None = None
    user_id: str | None = None
    role: str | None = None
    name: str | None = None
    email: EmailStr | None = None
    phone_number: str | None = None
    password: str | None = None
    is_active: bool | None = None

    monthly_income: float | None = None
    occupation: str | None = None
    savings_goal: float | None = None

    @field_validator("user_id", "role", "name", "phone_number", "password", "occupation", mode="before")
    @classmethod
    def clean_optional_strings(cls, v):
        if v is None:
            return None
        if not isinstance(v, str):
            return v
        v = v.strip()
        if not v:
            return None
        return v

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v):
        if v is None:
            return None
        if len(v) < 10:
            raise ValueError("Phone number must be at least 10 digits")
        return v

    @field_validator("password")
    @classmethod
    def check_password_strength(cls, v):
        if v is None:
            return None
        if len(v) < 5:
            raise ValueError("Password must be at least 5 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError("Password must contain at least one special character")
        return v
