"""旧解析 v6 の投稿を、新解析 v102 でやり直す道具（一度きりの作業用）。

設計: docs/handoff/reextract-v6-with-v102/design.md（r5 APPROVE）
既存のコードは変えない。既存の関数を import して、決まった順に呼ぶだけ。

モード
  （既定）dry-run        対象と除外の内訳を出し、--out-dir に order.txt・excluded.tsv を書く。DB には書かない。
  --execute              1件ずつ直列にやり直す（--job-id / --limit / --max-cost-usd / --stop-after-errors / --timeout-sec）。
  --repair --ids-file F  F（処理順の一覧）の件を直す。unreadable は2回まで再抽出、解析の取り残しは再解析、
                         v102 の件すべてに _merge_supplier_products(extra_pairs=pairs) をかける（冪等・Gemini は呼ばない）。
  --rollback-from DIR    DIR の控え（CSV）から v6 に戻す。既定は dry-run、--execute のときだけ書く。--job-id で job を選べる。

--out-dir の中身
  order.txt / excluded.tsv / records.jsonl / started_at.txt / repair_counts.json / pairs/<job_id>.json
  pairs/ はここ1か所だけ（--repair もここを読む。--rollback-from は v102 の組をその場で読むので pairs/ は使わない）。

控え（DIR）の CSV は psql の \\copy で作る。FORCE_QUOTE * で書き、NULL だけ引用符なしの空にする（空文字列・`\\N` と区別するため）。
  extraction_jobs.csv    : SELECT * FROM public.extraction_jobs  WHERE id = ANY(対象)
  extraction_items.csv   : SELECT * FROM public.extraction_items WHERE extraction_job_id = ANY(対象)
  analysis_results.csv   : SELECT ar.* FROM public.analysis_results ar JOIN public.extraction_items ei
                           ON ei.id = ar.extraction_item_id WHERE ei.extraction_job_id = ANY(対象)
  いずれも TO '<file>' WITH (FORMAT csv, HEADER true, FORCE_QUOTE *)

終了コード: 0 = 済んだ / 1 = --rollback-from で rollback_error の job がある / 2 = 始める前の確かめに失敗・引数の誤り /
  3 = 上限（費用・連続の失敗）で止まった / 4 = 最後まで回ったが失敗（gemini_error 等）が残っている。
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import sys
import time
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services import gemini_extraction_svc as gem
from app.services import line_analysis_v102_svc as svc
from app.services import tcg_analyzer_svc as analyzer
from app.tasks import tcg_extraction as extraction

logger = logging.getLogger(__name__)

V6_PROMPT_VERSION = "raw-extraction-v6-rawcode-p1"
TARGET_STATUSES = ("done", "empty", "error")
EXIT_OK = 0
EXIT_CONFIG = 2
EXIT_LIMIT = 3
EXIT_RESIDUAL = 4  # 最後まで回ったが、失敗した件が残っている（ループは次の回へ進む）
EXIT_ROLLBACK_ERROR = 1  # --rollback-from --execute で失敗した job がある
RESIDUAL_CATEGORIES = frozenset({"gemini_error", "analysis_error", "unreadable", "repair_exhausted", "pairs_error"})
REPAIR_MAX_PER_JOB = 2  # unreadable の再抽出は1件あたりここまで
ALARM_MARGIN_SEC = 30  # 予備の時間切れ = timeout-sec + これ（300 秒なら 330 秒）
FAILURE_CATEGORIES = frozenset({"unreadable", "gemini_error", "analysis_error", "pairs_error"})


class GeminiTimeout(BaseException):
    """予備の時間切れ。BaseException の子にして、台帳などの `except Exception` に飲まれないようにする。"""


# ---------------------------------------------------------------------------
# 時間切れ
# ---------------------------------------------------------------------------


@contextmanager
def alarm_guard(seconds: int):
    """signal.alarm による予備の時間切れ。戻ったら（例外でも）すぐ alarm(0) にする。"""

    def _handler(_signum, _frame):
        raise GeminiTimeout(f"alarm {seconds}s")

    previous = signal.signal(signal.SIGALRM, _handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


def build_genai_client(timeout_sec: int):
    """gemini_extraction_svc._get_genai_client と同じ作りに、HttpOptions(timeout=ミリ秒) を足した client。

    既存ファイルは変えない。install_gemini_timeout がこのプロセスの中だけで差し替える。
    """
    from google import genai  # noqa: PLC0415
    from google.genai import types as genai_types  # noqa: PLC0415

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY が未設定です。")
    options: dict = {"timeout": int(timeout_sec * 1000)}
    proxy_url = os.getenv("GEMINI_PROXY_URL", "").strip()
    if proxy_url:
        options["client_args"] = {"proxy": proxy_url}
        options["async_client_args"] = {"proxy": proxy_url}
    return genai.Client(api_key=api_key, http_options=genai_types.HttpOptions(**options))


def install_gemini_timeout(timeout_sec: int) -> None:
    """このプロセスの中だけ、Gemini client の作り方を時間切れ付きに差し替える（gemini_raw_copy_v8 は属性経由で呼ぶ）。"""
    gem._get_genai_client = lambda: build_genai_client(timeout_sec)  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# 小物
# ---------------------------------------------------------------------------


def new_session() -> Session:
    return extraction._get_sync_session()


def schema() -> str:
    return analyzer.TCG_SCHEMA


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fsync_dir(path: Path) -> None:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_text_durable(path: Path, content: str) -> None:
    """書いて fsync してから置き換える。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(content)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    _fsync_dir(path.parent)


