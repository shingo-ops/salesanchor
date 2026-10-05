# recon: MEGAドリームex の mark 修正（PM0198、id 440559、M3 → M2a）

実測時の origin/main SHA: 225c0c0ad292a13173a7b1bef5de8f484215faae
事実のみ。評価・提案は書かない。商品コードと商品名のみ（仕入元名・投稿本文は含まない）。

## §1 既存 ADR の検索
実行: `git grep -il -e "ADR-155" -- docs/adr`、`git grep -il -e "product master" -- docs/adr`、`git grep -il -e "商品マスタ" -- docs/adr`、`git grep -n -i -e "ADR-155" -e "product master" -e "商品マスタ" -- docs/adr/FEATURE-INDEX.md`（デッキビルド修正の recon と同じ実行結果。同じ origin/main）

- "ADR-155" を含む: docs/adr/ADR-155-product-master-ssot-csv-app.md、docs/adr/ADR-156-product-classification-tree-and-master-separation.md、docs/adr/README.md
- "product master" を含む: 該当なし（0 件）
- "商品マスタ" を含む: docs/adr/ADR-014-inventory-management.md、docs/adr/ADR-015.md、docs/adr/ADR-093-inventory-table-product-master-redesign.md、docs/adr/ADR-099-sa-inventory-model.md、docs/adr/ADR-100-sa-ingestion-analysis-pipeline.md、docs/adr/ADR-1001-deprecate-tcg-products-unify-to-public.md、docs/adr/ADR-1002-unify-product-id-and-fix-migration-compat.md、docs/adr/ADR-110-sa-translation-subsystem.md、docs/adr/ADR-129-audit-log-coverage-medium.md、docs/adr/ADR-145-public-products-force-rls.md、docs/adr/ADR-155-product-master-ssot-csv-app.md、docs/adr/ADR-156-product-classification-tree-and-master-separation.md、docs/adr/ADR-157-buyback-price-logger.md、docs/adr/ADR-SA-17-translation-bidirectional-glossary-two-layer.md、docs/adr/FEATURE-INDEX.md、docs/adr/README.md
- docs/adr/FEATURE-INDEX.md:18: 「在庫 / inventory / 商品マスタ / 仕入元 / オファー | ADR-099 ／ ADR-093 ／ ADR-014」（ADR-155 の行はない）
- docs/adr/ADR-155-product-master-ssot-csv-app.md:21: 「型番（mark）の誤登録も発生した（PM0198 MEGAドリームex: M3 → 正しくは M2a）」
- docs/adr/ADR-155-product-master-ssot-csv-app.md:25-26: 正規の更新手段は CSV 取り込みとアプリ画面。マイグレーションでの値の操作（INSERT / UPDATE / DELETE）は禁止。
- docs/adr/ADR-155-product-master-ssot-csv-app.md:27-31: 保護対象は public.products、tcg_products、product_search_keywords、product_exclude_keywords
- docs/adr/ADR-145-public-products-force-rls.md:55: `ALTER TABLE public.products FORCE ROW LEVEL SECURITY;`（アプリ保存は app.is_operator を設定する。§3 参照）
- 先行する同種の変更: docs/handoff/deckbuild-master-fix/（PR #3966。同じ手順・同じ SQL の構造）

## §2 照合の経路（v7 判定。backend/app/services/extraction_judgement_svc.py）
- backend/app/services/extraction_judgement_svc.py:22-28 `fold_for_match`（NFKC → 小文字 → カタカナをひらがなへ）
- backend/app/services/extraction_judgement_svc.py:31-44 `normalize_for_match`: 空白（:38-39）と記号 P*/S*（:40-42）を除去
- backend/app/services/extraction_judgement_svc.py:52-54 `_normalize_value`: 商品マスタの値（品番・記号・検索ワード・除外ワード）の正規化
- backend/app/services/extraction_judgement_svc.py:57-59 `_needs_boundary`: `len(normalized) <= 2 or normalized.isdigit()` のときだけ語境界を要求（"m3"（2 文字）は要求、"m2a"（3 文字）は要求しない）
- backend/app/services/extraction_judgement_svc.py:131-138 `_value_hits`: 正規化した値が照合文字列に含まれるか（部分文字列）
- backend/app/services/extraction_judgement_svc.py:140-148 `_code_candidate_basis`: product_code または mark が含まれれば "RAWCODE"（候補になる）
- backend/app/services/extraction_judgement_svc.py:183-212 `match_product` の商品ループ: コードまたはキーワードで候補入り（:194-204）、除外ワードで落とす（:206-209）。候補が 2 件以上なら ambiguous（:213 以降）

