"""
解析精度管理（新方式）: 誤りの兆候 S1〜S6 の SQL 式（SSOT）。

summary・posts・detail の3つの API は、必ずこのモジュールの定義だけを使う
（docs/handoff/line-accuracy-pages/design.md §3-3）。兆候は「誤りそのもの」ではなく
「誤りの候補」。増やすときはこのモジュールと設計書を同時に更新する。

母集団は extraction_shadow_results(res) / extraction_shadow_runs(run) /
extraction_jobs(job) / source_messages(sm) の JOIN。期間は run.started_at で絞る。
すべて読み取り専用の SELECT。値はすべて固定の SQL 文字列で、外から入るのは
名前付きパラメータ（:days / :supplier_id / :run_id など）だけ。
"""
from __future__ import annotations

from typing import Final

# 兆候の名前（表示順）。画面・API の signals キーはこの順番。
SIGNAL_CODES: Final[tuple[str, ...]] = ("S1", "S2", "S3", "S4", "S5", "S6")

# 兆候コード → フラグ列名（SQL に埋め込むのは必ずこの辞書の値だけ。外部入力は通さない）
SIGNAL_COLUMNS: Final[dict[str, str]] = {code: code.lower() for code in SIGNAL_CODES}

# S3 で「単品」とみなす単位マスタの kubun（public.units.kubun。「枚系」という kubun は存在しない）
SINGLE_UNIT_KUBUN: Final[str] = "単品系"
# S3 の対象とする状態コード（public.conditions.code の FLAG_SINGLE）
FLAG_SINGLE_CONDITION_CODE: Final[str] = "CN0008"
# S1 の完売語（大小文字を区別しない正規表現）
SOLD_OUT_REGEX: Final[str] = "完売|売切|売り切れ|SOLD ?OUT"
# S4 で「短い記号」とみなす products.mark の最大文字数
SHORT_MARK_MAX_LEN: Final[int] = 2

# 母集団の FROM（res/run/job/sm の JOIN + 仕入元・商品・状態・単位マスタの参照）。
# 単位は tcg_analyzer_svc.resolve_unit_v2 と同じく、完全一致 → 小文字一致の順で
# public.unit_aliases / public.units（canonical も別名として扱う）に当てる。
# マスタに無い語・空は kubun が NULL。
_BASE_FROM: Final[str] = """
    FROM public.extraction_shadow_results res
    JOIN public.extraction_shadow_runs run ON run.id = res.run_id
    JOIN public.extraction_jobs job ON job.id = run.extraction_job_id
    JOIN public.source_messages sm ON sm.id = job.source_message_id
    LEFT JOIN public.supplier_channels sc ON sc.id = sm.supplier_channel_id
    LEFT JOIN public.suppliers sup ON sup.id = sc.supplier_id
    LEFT JOIN public.products prod ON prod.id = res.product_id
    LEFT JOIN public.conditions cond ON cond.id = res.condition_id
    LEFT JOIN LATERAL (
        SELECT m.kubun
        FROM (
            SELECT ua.alias_text AS k, u.kubun
            FROM public.unit_aliases ua
            JOIN public.units u ON u.id = ua.unit_id
            WHERE u.is_active
            UNION ALL
            SELECT u2.canonical AS k, u2.kubun
            FROM public.units u2
            WHERE u2.is_active
        ) m
        WHERE res.raw_unit IS NOT NULL
          AND lower(m.k) = lower(btrim(res.raw_unit))
        ORDER BY (m.k = btrim(res.raw_unit)) DESC
        LIMIT 1
    ) unit_m ON TRUE
"""

# ブロック・見出しの本文（行番号は 1 始まり・両端含む。範囲外は空）
_BLOCK_TEXT: Final[str] = (
    "array_to_string((string_to_array(sm.raw_text, chr(10)))[res.line_start : res.line_end], chr(10))"
)
_HEADING_TEXT: Final[str] = (
    "array_to_string((string_to_array(sm.raw_text, chr(10)))"
    "[res.heading_line_start : res.heading_line_end], chr(10))"
)

# 母集団の列（blk_rows CTE が返す列）。兆候の式はこれらの列名だけを参照する。
_ROW_COLUMNS: Final[str] = f"""
        res.id, res.run_id, res.block_index, res.line_start, res.line_end,
        res.heading_line_start, res.heading_line_end,
        res.raw_product_name, res.raw_price, res.raw_unit, res.raw_quantity,
        res.raw_state, res.raw_ship, res.raw_multi,
        res.product_id, res.work_id, res.condition_id,
        res.quantity_normalized, res.price_normalized,
        res.ship_offer_type, res.ship_timing, res.note_ja, res.status, res.exclusion,
        res.match_status, res.needs_review, res.review_items, res.evidence, res.verify_failures,
        run.extraction_job_id AS job_id, run.started_at,
        COALESCE(sm.line_posted_at, sm.received_at, sm.created_at) AS posted_at,
        sup.id AS supplier_id, COALESCE(sup.name, sup.line_name) AS supplier_name,
        prod.mark AS product_mark, prod.name AS product_name,
        cond.code AS condition_code, cond.canonical AS condition_canonical,
        unit_m.kubun AS unit_kubun,
        {_BLOCK_TEXT} AS blk,
        {_HEADING_TEXT} AS hd
"""

