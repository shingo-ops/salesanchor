# recon: 共用マスタの語の修正（作品 8982、商品 420439 / 420450 / 420560 / 440578 / 466060）

実測日 2026-10-21。実測時の origin/main: 650005f29（`git log -1 origin/main` 取得時点の先頭付近）。事実のみ。投稿本文・仕入元名は含まない。

## §1 既存 ADR の検索
実行: `git grep -il -e "code_only_match" -- docs/adr`、`git grep -n -e "ADR-1020" -- docs/adr/FEATURE-INDEX.md`

- "code_only_match" を含む ADR: 該当なし（0 件）
- docs/adr/FEATURE-INDEX.md:19: 共用商品の登録 / 必須項目 / 空欄確認 → ADR-1020 ／ ADR-155 ／ ADR-156
- ADR-155（docs/adr/ADR-155-product-master-ssot-csv-app.md:25-27）: 商品マスタの値の正規の更新手段は CSV とアプリ画面。例外として直接 SQL を PO が 2026-10-04 に決定した前例が docs/handoff/deckbuild-master-fix/README.md にある。今回も PO 合意（2026-10-21）に基づく直接 SQL（PO の ! 実行のみ）。

## §2 照合の経路（事実）
- backend/app/services/extraction_judgement_svc.py:31 `normalize_for_match`（正規化）、:57 `_needs_boundary`（2文字以下・数字だけは語境界）、:246 `_keyword_matches`（空白で分けた全語が含まれれば一致）、:338 `_excluded_keywords`（除外語は分けずに全体が含まれれば除外）
- backend/app/services/gemini_raw_copy_v102_product_first.py:196 `_CODE_ONLY_OFF_WORKS_SQL`（match_by_code = TRUE かつ code_only_match = FALSE の作品は型番だけでは当てない）、:227 `build_g2_index`、:273 `_g2_candidates`、:280-282（名前の候補が 0 件のとき、型番だけ当てが許される作品に限り型番で当てる）、:286 `match_product_g2`

## §3 書き込み経路の前例
- backend/app/services/tcg_product_detail_svc.py:151 `update_product_detail`: 行ロック → 更新 → 語の入れ直し → audit_log 1 行。今回は同じ効果を SQL で行う（語は末尾に足すだけ。更新時刻を進め、audit_log を書く）。
- docs/handoff/deckbuild-master-fix/gen_sql.py: 直接 SQL の前例（DO ブロックで現在値を照合し、行数を確認し、最後の状態を照合し、dryrun.sql は apply.sql と同じで最後だけ ROLLBACK）。
- 作品 type_master の code_only_match を変える API はない。前例は直接 SQL。type_master に監査用のトリガはなく、audit_log に手で 1 行書く。

## §4 本番の今の値（reader 鍵・2026-10-21）
- type_master 8982: code_only_match = false、match_by_code = true
- 商品の語は docs/handoff/master-keyword-fix/README.md の表のとおり
- product_blank_confirmations: 対象 5 商品とも 0 行（合計 78 行は別商品）

## §5 シミュレーション（社外秘の本文は載せない。数のみ）
- 母集団: v102・有効投稿・直近 30 日の現行行 1424 文 + 未登録グループ 74 文 = 1498
- 全修正を入れた結果: 変わった文 10 行（重複を除くと 5 文）。ambiguous → matched 2、unmatched → matched 8。悪くなった文 0（matched → 別 id、matched → 未一致/迷い、とも 0）
- Vジャンプ系の取り違え検査（合成文 15 件）: 付録カード + VJ2610 は 424595 に確定（前は 420560）。Vジャンプ + 麦わら3人セットは 424595 に確定（前は 420439 と 424595 で迷い）。付録カード + 応募者全員サービス / 麦わら3人セットは未一致（前は取り違え/迷い）
- 限界: 30 日より古い行は母集団外。SQL はローカル DB で試していない（本番 dryrun が最初の実行確認）。
- 再解析の対象 job: 2 本（変わる 5 文の所属 job）
