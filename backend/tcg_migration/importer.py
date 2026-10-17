#!/usr/bin/env python3
"""
MIG-02 Phase 2: Data Importer
データを以下の順序でDBに投入する:
  1. Units + UnitAliases
  2. Conditions + ConditionAliases
  3. TcgSuppliers + SupplierChannels
  4. TcgProducts + ProductsLogistics + ProductSearchKeywords + ProductExcludeKeywords
  5. SourceMessages + ExtractionJobs + ExtractionItems

Phase 2 count checks:
  - suppliers         : 45
  - extraction_items  : 1626
  - products          : 267
  - exclude_keywords  : 54 (expected; actual may differ — will report)
"""

import hashlib
import json
import os
import re
import sys
import uuid
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# ── パス設定 ──────────────────────────────────────────────────────────────────
REPO_ROOT   = Path(__file__).resolve().parents[2]
DATA_DIR    = Path(__file__).resolve().parent / "data"
GEMINI_FILE = Path.home() / "vs02_work" / "data" / "gemini_all.json"
PRODUCT_BACKUP = Path.home() / "Documents" / "y13_07_backup" / "product_master_v2_before.json"

sys.path.insert(0, str(REPO_ROOT))
from tcg_migration.models import (
    AnalysisResult, AuditLog, Base, Condition, ConditionAlias,
    ExtractionItem, ExtractionJob, ItemNote, ProductExcludeKeyword,
    ProductSearchKeyword, ProductsLogistics, SourceMessage,
    SupplierChannel, TcgProduct, TcgSupplier, Unit, UnitAlias,
    UnparsedLine,
)

# ── DB接続 ─────────────────────────────────────────────────────────────────────
DB_URL = os.environ.get("TCG_DB_URL",
         "postgresql+psycopg2://myapp_user:password@localhost:5432/myapp_db")
engine = create_engine(DB_URL, echo=False)

# ── 期待値 ─────────────────────────────────────────────────────────────────────
EXPECTED = {
    "suppliers":        45,
    "extraction_items": 1626,
    "products":         267,
    "exclude_keywords": 54,   # task-spec value; actual from backup may differ
}

# ── ユーティリティ ─────────────────────────────────────────────────────────────

def new_uuid() -> uuid.UUID:
    return uuid.uuid4()


def strip_prefix(s: str, prefix: str) -> uuid.UUID:
    """'EIV2-<uuid>' or 'SMV2-<uuid>' → UUID オブジェクト"""
    raw = s.replace(prefix, "", 1)
    return uuid.UUID(raw)


def parse_span(span_str: str):
    """'L0006-L0008' → (6, 8), 'L0006' → (6,6), '' → (None, None)"""
    if not span_str:
        return None, None
    m = re.match(r"L(\d+)-L(\d+)", span_str)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.match(r"L(\d+)", span_str)
    if m:
        n = int(m.group(1))
        return n, n
    return None, None


def parse_price(price_str) -> Decimal | None:
    """'600円', '15000', '' → Decimal or None"""
    if price_str is None:
        return None
    s = str(price_str).replace("円", "").replace(",", "").strip()
    if not s:
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def parse_qty(qty_val) -> Decimal | None:
    """35, '35', '' → Decimal or None"""
    if qty_val is None or qty_val == "":
        return None
    try:
        return Decimal(str(qty_val))
    except InvalidOperation:
        return None


# ── 1. Units ───────────────────────────────────────────────────────────────────

def load_units(session: Session) -> dict[str, uuid.UUID]:
    """unit canonical → UUID"""
    unit_data = json.loads((DATA_DIR / "unit_master.json").read_text())
    canonical_to_id: dict[str, uuid.UUID] = {}

    for entry in unit_data:
        uid = new_uuid()
        unit = Unit(
            id=uid,
            code=entry["unitId"],
            canonical=entry["canonical"],
            kubun=entry.get("kubun"),
            is_active=True,
        )
        session.add(unit)
        canonical_to_id[entry["canonical"]] = uid

        for i, alias_text in enumerate(entry.get("aliases", [])):
            session.add(UnitAlias(
                id=new_uuid(),
                unit_id=uid,
                alias_text=alias_text,
                lang="ja",
            ))

    session.flush()
    print(f"  [units] {len(unit_data)} 行, {sum(len(e.get('aliases', [])) for e in unit_data)} エイリアス")
    return canonical_to_id


