# recon: v102 の前後の作品の多数決で、同数のとき候補を持つ作品が1つだけなら決める

この文書は何か：商品が2作品にまたがって決まらない件のうち、「同数」で止まっているものの現状を、コードの行番号つきで確かめた記録。
親（設計仕様書）: [docs/specs/line-analysis-tuning/README.md](../../specs/line-analysis-tuning/README.md)（子: [design.md](design.md)）

- 基準: origin/main 8ffee20532c7663acd9638382782367c5d884172。読み取りのみ。
- 既存 ADR 検索: `git grep -i "matched_context\|decide_by_context\|context_work" docs/adr docs/specs` と docs/adr/FEATURE-INDEX.md の v102 検索 → 規則そのものを定めた ADR は無し（grep 済み）。関連する方針は ADR-154（docs/adr/ADR-154-tcg-parity02-gas-python-migration.md:43「作品をまたぐ誤商品判定の防止」）。関連する過去の便は #4037「前後の商品で作品を決める」（docs/handoff/v102-followup-post-ref/recon.md:12）。

## 1. PO の決定（原文）
2026-10-19「y,上がドラゴンボール、下が遊戯王であれば遊戯王には当てはまらないため、ドラゴンボールを採用、ドラゴンボールとワンピースなど同じ型番があるシリーズに挟まれた場合は要確認に待っわす」

## 2. 現状（事実）
- backend/app/services/gemini_raw_copy_v102_context_work.py:126-128 `ranked = Counter(c.work_id for c in near).most_common()` の直後、先頭2つの作品が同数なら `return _undecided(REASON_TIE)`（候補を持たない作品が同数でも決めない）。
- 同ファイル :23-25 に規則定数 a / b / c。:96-131 `_decide_one`。(b) と (c) は `_pick(..., check_competitor=True)`（:77-87）で「候補がちょうど1つ」「落とす候補の作品がその投稿に無い」を見る。
- 規則の値の読み手（grep 結果）: backend/app/services/gemini_raw_copy_v101.py:1148-1149 が `product_context={"rule": decision.rule, ...}` として件に付けるだけ。表示・i18n・DB 列・pid_basis への参照は無い（pid_basis は `V102:<match_status>` で rule を使わない）。frontend/src に product_context / rule の参照なし。→ 値 "d" を足しても他の変更は要らない。
- 既存テスト: backend/tests/test_gemini_raw_copy_v102_context_work.py:63-135 が a / b / c / tie を固定。

## 3. 試算で確認した事実
- 試算の入力と結果は手元（社外秘）~/CC報告ファイル-keep/accuracy-20261014/ri/fix/tie/。リポジトリ・PR 本文には載せない。
