"""mig04_import_tables

Revision ID: 20260830000000
Revises: 51c0207e4db4
Create Date: 2026-08-30 00:00:00.000000

MIG-04 Phase 2: LINE エクスポートアップロード取り込みに必要なテーブル・列を追加。

変更内容:
  1. import_jobs テーブル新規作成（アップロード履歴・冪等化キー）
  2. extraction_jobs.prompt_version VARCHAR(50) 追加（nullable）
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "20260830000000"
down_revision: Union[str, Sequence[str], None] = "51c0207e4db4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. import_jobs テーブル作成
    op.create_table(
        "import_jobs",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("raw_sha256", sa.String(length=64), nullable=False),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("provider_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("unresolved_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("uploaded_by", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default=sa.text("'ok'")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("raw_sha256", name="uq_import_jobs_raw_sha256"),
    )

    # 2. extraction_jobs.prompt_version 追加
    op.add_column(
        "extraction_jobs",
        sa.Column("prompt_version", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # 逆順で削除
    op.drop_column("extraction_jobs", "prompt_version")
    op.drop_table("import_jobs")
