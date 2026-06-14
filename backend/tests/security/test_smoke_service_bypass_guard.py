from app.auth import dependencies


def test_smoke_bypass_disabled_without_token_and_email(monkeypatch):
    monkeypatch.setattr(dependencies, "_SMOKE_SERVICE_TOKEN", "")
    monkeypatch.setattr(dependencies, "_SMOKE_SERVICE_EMAIL", "")
    monkeypatch.setenv("ENVIRONMENT", "development")

    assert dependencies._smoke_service_bypass_enabled() is False


def test_smoke_bypass_enabled_in_non_production_when_configured(monkeypatch):
    monkeypatch.setattr(dependencies, "_SMOKE_SERVICE_TOKEN", "token")
    monkeypatch.setattr(dependencies, "_SMOKE_SERVICE_EMAIL", "smoke@example.com")
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.delenv("ALLOW_SMOKE_SERVICE_BYPASS_IN_PRODUCTION", raising=False)

    assert dependencies._smoke_service_bypass_enabled() is True


def test_smoke_bypass_disabled_in_production_without_explicit_allow(monkeypatch):
    monkeypatch.setattr(dependencies, "_SMOKE_SERVICE_TOKEN", "token")
    monkeypatch.setattr(dependencies, "_SMOKE_SERVICE_EMAIL", "smoke@example.com")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("ALLOW_SMOKE_SERVICE_BYPASS_IN_PRODUCTION", raising=False)

    assert dependencies._smoke_service_bypass_enabled() is False


def test_smoke_bypass_enabled_in_production_with_explicit_allow(monkeypatch):
    monkeypatch.setattr(dependencies, "_SMOKE_SERVICE_TOKEN", "token")
    monkeypatch.setattr(dependencies, "_SMOKE_SERVICE_EMAIL", "smoke@example.com")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ALLOW_SMOKE_SERVICE_BYPASS_IN_PRODUCTION", "1")

    assert dependencies._smoke_service_bypass_enabled() is True


def test_env_flag_accepts_true_values(monkeypatch):
    for value in ("1", "true", "yes", "on", "TRUE", " On "):
        monkeypatch.setenv("TEST_FLAG", value)
        assert dependencies._env_flag("TEST_FLAG") is True


def test_env_flag_rejects_default_and_false_values(monkeypatch):
    monkeypatch.delenv("TEST_FLAG", raising=False)
    assert dependencies._env_flag("TEST_FLAG") is False

    for value in ("0", "false", "no", "off", ""):
        monkeypatch.setenv("TEST_FLAG", value)
        assert dependencies._env_flag("TEST_FLAG") is False