def write_pairs(out_dir: Path, job_id: str, pairs: list[tuple[int, int]]) -> None:
    write_text_durable(out_dir / "pairs" / f"{job_id}.json", json.dumps([[p, c] for p, c in pairs]))


def write_current_pairs(out_dir: Path, job_id: str, current_pairs: list[tuple[int, int]] | None) -> None:
    """ADR-1032: 抽出の前に現行だった組を pairs/ の隣（current_pairs/）に残す。None（前の行が無い）は書かない。"""
    if current_pairs is None:
        return
    write_text_durable(out_dir / "current_pairs" / f"{job_id}.json", json.dumps([[p, c] for p, c in current_pairs]))


def read_current_pairs(out_dir: Path, job_id: str) -> list[tuple[int, int]] | None:
    path = out_dir / "current_pairs" / f"{job_id}.json"
    if not path.exists():
        return None
    return [(int(p), int(c)) for p, c in json.loads(path.read_text(encoding="utf-8"))]


def read_pairs(out_dir: Path, job_id: str) -> list[tuple[int, int]] | None:
    path = out_dir / "pairs" / f"{job_id}.json"
    if not path.exists():
        return None
    return [(int(p), int(c)) for p, c in json.loads(path.read_text(encoding="utf-8"))]


def ensure_started_at(out_dir: Path) -> datetime:
    """最初の開始時刻を保存して返す（2回目以降は保存済みを読む）。"""
    path = out_dir / "started_at.txt"
    if not path.exists():
        write_text_durable(path, now_iso() + "\n")
    return datetime.fromisoformat(path.read_text(encoding="utf-8").strip())


