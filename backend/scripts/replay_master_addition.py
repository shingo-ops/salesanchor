"""
マスタ追加の影響を「読むだけ」で試運転する（旧解析・新解析の両方）。

設計: docs/handoff/buyback-master-addition/design.md
recon: docs/handoff/buyback-master-addition/recon.md

入力: 商品マスタ CSV 取り込みと同じ形式（tcg_product_import_svc.parse_rows）の追加候補 CSV。
処理: 現在の有効マスタと「候補を足した版」を作り、過去の解析対象を前後で解き直して比べる。
  - legacy: tcg_analyzer_svc の match_pid_with_work（extraction_items を対象）
  - new   : extraction_judgement_svc.match_product
      (a) extraction_shadow_results の全ブロック（マスタ整備前に作られたもの）
      (b) 過去 N 日の LINE 原文（extraction_items の行範囲をブロックとして block_text で切り出す）
出力: JSON（標準出力、または --out）。いずれかの関門の件数が 0 でなければ終了コード 1。
DB: READ ONLY トランザクション。書き込みは一切しない。

使い方:
  python backend/scripts/replay_master_addition.py candidates.csv [--days 90] [--out result.json]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Iterable, Sequence
from contextlib import contextmanager
from dataclasses import dataclass

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.services import tcg_analyzer_svc as analyzer
from app.services.extraction_judgement_svc import (
    MatchResult,
    ProductEntry,
    block_text,
    match_product,
    normalize_for_match,
)
from app.services.extraction_shadow_svc import load_product_entries
from app.services.tcg_product_import_svc import parse_rows, split_keywords
from app.services.tcg_work_comparison_svc import match_item
from app.services.tcg_work_reference import load_work_reference

DEFAULT_DAYS = 90
DEFAULT_MIN_POPULATION = 1
PM_CODE_LIKE = re.compile(r"pm\d{4}")  # create_product の自動採番形式（PMxxxx）を正規化後の原文から探す
SAMPLE_LIMIT = 20
BOX_KUBUN_TYPES = frozenset({"箱系", "箱系大"})  # tcg_work_comparison_svc.compare の classes と同じ定義
FIRST_SYNTHETIC_ID = -1  # 候補には負の仮 ID を振る（実商品 ID と衝突しない）

OVERLAP_EQUAL = "equal"
OVERLAP_CONTAINED_IN = "contained_in_existing"
OVERLAP_CONTAINS = "contains_existing"

collapse_product_spaces = analyzer.collapse_product_spaces
normalize_en = analyzer.normalize_en

_DB_URL_RAW = os.environ.get("TCG_DB_URL", os.environ.get("DATABASE_URL", ""))
_DB_URL = _DB_URL_RAW.replace("postgresql+asyncpg", "postgresql+psycopg2").replace("asyncpg://", "psycopg2://")


@dataclass(frozen=True)
class Candidate:
    synthetic_id: int
    row_no: str
    japanese_title: str
    english_title: str
    mark: str
    work_code: str
    work_id: int | None
    category_class: str
    search_keywords: tuple[str, ...]
    exclude_keywords: tuple[str, ...]

    def entry(self) -> ProductEntry:
        # product_code は登録時に nextval('public.product_code_seq') で採番される（登録前は決まらない）ため None。
        # 自動採番コード（PMxxxx）の RAWCODE 当たりは meta.pm_code_like_raw_texts で実測する。
        return ProductEntry(
            id=self.synthetic_id,
            product_code=None,
            mark=self.mark or None,
            work_id=self.work_id,
            search_keywords=self.search_keywords,
            exclude_keywords=self.exclude_keywords,
        )


# ---------------------------------------------------------------------------
# 候補 CSV → Candidate
# ---------------------------------------------------------------------------


def build_candidates(
    rows: Sequence[dict[str, str]],
    work_ids_by_code: dict[str, int],
    category_class_by_code: dict[str, str],
) -> list[Candidate]:
    """CSV の行を Candidate にする。work_code が未登録なら work_id は None（関門1で検出）。"""
    return [
        Candidate(
            synthetic_id=FIRST_SYNTHETIC_ID - index,
            row_no=row.get("row_no", str(index + 1)),
            japanese_title=row.get("japanese_title", ""),
            english_title=row.get("english_title", ""),
            mark=row.get("mark", ""),
            work_code=row.get("work_code", ""),
            work_id=work_ids_by_code.get(row.get("work_code", "")),
            category_class=category_class_by_code.get(row.get("product_category_code", ""), ""),
            search_keywords=tuple(split_keywords(row.get("search_keywords", ""))),
            exclude_keywords=tuple(split_keywords(row.get("exclude_keywords", ""))),
        )
        for index, row in enumerate(rows)
    ]


# ---------------------------------------------------------------------------
# 関門1: 書き方の点検（system 共通）
# ---------------------------------------------------------------------------


def _kw_key(keyword: str) -> str:
    """tcg_keyword_lint.check_r3 と同じ正規化。"""
    return collapse_product_spaces(normalize_en(keyword))


def _overlap_kind(candidate_key: str, existing_key: str) -> str | None:
    if not candidate_key or not existing_key:
        return None
    if candidate_key == existing_key:
        return OVERLAP_EQUAL
    if candidate_key in existing_key:
        return OVERLAP_CONTAINED_IN
    if existing_key in candidate_key:
        return OVERLAP_CONTAINS
    return None


def check_work_ids(candidates: Iterable[Candidate], valid_work_ids: set[int]) -> list[dict]:
    """work_id が NULL または有効な作品でない候補（load_work_reference が例外を出す条件）。"""
    return [
        {"row_no": c.row_no, "title": c.japanese_title, "work_code": c.work_code, "work_id": c.work_id}
        for c in candidates
        if c.work_id is None or c.work_id not in valid_work_ids
    ]


def check_keyword_overlaps(candidates: Iterable[Candidate], existing_search_kw: dict[str, list[str]]) -> list[dict]:
    """候補の検索語が、既存商品の検索語と一致・被包含・包含するものを列挙する。"""
    existing = [(pid, kw, _kw_key(kw)) for pid, kws in existing_search_kw.items() for kw in kws]
    findings: list[dict] = []
    for cand in candidates:
        for cand_kw in cand.search_keywords:
            cand_key = _kw_key(cand_kw)
            for pid, kw, key in existing:
                kind = _overlap_kind(cand_key, key)
                if kind:
                    findings.append(
                        {"row_no": cand.row_no, "candidate_keyword": cand_kw,
                         "existing_product_id": pid, "existing_keyword": kw, "kind": kind}
                    )
    return findings


def run_gate1(
    candidates: Sequence[Candidate], valid_work_ids: set[int],
    existing_search_kw: dict[str, list[str]], file_errors: Sequence[str],
) -> dict:
    invalid = check_work_ids(candidates, valid_work_ids)
    overlaps = check_keyword_overlaps(candidates, existing_search_kw)
    return {
        "count": len(invalid) + len(overlaps) + len(file_errors),
        "file_errors": list(file_errors),
        "invalid_work_id": invalid,
        "keyword_overlaps": overlaps,
    }


# ---------------------------------------------------------------------------
# 旧解析（legacy）: match_pid_with_work
# ---------------------------------------------------------------------------


def with_candidates_legacy_context(context: dict, candidates: Sequence[Candidate]) -> dict:
    """現行マスタの legacy コンテキストに候補を足した新しい辞書を返す（元は変えない）。"""
    ids = {str(c.synthetic_id): c.synthetic_id for c in candidates}
    return {
        **context,
        "product_ids": {**context["product_ids"], **ids},
        "search": {**context["search"], **{str(c.synthetic_id): list(c.search_keywords) for c in candidates}},
        "exclude": {**context["exclude"], **{str(c.synthetic_id): list(c.exclude_keywords) for c in candidates}},
        "work_ids": {**context["work_ids"],
                     **{str(c.synthetic_id): (str(c.work_id) if c.work_id is not None else None) for c in candidates}},
        "classes": {**context["classes"], **{str(c.synthetic_id): c.category_class for c in candidates}},
    }


def legacy_work_id(item: dict, raw_text: str, works: list[dict]) -> str | None:
    """保存済みの resolved_work_id があればそれ、無ければ原文の作品名証拠（tcg_work_comparison_svc.old_work と同じ分岐）。"""
    if item.get("resolved_work_id") is not None:
        return str(item["resolved_work_id"])
    return analyzer.resolve_work_evidence(
        item["raw_product_name"], raw_text, item["line_start"], item["line_end"],
        item.get("raw_work_name"), item.get("raw_work_source_line_span"), works,
    )


def _legacy_signature(result: dict) -> tuple:
    return (result["product_id"], result["pid_resolved"], tuple(result["candidates"]))


def replay_legacy(
    items: Sequence[dict], raw_texts: dict[str, str], works: list[dict],
    before_ctx: dict, after_ctx: dict,
) -> dict:
    changes: list[dict] = []
    for item in items:
        work_id = legacy_work_id(item, raw_texts[item["source_id"]], works)
        before = match_item(item, work_id, before_ctx)
        after = match_item(item, work_id, after_ctx)
        if _legacy_signature(before) != _legacy_signature(after):
            changes.append({"item_id": str(item["id"]), "raw_product_name": item["raw_product_name"],
                            "work_id": work_id, "before": before, "after": after})
    return {"population": len(items), "changed_count": len(changes), "changes": changes}


# ---------------------------------------------------------------------------
# 新解析（new）: extraction_judgement_svc.match_product
# ---------------------------------------------------------------------------


def _new_signature(result: MatchResult) -> tuple:
    return (result.status, result.product_id)


def _new_view(result: MatchResult) -> dict:
    return {"status": result.status, "product_id": result.product_id, "candidates": list(result.candidates)}


def replay_new(blocks: Sequence[dict], before: Sequence[ProductEntry], after: Sequence[ProductEntry]) -> dict:
    """blocks: {"id", "text"}。status（matched/ambiguous/unmatched）の遷移と product_id の変化を変化として数える。"""
    changes: list[dict] = []
    for block in blocks:
        before_result = match_product(block["text"], before)
        after_result = match_product(block["text"], after)
        if _new_signature(before_result) != _new_signature(after_result):
            changes.append({"block_id": block["id"], "before": _new_view(before_result),
                            "after": _new_view(after_result)})
    return {"population": len(blocks), "changed_count": len(changes), "changes": changes}


# ---------------------------------------------------------------------------
# 関門3: 過去の原文に候補の名前・ワード・コードが出たか
# ---------------------------------------------------------------------------


def _normalized_terms(candidate: Candidate) -> list[str]:
    names = (candidate.japanese_title, candidate.english_title, candidate.mark)
    return [n for n in (normalize_for_match(v) for v in names) if n]


def new_system_hit(raw_text: str, candidate: Candidate) -> bool:
    """新解析の照合規則（match_product＝AND ワード・品番）または名前・型番の正規化一致で当たるか。"""
    nb = normalize_for_match(raw_text)
    if any(term in nb for term in _normalized_terms(candidate)):
        return True
    return match_product(raw_text, [candidate.entry()]).status != "unmatched"


def legacy_system_hit(raw_text: str, candidate: Candidate) -> bool:
    """旧解析の照合規則（normalize_en＋検索語照合）または名前・型番の正規化一致で当たるか。"""
    norm = normalize_en(raw_text)
    names = (candidate.japanese_title, candidate.english_title, candidate.mark)
    if any(n and normalize_en(n) in norm for n in names):
        return True
    return any(kw and analyzer.match_product_search_keyword(kw, norm) for kw in candidate.search_keywords)


def count_raw_text_hits(raw_texts: dict[str, str], candidates: Sequence[Candidate], hit_fn) -> dict:
    hits: list[dict] = []
    for source_id, raw in raw_texts.items():
        rows = [c.row_no for c in candidates if hit_fn(raw, c)]
        if rows:
            hits.append({"source_message_id": source_id, "candidate_rows": rows})
    return {"population": len(raw_texts), "count": len(hits), "samples": hits[:SAMPLE_LIMIT]}


# ---------------------------------------------------------------------------
# レポート組み立て
# ---------------------------------------------------------------------------


def population_gate(inputs: dict, min_population: int) -> dict:
    """再生対象が min_population 未満（0 を含む）なら不合格。空の母集団を「変化 0 件」と誤認しないための関門。"""
    populations = {
        "legacy_items": len(inputs["items"]),
        "new_shadow_blocks": len(inputs["shadow_blocks"]),
        "new_raw_message_blocks": len(inputs["message_blocks"]),
        "raw_texts": len(inputs["raw_texts"]),
    }
    return {
        "min_population": min_population,
        "populations": populations,
        "below_minimum": sorted(name for name, n in populations.items() if n < min_population),
        "dropped_items_missing_source": inputs.get("dropped_items_missing_source", 0),
    }


def count_pm_code_like(raw_texts: dict[str, str]) -> int:
    """PMxxxx 形式の文字列を含む原文の件数（自動採番コードの RAWCODE 誤当たりリスクの実測。報告のみ）。"""
    return sum(1 for raw in raw_texts.values() if PM_CODE_LIKE.search(normalize_for_match(raw)))


def build_report(
    *, candidates: Sequence[Candidate], gate1: dict, legacy: dict, new_shadow: dict, new_raw: dict,
    legacy_gate3: dict, new_gate3: dict, days: int, pop_gate: dict, pm_code_like_texts: int,
) -> dict:
    counts = {
        "gate1": gate1["count"],
        "legacy_gate2": legacy["changed_count"],
        "legacy_gate3": legacy_gate3["count"],
        "new_gate2_shadow_results_pre_maintenance": new_shadow["changed_count"],
        "new_gate2_raw_message_blocks": new_raw["changed_count"],
        "new_gate3": new_gate3["count"],
        "population_gate": len(pop_gate["below_minimum"]),
    }
    return {
        "meta": {"days": days, "candidate_count": len(candidates), "pm_code_like_raw_texts": pm_code_like_texts},
        "population_gate": pop_gate,
        "gate1": gate1,
        "legacy": {"gate2": legacy, "gate3": legacy_gate3},
        "new": {
            "gate2_shadow_results_pre_maintenance": new_shadow,
            "gate2_raw_message_blocks": new_raw,
            "gate3": new_gate3,
        },
        "gate_counts": counts,
        "exit_code": 1 if any(v > 0 for v in counts.values()) else 0,
    }


def evaluate(
    *, candidates: Sequence[Candidate], file_errors: Sequence[str], days: int, inputs: dict,
    min_population: int = DEFAULT_MIN_POPULATION,
) -> dict:
    """DB を読まない中核。inputs は load_inputs が返す辞書（テストでは手で組む）。"""
    after_ctx = with_candidates_legacy_context(inputs["legacy_context"], candidates)
    after_entries = [*inputs["entries"], *(c.entry() for c in candidates)]
    gate1 = run_gate1(candidates, inputs["valid_work_ids"], inputs["legacy_context"]["search"], file_errors)
    return build_report(
        candidates=candidates, gate1=gate1, days=days,
        legacy=replay_legacy(inputs["items"], inputs["raw_texts"], inputs["works"],
                             inputs["legacy_context"], after_ctx),
        new_shadow=replay_new(inputs["shadow_blocks"], inputs["entries"], after_entries),
        new_raw=replay_new(inputs["message_blocks"], inputs["entries"], after_entries),
        legacy_gate3=count_raw_text_hits(inputs["raw_texts"], candidates, legacy_system_hit),
        new_gate3=count_raw_text_hits(inputs["raw_texts"], candidates, new_system_hit),
        pop_gate=population_gate(inputs, min_population),
        pm_code_like_texts=count_pm_code_like(inputs["raw_texts"]),
    )


# ---------------------------------------------------------------------------
# DB 読み取り（READ ONLY）
# ---------------------------------------------------------------------------

_POSTED_AT = "COALESCE(s.line_posted_at, s.received_at, s.created_at)"

_ITEMS_SQL = f"""
    SELECT i.id, i.extraction_job_id, i.line_start, i.line_end, i.raw_product_name, i.raw_unit,
           i.raw_state, i.raw_memo, i.raw_work_name, i.raw_work_source_line_span, i.resolved_work_id,
           s.id AS source_id
    FROM public.extraction_items i
    JOIN public.extraction_jobs j ON j.id = i.extraction_job_id
    JOIN public.source_messages s ON s.id = j.source_message_id
    WHERE s.is_active AND s.superseded_by IS NULL AND j.status = 'done'
      AND i.raw_product_name IS NOT NULL AND i.line_start IS NOT NULL AND i.line_end IS NOT NULL
      AND {_POSTED_AT} >= now() - make_interval(days => :days)
