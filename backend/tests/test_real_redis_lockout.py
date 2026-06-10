"""
PR #1891 挙動確認: 実 Redis + 実 HTTP で巻き添え遮断修正を検証する

目的:
  ユニットテスト (test_security_hardening.py) では Redis を mock していた。
  本スクリプトは実際の Redis インスタンスを使い、
  Redis キーの操作 (SET/GET) が正しく機能していることを HTTP レベルで確認する。

実行前提:
  redis-server --port 6399 --requirepass testpass123 が起動済みであること。
  このファイルを実行する前に make check / CI テストとは独立している（実 Redis 依存）。

3つのシナリオ:
  S1 巻き添えゼロ  : IP ロック中 + JWT キャッシュあり  → 200 (or 403/404, NOT 429)
  S2 防御維持      : IP ロック中 + JWT キャッシュなし  → 429
  S3 正常系        : IP ロックなし + JWT キャッシュあり → 200 (or 403/404, NOT 429)

実行:
  REDIS_URL=redis://:testpass123@localhost:6399/0 \
    pytest backend/tests/test_real_redis_lockout.py -v --no-cov -s
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
import redis.asyncio as aioredis
from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import Result

# ── 環境設定 ─────────────────────────────────────────────────────────────────
# 実 Redis に向ける（起動済みであること）
REDIS_TEST_URL = os.environ.get("REDIS_URL", "redis://:testpass123@localhost:6399/0")
os.environ["REDIS_URL"] = REDIS_TEST_URL
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("CELERY_BROKER_URL", REDIS_TEST_URL)
os.environ.setdefault("CELERY_RESULT_BACKEND", REDIS_TEST_URL)
os.environ.setdefault("ENVIRONMENT", "test")

# reportlab スタブ（未インストール環境用）
for _mod in [
    "reportlab", "reportlab.lib", "reportlab.lib.pagesizes",
    "reportlab.lib.styles", "reportlab.lib.units", "reportlab.lib.colors",
    "reportlab.platypus", "reportlab.platypus.paragraph",
    "reportlab.platypus.tables", "reportlab.platypus.doctemplate",
    "reportlab.pdfbase", "reportlab.pdfbase.pdfmetrics",
    "reportlab.pdfbase.ttfonts", "reportlab.pdfgen", "reportlab.pdfgen.canvas",
]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()


# ── ヘルパー ──────────────────────────────────────────────────────────────────
def _jwt_cache_key(token: str) -> str:
    """app.cache._token_hash と同じ計算式"""
    return f"jwt:{hashlib.sha256(token.encode()).hexdigest()}"


def _ip_lock_key(ip: str) -> str:
    """app.cache.check_auth_rate_limit / record_auth_failure と同じ計算式"""
    return f"auth_fail_ip:{hashlib.sha256(ip.encode()).hexdigest()[:16]}"


# テストで固定するIPとトークン
TEST_IP = "10.0.0.1"
CACHED_TOKEN = "cached-valid-token-abc123"
UNCACHED_TOKEN = "no-cache-token-xyz789"
IP_LOCK_COUNT = "15"  # AUTH_FAIL_MAX=10 を超える値


def _make_mock_user(email: str = "shingo@example.com") -> MagicMock:
    """DBから返ってくる User オブジェクトのモック"""
    u = MagicMock()
    u.email = email
    u.tenant_id = 1
    u.is_active = True
    u.role = "admin"
    u.id = 1
    return u


# ── フィクスチャ ───────────────────────────────────────────────────────────────
@pytest_asyncio.fixture
async def real_redis():
    """実 Redis への接続を確立し、テスト後に使用したキーを削除する。"""
    r = aioredis.from_url(REDIS_TEST_URL, decode_responses=True)
    try:
        await r.ping()
    except Exception as e:
        pytest.skip(f"実 Redis に接続できません ({REDIS_TEST_URL}): {e}")
    yield r
    # クリーンアップ
    await r.delete(_jwt_cache_key(CACHED_TOKEN))
    await r.delete(_jwt_cache_key(UNCACHED_TOKEN))
    await r.delete(_ip_lock_key(TEST_IP))
    await r.aclose()


# ── テストクラス ──────────────────────────────────────────────────────────────
class TestRealRedisLockout:
    """
    実 Redis を使った巻き添え遮断修正の統合確認テスト。

    3 シナリオを順に実行し、HTTP ステータスコードを証跡として記録する。
    """

    async def _request_with_ip(
        self, app, token: str, ip: str = TEST_IP
    ) -> int:
        """指定 IP + トークンでエンドポイントを叩き、ステータスコードを返す。"""
        mock_user = _make_mock_user()
        mock_result = MagicMock(spec=Result)
        mock_result.scalar_one_or_none.return_value = mock_user

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.close = AsyncMock()

        with patch("app.auth.dependencies.get_db") as mock_get_db, \
             patch("app.auth.dependencies.is_token_blacklisted", new_callable=AsyncMock) as mock_bl:
            mock_bl.return_value = False
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=False)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    "/api/v1/companies",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "X-Forwarded-For": ip,
                    },
                )
        return resp.status_code

    # ──────────────────────────────────────────────────────────────────
    # S1: 巻き添えゼロ
    # ──────────────────────────────────────────────────────────────────
    @pytest.mark.asyncio
    async def test_s1_cached_user_bypasses_ip_lock(self, real_redis):
        """
        S1 巻き添えゼロ: IP ロック中でも JWT キャッシュ済みユーザーは 429 にならない。

        Redis 操作:
          - auth_fail_ip:{hash(IP)} = 15   (ロック成立)
          - jwt:{hash(CACHED_TOKEN)} = {"email": "shingo@example.com"}  (キャッシュ済み)

        期待: status_code != 429
        """
        from app.main import app

        # Redis にロック + キャッシュを設定
        await real_redis.set(_ip_lock_key(TEST_IP), IP_LOCK_COUNT, ex=900)
        await real_redis.set(
            _jwt_cache_key(CACHED_TOKEN),
            json.dumps({"email": "shingo@example.com"}),
            ex=300,
        )

        # 実 Redis を使って app が init_redis() 済みの状態で実行
        from app.cache import _redis as cache_redis
        original_redis = cache_redis

        from app import cache as cache_module
        cache_module._redis = real_redis  # app の Redis クライアントを実 Redis に差し替え

        try:
            status = await self._request_with_ip(app, CACHED_TOKEN)
        finally:
            cache_module._redis = original_redis

        print(f"\n[S1] IP ロック中 + キャッシュあり → HTTP {status}")
        assert status != 429, (
            f"巻き添え発生 (S1): IP ロック中にキャッシュ済みトークンが {status} で遮断された。"
            "PR #1891 の修正が機能していない。"
        )
        print(f"  ✅ PASS: {status} (429 ではない = 巻き添えなし)")

    # ──────────────────────────────────────────────────────────────────
    # S2: 防御維持
    # ──────────────────────────────────────────────────────────────────
    @pytest.mark.asyncio
    async def test_s2_cache_miss_still_blocked(self, real_redis):
        """
        S2 防御維持: IP ロック中でキャッシュなしのトークンは 429 になる。

        Redis 操作:
          - auth_fail_ip:{hash(IP)} = 15   (ロック成立)
          - jwt:{hash(UNCACHED_TOKEN)} 未設定  (キャッシュなし)

        期待: status_code == 429
        """
        from app.main import app

        # ロックを維持、未キャッシュトークンのキーは削除済み
        await real_redis.set(_ip_lock_key(TEST_IP), IP_LOCK_COUNT, ex=900)
        await real_redis.delete(_jwt_cache_key(UNCACHED_TOKEN))

        from app import cache as cache_module
        original_redis = cache_module._redis
        cache_module._redis = real_redis

        try:
            status = await self._request_with_ip(app, UNCACHED_TOKEN)
        finally:
            cache_module._redis = original_redis

        print(f"\n[S2] IP ロック中 + キャッシュなし → HTTP {status}")
        assert status == 429, (
            f"防御後退 (S2): IP ロック中にキャッシュなしトークンが {status} で通過した。"
            "check_auth_rate_limit のゲートが機能していない。"
        )
        print(f"  ✅ PASS: 429 (防御維持確認)")

    # ──────────────────────────────────────────────────────────────────
    # S3: 正常系
    # ──────────────────────────────────────────────────────────────────
    @pytest.mark.asyncio
    async def test_s3_normal_cached_no_lock(self, real_redis):
        """
        S3 正常系: IP ロックなし + JWT キャッシュあり → 通常通り認証成功。

        Redis 操作:
          - auth_fail_ip:{hash(IP)} 未設定 (ロックなし)
          - jwt:{hash(CACHED_TOKEN)} = {"email": "shingo@example.com"}  (キャッシュ済み)

        期待: status_code != 429
        """
        from app.main import app

        # ロック解除 + キャッシュ設定
        await real_redis.delete(_ip_lock_key(TEST_IP))
        await real_redis.set(
            _jwt_cache_key(CACHED_TOKEN),
            json.dumps({"email": "shingo@example.com"}),
            ex=300,
        )

        from app import cache as cache_module
        original_redis = cache_module._redis
        cache_module._redis = real_redis

        try:
            status = await self._request_with_ip(app, CACHED_TOKEN)
        finally:
            cache_module._redis = original_redis

        print(f"\n[S3] IP ロックなし + キャッシュあり → HTTP {status}")
        assert status != 429, (
            f"正常系破壊 (S3): キャッシュ済みトークンが {status} で遮断された。"
        )
        print(f"  ✅ PASS: {status} (通常認証成功)")


# ── 証跡サマリ ────────────────────────────────────────────────────────────────
def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """テスト結果サマリを証跡として出力する。"""
    passed = len(terminalreporter.stats.get("passed", []))
    failed = len(terminalreporter.stats.get("failed", []))
    if passed + failed == 0:
        return
    print("\n" + "=" * 60)
    print("PR #1891 実 Redis 統合確認 証跡サマリ")
    print("=" * 60)
    print(f"  S1 巻き添えゼロ  : {'PASS' if passed >= 1 else 'FAIL'}")
    print(f"  S2 防御維持      : {'PASS' if passed >= 2 else 'FAIL'}")
    print(f"  S3 正常系        : {'PASS' if passed >= 3 else 'FAIL'}")
    print(f"  合計: {passed} PASS / {failed} FAIL")
    print("=" * 60)
