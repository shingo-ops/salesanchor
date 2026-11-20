# card-E: PayPal の支払い手数料を請求書の合計に足す（invoice-create-portfolio 便E）

状態: 発行（Opus 2026-11-21）。
設計: docs/handoff/invoice-create-portfolio/design-e.md（審査 APPROVE）・recon-e.md。
実装承認: PO「1」（2026-11-20: 支払方法ごとの手数料をお客様への合計に足す）・PO「2」（同日: 円以外の請求書は PayPal の為替手数料 4% も足す）。PR マージ・デプロイまでの完走は ccopusgo の委任の範囲。
担当: クラウドの Sonnet（実装）。設計と審査は Opus。
枝: release/invoice-portfolio-e-payment-fee（origin に設計の commit 662a243d7 まで在る。この枝の上に実装を足す）。
基準: origin/main 6f997ca972ab10fc81751f0130c607f30eab5561（設計の基準 77971367b から触るファイルの差 0 件を 2026-11-21 に確かめた）。
危険便か: はい（migrations/ と scripts/run_all_migrations.sh を含む。ADR-136 の GO 手順。移行は列を足すだけ・値を書かない）。

## 受領確認（最初の報告の 1 行目に書く）

`RECEIVED invoice-portfolio-E HEAD=` に続けて、手順1 の後の `git rev-parse HEAD` の 40 桁を書く。

## 0. Opus の決めごと（根拠つき）

- D1 手数料は支払方法の種類が paypal のときだけ。bank・wise・支払方法なしは 0 で表を読まない（design-e §3-1）。
- D2 行は public.payment_fee_settings（migrations/20261002_160000_create_payment_fee_settings.sql:7-25）から読む。service='paypal'・currency='JPY'・期間内・テナント独自の行が共用の行（tenant_id IS NULL）より先・同じ側では effective_from が新しい1行（design-e §3-1）。
- D3 式は 元の額 B（小計＋送料＋税＋関税）× 率合計 /100 ＋ 固定額（円を請求書の通貨へ _convert）を通貨の最小単位へ切り捨て（design-e §3-2）。K1: 円 100,000 → 3,640 / 103,640。K2: USD 1,000.00・1USD=150円 → 81.26 / 1,081.26。
- D4 計算できないときは新しい理由 "payment_fee"（REASON_ORDER の最後）。作る道・PATCH は 409 "payment_fee" で何も書かない（design-e §3-1・§3-3）。
- D5 保存は全テナントの invoices に新しい2列 payment_fee_charged NUMERIC(15,2)・payment_fee_snapshot JSONB。既存の payment_fee（入金時に PayPal が引いた実額。integrations.py:799 が書く）には触らない（design-e §3-4）。
- D6 PayPal リンクは支払方法が paypal の請求書だけ出せる（それ以外は 409 "payment_method"）。詳細画面のボタンも同じ条件（design-e §3-5）。
- D7 下書きの PATCH で支払方法が変わったら合計を作り直して1文で書く。止まるときは何も書かない（design-e §3-5）。
- D8 AI 用の分類表に payment_fee_snapshot を mask で1行足す。件数 1164 → 1165（design-e §3-4・前例 1206acb56）。
- D9 新しい PG 試験ファイルは作らない。雛形と移行の確かめは既存の backend/tests/test_tenant_duty_rules_pg.py（便A の試験）に足す。行の選び方（K4）は既存の backend/tests/test_invoice_totals_pg.py（tenant 953）に足す。どちらも `_REVIEWED`（test_tenant_loop_migration_guard.py）の行に新しい移行の名前を足す。

## 0-1. カード発行前チェック（docs/ai-agents/design-partner.md §5.5）

| # | 点検 | 結果 |
|---|---|---|
| 1 | 設計の審査は APPROVE か | ○ design-e.md（APPROVE） |
| 2 | PO の実装承認があるか | ○ PO「1」「2」2026-11-20 |
| 3 | 触るファイルを全部挙げたか | ○ §1 |
| 4 | 触らない範囲を書いたか | ○ §1 末尾 |
| 5 | 変更前の文を実物から写したか | ○ §2（2026-11-21 の 662a243d7 から） |
| 6 | 受入条件が○×で判定できるか | ○ design-e §5 K1〜K12 |
| 7 | 危険パスの有無 | あり（migrations/・run_all_migrations.sh）→ ADR-136 |
| 8 | 新しい部品・色の直書きが無いか | ○ TotalsBox・既存の tfoot の形 |
| 9 | i18n の ja/en 同じキー | ○ §2-13 |
| 10 | 推測の値が無いか | ○ 数は design-e §3-2 の計算と本番の 10 行（recon-e R1） |
| 11 | 想定の分かれ道を書いたか | ○ §4 |
| 12 | 止める条件を書いたか | ○ §0-3・§4 |
| 13 | 報告の形を決めたか | ○ §5 |

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・commit は git log で確かめる | ○（§3） |
| guards/03-file.md | 既存ファイルの編集は Edit ツール。新しいファイルは移行1つだけで Write。プレースホルダを残さない | ○（§2） |
| guards/04-worktree.md | new-worktree.sh で作る・出力をパイプに通さない・実在は git worktree list で確かめる・push は -u 付き | ○（手順1・手順10） |
| guards/10-executor.md | 散文で頼まない。手順はコマンドで書く | ○（§3） |

## 0-3. 実装前点検（手順2 で流す。外れたら実装せず BLOCKED: で停止）

P1 次の指紋（git hash-object の先頭12字）がすべて一致する。1つでも違えば BLOCKED: で停止。

