# recon-cd: 請求書作成ポートフォリオ 便C・便D の調査（事実のみ）

基準 commit: `2ccb6a94e Merge pull request #5533 from shingo-ops/release/migration-external-cases`（origin/main。作業場所 release/invoice-create-portfolio-recon-cd の最初の `git log --oneline -1`）。
読んだ設計: docs/handoff/invoice-create-portfolio/design.md（§3-2〜§3-8・§4 便C・便D・§6・§8）。読んだ節: docs/handoff/design-partner-card-ops/guards/ の 00-common.md・03-file.md・10-executor.md。
書式: パスはリポジトリ直下からのフルパス。`パス:行` の後に原文。提案・設計・推測は書かない。見つからないものは「無い（検索した語）」。

---

## A. backend/app/routers/invoices.py

### A-1 道（デコレータ・関数名・権限）

| 行 | メソッドと道 | 関数名（行） | 権限 |
|---|---|---|---|
| 156-160 | GET `/invoices` | list_invoices (161) | invoices.view |
| 192-196 | GET `/invoices/{invoice_id}` | get_invoice (197) | invoices.view |
| 211-216 | POST `/invoices/from-quote/{quote_id}` | create_invoice_from_quote (217) | invoices.create |
| 314-319 | POST `/invoices` | create_invoice (320) | invoices.create |
| 432-436 | PATCH `/invoices/{invoice_id}` | update_invoice (437) | invoices.update |
| 474-478 | POST `/invoices/{invoice_id}/issue` | issue_invoice (479) | invoices.create |
| 503-507 | POST `/invoices/{invoice_id}/pay` | pay_invoice (508) | invoices.update |
| 544-548 | POST `/invoices/{invoice_id}/void` | void_invoice (549) | invoices.void |
| 608-612 | POST `/invoices/{invoice_id}/paypal-link` | issue_paypal_link (613) | invoices.update |
| 715-719 | POST `/invoices/{invoice_id}/paypal-confirm` | confirm_paypal_payment (720) | invoices.update |
| 794-797 | GET `/invoices/{invoice_id}/pdf` | download_invoice_pdf (798) | invoices.view |
| 888-891 | GET `/invoices/{invoice_id}/paypal-copy-pdf` | download_paypal_copy_pdf (892) | invoices.view |
| 917-920 | GET `/invoices/{invoice_id}/paypal-disputes` | list_invoice_paypal_disputes (921) | invoices.view |
| 952-955 | GET `/quotes/{quote_id}/pdf` | download_quote_pdf (956) | invoices.view |
| 1026-1029 | GET `/fx-rate/{currency}` | fetch_fx_rate (1030) | invoices.view |

- `backend/app/routers/invoices.py:53`: `router = APIRouter()`（prefix はこのファイルに無い）。
- draft-context・preview の道: 無い（検索した語: `draft-context`, `invoices/preview`。backend/app 全体で0件）。
- GET `/invoices/{invoice_id}` は 192 行目、GET `/invoices/draft-context` の道は無い。

### A-2 `_fetch_address_snapshot`（62-102）
- `backend/app/routers/invoices.py:62`: `async def _fetch_address_snapshot(db: AsyncSession, company_id: int | None, address_type: str,) -> dict | None:`
- 71-72: `if company_id is None:` / `return None`
- 74-84: `company_addresses a JOIN companies c` で `a.is_default = TRUE` かつ `a.address_type = :atype` の1行（`LIMIT 1`）。読む列: `a.branch_name, a.zip, a.address_line_1, a.address_line_2, a.city, a.state, a.country_code, a.telephone, c.name AS company_name, c.billing_display_name`。
- 90-102 返す形のキー: `company_name`, `billing_display_name`, `label`(=branch_name), `postal_code`(=zip), `address`(=address_line_1 と address_line_2 を空白で連結), `city`, `state`, `country`(=country_code), `phone`。`contact_name` / `email` は返さない。
- 呼ぶ行: 244, 245（from-quote）・348, 349（create）・987, 988（download_quote_pdf）。

### A-3 `_INVOICE_COLUMNS`（105-118）
```
    id, invoice_number, quote_id, company_id, contact_id, currency,
    subtotal, shipping_fee, tax_amount, total_amount,
    exchange_rate_jpy, exchange_rate_usd, amount_jpy, amount_usd,
    payment_method, status, branch_number,
    pdf_url, erp_key,
    issued_at, due_date, paid_at, voided_at, void_reason,
    notes, created_by, created_at, updated_at,
    ship_to_snapshot, bill_to_snapshot, issue_mode,
    duty_amount, duty_policy_snapshot, fx_rate_snapshot,
    paypal_order_id, paypal_approval_url, payment_fee,
    paypal_invoicer_view_url, paypal_copy_pdf_at,
    issuer_region
```
- `payment_method_id`・`tax_rate_percent`・`shipping_carrier`・`shipping_service`・`shipping_snapshot` は `_INVOICE_COLUMNS` に無い（検索した語: invoices.py 内の同名）。

### A-4 `_UPDATABLE_COLUMNS`（120）
- `backend/app/routers/invoices.py:120`: `_UPDATABLE_COLUMNS = {"payment_method", "due_date", "exchange_rate_jpy", "exchange_rate_usd", "notes"}`

### A-5 `_calc_currency_amounts`（135-153）
- 135-136: `def _calc_currency_amounts(total: Decimal, currency: str, rate_jpy: Decimal | None, rate_usd: Decimal | None) -> tuple[Decimal | None, Decimal | None]:`
- 140-143: JPY は `amount_jpy = total`、`rate_usd` が正なら `amount_usd = round(total / rate_usd, 2)`。
- 144-147: USD は `amount_usd = total`、`rate_jpy` があれば `amount_jpy = round(total * rate_jpy, 2)`。
- 148-152: EUR は `amount_jpy = round(total * rate_jpy, 2)`、`amount_usd = round(total * rate_usd, 2)`。
- 呼ぶ行: 345（create_invoice）の1か所のみ。from-quote では呼ばない（amount_jpy・amount_usd・exchange_rate_* を INSERT しない。258-268）。

### A-6 `get_fx_rate` を呼ぶ全行
- 48: `from app.services.fx_rate import get_fx_rate`
- 253: `fx_snap = get_fx_rate(currency) if currency and currency.upper() != "JPY" else None`（from-quote）
- 356: `fx_snap = get_fx_rate(data.currency) if data.currency and data.currency.upper() != "JPY" else None`（create）
- 1044: `result = get_fx_rate(currency)`（GET /fx-rate/{currency}）
- 関数の中身: `backend/app/services/fx_rate.py:30` `def get_fx_rate(currency: str) -> dict | None:`、45 行目 `resp = httpx.get(FX_BASE_URL, timeout=5.0)`、27 行目 `FX_BASE_URL = "https://open.er-api.com/v6/latest/JPY"`。返す形（38 行目のdocstring）: `{"currency": "USD", "rate": 150.25, "fetched_at": "2026-06-04T10:00:00Z"}`。JPY のとき None。

### A-7 発行の道（474-500）
- 486-489: `UPDATE invoices SET status = 'issued', issued_at = NOW(), updated_at = NOW() WHERE id = :id AND status = 'draft' RETURNING {_INVOICE_COLUMNS}`
- 491-492: 行が無いと `HTTP_400_BAD_REQUEST`, detail=`"draft状態の請求書のみ発行できます"`。
- 税・関税・合計・為替を計算し直す処理: 無い（検索した語: issue_invoice 内に `tax`・`duty`・`fx`・`get_fx_rate` が0件）。
- 494-499: `record_audit_log(... action="issue" ...)` → `await db.commit()`(497) → `await reset_tenant_context(db, tenant_id)`(498) → `await invalidate_dashboard_cache(tenant_id)`(499)。

