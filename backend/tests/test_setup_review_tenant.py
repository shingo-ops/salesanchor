"""setup_review_tenant.py の単体テスト。

DB をモックして以下を検証:
- パスワードを書くのは、リセット指定のときと、まだパスワードが無いときだけ
- ALLOW_REVIEW_TENANT_PASSWORD_RESET の読み取り
- Firebase の部品を使っていない
- customers テーブル参照が存在しない
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# ヘルパー: スクリプトを動的インポート
# ---------------------------------------------------------------------------

_SCRIPT_PATH = Path(__file__).resolve().parent.parent.parent / "scripts" / "setup_review_tenant.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("setup_review_tenant", _SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# テスト: パスワード変更ガード
# ---------------------------------------------------------------------------

class TestPasswordResetGuard:
    """既存ユーザーに対するパスワード更新の制御を検証する。"""

    def test_existing_password_without_reset_flag_is_kept(self):
        """既存のパスワードがあり、リセット指定なし → 書かない。"""
        mod = _load_module()
        assert mod._should_write_password(has_password=True, reset=False) is False

    def test_existing_password_with_reset_flag_is_written(self):
        """既存のパスワードがあり、リセット指定あり → 書く。"""
        mod = _load_module()
        assert mod._should_write_password(has_password=True, reset=True) is True

    def test_no_password_is_written_without_flag(self):
        """パスワードが無い（新しく作る） → 指定なしでも書く。"""
        mod = _load_module()
        assert mod._should_write_password(has_password=False, reset=False) is True

    def test_no_password_with_reset_flag_is_written(self):
        """パスワードが無く、リセット指定あり → 書く。"""
        mod = _load_module()
        assert mod._should_write_password(has_password=False, reset=True) is True

    def test_script_has_no_firebase(self):
        """スクリプトに Firebase の文字が無い（便2 の終わりの条件）。"""
        assert "firebase" not in _SCRIPT_PATH.read_text(encoding="utf-8").lower()

    def test_password_reset_requested_false_without_env(self, monkeypatch):
        """ALLOW_REVIEW_TENANT_PASSWORD_RESET 未設定 → False。"""
        monkeypatch.delenv("ALLOW_REVIEW_TENANT_PASSWORD_RESET", raising=False)
        mod = _load_module()
        assert mod._password_reset_requested() is False

    def test_password_reset_requested_true_with_env(self, monkeypatch):
        """ALLOW_REVIEW_TENANT_PASSWORD_RESET=1 → True。"""
        monkeypatch.setenv("ALLOW_REVIEW_TENANT_PASSWORD_RESET", "1")
        mod = _load_module()
        assert mod._password_reset_requested() is True

    def test_password_reset_requested_false_with_wrong_value(self, monkeypatch):
        """ALLOW_REVIEW_TENANT_PASSWORD_RESET=0 → False（'1' 以外は無効）。"""
        monkeypatch.setenv("ALLOW_REVIEW_TENANT_PASSWORD_RESET", "0")
        mod = _load_module()
        assert mod._password_reset_requested() is False


# ---------------------------------------------------------------------------
# テスト: customers テーブル参照がないこと
# ---------------------------------------------------------------------------

class TestNoCustomersTableReference:
    """スクリプト本文に customers テーブルへの SQL 参照がないことを検証する。"""

    def test_no_sql_customers_reference(self):
        """FROM customers / INSERT INTO customers の SQL 参照が存在しない。"""
        content = _SCRIPT_PATH.read_text(encoding="utf-8")
        # コメント行を除いた行に "FROM customers" や "INSERT INTO customers" がないこと
        non_comment_lines = [
            line for line in content.splitlines()
            if not line.lstrip().startswith("#")
        ]
        non_comment_text = "\n".join(non_comment_lines)
        assert "FROM customers" not in non_comment_text
        assert "INSERT INTO customers" not in non_comment_text

    def test_no_seed_demo_customers_function(self):
        """_seed_demo_customers 関数が削除されていること。"""
        content = _SCRIPT_PATH.read_text(encoding="utf-8")
        assert "def _seed_demo_customers" not in content

    def test_no_demo_customers_constant(self):
        """DEMO_CUSTOMERS 定数が削除されていること。"""
        content = _SCRIPT_PATH.read_text(encoding="utf-8")
        assert "DEMO_CUSTOMERS = [" not in content


# ---------------------------------------------------------------------------
# テスト: password_hash 列への SQL 参照がないこと
# ---------------------------------------------------------------------------

class TestNoPasswordHashColumn:
    """スクリプト本文に password_hash 列への SQL 参照がないことを検証する。

    docstring / コメントでの言及（ADR 説明）は許可。SQL 文内の参照のみ禁止。
    """

    def test_no_sql_password_hash_in_update(self):
        """UPDATE SET password_hash = の SQL パターンが存在しない。"""
        import re
        content = _SCRIPT_PATH.read_text(encoding="utf-8")
        # SQL UPDATE SET 節に password_hash が出現しないこと
        assert not re.search(r"SET\s+password_hash\s*=", content), \
            "SQL UPDATE SET password_hash = が検出されました"

    def test_no_password_hash_in_sql_column_list(self):
        """INSERT 文のカラムリスト（括弧内）に password_hash が含まれていない。"""
        import re
        content = _SCRIPT_PATH.read_text(encoding="utf-8")
        # INSERT INTO table (col1, col2, ...) のカラムリスト部分を抽出
        col_lists = re.findall(r"INSERT INTO\s+\S+\s*\(([^)]+)\)", content, re.DOTALL)
        for col_list in col_lists:
            assert "password_hash" not in col_list, \
                f"INSERT column list contains password_hash: {col_list[:100]}"
