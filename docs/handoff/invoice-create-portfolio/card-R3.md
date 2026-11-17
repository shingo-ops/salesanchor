# card-R3: 請求書の送料の一覧を返す道を足す（invoice-create-portfolio 便 R3）

作成: Opus（Planner）2026-11-17。設計: docs/handoff/invoice-create-portfolio/design-v2.md 第6版 §3-5・§4 R3・K6・K7（設計審査 5回目 APPROVE）。
実装承認: PO は 2026-11-17 に p1〜p8 を「見本どおり」と決め、PR マージ・デプロイまでの完走を委ねた（ccopusgo の委任の範囲）。
枝: release/invoice-portfolio-r3-shipping（origin/main から。便 R2 のマージの後に作る）。移行（migrations/）なし・deploy.yml なし・scripts/ なし。
# rules-ack: d5738ef7

## 受領確認（最初の報告の 1 行目に書く）

`RECEIVED invoice-portfolio-R3 HEAD=` に続けて、手順1 の後の `git rev-parse HEAD` の 40 桁を書く。

## 0. Opus の決めごと（根拠つき）

- D1 道は `POST /invoices/draft-shipping-quotes`。権限は `require_permission("invoices.create")`（design-v2 §3-5）。読むだけで書かない。見積の作成画面（frontend/src/pages/quote-create）は送料を使わない（`git grep "shipping/calculate" origin/main -- frontend/src` は FedExRateModal.tsx:137 の1件だけ）ので、見積の権限は足さない。登録は preview の直後・`GET /invoices/{invoice_id}` の前に置く。
- D2 入力は company_id と総重量（weight_kg）だけ。届け先の国・郵便番号と発送元の国は、サーバーが draft-context と同じ関数で決める: `_fetch_address_snapshot`（delivery・billing）→ `invoice_totals.destination_country`・`invoice_totals.destination_postal_code`（backend/app/services/invoice_totals.py:174-187）→ `decide_issuer_region(bill_to)` → `get_issuer_country_code`（backend/app/services/issuer.py:20-27・44-54）。draft-context の新規の作成と同じ順（backend/app/routers/invoices.py:338-345・362-364）。
- D3 FedEx の分岐を1つの関数 `fedex_live_quotes` にまとめる（backend/app/routers/shipping.py の `_try_fedex_live` の直後）。中身は今の calc_shipping の 415-437 行（連携の鍵を読む→あればライブ→無ければ未連携の文）と同じ。calc_shipping と新しい道の両方から呼ぶ。未連携の文は定数 `FEDEX_NOT_CONNECTED_MESSAGE` にして1か所に置く（文字は今と1字も変えない）。今の `/shipping/calculate` の 422（発送元の国が無いとき）と応答の形は変えない。backend/tests/test_fedex_rates.py は変えずに緑のまま。
- D4 静的な表の行は `calculate_shipping_fee(db, 届け先, 重さ)`（carrier なし）から、便の名前が fedex の行を除く。便の名前は送料の表の登録画面から自由に入る（shipping.py:108-117）ので、大文字小文字を区別せず `r.carrier.lower() != "fedex"` で除く。FedEx の行はライブだけ（ADR-125 D4・D5・PO の C1 判断・design-v2 §3-5・K6）。
- D5 発送元の国が無い（発行元の行に国が無い）ときは FedEx を呼ばない。連携の鍵も読まない。静的な行と live_error「発送元の国が未登録です。発行元の設定で国を登録してください」を返す（暗黙に JP を使わない。issuer.py:45 と同じ決まり）。
- D6 届け先の国が無い（発送先・請求先の写しのどちらにも国が無い）ときは 422 `draft_shipping_destination`。会社が無いときは 404 `not_found:company`（draft-context・preview と同じ符号）。失敗の detail は識別子の形（ADR-1071 W1。backend/tests/test_error_detail_guard.py）。
- D7 応答は `ShippingCalcResponse`（backend/app/schemas/shipping.py:123-134）。results はライブの行が先・静的な行が後。`cheapest` は None（便ごとに通貨が違い、1つに決められない。選ぶのは画面の人）。rate_precision はライブの値をそのまま。各行の `source`（fedex_live か static）が出所の印（ADR-125 D6）。
- D8 試験は新しいファイル backend/tests/test_invoice_draft_shipping.py。DB を使わず、test_fedex_rates.py:470-500 と同じく道の関数を直接呼び、DB と外の呼び出しは置き換える。

