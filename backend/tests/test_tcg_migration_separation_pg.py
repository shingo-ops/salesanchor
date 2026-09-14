"""V1-V6 migration-separation characterization in disposable PostgreSQL databases.

The data in this module is artificial verification data.  The shared ``pg``
fixture refuses anything except GitHub Actions' local ``jarvis_test_db`` and
creates a random database for every case.  Additional databases retain those
same guards and are left for the disposable PostgreSQL service to destroy.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import psycopg2
import pytest
from psycopg2 import sql
from sqlalchemy.engine import URL, make_url

from tests import test_tcg_work_matching_integration as work_fixture

pg = work_fixture.pg
SCHEMA = work_fixture.SCHEMA
MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"

INITIAL = "20260906_120000_create_tcg_tables_t001.sql"
LEGACY_ANALYSIS = "20260831_110000_create_tcg_analysis_tables_t004.sql"
CLASSIFICATION_MASTERS = "20260902_110000_tcg_classification_masters.sql"
CLASSIFICATION = "20260902_110100_tcg_products_classification_ids.sql"
MARK_ENGLISH = "20260903_180000_tcg_products_mark_en_t004.sql"
BATCH1 = "20260905_010000_tcg_pokemon_master_batch1_t004.sql"
CARDSET = "20260913_200000_tcg_cardset_exclusion.sql"
BUNDLE = "20260913_210000_tcg_cardset_bundle_registration.sql"
ABBREVIATIONS = "20260914_080000_add_abbreviation_keywords_t004.sql"
HISTORY = "20260906_130000_create_tcg_product_import_history_t004.sql"

SOURCE_SHA256 = {
    INITIAL: "e3d84e6a2a9de0b4746b8fb19397885be695aa495a870b30fbce29707161eb24",
    LEGACY_ANALYSIS: "46f05828c20298fcc932ee9094fdeb6caf59d417a9400099bec592e49413feda",
    CLASSIFICATION_MASTERS: "5585e3fd3c9d9f06d015a1c0edea532b36691ee115a77dafc68ee72c89a370a9",
    CLASSIFICATION: "f91ecf158dc21559739b7ed70382bc6655b4dc4221570afb37a21a57f7c820db",
    MARK_ENGLISH: "2a44eb1f7bb7538b4fcc761db34511299c4edc07bff72ce332b9064663189080",
    BATCH1: "5274436c08a71e9136aa67bc2d1b059964339bd1d9843261c39b355341bb4616",
    CARDSET: "ba03492e5e079e65d88806310f5ecc95e543e2ff5ecea22971bfa341bf6a271d",
    BUNDLE: "3199a1f6658ef9bac16d5c3cb77e2e7807e6257ad40a30e9820f03f2981c7691",
    ABBREVIATIONS: "ab4c478823a04ef02767023c88597bbd649d4af5517c9c77b03a97d4aa1074d5",
    HISTORY: "fc3f089a8cd132fa1f0081a620a377da97ba1b5217d793740d4c9a77a8bfc2eb",
}

CORE_TABLES = {
    "tcg_major_categories",
    "tcg_series",
    "tcg_manufacturers",
    "tcg_product_categories",
    "tcg_products",
    "product_search_keywords",
    "product_exclude_keywords",
}

PRODUCTION_CONSTRAINT_DEFINITIONS = {
    ("analysis_results", "FOREIGN KEY (product_id) REFERENCES {schema}.tcg_products(id)"),
    ("product_exclude_keywords", "PRIMARY KEY (id)"),
    (
        "product_exclude_keywords",
        "FOREIGN KEY (product_id) REFERENCES {schema}.tcg_products(id) ON DELETE CASCADE",
    ),
    ("product_exclude_keywords", "UNIQUE (product_id, keyword)"),
    ("product_search_keywords", "PRIMARY KEY (id)"),
    (
        "product_search_keywords",
        "FOREIGN KEY (product_id) REFERENCES {schema}.tcg_products(id) ON DELETE CASCADE",
    ),
    ("product_search_keywords", "UNIQUE (product_id, keyword)"),
    (
        "products_logistics",
        "FOREIGN KEY (product_id) REFERENCES {schema}.tcg_products(id) ON DELETE CASCADE",
    ),
    ("tcg_major_categories", "UNIQUE (code)"),
    ("tcg_major_categories", "PRIMARY KEY (id)"),
    ("tcg_manufacturers", "UNIQUE (code)"),
    ("tcg_manufacturers", "PRIMARY KEY (id)"),
    ("tcg_product_categories", "UNIQUE (code)"),
    ("tcg_product_categories", "PRIMARY KEY (id)"),
    (
        "tcg_products",
        "FOREIGN KEY (division_id) REFERENCES {schema}.tcg_major_categories(id)",
    ),
    (
        "tcg_products",
        "FOREIGN KEY (manufacturer_id) REFERENCES {schema}.tcg_manufacturers(id)",
    ),
    (
        "tcg_products",
        "FOREIGN KEY (product_category_id) REFERENCES {schema}.tcg_product_categories(id)",
    ),
    ("tcg_products", "FOREIGN KEY (work_id) REFERENCES {schema}.tcg_series(id)"),
    ("tcg_products", "UNIQUE (code)"),
    ("tcg_products", "PRIMARY KEY (id)"),
    ("tcg_series", "UNIQUE (code)"),
    ("tcg_series", "PRIMARY KEY (id)"),
}

CURRENT_TITLE_EDITS = {
    "PM0276": "MEGA 30th CELEBRATION カードセット フシギダネ・ヒトカゲ・ゼニガメ",
    "PM0277": "MEGA 30th CELEBRATION カードセット チコリータ・ヒノアラシ・ワニノコ",
    "PM0278": "MEGA 30th CELEBRATION カードセット キモリ・アチャモ・ミズゴロウ",
    "PM0279": "MEGA 30th CELEBRATION カードセット ナエトル・ヒコザル・ポッチャマ",
    "PM0280": "MEGA 30th CELEBRATION カードセット ツタージャ・ポカブ・ミジュマル",
    "PM0281": "MEGA 30th CELEBRATION カードセット ハリマロン・フォッコ・ケロマツ",
    "PM0282": "MEGA 30th CELEBRATION カードセット モクロー・ニャビー・アシマリ",
    "PM0283": "MEGA 30th CELEBRATION カードセット サルノリ・ヒバニー・メッソン",
    "PM0284": "MEGA 30th CELEBRATION カードセット ニャオハ・ホゲータ・クワッス",
    "PM0264": "30th CELEBRATION FUTURISTIC BOX",
    "PM0265": "30th CELEBRATION プレミアムデッキセット エーフィ・ブラッキー",
}

V4_SEARCH_WORDS = {
    "PM0276": "カードセット フシギダネ",
    "PM0277": "カードセット チコリータ",
    "PM0278": "カードセット キモリ",
    "PM0279": "カードセット ナエトル",
    "PM0280": "カードセット ツタージャ",
    "PM0281": "カードセット ハリマロン",
    "PM0282": "カードセット モクロー",
    "PM0283": "カードセット サルノリ",
    "PM0284": "カードセット ニャオハ",
}


def emit(capsys: pytest.CaptureFixture[str], case: str, **observations: object) -> None:
    with capsys.disabled():
        print(json.dumps({"case": case, **observations}, ensure_ascii=False, sort_keys=True))


def migration(name: str) -> str:
    raw = (MIGRATIONS / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == SOURCE_SHA256[name]
    return raw.decode()


def for_schema(name: str, schema: str) -> str:
    return migration(name).replace("tenant_004", schema).replace("tenant_001", schema)


def classification_structure(schema: str) -> str:
    lines = migration(CLASSIFICATION).splitlines()
    assert lines[8] == "DO $$"
    assert lines[18].strip().startswith("-- 1. tcg_products 4 UUID")
    assert lines[70].strip() == "END IF;"
    return "\n".join(lines[:71] + ["END $$;"]).replace("tenant_004", schema)


def mark_english_structure(schema: str) -> str:
    lines = migration(MARK_ENGLISH).splitlines()
    assert lines[14] == "DO $body$"
    assert lines[26].strip().startswith("-- mark")
    assert lines[50].strip() == "END IF;"
    return "\n".join(lines[:51] + ["END;", "$body$;"]).replace("tenant_004", schema)


def add_word_uniques(cursor: psycopg2.extensions.cursor, schema: str) -> None:
    for short, table in (("sk", "product_search_keywords"), ("ek", "product_exclude_keywords")):
        cursor.execute(
            sql.SQL("ALTER TABLE {}.{} ADD CONSTRAINT {} UNIQUE (product_id, keyword)").format(
                sql.Identifier(schema),
                sql.Identifier(table),
                sql.Identifier(f"uq_{short}_product_keyword"),
            )
        )


def seed_product(
    cursor: psycopg2.extensions.cursor,
    schema: str,
    code: str,
    title: str,
    *,
    references: tuple[str, str, str, str] = ("DIV01", "IP001", "MK001", "PC_BOX"),
    english: str | None = "verification english",
    mark: str | None = "VERIFY",
    active: bool = False,
) -> str:
    cursor.execute(
        sql.SQL(
            """INSERT INTO {}.tcg_products
            (code,japanese_title,english_title,mark,release_date,category_class,
             division_id,work_id,manufacturer_id,product_category_id,
             required_output_value,is_active)
            SELECT %s,%s,%s,%s,DATE '2030-02-03','Box',d.id,w.id,m.id,c.id,
                   'artificial verification value',%s
            FROM {}.tcg_major_categories d, {}.tcg_series w,
                 {}.tcg_manufacturers m, {}.tcg_product_categories c
            WHERE d.code=%s AND w.code=%s AND m.code=%s AND c.code=%s
            RETURNING id"""
        ).format(*[sql.Identifier(schema)] * 5),
        (code, title, english, mark, active, *references),
    )
    return str(cursor.fetchone()[0])


def product_snapshot(connection: psycopg2.extensions.connection, schema: str, code: str) -> dict:
    with connection.cursor() as cursor:
        cursor.execute(
            sql.SQL("SELECT to_jsonb(p) FROM {}.tcg_products p WHERE code=%s").format(sql.Identifier(schema)),
            (code,),
        )
        product = cursor.fetchone()[0]
        words = {}
        for table in ("product_search_keywords", "product_exclude_keywords"):
            cursor.execute(
                sql.SQL("SELECT to_jsonb(k) FROM {}.{} k WHERE product_id=%s ORDER BY position,id").format(
                    sql.Identifier(schema), sql.Identifier(table)
                ),
                (product["id"],),
            )
            words[table] = [row[0] for row in cursor.fetchall()]
    return {"product": product, **words}


def schema_snapshot(
    connection: psycopg2.extensions.connection,
    schema: str,
    tables: tuple[str, ...],
) -> dict[str, list[str]]:
    result = {}
    with connection.cursor() as cursor:
        for table in tables:
            cursor.execute(
                sql.SQL("SELECT to_jsonb(t)::text FROM {}.{} t ORDER BY to_jsonb(t)::text").format(
                    sql.Identifier(schema), sql.Identifier(table)
                )
            )
            result[table] = [row[0] for row in cursor.fetchall()]
    return result


@contextmanager
def additional_database(source_url: URL, prefix: str):
    assert os.getenv("GITHUB_ACTIONS") == "true"
    assert source_url.host in ("localhost", "127.0.0.1")
    assert source_url.database.startswith("tcg_work_test_")
    configured = make_url(os.environ["RLS_ADMIN_DATABASE_URL"])
    assert configured.host in ("localhost", "127.0.0.1")
    assert configured.database == "jarvis_test_db"
    name = f"{prefix}_{uuid4().hex}"
    kwargs = dict(
        host=configured.host,
        port=configured.port,
        user=configured.username,
        password=configured.password,
    )
    admin = psycopg2.connect(dbname=configured.database, **kwargs)
    admin.autocommit = True
    try:
        with admin.cursor() as cursor:
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    finally:
        admin.close()
    connection = psycopg2.connect(dbname=name, **kwargs)
    connection.autocommit = True
    try:
        yield connection, configured.set(database=name)
    finally:
        connection.close()


def test_v1_initial_ddl_has_twenty_of_twenty_two_product_constraints(pg, capsys):
    connection, _, _ = pg
    migration(INITIAL)
    with connection.cursor() as cursor:
        cursor.execute(
            """SELECT r.relname, c.conname, pg_get_constraintdef(c.oid)
               FROM pg_constraint c
               JOIN pg_class r ON r.oid=c.conrelid
               JOIN pg_namespace n ON n.oid=r.relnamespace
               WHERE n.nspname=%s
                 AND (r.relname=ANY(%s)
                      OR c.conname IN ('analysis_results_product_id_fkey',
                                       'products_logistics_product_id_fkey'))
               ORDER BY r.relname,c.conname""",
            (SCHEMA, sorted(CORE_TABLES)),
        )
        rows = cursor.fetchall()
        cursor.execute(
            """SELECT column_name,data_type,is_nullable
               FROM information_schema.columns
               WHERE table_schema=%s AND table_name='tcg_products'
               ORDER BY ordinal_position""",
            (SCHEMA,),
        )
        columns = cursor.fetchall()
    actual = {(table, definition.replace(f"{SCHEMA}.", "{schema}.")) for table, _, definition in rows}
    missing = PRODUCTION_CONSTRAINT_DEFINITIONS - actual
    assert actual <= PRODUCTION_CONSTRAINT_DEFINITIONS
    assert len(actual) == 20
    assert missing == {
        ("product_search_keywords", "UNIQUE (product_id, keyword)"),
        ("product_exclude_keywords", "UNIQUE (product_id, keyword)"),
    }
    assert len(columns) == 14
    assert [column[0] for column in columns] == [
        "id",
        "code",
        "japanese_title",
        "release_date",
        "category_class",
        "division_id",
        "work_id",
        "manufacturer_id",
        "product_category_id",
        "required_output_value",
        "is_active",
        "created_at",
        "mark",
        "english_title",
    ]
    emit(capsys, "V1", initial_constraints=20, production_constraints=22, missing_unique=2)


def test_v2_structure_fragments_preserve_csv_equivalent_edits_twice(pg, capsys):
    connection, _, _ = pg
    schema = "tenant_902"
    with connection.cursor() as cursor:
        cursor.execute(for_schema(LEGACY_ANALYSIS, schema))
        cursor.execute(for_schema(CLASSIFICATION_MASTERS, schema))
        cursor.execute(classification_structure(schema))
        cursor.execute(mark_english_structure(schema))
        product_id = seed_product(
            cursor,
            schema,
            "PM0001",
            "人工検証商品・編集後",
            references=("DIV02", "IP002", "MK002", "PC_SINGLE"),
            english="edited english",
            mark="EDITED",
        )
        cursor.execute(
            sql.SQL(
                "INSERT INTO {}.product_search_keywords(product_id,keyword,position) VALUES (%s,%s,7),(%s,%s,3)"
            ).format(sql.Identifier(schema)),
            (product_id, "edited search two", product_id, "edited search one"),
        )
        cursor.execute(
            sql.SQL("INSERT INTO {}.product_exclude_keywords(product_id,keyword,position) VALUES (%s,%s,4)").format(
                sql.Identifier(schema)
            ),
            (product_id, "edited exclusion"),
        )
    before = product_snapshot(connection, schema, "PM0001")
    with connection.cursor() as cursor:
        for _ in range(2):
            cursor.execute(classification_structure(schema))
            cursor.execute(mark_english_structure(schema))
        cursor.execute(
            """SELECT count(*) FROM pg_constraint c
               JOIN pg_class r ON r.oid=c.conrelid
               JOIN pg_namespace n ON n.oid=r.relnamespace
               WHERE n.nspname=%s AND r.relname='tcg_products'
                 AND c.conname LIKE 'fk_tcg_products_%_id'""",
            (schema,),
        )
        assert cursor.fetchone()[0] == 4
    assert product_snapshot(connection, schema, "PM0001") == before
    emit(
        capsys,
        "V2-structure",
        runs=2,
        editable_fields=10,
        row_differences=0,
        source_sha256={
            LEGACY_ANALYSIS: SOURCE_SHA256[LEGACY_ANALYSIS],
            CLASSIFICATION_MASTERS: SOURCE_SHA256[CLASSIFICATION_MASTERS],
            CLASSIFICATION: SOURCE_SHA256[CLASSIFICATION],
            MARK_ENGLISH: SOURCE_SHA256[MARK_ENGLISH],
        },
    )


def test_v2_current_mark_english_coalesce_preserves_nonnull_and_refills_null(pg, capsys):
    connection, _, _ = pg
    with connection.cursor() as cursor:
        seed_product(cursor, SCHEMA, "PM0001", "人工検証商品", english="keep english", mark="KEEP")
        cursor.execute(for_schema(MARK_ENGLISH, SCHEMA))
        cursor.execute(for_schema(MARK_ENGLISH, SCHEMA))
        cursor.execute(
            sql.SQL("SELECT mark,english_title FROM {}.tcg_products WHERE code='PM0001'").format(sql.Identifier(SCHEMA))
        )
        assert cursor.fetchone() == ("KEEP", "keep english")
        cursor.execute(
            sql.SQL("UPDATE {}.tcg_products SET mark=NULL,english_title=NULL WHERE code='PM0001'").format(
                sql.Identifier(SCHEMA)
            )
        )
        null_snapshot = product_snapshot(connection, SCHEMA, "PM0001")
        cursor.execute(for_schema(MARK_ENGLISH, SCHEMA))
        cursor.execute(
            sql.SQL("SELECT mark,english_title FROM {}.tcg_products WHERE code='PM0001'").format(sql.Identifier(SCHEMA))
        )
        assert cursor.fetchone() == ("MMD", "Monster ball Miror duplicate bulk set")
    refilled = product_snapshot(connection, SCHEMA, "PM0001")
    for key, value in null_snapshot["product"].items():
        if key not in {"mark", "english_title"}:
            assert refilled["product"][key] == value
    assert refilled["product_search_keywords"] == null_snapshot["product_search_keywords"]
    assert refilled["product_exclude_keywords"] == null_snapshot["product_exclude_keywords"]
    emit(capsys, "V2-coalesce", nonnull_preserved=2, null_refilled=2, source_sha256=SOURCE_SHA256[MARK_ENGLISH])


def test_v3_current_bundle_accepts_eleven_title_edits(pg, capsys):
    connection, _, _ = pg
    work_fixture.seed_bundle_dictionary(connection, "tenant_004")
    with connection.cursor() as cursor:
        cursor.executemany(
            "UPDATE tenant_004.tcg_products SET japanese_title=%s WHERE code=%s",
            [(title, code) for code, title in CURRENT_TITLE_EDITS.items()],
        )
        cursor.execute(
            """SELECT code,id,division_id,work_id,manufacturer_id,product_category_id
               FROM tenant_004.tcg_products WHERE code=ANY(%s) ORDER BY code""",
            (sorted(CURRENT_TITLE_EDITS),),
        )
        identities = cursor.fetchall()
        assert len(identities) == 11
        cursor.execute(migration(BUNDLE))
        cursor.execute(
            """SELECT code,id,division_id,work_id,manufacturer_id,product_category_id
               FROM tenant_004.tcg_products WHERE code=ANY(%s) ORDER BY code""",
            (sorted(CURRENT_TITLE_EDITS),),
        )
        assert cursor.fetchall() == identities
        cursor.execute(
            "SELECT code,japanese_title FROM tenant_004.tcg_products WHERE code=ANY(%s)",
            (sorted(CURRENT_TITLE_EDITS),),
        )
        assert dict(cursor.fetchall()) == CURRENT_TITLE_EDITS
        cursor.execute("SELECT count(*) FROM tenant_004.tcg_products WHERE code='PM0297'")
        assert cursor.fetchone()[0] == 1
    emit(capsys, "V3-title", edited_titles_accepted=11, identities_preserved=11, bundle_created=1)


def test_v3_structural_mismatch_rolls_back_transaction(pg, capsys):
    connection, _, _ = pg
    work_fixture.seed_bundle_dictionary(connection, "tenant_004")
    tables = (
        "tcg_products",
        "tcg_major_categories",
        "tcg_series",
        "tcg_manufacturers",
        "tcg_product_categories",
        "product_search_keywords",
        "product_exclude_keywords",
    )
    with connection.cursor() as cursor:
        cursor.execute("UPDATE tenant_004.tcg_products SET work_id=NULL WHERE code='PM0276'")
    before = schema_snapshot(connection, "tenant_004", tables)
    with connection.cursor() as cursor:
        with pytest.raises(psycopg2.errors.RaiseException, match="identity mismatch PM0276"):
            cursor.execute(migration(BUNDLE))
        cursor.execute("ROLLBACK")
        assert connection.get_transaction_status() == psycopg2.extensions.TRANSACTION_STATUS_IDLE
    assert schema_snapshot(connection, "tenant_004", tables) == before
    emit(capsys, "V3-rollback", structural_fault="PM0276.work_id=NULL", changed_rows_after_failure=0)


def test_v4_legacy_keyword_and_classification_replay_restores_edits(pg, capsys):
    connection, _, _ = pg
    with connection.cursor() as cursor:
        work_fixture.provision(cursor, "tenant_004")
        add_word_uniques(cursor, "tenant_004")
        seed_product(cursor, "tenant_004", "PM0200", "人工検証PM0200")
        seed_product(cursor, "tenant_004", "PM0263", "30th CELEBRATION", active=True)
        cursor.execute(migration(BATCH1))
        cursor.execute(migration(CARDSET))
        for code, keyword in V4_SEARCH_WORDS.items():
            cursor.execute(
                """DELETE FROM tenant_004.product_search_keywords k
                   USING tenant_004.tcg_products p
                   WHERE k.product_id=p.id AND p.code=%s AND k.keyword=%s""",
                (code, keyword),
            )
            assert cursor.rowcount == 1
        cursor.execute(
            """DELETE FROM tenant_004.product_exclude_keywords k
               USING tenant_004.tcg_products p
               WHERE k.product_id=p.id AND p.code='PM0263' AND k.keyword='カードセット'"""
        )
        assert cursor.rowcount == 1
        cursor.execute(
            """UPDATE tenant_004.tcg_products p SET
                   division_id=d.id,work_id=w.id,manufacturer_id=m.id,product_category_id=c.id
               FROM tenant_004.tcg_major_categories d,tenant_004.tcg_series w,
                    tenant_004.tcg_manufacturers m,tenant_004.tcg_product_categories c
               WHERE p.code='PM0200' AND d.code='DIV02' AND w.code='IP002'
                 AND m.code='MK002' AND c.code='PC_SINGLE'"""
        )
        cursor.execute(
            """SELECT p.code,'search',k.keyword,k.position
               FROM tenant_004.product_search_keywords k JOIN tenant_004.tcg_products p ON p.id=k.product_id
               UNION ALL
               SELECT p.code,'exclude',k.keyword,k.position
               FROM tenant_004.product_exclude_keywords k JOIN tenant_004.tcg_products p ON p.id=k.product_id"""
        )
        edited_words = set(cursor.fetchall())
        cursor.execute(migration(BATCH1))
        cursor.execute(migration(CARDSET))
        cursor.execute(migration(CLASSIFICATION))
        cursor.execute(
            """SELECT p.code,'search',k.keyword,k.position
               FROM tenant_004.product_search_keywords k JOIN tenant_004.tcg_products p ON p.id=k.product_id
               UNION ALL
               SELECT p.code,'exclude',k.keyword,k.position
               FROM tenant_004.product_exclude_keywords k JOIN tenant_004.tcg_products p ON p.id=k.product_id"""
        )
        after_words = set(cursor.fetchall())
        cursor.execute(
            """SELECT d.code,w.code,m.code,c.code FROM tenant_004.tcg_products p
               JOIN tenant_004.tcg_major_categories d ON d.id=p.division_id
               JOIN tenant_004.tcg_series w ON w.id=p.work_id
               JOIN tenant_004.tcg_manufacturers m ON m.id=p.manufacturer_id
               JOIN tenant_004.tcg_product_categories c ON c.id=p.product_category_id
               WHERE p.code='PM0200'"""
        )
        assert cursor.fetchone() == ("DIV01", "IP001", "MK001", "PC_BOX")
    restored = after_words - edited_words
    expected = {(code, "search", keyword, 1) for code, keyword in V4_SEARCH_WORDS.items()}
    expected.add(("PM0263", "exclude", "カードセット", 0))
    assert restored == expected
    assert edited_words < after_words
    emit(capsys, "V4", search_words_restored=9, exclude_words_restored=1, classification_fields_restored=4)


def test_v4_current_bundle_readds_pm0264_cardset_exclusion(pg, capsys):
    connection, _, _ = pg
    work_fixture.seed_bundle_dictionary(connection, "tenant_004")
    with connection.cursor() as cursor:
        cursor.execute(migration(BUNDLE))
        cursor.execute(
            """SELECT id,division_id,work_id,manufacturer_id,product_category_id
               FROM tenant_004.tcg_products WHERE code='PM0264'"""
        )
        identity = cursor.fetchone()
        cursor.execute(
            """DELETE FROM tenant_004.product_exclude_keywords k
               USING tenant_004.tcg_products p
               WHERE k.product_id=p.id AND p.code='PM0264' AND k.keyword='カードセット'"""
        )
        assert cursor.rowcount == 1
        edited = schema_snapshot(
            connection,
            "tenant_004",
            ("tcg_products", "product_search_keywords", "product_exclude_keywords"),
        )
        cursor.execute(migration(BUNDLE))
        cursor.execute(
            """SELECT id,division_id,work_id,manufacturer_id,product_category_id
               FROM tenant_004.tcg_products WHERE code='PM0264'"""
        )
        assert cursor.fetchone() == identity
        cursor.execute(
            """SELECT count(*) FROM tenant_004.product_exclude_keywords k
               JOIN tenant_004.tcg_products p ON p.id=k.product_id
               WHERE p.code='PM0264' AND k.keyword='カードセット'"""
        )
        assert cursor.fetchone()[0] == 1
    replayed = schema_snapshot(
        connection,
        "tenant_004",
        ("tcg_products", "product_search_keywords", "product_exclude_keywords"),
    )
    assert replayed["tcg_products"] == edited["tcg_products"]
    assert replayed["product_search_keywords"] == edited["product_search_keywords"]
    assert len(replayed["product_exclude_keywords"]) == len(edited["product_exclude_keywords"]) + 1
    emit(capsys, "V4-bundle", pm0264_exclude_words_restored=1, product_identity_preserved=True)


def test_v5_explicit_conflict_targets_require_keyword_uniques(pg, capsys):
    _, _, source_url = pg
    with (
        additional_database(source_url, "tcg_migration_without_unique") as (plain, _),
        additional_database(source_url, "tcg_migration_with_unique") as (constrained, _),
    ):
        for connection in (plain, constrained):
            with connection.cursor() as cursor:
                work_fixture.provision(cursor, SCHEMA)
                seed_product(cursor, SCHEMA, "PM0200", "人工検証PM0200")
                seed_product(cursor, SCHEMA, "PM0085", "人工検証PM0085")
        with constrained.cursor() as cursor:
            add_word_uniques(cursor, SCHEMA)
        with plain.cursor() as cursor:
            with pytest.raises(psycopg2.errors.InvalidColumnReference, match="unique or exclusion constraint"):
                cursor.execute(for_schema(BATCH1, SCHEMA))
            plain.rollback()
            cursor.execute(
                sql.SQL("SELECT count(*) FROM {}.tcg_products WHERE code='PM0272'").format(sql.Identifier(SCHEMA))
            )
            assert cursor.fetchone()[0] == 0
            with pytest.raises(psycopg2.errors.InvalidColumnReference, match="unique or exclusion constraint"):
                cursor.execute(for_schema(ABBREVIATIONS, SCHEMA))
            plain.rollback()
        with constrained.cursor() as cursor:
            cursor.execute(for_schema(BATCH1, SCHEMA))
            cursor.execute(for_schema(ABBREVIATIONS, SCHEMA))
            cursor.execute(
                sql.SQL("SELECT count(*) FROM {}.tcg_products WHERE code BETWEEN 'PM0272' AND 'PM0296'").format(
                    sql.Identifier(SCHEMA)
                )
            )
            assert cursor.fetchone()[0] == 25
            cursor.execute(
                sql.SQL(
                    """SELECT 'search',keyword FROM {}.product_search_keywords k
                       JOIN {}.tcg_products p ON p.id=k.product_id WHERE p.code='PM0085'
                       UNION ALL
                       SELECT 'exclude',keyword FROM {}.product_exclude_keywords k
                       JOIN {}.tcg_products p ON p.id=k.product_id WHERE p.code='PM0085'
                       ORDER BY 1,2"""
                ).format(*[sql.Identifier(SCHEMA)] * 4)
            )
            assert cursor.fetchall() == [
                ("exclude", "決戦の刻"),
                ("search", "決戦"),
                ("search", "頂上"),
            ]
    emit(capsys, "V5", databases=2, without_unique_failures=2, with_unique_migrations=2)


V6_TABLES = (
    "tcg_major_categories",
    "tcg_series",
    "tcg_manufacturers",
    "tcg_product_categories",
    "tcg_products",
    "product_search_keywords",
    "product_exclude_keywords",
    "products_logistics",
    "analysis_results",
    "tcg_product_import_jobs",
    "tcg_product_import_rows",
)


def test_v6_artificial_dump_restore_preserves_product_graph_and_history(pg, capsys):
    connection, _, source_url = pg
    with connection.cursor() as cursor:
        cursor.execute(for_schema(HISTORY, SCHEMA))
        product_id = seed_product(cursor, SCHEMA, "PMV001", "人工復元検証商品")
        cursor.execute(
            sql.SQL(
                """INSERT INTO {}.product_search_keywords(product_id,keyword,position)
                   VALUES (%s,'人工検索語B',9),(%s,'人工検索語A',2)"""
            ).format(sql.Identifier(SCHEMA)),
            (product_id, product_id),
        )
        cursor.execute(
            sql.SQL(
                "INSERT INTO {}.product_exclude_keywords(product_id,keyword,position) VALUES (%s,'人工除外語',4)"
            ).format(sql.Identifier(SCHEMA)),
            (product_id,),
        )
        cursor.execute(
            sql.SQL("INSERT INTO {}.products_logistics(product_id) VALUES (%s)").format(sql.Identifier(SCHEMA)),
            (product_id,),
        )
        cursor.execute(
            sql.SQL(
                """INSERT INTO {}.source_messages
                   (id,supplier_channel_id,raw_text,raw_sha256,received_at,is_active)
                   SELECT %s,id,'人工復元検証入力',%s,now(),true FROM {}.supplier_channels LIMIT 1"""
            ).format(sql.Identifier(SCHEMA), sql.Identifier(SCHEMA)),
            ("11111111-1111-4111-8111-111111111111", "1" * 64),
        )
        cursor.execute(
            sql.SQL("INSERT INTO {}.extraction_jobs(id,source_message_id,status) VALUES (%s,%s,'done')").format(
                sql.Identifier(SCHEMA)
            ),
            ("22222222-2222-4222-8222-222222222222", "11111111-1111-4111-8111-111111111111"),
        )
        cursor.execute(
            sql.SQL(
                """INSERT INTO {}.extraction_items
                   (id,extraction_job_id,line_start,line_end,raw_product_name)
                   VALUES (%s,%s,1,1,'人工復元検証商品')"""
            ).format(sql.Identifier(SCHEMA)),
            ("33333333-3333-4333-8333-333333333333", "22222222-2222-4222-8222-222222222222"),
        )
        cursor.execute(
            sql.SQL(
                """INSERT INTO {}.analysis_results
                   (extraction_item_id,product_id,pid_resolved,unit_resolved,needs_review,engine_version)
                   VALUES (%s,%s,true,false,false,'artificial-restore-verification')"""
            ).format(sql.Identifier(SCHEMA)),
            ("33333333-3333-4333-8333-333333333333", product_id),
        )
        cursor.execute(
            sql.SQL(
                """INSERT INTO {}.tcg_product_import_jobs
                   (id,filename,raw_sha256,total_rows,created_rows,executed_by,status,completed_at)
                   VALUES (%s,'artificial.csv',%s,1,1,'migration-verification','ok',now())"""
            ).format(sql.Identifier(SCHEMA)),
            ("44444444-4444-4444-8444-444444444444", "4" * 64),
        )
        cursor.execute(
            sql.SQL(
                """INSERT INTO {}.tcg_product_import_rows
                   (job_id,row_no,japanese_title,mark,result,product_code,messages)
                   VALUES (%s,1,'人工復元検証商品','VERIFY','created','PMV001','[]')"""
            ).format(sql.Identifier(SCHEMA)),
            ("44444444-4444-4444-8444-444444444444",),
        )
    before = schema_snapshot(connection, SCHEMA, V6_TABLES)
    server_major = connection.server_version // 10000
    dump_version = subprocess.run(["pg_dump", "--version"], check=True, capture_output=True, text=True).stdout.strip()
    restore_version = subprocess.run(
        ["pg_restore", "--version"], check=True, capture_output=True, text=True
    ).stdout.strip()
    dump_major = int(re.search(r"PostgreSQL\) (\d+)", dump_version).group(1))
    restore_major = int(re.search(r"PostgreSQL\) (\d+)", restore_version).group(1))
    assert dump_major == restore_major == server_major
    with (
        additional_database(source_url, "tcg_migration_restore") as (restored, restored_url),
        tempfile.TemporaryDirectory(prefix="tcg-migration-restore-") as temp_dir,
    ):
        dump_path = Path(temp_dir) / "artificial.dump"
        env = dict(os.environ)
        if source_url.password:
            env["PGPASSWORD"] = source_url.password
        common = ["--host", source_url.host, "--port", str(source_url.port or 5432), "--username", source_url.username]
        subprocess.run(
            [
                "pg_dump",
                *common,
                "--format=custom",
                f"--schema={SCHEMA}",
                "--file",
                str(dump_path),
                source_url.database,
            ],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
        subprocess.run(
            [
                "pg_restore",
                *common,
                "--exit-on-error",
                "--no-owner",
                "--no-privileges",
                "--dbname",
                restored_url.database,
                str(dump_path),
            ],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
        after = schema_snapshot(restored, SCHEMA, V6_TABLES)
    assert after == before
    digest = hashlib.sha256(json.dumps(before, sort_keys=True).encode()).hexdigest()
    emit(
        capsys,
        "V6",
        compared_tables=len(V6_TABLES),
        differences=0,
        snapshot_sha256=digest,
        server_major=server_major,
        pg_dump=dump_version,
        pg_restore=restore_version,
    )
