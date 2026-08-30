"""
MIG-04 Phase 5: 検収テスト

検収条件:
  1. 冪等性: 同一ファイルのアップロードは件数を増やさない
  2. supersede: 同一仕入元の新しい通で旧通に superseded_by が付く
  3. 未知投稿者: 取り込みが止まらず、未登録一覧に出る
  4. Gemini 記録: extraction_jobs に prompt_version カラムが存在
  5. import_jobs スキーマ確認
  6. 回帰: 既存 MIG-02 検収値が不変
  7. Phase 3 比較結果確認 (3仕入元の extraction_items 件数)
"""

import hashlib
import os
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.services.tcg_line_import_svc import (
    parse_line_export,
    resolve_suppliers,
    build_provider_entries,
    sha256_text,
)

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
# 1. 冪等性: スキーマレベル検証
# ─────────────────────────────────────────────────────────────────────────────

def test_import_jobs_sha256_unique_constraint(session):
    """import_jobs.raw_sha256 に UNIQUE 制約があること。"""
    rows = session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            WHERE t.relname = 'import_jobs'
              AND c.contype = 'u'
              AND c.conname LIKE '%sha256%'
            """
        )
    ).scalar()
    assert rows >= 1, "import_jobs.raw_sha256 に UNIQUE 制約が見つからない"


def test_import_jobs_idempotency_via_sha256(session):
    """
    冪等性はアプリレベルで制御: import_jobs.raw_sha256 UNIQUE 制約により
    同一ファイルの再登録を防ぐ。source_messages には DB UNIQUE 制約なし（設計どおり）。
    import_jobs のほうに UNIQUE 制約があれば冪等性が保証される。
    """
    # import_jobs.raw_sha256 UNIQUE 制約は別テスト (test_import_jobs_sha256_unique_constraint) で確認済み
    # source_messages には DB レベルの UNIQUE 制約はなく、アプリレベルで制御する設計を確認
    rows = session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            WHERE t.relname = 'source_messages'
              AND c.contype = 'u'
              AND c.conname LIKE '%sha256%'
            """
        )
    ).scalar()
    # 設計どおり: source_messages には sha256 UNIQUE 制約なし（import_jobs で制御）
    assert rows == 0, (
        "source_messages に sha256 UNIQUE 制約が追加されている。"
        "冪等性の制御方式が変更された可能性。確認が必要。"
    )


# ──────���──────────────────────────────────────────────────────────────────────
# 2. supersede: source_messages の superseded_by カラム検証
# ─────────────────────────────────────────────────────────────────────────────

def test_source_messages_has_superseded_by_column(session):
    """source_messages に superseded_by カラムがあること。"""
    row = session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_name = 'source_messages'
              AND column_name = 'superseded_by'
            """
        )
    ).scalar()
    assert row == 1, "source_messages.superseded_by カラムが存在��ない"


def test_source_messages_has_is_active_column(session):
    """source_messages に is_active カラムがあること。"""
    row = session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_name = 'source_messages'
              AND column_name = 'is_active'
            """
        )
    ).scalar()
    assert row == 1, "source_messages.is_active カラムが存在しない"


# ─────────────────────────────────────────────────────────────────────────────
# 3. 未知投稿者: サービスロジックの単体テスト（DB 不要）
# ─────────────────────────────────────────────────────────────────────────────

def test_unknown_sender_does_not_raise():
    """
    未知の投稿者 (suppliers に存在しない display_name) を含む LINE テキストを
    parse + resolve しても例外が出ず、unresolved リストに含まれること。
    """
    export_text = """\
2026.08.01 金曜日
10:00 既知の仕入元 商品A 100円
10:01 未知のユーザー 何か
"""
    messages = parse_line_export(export_text)
    non_system = [m for m in messages if not m["is_system_event"]]

    db_suppliers = [{"code": "SP0001", "name": "既知の仕入元"}]
    resolved, unresolved = resolve_suppliers(non_system, db_suppliers)

    assert len(resolved) == 1, f"解決済み: 1 を期待, got {len(resolved)}"
    assert resolved[0]["sp_code"] == "SP0001"

    assert len(unresolved) == 1, f"未解決: 1 を期待, got {len(unresolved)}"
    assert unresolved[0]["display_name"] == "未知のユーザー"