本番の事実（2026-11-17 20:55 JST に本番の読む道 ADR-1024 で数えた。生の出力は /tmp/CC報告ファイル/r3/carrier_creds.txt・zones_carriers.txt）:
- FedEx の連携は会社 004 と 006 にある（006 は DHL も）。001・003・005 は無い。
- 送料の静的な表（shipping_zones・shipping_rates）は全5社とも0行。今の本番では静的な行は出ず、FedEx の行だけが出る（004・006）か、未連携の文だけが出る（001・003・005）。

## 0-1. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・commit は git log で確かめる | ○（§3） |
| guards/03-file.md | 編集は Edit ツール。新しいファイルは Write ツール。プレースホルダを残さない | ○（§2） |
| guards/04-worktree.md | new-worktree.sh で作る・出力をパイプに通さない・実在は git worktree list で確かめる・push は -u 付き | ○（手順1・手順8） |
| guards/10-executor.md | 散文で頼まない。手順はコマンドで書く | ○（§3） |

## 0-2. 実装前点検（手順2 で流す。外れたら実装せず停止して BLOCKED: で報告）

- P1 `    return results, None, precision` が backend/app/routers/shipping.py に 1。
- P2 `        creds = await carrier_credentials.get_credentials(db, tenant_id, "fedex")` が shipping.py に 1（ほかの道の行は字下げが4つで別の文）。
- P3 `FedEx が未連携です。キャリア連携設定でアカウントを接続してください` が shipping.py に 1。
- P4 `draft-shipping-quotes` が backend/app/routers/invoices.py に 0。
- P5 `        total_amount=result.total_amount, uncomputed=result.uncomputed, incoterms=inputs.incoterms,` が invoices.py に 1。
- P6 `from app.models import User` が invoices.py に 1。
- P7 `from app.services import invoice_payment_methods, invoice_totals, paypal_payments` が invoices.py に 1。
- P8 `    payment_method_type: str | None = None` が backend/app/schemas/invoice.py に 1。
- P9 `draft-inventory` が invoices.py に 1 以上（便 R2 が main に入っている印。0 なら `BLOCKED: P9 R2 未合流`）。

## 1. 触るファイル

- backend/app/routers/shipping.py（2-1）
- backend/app/schemas/invoice.py（2-2）
- backend/app/routers/invoices.py（2-3）
- backend/tests/test_invoice_draft_shipping.py（2-4・新規）
- frontend/api-contract/openapi.json（手順6 で作る）

## 2. 変更

### 2-1. routers/shipping.py