def append_record(out_dir: Path, record: dict) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False)
    with open(out_dir / "records.jsonl", "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    print(line, flush=True)


def append_line_durable(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def read_ids_file(path: Path) -> list[str]:
    return [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


# ---------------------------------------------------------------------------
# D2 始める前の確かめ
# ---------------------------------------------------------------------------


def preflight(session: Session) -> list[str]:
    """違いの一覧（空なら OK）。"""
    problems: list[str] = []
    if svc.get_engine() != svc.ENGINE_V102:
        problems.append(f"{svc.ENGINE_ENV} が {svc.ENGINE_V102} ではありません（{svc.get_engine()}）")
    try:
        if not svc.load_prompt_from_db(session, svc.V102_PROMPT_KEY):
            problems.append("本番の指示書が空です")
    except Exception as exc:  # noqa: BLE001
        session.rollback()
        problems.append(f"本番の指示書が読めません: {type(exc).__name__}")
    try:
        count = session.execute(
            text(
                "SELECT count(*) FROM public.knowledge_rules WHERE is_active = TRUE "
                "AND category IN ('message_exclude', 'message_exclude_no_digit')"
            )
        ).scalar_one()
        if int(count) < 1:
            problems.append("knowledge_rules の除外系が 0 件です（読めずに素通りさせない）")
    except Exception as exc:  # noqa: BLE001
        session.rollback()
        problems.append(f"knowledge_rules が読めません: {type(exc).__name__}")
    return problems


def _report_problems(problems: list[str]) -> int:
    for p in problems:
        print(f"確かめに失敗: {p}", file=sys.stderr)
    return EXIT_CONFIG


# ---------------------------------------------------------------------------
# D3 対象の選び方
# ---------------------------------------------------------------------------


def classify_v6_jobs(session: Session, *, with_prefilter: bool, only_job: str | None = None):
    """v6 の job をすべて読み、(処理順の [(job_id, source_message_id)], 除外の [(job_id, 理由)]) を返す。"""
    s = schema()
    rows = session.execute(
        text(
            f"""
            SELECT ej.id::text, ej.source_message_id::text, ej.status, (sm.received_at IS NULL) AS recv_null,
                   EXISTS (SELECT 1 FROM {s}.item_corrections ic WHERE ic.source_message_id = ej.source_message_id) AS has_corr
            FROM {s}.extraction_jobs ej
            JOIN {s}.source_messages sm ON sm.id = ej.source_message_id
            WHERE ej.prompt_version = :v6
            ORDER BY sm.line_posted_at ASC NULLS LAST, ej.id
            """
        ),
        {"v6": V6_PROMPT_VERSION},
    ).fetchall()
    targets: list[tuple[str, str]] = []
    excluded: list[tuple[str, str]] = []
    for job_id, smid, status, recv_null, has_corr in rows:
        if only_job is not None and job_id != only_job:
            continue
        if status not in TARGET_STATUSES:
            excluded.append((job_id, "filtered" if status == "filtered" else f"status_{status}"))
        elif recv_null:
            excluded.append((job_id, "received_at_null"))
        elif has_corr:
            excluded.append((job_id, "item_corrections"))
        elif with_prefilter:
            ctx = extraction.load_extraction_context(session, job_id)
            if ctx is None:
                excluded.append((job_id, "no_context"))
            elif extraction._apply_pre_extraction_filter(session, ctx.raw_text) is not None:
                excluded.append((job_id, "prefilter"))
            else:
                targets.append((job_id, smid))
        else:
            targets.append((job_id, smid))
    return targets, excluded


def dry_run(out_dir: Path, only_job: str | None) -> int:
    with new_session() as session:
        problems = preflight(session)
        if problems:
            return _report_problems(problems)
        targets, excluded = classify_v6_jobs(session, with_prefilter=True, only_job=only_job)
        session.rollback()
    started = (out_dir / "started_at.txt").exists()
    order_name = "order.dryrun.txt" if started else "order.txt"  # 実行中の order.txt（費用の集計に使う）を上書きしない
    write_text_durable(out_dir / order_name, "".join(f"{j}\n" for j, _ in targets))
    excluded_name = "excluded.dryrun.tsv" if (out_dir / "excluded.tsv").exists() else "excluded.tsv"  # 最初の一覧を守る
    write_text_durable(out_dir / excluded_name, "".join(f"{j}\t{r}\n" for j, r in excluded))
    print(f"対象 {len(targets)} 件 / 除外 {len(excluded)} 件 {dict(Counter(r for _, r in excluded))}")
    print("最初の10件:")
    for job_id, _ in targets[:10]:
        print(f"  {job_id}")
    print(f"書いた: {out_dir / order_name}, {out_dir / excluded_name}")
    return EXIT_OK


# ---------------------------------------------------------------------------
# 費用
# ---------------------------------------------------------------------------


def total_cost(session: Session, job_ids: list[str], since: datetime) -> tuple[Decimal, int]:
    """(cost_usd の合計, cost_usd が NULL の件数)。台帳の source_ref と、最初の開始時刻以降の occurred_at で数える。"""
    refs = [f"extraction_job:{j}" for j in job_ids]
    row = session.execute(
        text(
            "SELECT COALESCE(sum(cost_usd), 0), count(*) FILTER (WHERE cost_usd IS NULL) "
            "FROM public.llm_usage_events WHERE source_ref = ANY(:refs) AND occurred_at >= :since"
        ),
        {"refs": refs, "since": since},
    ).one()
    return Decimal(row[0]), int(row[1])


# ---------------------------------------------------------------------------
# 1件の処理
# ---------------------------------------------------------------------------


def read_job_state(job_id: str) -> dict | None:
    """新しい session で job を読み直す（例外のあとの区分決めに使う）。"""
    s = schema()
    with new_session() as session:
        row = session.execute(
            text(
                f"""
                SELECT ej.prompt_version, ej.status, ej.review_reasons,
                       (SELECT count(*) FROM {s}.extraction_items ei WHERE ei.extraction_job_id = ej.id) AS items,
                       (SELECT count(*) FROM {s}.analysis_results ar
                          JOIN {s}.extraction_items ei ON ei.id = ar.extraction_item_id
                         WHERE ei.extraction_job_id = ej.id) AS results,
                       EXISTS (SELECT 1 FROM {s}.item_corrections ic WHERE ic.source_message_id = ej.source_message_id) AS corr
                FROM {s}.extraction_jobs ej WHERE ej.id = :ej
                """
            ),
            {"ej": job_id},
        ).first()
        session.rollback()
    if row is None:
        return None
    reasons = (row.review_reasons or "").split(svc.REASON_SEPARATOR)
    return {
        "prompt_version": row.prompt_version, "status": row.status, "reasons": reasons,
        "items": int(row.items), "results": int(row.results), "corrections": bool(row.corr),
        "v102": svc.is_v102_prompt_version(row.prompt_version),
    }


def _merge_pairs(job_id: str, pairs: list[tuple[int, int]],
                 current_pairs: list[tuple[int, int]] | None = None) -> str | None:
    """控えた組を付け直す（冪等）。item_corrections があれば飛ばして "skip_merge"。失敗は "merge_error"。成功は None。"""
    state = read_job_state(job_id)
    if state is not None and state["corrections"]:
        return "skip_merge"
    with new_session() as session:
        try:
            analyzer._merge_supplier_products(
                session, job_id, schema(), extra_pairs=pairs, prior_current_pairs=current_pairs,  # ADR-1032
            )
            session.commit()  # 変更が0件だと関数の中では commit しないため、必ず自分で commit する
        except Exception:  # noqa: BLE001
            session.rollback()
            logger.exception("[reextract] 付け直しに失敗: job=%s", job_id)
            return "merge_error"
    return None


def finish_after_extraction(job_id: str, pairs: list[tuple[int, int]], *, run_analysis: bool = True,
                            current_pairs: list[tuple[int, int]] | None = None) -> tuple[str, str]:
    """D4-6〜8。抽出が確定した（v102 になった）job の、区分決め・解析・付け直し。(区分, 注記) を返す。"""
    state = read_job_state(job_id)
    if state is None or not state["v102"]:
        return "gemini_error", "v102 になっていません"
    note = ""
    category = "done" if state["status"] == "done" else "empty"
    if svc.REASON_RESPONSE_UNREADABLE in state["reasons"]:
        category = "unreadable"  # 解析は飛ばす（読めなかった理由を上書きしない）。組は下で付け直す
    elif run_analysis:
        with new_session() as session:
            try:
                svc.run_v102_analysis(session, job_id)
            except Exception as exc:  # noqa: BLE001
                session.rollback()
                logger.exception("[reextract] 解析が例外: job=%s", job_id)
                category, note = "analysis_error", f"exception:{type(exc).__name__}"
        after = read_job_state(job_id)
        if after is not None and svc.REASON_EXTRACT_EXCEPTION in after["reasons"]:
            category, note = "analysis_error", svc.REASON_EXTRACT_EXCEPTION
    merge_result = _merge_pairs(job_id, pairs, current_pairs)
    if merge_result == "merge_error":
        category, note = "analysis_error", "merge_error"
    elif merge_result == "skip_merge" and category in ("done", "empty"):
        category, note = "skip_merge", "item_corrections あり"
    return category, note


def extract_one(job_id: str, timeout_sec: int) -> tuple[str | None, str]:
    """D4-4〜5。時間切れ付きで Gemini 段を呼ぶ。失敗なら ("gemini_error", 注記)、確定したら (None, "")。"""
    session = new_session()
    error: str | None = None
    try:
        with alarm_guard(timeout_sec + ALARM_MARGIN_SEC):
            svc.run_v102_extraction(session, job_id)
    except GeminiTimeout:
        error = "timeout"
    except Exception as exc:  # noqa: BLE001
        error = f"exception:{type(exc).__name__}"
    finally:
        try:
            if error is not None:
                session.rollback()
        finally:
            session.close()
    if error is None:
        return None, ""
    # 例外のあとは session を捨て、読み直す。v102 なら確定後の例外として先へ進む
    state = read_job_state(job_id)
    if state is not None and state["v102"]:
        return None, f"確定後の例外:{error}"
    return "gemini_error", error


def process_job(job_id: str, out_dir: Path, timeout_sec: int) -> tuple[str, str]:
    """D4 の1件（execute）。(区分, 注記)。"""
    # 2. 除外の判定をもう一度
    state = read_job_state(job_id)
    if state is None or state["prompt_version"] != V6_PROMPT_VERSION:
        return "skip_not_v6", ""
    if state["corrections"]:
        return "skip_corrections", ""
    rolled = out_dir / "rolled_back.txt"
    if rolled.exists() and job_id in read_ids_file(rolled):
        return "skip_rolled_back", "--rollback-from で v6 に戻した job"
    with new_session() as session:
        ctx = extraction.load_extraction_context(session, job_id)
        if ctx is None:
            session.rollback()
            return "skip_no_context", ""
        hit = extraction._apply_pre_extraction_filter(session, ctx.raw_text)
        # 3. v6 の組を控える（読み取りのみ）
        pairs = svc._load_resolved_pairs(session, job_id) if hit is None else []
        # ADR-1032: 現行だった組も控える（前の行が無ければ None＝控え無し）
        current_pairs = svc._load_current_pairs(session, job_id) if pairs else None
        session.rollback()
    if hit is not None:
        return "skip_prefilter", str(hit)
    try:  # 書いて fsync してから抽出に進む。書けなければ抽出しない
        write_pairs(out_dir, job_id, pairs)
        write_current_pairs(out_dir, job_id, current_pairs)
    except OSError as exc:
        return "pairs_error", type(exc).__name__
    # 4〜5
    failure, note = extract_one(job_id, timeout_sec)
    if failure is not None:
        return failure, note
    # 6〜8
    category, note2 = finish_after_extraction(job_id, pairs, current_pairs=current_pairs)
    return category, "; ".join(x for x in (note, note2) if x)


def record_of(mode: str, job_id: str, category: str, note: str, seconds: float, cost: Decimal | None) -> dict:
    return {
        "ts": now_iso(), "mode": mode, "job_id": job_id, "category": category, "note": note,
        "seconds": round(seconds, 2), "cost_total_usd": None if cost is None else float(cost),
    }


class _Budget:
    """費用の上限・連続の失敗の上限を見る。費用は order.txt の job の台帳を、最初の開始時刻以降で毎回数える。"""

    def __init__(self, out_dir: Path, max_cost: Decimal, stop_after_errors: int):
        self.max_cost = max_cost
        self.stop_after_errors = stop_after_errors
        self.consecutive = 0
        self.since = ensure_started_at(out_dir)
        order = out_dir / "order.txt"
        self.job_ids = read_ids_file(order) if order.exists() else []

    def check_cost(self) -> tuple[Decimal, str | None]:
        """(累計, 止める理由)。"""
        with new_session() as session:
            total, nulls = total_cost(session, self.job_ids, self.since)
            session.rollback()
        if nulls > 0:
            return total, f"cost_usd が NULL の行が {nulls} 件あります"
        if total >= self.max_cost:
            return total, f"費用が上限に達しました（{total} >= {self.max_cost}）"
        return total, None

    def after(self, category: str) -> str | None:
        self.consecutive = self.consecutive + 1 if category in FAILURE_CATEGORIES else 0
        if self.consecutive >= self.stop_after_errors:
            return f"連続の失敗が {self.consecutive} 回になりました"
        return None


def summarize(counter: Counter) -> None:
    print("集計: " + json.dumps(dict(counter), ensure_ascii=False))


def _is_work(category: str) -> bool:
    """Gemini か DB を実際に動かした区分（skip_* は除く。skip_merge は抽出まで済んでいる）。"""
    return not category.startswith(("skip_", "repair_")) or category == "skip_merge"


def execute(out_dir: Path, *, only_job: str | None, limit: int | None, max_cost: Decimal, stop_after_errors: int,
            timeout_sec: int) -> int:
    with new_session() as session:
        problems = preflight(session)
        if problems:
            return _report_problems(problems)
        targets, excluded = classify_v6_jobs(session, with_prefilter=False, only_job=only_job)
        session.rollback()
    out_dir.mkdir(parents=True, exist_ok=True)
    narrowed = only_job is not None or limit is not None
    if not narrowed and not (out_dir / "order.txt").exists():  # 全件の実行だけが一覧を作る
        write_text_durable(out_dir / "order.txt", "".join(f"{j}\n" for j, _ in targets))
        write_text_durable(out_dir / "excluded.tsv", "".join(f"{j}\t{r}\n" for j, r in excluded))
    budget = _Budget(out_dir, max_cost, stop_after_errors)
    counter: Counter = Counter()
    exit_code = EXIT_OK
    processed = 0
    for job_id, _smid in targets:
        if limit is not None and processed >= limit:
            break
        if job_id not in budget.job_ids:  # 絞った実行でも order.txt は上書きせず、末尾に足す（費用と --repair の範囲に入る）
            append_line_durable(out_dir / "order.txt", job_id)
            budget.job_ids.append(job_id)
        _total, reason = budget.check_cost()
        if reason:
            print(f"止めます: {reason}", file=sys.stderr)
            exit_code = EXIT_LIMIT
            break
        started = time.monotonic()
        category, note = process_job(job_id, out_dir, timeout_sec)
        seconds = time.monotonic() - started
        total, reason = budget.check_cost()
        append_record(out_dir, record_of("execute", job_id, category, note, seconds, total))
        counter[category] += 1
        processed += 1 if _is_work(category) else 0
        stop = reason or budget.after(category)
        if stop:
            print(f"止めます: {stop}", file=sys.stderr)
            exit_code = EXIT_LIMIT
            break
    summarize(counter)
    if processed >= 1:
        extraction._publish_review_changed()  # D5: 要確認画面へ1回通知
    if exit_code == EXIT_OK and RESIDUAL_CATEGORIES & set(counter):
        return EXIT_RESIDUAL
    return exit_code


# ---------------------------------------------------------------------------
# --repair
# ---------------------------------------------------------------------------


def _load_repair_counts(out_dir: Path) -> dict:
    path = out_dir / "repair_counts.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def repair_job(job_id: str, out_dir: Path, counts: dict, timeout_sec: int) -> tuple[str, str]:
    state = read_job_state(job_id)
    if state is None or not state["v102"]:
        return "repair_skip_not_v102", ""
    pairs = read_pairs(out_dir, job_id) or []
    current_pairs = read_current_pairs(out_dir, job_id)
    if svc.REASON_RESPONSE_UNREADABLE in state["reasons"]:
        if state["corrections"]:
            return "skip_corrections", "unreadable だが item_corrections あり"
        if int(counts.get(job_id, 0)) >= REPAIR_MAX_PER_JOB:
            return "repair_exhausted", f"{REPAIR_MAX_PER_JOB} 回やり直しても読めません（--rollback-from --job-id で戻す）"
        counts[job_id] = int(counts.get(job_id, 0)) + 1
        write_text_durable(out_dir / "repair_counts.json", json.dumps(counts))
        failure, note = extract_one(job_id, timeout_sec)
        if failure is not None:
            return failure, note
        category, note2 = finish_after_extraction(job_id, pairs, current_pairs=current_pairs)
        return category, "; ".join(x for x in (f"repair#{counts[job_id]}", note, note2) if x)
    # 空の応答（items 0・unreadable でない）は、抽出が review_reasons を NULL にする（line_analysis_v102_svc.py:513）。
    # 解析が走ると no_items 等が書かれる（同 :976）ので、NULL のままなら解析前で止まった件
    empty_unanalyzed = state["status"] == "empty" and state["items"] == 0 and all(not r for r in state["reasons"])
    need_analysis = (
        (state["items"] > 0 and state["results"] == 0) or svc.REASON_EXTRACT_EXCEPTION in state["reasons"] or empty_unanalyzed
    )
    return finish_after_extraction(job_id, pairs, run_analysis=need_analysis, current_pairs=current_pairs)


def repair(out_dir: Path, ids_file: Path, *, max_cost: Decimal, stop_after_errors: int, timeout_sec: int) -> int:
    with new_session() as session:
        problems = preflight(session)
        session.rollback()
    if problems:
        return _report_problems(problems)
    out_dir.mkdir(parents=True, exist_ok=True)
    job_ids = read_ids_file(ids_file)
    if not (out_dir / "order.txt").exists():
        write_text_durable(out_dir / "order.txt", "".join(f"{j}\n" for j in job_ids))
    budget = _Budget(out_dir, max_cost, stop_after_errors)
    budget.job_ids = sorted(set(budget.job_ids) | set(job_ids))
    counts = _load_repair_counts(out_dir)
    counter: Counter = Counter()
    exit_code = EXIT_OK
    changed = 0
    for job_id in job_ids:
        _total, reason = budget.check_cost()
        if reason:
            print(f"止めます: {reason}", file=sys.stderr)
            exit_code = EXIT_LIMIT
            break
        started = time.monotonic()
        category, note = repair_job(job_id, out_dir, counts, timeout_sec)
        seconds = time.monotonic() - started
        total, reason = budget.check_cost()
        append_record(out_dir, record_of("repair", job_id, category, note, seconds, total))
        counter[category] += 1
        changed += 1 if _is_work(category) else 0
        stop = reason or budget.after(category)
        if stop:
            print(f"止めます: {stop}", file=sys.stderr)
            exit_code = EXIT_LIMIT
            break
    summarize(counter)
    exhausted = [j for j in job_ids if int(counts.get(j, 0)) >= REPAIR_MAX_PER_JOB]
    if exhausted:
        print(f"再抽出が上限の件（--rollback-from --job-id で v6 に戻す候補）: {len(exhausted)} 件")
    if changed:
        extraction._publish_review_changed()
    if exit_code == EXIT_OK and RESIDUAL_CATEGORIES & set(counter):
        return EXIT_RESIDUAL
    return exit_code


# ---------------------------------------------------------------------------
# --rollback-from
# ---------------------------------------------------------------------------


def _parse_csv(text_: str) -> list[list[str | None]]:
    """COPY ... (FORMAT csv, FORCE_QUOTE *) の出力を読む。引用符なしの空 = NULL、引用符つきの空 = 空文字（`\\N` も普通の文字列）。"""
    rows: list[list[str | None]] = []
    row: list[str | None] = []
    buf: list[str] = []
    quoted = False  # このフィールドが引用符で始まったか
    in_quotes = False
    i, n = 0, len(text_)

    def end_field() -> None:
        value = "".join(buf)
        row.append(value if (quoted or value != "") else None)
        buf.clear()

    while i < n:
        ch = text_[i]
        if in_quotes:
            if ch == '"':
                if i + 1 < n and text_[i + 1] == '"':
                    buf.append('"')
                    i += 1
                else:
                    in_quotes = False
            else:
                buf.append(ch)
        elif ch == '"' and not buf and not quoted:
            in_quotes = quoted = True
        elif ch == ",":
            end_field()
            quoted = False
        elif ch in "\r\n":
            if ch == "\r" and i + 1 < n and text_[i + 1] == "\n":
                i += 1
            end_field()
            quoted = False
            rows.append(row)
            row = []
        else:
            buf.append(ch)
        i += 1
    if buf or quoted or row:
        end_field()
        rows.append(row)
    return rows


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str | None]]]:
    with open(path, encoding="utf-8", newline="") as fh:
        parsed = _parse_csv(fh.read())
    if not parsed:
        return [], []
    header = [h or "" for h in parsed[0]]
    rows = [dict(zip(header, r, strict=True)) for r in parsed[1:] if r != [None]]
    return header, rows


