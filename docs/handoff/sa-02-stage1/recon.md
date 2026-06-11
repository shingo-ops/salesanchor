# recon — SA-02 Stage 1（チャネルマスタ + webhook配線 + エコー受信）

**仕事名**: sa-02-stage1  
**日付**: 2026-06-11  
**対象ADR**: ADR-096  
**担当**: Terminal CC（architect recon）  
**詳細**: `docs/plans/sa-progress/SA-02-plan.md` §3 に全観点の差分表あり

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `migrations/20260604_090000_create_conversation_logs.sql:34` | conversation_logs テーブル定義（原文・言語・翻訳・解析・external_message_id UNIQUE・RLS） |
| `migrations/20260604_100000_create_company_stats_view.sql:39` | v_company_stats VIEW（会話数・最終会話日時を conversation_logs から集計） |
| `backend/app/routers/webhook.py:701` | process_messenger_event — Meta Messenger/Instagram webhook 処理本体 |
| `backend/app/routers/webhook.py:717` | platform 判定（'messenger' / 'instagram'）|
| `backend/app/discord_gateway/dm_writer.py:66` | upsert_lead_and_message — Discord DM 受信 → leads + meta_messages 書き込み |
| `backend/app/discord_gateway/dm_writer.py:226` | meta_messages 冪等 INSERT（SA-02 Stage 1 で conv_logs 書き込みを追加） |
| `backend/app/services/conv_log_writer.py:29` | write_conversation_log — 新規: conversation_logs 書き込みヘルパ（Stage 1 実装） |
| `backend/app/services/conv_log_writer.py:61` | _get_company_id_for_lead — deals テーブルから company_id を補完 |
| `migrations/20260611_100000_create_channel_masters.sql:40` | channel_masters テーブル定義（connection_type auto/manual・RLS・デフォルトシード） |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | Messenger/Instagram エコー受信の有効化方法 | Meta Webhook に message_echoes 購読が必要だが現状未設定（J1判断でON決定）。アプリ設定の申請不要・Webhook 購読追加で対応可 | ✅ 解消済み（J1: ON） |
| 2 | meta_messages → conversation_logs 移行方針 | 既存データ全件移行 vs 新規のみ切替 → J2判断で全件移行決定（段階2で実施・本番GO必須） | ✅ 解消済み（J2: 全件移行） |
| 3 | 手動記録の削除可否 | J3判断で論理削除（deleted_at）決定 | ✅ 解消済み（J3: 論理削除） |
| 4 | 会話要約の集計仕様 | J4判断でv1見送り・v2へ延期 | ✅ 解消済み（J4: v2延期） |

**未解決ゼロ確認**: 全て解消済み（J1〜J4は `docs/plans/sa-progress/SA-02-design.md` §2 に記録）

---

## 補足

- **並走戦略**: Stage 1 デプロイ後、meta_messages と conversation_logs の二重書き期間が始まる。日次自動突合で差異を監視（SA-02-design.md §10 参照）。
- **既存経路への影響ゼロ**: meta_messages への書き込みは一切変更なし。conv_logs への書き込みは try/except でラップし、失敗してもWebhook処理は継続する。
- **ADR-119 流用**: lead_channels（platform VARCHAR(30)・UNIQUE(platform, external_id)）をチャネル識別基盤として流用。channel_masters は連携状態管理の追加レイヤー。