# ── 2. Conditions ──────────────────────────────────────────────────────────────

def load_conditions(session: Session) -> dict[str, uuid.UUID]:
    """condition canonical → UUID"""
    cond_data = json.loads((DATA_DIR / "condition_master.json").read_text())
    canonical_to_id: dict[str, uuid.UUID] = {}

    for entry in cond_data:
        cid = new_uuid()
        cond = Condition(
            id=cid,
            code=entry["condId"],
            canonical=entry["canonical"],
            is_active=True,
        )
        session.add(cond)
        canonical_to_id[entry["canonical"]] = cid

        for alias_text in entry.get("aliases", []):
            session.add(ConditionAlias(
                id=new_uuid(),
                condition_id=cid,
                alias_text=alias_text,
                lang="ja",
            ))

    session.flush()
    print(f"  [conditions] {len(cond_data)} 行, {sum(len(e.get('aliases', [])) for e in cond_data)} エイリアス")
    return canonical_to_id


# ── 3. Suppliers + Channels ────────────────────────────────────────────────────

def load_suppliers(session: Session,
                   gemini_sp_ids: set[str]) -> dict[str, uuid.UUID]:
    """sp_code → supplier UUID"""
    # supplier_master_raw.txt を読んで name を引く
    raw_lines = (DATA_DIR / "supplier_master_raw.txt").read_text(encoding="utf-8").splitlines()
    header_map = {h: i for i, h in enumerate(raw_lines[0].split("\t"))}
    supplier_info: dict[str, dict] = {}
    for line in raw_lines[1:]:
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        sp_id = parts[header_map["SP_ID"]] if "SP_ID" in header_map else ""
        name  = parts[header_map["LINE名"]] if "LINE名" in header_map else ""
        line_id = parts[header_map["LINE_ID"]] if "LINE_ID" in header_map else ""
        if sp_id:
            supplier_info[sp_id] = {"name": name, "line_id": line_id.strip()}

    # gemini に登場する SP + SP0057 を登録
    target_sps = sorted(gemini_sp_ids | {"SP0057"})
    sp_to_uuid: dict[str, uuid.UUID] = {}

    for sp_code in target_sps:
        info = supplier_info.get(sp_code, {})
        name = info.get("name") or sp_code  # フォールバック
        line_id = info.get("line_id") or None
        sid = new_uuid()
        session.add(TcgSupplier(
            id=sid,
            code=sp_code,
            name=name,
            is_active=True,
        ))
        sp_to_uuid[sp_code] = sid

        # 経路: LINE
        session.add(SupplierChannel(
            id=new_uuid(),
            supplier_id=sid,
            channel="line",
            external_id=line_id,
            is_active=True,
        ))

    session.flush()
    print(f"  [suppliers] {len(target_sps)} 行 (gemini={len(gemini_sp_ids)}, +SP0057)")
    return sp_to_uuid


# ── 4. Products ────────────────────────────────────────────────────────────────