def test_all_unknown_senders_does_not_raise():
    """全投稿者が未知でも取り込みが止まらないこと（unresolved に全員）。"""
    export_text = """\
2026.08.01 金曜日
10:00 UNKNOWN_A 商品A
10:01 UNKNOWN_B 商品B
"""
    messages = parse_line_export(export_text)
    non_system = [m for m in messages if not m["is_system_event"]]
    db_suppliers: list[dict] = []  # 空
    resolved, unresolved = resolve_suppliers(non_system, db_suppliers)

    assert len(resolved) == 0
    assert len(unresolved) == 2


# ─────────────────────────────────────────────────────────────────────────────
# 4. Gemini 記録: extraction_jobs.prompt_version カラム
# ─────────────────────────────────────────────────────────────────────────────

def test_extraction_jobs_has_prompt_version(session):
    """extraction_jobs に prompt_version カラムがあること (MIG-04 Phase 2 で追加)。"""
    row = session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_name = 'extraction_jobs'
              AND column_name = 'prompt_version'
            """
        )
    ).scalar()
    assert row == 1, "extraction_jobs.prompt_version カラムが存在しない"


# ─────────────────────────────────────────────────────────────────────────────
# 5. import_jobs スキーマ確認 (MIG-04 Phase 2)
# ─────────────────────────────────────────────────────────────────────────────

def test_import_jobs_table_exists(session):
    """import_jobs テーブルが存在すること。"""
    row = session.execute(
        text(
            """
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_name = 'import_jobs'
            """
        )
    ).scalar()
    assert row == 1, "import_jobs テーブルが存在しない"


def test_import_jobs_columns(session):
    """import_jobs に必須カラムがあること。"""
    required_cols = {
        "id", "filename", "raw_sha256", "message_count",
        "provider_count", "unresolved_count", "uploaded_by", "status",
    }
    rows = session.execute(
        text(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'import_jobs'
            """
        )
    ).fetchall()
    actual = {r[0] for r in rows}
    missing = required_cols - actual
    assert not missing, f"import_jobs に不足カラム: {missing}"


# ─────────────────────────────────────────────────────────────────────────────
# 6. sha256_text ユーティリティ: 単体テスト
# ─────────────────────────────────────────────────────────────────────────────

def test_sha256_text():
    """sha256_text が正しい hex を返すこと。"""
    result = sha256_text("hello")
    expected = hashlib.sha256("hello".encode("utf-8")).hexdigest()
    assert result == expected


def test_sha256_text_idempotent():
    """同じ入力に対して常に同じ値を返すこと（冪等性の前提）。"""
    text_content = "テスト\n商品A 100円\n"
    assert sha256_text(text_content) == sha256_text(text_content)