"""

_SOURCES_SQL = f"""
    SELECT s.id, s.raw_text FROM public.source_messages s
    WHERE s.is_active AND s.superseded_by IS NULL AND {_POSTED_AT} >= now() - make_interval(days => :days)
"""

_SHADOW_SQL = """
    SELECT r.id, r.line_start, r.line_end, s.raw_text
    FROM public.extraction_shadow_results r
    JOIN public.extraction_shadow_runs u ON u.id = r.run_id
    JOIN public.extraction_jobs j ON j.id = u.extraction_job_id
    JOIN public.source_messages s ON s.id = j.source_message_id
    WHERE r.line_start IS NOT NULL AND r.line_end IS NOT NULL
"""


@contextmanager
def open_readonly_session(engine):
    """READ ONLY トランザクション＋運営者コンテキスト（他の public 読み取りと同じ SET LOCAL）。"""
    with Session(engine) as session:
        session.execute(text("SET TRANSACTION READ ONLY"))
        session.execute(text("SET LOCAL app.is_operator = 'true'"))
        if session.execute(text("SHOW transaction_read_only")).scalar_one() != "on":
            raise RuntimeError("READ_ONLY_NOT_ACTIVE")
        try:
            yield session
        finally:
            session.rollback()


def load_candidate_lookups(session: Session) -> tuple[dict[str, int], dict[str, str]]:
    """work_code→work_id と product_category_code→category_class（tcg_product_import_svc の同名ローダは async 専用のため sync で引く）。"""
    works = {str(r[0]): int(r[1]) for r in session.execute(
        text("SELECT code, id FROM public.type_master WHERE is_active = TRUE")).fetchall()}
    classes = {str(r[0]): ("Box" if r[1] in BOX_KUBUN_TYPES else "") for r in session.execute(
        text("SELECT code, kubun_type FROM public.tcg_product_categories WHERE is_active = TRUE")).fetchall()}
    return works, classes


def load_legacy_context(session: Session) -> tuple[dict, set[int]]:
    """tcg_work_comparison_svc.read_snapshot の context と同じ形（と有効な作品 ID 集合）を、既存ローダで組む。"""
    product_ids, _, _, _, _, units = analyzer.load_lookup_maps(session)
    search, exclude = analyzer.load_product_keywords(session)
    categories = analyzer.load_product_kubun_type_map(session)
    fallback = {str(r[0]): r[1] or "" for r in session.execute(
        text("SELECT id, category_class FROM public.products WHERE is_active = TRUE")).fetchall()}
    reference = load_work_reference(session, "public")
    return {
        "product_ids": product_ids, "units": units, "search": search, "exclude": exclude,
        "categories": categories, "normalization": analyzer.load_normalization_rules(session),
        "work_ids": {str(p["id"]): (str(p["work_id"]) if p["work_id"] is not None else None)
                     for p in reference["products"]},
        "classes": {pid: ("Box" if categories[pid] in BOX_KUBUN_TYPES else "") if pid in categories
                    else fallback.get(pid, "") for pid in product_ids},
    }, {int(w["id"]) for w in reference["works"]}


def _message_blocks(items: Sequence[dict], raw_texts: dict[str, str]) -> list[dict]:
    """extraction_items の行範囲（メッセージごとに重複除去）を block_text で切り出したブロック。"""
    spans = sorted({(str(i["source_id"]), i["line_start"], i["line_end"]) for i in items})
    return [{"id": f"{sid}:{ls}-{le}", "text": block_text(raw_texts[sid], ls, le)} for sid, ls, le in spans]


def load_inputs(session: Session, days: int) -> dict:
    params = {"days": days}
    legacy_context, valid_work_ids = load_legacy_context(session)
    items = [dict(r._mapping) for r in session.execute(text(_ITEMS_SQL), params).fetchall()]
    raw_texts = {str(r[0]): r[1] for r in session.execute(text(_SOURCES_SQL), params).fetchall()}
    all_items = [{**i, "source_id": str(i["source_id"])} for i in items]
    items = [i for i in all_items if i["source_id"] in raw_texts]
    shadow_blocks = [
        {"id": str(r[0]), "text": block_text(r[3], r[1], r[2])}
        for r in session.execute(text(_SHADOW_SQL)).fetchall()
    ]
    return {
        "legacy_context": legacy_context, "valid_work_ids": valid_work_ids,
        "entries": load_product_entries(session), "works": analyzer.load_work_master(session),
        "items": items, "raw_texts": raw_texts, "message_blocks": _message_blocks(items, raw_texts),
        "shadow_blocks": shadow_blocks, "dropped_items_missing_source": len(all_items) - len(items),
    }


# ---------------------------------------------------------------------------
# エントリポイント
# ---------------------------------------------------------------------------


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="マスタ追加の影響を読み取り専用で試運転する")
    parser.add_argument("csv", help="追加候補の CSV（商品マスタ CSV 取り込みと同じ形式）")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS, help=f"過去何日を対象にするか（既定 {DEFAULT_DAYS}）")
    parser.add_argument("--min-population", type=int, default=DEFAULT_MIN_POPULATION,
                        help=f"各再生対象の最小件数。下回る（0 を含む）と不合格（既定 {DEFAULT_MIN_POPULATION}）")
    parser.add_argument("--out", help="JSON の出力先（省略時は標準出力）")
    return parser.parse_args(argv)


def write_report(report: dict, out: str | None) -> None:
    payload = json.dumps(report, ensure_ascii=False, indent=2, default=str)
    if out:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(payload)
    else:
        print(payload)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if not _DB_URL:
        print("TCG_DB_URL も DATABASE_URL も設定されていません。", file=sys.stderr)
        return 2
    with open(args.csv, "rb") as fh:
        rows, file_errors = parse_rows(fh.read())
    engine = create_engine(_DB_URL, echo=False)
    try:
        with open_readonly_session(engine) as session:
            work_ids, classes = load_candidate_lookups(session)
            candidates = build_candidates(rows, work_ids, classes)
            inputs = load_inputs(session, args.days)
    finally:
        engine.dispose()
    report = evaluate(candidates=candidates, file_errors=file_errors, days=args.days, inputs=inputs,
                      min_population=args.min_population)
    write_report(report, args.out)
    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