(1) 変更前:
```
    return results, None, precision


@router.post(
    "/shipping/calculate",
```
変更後:
```
    return results, None, precision


# ADR-125 D5 + PO C1判断: FedEx 未連携のときの文（calc_shipping と請求書の送料一覧で同じ文を使う）
FEDEX_NOT_CONNECTED_MESSAGE = "FedEx が未連携です。キャリア連携設定でアカウントを接続してください"


async def fedex_live_quotes(
    db: AsyncSession,
    tenant_id: int,
    *,
    destination_country_code: str,
    origin_country_code: str,
    weight_kg: Decimal,
    origin_postal_code: Optional[str] = None,
    destination_postal_code: Optional[str] = None,
) -> tuple[list[ShippingCalcResult], Optional[str], Optional[str]]:
    """FedEx のライブ見積もり（ADR-125 D5）。(results, live_error, rate_precision) を返す。

    未連携なら静的な表に落とさず、行0件と未連携の文を返す。
    calc_shipping と請求書の送料一覧（invoice-create-portfolio R3・design-v2 §3-5）の両方から呼ぶ。
    """
    creds = await carrier_credentials.get_credentials(db, tenant_id, "fedex")
    if not creds:
        return [], FEDEX_NOT_CONNECTED_MESSAGE, None
    return await _try_fedex_live(
        creds=creds,
        tenant_id=tenant_id,
        destination_country_code=destination_country_code,
        origin_country_code=origin_country_code,
        weight_kg=weight_kg,
        origin_postal_code=origin_postal_code,
        destination_postal_code=destination_postal_code,
    )


@router.post(
    "/shipping/calculate",
```
(2) 変更前:
```
        creds = await carrier_credentials.get_credentials(db, tenant_id, "fedex")
        if creds:
            live_results, live_error, rate_precision = await _try_fedex_live(
                creds=creds,
                tenant_id=tenant_id,
                destination_country_code=data.country_code,
                origin_country_code=data.origin_country_code,
                weight_kg=data.weight_kg,
                origin_postal_code=data.origin_postal_code,
                destination_postal_code=data.destination_postal_code,
            )
            return ShippingCalcResponse(
                results=live_results,
                cheapest=live_results[0] if live_results else None,
                live_error=live_error,
                rate_precision=rate_precision,
            )
        # FedEx 未連携 → static に落とさず未連携状態を明示返却（ADR-125 D5 + PO C1判断）
        # 静的早見表は他キャリア（DHL/ヤマト等）専用として維持する（ADR-125 D4）
        return ShippingCalcResponse(
            results=[],
            cheapest=None,
            live_error="FedEx が未連携です。キャリア連携設定でアカウントを接続してください",
        )
```
変更後:
```
        # FedEx 未連携 → static に落とさず未連携状態を明示返却（ADR-125 D5 + PO C1判断。fedex_live_quotes の中）
        # 静的早見表は他キャリア（DHL/ヤマト等）専用として維持する（ADR-125 D4）
        live_results, live_error, rate_precision = await fedex_live_quotes(
            db,
            tenant_id,
            destination_country_code=data.country_code,
            origin_country_code=data.origin_country_code,
            weight_kg=data.weight_kg,
            origin_postal_code=data.origin_postal_code,
            destination_postal_code=data.destination_postal_code,
        )
        return ShippingCalcResponse(
            results=live_results,
            cheapest=live_results[0] if live_results else None,
            live_error=live_error,
            rate_precision=rate_precision,
        )
```
（未連携のときの応答は、前も後も results=[]・cheapest=None・live_error=未連携の文・rate_precision=None で同じ。）

### 2-2. schemas/invoice.py（ファイルの末尾）

変更前:
```
    payment_method_type: str | None = None
```
変更後:
```
    payment_method_type: str | None = None


# invoice-create-portfolio R3（design-v2 §3-5）: 請求書の送料の一覧の入力。届け先・発送元はサーバーが決める。
class DraftShippingQuotesRequest(BaseModel):
    company_id: int = Field(ge=1)
    weight_kg: Decimal = Field(gt=0, max_digits=10, decimal_places=3)
```
（weight_kg の決まりは今の ShippingCalcRequest.weight_kg（backend/app/schemas/shipping.py:75）と同じ。）

### 2-3. routers/invoices.py

(1) 変更前:
```
from app.models import User
```
変更後:
```
from app.models import User
from app.routers.shipping import calculate_shipping_fee, fedex_live_quotes
```
(2) 変更前:
```
    DraftContextResponse,
    InvoiceCreate,
```
変更後:
```
    DraftContextResponse,
    DraftShippingQuotesRequest,
    InvoiceCreate,
```
(3) 変更前:
```
from app.services import invoice_payment_methods, invoice_totals, paypal_payments
```
変更後:
```
from app.schemas.shipping import ShippingCalcResponse
from app.services import invoice_payment_methods, invoice_totals, paypal_payments
```
(4) 変更前:
```
        total_amount=result.total_amount, uncomputed=result.uncomputed, incoterms=inputs.incoterms,
    )
```
変更後:
```
        total_amount=result.total_amount, uncomputed=result.uncomputed, incoterms=inputs.incoterms,
    )


@router.post(
    "/invoices/draft-shipping-quotes",
    response_model=ShippingCalcResponse,
    dependencies=[Depends(require_permission("invoices.create"))],
)
async def get_invoice_draft_shipping_quotes(
    data: DraftShippingQuotesRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),  # noqa: ARG001
) -> ShippingCalcResponse:
    """請求書の送料の一覧（invoice-create-portfolio R3・design-v2 §3-5）。書かない。

    届け先と発送元は draft-context と同じ関数で決める。FedEx の行はライブだけ（ADR-125 D4・D5）。
    """
    co = await db.execute(text("SELECT id FROM companies WHERE id = :id"), {"id": data.company_id})
    if co.first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found:company")
    ship_to = await _fetch_address_snapshot(db, data.company_id, "delivery")
    bill_to = await _fetch_address_snapshot(db, data.company_id, "billing")
    destination = invoice_totals.destination_country(ship_to, bill_to)
    if destination is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="draft_shipping_destination")
    static_rows = [
        r for r in await calculate_shipping_fee(db, destination, data.weight_kg) if r.carrier.lower() != "fedex"
    ]
    origin = await get_issuer_country_code(db, tenant_id, decide_issuer_region(bill_to))
    if origin is None:
        return ShippingCalcResponse(
            results=static_rows,
            cheapest=None,
            live_error="発送元の国が未登録です。発行元の設定で国を登録してください",
        )
    live_rows, live_error, rate_precision = await fedex_live_quotes(
        db,
        tenant_id,
        destination_country_code=destination,
        origin_country_code=origin,
        weight_kg=data.weight_kg,
        destination_postal_code=invoice_totals.destination_postal_code(ship_to, bill_to),
    )
    return ShippingCalcResponse(
        results=[*live_rows, *static_rows],
        cheapest=None,
        live_error=live_error,
        rate_precision=rate_precision,
    )
```

