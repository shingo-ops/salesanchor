"""成約しやすさの分析（app/services/lead_conversion_factors.py と入口）の試験。

card-a-backend.md §3・§5-1。計算は標準ライブラリだけ。
statsmodels との突き合わせの期待値は定数で持つ（CI は statsmodels を入れない）。
"""

from __future__ import annotations

import datetime as dt
import math
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import text

from app.services import lead_conversion_factors as lcf
from tests.conftest import LEAD_FACTORS_MSG_DDL as _MSG_DDL

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "lead_regression"
sys.path.insert(0, str(_SCRIPTS))
import generate as gen  # noqa: E402

T0 = dt.datetime(2026, 1, 1, 0, 0, tzinfo=dt.timezone.utc)
IDX = {k: i + 1 for i, k in enumerate(lcf.ITEM_KEYS)}  # 行列の列（0 は定数）


def lead(i: int = 1, **kw) -> lcf.LeadRow:
    base = dict(
        id=i,
        status=lcf.STATUS_WON,
        initiative=lcf.INITIATIVE_INBOUND,
        channel_type=lcf.CHANNEL_MESSENGER,
        country=lcf.COUNTRY_US,
        temperature=lcf.TEMPERATURE_COLD,
        estimated_scale=lcf.SCALE_SMALL,
        customer_type=lcf.CUSTOMER_TYPE_PRICE,
        competitor_check=False,
        sales_form_values=["ec_site"],
    )
    base.update(kw)
    return lcf.LeadRow(**base)


def msg(lead_id: int, mid: int, direction: str, seconds: float) -> lcf.MessageRow:
    return lcf.MessageRow(lead_id, mid, direction, T0 + dt.timedelta(seconds=seconds))


IN, OUT = lcf.DIRECTION_INBOUND, lcf.DIRECTION_OUTBOUND


def basic_msgs(lead_id: int = 1, first_reply: float = 60, partner_gap: float = 60) -> list[lcf.MessageRow]:
    # in → out（最初の返信）→ in（相手の返信 = 直前の out からの秒数）
    return [
        msg(lead_id, 1, IN, 0),
        msg(lead_id, 2, OUT, first_reply),
        msg(lead_id, 3, IN, first_reply + partner_gap),
    ]


# ── 区切りちょうど（≦）──────────────────────────────────────
@pytest.mark.parametrize(
    ("first_reply", "expect"),
    [(3600, 1.0), (3601, 0.0)],
)
def test_first_reply_boundary(first_reply, expect):
    prep = lcf.prepare([lead()], basic_msgs(first_reply=first_reply))
    assert prep.x[0][IDX["first_reply_within_1h"]] == expect


@pytest.mark.parametrize(
    ("gap", "expect"),
    [(21600, 1.0), (21601, 0.0)],
)
def test_partner_reply_boundary(gap, expect):
    prep = lcf.prepare([lead()], basic_msgs(partner_gap=gap))
    assert prep.x[0][IDX["partner_reply_within_6h"]] == expect


def test_same_timestamp_ordered_by_id():
    # 同じ時刻なら id の昇順。out(id=4) が in(id=5) より先になるので、最初の受信の後に送信が無い
    a = [msg(1, 5, IN, 0), msg(1, 4, OUT, 0)]
    assert lcf.first_reply_seconds(sorted(a, key=lambda m: (m.ts, m.id))) is None
    assert lcf._ordered_messages(a)[1][0].id == 4
    # id が逆なら in(4) → out(5) で 0 秒
    b = [msg(1, 4, IN, 0), msg(1, 5, OUT, 0)]
    assert lcf.first_reply_seconds(lcf._ordered_messages(b)[1]) == 0.0


def test_outbound_first_lead_uses_first_outbound_after_first_inbound():
    # こちらから営業: out → in → out（これが最初の返信）→ in
    msgs = [msg(1, 1, OUT, 0), msg(1, 2, IN, 100), msg(1, 3, OUT, 200), msg(1, 4, IN, 500)]
    ordered = lcf._ordered_messages(msgs)[1]
    assert lcf.first_reply_seconds(ordered) == 100.0
    # 相手の返信: out(0)→in(100)=100、out(200)→in(500)=300 の平均 200
    assert lcf.partner_reply_mean_seconds(ordered) == 200.0


