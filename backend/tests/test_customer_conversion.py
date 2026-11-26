"""「既存顧客」は 3 つの条件がそろったときだけ自動で付く（ADR-1090）の試験。

3 つ: ① その人の会社に既定の請求先がある ② その人の会社がある ③ その会社に支払い済みの記録がある
（請求書の入金登録・注文の「支払済にする」）。
"""
from __future__ import annotations

import itertools
import re
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import text

from tests.conftest import _make_noop_audit_log
from tests.helpers_txn import create_company, create_lead

BILLING = [{"address_type": "billing", "country_code": "US", "is_default": True}]
CONVERT_BODY = {"company_id": 1, "contact_id": 1, "title": "商談"}

# 請求書の作成が読む public の表が試験の SQLite に無いので、合計の材料を差し替える
pytestmark = pytest.mark.usefixtures("stub_invoice_totals")


@pytest.fixture(autouse=True)
def _sqlite_audit_for_service():
    """試験の SQLite では tenant_NNN.audit_logs が無いので、判定の中の監査の書き込みだけ差し替える。"""
    with patch(
        "app.services.customer_conversion.record_audit_log", _make_noop_audit_log()
    ):
        yield


@pytest.fixture(autouse=True)
def _sqlite_token_shims(monkeypatch):
    """公開の登録フォームの試験用: 試験の SQLite では expires_at が文字列・NOW() が無い。"""
    from app.services.registration_token import _compute_hash

    async def fake_verify(db, raw_token):
        row = (
            await db.execute(
                text("SELECT id, tenant_id, lead_id, type FROM registration_tokens WHERE token_hash = :h"),
                {"h": _compute_hash(raw_token)},
            )
        ).mappings().first()
        return dict(row) if row else None

    async def fake_mark_used(db, token_id):
        await db.execute(
            text("UPDATE registration_tokens SET used_at = CURRENT_TIMESTAMP WHERE id = :id"), {"id": token_id}
        )

    monkeypatch.setattr("app.routers.registration_tokens.verify_token", fake_verify)
    monkeypatch.setattr("app.routers.registration_tokens.mark_token_used", fake_mark_used)


async def _status(db_session, lead_id: int) -> str:
    return (await db_session.execute(text("SELECT status FROM leads WHERE id = :i"), {"i": lead_id})).scalar_one()


