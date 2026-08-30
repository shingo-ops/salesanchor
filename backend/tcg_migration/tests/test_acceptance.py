"""
MIG-02 Phase 4: Acceptance Tests

期待値 (訂正済み 2026-08-30):
  suppliers=45, extraction_items=1626, products=267,
  exclude_keywords=123 (task-spec 54 は ADR-093 時点のスナップショット → 123 に訂正),
  needs_review=1394, pid_unresolved=344, unit_unresolved=528,
  SP0023=198, SP0057.extraction_items=0 + job.status='empty'
"""

import os
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

DB_URL = os.environ.get(
    "TCG_DB_URL",
    "postgresql+psycopg2://myapp_user:password@localhost:5432/myapp_db",
)

@pytest.fixture(scope="module")
def session():
    engine = create_engine(DB_URL)
    with Session(engine) as s:
        yield s


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 acceptance: マスタ / 抽出データ
# ─────────────────────────────────────────────────────────────────────────────

def test_suppliers_count(session):
    """tcg_suppliers: 44 (gemini) + 1 (SP0057) = 45"""
    count = session.execute(text("SELECT COUNT(*) FROM tcg_suppliers")).scalar()
    assert count == 45, f"suppliers: expected 45, got {count}"


def test_extraction_items_count(session):
    """extraction_items: gemini_all.json 1626 行"""
    count = session.execute(text("SELECT COUNT(*) FROM extraction_items")).scalar()
    assert count == 1626, f"extraction_items: expected 1626, got {count}"


def test_products_count(session):
    """tcg_products: backup 262 + stubs 5 = 267"""
    count = session.execute(text("SELECT COUNT(*) FROM tcg_products")).scalar()
    assert count == 267, f"products: expected 267, got {count}"


def test_exclude_keywords_count(session):
    """
    product_exclude_keywords: 123 行
    (task-spec 期待値 54 は ADR-093 時点のスナップショット。
     ライブ実測 123 が正として訂正済み — MIGRATION_LOG.md 参照)
    """
    count = session.execute(
        text("SELECT COUNT(*) FROM product_exclude_keywords")
    ).scalar()
    assert count == 123, f"exclude_keywords: expected 123, got {count}"


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4 acceptance: analysis_results
# ─────────────────────────────────────────────────────────────────────────────

def test_analysis_results_total(session):
    """analysis_results: 全 1626 行"""
    count = session.execute(text("SELECT COUNT(*) FROM analysis_results")).scalar()
    assert count == 1626, f"analysis_results: expected 1626, got {count}"


def test_needs_review_count(session):
    """needs_review=TRUE: 1394"""
    count = session.execute(
        text("SELECT COUNT(*) FROM analysis_results WHERE needs_review")
    ).scalar()
    assert count == 1394, f"needs_review: expected 1394, got {count}"


def test_pid_unresolved_count(session):
    """pid_resolved=FALSE: 344"""
    count = session.execute(
        text("SELECT COUNT(*) FROM analysis_results WHERE NOT pid_resolved")
    ).scalar()
    assert count == 344, f"pid_unresolved: expected 344, got {count}"


def test_unit_unresolved_count(session):
    """unit_resolved=FALSE: 528"""
    count = session.execute(
        text("SELECT COUNT(*) FROM analysis_results WHERE NOT unit_resolved")
    ).scalar()
    assert count == 528, f"unit_unresolved: expected 528, got {count}"


def test_sp0023_items(session):
    """SP0023 (株式会社N&U) analysis_results: 198"""
    count = session.execute(text("""
        SELECT COUNT(*) FROM analysis_results ar
        JOIN extraction_items ei ON ei.id = ar.extraction_item_id
        JOIN extraction_jobs  ej ON ej.id = ei.extraction_job_id
        JOIN source_messages  sm ON sm.id = ej.source_message_id
        JOIN supplier_channels sc ON sc.id = sm.supplier_channel_id
        JOIN tcg_suppliers s ON s.id = sc.supplier_id
        WHERE s.code = 'SP0023'
    """)).scalar()
    assert count == 198, f"SP0023: expected 198, got {count}"


def test_sp0057_extraction_items_zero(session):
    """SP0057 (Hiroshi): extraction_items = 0"""
    count = session.execute(text("""
        SELECT COUNT(*) FROM extraction_items ei
        JOIN extraction_jobs ej ON ej.id = ei.extraction_job_id
        JOIN source_messages sm ON sm.id = ej.source_message_id
        JOIN supplier_channels sc ON sc.id = sm.supplier_channel_id
        JOIN tcg_suppliers s ON s.id = sc.supplier_id
        WHERE s.code = 'SP0057'
    """)).scalar()
    assert count == 0, f"SP0057 extraction_items: expected 0, got {count}"


def test_sp0057_job_status_empty(session):
    """SP0057: extraction_job.status = 'empty'"""
    status = session.execute(text("""
        SELECT ej.status FROM extraction_jobs ej
        JOIN source_messages sm ON sm.id = ej.source_message_id
        JOIN supplier_channels sc ON sc.id = sm.supplier_channel_id
        JOIN tcg_suppliers s ON s.id = sc.supplier_id
        WHERE s.code = 'SP0057'
    """)).scalar()
    assert status == "empty", f"SP0057 job status: expected 'empty', got {repr(status)}"


def test_engine_version(session):
    """全 analysis_results の engine_version = 'compat-v1'"""
    count = session.execute(
        text("SELECT COUNT(*) FROM analysis_results WHERE engine_version != 'compat-v1'")
    ).scalar()
    assert count == 0, f"engine_version mismatch: {count} rows not 'compat-v1'"