def _column_types(session: Session, table: str) -> dict[str, str]:
    rows = session.execute(
        text(
            """
            SELECT a.attname, format_type(a.atttypid, a.atttypmod)
            FROM pg_attribute a
            WHERE a.attrelid = CAST(:rel AS regclass) AND a.attnum > 0 AND NOT a.attisdropped AND a.attgenerated = ''
            """
        ),
        {"rel": f"{schema()}.{table}"},
    ).fetchall()
    return {r[0]: r[1] for r in rows}


def _insert_rows(session: Session, table: str, header: list[str], rows: list[dict], types: dict[str, str]) -> None:
    cols = [c for c in header if c in types]
    names = ", ".join(f'"{c}"' for c in cols)
    values = ", ".join(f"CAST(:p{i} AS {types[c]})" for i, c in enumerate(cols))
    sql = text(f"INSERT INTO {schema()}.{table} ({names}) VALUES ({values})")
    for row in rows:
        session.execute(sql, {f"p{i}": row[c] for i, c in enumerate(cols)})


def _update_job(session: Session, header: list[str], row: dict, types: dict[str, str]) -> None:
    cols = [c for c in header if c in types and c != "id"]
    sets = ", ".join(f'"{c}" = CAST(:p{i} AS {types[c]})' for i, c in enumerate(cols))
    params = {f"p{i}": row[c] for i, c in enumerate(cols)}
    params["ej"] = row["id"]
    session.execute(text(f"UPDATE {schema()}.extraction_jobs SET {sets} WHERE id = CAST(:ej AS uuid)"), params)