### A-8 見積から作る道（217-311）
- 226-229: `SELECT * FROM quotes WHERE id = :id FOR UPDATE`。233-234: `q["status"] != "approved"` なら 400 `"承認済みの見積もりのみ請求書に変換できます"`。
- 247-249: `issuer_region = decide_issuer_region(bill_to_snap)` / `if issuer_region is None:` → 422 detail `"bill_to_country"`。
- 258-268 INSERT 列: `tenant_id, invoice_number, quote_id, company_id, contact_id, currency, subtotal, shipping_fee, tax_amount, total_amount, payment_method, status, branch_number, erp_key, notes, created_by, ship_to_snapshot, bill_to_snapshot, fx_rate_snapshot, issuer_region`。`payment_method` は値 `NULL`（266）。
- 274-275: `"subtotal": q["subtotal"], "shipping": q["shipping_fee"],` / `"tax": q["tax_amount"], "total": q["total_amount"],`（見積の値をそのまま写す）。
- 286-297: 見積明細を `hs_code` つきで写す。
- 送料の会社を読む行: 無い（検索した語: invoices.py 内の `shipping_carrier`）。
- 299-306: `record_audit_log(action="create_from_quote")` → `await db.commit()`(304) → `await reset_tenant_context(db, tenant_id)`(305) → `await invalidate_dashboard_cache(tenant_id)`(306)。

### A-9 直接作る道（320-429）
- 328-339: contact の存在確認（404 `"not_found:contact"`）と所属一致（400 `"指定された担当者は指定会社に所属していません"`）。
- 341-344: `subtotal = sum(item.quantity * item.unit_price for item in data.items)` / `shipping = data.shipping_fee or Decimal(0)` / `tax = data.tax_amount or Decimal(0)` / `total = subtotal + shipping + tax`。
- 345: `amount_jpy, amount_usd = _calc_currency_amounts(total, data.currency, data.exchange_rate_jpy, data.exchange_rate_usd)`
- 351-353: `decide_issuer_region(bill_to_snap)` が None なら 422 `"bill_to_country"`。
- 363-379: INSERT 列に `exchange_rate_jpy, exchange_rate_usd, amount_jpy, amount_usd, payment_method, due_date` を含む。`payment` の値は 387 行目 `"payment": data.payment_method`。
- 385: `"tax": tax, "total": total, "rate_jpy": data.exchange_rate_jpy,`
- 397-410: 明細 INSERT の列は `invoice_id, product_id, product_name, name_en, condition, unit, quantity, unit_price, weight, subtotal, sort_order`（`hs_code` は入れない）。
- 422-424: `await db.commit()` → `await reset_tenant_context(db, tenant_id)` → `await invalidate_dashboard_cache(tenant_id)`。

### A-10 PATCH の道と draft だけの門（432-471）
- 444-450: `old_row = ...` を読み、404 `"not_found:invoice"`。`if old_row["status"] != "draft":` → `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="draft状態の請求書のみ編集できます")`。門は欄ごとでなく道の全体に1つ（449-450）。
- 452-455: `update_data = data.model_dump(exclude_unset=True)` を `_UPDATABLE_COLUMNS` で絞り、空なら 400 `"no_fields_to_update"`。
- 460-463: `UPDATE invoices SET {set_clauses}, updated_at = NOW() WHERE id = :id RETURNING {_INVOICE_COLUMNS}`。
- 469-470: `await db.commit()` → `await reset_tenant_context(db, tenant_id)`。戻りは `InvoiceResponse`（response_model, 434）。

### A-11 GET /fx-rate/{currency}（1026-1050）
- 1041-1042: `if currency.upper() == "JPY":` / `return {"currency": "JPY", "rate": 1.0, "fetched_at": None}`
- 1044-1049: `result = get_fx_rate(currency)`、None のとき 503 detail=`f"為替レートの取得に失敗しました: {currency}"`。
- 権限: `require_permission("invoices.view")`(1028)。

### A-12 payment_method に 'paypal' を入れる行
- `backend/app/routers/invoices.py:672`: `payment_method = COALESCE(payment_method, 'paypal'), updated_at = NOW()`（paypal-link の UPDATE 668-675）
- `backend/app/routers/invoices.py:766`: `payment_method = 'paypal', updated_at = NOW()`（paypal-confirm の UPDATE 762-770）

### A-13 tax_amount・shipping_fee を読む行（invoices.py）
- 107: `subtotal, shipping_fee, tax_amount, total_amount,`（_INVOICE_COLUMNS）
- 260: INSERT 列 `subtotal, shipping_fee, tax_amount, total_amount,`（from-quote）
- 274-275: `"shipping": q["shipping_fee"],` `"tax": q["tax_amount"],`
- 342-343: `shipping = data.shipping_fee or Decimal(0)` / `tax = data.tax_amount or Decimal(0)`
- 367: INSERT 列（create）
- 832-833: `"shipping_fee": float(row["shipping_fee"] or 0),` `"tax_amount": float(row["tax_amount"] or 0),`（PDF）
- 876-877: 同上（`_render_paypal_copy_pdf`, 855）
- 966: `subtotal, shipping_fee, tax_amount, total_amount,`（download_quote_pdf の SELECT）
- 1009-1010: `"shipping_fee": float(row["shipping_fee"] or 0),` `"tax_amount": float(row["tax_amount"] or 0),`

### A-14 commit と reset_tenant_context の行（全て）
| commit | reset_tenant_context | 道 |
|---|---|---|
| 304 | 305 | from-quote |
| 422 | 423 | create |
| 469 | 470 | PATCH |
| 497 | 498 | issue |
| 538 | 539 | pay |
| 582 | 583 | void |
| 709 | 710 | paypal-link |
| 784 | 785 | paypal-confirm |
- 各行の末尾コメント: `# ADR-072 Phase 2.5`。import は 33 行目 `reset_tenant_context,`。

### A-15 その他（ヘッダの import）
- `backend/app/routers/invoices.py:50`: `from app.services.issuer import decide_issuer_region, get_issuer`
- 49: `from app.services.invoice_renderer import render_invoice_pdf, render_quote_pdf`
- PDF の道 814: `tenant_profile = await get_issuer(db, tenant_id, row["issuer_region"] or "overseas")`。

---

## B. backend/app/schemas/invoice.py

### InvoiceItemInput（28-37）
`product_id: int | None = Field(default=None, ge=1)` / `product_name: str = Field(min_length=1, max_length=255)` / `name_en: str | None = Field(default=None, max_length=255)` / `condition: str | None = Field(default=None, max_length=50)` / `unit: str | None = Field(default=None, max_length=20)` / `quantity: int = Field(ge=1)` / `unit_price: Decimal = Field(ge=0, max_digits=15, decimal_places=2)` / `weight: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=3)`

### InvoiceCreate（40-52）全欄
- 42 `company_id: int = Field(ge=1, description="会社ID")`
- 43 `contact_id: int = Field(ge=1, description="担当者ID")`
- 44 `currency: str = Field(default="JPY", max_length=10)`
- 45 `shipping_fee: Decimal | None = Field(default=None, ge=0, max_digits=15, decimal_places=2)`
- 46 `tax_amount: Decimal | None = Field(default=None, ge=0, max_digits=15, decimal_places=2)`
- 47 `exchange_rate_jpy: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=4)`
- 48 `exchange_rate_usd: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=4)`
- 49 `payment_method: str | None = Field(default=None, max_length=50)`
- 50 `due_date: date | None = None`
- 51 `notes: str | None = Field(default=None, max_length=5000)`
- 52 `items: list[InvoiceItemInput] = Field(min_length=1)`
- `model_config` / `extra="forbid"`: 無い（検索した語: `extra`, `model_config`。InvoiceCreate・InvoiceUpdate の中に0件）。`payment_method_ref`・`shipping`（送料の選択）の欄: 無い。

### InvoiceUpdate（55-60）全欄
- 56 `payment_method: str | None = Field(default=None, max_length=50)`
- 57 `due_date: date | None = None`
- 58 `exchange_rate_jpy: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=4)`
- 59 `exchange_rate_usd: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=4)`
- 60 `notes: str | None = Field(default=None, max_length=5000)`

