# 実装カード 便1: まとめの数の列・読み取り・配信の商品名・理由コード・再現の台本

> 親: [design.md](./design.md) §5-1〜§5-5・§8・§9／ADR: [ADR-1027](../../adr/ADR-1027-bundle-sale-reading.md)／KGI: [kgi.md](../../specs/bundle-sale/kgi.md)（K1〜K6 は便3 で照合。便1 は A1〜A4）
> 区分: ADR-1015 の A。`migrations/` と `scripts/run_all_migrations.sh` を含むため、マージ前に ADR-136 の GO 手順が要る（GO は Opus に委任）。
> 状態: カード作成済み。実装の承認は PO の「y」（2026-10-17、y の意味「設計を保存し、Sonnet に作らせ、本番反映と照合まで進めます」）。

## 読んだ節（Opus・カード作成時の照合）
- docs/handoff/design-partner-card-ops/guards/00-common.md: 全コマンドを cd 作業場所のフルパス && で始める・出力に上限・出力先は /tmp/CC報告ファイル/bundle-sale/bin1/（列挙対象の外）・commit/push/PR は各段で git log と .pr-number の実在を確かめる → 本カードの冒頭と項目 7 に反映。
- guards/07-migration.md: run_all_migrations.sh の末尾に run_sql を登録・採番は直近を実測してから・migrations は CODEOWNERS で shingo-ops の承認も要る → 項目 1 に反映。
- guards/05-pr.md: PR は scripts/gh-pr-create-safe.sh で作る・触るファイルは同一行カンマ区切り・GO 前は GO記録の欄を作らない・削除があれば列挙 → 冒頭に反映。
- 照合の結果: 違反なし（下書き PR は使わない。--admin・--auto は使わない）。

## 冒頭（必読）
- 受領確認: 着手前に「便1 カード受領・作業場所・HEAD」を報告ファイル /tmp/CC報告ファイル/bundle-sale/bin1/receipt.txt に書く（パスは一字一句そのまま）。
- 停止したときは、止まった項目・理由・生出力のパスを `BLOCKED:` または `NEEDS_DECISION:` で Opus に返す（報告経路は Opus への最終報告だけ）。
- 全コマンドは `cd /Users/tanizawashingo/worktrees/salesanchor/release-bundle-sale-bin1 &&` で始める。出力は head/tail で上限を付け、生出力は /tmp/CC報告ファイル/bundle-sale/bin1/ に保存する。
- commit・push・PR 作成は段を分け、各段で `git log -1` と `.pr-number` の実在を確かめる。PR は `bash scripts/gh-pr-create-safe.sh` で作る（本文は先に /tmp/CC報告ファイル/bundle-sale/bin1/pr-body.md へ書き、そのパスを --body-file に渡す）（下書きにしない）。PR 本文は #4463 の型。GO記録の欄は作らない（Opus が書く）。マージはしない。
- 実装役は `./scripts/dev/executor-preflight.sh || exit 1` を最初に実行する。作業場所は `bash scripts/new-worktree.sh release/bundle-sale-bin1 --claude`（origin/main 起点）。
- このカードに書いていないことはしない。迷ったら止まって Opus に `NEEDS_DECISION:` で返す。
- 本番 DB・secrets・GitHub の設定には触らない。本番データ（`/tmp/CC報告ファイル/bundle-sale/sim/all-rows.tsv`）は社外秘。リポジトリ・PR・コミットに中身を載せない。
- 行番号は origin/main d6b956826 時点（recon.md）。今の origin/main で行がずれていれば実物に合わせる。中身が違えば止まる。

