"""
登録トークン入力スキーマのユニットテスト（入力契約: 空欄→null 共通正規化）。

検証観点:
  A. AddressInput 空文字列 → None 正規化（全 Optional[str] フィールド共通）
  B. AddressInput email / telephone 形式バリデーション（値あり）
  C. AddressInput country_code 正規化・バリデーション
  D. RegisterRequest contact — ADR-126 追補: 担当者名は任意（空欄OK）
"""

import pytest
from pydantic import ValidationError

from app.schemas.registration_token import (
    AddressInput,
    ChangeBillingRequest,
    RegisterRequest,
    TokenType,
)


# --- A. 空文字列 → None 正規化 ---

class TestAddressInputEmptyNormalization:
    def _base(self, **kwargs) -> dict:
        return {"address_type": "billing", **kwargs}

    def test_email_empty_str_becomes_none(self):
        a = AddressInput(**self._base(email=""))
        assert a.email is None

    def test_telephone_empty_str_becomes_none(self):
        a = AddressInput(**self._base(telephone=""))
        assert a.telephone is None

    def test_branch_name_empty_str_becomes_none(self):
        a = AddressInput(**self._base(branch_name=""))
        assert a.branch_name is None

    def test_name_empty_str_becomes_none(self):
        a = AddressInput(**self._base(name=""))
        assert a.name is None

    def test_tax_id_empty_str_becomes_none(self):
        a = AddressInput(**self._base(tax_id=""))
        assert a.tax_id is None

    def test_address_line1_empty_str_becomes_none(self):
        a = AddressInput(**self._base(address_line_1=""))
        assert a.address_line_1 is None

    def test_address_line2_empty_str_becomes_none(self):
        a = AddressInput(**self._base(address_line_2=""))
        assert a.address_line_2 is None

    def test_address_line3_empty_str_becomes_none(self):
        a = AddressInput(**self._base(address_line_3=""))
        assert a.address_line_3 is None

    def test_city_empty_str_becomes_none(self):
        a = AddressInput(**self._base(city=""))
        assert a.city is None

    def test_state_empty_str_becomes_none(self):
        a = AddressInput(**self._base(state=""))
        assert a.state is None

    def test_zip_empty_str_becomes_none(self):
        a = AddressInput(**self._base(zip=""))
        assert a.zip is None

    def test_country_code_empty_str_becomes_none(self):
        a = AddressInput(**self._base(country_code=""))
        assert a.country_code is None

    def test_all_empty_fields_no_error(self):
        """フロントが全フィールド空文字列で送信しても 422 にならない"""
        a = AddressInput(
            address_type="billing",
            branch_name="", name="", email="", telephone="",
            tax_id="", address_line_1="", address_line_2="", address_line_3="",
            city="", state="", zip="", country_code="",
        )
        assert a.email is None
        assert a.telephone is None
        assert a.country_code is None


# --- B. email / telephone 形式バリデーション ---

class TestAddressInputFormatValidation:
    def _base(self, **kwargs) -> dict:
        return {"address_type": "delivery", **kwargs}

    def test_valid_email_accepted(self):
        a = AddressInput(**self._base(email="foo@example.com"))
        assert a.email == "foo@example.com"

    def test_invalid_email_raises_422(self):
        with pytest.raises(ValidationError, match="メールアドレス"):
            AddressInput(**self._base(email="not-an-email"))

    def test_valid_telephone_accepted(self):
        a = AddressInput(**self._base(telephone="09012345678"))
        assert a.telephone == "09012345678"

    def test_invalid_telephone_raises_422(self):
        with pytest.raises(ValidationError, match="電話番号"):
            AddressInput(**self._base(telephone="abc"))


# --- C. country_code 正規化・バリデーション ---

class TestAddressInputCountryCode:
    def _base(self, **kwargs) -> dict:
        return {"address_type": "billing", **kwargs}

    def test_lowercase_normalized_to_upper(self):
        a = AddressInput(**self._base(country_code="jp"))
        assert a.country_code == "JP"

    def test_valid_jp(self):
        a = AddressInput(**self._base(country_code="JP"))
        assert a.country_code == "JP"

    def test_none_accepted(self):
        a = AddressInput(**self._base(country_code=None))
        assert a.country_code is None

    def test_empty_str_becomes_none(self):
        a = AddressInput(**self._base(country_code=""))
        assert a.country_code is None

    def test_3char_raises_422(self):
        with pytest.raises(ValidationError, match="country_code"):
            AddressInput(**self._base(country_code="JPN"))

    def test_numeric_raises_422(self):
        with pytest.raises(ValidationError, match="country_code"):
            AddressInput(**self._base(country_code="12"))


# --- D. RegisterRequest contact — ADR-126 追補: 担当者名は任意 ---

