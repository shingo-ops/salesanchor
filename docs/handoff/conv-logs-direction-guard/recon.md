# recon — conv-logs-direction-guard

**仕事名**: conv-logs-direction-guard
**日付**: 2026-06-24
**対象ADR**: ADR-110（翻訳サブシステム）
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/routers/conv_logs.py:129` | `_fire_translation` 定義: direction パラメータなし（バグ箇所） |
| `backend/app/routers/conv_logs.py:321` | `create_conv_log` から `_fire_translation` を無条件呼び出し |
| `backend/app/routers/conv_logs.py:428` | `update_conv_log` から `_fire_translation` を無条件呼び出し |
| `backend/app/routers/conv_logs.py:359` | `existing["direction"]` — update 時に direction を既に取得済み |
| `backend/app/routers/conv_logs.py:49` | `ConvLogCreate.direction: str = "inbound"` — スキーマ定義 |
| `frontend/src/pages/inbox/ManualRecordSection.tsx:76` | `direction: "inbound"` ハードコード — 現 UI は outbound を生成しない |
| `frontend/src/pages/company-detail/CompanyConvLogsTab.tsx:132` | `translated_text` を全方向で表示しているが outbound conv_log は現 UI 未生成 |
| `backend/app/services/message_translator.py:114` | `detect_inbound_language` — 関数名からも inbound 専用と確認 |
| `backend/tests/test_conv_logs_fire_translation.py:1` | 既存テストファイル — direction guard テスト追加対象 |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | Phase B 多数決（lang_judge）は outbound を使うか | lang_judge の UNION ALL が direction='inbound' のみ集計（origin/feature/morimoto/lang-record-foundation で確認） | ✅ 解消済み |
| 2 | update_conv_log で direction は取得済みか | `backend/app/routers/conv_logs.py:359` で `existing["direction"]` として取得済み | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
