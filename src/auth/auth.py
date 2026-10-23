"""Authentication business logic: register and authenticate users."""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.auth.models import User
from src.auth.schemas import UserRegister
from src.auth.security import hash_password, verify_password


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, user_in: UserRegister) -> User:
    existing = get_user_by_email(db, user_in.email)
    if existing:
        return None  # caller handles the duplicate
    hashed = hash_password(user_in.password)
    user = User(email=user_in.email, password_hash=hashed, role=user_in.role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.password_hash or ""):
        return None
    return user