## 実物点検（最初に。推測で進めない）
1. `backend/app/services/line_analysis_v102_svc.py` の `_UPSERT_SQL`（:709-732）、`_analysis_values`（:672-706）、`_source_block`（:938-945）、`_apply_bulk_price`（:956-973）、`_write_results`（:995-1044）、`_unit_price_mismatches`（:913-930）、`_inherit_price` と `_INHERIT_PRICE_SQL`（:1161-1225）を読み、`_write_results` の中で「単位の別名マスタ（alias→canonical・unit_id）」がどの変数で手に入るかを報告に書く。手に入らない場合は `backend/app/services/tcg_analyzer_svc.py:103-129`（unit_alias_to_info）の今の読み込みを使う。新しく別名の表を持つ必要が出たら止まる。
2. `backend/app/services/v102_bulk_price_svc.py:50-189` の convert の戻り値（set / piece / review）の形を確かめる。
3. `backend/app/services/v102_unit_price_check_svc.py:54-68`（`_MARKET_SQL`）、`backend/app/services/v102_buyback_unit_svc.py:134-143`（is_buyback_candidate）を読む。
4. `backend/app/services/tcg_distribution_svc.py` の dist_base（:300-354 付近。japanese_title :304・english_title :305・`LEFT JOIN public.products p` :340 付近・gkey :326-328）を読む。
5. `migrations/20261011_150000_add_analysis_results_price_basis.sql`（前例の形）、`migrations/20260922_080000_rename_line_analysis_tables.sql:20,32`（line_units と VIEW public.units）、`scripts/run_all_migrations.sh` の末尾の登録行を読む。
6. `backend/tests/test_line_analysis_v102_pg.py:44-45` など、テストが migration を読み込む箇所を `git grep -n "20261011_150000" backend/tests` で全部挙げる。
7. 理由コードの 4 点の今の形: `backend/app/services/review_reason_codes_svc.py:22`（NON_ACKABLE）、`docs/handoff/v102-prod-switch/data/review_reason_codes/seed_20261016_bulk_price_basis_unknown.sql`、`frontend/src/locales/ja.json`・`en.json` の `reviewReason.bulk_price_basis_unknown`、`backend/app/data/review_reason_labels_ja.json`:17 と同期ツール（`backend/tests/test_review_reason_labels_ja_sync.py` が呼ぶもの）。

## 項目 1: migration 2 本（構造だけ・冪等・値の操作なし ADR-1007）

### 変更
- 新規 `migrations/20261017_HHMMSS_add_analysis_results_bundle_size.sql`: `ALTER TABLE public.analysis_results ADD COLUMN IF NOT EXISTS bundle_size integer NULL;` ＋ `COMMENT ON COLUMN`（「まとめ売りのまとめの数。NULL=まとめ売りでない。ADR-1027」）。CHECK は付けない（2 以上はコードで守る）。
- 新規 `migrations/20261017_HHMMSS_add_line_units_display_names.sql`: `ALTER TABLE public.line_units ADD COLUMN IF NOT EXISTS name_ja text NULL, ADD COLUMN IF NOT EXISTS name_en text NULL;` ＋ COMMENT。
- `scripts/run_all_migrations.sh` の末尾に 2 行 `run_sql`。deploy.yml には書かない（deploy.yml:223）。
- 実物点検 6 で挙げたテストの migration 読み込みに 2 本を足す。

### 触らない範囲
- VIEW public.units は作り直さない（配信は line_units を直接 JOIN する）。tenant_004 の表・既存の列には触らない。

## 項目 2: 読み取りの純関数（新規 `backend/app/services/v102_bundle_svc.py`）

- `detect_bundle(block, alias_to_canonical, set_words, price, quantity) -> BundleResult | None` を design.md §5-2 の 1〜8 のとおりに作る。戻り値は「決まった（bundle_size=N・canonical）」「決まらない（理由 bundle_unverified）」「当たりなし（None）」。
- 単位の語は引数の alias_to_canonical だけから作る。canonical が `Set` の語は単位の語から外し、set_words（数量の直後の「セット」判定用）に回す。単位の語をこのファイルに書かない。
- まとめの語はこのファイルの定数 1 か所（§5-2 の 3 の 12 語）。
- 括弧: `（）` `()` は NFKC で `()` になる。閉じない括弧は改行まで中とみなす。
- 設計時の台本 `/tmp/CC報告ファイル/bundle-sale/replay2/replay.py` の detect() と同じ結果になること（台本は判定の参照。台本の TSV 区切り " / " は本番では改行）。

## 項目 3: 解析の流れへのつなぎ（`line_analysis_v102_svc.py`）

- `_analysis_values` は `bundle_size=None` を返す。`_UPSERT_SQL` の INSERT 列・VALUES・ON CONFLICT の SET に bundle_size を足す。
- `_write_results` で `_analysis_values` の直後、全ての行（区分を問わない）に `_apply_bundle` を当てる。原文は `_source_block` で全ての行に作る。
  - 決まった: bundle_size=N、unit_canonical・unit_id・unit_resolved を中身の単位にそろえる。price_normalized・quantity_normalized は変えない。この行は `_apply_bulk_price` を通さない。
  - 決まらない: 値は変えず、review_reasons に `bundle_unverified` を足し needs_review を真にする（今の理由の足し方に合わせる）。
