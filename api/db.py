"""PostgreSQL prediction-log store (Claim 4 fuel for Phases 4-5).

One ``predictions`` row per prediction: the 24 request fields plus
prediction, probability, startup-pinned model_version, and timestamp.
No SQLite fallback per D-03 — when ``DATABASE_URL`` is unset the engine
is ``None``, table creation warns, and ``/predict`` fails closed with
503 rather than serving without a log.
"""
from __future__ import annotations

import datetime
import os
import time

from sqlalchemy import DateTime, Float, Integer, String, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from src.utils.config import load_config
from src.utils.logger import get_logger

log = get_logger()


class Base(DeclarativeBase):
    """Declarative base for the prediction-log tables."""


class PredictionLog(Base):
    """Full prediction record: 24 request fields + outcome + version."""

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    age: Mapped[float | None] = mapped_column(Float, nullable=True)
    bp: Mapped[float | None] = mapped_column(Float, nullable=True)
    sg: Mapped[float | None] = mapped_column(Float, nullable=True)
    al: Mapped[float | None] = mapped_column(Float, nullable=True)
    su: Mapped[float | None] = mapped_column(Float, nullable=True)
    bgr: Mapped[float | None] = mapped_column(Float, nullable=True)
    bu: Mapped[float | None] = mapped_column(Float, nullable=True)
    sc: Mapped[float | None] = mapped_column(Float, nullable=True)
    sod: Mapped[float | None] = mapped_column(Float, nullable=True)
    pot: Mapped[float | None] = mapped_column(Float, nullable=True)
    hemo: Mapped[float | None] = mapped_column(Float, nullable=True)
    pcv: Mapped[float | None] = mapped_column(Float, nullable=True)
    wc: Mapped[float | None] = mapped_column(Float, nullable=True)
    rc: Mapped[float | None] = mapped_column(Float, nullable=True)
    rbc: Mapped[str] = mapped_column(String(16))
    pc: Mapped[str] = mapped_column(String(16))
    pcc: Mapped[str] = mapped_column(String(16))
    ba: Mapped[str] = mapped_column(String(16))
    htn: Mapped[str] = mapped_column(String(16))
    dm: Mapped[str] = mapped_column(String(16))
    cad: Mapped[str] = mapped_column(String(16))
    appet: Mapped[str] = mapped_column(String(16))
    pe: Mapped[str] = mapped_column(String(16))
    ane: Mapped[str] = mapped_column(String(16))
    prediction: Mapped[int] = mapped_column(Integer)
    probability: Mapped[float] = mapped_column(Float)
    model_version: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        # Client-side default mirrors the server default so in-memory
        # instances (and mocked-session captures) always carry a timestamp
        # per D-04; the server default still applies on real INSERTs.
        default=datetime.datetime.now,
    )


# Unbound until lifespan configures it; tests replace this attribute
# wholesale via patch("api.db.Session"), so call it as db.Session().
Session = sessionmaker()


def get_database_url() -> str:
    """DATABASE_URL env wins; config db.database_url is the static fallback."""
    return os.environ.get("DATABASE_URL") or load_config()["db"].get("database_url", "") or ""


def get_engine():
    """Engine for the log store, or None when DATABASE_URL is unset.

    Never logs the URL value — only whether a store is configured.
    """
    url = get_database_url()
    if not url:
        return None
    return create_engine(url)


def create_tables(retries: int = 3) -> bool:
    """Create the log tables with retries; False when no store is configured.

    Raises loudly when a configured store stays unreachable (T-03-06) —
    Compose health-gated Postgres removes the startup race in deployment.
    """
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            engine = get_engine()
            if engine is None:
                log.warning(
                    "DATABASE_URL unset — prediction log unavailable (/predict will 503)"
                )
                return False
            Base.metadata.create_all(bind=engine)
            return True
        except Exception as exc:
            last_exc = exc
            log.warning(
                f"create_tables attempt {attempt}/{retries} failed: "
                f"{type(exc).__name__}: {exc}"
            )
            time.sleep(1)
    raise RuntimeError(
        f"Prediction-log tables unavailable after {retries} attempts: "
        f"{type(last_exc).__name__}: {last_exc}"
    )
