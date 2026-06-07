"""
Response スキーマの読み取り時バリデーター分離テスト。

背景:
  CompanyAddressResponse が CompanyAddressInput を継承していたため、
  形式不正なメール（例: 数字のみ）を持つ既存 DB 行で GET /companies が全件 500 になった。
  修正後は:
  - Response モデルは不正な既存データでも構築できる（読み取り時はバリデーターなし）
  - Input モデルは引き続き不正メールを拒否する（書き込み時バリデーターを維持）

参照: feat(phase1-b2-step5b-1) #121, 本番 500 incident (2026-06-07)
"""
import pytest
from pydantic import ValidationError

from app.schemas.company import CompanyAddressInput, CompanyAddressResponse
from app.schemas.contact import (
    ContactEmailInput,
    ContactEmailResponse,
)

# ─── CompanyAddressResponse ────���──────────────────────────────────────────────

class TestCompanyAddressResponseAcceptsInvalidData:
    """不正なメール・電話番号を含む DB 行でも Response が構築できること。"""

    def test_invalid_email_does_not_raise(self):
        """email 欄に数字のみの文字列が入った行でも ValidationError を起こさない。"""
        resp = CompanyAddressResponse(
            id=1,
            address_type="billing",
            email="376367830",  # 本番で実際に発生した不正値
        )
        assert resp.email == "376367830"

    def test_invalid_telephone_does_not_raise(self):
        """telephone 欄に形式外の文字列が入っていても ValidationError を起こさない。"""
        resp = CompanyAddressResponse(
            id=2,
            address_type="delivery",
            telephone="not-a-phone!!!",
        )
        assert resp.telephone == "not-a-phone!!!"

    def test_none_fields_accepted(self):
        """email/telephone が None のケースは従来通り構築できる。"""
        resp = CompanyAddressResponse(
            id=3,
            address_type="billing",
            email=None,
            telephone=None,
        )
        assert resp.email is None


class TestCompanyAddressInputRejectsInvalidData:
    """書き込み用 Input は不正なメール・電話番号を引き続き拒否すること。"""

    def test_invalid_email_raises(self):
        with pytest.raises(ValidationError, match="メールアドレスの形式"):
            CompanyAddressInput(
                address_type="billing",
                email="376367830",
            )

    def test_valid_email_accepted(self):
        inp = CompanyAddressInput(
            address_type="billing",
            email="user@example.com",
        )
        assert inp.email == "user@example.com"

    def test_none_email_accepted(self):
        inp = CompanyAddressInput(address_type="billing", email=None)
        assert inp.email is None


# ─── ContactEmailResponse ───────────────────────────────────────��────────────

class TestContactEmailResponseAcceptsInvalidData:
    """contact_emails 副テーブルの不正値でも Response が構築できること。"""

    def test_invalid_email_does_not_raise(self):
        resp = ContactEmailResponse(id=1, email="not-an-email")
        assert resp.email == "not-an-email"


class TestContactEmailInputRejectsInvalidData:
    """書き込み用 ContactEmailInput は不正メールを拒否すること。"""

    def test_invalid_email_raises(self):
        with pytest.raises(ValidationError, match="メールアドレスの形式"):
            ContactEmailInput(email="not-an-email")

    def test_valid_email_accepted(self):
        inp = ContactEmailInput(email="contact@example.com")
        assert inp.email == "contact@example.com"
