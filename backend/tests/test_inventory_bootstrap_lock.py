"""Shared public DDL must acquire the same lock, including exceptional exits."""
from __future__ import annotations

import ast
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

CASES = [
    ("test_inventory_parser_real_samples.py", "_ensure_inventory_schema"),
    ("test_inventory_sprint1_migrations.py", "_apply_public_migrations"),
    ("test_products_tcg_type_fk.py", "_bootstrap_public_products"),
    ("test_inventory_aggregated.py", "seed_aggregated_dataset"),
]


class ProbeError(Exception):
    def __init__(self, sqlstate):
        self.orig = SimpleNamespace(sqlstate=sqlstate)


class MigrationPath:
    @property
    def parents(self):
        return [self, self, self]

    def __truediv__(self, other):
        return self

    def read_text(self, *args):
        return "SELECT 1;"


class RemoveLocalImports(ast.NodeTransformer):
    """Load only the actual setup function, without application imports/fixtures."""

    def visit_Import(self, node):
        return None

    def visit_ImportFrom(self, node):
        return None


def load_setup(filename, function, namespace):
    path = Path(__file__).with_name(filename)
    tree = ast.parse(path.read_text())
    selected = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == function)
    selected.decorator_list = []
    selected = RemoveLocalImports().visit(selected)
    nodes = [selected]
    if filename == "test_inventory_parser_real_samples.py":
        nodes += [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_is_idempotent_migration_error"]
        nodes += [n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "_IDEMPOTENT_PG_SQLSTATES" for t in n.targets)]
    module = ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[]))
    namespace["__file__"] = str(path)
    exec(compile(module, str(path), "exec"), namespace)
    return namespace[function]


@pytest.mark.asyncio
@pytest.mark.parametrize("filename,function", CASES)
@pytest.mark.parametrize("sqlstate", [None, "23505"])
async def test_setup_holds_public_lock_and_propagates_errors(filename, function, sqlstate):
    events = []
    owner = None
    failure = ProbeError(sqlstate)

    @asynccontextmanager
    async def lock(engine):
        nonlocal owner
        assert owner is None
        owner = asyncio.current_task()
        events.append("lock")
        try:
            yield
        finally:
            owner = None
            events.append("unlock")

    class Connection:
        async def execute(self, statement):
            assert owner is asyncio.current_task(), "shared DDL ran without owning the public lock"
            events.append("ddl")
            await asyncio.sleep(0)
            raise failure

        exec_driver_sql = execute

    class Engine:
        @asynccontextmanager
        async def begin(self):
            assert owner is asyncio.current_task(), "transaction opened before shared public lock"
            yield Connection()

    engine = Engine()

    async def apply_migration(eng, filename):
        async with eng.begin() as conn:
            await conn.exec_driver_sql("SELECT 1")

    namespace = {
        "public_bootstrap_lock": lock,
        "pathlib": SimpleNamespace(Path=lambda *args: MigrationPath()),
        "Path": lambda *args: MigrationPath(),
        "MIGRATIONS_DIR": MigrationPath(),
        "_PG_BOOTSTRAP_MIGRATIONS": ["probe.sql"],
        "_apply_migration": apply_migration,
        "_split_sql_preserving_do_blocks": lambda sql: [sql],
        "create_async_engine": lambda *args, **kwargs: engine,
        "_PG_URL": "unused-test-value",
        "text": lambda sql: sql,
    }
    setup = load_setup(filename, function, namespace)
    with pytest.raises(ProbeError) as caught:
        if function == "seed_aggregated_dataset":
            await anext(setup())
        else:
            await setup(engine)
    assert caught.value is failure
    assert events == ["lock", "ddl", "unlock"]
    assert owner is None
