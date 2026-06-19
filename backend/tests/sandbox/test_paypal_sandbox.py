"""PayPal Sandbox 実機スモークテスト（ADR-101 再発防止 PR-A）

このテストは実 PayPal Sandbox API を呼び出す。通常の pytest スイート（test.yml）とは
分離されており、外部 API 向け専用ワークフロー（external-api-smoke.yml）でのみ実行される。

動作仕様:
  - PAYPAL_SANDBOX_CLIENT_ID / PAYPAL_SANDBOX_CLIENT_SECRET が未設定 → pytest.fail()
    （KGI-4: SKIP ではなく FAIL。設定漏れを CI で可視化する）
  - 実 PayPal Sandbox API に create→send→URL取得 の 3 ステップを実行
  - UUID ベースの一意な invoice_number を生成（重複番号エラー防止: fix #2243 教訓）

実行方法:
  external-api-smoke.yml で以下のように実行する:
    pytest -m sandbox backend/tests/sandbox/test_paypal_sandbox.py -v --tb=short

再発防止設計:
  docs/handoff/incident-paypal-invoicing-false-complete/design.md
  docs/handoff/incident-paypal-invoicing-false-complete/recon.md R6

分離の仕組み:
  backend/pyproject.toml の norecursedirs に "sandbox" を追加済み。
  通常の `pytest -q --tb=short`（test.yml）ではこのディレクトリは走査されない。
"""

import os
import uuid

import pytest

from app.services import paypal_payments as svc

_CLIENT_ID = os.environ.get("PAYPAL_SANDBOX_CLIENT_ID")
_CLIENT_SECRET = os.environ.get("PAYPAL_SANDBOX_CLIENT_SECRET")


@pytest.mark.sandbox
def test_paypal_sandbox_create_and_send_invoice() -> None:
    """実 PayPal Sandbox で create→send→recipient_view_url を確認する（KGI-4）。

    secrets 未設定は pytest.fail()（SKIP ではなく FAIL）。
    理由: SKIP のままでは FedEx と同じ構造的穴（CI 常時スキップ）が再現する。
    参照: docs/handoff/incident-paypal-invoicing-false-complete/recon.md R6
    """
    if not _CLIENT_ID or not _CLIENT_SECRET:
        pytest.fail(
            "PayPal Sandbox smoke test: PAYPAL_SANDBOX_CLIENT_ID / "
            "PAYPAL_SANDBOX_CLIENT_SECRET が未設定です。"
            "CI では external-api-smoke.yml の secrets を確認してください。"
            "（KGI-4: SKIP ではなく FAIL — 設計書 design.md §KGI 参照）"
        )

    # UUID で一意の invoice_number を生成（重複番号エラー回避: fix #2243 教訓）
    invoice_number = f"SMOKE-{uuid.uuid4().hex[:12].upper()}"

    result = svc.create_and_send_invoice(
        "sandbox",
        _CLIENT_ID,
        _CLIENT_SECRET,
        invoice_number=invoice_number,
        currency="JPY",
        amount=1,
        recipient_email="sb-buyer@example.com",
        reference="smoke-test",
        item_name="PR-A Smoke Test",
    )

    assert result["ok"] is True, (
        f"create_and_send_invoice 失敗: "
        f"HTTP {result.get('status_code')}: {result.get('message')}"
    )
    assert result["paypal_invoice_id"] is not None, (
        "paypal_invoice_id が取得できませんでした"
    )
    assert result["recipient_view_url"] is not None, (
        "recipient_view_url が取得できませんでした（PayPal Sandbox URL 取得フロー失敗）"
    )
    assert "paypal.com" in result["recipient_view_url"], (
        f"recipient_view_url が PayPal ドメインではありません: "
        f"{result['recipient_view_url']}"
    )

    # Disposable PR: this line keeps the sandbox-only diff non-empty.
