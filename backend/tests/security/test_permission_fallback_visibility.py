from pathlib import Path

from prometheus_client import REGISTRY

from app.metrics import record_permission_fallback

DEPENDENCIES_PATH = Path(__file__).resolve().parents[2] / "app" / "auth" / "dependencies.py"


def _counter_value(fallback: str) -> float:
    sample_name = "permission_fallback_total"
    for metric in REGISTRY.collect():
        for sample in metric.samples:
            if sample.name == sample_name and sample.labels.get("fallback") == fallback:
                return float(sample.value)
    return 0.0


def test_permission_fallback_metric_helper_records_low_cardinality_counter():
    before = _counter_value("admin_role_all_permissions")

    record_permission_fallback("admin_role_all_permissions")

    after = _counter_value("admin_role_all_permissions")
    assert after == before + 1


def test_admin_role_permission_fallback_still_exists_and_is_visible_to_reviewers():
    source = DEPENDENCIES_PATH.read_text(encoding="utf-8")

    assert "admin後方互換" in source
    assert "row and row[0] == \"admin\"" in source
    assert "SELECT key FROM public.permissions" in source