def _build_stub_products() -> list[dict]:
    """PM0263-PM0267 スタブ行"""
    return [
        {
            "code": "PM0263",
            "japanese_title": "30th CELEBRATION",
            "category_class": "Box",
            "search_keywords": ["30th", "CELEBRATION"],
            "exclude_keywords": [],
        },
        {
            "code": "PM0264",
            "japanese_title": "FUTURISTIC BOX",
            "category_class": "Box",
            "search_keywords": ["FUTURISTIC", "BOX"],
            "exclude_keywords": [],
        },
        {
            "code": "PM0265",
            "japanese_title": "30th CELEBRATION プレミアムデッキセット",
            "category_class": "Box",
            "search_keywords": ["30th", "CELEBRATION", "プレミアムデッキセット"],
            "exclude_keywords": [],
        },
        {
            "code": "PM0266",
            "japanese_title": "OP-17",
            "category_class": "Box",
            "search_keywords": ["OP-17"],
            "exclude_keywords": [],
        },
        {
            "code": "PM0267",
            "japanese_title": "（スタブ：未確認）",
            "category_class": "",
            "search_keywords": [],
            "exclude_keywords": [],
        },
    ]


def load_products(session: Session) -> dict[str, uuid.UUID]:
    """pm_code → product UUID"""
    backup = json.loads(PRODUCT_BACKUP.read_text())
    rows    = backup["rows"]
    headers = backup["headers"]
    h       = {hdr: i for i, hdr in enumerate(headers)}

    product_code_to_uuid: dict[str, uuid.UUID] = {}

    def _add_product(code, title, category_class, release_date_str,
                     div_id, work_id, mfr_id, cat_id, rov,
                     search_kw_raw, excl_kw_raw, pid_obj) -> uuid.UUID:
        """共通登録ロジック"""
        pid = new_uuid()
        product_code_to_uuid[code] = pid

        # release_date
        release_date = None
        if release_date_str and release_date_str not in ("-", ""):
            try:
                from datetime import date
                release_date = date.fromisoformat(release_date_str[:10])
            except ValueError:
                release_date = None

        session.add(TcgProduct(
            id=pid,
            code=code,
            japanese_title=title,
            category_class=category_class,
            release_date=release_date,
            division_id=None,     # UUID FK 未解決: 文字列 'DIV01' 等
            work_id=None,
            manufacturer_id=None,
            product_category_id=None,
            required_output_value=rov or None,
            is_active=True,
        ))
        session.add(ProductsLogistics(product_id=pid))

        # Search Keywords: スペース区切り
        if search_kw_raw and search_kw_raw.strip() and search_kw_raw.strip() != "-":
            for pos, kw in enumerate(search_kw_raw.strip().split()):
                if kw:
                    session.add(ProductSearchKeyword(
                        id=new_uuid(), product_id=pid, keyword=kw, position=pos
                    ))

        # Exclude Keywords: コンマ区切り
        if excl_kw_raw and excl_kw_raw.strip() and excl_kw_raw.strip() != "-":
            for pos, kw in enumerate(
                [w.strip() for w in excl_kw_raw.split(",") if w.strip()]
            ):
                session.add(ProductExcludeKeyword(
                    id=new_uuid(), product_id=pid, keyword=kw, position=pos
                ))

        return pid

    # PM0001-PM0262 (backup)
    for row in rows:
        code         = row[h["product_id"]]
        title        = row[h["Japanese Title"]]
        cat_class    = row[h["カテゴリ分類"]]
        rel_date     = row[h["Release Date"]]
        rov          = row[h["REQUIRED_OUTPUT_VALUE"]]
        sk_raw       = row[h["Search Keywords"]]
        ek_raw       = row[h["Exclude Keywords"]]
        _add_product(code, title, cat_class, str(rel_date) if rel_date else "",
                     None, None, None, None, rov, sk_raw, ek_raw, None)

    session.flush()

    # PM0263-PM0267 (stubs)
    for stub in _build_stub_products():
        pid = new_uuid()
        product_code_to_uuid[stub["code"]] = pid
        session.add(TcgProduct(
            id=pid,
            code=stub["code"],
            japanese_title=stub["japanese_title"],
            category_class=stub["category_class"],
            is_active=True,
        ))
        session.add(ProductsLogistics(product_id=pid))
        for pos, kw in enumerate(stub["search_keywords"]):
            session.add(ProductSearchKeyword(
                id=new_uuid(), product_id=pid, keyword=kw, position=pos
            ))

    session.flush()
    total_products = len(product_code_to_uuid)
    print(f"  [products] {total_products} 行 (backup={len(rows)}, stubs=5)")
    return product_code_to_uuid