# 兆候の SQL 式。blk_rows の列だけを参照し、NULL は偽として扱う（COALESCE）。
SIGNAL_EXPRS: Final[dict[str, str]] = {
    # S1 完売の見落とし: In Stock なのに、書き写し・備考・ブロック本文に完売語がある
    "S1": (
        "COALESCE(status = 'In Stock' AND "
        "(COALESCE(raw_quantity, '') || ' ' || COALESCE(raw_price, '') || ' ' || "
        "COALESCE(raw_state, '') || ' ' || COALESCE(note_ja, '') || ' ' || COALESCE(blk, '')) "
        f"~* '{SOLD_OUT_REGEX}', FALSE)"
    ),
    # S2 予約の見落とし: 発送区分が空なのに、見出しかブロックに「予約」がある
    "S2": (
        "COALESCE(ship_offer_type IS NULL AND "
        "(position('予約' in COALESCE(hd, '')) > 0 OR position('予約' in COALESCE(blk, '')) > 0), FALSE)"
    ),
    # S3 単位による単品扱い: FLAG_SINGLE なのに、単位が単位マスタの「単品系」ではない
    #   （マスタに無い単位・none・空も「単品系ではない」に数える）
    "S3": (
        f"COALESCE(condition_code = '{FLAG_SINGLE_CONDITION_CODE}' AND "
        f"unit_kubun IS DISTINCT FROM '{SINGLE_UNIT_KUBUN}', FALSE)"
    ),
    # S4 短い記号での確定: matched で、根拠が品番・記号の部分一致（RAWCODE）、記号が2文字以下
    "S4": (
        "COALESCE(match_status = 'matched' AND evidence ->> 'basis' = 'RAWCODE' AND "
        f"char_length(product_mark) <= {SHORT_MARK_MAX_LEN}, FALSE)"
    ),
    # S5 見出しの商品名を照合していない: 見出しがあるのに unmatched / ambiguous
    "S5": (
        "COALESCE(heading_line_start IS NOT NULL AND match_status IN ('unmatched', 'ambiguous'), FALSE)"
    ),
    # S6 単位の補完: raw_unit が none ではないのに、ブロック本文（小文字・空白除去）に無い
    "S6": (
        "COALESCE(raw_unit <> 'none' AND "
        "position(lower(regexp_replace(raw_unit, '\\s', '', 'g')) in "
        "lower(regexp_replace(blk, '\\s', '', 'g'))) = 0, FALSE)"
    ),
}


# 投稿（job）ごとに最新の run だけを使う（posts の 1 行 = 1 投稿。detail と同じ選び方）。
LATEST_RUN_PER_JOB_SQL: Final[str] = (
    "run.id = (SELECT r2.id FROM public.extraction_shadow_runs r2 "
    "WHERE r2.extraction_job_id = run.extraction_job_id "
    "ORDER BY r2.started_at DESC, r2.id DESC LIMIT 1)"
)


def period_supplier_where(days: int, supplier_id: int | None) -> tuple[str, dict[str, int]]:
    """期間（run.started_at。days=0 は全期間）と仕入元の WHERE と、そのパラメータ。"""
    clauses = ["TRUE"]
    params: dict[str, int] = {}
    if days:
        clauses.append("run.started_at >= now() - make_interval(days => :days)")
        params["days"] = days
    if supplier_id is not None:
        clauses.append("sup.id = :supplier_id")
        params["supplier_id"] = supplier_id
    return " AND ".join(clauses), params


def flagged_cte(where_sql: str) -> str:
    """`WITH blk_rows AS (...), flagged AS (... s1〜s6 ...)`。後ろに SELECT を続ける。"""
    flag_cols = ", ".join(f"{SIGNAL_EXPRS[c]} AS {SIGNAL_COLUMNS[c]}" for c in SIGNAL_CODES)
    return (
        f"WITH blk_rows AS (SELECT {_ROW_COLUMNS} {_BASE_FROM} WHERE {where_sql}), "
        f"flagged AS (SELECT blk_rows.*, {flag_cols} FROM blk_rows)"
    )


def signal_count_selects() -> str:
    """集計用: `count(*) FILTER (WHERE s1) AS s1, ...`（summary と posts で共用）。"""
    return ", ".join(
        f"count(*) FILTER (WHERE {SIGNAL_COLUMNS[c]}) AS {SIGNAL_COLUMNS[c]}" for c in SIGNAL_CODES
    )
