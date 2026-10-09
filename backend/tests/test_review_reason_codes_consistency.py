"""理由コードの抜け漏れ防止（DB なし）。設計: docs/handoff/v102-prod-switch/design.md §12-5。

新しい理由コードを足すときは「コード側の定数 ＋ ja/en.json の reviewReason.<code> ＋
data/review_reason_codes/ の SQL に1行」が揃わないとここで落ちる。
"""
import json
import re
from pathlib import Path

from app.services import gemini_raw_copy_v101 as v101
from app.services import gemini_raw_copy_v102_product_first as product_first
from app.services import line_analysis_v102_svc as v102
from app.services.tcg_empty_box_rules import EMPTY_REASONS

REPO = Path(__file__).resolve().parents[2]
SEED_DIR = REPO / "docs/handoff/v102-prod-switch/data/review_reason_codes"
LOCALES = REPO / "frontend/src/locales"
APP = REPO / "backend/app"
NON_CODE_KEYS = {"unknown", "source", "separator"}  # reviewReason 名前空間のうち理由コードではない鍵

_ROW = re.compile(r"\(\s*'([a-z][a-z0-9_]*)'\s*,\s*'(gemini|system)'\s*,\s*'(extraction|analysis)'\s*\)")


def _seed_codes() -> set[str]:
    codes: list[str] = []
    for path in sorted(SEED_DIR.glob("seed_*.sql")):
        codes += [match.group(1) for match in _ROW.finditer(path.read_text(encoding="utf-8"))]
    assert codes, "初期行の SQL からコードを読めない"
    assert len(codes) == len(set(codes)), "初期行の SQL でコードが重複している"
    return set(codes)


def _locale_codes(lang: str) -> set[str]:
    block = json.loads((LOCALES / f"{lang}.json").read_text(encoding="utf-8"))["reviewReason"]
    return set(block) - NON_CODE_KEYS


def _code_side_constants() -> set[str]:
    return {
        # gemini_raw_copy_v101.py
        v101.REJECTED_SHAPE, v101.REJECTED_PRICE, v101.REJECTED_DUPLICATE,
        v101.ROLE_SHIP, v101.ROLE_CONDITION,
        v101.UNSURE_OK, v101.UNSURE_INVALID,
        v101._REVIEW_QUANTITY_NO_NUMBER, v101._REVIEW_FOOTER,
        v101._REVIEW_UNIT_UNKNOWN, v101._REVIEW_CATEGORY_UNKNOWN, v101._REVIEW_HEADING_SHIP,
        v101._POST_NO_ITEMS, v101._POST_MISSING_ITEM,
        # gemini_raw_copy_v102_product_first.py
        product_first.REVIEW_CONDITION_UNKNOWN, product_first.REVIEW_MULTIPLE_CANDIDATES,
        product_first.REVIEW_PRODUCT_NOT_IN_MASTER, product_first.REVIEW_PRODUCT_MULTIPLE,
        # line_analysis_v102_svc.py
        v102.REASON_RESPONSE_UNREADABLE, v102.REASON_EXTRACT_EXCEPTION,
        # tcg_empty_box_rules.py
        *EMPTY_REASONS,
    }


def test_seed_codes_match_ja_and_en_translations():
    seed = _seed_codes()
    assert seed == _locale_codes("ja"), "初期行の SQL と ja.json の reviewReason が違う"
    assert seed == _locale_codes("en"), "初期行の SQL と en.json の reviewReason が違う"


def test_every_named_code_constant_is_in_the_seed():
    missing = _code_side_constants() - _seed_codes()
    assert not missing, f"コード側の理由コードが初期行に無い: {sorted(missing)}"


def test_every_seed_code_appears_in_backend_app():
    sources = [path.read_text(encoding="utf-8") for path in APP.rglob("*.py")]
    unused = sorted(code for code in _seed_codes() if not any(f'"{code}"' in text or f"'{code}'" in text for text in sources))
    assert not unused, f"backend/app のどこにも出てこない初期行: {unused}"