# ── 5. SourceMessages + ExtractionJobs + ExtractionItems ──────────────────────

def load_gemini(session: Session,
                sp_to_uuid: dict[str, uuid.UUID]) -> dict[str, uuid.UUID]:
    """
    gemini_all.json から:
      - source_messages (44 行 + SP0057 スタブ 1 行 = 45 行)
      - extraction_jobs (45 行)
      - extraction_items (1626 行)

    Returns: extraction_item_id (str) → ExtractionItem UUID
    """
    gemini = json.loads(GEMINI_FILE.read_text())

    # SP ごとに source_message を1つ作る
    sm_map: dict[str, dict] = {}  # sm_raw_id → {sp_id, sha256, raw_text}
    for item in gemini:
        sm_raw = item["source_message_id"]       # "SMV2-<uuid>"
        sp_id  = item["source"]["sp_id"]
        if sm_raw not in sm_map:
            sm_map[sm_raw] = {
                "sp_id":    sp_id,
                "sha256":   item["raw_sha256"],
                "raw_text": item.get("raw_text", ""),
            }

    # sm_raw_id → DB UUID のマップ
    sm_raw_to_uuid: dict[str, uuid.UUID] = {}
    # sm_raw_id → ExtractionJob UUID
    sm_raw_to_job_uuid: dict[str, uuid.UUID] = {}

    for sm_raw, info in sm_map.items():
        sm_uuid    = strip_prefix(sm_raw, "SMV2-")
        sp_ch_uuid = _get_channel_uuid(session, sp_to_uuid[info["sp_id"]])

        session.add(SourceMessage(
            id=sm_uuid,
            supplier_channel_id=sp_ch_uuid,
            raw_text=info["raw_text"],
            raw_sha256=info["sha256"],
            is_active=True,
        ))

        job_uuid = new_uuid()
        session.add(ExtractionJob(
            id=job_uuid,
            source_message_id=sm_uuid,
            status="done",
        ))
        sm_raw_to_uuid[sm_raw]     = sm_uuid
        sm_raw_to_job_uuid[sm_raw] = job_uuid

    # SP0057: スタブ (source_message + job status='empty')
    sp57_uuid    = sp_to_uuid["SP0057"]
    sp57_ch_uuid = _get_channel_uuid(session, sp57_uuid)
    sp57_sm_uuid = new_uuid()
    sp57_sha     = hashlib.sha256("SP0057_stub".encode()).hexdigest()[:64]
    session.add(SourceMessage(
        id=sp57_sm_uuid,
        supplier_channel_id=sp57_ch_uuid,
        raw_text="",
        raw_sha256=sp57_sha,
        is_active=True,
    ))
    sp57_job_uuid = new_uuid()
    session.add(ExtractionJob(
        id=sp57_job_uuid,
        source_message_id=sp57_sm_uuid,
        status="empty",
    ))
    session.flush()

    # extraction_items (1626 行)
    ei_raw_to_uuid: dict[str, uuid.UUID] = {}
    for item in gemini:
        sm_raw   = item["source_message_id"]
        job_uuid = sm_raw_to_job_uuid[sm_raw]
        ei_raw   = item["extraction_item_id"]  # "EIV2-<uuid>"
        ei_uuid  = strip_prefix(ei_raw, "EIV2-")

        gem = item.get("gemini", {})
        span_str = gem.get("span", "")
        line_start, line_end = parse_span(span_str)

        session.add(ExtractionItem(
            id=ei_uuid,
            extraction_job_id=job_uuid,
            line_start=line_start,
            line_end=line_end,
            raw_product_name=gem.get("name") or None,
            raw_quantity=str(gem.get("quantity", "")) or None,
            raw_price=str(gem.get("price", "")) or None,
            raw_unit=gem.get("unit") or None,
            raw_state=gem.get("state") or None,
            raw_memo=gem.get("memo") or None,
        ))
        ei_raw_to_uuid[ei_raw] = ei_uuid

    session.flush()

    n_sm   = len(sm_map) + 1   # +SP0057
    n_job  = n_sm
    n_ei   = len(gemini)
    print(f"  [source_messages] {n_sm} 行 (gemini={len(sm_map)}, SP0057 stub=1)")
    print(f"  [extraction_jobs] {n_job} 行")
    print(f"  [extraction_items] {n_ei} 行")
    return ei_raw_to_uuid


