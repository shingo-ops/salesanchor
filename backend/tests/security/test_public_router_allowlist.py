import ast
from pathlib import Path

MAIN_PATH = Path(__file__).resolve().parents[2] / "app" / "main.py"

# Routers intentionally included without app-level dependencies.
# Every item must have a reason. New dependency-free routers must be added here
# intentionally instead of slipping into public surface by accident.
ALLOWED_DEPENDENCY_FREE_ROUTERS: dict[str, str] = {
    # Public unauthenticated endpoints.
    "health.router": "Public health check used by monitoring.",
    "auth.router": "Login/auth endpoints start before an authenticated session exists.",
    "webhook.router": "External Meta webhook entrypoint; provider verification is handled in router.",
    "meta.router": "Meta data deletion callback/status API are public callback endpoints.",
    "contact.router": "LP contact form submit endpoint.",
    "registration_tokens.public_router": "Customer registration token public flow; token signature handles access.",
    "integrations.public_router": "OAuth callback/public integration entrypoints.",
    "google_calendar.public_router": "Google Calendar callback/webhook entrypoints.",

    # Router-internal guards. These are not public by intent, but main.py does not
    # attach app-level dependencies because the routers need public schema or mixed callback flows.
    "discord_oauth.router": "Mixed flow: start is tenant-authenticated inside router, callback is public.",
    "super_admin_knowledge.router": "Super-admin router; guard is expected inside router.",
    "super_admin_aliases.router": "Super-admin router; guard is expected inside router.",
    "super_admin_tcg.router": "Super-admin router; guard is expected inside router.",
    "product_masters.router": "Central product master router; guard is expected inside router.",
    "super_admin_dex.router": "Super-admin router; guard is expected inside router.",
    "super_admin_suppliers.router": "Super-admin router; guard is expected inside router.",
    "super_admin_link_templates.router": "Super-admin router; guard is expected inside router.",
    "super_admin_llm_budget.router": "Super-admin router; guard is expected inside router.",
    "super_admin_inbound.router": "Super-admin router; guard is expected inside router.",
    "parse_review.router": "Central parse review router; guard is expected inside router.",
    "inventory_offers.router": "Super-admin guarded in router per main.py comment.",
    "me_inventory_filters.router": "Current-user endpoint; guard is expected inside router.",
    "super_admin_phase_switch.router": "Super-admin router; guard is expected inside router.",
    "super_admin_tenants.router": "Super-admin router; guard is expected inside router.",
}


def _has_dependencies_keyword(call: ast.Call) -> bool:
    for keyword in call.keywords:
        if keyword.arg == "dependencies":
            value = keyword.value
            if isinstance(value, ast.List) and not value.elts:
                return False
            return True
    return False


def _include_router_calls() -> list[tuple[int, str, bool]]:
    tree = ast.parse(MAIN_PATH.read_text(encoding="utf-8"))
    calls: list[tuple[int, str, bool]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (
            isinstance(func, ast.Attribute)
            and func.attr == "include_router"
            and isinstance(func.value, ast.Name)
            and func.value.id == "app"
        ):
            continue
        if not node.args:
            continue
        router_expr = ast.unparse(node.args[0])
        calls.append((node.lineno, router_expr, _has_dependencies_keyword(node)))
    return sorted(calls)


def test_dependency_free_router_includes_are_explicitly_allowlisted():
    unclassified = [
        (lineno, router_expr)
        for lineno, router_expr, has_dependencies in _include_router_calls()
        if not has_dependencies and router_expr not in ALLOWED_DEPENDENCY_FREE_ROUTERS
    ]

    assert unclassified == []


def test_allowlist_entries_have_reasons():
    missing_reasons = [
        router_expr
        for router_expr, reason in ALLOWED_DEPENDENCY_FREE_ROUTERS.items()
        if not reason.strip()
    ]

    assert missing_reasons == []


def test_allowlist_entries_match_existing_dependency_free_router_includes():
    dependency_free = {
        router_expr
        for _, router_expr, has_dependencies in _include_router_calls()
        if not has_dependencies
    }
    stale_entries = sorted(set(ALLOWED_DEPENDENCY_FREE_ROUTERS) - dependency_free)

    assert stale_entries == []