- `_apply_bulk_price`: convert が set を返したときの換算（÷N・×N・備考・`V102:bulk:set:N`）を消し、代わりに理由 `bulk_price_basis_unknown` で review にする。piece と review の扱いは今のまま。
- 相場: `_MARKET_SQL` に `AND ar.bundle_size IS NULL`。`_unit_price_mismatches` の候補から bundle_size のある行を外す。
- 引き継ぎ: `_inherit_price` は bundle_size のある行を対象外。`_INHERIT_PRICE_SQL` の引き継ぎ元に `AND ar.bundle_size IS NULL`。
- 買取: `is_buyback_candidate`（v102_buyback_unit_svc.py:134-143）に `values.get("bundle_size") is None`。

### 触らない範囲
- 人の直し（`v102_human_decisions_svc.py`）・状態の決め方・NON_ACKABLE_REASON_CODES・画面のコード（frontend の在庫表・閲覧・比較表）。

## 項目 4: 配信の商品名と鍵（`tcg_distribution_svc.py`）

- dist_base に `LEFT JOIN public.line_units lu ON lu.id = ar.unit_id`。
- 商品名の 2 欄を Python の関数 1 つ `bundle_title_sql()`（同ファイル）で作り、SQL はそれを埋め込む:
  - japanese_title: bundle_size が NULL なら `COALESCE(p.name,'')`、あれば `COALESCE(p.name,'') || ' ' || ar.bundle_size || COALESCE(lu.name_ja, lu.canonical, ar.unit_canonical) || 'セット'`
  - english_title: NULL なら `COALESCE(p.name_en,'')`、あれば `COALESCE(p.name_en,'') || ' ' || ar.bundle_size || ' ' || COALESCE(lu.name_en, lu.canonical, ar.unit_canonical) || ' Set'`
- gkey の concat_ws に `COALESCE(ar.bundle_size::text, '')` を足す。
- 「セット」「Set」はこの関数の中だけに書く。

## 項目 5: 理由コード bundle_unverified（4 点）

- 新規 `docs/handoff/v102-prod-switch/data/review_reason_codes/seed_20261017_bundle_unverified.sql`（前例 seed_20261016 の形・1 行 `('bundle_unverified','system','analysis')`）と、本番用の `bu_dryrun.sql`・`bu_commit.sql`・`bu_verify.sql`・`bu_rollback.sql`（前例 bp_*.sql の形）。実行はしない（便2）。
- コード側の定数（line_analysis_v102_svc か v102_bundle_svc。整合テストが拾う場所）。NON_ACKABLE には入れない。
- `frontend/src/locales/ja.json`・`en.json` の reviewReason に `bundle_unverified`（ja「まとめ売りの数が本文で決まらない」/ en「Bundle size not determined from text」）を bulk_price_basis_unknown の隣に。
- `backend/app/data/review_reason_labels_ja.json` を同期ツールで作り直す（手で書かない）。

## 項目 6: 単位の呼び名の記録 SQL（実行しない・便2）

- 新規 `docs/handoff/bundle-sale/data/units_display_dry_run.sql`・`units_display_commit.sql`・`units_display_verify.sql`・`units_display_rollback.sql`。line_units を id で特定して design.md §5-1 の表の値（9 カートン/Case、10 BOX/Box、11 パック/Pack、12 枚/Piece、13 セット/Set、16 個/Item）を入れる。commit は BEGIN…COMMIT、更新前に canonical が表どおりかを確かめ、違えば 0 行で終わる WHERE にする。rollback は 6 行を NULL に戻す。

## 項目 7: 再現の台本 `scripts/dev/bundle_replay.py`

- 引数: all-rows.tsv・units（q3）・aliases（q4）・出力フォルダ。`v102_bundle_svc.detect_bundle` を import して全行に当てる（判定の作りを 2 か所に持たない）。
- TSV の本文の " / " を改行に戻して当てる。price_basis が `V102:bulk:set:N` の行は数量を ÷N して換算前に戻してから当てる。
- 出力: rows.tsv（item_id・判定・N・単位・理由）、summary.txt（判定ごとの行数・本文 md5 の種数・job 数、「N＋別名に無い語＋まとめの語」の語の数え）。データはリポジトリに置かない。

## 項目 8: テスト

- 新規 `backend/tests/test_v102_bundle.py`: §5-2 の各条件（B1・括弧・閉じない括弧・入・N=1・違う (N,単位) 2 つ・値段なし・割り切れ・数量の直後セット・Set の別名を単位に使わない）、`v102_bundle_svc.py` のソースに単位の語（パック・枚・個・pack・piece・box・カートン）が無いこと、`bundle_title_sql()` の 2 欄と gkey。
- `backend/tests/test_v102_bulk_price.py`: L22・L28・L44・L102・L152 を「割らない・掛けない・bundle_size=N」に、L163 の期待を (26000, 5, "Piece", bundle_size=100) に書き換える。piece と review のテストは変えずに緑。set を返したのに R' で決まらないとき bulk_price_basis_unknown になるテストを 1 つ足す。
- 相場・引き継ぎ・買取から bundle_size のある行が外れるテスト（既存の test_v102_unit_price_check.py・test_v102_price_inherit_pg.py・test_v102_buyback_unit.py に足す）。