def _get_channel_uuid(session: Session, supplier_uuid: uuid.UUID) -> uuid.UUID:
    """supplier の LINE チャネル UUID を返す"""
    result = session.execute(
        text("SELECT id FROM supplier_channels WHERE supplier_id = :sid AND channel = 'line'"),
        {"sid": str(supplier_uuid)},
    ).fetchone()
    if result:
        return uuid.UUID(str(result[0]))
    raise RuntimeError(f"channel not found for supplier {supplier_uuid}")


# ── Phase 2 count check ────────────────────────────────────────────────────────

def phase2_count_check(session: Session) -> bool:
    checks = {
        "suppliers":        "SELECT COUNT(*) FROM tcg_suppliers",
        "extraction_items": "SELECT COUNT(*) FROM extraction_items",
        "products":         "SELECT COUNT(*) FROM tcg_products",
        "exclude_keywords": "SELECT COUNT(*) FROM product_exclude_keywords",
    }

    print("\n" + "=" * 60)
    print("Phase 2 Count Check")
    print("=" * 60)
    all_ok = True
    for key, sql in checks.items():
        actual   = session.execute(text(sql)).scalar()
        expected = EXPECTED[key]
        status   = "OK" if actual == expected else "MISMATCH"
        if actual != expected:
            all_ok = False
        print(f"  {key:<20} actual={actual:>6}  expected={expected:>6}  {status}")

    print("=" * 60)
    if all_ok:
        print("  → Phase 2 PASS")
    else:
        print("  → Phase 2 FAIL: 上記の不一致を確認してください")
    return all_ok


# ── main ───────────────────────────────────────────────────────────────────────

def main():
    print("MIG-02 Phase 2 Importer 開始")
    print(f"  DB : {DB_URL}")
    print(f"  GEMINI: {GEMINI_FILE}")
    print(f"  PRODUCT BACKUP: {PRODUCT_BACKUP}")

    # gemini の SP IDs を事前収集
    gemini = json.loads(GEMINI_FILE.read_text())
    gemini_sp_ids = {item["source"]["sp_id"] for item in gemini}

    with Session(engine) as session:
        with session.begin():
            print("\n[1/5] Units...")
            unit_canonical_to_uuid = load_units(session)

            print("[2/5] Conditions...")
            cond_canonical_to_uuid = load_conditions(session)

            print("[3/5] Suppliers + Channels...")
            sp_to_uuid = load_suppliers(session, gemini_sp_ids)

            print("[4/5] Products...")
            product_code_to_uuid = load_products(session)

            print("[5/5] SourceMessages + ExtractionJobs + ExtractionItems...")
            ei_raw_to_uuid = load_gemini(session, sp_to_uuid)

            # commit 前に Phase 2 count check
            ok = phase2_count_check(session)

        if not ok:
            print("\n⚠️  Phase 2 count check 失敗。STOP して報告:")
            print("   exclude_keywords の実測値が期待値 54 と異なります。")
            print("   y13_07_backup (262行) からコンマ区切りで集計すると 123 エントリとなります。")
            print("   期待値 54 の算出根拠を確認してください。")
            print("   データは commit 済みです（修正は期待値に合わせる変更は行いません）。")
            sys.exit(1)
        else:
            print("\n✅ Phase 2 PASS — importer 完了")


if __name__ == "__main__":
    main()