| ファイル | 指紋 |
|---|---|
| backend/app/services/invoice_totals.py | 7bb06ec438b7 |
| backend/app/routers/invoices.py | 6397449b71d1 |
| backend/app/schemas/invoice.py | 31d668f49dba |
| backend/app/services/invoice_renderer.py | 7bdbd1c6d641 |
| backend/app/services/tenant.py | d4638a0ac692 |
| backend/tests/conftest.py | 1a0c1bd58caf |
| backend/tests/test_paypal_invoicing.py | a0fbfe3ce876 |
| backend/tests/test_invoice_totals.py | e1923e8ffd60 |
| backend/tests/test_invoice_totals_pg.py | 97ece1954d88 |
| backend/tests/ops/test_ai_cloud_views.py | 6416eed0a208 |
| backend/tests/rls_bootstrap.py | 68d2612cc916 |
| backend/tests/test_tenant_loop_migration_guard.py | 066aa6537fe2 |
| backend/tests/test_api_error_reason_sync.py | f1c77b10adcd |
| migrations/20261024_100300_create_ai_cloud_views.sql | d5f5b75a29eb |
| docs/handoff/cloud-case-ai/stage1-column-class.tsv | dd7c9deaf3ee |
| scripts/migration-guard/reference-allowlist.tsv | 54432145a726 |
| scripts/run_all_migrations.sh | 07c09967a5a8 |
| frontend/src/pages/invoice-create/InvoiceCreatePage.tsx | 51d7c5391aac |
| frontend/src/pages/invoice-create/InvoicePaymentTotalsSection.tsx | ffbeba9008d9 |
| frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx | 15e93b6a56cb |
| frontend/src/lib/apiErrorReason.ts | e3a7d00bda28 |
| frontend/src/lib/apiErrorReason.test.ts | e90a3f92d948 |
| frontend/src/lib/invoiceDraftContext.ts | ed6926a36b29 |
| frontend/src/locales/ja.json | 3b2ecbb4482e |
| frontend/src/locales/en.json | 11ebb563122d |
| frontend/src/pages/invoice-create/InvoiceCreatePage.test.tsx | bbb73267f8c2 |

P2 新しい移行の名前 migrations/20261121_100000_add_invoice_payment_fee_charged.sql がまだ無い（ls の数 0）。
P3 backend/tests/test_tenant_duty_rules_pg.py が在る（便A の試験。D9 で足す先）。

## 1. 触るファイル

新規（1）:
- migrations/20261121_100000_add_invoice_payment_fee_charged.sql

変更（backend）:
- backend/app/services/invoice_totals.py
- backend/app/routers/invoices.py
- backend/app/schemas/invoice.py
- backend/app/services/invoice_renderer.py
- backend/app/services/tenant.py
- backend/tests/conftest.py
- backend/tests/test_invoice_totals.py
- backend/tests/test_invoice_totals_pg.py
- backend/tests/test_tenant_duty_rules_pg.py
- backend/tests/test_paypal_invoicing.py
- backend/tests/test_invoices_create_flow.py
- backend/tests/test_api_error_reason_sync.py
- backend/tests/ops/test_ai_cloud_views.py
- backend/tests/rls_bootstrap.py
- backend/tests/test_tenant_loop_migration_guard.py

変更（移行・分類・一覧）:
- migrations/20261024_100300_create_ai_cloud_views.sql
- docs/handoff/cloud-case-ai/stage1-column-class.tsv
- scripts/migration-guard/reference-allowlist.tsv
- scripts/run_all_migrations.sh

変更（frontend）:
- frontend/src/lib/invoiceDraftContext.ts
- frontend/src/lib/apiErrorReason.ts
- frontend/src/lib/apiErrorReason.test.ts
- frontend/src/pages/invoice-create/InvoiceCreatePage.tsx
- frontend/src/pages/invoice-create/InvoicePaymentTotalsSection.tsx
- frontend/src/pages/invoice-create/InvoiceCreatePage.test.tsx
- frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx
- frontend/src/locales/ja.json
- frontend/src/locales/en.json
- frontend/api-contract/openapi.json（手順7 の export_openapi が書き換える生成物。手で書かない）

触らない: 既存の invoices.payment_fee 列とそれを書く integrations.py・payment_fee_settings の表と設定の画面・見積（quotes）の道と見積の PDF（invoice_renderer.py:645 付近は None のまま）・from-quote の道・deploy.yml・frontend/tests-e2e/。

## 2. 変更

### 2-1. migrations/20261121_100000_add_invoice_payment_fee_charged.sql（新規・Write）

形は前例 migrations/20261113_120000_create_tenant_duty_rules_and_invoice_columns.sql の invoices に列を足す塊と同じ（DO $$ で pg_namespace の `nspname ~ '^tenant_[0-9]+$'` を回し、EXECUTE format(... %I ...) で ALTER TABLE ... ADD COLUMN IF NOT EXISTS、続けて COMMENT ON COLUMN、最後に RAISE NOTICE）。値を書く文・消す文は一切入れない（test_migration_writes_no_values が見る）。

- 先頭のコメント: `-- invoice-create-portfolio 便E（design-e.md §3-4）: お客様への合計に足した支払い手数料と、その計算の写しを全テナントの invoices に足す。値は書かない。冪等。`
- 列: `payment_fee_charged NUMERIC(15, 2)`・`payment_fee_snapshot JSONB`（どちらも NULL 可・既定値なし）
- 説明: payment_fee_charged「お客様への合計に足した支払い手数料（請求書の通貨）。入金時の実額は payment_fee」／payment_fee_snapshot「手数料の計算に使った設定の行と値の写し」
- invoices の表が無いスキーマは飛ばす（前例と同じ to_regclass の確かめ。前例に無ければ `IF to_regclass(format('%I.invoices', r.nspname)) IS NULL THEN CONTINUE; END IF;` を足す）

### 2-2. scripts/run_all_migrations.sh

`run_sql migrations/20261119_120000_add_calendar_events_color_key.sql` の行の次（空行と mr_report_summary の前）に2行を足す:

```
# invoice-create-portfolio 便E: 請求書に支払い手数料の額と写しの列を足す（全テナント・冪等・値は書かない）
run_sql migrations/20261121_100000_add_invoice_payment_fee_charged.sql
```

### 2-3. backend/app/services/tenant.py（雛形）

invoices の雛形の `    shipping_snapshot JSONB,` の次・`    notes TEXT,` の前に足す（その2行の組は1か所だけ。`shipping_snapshot JSONB,` 単独は他にもあるので2行の組で探す）:

```
    -- invoice-create-portfolio 便E: お客様への合計に足した支払い手数料と計算の写し（移行 20261121_100000 と同じ形）
    payment_fee_charged NUMERIC(15, 2),
    payment_fee_snapshot JSONB,
```

### 2-4. backend/tests/rls_bootstrap.py・backend/tests/test_tenant_loop_migration_guard.py

- rls_bootstrap.py の `_TENANT_LOOP_MIGRATIONS` の最後 `    "20261115_100000_add_payment_method_versioning.sql": 1,` の次に `    "20261121_100000_add_invoice_payment_fee_charged.sql": 1,`。
- test_tenant_loop_migration_guard.py の一覧（:40-60 の frozenset。最後が `"20261115_100000_add_payment_method_versioning.sql",`）の次に `"20261121_100000_add_invoice_payment_fee_charged.sql",`。
- 同じファイルの `_REVIEWED` の `"test_tenant_duty_rules_pg.py"` の frozenset に新しい移行の名前を足す: `frozenset({"20261113_120000_create_tenant_duty_rules_and_invoice_columns.sql", "20261121_100000_add_invoice_payment_fee_charged.sql"})`。
- `_REVIEWED` の `"test_invoice_totals_pg.py"` の行が在れば、そこにも新しい移行の名前は足さない（K4 の試験は public の表だけを流す）。行が無ければ足さない。
- このファイルの他の試験が「新しい移行がどこかの一覧に無い」と言って落ちたら、その試験の言うとおりに一覧へ1行足す（足した場所を報告に書く）。

