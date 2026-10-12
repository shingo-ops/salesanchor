"""DB構造ビューア API — information_schema から動的にテーブル・カラム・FK情報を取得"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db

router = APIRouter()


@router.get(
    "/super-admin/db-schema/tables",
    dependencies=[Depends(require_super_admin)],
)
async def list_tables(db: AsyncSession = Depends(get_db)):
    """全テーブル一覧（public + tenant_001〜006）を返す"""
    result = await db.execute(
        text("""
            SELECT
                t.table_schema,
                t.table_name,
                obj_description(
                    (quote_ident(t.table_schema) || '.' || quote_ident(t.table_name))::regclass
                ) AS table_comment
            FROM information_schema.tables t
            WHERE t.table_type = 'BASE TABLE'
              AND t.table_schema IN ('public', 'tenant_001', 'tenant_002', 'tenant_003', 'tenant_004', 'tenant_005', 'tenant_006')
              AND t.table_name NOT LIKE 'pg_%'
            ORDER BY t.table_schema, t.table_name
        """)
    )
    rows = result.mappings().all()
    return [
        {
            "schema": row["table_schema"],
            "table": row["table_name"],
            "comment": row["table_comment"],
        }
        for row in rows
    ]


@router.get(
    "/super-admin/db-schema/tables/{schema_name}/{table_name}/columns",
    dependencies=[Depends(require_super_admin)],
)
async def list_columns(
    schema_name: str,
    table_name: str,
    db: AsyncSession = Depends(get_db),
):
    """指定テーブルのカラム一覧を返す"""
    # カラム情報
    col_result = await db.execute(
        text("""
            SELECT
                c.column_name,
                c.data_type,
                c.udt_name,
                c.character_maximum_length,
                c.numeric_precision,
                c.is_nullable,
                c.column_default,
                col_description(
                    (quote_ident(c.table_schema) || '.' || quote_ident(c.table_name))::regclass,
                    c.ordinal_position
                ) AS column_comment
            FROM information_schema.columns c
            WHERE c.table_schema = :schema
              AND c.table_name = :table
            ORDER BY c.ordinal_position
        """),
        {"schema": schema_name, "table": table_name},
    )
    columns = col_result.mappings().all()

    # FK情報
    fk_result = await db.execute(
        text("""
            SELECT
                kcu.column_name,
                ccu.table_schema AS foreign_schema,
                ccu.table_name AS foreign_table,
                ccu.column_name AS foreign_column
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
                ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema = :schema
              AND tc.table_name = :table
        """),
        {"schema": schema_name, "table": table_name},
    )
    fk_rows = fk_result.mappings().all()
    fk_map = {
        row["column_name"]: {
            "schema": row["foreign_schema"],
            "table": row["foreign_table"],
            "column": row["foreign_column"],
        }
        for row in fk_rows
    }

    # PK情報
    pk_result = await db.execute(
        text("""
            SELECT kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'PRIMARY KEY'
              AND tc.table_schema = :schema
              AND tc.table_name = :table
        """),
        {"schema": schema_name, "table": table_name},
    )
    pk_columns = {row["column_name"] for row in pk_result.mappings().all()}

    return {
        "schema": schema_name,
        "table": table_name,
        "columns": [
            {
                "name": col["column_name"],
                "type": col["data_type"],
                "udt_name": col["udt_name"],
                "max_length": col["character_maximum_length"],
                "precision": col["numeric_precision"],
                "nullable": col["is_nullable"] == "YES",
                "default": col["column_default"],
                "comment": col["column_comment"],
                "is_pk": col["column_name"] in pk_columns,
                "fk": fk_map.get(col["column_name"]),
            }
            for col in columns
        ],
    }


@router.get(
    "/super-admin/db-schema/tables/{schema_name}/{table_name}/references",
    dependencies=[Depends(require_super_admin)],
)
async def list_references(
    schema_name: str,
    table_name: str,
    db: AsyncSession = Depends(get_db),
):
    """指定テーブルを参照している他テーブル（逆参照）を返す"""
    result = await db.execute(
        text("""
            SELECT
                tc.table_schema AS source_schema,
                tc.table_name AS source_table,
                kcu.column_name AS source_column,
                ccu.column_name AS target_column
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
                ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND ccu.table_schema = :schema
              AND ccu.table_name = :table
        """),
        {"schema": schema_name, "table": table_name},
    )
    rows = result.mappings().all()
    return [
        {
            "source_schema": row["source_schema"],
            "source_table": row["source_table"],
            "source_column": row["source_column"],
            "target_column": row["target_column"],
        }
        for row in rows
    ]