### InvoiceResponse（86-152）全欄
95 `id: int` / 96 `invoice_number: str | None` / 97 `quote_id: int | None` / 98 `company_id: int` / 99 `contact_id: int | None` / 100 `currency: str` / 101 `subtotal: Decimal | None` / 102 `shipping_fee: Decimal | None` / 103 `tax_amount: Decimal | None` / 104 `total_amount: Decimal | None` / 105 `exchange_rate_jpy: Decimal | None` / 106 `exchange_rate_usd: Decimal | None` / 107 `amount_jpy: Decimal | None` / 108 `amount_usd: Decimal | None` / 109 `payment_method: str | None` / 110 `status: str` / 111 `branch_number: int | None` / 112 `pdf_url: str | None` / 113 `erp_key: str | None` / 114 `issued_at: datetime | None` / 115 `due_date: date | None` / 116 `paid_at: datetime | None` / 117 `voided_at: datetime | None` / 118 `void_reason: str | None` / 119 `notes: str | None` / 120 `created_by: int | None` / 121 `created_at: datetime` / 122 `updated_at: datetime` / 124 `ship_to_snapshot: dict | None = None` / 125 `bill_to_snapshot: dict | None = None` / 126 `issue_mode: str | None = None` / 127 `duty_amount: Decimal | None = None` / 128 `duty_policy_snapshot: dict | None = None` / 129 `fx_rate_snapshot: dict | None = None` / 131 `paypal_order_id: str | None = None` / 132 `paypal_approval_url: str | None = None` / 133 `payment_fee: Decimal | None = None` / 135 `paypal_invoicer_view_url: str | None = None` / 136 `paypal_copy_pdf_at: datetime | None = None` / 138 `issuer_region: str | None = None`
- 140: `model_config = {"from_attributes": True}`。145-152: JSON 文字を dict に読み直す validator（対象 `ship_to_snapshot`, `bill_to_snapshot`, `duty_policy_snapshot`, `fx_rate_snapshot`）。
- `payment_method_id`・`tax_rate_percent`・`shipping_carrier`・`shipping_service`・`shipping_snapshot` の欄: 無い（検索した語: schemas/invoice.py 内の同名）。

### InvoiceDetailResponse（155-156）
`class InvoiceDetailResponse(InvoiceResponse):` / `items: list[InvoiceItemResponse] = []`

### InvoiceItemResponse（67-83）
`id: int`, `product_id: int | None`, `product_name: str`, `name_en: str | None = None`, `condition: str | None = None`, `unit: str | None = None`, `quantity: int`, `unit_price: Decimal`, `weight: Decimal | None`, `subtotal: Decimal`, `sort_order: int`, `hs_code: str | None = None`。

### VoidRequest（63-64）
`reason: str = Field(min_length=1, max_length=500)`

---

## C. backend/app/services/invoice_renderer.py

### C-1 合計の区切り（336-368）
- 336: `# ── 6. 合計行 ───...`
- 343-345: `"Subtotal:"` 行。
- 347-350: `if data.shipping_fee:` → `c.drawRightString(165 * mm, y, "Shipping:")`
- 352-355: `if data.tax_amount:` / `c.drawRightString(165 * mm, y, "Tax:")` / `c.drawRightString(190 * mm, y, _fmt_money(data.tax_amount, data.currency))`（率の表示: 無い。検索した語: `tax_rate`, `%`）。
- 357-361: `# Duty 行（None の場合は非表示）` / `if data.duty_amount is not None:` / `c.drawRightString(165 * mm, y, "Duty:")`
- 363-368: `"TOTAL:"` 行。
- データクラス 133-157: `InvoiceRenderData` の欄は `doc_type, doc_code, issued_at, ship_to, bill_to, items, subtotal, shipping_fee, tax_amount, total, currency, duty_amount, fx_rate, notes, tenant_name, tenant_address, tenant_phone, tenant_email, tenant_website, tenant_registration_number, paypal_copy`。`tax_rate_percent`・支払方法の欄: 無い。

### C-2 fx の表示（370-383）
- 371: `if data.fx_rate is not None and data.currency != "JPY":`
- 374-376: `rate_line = (f"Exchange rate: 1 {data.fx_rate.currency} = JPY {data.fx_rate.rate:,.4f}")`
- 377-378: `if data.fx_rate.fetched_at:` / `rate_line += f"  (as of {data.fx_rate.fetched_at[:19]}Z)"`
- 380-381: `jpy_total = data.total * data.fx_rate.rate` / `c.drawString(20 * mm, y - 4 * mm, f"JPY equivalent: ¥{jpy_total:,.0f}")`
- `FxRateSnapshot`（126-129）: `currency: str` / `rate: float  # 1 外貨 = rate JPY` / `fetched_at: Optional[str] = None`。変換 `_to_fx`（482-489）は `snap.get("currency")`, `snap.get("rate")`, `snap.get("fetched_at")` を読む。

### C-3 支払の区切り
- 無い（検索した語: `payment`, `Payment`, `bank`, `Bank`, `IBAN`, `SWIFT`, `wise`。invoice_renderer.py 内で0件）。
- 合計（366-368）の次は 370 の為替脚注、385 の `# ── 8. Notes`、399 の `# ── 9. PayPal 写し注記`。

### C-4 関数
- 441-442: `def render_invoice_pdf(invoice_data: dict, tenant_profile: dict, paypal_copy: dict | None = None) -> bytes:`
- 527: `def render_quote_pdf(quote_data: dict, tenant_profile: dict) -> bytes:`（見積 PDF。583 行目 `duty_amount=None,  # 見積書では Duty 行は表示しない`、584 `fx_rate=None,`）。
- 224: `def _render_doc_pdf(data: InvoiceRenderData) -> bytes:`（請求書・見積書の共通）。
- 407: `def _draw_paypal_copy_footer(c, font: str, width: float, paypal_copy: dict) -> None:`
- 164: `def _fmt_money(amount: float, currency: str) -> str:`
- `render_invoice_pdf` が読む invoice_data のキー（469-520 付近）: `invoice_code`, `issued_at`, `ship_to_snapshot`, `bill_to_snapshot`, `items`, `subtotal`, `shipping_fee`, `tax_amount`, `total`（`total_amount` も invoices.py:834 が渡す）, `currency`, `duty_amount`, `fx_rate_snapshot`, `notes`。

---

## D. 発行元・税率・振込先・PayPal・テナント設定

### D-1 backend/app/services/issuer.py（全96行）
- 17: `ISSUER_REGIONS = ("domestic", "overseas")`
- 20-27: `def decide_issuer_region(bill_to_snapshot: Mapping[str, Any] | None) -> str | None:`。24-27: `country = bill_to_snapshot.get("country")` … `return "domestic" if country.strip().upper() == "JP" else "overseas"`。国が無いと None。
- 44: `async def get_issuer(db: AsyncSession, tenant_id: int, region: str) -> dict:`。48 `profiles = tenant_table_ref(db, tenant_id, "tenant_issuer_profiles")`。51-60: `SELECT p.company_name, p.email, p.website, p.country_code, p.postal_code, p.state_region, p.city, p.address1, p.address2, p.phone, p.is_invoice_registered, p.registration_number, pr.name_ja AS prefecture_name, co.name AS country_name FROM {profiles} p ... WHERE p.region = :region ORDER BY p.id LIMIT 1`。
- 返すキー（66-74）: `name, address, phone, email, website, registration_number, legacy`。`country_code` は返さない（SELECT はするが dict に入れない）。発行元の国コードだけを返す関数: 無い（検索した語: `country_code` を返す issuer の関数）。
- 行が無いとき 75-95 で旧表 `tenant_profile`（`company_name, company_name_en, address, phone, email, website`）を読む。

### D-2 発行元の表の列（backend/app/services/tenant.py:1235-1264）
`tenant_issuer_profiles`: `id SERIAL PRIMARY KEY`, `tenant_id INTEGER NOT NULL DEFAULT {tenant_id}`, `region VARCHAR(20) NOT NULL`, `company_name VARCHAR(255) NOT NULL`, `email VARCHAR(255)`, `website VARCHAR(255)`, `country_code CHAR(2) NOT NULL REFERENCES public.countries(code)`, `postal_code VARCHAR(10)`, `prefecture_code CHAR(2)`, `state_region TEXT`, `city TEXT NOT NULL`, `address1 TEXT NOT NULL`, `address2 TEXT`, `phone VARCHAR(16)`, `is_invoice_registered BOOLEAN NOT NULL DEFAULT FALSE`, `registration_number VARCHAR(14)`, `updated_by_user_id INTEGER`, `created_at`, `updated_at`。UNIQUE `(tenant_id, region)`（1255）。
- 読むコード: backend/app/services/issuer.py:48（`tenant_issuer_profiles` を含む行は backend/app 内で issuer.py:48 と tenant.py のみ）。書くコード: 無い（検索した語: `tenant_issuer_profiles` の INSERT/UPDATE。backend/app 内の書く道は0件）。

