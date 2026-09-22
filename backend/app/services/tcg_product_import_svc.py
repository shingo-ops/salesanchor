"""
IMPORT-01: 商品マスタ CSV 取り込みサービス。

CSV を読み、参照マスタのコードを uuid に変換し、検査してから既存の
商品マスタ登録処理へ渡す。登録そのものは tcg_product_master_svc の
create_product をそのまま使い、本サービスでは新しい登録処理を書かない。

段階:
  preview : 検査だけを行い、書き込みを一切しない
  commit  : 同じ検査をやり直し、止める判定の無い行だけを登録する

CSV の列（10列・見出し行あり）:
  mark / japanese_title / english_title / release_date /
  search_keywords / exclude_keywords /
  division_code / work_code / manufacturer_code / product_category_code

code / category_class / is_active は create_product が自動で入れるため
CSV には持たせない。

TCG のテーブルは専用スキーマにあるため、全 SQL を TCG_SCHEMA で修飾する。

根拠: docs/handoff/tcg-product-import/design.md 5-3 / 5-4 / 5-5
"""
from __future__ import annotations

import csv
import hashlib
import io
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Step 4/5: TCG テーブルは public スキーマに移行済み
TCG_SCHEMA = "public"

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

CSV_COLUMNS: list[str] = [
    "mark",
    "japanese_title",
    "english_title",
    "release_date",
    "search_keywords",
    "exclude_keywords",
    "division_code",
    "work_code",
    "manufacturer_code",
    "product_category_code",
]

# 空だと登録できない列（design 5-4 の 1番・2番）
REQUIRED_COLUMNS: list[str] = [
    "japanese_title",
    "division_code",
    "work_code",
    "manufacturer_code",
    "product_category_code",
]

# コード列 → 参照マスタのテーブル名
# NOTE: division_code と product_category_code は load_lookup_maps 内で公開スキーマ（public）の
# SSOT（product_kinds / tcg_product_categories）で上書きされる（ADR-156 Phase 3A/3B）。
# 初回クエリ（TCG_SCHEMA）は無駄になるが、静的解析ガード（test_tcg_schema_qualification.py）が
# このマッピングの構造を直接検証するため、後方互換性のため変更しない。
LOOKUP_TABLES: dict[str, str] = {
    "division_code": "tcg_major_categories",       # overridden in load_lookup_maps → public.product_kinds
    "manufacturer_code": "tcg_manufacturers",
    "product_category_code": "tcg_product_categories",  # overridden in load_lookup_maps → public.tcg_product_categories
}

# コード列 → create_product に渡す引数名
LOOKUP_ARGS: dict[str, str] = {
    "division_code": "product_kind_id",
    "work_code": "work_id",
    "manufacturer_code": "manufacturer_id",
    "product_category_code": "product_category_id",
}

RESULT_CREATED = "created"
RESULT_SKIPPED = "skipped"
RESULT_ERROR = "error"

SHORT_KEYWORD_LEN = 3


# ---------------------------------------------------------------------------
# CSV の読み取り
# ---------------------------------------------------------------------------


def file_digest(raw: bytes) -> str:
    """取り込みファイルの指紋。同じファイルの二度取り込みを弾くために使う。"""
    return hashlib.sha256(raw).hexdigest()


def decode_csv(raw: bytes) -> str:
    """UTF-8 として読む。先頭の目印が付いていれば取り除く。"""
    return raw.decode("utf-8-sig")


def split_keywords(value: str) -> list[str]:
    """カンマで割り、前後の空白を落とし、空を捨てる。create_product と同じ扱い。"""
    return [k.strip() for k in (value or "").split(",") if k.strip()]


def looks_like_iso_date(value: str) -> bool:
    """発売日が 4桁-2桁-2桁 の形かどうか。空は許す（任意項目のため）。"""
    v = (value or "").strip()
    if not v:
        return True
    parts = v.split("-")
    if len(parts) != 3:
        return False
    if len(parts[0]) != 4 or len(parts[1]) != 2 or len(parts[2]) != 2:
        return False
    return all(p.isdigit() for p in parts)


def parse_rows(raw: bytes) -> tuple[list[dict[str, str]], list[str]]:
    """
    CSV を読み、1行を1つの辞書にして返す。

    Returns:
      rows        : 行番号つきの辞書の一覧。row_no は見出しを除いた 1 始まり
      file_errors : ファイル全体を止める理由の一覧。空なら形は正しい
    """
    file_errors: list[str] = []
    reader = csv.reader(io.StringIO(decode_csv(raw)))
    records = [r for r in reader]

    if not records:
        return [], ["CSV_EMPTY"]

    header = [h.strip() for h in records[0]]
    if header != CSV_COLUMNS:
        file_errors.append("CSV_HEADER_MISMATCH")
        return [], file_errors

    rows: list[dict[str, str]] = []
    for i, rec in enumerate(records[1:], start=1):
        if not any((c or "").strip() for c in rec):
            continue
        if len(rec) != len(CSV_COLUMNS):
            file_errors.append("CSV_COLUMN_COUNT_MISMATCH_ROW_" + str(i))
            continue
        row = {CSV_COLUMNS[j]: (rec[j] or "").strip() for j in range(len(CSV_COLUMNS))}
        row["row_no"] = str(i)
        rows.append(row)

    return rows, file_errors


