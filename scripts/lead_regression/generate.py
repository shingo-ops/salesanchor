#!/usr/bin/env python3
"""テスト用データの作り方の正本（card-a-backend.md §4）。

- generate(seed, base_date) -> Dataset: 行のデータ（Python の値）を返す。同じ seed・base_date なら同じ結果。
- render_sql(dataset, tenant_id, mode): 本番に流す SQL を文字列で返す。
- CLI: python3 scripts/lead_regression/generate.py --seed 20261101 --base-date 2026-11-01 \
        --tenant-id 1 --mode dryrun|commit --out "$SCRATCH/lead_insert.sql"

本番の DB には繋がない（この道具は SQL ファイルを書くだけ）。
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.services import lead_conversion_factors as lcf  # noqa: E402
from app.services.message_translator import infer_original_language  # noqa: E402

# ── 件数 ──────────────────────────────────────────────────
N_LEADS = 470
N_WON = 150
N_LOST = N_LEADS - N_WON
LOST_REASON_COUNT = 8  # tenant_001 の close_reasons の type lost の数（本番の事実）

# ── 仕込む強さ（オッズ比）。ここ 1 か所だけに置く（画面にも入口にも書かない）──
PLANTED_ODDS: dict[str, float] = {
    "initiative_inbound": 2.0,
    "sales_form_wholesale": 2.5,
    "first_reply_within_1h": 1.8,
    "partner_reply_within_6h": 1.6,
    "channel_whatsapp": 1.5,
    "channel_instagram": 1.0,
    "country_gb": 1.0,
    "country_au": 1.0,
    "temperature_hot": 1.0,
    "temperature_warm": 1.0,
    "message_count": 1.0,
    "scale_large": 1.7,
    "scale_medium": 1.0,
    "customer_type_trust": 1.8,
    "competitor_found": 0.6,
}
assert tuple(PLANTED_ODDS) == lcf.ITEM_KEYS

SALES_FORM_OTHERS = ("physical_store", "ec_site", "live_streaming", "other")
# 店舗の形の選択肢（テナント004と同じ 5 つ。migrations/20260614_100000_create_sales_form_tables.sql）
SALES_FORM_OPTIONS = (
    ("実店舗", "physical_store", 1),
    ("ECサイト", "ec_site", 2),
    ("ライブ配信", "live_streaming", 3),
    ("卸・代理店", "wholesale", 4),
    ("その他", "other", 5),
)

INBOUND_BODIES = (
    "Hello, I am interested in your products.",
    "Could you share the price list and minimum order quantity?",
    "Thank you for the information. Please send more details.",
    "We would like to place a trial order next month.",
    "Is shipping to our country available?",
)
OUTBOUND_BODIES = (
    "Thank you for contacting us. Happy to help with your inquiry.",
    "Here is our current catalog and pricing.",
    "Please let us know if you have any questions.",
    "We can ship to your country. Details are attached.",
    "Just following up on our previous message.",
)

PLATFORM_META = (lcf.CHANNEL_INSTAGRAM, lcf.CHANNEL_MESSENGER)


@dataclass
class GenMessage:
    seq: int  # 1 から（SQL 用の連番。message_id の後ろ 6 桁）
    lead_index: int  # 0 始まり（lead_code の連番 - 1）
    direction: str
    ts: dt.datetime
    body: str
    message_id: str  # tlr-s<seed>-m<6桁>


@dataclass
class Dataset:
    seed: int
    base_date: dt.date
    leads: list[lcf.LeadRow]  # id は 1..470（lead_code の連番）。sales_form_values は 1 つ
    messages: list[lcf.MessageRow]  # analyze() に渡す形（id は GenMessage.seq）
    gen_messages: list[GenMessage]
    lead_codes: list[str]
    first_ts: list[dt.datetime]  # リードごとの最初のメッセージの時刻
    close_reason_order: list[int | None]  # 失注のリードだけ 1..8
    redraws: int
    b0: float
    log_odds_detail: dict[str, float] = field(default_factory=dict)


def _split3(rng: random.Random, n: int) -> list[int]:
    """n を 3 つに 157・157・156 の形で分ける（端数の配り先は rng）。"""
    base, rest = divmod(n, 3)
    counts = [base, base, base]
    for idx in rng.sample(range(3), rest):
        counts[idx] += 1
    return counts


def _alloc(rng: random.Random, values: list[str], counts: list[int]) -> list[str]:
    out: list[str] = []
    for v, c in zip(values, counts):
        out.extend([v] * c)
    rng.shuffle(out)
    return out


def _bisect_b0(etas: list[float], target: float) -> float:
    lo, hi = -50.0, 50.0
    for _ in range(300):
        mid = (lo + hi) / 2
        s = sum(1.0 / (1.0 + math.exp(-(mid + e))) for e in etas)
        if s < target:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-13:
            break
    return (lo + hi) / 2


def generate(seed: int, base_date: dt.date) -> Dataset:
    rng = random.Random(seed)
    n = N_LEADS

    # ── 項目の割り振り（互いに無関係・別々に）──
    initiative = _alloc(rng, [lcf.INITIATIVE_INBOUND, lcf.INITIATIVE_OUTBOUND], [235, 235])

    others_counts = [82, 82, 82, 82]
    others_counts[rng.randrange(4)] += 1  # 82・82・82・83（どれが 83 かは rng）
    sales_form = _alloc(
        rng,
        [lcf.SALES_FORM_WHOLESALE, *SALES_FORM_OTHERS],
        [141, *others_counts],
    )
    first_fast = _alloc(rng, ["1", "0"], [235, 235])
    partner_fast = _alloc(rng, ["1", "0"], [235, 235])
    customer_type = _alloc(rng, [lcf.CUSTOMER_TYPE_TRUST, lcf.CUSTOMER_TYPE_PRICE], [235, 235])
    competitor = _alloc(rng, ["1", "0"], [235, 235])
    channel = _alloc(rng, [lcf.CHANNEL_MESSENGER, lcf.CHANNEL_INSTAGRAM, lcf.CHANNEL_WHATSAPP], _split3(rng, n))
    country = _alloc(rng, list(lcf.COUNTRIES), _split3(rng, n))
    temperature = _alloc(
        rng, [lcf.TEMPERATURE_COLD, lcf.TEMPERATURE_WARM, lcf.TEMPERATURE_HOT], _split3(rng, n)
    )
    scale = _alloc(rng, [lcf.SCALE_SMALL, lcf.SCALE_MEDIUM, lcf.SCALE_LARGE], _split3(rng, n))
    msg_count = [rng.randint(4, 20) for _ in range(n)]

    # ── 成約の確率（log をとって足す）──
    ln = {k: math.log(v) for k, v in PLANTED_ODDS.items()}
    etas: list[float] = []
    for i in range(n):
        e = 0.0
        e += ln["initiative_inbound"] if initiative[i] == lcf.INITIATIVE_INBOUND else 0.0
        e += ln["sales_form_wholesale"] if sales_form[i] == lcf.SALES_FORM_WHOLESALE else 0.0
        e += ln["first_reply_within_1h"] if first_fast[i] == "1" else 0.0
        e += ln["partner_reply_within_6h"] if partner_fast[i] == "1" else 0.0
        e += ln["channel_whatsapp"] if channel[i] == lcf.CHANNEL_WHATSAPP else 0.0
        e += ln["channel_instagram"] if channel[i] == lcf.CHANNEL_INSTAGRAM else 0.0
        e += ln["country_gb"] if country[i] == lcf.COUNTRY_GB else 0.0
        e += ln["country_au"] if country[i] == lcf.COUNTRY_AU else 0.0
        e += ln["temperature_hot"] if temperature[i] == lcf.TEMPERATURE_HOT else 0.0
        e += ln["temperature_warm"] if temperature[i] == lcf.TEMPERATURE_WARM else 0.0
        e += ln["message_count"] * msg_count[i]
        e += ln["scale_large"] if scale[i] == lcf.SCALE_LARGE else 0.0
        e += ln["scale_medium"] if scale[i] == lcf.SCALE_MEDIUM else 0.0
        e += ln["customer_type_trust"] if customer_type[i] == lcf.CUSTOMER_TYPE_TRUST else 0.0
        e += ln["competitor_found"] if competitor[i] == "1" else 0.0
        etas.append(e)
    b0 = _bisect_b0(etas, float(N_WON))
    probs = [1.0 / (1.0 + math.exp(-(b0 + e))) for e in etas]
    assert abs(sum(probs) - N_WON) < 1e-9

    won: list[bool] = []
    redraws = 0
    while True:
        won = [rng.random() < p for p in probs]
        if sum(won) == N_WON:
            break
        redraws += 1

    # ── メッセージ ──
    day0 = dt.datetime.combine(base_date, dt.time(0, 0), tzinfo=dt.timezone.utc)
    latest_allowed = day0 - dt.timedelta(days=2)
    gen_messages: list[GenMessage] = []
    first_ts: list[dt.datetime] = []
    seq = 0
    for i in range(n):
        t = day0 - dt.timedelta(seconds=rng.randint(70 * 86400, 180 * 86400))
        first_ts.append(t)
        starts_inbound = initiative[i] == lcf.INITIATIVE_INBOUND
        first_reply_done = False
        in_k = out_k = 0
        for j in range(msg_count[i]):
            direction = (
                lcf.DIRECTION_INBOUND if (j % 2 == 0) == starts_inbound else lcf.DIRECTION_OUTBOUND
            )
            if j > 0:
                if direction == lcf.DIRECTION_INBOUND:
                    # 相手の返信（すぐ前はこちらの送信）
                    gap = (
                        rng.randint(300, 21600) if partner_fast[i] == "1" else rng.randint(21660, 259200)
                    )
                else:
                    seen_inbound = any(m.direction == lcf.DIRECTION_INBOUND for m in gen_messages[-j:])
                    if seen_inbound and not first_reply_done:
                        gap = rng.randint(60, 3540) if first_fast[i] == "1" else rng.randint(3660, 172800)
                        first_reply_done = True
                    else:
                        gap = rng.randint(300, 86400)
                t = t + dt.timedelta(seconds=gap)
            seq += 1
            if direction == lcf.DIRECTION_INBOUND:
                body = INBOUND_BODIES[in_k % len(INBOUND_BODIES)]
                in_k += 1
            else:
                body = OUTBOUND_BODIES[out_k % len(OUTBOUND_BODIES)]
                out_k += 1
            gen_messages.append(
                GenMessage(
                    seq=seq,
                    lead_index=i,
                    direction=direction,
                    ts=t,
                    body=body,
                    message_id=f"tlr-s{seed}-m{seq:06d}",
                )
            )
        assert t < latest_allowed, "最後のメッセージが base_date の 2日前より前にない"

    # ── 失注の理由（id 順に lost の 8 個を繰り返し）──
    order: list[int | None] = []
    k = 0
    for i in range(n):
        if won[i]:
            order.append(None)
        else:
            order.append(k % LOST_REASON_COUNT + 1)
            k += 1

    lead_codes = [f"TLR-{i + 1:05d}" for i in range(n)]
    leads = [
        lcf.LeadRow(
            id=i + 1,
            status=lcf.STATUS_WON if won[i] else lcf.STATUS_LOST,
            initiative=initiative[i],
            channel_type=channel[i],
            country=country[i],
            temperature=temperature[i],
            estimated_scale=scale[i],
            customer_type=customer_type[i],
            competitor_check=competitor[i] == "1",
            sales_form_values=[sales_form[i]],
        )
        for i in range(n)
    ]
    messages = [
        lcf.MessageRow(lead_id=m.lead_index + 1, id=m.seq, direction=m.direction, ts=m.ts) for m in gen_messages
    ]
    return Dataset(
        seed=seed,
        base_date=base_date,
        leads=leads,
        messages=messages,
        gen_messages=gen_messages,
        lead_codes=lead_codes,
        first_ts=first_ts,
        close_reason_order=order,
        redraws=redraws,
        b0=b0,
    )


# ── SQL の書き出し ─────────────────────────────────────────
def _q(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def _ts(t: dt.datetime) -> str:
    return _q(t.astimezone(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S+00")) + "::timestamptz"


def _chunks(rows: list[str], size: int = 200) -> list[list[str]]:
    return [rows[i : i + size] for i in range(0, len(rows), size)]


def expected_counts(ds: Dataset) -> dict[str, int]:
    meta_leads = {i for i, lead in enumerate(ds.leads) if lead.channel_type in PLATFORM_META}
    wa_leads = {i for i, lead in enumerate(ds.leads) if lead.channel_type == lcf.CHANNEL_WHATSAPP}
    meta_msgs = [m for m in ds.gen_messages if m.lead_index in meta_leads]
    return {
        "leads": len(ds.leads),
        "won": sum(1 for lead in ds.leads if lead.status == lcf.STATUS_WON),
        "lost": sum(1 for lead in ds.leads if lead.status == lcf.STATUS_LOST),
        "selections": len(ds.leads),
        "deal_close_reasons": sum(1 for o in ds.close_reason_order if o is not None),
        "lead_channels_instagram": sum(1 for lead in ds.leads if lead.channel_type == lcf.CHANNEL_INSTAGRAM),
        "lead_channels_messenger": sum(1 for lead in ds.leads if lead.channel_type == lcf.CHANNEL_MESSENGER),
        "meta_messages": len(meta_msgs),
        "conv_logs_meta_copy": sum(1 for m in meta_msgs if m.direction == lcf.DIRECTION_INBOUND),
        "conv_logs_whatsapp": sum(1 for m in ds.gen_messages if m.lead_index in wa_leads),
    }


def render_sql(ds: Dataset, tenant_id: int, mode: str) -> str:
    if mode not in ("dryrun", "commit"):
        raise ValueError("mode は dryrun か commit")
    schema = f"tenant_{tenant_id:03d}"
    prefix = f"tlr-s{ds.seed}-"
    exp = expected_counts(ds)
    out: list[str] = []
    w = out.append

    w("-- テスト用データの書き込み（作り方の正本: scripts/lead_regression/generate.py）")
    w(f"-- seed={ds.seed} base_date={ds.base_date.isoformat()} 成約の引き直し回数={ds.redraws}")
    w("SET statement_timeout = '600s';")
    w("SET lock_timeout = '10s';")
    w("BEGIN;")

    # 前提の点検
    w("DO $$")
    w("BEGIN")
    w(f"  IF (SELECT count(*) FROM {schema}.leads WHERE lead_code LIKE 'TLR-%') <> 0 THEN")
    w("    RAISE EXCEPTION '前提が違う: TLR- のリードが既にある';")
    w("  END IF;")
    w(f"  IF (SELECT count(*) FROM {schema}.tenant_sales_form_options) <> 0 THEN")
    w("    RAISE EXCEPTION '前提が違う: 店舗の形の選択肢が既にある';")
    w("  END IF;")
    w(f"  IF (SELECT count(*) FROM {schema}.close_reasons WHERE type = 'lost') <> {LOST_REASON_COUNT} THEN")
    w("    RAISE EXCEPTION '前提が違う: 失注理由の選択肢が 8 件ではない';")
    w("  END IF;")
    w(f"  IF to_regclass('{schema}.deal_close_reasons') IS NULL THEN")
    w("    RAISE EXCEPTION '前提が違う: deal_close_reasons の表が無い';")
    w("  END IF;")
    w("END $$;")

    # 店舗の形の選択肢
    w(f"INSERT INTO {schema}.tenant_sales_form_options (tenant_id, label, value, sort_order) VALUES")
    w(",\n".join(f"  ({tenant_id}, {_q(lab)}, {_q(val)}, {so})" for lab, val, so in SALES_FORM_OPTIONS) + ";")

    # leads（id は RETURNING で受ける）
    lead_rows = []
    for i, lead in enumerate(ds.leads):
        lead_rows.append(
            "  ("
            + ", ".join(
                [
                    str(tenant_id),
                    _q(ds.lead_codes[i]),
                    _q(ds.lead_codes[i]),
                    _q(lead.channel_type or ""),
                    _q(lead.initiative or ""),
                    _q(lead.status),
                    _q(lead.temperature or ""),
                    _q(lead.estimated_scale or ""),
                    _q(lead.customer_type or ""),
                    _q(lead.country or ""),
                    "TRUE" if lead.competitor_check else "FALSE",
                    _ts(ds.first_ts[i]),
                    _ts(ds.first_ts[i]),
                ]
            )
            + ")"
        )
    w(
        f"INSERT INTO {schema}.leads (tenant_id, lead_code, customer_name, channel_type, initiative, status, "
        "temperature, estimated_scale, customer_type, country, competitor_check, created_at, updated_at) VALUES"
    )
    w(",\n".join(lead_rows))
    w("RETURNING id, lead_code;")

    # 店舗の形の選択
    for part in _chunks([f"({_q(ds.lead_codes[i])}, {_q(lead.sales_form_values[0])})" for i, lead in enumerate(ds.leads)]):
        w(f"INSERT INTO {schema}.lead_sales_form_selections (lead_id, option_id)")
        w("SELECT l.id, o.id FROM (VALUES")
        w(",\n".join("  " + r for r in part))
        w(f") AS v(lead_code, value) JOIN {schema}.leads l ON l.lead_code = v.lead_code")
        w(f"JOIN {schema}.tenant_sales_form_options o ON o.value = v.value AND o.tenant_id = {tenant_id};")

    # 失注の理由（lost の 8 個を sort_order 順に）
    reason_rows = [
        f"({_q(ds.lead_codes[i])}, {o})" for i, o in enumerate(ds.close_reason_order) if o is not None
    ]
    for part in _chunks(reason_rows):
        w(f"INSERT INTO {schema}.deal_close_reasons (lead_id, reason_id, is_primary)")
        w("SELECT l.id, r.id, '1' FROM (VALUES")
        w(",\n".join("  " + r for r in part))
        w(f") AS v(lead_code, ord) JOIN {schema}.leads l ON l.lead_code = v.lead_code")
        w("JOIN (SELECT id, row_number() OVER (ORDER BY sort_order, id) AS ord")
        w(f"      FROM {schema}.close_reasons WHERE type = 'lost') r ON r.ord = v.ord;")

    # lead_channels（Instagram・Facebook のリードだけ）
    ch_rows = [
        f"({_q(ds.lead_codes[i])}, {_q(lead.channel_type or '')}, {_q('tlr-psid-' + ds.lead_codes[i][4:])})"
        for i, lead in enumerate(ds.leads)
        if lead.channel_type in PLATFORM_META
    ]
    for part in _chunks(ch_rows):
        w(f"INSERT INTO {schema}.lead_channels (lead_id, platform, external_id)")
        w("SELECT l.id, v.platform, v.external_id FROM (VALUES")
        w(",\n".join("  " + r for r in part))
        w(f") AS v(lead_code, platform, external_id) JOIN {schema}.leads l ON l.lead_code = v.lead_code;")

    # meta_messages（Instagram・Facebook）と conversation_logs
    meta_rows: list[str] = []
    copy_rows: list[str] = []
    wa_rows: list[str] = []
    for m in ds.gen_messages:
        lead = ds.leads[m.lead_index]
        code = ds.lead_codes[m.lead_index]
        psid = "tlr-psid-" + code[4:]
        platform = lead.channel_type or ""
        if platform in PLATFORM_META:
            if m.direction == lcf.DIRECTION_INBOUND:
                lang = infer_original_language(m.body)
                payload = json.dumps(
                    {
                        "timestamp": int(m.ts.timestamp() * 1000),
                        "has_text": True,
                        "has_attachments": False,
                    },
                    separators=(", ", ": "),
                )
                meta_rows.append(
                    "("
                    + ", ".join(
                        [
                            _q(code), _q(platform), _q(psid), "NULL", _q(m.body), "'inbound'",
                            _q(payload), _q(m.message_id), _q(lang) if lang else "NULL", _ts(m.ts),
                        ]
                    )
                    + ")"
                )
                copy_rows.append(
                    "("
                    + ", ".join(
                        [_q(code), _q(platform), _q(psid), "'inbound'", _q(psid), _q(m.body), _q(m.message_id), _ts(m.ts)]
                    )
                    + ")"
                )
            else:
                meta_rows.append(
                    "("
                    + ", ".join(
                        [
                            _q(code), _q(platform), _q("tlr-page"), _q(psid), _q(m.body), "'outbound'",
                            "NULL", _q(m.message_id), "NULL", _ts(m.ts),
                        ]
                    )
                    + ")"
                )
        else:
            wa_rows.append(
                "(" + ", ".join([_q(code), _q(platform), _q(m.direction), _q(m.body), _ts(m.ts)]) + ")"
            )

    for part in _chunks(meta_rows):
        w(
            f"INSERT INTO {schema}.meta_messages (tenant_id, lead_id, platform, sender_id, recipient_id, "
            "message_text, direction, raw_payload, message_id, original_language, created_at, "
            "messaging_type)"
        )
        w(f"SELECT {tenant_id}, l.id, v.platform, v.sender_id, v.recipient_id, v.message_text, v.direction,")
        w("       v.raw_payload::jsonb, v.message_id, v.original_language, v.created_at,")
        w("       CASE WHEN v.direction = 'outbound' THEN 'RESPONSE' END")
        w("FROM (VALUES")
        w(",\n".join("  " + r for r in part))
        w(
            ") AS v(lead_code, platform, sender_id, recipient_id, message_text, direction, raw_payload, "
            "message_id, original_language, created_at)"
        )
        w(f"JOIN {schema}.leads l ON l.lead_code = v.lead_code;")

    for part in _chunks(copy_rows):
        w(
            f"INSERT INTO {schema}.conversation_logs (tenant_id, lead_id, channel_type, channel_identity, "
            "direction, sender, content_text, external_message_id, occurred_at, created_at)"
        )
        w(f"SELECT {tenant_id}, l.id, v.channel_type, v.channel_identity, v.direction, v.sender, v.content_text,")
        w("       v.external_message_id, v.occurred_at, v.occurred_at")
        w("FROM (VALUES")
        w(",\n".join("  " + r for r in part))
        w(
            ") AS v(lead_code, channel_type, channel_identity, direction, sender, content_text, "
            "external_message_id, occurred_at)"
        )
        w(f"JOIN {schema}.leads l ON l.lead_code = v.lead_code;")

    for part in _chunks(wa_rows):
        w(
            f"INSERT INTO {schema}.conversation_logs (tenant_id, lead_id, channel_type, direction, "
            "content_text, occurred_at, created_at)"
        )
        w(f"SELECT {tenant_id}, l.id, v.channel_type, v.direction, v.content_text, v.occurred_at, v.occurred_at")
        w("FROM (VALUES")
        w(",\n".join("  " + r for r in part))
        w(") AS v(lead_code, channel_type, direction, content_text, occurred_at)")
        w(f"JOIN {schema}.leads l ON l.lead_code = v.lead_code;")

    # 件数の点検
    w("DO $$")
    w("BEGIN")
    checks = [
        ("TLR- のリード", f"SELECT count(*) FROM {schema}.leads WHERE lead_code LIKE 'TLR-%'", exp["leads"]),
        (
            "成約",
            f"SELECT count(*) FROM {schema}.leads WHERE lead_code LIKE 'TLR-%' AND status = '{lcf.STATUS_WON}'",
            exp["won"],
        ),
        (
            "失注",
            f"SELECT count(*) FROM {schema}.leads WHERE lead_code LIKE 'TLR-%' AND status = '{lcf.STATUS_LOST}'",
            exp["lost"],
        ),
        (
            "店舗の形の選択",
            f"SELECT count(*) FROM {schema}.lead_sales_form_selections s JOIN {schema}.leads l ON l.id = s.lead_id "
            "WHERE l.lead_code LIKE 'TLR-%'",
            exp["selections"],
        ),
        (
            "失注の理由",
            f"SELECT count(*) FROM {schema}.deal_close_reasons d JOIN {schema}.leads l ON l.id = d.lead_id "
            "WHERE l.lead_code LIKE 'TLR-%'",
            exp["deal_close_reasons"],
        ),
        (
            "lead_channels instagram",
            f"SELECT count(*) FROM {schema}.lead_channels WHERE external_id LIKE 'tlr-psid-%' "
            f"AND platform = '{lcf.CHANNEL_INSTAGRAM}'",
            exp["lead_channels_instagram"],
        ),
        (
            "lead_channels messenger",
            f"SELECT count(*) FROM {schema}.lead_channels WHERE external_id LIKE 'tlr-psid-%' "
            f"AND platform = '{lcf.CHANNEL_MESSENGER}'",
            exp["lead_channels_messenger"],
        ),
        (
            "meta_messages",
            f"SELECT count(*) FROM {schema}.meta_messages WHERE message_id LIKE '{prefix}%'",
            exp["meta_messages"],
        ),
        (
            "conversation_logs（Instagram・Facebook の写し）",
            f"SELECT count(*) FROM {schema}.conversation_logs WHERE external_message_id LIKE '{prefix}%'",
            exp["conv_logs_meta_copy"],
        ),
        (
            "conversation_logs（WhatsApp）",
            f"SELECT count(*) FROM {schema}.conversation_logs c JOIN {schema}.leads l ON l.id = c.lead_id "
            f"WHERE l.lead_code LIKE 'TLR-%' AND c.channel_type = '{lcf.CHANNEL_WHATSAPP}'",
            exp["conv_logs_whatsapp"],
        ),
    ]
    for label, sql, want in checks:
        w(f"  IF ({sql}) <> {want} THEN")
        w(f"    RAISE EXCEPTION '件数の点検に失敗: {label} が {want} 件ではない';")
        w("  END IF;")
    w("END $$;")

    w("ROLLBACK;" if mode == "dryrun" else "COMMIT;")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--base-date", required=True)
    ap.add_argument("--tenant-id", type=int, required=True)
    ap.add_argument("--mode", choices=("dryrun", "commit"), required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    out = Path(args.out).resolve()
    try:
        out.relative_to(REPO_ROOT)
    except ValueError:
        pass
    else:
        print(f"STOP: 出力先がリポジトリの中です: {out}", file=sys.stderr)
        return 2
    ds = generate(args.seed, dt.date.fromisoformat(args.base_date))
    sql = render_sql(ds, args.tenant_id, args.mode)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(sql, encoding="utf-8")
    print(f"wrote {out} lines={sql.count(chr(10))} redraws={ds.redraws}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
