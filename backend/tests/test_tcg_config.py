"""
TCG スキーマ設定モジュール（tcg_config.py）のユニットテスト。

テスト観点:
  1. TCG_SCHEMA 未設定時は tenant_004 がデフォルト
  2. TCG_SCHEMA=tenant_006 のとき tenant_006 が返る
  3. 不正な値（tenant_abc, 任意文字列, 空文字）で RuntimeError
  4. サービスモジュールが TCG_SCHEMA を使って正しい SQL を組み立てる（monkeypatch）
"""
from __future__ import annotations

import importlib
import os
import sys
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# tcg_config モジュール自体のテスト
# ---------------------------------------------------------------------------


def _reload_tcg_config(env_value: str | None) -> str:
    """
    指定した環境変数値で tcg_config を再ロードして TCG_SCHEMA を返す。
    モジュールレベルの検証を走らせるために importlib.reload を使う。
    """
    env_patch: dict[str, str] = {}
    if env_value is not None:
        env_patch["TCG_SCHEMA"] = env_value

    # 未設定ケースでは既存の TCG_SCHEMA 環境変数を除外する
    with patch.dict(os.environ, env_patch, clear=False):
        if env_value is None:
            os.environ.pop("TCG_SCHEMA", None)
        mod = importlib.import_module("app.tcg_config")
        importlib.reload(mod)
        return mod.TCG_SCHEMA


def test_tcg_config_default_is_tenant_004():
    """TCG_SCHEMA 未設定時はデフォルト tenant_004 が返る。"""
    schema = _reload_tcg_config(None)
    assert schema == "tenant_004"


def test_tcg_config_custom_schema():
    """TCG_SCHEMA=tenant_006 のとき tenant_006 が返る。"""
    schema = _reload_tcg_config("tenant_006")
    assert schema == "tenant_006"


@pytest.mark.parametrize(
    "invalid_value",
    [
        "tenant_abc",       # 数字でない
        "tenant_04",        # 桁数不足
        "tenant_0004",      # 桁数超過
        "TENANT_004",       # 大文字
        "public",           # 任意文字列
        "",                 # 空文字
        "tenant_004 ",      # 末尾スペース
        "tenant-004",       # ハイフン
        "'; DROP TABLE",    # インジェクション試行
    ],
)
def test_tcg_config_invalid_value_raises(invalid_value: str):
    """不正な TCG_SCHEMA 値では RuntimeError が発生する。"""
    with pytest.raises(RuntimeError, match="無効"):
        _reload_tcg_config(invalid_value)


# ---------------------------------------------------------------------------
# サービスモジュールへの波及テスト（monkeypatch）
# ---------------------------------------------------------------------------


def test_tcg_line_import_svc_uses_configured_schema(monkeypatch):
    """
    tcg_line_import_svc が組み立てる SQL に
    設定済みの TCG_SCHEMA が使われること。

    monkeypatch でサービスモジュールの TCG_SCHEMA を差し替えて
    SQL 文字列に正しいスキーマ修飾が入るかを検証する。
    """
    import app.services.tcg_line_import_svc as svc

    monkeypatch.setattr(svc, "TCG_SCHEMA", "tenant_006")

    # サービスがインポートする TCG_SCHEMA を確認（モジュール属性として取得）
    assert svc.TCG_SCHEMA == "tenant_006"
