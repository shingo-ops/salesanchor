# 実装カード: 通知先の登録・一覧・編集で日時を文字に直す（design.md §9 改訂1）

- 設計: docs/handoff/discord-outside-ticket-notify/design.md §9（Architect 自己審査 APPROVE）
- PO 承認: 「1」（2026-11-04、内部サーバーエラーを直す）
- ブランチ: release/notification-channel-datetime（origin/main 0cf24fdc5 から）
- 触ってよいファイル（この 2 つと報告書 docs/handoff/discord-outside-ticket-notify/impl-report-channel-datetime.md だけ）:
  - backend/app/routers/notifications.py
  - backend/tests/test_notification_event_routing.py
- 触らない: DB・migrations・frontend・i18n・openapi.json・delete_channel・send_discord_notification・ChannelResponse の欄の型

## §1 backend/app/routers/notifications.py

(1) `_UPDATABLE = ...`（:64）の次の空行のあとに足す:

```python
def _channel_response(row) -> ChannelResponse:
    """行から返す形を作る。PostgreSQL は created_at を日時の型で返すので ISO の文字に直す（design.md §9）"""
    data = dict(row)
    value = data.get("created_at")
    if value is not None and not isinstance(value, str):
        data["created_at"] = value.isoformat()
    return ChannelResponse(**data)
```

(2) 置き換え（3 か所。ほかは 1 文字も変えない）:
- list_channels（:80）: `return [ChannelResponse(**row) for row in result.mappings().all()]` → `return [_channel_response(row) for row in result.mappings().all()]`
- create_channel（:103）: `return ChannelResponse(**dict(row))` → `return _channel_response(row)`
- update_channel（:136）: `return ChannelResponse(**dict(row))` → `return _channel_response(row)`

## §2 backend/tests/test_notification_event_routing.py

ファイルの末尾に足す（import はファイル内で足りないものだけ足す）:

```python
# ---------------------------------------------------------------------------
# design.md §9: PostgreSQL は created_at を日時の型で返す（SQLite は文字で返すので上の試験では見えない）
# ---------------------------------------------------------------------------

def _row(created_at):
    return {"id": 1, "channel_name": "c1", "webhook_url": "https://discord.example/webhooks/1",
            "event_types": "[]", "is_active": True, "created_at": created_at, "updated_at": None}


def test_channel_response_converts_datetime_to_iso():
    from datetime import datetime, timezone
    from app.routers.notifications import _channel_response
    dt = datetime(2026, 11, 4, 3, 0, 0, tzinfo=timezone.utc)
    assert _channel_response(_row(dt)).created_at == dt.isoformat()


def test_channel_response_keeps_string():
    from app.routers.notifications import _channel_response
    assert _channel_response(_row("2026-11-04 03:00:00")).created_at == "2026-11-04 03:00:00"
```

## §3 確かめ

- `cd backend && python -m pytest tests/test_notification_event_routing.py -q` の生出力を報告書に貼る
- 想定分岐: 既存の試験が落ちたら直さずに BLOCKED で止める。行番号がずれていたら、上の「置き換え前」の文字列で場所を探す。見つからなければ BLOCKED
