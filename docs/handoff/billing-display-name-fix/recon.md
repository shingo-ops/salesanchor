# recon — billing-display-name-fix

**仕事名**: billing-display-name-fix  
**日付**: 2026-06-12  
**対象ADR**: ADR-127（追補）, ADR-101（不変性参照）  
**担当**: Morimoto

---

## 背景

SA-03 stage 3 (change_billing) 実装後に以下3件の不整合が発覚した:
1. 請求書PDFの BILL TO 宛名が `billing_display_name` を無視している
2. `change_billing` INSERT で `company_addresses.name` が常に空文字になる
3. InboxKartePanel の請求先変更ボタンに登録済みガードがない（API 側も同様）

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/routers/invoices.py:68-71` | `_fetch_address_snapshot` SELECT — `c.name AS company_name` のみ、`billing_display_name` 欠如 |
| `backend/app/routers/invoices.py:84-95` | スナップショット返却 dict — `billing_display_name` キー欠如 |
| `backend/app/services/invoice_renderer.py:425-426` | `render_invoice_pdf._to_addr` — `snap.get("company_name")` のみ参照 |
| `backend/app/services/invoice_renderer.py:503-504` | `render_quote_pdf._to_addr` — 同上 |
| `backend/app/routers/registration_tokens.py:508-511` | `change_billing` INSERT の `"name": addr.name` — フロントの `address.name` が `""` のため常に空文字 |
| `frontend/src/pages/register/RegisterChangeBillingPage.tsx:44` | `address.name` の初期値 `""` — フォーム入力なし |
| `frontend/src/pages/inbox/InboxKartePanel.tsx:300-308` | change_billing ボタン — 登録状態チェックなし、未登録リードにも表示 |
| `backend/app/routers/registration_tokens.py:82-100` | `type=register` の登録済みゲートのみ実装。`change_billing` の未登録ゲートは未実装 |
| `frontend/src/pages/company-detail/CompanyDetailPage.tsx:130` | `isAlreadyRegistered = billingAddresses.some((a) => a.is_default)` — 参照すべき実装パターン |

---

## 根拠となる事実

### billing_display_name と invoice BILL TO の乖離

- `billing_display_name` は `companies` テーブルの列（`change_billing` 時に更新）
- `tasks/reports.py:46` は `COALESCE(billing_display_name, ba.name, c.name)` — レポートは優先使用
- `_fetch_address_snapshot` は `c.name AS company_name` のみ取得 → PDF も `companies.name` 固定
- 結果: `change_billing` で請求書表示名を変えても新規請求書の宛名が変わらない
- 既存スナップショットには `billing_display_name` キーが存在しない → ADR-101 のスナップショット不変性は維持済み

### company_addresses.name が空文字

- `RegisterChangeBillingPage.tsx:44` で `address.name = ""` 初期値
- フォームに name 入力欄なし
- `change_billing` INSERT: `"name": addr.name` → 常に `""` でINSERT
- `billing_display_name` は別フィールド（同リクエストに存在）→ フォールバックで使える

### InboxKartePanel 未登録ガード欠如

- `CompanyDetailPage.tsx:130` は `isAlreadyRegistered` で change_billing ボタンを条件表示
- `InboxKartePanel.tsx:300-308` は無条件表示
- 未登録 lead で発行しても API は `change_billing` ハンドラで「billing is_default なし」状態に陥る
  （アドレス行の降格 UPDATE が0件のまま新行 INSERT → 実質 register 相当の挙動）

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | 既存スナップショットに `billing_display_name` キーを追加する必要があるか | 不要 — `snap.get("billing_display_name")` は `None` を返し `company_name` にフォールバック | ✅ 解消済み |
| 2 | 見積書PDFも同じ修正が必要か | `render_quote_pdf._to_addr` も同構造のため同一修正適用 | ✅ 解消済み |
| 3 | `register` / `add_address` の `name` フォールバックも統一すべきか | 両エンドポイントはリクエストに `billing_display_name` なし → change_billing のみ対象で十分 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