def rollback_job(job_id: str, jobs_row: dict, jobs_header: list[str], items: list[dict], items_header: list[str],
                 results: list[dict], results_header: list[str], *, execute_writes: bool) -> tuple[str, str]:
    """1 job を控えから戻す。1つの取引。失敗したらその job だけ rollback する。"""
    s = schema()
    session = new_session()
    try:
        corr = session.execute(  # 0. v102 の items に紐づく item_corrections
            text(
                f"SELECT count(*) FROM {s}.item_corrections ic WHERE ic.extraction_item_id IN "
                f"(SELECT id FROM {s}.extraction_items WHERE extraction_job_id = CAST(:ej AS uuid))"
            ),
            {"ej": job_id},
        ).scalar_one()
        if int(corr) > 0:
            session.rollback()
            return "skip_corrections", f"item_corrections {int(corr)} 件"
        if not execute_writes:
            session.rollback()
            return "would_rollback", f"items {len(items)} / results {len(results)}"
        pairs = svc._load_resolved_pairs(session, job_id)  # 1. v102 が出していた組
        session.execute(text(f"DELETE FROM {s}.extraction_items WHERE extraction_job_id = CAST(:ej AS uuid)"), {"ej": job_id})  # 2.
        _insert_rows(session, "extraction_items", items_header, items, _column_types(session, "extraction_items"))  # 3.
        _insert_rows(session, "analysis_results", results_header, results, _column_types(session, "analysis_results"))
        _update_job(session, jobs_header, jobs_row, _column_types(session, "extraction_jobs"))  # 4.
        analyzer._merge_supplier_products(session, job_id, s, extra_pairs=pairs, revival_guard=False)  # 5.（ADR-1032: 取り消しは現行を動かさない方へ）
        session.commit()  # 変更が0件だと関数の中では commit しない。手順0〜4はここで確定する
        return "rolled_back", f"items {len(items)} / results {len(results)}"
    except Exception as exc:  # noqa: BLE001
        session.rollback()
        logger.exception("[reextract] 戻しに失敗: job=%s", job_id)
        return "rollback_error", f"{type(exc).__name__}: {str(exc)[:200]}"
    finally:
        session.close()