## 項目 9: 文書の注記

- `docs/adr/ADR-1021-bulk-condition-state.md` の便2 の決まり（:27-38 付近）に「set の換算は ADR-1027 で置き換え（piece・review はそのまま）」を 1 行。`docs/handoff/g28-bulk-price/design.md` の便2 にも同じ 1 行。`node scripts/generate-adr-index.js` で索引を作り直す（ステータス欄に「承認」の字を書かない。generate-adr-index.js:59）。

## 止まる条件
- 実物点検の結果がこのカードの前提（file:line の中身）と違う。
- 別名マスタを `_write_results` で使えず、新しい読み込みか語の表が要る。
- 項目 7 の結果が A1（82 種 144 行・5 種 5 行・4,655 行、replay2/out2/rows.tsv と行ごとに一致）と 1 行でも違う。違う行を一覧にして返す。
- テストが通らず原因がカードの範囲外。カードに無いファイルを触る必要が出た。

## 受け入れ基準
| 基準 | 検証方法 |
|---|---|
| A1 bundle_replay.py の結果が 決まる 144 行（82 種）・決まらない 5 行（5 種）・当たらない 4,655 行で、`/tmp/CC報告ファイル/bundle-sale/replay2/out2/rows.tsv` と item_id ごとの判定・N・単位が全て一致 | Sonnet が PR 前に実行し、生出力と差分（0 行）を `/tmp/CC報告ファイル/bundle-sale/bin1/` に保存 |
| A2 項目 8 の新しいテストが緑 | CI（backend pytest） |
| A3 test_v102_bulk_price.py の書き換えと、piece・review のテストが変わらず緑 | CI と PR の差分 |
| A4 i18n の ja/en が同じキー、理由コードの整合テスト 2 本が緑 | CI |
| migration 2 本が run_all_migrations.sh に登録 | migration-guard（CI） |

## 触るファイル（全部）
migrations/20261017_HHMMSS_add_analysis_results_bundle_size.sql、migrations/20261017_HHMMSS_add_line_units_display_names.sql、scripts/run_all_migrations.sh、backend/app/services/v102_bundle_svc.py、backend/app/services/line_analysis_v102_svc.py、backend/app/services/v102_bulk_price_svc.py（set を返す形を変える場合のみ）、backend/app/services/v102_unit_price_check_svc.py、backend/app/services/v102_buyback_unit_svc.py、backend/app/services/tcg_distribution_svc.py、backend/app/data/review_reason_labels_ja.json、frontend/src/locales/ja.json、frontend/src/locales/en.json、docs/handoff/v102-prod-switch/data/review_reason_codes/seed_20261017_bundle_unverified.sql・bu_dryrun.sql・bu_commit.sql・bu_verify.sql・bu_rollback.sql、docs/handoff/bundle-sale/data/units_display_{dry_run,commit,verify,rollback}.sql、scripts/dev/bundle_replay.py、backend/tests/test_v102_bundle.py、backend/tests/test_v102_bulk_price.py、backend/tests/test_v102_unit_price_check.py、backend/tests/test_v102_price_inherit_pg.py、backend/tests/test_v102_buyback_unit.py、実物点検 6 で挙げた migration を読むテスト、docs/adr/ADR-1021-bulk-condition-state.md、docs/handoff/g28-bulk-price/design.md、docs/adr/README.md

## 戻し方
PR を revert する。列は NULL 許可で足すだけなので残しても読む処理が無くなるだけ（ADR-1027 の戻し方）。本番で再解析した後なら reanalyze_v102_job でやり直す（Gemini は呼ばない）。

## カードチェック（Opus・2026-10-17）
- 設計 §5-1〜§5-5 の全項目がカードの項目 1〜9 に対応する（§5-4 の表示＝項目 4、§5-5＝項目 5、便1 の注記＝項目 9、守り手4＝項目 7）。
- 正本の重複なし: 単位の語は別名マスタ・判定は v102_bundle_svc 1 か所（台本も import）・商品名の作り方は bundle_title_sql 1 か所・呼び名は line_units。
- 未確認は実物点検 1（別名マスタの受け渡し）と 6（migration を読むテスト）に置き、違えば止まる条件にした。画面のコードは触らない（デザイン部品の追加なし）。

END OF CARD
