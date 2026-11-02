"""Pydantic schemas for authentication."""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Union


class TokenData(BaseModel):
    user_id: int | None = None
    role: str | None = None


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    role: str = Field(default="patient", pattern="^(patient|doctor)$")


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str
    role: str
    is_active: bool
    created_at: datetime | None = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Profile schemas (Phase 8-02)
# ---------------------------------------------------------------------------


class PatientProfileCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    date_of_birth: datetime | None = None
    sex: str | None = Field(default=None, max_length=10)  # "M", "F", "O"
    phone: str | None = Field(default=None, max_length=20)
    mrn: str | None = Field(default=None, max_length=50)


class PatientProfileOut(BaseModel):
    user_id: int
    first_name: str
    last_name: str
    date_of_birth: datetime | None = None
    sex: str | None = None
    phone: str | None = None
    mrn: str | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class DoctorProfileCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    license_number: str | None = Field(default=None, max_length=50)
    specialization: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=20)


class DoctorProfileOut(BaseModel):
    user_id: int
    first_name: str
    last_name: str
    license_number: str | None = None
    specialization: str | None = None
    phone: str | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class ProfileOut(BaseModel):
    """Role-appropriate profile returned by GET /auth/profile."""

    role: str
    patient_profile: PatientProfileOut | None = None
    doctor_profile: DoctorProfileOut | None = None


class PatientDoctorAssign(BaseModel):
    patient_email: EmailStr


class PatientDoctorMappingOut(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    assigned_at: datetime | None = None
    is_active: bool

    class Config:
        from_attributes = True