### 2-5. AI 用の分類（D8。前例 1206acb56 と同じ手順）

- migrations/20261024_100300_create_ai_cloud_views.sql: invoices の行（`('tenant_*','invoices',ARRAY['shipping_snapshot'],'mask','')` の付近。:454 付近）の次に `('tenant_*','invoices',ARRAY['payment_fee_snapshot'],'mask',''),` を1行足す（前後のカンマの並びを崩さない）。同じファイルの 3 行目の件数の文「1164 行」を「1165 行」にする。
- backend/tests/ops/test_ai_cloud_views.py:486 の `== 1164` を `== 1165` にする。
- docs/handoff/cloud-case-ai/stage1-column-class.tsv: `tenant_*	invoices	shipping_snapshot	mask		jsonb` の行の次に `tenant_*	invoices	payment_fee_snapshot	mask		jsonb`（区切りはタブ）。
- scripts/migration-guard/reference-allowlist.tsv の 20261024_100300 の行: 2列目の sha256 を手順5 で出す新しい値に替え、3列目（理由）の最後に ` / invoice-create-portfolio card-E（分類1行追加）` を足す。他の列は変えない。

### 2-6. backend/app/services/invoice_totals.py

（1）理由（:24-28）:
```
REASON_DUTY_CARRIER = "duty_needs_carrier"
REASON_PAYMENT_FEE = "payment_fee"
REASON_ORDER = (REASON_SHIPPING, REASON_FX, REASON_TAX, REASON_DUTY_CARRIER, REASON_PAYMENT_FEE)
```

（2）TotalsInputs の前に2つの型を足し、TotalsInputs に1項目足す:
```
@dataclass(frozen=True)
class PaymentFeeRow:
    id: int
    fee_type: str
    rate_pct: Decimal
    fixed_amount: Decimal
    threshold: Decimal | None


@dataclass(frozen=True)
class PaymentFeeRows:
    receiving: PaymentFeeRow | None
    fx: PaymentFeeRow | None
    required_fx: bool
```
TotalsInputs の最後（`fx: dict[str, FxRow]` の次）に `payment_fee_rows: PaymentFeeRows | None = None`。

（3）TotalsResult の `amount_usd: Decimal | None` の次（`_reasons` の前）に:
```
    payment_fee: Decimal = Decimal("0")
    payment_fee_snapshot: dict | None = None
```

（4）compute_totals の引数の最後に `payment_method_type: str | None = None`（`inputs: TotalsInputs,` の次）。

（5）計算の場所: 「請求書の通貨の為替」の塊（`if currency != "JPY": row = inputs.fx.get(currency) ...` が終わった所）の後、`usd_row = inputs.fx.get("USD")` の前に足す:
```
    # ── 支払い手数料（便E。PayPal だけ。design-e.md §3-2）──────
    payment_fee = Decimal("0")
    payment_fee_snapshot: dict | None = None
    if payment_method_type == "paypal":
        pf = inputs.payment_fee_rows
        bad = (
            pf is None
            or pf.receiving is None
            or (pf.required_fx and pf.fx is None)
            or pf.receiving.threshold is not None
            or (pf.fx is not None and pf.fx.threshold is not None)
        )
        if bad:
            reasons.add(REASON_PAYMENT_FEE)
            total_amount = None
        elif total_amount is not None:
            rows = [pf.receiving] + ([pf.fx] if pf.fx is not None else [])
            rate = sum((r.rate_pct for r in rows), Decimal("0"))
            fixed_jpy = sum((r.fixed_amount for r in rows), Decimal("0"))
            used_fee_fx: list[dict] = []
            try:
                fixed = _convert(fixed_jpy, "JPY", currency, inputs.fx, used_fee_fx) if fixed_jpy else Decimal("0")
            except _FxMissing:
                reasons.add(REASON_FX)
                total_amount = None
            else:
                base = total_amount
                payment_fee = floor_minor(base * rate / Decimal("100") + fixed, currency)
                total_amount = base + payment_fee
                payment_fee_snapshot = {
                    "method_type": "paypal",
                    "fee_types": [r.fee_type for r in rows],
                    "setting_ids": [r.id for r in rows],
                    "rate_pct": str(rate),
                    "fixed_amount_jpy": str(fixed_jpy),
                    "fixed_converted": str(fixed),
                    "base_amount": str(base),
                    "base_date": inputs.base_date.isoformat(),
                }
```
注意: `_convert` は円 → 請求書の通貨で、ここでは「固定額を足してから切り捨て」なので、固定額だけ先に _convert で切り捨てる形になる。K2 の期待値 81.26 は「1,000×8.1/100 = 81」＋「40/150 = 0.26（切り捨て）」= 81.26 で、どちらの順でも同じ値になることを試験で確かめる（K2 の数が合わなければ式を変えずに BLOCKED: で停止）。

（6）`return TotalsResult(` の `amount_usd=amount_usd,` の次に `payment_fee=payment_fee,`・`payment_fee_snapshot=payment_fee_snapshot,`。

（7）読む関数を load_totals_inputs の前に足す:
```
async def load_payment_fee_rows(
    db: AsyncSession, tenant_id: int, *, issuer_region: str | None, currency: str, base_date: date,
) -> PaymentFeeRows:
    """PayPal の手数料の行（design-e.md §3-1）。テナント独自の行が先・期間内・新しい effective_from。"""
    receiving_type = "receiving_domestic" if issuer_region == "domestic" else "receiving_international"
    required_fx = currency.upper() != "JPY"

    async def _one(fee_type: str) -> PaymentFeeRow | None:
        result = await db.execute(
            text("""
                SELECT id, fee_type, rate_pct, fixed_amount, threshold
                FROM public.payment_fee_settings
                WHERE service = 'paypal' AND fee_type = :ft AND currency = 'JPY'
                  AND (tenant_id = :tid OR tenant_id IS NULL)
                  AND effective_from <= :d
                  AND COALESCE(effective_to, DATE '9999-12-31') >= :d
                ORDER BY (tenant_id IS NULL), effective_from DESC, id DESC
                LIMIT 1
            """),
            {"ft": fee_type, "tid": int(tenant_id), "d": base_date},
        )
        r = result.mappings().first()
        if r is None:
            return None
        return PaymentFeeRow(
            id=r["id"], fee_type=r["fee_type"], rate_pct=Decimal(r["rate_pct"]),
            fixed_amount=Decimal(r["fixed_amount"]),
            threshold=Decimal(r["threshold"]) if r["threshold"] is not None else None,
        )

    return PaymentFeeRows(
        receiving=await _one(receiving_type),
        fx=await _one("fx_receiving") if required_fx else None,
        required_fx=required_fx,
    )
```
`ORDER BY (tenant_id IS NULL)` は false（自社の行）が先に並ぶ。

