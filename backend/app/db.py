"""Results database: every satellite analysis and comparison is saved here.

It serves three purposes:
- History: list and reopen past results (GET /api/history).
- Cache: the same area, date(s) and model return the saved result instantly instead of re-running
  the model. Results for "latest imagery" expire after CACHE_LATEST_DAYS, because Esri updates it.
- Records: coverage, scores and area are stored as columns, so they can be queried or exported.

SQLite by default (one file, nothing to install). Set DATABASE_URL to use PostgreSQL instead.
"""
import gzip
import hashlib
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import (JSON, DateTime, Float, Integer, LargeBinary, String, create_engine, func,
                        select)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


class Record(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(16), index=True)          # "analysis" | "comparison"
    cache_key: Mapped[str] = mapped_column(String(40), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    # Area: [west, south, east, north] in degrees, plus its centre for map queries.
    west: Mapped[float] = mapped_column(Float)
    south: Mapped[float] = mapped_column(Float)
    east: Mapped[float] = mapped_column(Float)
    north: Mapped[float] = mapped_column(Float)
    center_lat: Mapped[float] = mapped_column(Float, index=True)
    center_lon: Mapped[float] = mapped_column(Float, index=True)
    area_ha: Mapped[float] = mapped_column(Float)

    # Imagery: Wayback release ids (None = latest) and their dates.
    release: Mapped[int | None] = mapped_column(Integer)
    date: Mapped[str] = mapped_column(String(32))
    release_after: Mapped[int | None] = mapped_column(Integer)
    date_after: Mapped[str | None] = mapped_column(String(32))

    # Summary, stored as columns so it can be listed and queried without opening the result.
    coverage: Mapped[dict] = mapped_column(JSON)                       # after-date coverage for comparisons
    green_score: Mapped[float] = mapped_column(Float)
    urban_score: Mapped[float] = mapped_column(Float)
    level: Mapped[str] = mapped_column(String(16))
    changed_percent: Mapped[float | None] = mapped_column(Float)
    changed_hectares: Mapped[float | None] = mapped_column(Float)
    model: Mapped[str] = mapped_column(String(120))

    # The full API response (with images), gzip-compressed JSON.
    result: Mapped[bytes] = mapped_column(LargeBinary)


def _engine_args(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {"pool_pre_ping": True}


engine = create_engine(settings.database_url, **_engine_args(settings.database_url))
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def init_db() -> None:
    if settings.database_url.startswith("sqlite:///"):
        settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(engine)


def cache_key(**parts) -> str:
    """Stable key for one request: area (rounded to ~1 m), zoom, release(s), options and model."""
    if "bbox" in parts:
        parts["bbox"] = [round(v, 5) for v in parts["bbox"]]
    return hashlib.sha1(json.dumps(parts, sort_keys=True).encode()).hexdigest()


def find_cached(key: str, uses_latest: bool) -> Record | None:
    """Newest saved result for this key, unless it is "latest" imagery older than the cache window."""
    with SessionLocal() as s:
        q = select(Record).where(Record.cache_key == key).order_by(Record.created_at.desc()).limit(1)
        rec = s.scalars(q).first()
    if rec is None:
        return None
    if uses_latest:
        created = rec.created_at if rec.created_at.tzinfo else rec.created_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - created > timedelta(days=settings.cache_latest_days):
            return None
    return rec


def save(kind: str, key: str, bbox: list[float], summary: dict, result_json: str) -> int:
    w, s_, e, n = bbox
    rec = Record(kind=kind, cache_key=key, created_at=datetime.now(timezone.utc),
                 west=w, south=s_, east=e, north=n, center_lat=(s_ + n) / 2, center_lon=(w + e) / 2,
                 result=gzip.compress(result_json.encode()), **summary)
    with SessionLocal() as s:
        s.add(rec)
        s.commit()
        return rec.id


def load_result(rec: Record) -> dict:
    return json.loads(gzip.decompress(rec.result))


def get(record_id: int) -> Record | None:
    with SessionLocal() as s:
        return s.get(Record, record_id)


def delete(record_id: int) -> bool:
    with SessionLocal() as s:
        rec = s.get(Record, record_id)
        if rec is None:
            return False
        s.delete(rec)
        s.commit()
        return True


def list_records(kind: str | None, limit: int, offset: int) -> tuple[list[Record], int]:
    with SessionLocal() as s:
        q = select(Record)
        count_q = select(func.count(Record.id))
        if kind:
            q, count_q = q.where(Record.kind == kind), count_q.where(Record.kind == kind)
        rows = s.scalars(q.order_by(Record.created_at.desc()).limit(limit).offset(offset)).all()
        return list(rows), s.scalar(count_q)


def count() -> int:
    with SessionLocal() as s:
        return s.scalar(select(func.count(Record.id)))
