# recon: 試作版 v102 で「黙って消える」件と印

この文書は何か：試作版（v102）の結果から、件や印が人に知らされないまま消える所の、現状の事実の一覧。
親（仕様書）：[../../specs/line-analysis-tuning/README.md](../../specs/line-analysis-tuning/README.md)
設計：[design.md](./design.md)

調査日：2026-10-08。基準：origin/main 8f27d5449。調査は Sonnet、Opus が要の箇所を再確認した。
社外秘：投稿の原文・仕入元の名前・指示書の本文は、この文書に書かない。実測の生データは手元（CC報告ファイル-keep の silent-drop-recon-20261008）にある。

## 1. 試作版は本番から呼ばれていない
- 呼び出し元は手動の道具だけ：`backend/app/tools/prompt_ab.py:61-69`・`:209`・`:250`・`:252-253`・`:265`・`:267`、`backend/app/tools/prompt_ab_recompute.py:78`。
- `backend/app` の tasks・routers と `scripts/` からの import は 0 件。

## 2. 件を落とす所（`backend/app/services/gemini_raw_copy_v101.py`）
| # | 箇所 | 条件 | 落とした件の行き先 |
|---|---|---|---|
| D1 | `:163-166` | 形の検査 `_shape_error`（`:89-104`）に違反 | `errors` だけ |
| D2 | `:169-171` | 価格の文字を含む行が無い（`_priced_line` `:117-122`） | `errors` だけ |
| D3 | `:172-174` | 価格の行がほかの件と同じ | `errors` だけ |
| D4 | `:155-157` | JSON が読めない・items が無い | `errors` だけ（全件） |
| D5 | `backend/app/tools/prompt_ab.py:271-272` | 取り出しの例外 | `v102_items_error` |
- `backend/app/tools/prompt_ab.py:265` は `parse_v101_response` の `errors` を `_errors` として捨てる。`v102_items`・`v102_flags` には載らない。
- `prompt_ab_recompute.py` の出力には `errors` 欄が無い（`:78` が `_v102_row_fields` の結果だけを書く）。
- D2 の不具合：`_priced_line`（`:117-122`）は全角「／」だけで分割する。半角「/」でつないだ2つの価格は行を見つけられず、件が落ちる（同じ処理の再現で確認：全角は見つかり、半角は None）。

## 3. 印を作るが要確認に入らない所
- `v102_flags` の `possible_missing_item`（`:760-770`・`:966`）、`quantity_no_number`（`:962`・`:967`）、`possible_footer_line`（`:944`・`:967`）。書くのは `prompt_ab.py:270` と `prompt_ab_recompute.py` だけで、読む処理は無い。
- 件が0の投稿では印も出ない（`:939-940`）。
- 単位が決まらないと `unit='none'`（`:744`）。単位の要確認の種類はコードに無い。
- 商品が照合できても分類が無いと `product_category='不明'`（`backend/app/services/gemini_raw_copy_v102_product_first.py:266-268`）。要確認なし。

## 4. 実測（手元の4回分：125投稿、指示書 f_c 2回・e 2回）
| 種類 | f_c 1回目 | f_c 2回目 | e 1回目 | e 2回目 |
|---|---|---|---|---|
| 件が消えた（D2） | 1 | 0 | 0 | 1 |
| possible_missing_item | 1 | 0 | 0 | 0 |
| quantity_no_number | 11 | 4 | 5 | 5 |
| possible_footer_line | 9 | 10 | 10 | 10 |
| 単位 none で要確認なし | 37 | 35 | 854 | 855 |
| 照合済みで分類「不明」 | 55 | 63 | 欄なし | 欄なし |
- 消えた2件：1件は Gemini の写し違い（価格の数字が行に無い）、1件は D2 の半角「/」の不具合。

## 5. 衝突の確認
- 開いた PR #4038 が `gemini_raw_copy_v102_product_first.py` を触っている。本件はこのファイルを変えない。
- `gemini_raw_copy_v101.py`・`prompt_ab.py`・`prompt_ab_recompute.py`・その試験を触る開いた PR は、取得した50件の中に無い（PR 作成前に全件で再確認する）。

## 6. 既存の要確認の正本（本番。設計の向き先）
- `analysis_results.needs_review`・`review_reasons`（`migrations/20260831_110000_create_tcg_analysis_tables_t004.sql:314-316`）。配信は `needs_review` が偽の件だけ（`backend/app/services/tcg_distribution_svc.py:262`・`:334`）。
- 試作版の結果は、まだこの表に書かれない（`backend/app/tools/prompt_ab.py:14-15`）。

## 7. ADR 検索
- `docs/adr/ADR-154-tcg-parity02-gas-python-migration.md:70`：配信は needs_review=false の行に限定する。
- `docs/adr/ADR-014-inventory-management.md:29`：解析ロジックの秘匿。
- 試作版の要確認を直接扱う ADR：該当なし（`docs/adr/FEATURE-INDEX.md` と本文を、要確認・review・試作・v102 で検索）。
