# 実装カード：便2「ブックレット系」（ADR-1035）

- 起案：2026-10-20、Opus。PO の実装承認：2026-10-20（便2 に進む「1」）。
- 設計：[design.md](./design.md)「便2」「値」「リスクと対処」「受入条件 K3-2・K5〜K7」
- ブランチ：`release/booklet-category-bin2`（worktree `~/worktrees/salesanchor/release-booklet-category-bin2`）

## この PR でやること（コードと構造。データは入れない）

| # | 場所（origin/main 64fd420a9 で確かめた行） | 前 | 後 |
|---|---|---|---|
| 1 | `backend/app/services/gemini_raw_copy_v102_product_first.py:48-52` | 区分の定数は 5 つ | `PRODUCT_KUBUN_SET` の次に `PRODUCT_KUBUN_BOOKLET = "ブックレット系"  # 状態を booklet 群の行で判定し、語が無ければ With booklet にする（ADR-1035）` を足す |
| 2 | 同 `:86-91` | single・promo_pack の定数 | `VALUE_GROUP_BOOKLET = "booklet"`、`CONDITION_BOOKLET_DEFAULT = "With booklet"`、`BASIS_BOOKLET_DEFAULT = "R9:ブックレット既定"  # R4 で始めない（R6〜R8 と同じ扱い）` を、既存の並びに合わせて足す |
| 3 | 同 `:581-584` `_KUBUN_TO_VALUE_GROUP` | 2 行 | `PRODUCT_KUBUN_BOOKLET: (VALUE_GROUP_BOOKLET, CONDITION_BOOKLET_DEFAULT, BASIS_BOOKLET_DEFAULT),` を足す。`_resolve_scoped_condition` と `_resolve_condition` の本体は変えない |
| 4 | `backend/app/services/tcg_analyzer_svc.py:653` | `("single", "promo_pack")` | `("single", "promo_pack", "booklet")` |
| 5 | `backend/app/services/line_analysis_v102_svc.py:644` `_SCOPED_GROUP_OF_KUBUN` | 2 つ | `PRODUCT_KUBUN_BOOKLET: VALUE_GROUP_BOOKLET` を足す（import も足す） |
| 6 | `backend/app/services/tcg_result_order.py:11` | 5 つ | 末尾に `"booklet"` を足し、上のコメントの群の順にも「→ ブックレット」を足す |
| 7 | 新しい migration（構造だけ） | value_group の CHECK は 5 群と NULL | `booklet` を足して制約を作り直す。ADR-1031 で promo_pack を足した migration を探し、同じ書き方にする。データは入れない。`scripts/run_all_migrations.sh` に登録する |
| 8 | 記録 SQL `docs/handoff/condition-unit-booklet/data/bin2/`（新規） | — | 01_precheck・02_apply（`-v end=ROLLBACK\|COMMIT`）・03_verify・04_rollback・05_target_jobs。便1 の data/ と同じ形にする。中身は下の「データ」 |
| 9 | テスト `backend/tests/test_adr1035_booklet.py`（新規） | — | 下の「テスト」 |
| 10 | `backend/tests/test_tcg_result_order.py` | 5 群の固定値 | 6 群に直す |
| 11 | `backend/tests/test_inventory_distribution_rows.py:107`・`:119`・`:270-284` | 今の SQL の長さとハッシュ | `VALUE_GROUP_ORDER` が変わった後の値で作り直す。ほかの固定値は変えない |

触らない範囲：上の 11 か所以外の製品コード。とくに `_resolve_scoped_condition` の本体、`gemini_raw_copy_v102_soldout_ref.py`（〆の規則 11b。design の値 6.）、v6・v10・v101・shadow・GAS、状態の色、フロントエンド。

## データ（記録 SQL。AI は書くだけで、流すのは PO が台本で行う）

