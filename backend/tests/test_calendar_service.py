"""
アプリ内カレンダーサービス（calendar_service + google_webhook）単体テスト。

DB・Google API は全てモックする。SQLAlchemy AsyncSession を AsyncMock で代替。

カバー範囲:
  calendar_service:
    - _build_sync_origin_id（純粋関数）
    - _to_google_event_body（純粋関数）
    - _get_sync_mode（DB モック）
    - _is_app_origin（DB モック）
    - list_events（DB モック）
    - create_event（DB モック + Google スキップ）
    - update_event（DB モック）
    - delete_event（DB モック）
    - upsert_from_google（DB モック）

  google_webhook:
    - _get_webhook_address（環境変数）
    - get_tenant_by_channel（DB モック）
    - handle_webhook_notification（sync 通知の無視 / 不明 channel）
    - register_webhook（Google 未接続のスキップ）
    - stop_webhook（レコードなしの早期 return）
    - renew_expiring_webhooks（更新ゼロケース）
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.fernet import Fernet

# テスト用環境変数を事前に設定
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("METADATA_FERNET_KEY", Fernet.generate_key().decode())
os.environ.setdefault("GOOGLE_CALENDAR_CLIENT_ID", "test-client-id")
os.environ.setdefault("GOOGLE_CALENDAR_CLIENT_SECRET", "test-secret")
os.environ.setdefault("GOOGLE_CALENDAR_REDIRECT_URI", "https://api.example.com/callback")


# ---------------------------------------------------------------------------
# ヘルパー: AsyncSession モック
# ---------------------------------------------------------------------------

def _make_db(first_return=None, fetchall_return=None, scalar_return=None):
    """AsyncSession のモックを生成する。"""
    db = AsyncMock()
    db.commit = AsyncMock()

    result = MagicMock()
    result.first = MagicMock(return_value=first_return)
    result.fetchall = MagicMock(return_value=fetchall_return or [])
    result.scalar_one = MagicMock(return_value=scalar_return or 1)
    db.execute = AsyncMock(return_value=result)
    return db


# ===========================================================================
# calendar_service テスト
# ===========================================================================


class TestBuildSyncOriginId:
    def test_format(self):
        from app.services.calendar_service import _build_sync_origin_id
        result = _build_sync_origin_id(tenant_id=1, calendar_event_id=42)
        assert result == "app:1:42"

    def test_different_values(self):
        from app.services.calendar_service import _build_sync_origin_id
        assert _build_sync_origin_id(99, 999) == "app:99:999"


class TestToGoogleEventBody:
    def test_datetime_event(self):
        from app.services.calendar_service import _to_google_event_body
        payload = {
            "title": "ミーティング",
            "start_datetime": "2026-06-01T10:00:00+09:00",
            "end_datetime": "2026-06-01T11:00:00+09:00",
            "is_all_day": False,
        }
        body = _to_google_event_body(payload)
        assert body["summary"] == "ミーティング"
        assert body["start"]["dateTime"] == "2026-06-01T10:00:00+09:00"
        assert body["start"]["timeZone"] == "Asia/Tokyo"
        assert body["end"]["dateTime"] == "2026-06-01T11:00:00+09:00"
        assert "date" not in body["start"]

    def test_all_day_event(self):
        from app.services.calendar_service import _to_google_event_body
        payload = {
            "title": "終日イベント",
            "start_datetime": "2026-06-01",
            "end_datetime": "2026-06-02",
            "is_all_day": True,
        }
        body = _to_google_event_body(payload)
        assert body["start"]["date"] == "2026-06-01"
        assert body["end"]["date"] == "2026-06-02"
        assert "dateTime" not in body["start"]

    @staticmethod
    def _all_day(start: str, end: str) -> dict:
        from app.services.calendar_service import _to_google_event_body
        return _to_google_event_body(
            {"title": "終日", "start_datetime": start, "end_datetime": end, "is_all_day": True}
        )

    def test_all_day_utc_one_day_uses_jst_date(self):
        body = self._all_day("2026-06-30T15:00:00.000Z", "2026-07-01T14:59:00.000Z")
        assert body["start"] == {"date": "2026-07-01"}
        assert body["end"] == {"date": "2026-07-02"}

    def test_all_day_utc_three_days_uses_jst_date(self):
        body = self._all_day("2026-06-30T15:00:00.000Z", "2026-07-03T14:59:00.000Z")
        assert body["start"] == {"date": "2026-07-01"}
        assert body["end"] == {"date": "2026-07-04"}

    def test_all_day_with_jst_offset(self):
        body = self._all_day("2026-07-01T00:00:00+09:00", "2026-07-01T23:59:00+09:00")
        assert body["start"] == {"date": "2026-07-01"}
        assert body["end"] == {"date": "2026-07-02"}

    def test_all_day_without_offset_is_jst(self):
        body = self._all_day("2026-07-01T00:00:00", "2026-07-01T23:59:00")
        assert body["start"] == {"date": "2026-07-01"}
        assert body["end"] == {"date": "2026-07-02"}

    def test_all_day_round_trip_through_google_times(self):
        from zoneinfo import ZoneInfo
        from app.services.calendar_service import _google_times

        body = self._all_day("2026-06-30T15:00:00.000Z", "2026-07-01T14:59:00.000Z")
        s, e, all_day = _google_times(body["start"], body["end"])
        jst = ZoneInfo("Asia/Tokyo")
        assert all_day is True
        assert s == datetime(2026, 7, 1, 0, 0, tzinfo=jst)
        assert e == datetime(2026, 7, 1, 23, 59, tzinfo=jst)

    def test_all_day_end_before_start_becomes_one_day(self):
        body = self._all_day("2026-07-05T00:00:00+09:00", "2026-07-01T23:59:00+09:00")
        assert body["start"] == {"date": "2026-07-05"}
        assert body["end"] == {"date": "2026-07-06"}

    def test_with_description_and_location(self):
        from app.services.calendar_service import _to_google_event_body
        payload = {
            "title": "テスト",
            "start_datetime": "2026-06-01T10:00:00+09:00",
            "end_datetime": "2026-06-01T11:00:00+09:00",
            "is_all_day": False,
            "description": "詳細説明",
            "location": "東京都渋谷区",
        }
        body = _to_google_event_body(payload)
        assert body["description"] == "詳細説明"
        assert body["location"] == "東京都渋谷区"

    def test_without_description_and_location(self):
        from app.services.calendar_service import _to_google_event_body
        payload = {
            "title": "テスト",
            "start_datetime": "2026-06-01T10:00:00+09:00",
            "end_datetime": "2026-06-01T11:00:00+09:00",
        }
        body = _to_google_event_body(payload)
        assert "description" not in body
        assert "location" not in body

    def test_empty_title_defaults(self):
        from app.services.calendar_service import _to_google_event_body
        payload = {
            "start_datetime": "2026-06-01T10:00:00+09:00",
            "end_datetime": "2026-06-01T11:00:00+09:00",
        }
        body = _to_google_event_body(payload)
        assert body["summary"] == ""


class TestGetSyncMode:
    @pytest.mark.asyncio
    async def test_returns_sync_mode(self):
        from app.services.calendar_service import _get_sync_mode
        db = _make_db(first_return=("bidirectional",))
        result = await _get_sync_mode(db, tenant_id=1)
        assert result == "bidirectional"

    @pytest.mark.asyncio
    async def test_returns_none_when_no_config(self):
        from app.services.calendar_service import _get_sync_mode
        db = _make_db(first_return=None)
        result = await _get_sync_mode(db, tenant_id=99)
        assert result == "none"


class TestIsAppOrigin:
    @pytest.mark.asyncio
    async def test_returns_true_when_found(self):
        from app.services.calendar_service import _is_app_origin
        db = _make_db(first_return=(1,))
        result = await _is_app_origin(db, google_event_id="google_abc", tenant_id=1)
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_not_found(self):
        from app.services.calendar_service import _is_app_origin
        db = _make_db(first_return=None)
        result = await _is_app_origin(db, google_event_id="google_xyz", tenant_id=1)
        assert result is False


class TestListEvents:
    @pytest.mark.asyncio
    async def test_returns_empty_list(self):
        from app.services.calendar_service import list_events
        db = _make_db(fetchall_return=[])
        result = await list_events(db, tenant_id=1, start="2026-06-01", end="2026-06-30")
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_events(self):
        from app.services.calendar_service import list_events
        now = datetime(2026, 6, 1, 10, 0, 0, tzinfo=timezone.utc)
        row = (1, 2, "shared", "meeting", "テスト会議", None, None, now, now, False, None, "app", "synced", 2, now, now, "鈴木 花子", "田中 太郎", None, None, None, None)
        db = _make_db(fetchall_return=[row])
        result = await list_events(db, tenant_id=1, start="2026-06-01", end="2026-06-30")
        assert len(result) == 1
        assert result[0]["title"] == "テスト会議"
        assert result[0]["calendar_type"] == "shared"
        assert result[0]["owner_name"] == "鈴木 花子"

    @pytest.mark.asyncio
    async def test_shared_type_filter(self):
        """calendar_type=shared でクエリが通ること。"""
        from app.services.calendar_service import list_events
        db = _make_db(fetchall_return=[])
        await list_events(db, tenant_id=1, start="2026-06-01", end="2026-06-30", calendar_type="shared")
        db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_personal_type_filter(self):
        """calendar_type=personal + user_id でクエリが通ること。"""
        from app.services.calendar_service import list_events
        db = _make_db(fetchall_return=[])
        await list_events(db, tenant_id=1, start="2026-06-01", end="2026-06-30",
                          calendar_type="personal", user_id=5)
        db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_hides_other_users_personal(self):
        """他人の personal は常に除く: SQL に絞りが入り、params に me が入る。"""
        from app.services.calendar_service import list_events
        db = _make_db(fetchall_return=[])
        await list_events(db, tenant_id=1, start="2026-06-01", end="2026-06-30", user_id=5)
        stmt, params = db.execute.call_args.args
        assert "ce.calendar_type = 'shared' OR ce.user_id = :me" in stmt.text
        assert params["me"] == 5

    @pytest.mark.asyncio
    async def test_list_without_user_returns_shared_only(self):
        from app.services.calendar_service import list_events
        db = _make_db(fetchall_return=[])
        await list_events(db, tenant_id=1, start="2026-06-01", end="2026-06-30")
        stmt, params = db.execute.call_args.args
        assert "AND ce.calendar_type = 'shared'" in stmt.text
        assert ":me" not in stmt.text
        assert "me" not in params

    @pytest.mark.asyncio
    async def test_s1_range_call_unchanged(self):
        """S1: 期間だけの呼び出しは ILIKE・LIMIT・DESC を持たず、条件の順も今のまま。"""
        from app.services.calendar_service import list_events
        db = _make_db(fetchall_return=[])
        await list_events(db, tenant_id=1, start="2026-06-01", end="2026-06-30")
        stmt, _params = db.execute.call_args.args
        assert "ILIKE" not in stmt.text
        assert "LIMIT" not in stmt.text
        assert "DESC" not in stmt.text
        assert "ce.start_datetime < :end AND ce.end_datetime > :start" in stmt.text

    @pytest.mark.asyncio
    async def test_s2_title_search_sql_and_params(self):
        """S2: 題名検索は ILIKE・新しい順・LIMIT が入り、期間の条件は入らない。"""
        from app.services.calendar_service import list_events
        db = _make_db(fetchall_return=[])
        await list_events(db, tenant_id=1, user_id=7, title_query="商談", limit=50)
        stmt, params = db.execute.call_args.args
        assert "ce.title ILIKE :title_q ESCAPE" in stmt.text
        assert "ORDER BY ce.start_datetime DESC" in stmt.text
        assert "LIMIT :limit" in stmt.text
        assert "(ce.calendar_type = 'shared' OR ce.user_id = :me)" in stmt.text
        assert ":start" not in stmt.text
        assert ":end" not in stmt.text
        assert params["title_q"] == "%商談%"
        assert params["limit"] == 50
        assert params["me"] == 7

    @pytest.mark.asyncio
    async def test_s3_title_query_escapes_wildcards(self):
        """S3: %・_・\\ は文字として扱う。"""
        from app.services.calendar_service import list_events
        db = _make_db(fetchall_return=[])
        await list_events(db, tenant_id=1, user_id=7, title_query="50%_off\\", limit=50)
        _stmt, params = db.execute.call_args.args
        assert params["title_q"] == "%50\\%\\_off\\\\%"

    @pytest.mark.asyncio
    async def test_s4_no_range_where_is_valid(self):
        """S4: 期間なし・user_id なしでも WHERE が壊れない。"""
        from app.services.calendar_service import list_events
        db = _make_db(fetchall_return=[])
        await list_events(db, tenant_id=1, user_id=None, title_query="x")
        stmt, _params = db.execute.call_args.args
        assert "WHERE TRUE AND ce.calendar_type = 'shared'" in stmt.text


class TestCreateEvent:
    @pytest.mark.asyncio
    async def test_create_without_google_sync(self):
        """sync_mode='none' の場合、Google API は呼ばれない。"""
        from app.services.calendar_service import create_event

        # DB: INSERT RETURNING 1, then _get_sync_mode returns 'none'
        db = AsyncMock()
        db.commit = AsyncMock()

        insert_result = MagicMock()
        insert_result.scalar_one = MagicMock(return_value=1)
        sync_result = MagicMock()
        sync_result.first = MagicMock(return_value=("none", None))

        db.execute = AsyncMock(side_effect=[insert_result, sync_result])

        payload = {
            "title": "新しいイベント",
            "start_datetime": "2026-06-01T10:00:00+09:00",
            "end_datetime": "2026-06-01T11:00:00+09:00",
            "calendar_type": "shared",
        }
        result = await create_event(db, tenant_id=1, user_id=2, payload=payload)
        assert result["id"] == 1
        assert db.execute.call_args_list[0].args[1]["uid"] == 2

    @pytest.mark.asyncio
    async def test_create_personal_event(self):
        """personal イベントでも owner 用 user_id がセットされる。"""
        from app.services.calendar_service import create_event

        db = AsyncMock()
        db.commit = AsyncMock()

        insert_result = MagicMock()
        insert_result.scalar_one = MagicMock(return_value=5)
        sync_result = MagicMock()
        sync_result.first = MagicMock(return_value=("none", None))
        db.execute = AsyncMock(side_effect=[insert_result, sync_result])

        payload = {
            "title": "個人予定",
            "start_datetime": "2026-06-01T10:00:00+09:00",
            "end_datetime": "2026-06-01T11:00:00+09:00",
            "calendar_type": "personal",
        }
        result = await create_event(db, tenant_id=1, user_id=3, payload=payload)
        assert result["id"] == 5
        assert db.execute.call_args_list[0].args[1]["uid"] == 3

    @pytest.mark.asyncio
    async def test_create_with_google_sync_failure(self):
        """Google 同期失敗時でも DB に保存される（sync_status='failed'）。"""
        from app.services.calendar_service import create_event

        db = AsyncMock()
        db.commit = AsyncMock()

        insert_result = MagicMock()
        insert_result.scalar_one = MagicMock(return_value=10)
        sync_result = MagicMock()
        sync_result.first = MagicMock(return_value=("bidirectional", 1))
        update_result = MagicMock()

        db.execute = AsyncMock(side_effect=[insert_result, sync_result, update_result])

        with patch("app.services.google_calendar.create_event", AsyncMock(side_effect=RuntimeError("API error"))):
            payload = {
                "title": "同期失敗テスト",
                "start_datetime": "2026-06-01T10:00:00+09:00",
                "end_datetime": "2026-06-01T11:00:00+09:00",
                "calendar_type": "shared",
            }
            result = await create_event(db, tenant_id=1, user_id=1, payload=payload)
            assert result["id"] == 10

    @pytest.mark.asyncio
    async def test_create_by_non_connector_skips_google(self):
        """つないだ人と別の人が作った予定は Google に送らない。"""
        from app.services.calendar_service import create_event

        db = AsyncMock()
        db.commit = AsyncMock()
        insert_result = MagicMock()
        insert_result.scalar_one = MagicMock(return_value=11)
        sync_result = MagicMock()
        sync_result.first = MagicMock(return_value=("bidirectional", 1))
        db.execute = AsyncMock(side_effect=[insert_result, sync_result])

        gcreate = AsyncMock()
        with patch("app.services.google_calendar.create_event", gcreate):
            payload = {
                "title": "別の人の予定",
                "start_datetime": "2026-06-01T10:00:00+09:00",
                "end_datetime": "2026-06-01T11:00:00+09:00",
                "calendar_type": "shared",
            }
            result = await create_event(db, tenant_id=1, user_id=2, payload=payload)
        assert result["id"] == 11
        gcreate.assert_not_called()
        assert db.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_create_by_connector_sends_to_google(self):
        """つないだ本人が作った予定は Google に送り、id を保存する。"""
        from app.services.calendar_service import create_event

        db = AsyncMock()
        db.commit = AsyncMock()
        insert_result = MagicMock()
        insert_result.scalar_one = MagicMock(return_value=1)
        sync_result = MagicMock()
        sync_result.first = MagicMock(return_value=("bidirectional", 3))
        db.execute = AsyncMock(side_effect=[insert_result, sync_result, MagicMock()])

        gcreate = AsyncMock(return_value={"id": "g1"})
        with patch("app.services.google_calendar.create_event", gcreate):
            payload = {
                "title": "本人の予定",
                "start_datetime": "2026-06-01T10:00:00+09:00",
                "end_datetime": "2026-06-01T11:00:00+09:00",
                "calendar_type": "shared",
            }
            await create_event(db, tenant_id=1, user_id=3, payload=payload)
        gcreate.assert_called_once()
        params = db.execute.call_args_list[2].args[1]
        assert params["gid"] == "g1"
        assert params["oid"] == "app:1:1"

    @pytest.mark.asyncio
    async def test_create_all_day_sends_jst_date_to_google(self):
        """終日を ...Z の形で送っても、Google へ渡す日付は日本時間の日付になる。"""
        from app.services.calendar_service import create_event

        db = AsyncMock()
        db.commit = AsyncMock()
        insert_result = MagicMock()
        insert_result.scalar_one = MagicMock(return_value=1)
        sync_result = MagicMock()
        sync_result.first = MagicMock(return_value=("bidirectional", 3))
        db.execute = AsyncMock(side_effect=[insert_result, sync_result, MagicMock()])

        gcreate = AsyncMock(return_value={"id": "g1"})
        with patch("app.services.google_calendar.create_event", gcreate):
            payload = {
                "title": "終日の予定",
                "start_datetime": "2026-06-30T15:00:00.000Z",
                "end_datetime": "2026-07-01T14:59:00.000Z",
                "is_all_day": True,
                "calendar_type": "shared",
            }
            await create_event(db, tenant_id=1, user_id=3, payload=payload)
        body = gcreate.call_args.args[2]
        assert body["start"] == {"date": "2026-07-01"}
        assert body["end"] == {"date": "2026-07-02"}


class TestUpdateEvent:
    @pytest.mark.asyncio
    async def test_update_no_fields(self):
        """更新フィールドがない場合は早期 return。"""
        from app.services.calendar_service import update_event
        db = _make_db()
        result = await update_event(db, tenant_id=1, event_id=1, user_id=1, payload={})
        assert result["id"] == 1
        db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_title_without_google_sync(self):
        """sync_mode='none' / google_event_id なし → Google 同期なし。"""
        from app.services.calendar_service import update_event

        db = AsyncMock()
        db.commit = AsyncMock()
        update_result = MagicMock()
        geid_result = MagicMock()
        geid_result.first = MagicMock(return_value=(None,))  # google_event_id = None
        sync_result = MagicMock()
        sync_result.first = MagicMock(return_value=("none", None))

        db.execute = AsyncMock(side_effect=[update_result, geid_result, sync_result])

        result = await update_event(db, tenant_id=1, event_id=3, user_id=1,
                                    payload={"title": "更新タイトル"})
        assert result["id"] == 3

    @pytest.mark.asyncio
    async def test_update_sets_calendar_type_and_user_id(self):
        from app.services.calendar_service import update_event

        db = AsyncMock()
        db.commit = AsyncMock()
        geid_result = MagicMock()
        geid_result.first = MagicMock(return_value=(None,))
        sync_result = MagicMock()
        sync_result.first = MagicMock(return_value=("none", None))
        db.execute = AsyncMock(side_effect=[MagicMock(), geid_result, sync_result])

        await update_event(db, tenant_id=1, event_id=3, user_id=1,
                           payload={"calendar_type": "personal", "user_id": 1})
        stmt, params = db.execute.call_args_list[0].args
        assert "calendar_type = :calendar_type" in stmt.text
        assert "user_id = :user_id" in stmt.text
        assert params["calendar_type"] == "personal"
        assert params["user_id"] == 1

    @pytest.mark.asyncio
    async def test_update_all_day_sends_jst_date_to_google(self):
        """終日を ...Z の形で直しても、Google へ渡す日付は日本時間の日付になる。"""
        from app.services.calendar_service import update_event

        db = AsyncMock()
        db.commit = AsyncMock()
        geid = MagicMock()
        geid.first = MagicMock(return_value=("g1", None))
        sync = MagicMock()
        sync.first = MagicMock(return_value=("bidirectional",))
        db.execute = AsyncMock(side_effect=[MagicMock(), geid, sync, MagicMock()])

        gupdate = AsyncMock(return_value={"id": "g1"})
        with patch("app.services.google_calendar.update_event", gupdate):
            await update_event(
                db, tenant_id=1, event_id=9, user_id=3,
                payload={
                    "title": "終日",
                    "start_datetime": "2026-06-30T15:00:00.000Z",
                    "end_datetime": "2026-07-01T14:59:00.000Z",
                    "is_all_day": True,
                },
            )
        body = gupdate.call_args.args[3]
        assert body["start"] == {"date": "2026-07-01"}
        assert body["end"] == {"date": "2026-07-02"}


class TestDeleteEvent:
    @pytest.mark.asyncio
    async def test_delete_without_google(self):
        """google_event_id がない場合は Google API を呼ばない。"""
        from app.services.calendar_service import delete_event

        db = AsyncMock()
        db.commit = AsyncMock()
        geid_result = MagicMock()
        geid_result.first = MagicMock(return_value=(None,))
        delete_result = MagicMock()
        sync_result = MagicMock()
        sync_result.first = MagicMock(return_value=("none", None))

        db.execute = AsyncMock(side_effect=[geid_result, delete_result, sync_result])
        await delete_event(db, tenant_id=1, event_id=5)
        # commit が呼ばれたことを確認
        db.commit.assert_called()


class TestUpsertFromGoogle:
    @pytest.mark.asyncio
    async def test_skips_when_no_event_id(self):
        from app.services.calendar_service import upsert_from_google
        db = _make_db()
        out = await upsert_from_google(db, tenant_id=1, google_event={}, owner_user_id=9)
        assert out == "skipped"
        db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_deletes_cancelled_event_only_google_rows(self):
        from app.services.calendar_service import upsert_from_google

        db = AsyncMock()
        db.commit = AsyncMock()
        origin_result = MagicMock()
        origin_result.first = MagicMock(return_value=None)  # not app origin
        delete_result = MagicMock()
        db.execute = AsyncMock(side_effect=[origin_result, delete_result])

        out = await upsert_from_google(
            db, tenant_id=1, google_event={"id": "ev1", "status": "cancelled"}, owner_user_id=9
        )
        assert out == "deleted"
        sql = db.execute.call_args_list[1].args[0].text
        assert "source = 'google'" in sql
        db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_app_origin(self):
        from app.services.calendar_service import upsert_from_google

        db = AsyncMock()
        db.commit = AsyncMock()
        origin_result = MagicMock()
        origin_result.first = MagicMock(return_value=(1,))  # app origin found
        db.execute = AsyncMock(return_value=origin_result)

        out = await upsert_from_google(
            db, tenant_id=1,
            google_event={"id": "ev_app", "status": "confirmed"}, owner_user_id=9,
        )
        assert out == "skipped"
        # execute は _is_app_origin の1回のみ（upsert は呼ばれない）
        assert db.execute.call_count == 1
        db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_upserts_valid_event_as_personal_with_owner(self):
        from app.services.calendar_service import upsert_from_google

        db = AsyncMock()
        db.commit = AsyncMock()
        origin_result = MagicMock()
        origin_result.first = MagicMock(return_value=None)  # not app origin
        upsert_result = MagicMock()
        db.execute = AsyncMock(side_effect=[origin_result, upsert_result])

        google_event = {
            "id": "ev_google_001",
            "summary": "Google会議",
            "start": {"dateTime": "2026-06-01T10:00:00+09:00"},
            "end": {"dateTime": "2026-06-01T11:00:00+09:00"},
        }
        out = await upsert_from_google(
            db, tenant_id=1, google_event=google_event, owner_user_id=9
        )
        assert out == "upserted"
        stmt, params = db.execute.call_args_list[1].args
        sql = stmt.text
        assert "'personal'" in sql
        assert ":owner" in sql
        assert "ON CONFLICT (google_event_id) WHERE google_event_id IS NOT NULL" in sql
        assert "WHERE calendar_events.source = 'google'" in sql
        do_update = sql.split("DO UPDATE SET", 1)[1]
        assert "calendar_type" not in do_update
        assert "user_id" not in do_update
        assert params["owner"] == 9
        assert isinstance(params["start"], datetime)
        assert params["start"].utcoffset().total_seconds() == 9 * 3600
        db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_invalid_start_end(self):
        from app.services.calendar_service import upsert_from_google

        db = AsyncMock()
        db.commit = AsyncMock()
        origin_result = MagicMock()
        origin_result.first = MagicMock(return_value=None)
        db.execute = AsyncMock(return_value=origin_result)

        google_event = {
            "id": "ev_no_dates",
            "summary": "日時なし",
            "start": {},
            "end": {},
        }
        out = await upsert_from_google(
            db, tenant_id=1, google_event=google_event, owner_user_id=9
        )
        assert out == "skipped"
        # start/end なしなので upsert 実行されない
        assert db.execute.call_count == 1
        db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_upserts_all_day_event(self):
        from app.services.calendar_service import upsert_from_google

        db = AsyncMock()
        db.commit = AsyncMock()
        origin_result = MagicMock()
        origin_result.first = MagicMock(return_value=None)
        upsert_result = MagicMock()
        db.execute = AsyncMock(side_effect=[origin_result, upsert_result])

        google_event = {
            "id": "ev_all_day",
            "summary": "終日イベント",
            "start": {"date": "2026-06-01"},
            "end": {"date": "2026-06-02"},
        }
        out = await upsert_from_google(
            db, tenant_id=1, google_event=google_event, owner_user_id=9
        )
        assert out == "upserted"
        params = db.execute.call_args_list[1].args[1]
        assert params["all_day"] is True
        db.commit.assert_not_called()


class TestGoogleTimes:
    def test_all_day_maps_to_app_shape_in_jst(self):
        from zoneinfo import ZoneInfo
        from app.services.calendar_service import _google_times

        s, e, all_day = _google_times({"date": "2026-11-05"}, {"date": "2026-11-06"})
        jst = ZoneInfo("Asia/Tokyo")
        assert all_day is True
        assert s == datetime(2026, 11, 5, 0, 0, tzinfo=jst)
        assert e == datetime(2026, 11, 5, 23, 59, tzinfo=jst)

    def test_all_day_end_before_start_falls_back_to_start_day(self):
        from zoneinfo import ZoneInfo
        from app.services.calendar_service import _google_times

        s, e, _ = _google_times({"date": "2026-11-05"}, {"date": "2026-11-05"})
        assert e == datetime(2026, 11, 5, 23, 59, tzinfo=ZoneInfo("Asia/Tokyo"))

    def test_timed_event_keeps_offset(self):
        from app.services.calendar_service import _google_times

        s, e, all_day = _google_times(
            {"dateTime": "2026-11-05T10:00:00+09:00"},
            {"dateTime": "2026-11-05T11:00:00+09:00"},
        )
        assert all_day is False
        assert s == datetime.fromisoformat("2026-11-05T10:00:00+09:00")
        assert e == datetime.fromisoformat("2026-11-05T11:00:00+09:00")

    def test_naive_datetime_uses_time_zone_field(self):
        from zoneinfo import ZoneInfo
        from app.services.calendar_service import _google_times

        s, e, _ = _google_times(
            {"dateTime": "2026-11-05T10:00:00", "timeZone": "America/New_York"},
            {"dateTime": "2026-11-05T11:00:00", "timeZone": "America/New_York"},
        )
        assert s.tzinfo == ZoneInfo("America/New_York")
        assert e.tzinfo == ZoneInfo("America/New_York")


# ===========================================================================
# google_webhook テスト
# ===========================================================================


class TestGetWebhookAddress:
    def test_default_base_url(self):
        from app.services.google_webhook import _get_webhook_address
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("API_BASE_URL", None)
            addr = _get_webhook_address()
            assert addr == "https://api.salesanchor.jp/api/v1/google-calendar/webhook"

    def test_custom_base_url(self):
        from app.services.google_webhook import _get_webhook_address
        with patch.dict(os.environ, {"API_BASE_URL": "https://test.example.com"}):
            addr = _get_webhook_address()
            assert addr == "https://test.example.com/api/v1/google-calendar/webhook"

    def test_trailing_slash_stripped(self):
        from app.services.google_webhook import _get_webhook_address
        with patch.dict(os.environ, {"API_BASE_URL": "https://test.example.com/"}):
            addr = _get_webhook_address()
            assert not addr.startswith("https://test.example.com//")


class TestVerifyChannel:
    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        from app.services.google_webhook import verify_channel
        db = _make_db(first_return=None)
        assert await verify_channel(db, "nonexistent", "tok") is None

    @pytest.mark.asyncio
    async def test_returns_none_when_hash_null(self):
        from app.services.google_webhook import verify_channel
        db = _make_db(first_return=(7, None))
        assert await verify_channel(db, "ch_123", "tok") is None

    @pytest.mark.asyncio
    async def test_returns_none_when_token_mismatch(self):
        import hashlib
        from app.services.google_webhook import verify_channel
        db = _make_db(first_return=(7, hashlib.sha256(b"right").hexdigest()))
        assert await verify_channel(db, "ch_123", "wrong") is None
        assert await verify_channel(db, "ch_123", "") is None

    @pytest.mark.asyncio
    async def test_returns_tenant_id_when_token_matches(self):
        import hashlib
        from app.services.google_webhook import verify_channel
        db = _make_db(first_return=(7, hashlib.sha256(b"right").hexdigest()))
        assert await verify_channel(db, "ch_123", "right") == 7


def _make_sync_db(lock=True, cfg=(9, "read_only"), sync_token=None, sub_exists=True):
    """sync_tenant_from_google 用の db モック。実行された (sql, params) を db.calls に積む。"""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    calls = []

    async def _exec(stmt, params=None):
        sql = str(getattr(stmt, "text", stmt))
        calls.append((sql, params))
        r = MagicMock()
        r.rowcount = 0
        if "pg_try_advisory_lock" in sql:
            r.scalar = MagicMock(return_value=lock)
        elif "FROM tenant_google_calendar_config" in sql:
            r.first = MagicMock(return_value=cfg)
        elif "SELECT sync_token" in sql:
            r.first = MagicMock(return_value=(sync_token,) if sub_exists else None)
        else:
            r.first = MagicMock(return_value=None)
        return r

    db.execute = _exec
    db.calls = calls
    return db


def _make_list_service(responses):
    """events().list(**kw).execute が responses を順に返す Google サービスのモック。"""
    service = MagicMock()
    kw_log = []
    it = iter(responses)

    def _list(**kw):
        kw_log.append(kw)
        r = next(it)
        m = MagicMock()
        if isinstance(r, Exception):
            m.execute.side_effect = r
        else:
            m.execute.return_value = r
        return m

    service.events.return_value.list.side_effect = _list
    return service, kw_log


def _sync_patches(service, upsert=None):
    upsert = upsert or AsyncMock(return_value="upserted")
    return upsert, [
        patch("app.services.google_webhook.set_tenant_context", AsyncMock()),
        patch("app.services.google_webhook.reset_tenant_context", AsyncMock()),
        patch("app.services.google_calendar._get_service", AsyncMock(return_value=service)),
        patch("app.services.calendar_service.upsert_from_google", upsert),
    ]


class TestSyncTenantFromGoogle:
    async def _run(self, db, service, upsert=None):
        from contextlib import ExitStack
        from app.services.google_webhook import sync_tenant_from_google

        up, patches = _sync_patches(service, upsert)
        with ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            result = await sync_tenant_from_google(db, 1)
        return result, up

    @pytest.mark.asyncio
    async def test_sync_token_sends_only_sync_token(self):
        db = _make_sync_db(sync_token="TOK1")
        service, kw = _make_list_service([{"items": [{"id": "a"}], "nextSyncToken": "TOK2"}])
        result, up = await self._run(db, service)
        assert result["full"] is False
        assert kw[0]["syncToken"] == "TOK1"
        assert "timeMin" not in kw[0]
        assert kw[0]["singleEvents"] is True
        assert "showDeleted" not in kw[0]
        assert not any("DELETE FROM calendar_events" in s for s, _ in db.calls)
        up.assert_awaited_once()
        assert up.await_args.args[3] == 9

    @pytest.mark.asyncio
    async def test_no_token_full_read_deletes_unseen_google_rows(self):
        db = _make_sync_db(sync_token=None)
        service, kw = _make_list_service([
            {"items": [{"id": "a"}, {"id": "b", "status": "cancelled"}], "nextSyncToken": "N"}
        ])
        result, _ = await self._run(db, service)
        assert result["full"] is True
        assert "timeMin" in kw[0] and "syncToken" not in kw[0]
        deletes = [(s, p) for s, p in db.calls if "DELETE FROM calendar_events" in s]
        assert len(deletes) == 1
        sql, params = deletes[0]
        assert "source = 'google'" in sql
        assert "CAST(:seen AS text[])" in sql
        assert params["seen"] == ["a"]

    @pytest.mark.asyncio
    async def test_410_falls_back_to_full_read_once(self):
        import httplib2
        from googleapiclient.errors import HttpError

        err = HttpError(httplib2.Response({"status": 410}), b"gone")
        db = _make_sync_db(sync_token="OLD")
        service, kw = _make_list_service([err, {"items": [], "nextSyncToken": "NEW"}])
        result, _ = await self._run(db, service)
        assert result["full"] is True
        assert len(kw) == 2
        assert kw[0]["syncToken"] == "OLD"
        assert "timeMin" in kw[1] and "syncToken" not in kw[1]

    @pytest.mark.asyncio
    async def test_reads_all_pages_and_saves_last_next_sync_token(self):
        db = _make_sync_db(sync_token="T")
        service, kw = _make_list_service([
            {"items": [{"id": "a"}], "nextPageToken": "P2"},
            {"items": [{"id": "b"}], "nextSyncToken": "LAST"},
        ])
        result, up = await self._run(db, service)
        assert result["upserted"] == 2
        assert kw[1]["pageToken"] == "P2"
        saves = [(s, p) for s, p in db.calls if "SET sync_token" in s]
        assert len(saves) == 1 and saves[0][1]["t"] == "LAST"
        db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_lock_not_acquired_does_nothing(self):
        db = _make_sync_db(lock=False)
        service, kw = _make_list_service([])
        result, up = await self._run(db, service)
        assert result == {"skipped": "locked"}
        assert kw == []
        up.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_write_only_does_not_call_google(self):
        db = _make_sync_db(cfg=(9, "write_only"))
        service, kw = _make_list_service([])
        result, _ = await self._run(db, service)
        assert result == {"skipped": "off"}
        assert kw == []

    @pytest.mark.asyncio
    async def test_no_owner_skips(self):
        db = _make_sync_db(cfg=(None, "bidirectional"))
        service, kw = _make_list_service([])
        result, _ = await self._run(db, service)
        assert result == {"skipped": "no_owner"}
        assert kw == []


class TestRegisterWebhook:
    @pytest.mark.asyncio
    async def test_skips_when_google_not_connected(self):
        """Google 未接続（RuntimeError）のときは None を返す。"""
        from app.services.google_webhook import register_webhook
        db = _make_db()
        with patch("app.services.google_calendar._get_service",
                   AsyncMock(side_effect=RuntimeError("not connected"))):
            result = await register_webhook(db, tenant_id=1)
            assert result is None

    @pytest.mark.asyncio
    async def test_skips_when_watch_fails(self):
        """events().watch().execute() 失敗時は None を返す。"""
        from app.services.google_webhook import register_webhook

        mock_service = MagicMock()
        mock_service.events().watch().execute.side_effect = Exception("API error")

        db = _make_db()
        with patch("app.services.google_calendar._get_service",
                   AsyncMock(return_value=mock_service)):
            result = await register_webhook(db, tenant_id=1)
            assert result is None

    @pytest.mark.asyncio
    async def test_sends_token_saves_hash_and_stops_old_channel(self):
        import hashlib
        from app.services.google_webhook import register_webhook

        mock_service = MagicMock()
        mock_service.events.return_value.watch.return_value.execute.return_value = {
            "expiration": "1893456000000",
            "resourceId": "res_new",
        }
        stop_exec = mock_service.channels.return_value.stop.return_value.execute

        db = AsyncMock()
        db.commit = AsyncMock()
        old_result = MagicMock()
        old_result.first = MagicMock(return_value=("old_ch", "old_res"))
        db.execute = AsyncMock(side_effect=[old_result, MagicMock()])

        with patch("app.services.google_calendar._get_service",
                   AsyncMock(return_value=mock_service)), patch(
            "app.services.google_webhook.reset_tenant_context", AsyncMock()
        ):
            result = await register_webhook(db, tenant_id=1)

        assert result is not None
        body = mock_service.events.return_value.watch.call_args.kwargs["body"]
        token = body["token"]
        assert token
        upsert_params = db.execute.call_args_list[1].args[1]
        assert upsert_params["thash"] == hashlib.sha256(token.encode()).hexdigest()
        assert "channel_token_hash" in db.execute.call_args_list[1].args[0].text
        mock_service.channels.return_value.stop.assert_called_once_with(
            body={"id": "old_ch", "resourceId": "old_res"}
        )
        stop_exec.assert_called_once()


class TestStopWebhook:
    @pytest.mark.asyncio
    async def test_returns_early_when_no_subscription(self):
        """サブスクリプションが存在しない場合は早期 return。"""
        from app.services.google_webhook import stop_webhook
        db = _make_db(first_return=None)
        await stop_webhook(db, tenant_id=1)
        # commit は呼ばれない（DELETE も実行されない）
        db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_stops_and_deletes_subscription(self):
        """サブスクリプションが存在する場合は Google チャンネルを停止して DB から削除。"""
        from app.services.google_webhook import stop_webhook

        mock_service = MagicMock()
        mock_service.channels().stop().execute = MagicMock()

        db = AsyncMock()
        db.commit = AsyncMock()

        sub_result = MagicMock()
        sub_result.first = MagicMock(return_value=("ch_abc", "res_xyz"))
        delete_result = MagicMock()
        db.execute = AsyncMock(side_effect=[sub_result, delete_result])

        with patch("app.services.google_calendar._get_service",
                   AsyncMock(return_value=mock_service)):
            await stop_webhook(db, tenant_id=1)
        db.commit.assert_called()


class TestRenewExpiringWebhooks:
    @pytest.mark.asyncio
    async def test_returns_zero_when_no_expiring(self):
        """更新対象がない場合は 0 を返す。"""
        from app.services.google_webhook import renew_expiring_webhooks
        db = _make_db(fetchall_return=[])
        result = await renew_expiring_webhooks(db)
        assert result == 0

    @pytest.mark.asyncio
    async def test_renews_expiring_channel(self):
        """有効期限が近い場合は register_webhook を呼ぶ（Google 未接続で None = renewed=0）。"""
        from app.services.google_webhook import renew_expiring_webhooks

        db = AsyncMock()
        db.commit = AsyncMock()

        expiring_result = MagicMock()
        expiring_result.fetchall = MagicMock(return_value=[(1,)])  # tenant_id=1
        # register_webhook 内で _get_sync_mode を DB に問い合わせる → RuntimeError を出してスキップ
        # _get_service は RuntimeError → register_webhook は None を返す → renewed=0
        sub_result = MagicMock()
        sub_result.first = MagicMock(return_value=None)
        db.execute = AsyncMock(side_effect=[expiring_result, sub_result])

        with patch("app.services.google_calendar._get_service",
                   AsyncMock(side_effect=RuntimeError("not connected"))), patch(
            "app.services.google_webhook.set_tenant_context", AsyncMock()
        ) as set_ctx, patch(
            "app.services.google_webhook.clear_tenant_context", AsyncMock()
        ) as clear_ctx:
            result = await renew_expiring_webhooks(db)
        # Google 未接続 → None が返る → renewed は 0
        assert result == 0
        # 会社ごとに文脈を張り、最後に必ず外す
        set_ctx.assert_awaited_once()
        clear_ctx.assert_awaited_once()


# ===========================================================================
# 便3: Google Meet
# ===========================================================================

MEET = "https://meet.google.com/abc-defg-hij"


class TestCanAddMeet:
    @staticmethod
    def _db(row):
        db = AsyncMock()
        result = MagicMock()
        result.first = MagicMock(return_value=row)
        db.execute = AsyncMock(return_value=result)
        return db

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "row,user_id,expected",
        [
            (("bidirectional", 3), 3, True),
            (("write_only", 3), 3, True),
            (("read_only", 3), 3, False),
            (("bidirectional", 3), 4, False),
        ],
    )
    async def test_can_add_meet(self, row, user_id, expected):
        from app.services.calendar_service import can_add_meet

        assert await can_add_meet(self._db(row), 1, user_id) is expected

    @pytest.mark.asyncio
    async def test_not_connected_is_false(self):
        from app.services.calendar_service import can_add_meet

        assert await can_add_meet(self._db(None), 1, 3) is False


class TestCreateEventWithMeet:
    @staticmethod
    def _db():
        db = AsyncMock()
        db.commit = AsyncMock()
        insert_result = MagicMock()
        insert_result.scalar_one = MagicMock(return_value=1)
        sync_result = MagicMock()
        sync_result.first = MagicMock(return_value=("bidirectional", 3))
        db.execute = AsyncMock(side_effect=[insert_result, sync_result, MagicMock()])
        return db

    @staticmethod
    def _payload():
        return {
            "title": "Meet 付き",
            "start_datetime": "2026-06-01T10:00:00+09:00",
            "end_datetime": "2026-06-01T11:00:00+09:00",
            "add_meet": True,
        }

    @pytest.mark.asyncio
    async def test_sends_create_request_and_saves_hangout_link(self):
        from app.services.calendar_service import create_event

        db = self._db()
        gcreate = AsyncMock(return_value={"id": "g1", "hangoutLink": MEET})
        with patch("app.services.google_calendar.create_event", gcreate):
            result = await create_event(db, tenant_id=1, user_id=3, payload=self._payload())
        assert result == {"id": 1, "meet_url": MEET}
        assert gcreate.call_args.kwargs["conference"] is True
        body = gcreate.call_args.args[2]
        req = body["conferenceData"]["createRequest"]
        assert req["conferenceSolutionKey"] == {"type": "hangoutsMeet"}
        assert req["requestId"]
        assert db.execute.call_args_list[2].args[1]["meet_url"] == MEET
        # add_meet は表の列ではない
        assert "add_meet" not in db.execute.call_args_list[0].args[1]

    @pytest.mark.asyncio
    async def test_request_id_is_new_each_time(self):
        from app.services.calendar_service import create_event

        ids = []
        for _ in range(2):
            gcreate = AsyncMock(return_value={"id": "g1", "hangoutLink": MEET})
            with patch("app.services.google_calendar.create_event", gcreate):
                await create_event(self._db(), tenant_id=1, user_id=3, payload=self._payload())
            ids.append(gcreate.call_args.args[2]["conferenceData"]["createRequest"]["requestId"])
        assert ids[0] != ids[1]

    @pytest.mark.asyncio
    async def test_pending_is_reread_until_link_appears(self):
        from app.services.calendar_service import create_event

        db = self._db()
        pending = {"id": "g1", "conferenceData": {"createRequest": {"status": {"statusCode": "pending"}}}}
        gcreate = AsyncMock(return_value=pending)
        gget = AsyncMock(side_effect=[{"id": "g1"}, {"id": "g1", "hangoutLink": MEET}])
        with patch("app.services.google_calendar.create_event", gcreate), patch(
            "app.services.google_calendar.get_event", gget
        ), patch("app.services.calendar_service.asyncio.sleep", AsyncMock()) as slept:
            result = await create_event(db, tenant_id=1, user_id=3, payload=self._payload())
        assert result["meet_url"] == MEET
        assert gget.call_count == 2
        assert slept.call_count == 2

    @pytest.mark.asyncio
    async def test_pending_forever_leaves_meet_url_null_but_event_saved(self):
        from app.services.calendar_service import create_event

        db = self._db()
        pending = {"id": "g1", "conferenceData": {"createRequest": {"status": {"statusCode": "pending"}}}}
        gcreate = AsyncMock(return_value=pending)
        gget = AsyncMock(return_value={"id": "g1"})
        with patch("app.services.google_calendar.create_event", gcreate), patch(
            "app.services.google_calendar.get_event", gget
        ), patch("app.services.calendar_service.asyncio.sleep", AsyncMock()):
            result = await create_event(db, tenant_id=1, user_id=3, payload=self._payload())
        assert result == {"id": 1, "meet_url": None}
        assert gget.call_count == 2
        params = db.execute.call_args_list[2].args[1]
        assert params["gid"] == "g1"
        assert params["meet_url"] is None

    @pytest.mark.asyncio
    async def test_without_add_meet_no_conference(self):
        from app.services.calendar_service import create_event

        db = self._db()
        gcreate = AsyncMock(return_value={"id": "g1"})
        payload = self._payload()
        payload.pop("add_meet")
        with patch("app.services.google_calendar.create_event", gcreate):
            result = await create_event(db, tenant_id=1, user_id=3, payload=payload)
        assert result["meet_url"] is None
        assert "conference" not in gcreate.call_args.kwargs
        assert "conferenceData" not in gcreate.call_args.args[2]


class TestUpdateEventWithMeet:
    @pytest.mark.asyncio
    async def test_add_meet_only_sends_conference_data_only(self):
        from app.services.calendar_service import update_event

        db = AsyncMock()
        db.commit = AsyncMock()
        row = MagicMock()
        row.first = MagicMock(return_value=("g1", None))
        sync = MagicMock()
        sync.first = MagicMock(return_value=("bidirectional",))
        db.execute = AsyncMock(side_effect=[row, sync, MagicMock()])

        gupdate = AsyncMock(return_value={"id": "g1", "hangoutLink": MEET})
        with patch("app.services.google_calendar.update_event", gupdate):
            result = await update_event(db, tenant_id=1, event_id=9, user_id=3, payload={"add_meet": True})
        assert result == {"id": 9, "meet_url": MEET}
        body = gupdate.call_args.args[3]
        assert list(body) == ["conferenceData"]
        for key in ("summary", "start", "end"):
            assert key not in body
        assert gupdate.call_args.kwargs["conference"] is True
        assert db.execute.call_args_list[2].args[1] == {"url": MEET, "id": 9}

    @pytest.mark.asyncio
    async def test_update_with_fields_and_meet_sends_full_body_plus_conference(self):
        from app.services.calendar_service import update_event

        db = AsyncMock()
        db.commit = AsyncMock()
        geid = MagicMock()
        geid.first = MagicMock(return_value=("g1", None))
        sync = MagicMock()
        sync.first = MagicMock(return_value=("bidirectional",))
        db.execute = AsyncMock(side_effect=[MagicMock(), geid, sync, MagicMock(), MagicMock()])

        gupdate = AsyncMock(return_value={"id": "g1", "hangoutLink": MEET})
        with patch("app.services.google_calendar.update_event", gupdate):
            result = await update_event(
                db, tenant_id=1, event_id=9, user_id=3, payload={"title": "題", "add_meet": True}
            )
        assert result == {"id": 9, "meet_url": MEET}
        body = gupdate.call_args.args[3]
        assert body["summary"] == "題"
        assert "createRequest" in body["conferenceData"]
        assert gupdate.call_args.kwargs["conference"] is True

    @pytest.mark.asyncio
    async def test_update_returns_existing_meet_url(self):
        from app.services.calendar_service import update_event

        db = AsyncMock()
        db.commit = AsyncMock()
        geid = MagicMock()
        geid.first = MagicMock(return_value=(None, MEET))
        sync = MagicMock()
        sync.first = MagicMock(return_value=("none",))
        db.execute = AsyncMock(side_effect=[MagicMock(), geid, sync])
        result = await update_event(db, tenant_id=1, event_id=9, user_id=3, payload={"title": "題"})
        assert result == {"id": 9, "meet_url": MEET}


class TestUpsertMeetUrl:
    @pytest.mark.asyncio
    async def test_hangout_link_is_saved(self):
        from app.services.calendar_service import upsert_from_google

        db = AsyncMock()
        origin_result = MagicMock()
        origin_result.first = MagicMock(return_value=None)
        db.execute = AsyncMock(side_effect=[origin_result, MagicMock()])
        out = await upsert_from_google(
            db,
            tenant_id=1,
            google_event={
                "id": "ev1",
                "summary": "Meet 付き",
                "hangoutLink": MEET,
                "start": {"dateTime": "2026-06-01T10:00:00+09:00"},
                "end": {"dateTime": "2026-06-01T11:00:00+09:00"},
            },
            owner_user_id=9,
        )
        assert out == "upserted"
        stmt, params = db.execute.call_args_list[1].args
        assert params["meet_url"] == MEET
        assert "meet_url         = EXCLUDED.meet_url" in stmt.text
        assert "WHERE calendar_events.source = 'google'" in stmt.text

    @pytest.mark.asyncio
    async def test_no_hangout_link_is_null(self):
        from app.services.calendar_service import upsert_from_google

        db = AsyncMock()
        origin_result = MagicMock()
        origin_result.first = MagicMock(return_value=None)
        db.execute = AsyncMock(side_effect=[origin_result, MagicMock()])
        await upsert_from_google(
            db,
            tenant_id=1,
            google_event={
                "id": "ev2",
                "start": {"dateTime": "2026-06-01T10:00:00+09:00"},
                "end": {"dateTime": "2026-06-01T11:00:00+09:00"},
            },
            owner_user_id=9,
        )
        assert db.execute.call_args_list[1].args[1]["meet_url"] is None


class TestListEventsMeetUrl:
    @pytest.mark.asyncio
    async def test_meet_url_is_last_column(self):
        from app.services.calendar_service import list_events

        now = datetime(2026, 6, 1, 10, 0, 0, tzinfo=timezone.utc)
        row = (1, 2, "shared", "meeting", "会議", None, None, now, now, False, None, "app", "synced", 2, now, now, "鈴木", "田中", MEET, None, None, None)
        db = _make_db(fetchall_return=[row])
        result = await list_events(db, tenant_id=1, start="2026-06-01", end="2026-06-30")
        assert result[0]["meet_url"] == MEET
        assert result[0]["created_by_name"] == "田中"
        sql = db.execute.call_args.args[0].text
        assert sql.index("created_by_name") < sql.index("ce.meet_url")


# ===========================================================================
# 便15A: 予定の繰り返し（ADR-1075）
# ===========================================================================

import contextlib  # noqa: E402
from datetime import timedelta  # noqa: E402
from zoneinfo import ZoneInfo  # noqa: E402

_JST = ZoneInfo("Asia/Tokyo")


def _jt(y, mo, d, h=10, mi=0):
    return datetime(y, mo, d, h, mi, tzinfo=_JST)


class _Res:
    def __init__(self, rows):
        self._rows = rows

    def first(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return list(self._rows)

    def scalar_one(self):
        return self._rows[0][0]


class _FakeDB:
    """実行された SQL を順に記録し、文に含まれる文字で行を返す偽の接続。"""

    def __init__(self, handlers=(), sync_mode="bidirectional"):
        self.calls: list[tuple[str, dict]] = []
        self.handlers = list(handlers)
        if sync_mode is not None:
            self.handlers.append(("tenant_google_calendar_config", [(sync_mode,)]))
        self.commit = AsyncMock()

    async def execute(self, stmt, params=None):
        sql = stmt.text if hasattr(stmt, "text") else str(stmt)
        self.calls.append((sql, params or {}))
        for needle, rows in self.handlers:
            if needle in sql:
                return _Res(rows)
        return _Res([])

    def find(self, needle):
        return [(i, s, p) for i, (s, p) in enumerate(self.calls) if needle in s]


def _ev(**over) -> dict:
    d = {
        "created_by_user_id": 5, "calendar_type": "shared", "user_id": 5, "google_event_id": "gm",
        "meet_url": None, "id": 1, "source": "app", "recurrence_rule": "FREQ=WEEKLY;BYDAY=TH",
        "recurring_event_id": None, "original_start_datetime": None,
        "start_datetime": _jt(2026, 11, 12), "end_datetime": _jt(2026, 11, 12, 11),
        "is_all_day": False, "is_cancelled": False, "title": "定例", "description": None,
        "location": None, "category": "meeting",
    }
    d.update(over)
    return d


def _tup(ev: dict) -> tuple:
    from app.services.calendar_service import EVENT_COLUMNS

    return tuple(ev[c] for c in EVENT_COLUMNS)


def _exc(**over) -> dict:
    """2026-11-26 の回の例外の行（id 9・元の行 1）。"""
    return _ev(
        id=9, recurrence_rule=None, recurring_event_id=1, original_start_datetime=_jt(2026, 11, 26),
        start_datetime=_jt(2026, 11, 26, 14), end_datetime=_jt(2026, 11, 26, 15),
        google_event_id="gx", **over,
    )


class _G:
    """Google の呼び口の偽物。送った順と引数を log に残す。"""

    def __init__(self, fail=lambda name, args: False):
        self.log: list[tuple] = []
        self.fail = fail

    def fn(self, name, ret):
        async def f(*args, **kwargs):
            self.log.append((name,) + args[2:])
            if self.fail(name, args[2:]):
                raise RuntimeError("boom")
            return ret

        return f

    def names(self):
        return [entry[0] for entry in self.log]


@contextlib.contextmanager
def _google(g: _G):
    with patch("app.services.google_calendar.update_event", new=g.fn("update_event", {"id": "gu"})), patch(
        "app.services.google_calendar.create_event", new=g.fn("create_event", {"id": "gnew"})
    ), patch("app.services.google_calendar.delete_event", new=g.fn("delete_event", None)), patch(
        "app.services.google_calendar.get_instance", new=g.fn("get_instance", {"id": "ginst"})
    ), patch("app.services.calendar_service.reset_tenant_context", new=AsyncMock()):
        yield


def _master_db(master=None, exceptions=(), exc_row=None, new_id=77, **kw):
    master = master or _ev()
    handlers = [
        ("SELECT google_event_id FROM calendar_events WHERE recurring_event_id", [(g,) for g in exceptions]),
        ("original_start_datetime = :orig", [_tup(exc_row)] if exc_row else []),
        ("INSERT INTO calendar_events", [(new_id,)]),
        ("WHERE id = :id", [_tup(master)]),
    ]
    return _FakeDB(handlers, **kw)


def _statuses(db, status):
    return [p.get("id") for _i, s, p in db.find(f"sync_status = '{status}'")]


class TestListRecurrence:
    def _master_row(self, **over):
        now = _jt(2026, 11, 12)
        base = [1, 5, "shared", "meeting", "定例", None, None, now, now + timedelta(hours=1), False,
                "gm", "app", "synced", 5, now, now, "鈴木", "田中", None,
                "FREQ=WEEKLY;BYDAY=TH", None, None]
        for k, v in over.items():
            base[k] = v
        return tuple(base)

    @pytest.mark.asyncio
    async def test_weekly_master_expands(self):
        from app.services.calendar_service import list_events

        db = _FakeDB([("SELECT ce.id", [self._master_row()])], sync_mode=None)
        out = await list_events(db, 1, start="2026-11-01T00:00:00+09:00", end="2026-12-01T00:00:00+09:00")
        starts = [o["start_datetime"][:16] for o in out]
        assert starts == ["2026-11-12T10:00", "2026-11-19T10:00", "2026-11-26T10:00"]
        assert all(o["occurrence_start"] == o["start_datetime"] and o["id"] == 1 for o in out)
        assert all(o["recurring_event_id"] == 1 and o["recurrence"] == "weekly" for o in out)
        assert out[0]["end_datetime"][:16] == "2026-11-12T11:00"

    @pytest.mark.asyncio
    async def test_exception_replaces_occurrence(self):
        from app.services.calendar_service import list_events

        exc_start = _jt(2026, 11, 26, 14)
        exc_row = self._master_row()
        exc_row = list(exc_row)
        exc_row[0], exc_row[7], exc_row[8] = 9, exc_start, exc_start + timedelta(hours=1)
        exc_row[19], exc_row[20], exc_row[21] = None, 1, _jt(2026, 11, 26)
        handlers = [
            ("SELECT ce.recurring_event_id, ce.original_start_datetime", [(1, _jt(2026, 11, 26))]),
            ("SELECT ce.id", [self._master_row(), tuple(exc_row)]),
        ]
        db = _FakeDB(handlers, sync_mode=None)
        out = await list_events(db, 1, start="2026-11-01T00:00:00+09:00", end="2026-12-01T00:00:00+09:00")
        assert [o["start_datetime"][:16] for o in out] == [
            "2026-11-12T10:00", "2026-11-19T10:00", "2026-11-26T14:00",
        ]
        last = out[-1]
        assert last["id"] == 9 and last["occurrence_start"].startswith("2026-11-26T10:00")
        assert last["recurrence"] == "weekly"

    @pytest.mark.asyncio
    async def test_sql_shape_and_cancelled_not_returned(self):
        from app.services.calendar_service import list_events

        db = _FakeDB([("SELECT ce.id", [self._master_row()])], sync_mode=None)
        await list_events(db, 1, start="2026-11-01T00:00:00+09:00", end="2026-12-01T00:00:00+09:00", user_id=5)
        main = db.calls[0][0]
        assert "(ce.start_datetime < :end AND ce.end_datetime > :start AND ce.recurrence_rule IS NULL) OR" in main
        assert "ce.(" not in main
        assert "AND NOT ce.is_cancelled" in main
        assert main.index("ce.user_id = :me") < main.index("AND NOT ce.is_cancelled")
        assert "ce.recurrence_rule, ce.recurring_event_id, ce.original_start_datetime" in main

    @pytest.mark.asyncio
    async def test_exception_requery_has_visibility(self):
        from app.services.calendar_service import list_events

        db = _FakeDB([("SELECT ce.id", [self._master_row()])], sync_mode=None)
        await list_events(db, 1, start="2026-11-01T00:00:00+09:00", end="2026-12-01T00:00:00+09:00", user_id=5)
        sql, params = db.calls[1]
        assert "ce.recurring_event_id = ANY(:ids)" in sql
        assert "(ce.calendar_type = 'shared' OR ce.user_id = :me)" in sql
        assert "is_cancelled" not in sql  # 消した印の行も含めて引く
        assert params["ids"] == [1] and params["me"] == 5

        db = _FakeDB([("SELECT ce.id", [self._master_row()])], sync_mode=None)
        await list_events(db, 1, start="2026-11-01T00:00:00+09:00", end="2026-12-01T00:00:00+09:00")
        assert "ce.calendar_type = 'shared'" in db.calls[1][0] and ":me" not in db.calls[1][0]

    @pytest.mark.asyncio
    async def test_search_does_not_expand(self):
        from app.services.calendar_service import list_events

        db = _FakeDB([("SELECT ce.id", [self._master_row()])], sync_mode=None)
        out = await list_events(db, 1, user_id=5, title_query="定例", limit=10)
        assert len(db.calls) == 1
        assert "ce.recurrence_rule IS NULL" not in db.calls[0][0]
        assert len(out) == 1 and out[0]["occurrence_start"] is None and out[0]["recurrence"] == "weekly"

    @pytest.mark.asyncio
    async def test_is_first_occurrence_on_expanded(self):
        from app.services.calendar_service import list_events

        db = _FakeDB([("SELECT ce.id", [self._master_row()])], sync_mode=None)
        out = await list_events(db, 1, start="2026-11-01T00:00:00+09:00", end="2026-12-01T00:00:00+09:00")
        assert [o["is_first_occurrence"] for o in out] == [True, False, False]

    @pytest.mark.asyncio
    async def test_is_first_occurrence_missing_master(self):
        from app.services.calendar_service import list_events

        first = list(self._master_row())
        first[19], first[20], first[21] = None, 1, _jt(2026, 11, 12)
        second = list(self._master_row())
        second[0], second[7], second[8] = 9, _jt(2026, 11, 19), _jt(2026, 11, 19, 11)
        second[19], second[20], second[21] = None, 1, _jt(2026, 11, 19)
        handlers = [
            (
                "SELECT id, recurrence_rule, start_datetime, is_all_day",
                [(1, "FREQ=WEEKLY;BYDAY=TH", _jt(2026, 11, 12), False)],
            ),
            ("SELECT ce.id", [tuple(first), tuple(second)]),
        ]
        db = _FakeDB(handlers, sync_mode=None)
        out = await list_events(db, 1, start="2026-11-01T00:00:00+09:00", end="2026-12-01T00:00:00+09:00")
        assert len(out) == 2
        assert [o["is_first_occurrence"] for o in out] == [True, False]
        assert all(o["recurrence"] == "weekly" for o in out)

    @pytest.mark.asyncio
    async def test_is_first_occurrence_single_and_search(self):
        from app.services.calendar_service import list_events

        single = list(self._master_row())
        single[19], single[20] = None, None
        db = _FakeDB([("SELECT ce.id", [tuple(single)])], sync_mode=None)
        out = await list_events(db, 1, start="2026-11-01T00:00:00+09:00", end="2026-12-01T00:00:00+09:00")
        assert len(out) == 1 and out[0]["is_first_occurrence"] is False

        db = _FakeDB([("SELECT ce.id", [self._master_row()])], sync_mode=None)
        out = await list_events(db, 1, user_id=5, title_query="定例", limit=10)
        assert len(out) == 1 and out[0]["is_first_occurrence"] is True


class TestCreateRecurrence:
    @pytest.mark.asyncio
    async def test_rule_saved_and_sent_to_google(self):
        from app.services.calendar_service import create_event

        db = _FakeDB([("INSERT INTO calendar_events", [(31,)])], sync_mode=None)
        g = _G()
        payload = {
            "title": "定例", "start_datetime": "2026-11-12T10:00:00+09:00",
            "end_datetime": "2026-11-12T11:00:00+09:00", "recurrence": "weekly",
        }
        with _google(g), patch("app.services.calendar_service.can_add_meet", new=AsyncMock(return_value=True)):
            await create_event(db, 1, 5, payload)
        insert = db.find("INSERT INTO calendar_events")[0]
        assert "recurrence_rule" in insert[1] and insert[2]["rrule"] == "FREQ=WEEKLY;BYDAY=TH"
        body = g.log[0][1]
        assert g.names() == ["create_event"] and body["recurrence"] == ["RRULE:FREQ=WEEKLY;BYDAY=TH"]

    @pytest.mark.asyncio
    async def test_no_recurrence_keeps_null(self):
        from app.services.calendar_service import create_event

        db = _FakeDB([("INSERT INTO calendar_events", [(31,)])], sync_mode=None)
        payload = {"title": "単発", "start_datetime": "2026-11-12T10:00:00+09:00",
                   "end_datetime": "2026-11-12T11:00:00+09:00"}
        with _google(_G()), patch("app.services.calendar_service.can_add_meet", new=AsyncMock(return_value=False)):
            await create_event(db, 1, 5, payload)
        assert db.find("INSERT INTO calendar_events")[0][2]["rrule"] is None


OCC = _jt(2026, 11, 26).isoformat()


class TestUpdateRecurring:
    async def _run(self, db, event, payload, scope, g=None, occ=None):
        from app.services.calendar_service import update_recurring_event

        g = g or _G()
        with _google(g):
            result = await update_recurring_event(
                db, 1, 5, event, payload, scope, occ or _jt(2026, 11, 26)
            )
        return result, g

    @pytest.mark.asyncio
    async def test_a_single_to_recurring_recreates_in_google(self):
        single = _ev(recurrence_rule=None, google_event_id="gs", id=3)
        db = _FakeDB([], sync_mode="bidirectional")
        result, g = await self._run(db, single, {"recurrence": "weekly"}, None)
        upd = db.find("UPDATE calendar_events SET")[0]
        assert "sync_status = 'pending'" in upd[1] and upd[2]["f_recurrence_rule"] == "FREQ=WEEKLY;BYDAY=TH"
        assert g.names() == ["delete_event", "create_event"] and g.log[0][1] == "gs"
        assert g.log[1][1]["recurrence"] == ["RRULE:FREQ=WEEKLY;BYDAY=TH"]
        assert result["id"] == 3 and 3 in _statuses(db, "synced")

    @pytest.mark.asyncio
    async def test_b_this_inserts_exception_and_patches_instance(self):
        db = _master_db()
        result, g = await self._run(db, _ev(), {"title": "この回だけ"}, "this")
        ins = db.find("INSERT INTO calendar_events")[0][2]
        assert ins["recurring_event_id"] == 1 and ins["original_start_datetime"] == _jt(2026, 11, 26)
        assert ins["title"] == "この回だけ" and ins["is_cancelled"] is False
        assert g.names() == ["get_instance", "update_event"]
        assert g.log[0][1:] == ("gm", _jt(2026, 11, 26), False)
        assert g.log[1][1] == "ginst" and "recurrence" not in g.log[1][2]
        synced = db.find("sync_status = 'synced'")[0][2]
        assert synced["id"] == 77 and synced["gid"] == "ginst" and synced["oid"] == "app:1:77"
        assert result["id"] == 77

    @pytest.mark.asyncio
    async def test_b_this_patch_failure_marks_failed(self):
        db = _master_db()
        g = _G(fail=lambda n, a: n == "update_event")
        await self._run(db, _ev(), {"title": "x"}, "this", g=g)
        assert 77 in _statuses(db, "failed") and 77 not in _statuses(db, "synced")

    @pytest.mark.asyncio
    async def test_b2_this_existing_exception_updates_row(self):
        db = _master_db(exc_row=_exc())
        result, g = await self._run(db, _ev(), {"title": "更新"}, "this")
        upd = db.find("UPDATE calendar_events SET")[0]
        assert upd[2]["id"] == 9 and upd[2]["f_title"] == "更新" and "sync_status = 'pending'" in upd[1]
        assert db.find("INSERT INTO calendar_events") == []
        assert g.names() == ["update_event"] and g.log[0][1] == "gx"
        assert result["id"] == 9

    @pytest.mark.asyncio
    async def test_c_following_cuts_and_creates(self):
        db = _master_db(exceptions=["ge1", "ge2"])
        result, g = await self._run(db, _ev(), {"title": "これ以降"}, "following")
        cut = db.find("SET recurrence_rule = :r")[0]
        assert cut[2]["r"] == "FREQ=WEEKLY;BYDAY=TH;UNTIL=20261125T145959Z" and cut[2]["id"] == 1
        read_idx = db.find("SELECT google_event_id FROM calendar_events WHERE recurring_event_id")[0][0]
        del_idx = db.find("DELETE FROM calendar_events")[0][0]
        assert read_idx < del_idx
        assert db.find("DELETE FROM calendar_events")[0][2]["occ"] == _jt(2026, 11, 26)
        ins = db.find("INSERT INTO calendar_events")[0][2]
        assert ins["recurrence_rule"] == "FREQ=WEEKLY;BYDAY=TH" and ins["title"] == "これ以降"
        assert ins["start_datetime"] == _jt(2026, 11, 26)
        assert g.names() == ["update_event", "update_event", "update_event", "create_event"]
        assert [e[1] for e in g.log[:3]] == ["ge1", "ge2", "gm"]
        assert g.log[0][2] == {"status": "cancelled"}
        assert g.log[2][2] == {"recurrence": ["RRULE:FREQ=WEEKLY;BYDAY=TH;UNTIL=20261125T145959Z"]}
        assert sorted(_statuses(db, "synced")) == [1, 77] and result["id"] == 77

    @pytest.mark.asyncio
    async def test_c_patch_failure_inserts_no_google_and_both_failed(self):
        db = _master_db()
        g = _G(fail=lambda n, a: n == "update_event" and a[1].get("recurrence"))
        await self._run(db, _ev(), {"title": "x"}, "following", g=g)
        assert "create_event" not in g.names()
        assert sorted(_statuses(db, "failed")) == [1, 77] and _statuses(db, "synced") == []

    @pytest.mark.asyncio
    async def test_c_insert_failure_only_new_row_failed(self):
        db = _master_db()
        g = _G(fail=lambda n, a: n == "create_event")
        await self._run(db, _ev(), {"title": "x"}, "following", g=g)
        assert _statuses(db, "synced") == [1] and _statuses(db, "failed") == [77]

    @pytest.mark.asyncio
    async def test_d1_all_patches_without_recurrence(self):
        db = _master_db()
        result, g = await self._run(db, _ev(), {"title": "全部"}, "all")
        ups = db.find("UPDATE calendar_events SET")
        assert any(p["id"] == 1 and p["f_title"] == "全部" and "recurring_event_id" not in s for _i, s, p in ups)
        assert any("recurring_event_id = :id" in s and p["f_title"] == "全部" for _i, s, p in ups)
        assert g.names() == ["update_event"] and g.log[0][1] == "gm"
        assert "recurrence" not in g.log[0][2] and g.log[0][2]["summary"] == "全部"
        assert _statuses(db, "synced") == [1] and result["id"] == 1

    @pytest.mark.asyncio
    async def test_d1_patch_failure_marks_failed(self):
        db = _master_db()
        await self._run(db, _ev(), {"title": "x"}, "all", g=_G(fail=lambda n, a: True))
        assert _statuses(db, "failed") == [1]

    @pytest.mark.asyncio
    async def test_d1_moved_exception_title_only(self):
        db = _master_db()
        exc = _exc()
        payload = {"title": "題名", "start_datetime": exc["start_datetime"].isoformat()}
        _r, g = await self._run(db, exc, payload, "all")
        assert g.names() == ["update_event"] and g.log[0][1] == "gm"
        assert db.find("DELETE FROM calendar_events") == []

    @pytest.mark.asyncio
    async def test_d2_all_time_change_recreates(self):
        db = _master_db(exceptions=["ge1"])
        payload = {"start_datetime": _jt(2026, 11, 26, 11).isoformat(), "end_datetime": _jt(2026, 11, 26, 12).isoformat()}
        result, g = await self._run(db, _ev(), payload, "all")
        upd = [p for _i, s, p in db.find("UPDATE calendar_events SET") if p.get("id") == 1][0]
        assert upd["f_start_datetime"] == _jt(2026, 11, 12, 11) and upd["f_end_datetime"] == _jt(2026, 11, 12, 12)
        assert upd["f_recurrence_rule"] == "FREQ=WEEKLY;BYDAY=TH"
        assert db.find("DELETE FROM calendar_events")[0][2] == {"mid": 1}
        assert g.names() == ["update_event", "delete_event", "create_event"]
        assert g.log[0][1:] == ("ge1", {"status": "cancelled"}) and g.log[1][1] == "gm"
        assert g.log[2][1]["recurrence"] == ["RRULE:FREQ=WEEKLY;BYDAY=TH"]
        assert _statuses(db, "synced") == [1] and result["id"] == 1

    @pytest.mark.asyncio
    async def test_d2_moved_exception_shifts_master_from_pressed_occurrence(self):
        exc = {**_exc(), "start_datetime": _jt(2026, 11, 27, 10), "end_datetime": _jt(2026, 11, 27, 11)}
        db = _master_db(exc_row=exc)
        payload = {"start_datetime": _jt(2026, 11, 27, 11).isoformat(), "end_datetime": _jt(2026, 11, 27, 12).isoformat()}
        await self._run(db, exc, payload, "all", occ=_jt(2026, 11, 26))
        upd = [p for _i, s, p in db.find("UPDATE calendar_events SET") if p.get("id") == 1][0]
        assert upd["f_start_datetime"] == _jt(2026, 11, 13, 11) and upd["f_end_datetime"] == _jt(2026, 11, 13, 12)

    @pytest.mark.asyncio
    async def test_d2_recreate_delete_failure(self):
        db = _master_db()
        g = _G(fail=lambda n, a: n == "delete_event")
        await self._run(db, _ev(), {"recurrence": "daily"}, "all", g=g)
        assert "create_event" not in g.names() and _statuses(db, "failed") == [1]
        assert not any("google_event_id = NULL" in s for _i, s, _p in db.find("sync_status = 'failed'"))

    @pytest.mark.asyncio
    async def test_d2_recreate_create_failure_clears_ids(self):
        db = _master_db()
        g = _G(fail=lambda n, a: n == "create_event")
        await self._run(db, _ev(), {"recurrence": "daily"}, "all", g=g)
        failed = db.find("sync_status = 'failed'")
        assert len(failed) == 1 and "google_event_id = NULL, sync_origin_id = NULL" in failed[0][1]

    @pytest.mark.asyncio
    async def test_d3_all_none_to_single(self):
        db = _master_db(exceptions=["ge1"])
        _r, g = await self._run(db, _ev(), {"recurrence": "none"}, "all")
        upd = [p for _i, s, p in db.find("UPDATE calendar_events SET") if p.get("id") == 1][0]
        assert upd["f_recurrence_rule"] is None
        assert db.find("DELETE FROM calendar_events")[0][2] == {"mid": 1}
        assert g.names() == ["update_event", "delete_event", "create_event"]
        assert "recurrence" not in g.log[2][1]

    @pytest.mark.asyncio
    async def test_update_all_none_keeps_pressed_occurrence(self):
        db = _master_db()
        await self._run(db, _ev(), {"recurrence": "none"}, "all")
        upd = [p for _i, s, p in db.find("UPDATE calendar_events SET") if p.get("id") == 1][0]
        assert upd["f_start_datetime"] == _jt(2026, 11, 26) and upd["f_end_datetime"] == _jt(2026, 11, 26, 11)

        db = _master_db()
        payload = {"recurrence": "none", "start_datetime": _jt(2026, 11, 27, 9).isoformat(),
                   "end_datetime": _jt(2026, 11, 27, 10).isoformat()}
        await self._run(db, _ev(), payload, "all")
        upd = [p for _i, s, p in db.find("UPDATE calendar_events SET") if p.get("id") == 1][0]
        assert upd["f_start_datetime"] == _jt(2026, 11, 27, 9) and upd["f_end_datetime"] == _jt(2026, 11, 27, 10)

    @pytest.mark.asyncio
    async def test_send_ok_false_sends_nothing(self):
        for master, mode in ((_ev(), "none"), (_ev(google_event_id=None), "bidirectional")):
            for scope, payload in (("this", {"title": "x"}), ("following", {"title": "x"}),
                                   ("all", {"title": "x"}), ("all", {"recurrence": "daily"})):
                db = _master_db(master=master, sync_mode=mode)
                _r, g = await self._run(db, master, payload, scope)
                assert g.log == []
                assert _statuses(db, "synced") == [] and _statuses(db, "failed") == []

    @pytest.mark.asyncio
    async def test_cancel_failure_does_not_stop_the_rest(self):
        db = _master_db(exceptions=["ge1", "ge2"])
        g = _G(fail=lambda n, a: a[0] == "ge1")
        await self._run(db, _ev(), {"recurrence": "daily"}, "all", g=g)
        assert [e[1] for e in g.log[:2]] == ["ge1", "ge2"]
        assert g.names()[2:] == ["delete_event", "create_event"]

    @pytest.mark.asyncio
    async def test_update_and_delete_exception_id_routes_to_master(self):
        from app.services.calendar_service import delete_recurring_event

        # 直す: following（1 回目でない）は元の行を切って新しい行を作る
        db = _master_db()
        exc = _exc()
        _r, g = await self._run(db, exc, {"title": "x"}, "following")
        assert db.find("SET recurrence_rule = :r")[0][2]["id"] == 1
        assert ("update_event", "gm") == g.log[0][:2] or any(e[1] == "gm" for e in g.log)
        assert not any(e[1] == "gx" and e[0] != "update_event" for e in g.log)
        # 直す: all
        db = _master_db()
        _r, g = await self._run(db, _exc(), {"title": "x"}, "all")
        assert g.log[0][1] == "gm"
        titled = [p["id"] for _i, s, p in db.find("UPDATE calendar_events SET") if "f_title" in p and "recurring_event_id" not in s]
        assert titled == [1]
        # 消す: all は元の行を消す
        db = _master_db()
        g = _G()
        with _google(g):
            await delete_recurring_event(db, 1, _exc(), "all", _jt(2026, 11, 26))
        assert db.find("DELETE FROM calendar_events WHERE id = :id")[0][2] == {"id": 1}
        assert g.names()[-1] == "delete_event" and g.log[-1][1] == "gm"
        # 消す: following
        db = _master_db()
        g = _G()
        with _google(g):
            await delete_recurring_event(db, 1, _exc(), "following", _jt(2026, 11, 26))
        assert db.find("SET recurrence_rule = :r")[0][2]["id"] == 1
        assert g.log[-1][1] == "gm"

    @pytest.mark.asyncio
    async def test_send_ok_new_rows_synced(self):
        db = _master_db()
        _r, g = await self._run(db, _ev(), {"title": "x"}, "following")
        assert g.names().count("create_event") == 1 and 77 in _statuses(db, "synced")
        db = _master_db()
        _r, g = await self._run(db, _ev(), {"title": "x"}, "this")
        assert g.names().count("get_instance") == 1 and g.names().count("update_event") == 1
        assert 77 in _statuses(db, "synced")


class TestDeleteRecurring:
    async def _run(self, db, event, scope, g=None):
        from app.services.calendar_service import delete_recurring_event

        g = g or _G()
        with _google(g):
            await delete_recurring_event(db, 1, event, scope, _jt(2026, 11, 26))
        return g

    @pytest.mark.asyncio
    async def test_this_inserts_cancelled_exception(self):
        db = _master_db()
        g = await self._run(db, _ev(), "this")
        ins = db.find("INSERT INTO calendar_events")[0][2]
        assert ins["is_cancelled"] is True and ins["original_start_datetime"] == _jt(2026, 11, 26)
        assert g.names() == ["get_instance", "update_event"]
        assert g.log[1][1:] == ("ginst", {"status": "cancelled"})
        ids = db.find("SET google_event_id = :gid, sync_origin_id = :oid WHERE id = :id")[0][2]
        assert ids["gid"] == "ginst" and ids["id"] == 77

    @pytest.mark.asyncio
    async def test_this_existing_exception_marked_cancelled(self):
        db = _master_db(exc_row=_exc())
        g = await self._run(db, _ev(), "this")
        assert db.find("INSERT INTO calendar_events") == []
        assert "is_cancelled = true" in db.find("UPDATE calendar_events SET is_cancelled")[0][1]
        assert g.log == [("update_event", "gx", {"status": "cancelled"})]

    @pytest.mark.asyncio
    async def test_following_cuts_without_insert(self):
        db = _master_db(exceptions=["ge1", "ge2"])
        g = await self._run(db, _ev(), "following")
        assert db.find("INSERT INTO calendar_events") == []
        assert g.names() == ["update_event"] * 3
        assert [e[1] for e in g.log] == ["ge1", "ge2", "gm"]
        assert g.log[2][2] == {"recurrence": ["RRULE:FREQ=WEEKLY;BYDAY=TH;UNTIL=20261125T145959Z"]}

    @pytest.mark.asyncio
    async def test_all_cancels_exceptions_then_deletes(self):
        db = _master_db(exceptions=["ge1", "ge2"])
        g = await self._run(db, _ev(), "all")
        assert g.names() == ["update_event", "update_event", "delete_event"]
        assert g.log[2][1] == "gm"
        read_idx = db.find("SELECT google_event_id FROM calendar_events WHERE recurring_event_id")[0][0]
        del_idx = db.find("DELETE FROM calendar_events WHERE id = :id")[0][0]
        assert read_idx < del_idx

    @pytest.mark.asyncio
    async def test_failures_never_change_sync_status(self):
        for scope in ("this", "following", "all"):
            db = _master_db(exceptions=["ge1"])
            await self._run(db, _ev(), scope, g=_G(fail=lambda n, a: True))
            assert _statuses(db, "failed") == [] and _statuses(db, "synced") == []


class TestUpsertRecurringInstance:
    @pytest.mark.asyncio
    async def test_instance_of_app_origin_is_skipped(self):
        from app.services.calendar_service import upsert_from_google

        db = _make_db()
        event = {"id": "gm_20261126T010000Z", "recurringEventId": "gm",
                 "start": {"dateTime": "2026-11-26T10:00:00+09:00"}, "end": {"dateTime": "2026-11-26T11:00:00+09:00"}}
        with patch("app.services.calendar_service._is_app_origin", new=AsyncMock(side_effect=[False, True])) as origin:
            assert await upsert_from_google(db, 1, event, 5) == "skipped"
        assert origin.await_args_list[1].args[1] == "gm"
        db.execute.assert_not_called()


class TestCheckRecurrenceRequest:
    async def _check(self, event, payload, scope, occ, db=None):
        from app.services.calendar_service import check_recurrence_request

        db = db or _master_db(master=_ev())
        return await check_recurrence_request(db, event=event, payload=payload, scope=scope, occurrence_start=occ)

    @pytest.mark.asyncio
    async def test_all_eight_identifiers(self):
        single = _ev(recurrence_rule=None)
        master = _ev()
        # recurrence_meet_not_allowed
        assert await self._check(master, {"add_meet": True}, "all", OCC) == "recurrence_meet_not_allowed"
        assert await self._check(_ev(recurrence_rule=None, meet_url="u"), {"recurrence": "weekly"}, None, None) == "recurrence_meet_not_allowed"
        # recurrence_not_available（第 5 木曜）
        fifth = _ev(recurrence_rule=None, start_datetime=_jt(2026, 10, 29), end_datetime=_jt(2026, 10, 29, 11))
        assert await self._check(fifth, {"recurrence": "monthly_nth"}, None, None) == "recurrence_not_available"
        # recurrence_scope_not_allowed
        assert await self._check(single, {"title": "x"}, "this", OCC) == "recurrence_scope_not_allowed"
        # recurrence_scope_required
        assert await self._check(master, {"title": "x"}, None, OCC) == "recurrence_scope_required"
        # recurrence_occurrence_invalid
        assert await self._check(master, {"title": "x"}, "all", None) == "recurrence_occurrence_invalid"
        assert await self._check(master, {"title": "x"}, "all", "bad") == "recurrence_occurrence_invalid"
        assert await self._check(master, {"title": "x"}, "all", _jt(2026, 11, 27).isoformat()) == "recurrence_occurrence_invalid"
        exc = _exc()
        assert await self._check(exc, {"title": "x"}, "this", _jt(2026, 11, 19).isoformat()) == "recurrence_occurrence_invalid"
        assert await self._check(exc, {"title": "x"}, "this", OCC) is None
        # recurrence_this_not_allowed
        assert await self._check(master, {"recurrence": "daily"}, "this", OCC) == "recurrence_this_not_allowed"
        assert await self._check(master, {"calendar_type": "personal"}, "this", OCC) == "recurrence_this_not_allowed"
        # recurrence_google_source
        assert await self._check(_ev(recurrence_rule=None, source="google"), {"recurrence": "weekly"}, None, None) == "recurrence_google_source"
        # recurrence_after_until
        until = _ev(recurrence_rule="FREQ=WEEKLY;BYDAY=TH;UNTIL=20261130T145959Z")
        late = {"start_datetime": _jt(2026, 12, 31).isoformat(), "end_datetime": _jt(2026, 12, 31, 11).isoformat()}
        assert await self._check(until, late, "all", OCC) == "recurrence_after_until"
        # 正常
        assert await self._check(master, {"title": "x"}, "all", OCC) is None
        assert await self._check(master, {"recurrence": "weekly"}, "this", OCC) is None
        assert await self._check(single, {"recurrence": "none"}, None, None) is None
        assert await self._check(master, None, "all", OCC) is None

    def test_create_checks(self):
        from app.services.calendar_service import check_create_recurrence

        base = {"start_datetime": "2026-11-12T10:00:00+09:00"}
        assert check_create_recurrence({**base, "recurrence": "none", "add_meet": True}) is None
        assert check_create_recurrence({**base, "recurrence": "weekly", "add_meet": True}) == "recurrence_meet_not_allowed"
        assert check_create_recurrence({"start_datetime": "2026-10-29T10:00:00+09:00", "recurrence": "monthly_nth"}) == "recurrence_not_available"
        assert check_create_recurrence({**base, "recurrence": "weekly"}) is None
