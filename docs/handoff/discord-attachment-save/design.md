# design: attachment-storage 便3（Discord添付ファイル受信時保存）

## 設計日: 2026-09-02

---

## 1. 関連ADR

- **ADR-091**: attachment-storage 方針（自社保管・削除ルール・容量上限）
  - 画像を自社保存する
  - 配信は認証つきAPI経由（静的公開しない）
  - テナントあたり容量上限 8GB（上限超過時は古い順に削除）
  - リード削除時に物理削除

---

## 2. 外部事例

Discord CDN の URL は期限切れ（約24時間）と投稿削除で実体が消える。  
この問題は Discord BOT 開発コミュニティで広く認識されており、  
受信時即時ダウンロード保存が標準的な対処（discord.py Issues #7557 参照）。  
S3/GCS に転送するパターンが多いが、当プロジェクトはオンプレVPS環境なので  
ローカルファイルシステム + 後段 rsync でバックアップする方式を採用（ADR-091）。

---

## 3. 設計方針

### 3-1. 失敗しても本文受信は止めない

添付ダウンロード失敗（CDN 503・タイムアウト・書き込み失敗）は WARNING ログのみ。  
`_save_attachment_to_disk` は全パスで `(None, None, None)` を返し、  
`process_ticket_channel_message` は `True` を返して正常終了とする。

### 3-2. 冪等性（ON CONFLICT DO NOTHING）

`lead_attachments.message_id` は UNIQUE 制約。  
Discord は同一イベントを稀に2回配信するが、重複 INSERT は無視される。

### 3-3. テナントスキーマ分離

既存の `_schema(tenant_id)` ヘルパーと `set_tenant_context` を使い、  
全 SQL はテナントスキーマに対して実行される。RLS も有効。

### 3-4. ファイルパス形式

```
{ATTACHMENT_ROOT}/{tenant_NNN}/lead_{id}/{message_id}{.ext}
例: /data/attachments/tenant_006/lead_1049/1234567890123456789.png
```

拡張子はアップロード時のファイル名から取得（最大10文字でクリップ）。  
ファイル名がない場合は拡張子なし。

---

## 4. 受入基準

| 基準 | 検証方法 |
|---|---|
| Discord 画像メッセージ受信時に `/data/attachments/tenant_XXX/lead_YYY/{msg_id}.{ext}` が作成される | VPS コンテナ内で `ls /data/attachments/tenant_006/lead_*` で確認 |
| `lead_attachments` テーブルに1行 INSERT される | `SELECT * FROM tenant_006.lead_attachments LIMIT 5` |
| ダウンロード失敗時も `meta_messages` には行が残り翻訳が動く | 手動テスト: CDN URL を無効化した状態でメッセージ投稿 → 受信箱に本文が表示される |
| 同一 message_id の2回目受信で重複 INSERT されない | `SELECT count(*) FROM tenant_006.lead_attachments WHERE message_id='{id}'` = 1 |
| テスト5件すべて PASSED | `pytest backend/tests/test_discord_attachment_save.py` |

---

## 5. 弊害・リスク

| リスク | 対処 |
|---|---|
| Discord CDN からのダウンロードが遅い（30s タイムアウト） | メッセージ受信 latency が最大 30s 伸びる可能性。Bot イベントループへの影響は `asyncio` 非同期処理で最小化 |
| `/data/attachments` への書き込み失敗（容量・パーミッション） | `except Exception` でキャッチしてログのみ。本文受信は継続 |
| テナント容量上限 8GB 超過 | 便5で実装。現状は超過チェックなし（ADR-091 で便5タスクとして明記） |

---

## 6. 維持の仕組み

- テスト `backend/tests/test_discord_attachment_save.py` が CI で毎回実行される
- `lead_attachments` テーブルの存在は便2の migration で保証（`ON CONFLICT DO NOTHING` で安全）
- `ATTACHMENT_ROOT` が未設定でも `/data/attachments` にフォールバック（docker-compose.yml で mount 済み）

---

## 7. 未実施（次便）

- **便4**: `/api/attachments/{id}` 認証つき配信 API（`leads.py:1275` の `get_message_attachment_url` を修正）
- **便5**: リード削除時の物理削除・容量上限超過時の古い順削除
