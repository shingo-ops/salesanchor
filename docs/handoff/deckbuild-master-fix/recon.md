# recon: デッキビルド系商品マスタの修正（products 58, 60, 74, 75, 103, 105）

実測時の origin/main SHA: 225c0c0ad292a13173a7b1bef5de8f484215faae
事実のみ。評価・提案は書かない。商品コードと商品名のみ（仕入元名・投稿本文は含まない）。

## §1 既存 ADR の検索
実行: `git grep -il -e "ADR-155" -- docs/adr`、`git grep -il -e "product master" -- docs/adr`、`git grep -il -e "商品マスタ" -- docs/adr`、`git grep -n -i -e "ADR-155" -e "product master" -e "商品マスタ" -- docs/adr/FEATURE-INDEX.md`

- "ADR-155" を含む: docs/adr/ADR-155-product-master-ssot-csv-app.md、docs/adr/ADR-156-product-classification-tree-and-master-separation.md、docs/adr/README.md
- "product master" を含む: 該当なし（0 件）
- "商品マスタ" を含む: docs/adr/ADR-014-inventory-management.md、docs/adr/ADR-015.md、docs/adr/ADR-093-inventory-table-product-master-redesign.md、docs/adr/ADR-099-sa-inventory-model.md、docs/adr/ADR-100-sa-ingestion-analysis-pipeline.md、docs/adr/ADR-1001-deprecate-tcg-products-unify-to-public.md、docs/adr/ADR-1002-unify-product-id-and-fix-migration-compat.md、docs/adr/ADR-110-sa-translation-subsystem.md、docs/adr/ADR-129-audit-log-coverage-medium.md、docs/adr/ADR-145-public-products-force-rls.md、docs/adr/ADR-155-product-master-ssot-csv-app.md、docs/adr/ADR-156-product-classification-tree-and-master-separation.md、docs/adr/ADR-157-buyback-price-logger.md、docs/adr/ADR-SA-17-translation-bidirectional-glossary-two-layer.md、docs/adr/FEATURE-INDEX.md、docs/adr/README.md
- docs/adr/FEATURE-INDEX.md:18: 「在庫 / inventory / 商品マスタ / 仕入元 / オファー | ADR-099 ／ ADR-093 ／ ADR-014」（ADR-155 の行はない）
- docs/adr/ADR-155-product-master-ssot-csv-app.md:25: 「商品マスタデータの正規の更新手段は **CSV 取り込み**と**アプリ画面**の 2 経路のみとする。」
- docs/adr/ADR-155-product-master-ssot-csv-app.md:26: 「マイグレーションは商品マスタ関連テーブルの**構造変更**…にのみ使用する。値の操作（INSERT / UPDATE / DELETE）は禁止する。」
- docs/adr/ADR-155-product-master-ssot-csv-app.md:27-31: 保護対象は public.products、tcg_products、product_search_keywords、product_exclude_keywords
- docs/adr/ADR-145-public-products-force-rls.md:55: `ALTER TABLE public.products FORCE ROW LEVEL SECURITY;`（app.is_operator の設定はアプリ保存でも行う。§3 参照）
- docs/adr/ADR-129-audit-log-coverage-medium.md:50: 商品マスタ CRUD は `require_super_admin` で入口が絞られている旨の記述
- PO の決定（チーム長経由）: ADR-155 の例外として直接 SQL での変更を 2026-10-04 に決定（docs/handoff/deckbuild-master-fix/README.md に引用）

