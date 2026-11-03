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
        row = (1, 2, "shared", "meeting", "テスト会議", None, None, now, now, False, None, "app", "synced", 2, now, now, "鈴木 花子", "田中 太郎")
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
