"""public.tcg_status_master の effect・match_type が取りうる値（1か所の定数）。

読む側の v102_status_context と、書く側の検証 schemas/central_masters.py が、ここから読む。
OUTPUT・EXCLUDE・REGEX・LITERAL・DEFAULT は従来の値。残りは予約の手がかり（便PO）で、resolve_status_v2 は読まない。
"""
from __future__ import annotations

EFFECT_OUTPUT = "OUTPUT"
EFFECT_EXCLUDE = "EXCLUDE"
EFFECT_HEADING = "HEADING"  # 件の上にある見出しの行から決める
EFFECT_DATE_AHEAD = "DATE_AHEAD"  # 件の行の「先の日付」から決める
EFFECT_RELEASE_AHEAD = "RELEASE_AHEAD"  # 商品マスタの発売日が投稿日より先なら決める

MATCH_REGEX = "REGEX"
MATCH_LITERAL = "LITERAL"
MATCH_DEFAULT = "DEFAULT"
MATCH_RELEASE = "RELEASE"  # 文字の照合ではなく、商品の発売日で決める行

CONTEXT_EFFECTS = (EFFECT_RELEASE_AHEAD, EFFECT_DATE_AHEAD, EFFECT_HEADING)  # 適用順（v102_status_context が使う）

VALID_EFFECTS = frozenset({EFFECT_OUTPUT, EFFECT_EXCLUDE, *CONTEXT_EFFECTS})
VALID_MATCH_TYPES = frozenset({MATCH_REGEX, MATCH_LITERAL, MATCH_DEFAULT, MATCH_RELEASE})
