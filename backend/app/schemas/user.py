from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserRegisterInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = ""
    # Self-registration is always CITIZEN — elevated roles are granted by an ADMIN via
    # a separate (not-yet-built) admin endpoint, never chosen by the registrant.


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginInput(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut
