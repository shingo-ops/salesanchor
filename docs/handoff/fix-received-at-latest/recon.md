# recon: source_messages.received_at が「最古の投稿時刻」になっている問題

- 調査日: 2026-09-29（JST）／基準: origin/main `638cc6f91`
- 本番は読み取り専用で照会した（`SET default_transaction_read_only=on` → `on` を確認、SELECT のみ）
- 起点の調査: `docs/handoff/line-import-missed-0928/recon.md`（PR #3840）§6-2
- 既存ADR・設計の検索: `docs/adr/FEATURE-INDEX.md` →「取り込み / 解析 / パイプライン」→ ADR-100、ADR-154。商品単位の置き換えは `docs/adr/ADR-158-product-level-supersession.md`（Status は Proposed のままだが、実装済み・本番反映済み: PR #3747／#3755／#3763／#3769）。received_at の意味を決めた ADR はない

## 1. 現在のコード（事実）

`backend/app/services/tcg_line_import_svc.py:303-321`（build_provider_entries）
```python
for code, msgs in groups.items():
    # timestamp 昇順ソート → 末尾が最新
    sorted_msgs = sorted(msgs, key=lambda m: m["timestamp"])
    latest_msg = sorted_msgs[-1]
    raw_text = latest_msg["body"]
    received_at = sorted_msgs[0]["timestamp"]          # ← 最古
    canonical_name = sorted_msgs[0]["canonical_name"]
    ...
            "received_at": received_at,
            "line_posted_at": latest_msg["timestamp"], # ← 最新
```
- docstring（同ファイル:289）も「最初の timestamp」
- `_write_source_messages`（同ファイル:423-439）は `entry["received_at"]` を received_at 列に、`entry["line_posted_at"]` を line_posted_at 列に保存する
- 「reused」（既存の行と同じか）の判定は `supplier_channel_id`／`line_posted_at`／`raw_sha256`／`raw_text` で行い、received_at は使わない（同ファイル `_write_source_messages` 内の SELECT）
- 一意インデックス `uq_pub_source_messages_line_identity (supplier_channel_id, line_posted_at, raw_sha256)` にも received_at は入っていない（`migrations/20260921_110000_pipeline_tables_public.sql:26-28`）
- source_messages に書き込むのは `_write_source_messages` の1か所だけ（ほかは実行済みの一回限りの移行スクリプト `scripts/migrate-pipeline-data-to-public.sh:76`）
- Android の経路は全履歴を送る（`backend/app/routers/line_import_devices.py:69` の window_hours 既定値 0、`tools/termux-line-import/client.py:432`）。そのため最古の投稿は数週間前になる
- 導入された時期: コミット 58b6d4418（2026-09-05、最古を入れる実装）→ ca0c4f983（2026-09-05、本文だけ最新に変更）→ aa74625c8（2026-09-10、line_posted_at を追加）

## 2. received_at を使っている箇所（事実）

| 箇所 | 用途 | 今の影響 |
|---|---|---|
| `backend/app/services/tcg_analyzer_svc.py:1757-1792`（`_merge_supplier_products`、ADR-158） | 同じチャネルの中で (product_id, condition_id) ごとに `sm.received_at DESC, ar.computed_at DESC` の1位を is_current=TRUE にする | **新しい投稿が古い投稿に負ける**（配信の対象を誤って選ぶ） |
| `backend/app/services/tcg_analysis_dashboard_svc.py:457` | 仕入元ごとの「最終受信日時」の表示 | 実際より古い日付が出る |
| `backend/app/routers/super_admin_suppliers.py:854`、`backend/app/services/tcg_supplier_quality_svc.py:84` | 「最新原文」を選ぶ（received_at DESC） | 最新でない原文を選ぶおそれがある |
| `backend/app/services/tcg_import_progress.py:160` | 進捗画面に値をそのまま出す | 表示が不正確（並び順は created_at なので影響なし） |
| `backend/app/services/tcg_distribution_svc.py`（max_age_hours） | line_posted_at を使っている | 影響なし（`docs/handoff/fix-distribution-posted-at/recon.md` で line_posted_at に切り替え済み） |

## 3. 文書での意味（事実）
- `docs/handoff/time-handling-ssot/recon.md:106`「received_at はその仕入元の**最後の**メッセージ時刻を表す」→ 実装と逆
- `docs/handoff/fix-distribution-posted-at/recon.md:28` は、received_at を「最古」と認識したうえで変更の対象外とし、配信側だけを line_posted_at に切り替えた
- `docs/handoff/pmg-import-delivery-ssot/design.md:24`「既存 received_at と旧データは変更しない」（line_posted_at 列を追加したときの方針）

## 4. 本番の実測（事実、生出力）

```
 total | null_line_posted_at | mismatch |  lt  | gt
-------+---------------------+----------+------+----
  1554 |                   0 |     1196 | 1196 |  0
```
- 1,554行のうち1,196行で received_at ≠ line_posted_at。すべて received_at のほうが古い。line_posted_at が NULL の行は0件

is_current の再計算を試算した結果（並べ替えを line_posted_at DESC, computed_at DESC にした場合。書き込みはしていない）
```
 true_to_false | false_to_true | unchanged | total_rows      ← pid_resolved かつ product_id あり
          1452 |          1453 |     13620 |      16525
 true_to_false | false_to_true | unchanged | total_rows      ← さらに配信の基本条件（単位・価格・除外）を満たすもの
           962 |          1041 |      8860 |      10863
```
(チャネル, 商品, 状態) ごとの is_current=TRUE の件数
```
 total_partitions | zero_true | one_true | multi_true
             3912 |         1 |     3911 |          0
```
- analysis_results は全体で 22,894 行

実例（`docs/handoff/line-import-missed-0928/recon.md` §6-2）: 平田光希の 2026-09-28 21:36 の投稿（received_at 2026-08-30 12:50）の product 621／125079／125081／440406 が、同じチャネルの 2026-09-24 23:01 の投稿（received_at 2026-09-24 16:58）に負けて is_current=FALSE になっている

## 5. デプロイの順番（事実）
`.github/workflows/deploy.yml:160`「Deploy to VPS」で backend と celery-worker を再起動したあとに、`.github/workflows/deploy.yml:441`「Run database migrations」（`scripts/run_all_migrations.sh`）が実行される。**新しいコードが先に起動し、マイグレーションはそのあと**

## 6. テスト（事実）
- `backend/tests/test_tcg_line_import.py:347-364`（`test_build_timestamp_ascending_order`）は `received_at == "2026-08-01 10:00:00"`（最古）を期待している → 修正すると失敗する
- 必須のCIチェック: `pytest (SQLite + PostgreSQL RLS)`（`.github/workflows/test.yml`）。PG統合テストは `RLS_ADMIN_DATABASE_URL` を使う（例: `backend/tests/test_tcg_distribution_pg.py`）

## 6-2. 配信への実際の影響（2026-09-29 追加照会、事実）
- 配信のSQLは、origin/main の `source_cte()`／`review_joins()`（`backend/app/services/tcg_condition_review_svc.py:41-54`、`:108-179`）で生成した文字列をそのまま、本番に読み取り専用で流して再現した（`backend/app/services/tcg_distribution_svc.py:188-263`）
- 本番の設定: `tcg_distribution_settings.max_age_hours = 48`（`backend/app/services/tcg_distribution_svc.py:751`）。有効な配信先は3件。仕入元ごとの絞り込みはない
- **現在の配信: 249行**。平田光希（supplier_id 25505）は **0行**
  - is_current=TRUE になっているのは 2026-09-24 23:01 の投稿の行だけで、48時間の絞り込みで外れている。2026-09-28 21:36 の投稿（received_at 2026-08-30 12:50）は is_current=FALSE
