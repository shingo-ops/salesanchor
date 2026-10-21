# 実装カード: サプライ系 便1（コードと CHECK）

PO 実装承認: 2026-10-20「1」（便1 の仕組みの直しに取りかかる）。設計: docs/handoff/supply-category/design.md（PR #4580、審査 APPROVE c0d2bed8a）。

## 作業場所
- `bash scripts/new-worktree.sh release/supply-category-bin1 --claude`（origin/main 起点）。作業はその中だけで行う。
- 開始時に `./scripts/dev/executor-preflight.sh || exit 1`。

## やること（design.md「便1」の表 #1〜#10 をそのまま）
1. `backend/app/services/gemini_raw_copy_v102_product_first.py`
   - 区分の定数に `PRODUCT_KUBUN_SUPPLY = "サプライ系"`。
   - 状態の定数に `VALUE_GROUP_SUPPLY = "supply"`、`CONDITION_SUPPLY_DEFAULT = "Supply"`、`BASIS_SUPPLY_DEFAULT = "R10:サプライ既定"`。
   - `_KUBUN_TO_VALUE_GROUP` に `PRODUCT_KUBUN_SUPPLY: (VALUE_GROUP_SUPPLY, CONDITION_SUPPLY_DEFAULT, BASIS_SUPPLY_DEFAULT)`。
   - `_resolve_unit_from_state`: セット系の分岐の後に「区分がサプライ系で、状態の単位があれば、書かれた単位に関わらず状態の単位にする」分岐。unit_basis は `from_condition`、`reason: "supply_kubun"`。
   - `PRODUCT_KUBUNS_DEFAULTING_TO_BOX` は変えない。
2. `backend/app/services/tcg_analyzer_svc.py` の `SCOPED_VALUE_GROUPS` に `"supply"`。
3. `backend/app/services/line_analysis_v102_svc.py` の `_SCOPED_GROUP_OF_KUBUN` に サプライ系 → supply。
4. `backend/app/services/tcg_result_order.py` の `VALUE_GROUP_ORDER` 末尾に `"supply"`。
5. 新規 migration（構造だけ）: line_conditions.value_group の CHECK に `supply` を足す。`migrations/20261020_100000_line_conditions_value_group_add_booklet.sql` と同じ形で「既に supply を許していれば飛ばす」ガード付き。`scripts/run_all_migrations.sh` の booklet の次に登録。データの INSERT は書かない（ADR-1007）。
6. テスト
   - 新規 backend/tests/test_supply_category.py: design.md K1 の 4 点（サプライ系「100枚入 350円 在庫1,000」→ 単位 Bag・状態 Supply・basis R10・数量 1000・価格 350 は件を組み立てる層で見る／サプライ系でない商品の「100枚入」は Piece のまま／v6 経路で supply 行が返らない／migration 2 回流し成功）。
   - 変更してよい既存テストは 4 本だけ: `backend/tests/test_tcg_result_order.py`、`backend/tests/test_inventory_distribution_rows.py`、`backend/tests/test_adr1035_booklet.py`（固定値）、`backend/tests/test_line_conditions_value_group_rerun_pg.py`（流れを supply まで延ばす）。

## 触らない範囲
- 上記以外の製品コード・既存テスト・frontend・deploy.yml・本番 scripts。
- マスタの値（単位 Bag・区分・状態行・作品・細分類）は便2。この便では入れない。
- ADR-1035 の文書（設計 PR で済み）。

## 想定分岐（迷ったら止めて Opus へ NEEDS_DECISION:）
- 行番号が design.md とずれている → 名前で探して直す。中身が設計と違う（例: 分岐の形が想定と違う）なら止める。
- 4 本以外の既存テストが落ちる → 直さずに止める。
- migration の前例の形が読めない → 止める。

## 完了の条件
- ローカルで新規テストと変更した 4 本、関連テストが通る（生出力をファイルへ）。
- `gh auth status` で shingo-cc を確認し、`gh pr create --base main`。migration を含むので **Draft** で起票し、本文に「### 標準ワークフロー確認」（design は docs/handoff/supply-category/design.md・PR #4580 を参照）、触るファイル一覧を入れる。社外秘の原文・投稿番号は入れない。
- 報告は DONE / BLOCKED: / NEEDS_DECISION: で、PR URL・HEAD・テスト生出力のパス。
