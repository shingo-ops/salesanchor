"""generate_password のユニットテスト。

hash_password / verify_password は password_hash 列廃止に伴い削除済み（2026-06-12）。
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import string

import pytest

from app.auth.utils import (
    PASSWORD_SYMBOLS,
    generate_password,
)


class TestGeneratePassword:
    def test_default_length_is_16(self):
        assert len(generate_password()) == 16

    @pytest.mark.parametrize("length", [4, 8, 12, 24, 32, 64])
    def test_custom_length(self, length):
        assert len(generate_password(length)) == length

    @pytest.mark.parametrize("length", [0, 1, 2, 3, -1])
    def test_invalid_length_raises(self, length):
        with pytest.raises(ValueError):
            generate_password(length)

    def test_contains_all_character_classes(self):
        # 100回生成して、毎回4カテゴリ全部を含むこと
        for _ in range(100):
            pw = generate_password()
            assert any(c.islower() for c in pw), f"小文字なし: {pw}"
            assert any(c.isupper() for c in pw), f"大文字なし: {pw}"
            assert any(c.isdigit() for c in pw), f"数字なし: {pw}"
            assert any(c in PASSWORD_SYMBOLS for c in pw), f"記号なし: {pw}"

    def test_only_uses_allowed_alphabet(self):
        allowed = set(string.ascii_letters + string.digits + PASSWORD_SYMBOLS)
        for _ in range(50):
            pw = generate_password()
            assert set(pw) <= allowed, f"許可外文字: {set(pw) - allowed}"

    def test_uniqueness(self):
        # 100回生成して全て異なる（暗号学的乱数なので衝突しないこと）
        passwords = {generate_password() for _ in range(100)}
        assert len(passwords) == 100
