# card: 便C 請求書の額をサーバーで計算し、振込先と税率を PDF に出す（invoice-create-portfolio）

状態: カード発行（Opus、2026-11-15）。PO の設計承認と実装承認は 2026-11-13「1,（２）決済手数料を合計に足す仕組みは、今回は作りません。別の作業に回します。→次便で」と、同じ日の常設の指示「…確立したなら進める。…PRマージ、デプロイまで完走させてくれ。」（design.md 第9版・審査 APPROVE）。2026-11-15 に PO が「1」で「請求書の画面の作業を先に進め、最後にまとめて見てもらう」を選んだ。
設計: docs/handoff/invoice-create-portfolio/design.md §3-2・§3-3（計算 1〜6）・§3-4（規則・道の表・為替・送料）・§3-5・§3-7・§3-8（請求書との関係）・§4 の便 C・§6・§8 の K3・K4・K6・K7・K9・K12・K13・K15・K16・K18・K22・K23（サーバー側）・K24・K25（便 C 側）。事実の行番号は docs/handoff/invoice-create-portfolio/recon-cd.md（基準 2ccb6a94e。b80c23725 まで backend と frontend/src に差分なし）。
担当: クラウドの Sonnet。触ってよいのは下の「1. 触るファイル」だけ。本番・GitHub の secret・DB には触らない。PR は作らない（Opus が作る）。
基準: origin/main `b80c23725` で行番号を測った（2026-11-15 の `8a148e732` まで backend と frontend/src に差分なし。表と列の名前は 8a148e732 の tenant.py:1267-1330・:1440-1482 と migrations で照合済み）。行番号がずれていたら「変更前」の文で場所を探す（同じ文が 2 か所あれば BLOCKED: で停止。ただし ` invoice_id = inv_result.scalar_one()` は invoices.py に 2 か所あり、§2-5 で示した関数（create_invoice_from_quote・create_invoice）の中のものをそれぞれ使う。これは止めない）。
危険便か: いいえ（`migrations/`・`.github/workflows/`・本番の `scripts/` を触らない。列と表は便A・便V で作り済み）。マージ前に Opus の審査役の APPROVE と CI 全通過を必須にする（担当の作業ではない）。
同じ枝: この便 C と便 D（docs/handoff/invoice-create-portfolio/card-D.md）は同じ枝 `release/invoice-create-portfolio-bin-cd` に、C→D の順に別のコミットで入れ、1つの PR で出す（design.md §4。C だけ出すと今の作成画面が 422 になるため）。便 C のコミットの時点では frontend の型の点検（tsc）が落ちてよい。便 D のコミットの後に全部が通ること。

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

## Opus の決めごと（このカードで固めたこと。根拠つき）

- D1 計算の場所は新しい backend/app/services/invoice_totals.py の `compute_totals`（純粋な関数。DB を読まない）だけ。DB を読むのは同じファイルの `load_totals_inputs`。試算・作る・見積から作る・発行の 4 つの道がこの 2 つを呼ぶ（design.md §3-4 冒頭）。
- D2 端数: 消費税、関税の中身の1つずつ、換算した送料、換算した下限・上限を、請求書の通貨の最小単位（JPY は 1、それ以外は 0.01）へ切り捨てる（ROUND_FLOOR。design.md §7 の1）。為替の列 amount_jpy・amount_usd は今と同じ `round(x, 2)`（invoices.py:142・:147。design.md §3-4「表示用の換算額」）。
- D3 基準日は日本時間の今日（`datetime.now(ZoneInfo("Asia/Tokyo")).date()`）。発行の道も同じ関数で発行の日を取る（design.md §3-4）。
- D4 為替は public.app_fx_rate_history の通貨ごとの最新 1 行だけ（`DISTINCT ON (currency) ... ORDER BY currency, fetched_at DESC`）。JPY は率 1 として扱い、表を読まない。2 つの外貨の間は円を通す。backend/app/routers/invoices.py から `get_fx_rate` の import と 3 か所の呼び出し（:253・:356・:1044）を消す（K13・K24）。backend/app/services/fx_rate.py と backend/app/tasks/fx_rate_updater.py は触らない（表に値を入れる係が使う）。
- D5 「未計算」の理由は 4 つで、この順に並べる: `shipping_required`・`fx_rate`・`tax_rate`・`duty_needs_carrier`。試算は 200 で理由の一覧を返す（409 にしない）。作る・見積から作る・発行は、一覧の先頭の理由で止める: `shipping_required` は 422、ほかの 3 つは 409。detail は理由の文字だけ（apiErrorReason.ts が文字で引くため。api.ts:129-131）。
- D6 消費税は届け先の国が JP のときだけ。届け先の国＝発送先の写しの country、無ければ請求先の写しの country（design.md §3-3 の1）。税の基準は 小計＋送料（換算後）。税率の行が無い JP 宛は `tax_rate`。外国宛は tax_amount 0・tax_rate_percent NULL。
- D7 関税: 会社の条件（public.tenant_settings.duty_incoterms。行が無ければ `DAP` とみなす。schemas/tenant_policy.py:20 の既定と同じ）が DDP のときだけ。行の選び方と `duty_needs_carrier` は design.md §3-3 の3・6 のとおり。送料の会社の比べ方は `strip().lower()`、空は None。関税の行が無い・DAP・DDU のとき duty_amount は NULL。
- D8 送料の受け方（design.md §3-4 の送料の規則）: 作る道の `shipping` は `{"mode": "calculate", "carrier", "service_type", "fee", "currency"}` か `{"mode": "none"}`。無いと 422 `shipping_required`。見積から作る道は見積の shipping_fee が 0 より大きいとき mode `quote`（元の額＝見積の送料・元の通貨＝見積の通貨・会社＝quotes.shipping_carrier）、それ以外は `none`。
- D9 支払方法の正本は振込先の表（今の版・is_active・地域・詳細の行がある・Wise は通貨が同じ）と public.tenant_paypal_config（PayPal）。新しい backend/app/services/invoice_payment_methods.py の 1 か所でだけ読む。作る道と PATCH は `payment_method_ref` `{"method_type": "bank"|"wise"|"paypal", "id": int|null}` を受け、候補に無ければ 422 `payment_method`。保存は payment_method に method_type の文字、payment_method_id に版の id（PayPal は NULL）（design.md §3-4 の表の下）。
- D10 発行は `SELECT ... FOR UPDATE` で請求書を読み、下書きでなければ今と同じ 400「draft状態の請求書のみ発行できます」。保存した明細・送料の写し・届け先の写し・通貨から発行の日で計算し直し、税・関税・合計・為替の列・写しを上書きしてから issued にする。payment_method_id があり今の候補（保存した issuer_region・通貨で引く）に無ければ 409 `payment_method`（design.md §3-4 の発行の行・§3-8）。shipping_snapshot が NULL の古い下書きは、保存した shipping_fee が 0 より大きければ mode `quote`（元の額＝shipping_fee・元の通貨＝請求書の通貨・会社＝shipping_carrier）、それ以外は `none` とみなす。
- D11 PATCH は `payment_method_ref`・`due_date`・`notes` だけを受ける（extra="forbid"）。下書きでないときは今の門の 400 がそのまま止める。`payment_method_ref` に null を送ったら 422 `payment_method`（支払方法を外す道は作らない）。候補は請求書に保存した issuer_region（NULL は overseas）と currency で引く。
- D12 draft-context（GET /api/v1/invoices/draft-context）は書かない道。`company_id` か `invoice_id` のどちらかが要る（どちらも無いと 422 `draft_context_target`）。両方あって会社が違うと 422 `invoice_company_mismatch`。会社・担当者・請求書が無いと 404 `not_found:company`・`not_found:contact`・`not_found:invoice`。担当者は任意の `contact_id` で、会社に属さないと今の作る道と同じ 400「指定された担当者は指定会社に所属していません」。請求先の国が無く地域が決まらないときは issuer_region を null、支払方法を空の一覧にする（作る道は今と同じ 422 bill_to_country で止める）。この道は GET /invoices/{invoice_id} より前に宣言する（design.md §3-4 の表）。
- D13 試算（POST /api/v1/invoices/preview）は書かないが POST なので backend/app/realtime/topics.py の NO_SIGNAL_ROUTES に今の請求書の道と同じ `_PENDING` で足す（design.md §3-4 の topics の項）。draft-context は GET なので載せない。
- D14 詳細の道（GET /invoices/{id}）は `payment_method_display_name`・`payment_method_type` を足して返す（版の一覧の行から。口座番号は返さない）。一覧の道と PATCH・発行の応答（InvoiceResponse）は新しい 5 列（payment_method_id・tax_rate_percent・shipping_carrier・shipping_service・shipping_snapshot）を返す。
- D15 PDF: Tax の行に率を添える（`Tax (10%):`。tax_rate_percent が NULL なら今のまま `Tax:`）。合計の下（為替の脚注の前）に支払方法の区切りを描く（design.md §3-7）。PayPal の写しの PDF（`_render_paypal_copy_pdf`）と見積の PDF は変えない。
- D16 新しい理由コード 6 つ（`duty_needs_carrier`・`duty_rule_overlap`・`shipping_required`・`fx_rate`・`tax_rate`・`payment_method`）を frontend/src/lib/apiErrorReason.ts の一覧（18→24）・ja.json と en.json の apiError・backend/tests/test_api_error_reason_sync.py の固定の一覧に足す（design.md §4 の便 C の行）。`draft_context_target`・`invoice_company_mismatch` は画面が送らない形の誤り（画面は必ず片方だけを送る）なので足さない。
- D17 SQLite の試験は DB の外の表（public.tax_rates など）を持たないので、`load_totals_inputs` を差し替える fixture `stub_invoice_totals` を conftest.py に足し、請求書を作る試験のファイルでは `pytestmark` で使う。DB の読み方そのもの・draft-context・支払方法・PDF・新しいテナント（K22）・GET /fx-rate は実 PostgreSQL の試験 backend/tests/test_invoice_totals_pg.py で確かめる（CI だけで動く）。
- D18 PG の試験のテナント番号は 953（2026-11-16 に origin/main 2cc593393 で `git grep -w 953 -- backend migrations scripts` が 0 件。最初に選んだ 976 は PG の試験2本が使っていたため替えた。P7 で担当がもう一度数える）。
- D19 API の形が変わるので frontend/api-contract/openapi.json を作り直して入れる（.github/workflows/api-contract-check.yml が照合する）。

## 0. カード発行前チェック（docs/ai-agents/design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は担当が作らない（Opus が作る） | ○（冒頭・§5） |
| 3 | 報告の宛先と生出力の扱い | ○（§5。完了報告の本文に各手順の出力を tail の範囲でそのまま貼る） |
| 4 | 1便1目的 | ○（請求書の額をサーバーで計算する道と PDF。画面は便 D） |
| 5 | 既存ブランチへの追記ではない | ○（このカードが main に入った後、Opus が origin/main から新しい実装の枝 `release/invoice-create-portfolio-bin-cd` を作る） |
| 6 | 書式は実例で示した | ○（§2 に新規の中心の全文と、既存の変更前・変更後） |
| 7 | 合格基準を出力まで縛った | ○（§3 の各手順の期待） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（手順9 の `git status --short` と `git diff --stat`） |
| 9 | 出力量に上限のないコマンドを使わない | ○（すべて tail か wc） |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○（§4・§5・末尾） |
| 11 | 期待値は実測から | ○（P の数と変更前の文は b80c23725 の写しで実測。試験の本数は §2 の一覧から数えた） |
| 12 | 停止は本番影響のあるものに限る | ○（§4） |
| 13 | 委任文の定型4点 | ○（§6） |

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・報告に無い出力を成功と扱わない（commit は git log で確かめる） | ○（§3） |
| guards/03-file.md | 編集は Edit ツール。プレースホルダを残さない | ○（§2） |
| guards/10-executor.md | 散文で頼まない。手順はコマンドで書く | ○（§3） |

## 受領確認（最初の報告の 1 行目に書く）

`RECEIVED invoice-create-portfolio-C HEAD=`（続けて `git rev-parse HEAD` の 40 桁）。2 行目に「本報告はカード 便C 請求書の額をサーバーで計算し、振込先と税率を PDF に出す の実行結果である」と書く。

## 0-3. 実装前点検（手順2 で流す。外れたら実装せず BLOCKED: で停止）

- P1 このカードと card-D.md が枝に在る。
- P2 §1 の新規 6 ファイルがどれも無い。
- P3 列は便A で入り済み: `grep -c "payment_method_id INTEGER" backend/app/services/tenant.py` が 1 以上、`grep -c "shipping_snapshot JSONB" backend/app/services/tenant.py` が 1 以上、`grep -c "tax_rate_percent NUMERIC(5, 2)" backend/app/services/tenant.py` が 1 以上。
- P4 版の列は便V で入り済み: `grep -c "superseded_by_id" backend/app/services/tenant.py` が 1 以上。
- P5 まだ計算の道が無い: `grep -c "draft-context\|invoices/preview\|invoice_totals" backend/app/routers/invoices.py backend/app/realtime/topics.py` がどちらも 0。
- P6 §2 の「変更前」の目印の行が、それぞれのファイルに 1 回ずつある（手順2 の `grep -c -x -F` がどれも 1）。
- P7 `git grep -c -w 953 -- backend migrations scripts | wc -l` が 0（試験のテナント番号 953 は未使用。D18）。
- P8 `get_fx_rate` を呼ぶのは router では invoices.py の 3 か所だけ: `grep -c "get_fx_rate(" backend/app/routers/invoices.py` が 3。

## 1. 触るファイル

1. backend/app/services/invoice_totals.py（新規）
2. backend/app/services/invoice_payment_methods.py（新規）
3. backend/tests/test_invoice_totals.py（新規）
4. backend/tests/test_invoices_create_flow.py（新規）
5. backend/tests/test_invoice_totals_pg.py（新規）
6. backend/tests/test_invoice_pdf_payment.py（新規）
7. backend/app/schemas/invoice.py
8. backend/app/routers/invoices.py
9. backend/app/services/issuer.py
10. backend/app/services/invoice_renderer.py
11. backend/app/realtime/topics.py
12. backend/tests/conftest.py
13. backend/tests/test_invoices.py
14. backend/tests/test_issuer.py
15. backend/tests/test_paypal_invoicing.py
16. backend/tests/test_company_stats.py
17. backend/tests/test_products.py
18. backend/tests/test_api_error_reason_sync.py
19. frontend/src/lib/apiErrorReason.ts
20. frontend/src/lib/apiErrorReason.test.ts
21. frontend/src/locales/ja.json
22. frontend/src/locales/en.json
23. frontend/api-contract/openapi.json（手順7 の書き出しで作り直す。手で書かない）

触らない: 上に無いファイル全部。特に migrations/・backend/app/services/tenant.py・backend/app/services/fx_rate.py・backend/app/tasks/・.github/workflows/ の全部・frontend/src/pages/・frontend/src/components/（画面は便 D）。

## 2. 変更

### 2-1. backend/app/services/invoice_totals.py（新規。全文）

```python
"""請求書の額の計算（invoice-create-portfolio 便C・design.md §3-3・§3-4）。

ここが唯一の計算の場所。試算・作る・見積から作る・発行の道がこれを呼ぶ。
- compute_totals: 純粋な関数（DB を読まない）。
- load_totals_inputs: 計算に要る行を DB から読む（税率・関税の条件・関税の行・為替）。
端数は請求書の通貨の最小単位へ切り捨て（design.md §7 の1）。為替の列は今と同じ round(x, 2)。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import ROUND_FLOOR, Decimal
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import tenant_table_ref

JST = ZoneInfo("Asia/Tokyo")

# 「未計算」の理由（この順に並べる。作る道は先頭で止める。design.md §3-4）
REASON_SHIPPING = "shipping_required"
REASON_FX = "fx_rate"
REASON_TAX = "tax_rate"
REASON_DUTY_CARRIER = "duty_needs_carrier"
REASON_ORDER = (REASON_SHIPPING, REASON_FX, REASON_TAX, REASON_DUTY_CARRIER)

SHIPPING_MODES = ("calculate", "quote", "none")
DUTY_BASES = ("subtotal", "subtotal_shipping", "subtotal_shipping_prior")


def today_jst() -> date:
    return datetime.now(JST).date()


def normalize_carrier(value: str | None) -> str | None:
    """送料の会社の比べ方: 前後の空白を除き小文字。空は None（design.md §3-3 の3）。"""
    if value is None:
        return None
    s = value.strip().lower()
    return s or None


def minor_unit(currency: str) -> Decimal:
    return Decimal("1") if currency == "JPY" else Decimal("0.01")


def floor_minor(value: Decimal, currency: str) -> Decimal:
    return value.quantize(minor_unit(currency), rounding=ROUND_FLOOR)


def _iso_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


@dataclass(frozen=True)
class TotalsItem:
    quantity: int
    unit_price: Decimal


@dataclass(frozen=True)
class ShippingChoice:
    mode: str  # calculate / quote / none
    carrier: str | None = None
    service_type: str | None = None
    fee: Decimal | None = None
    currency: str | None = None


@dataclass(frozen=True)
class FxRow:
    currency: str
    rate_jpy: Decimal
    fetched_at: datetime


@dataclass(frozen=True)
class TaxRow:
    rate_percent: Decimal
    effective_from: date


@dataclass(frozen=True)
class DutyComponent:
    sort_order: int
    label: str
    base: str
    rate_pct: Decimal
    min_amount: Decimal | None
    max_amount: Decimal | None
    amount_currency: str | None


@dataclass(frozen=True)
class DutyRule:
    id: int
    carrier: str | None
    label: str
    source_url: str
    effective_from: date
    effective_to: date | None
    components: tuple[DutyComponent, ...]


@dataclass(frozen=True)
class TotalsInputs:
    base_date: date
    incoterms: str
    tax: TaxRow | None
    duty_rules: tuple[DutyRule, ...]
    fx: dict[str, FxRow]


@dataclass
class TotalsResult:
    currency: str
    subtotal: Decimal
    shipping_fee: Decimal | None
    tax_amount: Decimal | None
    tax_rate_percent: Decimal | None
    duty_amount: Decimal | None
    duty_label: str | None
    duty_components: list[dict]
    total_amount: Decimal | None
    uncomputed: list[str]
    shipping_carrier: str | None
    shipping_service: str | None
    shipping_snapshot: dict | None
    duty_policy_snapshot: dict
    fx_rate_snapshot: dict | None
    exchange_rate_jpy: Decimal | None
    exchange_rate_usd: Decimal | None
    amount_jpy: Decimal | None
    amount_usd: Decimal | None
    _reasons: set[str] = field(default_factory=set, repr=False)


class _FxMissing(Exception):
    pass


def _fx_record(row: FxRow) -> dict:
    return {"currency": row.currency, "rate_jpy": str(row.rate_jpy), "fetched_at": _iso_utc(row.fetched_at)}


def _rate(fx: dict[str, FxRow], currency: str) -> Decimal:
    if currency == "JPY":
        return Decimal("1")
    row = fx.get(currency)
    if row is None:
        raise _FxMissing(currency)
    return row.rate_jpy


def _convert(amount: Decimal, src: str, dst: str, fx: dict[str, FxRow], used: list[dict]) -> Decimal:
    """src の額を dst の通貨へ（円を通す）。dst の最小単位へ切り捨て。使った為替の行を used に足す。"""
    if src == dst:
        return floor_minor(amount, dst)
    jpy = amount * _rate(fx, src)
    out = jpy / _rate(fx, dst)
    for cur in (src, dst):
        if cur != "JPY":
            rec = _fx_record(fx[cur])
            if rec not in used:
                used.append(rec)
    return floor_minor(out, dst)


def destination_country(ship_to: dict | None, bill_to: dict | None) -> str | None:
    """届け先の国＝発送先の写しの国、無ければ請求先の写しの国（design.md §3-3 の1）。"""
    for snap in (ship_to, bill_to):
        if snap and snap.get("country"):
            return str(snap["country"]).upper()
    return None


def destination_postal_code(ship_to: dict | None, bill_to: dict | None) -> str | None:
    """届け先の郵便番号（国と同じ写しから取る。design.md §3-4 の FedEx の項）。"""
    for snap in (ship_to, bill_to):
        if snap and snap.get("country"):
            return snap.get("postal_code") or None
    return None


def compute_totals(
    *,
    currency: str,
    items: list[TotalsItem],
    shipping: ShippingChoice | None,
    destination: str | None,
    inputs: TotalsInputs,
) -> TotalsResult:
    currency = currency.upper()
    reasons: set[str] = set()
    subtotal = sum((Decimal(it.quantity) * it.unit_price for it in items), Decimal("0"))

    # ── 送料 ────────────────────────────────────────────────
    shipping_fee: Decimal | None
    shipping_snapshot: dict | None
    ship_fx: list[dict] = []
    if shipping is None:
        reasons.add(REASON_SHIPPING)
        shipping_fee = None
        shipping_snapshot = None
        carrier_raw = None
        service = None
    elif shipping.mode == "none":
        shipping_fee = Decimal("0")
        carrier_raw = None
        service = None
        shipping_snapshot = {
            "source": "none", "original_fee": None, "original_currency": None,
            "carrier": None, "service_type": None, "fx": [], "no_charge": True,
        }
    else:
        carrier_raw = shipping.carrier
        service = shipping.service_type
        src_cur = (shipping.currency or currency).upper()
        fee = shipping.fee if shipping.fee is not None else Decimal("0")
        try:
            shipping_fee = _convert(fee, src_cur, currency, inputs.fx, ship_fx)
        except _FxMissing:
            reasons.add(REASON_FX)
            shipping_fee = None
        shipping_snapshot = {
            "source": shipping.mode, "original_fee": str(fee), "original_currency": src_cur,
            "carrier": carrier_raw, "service_type": service, "fx": ship_fx, "no_charge": False,
        }

    # ── 消費税（JP 宛だけ）──────────────────────────────────
    tax_amount: Decimal | None
    tax_rate_percent: Decimal | None
    if destination == "JP":
        if inputs.tax is None:
            reasons.add(REASON_TAX)
            tax_amount = None
            tax_rate_percent = None
        else:
            tax_rate_percent = inputs.tax.rate_percent
            if shipping_fee is None:
                tax_amount = None
            else:
                tax_amount = floor_minor((subtotal + shipping_fee) * tax_rate_percent / Decimal("100"), currency)
    else:
        tax_amount = Decimal("0")
        tax_rate_percent = None

    # ── 関税（DDP だけ）────────────────────────────────────
    duty_amount: Decimal | None = None
    duty_label: str | None = None
    duty_components: list[dict] = []
    duty_fx: list[dict] = []
    rule_snap: dict | None = None
    if inputs.incoterms == "DDP" and inputs.duty_rules:
        carrier = normalize_carrier(carrier_raw)
        matched = [r for r in inputs.duty_rules if carrier is not None and r.carrier == carrier]
        generic = [r for r in inputs.duty_rules if r.carrier is None]
        rule = matched[0] if matched else (generic[0] if generic else None)
        if rule is None:
            reasons.add(REASON_DUTY_CARRIER)
        else:
            duty_label = rule.label
            rule_snap = {
                "id": rule.id, "carrier": rule.carrier, "label": rule.label, "source_url": rule.source_url,
                "effective_from": rule.effective_from.isoformat(),
                "effective_to": rule.effective_to.isoformat() if rule.effective_to else None,
            }
            if shipping_fee is not None:
                prior = Decimal("0")
                total_duty = Decimal("0")
                try:
                    for comp in sorted(rule.components, key=lambda c: c.sort_order):
                        if comp.base == "subtotal":
                            base = subtotal
                        elif comp.base == "subtotal_shipping":
                            base = subtotal + shipping_fee
                        else:
                            base = subtotal + shipping_fee + prior
                        raw = base * comp.rate_pct / Decimal("100")
                        comp_cur = (comp.amount_currency or currency).upper()
                        lo = _convert(comp.min_amount, comp_cur, currency, inputs.fx, duty_fx) if comp.min_amount is not None else None
                        hi = _convert(comp.max_amount, comp_cur, currency, inputs.fx, duty_fx) if comp.max_amount is not None else None
                        if lo is not None and raw < lo:
                            raw = lo
                        if hi is not None and raw > hi:
                            raw = hi
                        amount = floor_minor(raw, currency)
                        prior += amount
                        total_duty += amount
                        duty_components.append({
                            "label": comp.label, "base": comp.base, "rate_pct": str(comp.rate_pct),
                            "min_amount": str(comp.min_amount) if comp.min_amount is not None else None,
                            "max_amount": str(comp.max_amount) if comp.max_amount is not None else None,
                            "amount_currency": comp.amount_currency, "amount": str(amount),
                        })
                    duty_amount = total_duty
                except _FxMissing:
                    reasons.add(REASON_FX)
                    duty_components = []
                    duty_amount = None

    duty_policy_snapshot = {
        "incoterms": inputs.incoterms, "base_date": inputs.base_date.isoformat(),
        "rule": rule_snap, "components": duty_components, "fx": duty_fx,
    }

    # ── 合計 ─────────────────────────────────────────────
    total_amount: Decimal | None = None
    blocked = bool(reasons) or shipping_fee is None or tax_amount is None
    if inputs.incoterms == "DDP" and rule_snap is not None and duty_amount is None:
        blocked = True
    if not blocked:
        total_amount = subtotal + shipping_fee + tax_amount + (duty_amount or Decimal("0"))

    # ── 請求書の通貨の為替（fx_rate_snapshot・exchange_rate_jpy）──────
    fx_rate_snapshot: dict | None = None
    exchange_rate_jpy: Decimal | None = None
    if currency != "JPY":
        row = inputs.fx.get(currency)
        if row is None:
            reasons.add(REASON_FX)
            total_amount = None
        else:
            exchange_rate_jpy = row.rate_jpy
            fx_rate_snapshot = {"currency": currency, "rate": float(row.rate_jpy), "fetched_at": _iso_utc(row.fetched_at)}

    usd_row = inputs.fx.get("USD")
    exchange_rate_usd = usd_row.rate_jpy if (currency != "USD" and usd_row is not None) else None
    amount_jpy: Decimal | None = None
    amount_usd: Decimal | None = None
    if total_amount is not None:
        amount_jpy = total_amount if currency == "JPY" else round(total_amount * exchange_rate_jpy, 2)
        if currency == "USD":
            amount_usd = total_amount
        elif usd_row is not None and usd_row.rate_jpy > 0:
            amount_usd = round(amount_jpy / usd_row.rate_jpy, 2)

    return TotalsResult(
        currency=currency,
        subtotal=subtotal,
        shipping_fee=shipping_fee,
        tax_amount=tax_amount,
        tax_rate_percent=tax_rate_percent,
        duty_amount=duty_amount,
        duty_label=duty_label,
        duty_components=duty_components,
        total_amount=total_amount,
        uncomputed=[r for r in REASON_ORDER if r in reasons],
        shipping_carrier=carrier_raw.strip() if carrier_raw and carrier_raw.strip() else None,
        shipping_service=service,
        shipping_snapshot=shipping_snapshot,
        duty_policy_snapshot=duty_policy_snapshot,
        fx_rate_snapshot=fx_rate_snapshot,
        exchange_rate_jpy=exchange_rate_jpy,
        exchange_rate_usd=exchange_rate_usd,
        amount_jpy=amount_jpy,
        amount_usd=amount_usd,
    )


# ── DB を読む ─────────────────────────────────────────────────


async def load_latest_fx(db: AsyncSession) -> dict[str, FxRow]:
    result = await db.execute(text("""
        SELECT DISTINCT ON (currency) currency, rate_jpy, fetched_at
        FROM public.app_fx_rate_history
        ORDER BY currency, fetched_at DESC
    """))
    return {
        r["currency"]: FxRow(currency=r["currency"], rate_jpy=Decimal(r["rate_jpy"]), fetched_at=r["fetched_at"])
        for r in result.mappings().all()
    }


async def load_tax_row(db: AsyncSession, base_date: date) -> TaxRow | None:
    result = await db.execute(
        text("""
            SELECT rate_percent, effective_from FROM public.tax_rates
            WHERE effective_from <= :d ORDER BY effective_from DESC LIMIT 1
        """),
        {"d": base_date},
    )
    row = result.mappings().first()
    return None if row is None else TaxRow(rate_percent=Decimal(row["rate_percent"]), effective_from=row["effective_from"])


async def load_incoterms(db: AsyncSession, tenant_id: int) -> str:
    result = await db.execute(
        text("SELECT duty_incoterms FROM public.tenant_settings WHERE tenant_id = :tid"),
        {"tid": int(tenant_id)},
    )
    row = result.first()
    return (row[0] if row and row[0] else "DAP").upper()


async def load_duty_rules(db: AsyncSession, tenant_id: int, country: str, base_date: date) -> tuple[DutyRule, ...]:
    rules_t = tenant_table_ref(db, tenant_id, "tenant_duty_rules")
    comps_t = tenant_table_ref(db, tenant_id, "tenant_duty_rule_components")
    result = await db.execute(
        text(f"""
            SELECT id, carrier, label, source_url, effective_from, effective_to
            FROM {rules_t}
            WHERE destination_country_code = :country
              AND is_active = TRUE
              AND effective_from <= :d
              AND COALESCE(effective_to, DATE '9999-12-31') >= :d
            ORDER BY id
        """),
        {"country": country, "d": base_date},
    )
    rules: list[DutyRule] = []
    for r in result.mappings().all():
        comp_rows = await db.execute(
            text(f"""
                SELECT sort_order, label, base, rate_pct, min_amount, max_amount, amount_currency
                FROM {comps_t} WHERE rule_id = :rid ORDER BY sort_order, id
            """),
            {"rid": r["id"]},
        )
        comps = tuple(
            DutyComponent(
                sort_order=c["sort_order"], label=c["label"], base=c["base"],
                rate_pct=Decimal(c["rate_pct"]),
                min_amount=Decimal(c["min_amount"]) if c["min_amount"] is not None else None,
                max_amount=Decimal(c["max_amount"]) if c["max_amount"] is not None else None,
                amount_currency=(c["amount_currency"].strip() if c["amount_currency"] else None),
            )
            for c in comp_rows.mappings().all()
        )
        rules.append(DutyRule(
            id=r["id"], carrier=r["carrier"], label=r["label"], source_url=r["source_url"],
            effective_from=r["effective_from"], effective_to=r["effective_to"], components=comps,
        ))
    return tuple(rules)


async def load_totals_inputs(
    db: AsyncSession, tenant_id: int, *, destination: str | None, base_date: date,
) -> TotalsInputs:
    incoterms = await load_incoterms(db, tenant_id)
    duty_rules: tuple[DutyRule, ...] = ()
    if incoterms == "DDP" and destination:
        duty_rules = await load_duty_rules(db, tenant_id, destination, base_date)
    return TotalsInputs(
        base_date=base_date,
        incoterms=incoterms,
        tax=await load_tax_row(db, base_date),
        duty_rules=duty_rules,
        fx=await load_latest_fx(db),
    )


def first_block(result: TotalsResult) -> tuple[int, str] | None:
    """作る道の止め方（D5）。止めないときは None。"""
    if not result.uncomputed:
        return None
    reason = result.uncomputed[0]
    return (422 if reason == REASON_SHIPPING else 409), reason


def to_db_params(result: TotalsResult) -> dict[str, Any]:
    """INSERT・UPDATE に渡す値（写しは JSON の文字）。"""
    import json

    return {
        "subtotal": result.subtotal,
        "shipping": result.shipping_fee,
        "tax": result.tax_amount,
        "tax_rate_percent": result.tax_rate_percent,
        "duty_amount": result.duty_amount,
        "total": result.total_amount,
        "rate_jpy": result.exchange_rate_jpy,
        "rate_usd": result.exchange_rate_usd,
        "amt_jpy": result.amount_jpy,
        "amt_usd": result.amount_usd,
        "shipping_carrier": result.shipping_carrier,
        "shipping_service": result.shipping_service,
        "shipping_snapshot": json.dumps(result.shipping_snapshot) if result.shipping_snapshot is not None else None,
        "duty_policy_snapshot": json.dumps(result.duty_policy_snapshot),
        "fx_rate": json.dumps(result.fx_rate_snapshot) if result.fx_rate_snapshot is not None else None,
    }
```

