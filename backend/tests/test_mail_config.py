"""メール送信の設定の読み取り口（ADR-1013 便3）のテスト。"""

import pytest

from app.services import mail_config

_NAMES = ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "MAIL_FROM", "CONTACT_NOTIFY_EMAIL")


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in _NAMES:
        monkeypatch.delenv(name, raising=False)


def _full(monkeypatch, **overrides):
    values = {
        "SMTP_HOST": "smtp.example.test",
        "SMTP_PORT": "2525",
        "SMTP_USER": "user@example.test",
        "SMTP_PASSWORD": "s3cret-value-xyz",
        "MAIL_FROM": "from@example.test",
    }
    values.update(overrides)
    for k, v in values.items():
        monkeypatch.setenv(k, v)


def test_all_set_returns_values(monkeypatch):
    _full(monkeypatch)
    s = mail_config.smtp_settings()
    assert s is not None
    assert (s.host, s.port, s.user, s.password, s.mail_from) == (
        "smtp.example.test", 2525, "user@example.test", "s3cret-value-xyz", "from@example.test",
    )


@pytest.mark.parametrize("name", ["SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "MAIL_FROM"])
@pytest.mark.parametrize("blank", ["", "   "])
def test_any_blank_returns_none(monkeypatch, name, blank):
    _full(monkeypatch, **{name: blank})
    assert mail_config.smtp_settings() is None


def test_unset_returns_none():
    assert mail_config.smtp_settings() is None


@pytest.mark.parametrize("raw", ["", "abc"])
def test_bad_port_falls_back_to_587(monkeypatch, raw):
    _full(monkeypatch, SMTP_PORT=raw)
    assert mail_config.smtp_settings().port == 587


def test_unset_port_is_587(monkeypatch):
    _full(monkeypatch)
    monkeypatch.delenv("SMTP_PORT")
    assert mail_config.smtp_settings().port == 587


def test_contact_notify_email_empty_uses_default(monkeypatch):
    monkeypatch.setenv("CONTACT_NOTIFY_EMAIL", "")
    assert mail_config.contact_notify_email() == "support@salesanchor.jp"
    monkeypatch.delenv("CONTACT_NOTIFY_EMAIL")
    assert mail_config.contact_notify_email() == "support@salesanchor.jp"


def test_contact_notify_email_set(monkeypatch):
    monkeypatch.setenv("CONTACT_NOTIFY_EMAIL", "ops@example.test")
    assert mail_config.contact_notify_email() == "ops@example.test"


def test_repr_does_not_contain_password(monkeypatch):
    _full(monkeypatch)
    s = mail_config.smtp_settings()
    assert "s3cret-value-xyz" not in repr(s)
    assert "s3cret-value-xyz" not in str(s)
