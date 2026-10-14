"""パスワードの決まり（ADR-1013 便3・design.md:88-97）のテスト。"""

import re
from pathlib import Path

from app.auth import password_policy

DATA_DIR = Path(password_policy.__file__).parent / "data"


def _words():
    return [w.strip() for w in (DATA_DIR / "common-passwords.txt").read_text(encoding="utf-8").splitlines() if w.strip()]


def _uncommon(n: int) -> str:
    return ("Zq7#" * 40)[:n]


def test_14_chars_too_short():
    assert password_policy.check_password(_uncommon(14)) == "password_too_short"


def test_15_chars_ok():
    assert password_policy.check_password(_uncommon(15)) is None


def test_64_chars_ok():
    assert password_policy.check_password(_uncommon(64)) is None


def test_65_chars_too_long():
    assert password_policy.check_password(_uncommon(65)) == "password_too_long"


def test_length_counts_characters_not_bytes():
    assert password_policy.check_password("あ" * 15) is None
    assert password_policy.check_password("あ" * 14) == "password_too_short"


def test_common_word_rejected_case_insensitive():
    # 一覧の先頭の語は 15 文字未満（too_short が先に出る）ため、15 文字以上で最初に載っている語を使う
    word = next(w for w in _words() if 15 <= len(w) <= 64)
    assert password_policy.check_password(word) == "password_too_common"
    assert password_policy.check_password(word.upper()) == "password_too_common"


def test_too_short_is_checked_before_too_common():
    assert password_policy.check_password(_words()[0]) == "password_too_short"


def test_list_count_matches_readme():
    raw = (DATA_DIR / "common-passwords.txt").read_bytes()
    wc_l = raw.count(b"\n")
    readme = (DATA_DIR / "README.md").read_text(encoding="utf-8")
    assert re.search(rf"\b{wc_l}\b", readme), f"README に件数 {wc_l} が書かれていない"