# ── 外す決まり 7 種（上から順に当て、最初の 1 つだけに数える）──────────
@pytest.mark.parametrize(
    ("key", "lead_kw", "msgs"),
    [
        ("by_status", {"status": "lead"}, None),
        ("other_values", {"country": "JP"}, None),
        ("no_inbound", {}, [msg(1, 1, OUT, 0), msg(1, 2, OUT, 10)]),
        ("no_outbound", {}, [msg(1, 1, IN, 0), msg(1, 2, IN, 10)]),
        ("no_reply_pair", {}, [msg(1, 1, OUT, 0), msg(1, 2, IN, 10)]),
        ("no_sales_form", {"sales_form_values": []}, None),
        ("missing_scale_or_type", {"estimated_scale": None}, None),
    ],
)
def test_exclusion_each_kind(key, lead_kw, msgs):
    prep = lcf.prepare([lead(**lead_kw)], msgs if msgs is not None else basic_msgs())
    assert prep.excluded[key] == 1
    assert sum(prep.excluded.values()) == 1
    assert prep.lead_ids == []


def test_excluded_first_match_only():
    # 状態も国も対象外 → by_status だけに数える
    prep = lcf.prepare([lead(status="lead", country="JP")], basic_msgs())
    assert prep.excluded["by_status"] == 1 and prep.excluded["other_values"] == 0


def test_wholesale_included_means_wholesale():
    prep = lcf.prepare([lead(sales_form_values=["ec_site", lcf.SALES_FORM_WHOLESALE])], basic_msgs())
    assert prep.x[0][IDX["sales_form_wholesale"]] == 1.0
    assert prep.x[0][IDX["message_count"]] == 3.0


# ── 件数・計算できない ────────────────────────────────────────
def _big_dataset_leads(seed: int = 1):
    ds = gen.generate(seed, dt.date(2026, 11, 1))
    return ds


def test_insufficient_when_few_leads():
    res = lcf.analyze([lead()], basic_msgs())
    assert res.status == "insufficient"
    assert res.items == []
    assert res.included_count == 1


def test_complete_separation_is_not_computable_not_exception():
    ds = _big_dataset_leads()
    # 相見積もりの有無で成約が完全に分かれる（完全分離）
    leads = [
        lcf.LeadRow(**{**lead_.__dict__, "status": lcf.STATUS_WON if lead_.competitor_check else lcf.STATUS_LOST})
        for lead_ in ds.leads
    ]
    res = lcf.analyze(leads, ds.messages)
    assert res.status == "not_computable"
    assert res.items == []
    items = lcf.item_results(res.fit)
    assert len(items) == 15
    assert all(not it["computable"] and it["odds_ratio"] is None for it in items)


# ── 作り物のデータの計算 ──────────────────────────────────────
def test_ok_returns_15_items_in_order():
    ds = _big_dataset_leads()
    res = lcf.analyze(ds.leads, ds.messages)
    assert res.status == "ok"
    assert [it["key"] for it in res.items] == list(lcf.ITEM_KEYS)
    assert res.included_count == 470 and res.won_count == 150 and res.lost_count == 320
    assert all(res.items[i]["ci_low"] < res.items[i]["odds_ratio"] < res.items[i]["ci_high"] for i in range(15))


