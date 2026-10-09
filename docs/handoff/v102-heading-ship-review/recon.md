# recon: 試作版 v102 で「見出しの直下の発送日の行」が2件目以降にも入る件

この文書は何か：Gemini が見出しの直下の発送日の行を、自分の発送日の行を持つ2件目以降の件にも入れても、今の受け取り側は何も言わない、という現状の事実の一覧。
親（仕様書）：[../../specs/line-analysis-tuning/README.md](../../specs/line-analysis-tuning/README.md)
設計：[design.md](./design.md)

調査日：2026-10-09。基準：origin/main e51dceba7（`git rev-parse origin/main`）。調査は Opus（事実）、行番号は Sonnet が実物で再確認した。
社外秘：投稿の原文・仕入元の名前・指示書の本文は、この文書に書かない。試験の例文は作った文。

## 1. 行の役目の決め方
- `backend/app/services/gemini_raw_copy_v101.py:53` 役目の名前（price・ship・condition・stock・name）。
- `backend/app/services/gemini_raw_copy_v101.py:55` `_SHIP_RE`：発送の見分けは固定の正規表現（マスタ由来ではない）。
- `backend/app/services/gemini_raw_copy_v101.py:367-379` `line_role`：price → 在庫語始まり → ship → condition → stock → name の順。価格の行は ship にならない。
- `backend/app/services/gemini_raw_copy_v101.py:382-387` `assign_roles`：件ごとに lines の各行の役目を返す。

## 2. 件の出力に役目が残る
- `backend/app/services/gemini_raw_copy_v101.py:854` 件の `roles` は F5 後の name_roles（`:1140` `_apply_f5`）。ship は F3・F5 で変わらない。
- 同じ見出しを結ぶ欄は件に無い。よって「lines の最小の行番号が同じ件」を同じ見出しとみなす。

## 3. 要確認の理由の足し方
- `backend/app/services/gemini_raw_copy_v101.py:1077-1086` `_item_reasons`（件ごと）。定数 `:1047-1048`。
- `backend/app/services/gemini_raw_copy_v101.py:1123` `_extract_v102`：`review_reasons=True` のときだけ件の `review` に足す（`:1165-1169` 付近）。
- 件の要確認の形と kind の表：`docs/handoff/v102-no-silent-drop/design.md:20-30`（§3-1）。

## 4. 衝突の確認
- `backend/app/services/gemini_raw_copy_v101.py` を触る開いた PR：PR 作成前に `gh pr list --state open` で再確認する（結果は PR 本文）。

## 5. ADR 検索
- `docs/adr/ADR-154-tcg-parity02-gas-python-migration.md:70`：配信は needs_review=false の行に限定する（引き渡しの向き先）。
- `docs/adr/ADR-014-inventory-management.md:29`：解析ロジックの秘匿（原文を載せない）。
- `docs/adr/ADR-027-ui-internationalization.md`：理由は文章でなく種類（kind）で持つ。
- 見出しの発送日の割り当てを直接扱う ADR：該当なし（docs/adr/FEATURE-INDEX.md と本文を、発送・見出し・要確認で検索）。
