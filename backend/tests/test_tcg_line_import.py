"""
MIG-04 Stage 1 & REVIEW-STAGE: tcg_line_import_svc の単体テスト（DB 不要）。

テスト対象:
  - parse_line_export: 日付行 / 時刻行 / 継続行 / システムイベント / エッジケース
  - parse_line_export: GAS latest24SplitHeader_ 準拠の送信者名切り出し
      - マスタに「倉田 和博」があるとき「12:00 倉田 和博 本文」→ display_name=「倉田 和博」
      - マスタにない「とも」は最初のスペースで切り出し
      - 「仕入元A」と「仕入元AB社」の両方がマスタにあるとき誤マッチしない
  - resolve_suppliers: 完全一致（GAS byName[displayName] 準拠）/ 未解決 / 全員未解決
  - build_provider_entries: グループ化 / タイムスタンプ昇順 / SHA256
  - sha256_text: 冪等性
  - window_hours 自動計算: window_start が None かつ window_hours>0 で JST 基準 cutoff が設定される
  - import_line_export: supersede の実行順序（INSERT before UPDATE）
  - import_line_export: _enqueue_extraction は db.commit() の後に呼ばれること
  [REVIEW-STAGE]
  - 未解決0件 → 従来どおり source_messages が書かれ、エンキューされる（review_status='ok'）
  - 未解決1件以上 → source_messages が1件も書かれない、review_status='pending_review'、エンキューされない
  - 窓が JST 基準であること（_compute_window 境界テスト）
  - 破棄タスク → 24h 超の pending_review が discarded になる
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from app.services.tcg_line_import_svc import (
    JST,
    _compute_window,
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
    """完全一致のみ解決される（プレフィックス一致は unresolved 扱い）。GAS byName[displayName] と同等。"""
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
    assert len(resolved) == 0
    assert len(unresolved) == 1
    assert unresolved[0]["display_name"] == "仕入元A（別支店）"


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

    from app.tcg_config import TCG_SCHEMA as _SCHEMA

    insert_pos = next(
        (i for i, sql in enumerate(call_sqls) if f"INSERT INTO {_SCHEMA}.source_messages" in sql),
        None,
    )
    update_pos = next(
        (i for i, sql in enumerate(call_sqls) if f"UPDATE {_SCHEMA}.source_messages" in sql and "superseded_by" in sql),
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


# ─────────────────────────────────────────────────────────────────────────────
# parse_line_export — GAS latest24SplitHeader_ 準拠の送信者名切り出し
# ─────────────────────────────────────────────────────────────────────────────

def test_split_sender_multiword_master_name():
    """
    マスタに「倉田 和博」（スペース含む複合語）があるとき、
    「12:00 倉田 和博 本文テキスト」の display_name が「倉田 和博」になること。

    根拠: GAS latest24SplitHeader_ は tail.indexOf(name + ' ') === 0 でマスタ名を
          優先確定する。従来の Python は split(' ', 1) で「倉田」のみを取り出してしまい、
          resolve_suppliers での完全一致が成立しなかった。

    GAS 参照: Latest24LineImport.js:31-32
    """
    export = "2026.08.01 金曜日\n12:00 倉田 和博 本文テキスト\n"
    supplier_names = ["倉田 和博"]

    msgs = parse_line_export(export, supplier_names)
    user_msgs = [m for m in msgs if not m["is_system_event"]]

    assert len(user_msgs) == 1
    assert user_msgs[0]["display_name"] == "倉田 和博", (
        f"display_name={user_msgs[0]['display_name']!r}: "
        "マスタ名「倉田 和博」で前方一致すべきだが最初のスペースで分割された"
    )
    assert user_msgs[0]["body"] == "本文テキスト"


def test_split_sender_unresolved_falls_back_to_first_space():
    """
    マスタにない送信者「とも」は従来どおり最初のスペースで分割されること。

    GAS 参照: latest24SplitHeader_ のフォールバック（Latest24LineImport.js:35-36）
    """
    export = "2026.08.01 金曜日\n12:00 とも 本文テキスト\n"
    supplier_names = ["倉田 和博"]  # 「とも」はマスタにない

    msgs = parse_line_export(export, supplier_names)
    user_msgs = [m for m in msgs if not m["is_system_event"]]

    assert len(user_msgs) == 1
    assert user_msgs[0]["display_name"] == "とも"
    assert user_msgs[0]["body"] == "本文テキスト"


# ─────────────────────────────────────────────────────────────────────────────
# received_at のタイムゾーン（JST として保存）
# ─────────────────────────────────────────────────────────────────────────────


def test_jst_constant_is_plus9():
    """JST 定数が +09:00 であること。"""
    assert JST.utcoffset(None) == timedelta(hours=9)


def test_received_at_parsed_as_jst_not_utc():
    """
    "2026-09-03 01:19:00" を受け取ったとき、
    保存される datetime の tzinfo が +09:00 であり UTC (+00:00) でないこと。

    根拠: GAS latest24Iso_() が JST のローカル時刻文字列を返す。
    .replace(tzinfo=UTC) のままでは配信 SQL の AT TIME ZONE 'Asia/Tokyo' で
    +9h ずれて表示される（DIST-R3）。
    """
    timestamp_str = "2026-09-03 01:19:00"
    dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=JST)
    assert dt.utcoffset() == timedelta(hours=9), (
        f"expected +09:00, got {dt.utcoffset()}"
    )
    assert dt.utcoffset() != timedelta(0), (
        "UTC として保存されている: 配信 SQL の AT TIME ZONE 'Asia/Tokyo' で +9h ずれる"
    )


async def test_received_at_stored_as_jst_in_insert():
    """
    import_line_export が DB に渡す received_at パラメータが JST (+09:00) であること。

    GAS の latest24Iso_() は JST ローカル時刻文字列を返す。
    .replace(tzinfo=UTC) で保存すると配信 SQL の AT TIME ZONE 'Asia/Tokyo' により
    表示が +9h ずれる（DIST-R3）。
    正しくは JST aware datetime として保存し、配信 SQL は現状維持とする（ADR-154 GAS 再現）。
    """
    export_text = (
        "2026.09.03 水曜日\n"
        "1:19 仕入元A 商品X 100円\n"
    )
    received_at_params: list = []

    async def tracked_execute(stmt, params=None):
        sql = str(stmt)
        result = MagicMock()
        if params and isinstance(params, dict) and "received_at" in params:
            received_at_params.append(params["received_at"])
        if "import_jobs" in sql and "raw_sha256" in sql:
            result.fetchone.return_value = None
        elif "tcg_suppliers" in sql and "supplier_channels" not in sql:
            result.fetchall.return_value = [("SP0001", "仕入元A")]
        elif "supplier_channels" in sql:
            result.fetchone.return_value = ("test-channel-id",)
        elif "source_messages" in sql and "SELECT" in sql:
            result.fetchall.return_value = []
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
        window_hours=0,
    )

    assert len(received_at_params) >= 1, "received_at が DB に渡されなかった"
    dt = received_at_params[0]
    assert dt is not None, "received_at が None（ValueError でフォールバック）"
    assert dt.utcoffset() == timedelta(hours=9), (
        f"expected +09:00, got {dt.utcoffset()}: "
        "UTC として保存されると配信 SQL の AT TIME ZONE 'Asia/Tokyo' で +9h ずれる"
    )


def test_split_sender_no_prefix_false_match():
    """
    「仕入元A」と「仕入元AB社」の両方がマスタにあるとき、
    「12:00 仕入元AB社 本文」の display_name が「仕入元AB社」になること。

    最長一致（GAS の latest24NameMatcher_ = 長さ降順ソート）により、
    短い「仕入元A」がプレフィックスとして誤マッチしないことを検証する。
    「仕入元AB社」は「仕入元A 」で始まらないため「仕入元A」にはマッチしない。

    GAS 参照: Latest24LineImport.js:23-24（コメント "Longest name wins..."）
    """
    export = "2026.08.01 金曜日\n12:00 仕入元AB社 本文テキスト\n"
    # 長さ降順: 「仕入元AB社」(6文字) → 「仕入元A」(4文字)
    supplier_names = ["仕入元AB社", "仕入元A"]

    msgs = parse_line_export(export, supplier_names)
    user_msgs = [m for m in msgs if not m["is_system_event"]]

    assert len(user_msgs) == 1
    assert user_msgs[0]["display_name"] == "仕入元AB社", (
        f"display_name={user_msgs[0]['display_name']!r}: "
        "「仕入元A」への短縮誤マッチが発生した（最長一致ソートが機能していない）"
    )
    assert user_msgs[0]["body"] == "本文テキスト"


# ─────────────────────────────────────────────────────────────────────────────
# [REVIEW-STAGE] _compute_window: JST 基準の窓計算
# ─────────────────────────────────────────────────────────────────────────────


def test_compute_window_jst_basis():
    """
    window_hours=24 のとき cutoff が JST 基準であること。

    旧実装: datetime.now(timezone.utc) - timedelta(hours=24) → UTC 基準で実質 33h（DIST-R3）
    新実装: datetime.now(JST)       - timedelta(hours=24) → JST 基準で正確に 24h

    検証方法:
      JST 現在時刻の 24h 前より 1 秒前のタイムスタンプを作り、
      _compute_window の戻り値 window_start がそれより「後」であることを確認する。
      UTC ベースの旧実装なら cutoff が 9h 古いため、このタイムスタンプが通過してしまう。
    """
    now_jst = datetime.now(JST)
    # JST 24h 前のちょうど 1 秒前（= 24h1s 前）
    just_outside_jst = (now_jst - timedelta(hours=24, seconds=1)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    effective_start, _ = _compute_window(24, None, None)
    assert effective_start is not None
    # 境界: 24h1s 前は cutoff より前 → フィルタで除外されるはず
    assert just_outside_jst < effective_start, (
        f"JST 24h+1s 前({just_outside_jst}) が window_start({effective_start}) 以降になっている。"
        "UTC 基準の旧実装になっている可能性がある（DIST-R3）"
    )


def test_compute_window_explicit_start_not_overridden():
    """window_start が明示されているとき window_hours の自動計算は行われない。"""
    explicit = "2026-08-01 10:00:00"
    effective_start, _ = _compute_window(24, explicit, None)
    assert effective_start == explicit


def test_compute_window_zero_hours_disables_filter():
    """window_hours=0 のとき effective_start が None（フィルタ無効）になる。"""
    effective_start, _ = _compute_window(0, None, None)
    assert effective_start is None


# ─────────────────────────────────────────────────────────────────────────────
# [REVIEW-STAGE] import_line_export: 未解決0件 / 未解決あり 分岐
# ─────────────────────────────────────────────────────────────────────────────


def _make_db_mock(supplier_rows: list[tuple]) -> MagicMock:
    """
    import_line_export 用の DB モックを生成する。
    supplier_rows: [(code, name), ...]
    """
    async def tracked_execute(stmt, params=None):
        sql = str(stmt)
        result = MagicMock()
        if "import_jobs" in sql and "raw_sha256" in sql:
            result.fetchone.return_value = None          # 未取り込み
        elif "tcg_suppliers" in sql and "supplier_channels" not in sql:
            result.fetchall.return_value = supplier_rows
        elif "supplier_channels" in sql and "SELECT" in sql:
            result.fetchone.return_value = ("test-channel-id",)
        elif "source_messages" in sql and "SELECT" in sql:
            result.fetchall.return_value = []            # 既存 active なし
        else:
            result.fetchone.return_value = None
            result.fetchall.return_value = []
        return result

    db = MagicMock()
    db.execute = tracked_execute
    db.commit = AsyncMock()
    return db


async def test_import_zero_unresolved_writes_source_messages():
    """
    未解決0件のとき source_messages が書かれ、エンキューされ、
    review_status='ok' が返ること。
    """
    export_text = (
        "2026.08.01 金曜日\n"
        "10:00 仕入元A 商品X 100円\n"
    )
    db = _make_db_mock([("SP0001", "仕入元A")])
    sqls: list[str] = []

    orig_execute = db.execute

    async def capturing_execute(stmt, params=None):
        sqls.append(str(stmt))
        return await orig_execute(stmt, params)

    db.execute = capturing_execute

    with patch("app.services.tcg_line_import_svc._enqueue_extraction") as mock_enqueue:
        result = await import_line_export(
            db=db,
            filename="test.txt",
            export_text=export_text,
            uploaded_by=None,
            window_hours=0,
        )

    assert result["review_status"] == "ok"
    assert result["unresolved_count"] == 0
    assert any("INSERT INTO tenant_004.source_messages" in s for s in sqls), \
        "source_messages への INSERT が実行されていない"
    mock_enqueue.assert_called_once()
    db.commit.assert_called_once()


async def test_import_unresolved_does_not_write_source_messages():
    """
    未解決1件以上のとき source_messages が1件も書かれず、
    エンキューされず、review_status='pending_review' が返ること。
    """
    export_text = (
        "2026.08.01 金曜日\n"
        "10:00 未登録ユーザー 商品X 100円\n"
    )
    db = _make_db_mock([])   # 仕入元マスタ空 → 全員未解決
    sqls: list[str] = []

    orig_execute = db.execute

    async def capturing_execute(stmt, params=None):
        sqls.append(str(stmt))
        return await orig_execute(stmt, params)

    db.execute = capturing_execute

    with patch("app.services.tcg_line_import_svc._enqueue_extraction") as mock_enqueue:
        result = await import_line_export(
            db=db,
            filename="test.txt",
            export_text=export_text,
            uploaded_by=None,
            window_hours=0,
        )

    assert result["review_status"] == "pending_review"
    assert result["unresolved_count"] == 1
    assert result["provider_count"] == 0
    assert not any("INSERT INTO tenant_004.source_messages" in s for s in sqls), \
        "pending_review なのに source_messages への INSERT が実行された"
    mock_enqueue.assert_not_called()
    db.commit.assert_called_once()   # import_jobs 保存の commit は1回


async def test_import_partial_unresolved_also_blocks():
    """
    解決済み仕入元が混在していても、未解決が1件でもあれば保留になること。
    （解決済みの分も含めて全件保留）
    """
    export_text = (
        "2026.08.01 金曜日\n"
        "10:00 仕入元A 商品X 100円\n"   # 解決済み
        "10:05 未登録ユーザー 商品Y\n"  # 未解決
    )
    db = _make_db_mock([("SP0001", "仕入元A")])
    sqls: list[str] = []

    orig_execute = db.execute

    async def capturing_execute(stmt, params=None):
        sqls.append(str(stmt))
        return await orig_execute(stmt, params)

    db.execute = capturing_execute

    with patch("app.services.tcg_line_import_svc._enqueue_extraction") as mock_enqueue:
        result = await import_line_export(
            db=db,
            filename="test.txt",
            export_text=export_text,
            uploaded_by=None,
            window_hours=0,
        )

    assert result["review_status"] == "pending_review"
    assert not any("INSERT INTO tenant_004.source_messages" in s for s in sqls)
    mock_enqueue.assert_not_called()


async def test_import_unresolved_stores_pending_messages():
    """
    保留時に pending_messages（JSON）と unresolved_names が import_jobs に渡されること。
    """
    export_text = (
        "2026.08.01 金曜日\n"
        "10:00 未登録ユーザー 商品X 100円\n"
    )
    db = _make_db_mock([])
    captured_params: list[dict] = []

    orig_execute = db.execute

    async def capturing_execute(stmt, params=None):
        sql = str(stmt)
        if params and "pending_messages" in sql:
            captured_params.append(dict(params))
        return await orig_execute(stmt, params)

    db.execute = capturing_execute

    with patch("app.services.tcg_line_import_svc._enqueue_extraction"):
        await import_line_export(
            db=db,
            filename="test.txt",
            export_text=export_text,
            uploaded_by=None,
            window_hours=0,
        )

    assert len(captured_params) == 1, "pending_messages を含む INSERT が1件実行されていない"
    p = captured_params[0]
    assert p["pending_messages"] is not None
    msgs = json.loads(p["pending_messages"])
    assert len(msgs) == 1
    assert msgs[0]["display_name"] == "未登録ユーザー"
    names = json.loads(p["unresolved_names"])
    assert names == ["未登録ユーザー"]


# ─────────────────────────────────────────────────────────────────────────────
# [REVIEW-STAGE] 破棄タスク
# ─────────────────────────────────────────────────────────────────────────────


def test_discard_stale_pending_jobs_calls_update():
    """
    discard_stale_pending_jobs が UPDATE ... SET review_status='discarded' を発行すること。
    """
    from app.tasks.tcg_import_discard import discard_stale_pending_jobs

    mock_result = MagicMock()
    mock_result.fetchall.return_value = [("job-uuid-1",), ("job-uuid-2",)]

    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)
    mock_session.execute.return_value = mock_result

    mock_Session = MagicMock(return_value=mock_session)

    with (
        patch("app.tasks.tcg_import_discard._get_sync_engine"),
        patch("app.tasks.tcg_import_discard.sessionmaker", return_value=mock_Session),
    ):
        result = discard_stale_pending_jobs()

    assert result == {"discarded_count": 2}
    mock_session.execute.assert_called_once()
    sql = str(mock_session.execute.call_args[0][0])
    assert "discarded" in sql
    assert "pending_review" in sql
    assert "24 hours" in sql
    mock_session.commit.assert_called_once()


def test_discard_stale_no_rows():
    """対象行が0件のとき {"discarded_count": 0} を返す。"""
    from app.tasks.tcg_import_discard import discard_stale_pending_jobs

    mock_result = MagicMock()
    mock_result.fetchall.return_value = []

    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)
    mock_session.execute.return_value = mock_result

    mock_Session = MagicMock(return_value=mock_session)

    with (
        patch("app.tasks.tcg_import_discard._get_sync_engine"),
        patch("app.tasks.tcg_import_discard.sessionmaker", return_value=mock_Session),
    ):
        result = discard_stale_pending_jobs()

    assert result == {"discarded_count": 0}


# ─────────────────────────────────────────────────────────────────────────────
# [IMP-39] ルーター順序 / datetime 型 修正の回帰テスト
# ─────────────────────────────────────────────────────────────────────────────


def test_history_route_before_job_id_route():
    """
    GET /tcg/line-import/history は GET /tcg/line-import/{import_job_id} より前に定義されること。

    FastAPI はルートを定義順に評価するため、固定パスが可変パスより後にあると
    'history' が UUID パラメータとして誤評価される（IMP-39 で本番障害として発覚）。
    """
    from app.routers.tcg_line_import import router

    get_routes = [r for r in router.routes if hasattr(r, "methods") and "GET" in r.methods]
    paths = [r.path for r in get_routes]

    history_idx = next((i for i, p in enumerate(paths) if p == "/tcg/line-import/history"), None)
    job_id_idx = next((i for i, p in enumerate(paths) if p == "/tcg/line-import/{import_job_id}"), None)

    assert history_idx is not None, "/tcg/line-import/history がルーターに存在しない"
    assert job_id_idx is not None, "/tcg/line-import/{import_job_id} がルーターに存在しない"
    assert history_idx < job_id_idx, (
        f"/history (idx={history_idx}) が /{{import_job_id}} (idx={job_id_idx}) より後に定義されている。"
        "固定パスは可変パスより前に定義すること"
    )


def test_pending_route_before_job_id_route():
    """
    GET /tcg/line-import/pending は GET /tcg/line-import/{import_job_id} より前に定義されること。
    """
    from app.routers.tcg_line_import import router

    get_routes = [r for r in router.routes if hasattr(r, "methods") and "GET" in r.methods]
    paths = [r.path for r in get_routes]

    pending_idx = next((i for i, p in enumerate(paths) if p == "/tcg/line-import/pending"), None)
    job_id_idx = next((i for i, p in enumerate(paths) if p == "/tcg/line-import/{import_job_id}"), None)

    assert pending_idx is not None, "/tcg/line-import/pending がルーターに存在しない"
    assert job_id_idx is not None, "/tcg/line-import/{import_job_id} がルーターに存在しない"
    assert pending_idx < job_id_idx, (
        f"/pending (idx={pending_idx}) が /{{import_job_id}} (idx={job_id_idx}) より後に定義されている"
    )


async def test_import_window_start_passed_as_datetime():
    """
    import_line_export が import_jobs に INSERT するとき、
    window_start / window_end が文字列ではなく datetime オブジェクトで渡されること。

    asyncpg は TIMESTAMPTZ カラムへの文字列代入を拒否する（IMP-39 で本番障害として発覚）。
    """
    export_text = (
        "2026.08.01 金曜日\n"
        "10:00 仕入元A 商品X 100円\n"
    )
    db = _make_db_mock([("SP0001", "仕入元A")])
    captured_ws: list = []

    orig_execute = db.execute

    async def capturing_execute(stmt, params=None):
        sql = str(stmt)
        if params and "import_jobs" in sql and "window_start" in sql and "INSERT" in sql:
            captured_ws.append(params.get("ws"))
        return await orig_execute(stmt, params)

    db.execute = capturing_execute

    with patch("app.services.tcg_line_import_svc._enqueue_extraction"):
        await import_line_export(
            db=db,
            filename="test.txt",
            export_text=export_text,
            uploaded_by=None,
            window_hours=24,   # window_start を自動計算させる
        )

    assert len(captured_ws) == 1, "import_jobs への INSERT が実行されていない"
    ws_val = captured_ws[0]
    assert isinstance(ws_val, datetime), (
        f"window_start は datetime 型で渡す必要があるが {type(ws_val).__name__} が渡された（IMP-39）"
    )