class TestRegisterRequestContact:
    """ADR-126 追補: Contact Name は任意。空欄での送信は 422 にならない。
    フォールバック（billing_display_name → display_name）はルーター層で行うため
    スキーマ単体テストでは contact_name=None/空 が通ることのみ検証する。
    """

    def _base(self, **kwargs) -> dict:
        return {"token": "tok", "addresses": [], **kwargs}

    def test_name_and_email_ok(self):
        r = RegisterRequest(**self._base(contact_name="田中", contact_email="t@example.com"))
        assert r.contact_name == "田中"

    def test_name_and_telephone_ok(self):
        r = RegisterRequest(**self._base(contact_name="田中", contact_telephone="09012345678"))
        assert r.contact_telephone == "09012345678"

    def test_all_contact_fields_empty_accepted(self):
        """全担当者フィールド未入力でバリデーションエラーにならない（ADR-126 追補）"""
        r = RegisterRequest(**self._base())
        assert r.contact_name is None
        assert r.contact_email is None
        assert r.contact_telephone is None

    def test_empty_name_accepted(self):
        """contact_name="" も None として扱われ、エラーにならない"""
        r = RegisterRequest(**self._base(contact_name="", contact_email="t@example.com"))
        assert r.contact_name is None

    def test_name_only_no_email_accepted(self):
        """担当者名のみ（メール・電話なし）でもエラーにならない"""
        r = RegisterRequest(**self._base(contact_name="田中"))
        assert r.contact_name == "田中"

    def test_contact_email_empty_str_becomes_none(self):
        """contact_email="" は None として扱われる"""
        r = RegisterRequest(**self._base(
            contact_name="田中", contact_email="", contact_telephone="09012345678"
        ))
        assert r.contact_email is None
        assert r.contact_telephone == "09012345678"


# --- E. TokenType — ADR-127: change_billing 追加 ---

class TestTokenTypeEnum:
    """ADR-127: TokenType Enum に change_billing が含まれること。"""

    def test_register_valid(self):
        assert TokenType.register.value == "register"

    def test_add_address_valid(self):
        assert TokenType.add_address.value == "add_address"

    def test_change_billing_valid(self):
        assert TokenType.change_billing.value == "change_billing"

    def test_all_three_types_present(self):
        values = {t.value for t in TokenType}
        assert values == {"register", "add_address", "change_billing"}


# --- F. ChangeBillingRequest スキーマ — ADR-127 §2 ---

class TestChangeBillingRequest:
    """ADR-127 B-2: ChangeBillingRequest の入力契約を検証する。"""

    def _base_address(self, **kwargs) -> dict:
        return {"address_type": "billing", **kwargs}

    def _base(self, **kwargs) -> dict:
        return {
            "token": "tok",
            "address": self._base_address(**kwargs),
        }

    def test_minimal_valid(self):
        """token + billing address だけで ValidationError にならない"""
        req = ChangeBillingRequest(**self._base())
        assert req.token == "tok"
        assert req.address.address_type == "billing"

    def test_billing_display_name_optional(self):
        req = ChangeBillingRequest(**self._base(name="ACME"))
        assert req.billing_display_name is None

    def test_billing_display_name_set(self):
        req = ChangeBillingRequest(
            token="tok",
            address=self._base_address(),
            billing_display_name="ACME Inc.",
        )
        assert req.billing_display_name == "ACME Inc."

    def test_payment_recipient_name_optional(self):
        req = ChangeBillingRequest(**self._base())
        assert req.payment_recipient_name is None

    def test_payment_recipient_name_set(self):
        req = ChangeBillingRequest(
            token="tok",
            address=self._base_address(),
            payment_recipient_name="ACME TRADING",
        )
        assert req.payment_recipient_name == "ACME TRADING"

    def test_address_email_validated(self):
        """AddressInput の email バリデーションが ChangeBillingRequest 内でも機能する"""
        with pytest.raises(ValidationError, match="メールアドレス"):
            ChangeBillingRequest(**self._base(email="not-an-email"))

    def test_address_country_code_normalized(self):
        req = ChangeBillingRequest(**self._base(country_code="jp"))
        assert req.address.country_code == "JP"

    def test_address_empty_strings_normalized_to_none(self):
        req = ChangeBillingRequest(**self._base(email="", city="", zip=""))
        assert req.address.email is None
        assert req.address.city is None
        assert req.address.zip is None

    def test_delivery_address_type_rejected(self):
        """change_billing は address_type='billing' 以外が渡されても Pydantic は通す (ルーター層でチェック)。
        ここではスキーマが delivery を受け付けることの確認のみ（意図的な設計）。"""
        req = ChangeBillingRequest(
            token="tok",
            address={"address_type": "delivery"},
        )
        assert req.address.address_type == "delivery"