## §2 照合の経路（v7 判定。backend/app/services/extraction_judgement_svc.py）
- backend/app/services/extraction_judgement_svc.py:22-28 `fold_for_match`: NFKC → 小文字 → カタカナをひらがなへ（:24 `unicodedata.normalize("NFKC", text or "").lower()`、:25-27 コードポイントのずらし）
- backend/app/services/extraction_judgement_svc.py:31-44 `normalize_for_match`: 空白（:38-39 `if ch.isspace(): continue`）と記号 P*/S*（:40-42）を除去
- backend/app/services/extraction_judgement_svc.py:52-54 `_normalize_value`: 商品マスタの値（品番・記号・検索ワード・除外ワード）の正規化
- backend/app/services/extraction_judgement_svc.py:57-59 `_needs_boundary`: `len(normalized) <= 2 or normalized.isdigit()`（2 文字以下または数字だけの値のみ語境界を要求。3 文字の "sv7" は要求しない）
- backend/app/services/extraction_judgement_svc.py:62-67 `has_word_boundary`
- backend/app/services/extraction_judgement_svc.py:131-138 `_value_hits`: 正規化した値が照合文字列に含まれるか（部分文字列）
- backend/app/services/extraction_judgement_svc.py:140-148 `_code_candidate_basis`: product_code または mark が含まれれば "RAWCODE"（候補になる）
- backend/app/services/extraction_judgement_svc.py:152-163 `_keyword_matches`: キーワードを空白で分割（:159）し、全トークンが含まれるとき一致（:161 `all(...)`）。順序は問わない
- backend/app/services/extraction_judgement_svc.py:166-173 `_excluded_keywords`: 除外キーワードは分割せず、正規化した文字列全体が含まれれば除外（:170-172）
- backend/app/services/extraction_judgement_svc.py:177-180 `_is_candidate`
- backend/app/services/extraction_judgement_svc.py:183-212 `match_product` の商品ループ: コードまたはキーワードで候補入り（:194-204）、除外ワードに当たれば候補から落とす（:206-209）、残りを候補にする（:211）。候補が 2 件以上なら ambiguous（:213 以降）

## §3 アプリ保存の経路（正規の更新手段）
- frontend/src/features/tcg-product-import/TcgProductDetailDrawer.tsx:80 詳細取得、:132 保存（`api.put`）
- backend/app/routers/tcg_product_import.py:294-307 `PUT /tcg/products/detail/{product_id}`（`require_super_admin`）
- backend/app/services/tcg_product_detail_svc.py:111 `update_product_detail`
- backend/app/services/tcg_product_detail_svc.py:116-118 `SELECT id FROM public.products WHERE id=:pid FOR UPDATE`
- backend/app/services/tcg_product_detail_svc.py:119-121 revision 不一致なら 409 `PRODUCT_DETAIL_CONFLICT`
- backend/app/services/tcg_product_detail_svc.py:170 `SET LOCAL app.is_operator = 'true'`
- backend/app/services/tcg_product_detail_svc.py:171-179 `UPDATE public.products SET name, name_en, mark, release_date, product_kind_id, work_id, manufacturer_id, product_category_id, category_class WHERE id=:pid`
- backend/app/services/tcg_product_detail_svc.py:180-192 キーワード: 変更があるリストだけ、その商品の行をすべて削除してから位置 1..n で挿入（:192 `enumerate(words, 1)`）
- backend/app/services/tcg_product_detail_svc.py:193-199 audit_log 挿入（:194 `_audit_pid = str(uuid4())` を record_id に使う、changed_by は actor の先頭 100 文字、old/new は JSON 文字列）
- migrations/20260921_110000_pipeline_tables_public.sql:404-413 `public.audit_log`（record_id UUID、changed_by VARCHAR(100)、old_values/new_values TEXT）
- migrations/062_create_inventory_movements_and_budget.sql:71-80 `set_updated_at_products` とトリガ（public.products の UPDATE で updated_at を更新）
- backend/app/services/tcg_product_master_svc.py:206 重複 mark の判定は新規登録・取り込み側（詳細保存では行わない）
- キャッシュ無効化: 経路内に該当なし（backend/app/routers/tcg_product_import.py:171 は `Cache-Control: no-store` のみ）

## §4 作業参照のダイジェスト
- backend/app/services/tcg_work_reference.py:30-31 `reference_digest`（参照全体の sha256）
- backend/app/services/tcg_work_reference.py:86-94 参照に全有効商品の name・name_en・mark・検索/除外キーワードが入る
- backend/app/services/tcg_analyzer_svc.py:1256-1259 保存済み v5 以降ジョブの再解析で、現在の参照のダイジェストが保存値と違えば `ValueError("Work reference changed; re-extraction required")`
- backend/app/tasks/tcg_extraction.py:423-428 抽出中に参照が変われば `REFERENCE_CHANGED`
- backend/app/services/tcg_work_comparison_svc.py:203 同条件で `INVALID_SAVED_REFERENCE`