## §3 アプリ保存の経路（SQL が写している正規の更新手段）
- backend/app/routers/tcg_product_import.py:294-307 `PUT /tcg/products/detail/{product_id}`（`require_super_admin`）
- backend/app/services/tcg_product_detail_svc.py:111 `update_product_detail`
- backend/app/services/tcg_product_detail_svc.py:116-118 `FOR UPDATE`、:119-121 revision 不一致なら 409
- backend/app/services/tcg_product_detail_svc.py:170 `SET LOCAL app.is_operator = 'true'`
- backend/app/services/tcg_product_detail_svc.py:171-179 `UPDATE public.products SET name, name_en, mark, ...`
- backend/app/services/tcg_product_detail_svc.py:193-199 audit_log 挿入（:194 `_audit_pid = str(uuid4())` を record_id に使う）
- migrations/20260921_110000_pipeline_tables_public.sql:404-413 `public.audit_log`（record_id UUID、changed_by VARCHAR(100)、old_values/new_values TEXT）
- migrations/062_create_inventory_movements_and_budget.sql:71-80 `set_updated_at_products` とトリガ（public.products の UPDATE で updated_at を更新）

## §4 作業参照のダイジェスト
- backend/app/services/tcg_work_reference.py:30-31 `reference_digest`
- backend/app/services/tcg_work_reference.py:86-94 参照に全有効商品の name・name_en・mark・検索/除外キーワードが入る
- backend/app/services/tcg_analyzer_svc.py:1256-1259 保存済み v5 以降ジョブの再解析で、ダイジェストが保存値と違えば `ValueError("Work reference changed; re-extraction required")`
- backend/app/tasks/tcg_extraction.py:423-428 抽出中に参照が変われば `REFERENCE_CHANGED`

## §5 v6 の型番ゲート
- backend/app/services/tcg_analyzer_svc.py:1219-1221 有効な全商品の mark → id を読む
- backend/app/services/tcg_analyzer_svc.py:1223-1224 `rawcode_to_id` を mark → id で作り、product_code → id で上書き（product_code 優先）
- backend/app/services/tcg_analyzer_svc.py:1431 `rawcode_to_id.get(_rawcode)`（Gemini v6 の raw_product_code の完全一致）
- 変更前の対応: "M2a" は対応なし（code・mark とも M2a の有効商品なし）。"M3" は id 12（product_code M3 が優先）。
- 変更後の対応: "M2a" は id 440559。"M3" は id 12 のまま。

## §6 変更前の本番値（2026-10-05、読み取り）
| id | code | mark | name | name_en | release_date | 分類 | search_keywords（位置順） | exclude_keywords（位置順） | updated_at |
|---|---|---|---|---|---|---|---|---|---|
| 440559 | PM0198 | M3 | MEGAドリームex | MEGA Dream ex | 2025-11-28 | ポケモンカード / トレーディングカードゲーム / ボックス / ブースターパック（商品区分 Box、メーカー The Pokemon Company） | MEGAドリームex / MEGA Dream / メガドリーム | AR / PSA / PSA10 / PSA9 / SAR / SR / パラレル / マスターボールミラー | 2026-10-03T17:49:56Z |
| 12 | M3 | M3 | ムニキスゼロ | Nihil Zero | 2026-01-23 | ポケモンカード / トレーディングカードゲーム / ボックス / ブースターパック | ムニキスゼロ / ムニキス | （なし） | 2026-10-02T11:34:44Z |

v6 の直近の利用（読み取り）: analysis_results の product_id が 440559 のもの 295 行、12 のもの 262 行。extraction_items の resolved_product_code が 440559 のもの 157 行、12 のもの 129 行。他テーブルの参照（440559 / 12）: extraction_shadow_results 49 / 45、analysis_run_snapshots 77 / 47、buyback_shop_products 3 / 3、inventory 0 / 6。

## §7 T2 の証拠（v9 T2、3,066 ブロック、ローカルで実際の match_product を再実行）
- 基準（現在の本番マスタ）: matched 2,392 / ambiguous 357 / unmatched 301、自動確定 343。
- 変更後のマスタ（id 440559 の mark のみ M2a）: ambiguous → matched 16、その他の遷移なし、matched → 非 matched / 別商品 0。matched 2,392 → 2,408、自動確定 343 のまま。
- 変化した 16 ブロックはすべて M3 と PM0198 の曖昧で、原文は ムニキスゼロ の記載。変更後は id 12 に RAWCODE で確定。
- 合成プローブ: "M2a" / "[M2a]" / "M2a BOX" は PM0198、"M3" / "M3 BOX" / "ムニキスゼロ [M3]" は id 12。"M2 a" は M2 と PM0198 の曖昧（空白が除かれ 3 文字の値に語境界が要らないため）、"M2ab" は PM0198。

## §8 公式の根拠
- https://www.pokemon-card.com/ex/m2a/index.html: 「ハイクラスパック「MEGAドリームex」」 / 「11月28日（金）発売！」
- https://www.pokemon-card.com/card-search/details.php/card/48585: Set Code "M2a"、「ハイクラスパック 「MEGAドリームex」」、"063 / 193"
- https://www.pokemon-card.com/ex/m3/: 「ムニキスゼロ」 / 「発売日：2026年1月23日（金）」。ページ本文中の文字としての "M3": 未確認（URL とカード画像名に現れる）。
