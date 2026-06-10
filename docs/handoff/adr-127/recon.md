# recon — ADR-127: 登録後の変更・追加を専用フォーム化

**仕事名**: adr-127-registration-post-forms
**日付**: 2026-06-11
**対象ADR**: ADR-127
**担当**: architect

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/schemas/registration_token.py:26-28` | `TokenType` Enum: `register` / `add_address` の2種のみ |
| `migrations/20260604_080000_create_registration_tokens.sql:11` | DB CHECK制約: `type IN ('register', 'add_address')` — 新種別追加に migration 必要 |
| `backend/app/routers/registration_tokens.py:90-93` | 発行URL分岐: `add_address` → `/register/address?token=`、else → `/register?token=` |
| `backend/app/services/registration_token.py:115,148` | `verify_token` が `type` を str として返す |
| `frontend/src/pages/register/RegisterAddressPage.tsx:36-51` | `emptyAddress()`: `address_type: "delivery"`, `is_default: false` 固定 |
| `frontend/src/pages/register/RegisterAddressPage.tsx:163-171` | address_type select が露出（billing も選択可 — 配送先追加専用化で削除対象） |
| `backend/app/routers/invoices.py:53-82` | `_fetch_address_snapshot`: 請求書作成時に billing is_default=true をスナップショット取得 |
| `migrations/20260604_160000_add_invoice_snapshot_columns.sql:31` | `invoices.bill_to_snapshot JSONB` — 作成時点で凍結。billing 変更後も既存請求書は不変 |
| `frontend/src/pages/company-detail/CompanyDetailPage.tsx:90` | `billingAddresses` — addresses 配列から billing フィルタ済み。登録済み判定に使用可 |
| `frontend/src/pages/company-detail/CompanyDetailPage.tsx:112-120` | 現在の「登録リンク生成」ボタン: `type: "register"` 固定 |
| `frontend/src/pages/inbox/InboxKartePanel.tsx:262-266` | `karte-overflow-menu`: 現在アイテムなし、「サブADRごとに追加」コメント済み |

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | 請求先変更: 既存 billing 行を UPDATE するか旧行を残して新行 INSERT するか | 案B（降格＋INSERT）に決定。ADR-127 §2 に記載 | ✅ 解消済み |
| 2 | 発行ゲートをフロント・バックエンドどちらで実装するか | 二段（フロント無効化＋バックエンド拒否）に決定 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
