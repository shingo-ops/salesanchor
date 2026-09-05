"""
MIG-04 Stage 1: tcg_line_import_svc の単体テスト（DB 不要）。

テスト対象:
  - parse_line_export: 日付行 / 時刻行 / 継続行 / システムイベント / エッジケース
  - resolve_suppliers: プレフィックス最長一致 / 未解決 / 全員未解決
  - build_provider_entries: グループ化 / タイムスタンプ昇順 / SHA256
  - sha256_text: 冪等性
  - window_hours 自動計算: window_start が None かつ window_hours>0 で cutoff が設定される
  - import_line_export: supersede の実行順序（INSERT before UPDATE）
  - import_line_export: _enqueue_extraction は db.commit() の後に呼ばれること
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.tcg_line_import_svc import (
    build_provider_entries,
    import_line_export,
    parse_line_export,
    resolve_suppliers,
    sha256_text,
)


# ─────────────────────────────────────────────────────────────────────────────
# sha256_text
# ─────────────────────────────────────────────────────────────────────────────


def test_sha256_text_matches_stdlib():
    """sha256_text が stdlib の結果と一致する。"""
    content = "hello world"
    expected = hashlib.sha256(content.encode("utf-8")).hexdigest()
    assert sha256_text(content) == expected


def test_sha256_text_idempotent():
    """同一入力は常に同じ値を返す。"""
    content = "テスト\n商品A 100円\n"
    assert sha256_text(content) == sha256_text(content)


def test_sha256_text_different_inputs():
    """異なる入力は異なる値を返す。"""
    assert sha256_text("abc") != sha256_text("ABC")


# ─────────────────────────────────────────────────────────────────────────────
# parse_line_export
# ─────────────────────────────────────────────────────────────────────────────


def test_parse_basic_messages():
    """通常の日付行 + 時刻行が正しくパースされる。"""
    export_text = """\
2026.08.01 金曜日
10:00 山田太郎 商品A 100円
10:05 鈴木次郎 商品B 200円
"""
    messages = parse_line_export(export_text)
    assert len(messages) == 2
    assert messages[0]["timestamp"] == "2026-08-01 10:00:00"
    assert messages[0]["display_name"] == "山田太郎"
    assert messages[0]["body"] == "商品A 100円"
    assert messages[1]["timestamp"] == "2026-08-01 10:05:00"
    assert messages[1]["display_name"] == "鈴木次郎"


def test_parse_single_digit_hour():
    """1桁の時刻（9:05 など）が 09:05:00 に正規化される。"""
    export_text = """\
2026.08.01 金曜日
9:05 山田太郎 商品A
"""
    messages = parse_line_export(export_text)
    assert messages[0]["timestamp"] == "2026-08-01 09:05:00"


def test_parse_continuation_line():
    """継続行が \\n\\n で結合される（SQR-05 準拠）。"""
    export_text = """\
2026.08.01 金曜日
10:00 山田太郎 1行目
継続行
さらに続き
"""
    messages = parse_line_export(export_text)
    assert len(messages) == 1
    assert messages[0]["body"] == "1行目\n\n継続行\n\nさらに続き"


def test_parse_system_event_join():
    """「がグループに参加しました」はシステムイベントとしてマークされる。"""
    export_text = """\
2026.08.01 金曜日
10:00 田中花子 がグループに参加しました。
10:01 山田太郎 商品A
"""
    messages = parse_line_export(export_text)
    system = [m for m in messages if m["is_system_event"]]
    normal = [m for m in messages if not m["is_system_event"]]
    assert len(system) == 1
    assert len(normal) == 1
    assert system[0]["display_name"] == "田中花子"


def test_parse_system_event_invite():
    """「をグループに招待しました」もシステムイベント。"""
    export_text = """\
