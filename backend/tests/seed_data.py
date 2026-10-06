"""試験が自分で用意するマスタ seed の供給元（ADR-1007 段2）。

migration が値を書かなくなっても試験が壊れないように、データの正本を migration ではなく
次の場所に置く。DB は使わない純粋な関数だけを置く（PG へ流す側は rls_bootstrap.py）。

- 国: frontend/src/constants/countries.ts
- type_master: 下の _load_tcg_type_seed_rows（SQLite の試験 DB と PG の試験で共用）
- 集計ルール: app.services.inventory_aggregation.DEFAULT_AGGREGATION_RULES（アプリのコード）

SQL はすべて ON CONFLICT で冪等。実行は conn.exec_driver_sql（SQLAlchemy の :name 解析を避ける）。
"""

from __future__ import annotations

import re
from pathlib import Path


def _load_country_seed_rows() -> list[tuple[str, str, str]]:
    """frontend/src/constants/countries.ts を SSOT として国 seed を読む。"""
    src = (Path(__file__).resolve().parents[2] / "frontend" / "src" / "constants" / "countries.ts").read_text("utf-8")
    pattern = re.compile(r'\{ name: "([^"]+)", code: "([A-Z]{2})", dial: "([^"]+)" \}')
    return [(m.group(2), m.group(1), m.group(3)) for m in pattern.finditer(src)]


def _load_tcg_type_seed_rows() -> list[tuple[str, str, str | None]]:
    """type_master の seed rows を canonical code に合わせる。"""
    return [
        ("pokemon_booster_box", "ポケモンカード", "Pokémon Card"),
        ("one_piece", "ワンピース", "One Piece TCG"),
        ("dragon_ball", "ドラゴンボール", "Dragon Ball TCG"),
        ("union_arena", "ユニオンアリーナ", "Union Arena"),
        ("yugioh", "遊戯王", "Yu-Gi-Oh!"),
        ("other", "その他", "Other"),
        ("gundam", "ガンダムカードゲーム", "Gundam Card Game"),
        ("weiss_schwarz", "ヴァイスシュヴァルツ", "Weiß Schwarz"),
        ("digimon", "デジモンカードゲーム", "Digimon Card Game"),
        ("hololive", "ホロライブ", "hololive Official Card Game"),
        ("lorcana", "ディズニー ロルカナ", "Disney Lorcana"),
        ("xross_stars", "クロススタァ", "Xross Stars"),
    ]


def _lit(value: str | None) -> str:
    """SQL 文字列リテラル（' を '' に置換）。None は NULL。"""
    return "NULL" if value is None else "'" + value.replace("'", "''") + "'"


def country_seed_sql() -> str:
    """public.countries へ 190 行を入れる SQL（既にある行は触らない）。"""
    values = ",\n".join(
        f"({_lit(code)}, {_lit(name)}, {_lit(dial)}, TRUE)" for code, name, dial in _load_country_seed_rows()
    )
    return (
        "INSERT INTO public.countries (code, name, dial_code, is_active) VALUES\n"
        + values
        + "\nON CONFLICT (code) DO NOTHING"
    )


def type_master_seed_sql() -> str:
    """public.type_master へ 12 種別を入れる SQL。sort_order は SQLite の試験 DB と同じ 100。"""
    values = ",\n".join(
        f"({_lit(code)}, {_lit(name_ja)}, {_lit(name_en)}, 100, TRUE)"
        for code, name_ja, name_en in _load_tcg_type_seed_rows()
    )
    return (
        "INSERT INTO public.type_master (code, name_ja, name_en, sort_order, is_active) VALUES\n"
        + values
        + "\nON CONFLICT (code) DO NOTHING"
    )


def aggregation_rules_seed_sql() -> str:
    """public.inventory_aggregation_rules へアプリの既定 4 行を入れる SQL。"""
    from app.services.inventory_aggregation import DEFAULT_AGGREGATION_RULES

    values = ",\n".join(
        f"({_lit(rule.condition)}, {int(rule.price_tolerance)}, {int(rule.stock_tolerance)})"
        for rule in DEFAULT_AGGREGATION_RULES
    )
    return (
        "INSERT INTO public.inventory_aggregation_rules (condition, price_tolerance, stock_tolerance) VALUES\n"
        + values
        + "\nON CONFLICT (condition) DO NOTHING"
    )