（8）load_totals_inputs の引数と中身:
```
async def load_totals_inputs(
    db: AsyncSession, tenant_id: int, *, destination: str | None, base_date: date,
    issuer_region: str | None = None, currency: str | None = None, payment_method_type: str | None = None,
) -> TotalsInputs:
```
`return TotalsInputs(` の `fx=await load_latest_fx(db),` の次に:
```
        payment_fee_rows=(
            await load_payment_fee_rows(db, tenant_id, issuer_region=issuer_region, currency=currency or "JPY", base_date=base_date)
            if payment_method_type == "paypal" else None
        ),
```

（9）to_db_params の返す dict の最後に:
```
        "payment_fee_charged": result.payment_fee if result.payment_fee_snapshot is not None else None,
        "payment_fee_snapshot": json.dumps(result.payment_fee_snapshot) if result.payment_fee_snapshot is not None else None,
```
（paypal 以外は列を NULL のままにする。「手数料を足していない」と「0円を足した」を分けるため。）

### 2-7. backend/app/schemas/invoice.py

- InvoicePreviewRequest（:94-100）の `shipping: ShippingInput | None = None` の次に `payment_method_type: Literal["bank", "wise", "paypal"] | None = None`。
- InvoicePreviewResponse（:103-114）の `total_amount: Decimal | None` の次に `payment_fee: Decimal = Decimal("0")`。
- InvoiceResponse の `payment_fee: Decimal | None = None`（:247 付近）の次に `    # 便E: お客様への合計に足した支払い手数料（入金時の実額は payment_fee）` と `    payment_fee_charged: Decimal | None = None`。

### 2-8. backend/app/routers/invoices.py

（1）_INVOICE_COLUMNS（:142）の最後の行 `payment_method_id, tax_rate_percent, shipping_carrier, shipping_service, shipping_snapshot` を `payment_method_id, tax_rate_percent, shipping_carrier, shipping_service, shipping_snapshot,` にし、次の行に `    payment_fee_charged, payment_fee_snapshot` を足す。

（2）_INSERT_INVOICE_SQL（:173-192）: 列の並びの `shipping_carrier, shipping_service, shipping_snapshot` を `shipping_carrier, shipping_service, shipping_snapshot,` にして次に `        payment_fee_charged, payment_fee_snapshot`。値の並びの `:shipping_carrier, :shipping_service, :shipping_snapshot` も同じく `, :payment_fee_charged, :payment_fee_snapshot` を足す（列と値の数をそろえる）。

（3）_RECOMPUTE_SET_SQL（:195-200）の最後の行 `tax_rate_percent = :tax_rate_percent, shipping_snapshot = :shipping_snapshot` を `tax_rate_percent = :tax_rate_percent, shipping_snapshot = :shipping_snapshot,` にし、次に `    payment_fee_charged = :payment_fee_charged, payment_fee_snapshot = :payment_fee_snapshot`。

（4）_compute（:246-253）:
```
async def _compute(db, tenant_id, *, currency, items, shipping, ship_to, bill_to, base_date=None,
                   payment_method_type=None, issuer_region=None):
    destination = invoice_totals.destination_country(ship_to, bill_to)
    inputs = await invoice_totals.load_totals_inputs(
        db, tenant_id, destination=destination, base_date=base_date or invoice_totals.today_jst(),
        issuer_region=issuer_region, currency=currency, payment_method_type=payment_method_type,
    )
    return invoice_totals.compute_totals(
        currency=currency, items=items, shipping=shipping, destination=destination, inputs=inputs,
        payment_method_type=payment_method_type,
    )
```

（5）preview（:423-450）: `bill_to = ...` の次に `issuer_region = decide_issuer_region(bill_to)`。load_totals_inputs の呼び出しに `issuer_region=issuer_region, currency=data.currency.upper(), payment_method_type=data.payment_method_type,` を足す。compute_totals に `payment_method_type=data.payment_method_type,` を足す。compute の後に、PayPal なのに地域が決まらないときは手数料の理由で止める（design-e §3-1）:
```
    if data.payment_method_type == "paypal" and issuer_region is None:
        if invoice_totals.REASON_PAYMENT_FEE not in result.uncomputed:
            result.uncomputed.append(invoice_totals.REASON_PAYMENT_FEE)
        result.total_amount = None
        result.payment_fee = Decimal("0")
```
（地域 None のとき load_payment_fee_rows は international の行を選ぶので、計算させてから消す。応答の uncomputed の並びは REASON_ORDER の最後なので append でよい。）
InvoicePreviewResponse(...) に `payment_fee=result.payment_fee,` を足す。decide_issuer_region は create が使っているのと同じ import（既に invoices.py にある）。

（6）create（:676-700）: `payment_text = None` から `except PaymentMethodInvalid: ... detail="payment_method")` までの塊（支払方法の確かめ）を、`currency = data.currency.upper()` の次・`totals = await _compute(` の前へ動かす（中身は変えない）。_compute の呼び出しに `payment_method_type=data.payment_method_ref.method_type if data.payment_method_ref is not None else None, issuer_region=issuer_region,` を足す。