# ---------------------------------------------------------------------------
# 参照マスタの引き当て
# ---------------------------------------------------------------------------


async def load_lookup_maps(db: AsyncSession) -> dict[str, dict[str, str]]:
    """
    参照マスタから、コードと id の対応を引く。

    Returns:
      {"division_code": {"DIV01": "uuid", ...}, "work_code": {"SV": "1", ...}, ...}

    Phase 3 SSOT: tcg_product_categories は public スキーマへ移動（INTEGER PK）。
    public.products.product_category_id は UUID→INTEGER に変換済み。
    work_code と同様に public スキーマから引く。
    """
    maps: dict[str, dict[str, str]] = {}
    # work_code → public.type_master (SSOT, INTEGER PK)
    work_result = await db.execute(
        text("SELECT code, id FROM public.type_master WHERE is_active = TRUE")
    )
    maps["work_code"] = {str(r[0]): str(r[1]) for r in work_result.fetchall()}
    for column, table in LOOKUP_TABLES.items():
        result = await db.execute(
            text(f"SELECT code, id FROM {TCG_SCHEMA}.{table} WHERE is_active = TRUE")
        )
        maps[column] = {str(r[0]): str(r[1]) for r in result.fetchall()}
    # Phase 3 SSOT: tcg_product_categories moved to public (INTEGER PK).
    # Override the tenant-schema result with the canonical public-schema integer IDs.
    pc_result = await db.execute(
        text("SELECT code, id FROM public.tcg_product_categories WHERE is_active = TRUE")
    )
    maps["product_category_code"] = {str(r[0]): int(r[1]) for r in pc_result.fetchall()}
    # Phase 3A SSOT: tcg_major_categories moved to public.product_kinds (INTEGER PK).
    # Override tenant-schema result with canonical public-schema integer IDs.
    pk_result = await db.execute(
        text("SELECT code, id FROM public.product_kinds WHERE is_active = TRUE")
    )
    pk_map: dict[str, int] = {str(r[0]): int(r[1]) for r in pk_result.fetchall()}
    # Backward-compatible aliases for legacy CSV division codes
    _DIVISION_ALIASES = {"DIV01": "TCG", "DIV02": "FIGURE", "DIV03": "GOODS"}
    for old_code, new_code in _DIVISION_ALIASES.items():
        if new_code in pk_map:
            pk_map[old_code] = pk_map[new_code]
    maps["division_code"] = pk_map  # type: ignore[assignment]
    return maps


async def load_existing_marks(db: AsyncSession) -> dict[str, str]:
    """
    既に登録されている型番と商品コードの対応を引く。件数の上限を設けない。

    design 5-4 の7番（同じ型番が既に在る行を警告する）で使う。既存の
    重複チェックは候補取得を打ち切るため、その穴をここで埋める。
    """
    result = await db.execute(
        text(
            "SELECT mark, product_code FROM public.products "
            "WHERE mark IS NOT NULL AND mark <> '' AND is_active = TRUE"
        )
    )
    return {str(r[0]).strip(): str(r[1]) for r in result.fetchall()}


# ---------------------------------------------------------------------------
# 検査（DB を引かない分）
# ---------------------------------------------------------------------------


def check_codes(row: dict[str, str], lookups: dict[str, dict[str, str]]) -> list[str]:
    """4つのコード列が空でなく、参照マスタに実在することを見る。

    lookups は load_lookup_maps が返す辞書（work_code を含む全コード列）。
    LOOKUP_TABLES は TCG スキーマのテーブルのみのため、ここでは lookups のキーを使う。
    """
    errors: list[str] = []
    for column in lookups:
        code = row.get(column, "")
        if not code:
            errors.append("MISSING_" + column.upper())
        elif code not in lookups[column]:
            errors.append("UNKNOWN_" + column.upper() + "_" + code)
    return errors


