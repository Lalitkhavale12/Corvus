"""Database session management for auth — lazy engine, no import-time connection."""

from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from src.utils.config import load_config

Base = declarative_base()

_engine = None
_SessionLocal = None


def get_database_url() -> str:
    cfg = load_config()
    db_cfg = cfg.get("db", {})
    url = db_cfg.get("database_url", "")
    if not url:
        url = os.getenv("DATABASE_URL", "")
    return url


def get_engine():
    global _engine
    if _engine is None:
        url = get_database_url()
        if not url:
            return None
        _engine = create_engine(url, pool_pre_ping=True)
    return _engine


def get_session_local():
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        if engine is None:
            return None
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal


def get_db():
    SessionLocal = get_session_local()
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL not configured — auth requires PostgreSQL")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