（7）PATCH（:722-768）: `if not update_data:` の検査の後、`set_clauses = ...` の前に、支払方法が来たときだけ作り直す:
```
    recompute: dict = {}
    if "payment_method_ref" in sent:
        items = await _get_invoice_items(db, invoice_id)
        totals = await _compute(
            db, tenant_id, currency=old_row["currency"],
            items=[invoice_totals.TotalsItem(quantity=i["quantity"], unit_price=Decimal(i["unit_price"])) for i in items],
            shipping=_shipping_from_stored(old_row),
            ship_to=_load_snapshot(old_row["ship_to_snapshot"]), bill_to=_load_snapshot(old_row["bill_to_snapshot"]),
            payment_method_type=ref.method_type, issuer_region=old_row["issuer_region"] or "overseas",
        )
        _raise_if_blocked(totals)
        recompute = invoice_totals.to_db_params(totals)
        recompute.pop("shipping_carrier")
        recompute.pop("shipping_service")
```
UPDATE を1文にする:
```
    set_clauses = ", ".join(f"{k} = :{k}" for k in update_data)
    if recompute:
        set_clauses = f"{set_clauses}, {_RECOMPUTE_SET_SQL}"
    params = {**update_data, **recompute, "id": invoice_id}

    result = await db.execute(
        text(f"UPDATE invoices SET {set_clauses}, updated_at = NOW() WHERE id = :id AND status = 'draft' RETURNING {_INVOICE_COLUMNS}"),
        params,
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invoice_not_draft")
```
記録（record_audit_log）の new_data は、今の update_data に、作り直したときだけ `"total_amount": str(totals.total_amount)` と `"payment_fee_charged": str(totals.payment_fee)` を足した dict（Decimal をそのまま入れない）。`update_data["id"] = invoice_id` の行は消す（params に入れたので）。

（8）issue（:796-801）の _compute に `payment_method_type=old["payment_method"], issuer_region=old["issuer_region"] or "overseas",` を足す。

（9）paypal-link（:943 付近）: `if inv_row["total_amount"] is None or ...` の検査の次に:
```
    # 便E: PayPal の手数料を足した請求書だけ PayPal で請求する（ADR-101 :173・design-e §3-5）
    if inv_row["payment_method"] != "paypal":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="payment_method")
```
:1002 の `COALESCE(payment_method, 'paypal')` は変えない。

（10）PDF の invoice_data 2か所（download_invoice_pdf の :1155-1180 と _render_paypal_copy_pdf の :1201-1224）の `"duty_amount": ...,` の次に:
```
        "payment_fee_charged": float(row["payment_fee_charged"]) if row["payment_fee_charged"] is not None else None,
```

### 2-9. backend/app/services/invoice_renderer.py

- データ型の `duty_amount: Optional[float] = None`（:149）の次に `payment_fee_charged: Optional[float] = None`。
- 合計の前の行（:387-401）の Duty の塊の次（`# 合計（太字）` の前）に:
```
    # 支払い手数料（便E。0 か None なら出さない）
    if data.payment_fee_charged:
        c.drawRightString(165 * mm, y, "Payment fee:")
        c.drawRightString(190 * mm, y, _fmt_money(data.payment_fee_charged, data.currency))
        y -= 5 * mm
```
- 組み立て（:572 `duty_amount=invoice_data.get("duty_amount"),`）の次に `payment_fee_charged=invoice_data.get("payment_fee_charged"),`。見積の組み立て（:645 付近）は触らない。

### 2-10. backend/tests/conftest.py

（1）SQLite の invoices の表（:1220 `shipping_snapshot TEXT`）を `shipping_snapshot TEXT,` にして次に `                payment_fee_charged NUMERIC(15, 2),` と `                payment_fee_snapshot TEXT`。

（2）stub_invoice_totals（:2356-）: state に `"payment_fee_rows": None,`。`_fake` を `async def _fake(db, tenant_id, *, destination, base_date, **kw):` にし、calls に `**kw` も入れ（`{"destination": destination, "base_date": base_date, **kw}`）、TotalsInputs に `payment_fee_rows=state["payment_fee_rows"] if kw.get("payment_method_type") == "paypal" else None,` を渡す。

（3）stub_invoice_totals の次に fixture を足す:
```
@pytest.fixture
def fake_payment_ref(monkeypatch):
    """SQLite の試験用: 振込先の表を読まずに支払方法の確かめを通す（design-e §3-5）。"""
    from app.services import invoice_payment_methods as ipm

    async def _fake(db, tenant_id, *, method_type, method_id, region, currency):
        return method_type, method_id

    monkeypatch.setattr(ipm, "resolve_payment_ref", _fake)
```

（4）試験で使う手数料の行を作る関数を fixture の次に足す（同じ conftest に置き、試験から import する）:
```
def paypal_fee_rows(*, international: bool = True, with_fx: bool = False):
    from decimal import Decimal

    from app.services import invoice_totals as it

    receiving = it.PaymentFeeRow(
        id=2 if international else 1,
        fee_type="receiving_international" if international else "receiving_domestic",
        rate_pct=Decimal("4.1000") if international else Decimal("3.6000"),
        fixed_amount=Decimal("40.00"), threshold=None,
    )
    fx = it.PaymentFeeRow(id=3, fee_type="fx_receiving", rate_pct=Decimal("4.0000"), fixed_amount=Decimal("0"), threshold=None) if with_fx else None
    return it.PaymentFeeRows(receiving=receiving, fx=fx, required_fx=with_fx)
```

### 2-11. 試験

（1）backend/tests/test_invoice_totals.py（純粋な計算）に足す:
- K1 `test_e1_paypal_domestic_jpy`: currency JPY・小計 100000（1 個×100000）・送料 none・届け先 US（税 0）・`payment_fee_rows=paypal_fee_rows(international=False)`・payment_method_type "paypal" → payment_fee 3640・total 103640・snapshot の rate_pct "3.6000"。
- K2 `test_e2_paypal_international_usd_with_fx`: USD・小計 1000.00・届け先 US・`paypal_fee_rows(with_fx=True)` → payment_fee Decimal("81.26")・total Decimal("1081.26")。
- K3 `test_e3_bank_wise_none_have_no_fee`: bank・wise・None の3つで payment_fee 0・snapshot None・total は手数料なしの値。
- K5 `test_e4_paypal_blocks_without_rows`: payment_fee_rows None・receiving None・threshold あり・USD で fx None の4通り → uncomputed の最後が "payment_fee"・total None・first_block が (409, "payment_fee")。
- `test_e5_reason_order_ends_with_payment_fee`: REASON_ORDER[-1] == "payment_fee"。
- to_db_params: paypal なら payment_fee_charged と payment_fee_snapshot（JSON の文字）、bank なら両方 None。
（`paypal_fee_rows` は `from tests.conftest import paypal_fee_rows` で読む。読めなければ同じ関数を試験ファイルの中に置く。）