### 2-4. backend/tests/test_invoice_draft_shipping.py（新規。Write ツールで作る）

```
"""請求書の送料の一覧の道（invoice-create-portfolio R3・design-v2 §3-5・K6）。

DB は使わない。道の関数を直接呼び、DB・住所の写し・発行元の国・静的な表・FedEx を置き換える
（backend/tests/test_fedex_rates.py の TestShippingCalculateEndpoint と同じやり方）。
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.routers.invoices import get_invoice_draft_shipping_quotes
from app.routers.shipping import FEDEX_NOT_CONNECTED_MESSAGE
from app.schemas.invoice import DraftShippingQuotesRequest
from app.schemas.shipping import ShippingCalcResult

SHIP_TO = {"country": "US", "postal_code": "10001"}
BILL_TO = {"country": "US", "postal_code": "94105"}


def _row(carrier: str, source: str = "static", fee: str = "1000") -> ShippingCalcResult:
    return ShippingCalcResult(carrier=carrier, zone="Z1", fee=Decimal(fee), currency="JPY", source=source)


STATIC_ROWS = [_row("FedEx"), _row("fedex"), _row("DHL"), _row("UPS")]


def _db(company_exists: bool = True) -> AsyncMock:
    res = MagicMock()
    res.first.return_value = (5,) if company_exists else None
    db = AsyncMock()
    db.execute = AsyncMock(return_value=res)
    return db


async def _call(db, *, snapshots=(SHIP_TO, BILL_TO), origin="JP", creds=None, live=None):
    """道を呼ぶ。live は _try_fedex_live の戻り値（None なら呼ばれない想定）。"""
    snap = AsyncMock(side_effect=list(snapshots))
    try_live = AsyncMock(return_value=live)
    get_creds = AsyncMock(return_value=creds)
    with patch("app.routers.invoices._fetch_address_snapshot", snap), \
         patch("app.routers.invoices.get_issuer_country_code", AsyncMock(return_value=origin)), \
         patch("app.routers.invoices.calculate_shipping_fee", AsyncMock(return_value=list(STATIC_ROWS))) as calc, \
         patch("app.services.carrier_credentials.get_credentials", get_creds), \
         patch("app.routers.shipping._try_fedex_live", try_live):
        resp = await get_invoice_draft_shipping_quotes(
            data=DraftShippingQuotesRequest(company_id=5, weight_kg=Decimal("2.5")),
            db=db,
            tenant_id=1,
            current_user=MagicMock(),
        )
    return resp, calc, get_creds, try_live


def _carriers(resp, source: str) -> list[str]:
    return [r.carrier.lower() for r in resp.results if r.source == source]


@pytest.mark.asyncio
async def test_k6_live_ok_fedex_live_only_and_others_static():
    """K6: 連携あり・ライブ成功 → FedEx はライブの行だけ・静的な FedEx は0件・DHL と UPS は静的。"""
    live_row = _row("fedex", source="fedex_live", fee="3200")
    resp, calc, _, try_live = await _call(_db(), creds={"client_id": "x"}, live=([live_row], None, "exact"))
    assert _carriers(resp, "fedex_live") == ["fedex"]
    assert "fedex" not in _carriers(resp, "static")
    assert sorted(_carriers(resp, "static")) == ["dhl", "ups"]
    assert resp.results[0].source == "fedex_live"
    assert resp.live_error is None
    assert resp.rate_precision == "exact"
    assert resp.cheapest is None
    calc.assert_awaited_once()
    assert calc.await_args.args[1] == "US"
    kw = try_live.await_args.kwargs
    assert kw["destination_country_code"] == "US"
    assert kw["origin_country_code"] == "JP"
    assert kw["destination_postal_code"] == "10001"
    assert kw["weight_kg"] == Decimal("2.5")


@pytest.mark.asyncio
async def test_k6_not_connected_no_fedex_rows_and_message():
    """K6: 未連携 → FedEx の行は0件（静的もライブも）・未連携の文・DHL と UPS は静的。"""
    resp, _, _, try_live = await _call(_db(), creds=None)
    assert all(r.carrier.lower() != "fedex" for r in resp.results)
    assert sorted(_carriers(resp, "static")) == ["dhl", "ups"]
    assert resp.live_error == FEDEX_NOT_CONNECTED_MESSAGE
    try_live.assert_not_awaited()


@pytest.mark.asyncio
async def test_k6_live_failure_no_fedex_rows_and_error():
    """K6: ライブ失敗 → FedEx の行は0件・live_error あり・DHL と UPS は静的。"""
    resp, _, _, _ = await _call(_db(), creds={"client_id": "x"}, live=([], "タイムアウト", None))
    assert all(r.carrier.lower() != "fedex" for r in resp.results)
    assert sorted(_carriers(resp, "static")) == ["dhl", "ups"]
    assert resp.live_error == "タイムアウト"


@pytest.mark.asyncio
async def test_no_origin_does_not_call_fedex():
    """発送元の国が無い → 連携の鍵を読まず FedEx を呼ばない・静的な行と文を返す（暗黙に JP を使わない）。"""
    resp, _, get_creds, try_live = await _call(_db(), origin=None, creds={"client_id": "x"})
    assert sorted(_carriers(resp, "static")) == ["dhl", "ups"]
    assert resp.live_error is not None and "発送元" in resp.live_error
    get_creds.assert_not_awaited()
    try_live.assert_not_awaited()


@pytest.mark.asyncio
async def test_destination_from_bill_to_when_no_ship_to():
    """発送先の写しが無い → 請求先の国と郵便番号を使う（draft-context と同じ関数）。"""
    live_row = _row("fedex", source="fedex_live")
    _, calc, _, try_live = await _call(
        _db(), snapshots=(None, BILL_TO), creds={"client_id": "x"}, live=([live_row], None, "exact"),
    )
    assert calc.await_args.args[1] == "US"
    assert try_live.await_args.kwargs["destination_postal_code"] == "94105"


@pytest.mark.asyncio
async def test_no_destination_is_422():
    with pytest.raises(HTTPException) as exc:
        await _call(_db(), snapshots=(None, None))
    assert exc.value.status_code == 422
    assert exc.value.detail == "draft_shipping_destination"


@pytest.mark.asyncio
async def test_unknown_company_is_404():
    with pytest.raises(HTTPException) as exc:
        await _call(_db(company_exists=False))
    assert exc.value.status_code == 404
    assert exc.value.detail == "not_found:company"


@pytest.mark.asyncio
async def test_calc_shipping_not_connected_unchanged():
    """今の /shipping/calculate の未連携の応答が前と同じ（D3）。"""
    from app.routers.shipping import calc_shipping
    from app.schemas.shipping import ShippingCalcRequest

    with patch("app.services.carrier_credentials.get_credentials", AsyncMock(return_value=None)):
        resp = await calc_shipping(
            data=ShippingCalcRequest(country_code="US", weight_kg=Decimal("1.0"), carrier="fedex", origin_country_code="JP"),
            db=AsyncMock(),
            tenant_id=1,
            current_user=MagicMock(),
        )
    assert resp.model_dump() == {
        "results": [],
        "cheapest": None,
        "live_error": "FedEx が未連携です。キャリア連携設定でアカウントを接続してください",
        "rate_precision": None,
    }
```