def rollback(out_dir: Path, backup_dir: Path, *, only_job: str | None, execute_writes: bool) -> int:
    jobs_header, jobs = _read_csv(backup_dir / "extraction_jobs.csv")
    items_header, items = _read_csv(backup_dir / "extraction_items.csv")
    results_header, results = _read_csv(backup_dir / "analysis_results.csv")
    items_by_job: dict[str, list[dict]] = {}
    item_job: dict[str, str] = {}
    for row in items:
        items_by_job.setdefault(row["extraction_job_id"], []).append(row)
        item_job[row["id"]] = row["extraction_job_id"]
    results_by_job: dict[str, list[dict]] = {}
    for row in results:
        results_by_job.setdefault(item_job.get(row["extraction_item_id"], ""), []).append(row)
    out_dir.mkdir(parents=True, exist_ok=True)
    counter: Counter = Counter()
    for row in jobs:
        job_id = row["id"]
        if only_job is not None and job_id != only_job:
            continue
        started = time.monotonic()
        category, note = rollback_job(
            job_id, row, jobs_header, items_by_job.get(job_id, []), items_header,
            results_by_job.get(job_id, []), results_header, execute_writes=execute_writes,
        )
        append_record(out_dir, record_of("rollback", job_id, category, note, time.monotonic() - started, None))
        if category == "rolled_back":
            append_line_durable(out_dir / "rolled_back.txt", job_id)  # 次の --execute が、この job をやり直さないように
        counter[category] += 1
    summarize(counter)
    if counter.get("rolled_back"):
        extraction._publish_review_changed()
    return EXIT_ROLLBACK_ERROR if counter.get("rollback_error") else EXIT_OK


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m app.tools.reextract_v6_with_v102",
        description="旧解析 v6 の投稿を新解析 v102 でやり直す（既定は dry-run）。",
    )
    p.add_argument("--out-dir", required=True, help="一覧・記録・pairs/・started_at.txt の置き場（本番は /work）")
    p.add_argument("--execute", action="store_true", help="やり直す（--rollback-from と合わせると戻しを書く）")
    p.add_argument("--repair", action="store_true", help="取り残しを直す（--ids-file が要る）")
    p.add_argument("--ids-file", help="処理順の job id 一覧（order.txt）")
    p.add_argument("--rollback-from", help="控えのディレクトリ（extraction_jobs.csv など）")
    p.add_argument("--job-id", help="1 job だけ")
    p.add_argument("--limit", type=int, help="この件数で止める")
    p.add_argument("--max-cost-usd", type=Decimal, default=Decimal("11"))
    p.add_argument("--stop-after-errors", type=int, default=5)
    p.add_argument("--timeout-sec", type=int, default=300)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    out_dir = Path(args.out_dir)
    if args.rollback_from:
        return rollback(out_dir, Path(args.rollback_from), only_job=args.job_id, execute_writes=args.execute)
    if args.repair:
        if not args.ids_file:
            print("--repair には --ids-file が要ります", file=sys.stderr)
            return EXIT_CONFIG
        install_gemini_timeout(args.timeout_sec)
        return repair(out_dir, Path(args.ids_file), max_cost=args.max_cost_usd,
                      stop_after_errors=args.stop_after_errors, timeout_sec=args.timeout_sec)
    if args.execute:
        install_gemini_timeout(args.timeout_sec)
        return execute(out_dir, only_job=args.job_id, limit=args.limit, max_cost=args.max_cost_usd,
                       stop_after_errors=args.stop_after_errors, timeout_sec=args.timeout_sec)
    return dry_run(out_dir, args.job_id)


if __name__ == "__main__":
    sys.exit(main())