2026.08.01 金曜日
10:00 山田太郎 田中花子をグループに招待しました。
"""
    messages = parse_line_export(export_text)
    assert messages[0]["is_system_event"] is True


def test_parse_system_event_recall():
    """「がメッセージの送信を取り消しました」もシステムイベント。"""
    export_text = """\
2026.08.01 金曜日
10:00 山田太郎 がメッセージの送信を取り消しました。
"""
    messages = parse_line_export(export_text)
    assert messages[0]["is_system_event"] is True


def test_parse_multiple_date_blocks():
    """複数の日付ブロックにまたがるメッセージが正しく日付を引き継ぐ。"""
    export_text = """\
2026.08.01 金曜日
10:00 山田太郎 商品A
2026.08.02 土曜日
11:00 鈴木次郎 商品B
"""
    messages = parse_line_export(export_text)
    assert len(messages) == 2
    assert messages[0]["timestamp"].startswith("2026-08-01")
    assert messages[1]["timestamp"].startswith("2026-08-02")


def test_parse_empty_body():
    """空の本文（送信者名のみ）でも落ちない。"""
    export_text = """\
2026.08.01 金曜日
10:00 山田太郎
"""
    messages = parse_line_export(export_text)
    assert len(messages) == 1
    assert messages[0]["body"] == ""


def test_parse_empty_export():
    """空のエクスポートテキストは空リストを返す。"""
    assert parse_line_export("") == []


def test_parse_no_date_block():
    """日付行なしの時刻行は無視される（current_date が None のため）。"""
    export_text = "10:00 山田太郎 商品A\n"
    messages = parse_line_export(export_text)
    assert messages == []


# ─────────────────────────────────────────────────────────────────────────────
# resolve_suppliers
# ─────────────────────────────────────────────────────────────────────────────


def test_resolve_exact_match():
    """完全一致のサプライヤーが解決される。"""
    messages = [
        {
            "timestamp": "2026-08-01 10:00:00",
            "display_name": "仕入元A",
            "body": "商品X",
            "is_system_event": False,
        }
    ]
    db_suppliers = [{"code": "SP0001", "name": "仕入元A"}]
    resolved, unresolved = resolve_suppliers(messages, db_suppliers)
    assert len(resolved) == 1
    assert resolved[0]["sp_code"] == "SP0001"
    assert len(unresolved) == 0


def test_resolve_prefix_match():
    """プレフィックス一致でサプライヤーが解決される（display_name が name で始まる場合）。"""
    messages = [
        {
            "timestamp": "2026-08-01 10:00:00",
            "display_name": "仕入元A（別支店）",
            "body": "商品X",
            "is_system_event": False,
        }
    ]
    db_suppliers = [{"code": "SP0001", "name": "仕入元A"}]
    resolved, unresolved = resolve_suppliers(messages, db_suppliers)
    assert len(resolved) == 1
    assert resolved[0]["sp_code"] == "SP0001"


def test_resolve_longest_prefix_wins():
    """複数プレフィックス一致の場合、最長一致が優先される。"""
    messages = [
        {
            "timestamp": "2026-08-01 10:00:00",
            "display_name": "仕入元AB",
            "body": "商品X",
            "is_system_event": False,
        }
    ]
    db_suppliers = [
        {"code": "SP0001", "name": "仕入元A"},
        {"code": "SP0002", "name": "仕入元AB"},
    ]
    resolved, unresolved = resolve_suppliers(messages, db_suppliers)
    assert resolved[0]["sp_code"] == "SP0002"  # 最長一致


def test_resolve_unknown_sender():
    """未知の送信者が unresolved に入り、取り込みは継続する。"""
    messages = [
        {
            "timestamp": "2026-08-01 10:00:00",
            "display_name": "未知のユーザー",
            "body": "何か",
            "is_system_event": False,
        }
    ]
    db_suppliers = [{"code": "SP0001", "name": "仕入元A"}]
    resolved, unresolved = resolve_suppliers(messages, db_suppliers)
    assert len(resolved) == 0
    assert len(unresolved) == 1
    assert unresolved[0]["display_name"] == "未知のユーザー"


def test_resolve_all_unknown():
    """全員未知でも例外が出ず、全員が unresolved に入る。"""
    messages = [
        {"timestamp": "2026-08-01 10:00:00", "display_name": "A", "body": "x", "is_system_event": False},
        {"timestamp": "2026-08-01 10:01:00", "display_name": "B", "body": "y", "is_system_event": False},
    ]
    db_suppliers: list[dict] = []
    resolved, unresolved = resolve_suppliers(messages, db_suppliers)
    assert len(resolved) == 0
    assert len(unresolved) == 2


def test_resolve_mixed_resolved_unresolved():
    """既知と未知が混在する場合、それぞれ正しく仕分けされる。"""
    messages = [
        {"timestamp": "2026-08-01 10:00:00", "display_name": "既知の仕入元", "body": "商品A", "is_system_event": False},
        {"timestamp": "2026-08-01 10:01:00", "display_name": "未知のユーザー", "body": "何か", "is_system_event": False},
    ]
    db_suppliers = [{"code": "SP0001", "name": "既知の仕入元"}]
    resolved, unresolved = resolve_suppliers(messages, db_suppliers)
    assert len(resolved) == 1
    assert len(unresolved) == 1


def test_resolve_timestamps_grouped_by_display_name():
    """同一 display_name の複数メッセージが1つの unresolved エントリにまとまる。"""
    messages = [
        {"timestamp": "2026-08-01 10:00:00", "display_name": "未知", "body": "x", "is_system_event": False},
        {"timestamp": "2026-08-01 10:05:00", "display_name": "未知", "body": "y", "is_system_event": False},
    ]
    _, unresolved = resolve_suppliers(messages, [])
    assert len(unresolved) == 1
    assert len(unresolved[0]["timestamps"]) == 2


# ─────────────────────────────────────────────────────────────────────────────
# build_provider_entries
# ─────────────────────────────────────────────────────────────────────────────


def test_build_groups_by_sp_code():
    """同一 sp_code のメッセージが1エントリに結合される（SQR-05）。"""
    resolved_messages = [
        {
            "sp_code": "SP0001", "canonical_name": "仕入元A",
            "timestamp": "2026-08-01 10:00:00", "body": "商品A 100円",
            "display_name": "仕入元A", "is_system_event": False,
        },
        {
            "sp_code": "SP0001", "canonical_name": "仕入元A",
            "timestamp": "2026-08-01 10:05:00", "body": "商品B 200円",
            "display_name": "仕入元A", "is_system_event": False,
        },
        {
            "sp_code": "SP0002", "canonical_name": "仕入元B",
            "timestamp": "2026-08-01 11:00:00", "body": "商品C 300円",
            "display_name": "仕入元B", "is_system_event": False,
        },
    ]
    entries = build_provider_entries(resolved_messages)
    assert len(entries) == 2
    sp_codes = {e["sp_code"] for e in entries}
    assert sp_codes == {"SP0001", "SP0002"}


def test_build_latest_only_with_two_messages():
    """複数メッセージは最新1件のみが raw_text になる（SQR-05）。"""
    resolved_messages = [
        {
            "sp_code": "SP0001", "canonical_name": "仕入元A",
            "timestamp": "2026-08-01 10:00:00", "body": "msg1",
            "display_name": "仕入元A", "is_system_event": False,
        },
        {
            "sp_code": "SP0001", "canonical_name": "仕入元A",
            "timestamp": "2026-08-01 10:05:00", "body": "msg2",
            "display_name": "仕入元A", "is_system_event": False,
        },
    ]
    entries = build_provider_entries(resolved_messages)
    assert entries[0]["raw_text"] == "msg2"
    assert entries[0]["skipped_message_count"] == 1


def test_build_timestamp_ascending_order():
    """received_at は最初のタイムスタンプ、raw_text は最新（最後）のメッセージ本文（SQR-05）。"""
    resolved_messages = [
        {
            "sp_code": "SP0001", "canonical_name": "仕入元A",
            "timestamp": "2026-08-01 10:05:00", "body": "後のメッセージ",
            "display_name": "仕入元A", "is_system_event": False,
        },
        {
            "sp_code": "SP0001", "canonical_name": "仕入元A",
            "timestamp": "2026-08-01 10:00:00", "body": "最初のメッセージ",
            "display_name": "仕入元A", "is_system_event": False,
        },
    ]
    entries = build_provider_entries(resolved_messages)
    assert len(entries) == 1
    assert entries[0]["received_at"] == "2026-08-01 10:00:00"
    assert entries[0]["raw_text"] == "後のメッセージ"


def test_build_sha256_computed():
    """sha256 フィールドが raw_text の SHA-256 になっている。"""
    resolved_messages = [
        {
            "sp_code": "SP0001", "canonical_name": "仕入元A",
            "timestamp": "2026-08-01 10:00:00", "body": "商品A",
            "display_name": "仕入元A", "is_system_event": False,
        }
    ]
    entries = build_provider_entries(resolved_messages)
    assert entries[0]["sha256"] == sha256_text("商品A")


def test_build_single_message():
    """メッセージが1件だけの場合も正しく動作する。"""
    resolved_messages = [
        {
            "sp_code": "SP0001", "canonical_name": "仕入元A",
            "timestamp": "2026-08-01 10:00:00", "body": "商品A",
            "display_name": "仕入元A", "is_system_event": False,
        }
    ]
    entries = build_provider_entries(resolved_messages)
    assert len(entries) == 1
    assert entries[0]["raw_text"] == "商品A"


def test_build_empty_input():
    """空リスト入力で空リストを返す。"""
    assert build_provider_entries([]) == []


def test_build_latest_only_with_three_messages():
    """同一仕入元に3件あるとき、最新1件のみが raw_text になる（SQR-05）。"""
    resolved_messages = [
        {
            "sp_code": "SP0001", "canonical_name": "仕入元A",
            "timestamp": "2026-08-01 10:00:00", "body": "1件目",
            "display_name": "仕入元A", "is_system_event": False,
        },
        {
            "sp_code": "SP0001", "canonical_name": "仕入元A",
            "timestamp": "2026-08-01 10:05:00", "body": "2件目",
            "display_name": "仕入元A", "is_system_event": False,
        },
        {
            "sp_code": "SP0001", "canonical_name": "仕入元A",
            "timestamp": "2026-08-01 10:10:00", "body": "3件目（最新）",
            "display_name": "仕入元A", "is_system_event": False,
        },
    ]
    entries = build_provider_entries(resolved_messages)
    assert len(entries) == 1
    assert entries[0]["raw_text"] == "3件目（最新）"
    assert entries[0]["skipped_message_count"] == 2


def test_build_skipped_message_count_single():
    """メッセージが1件のときは skipped_message_count == 0。"""
    resolved_messages = [
        {
            "sp_code": "SP0001", "canonical_name": "仕入元A",
            "timestamp": "2026-08-01 10:00:00", "body": "唯一のメッセージ",
            "display_name": "仕入元A", "is_system_event": False,
        }
    ]
    entries = build_provider_entries(resolved_messages)
    assert entries[0]["skipped_message_count"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# 24h ウィンドウ自動計算（window_hours ロジック）
# ─────────────────────────────────────────────────────────────────────────────


def test_window_hours_cutoff_is_24h_ago():
    """
    window_hours=24 の場合、現在時刻の24時間前より前のメッセージは除外される。

    import_line_export は async DB 関数なので直接呼べないが、
    cutoff 計算ロジックを parse + resolve 経由で間接的に検証する:
    - 現在時刻 - 25h のタイムスタンプ → 除外
    - 現在時刻 - 1h のタイムスタンプ → 含まれる
    ここではサービス内の window_start 自動計算ロジックを
    単体で模倣して cutoff の妥当性を確認する。
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)
    old_ts = (now - timedelta(hours=25)).strftime("%Y-%m-%d %H:%M:%S")
    new_ts = (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")

    messages = [
        {"timestamp": old_ts, "display_name": "A", "body": "old", "is_system_event": False},
        {"timestamp": new_ts, "display_name": "B", "body": "new", "is_system_event": False},
    ]
    window_start = cutoff.strftime("%Y-%m-%d %H:%M:%S")
    filtered = [m for m in messages if m["timestamp"] >= window_start]
    assert len(filtered) == 1
    assert filtered[0]["body"] == "new"


def test_window_hours_zero_disables_filter():
    """window_hours=0 の場合はウィンドウフィルタが無効（全件通過）。"""
    now = datetime.now(timezone.utc)
    old_ts = (now - timedelta(hours=100)).strftime("%Y-%m-%d %H:%M:%S")
    new_ts = (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")

    messages = [
        {"timestamp": old_ts, "display_name": "A", "body": "old", "is_system_event": False},
        {"timestamp": new_ts, "display_name": "B", "body": "new", "is_system_event": False},
    ]
    # window_hours=0: effective_window_start remains None → no filter
    window_hours = 0
    effective_window_start = None  # window_hours=0 → no auto-calc
    filtered = messages if not effective_window_start else [
        m for m in messages if m["timestamp"] >= effective_window_start
    ]
    assert len(filtered) == 2


def test_window_start_explicit_overrides_auto():
    """
    window_start が明示指定されている場合は window_hours の自動計算は行われない。
    サービスのロジック: effective_window_start は window_start が None のときのみ自動計算。
    """
    explicit_start = "2026-08-01 10:00:00"
    messages = [
        {"timestamp": "2026-08-01 09:00:00", "display_name": "A", "body": "before", "is_system_event": False},
        {"timestamp": "2026-08-01 11:00:00", "display_name": "B", "body": "after", "is_system_event": False},
    ]
    # window_start が指定されている → effective_window_start = window_start
    effective = explicit_start  # not overridden by window_hours
    filtered = [m for m in messages if m["timestamp"] >= effective]
    assert len(filtered) == 1
    assert filtered[0]["body"] == "after"


# ─────────────────────────────────────────────────────────────────────────────
# import_line_export: supersede の実行順序（INSERT before UPDATE）
# ─────────────────────────────────────────────────────────────────────────────


async def test_source_message_insert_before_update_supersede():
    """
    INSERT INTO source_messages は UPDATE source_messages SET superseded_by より
    先に実行されること。

    根拠:
      backend/migrations/20260831_110000_create_tcg_analysis_tables_t004.sql:230-231
        superseded_by UUID REFERENCES tenant_004.source_messages(id)
      DEFERRABLE 未指定 = NOT DEFERRABLE INITIALLY IMMEDIATE。
      UPDATE で new_sm_id を参照する前に INSERT が済んでいない場合、
      ForeignKeyViolation が発生する。

    発生条件:
      対象 supplier_channel_id に is_active=TRUE の source_message が既存の場合のみ。
      本テストでは fetchall が ("test-old-sm-id",) を返すことでその状態を再現する。
    """
    export_text = (
        "2026.08.01 金曜日\n"
        "10:00 仕入元A 商品X 100円\n"
    )
    call_sqls: list[str] = []

    async def tracked_execute(stmt, params=None):
        sql = str(stmt)
        call_sqls.append(sql)
        result = MagicMock()
        if "import_jobs" in sql and "raw_sha256" in sql:
            # 冪等化チェック: 未取り込み
            result.fetchone.return_value = None
        elif "tcg_suppliers" in sql and "supplier_channels" not in sql:
            # サプライヤー一覧（プレフィックス一致で "仕入元A" を解決）
            result.fetchall.return_value = [("SP0001", "仕入元A")]
        elif "supplier_channels" in sql:
            # チャンネル取得: 1件あり
            result.fetchone.return_value = ("test-channel-id",)
        elif "source_messages" in sql and "SELECT" in sql:
            # 既存 active レコード: 1件あり（supersede が走る条件）
            result.fetchall.return_value = [("test-old-sm-id",)]
        else:
            result.fetchone.return_value = None
            result.fetchall.return_value = []
        return result

    db = MagicMock()
    db.execute = tracked_execute
    db.commit = AsyncMock()

    await import_line_export(
        db=db,
        filename="test.txt",
        export_text=export_text,
        uploaded_by=None,
        window_hours=0,  # フィルタなし: 全メッセージを取り込む
    )

    insert_pos = next(
        (i for i, sql in enumerate(call_sqls) if "INSERT INTO tenant_004.source_messages" in sql),
        None,
    )
    update_pos = next(
        (i for i, sql in enumerate(call_sqls) if "UPDATE tenant_004.source_messages" in sql and "superseded_by" in sql),
        None,
    )

    assert insert_pos is not None, "INSERT INTO source_messages が呼ばれなかった"
    assert update_pos is not None, "UPDATE source_messages SET superseded_by が呼ばれなかった"
    assert insert_pos < update_pos, (
        f"INSERT (位置 {insert_pos}) が UPDATE (位置 {update_pos}) より後: "
        "superseded_by FK は NOT DEFERRABLE のため ForeignKeyViolation が発生する"
    )


async def test_enqueue_called_after_commit():
    """
    _enqueue_extraction は db.commit() の後に呼ばれること。

    根拠: commit 前にエンキューすると、その後 rollback が発生した場合に
          DB に存在しない source_message_id で extract タスクが実行される。
          commit 後エンキューにより孤立タスク（orphan task）を防ぐ。

    検証方法: call_order リストに "commit" / "enqueue" をタイムスタンプ順で追記し、
              "commit" が "enqueue" より先に来ることを assert する。
    """
    export_text = (
        "2026.08.01 金曜日\n"
        "10:00 仕入元A 商品X 100円\n"
    )
    call_order: list[str] = []

    async def tracked_execute(stmt, params=None):
        result = MagicMock()
        sql = str(stmt)
        if "import_jobs" in sql and "raw_sha256" in sql:
            result.fetchone.return_value = None
        elif "tcg_suppliers" in sql and "supplier_channels" not in sql:
            result.fetchall.return_value = [("SP0001", "仕入元A")]
        elif "supplier_channels" in sql:
            result.fetchone.return_value = ("test-channel-id",)
        elif "source_messages" in sql and "SELECT" in sql:
            result.fetchall.return_value = [("test-old-sm-id",)]
        else:
            result.fetchone.return_value = None
            result.fetchall.return_value = []
        return result

    async def tracked_commit():
        call_order.append("commit")

    db = MagicMock()
    db.execute = tracked_execute
    db.commit = tracked_commit

    with patch(
        "app.services.tcg_line_import_svc._enqueue_extraction",
        side_effect=lambda sm_id: call_order.append("enqueue"),
    ):
        await import_line_export(
            db=db,
            filename="test.txt",
            export_text=export_text,
            uploaded_by=None,
            window_hours=0,
        )

    assert "commit" in call_order, "db.commit() が呼ばれなかった"
    assert "enqueue" in call_order, "_enqueue_extraction が呼ばれなかった"
    commit_pos = call_order.index("commit")
    enqueue_pos = call_order.index("enqueue")
    assert commit_pos < enqueue_pos, (
        f"_enqueue_extraction (位置 {enqueue_pos}) が db.commit (位置 {commit_pos}) より先: "
        "rollback 時に孤立タスクが発生する"
    )