## 3. 手順

手順1 作業場所を公式の台本で作る（ホームに clone した別の場所は使わない）。1 つずつ流し、出力を報告に書く。リポジトリの場所が `/home/user/salesanchor` でないときは、実際の場所に読み替えて同じ命令を流し、読み替えたことを書く。
    cd /home/user/salesanchor && git fetch origin main
    cd /home/user/salesanchor && git branch --list release/invoice-portfolio-r3-shipping
    cd /home/user/salesanchor && bash scripts/new-worktree.sh release/invoice-portfolio-r3-shipping
    cd /home/user/salesanchor && git worktree list
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r3-shipping && git merge-base --is-ancestor origin/main HEAD; echo "is-ancestor exit=$?"
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r3-shipping && git rev-parse HEAD
  期待: 2行目の出力が空（空でなければ `BLOCKED: 手順1 枝が既にある`）。4行目に `worktrees/salesanchor/release-invoice-portfolio-r3-shipping` が出る（出なければ `BLOCKED: 手順1 作業場所`）。5行目 `is-ancestor exit=0`。台本が作る .claude-pipeline/active-work.d/ の未追跡ファイルは add しない。

手順2 実装前点検 P1〜P9
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r3-shipping && grep -c "    return results, None, precision" backend/app/routers/shipping.py
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r3-shipping && grep -c '^        creds = await carrier_credentials.get_credentials(db, tenant_id, "fedex")$' backend/app/routers/shipping.py
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r3-shipping && grep -c "FedEx が未連携です。キャリア連携設定でアカウントを接続してください" backend/app/routers/shipping.py
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r3-shipping && grep -c "draft-shipping-quotes" backend/app/routers/invoices.py
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r3-shipping && grep -c "        total_amount=result.total_amount, uncomputed=result.uncomputed, incoterms=inputs.incoterms," backend/app/routers/invoices.py
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r3-shipping && grep -c "^from app.models import User$" backend/app/routers/invoices.py
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r3-shipping && grep -c "^from app.services import invoice_payment_methods, invoice_totals, paypal_payments$" backend/app/routers/invoices.py
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r3-shipping && grep -c "^    payment_method_type: str | None = None$" backend/app/schemas/invoice.py
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r3-shipping && grep -c "draft-inventory" backend/app/routers/invoices.py
  期待（命令の順）: 1、1、1、0、1、1、1、1、1以上。