def validate_row_static(
    row: dict[str, str],
    lookups: dict[str, dict[str, str]],
    existing_marks: dict[str, str],
    seen: dict[tuple[str, str], str],
) -> dict[str, Any]:
    """
    DB を引かずに判る検査。design 5-4 の 1 2 3 5 7 8 9 11 を見る。
    6番と10番は DB を引くため別の関数で行う。

    seen は同一ファイル内の重複を見るための持ち回り。呼ぶ側が空の辞書を
    用意し、行の順に渡す。
    """
    blocking: list[str] = []
    warnings: list[str] = []

    title = row.get("japanese_title", "")
    if not title:
        blocking.append("JAPANESE_TITLE_REQUIRED")

    blocking.extend(check_codes(row, lookups))

    if not looks_like_iso_date(row.get("release_date", "")):
        blocking.append("RELEASE_DATE_FORMAT")

    mark = row.get("mark", "")
    key = (title, mark)
    if title and key in seen:
        blocking.append("DUPLICATE_IN_FILE_ROW_" + seen[key])
    elif title:
        seen[key] = row.get("row_no", "")

    if not mark:
        warnings.append("MARK_EMPTY")
    elif mark in existing_marks:
        warnings.append("MARK_ALREADY_USED_BY_" + existing_marks[mark])

    keywords = split_keywords(row.get("search_keywords", ""))
    if not keywords:
        warnings.append("NO_SEARCH_KEYWORD")
    for word in keywords:
        if len(word) <= SHORT_KEYWORD_LEN:
            warnings.append("SHORT_KEYWORD_" + word)

    return {
        "row_no": row.get("row_no", ""),
        "japanese_title": title,
        "mark": mark,
        "blocking": blocking,
        "warnings": warnings,
    }


def build_payload(
    row: dict[str, str], lookups: dict[str, dict[str, str]]
) -> dict[str, Any]:
    """create_product に渡す引数を組み立てる。使われない2つには空文字を渡す。"""
    payload: dict[str, Any] = {
        "extraction_item_id": "",
        "source_message_id": "",
        "japanese_title": row.get("japanese_title", ""),
        "english_title": row.get("english_title", ""),
        "mark": row.get("mark", ""),
        "release_date": row.get("release_date", ""),
        "search_keywords": row.get("search_keywords", ""),
        "exclude_keywords": row.get("exclude_keywords", ""),
    }
    for column, arg in LOOKUP_ARGS.items():
        payload[arg] = lookups[column].get(row.get(column, ""), "")
    return payload


# ---------------------------------------------------------------------------
# 検査（DB を引く分）
# ---------------------------------------------------------------------------


async def load_keyword_owners(db: AsyncSession) -> dict[str, list[str]]:
    """検索キーワードと、それを持つ商品コードの対応を引く。"""
    result = await db.execute(
        text(
            "SELECT k.keyword, p.product_code FROM public.product_search_keywords k "
            "JOIN public.products p ON p.id = k.product_id "
            "WHERE p.is_active = TRUE"
        )
    )
    owners: dict[str, list[str]] = {}
    for record in result.fetchall():
        owners.setdefault(str(record[0]).strip(), []).append(str(record[1]))
    return owners


async def validate_row_dynamic(
    db: AsyncSession,
    row: dict[str, str],
    payload: dict[str, Any],
    keyword_owners: dict[str, list[str]],
) -> list[str]:
    """
    DB を引く検査。design 5-4 の 6番と10番。いずれも警告どまりで止めない。

    既存の重複チェックはそのまま呼ぶ。判定ロジックをここに写さない。
    """
    from app.services.tcg_product_master_svc import check_duplicates

    warnings: list[str] = []

    for word in split_keywords(row.get("search_keywords", "")):
        owners = keyword_owners.get(word, [])
        if owners:
            warnings.append("KEYWORD_ALSO_HITS_" + word + "_" + ",".join(owners[:3]))

    data = await check_duplicates(
        db,
        japanese_title=payload["japanese_title"],
        work_id=payload["work_id"],
        manufacturer_id=payload["manufacturer_id"],
        product_category_id=payload["product_category_id"],
        mark=payload["mark"],
        search_keywords=payload["search_keywords"],
    )
    for cand in data.get("candidates", []):
        warnings.append("DUPLICATE_CANDIDATE_" + str(cand.get("product_id", "")))

    return warnings


async def preview(db: AsyncSession, raw: bytes, filename: str) -> dict[str, Any]:
    """検査だけを行う。書き込みは一切しない。"""
    rows, file_errors = parse_rows(raw)
    if file_errors:
        return {
            "filename": filename,
            "digest": file_digest(raw),
            "file_errors": file_errors,
            "total": 0,
            "ok": 0,
            "blocked": 0,
            "rows": [],
        }

    lookups = await load_lookup_maps(db)
    existing_marks = await load_existing_marks(db)
    keyword_owners = await load_keyword_owners(db)
    seen: dict[tuple[str, str], str] = {}
    results: list[dict[str, Any]] = []

    for row in rows:
        checked = validate_row_static(row, lookups, existing_marks, seen)
        if not checked["blocking"]:
            payload = build_payload(row, lookups)
            checked["warnings"].extend(
                await validate_row_dynamic(db, row, payload, keyword_owners)
            )
        results.append(checked)

    blocked = len([r for r in results if r["blocking"]])
    return {
        "filename": filename,
        "digest": file_digest(raw),
        "file_errors": [],
        "total": len(results),
        "ok": len(results) - blocked,
        "blocked": blocked,
        "rows": results,
    }