## §5 v6 の型番ゲート（Gate 1）
- backend/app/services/tcg_analyzer_svc.py:1219-1224 `rawcode_to_id`: mark → id を作り、product_code → id で上書き（product_code 優先）
- backend/app/services/tcg_analyzer_svc.py:1431 `rawcode_to_id.get(_rawcode)`（Gemini v6 の raw_product_code の完全一致）
- backend/app/services/tcg_analyzer_svc.py:279-296 `match_one_kw`: 純 ASCII は語境界、日本語混じりは `token_and_match`
- backend/app/services/tcg_analyzer_svc.py:501-514 `match_product_keyword`
- v6 のキーワード照合は products.mark を使わない（`match_pid_with_work` は search_kw / exclude_kw の辞書のみ受け取る。本体は未読）
- 未確認: `token_and_match` の語順非依存、Gemini の選択の変化

## §6 変更前の本番値（/tmp/CC報告ファイル/system-accuracy-v9/masters/current_values.csv、2026-10-04 21:19 取得）
| id | code | mark | name | search_keywords（位置順） | exclude_keywords（位置順） | is_active |
|---|---|---|---|---|---|---|
| 58 | SV9 | SV9 | バトルパートナーズ | バトルパートナーズ | デッキビルド / デッキビルドBOX バトルパートナーズ | t |
| 60 | SVN | SV9 | バトルパートナーズ | バトルパートナーズ デッキビルド | （なし） | t |
| 74 | SV7 | SV7 | ステラミラクル | ステラミラクル | デッキビルド / デッキビルドBOX ステラミラクル | t |
| 75 | SVK | SV7 | ステラミラクル | デッキビルド ステラミラクル | （なし） | t |
| 103 | SV3 | SV3 | 黒炎の支配者 | 黒炎 / 黒炎の支配者 | デッキビルド / デッキビルドBOX | t |
| 105 | SVF | SV3 | 黒炎の支配者 | 黒炎の支配者 デッキビルド | （なし） | t |

6 件とも updated_at = 2026-10-03T17:49:56.779294+00:00。

## §7 T2 の証拠（v9 T2、3,066 ブロック、ローカルで実際の match_product を再実行）
- 基準（2026-10-01 のマスタ）: matched 2,336 / ambiguous 429 / unmatched 301。自動確定（needs_review=false）343。
- 曖昧の主因（ambiguous の class 2 のうち、候補の名前が違うもの 336、同名のもの 85）。同名 85 のうち SV3/SVF 20、SV7/SVK 20、SV9/SVN 16 の計 56 ブロック。
- 原因: 変種（SVF / SVK / SVN）は基底（SV3 / SV7 / SV9）と同じ mark を持ち、コードまたは mark が文中にあると両方が候補に入る（56 ブロックすべてで、変種は mark のみで候補入り。キーワードの当たりなし）。56 ブロックの文中に「デッキビルド」「ビルドBOX」は 0 件、「BOX」は 36 件。
- 変更後のマスタ（目標の状態＋品番キーワード）でのシミュレーション: ambiguous → matched 56（すべて基底に確定）、その他の遷移なし、matched → 非 matched / 別商品 0。matched 2,336 → 2,392、自動確定 343 のまま、クラス1相当 2,315 → 2,371 / 3,066。
- 合成プローブ（短い文字列）: 「{基底名} デッキビルド…」の各表記は変種、「SV7/SV3/SV9 BOX」は基底、「SV7 デッキビルドBOX」「[SV7] デッキビルド」は変種、「SV7a デッキビルド」は SV7a/SVK で曖昧（現状と同じ）。
- v6 の直近 30 日（本番の読み取り、2026-10-04 21:19）: analysis_results の product_id 別件数 60 = 13、75 = 7、105 = 11（58 は 269、74 は 198、103 は 178）。Gemini の選択（extraction_items.resolved_product_code）58:165、60:19、74:93、75:4、103:103、105:1。
- 元データ（ローカル、repo 外）: /tmp/CC報告ファイル/system-accuracy-v9/product-check/sim/deckbuild_sim.md、sim2/deckbuild_sim2.md、sim3/deckbuild_sim3.md、dup_master_check.md