# ── statsmodels との突き合わせ（小数 4 桁）──────────────────────
# 期待値: seed 1・base_date 2026-11-01 の Dataset（generate.generate(1, date(2026, 11, 1))）の
# 説明の行列（定数 1 の列 ＋ 15 列）について、クラウドの使い捨ての環境（Python 3.12・numpy 2.5.4・
# statsmodels 0.15.0）で Logit(y, X).fit(method="newton", maxiter=100, tol=1e-10)、
# conf_int(0.05)（対数の上の幅）を出した値（小数 6 桁）。0 番目は定数項。
SM_SEED1 = {
    "beta": [-2.982649, 0.804744, 1.262399, 0.532659, 0.443677, -0.002634, -0.014361, 0.088498, 0.153174, -0.054627, -0.194178, 0.018505, 0.869182, 0.207042, 0.767061, -0.30495],
    "se": [0.514217, 0.222843, 0.233664, 0.221634, 0.22161, 0.269682, 0.274654, 0.271927, 0.274116, 0.268171, 0.270566, 0.023405, 0.26872, 0.279755, 0.222031, 0.22237],
    "ci_low": [-3.990496, 0.367981, 0.804426, 0.098263, 0.00933, -0.531202, -0.552673, -0.44447, -0.384083, -0.580232, -0.724479, -0.027368, 0.3425, -0.341269, 0.331889, -0.740788],
    "ci_high": [-1.974801, 1.241508, 1.720373, 0.967054, 0.878024, 0.525933, 0.52395, 0.621466, 0.690431, 0.470979, 0.336122, 0.064379, 1.395865, 0.755352, 1.202234, 0.130887],
}


def _fit_seed1():
    ds = gen.generate(1, dt.date(2026, 11, 1))
    res = lcf.analyze(ds.leads, ds.messages)
    assert res.fit is not None and res.fit.computable
    return res.prepared, res.fit


def test_matches_statsmodels_constants_4_digits():
    _, fit = _fit_seed1()
    lo = [b - lcf.Z_975 * s for b, s in zip(fit.beta, fit.se)]
    hi = [b + lcf.Z_975 * s for b, s in zip(fit.beta, fit.se)]
    for mine, ref in ((fit.beta, SM_SEED1["beta"]), (fit.se, SM_SEED1["se"]), (lo, SM_SEED1["ci_low"]), (hi, SM_SEED1["ci_high"])):
        assert len(mine) == len(ref) == 16
        assert max(abs(a - b) for a, b in zip(mine, ref)) < 5e-5


def test_matches_statsmodels_live_when_available():
    sm = pytest.importorskip("statsmodels.api")
    np = pytest.importorskip("numpy")
    prep, fit = _fit_seed1()
    r = sm.Logit(np.array(prep.y), np.array(prep.x)).fit(method="newton", maxiter=100, tol=1e-10, disp=0)
    ci = r.conf_int(0.05)
    assert max(abs(a - b) for a, b in zip(fit.beta, r.params)) < 5e-5
    assert max(abs(a - b) for a, b in zip(fit.se, r.bse)) < 5e-5
    lo = [b - lcf.Z_975 * s for b, s in zip(fit.beta, fit.se)]
    assert max(abs(a - b) for a, b in zip(lo, ci[:, 0])) < 5e-5


def test_gauss_jordan_inverse():
    m = [[4.0, 7.0, 2.0], [3.0, 6.0, 1.0], [2.0, 5.0, 3.0]]
    inv = lcf._invert(m)
    assert inv is not None
    for i in range(3):
        for j in range(3):
            v = sum(m[i][k] * inv[k][j] for k in range(3))
            assert math.isclose(v, 1.0 if i == j else 0.0, abs_tol=1e-12)
    assert lcf._invert([[1.0, 2.0], [2.0, 4.0]]) is None


# ── 入口（SQLite）────────────────────────────────────────────
_URL = "/api/v1/analytics/lead-conversion-factors"

_OPTION_ID = {"physical_store": 1, "ec_site": 2, "live_streaming": 3, "wholesale": 4, "other": 5}


@pytest.fixture
async def msg_tables(db_session):
    for ddl in _MSG_DDL.values():
        await db_session.execute(text(ddl))
    await db_session.commit()
    yield
    for name in _MSG_DDL:
        await db_session.execute(text(f"DROP TABLE IF EXISTS {name}"))
    await db_session.commit()


