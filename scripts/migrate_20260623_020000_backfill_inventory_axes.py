"""Inventory axis backfill helper (stage2a).

This script is intentionally not auto-registered in run_all_migrations.sh.
It prepares defensive backfill logic for existing public.inventory rows.
"""

from __future__ import annotations

import argparse
import logging
import os

from sqlalchemy import text
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.services.inventory_axes import log_axis_isolation, project_inventory_axes

logger = logging.getLogger(__name__)


def _iter_inventory_rows(db: Session):
    result = db.execute(text("SELECT id, condition, unit FROM public.inventory ORDER BY id ASC"))
    for row in result.mappings().all():
        yield dict(row)


def backfill_inventory_axes(db: Session, *, dry_run: bool = True) -> list[dict[str, object]]:
    changed: list[dict[str, object]] = []
    for row in _iter_inventory_rows(db):
        projection = project_inventory_axes(row.get("condition"), row.get("unit"))
        log_axis_isolation(
            logger_=logger,
            condition=row.get("condition"),
            unit=row.get("unit"),
            context=f"backfill_inventory_axes.row_id={row.get('id')}",
            projection=projection,
        )
        if projection.isolated:
            continue
        payload = {
            "id": row["id"],
            "seal": projection.seal,
            "search_cond": projection.search_cond,
            "grade": projection.grade,
            "damage": projection.damage if projection.damage is not None else False,
        }
        changed.append(payload)
        if not dry_run:
            db.execute(
                text(
                    """
                    UPDATE public.inventory
                       SET seal = :seal,
                           search_cond = :search_cond,
                           grade = :grade,
                           damage = :damage,
                           updated_at = NOW()
                     WHERE id = :id
                    """
                ),
                payload,
            )
    if not dry_run:
        db.commit()
    return changed


def _build_engine():
    database_url = os.getenv("DATABASE_URL") or os.getenv("TEST_PG_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL or TEST_PG_URL is required")
    return create_engine(database_url, echo=False)


def _main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="perform UPDATEs instead of dry-run")
    args = parser.parse_args()

    engine = _build_engine()
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        with session_factory() as db:
            rows = backfill_inventory_axes(db, dry_run=not args.apply)
            print(f"changed_rows={len(rows)}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _main()