注: `compute_totals` の「合計」の段の `blocked` は、関税の行を選んだのに額が出ない（送料が未計算・為替が無い）ときも止める。関税の行が無い・DAP・DDU のときは duty_amount が NULL のまま合計に 0 として足す（design.md §3-4「関税が NULL のときは0として足す」）。

### 2-2. backend/app/services/invoice_payment_methods.py（新規。全文）

```python
"""請求書の支払方法の候補と版（invoice-create-portfolio 便C・design.md §3-2・§3-4・§3-8・ADR-1079）。

正本: 振込先の表（tenant_invoice_payment_methods と詳細2表）と public.tenant_paypal_config。
- 候補＝今の版（superseded_by_id と deleted_at が NULL）・is_active・発行元の地域が同じ・詳細の行がある。
- Wise は wise_currency が請求書の通貨と同じものだけを受ける（候補の一覧は全部を返し、画面が絞る）。
- 口座番号は load_payment_version（PDF だけが呼ぶ）でだけ読む。
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import tenant_table_ref


class PaymentMethodInvalid(Exception):
    """候補に無い支払方法（422 payment_method）。"""


async def _has_paypal(db: AsyncSession, tenant_id: int) -> bool:
    result = await db.execute(
        text("SELECT 1 FROM public.tenant_paypal_config WHERE tenant_id = :tid"),
        {"tid": int(tenant_id)},
    )
    return result.first() is not None


async def list_payment_choices(db: AsyncSession, tenant_id: int, region: str | None) -> list[dict]:
    """draft-context に返す候補（id・method_type・display_name・wise_currency）。region が None なら空。"""
    if region is None:
        return []
    methods = tenant_table_ref(db, tenant_id, "tenant_invoice_payment_methods")
    bank = tenant_table_ref(db, tenant_id, "tenant_invoice_payment_bank")
    wise = tenant_table_ref(db, tenant_id, "tenant_invoice_payment_wise")
    result = await db.execute(
        text(f"""
            SELECT m.id, m.method_type, m.display_name, w.wise_currency
            FROM {methods} m
            LEFT JOIN {bank} b ON b.payment_method_id = m.id
            LEFT JOIN {wise} w ON w.payment_method_id = m.id
            WHERE m.region = :region
              AND m.is_active = TRUE
              AND m.superseded_by_id IS NULL
              AND m.deleted_at IS NULL
              AND ((m.method_type = 'bank' AND b.payment_method_id IS NOT NULL)
                OR (m.method_type = 'wise' AND w.payment_method_id IS NOT NULL))
            ORDER BY m.sort_order, m.id
        """),
        {"region": region},
    )
    choices = [
        {
            "id": r["id"],
            "method_type": r["method_type"],
            "display_name": r["display_name"],
            "wise_currency": (r["wise_currency"].strip() if r["wise_currency"] else None) if r["method_type"] == "wise" else None,
        }
        for r in result.mappings().all()
    ]
    if await _has_paypal(db, tenant_id):
        choices.append({"id": None, "method_type": "paypal", "display_name": None, "wise_currency": None})
    return choices


def _accepts(choice: dict, method_type: str, method_id: int | None, currency: str) -> bool:
    if choice["method_type"] != method_type or choice["id"] != method_id:
        return False
    if method_type == "wise":
        return (choice["wise_currency"] or "").upper() == currency.upper()
    return True


async def resolve_payment_ref(
    db: AsyncSession, tenant_id: int, *, method_type: str, method_id: int | None, region: str | None, currency: str,
) -> tuple[str, int | None]:
    """受けた支払方法を確かめ、(payment_method の文字, payment_method_id) を返す。候補に無ければ PaymentMethodInvalid。"""
    choices = await list_payment_choices(db, tenant_id, region)
    if not any(_accepts(c, method_type, method_id, currency) for c in choices):
        raise PaymentMethodInvalid()
    return method_type, method_id


async def is_current_choice(
    db: AsyncSession, tenant_id: int, *, payment_method_id: int, region: str, currency: str,
) -> bool:
    """発行の前の確かめ（design.md §3-4 の発行の行）。payment_method_id の版が今も候補にあるか。"""
    choices = await list_payment_choices(db, tenant_id, region)
    return any(
        c["id"] == payment_method_id and _accepts(c, c["method_type"], payment_method_id, currency)
        for c in choices
    )


async def load_payment_label(db: AsyncSession, tenant_id: int, payment_method_id: int | None) -> dict | None:
    """詳細の道に返す表示（display_name・method_type）。古い版も読む。口座番号は読まない。"""
    if payment_method_id is None:
        return None
    methods = tenant_table_ref(db, tenant_id, "tenant_invoice_payment_methods")
    result = await db.execute(
        text(f"SELECT method_type, display_name FROM {methods} WHERE id = :id"),
        {"id": payment_method_id},
    )
    row = result.mappings().first()
    return None if row is None else {"method_type": row["method_type"], "display_name": row["display_name"]}


async def load_payment_version(db: AsyncSession, tenant_id: int, payment_method_id: int) -> dict | None:
    """PDF に描く版の中身（古い版・消した版でもその版を読む。design.md §3-7）。無ければ None。"""
    methods = tenant_table_ref(db, tenant_id, "tenant_invoice_payment_methods")
    bank = tenant_table_ref(db, tenant_id, "tenant_invoice_payment_bank")
    wise = tenant_table_ref(db, tenant_id, "tenant_invoice_payment_wise")
    result = await db.execute(
        text(f"""
            SELECT m.method_type, m.display_name,
                   b.account_holder AS bank_account_holder, b.bank_name AS bank_bank_name,
                   b.bank_branch, b.bank_account_type, b.bank_account_number, b.swift_code,
                   w.account_holder AS wise_account_holder, w.wise_email, w.iban, w.swift_bic,
                   w.bank_name AS wise_bank_name
            FROM {methods} m
            LEFT JOIN {bank} b ON b.payment_method_id = m.id
            LEFT JOIN {wise} w ON w.payment_method_id = m.id
            WHERE m.id = :id
        """),
        {"id": payment_method_id},
    )
    row = result.mappings().first()
    if row is None:
        return None
    if row["method_type"] == "bank" and row["bank_account_number"] is not None:
        return {
            "method_type": "bank", "display_name": row["display_name"],
            "bank_name": row["bank_bank_name"], "bank_branch": row["bank_branch"],
            "account_type": row["bank_account_type"], "account_number": row["bank_account_number"],
            "account_holder": row["bank_account_holder"], "swift_code": row["swift_code"],
        }
    if row["method_type"] == "wise" and row["wise_account_holder"] is not None:
        return {
            "method_type": "wise", "display_name": row["display_name"],
            "account_holder": row["wise_account_holder"], "wise_email": row["wise_email"],
            "bank_name": row["wise_bank_name"], "swift_bic": row["swift_bic"], "iban": row["iban"],
        }
    return None
```

### 2-3. backend/app/services/issuer.py（足す）

変更前（目印。この行の直前に足す）:
```python
async def get_issuer(db: AsyncSession, tenant_id: int, region: str) -> dict:
```
変更後（目印の行の前に次の関数と空行 2 つを足す。目印の行と get_issuer の中身は変えない）:
```python
async def get_issuer_country_code(db: AsyncSession, tenant_id: int, region: str | None) -> str | None:
    """発送元の国＝その地域の発行元の行の country_code（design.md §3-2 の送料）。行が無ければ None。暗黙に "JP" を使わない（ADR-125 D5）。"""
    if region not in ISSUER_REGIONS:
        return None
    profiles = tenant_table_ref(db, tenant_id, "tenant_issuer_profiles")
    result = await db.execute(
        text(f"SELECT country_code FROM {profiles} WHERE region = :region ORDER BY id LIMIT 1"),
        {"region": region},
    )
    row = result.first()
    return (row[0] or None) if row else None


```

### 2-4. backend/app/schemas/invoice.py

(1) 変更前:
```python
from pydantic import BaseModel, Field, field_validator
```
変更後:
```python
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
```

