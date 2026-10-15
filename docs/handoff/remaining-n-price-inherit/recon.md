# recon — remaining-n-price-inherit（価格なし・数ありの行に前の価格を引き継ぐ）

**仕事名**: remaining-n-price-inherit
**日付**: 2026-10-15
**対象ADR**: ADR-158（参照。Status Proposed）・ADR-1014・ADR-113・ADR-1015
**担当**: 文書担当（設計は Opus、PO 承認は設計のみ）
**測った版**: 実測 HEAD 803d7c58a（origin/main）。設計の基準は 61d69bd1f。基準から実測 HEAD までに、下の表の対象ファイル（サービス6本・関連試験・line-analysis-tuning の README・ADR-158）の差分は 0（`git diff --stat` が空）。よって下の file:line はそのまま有効。

---

## ADR 検索結果（着手前）

- `git grep -i docs/adr/` で price_basis・price_normalized は 0 件。is_current は ADR-158 のみ。「価格なし」は ADR-100 の一覧語のみ。`docs/adr/FEATURE-INDEX.md` は 残り・price・is_current・引き継・価格・完売・〆 のすべてで 0 件。
- 関連として参照する ADR: ADR-158（商品の部分更新の趣旨）、ADR-1014（在庫表は配信行を表示）、ADR-113（handoff 様式）、ADR-1015（変更区分）、ADR-1003（GO の委任）。
- ADR と実装の食い違い: ADR-158 は Proposed。本件は ADR を変えない。

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/services/line_analysis_v102_svc.py:942` | 保存ループ `for index, (item, row) in enumerate(pairs):` の開始。差し込み位置の直前 |
| `backend/app/services/line_analysis_v102_svc.py:943` | `values = _apply_soldout_targets(` の開始（:943-947 が values の組み立て） |
| `backend/app/services/line_analysis_v102_svc.py:948` | `result_id = session.execute(` の開始。UPSERT の直前 |
| `backend/app/services/line_analysis_v102_svc.py:941` | `mismatches = _unit_price_mismatches(...)`（相場検査。引き継いだ価格は検査に入れない） |
| `backend/app/services/line_analysis_v102_svc.py:1210` | `_write_results` の呼び出し |
| `backend/app/services/line_analysis_v102_svc.py:1211` | commit |
| `backend/app/services/line_analysis_v102_svc.py:1219` | `_merge_supplier_products` の呼び出し |
| `backend/app/services/line_analysis_v102_svc.py:690` | price_basis は `V102:<basis>` か NULL |
| `backend/app/services/line_analysis_v102_svc.py:110` | `_PRICE_BASIS_MAX = 100` |
| `backend/app/services/line_analysis_v102_svc.py:105` | `STATUS_SOLD_OUT = "Sold out"` |
| `backend/app/services/line_analysis_v102_svc.py:62` | `from app.services.v102_human_decisions_svc import Decisions, load_v102_decisions` |
| `backend/app/services/line_analysis_v102_svc.py:882` | `_buyback_units`（SAVEPOINT＋try/except の既存の型。:882-890） |
| `backend/app/services/line_analysis_v102_svc.py:893` | `_unit_price_mismatches`（同上の型。:893-910） |
| `backend/app/services/line_analysis_v102_svc.py:1004` | `_FOLLOWUP_CURRENT_SQL`（job id から supplier_channel_id と line_posted_at を引く。:1004-1008） |
| `backend/app/services/line_analysis_v102_svc.py:1041` | `SOLDOUT_REF_MAX_GAP_SECONDS = 172800`（48時間。流用する） |
| `backend/app/services/line_analysis_v102_svc.py:1052` | `load_soldout_ref_posts`（今の投稿より前・48時間以内の測り方。:1052-1069） |
| `backend/app/services/line_analysis_v102_svc.py:1072` | `_STOCK_ITEMS_SQL`（各投稿の最新 job だけを読む型。:1072-1084） |
| `backend/app/services/v102_human_decisions_svc.py:35` | `FIELD_V102_PRICE = "v102_price"` |
| `backend/app/services/v102_human_decisions_svc.py:49` | `_CORRECTIONS_SQL`（item_corrections の最新行の読み方。:49-54） |
| `backend/app/services/v102_human_decisions_svc.py:75` | `Decisions`（product_id・condition_id・ack_codes のみ。価格の判断は持たない。:75-85） |
| `backend/app/services/v102_transcription_svc.py:302` | 人が価格を直すと `v102_price` の行に human_value が入る。空にすると空文字 |
| `backend/app/services/v102_transcription_svc.py:278` | `_blank_to_none`（空の価格は None にそろえる） |
| `backend/app/services/tcg_analyzer_svc.py:1955` | `_merge_supplier_products` の SQL（価格を見ず最新 job を is_current=TRUE にする。:1955-1981） |
| `backend/app/services/tcg_analyzer_svc.py:1927` | `_merge` は received_at 基準（:1927・:1958・:1968） |
| `backend/app/services/tcg_distribution_svc.py:224` | 配信の窓は `sm.line_posted_at`（`_age_window`。:216-226） |
| `backend/app/services/tcg_distribution_svc.py:335` | 配信 SQL `cr.needs_review IS FALSE` |
| `backend/app/services/tcg_distribution_svc.py:338` | 配信 SQL `ar.price_normalized IS NOT NULL` |
| `backend/app/services/tcg_condition_review_svc.py:233` | price NULL に `price_unresolved` を付ける |
| `backend/app/services/tcg_condition_review_svc.py:240` | 価格があれば `price_unresolved` を外す |
| `backend/app/services/v102_unit_price_check_svc.py:54` | 相場検査の読み取り `_MARKET_SQL`（is_current の行だけを相場にする） |
| `backend/app/services/tcg_analysis_dashboard_svc.py:471` | ダッシュボードの `price_ok` は `price_normalized IS NOT NULL` の件数 |
| `backend/tests/test_line_analysis_v102_svc.py:475` | `_FakeSession`（execute は fetchall と scalar_one のみ） |
| `backend/tests/test_inventory_distribution_rows_pg.py:50` | `_add_job`（supplier_channels の先頭1件を使う） |
| `backend/tests/test_inventory_distribution_rows_pg.py:63` | `_add_row` |
| `backend/tests/test_inventory_distribution_rows_pg.py:83` | `_rows`（配信 SQL の結果を読む） |
| `backend/tests/test_line_analysis_v102_pg.py:198` | `run_v102_pipeline` を差し替えて product_id などを差し込む型（:198-220 付近） |
| `migrations/20261011_150000_add_analysis_results_price_basis.sql:2` | price_basis は VARCHAR(100)。`INHERIT:<uuid>` は 44 字で収まる |
| `docs/specs/line-analysis-tuning/README.md:41` | price_basis の表の行（今の値は V102:yen_free と NULL のみ）。実装 PR で1行足す |
| `docs/adr/ADR-158-product-level-supersession.md:35` | 「商品の部分更新」（旧の他商品は継続）。実装は (product_id, condition_id) 単位 |
| `docs/handoff/distribution-age-window/card-AGE.md:11` | 配信の max_age_hours は文書上 48 |

## 現状の流れ（事実）

1. 解析の保存（:942 のループ）は、価格が無い行も `price_normalized = NULL` で保存する。
2. 保存後、`_merge_supplier_products`（:1219）は価格を見ずに、同じ (商品, 状態) の最新 job の行を is_current=TRUE にする。
3. 配信は `price_normalized IS NOT NULL`（:338）と `needs_review IS FALSE`（:335）の両方を要る。価格が NULL の行は `price_unresolved` が付いて（:233）二重に落ちる。
4. よって「残りN個」のように数だけ書かれた投稿が最新になると、その (商品, 状態) は在庫表・GAS・配信から消える。
5. price_basis は書く側以外のどこも参照しない（配信・要確認・ダッシュボードとも）。

## 本番の実測（全体件数のみ。2026-10-15 読み取り）

| 項目 | 件数 |
|---|---|
| 30日（JST 2026-09-15〜10-15）の v102 の行 | 7,208 |
| うち 商品特定済み・価格なし・数あり | 13（0.18%） |
| うち 完売扱い | 0 |
| うち 現在値になっている（いま消えている組） | 5 |
| うち 前の価格がある | 10 |
| 前の価格ありの 10 行の経過時間 | 0.4〜101.5 時間（48時間以内 8、超過 2） |

いま消えている 5 組の内訳: 引き継ぎで直る 1／価格が原文にあるのに読めていない 3（別テーマ）／前の価格が無い 1。

限界: 「残り」の判定は raw_quantity と raw_price のみ。商品名側の「残り」は数えていない。期間は30日。

## 既存試験の型

- 単体: `backend/tests/test_line_analysis_v102_svc.py:475` の `_FakeSession` は execute が fetchall と scalar_one だけを持つ。読み取りを begin_nested の中に入れれば、例外は握りつぶされ値は変わらない。
- PG: `backend/tests/test_inventory_distribution_rows_pg.py:50` の `_add_job`・`_add_row`・`_rows` の型。`pg` fixture は GITHUB_ACTIONS が true のときだけ動く＝ローカルでは skip（CI でのみ実行）。
- `_add_row` は price_basis と is_current の列を INSERT しない（is_current は既定 TRUE）。INHERIT 行や非 current 行を作るには UPDATE が要る。
- 別チャンネルの fixture は既存に無い（`_add_job` はいつも supplier_channels の先頭1件）。

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | 本番の配信の max_age_hours の現在値 | 文書上は 48（`docs/handoff/distribution-age-window/card-AGE.md:11`）。コード側に既定なし（未設定なら配信しない。`backend/app/services/tcg_distribution_svc.py:197-209`） | 【未確認】合格を妨げない |
| 2 | received_at と line_posted_at がずれる件数 | 本番の読み取りで数える | 【未確認】ずれる件は対象外 |
| 3 | GAS 本体が価格空行をどう扱うか | 今回は価格が入るので影響なし | 【未確認】合格を妨げない |
| 4 | max_age_hours が 48 のとき、引き継いだ価格の元投稿は最大96時間前になりうる | 設計で許容（元は新しい投稿の48時間以内）。本番で運用し PO が見直す | 【未確認】本番の実際の件数 |
| 5 | 試験用の tenant スキーマ版 supplier_channels の NOT NULL 列 | 実装時に fixture 作成で確認 | 【未確認】 |
| 6 | 引き継ぎで相場検査の対象行が増えるか | 同じ (商品, 状態) の旧行は is_current=FALSE になる。試験で確認 | 【推測】試験で確かめる |

**未解決ゼロ確認**: 【未確認】の 1〜5 と【推測】の 6 は合格を妨げない（design.md 7章に再掲）。

## 補足

- 社外秘の仕入元別の内訳・投稿原文はこの文書に載せない。