### D-3 public.tax_rates
- 列（`migrations/20261112_150000_create_viewer_contract_public_tables.sql:85-93`）:
  - 86 `id BIGSERIAL PRIMARY KEY,`
  - 87 `rate_percent NUMERIC(5, 2) NOT NULL,`
  - 88 `effective_from DATE NOT NULL,`
  - 89 `created_by_user_id INTEGER NULL REFERENCES public.users(id) ON DELETE SET NULL,`
  - 90 `created_at TIMESTAMPTZ NOT NULL DEFAULT now(),`
  - 91 `CONSTRAINT uq_tax_rates_effective_from UNIQUE (effective_from),`
  - 92 `CONSTRAINT ck_tax_rates_rate_percent CHECK (rate_percent >= 0 AND rate_percent <= 100)`
  - 国の列・有効期間の終わりの列: 無い（表に `effective_to`・`country` は無い）。
- RLS: 223-228 `FORCE ROW LEVEL SECURITY`、`tax_rates_read ... FOR SELECT USING (true)`、`tax_rates_write ... FOR ALL`。
- 今それを読むコード: backend/app/routers/super_admin_tax_rates.py:66（`SELECT {_COLS} FROM public.tax_rates ORDER BY effective_from DESC`）・73（`SELECT max(effective_from) FROM public.tax_rates`）・119（`SELECT effective_from FROM public.tax_rates WHERE id = :id`）。書くコード: 同ファイル 91（`INSERT INTO public.tax_rates (rate_percent, effective_from, created_by_user_id)`）・128（行の削除）。請求書側（backend/app/routers/invoices.py・backend/app/services/）が tax_rates を読む行: 無い（検索した語: `tax_rates`。services/ と invoices.py に0件）。

### D-4 振込先の表（backend/app/services/tenant.py）
- `tenant_invoice_payment_methods`（1267-1286）: `id SERIAL PRIMARY KEY`, `tenant_id INTEGER NOT NULL DEFAULT {tenant_id}`, `region VARCHAR(20) NOT NULL`, `method_type VARCHAR(10) NOT NULL`, `display_name TEXT NOT NULL`, `sort_order INTEGER NOT NULL DEFAULT 0`, `is_active BOOLEAN NOT NULL DEFAULT TRUE`, `updated_by_user_id INTEGER`, `created_at`, `updated_at`, `superseded_by_id INTEGER`(1278), `deleted_at TIMESTAMPTZ`(1279)。CHECK: `region IN ('domestic', 'overseas')`、`method_type IN ('bank', 'wise')`、`superseded_by_id <> id`。1289: `CREATE UNIQUE INDEX IF NOT EXISTS uq_tenant_invoice_payment_methods_superseded_by ... WHERE superseded_by_id IS NOT NULL;`
- `tenant_invoice_payment_bank`（1292-1308）: `payment_method_id INTEGER PRIMARY KEY`, `method_type VARCHAR(10) NOT NULL DEFAULT 'bank'`, `tenant_id`, `account_holder TEXT NOT NULL`, `bank_name TEXT NOT NULL`, `bank_branch TEXT NOT NULL`, `bank_account_type TEXT NOT NULL`, `bank_account_number TEXT NOT NULL`, `swift_code TEXT`, `bank_address TEXT`, `created_at`, `updated_at`。
- `tenant_invoice_payment_wise`（1311-1329）: `payment_method_id INTEGER PRIMARY KEY`, `method_type VARCHAR(10) NOT NULL DEFAULT 'wise'`, `tenant_id`, `account_holder TEXT NOT NULL`, `wise_currency CHAR(3) NOT NULL`, `wise_email VARCHAR(255) NOT NULL`, `iban TEXT`, `swift_bic TEXT`, `bank_name TEXT`, `bank_address TEXT`, `note TEXT`, `created_at`, `updated_at`。
- 版の見張り（トリガー）: tenant.py:1342-1344（詳細表の親を `FOR SHARE` で読む）・1398（`superseded_by_id` の指す先）・1419-1435（トリガー6つ: `trg_tenant_invoice_payment_methods_version_guard`, `trg_tenant_invoice_payment_bank_immutable`, `trg_tenant_invoice_payment_wise_immutable`, `trg_tenant_invoice_payment_methods_no_wipe`, `trg_tenant_invoice_payment_bank_no_wipe`, `trg_tenant_invoice_payment_wise_no_wipe`）。
- 移行ファイル: `migrations/20261112_160000_create_tenant_issuer_and_payment_tables.sql`（元の表）、`migrations/20261115_100000_add_payment_method_versioning.sql`（版の2列と見張り。ファイルの存在のみ確認）。
- invoices 表の便A の列（tenant.py:904-908）: `payment_method_id INTEGER,` / `tax_rate_percent NUMERIC(5, 2),` / `shipping_carrier VARCHAR(50),` / `shipping_service VARCHAR(100),` / `shipping_snapshot JSONB,`。移行: `migrations/20261113_120000_create_tenant_duty_rules_and_invoice_columns.sql:7-11`。quotes 表の送料の会社: tenant.py:811 `shipping_carrier VARCHAR(50),`。
- 今それを読み書きするコード: 無い（検索した語: `tenant_invoice_payment` を backend/app/ で検索。tenant.py の DDL・トリガー・RLS（1537-1540, 1775-1784）だけで、routers/・services/（tenant.py 以外）に0件）。

### D-5 public.tenant_paypal_config
- 列（`migrations/20260610_071110_add_paypal_config.sql:15-24`）: `id SERIAL PRIMARY KEY`, `tenant_id INTEGER NOT NULL UNIQUE REFERENCES tenants(id) ON DELETE CASCADE`, `client_id_encrypted TEXT NOT NULL`, `client_secret_encrypted TEXT NOT NULL`, `environment TEXT NOT NULL DEFAULT 'sandbox' CHECK (environment IN ('sandbox', 'live'))`, `updated_by_user_id INTEGER`, `created_at`, `updated_at`。列追加: `webhook_id`（`migrations/20260611_150000_add_paypal_webhook_id.sql:15-17`）。
- 読むコード: backend/app/services/paypal_payments.py:54（`SELECT environment FROM tenant_paypal_config WHERE tenant_id = :tid`。関数 `get_status` 51）・67-68（`get_credentials` 63）・420（`SELECT webhook_id`）、backend/app/routers/integrations.py:984（`SELECT tenant_id FROM tenant_paypal_config WHERE webhook_id IS NOT NULL`）。書くコード: paypal_payments.py:94（INSERT）・119（行の削除）・430（`UPDATE tenant_paypal_config SET webhook_id`）。
- invoices.py 側の利用: 46 `from app.services import paypal_payments`、598-599 `_require_paypal_creds` → `paypal_payments.get_credentials(db, tenant_id)`。

### D-6 tenant_settings の default_currency・duty_incoterms を読むコード
- `backend/app/routers/tenant_policy.py:38-42`: `_POLICY_COLS = ("inventory_agg_filter, agg_price_threshold_jpy, agg_qty_threshold, " "quote_validity_days, default_currency, document_language, " "duty_incoterms, issue_mode")`。
- `backend/app/schemas/tenant_policy.py:18`: `default_currency: str = Field(default="JPY", max_length=10)`、20 `duty_incoterms: Literal["DAP", "DDU", "DDP"] = "DAP"`、31 `default_currency: str | None = Field(default=None, max_length=10)`、33 `duty_incoterms: Literal["DAP", "DDU", "DDP"] | None = None`。
- `backend/app/services/duty_rules.py:264-271`: `async def get_duty_incoterms(db: AsyncSession, tenant_id: int) -> str | None:` / `SELECT duty_incoterms FROM public.tenant_settings WHERE tenant_id = :tenant_id`（行が無いと None）。呼び元 backend/app/routers/duty_rules.py:76。
- `backend/app/services/tenant.py:2079-2080`: 新しい会社の tenant_settings の INSERT 列に `default_currency`, `duty_incoterms`。
- invoices.py が default_currency を読む行: 無い（検索した語: `default_currency` を routers/invoices.py で検索）。

