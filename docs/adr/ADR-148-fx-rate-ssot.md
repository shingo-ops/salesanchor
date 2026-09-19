# ADR-148: 為替レート SSOT（public.app_fx_rates）

| 項目 | 内容 |
|------|------|
| **状態** | Accepted |
| **日付** | 2026-06-28 |
| **担当** | Hikky-dev |

---

## 背景

請求書 UI では USD/JPY 為替レートをユーザーが手動入力していた。将来的に1日2回の自動取得・全テナント共通参照を実現するために SSOT テーブルが必要になった。

## 決定

- `public.app_fx_rates` テーブルを新設し、Celery Beat が JST 6:00 / 18:00 に自動 UPSERT する
- 全テナント共通情報のため public スキーマに配置し、RLS で読み取り全許可・書き込み operator 限定とする
- 外部API呼び出し実装は既存の `backend/app/services/fx_rate.py` を再利用・無改変とする
- 既存の請求書 FX 入力フローは独立系統のまま維持する（本 ADR の対象外）

## 結果

- Celery Beat スケジュールに2エントリ追加（JST 6:00 / 18:00）
- `GET /api/v1/fx-rate/{currency}` でログイン済み全ユーザーが参照可能
- `POST /api/v1/super-admin/fx-rate/refresh` で is_super_admin が手動更新可能
- super-admin メニューに `/super-admin/fx-rate` ページを追加

## 関連

- `docs/handoff/fx-rate-ssot/recon.md`
- `docs/handoff/fx-rate-ssot/design.md`
- ADR-072（RLS operator コンテキスト）
