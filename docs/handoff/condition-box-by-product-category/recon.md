# recon: 状態判定 — 箱の商品を単品扱い（FLAG_SINGLE）にしない

- 作成：2026-10-06（調査は Sonnet、記録と確認は Opus）
- 設計：[design.md](design.md)
- 基準：origin/main 9c1b457ce（worktree `release/condition-box-by-product-category`）
- 社外秘：仕入元名・投稿本文は書かない（集計値と file:line だけ）。標本の生データは手元の `/tmp/CC報告ファイル/flag-single-recon/` と `/tmp/CC報告ファイル/condition-box/` にある。

## 1. 発端（観測事実）
- 2026-10-05 のお客様の申告で、Nike コラボ・ヒロインズ付録・30th カードセット・スターターセットが在庫一覧に出なかった。どれも状態が FLAG_SINGLE（単品扱い）になり、配信の対象外になっていた（`backend/app/services/tcg_distribution_svc.py:206-213`、本番の include_flag_single=false）。
- 本番の is_current 行は 11,321件。そのうち FLAG_SINGLE が 4,489件で、basis が `R4:単位既定:単位不明` のものが 4,254件。
- 商品・単位とも解決済みで needs_review=false の FLAG_SINGLE は 351件（＝単品扱いでなければ配信に載る行）。Opus が目で判定した結果（概数）は次のとおり。
  - 未開封の箱・セット・デッキ：約245件
  - まとめ売り・鑑定済みのシングル：約75件
  - プロモカード・雑誌付録：約31件

## 2. 既存 ADR（git grep 済み）
- `docs/adr/` を FLAG_SINGLE・`R4:単位既定`・resolve_condition・condition_basis で検索した。ヒットは0件。FEATURE-INDEX.md にも無い。
- 状態判定のルールは ADR ではなく、handoff の設計で管理されている。
  - `docs/handoff/tcg-cond-r5-fix/design.md`（R5 パック既定の追加）
  - `docs/handoff/condition-fallback-count/design.md:19,27`（`R4:単位既定:単位不明` を「完全お手上げ」として数える）
  - `docs/handoff/line-accuracy-pages/recon.md:62-65`、`docs/handoff/line-accuracy-pages/accuracy-evidence.md:28`（単位「個」で FLAG_SINGLE の 354件のうち、抜き取り10件がすべて誤り）
  - `docs/handoff/tcg-product-master-growth/recon.md:683,742`（ポケモンセンターの PSA シングルが BOX の商品に誤って当たった 15行。どれも単位は「枚」）

## 3. 状態判定のコード
- `backend/app/services/tcg_analyzer_svc.py:787-880` `resolve_condition_v2(raw_state, raw_product_name, kubun, cond_entries, cond_canonical_to_uuid, *, raw_memo)`
  - :815-825 R1 の前処理：箱系の単位でシングルの語があれば、basis に注記を付ける。
  - :827-849 状態マスタのキーワード（priority 順）。CN0008 FLAG_SINGLE は priority=1、適用区分は「枚系,単位不明」、語は PSA・SR・プロモ・枚 など。
  - :851-859 R4 の既定：kubun が箱系大なら Case、箱系なら Sealed box。
  - :861-877 R5：パック系なら Searched pack。
  - :879-880 **それ以外はすべて FLAG_SINGLE**（basis `R4:単位既定:単位不明`）。kubun が 単品系・複合・冊子系・条件つき・数量専用・除外・不明・空 のすべてがここに来る。
- 商品の情報は引数に無い。
- 解析の順番（`analyze_extraction_job`）：:1377 単位 → :1398-1486 商品の照合（matched_code・pid_resolved）→ :1503 product_uuid → :1509 状態。**状態を決める時点で、商品の照合は済んでいる。**
- 商品分類の辞書：`load_product_kubun_type_map`（:156-174。product_category_id → tcg_product_categories.kubun_type。キーは str(products.id)）と、それを使う `product_category_classes`（:1229-1238）。
- 既存の防御：シングルの印（SAR・AR・PSA 等、`backend/app/services/tcg_product_guards.py:5-17`）があると、Box の商品を照合の候補から外す（:561-563、:1421-1425）。
- ほかの呼び出し元：extraction_shadow_svc.py:272（商品あり・分類は読んでいない）、gemini_raw_copy_v10.py:342・gemini_raw_copy_v101.py:402,695（商品の照合なし）、tcg_unit_recovery_svc.py:499,952（商品を SELECT していない。対象を `condition_basis == "R4:単位既定:単位不明"` の完全一致で選ぶ。:476,:935）。
- テスト：`backend/tests/test_tcg_keyword_matching.py:949-1021`（R4・FLAG_SINGLE・R5）。

## 4. 商品の分類（マスタ）
- 箱か単品かを表す正本は `products.product_category_id`（INTEGER、FK は `public.tcg_product_categories(id)`。`migrations/20260920_010000_phase3_fk_rewire_unit_condition.sql:231-305`）。
- `tcg_product_categories` は本番に2行：id=1 PC_BOX（kubun_type=箱系）、id=2 PC_SINGLE（kubun_type=シングル系）。
- `products.category_class` は、いまの書き込み経路では作品名が入る（`backend/app/services/tcg_product_master_svc.py:374-380`、`backend/app/services/tcg_product_detail_svc.py:140`）。判定には使えない。
- 編集の経路：商品マスタ詳細ドロワー（`frontend/src/features/tcg-product-import/TcgProductDetailDrawer.tsx:135`）→ PUT `/tcg/products/detail/{product_id}`（`backend/app/routers/tcg_product_import.py:293-305`）。ほかに CSV 取り込み。
- 本番の値（active 1,323 商品）：PC_BOX 60、PC_SINGLE 20、NULL 1,243。主力の弾（SV・M・OP・FB の各弾）は1つも分類されていない。

## 5. 本番の分布（is_current 11,321行）
| 商品 | 分類 | 商品数 | 行数 | うち R4 単位不明 |
|---|---|---|---|---|
| あり | PC_BOX | 51 | 940 | 370 |
| あり | PC_SINGLE | 12 | 258 | 178 |
| あり | NULL | 277 | 3,989 | 1,799 |
| なし | — | — | 6,134 | 1,907 |

- 351件の標本の、単位の区分 × 商品の分類：

| kubun | Box | Single | 空 | 商品なし | 計 |
|---|---|---|---|---|---|
| 条件つき（個など） | 56 | 6 | 154 | 15 | 231 |
| 単品系（枚） | 6 | 5 | 57 | 0 | 68 |
| 複合（セット） | 8 | 2 | 27 | 0 | 37 |
| 冊子系（冊） | 0 | 6 | 8 | 0 | 14 |
| 数量専用（点） | 1 | 0 | 0 | 0 | 1 |

- 単品系（枚）× Box の6行には、鑑定済みシングル（PSA7・PSA8）が2行ある。単品系まで箱扱いにすると、シングルを箱にする誤りが出る。
- 再解析：1ジョブ単位の API がある（POST `/tcg/extraction-jobs/{id}/reanalyze`、`backend/app/routers/tcg_product_master.py:316-362`）。一括で再解析する道具は見つかっていない。配信は直近48時間の is_current 行だけを見るので、新しい投稿の解析で置き換わっていく。

## 6. 未確認
- E4（状態から単位を逆に引く処理、`backend/app/services/tcg_unit_recovery_svc.py:1088` 以降）が、箱系の行に単位を付けるか。
- 商品を一括で分類し直す機能の有無。
- 商品は見つかっているのに product_id が NULL の行（29件）の原因。