手順3 §2 の変更をする（2-1 から順に。2-1〜2-3 は Edit ツール、2-4 は Write ツール）

手順4 道具を入れる（作業場所の外 ~/venv312。素の pip は見張りが止めるので使わない）
    cd ~ && python3.12 -m venv ~/venv312 2>&1 | tail -3
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r3-shipping/backend && ~/venv312/bin/pip install -q -r requirements.txt 2>&1 | tail -3
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r3-shipping/backend && ~/venv312/bin/pip install -q -r requirements-dev.txt 2>&1 | tail -3
  python3.12 が無いときだけ 1行目の代わりに `cd ~ && uv venv --python 3.12 ~/venv312` と `cd ~ && ~/venv312/bin/python -m ensurepip` を流す（それも失敗したら `BLOCKED: python3.12 なし`）。

手順5 形と試験
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r3-shipping && ~/venv312/bin/ruff check backend/app/routers/shipping.py backend/app/schemas/invoice.py backend/app/routers/invoices.py backend/tests/test_invoice_draft_shipping.py 2>&1 | tail -10
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r3-shipping/backend && ~/venv312/bin/python -m pytest -q -p no:cacheprovider tests/test_invoice_draft_shipping.py tests/test_fedex_rates.py 2>&1 | tail -15
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r3-shipping/backend && ~/venv312/bin/python -m pytest -q -p no:cacheprovider tests/test_invoices.py tests/test_error_detail_guard.py 2>&1 | tail -15
  期待: ruff `All checks passed!`。2行目は failed 0・error 0（test_invoice_draft_shipping.py の 8 本が passed に入る。本数はそのまま書く）。3行目は failed 0・error 0。