(2) 変更前（InvoiceCreate の全体。`class InvoiceCreate(BaseModel):` から `    items: list[InvoiceItemInput] = Field(min_length=1)` まで）を、次で置き換える:
```python
class PaymentMethodRef(BaseModel):
    """支払方法の選び方（design.md §3-4）。bank・wise は版の id、paypal は id なし。"""
    model_config = ConfigDict(extra="forbid")
    method_type: Literal["bank", "wise", "paypal"]
    id: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def _id_matches_type(self):
        if self.method_type == "paypal" and self.id is not None:
            raise ValueError("paypal_takes_no_id")
        if self.method_type != "paypal" and self.id is None:
            raise ValueError("id_required")
        return self


class ShippingInput(BaseModel):
    """送料の選び方（design.md §3-4 の送料の規則）。calculate=/shipping/calculate の結果の1つ、none=送料を請求しない。"""
    model_config = ConfigDict(extra="forbid")
    mode: Literal["calculate", "none"]
    carrier: str | None = Field(default=None, max_length=50)
    service_type: str | None = Field(default=None, max_length=100)
    fee: Decimal | None = Field(default=None, ge=0, max_digits=15, decimal_places=2)
    currency: str | None = Field(default=None, min_length=3, max_length=3)

    @model_validator(mode="after")
    def _fields_match_mode(self):
        if self.mode == "calculate":
            if not (self.carrier and self.carrier.strip()) or self.fee is None or not self.currency:
                raise ValueError("calculate_needs_carrier_fee_currency")
        elif any(v is not None for v in (self.carrier, self.service_type, self.fee, self.currency)):
            raise ValueError("none_takes_no_fields")
        return self


class InvoiceCreate(BaseModel):
    """請求書登録リクエスト。額（送料・消費税・為替）は受けず、サーバーが計算する（invoice-create-portfolio 便C）。"""
    model_config = ConfigDict(extra="forbid")
    company_id: int = Field(ge=1, description="会社ID")
    contact_id: int = Field(ge=1, description="担当者ID")
    currency: str = Field(default="JPY", min_length=3, max_length=3)
    shipping: ShippingInput | None = None
    payment_method_ref: PaymentMethodRef | None = None
    due_date: date | None = None
    notes: str | None = Field(default=None, max_length=5000)
    items: list[InvoiceItemInput] = Field(min_length=1)


class InvoicePreviewItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    quantity: int = Field(ge=1)
    unit_price: Decimal = Field(ge=0, max_digits=15, decimal_places=2)


class InvoicePreviewRequest(BaseModel):
    """試算（書かない）。作る道と同じ材料で額だけを返す。"""
    model_config = ConfigDict(extra="forbid")
    company_id: int = Field(ge=1)
    currency: str = Field(min_length=3, max_length=3)
    items: list[InvoicePreviewItem] = Field(default_factory=list)
    shipping: ShippingInput | None = None


class InvoicePreviewResponse(BaseModel):
    currency: str
    subtotal: Decimal
    shipping_fee: Decimal | None
    tax_amount: Decimal | None
    tax_rate_percent: Decimal | None
    duty_amount: Decimal | None
    duty_label: str | None
    duty_components: list[dict]
    total_amount: Decimal | None
    uncomputed: list[str]
    incoterms: str


class DraftContextAddress(BaseModel):
    company_name: str | None = None
    billing_display_name: str | None = None
    label: str | None = None
    postal_code: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    phone: str | None = None


class DraftContextFx(BaseModel):
    currency: str
    rate: float
    fetched_at: str | None


class DraftContextPayment(BaseModel):
    id: int | None
    method_type: str
    display_name: str | None
    wise_currency: str | None


class DraftContextResponse(BaseModel):
    company_id: int
    ship_to: DraftContextAddress | None
    bill_to: DraftContextAddress | None
    contact_name: str | None
    contact_email: str | None
    issuer_region: str | None
    origin_country_code: str | None
    destination_country_code: str | None
    destination_postal_code: str | None
    currencies: list[str]
    fx_rates: list[DraftContextFx]
    default_currency: str | None
    currency: str | None
    payment_methods: list[DraftContextPayment]
    tax_rate_percent: Decimal | None
    incoterms: str
```

(3) 変更前（InvoiceUpdate の全体）:
```python
class InvoiceUpdate(BaseModel):
    payment_method: str | None = Field(default=None, max_length=50)
    due_date: date | None = None
    exchange_rate_jpy: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=4)
    exchange_rate_usd: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=4)
    notes: str | None = Field(default=None, max_length=5000)
```
変更後:
```python
class InvoiceUpdate(BaseModel):
    """下書きの直し（design.md §3-4 の PATCH）。為替と支払方法の文字は受けない。"""
    model_config = ConfigDict(extra="forbid")
    payment_method_ref: PaymentMethodRef | None = None
    due_date: date | None = None
    notes: str | None = Field(default=None, max_length=5000)
```

(4) InvoiceResponse の最後の欄の後に足す。変更前:
```python
    issuer_region: str | None = None

    model_config = {"from_attributes": True}

    # ADR-1061 便2-2c2a（D13）: 写しの列は本番（PostgreSQL の JSONB）では dict で返るが、
```
変更後:
```python
    issuer_region: str | None = None
    # invoice-create-portfolio 便A・便C: 案内した振込先の版・使った税率・送料の会社とサービス・送料の写し
    payment_method_id: int | None = None
    tax_rate_percent: Decimal | None = None
    shipping_carrier: str | None = None
    shipping_service: str | None = None
    shipping_snapshot: dict | None = None

    model_config = {"from_attributes": True}

    # ADR-1061 便2-2c2a（D13）: 写しの列は本番（PostgreSQL の JSONB）では dict で返るが、
```

(5) 変更前:
```python
        "ship_to_snapshot", "bill_to_snapshot", "duty_policy_snapshot", "fx_rate_snapshot", mode="before"
```
変更後:
```python
        "ship_to_snapshot", "bill_to_snapshot", "duty_policy_snapshot", "fx_rate_snapshot", "shipping_snapshot",
        mode="before",
```

(6) 変更前:
```python
class InvoiceDetailResponse(InvoiceResponse):
    items: list[InvoiceItemResponse] = []
```
変更後:
```python
class InvoiceDetailResponse(InvoiceResponse):
    items: list[InvoiceItemResponse] = []
    # 便C: payment_method_id の版の表示（口座番号は返さない。design.md §3-4）
    payment_method_display_name: str | None = None
    payment_method_type: str | None = None
```

### 2-5. backend/app/routers/invoices.py

(1) import。変更前:
```python
from app.services.fx_rate import get_fx_rate
```
変更後（この行を消し、次の 2 行を `from app.services.invoice_renderer import ...` の行の前に置く）:
```python
from app.services import invoice_payment_methods, invoice_totals
from app.services.invoice_payment_methods import PaymentMethodInvalid
```
`from app.schemas.invoice import (` の中に `DraftContextResponse`・`InvoicePreviewRequest`・`InvoicePreviewResponse` を足す（並びはアルファベット順）。`from app.services.issuer import decide_issuer_region, get_issuer` を `from app.services.issuer import decide_issuer_region, get_issuer, get_issuer_country_code` にする。`from app.services.fx_currencies import list_invoice_currencies` を足す。

(2) `_INVOICE_COLUMNS` の最後の行。変更前:
```python
    issuer_region
"""
```
変更後:
```python
    issuer_region,
    payment_method_id, tax_rate_percent, shipping_carrier, shipping_service, shipping_snapshot
"""
```

(3) 変更前:
```python
_UPDATABLE_COLUMNS = {"payment_method", "due_date", "exchange_rate_jpy", "exchange_rate_usd", "notes"}
```
変更後:
```python
_UPDATABLE_COLUMNS = {"due_date", "notes"}
```

(4) `_calc_currency_amounts`（`def _calc_currency_amounts(` から `    return amount_jpy, amount_usd` まで）を消し、同じ場所に次を置く（ここの関数と定数は作る道・見積から作る道・発行の道が共に使う）:
```python
_INSERT_INVOICE_SQL = """
    INSERT INTO invoices (
        tenant_id, invoice_number, quote_id, company_id, contact_id, currency,
        subtotal, shipping_fee, tax_amount, total_amount,
        exchange_rate_jpy, exchange_rate_usd, amount_jpy, amount_usd,
        payment_method, payment_method_id, status, branch_number, erp_key,
        due_date, notes, created_by,
        ship_to_snapshot, bill_to_snapshot, fx_rate_snapshot, issuer_region,
        duty_amount, duty_policy_snapshot, tax_rate_percent,
        shipping_carrier, shipping_service, shipping_snapshot
    ) VALUES (
        :tid, :inv_num, :qid, :company_id, :contact_id, :currency,
        :subtotal, :shipping, :tax, :total,
        :rate_jpy, :rate_usd, :amt_jpy, :amt_usd,
        :payment, :payment_method_id, 'draft', 1, :erp_key,
        :due_date, :notes, :created_by,
        :ship_to, :bill_to, :fx_rate, :issuer_region,
        :duty_amount, :duty_policy_snapshot, :tax_rate_percent,
        :shipping_carrier, :shipping_service, :shipping_snapshot
    ) RETURNING id
"""

_RECOMPUTE_SET_SQL = """
    subtotal = :subtotal, shipping_fee = :shipping, tax_amount = :tax, total_amount = :total,
    exchange_rate_jpy = :rate_jpy, exchange_rate_usd = :rate_usd, amount_jpy = :amt_jpy, amount_usd = :amt_usd,
    fx_rate_snapshot = :fx_rate, duty_amount = :duty_amount, duty_policy_snapshot = :duty_policy_snapshot,
    tax_rate_percent = :tax_rate_percent, shipping_snapshot = :shipping_snapshot
"""


def _load_snapshot(value):
    """写しの列は PG では dict、SQLite の試験では JSON の文字。"""
    if isinstance(value, str):
        return json.loads(value)
    return value


def _raise_if_blocked(result: invoice_totals.TotalsResult) -> None:
    blocked = invoice_totals.first_block(result)
    if blocked is not None:
        raise HTTPException(status_code=blocked[0], detail=blocked[1])


def _shipping_choice(body) -> invoice_totals.ShippingChoice | None:
    if body is None:
        return None
    if body.mode == "none":
        return invoice_totals.ShippingChoice(mode="none")
    return invoice_totals.ShippingChoice(
        mode="calculate", carrier=body.carrier, service_type=body.service_type,
        fee=body.fee, currency=body.currency.upper(),
    )


def _shipping_from_stored(row) -> invoice_totals.ShippingChoice:
    """発行の時に保存した送料の写しから選び方を戻す（D10）。"""
    snap = _load_snapshot(row["shipping_snapshot"])
    if snap and snap.get("source") in ("calculate", "quote"):
        return invoice_totals.ShippingChoice(
            mode=snap["source"], carrier=snap.get("carrier"), service_type=snap.get("service_type"),
            fee=Decimal(snap["original_fee"]), currency=snap.get("original_currency") or row["currency"],
        )
    if snap and snap.get("source") == "none":
        return invoice_totals.ShippingChoice(mode="none")
    fee = Decimal(row["shipping_fee"] or 0)
    if fee > 0:
        return invoice_totals.ShippingChoice(
            mode="quote", carrier=row["shipping_carrier"], fee=fee, currency=row["currency"],
        )
    return invoice_totals.ShippingChoice(mode="none")


async def _compute(db, tenant_id, *, currency, items, shipping, ship_to, bill_to, base_date=None):
    destination = invoice_totals.destination_country(ship_to, bill_to)
    inputs = await invoice_totals.load_totals_inputs(
        db, tenant_id, destination=destination, base_date=base_date or invoice_totals.today_jst(),
    )
    return invoice_totals.compute_totals(
        currency=currency, items=items, shipping=shipping, destination=destination, inputs=inputs,
    )
```