# ---------------------------------------------------------------------------
# 取り込みの実行
# ---------------------------------------------------------------------------


async def start_job(
    db: AsyncSession, filename: str, digest: str, total: int, executed_by: str
) -> str:
    """取り込み1回ぶんの親を作る。同じ指紋のファイルは一意索引が弾く。"""
    result = await db.execute(
        text(
            f"INSERT INTO {TCG_SCHEMA}.tcg_product_import_jobs "
            "(filename, raw_sha256, total_rows, executed_by, status) "
            "VALUES (:filename, :digest, :total, :who, 'running') RETURNING id"
        ),
        {"filename": filename, "digest": digest, "total": total, "who": executed_by},
    )
    job_id = str(result.fetchone()[0])
    await db.commit()
    return job_id


async def record_row(
    db: AsyncSession, job_id: str, checked: dict[str, Any], result_kind: str,
    product_code: str, messages: str, *, commit: bool = True,
) -> None:
    """CSV の1行ぶんの結果を残す。"""
    await db.execute(
        text(
            f"INSERT INTO {TCG_SCHEMA}.tcg_product_import_rows "
            "(job_id, row_no, japanese_title, mark, result, product_code, messages) "
            "VALUES (:job, :row_no, :title, :mark, :kind, :code, :messages)"
        ),
        {
            "job": job_id,
            "row_no": int(checked["row_no"] or 0),
            "title": checked["japanese_title"],
            "mark": checked["mark"] or None,
            "kind": result_kind,
            "code": product_code or None,
            "messages": messages or None,
        },
    )
    if commit:
        await db.commit()


async def finish_job(
    db: AsyncSession, job_id: str, created: int, skipped: int, status: str
) -> None:
    """取り込み1回ぶんの親を締める。"""
    await db.execute(
        text(
            f"UPDATE {TCG_SCHEMA}.tcg_product_import_jobs "
            "SET created_rows = :created, skipped_rows = :skipped, "
            "status = :status, completed_at = NOW() WHERE id = :job"
        ),
        {"created": created, "skipped": skipped, "status": status, "job": job_id},
    )
    await db.commit()


async def commit_import(
    db: AsyncSession, raw: bytes, filename: str, executed_by: str
) -> dict[str, Any]:
    """Commit each product, its keywords and created receipt together.

    Earlier rows stay committed on failure. An uncertain commit response is not
    retried: rollback does not prove that the server did not commit the row.
    """
    from app.services.tcg_product_master_svc import create_product

    async def rollback_preserving_error(error: BaseException) -> None:
        try:
            await db.rollback()
        except BaseException as rollback_error:
            raise error from rollback_error

    async def record_rejection(checked: dict[str, Any], kind: str, notes: str) -> None:
        try:
            await record_row(db, job_id, checked, kind, "", notes)
        except BaseException as error:
            await rollback_preserving_error(error)
            raise

    checked_all = await preview(db, raw, filename)
    if checked_all["file_errors"]:
        return checked_all

    lookups = await load_lookup_maps(db)
    rows, _ = parse_rows(raw)
    by_row = {r["row_no"]: r for r in checked_all["rows"]}
    job_id = await start_job(
        db, filename, checked_all["digest"], checked_all["total"], executed_by
    )

    created = 0
    skipped = 0
    for row in rows:
        checked = by_row[row["row_no"]]
        notes = ";".join(checked["blocking"] + checked["warnings"])
        if checked["blocking"]:
            await record_rejection(checked, RESULT_SKIPPED, notes)
            skipped += 1
            continue
        payload = build_payload(row, lookups)
        try:
            outcome = await create_product(db, force=True, commit=False, **payload)
        except ValueError as error:
            # Only a creation ValueError may become a rejected row. Rollback
            # must succeed before its error receipt starts another transaction.
            await rollback_preserving_error(error)
            await record_rejection(checked, RESULT_ERROR, str(error))
            skipped += 1
            continue
        except BaseException as error:
            await rollback_preserving_error(error)
            raise

        try:
            code = str(outcome.get("product_id", ""))
            await record_row(db, job_id, checked, RESULT_CREATED, code, notes, commit=False)
            await db.commit()
        except BaseException as error:
            await rollback_preserving_error(error)
            raise
        created += 1

    try:
        await finish_job(db, job_id, created, skipped, "ok")
    except BaseException as error:
        await rollback_preserving_error(error)
        raise
    return {
        "job_id": job_id,
        "filename": filename,
        "total": checked_all["total"],
        "created": created,
        "skipped": skipped,
        "rows": checked_all["rows"],
    }
