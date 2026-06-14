import ast
from pathlib import Path

ROUTERS_DIR = Path(__file__).resolve().parents[2] / "app" / "routers"

# Router files included from main.py without app-level dependencies because they
# operate on public schema or need mixed callback flows. These files must carry
# their own central-admin guard unless explicitly documented otherwise.
SUPER_ADMIN_GUARD_FILES: dict[str, str] = {
    "super_admin_knowledge.py": "super-admin knowledge rules",
    "super_admin_aliases.py": "super-admin supplier aliases",
    "super_admin_tcg.py": "super-admin TCG masters",
    "product_masters.py": "central product masters",
    "super_admin_dex.py": "super-admin dex masters",
    "super_admin_suppliers.py": "super-admin suppliers",
    "super_admin_link_templates.py": "super-admin link templates",
    "super_admin_llm_budget.py": "super-admin LLM budget",
    "super_admin_inbound.py": "super-admin inbound review",
    "parse_review.py": "central parse review",
    "inventory_offers.py": "super-admin inventory offers",
    "super_admin_phase_switch.py": "super-admin phase switch",
    "super_admin_tenants.py": "super-admin tenant lifecycle",
}


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _has_require_super_admin_reference(source: str) -> bool:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "require_super_admin":
            return True
        if isinstance(node, ast.Attribute) and node.attr == "require_super_admin":
            return True
    return False


def _has_guard_comment(source: str) -> bool:
    # Emergency escape hatch for intentionally mixed routers. Must be explicit so
    # reviewers see the exception in diff.
    return "SECURITY: super-admin guard exception" in source


def test_super_admin_router_files_exist():
    missing = [
        filename
        for filename in SUPER_ADMIN_GUARD_FILES
        if not (ROUTERS_DIR / filename).exists()
    ]

    assert missing == []


def test_super_admin_router_files_reference_guard_or_explicit_exception():
    missing_guard: list[str] = []
    for filename in sorted(SUPER_ADMIN_GUARD_FILES):
        path = ROUTERS_DIR / filename
        source = _source(path)
        if _has_require_super_admin_reference(source):
            continue
        if _has_guard_comment(source):
            continue
        missing_guard.append(filename)

    assert missing_guard == []


def test_super_admin_guard_file_reasons_are_documented():
    missing_reason = [
        filename
        for filename, reason in SUPER_ADMIN_GUARD_FILES.items()
        if not reason.strip()
    ]

    assert missing_reason == []