(5) draft-context と試算の道。`@router.get(\n    "/invoices/{invoice_id}",\n    response_model=InvoiceDetailResponse,` の `@router.get(` の行の直前に、次の 2 つの道を置く（D12。順番が大事）:
```python
@router.get(
    "/invoices/draft-context",
    response_model=DraftContextResponse,
    dependencies=[Depends(require_permission("invoices.create"))],
)
async def get_invoice_draft_context(
    company_id: int | None = Query(default=None, ge=1),
    contact_id: int | None = Query(default=None, ge=1),
    invoice_id: int | None = Query(default=None, ge=1),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),  # noqa: ARG001
):
    """作成画面と下書きの詳細画面の材料（書かない。design.md §3-4 の表の1行目）。"""
    stored = None
    if invoice_id is not None:
        res = await db.execute(
            text("SELECT company_id, contact_id, currency, issuer_region FROM invoices WHERE id = :id"),
            {"id": invoice_id},
        )
        stored = res.mappings().first()
        if stored is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found:invoice")
        if company_id is not None and company_id != stored["company_id"]:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invoice_company_mismatch")
        company_id = stored["company_id"]
        if contact_id is None:
            contact_id = stored["contact_id"]
    if company_id is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="draft_context_target")

    co = await db.execute(text("SELECT id FROM companies WHERE id = :id"), {"id": company_id})
    if co.first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found:company")

    contact_name = None
    contact_email = None
    if contact_id is not None:
        ct = await db.execute(
            text("SELECT company_id, display_name, surname, given_name, primary_email FROM contacts WHERE id = :id"),
            {"id": contact_id},
        )
        ct_row = ct.mappings().first()
        if ct_row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found:contact")
        if ct_row["company_id"] != company_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="指定された担当者は指定会社に所属していません")
        contact_name = ct_row["display_name"] or " ".join(
            p for p in (ct_row["surname"], ct_row["given_name"]) if p
        ) or None
        contact_email = ct_row["primary_email"]

    ship_to = await _fetch_address_snapshot(db, company_id, "delivery")
    bill_to = await _fetch_address_snapshot(db, company_id, "billing")
    if stored is not None:
        region = stored["issuer_region"] or "overseas"
    else:
        region = decide_issuer_region(bill_to)

    fx = await invoice_totals.load_latest_fx(db)
    currencies = await list_invoice_currencies(db)
    tax_row = await invoice_totals.load_tax_row(db, invoice_totals.today_jst())
    policy = await db.execute(
        text("SELECT default_currency FROM public.tenant_settings WHERE tenant_id = :tid"),
        {"tid": int(tenant_id)},
    )
    policy_row = policy.first()
    return DraftContextResponse(
        company_id=company_id,
        ship_to=ship_to,
        bill_to=bill_to,
        contact_name=contact_name,
        contact_email=contact_email,
        issuer_region=region,
        origin_country_code=await get_issuer_country_code(db, tenant_id, region),
        destination_country_code=invoice_totals.destination_country(ship_to, bill_to),
        destination_postal_code=invoice_totals.destination_postal_code(ship_to, bill_to),
        currencies=currencies,
        fx_rates=[
            {"currency": cur, "rate": float(row.rate_jpy), "fetched_at": invoice_totals._iso_utc(row.fetched_at)}
            for cur, row in sorted(fx.items())
        ],
        default_currency=(policy_row[0] if policy_row else None),
        currency=(stored["currency"] if stored is not None else None),
        payment_methods=await invoice_payment_methods.list_payment_choices(db, tenant_id, region),
        tax_rate_percent=(tax_row.rate_percent if tax_row else None),
        incoterms=await invoice_totals.load_incoterms(db, tenant_id),
    )


@router.post(
    "/invoices/preview",
    response_model=InvoicePreviewResponse,
    dependencies=[Depends(require_permission("invoices.create"))],
)
async def preview_invoice(
    data: InvoicePreviewRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),  # noqa: ARG001
):
    """試算（書かない）。未計算でも 200 で理由を返す（D5）。"""
    co = await db.execute(text("SELECT id FROM companies WHERE id = :id"), {"id": data.company_id})
    if co.first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found:company")
    ship_to = await _fetch_address_snapshot(db, data.company_id, "delivery")
    bill_to = await _fetch_address_snapshot(db, data.company_id, "billing")
    destination = invoice_totals.destination_country(ship_to, bill_to)
    inputs = await invoice_totals.load_totals_inputs(
        db, tenant_id, destination=destination, base_date=invoice_totals.today_jst(),
    )
    result = invoice_totals.compute_totals(
        currency=data.currency,
        items=[invoice_totals.TotalsItem(quantity=i.quantity, unit_price=i.unit_price) for i in data.items],
        shipping=_shipping_choice(data.shipping),
        destination=destination,
        inputs=inputs,
    )
    return InvoicePreviewResponse(
        currency=result.currency, subtotal=result.subtotal, shipping_fee=result.shipping_fee,
        tax_amount=result.tax_amount, tax_rate_percent=result.tax_rate_percent,
        duty_amount=result.duty_amount, duty_label=result.duty_label, duty_components=result.duty_components,
        total_amount=result.total_amount, uncomputed=result.uncomputed, incoterms=inputs.incoterms,
    )
```
注: `contacts` に `surname`・`given_name`・`display_name`・`primary_email` の列があることは backend/app/services/tenant.py の contacts の CREATE TABLE（recon-cd.md）で確かめた。SQLite の試験の contacts に無い列があれば、draft-context の試験は PG のファイルだけに置く（§2-11）。

(6) 詳細の道 `get_invoice` の最後の 2 行。変更前:
```python
    items = await _get_invoice_items(db, invoice_id)
    return InvoiceDetailResponse(**dict(row), items=[InvoiceItemResponse(**i) for i in items])


@router.post(
    "/invoices/from-quote/{quote_id}",
```
変更後:
```python
    items = await _get_invoice_items(db, invoice_id)
    label = await invoice_payment_methods.load_payment_label(db, tenant_id, row["payment_method_id"])
    return InvoiceDetailResponse(
        **dict(row), items=[InvoiceItemResponse(**i) for i in items],
        payment_method_display_name=(label or {}).get("display_name"),
        payment_method_type=(label or {}).get("method_type"),
    )


@router.post(
    "/invoices/from-quote/{quote_id}",
```

(7) 見積から作る道 `create_invoice_from_quote`。`    # 為替レート取得（JPY 以外の場合）\n    currency = q["currency"]\n    fx_snap = get_fx_rate(currency) if ...` の 3 行から、`    invoice_id = inv_result.scalar_one()` の行の直前（INSERT の `)` まで）を、次で置き換える。明細の写し（`# 見積明細をコピー（hs_code を含む）` 以降）と監査・commit・返し方は変えない:
```python
    currency = (q["currency"] or "JPY").upper()
    quote_items_rows = (await db.execute(
        text("SELECT quantity, unit_price FROM quote_items WHERE quote_id = :qid ORDER BY sort_order"),
        {"qid": quote_id},
    )).mappings().all()
    q_fee = Decimal(q["shipping_fee"] or 0)
    shipping = (
        invoice_totals.ShippingChoice(mode="quote", carrier=q.get("shipping_carrier"), fee=q_fee, currency=currency)
        if q_fee > 0 else invoice_totals.ShippingChoice(mode="none")
    )
    totals = await _compute(
        db, tenant_id, currency=currency,
        items=[invoice_totals.TotalsItem(quantity=r["quantity"], unit_price=Decimal(r["unit_price"])) for r in quote_items_rows],
        shipping=shipping, ship_to=ship_to_snap, bill_to=bill_to_snap,
    )
    _raise_if_blocked(totals)

    inv_result = await db.execute(
        text(_INSERT_INVOICE_SQL),
        {
            "tid": tenant_id, "inv_num": invoice_number, "qid": quote_id,
            "company_id": company_id, "contact_id": q.get("contact_id"),
            "currency": currency,
            "payment": None, "payment_method_id": None,
            "erp_key": erp_key, "due_date": None, "notes": q["notes"], "created_by": current_user.id,
            "ship_to": json.dumps(ship_to_snap) if ship_to_snap else None,
            "bill_to": json.dumps(bill_to_snap) if bill_to_snap else None,
            "issuer_region": issuer_region,
            **invoice_totals.to_db_params(totals),
        },
    )
```

(8) 作る道 `create_invoice`。`    subtotal = sum(item.quantity * item.unit_price for item in data.items)` の行から、`    invoice_id = inv_result.scalar_one()` の行の直前までを、次で置き換える（担当者の確かめ・明細の INSERT・監査・commit・返し方は変えない。監査の `"total": str(total)` は `"total": str(totals.total_amount)` にする）:
```python
    # スナップショット取得
    ship_to_snap = await _fetch_address_snapshot(db, data.company_id, "delivery")
    bill_to_snap = await _fetch_address_snapshot(db, data.company_id, "billing")
    # ADR-1061 便2-2c2a: 発行元の地域は請求先の国で決めて保存する（国が無いと作らない）
    issuer_region = decide_issuer_region(bill_to_snap)
    if issuer_region is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="bill_to_country")

    currency = data.currency.upper()
    totals = await _compute(
        db, tenant_id, currency=currency,
        items=[invoice_totals.TotalsItem(quantity=i.quantity, unit_price=i.unit_price) for i in data.items],
        shipping=_shipping_choice(data.shipping), ship_to=ship_to_snap, bill_to=bill_to_snap,
    )
    _raise_if_blocked(totals)

    payment_text = None
    payment_method_id = None
    if data.payment_method_ref is not None:
        try:
            payment_text, payment_method_id = await invoice_payment_methods.resolve_payment_ref(
                db, tenant_id, method_type=data.payment_method_ref.method_type,
                method_id=data.payment_method_ref.id, region=issuer_region, currency=currency,
            )
        except PaymentMethodInvalid:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="payment_method")

    max_result = await db.execute(text("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM invoices"))
    next_id = max_result.scalar()
    invoice_number = f"IN-{next_id:04d}-01"
    erp_key = str(uuid.uuid4())[:8].upper()

    inv_result = await db.execute(
        text(_INSERT_INVOICE_SQL),
        {
            "tid": tenant_id, "inv_num": invoice_number, "qid": None,
            "company_id": data.company_id, "contact_id": data.contact_id,
            "currency": currency,
            "payment": payment_text, "payment_method_id": payment_method_id,
            "erp_key": erp_key, "due_date": data.due_date, "notes": data.notes, "created_by": current_user.id,
            "ship_to": json.dumps(ship_to_snap) if ship_to_snap else None,
            "bill_to": json.dumps(bill_to_snap) if bill_to_snap else None,
            "issuer_region": issuer_region,
            **invoice_totals.to_db_params(totals),
        },
    )
```

(9) PATCH の道 `update_invoice`。変更前:
```python
    update_data = data.model_dump(exclude_unset=True)
    update_data = {k: v for k, v in update_data.items() if k in _UPDATABLE_COLUMNS}
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="no_fields_to_update")
```
変更後:
```python
    sent = data.model_dump(exclude_unset=True)
    update_data = {k: v for k, v in sent.items() if k in _UPDATABLE_COLUMNS}
    if "payment_method_ref" in sent:
        ref = data.payment_method_ref
        if ref is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="payment_method")
        try:
            payment_text, payment_method_id = await invoice_payment_methods.resolve_payment_ref(
                db, tenant_id, method_type=ref.method_type, method_id=ref.id,
                region=old_row["issuer_region"] or "overseas", currency=old_row["currency"],
            )
        except PaymentMethodInvalid:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="payment_method")
        update_data["payment_method"] = payment_text
        update_data["payment_method_id"] = payment_method_id
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="no_fields_to_update")
```
（下書きでないときは、この前にある今の門の 400 が止める。D11）

(10) 発行の道 `issue_invoice` の中身（`    """請求書を発行する（draft → issued）"""` の次の行から `    row = result.mappings().first()\n    if not row:\n        raise HTTPException(... "draft状態の請求書のみ発行できます")` まで）を、次で置き換える（監査・commit・返し方は変えない）:
```python
    cur = await db.execute(
        text(f"SELECT {_INVOICE_COLUMNS} FROM invoices WHERE id = :id FOR UPDATE"),
        {"id": invoice_id},
    )
    old = cur.mappings().first()
    if not old or old["status"] != "draft":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="draft状態の請求書のみ発行できます")

    if old["payment_method_id"] is not None:
        ok = await invoice_payment_methods.is_current_choice(
            db, tenant_id, payment_method_id=old["payment_method_id"],
            region=old["issuer_region"] or "overseas", currency=old["currency"],
        )
        if not ok:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="payment_method")

    items = await _get_invoice_items(db, invoice_id)
    totals = await _compute(
        db, tenant_id, currency=old["currency"],
        items=[invoice_totals.TotalsItem(quantity=i["quantity"], unit_price=Decimal(i["unit_price"])) for i in items],
        shipping=_shipping_from_stored(old),
        ship_to=_load_snapshot(old["ship_to_snapshot"]), bill_to=_load_snapshot(old["bill_to_snapshot"]),
    )
    _raise_if_blocked(totals)
    params = invoice_totals.to_db_params(totals)
    params.pop("shipping_carrier")
    params.pop("shipping_service")
    result = await db.execute(
        text(
            f"UPDATE invoices SET {_RECOMPUTE_SET_SQL}, status = 'issued', issued_at = NOW(), updated_at = NOW() "
            f"WHERE id = :id AND status = 'draft' RETURNING {_INVOICE_COLUMNS}"
        ),
        {**params, "id": invoice_id},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="draft状態の請求書のみ発行できます")
```
注: 送料の会社とサービスの列（shipping_carrier・shipping_service）は発行で変えない（design.md §3-4「選んだ送料の会社と元の額・支払方法は変えない」）。shipping_snapshot は元の額を保ったまま換算の率だけが新しくなる。

(11) PDF の道 `download_invoice_pdf`。変更前:
```python
        "fx_rate_snapshot": row["fx_rate_snapshot"],
        "notes": row["notes"],
    }

    pdf_bytes = await run_in_threadpool(render_invoice_pdf, invoice_data, tenant_profile)
```
変更後:
```python
        "fx_rate_snapshot": row["fx_rate_snapshot"],
        "notes": row["notes"],
        "tax_rate_percent": float(row["tax_rate_percent"]) if row["tax_rate_percent"] is not None else None,
        "payment": await _pdf_payment(db, tenant_id, row),
    }

    pdf_bytes = await run_in_threadpool(render_invoice_pdf, invoice_data, tenant_profile)
```
そして `download_invoice_pdf` の `@router.get(\n    "/invoices/{invoice_id}/pdf",` の直前に次を足す:
```python
async def _pdf_payment(db: AsyncSession, tenant_id: int, row) -> dict | None:
    """PDF の支払方法の区切り（design.md §3-7）。版は古くても消されていてもその版を読む。"""
    if row["payment_method_id"] is not None:
        return await invoice_payment_methods.load_payment_version(db, tenant_id, row["payment_method_id"])
    if row["payment_method"] == "paypal":
        return {"method_type": "paypal"}
    return None


```

