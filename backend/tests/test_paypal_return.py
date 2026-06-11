"""PayPal 戻りトークン（Fernet 署名）のテスト。

対応 AC: design.md #1（往復復元）/ #2（改ざん・不正は None）。
"""

from app.services import paypal_payments as svc


def test_return_token_roundtrip():
    tok = svc.make_return_token(4, 123)
    assert isinstance(tok, str) and tok
    assert svc.parse_return_token(tok) == (4, 123)


def test_return_token_roundtrip_other_values():
    assert svc.parse_return_token(svc.make_return_token(6, 999999)) == (6, 999999)


def test_return_token_tampered_returns_none():
    tok = svc.make_return_token(4, 123)
    # 中間の1文字を改変 → Fernet の HMAC 検証失敗
    idx = 10
    flipped = "X" if tok[idx] != "X" else "Y"
    bad = tok[:idx] + flipped + tok[idx + 1:]
    assert svc.parse_return_token(bad) is None


def test_return_token_garbage_returns_none():
    assert svc.parse_return_token("not-a-valid-token") is None
    assert svc.parse_return_token("") is None