async def _contact(client, company_id: int) -> int:
    r = await client.post("/api/v1/contacts", json={"company_id": company_id, "display_name": "担当"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _pay_by_order(client, company_id: int, no: str) -> None:
    ct = await _contact(client, company_id)
    r = await client.post("/api/v1/orders", json={"company_id": company_id, "contact_id": ct, "order_number": no})
    assert r.status_code == 201, r.text
    r = await client.patch(f"/api/v1/orders/{r.json()['id']}/paid", json={"paid": True})
    assert r.status_code == 200, r.text


async def _pay_by_invoice(client, db_session, company_id: int, keep_billing_default: bool) -> None:
    """請求書は請求先の国が要るので、請求先を入れて発行する。keep_billing_default が False のときは、
    入金の前に既定を外す（入金の時点で①がまだ無い状態を作る）。"""
    ct = await _contact(client, company_id)
    r = await client.patch(f"/api/v1/companies/{company_id}", json={"addresses": BILLING})
    assert r.status_code == 200, r.text
    r = await client.post("/api/v1/invoices", json={
        "company_id": company_id, "contact_id": ct, "shipping": {"mode": "none"},
        "items": [{"product_name": "商品", "quantity": 1, "unit_price": "1000.00"}],
    })
    assert r.status_code == 201, r.text
    inv_id = r.json()["id"]
    assert (await client.post(f"/api/v1/invoices/{inv_id}/issue")).status_code == 200
    if not keep_billing_default:
        await db_session.execute(
            text("UPDATE company_addresses SET is_default = FALSE WHERE company_id = :c"), {"c": company_id}
        )
        await db_session.commit()
    r = await client.post(f"/api/v1/invoices/{inv_id}/pay")
    assert r.status_code == 200, r.text


class _Scenario:
    """対象のリード L に、3 つを好きな順番で入れていく。② の前に ① ③ が来る順番では、会社を別のリード X の下に
    置いておき、② のときに L へ付け替える（会社を作るときはリードが必須のため）。"""

    def __init__(self, client, db_session, pay_kind: str):
        self.client, self.db, self.pay_kind = client, db_session, pay_kind
        self.lead = None
        self.other = None
        self.cid = None
        self.company_done = False
        self.reg_done = False
        self.pay_seq = 0

    async def start(self):
        self.lead = await create_lead(self.client, "対象リード")
        self.other = await create_lead(self.client, "置き場のリード")

    async def _ensure_company(self):
        if self.cid is None:
            owner = self.lead if self.company_done else self.other
            self.cid = await create_company(self.client, owner, name="会社")

    async def step(self, which: str):
        if which == "company":
            if self.cid is None:
                self.cid = await create_company(self.client, self.lead, name="会社")
            else:
                r = await self.client.patch(f"/api/v1/companies/{self.cid}", json={"lead_id": self.lead})
                assert r.status_code == 200, r.text
            self.company_done = True
        elif which == "reg":
            await self._ensure_company()
            r = await self.client.patch(f"/api/v1/companies/{self.cid}", json={"addresses": BILLING})
            assert r.status_code == 200, r.text
            self.reg_done = True
        elif which == "pay":
            await self._ensure_company()
            self.pay_seq += 1
            if self.pay_kind == "order":
                await _pay_by_order(self.client, self.cid, f"ORD-CC-{self.pay_seq}")
            else:
                await _pay_by_invoice(self.client, self.db, self.cid, keep_billing_default=self.reg_done)
        else:  # pragma: no cover
            raise AssertionError(which)


@pytest.mark.parametrize("pay_kind", ["invoice", "order"])
@pytest.mark.parametrize("order", list(itertools.permutations(["reg", "company", "pay"])))
async def test_k1_all_three_in_any_order_converts_at_last_step(client, db_session, order, pay_kind):
    """K1: 3 つがそろった瞬間（最後の 1 つの直後）に既存顧客になる。順番 6 通り × 支払い 2 通り。"""
    sc = _Scenario(client, db_session, pay_kind)
    await sc.start()
    for i, which in enumerate(order):
        await sc.step(which)
        if i < 2:
            assert await _status(db_session, sc.lead) == "lead", (order, which)
    assert await _status(db_session, sc.lead) == "existing_customer", order


@pytest.mark.parametrize(
    "have",
    [c for n in range(3) for c in itertools.combinations(["reg", "company", "pay"], n)],
)
async def test_k2_missing_any_condition_does_not_convert(client, db_session, have):
    """K2: 3 つのうち 0〜2 個では既存顧客にならない（欠けの 7 通り）。"""
    sc = _Scenario(client, db_session, "order")
    await sc.start()
    # ② が無いときは、会社は置き場のリードの下のまま（対象のリードに会社が無い）
    for which in ("company", "reg", "pay"):
        if which in have:
            await sc.step(which)
    assert await _status(db_session, sc.lead) == "lead", have


async def test_manual_registration_without_form_counts(client, db_session):
    """会社の画面で手で請求先を入れた人（登録フォームを使っていない人）も、支払いで既存顧客になる。"""
    lead = await create_lead(client, "手入力")
    cid = await create_company(client, lead, name="手入力会社", addresses=BILLING)
    assert await _status(db_session, lead) == "lead"
    await _pay_by_order(client, cid, "ORD-CC-MANUAL")
    assert await _status(db_session, lead) == "existing_customer"


async def test_k3_api_rejects_manual_existing_customer(client, db_session):
    """K3: 手で既存顧客を付ける道は閉じている（作る・直す）。"""
    r = await client.post("/api/v1/leads", json={"customer_name": "手で", "status": "existing_customer"})
    assert r.status_code == 422
    assert r.json()["detail"] == "existing_customer_is_automatic"

    lead = await create_lead(client, "直す")
    r = await client.patch(f"/api/v1/leads/{lead}", json={"status": "existing_customer"})
    assert r.status_code == 422
    assert r.json()["detail"] == "existing_customer_is_automatic"
    assert await _status(db_session, lead) == "lead"


async def test_k3_patch_same_value_for_existing_customer_is_allowed(client, db_session):
    """今が既存顧客の人に同じ値を送るのは通す（別の項目の保存が落ちないように）。"""
    lead = await create_lead(client, "既存")
    await db_session.execute(text("UPDATE leads SET status = 'existing_customer' WHERE id = :i"), {"i": lead})
    await db_session.commit()
    r = await client.patch(f"/api/v1/leads/{lead}", json={"status": "existing_customer", "notes": "メモ"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "existing_customer"


async def test_convert_existing_customer_returns_409(client, db_session):
    """既存顧客になった人は「商談に進める」で戻せない（409 already_existing_customer）。"""
    lead = await create_lead(client, "既存")
    await db_session.execute(text("UPDATE leads SET status = 'existing_customer' WHERE id = :i"), {"i": lead})
    await db_session.commit()
    r = await client.post(f"/api/v1/leads/{lead}/convert", json=CONVERT_BODY)
    assert r.status_code == 409, r.text
    assert r.json()["detail"] == "already_existing_customer"
    assert await _status(db_session, lead) == "existing_customer"


async def test_company_create_with_billing_after_payment_path(client, db_session):
    """会社を作る道: 別のリードの会社の支払いと請求先を、会社の付け替えで本人へ移すと本人が既存顧客になる。"""
    sc = _Scenario(client, db_session, "order")
    await sc.start()
    await sc.step("reg")
    await sc.step("pay")
    assert await _status(db_session, sc.lead) == "lead"
    await sc.step("company")
    assert await _status(db_session, sc.lead) == "existing_customer"


async def test_payment_survives_when_judgement_raises(client, db_session):
    """判定が例外を出しても、入金の記録は残る（SAVEPOINT だけ戻る）。"""
    lead = await create_lead(client, "例外")
    cid = await create_company(client, lead, name="例外会社", addresses=BILLING)

    async def boom(*a, **k):
        raise RuntimeError("boom")

    with patch("app.services.customer_conversion._all_three_conditions_met", boom):
        await _pay_by_order(client, cid, "ORD-CC-BOOM")
    paid = (
        await db_session.execute(text("SELECT COUNT(*) FROM orders WHERE company_id = :c AND paid_at IS NOT NULL"), {"c": cid})
    ).scalar_one()
    assert paid == 1
    assert await _status(db_session, lead) == "lead"


async def test_login_path_writes_audit_and_public_path_does_not(client, db_session):
    """ログインした道は監査（auto_convert）を残し、公開の登録フォームの道は監査の表に書かない。"""
    # ログインした道: 注文の支払済
    lead = await create_lead(client, "監査あり")
    cid = await create_company(client, lead, name="監査あり会社", addresses=BILLING)
    await _pay_by_order(client, cid, "ORD-CC-AUDIT")
    assert await _status(db_session, lead) == "existing_customer"
    n = (await db_session.execute(text("SELECT COUNT(*) FROM audit_logs WHERE action = 'auto_convert'"))).scalar_one()
    assert n == 1

    # 公開の道: 先に会社と支払いがあり、登録フォームの送信で最後の 1 つがそろう
    lead2 = await create_lead(client, "公開")
    cid2 = await create_company(client, lead2, name="公開会社")
    await _pay_by_order(client, cid2, "ORD-CC-PUBLIC")
    assert await _status(db_session, lead2) == "lead"
    r = await client.post("/api/v1/registration-tokens", json={"lead_id": lead2, "type": "register"})
    assert r.status_code in (200, 201), r.text
    token = r.json()["token"]
    form = {
        "token": token,
        "addresses": [{"address_type": "billing", "is_default": True, "name": "B", "address_line_1": "1 Main St", "country_code": "US"}],
        "billing_display_name": "B",
        "contact_name": "Taro",
        "contact_email": "taro@example.com",
    }
    r = await client.post("/api/v1/public/register", json=form)
    assert r.status_code == 200, r.text
    assert await _status(db_session, lead2) == "existing_customer"
    n2 = (await db_session.execute(text("SELECT COUNT(*) FROM audit_logs WHERE action = 'auto_convert'"))).scalar_one()
    assert n2 == 1  # 公開の道では増えない


async def test_registration_link_refused_when_registered(client, db_session):
    """登録が済んだ人には登録フォームのリンクを作れない（409 already_registered）。判定は 1 つの関数を共有する。"""
    lead = await create_lead(client, "登録済み")
    await create_company(client, lead, name="登録済み会社", addresses=BILLING)
    r = await client.post("/api/v1/registration-tokens", json={"lead_id": lead, "type": "register"})
    assert r.status_code == 409
    assert r.json()["detail"] == "already_registered"

    lead2 = await create_lead(client, "未登録")
    await create_company(client, lead2, name="未登録会社")
    r = await client.post("/api/v1/registration-tokens", json={"lead_id": lead2, "type": "change_billing"})
    assert r.status_code == 409
    assert r.json()["detail"] == "not_registered"


async def test_registration_completed_in_five_lead_responses_and_none_in_list(client, db_session):
    """registration_completed が詳細・作る・直す・商談に進めるで入り、一覧では None（統合は SQLite で動かないので対象外）。"""
    # 作る
    r = await client.post("/api/v1/leads", json={"customer_name": "返り値"})
    assert r.status_code == 201
    assert r.json()["registration_completed"] is False
    lead = r.json()["id"]
    # 詳細
    r = await client.get(f"/api/v1/leads/{lead}")
    assert r.json()["registration_completed"] is False
    # 直す
    r = await client.patch(f"/api/v1/leads/{lead}", json={"notes": "x"})
    assert r.json()["registration_completed"] is False
    # 商談に進める
    r = await client.post(f"/api/v1/leads/{lead}/convert", json=CONVERT_BODY)
    assert r.status_code == 200, r.text
    assert r.json()["registration_completed"] is False
    # 登録が済むと True
    await create_company(client, lead, name="返り値会社", addresses=BILLING)
    r = await client.get(f"/api/v1/leads/{lead}")
    assert r.json()["registration_completed"] is True
    # 統合（5 か所目）は試験の SQLite では動かない（統合の試験は PostgreSQL 専用・test_lead_merge_pg.py）ので、ここでは見ない
    # 一覧は入れない（一覧の API は試験の SQLite では動かないので、返す型の既定値が None であることで見る）
    from app.schemas.lead import LeadResponse

    assert LeadResponse.model_fields["registration_completed"].default is None


def test_condition_is_written_in_one_place_only():
    """1 か所だけ: (a) existing_customer を SET する文は customer_conversion.py にだけ。
    (b) 登録済みの判定の写しが registration_tokens.py に残っていない。"""
    app_dir = Path(__file__).resolve().parents[1] / "app"
    pat = re.compile(r"SET\s+status\s*=\s*'existing_customer'")
    hits = sorted(
        str(p.relative_to(app_dir))
        for p in app_dir.rglob("*.py")
        if pat.search(p.read_text(encoding="utf-8"))
    )
    assert hits == ["services/customer_conversion.py"]

    src = (app_dir / "routers" / "registration_tokens.py").read_text(encoding="utf-8")
    assert src.count("JOIN companies c ON c.id = ca.company_id") == 0
    assert src.count("is_registration_completed(") == 2