(12) 為替を見せる道 `fetch_fx_rate`。`fetch_fx_rate` の引数に `db: AsyncSession = Depends(get_db),` を `currency: str,` の次に足す。docstring の「ライブ取得する（C-7）」を「為替の表（public.app_fx_rate_history）の最新行を返す（invoice-create-portfolio 便C・K24）」に直す。変更前:
```python
    result = get_fx_rate(currency)
    if result is None:
```
変更後:
```python
    fx = await invoice_totals.load_latest_fx(db)
    row = fx.get(currency.upper())
    result = (
        None if row is None
        else {"currency": row.currency, "rate": float(row.rate_jpy), "fetched_at": invoice_totals._iso_utc(row.fetched_at)}
    )
    if result is None:
```
（503 の文「為替レートの取得に失敗しました: {currency}」と JPY の枝は変えない）

(13) 確かめ: 変更の後 `grep -c "get_fx_rate" backend/app/routers/invoices.py` が 0、`grep -c "_calc_currency_amounts" backend/app/routers/invoices.py` が 0（手順5）。

### 2-6. backend/app/services/invoice_renderer.py

(1) InvoiceRenderData に 2 つの欄を足す。変更前:
```python
    paypal_copy: Optional[dict] = None


# ─────────────────────────────────────────────────────────────────────
```
（InvoiceRenderData の最後。同じ並びが 2 か所あれば最初のもの＝:157 付近）
変更後:
```python
    paypal_copy: Optional[dict] = None
    # invoice-create-portfolio 便C: 使った税率（Tax 行に添える）と支払方法の区切り（design.md §3-7）
    tax_rate_percent: Optional[float] = None
    payment: Optional[dict] = None


# ─────────────────────────────────────────────────────────────────────
```

(2) Tax 行。変更前:
```python
    if data.tax_amount:
        c.drawRightString(165 * mm, y, "Tax:")
```
変更後:
```python
    if data.tax_amount:
        tax_label = "Tax:" if data.tax_rate_percent is None else f"Tax ({data.tax_rate_percent:g}%):"
        c.drawRightString(165 * mm, y, tax_label)
```

(3) 合計の後・為替の脚注の前に支払方法の区切りを足す。変更前:
```python
    # ── 7. 為替レート脚注（外貨時のみ）────────────────────────────────
```
変更後（目印の行の前に次を足す）:
```python
    # ── 6b. 支払方法（invoice-create-portfolio 便C。design.md §3-7）──────────
    if data.payment:
        lines = _payment_lines(data.payment)
        if lines:
            c.setFont(font, 9)
            c.drawString(20 * mm, y, "Payment:")
            y -= 4 * mm
            c.setFont(font, 8)
            for line in lines:
                c.drawString(22 * mm, y, line[:90])
                y -= 4 * mm
            y -= 2 * mm

    # ── 7. 為替レート脚注（外貨時のみ）────────────────────────────────
```
そして `def render_invoice_pdf(` の定義の前（同じファイルの上の方の関数の並び。`_render_doc_pdf` の定義の前）に次を足す:
```python
def _payment_lines(payment: dict) -> list[str]:
    """支払方法の区切りの行（銀行・Wise・PayPal）。値の無い行は描かない。"""
    kind = payment.get("method_type")
    if kind == "paypal":
        return ["PayPal"]
    if kind == "bank":
        pairs = [
            ("Bank", payment.get("bank_name")),
            ("Branch", payment.get("bank_branch")),
            ("Account type", payment.get("account_type")),
            ("Account number", payment.get("account_number")),
            ("Account holder", payment.get("account_holder")),
            ("SWIFT", payment.get("swift_code")),
        ]
    elif kind == "wise":
        pairs = [
            ("Account holder", payment.get("account_holder")),
            ("Wise email", payment.get("wise_email")),
            ("Bank", payment.get("bank_name")),
            ("SWIFT/BIC", payment.get("swift_bic")),
            ("IBAN", payment.get("iban")),
        ]
    else:
        return []
    return [f"{k}: {v}" for k, v in pairs if v]
```

(4) `render_invoice_pdf` の中の `InvoiceRenderData(` に 2 行を足す。変更前:
```python
        tenant_registration_number=tenant_profile.get("registration_number"),
        paypal_copy=paypal_copy,
    )

    return _render_doc_pdf(data)
```
（`render_invoice_pdf` の中のもの。`render_quote_pdf` には同じ並びが無いことを手順2 で数える）
変更後:
```python
        tenant_registration_number=tenant_profile.get("registration_number"),
        paypal_copy=paypal_copy,
        tax_rate_percent=invoice_data.get("tax_rate_percent"),
        payment=invoice_data.get("payment"),
    )

    return _render_doc_pdf(data)
```
注: `_render_paypal_copy_pdf`（invoices.py）は invoice_data に `payment` を入れないので、写しの PDF は今のまま（D15）。

### 2-7. backend/app/realtime/topics.py

請求書の道の並び（`("POST", "/api/v1/invoices"): _PENDING,` の行）の次の行に足す。変更前:
```python
    ("POST", "/api/v1/invoices"): _PENDING,
```
変更後:
```python
    ("POST", "/api/v1/invoices"): _PENDING,
    ("POST", "/api/v1/invoices/preview"): _PENDING,
```
（手順2 で変更前の行が 1 回だけあることを数える。外れたら `BLOCKED: topics.py 変更前の文`）

### 2-8. 理由コード 6 つ（D16）

(1) frontend/src/lib/apiErrorReason.ts の API_ERROR_REASON_KEYS の最後の要素の後に、次の 6 行を足す（今の並びの書き方に合わせる。キーの名前は値の通り）:
```ts
  duty_needs_carrier: "apiError.dutyNeedsCarrier",
  duty_rule_overlap: "apiError.dutyRuleOverlap",
  shipping_required: "apiError.shippingRequired",
  fx_rate: "apiError.fxRate",
  tax_rate: "apiError.taxRate",
  payment_method: "apiError.paymentMethod",
```
今の一覧が `{ code: "apiError.xxx" }` の形でなく配列などの別の形なら、その形のまま同じ 6 つを足す（形を変えない）。

(2) frontend/src/lib/apiErrorReason.test.ts:76 の件数 `18` を `24` にする。

(3) frontend/src/locales/ja.json の `"apiError": {` の中の最後のキーの後に足す:
```json
"dutyNeedsCarrier": "この国の関税の額は送料の会社ごとに決まっているため、送料の会社が無いと関税を計算できません。送料の会社を選ぶか、関税の額の画面で「どの会社でも」の決まりを足してください。",
"dutyRuleOverlap": "同じ国・同じ送料の会社で有効期間が重なる決まりがあるため、保存できません。期間を直すか、前の決まりを止めてください。",
"shippingRequired": "送料が決まっていないため、請求書を作れません。送料を選ぶか、「送料を請求しない」を選んでください。",
"fxRate": "この通貨の為替の値が取れていないため、金額を計算できません。円かドルを選ぶか、為替の値が入るまで待ってからやり直してください。",
"taxRate": "今日使える消費税の率が登録されていないため、日本宛の請求書を作れません。最高管理者に税率の画面で率を登録してもらってください。",
"paymentMethod": "選んだ支払方法は今は使えないため、請求書を保存できません。支払方法を選び直してください。"
```
（`dutyRuleOverlap` が便B で既に apiError の中にあるときは、その行を残して残り 5 つだけを足す。手順2 で数える）

(4) frontend/src/locales/en.json の `"apiError": {` の中に同じキーで足す:
```json
"dutyNeedsCarrier": "Duty for this country depends on the shipping carrier, so it cannot be calculated without one. Choose a carrier, or add an \"any carrier\" rule on the duty amounts screen.",
"dutyRuleOverlap": "Another rule for the same country and carrier overlaps this period, so it cannot be saved. Change the period or turn off the earlier rule.",
"shippingRequired": "Shipping has not been decided, so the invoice cannot be created. Choose a shipping rate or select \"Do not charge shipping\".",
"fxRate": "No exchange rate is available for this currency, so amounts cannot be calculated. Choose JPY or USD, or try again after the rate is loaded.",
"taxRate": "No consumption tax rate is registered for today, so invoices to Japan cannot be created. Ask a super admin to register the rate on the tax rate screen.",
"paymentMethod": "The selected payment method is no longer available, so the invoice cannot be saved. Choose a payment method again."
```

(5) backend/tests/test_api_error_reason_sync.py の固定の一覧（:41-61）の最後に、同じ 6 つのコードを同じ書き方で足す。

### 2-9. backend/tests/conftest.py

(1) SQLite の invoices の表（`CREATE TABLE IF NOT EXISTS invoices (`）の最後の列。変更前:
```python
                paypal_copy_pdf_at TIMESTAMP,
                issuer_region VARCHAR(20)
            )
```
変更後:
```python
                paypal_copy_pdf_at TIMESTAMP,
                issuer_region VARCHAR(20),
                payment_method_id INTEGER,
                tax_rate_percent NUMERIC(5, 2),
                shipping_carrier VARCHAR(50),
                shipping_service VARCHAR(100),
                shipping_snapshot TEXT
            )
```

(2) ファイルの末尾に fixture を足す（D17）:
```python
@pytest.fixture
def stub_invoice_totals(monkeypatch):
    """SQLite の試験用: invoice_totals.load_totals_inputs を差し替える（public の表を読まない）。

    既定は DAP・税率 10%（2019-10-01）・為替 USD=150。試験は返り値の .set(...) で中身を変えられる。
    """
    from datetime import date, datetime, timezone
    from decimal import Decimal

    from app.services import invoice_totals as it

    state = {
        "incoterms": "DAP",
        "tax": it.TaxRow(rate_percent=Decimal("10.00"), effective_from=date(2019, 10, 1)),
        "duty_rules": (),
        "fx": {"USD": it.FxRow(currency="USD", rate_jpy=Decimal("150.0000"), fetched_at=datetime(2026, 11, 15, 1, 0, tzinfo=timezone.utc))},
        "calls": [],
    }

    async def _fake(db, tenant_id, *, destination, base_date):
        state["calls"].append({"destination": destination, "base_date": base_date})
        return it.TotalsInputs(
            base_date=base_date, incoterms=state["incoterms"], tax=state["tax"],
            duty_rules=state["duty_rules"], fx=state["fx"],
        )

    class _Handle:
        def set(self, **kw):
            state.update(kw)
            return self

        @property
        def calls(self):
            return state["calls"]

    monkeypatch.setattr(it, "load_totals_inputs", _fake)
    return _Handle()
```
`import pytest` が conftest.py の上に既にあることを手順2 で数える。

### 2-10. 今ある試験の直し（作る道の形が変わるため）

どのファイルも、POST /api/v1/invoices の体から `shipping_fee`・`tax_amount`・`exchange_rate_jpy`・`exchange_rate_usd`・`payment_method` を消し、`"shipping": {"mode": "none"}` を足す。そのファイルの先頭（import の後）に `pytestmark = pytest.mark.usefixtures("stub_invoice_totals")` を足す（`import pytest` が無ければ足す）。

- backend/tests/test_invoices.py
  - `_create_invoice` の payload に `"shipping": {"mode": "none"},` を足す。
  - `test_update_invoice_draft`（:139-150）: 送る体を `{"notes": "更新メモ"}`、確かめを `res.json()["notes"] == "更新メモ"` に変える（payment_method の文字は受けない。D11）。
  - `test_converted_invoice_inherits_amounts`（:229-244）: 名前を `test_converted_invoice_recomputes_amounts` にし、見積の shipping_fee 500・tax_amount 100 の見積から作った請求書が、shipping_fee 500、tax_amount 0（会社の請求先は US。外国宛は 0）、total_amount＝小計＋500 になることを確かめる（design.md §3-4 の見積から作る行「見積の tax_amount・total_amount は写さない」）。
  - `class` の `_calc_currency_amounts` の試験 5 本（:259-306）を消す（関数を消すため。同じ意味は test_invoice_totals.py の T12〜T14 が持つ）。
  - `test_create_invoice_calculates_subtotal`（:308-）: `tax_amount` を送らず、`subtotal`・`total_amount` が明細の合計（US 宛で税 0・送料 0）であることを確かめる。
  - :764-773 の形の試験（InvoiceResponse の欄）: 新しい 5 欄（`payment_method_id`・`tax_rate_percent`・`shipping_carrier`・`shipping_service`・`shipping_snapshot`）に None を足す。
  - get_fx_rate の単体試験（:621-666）は残す（fx_rate.py は消さない）。
- backend/tests/test_issuer.py（:266・:278・:287・:301・:309 の POST /invoices）、backend/tests/test_paypal_invoicing.py（:199・:205・:293）、backend/tests/test_company_stats.py（:79）、backend/tests/test_products.py（:442）: 上の決まりで体を直し、pytestmark を足す。額を確かめている行は、送料 0・US 宛で税 0 の値に合わせる（請求先が JP の試験は stub の税率 10% で税が付く。値は §2-11 の試験 F7 の式で出す）。
- 手順2 で各ファイルの `tax_amount`・`shipping_fee` を数えて報告に貼る（直す前の数）。直した後、手順6 の試験が通ること。

### 2-11. 新しい試験