- 状態マスタ（line_conditions、ADR-1007 の様式。ADR-1031 で promo_pack の行を足した記録 SQL を探し、列と書き方をそろえる）に 2 行を足す。
  - With booklet：群 booklet、適用区分 ブックレット系、KEYWORD、当てる語なし、priority 10、value_rank 1、単位 Booklet（id 17）、OUTPUT。
  - Without booklet：群 booklet、適用区分 ブックレット系、REGEX `(?i)((ブックレット|冊子)[\s　]*(無し|なし|抜き|欠品|欠け)|(?<![a-z])(no|without)[\s　]+booklet)`、priority 2、value_rank 2、単位は空、OUTPUT。
  - code は CN0023（With booklet）・CN0024（Without booklet）を固定で書く。line_conditions.code には画面が自動で作る CN+14 桁の日時の値もあるため、最大値からの採番はしない（2026-10-20 dryrun で桁あふれ）。precheck で番号と英語名が重ならないことを確かめる。
- 区分マスタ（tcg_product_categories）に 1 行を足す：`PC_BOOKLET`、表示名 `Booklet`、kubun_type `ブックレット系`。
- 商品 440415 の区分を、ブックレット系にする。WHERE には `id=440415 AND 今の区分 id=2` を書き、更新件数が 1 でなければ 1/0 で止める。
- 05_target_jobs：440415 の v102 の現行行を持つ job **だけ**。外す商品は無い（便1 の入れ忘れの再発防止。design「便1 の結果」K4）。対象の job 数を precheck で出す。
- 04_rollback：2 行を is_active=false にし、440415 の区分を 2 に戻す。区分の行は is_active=false にする。

## テスト（K6・K7）

1. 区分がブックレット系で、原文に付き・無しの語が無ければ、状態 With booklet・basis `R9:ブックレット既定`・要確認なし。
2. 「ブックレット無し」「冊子なし」「冊子 抜き」「No booklet」「without booklet」のときは Without booklet になる。
3. 「送料無料」「無地スリーブ」「casino booklet」「Mono booklet」「booklet付き」のときは With booklet のまま（誤爆しない）。
4. 群の行が masters に無いときは、今と同じ道を通る（ブックレット系の商品でも、状態は今の判定のまま）。
5. v6 の経路（`tcg_analyzer_svc` の `SCOPED_VALUE_GROUPS` で除く所、:747）は、booklet の行を返さない。
6. `VALUE_GROUP_ORDER` で booklet が最後にある。
- 既存のテストのうち、直してよいのは #10・#11 の 2 本だけ。ほかのテストファイルは変えない。

## 確かめる手順（実装役）

1. `./scripts/dev/executor-preflight.sh || exit 1`（worktree の中で）
2. 実装の前に、上の行番号が今も同じ中身か確かめる。違ったら止めて報告する（BLOCKED:）。
3. 実装したら、backend のテスト（少なくとも新しいテスト、#10・#11、`test_*v102*`・`test_*adr1031*`・`test_*result_order*`・`test_inventory_distribution*`）を流す。生出力はファイルに残す。
4. i18n の対象になる画面の文字は無い（フロントは触らない）。
5. commit・push・`gh pr create --base main`（`gh auth status` で shingo-cc 名義を確かめる。本文は PR テンプレートの形にし、「### 標準ワークフロー確認」と、触るファイル・削除するファイルを全部書く）。migration を含むので **Draft** で起票する。マージはしない。

## 想定される分かれ道

- ADR-1031 の promo_pack の migration や記録 SQL が見つからない → 推測で作らず、BLOCKED: で報告する。
- CHECK 制約の名前が、migration と本番の作り方で違いそう → 制約の名前を `pg_constraint` で読む SQL を precheck に入れ、作り直す SQL は名前を固定にしない。
- `test_inventory_distribution_rows.py` の固定値が、ほかの理由でもずれている → 直さず、NEEDS_DECISION: で報告する。
- 単位 id 17 が Booklet でない → 止めて報告する（precheck で確かめる）。

## 反映の順序（Opus と PO）

① この PR を審査し、マージして本番に反映する（行がまだ無いので、今と同じ動き）→ ② PO が記録 SQL の dryrun と commit を台本で流す → ③ 再解析 → ④ K3-2・K5 を reader で測り、design.md に記録する。
