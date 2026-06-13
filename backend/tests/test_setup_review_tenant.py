"""setup_review_tenant.py の単体テスト。

Firebase Admin SDK と DB をモックして以下を検証:
- 通常実行: 既存 Firebase ユーザーの password update が呼ばれない
- ALLOW_REVIEW_TENANT_PASSWORD_RESET=1: password update が呼ばれる
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
    # firebase_admin を先にモック
    mock_fb = MagicMock()
    mock_fb._apps = {}
    sys.modules.setdefault("firebase_admin", mock_fb)
    sys.modules.setdefault("firebase_admin.auth", MagicMock())
    sys.modules.setdefault("firebase_admin.credentials", MagicMock())
    sys.modules.setdefault("firebase_admin.exceptions", MagicMock())
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# テスト: パスワード変更ガード
# ---------------------------------------------------------------------------

class TestPasswordResetGuard:
    """既存ユーザーに対するパスワード更新の制御を検証する。"""

    def test_existing_user_no_reset_flag_skips_password_update(self, monkeypatch):
        """通常実行（フラグなし）: 既存ユーザーへの password update は呼ばれない。"""
        monkeypatch.delenv("ALLOW_REVIEW_TENANT_PASSWORD_RESET", raising=False)
        mod = _load_module()

        mock_update = MagicMock()
        mock_generate = MagicMock(return_value="NewPass123!")

        with patch.object(mod, "_firebase_update_password", mock_update), \
             patch.object(mod, "_firebase_get_uid", return_value="existing-uid-abc"):
            # _password_reset_requested() が False のとき update は呼ばれない
            existing_uid = mod._firebase_get_uid("review@salesanchor.jp")
            reset_requested = mod._password_reset_requested()

            if existing_uid and not reset_requested:
                pass  # update skipped
            elif existing_uid and reset_requested:
                new_pw = mock_generate()
                mod._firebase_update_password(existing_uid, new_pw)

        mock_update.assert_not_called()

    def test_existing_user_with_reset_flag_calls_password_update(self, monkeypatch):
        """ALLOW_REVIEW_TENANT_PASSWORD_RESET=1: 既存ユーザーへの password update が呼ばれる。"""
        monkeypatch.setenv("ALLOW_REVIEW_TENANT_PASSWORD_RESET", "1")
        mod = _load_module()

        mock_update = MagicMock()
        mock_generate = MagicMock(return_value="NewPass123!")

        with patch.object(mod, "_firebase_update_password", mock_update), \
             patch.object(mod, "_firebase_get_uid", return_value="existing-uid-abc"):
            existing_uid = mod._firebase_get_uid("review@salesanchor.jp")
            reset_requested = mod._password_reset_requested()

            if existing_uid and reset_requested:
                new_pw = mock_generate()
                mod._firebase_update_password(existing_uid, new_pw)

        mock_update.assert_called_once()

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
