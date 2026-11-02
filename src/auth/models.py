"""SQLAlchemy models for authentication."""

from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.database import Base


class User(Base):
    """User account — patient or doctor."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=True)  # nullable for OAuth-only users later
    role = Column(String(20), nullable=False, default="patient")  # "patient" or "doctor"
    google_id = Column(String(255), unique=True, nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    patient_profile = relationship(
        "PatientProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    doctor_profile = relationship(
        "DoctorProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    patient_mappings = relationship(
        "PatientDoctorMapping",
        foreign_keys="PatientDoctorMapping.patient_id",
        back_populates="patient",
    )
    doctor_mappings = relationship(
        "PatientDoctorMapping",
        foreign_keys="PatientDoctorMapping.doctor_id",
        back_populates="doctor",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"


class PatientProfile(Base):
    """Patient profile — one-to-one with a User whose role is ``patient``."""

    __tablename__ = "patient_profiles"

    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(DateTime(timezone=True), nullable=True)
    sex = Column(String(10), nullable=True)  # "M", "F", "O"
    phone = Column(String(20), nullable=True)
    mrn = Column(String(50), unique=True, nullable=True, index=True)  # medical record number
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="patient_profile")

    def __repr__(self) -> str:
        return f"<PatientProfile(user_id={self.user_id}, mrn={self.mrn})>"


class DoctorProfile(Base):
    """Doctor profile — one-to-one with a User whose role is ``doctor``."""

    __tablename__ = "doctor_profiles"

    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    license_number = Column(String(50), unique=True, nullable=True, index=True)
    specialization = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="doctor_profile")

    def __repr__(self) -> str:
        return f"<DoctorProfile(user_id={self.user_id}, license={self.license_number})>"


class PatientDoctorMapping(Base):
    """Doctor→patient assignment — which doctor is responsible for which patient."""

    __tablename__ = "patient_doctor_mapping"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True, nullable=False)

    patient = relationship("User", foreign_keys=[patient_id], back_populates="patient_mappings")
    doctor = relationship("User", foreign_keys=[doctor_id], back_populates="doctor_mappings")

    def __repr__(self) -> str:
        return f"<PatientDoctorMapping(doctor_id={self.doctor_id}, patient_id={self.patient_id})>"
