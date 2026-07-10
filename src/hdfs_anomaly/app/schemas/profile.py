from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from hdfs_anomaly.app.models.profile import Role, Status


class ProfileResponse(BaseModel):
    id: int
    email: str
    status: Status
    role: Role
    version: int
    created_at: datetime


class EmailChangeRequest(BaseModel):
    new_email: EmailStr
    current_password: str = Field(min_length=1)
    version: int


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=6)
    version: int


class AdminProfilesPageResponse(BaseModel):
    items: list[ProfileResponse]
    has_next: bool


class AdminProfileStatusUpdateRequest(BaseModel):
    status: Status
    version: int = Field(ge=0)


class AdminProfileRoleUpdateRequest(BaseModel):
    role: Role
    version: int = Field(ge=0)
