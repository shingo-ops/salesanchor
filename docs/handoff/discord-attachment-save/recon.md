# recon: attachment-storage 便3（Discord添付ファイル受信時保存）

## 調査日: 2026-09-02

---

## 1. 既存ADR検索

```
git grep -i "attachment" docs/adr/
```

- `docs/adr/ADR-091-attachment-storage.md` — 自社保管方針の根拠ADR（便1〜5の設計）
- `docs/adr/FEATURE-INDEX.md` に `attachment-storage` 索引あり

---

## 2. 起点ファイル

| ファイル | 目的 |
|---|---|
| `backend/app/discord_gateway/ticket_channel_writer.py` | チケットチャンネルの受信メッセージを `meta_messages` に保存し翻訳をenqueueする |
| `backend/app/services/discord_sender.py` | httpx パターンの参考（`_TIMEOUT_SEC`, `async with httpx.AsyncClient`） |
| `backend/app/auth/dependencies.py:255` | `set_tenant_context` / `reset_tenant_context` |
| `migrations/20260902_100000_create_lead_attachments.sql` | `lead_attachments` テーブル定義（便2・PR#3199でマージ済み） |

---

## 3. ticket_channel_writer.py の処理フロー（変更前）

```
process_ticket_channel_message
  └─ _lookup_ticket_channel_lead    # channel_id → lead
  └─ bot/webhook チェック
  └─ inbound チェック（author == discord_user_id）
  └─ _extract_first_attachment      # (url, kind) を取得
  └─ INSERT INTO meta_messages      # ON CONFLICT DO NOTHING
  └─ enqueue_inbound_translation    # 本文があれば翻訳キュー投入
```

変更後は `enqueue_inbound_translation` の前に `_save_attachment_to_disk` と `INSERT INTO lead_attachments` を挟む。

---

## 4. lead_attachments テーブル（`backend/app/discord_gateway/ticket_channel_writer.py` で使用）

```sql
-- tenant_XXX.lead_attachments（5テナント作成済み・便2で確認）
id              BIGSERIAL PRIMARY KEY
tenant_id       INTEGER NOT NULL
lead_id         BIGINT NOT NULL REFERENCES leads(id) ON DELETE CASCADE
message_id      VARCHAR(64) UNIQUE
platform        VARCHAR(32) NOT NULL
file_path       TEXT NOT NULL              -- 相対パス（ATTACHMENT_ROOT 基準）
file_size       BIGINT NOT NULL
content_type    VARCHAR(128)
original_filename TEXT
created_at      TIMESTAMPTZ DEFAULT now()
updated_at      TIMESTAMPTZ DEFAULT now()
```

---

## 5. 環境変数・定数

| 変数 | デフォルト | 説明 |
|---|---|---|
| `ATTACHMENT_ROOT` | `/data/attachments` | ホスト bind-mount ポイント（便1で追加・確認済み） |
| `_DOWNLOAD_TIMEOUT_SEC` | `30.0` | httpx タイムアウト |

---

## 6. テナント状況（2026-09-02実測）

- テナント: 001, 003, 004, 005, 006（002はスキーマなし）
- `lead_attachments` テーブル: 5テナントに作成済み
- 既存添付データ: tenant_006 に3件（CDN URLのみ保存・ファイル未保存）
- `/data/attachments`: コンテナ内に存在（空）

---

## 7. 影響範囲

- 変更ファイル: `ticket_channel_writer.py` のみ
- 呼び出し元: `backend/app/discord_gateway/event_handler.py`（`process_ticket_channel_message` を呼ぶ）
- 追加依存: `httpx`（既存 `requirements.txt` に含まれる）, `pathlib`（標準）
- DB: `lead_attachments` テーブルへの INSERT のみ（`meta_messages` の既存処理は無変更）