（2）backend/tests/test_invoice_totals_pg.py（K4）: `_PUBLIC_MIGRATIONS`（:42-48）に `"20261002_160000_create_payment_fee_settings.sql"` を足す。試験 `test_load_payment_fee_rows_prefers_tenant_and_latest` を足す: 試験の最初に public.tenants に 953 の行が無ければ入れ（列は既存の試験 test_tenant_budget_settings_rls.py:92 の入れ方にならう）、payment_fee_settings に次の行を入れる → 呼んで確かめる → 試験の最後に入れた行と tenants の行（入れた場合だけ）を戻す:
- 共用・receiving_international・4.1・effective_from 2025-01-01
- 共用・receiving_international・5.0・effective_from 2026-12-01（基準日 2026-11-15 より後なので使わない）
- 共用・receiving_international・3.9・effective_from 2024-01-01・effective_to 2024-12-31（期間外）
- 953・receiving_international・3.0・effective_from 2026-01-01（自社の行が勝つ）
- 共用・fx_receiving・4.0・effective_from 2025-01-01
確かめ: `load_payment_fee_rows(db, 953, issuer_region="overseas", currency="USD", base_date=date(2026, 11, 15))` の receiving.rate_pct == 3.0・fx.rate_pct == 4.0・required_fx True。次に 953 の行を戻してから呼ぶと receiving.rate_pct == 4.1。currency "JPY" なら fx None・required_fx False。
戻すときの文は既存の PG 試験の後片付けの書き方にならう（この指示書には消す文の字面を書かない。検査 L23 のため）。

（3）backend/tests/test_tenant_duty_rules_pg.py（K9）: 既存の雛形の試験（:74 test_tenant_ddl_has_duty_tables_and_invoice_columns）と同じ型で、雛形から作ったスキーマの invoices に payment_fee_charged（numeric）と payment_fee_snapshot（jsonb）がある試験を足す。移行を2回流しても失敗せず2列があることも、同じファイルの移行の試験の型で足す（新しい移行の名前の定数を1つ足す）。

（4）backend/tests/test_paypal_invoicing.py（K7b・K7c）:
- pytestmark を `pytest.mark.usefixtures("stub_invoice_totals", "fake_payment_ref")` にする。
- `_issued_invoice` に引数 `stub` を足し（呼び出し側は `stub_invoice_totals` を渡す）、作る前に `stub.set(payment_fee_rows=paypal_fee_rows())`、作る依頼に `"payment_method_ref": {"method_type": "paypal", "id": None}` を足す。今の呼び出し 6 か所（:217・:226・:260・:268・:348・:371）を合わせて直す（試験の引数に stub_invoice_totals を足す）。
- 新しい試験 `test_issue_paypal_link_409_when_not_paypal`: bank（`{"method_type": "bank", "id": None}`）で作って発行 → paypal-link が 409・detail "payment_method"・PayPal へ送る関数（create_and_send_invoice）が呼ばれていない。
- 既存の test_issue_paypal_link_success で、PayPal へ送る amount が手数料込みの total_amount（請求書の応答の total_amount と同じ）であることを確かめる行を足す。
- K7c: 請求書の PDF（GET /invoices/{id}/pdf）の文字に "Payment fee" が在ること（既存の test_render_invoice_pdf_with_paypal_copy の PDF の読み方にならう）・手数料なし（bank）の請求書の PDF には無いこと。写しの PDF も同じ invoice_data を通るので、_render_paypal_copy_pdf に payment_fee_charged が渡ることを、直接 render_invoice_pdf に `payment_fee_charged: 41.0` を入れた invoice_data で "Payment fee" が出る試験で確かめる。

（5）backend/tests/test_invoices_create_flow.py（K5・K6・K7）: fixture `fake_payment_ref` を使う試験を足す。
- preview に `payment_method_type: "paypal"` と stub の行 → 応答の payment_fee > 0・total_amount に足されている。bank → payment_fee "0"。PayPal で行なし（stub の既定）→ uncomputed に "payment_fee"。
- create（PayPal・行あり）→ 201・詳細の応答の payment_fee_charged と total_amount が手数料込み。create（PayPal・行なし）→ 409 "payment_fee"・請求書の数が増えない。
- PATCH: bank で作った下書きに `payment_method_ref: {"method_type": "paypal", "id": None}` → total_amount が手数料の分だけ上がり payment_fee_charged が入る。続けて bank に戻す → payment_fee_charged が null・total_amount が元の値。行なしで PayPal に変える → 409 "payment_fee"・支払方法も合計も前のまま。
- issue: PayPal の下書きを発行 → 200・payment_fee_charged が入ったまま。
（作り方は今のファイルの `_body(company_id, contact_id, **kw)` と `_create_company_contact` を使う。）

（6）backend/tests/test_api_error_reason_sync.py: :50-72 の一覧の `"invoice_not_draft",` の次に `"payment_fee",`。

### 2-12. frontend

（1）frontend/src/lib/invoiceDraftContext.ts:
- InvoicePreview（:70-82）の `total_amount: string | null;` の次に `payment_fee: string;`。
- InvoicePreviewRequest（:93 付近）の `shipping: ShippingChoice | null;` の次に `payment_method_type: PaymentMethodType | null;`。

（2）frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:113-121 の previewRequest の `shipping,` の次に:
```
          payment_method_type: paymentRefFromKey(paymentChoices, paymentValue)?.method_type ?? null,
```
（paymentChoices・paymentValue は :184 で既に使っている同じ値。）

（3）frontend/src/pages/invoice-create/InvoicePaymentTotalsSection.tsx:200-207 の TotalsBox の rows の tax の行の次に、手数料が 0 より大きいときだけ1行（配列の中で条件つきに足す）:
```
            ...(preview !== null && Number(preview.payment_fee) > 0
              ? [{ key: "paymentFee", label: t("invoiceForm.paymentFee"), value: <span data-testid="invoice-total-payment-fee">{money(preview.payment_fee)}</span> }]
              : []),
```

（4）frontend/src/lib/apiErrorReason.ts の API_ERROR_REASON_KEYS の `invoice_not_draft: "apiError.invoiceNotDraft",` の次に `payment_fee: "apiError.paymentFee",`。apiErrorReason.test.ts:76 の `toBe(26)` を `toBe(27)`。

（5）frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx:
- InvoiceDetail（:56-）の `amount_usd: number | null;` の次に `payment_fee_charged: number | null;`。
- tfoot の税の行（`{t("quotes.tax")}` の行）の次に:
```
          {invoice.payment_fee_charged != null && invoice.payment_fee_charged > 0 && <tr><td colSpan={6} style={{ textAlign: "right" }}>{t("invoices.paymentFeeCharged")}</td><td>{fmt(invoice.payment_fee_charged)}</td></tr>}
```
- PayPal リンクのボタン（:216 付近 `!invoice.paypal_approval_url &&`）の条件に `invoice.payment_method === "paypal" &&` を足す（`hasPermission("invoices.update") &&` の次）。

