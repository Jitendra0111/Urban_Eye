"""Saved results: list, reopen and delete past satellite analyses and comparisons."""
from fastapi import APIRouter, HTTPException, Query
from starlette.concurrency import run_in_threadpool

from . import db
from .schemas import HistoryEntry, HistoryItem, HistoryPage

router = APIRouter(prefix="/api/history", tags=["history"])


def _item(rec: db.Record) -> HistoryItem:
    return HistoryItem(id=rec.id, kind=rec.kind, created_at=rec.created_at.isoformat(),
                       bbox=[rec.west, rec.south, rec.east, rec.north], area_ha=rec.area_ha,
                       date=rec.date, date_after=rec.date_after, release=rec.release,
                       release_after=rec.release_after, coverage=rec.coverage,
                       green_score=rec.green_score, urban_score=rec.urban_score, level=rec.level,
                       changed_percent=rec.changed_percent, changed_hectares=rec.changed_hectares,
                       model=rec.model)


@router.get("", response_model=HistoryPage, summary="Saved results, newest first (no images)")
def history(kind: str | None = Query(None, pattern="^(analysis|comparison)$"),
            limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)):
    rows, total = db.list_records(kind, limit, offset)
    return HistoryPage(total=total, items=[_item(r) for r in rows])


@router.get("/{record_id}", response_model=HistoryEntry, summary="One saved result, with its images")
async def entry(record_id: int):
    rec = await run_in_threadpool(db.get, record_id)
    if rec is None:
        raise HTTPException(404, "No saved result with this id")
    result = await run_in_threadpool(db.load_result, rec)
    return HistoryEntry(item=_item(rec), result={**result, "saved_id": rec.id, "cached": True})


@router.delete("/{record_id}", status_code=204, summary="Delete a saved result")
def remove(record_id: int):
    if not db.delete(record_id):
        raise HTTPException(404, "No saved result with this id")