手順6 API の形を書き出し、今の送料の道が変わっていないことを比べる
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r3-shipping/backend && ENVIRONMENT=test ~/venv312/bin/python -m tools.export_openapi ../frontend/api-contract/openapi.json 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r3-shipping && git diff --numstat frontend/api-contract/openapi.json | tail -1
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r3-shipping && grep -c '"/api/v1/invoices/draft-shipping-quotes"' frontend/api-contract/openapi.json
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r3-shipping && git show origin/main:frontend/api-contract/openapi.json > ~/oa-main.json && ~/venv312/bin/python -c "import json,os; a=json.load(open(os.path.expanduser('~/oa-main.json'))); b=json.load(open('frontend/api-contract/openapi.json')); p='/api/v1/shipping/calculate'; ks=['ShippingCalcRequest','ShippingCalcResult','ShippingCalcResponse']; print('calc path same:', a['paths'][p]==b['paths'][p]); print('calc schemas same:', all(a['components']['schemas'][k]==b['components']['schemas'][k] for k in ks))"
  期待: 1行目は何も出ない。2行目は足した行が 0 より大きい。3行目 1。4行目 `calc path same: True` と `calc schemas same: True`。

手順7 変えたファイル
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r3-shipping && git status --short | tail -20
  期待: §1 の 5 ファイルだけ（.claude-pipeline/active-work.d/ の未追跡は除く）。ほかが出たら `BLOCKED: 範囲外のファイル`。

手順8 記録と送り出し
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r3-shipping && git add backend/app/routers/shipping.py backend/app/schemas/invoice.py backend/app/routers/invoices.py backend/tests/test_invoice_draft_shipping.py frontend/api-contract/openapi.json && git status --short | tail -20
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r3-shipping && git config user.name "shingo-cc" && git config user.email "shingo-cc@users.noreply.github.com" && git commit -q -m "feat(invoices): add draft-shipping-quotes route listing static rates without FedEx plus FedEx live quotes (invoice-portfolio R3)" && git log --oneline -1 | tail -1
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r3-shipping && git push -u origin release/invoice-portfolio-r3-shipping 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r3-shipping && git rev-parse HEAD
  push は --no-verify・force を付けない。push が止められたら言い換えず `BLOCKED: push`。

## 4. 想定される分かれ道

- 停止する（その場で停止し、それまでの出力と §5 の報告を返して終わる。別のやり方を試さない）:
  - P1〜P9 のどれかが外れた → `BLOCKED: P番号`。
  - §2 の変更前の文が見つからない・2 か所以上当たる → `BLOCKED: ファイル名 変更前の文`。
  - 手順5 で failed か error が出た → 試験を直さず最後の 15 行を貼って `BLOCKED: pytest`。カードからの書き写し間違い（字・字下げ）が出力から分かるときだけ直してよい。直したら何をどう直したかを書く。
  - 手順5 で import の循環（ImportError・circular import）が出た → 直さず `BLOCKED: import 循環`。
  - 手順6 の 4行目が True でない・KeyError が出た → 直さず `BLOCKED: 今の送料の道の形が変わる`。
  - 手順6 のほかの期待が外れた → `BLOCKED: 手順6`。
  - test_error_detail_guard.py が落ちた → `BLOCKED: 失敗の文の見張り`。
- 記録して続ける: ruff が I（並び順）だけを出した → `~/venv312/bin/ruff check --fix --select I` を同じファイルに流して結果を書く。I 以外なら `BLOCKED: ruff`。skipped・警告はそのまま書く。

## 5. 報告の形

- 宛先: クラウドの実行の最後の返事。ファイルに書かない。
- 1 行目: 受領確認の行。2 行目: 「本報告はカード 便R3 請求書の送料の一覧を返す道を足す の実行結果である」。
- 手順1・2・5・6・7・8 の出力をそのまま貼る（要約しない）。全体で 1500 字を超えるときは、手順5・手順6・手順8 を優先して貼り、ほかは期待と合ったかを ○× で書く。
- 停止したときは「停止した手順番号／最後に実行したコマンド／停止した理由」の 3 点。
- 秘密の値・鍵・パスワードは貼らない。
- 最後の行: `DONE` か `BLOCKED: 理由`。

## 6. 委任の定型

- sleep しない。CI の結果は Opus が見る。PR は作らない（Opus が作る）。
- ファイルの編集は Edit ツール、新しいファイルは Write ツール。ヒアドキュメントで書かない。
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える。

## 7. 触らない範囲

§1 以外のファイル。shipping.py の `calculate_shipping_fee`・`_try_fedex_live` の中身、calc_shipping の 422 の分岐と非 FedEx の分岐、ほかの道（ラベル・集荷・連携の確かめ）。invoices.py の draft-context・draft-inventory・preview の中身。backend/tests/test_fedex_rates.py（変えない）。migrations/・deploy.yml・scripts/・frontend の画面（便 R5）。

END OF CARD