- **修正を再現した場合（design.md §5 と同じ並べ替え）: 852行**
  - 新しく出る: 607件（例: 伊石侑生 product 125081 ¥65,000、2026-09-28 20:04 の投稿）
  - 消える: 4件（たいき 5／14／440570、kaishi 440569。どれも 2026-09-27 の投稿。消える理由は未確認）
  - 価格が変わる: 5件
  - 平田光希: 0行 → 4行（621 ¥8,000／125079 ¥19,000／125081 ¥96,000／440406 ¥28,000。すべて 2026-09-28 21:36 の投稿）
- 仕入元ごとの MAX(received_at) と MAX(line_posted_at)（JST）の比較: oyama 09-24 14:02／09-28 21:03、ヒロト 09-24 10:21／09-29 01:11、もと 09-24 14:52／09-28 22:03、やまざきけんと 09-23 13:01／09-28 22:24、平田光希 09-24 16:58／09-28 23:15
- 「最終受信日時」（`backend/app/services/tcg_analysis_dashboard_svc.py:457`）は、frontend に型定義（`frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:68`）があるだけで、画面に表示している箇所は grep では見つからなかった（未確認）
- source_messages で最も古い行の created_at は 2026-09-10 11:49 JST。9/10 以降、どの日にもずれがある（日によっては全件）。9/10 より前は、テーブルにデータがないため確かめられない
- TRUE が0件のグループ: もと（チャネル 1cba1d0a…）の product 36、condition 14。行は1行だけで、is_current=FALSE（2026-09-25 15:30 の投稿）。原因は未確認

## 6-3. 修正で「消える4件」と「価格が変わる5件」の内訳（2026-09-29 追加照会、事実）
生出力: scratchpad partitions_result.txt（照会文 main_partitions.sql は origin/main の review_joins から生成）
| 行 | 修正後に選ばれる行 | 配信されない理由 | 最新の投稿の本文 |
|---|---|---|---|
| たいき product 5（OP-15） | 09-27 10:47 の投稿 | 価格なし（price_unresolved） | 「OP-14 BOX / OP-15 BOX / OP-16 BOX 〆」 |
| たいき product 14（OP-14） | 同じ投稿 | 価格なし | 同じ本文 |
| たいき product 440570（OP-16） | 同じ投稿 | Sold out／excluded（raw_memo='〆' は OP-16 の行にだけ付いた） | 同じ本文 |
| kaishi product 440569 | 09-27 12:07 の投稿 | 価格なし | 「ストームエメラルダ / 残り31BOX / 30th / 〆」 |
- 4件とも、より新しい投稿が「現在の情報」になるが、その投稿に価格がないため配信されない。今は、受信時刻の誤りのせいで古いほうの価格付きの行が選ばれていて、配信されている
- 価格が変わる5件:
  - 株式会社N&U 458213: 13,300（09-27）→ 13,000（09-28 11:10）。最新の投稿の本文「13000@30」と一致
  - yusuke 227（condition 13）: 同じ投稿の中の「ダメージ(小) ¥173,000」と「ダメージ(大) ¥170,000」が、同じ condition_id と同じ computed_at で並んでいる。並べ替えで1行に決まらない（今のコードも、design §5 も同じ）
  - 斉藤・倉田 和博 440425: 「フクオカ」「ヒロシマ」「トウホク」などの別の商品が、すべて product 440425（ポケモンセンターカナザワオープン記念）に結び付けられている。同じ時刻で並んでいて、1行に決まらない
  - たいき 18: この照会では、修正の前後で選ばれる行が同じ（¥19,000）で、価格は変わらなかった。前回の集計（6-2）と食い違っている（未確認）
- 照会担当の報告には「`fetch_output_rows` に48時間の絞り込みはない」という記述があったが、誤り。`backend/app/services/tcg_distribution_svc.py:214-221` で `age_condition` として付けている。この照会は行ごとの比較なので、結論には影響しない

## 7. 未確認
- (チャネル, 商品, 状態) で TRUE が0件の1件について、原因は調べていない
- 本番の定期バックアップの有無と、直近の取得時刻