backend/tests/test_invoice_totals.py（純粋な計算。DB なし。21 本）
- 共通: `inputs(**kw)` を作る小さな関数（既定 DAP・税 10%・USD 150・基準日 2026-11-15）。
- T1 JP 宛・JPY・明細 3000×2・送料 none → 小計 6000・税 600・合計 6600・tax_rate_percent 10.00（K7）。
- T2 JP 宛で税の基準は 小計＋送料: 送料 calculate 1000 JPY → 税 700・合計 7700。
- T3 税の切り捨て: JP 宛・JPY・明細 999×1 → 税 99（99.9 を切り捨て）。USD の請求書で 10.05×1 → 税 1.00（1.005 を切り捨て）。
- T4 US 宛 → 税 0・tax_rate_percent None。
- T5 JP 宛で税の行が無い → uncomputed `["tax_rate"]`・合計 None・first_block が (409, "tax_rate")。
- T6 送料 None → uncomputed 先頭 `shipping_required`・first_block (422, "shipping_required")（K4）。
- T7 送料の換算: 請求書 USD・送料 15000 JPY・USD 150 → 送料 100.00。shipping_snapshot の original_fee "15000"・original_currency "JPY"・fx に USD の行。
- T8 請求書 EUR で EUR の行が無い → uncomputed に `fx_rate`・合計 None。
- T9 DAP と DDU → duty_amount None・合計に足さない（K6）。
- T10 DDP・carrier NULL の行（中身 base subtotal 10%）→ duty 600（小計 6000）・duty_label が行の label・duty_policy_snapshot の rule.id。
- T11 DDP・会社一致が優先: 行 A carrier "fedex" 5%・行 B carrier NULL 10%、送料 carrier " FedEx " → 行 A（300）。
- T12 DDP・会社つきの行だけで送料 none → `duty_needs_carrier`。会社が一致しない（"dhl"）→ `duty_needs_carrier`（K18）。
- T13 中身の基準 3 通り: subtotal・subtotal_shipping・subtotal_shipping_prior（前の中身の額を足す）を 1 つの行で並べて額を確かめる。
- T14 下限・上限: min 2000 JPY で raw 600 → 2000。max 10 USD を JPY の請求書で（USD 150）→ 1500 で挟む。min の通貨の行が無い → `fx_rate`。
- T15 中身ごとに切り捨ててから足す: 2 つの中身がそれぞれ 0.5 円を生む → 合計 0。
- T16 合計＝小計＋送料＋税＋関税（K9）。関税 NULL のときは 0 として足す。
- T17 為替の列（K13）: JPY の請求書 → exchange_rate_jpy None・amount_jpy＝合計・exchange_rate_usd 150・amount_usd＝round(合計/150, 2)。USD の請求書 → exchange_rate_jpy 150・amount_usd＝合計・exchange_rate_usd None・fx_rate_snapshot の rate 150.0・fetched_at が "+00:00" で終わる。
- T18 USD の行が無い JPY の請求書 → amount_usd None で uncomputed は空（止めない）。
- T19 normalize_carrier: " FedEx " → "fedex"、"" → None、None → None。
- T20 destination_country: 発送先の写しが優先、無ければ請求先、どちらも無い → None。destination_postal_code は国と同じ写しから。
- T21 today_jst: `datetime.now` を 2026-11-14T15:30:00Z に固定すると 2026-11-15（ZoneInfo の確かめ。`monkeypatch` で invoice_totals.datetime を差し替える）。

backend/tests/test_invoices_create_flow.py（SQLite。`pytestmark = pytest.mark.usefixtures("stub_invoice_totals")` ではなく、各試験が fixture `stub_invoice_totals` を引数で受けて中身を変える。16 本）
- 会社と担当は test_invoices.py の `_create_company_contact` と同じ作り方（このファイルに写す。country を "JP" と "US" で使い分ける）。
- F1 shipping 無しの作成 → 422 detail `shipping_required`（K4）。
- F2 `{"mode": "none"}` → 201・shipping_fee 0・shipping_snapshot.no_charge true・shipping_carrier null。
- F3 calculate（carrier "FedEx"・service_type "FEDEX_INTERNATIONAL_PRIORITY"・fee "12000"・currency "JPY"）を USD の請求書で → shipping_fee 80.00・shipping_carrier "FedEx"・shipping_service が同じ。
- F4 作る道に `tax_amount`・`shipping_fee`・`exchange_rate_jpy`・`exchange_rate_usd`・`amount_jpy`・`amount_usd`・`payment_method` のどれかを足すと 422（7 通りを parametrize。K18）。
- F5 calculate で carrier が無い・fee が無い → 422。none に fee を付ける → 422。
- F6 preview と作成が同じ額（K9）: JP の会社・明細 2 行・送料 calculate 1500 JPY → preview の各額と、作った請求書の subtotal・shipping_fee・tax_amount・total_amount が一致。
- F7 JP 宛で税率の行が無い（stub を `tax=None`）→ preview は 200 で uncomputed `["tax_rate"]`・作成は 409 `tax_rate`（K7・K18）。
- F8 EUR で為替が無い → preview 200 uncomputed に `fx_rate`・作成 409 `fx_rate`。
- F9 DDP（stub に carrier "fedex" の行だけ）: 作成で送料 none → 409 `duty_needs_carrier`、carrier "dhl" → 409 `duty_needs_carrier`、carrier " FedEx " → 201 で duty_amount が中身の額（K18 の作る道 2 通りと比べ方）。
- F10 DDP の率を変えると preview と作成の duty_amount が変わる（K6）。
- F11 見積から作る（K16）: 送料 0 の見積 → 201・shipping_snapshot.source "none"。送料 500 の見積 → shipping_snapshot.source "quote"・original_fee "500.00" か "500"（Decimal の文字。どちらかを assert で受ける）・同じ明細と送料で作る道と税・合計が一致。
- F12 見積から作る・DDP・会社つきの行だけ（見積の shipping_carrier は NULL）→ 409 `duty_needs_carrier`。見積の shipping_carrier "  FEDEX " と行 "fedex" → 一致して 201（K18 の比べ方）。見積の shipping_carrier を入れるのは直接の `UPDATE quotes SET shipping_carrier = ...`（db_session）で行う。
- F13 発行で計算し直す（K15）: 作成（JP 宛・税 10%）→ stub の税を 8% にして発行 → tax_amount が 8% の額・明細と shipping_carrier は同じ。stub の calls の最後の base_date が today_jst()。
- F14 発行で為替を新しくする（K15）: USD の請求書・送料 calculate 15000 JPY（USD 150 → 100.00）→ stub の USD を 100 にして発行 → shipping_fee 150.00・exchange_rate_jpy 100・合計が変わる。shipping_snapshot.original_fee は "15000" のまま。
- F15 発行で止まる: 作成後に stub を DDP・会社つきの行だけにして発行 → 409 `duty_needs_carrier`・status は draft のまま（K18 の発行の道）。
- F16 為替は表だけ（K13）: `monkeypatch.setattr("app.services.fx_rate.get_fx_rate", 呼ぶと例外を投げる関数)` のもとで、作成・見積から作成・発行が通る。PATCH に `exchange_rate_jpy`・`payment_method`（文字）を送ると 422、`payment_method_ref: null` を送ると 422 `payment_method`、発行済みの請求書に `{"notes": "x"}` を送ると 400「draft状態の請求書のみ編集できます」（K18・K23）。

backend/tests/test_invoice_totals_pg.py（実 PostgreSQL。CI だけで動く。テナント 953。前例 backend/tests/test_duty_rules_pg.py の skip の決まり・テナントの作り方・後始末をそのまま使う。1 つの試験関数 `test_invoice_totals_pg_end_to_end` の中で順に確かめる）
- G1 読み方: public.tax_rates に試験の行（基準日 2100-01-01 の 9.00%。試験の後で消す）を入れ、`load_tax_row(db, date(2100, 1, 2))` が 9.00 を返し、`date(2099, 12, 31)` では前の行（無ければ None）になる。public.app_fx_rate_history に `ZZT`（試験だけの通貨）の 2 行（古い 100・新しい 120）を入れ、`load_latest_fx` の `ZZT` が 120。試験の後で ZZT の行と 2100 の行を消す。
- G2 関税の行の読み方: テナント 953 に DDP の行（US・carrier NULL・2026-01-01〜2026-12-31・中身 2 つ）と止めた行（is_active false）を入れ、`load_duty_rules(db, 953, "US", date(2026, 12, 31))` が 1 行（止めた行は出ない・終わりの日を含む）・中身が sort_order 順。`date(2027, 1, 1)` で 0 行。
- G3 新しいテナント（K22）: 953 のスキーマを backend/app/services/tenant.py の作り方（前例の PG 試験と同じ関数）で作り、`_INSERT_INVOICE_SQL` を `invoice_totals.to_db_params` の値で流して 1 行が入り、`SELECT {_INVOICE_COLUMNS} FROM tenant_953.invoices` が読め、`InvoiceDetailResponse` に入れられる。
- G4 支払方法の候補（K3・K25）: 国内の銀行の版 X（詳細つき）・海外の Wise（USD）・詳細の無い行・is_active false の行を入れる。`list_payment_choices(db, 953, "domestic")` は X だけ。`"overseas"` は Wise だけで wise_currency "USD"。`resolve_payment_ref` は Wise を JPY で渡すと PaymentMethodInvalid、詳細の無い行の id も PaymentMethodInvalid、PayPal は public.tenant_paypal_config に 953 の行が無いので PaymentMethodInvalid。
- G5 版（K25 の便 C 側）: X を直す手順（design.md §3-8 の直す手順: 新しい行 Y と詳細を足し `UPDATE ... SET superseded_by_id = Y WHERE id = X AND superseded_by_id IS NULL AND deleted_at IS NULL`）の後、候補は Y だけ・X で `resolve_payment_ref` は PaymentMethodInvalid・`is_current_choice(X)` は False・`load_payment_version(X)` は X の口座番号を返す。
- G6 draft-context の形（K24 の後半・K23）: 試験用の FastAPI の client を使わず、道の関数 `get_invoice_draft_context` を直接 await で呼ぶ（引数に db・tenant_id 953・current_user は None）。fx_rates の ZZT の fetched_at が "+00:00" で終わる。invoice_id を渡すと保存した issuer_region（domestic）で候補を返し、会社の請求先の国を US に変えた後も同じ候補。
- G7 GET /fx-rate（K24）: `fetch_fx_rate("ZZT", db=db, ...)` を直接呼んで rate 120.0・fetched_at が "+00:00" で終わる。`"ZZQ"`（行なし）で HTTPException 503。`"JPY"` は rate 1.0・fetched_at None。`app.services.fx_rate.get_fx_rate` を呼ぶと例外を投げる関数に差し替えた上で行う。
- G8 後始末: 入れた public の行（tax_rates 2100・app_fx_rate_history ZZT・必要なら tenant_settings 953）とテナント 953 のスキーマを消す（前例の後始末の書き方を写す。命令の文は前例と同じものを使う）。

backend/tests/test_invoice_pdf_payment.py（DB なし。4 本。前例 test_invoices.py:676-750 の PDF の試験の書き方を写す）
- 文字の取り方: `reportlab.pdfgen.canvas.Canvas.drawString` と `drawRightString` を、引数の文字を list に足してから元の関数を呼ぶ関数に monkeypatch で包み、`render_invoice_pdf` を呼んだ後の list を見る。
- H1 銀行の版（bank_name "Test Bank"・account_number "1234567"・account_holder "Test Holder"）を `payment` に渡すと、"Payment:" と "Account number: 1234567" と "Bank: Test Bank" が描かれる（K12）。
- H2 `tax_rate_percent` 10.0・tax_amount 600 → "Tax (10%):" が描かれる。tax_rate_percent None → "Tax:"。
- H3 Wise の版（iban なし）→ "IBAN" の行が描かれず、"Wise email: a@example.com" が描かれる。PayPal → "PayPal"。
- H4 `payment` が None → "Payment:" が描かれない。

## 3. 手順

手順1 枝を取る
    cd ~ && git clone https://github.com/shingo-ops/salesanchor.git sa 2>&1 | tail -1
    cd ~/sa && git checkout release/invoice-create-portfolio-bin-cd
    cd ~/sa && git log --oneline -1 | tail -1
    cd ~/sa && git merge-base --is-ancestor origin/main HEAD; echo "is-ancestor exit=$?"
  期待: 4行目 `is-ancestor exit=0`。1 なら `BLOCKED: 手順1 is-ancestor`（取り込みは Opus が行う）。