---

## E. 便B で入ったもの

### E-1 backend/app/services/duty_rules.py（関税の額の決まりの CRUD。計算は無い）
- 21-25: `_RULE_COLS = ("id, destination_country_code, carrier, label, effective_from, effective_to, " "source_url, note, is_active, created_at, updated_at")`、25 `_COMPONENT_COLS = "id, rule_id, sort_order, label, base, rate_pct, min_amount, max_amount, amount_currency"`。
- 例外: 28 `class DutyRuleNotFound(Exception)`, 32 `class DutyCountryInvalid(Exception)`, 36 `class DutyRuleOverlap(Exception)`（40 行目 `super().__init__("duty_rule_overlap")`）。
- 公開関数（引数 → 返す形）:
  - 101 `async def list_duty_rules(db: AsyncSession, tenant_id: int) -> list[dict]`（国・carrier NULLS FIRST・effective_from・id の順。中身つき）
  - 113 `async def get_duty_rule(db: AsyncSession, tenant_id: int, rule_id: int) -> dict`
  - 194 `async def create_duty_rule(db: AsyncSession, tenant_id: int, body: DutyRuleIn) -> dict`
  - 223 `async def update_duty_rule(db: AsyncSession, tenant_id: int, rule_id: int, body: DutyRuleIn) -> tuple[dict, dict]`
  - 256 `async def delete_duty_rule(db: AsyncSession, tenant_id: int, rule_id: int) -> dict`
  - 264 `async def get_duty_incoterms(db: AsyncSession, tenant_id: int) -> str | None`
- 返す dict の形（`_rule_out` 61-75）: `id`, `destination_country_code`, `carrier`, `label`, `effective_from`, `effective_to`, `source_url`, `note`, `is_active`, `created_at`, `updated_at`, `components`。中身（`_component_out` 48-58）: `id`, `sort_order`, `label`, `base`, `rate_pct`(文字), `min_amount`(文字), `max_amount`(文字), `amount_currency`。
- 請求書の関税を計算する関数・「その国・その日に有効な行」を探す関数: 無い（検索した語: `invoice_totals`, `duty_needs_carrier`, 有効な行を日付で探す関数。backend/app/ に `invoice_totals` は0件。ファイル backend/app/services/invoice_totals.py も無い）。
- ルーター: backend/app/routers/duty_rules.py。46 行目 `detail={"code": "duty_rule_overlap", "rule_ids": exc.rule_ids},`、76-80 `DutyRuleOptions(duty_incoterms=incoterms, currencies=currencies, bases=list(DUTY_BASES))`。

### E-2 backend/app/services/fx_currencies.py（全20行）
- 12: `async def list_invoice_currencies(db: AsyncSession) -> list[str]:`
- 15-16: `"SELECT DISTINCT currency FROM public.app_fx_rate_history " "WHERE currency <> 'JPY' ORDER BY currency"`
- 19: `return ["JPY", *[str(r[0]) for r in result.all()]]`
- 公開関数はこの1つだけ。

### E-3 app_fx_rate_history の列と、最新行を読む既存の関数
- 列（`migrations/20261003_100000_create_app_fx_rate_history.sql:24-30`）: `currency VARCHAR(3) NOT NULL,` / `rate_jpy NUMERIC(12,4) NOT NULL CHECK (rate_jpy > 0),` / `fetched_at TIMESTAMPTZ NOT NULL,` / `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),` / `PRIMARY KEY (currency, fetched_at)`。
- 最新行を読む既存のコード: `backend/app/routers/fx_rate_admin.py:66` `async def get_fx_rate(currency: str, db: AsyncSession = Depends(get_db), _user: User = Depends(get_current_user),)`（GET `/fx-rates/{currency}`, 61-65）。77-85: `SELECT currency, rate_jpy, fetched_at, created_at FROM public.app_fx_rate_history WHERE currency = :cur ORDER BY fetched_at DESC LIMIT 1`。行が無いと 404 `f"為替レートが未取得です: {currency.upper()}"`。返す `FxRateResponse(currency, rate_jpy(float), fetched_at(isoformat), updated_at)`（92-98）。ほかに fx_rate_admin.py:160 `FROM public.app_fx_rate_history WHERE currency = 'USD' ...`（refresh の道）。
- 通貨ごとの最新1行を返す services/ の関数: 無い（検索した語: `app_fx_rate_history` を backend/app/services/ で検索。fx_currencies.py の1か所のみ）。
- 書く側: backend/app/tasks/fx_rate_updater.py:43 `def update_usd_jpy_rate() -> None:`（USD のみ）。

---

## F. realtime・API エラー理由

### F-1 backend/app/realtime/topics.py
- 4: `- NO_SIGNAL_ROUTES: 今は合図を出さないルート。一括除外（ワイルドカード）は使わない。`
- 95: `NO_SIGNAL_ROUTES: dict[tuple[str, str], str] = {`
- 106-108（関税の額の道は登録済み）: `("POST", "/api/v1/admin/duty-rules"): _PENDING,` / `("PUT", "/api/v1/admin/duty-rules/{rule_id}"): _PENDING,` / `("DELETE", "/api/v1/admin/duty-rules/{rule_id}"): _PENDING,`
- 237-244（請求書の道）:
  - 237 `("POST", "/api/v1/invoices"): _PENDING,`
  - 238 `("POST", "/api/v1/invoices/from-quote/{quote_id}"): _PENDING,`
  - 239 `("PATCH", "/api/v1/invoices/{invoice_id}"): _PENDING,`
  - 240 `("POST", "/api/v1/invoices/{invoice_id}/issue"): _PENDING,`
  - 241 `("POST", "/api/v1/invoices/{invoice_id}/pay"): _PENDING,`
  - 242 `("POST", "/api/v1/invoices/{invoice_id}/paypal-confirm"): _PENDING,`
  - 243 `("POST", "/api/v1/invoices/{invoice_id}/paypal-link"): _PENDING,`
  - 244 `("POST", "/api/v1/invoices/{invoice_id}/void"): _PENDING,`
- `/api/v1/invoices/preview` の行: 無い（検索した語: `invoices/preview`）。
- 380: `("POST", "/api/v1/super-admin/fx-rate/refresh"): _PENDING,`。

### F-2 frontend/src/lib/apiErrorReason.ts
- 11-30: `export const API_ERROR_REASON_KEYS: Readonly<Record<string, string>> = {` の18行: `no_fields_to_update`(12), `conflict_constraint`(13), `role_not_editable_here`(14), `role_not_deletable`(15), `role_permissions_edit_forbidden`(16), `role_permissions_not_editable_here`(17), `role_page_keys_not_savable`(18), `role_not_assignable`(19), `merge_target_archived`(20), `bill_to_country`(21), `recurrence_meet_not_allowed`(22), `recurrence_not_available`(23), `recurrence_after_until`(24), `recurrence_scope_not_allowed`(25), `recurrence_google_source`(26), `recurrence_scope_required`(27), `recurrence_occurrence_invalid`(28), `recurrence_this_not_allowed`(29)。
- 新コード `duty_needs_carrier`・`duty_rule_overlap`・`shipping_required`・`fx_rate`・`tax_rate`・`payment_method` の表の行: 無い（検索した語: frontend/src で `duty_needs_carrier`, `shipping_required`, `payment_method_ref` は0件。`duty_rule_overlap` は backend/app/routers/duty_rules.py:46 と services/duty_rules.py:40 に在り、apiErrorReason.ts には無い）。
- 41 `export const NOT_FOUND_PREFIX = "not_found:";`、48-115 `NOT_FOUND_TARGET_KEYS`（`invoice`(56)・`quote`(62)・`contact`(54)・`company`(51) を含む66行）。

### F-3 frontend/src/lib/apiErrorReason.test.ts
- 76: `expect(Object.keys(API_ERROR_REASON_KEYS).length).toBe(18);`
- 89: `expect(Object.keys(NOT_FOUND_TARGET_KEYS).length).toBe(66);`
- 146: `expect(Object.keys(NOT_FOUND_TARGET_KEYS).filter((t) => !used.has(t))).toEqual([]);`

