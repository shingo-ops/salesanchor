# design: Discord 画像送信（attachment-storage 便6）

設計日: 2026-09-03  
参照 recon: `docs/handoff/discord-image-send/recon.md`  
参照 ADR: ADR-091 (attachment-storage), ADR-072 (reset_tenant_context)

## KGI

受信箱の Discord スレッドから画像を Discord チャンネルへ送信でき、  
送信画像が `lead_attachments` テーブルおよびディスクに保存される。

## KPI / 完了定義

| 基準 | 検証方法 |
|------|---------|
| `DISCORD_BOT_TOKEN` 未設定 → 409 | pytest `test_no_meta_config_returns_409` (messenger) / 409チェックは共通コード |
| `discord_guild_channel_id` 未設定 → 404 | pytest `test_discord_without_channel_returns_404` |
| Discord API 呼び出し成功 → 201 + `meta_messages` outbound 行 | CI pytest 全 PASS |
| 送信画像が `lead_attachments` に保存される | `test_discord_d2.py` or 結合テスト（便7以降） |
| 保存失敗時も送信成功として返す | try/except + WARNING ログ（ユニットテスト対象外・ログで確認） |

## 設計方針

### Discord API 呼び出し

既存 `discord_api_request_with_file()` (`discord_rest.py:139`) を利用。  
multipart POST で `files[0]` キーにファイルを添付。  
リトライは discord_rest.py の共通レジリエンスレイヤーに委譲。

### attachment 保存（便6）

- 受信側 (`ticket_channel_writer.py:42` `_save_attachment_to_disk`) と同一の保存形式を採用。
- 保存先: `ATTACHMENT_ROOT/tenant_{id:03d}/lead_{lead_id}/{discord_message_id}{ext}`
- `lead_attachments.message_id` は UNIQUE 制約 → `ON CONFLICT (message_id) DO NOTHING` で冪等。
- **保存失敗は警告ログのみ・送信成功扱い**（受信側と同じ設計決定）。

### meta_messages INSERT

- `direction='outbound'`, `platform='discord'`, `attachment_type='image'`
- RETURNING 未対応 SQLite 環境向けに `SELECT last_insert_rowid()` フォールバックあり。

### ADR-072 遵守

`db.commit()` 直後に `reset_tenant_context(db, tenant_id)` を実行（`leads.py:2347-2348`）。

## 外部事例

Discord Bot multipart upload: 公式ドキュメント  
`POST /channels/{channel_id}/messages` + `multipart/form-data` (`files[0]` key)  
添付ファイルは 8MB 上限（`leads.py:_MAX_IMAGE_BYTES = 8 * 1024 * 1024` で事前チェック済み）。

## 弊害・リスク

| リスク | 対策 |
|--------|------|
| Discord API 一時障害 | discord_rest.py の 5xx 指数バックオフ (最大 5回) |
| ATTACHMENT_ROOT 未設定 | デフォルト `/data/attachments`・失敗は WARNING のみ |
| message_id 重複 (リトライ時) | `ON CONFLICT (message_id) DO NOTHING` |

## 触るファイル

- `backend/app/routers/leads.py` — 送信実装 + attachment 保存ブロック追加
- `backend/tests/test_message_image_send.py` — テスト修正 (400→404, DISCORD_BOT_TOKEN patch)

## 削除するファイル

- `backend/app/routers/leads.py` — 変更あり（deletions ≥ 1）

## 8. 保存失敗の可視化（PO決定 2026-09-03・追記）

送信は成功したが自社保管だけが失敗した場合、応答に attachment_saved を含め、
画面に警告を表示する。送信自体は成功として扱う。

### 判断の根拠（外部事例）

複数のサービスにまたがる処理で一部だけが失敗する状態は
部分的な失敗と呼ばれ、広く知られた問題である。

800人以上のバックエンド技術者を対象にした2023年の調査では、
約60%がマイクロサービスに取り組んだ最初の1年で
本番環境において静かな不整合に遭遇したと報告されている。
不注意ではなく、既定のツールでは複数サービスにまたがる
原子的な操作が本質的に難しいためとされている。

APIが正常に見えながら壊れていることがあり、その典型例が
成功応答を返しているのに不完全なデータを返している場合とされている。

一括処理APIの設計指針として、複雑さが増しても
クライアントに何が成功して何が失敗したかの実行可能な情報を
渡すべきとされている。

### 我々への応用

Discord への送信は取り消せない。全体をエラーにすると
送信済みなのにエラー表示となり、再送による二重投稿を招く。

警告ログのみに留めると、画面には送信済みと出て
自社には残らない状態が静かに続く。

したがって送信は成功として扱いつつ、保管の失敗を応答に含める。

### 残る限界

失敗したことが分かるだけで、復旧手段は無い。
後から再保存する仕組みは本便に含めない。
