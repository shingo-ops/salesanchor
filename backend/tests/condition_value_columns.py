"""試験 DB の public.conditions を本番の形（value_group / value_rank 列あり）に揃える helper。

本番は migrations/20261017_120000_line_conditions_value_rank.sql で public.line_conditions に列を足す
（public.conditions はその view）。試験 DB には line_conditions が無く、public.conditions は
20260919_020000_master_ssot_public_tables.sql の TABLE なので、同じ型・制約で列を足し（tcg_analyzer_svc.py の状態マスタ読み込みは value_rank 列があると match_type / effect も読むので、
本番にある match_type / effect［20260925_010000_conditions_add_match_type.sql と同じ型・既定値］も一緒に足す）、
本番と同じ 11 状態の値（ADR-1023 §4）を canonical で UPDATE する（行は新たに作らない）。
result_order_sql（状態マスタの value_group / value_rank を引く）を通る実 PG 試験の fixture から呼ぶ。
"""
from __future__ import annotations

# 本番の値（ADR-1023）。canonical -> (value_group, value_rank)
CONDITION_VALUES: dict[str, tuple[str, int]] = {
    "Case": ("case", 1), "Damaged case": ("case", 2), "Opened case": ("case", 3),
    "Sealed box": ("box", 1), "Damaged sealed box": ("box", 2), "No shrink box": ("box", 3),
    "Opened box": ("box", 4), "Searched box": ("box", 5),
    "Unsearched pack": ("pack", 1), "Searched pack": ("pack", 2), "AR confirmed pack": ("pack", 3),
}

_VALUES_SQL = ", ".join(f"('{c}','{g}',{r})" for c, (g, r) in CONDITION_VALUES.items())

# 1 文ずつ実行できる形（asyncpg の exec_driver_sql は複数文を受けないため）
CONDITION_VALUE_STATEMENTS: tuple[str, ...] = (
    "ALTER TABLE public.conditions "
    "ADD COLUMN IF NOT EXISTS match_type TEXT NOT NULL DEFAULT 'KEYWORD', "
    "ADD COLUMN IF NOT EXISTS effect TEXT NOT NULL DEFAULT 'OUTPUT', "
    "ADD COLUMN IF NOT EXISTS value_group TEXT "
    "CONSTRAINT conditions_value_group_check CHECK (value_group IS NULL OR value_group IN ('box','case','pack')), "
    "ADD COLUMN IF NOT EXISTS value_rank INTEGER "
    "CONSTRAINT conditions_value_rank_check CHECK (value_rank IS NULL OR value_rank >= 1)",
    "UPDATE public.conditions c SET value_group = v.g, value_rank = v.r "
    f"FROM (VALUES {_VALUES_SQL}) AS v(canonical, g, r) WHERE c.canonical = v.canonical",
)


def apply_condition_value_columns(cursor) -> None:
    """psycopg2 の cursor 用。20260919 の読み込み直後に呼ぶ。"""
    for statement in CONDITION_VALUE_STATEMENTS:
        cursor.execute(statement)


def seed_condition_value_rows(cursor) -> None:
    """test_tcg_result_order 用。本番と同じ 11 状態の行を（無ければ作って）値入りにする。

    fixture は状態の行を後から INSERT するため、fixture 時点の UPDATE では当たらない行がある。
    code は試験専用の CNV01 形式で、既存の canonical には触れず値だけを入れる。
    """
    for number, canonical in enumerate(CONDITION_VALUES, start=1):
        cursor.execute(
            "INSERT INTO public.conditions (code, canonical, is_active) "
            "SELECT %s, %s, true WHERE NOT EXISTS (SELECT 1 FROM public.conditions WHERE canonical = %s)",
            (f"CNV{number:02d}", canonical, canonical),
        )
    cursor.execute(CONDITION_VALUE_STATEMENTS[1])