（6）frontend/src/pages/invoice-create/InvoiceCreatePage.test.tsx（K8）: 今の試算の受け答えの作り方にならい、PayPal を選んだとき応答の payment_fee "3640" で `invoice-total-payment-fee` が出て「3,640」相当の表示があり、銀行（payment_fee "0"）では `invoice-total-payment-fee` が無い試験を足す。試算の依頼に payment_method_type が入ることも確かめる。今の試験の試算の応答（作り物）に `payment_fee: "0"` が無くて型で落ちるなら足す。

### 2-13. frontend/src/locales/ja.json・en.json（同じキー）

- invoiceForm（`"notComputed"` のある塊）に `"paymentFee"`: ja「支払い手数料」/ en「Payment fee」。
- invoices（`"usdConvert"` のある塊）に `"paymentFeeCharged"`: ja「支払い手数料」/ en「Payment fee」。
- apiError（`"invoiceNotDraft"` のある塊。最後の項目なので前の行にカンマを足す）に `"paymentFee"`: ja「支払い手数料の設定が見つからないため、合計を計算できません。設定の画面で PayPal の手数料を確かめてください。」/ en「No payment fee setting was found, so the total cannot be calculated. Check the PayPal fee in settings.」

## 3. 手順

手順1 作業場所（枝は origin に在る。new-worktree.sh で作ってから origin の枝を取り込む）
    cd /home/user/salesanchor && git fetch origin main release/invoice-portfolio-e-payment-fee
    cd /home/user/salesanchor && git branch --list release/invoice-portfolio-e-payment-fee
    cd /home/user/salesanchor && bash scripts/new-worktree.sh release/invoice-portfolio-e-payment-fee --claude
    cd /home/user/salesanchor && git worktree list
    cd ~/worktrees/salesanchor/release-invoice-portfolio-e-payment-fee && git merge --no-edit origin/release/invoice-portfolio-e-payment-fee; echo "rel exit=$?"
    cd ~/worktrees/salesanchor/release-invoice-portfolio-e-payment-fee && git merge-base --is-ancestor origin/release/invoice-portfolio-e-payment-fee HEAD; echo "is-ancestor exit=$?"
    cd ~/worktrees/salesanchor/release-invoice-portfolio-e-payment-fee && git rev-parse HEAD
  new-worktree.sh が「既に在る」で止まったら、作業場所の名前を報告して BLOCKED: で停止する。rel exit か is-ancestor exit が 0 でなければ停止する。

手順2 実装前点検（§0-3）
    cd ~/worktrees/salesanchor/release-invoice-portfolio-e-payment-fee && git hash-object backend/app/services/invoice_totals.py backend/app/routers/invoices.py backend/app/schemas/invoice.py backend/app/services/invoice_renderer.py backend/app/services/tenant.py backend/tests/conftest.py backend/tests/test_paypal_invoicing.py backend/tests/test_invoice_totals.py backend/tests/test_invoice_totals_pg.py
    cd ~/worktrees/salesanchor/release-invoice-portfolio-e-payment-fee && git hash-object backend/tests/ops/test_ai_cloud_views.py backend/tests/rls_bootstrap.py backend/tests/test_tenant_loop_migration_guard.py backend/tests/test_api_error_reason_sync.py migrations/20261024_100300_create_ai_cloud_views.sql docs/handoff/cloud-case-ai/stage1-column-class.tsv scripts/migration-guard/reference-allowlist.tsv scripts/run_all_migrations.sh
    cd ~/worktrees/salesanchor/release-invoice-portfolio-e-payment-fee && git hash-object frontend/src/pages/invoice-create/InvoiceCreatePage.tsx frontend/src/pages/invoice-create/InvoicePaymentTotalsSection.tsx frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx frontend/src/lib/apiErrorReason.ts frontend/src/lib/apiErrorReason.test.ts frontend/src/lib/invoiceDraftContext.ts frontend/src/locales/ja.json frontend/src/locales/en.json frontend/src/pages/invoice-create/InvoiceCreatePage.test.tsx
    cd ~/worktrees/salesanchor/release-invoice-portfolio-e-payment-fee && ls migrations | grep -c 20261121_100000
    cd ~/worktrees/salesanchor/release-invoice-portfolio-e-payment-fee && ls backend/tests/test_tenant_duty_rules_pg.py
  出力の先頭12字を §0-3 の表と照らす。1つでも違う・P2 が 0 でない・P3 が無ければ実装せず BLOCKED: で停止する。

手順3 §2 のとおりに編集する（既存ファイルは Edit ツール、新しい移行は Write ツール）。§2 の変更前の文が見つからない・2か所以上ある場合は、推測で選ばず BLOCKED: で停止する。

手順4 Python の検査と試験
    cd ~/worktrees/salesanchor/release-invoice-portfolio-e-payment-fee/backend && python3.12 -m venv /tmp/venv312 && /tmp/venv312/bin/pip install -q -r requirements.txt -r requirements-dev.txt
    cd ~/worktrees/salesanchor/release-invoice-portfolio-e-payment-fee/backend && /tmp/venv312/bin/ruff check app tests
    cd ~/worktrees/salesanchor/release-invoice-portfolio-e-payment-fee/backend && /tmp/venv312/bin/python -m pytest -q -p no:cacheprovider tests/test_invoice_totals.py tests/test_invoices_create_flow.py tests/test_paypal_invoicing.py tests/test_api_error_reason_sync.py tests/test_tenant_loop_migration_guard.py 2>&1 | tail -30
    cd ~/worktrees/salesanchor/release-invoice-portfolio-e-payment-fee/backend && /tmp/venv312/bin/python -m pytest -q -p no:cacheprovider tests/ -k "invoice" 2>&1 | tail -30
  PG の試験（_pg.py・ops/）は手元に PG が無ければ skip になる。skip の数をそのまま報告し、CI で流れる。落ちた試験があれば直してから先へ進む。§2 の形を変えないと直らないときは BLOCKED: で停止する。