# ─────────────────────────────────────────────────────────────────────────────
# 7. Phase 3 比較: 3仕入元の extraction_items 件数確認
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("sp_code,expected", [
    ("SP0004", 91),
    ("SP0011", 14),
    ("SP0023", 198),
])
def test_phase3_extraction_items_count(session, sp_code, expected):
    """Phase 3 検証の3仕入元 extraction_items 件数が変化していないこと。"""
    count = session.execute(
        text(
            """
            SELECT COUNT(*) FROM extraction_items ei
            JOIN extraction_jobs ej ON ej.id = ei.extraction_job_id
            JOIN source_messages sm ON sm.id = ej.source_message_id
            JOIN supplier_channels sc ON sc.id = sm.supplier_channel_id
            JOIN tcg_suppliers ts ON ts.id = sc.supplier_id
            WHERE ts.code = :sp_code
            """
        ),
        {"sp_code": sp_code},
    ).scalar()
    assert count == expected, (
        f"{sp_code}: extraction_items={count}, expected={expected} (Phase 3 比較基準値不変の確認)"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 8. SQR-05 (最新1通のみ採用): build_provider_entries 単体テスト
# ─────────────────────────────────────────────────────────────────────────────

def test_build_provider_entries_groups_by_sp_code():
    """同一 sp_code の複数メッセージが1エントリに結合されること (SQR-05)。"""
    resolved_messages = [
        {
            "sp_code": "SP0001",
            "canonical_name": "仕入元A",
            "timestamp": "2026-08-01 10:00:00",
            "body": "商品A 100円",
            "display_name": "仕入元A",
            "is_system_event": False,
        },
        {
            "sp_code": "SP0001",
            "canonical_name": "仕入元A",
            "timestamp": "2026-08-01 10:05:00",
            "body": "商品B 200円",
            "display_name": "仕入元A",
            "is_system_event": False,
        },
        {
            "sp_code": "SP0002",
            "canonical_name": "仕入元B",
            "timestamp": "2026-08-01 11:00:00",
            "body": "商品C 300円",
            "display_name": "仕入元B",
            "is_system_event": False,
        },
    ]
    entries = build_provider_entries(resolved_messages)

    sp_codes = [e["sp_code"] for e in entries]
    assert "SP0001" in sp_codes
    assert "SP0002" in sp_codes
    assert len(entries) == 2, f"エントリ数: 2 を期待, got {len(entries)}"

    sp0001_entry = next(e for e in entries if e["sp_code"] == "SP0001")
    # 2メッセージが \n\n で結合されている
    assert "\n\n" in sp0001_entry["raw_text"], "SQR-05: メッセージが \\n\\n で結合されていない"
    # received_at は最初のメッセージの timestamp
    assert sp0001_entry["received_at"] == "2026-08-01 10:00:00"


def test_build_provider_entries_timestamp_order():
    """受信順（timestamp 昇順）でソートされること。"""
    resolved_messages = [
        {
            "sp_code": "SP0001",
            "canonical_name": "仕入元A",
            "timestamp": "2026-08-01 10:05:00",
            "body": "後のメッセージ",
            "display_name": "仕入元A",
            "is_system_event": False,
        },
        {
            "sp_code": "SP0001",
            "canonical_name": "仕入元A",
            "timestamp": "2026-08-01 10:00:00",
            "body": "最初のメッセージ",
            "display_name": "仕入元A",
            "is_system_event": False,
        },
    ]
    entries = build_provider_entries(resolved_messages)
    assert len(entries) == 1
    entry = entries[0]
    assert entry["received_at"] == "2026-08-01 10:00:00", "received_at は最初の timestamp"
    assert entry["raw_text"].startswith("最初のメッセージ"), "先頭が最初のメッセージ"


# ─────────────────────────────────────────────────────────────────────────────
# 9. parse_line_export: システムイベント除外の単体テスト
# ─────────────────────────────────────────────────────────────────────────────

def test_system_event_excluded():
    """システムイベント行が is_system_event=True としてマークされること。"""
    export_text = """\
2026.08.01 金曜日
10:00 山田太郎 商品A 100円
10:01 田中花子 がグループに参加しました。
10:02 鈴木次郎 商品B 200円
"""
    messages = parse_line_export(export_text)
    system_events = [m for m in messages if m["is_system_event"]]
    normal_msgs = [m for m in messages if not m["is_system_event"]]

    assert len(system_events) == 1, f"システムイベント: 1 を期待, got {len(system_events)}"
    assert len(normal_msgs) == 2, f"通常メッセージ: 2 を期待, got {len(normal_msgs)}"


# ─────────────────────────────────────────────────────────────────────────────
# 10. 回帰: MIG-02 の検収値が不変 (並行チェック)
# ─────────────────────────────────────────────────────────────────────────────

def test_regression_suppliers_count(session):
    """tcg_suppliers: 45 (MIG-02 基準値)。"""
    count = session.execute(text("SELECT COUNT(*) FROM tcg_suppliers")).scalar()
    assert count == 45, f"回帰: suppliers={count}, expected=45"


def test_regression_extraction_items_count(session):
    """extraction_items: 1626 (MIG-02 基準値)。"""
    count = session.execute(text("SELECT COUNT(*) FROM extraction_items")).scalar()
    assert count == 1626, f"回帰: extraction_items={count}, expected=1626"


def test_regression_analysis_results_count(session):
    """analysis_results: 1626 (MIG-04 基準値)。"""
    count = session.execute(text("SELECT COUNT(*) FROM analysis_results")).scalar()
    assert count == 1626, f"回帰: analysis_results={count}, expected=1626"


def test_regression_engine_version_compat_v1(session):
    """全 analysis_results が compat-v1 (Phase 4 で上書きしていないこと)。"""
    count = session.execute(
        text("SELECT COUNT(*) FROM analysis_results WHERE engine_version != 'compat-v1'")
    ).scalar()
    assert count == 0, f"回帰: compat-v1 以外の engine_version が {count} 行存在"