### F-4 backend/tests/test_api_error_reason_sync.py
- 41-61: `def test_table_rows_are_read(): assert _codes() == [` の固定の一覧18件（上の F-2 と同じ順）。
- 64-67: `test_table_codes_are_used_in_app`（表のコードが backend/app/*.py に `"コード"` の形で在ることを確かめる）。
- 72-73: `assert len(targets) == 66` / `assert len(set(targets)) == 66`。

### F-5 ja.json・en.json の apiError
- `frontend/src/locales/ja.json:6224` と `frontend/src/locales/en.json:6224`: `"apiError": {`。キー（6225-6242）: `noFieldsToUpdate`, `conflictConstraint`, `roleNotEditableHere`, `roleNotDeletable`, `rolePermissionsEditForbidden`, `rolePermissionsNotEditableHere`, `rolePageKeysNotSavable`, `roleNotAssignable`, `mergeTargetArchived`, `billToCountry`, `recurrenceMeetNotAllowed`, `recurrenceNotAvailable`, `recurrenceAfterUntil`, `recurrenceScopeNotAllowed`, `recurrenceGoogleSource`, `recurrenceScopeRequired`, `recurrenceOccurrenceInvalid`, `recurrenceThisNotAllowed`。続く 6243 `notFound`, 6244 `notFoundUnknown`, 6245 `notFoundTarget`。
- 例（ja.json:6234）: `"billToCountry": "請求先の国が入っていないため、請求書を作れません。取引先の画面で、既定の請求先の住所と国を入れてください。",`。新6コードに対応するキー: 無い（検索した語: ja.json・en.json の apiError 内）。

---

## G. shipping calculate と権限の配布

### G-1 backend/app/routers/shipping.py の calculate
- 386-390: `@router.post("/shipping/calculate", response_model=ShippingCalcResponse, dependencies=[Depends(require_permission("shipping.calculate"))],)`
- 391-396: `async def calc_shipping(data: ShippingCalcRequest, db: AsyncSession = Depends(get_db), tenant_id: int = Depends(get_current_tenant), current_user: User = Depends(get_current_user),):`
- 409: `if data.carrier == "fedex":`（FedEx ライブ。それ以外は静的表。397-407 の docstring）。
- 受ける形（backend/app/schemas/shipping.py:73-104 `ShippingCalcRequest`）: `country_code: str = Field(min_length=2, max_length=3)`, `weight_kg: Decimal = Field(gt=0, max_digits=10, decimal_places=3)`, `carrier: Optional[str] = Field(default=None, max_length=50)`, `origin_country_code: Optional[str]`(min 2/max 3), `origin_postal_code: Optional[str]`(max 20), `destination_postal_code: Optional[str]`(max 20), `length_cm`, `width_cm`, `height_cm`, `address_type: Optional[Literal["RESIDENTIAL", "BUSINESS"]]`, `order_id: Optional[int]`。
- 返す形（107-134）: `ShippingCalcResult`＝`carrier: str`, `zone: str`, `fee: Decimal`, `currency: str`, `source: Literal["static", "fedex_live"] = "static"`, `service_type`, `service_name`, `transit_days`, `delivery_timestamp`, `surcharges`。`ShippingCalcResponse`＝`results: list[ShippingCalcResult]`, `cheapest: Optional[ShippingCalcResult]`, `live_error: Optional[str] = None`, `rate_precision: Optional[Literal["exact", "approximate"]] = None`。

### G-2 権限 invoices.create・invoices.update・shipping.calculate を役割に配るコード
- 権限の定義: `migrations/004_add_phase2_permissions.sql:23` `('invoices.create', 'invoices', 'create', '請求書の発行', '請求'),`、24 `('invoices.update', 'invoices', 'update', '請求書の編集', '請求'),`、29 `('shipping.calculate', 'shipping', 'calculate', '配送料の自動計算', '配送')`。一覧: `docs/handoff/role-menu-permissions/perms-135.tsv:44-45,111`。
- 新しい会社の既定の役割（`backend/app/services/tenant.py` の `DEFAULT_ROLES`、49-186）:
  - 56 オーナー: `"permissions": "ALL"`
  - 65 システム管理者: `"permissions": "ALL_EXCEPT_SYSTEM_MANAGE"`
  - 85-86 マネージャー: `"invoices.view", "invoices.update",` / `"shipping.view", "shipping.calculate",`（invoices.create は無い）
  - 114-115 営業: `"invoices.view", "invoices.create",` / `"shipping.view", "shipping.calculate",`（invoices.update は無い）
  - 140-141 CS: `"invoices.view",` / `"shipping.view",`（invoices.create・shipping.calculate は無い）
  - 仕入れ（149-166）: invoices・shipping の権限は無い。
  - 179 発送: `"shipping.view", "shipping.calculate", "shipping.manage",`（invoices.* は無い）
- 既存の会社の役割への配布: migrations 内で `invoices.create`・`invoices.update`・`shipping.calculate` を役割に割り当てる行は、004 の権限定義以外に無い（検索した語: `invoices.(view|create|update)`, `shipping.(view|calculate)` を migrations/ で検索。004 のみ）。本番の役割の表の中身: 未確認（読んでいない）。
- その他の参照: backend/app/routers/assistant.py:83 `_perm_invoices_create = require_permission("invoices.create")`。

---

## H. frontend

### H-1 frontend/src/pages/invoice-create/InvoiceCreatePage.tsx（全449行）
- import（11-29）: `useState, FormEvent` / `useNavigate, useLocation` / `useTranslation` / `api, ApiError` / `useApiQuery` / `PageLayout` / `CompanyContactSelector` / `InventorySearchBar, InventorySearchCandidate` / `Button` / `SelectControl` / `LineItem, QuoteHandoffState, blankItem, buildInitialItems, weightForUnit`（../quote-create/quoteDraft）/ `TextFieldControl` / `LoadingBlock`。
- 型: 31-39 `interface QuoteSummary`、42-58 `interface QuoteDetail`（`id, quote_code, company_id, contact_id, currency, items[]`。`shipping_fee`・`tax_amount`・`shipping_carrier` の欄は無い）。
- 全体の区切り: 219-228 `PageLayout`（`titleText={t("invoices.createTitle")}`）、231-238 エラー表示・「取引先の画面へ」ボタン、240-255 モード切替（`data-testid="invoice-mode-inventory"`(244)・`"invoice-mode-quote"`(251)）、257-293 `mode === "quote"` の見積選択（`data-testid="invoice-from-quote"`(258)）、295-445 `<form onSubmit={submitInvoice}>`（取引先 304-311、通貨・備考 312-325、明細 327-408、空行追加 410-412、`InventorySearchBar` 414-420、送料・消費税・合計・総重量 422-439、キャンセル／作成 441-444）。
- state（77-100）:
  - 77 `const [mode, setMode] = useState<"inventory" | "quote">("quote");`
  - 80 `const [companyId, setCompanyId] = useState<number | null>(draft?.companyId ?? null);`
  - 81 `const [contactId, setContactId] = useState<number | null>(draft?.contactId ?? null);`
  - 82 `const [selectorError, setSelectorError] = useState("");`
  - 83 `const [currency, setCurrency] = useState(draft?.currency ?? "USD");`
  - 84 `const [shippingFee, setShippingFee] = useState(draft?.shippingFee ?? "");`
  - 85 `const [taxAmount, setTaxAmount] = useState(draft?.taxAmount ?? "");`
  - 86 `const [notes, setNotes] = useState(draft?.notes ?? "");`
  - 87 `const [items, setItems] = useState<LineItem[]>(() => buildInitialItems(handoff));`
  - 89 `const [sourceQuoteCode, setSourceQuoteCode] = useState<string | null>(null);`
  - 92 `const quotesQ = useApiQuery<QuoteSummary[]>("/quotes?status=approved", { enabled: mode === "quote" });`
  - 96 `const [error, setError] = useState("");` / 98 `const [billToCompanyId, setBillToCompanyId] = useState<number | null>(null);` / 100 `const [saving, setSaving] = useState(false);`
- 見積の読み込み（136-167）: 141 `const q = await api.get<QuoteDetail>(`/quotes/${quoteId}`);`、144 `setCurrency(q.currency);`。見積から作る道（POST /invoices/from-quote）を呼ぶ行: 無い（検索した語: `from-quote`。この画面は見積を読み込んで 191 の POST /invoices を使う）。
- 計算（169-174）: `const subtotal = items.reduce((s, it) => s + it.quantity * it.unit_price, 0);` / 171 `const totalWeight = items.reduce((s, it) => s + it.quantity * (it.weight ?? 0), 0);` / 172 `const shipping = shippingFee ? Number(shippingFee) : 0;` / 173 `const tax = taxAmount ? Number(taxAmount) : 0;` / 174 `const total = subtotal + shipping + tax;`
- POST の中身（191-208）: `api.post<{ id: number }>("/invoices", { company_id: companyId, contact_id: contactId, currency, shipping_fee: shipping || null, tax_amount: tax || null, notes: notes || null, items: items.map((i) => ({ product_id, product_name, name_en, condition, unit, quantity, unit_price, weight })) })`。成功で 209 `navigate(`/invoices/${inv.id}`);`。失敗 210-212: `ApiError` で `e.responseDetail === "bill_to_country"` のとき `setBillToCompanyId(companyId)`。
- 通貨の欄（313-320）: `<SelectControl fullWidth value={currency} onChange={(e) => setCurrency(e.target.value)}>` の中に `<option value="JPY">JPY</option>`(316) / `<option value="USD">USD</option>`(317) / `<option value="EUR">EUR</option>`(318)。
- 送料・税・合計の欄（422-439）: 425 `<TextFieldControl type="number" min="0" step="1" value={shippingFee} onChange={(e) => setShippingFee(e.target.value)} />`、429 `<TextFieldControl type="number" min="0" step="1" value={taxAmount} onChange={(e) => setTaxAmount(e.target.value)} />`、433 合計 `{total.toLocaleString()} {currency}`、437 総重量 `data-testid="invoice-total-weight"`。
- 在庫表からの引き継ぎ: `QuoteHandoffState`（../quote-create/quoteDraft）。
- FedExRateModal を使う行: 無い（検索した語: `FedExRateModal`。このファイルに0件）。支払方法の欄・為替の表示・住所の表示: 無い（検索した語: `payment`, `fx`, `ship_to`）。

### H-2 frontend/src/features/secretary/SecretaryDraftInvoice.tsx
- 31: `const CURRENCIES = ["JPY", "USD", "EUR"] as const;`
- 58: `const [currency, setCurrency] = useState<string>(draft.currency || "JPY");`
- 92-103 POST の中身: `api.post<{ id: number }>("/invoices", { company_id: customer.companyId, contact_id: customer.contactId, currency, due_date: dueDate || null, notes: notes || null, items: items.map((i) => ({ product_name: i.name.trim(), quantity: Number(i.quantity), unit_price: Number(i.unitPrice) })), });`（`shipping_fee`・`tax_amount`・`shipping` は送らない）。
- 185-191 通貨の欄: `<Select fullWidth label={t("secretary.invoice.currency")} value={currency} onChange={(e) => setCurrency(e.target.value)} options={CURRENCIES.map((c) => ({ value: c, label: c }))} />`。
- 105-107 失敗: `setError(e instanceof Error ? e.message : t("common.saveError"));`。

### H-3 frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx
- 70 `payment_method: string | null;`、86 `fx_rate_snapshot: FxRateSnapshot | null;`、90 `payment_fee: number | null;`、93 `paypal_copy_pdf_at: string | null;`。
- 296: `<div><strong>{t("invoices.paymentMethod")}:</strong> {invoice.payment_method || "-"}</div></div>`（支払方法の表示）。
- PDF: 151-153 `const handleDownloadPdf = () => { window.open(`/api/invoices/${id}/pdf`, "_blank");`、155-157 `handleDownloadCopyPdf`（`/api/invoices/${id}/paypal-copy-pdf`）、222 `<Button variant="secondary" size="sm" layoutClassName="field-h-md" onClick={handleDownloadPdf}>{t("invoices.snapshot.downloadPdf")}</Button>`、247-248 写し PDF のボタン。
- 発行ボタン: 198-199 `invoice.status === "draft" && hasPermission("invoices.create")` → `doAction("issue")`。`doAction` は 137 `await api.post(`/invoices/${id}/${action}`, body);`。
- PATCH を呼ぶ所: 無い（検索した語: `api.patch`, `patch(`。api の呼び出しは 137 の `api.post` のみ）。`payment_method_id`・支払方法の選択欄: 無い。

### H-4 frontend/src/components/FedExRateModal.tsx
- 48-58 `interface Props`: `open: boolean;`(50) / `onClose: () => void;`(51) / `destinationCountryCode?: string;`(53) / `weightKg: number;`(55) / `onSelectRate: (fee: number, currency: string, serviceType: string | null) => void;`(57)。`originCountryCode`・`destinationPostalCode` の props: 無い（検索した語: Props 内）。
- 107-110: `destinationCountryCode: destinationCountryCodeProp, weightKg, onSelectRate,` の分割代入。
- useState（112-118）: `useState("JP")`(112 originCountryCode) / `useState(destinationCountryCodeProp ?? "")`(113 destCC) / `useState(weightKg)`(114 internalWeightKg) / `useState("")`(115 destinationPostalCode) / `useState(false)`(116 loading) / `useState<ShippingCalcResponse | null>(null)`(117) / `useState<string | null>(null)`(118)。
- 128 `weight_kg: internalWeightKg,`、130 `origin_country_code: originCountryCode || "JP",`、131 `...(destinationPostalCode ? { destination_postal_code: destinationPostalCode } : {}),`。
- 205 `disabled={loading || !originCountryCode || !destCC}`。
- onSelectRate の呼び出し: 340 `onSelectRate(r.fee, r.currency, r.service_type);`（carrier を渡さない）。
- 呼び出し元: backend ではなく frontend/src/pages/quote-create/QuoteCreatePage.tsx:22（import）・289-294 `<FedExRateModal open={showFedExModal} onClose={() => setShowFedExModal(false)} weightKg={totalWeight} onSelectRate={(fee) => setShippingFee(String(Math.round(fee)))} />`。ほかの呼び出し元: 無い（検索した語: `FedExRateModal`。frontend/src で QuoteCreatePage と自身の test・stories のみ）。
- 試験・stories: frontend/src/components/FedExRateModal.test.tsx, FedExRateModal.stories.tsx。

### H-5 frontend/src/pages/quote-detail/QuoteDetailPage.tsx
- 100-104: `const handleFetchFxRate = async () => { if (!quote || !quote.currency || quote.currency === "JPY") return; setFxLoading(true); try { const result = await api.get<FxRateResult>(`/fx-rate/${quote.currency}`);`（104）。
- 169: `{fxRate.fetched_at && <span style={{ color: "var(--text-muted)", marginLeft: "var(--space-2)" }}>({fxRate.fetched_at.slice(0, 19)}Z)</span>}`
- 見積から請求書を作る呼び出し: 同ファイル内の `from-quote`（本調査では行番号を取っていない。未確認）。

### H-6 使える金型の props の定義行（frontend/src/components/）
- Select.tsx: 20-24 `SelectOption`＝`value: string;`(21) `label: string;`(22) `disabled?: boolean;`(23)。26-32 `interface SelectControlOwnProps`＝`options: SelectOption[];`(27) `size?: SelectSize;`(28) `fullWidth?: boolean;`(29) `placeholder?: string;`(30)。39-52 options 方式と children 方式の2形。`export const SelectControl`(64)。117-121 `interface SelectOwnProps extends SelectControlOwnProps`＝`label?: string;`(118) `helperText?: string;`(119) `error?: string;`(120)。`export function Select`(126)。
- Button.tsx: 25-36 `interface ButtonOwnProps`＝`variant?: ButtonVariant;`(26) `size?: ButtonSize;`(27) `fullWidth?: boolean;`(30) `loading?: boolean;`(31) `children?: ReactNode;`(36)。41 `export type ButtonProps = ButtonOwnProps & Omit<ButtonHTMLAttributes<HTMLButtonElement>, ...>;`。`export const Button`(43)。
- TextField.tsx: 23-29 `interface TextFieldOwnProps`＝`label?: string;`(24) `helperText?: string;`(25) `error?: string;`(26) `size?: TextFieldSize;`(27) `fullWidth?: boolean;`(28)。`export const TextFieldControl`(43)。`export function TextField`(60)。
- Textarea.tsx: 20-25 `interface TextareaOwnProps`（`label?`, `helperText?`, `error?`, `size?`, `fullWidth?`）。`export function Textarea`(62)。
- CompanyContactSelector.tsx: 60-70 `interface CompanyContactSelectorProps`＝`value: CompanyContactSelectorValue;`(61) `onChange: (next: CompanyContactSelectorValue) => void;`(62) `required?: boolean;`(64) `disabled?: boolean;`(66) `error?: string;`(70)。
- InventorySearchBar.tsx: 72-84 `export interface InventorySearchBarProps`＝`onSelect: (candidate: InventorySearchCandidate) => void;`(74) `disabled?: boolean;`(78) `placeholder?: string;`(80) `testIdPrefix?: string;`(84)。
- Modal.tsx: 25-32 `interface ModalProps`＝`open: boolean;`(26) `onClose: () => void;`(27) `title: string;`(28) `size?: ModalSize;`(29) `children: ReactNode;`(32)。`export function Modal`(36)。別に components/loading/Modal.tsx:4-17（`open, onClose, title?: ReactNode, children?, footer`）。
- PageLayout.tsx（使用: InvoiceCreatePage.tsx:219 `titleText` / `subtitleKey` / `headerAction`）。定義行は未確認（読んでいない）。

---

## I. 試験

### I-1 backend/tests（請求書の道・fx-rate・invoice_renderer を呼ぶファイル）
`backend/tests/test_invoices.py`（70件）, `test_issuer.py`（13）, `test_paypal_invoicing.py`（16）, `test_company_stats.py`（6）, `test_fx_rate_admin_router.py`（9）, `test_products.py`（1）, `error_detail_baseline.json`（1）。

POST /invoices・from-quote・issue・PATCH を呼ぶ行:
- test_invoices.py: 51（`_create_invoice` の POST /invoices）, 145（PATCH）, 161（issued 後の PATCH → 400）, 171（PATCH 空）, 187・207・221・226・244（from-quote）, 311（POST /invoices）, 341・353-354・363・375-377・387-388・399-401・410・417・436・471・519-520・533-534・545 付近（issue 経由の状態遷移）, 564・572・580・590・602（TestInvoicesValidation の POST）。
- test_issuer.py: 266・287・309（POST /invoices）, 278・301（from-quote）, 319（GET）。
- test_paypal_invoicing.py: 199（POST /invoices）, 205（issue）, 214・239・278（paypal-link）, 247・257・282（paypal-copy-pdf）。
- test_company_stats.py: 79（POST /invoices）, 89・135・183（issue）, 91（pay）, 96（void）。
- test_products.py: 442（POST /invoices）。
- invoice_renderer を呼ぶ行: test_invoices.py 678・698（render_invoice_pdf）・704・722（render_quote_pdf）・728・748（render_invoice_pdf, fx つき）。test_issuer.py 19（import）・175・177・209・248（render_invoice_pdf）・182・234（render_quote_pdf）。test_paypal_invoicing.py 276（`monkeypatch.setattr(inv_mod, "render_invoice_pdf", ...)`）・288・296。
- GET /fx-rate/{currency}（invoices.py 側）を呼ぶ試験: 無い（検索した語: `fx-rate/`。test_fx_rate_admin_router.py:97-104 は route の `path == "/api/v1/fx-rate/{currency}"` が在ることを確かめる。実際に呼ぶ行は無い）。`get_fx_rate` を差し替える行: test_fx_rate_admin_router.py:191・234・254 `"app.services.fx_rate.get_fx_rate"`（refresh の道向け）。test_invoices.py 618-670 `TestFxRateService`（`get_fx_rate` の単体）。
- draft-context・preview・duty_needs_carrier 等を呼ぶ試験: 無い。

tax_amount・shipping_fee・exchange_rate_jpy・payment_method を送る・使う行の全一覧:
- test_invoices.py:146 `"payment_method": "銀行振込",`（PATCH の中身）／150 `assert res.json()["payment_method"] == "銀行振込"`。
- test_invoices.py:236-237 `"shipping_fee": "500.00",` / `"tax_amount": "100.00",`（見積作成の中身。見積から請求書を作る試験 232-244）。
- test_invoices.py:314 `"tax_amount": "1000.00",`（POST /invoices の中身）。
- test_invoices.py:260-306 `_calc_currency_amounts` の単体（引数に rate_jpy・rate_usd。JPY・USD・EUR）。
- test_invoices.py:690-691・716-717・740-741 `"shipping_fee": ..., "tax_amount": ...`（レンダラー試験の invoice_data / quote_data）。
- test_invoices.py:764-773 `"currency": "JPY"` … `"exchange_rate_jpy": None, "exchange_rate_usd": None,` … `"payment_method": None,`（InvoiceResponse スキーマの試験, class 752）。
- test_issuer.py:51-52・69-70 `"shipping_fee": 0.0,` / `"tax_amount": 0.0,`（`_invoice_data`・`_quote_data`）。
- test_paypal_invoicing.py:293 `"subtotal": 1000, "shipping_fee": 0, "tax_amount": 0, "total_amount": 1000,`。
- `exchange_rate_jpy` を POST /invoices で送る行: 無い（検索した語: `exchange_rate_jpy`。test_invoices.py:769 のスキーマ試験のみ）。`payment_method` を POST /invoices で送る行: 無い。

### I-2 frontend の試験
- InvoiceCreatePage を使う試験: `frontend/src/lib/query/batch3cPages.test.tsx:16`（import）・79（`{ name: "invoice create", Page: InvoiceCreatePage, route: "/invoices/new", ... path: "/quotes?status=approved", text: "Q-7" ...}`）, `frontend/src/components/CommerceNavigationButtonMigration.test.tsx:7`・86・92・107・120, `AllLegacyButtonDynamicMigration.test.tsx:7`・44（`invoice-mode-inventory`・`invoice-mode-quote`）, `BillToCountryGuidance.test.tsx:7`・46, `CommerceSubmitButtonMigration.test.tsx:6`・68（`'invoice-add-blank', 'invoice-item-row-'`）。InvoiceCreatePage 専用の試験ファイル（InvoiceCreatePage.test.tsx）: 無い（検索した語: `InvoiceCreatePage*test*` のファイル名）。
- SecretaryDraftInvoice: 専用の試験ファイル無い（検索した語: `SecretaryDraftInvoice*test*`）。使う試験: `frontend/src/features/secretary/SecretaryChat.test.tsx`（46 `mock.permissions = new Set(["customers.view", "invoices.create"]);`、50 `const invoiceReply = ...`、214 `describe("SecretaryChat invoice draft", ...)`、229 `expect(mock.post).toHaveBeenCalledWith("/invoices", {` 、263）。
- InvoiceDetailPage: 専用の試験ファイル無い。使う試験: `frontend/src/lib/query/batch3aPages.test.tsx:16`・79（`path: "/invoices/3", text: /INV-3/`）, `AllLegacyButtonOperationMigration.test.tsx:8`・27, `CommerceNavigationButtonMigration.test.tsx:8`・99。
- FedExRateModal: `frontend/src/components/FedExRateModal.test.tsx`（70 `describe("FedExRateModal"`、71・76・82・88・122・128・145 の it。119 `expect(onSelectRate).toHaveBeenCalledWith(5000, "JPY", "FEDEX_IP");`、22 `"fedexRateModal.originPlaceholder": "JP",`）。
- QuoteDetailPage の試験ファイル: 無い（検索した語: `QuoteDetailPage*test*`）。

---

## 補足（調査中に見つけた、設計書の行番号との差）
- design.md §3-4 は topics.py の請求書の道を `:228-235` と書く。基準 commit では 237-244。
- design.md が「便V の後に入る」と書く振込先の表の2列・索引・トリガー6つは、基準 commit の tenant.py（1278-1289, 1419-1435）と migrations/20261115_100000_add_payment_method_versioning.sql に既にある。
- design.md が「便A」で足すと書く invoices の5列は tenant.py:904-908 に既にある。
- design.md が便B と書く関税の額の道・services/duty_rules.py・services/fx_currencies.py は既にある。関税の計算（invoice_totals）は無い。