手順5 分類の指紋（§2-5）
    cd ~/worktrees/salesanchor/release-invoice-portfolio-e-payment-fee && sha256sum migrations/20261024_100300_create_ai_cloud_views.sql
  出た値を reference-allowlist.tsv の 20261024_100300 の行の2列目に Edit で入れる。
    cd ~/worktrees/salesanchor/release-invoice-portfolio-e-payment-fee && grep -c 'invoice-create-portfolio card-E' scripts/migration-guard/reference-allowlist.tsv
    cd ~/worktrees/salesanchor/release-invoice-portfolio-e-payment-fee && grep -c 'payment_fee_snapshot' migrations/20261024_100300_create_ai_cloud_views.sql docs/handoff/cloud-case-ai/stage1-column-class.tsv
    cd ~/worktrees/salesanchor/release-invoice-portfolio-e-payment-fee && ls scripts/migration-guard/
  migration-guard に手元で流せる検査（例 check.py・check.sh）があれば repo モードで流し、出力の最後 20 行を報告に貼る。無ければ「手元の検査なし・CI で確かめる」と書く。

手順6 移行ファイルの字面の確かめ
    cd ~/worktrees/salesanchor/release-invoice-portfolio-e-payment-fee && grep -n -i -E 'ADD COLUMN IF NOT EXISTS|COMMENT ON COLUMN|RAISE NOTICE' migrations/20261121_100000_add_invoice_payment_fee_charged.sql
    cd ~/worktrees/salesanchor/release-invoice-portfolio-e-payment-fee && grep -c -i -E 'insert into|update public|drop ' migrations/20261121_100000_add_invoice_payment_fee_charged.sql
  2つ目の数が 0 でなければ停止する。

手順7 API の型の書き出し
    cd ~/worktrees/salesanchor/release-invoice-portfolio-e-payment-fee/backend && ENVIRONMENT=test /tmp/venv312/bin/python -m tools.export_openapi ../frontend/api-contract/openapi.json
    cd ~/worktrees/salesanchor/release-invoice-portfolio-e-payment-fee && git status --short | head -60
  CI（.github/workflows/api-contract-check.yml:38）と同じ書き出し。失敗したら出力の最後 20 行を貼って BLOCKED: で停止する。

手順8 画面の検査と試験
    cd ~/worktrees/salesanchor/release-invoice-portfolio-e-payment-fee/frontend && npm ci --no-audit --no-fund 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-portfolio-e-payment-fee/frontend && npm run check:all 2>&1 | tail -40
    cd ~/worktrees/salesanchor/release-invoice-portfolio-e-payment-fee/frontend && npx vitest run src/lib/apiErrorReason.test.ts src/lib/invoiceDraftContext.test.ts src/pages/invoice-create src/pages/invoice-detail 2>&1 | tail -30
  落ちたら直す。§2 の形を変えないと直らないときは BLOCKED: で停止する。

手順9 差分の確かめ
    cd ~/worktrees/salesanchor/release-invoice-portfolio-e-payment-fee && git status --short | head -60
    cd ~/worktrees/salesanchor/release-invoice-portfolio-e-payment-fee && git diff --stat | tail -40
  §1 に無いファイル（生成物を除く）が変わっていたら、何かを報告に書いて BLOCKED: で停止する。

手順10 記録と送る
    cd ~/worktrees/salesanchor/release-invoice-portfolio-e-payment-fee && git add migrations/20261121_100000_add_invoice_payment_fee_charged.sql migrations/20261024_100300_create_ai_cloud_views.sql scripts/run_all_migrations.sh scripts/migration-guard/reference-allowlist.tsv docs/handoff/cloud-case-ai/stage1-column-class.tsv
    cd ~/worktrees/salesanchor/release-invoice-portfolio-e-payment-fee && git add backend/app frontend/src backend/tests
    cd ~/worktrees/salesanchor/release-invoice-portfolio-e-payment-fee && git status --short | head -60
    cd ~/worktrees/salesanchor/release-invoice-portfolio-e-payment-fee && git add frontend/api-contract/openapi.json
    cd ~/worktrees/salesanchor/release-invoice-portfolio-e-payment-fee && git -c user.name=shingo-cc -c user.email=shingo-cc@users.noreply.github.com commit -m "feat(invoice): add PayPal payment fee to invoice totals (card-E)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
    cd ~/worktrees/salesanchor/release-invoice-portfolio-e-payment-fee && git log --oneline -3
    cd ~/worktrees/salesanchor/release-invoice-portfolio-e-payment-fee && git push -u origin release/invoice-portfolio-e-payment-fee
    cd ~/worktrees/salesanchor/release-invoice-portfolio-e-payment-fee && git log --oneline origin/release/invoice-portfolio-e-payment-fee -1
  commit が見張りに止められたら、言い換えて回避せず、止めた文をそのまま報告して BLOCKED: で停止する。push が拒まれたら force で押さず停止する。

## 4. 想定される分かれ道

- K2 の数が 81.26 にならない → 式を変えずに、出た値と途中の値（率・固定額の換算）を報告して BLOCKED: で停止。
- 移行の前例に to_regclass の確かめが無い → §2-1 の1行を足す（足したことを報告）。
- test_tenant_loop_migration_guard.py が別の一覧を求める → 試験の言うとおりに1行足し、場所を報告。
- SQLite の試験で invoices の列が足りないと落ちる → §2-10（1）の足し忘れ。conftest を直す。
- 既存の試験が支払方法なしの請求書で PayPal リンクを出していて 409 で落ちる → §2-11（4）のとおり PayPal の請求書に直す。他のファイルで同じことが起きたら、そのファイル名を報告して同じ直し方をする。
- test_ai_cloud_views.py の件数が 1165 にならない（PG がある CI で）→ 手元では分からない。CI の結果を Opus が読む。
- 画面の check:all が i18n の検査で落ちる → ja/en のキーの綴りと置き場所を §2-13 と照らす。
- 上のどれにも当たらない失敗 → 推測で直さず、出力の最後 40 行を貼って BLOCKED: で停止。

## 5. 報告の形

1 行目: `RECEIVED invoice-portfolio-E HEAD=` に手順1 の rev-parse の40桁を続ける
続けて手順ごとに: 実行したコマンドと出力の最後の行（試験は passed/failed/skipped の数の行）。手順2 の指紋は全部貼る。手順10 の git log の2つの出力を貼る。
最後の行: `DONE` か `BLOCKED:`（後ろに理由）か `NEEDS_DECISION:`（後ろに聞きたいこと） のどれか1つ。

## 6. 委任の定型

- この指示書に無いことはしない。PR は作らない（Opus が作る）。マージしない。本番に触らない。
- 消す命令・force push・枝の削除はしない。
- 見張り（hook）に止められたら言い換えて回避しない。止めた文をそのまま報告して停止する。
- 迷ったら推測で進めず停止して NEEDS_DECISION: で聞く。

END OF CARD
