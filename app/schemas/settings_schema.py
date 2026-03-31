from pydantic import BaseModel, EmailStr, field_validator





class SettingsUpdate(BaseModel):
    # profile/account settings
    name: str | None = None
    email: EmailStr | None = None
    phone_number: str | None = None
    password: str | None = None

    # app settings
    default_currency: str | None = None
    monthly_budget: float | None = None

    email_notifications: bool | None = None
    push_notifications: bool | None = None
    budget_alerts: bool | None = None

    @field_validator("name", "phone_number", "password", "default_currency","email", mode="before")
    @classmethod
    def clean_strings(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            v = v.strip()
            if v == "":
                return None
        return v

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
    def validate_password(cls, v):
        if v is None:
            return v

        if len(v) < 5:
            raise ValueError("Password must be at least 5 characters long")

        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")

        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")

        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError("Password must contain at least one special character")

        return v

    @field_validator("default_currency")
    @classmethod
    def validate_currency(cls, v):
        if v is None:
            return v
        return v.upper()