手順2 実装前点検 P1〜P8 と変更前の文を流し、結果をそのまま報告に貼る
    cd ~/sa && git rev-parse HEAD | tail -1
    cd ~/sa && ls docs/handoff/invoice-create-portfolio/card-C.md docs/handoff/invoice-create-portfolio/card-D.md | wc -l
    cd ~/sa && ls backend/app/services/invoice_totals.py backend/app/services/invoice_payment_methods.py backend/tests/test_invoice_totals.py backend/tests/test_invoices_create_flow.py backend/tests/test_invoice_totals_pg.py backend/tests/test_invoice_pdf_payment.py 2>&1 | grep -c "No such file or directory"
    cd ~/sa && grep -c "payment_method_id INTEGER" backend/app/services/tenant.py
    cd ~/sa && grep -c "shipping_snapshot JSONB" backend/app/services/tenant.py
    cd ~/sa && grep -c "tax_rate_percent NUMERIC(5, 2)" backend/app/services/tenant.py
    cd ~/sa && grep -c "superseded_by_id" backend/app/services/tenant.py
    cd ~/sa && grep -c "draft-context\|invoices/preview\|invoice_totals" backend/app/routers/invoices.py backend/app/realtime/topics.py | tail -2
    cd ~/sa && git grep -c -w 953 -- backend migrations scripts | wc -l
    cd ~/sa && grep -c "get_fx_rate(" backend/app/routers/invoices.py
    cd ~/sa && grep -c -x -F 'from app.services.fx_rate import get_fx_rate' backend/app/routers/invoices.py
    cd ~/sa && grep -c -x -F '_UPDATABLE_COLUMNS = {"payment_method", "due_date", "exchange_rate_jpy", "exchange_rate_usd", "notes"}' backend/app/routers/invoices.py
    cd ~/sa && grep -c -x -F '    issuer_region' backend/app/routers/invoices.py
    cd ~/sa && grep -c -x -F '    subtotal = sum(item.quantity * item.unit_price for item in data.items)' backend/app/routers/invoices.py
    cd ~/sa && grep -c -x -F '    update_data = {k: v for k, v in update_data.items() if k in _UPDATABLE_COLUMNS}' backend/app/routers/invoices.py
    cd ~/sa && grep -c -x -F '    result = get_fx_rate(currency)' backend/app/routers/invoices.py
    cd ~/sa && grep -c -x -F '        "notes": row["notes"],' backend/app/routers/invoices.py
    cd ~/sa && grep -c -x -F 'async def get_issuer(db: AsyncSession, tenant_id: int, region: str) -> dict:' backend/app/services/issuer.py
    cd ~/sa && grep -c -x -F 'from pydantic import BaseModel, Field, field_validator' backend/app/schemas/invoice.py
    cd ~/sa && grep -c -x -F 'class InvoiceUpdate(BaseModel):' backend/app/schemas/invoice.py
    cd ~/sa && grep -c -x -F '    issuer_region: str | None = None' backend/app/schemas/invoice.py
    cd ~/sa && grep -c -x -F '        c.drawRightString(165 * mm, y, "Tax:")' backend/app/services/invoice_renderer.py
    cd ~/sa && grep -c -x -F '    # ── 7. 為替レート脚注（外貨時のみ）────────────────────────────────' backend/app/services/invoice_renderer.py
    cd ~/sa && grep -c -x -F '        paypal_copy=paypal_copy,' backend/app/services/invoice_renderer.py
    cd ~/sa && grep -c -x -F '    ("POST", "/api/v1/invoices"): _PENDING,' backend/app/realtime/topics.py
    cd ~/sa && grep -c -x -F '                issuer_region VARCHAR(20)' backend/tests/conftest.py
    cd ~/sa && grep -c -x "import pytest" backend/tests/conftest.py
    cd ~/sa && grep -c '"dutyRuleOverlap"' frontend/src/locales/ja.json frontend/src/locales/en.json | tail -2
    cd ~/sa && grep -c "tax_amount\|shipping_fee" backend/tests/test_invoices.py backend/tests/test_issuer.py backend/tests/test_paypal_invoicing.py backend/tests/test_company_stats.py backend/tests/test_products.py | tail -5
  期待（番号は上の命令の順番。1 本の命令が 2 行以上を出すものがあるので、出力の行の数ではなく命令の番号で見る）: 1番は 40 桁。2番 2。3番 6。4〜7番はどれも 1 以上。8番は2ファイルとも `:0`（2 行）。9番 0。10番 3。11番〜26番はどれも 1（ただし 17番 `        "notes": row["notes"],` が 2 以上なら、PDF の道 `download_invoice_pdf` の中のものを使い、数を報告に書いて続ける）。27番（`import pytest` の行そのもの。`import pytest_asyncio` は数えない）1。28番（dutyRuleOverlap・2 行）は数をそのまま書く（どちらも 0 なら §2-8 の (3)(4) で 6 つ足す。1 なら 5 つ）。29番（tax_amount・shipping_fee・5 行）は数をそのまま書く。

手順3 §2 の変更をする（2-1 から順に。新規の 6 ファイルは Write ツール、それ以外は Edit ツールで行う。2-12 の openapi.json は手順7 で作る）

手順4 道具を入れる（本番と同じ Python 3.12 の venv を作業場所の外 ~/venv312 に作る。素の pip は見張り py312-guard が止めるので使わない）
    cd ~ && python3.12 --version 2>&1 | tail -1
    cd ~ && python3.12 -m venv ~/venv312 2>&1 | tail -3
    cd ~ && ~/venv312/bin/python --version 2>&1 | tail -1
    cd ~/sa/backend && ~/venv312/bin/pip install -q -r requirements.txt 2>&1 | tail -3
    cd ~/sa/backend && ~/venv312/bin/pip install -q -r requirements-dev.txt 2>&1 | tail -3
    cd ~ && ~/venv312/bin/ruff --version | tail -1
  手順4 の python3.12 が無いときだけ、1行目と2行目の代わりに次を流す（それも失敗したら `BLOCKED: python3.12 なし`）。
    cd ~ && uv venv --python 3.12 ~/venv312 2>&1 | tail -3
    cd ~ && ~/venv312/bin/python -m ensurepip 2>&1 | tail -1

手順5 backend の形
    cd ~/sa && ~/venv312/bin/ruff check backend/app/services/invoice_totals.py backend/app/services/invoice_payment_methods.py backend/app/services/issuer.py backend/app/services/invoice_renderer.py backend/app/schemas/invoice.py backend/app/routers/invoices.py backend/app/realtime/topics.py 2>&1 | tail -10
    cd ~/sa && ~/venv312/bin/ruff check backend/tests/test_invoice_totals.py backend/tests/test_invoices_create_flow.py backend/tests/test_invoice_totals_pg.py backend/tests/test_invoice_pdf_payment.py backend/tests/conftest.py backend/tests/test_invoices.py backend/tests/test_issuer.py backend/tests/test_paypal_invoicing.py backend/tests/test_company_stats.py backend/tests/test_products.py backend/tests/test_api_error_reason_sync.py 2>&1 | tail -10
    cd ~/sa && grep -c "get_fx_rate" backend/app/routers/invoices.py
    cd ~/sa && grep -c "_calc_currency_amounts" backend/app/routers/invoices.py
    cd ~/sa && grep -c "/api/v1/invoices/preview" backend/app/realtime/topics.py
    cd ~/sa && grep -n '"/invoices/draft-context"\|"/invoices/{invoice_id}",' backend/app/routers/invoices.py | head -3
  期待: ruff は2本とも `All checks passed!`／3行目 0／4行目 0／5行目 1／6行目は draft-context の行番号が `"/invoices/{invoice_id}",` の行番号より小さい。

手順6 backend の試験（実 PostgreSQL の試験は CI だけで動く。ここでは skip と出てよい。failed と error は 0 であること）
    cd ~/sa/backend && ~/venv312/bin/python -m pytest -q -p no:cacheprovider tests/test_invoice_totals.py tests/test_invoice_pdf_payment.py tests/test_invoice_totals_pg.py 2>&1 | tail -15
    cd ~/sa/backend && ~/venv312/bin/python -m pytest -q -p no:cacheprovider tests/test_invoices_create_flow.py tests/test_invoices.py 2>&1 | tail -15
    cd ~/sa/backend && ~/venv312/bin/python -m pytest -q -p no:cacheprovider tests/test_issuer.py tests/test_paypal_invoicing.py tests/test_company_stats.py tests/test_products.py tests/test_api_error_reason_sync.py tests/test_realtime_topics.py 2>&1 | tail -15
  期待: 1本目は `25 passed`（計算 21・PDF 4）と `1 skipped`（PG の1本）。2本目・3本目は failed 0・error 0（本数はそのまま書く）。

手順7 API の形を書き出す
    cd ~/sa/backend && ENVIRONMENT=test ~/venv312/bin/python -m tools.export_openapi ../frontend/api-contract/openapi.json 2>&1 | tail -5
    cd ~/sa && grep -c '"/api/v1/invoices/draft-context"\|"/api/v1/invoices/preview"' frontend/api-contract/openapi.json
    cd ~/sa && git diff --numstat frontend/api-contract/openapi.json | tail -1
  期待: 1行目は何も出ない（exit 0）。2行目 2。3行目は足した行が 0 より大きい（数は Opus が見る）。

手順8 画面の言葉の点検（tsc はこのコミットでは流さない。便 D の後に流す）
    cd ~/sa/frontend && npm ci 2>&1 | tail -3
    cd ~/sa/frontend && npm run check:all 2>&1 | tail -30
    cd ~/sa/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/lib/apiErrorReason.test.ts 2>&1 | tail -20
  期待: check:all は最後まで通り、失敗の行が無い（終了 0）。vitest は 1 ファイル passed で failed 0。

手順9 変えたファイルの名前と数
    cd ~/sa && git status --short | tail -40
    cd ~/sa && git diff --stat | tail -25
  期待: §1 のファイルだけ（新規の 6 ファイルは `??` で各1行。既存は 17 ファイル）。

手順10 記録と送り出し（便 C のコミット。push は便 D の後に Opus の指示で行うので、ここでは push しない）
    cd ~/sa && git add backend/app/services/invoice_totals.py backend/app/services/invoice_payment_methods.py backend/app/services/issuer.py backend/app/services/invoice_renderer.py backend/app/schemas/invoice.py backend/app/routers/invoices.py backend/app/realtime/topics.py && git status --short | tail -40
    cd ~/sa && git add backend/tests/test_invoice_totals.py backend/tests/test_invoices_create_flow.py backend/tests/test_invoice_totals_pg.py backend/tests/test_invoice_pdf_payment.py backend/tests/conftest.py backend/tests/test_invoices.py && git status --short | tail -40
    cd ~/sa && git add backend/tests/test_issuer.py backend/tests/test_paypal_invoicing.py backend/tests/test_company_stats.py backend/tests/test_products.py backend/tests/test_api_error_reason_sync.py && git status --short | tail -40
    cd ~/sa && git add frontend/src/lib/apiErrorReason.ts frontend/src/lib/apiErrorReason.test.ts frontend/src/locales/ja.json frontend/src/locales/en.json frontend/api-contract/openapi.json && git status --short | tail -40
    cd ~/sa && git config user.name "shingo-cc" && git config user.email "shingo-cc@users.noreply.github.com" && git commit -q -m "feat(invoices): compute invoice totals on the server and print payment destination on PDF (invoice-create-portfolio bin C)" && git log --oneline -1 | tail -1
    cd ~/sa && git branch --show-current | tail -1
  最後の `git add` の後の status に §1 に無いファイルが出たら、commit せずに `BLOCKED: 範囲外のファイル` で停止する。`git branch --show-current` が `release/invoice-create-portfolio-bin-cd` でなければ `BLOCKED: 枝の名前` で停止する。続けて card-D.md の手順へ進む（同じ実行の中で。card-D.md の手順1 は枝を取り直さない）。

## 4. 想定される分かれ道

- 停止する（その場で作業を停止し、それまでの出力と §5 の報告を返して終わる。別のやり方を試さない）:
  - 手順1 の is-ancestor が 0 でない・P1〜P8 のどれかが外れた → `BLOCKED: 手順1` か `BLOCKED: P番号`。
  - §2 の変更前の文が見つからない・2 か所ある（手順2 の注記のものと、冒頭「基準」の行の `invoice_id = inv_result.scalar_one()` を除く） → `BLOCKED: ファイル名 変更前の文`。
  - apiErrorReason.ts の一覧の形が §2-8 (1) の想定と違い、同じ形で足す方法が 1 つに決まらない → `BLOCKED: apiErrorReason の形`。
  - SQLite の contacts に surname・given_name・primary_email の列が無く、draft-context の道が SQLite の試験の import で落ちる → 出力を貼って `BLOCKED: contacts の列`（道の SQL は変えない）。
  - 手順5 の数・手順7 の数の期待が外れた → 出力を貼って `BLOCKED: 手順5` か `BLOCKED: 手順7`。
  - 手順6 で failed か error が 1 件でも出た → 試験を直さず最後の 15 行を貼って `BLOCKED: pytest`。ただしカードからの書き写し間違い（字・字下げ）か、§2-10 の「額を確かめている行」の値の合わせ（式は §2-11 F7・送料 0・US 宛で税 0）が出力から分かるときだけ直してよい。直したら何をどう直したかを書く。
  - 手順8 の check:all・vitest のどれかが失敗した → 直さず最後の行を貼って `BLOCKED: 手順8 check:all` か `BLOCKED: 手順8 vitest`。書き写し間違いの扱いは手順6 と同じ。
- 記録して続ける（値を報告に書き、判定は Opus がする）:
  - ruff が I（並び順）だけを出した → `~/venv312/bin/ruff check --fix --select I` を同じファイルに流して、その結果を書く。I 以外を出したら `BLOCKED: ruff`。
  - ruff が E501（行が長い）だけを出した → 直さずにそのまま書く。
  - 手順6 で skipped が出る → そのまま書く。
  - npm ci や vitest が警告（warn）を出す → そのまま書く。

## 5. 報告の形

- 宛先: 完了報告の本文（クラウドの実行の最後の返事）。ファイルに書かない。
- 1 行目: `RECEIVED invoice-create-portfolio-C HEAD=…`。2 行目: 「本報告はカード 便C 請求書の額をサーバーで計算し、振込先と税率を PDF に出す の実行結果である」。便 D を続けて流したときは、便 D の報告をこの後ろに続ける（card-D.md §5）。
- 手順1・2・4・5・6・7・8・9・10 の出力（tail の範囲）をそのまま貼る。要約しない。
- 停止したときは「停止した手順番号／最後に実行したコマンド／停止した理由」の 3 点。
- 秘密の値・鍵・パスワードは貼らない。
- 最後の行: `DONE` か `BLOCKED: 理由`（便 D まで流したときは card-D.md の最後の行が全体の最後）。

## 6. 委任の定型

- sleep しない。待ちが要るものは Opus が見る（CI の結果など）。
- ファイルの編集は Edit ツールで行う（新規の 6 ファイルだけ Write ツール）。ヒアドキュメントで書かない。
- PR は作らない（Opus が作り、`scripts/dev/validate-pr-body.sh` で確かめる）。
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える。

END OF CARD