def _fmt(t: dt.datetime) -> str:
    return t.astimezone(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


async def _load(db_session, ds: gen.Dataset, *, extra_deleted: bool = False):
    for lead_ in ds.leads:
        await db_session.execute(
            text(
                "INSERT INTO leads (id, tenant_id, customer_name, status, initiative, channel_type, country, "
                "temperature, estimated_scale, customer_type, competitor_check) "
                "VALUES (:id, 999, :n, :status, :ini, :ch, :co, :te, :sc, :ct, :cc)"
            ),
            dict(
                id=lead_.id, n=f"TLR-{lead_.id:05d}", status=lead_.status, ini=lead_.initiative,
                ch=lead_.channel_type, co=lead_.country, te=lead_.temperature, sc=lead_.estimated_scale,
                ct=lead_.customer_type, cc=1 if lead_.competitor_check else 0,
            ),
        )
        await db_session.execute(
            text("INSERT INTO lead_sales_form_selections (lead_id, option_id) VALUES (:l, :o)"),
            dict(l=lead_.id, o=_OPTION_ID[lead_.sales_form_values[0]]),
        )
    channel = {lead_.id: lead_.channel_type for lead_ in ds.leads}
    for m in ds.gen_messages:
        lead_id = m.lead_index + 1
        if channel[lead_id] == lcf.CHANNEL_WHATSAPP:
            await db_session.execute(
                text("INSERT INTO conversation_logs (lead_id, direction, content_text, occurred_at) VALUES (:l, :d, :b, :t)"),
                dict(l=lead_id, d=m.direction, b=m.body, t=_fmt(m.ts)),
            )
        else:
            await db_session.execute(
                text("INSERT INTO meta_messages (lead_id, platform, direction, message_text, created_at) VALUES (:l, :p, :d, :b, :t)"),
                dict(l=lead_id, p=channel[lead_id], d=m.direction, b=m.body, t=_fmt(m.ts)),
            )
    if extra_deleted:
        # 消した行（deleted_at あり）は読まない: 読むと最初の返信が 0 秒になる行を 1 つ足す
        meta_lead = next(lead_ for lead_ in ds.leads if lead_.channel_type != lcf.CHANNEL_WHATSAPP)
        first = min(m.ts for m in ds.gen_messages if m.lead_index + 1 == meta_lead.id)
        await db_session.execute(
            text(
                "INSERT INTO meta_messages (lead_id, platform, direction, message_text, created_at, deleted_at) "
                "VALUES (:l, :p, 'outbound', 'x', :t, '2026-01-01 00:00:00')"
            ),
            dict(l=meta_lead.id, p=meta_lead.channel_type, t=_fmt(first - dt.timedelta(seconds=1))),
        )
    await db_session.commit()


async def test_endpoint_requires_permission(client, msg_tables):
    with patch("app.auth.dependencies.load_user_permissions", new=AsyncMock(return_value=set())):
        res = await client.get(_URL)
    assert res.status_code == 403


async def test_endpoint_no_leads_is_insufficient(client, msg_tables):
    res = await client.get(_URL)
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "insufficient"
    assert body["included_count"] == 0 and body["won_count"] == 0 and body["lost_count"] == 0
    assert body["items"] == []
    assert body["required_per_item"] == 10 and body["item_count"] == 15
    assert set(body["excluded"]) == set(lcf.EXCLUDED_KEYS)
    assert all(v == 0 for v in body["excluded"].values())


async def test_endpoint_equals_direct_function(client, db_session, msg_tables):
    ds = gen.generate(2, dt.date(2026, 11, 1))
    await _load(db_session, ds, extra_deleted=True)
    res = await client.get(_URL)
    assert res.status_code == 200
    body = res.json()
    direct = lcf.analyze(ds.leads, ds.messages)
    assert direct.status == "ok"
    assert body["status"] == "ok"
    assert (body["included_count"], body["won_count"], body["lost_count"]) == (470, 150, 320)
    assert body["excluded"] == direct.excluded
    assert len(body["items"]) == 15
    for got, want in zip(body["items"], direct.items):
        assert got == want  # 完全に同じ（丸めない）
