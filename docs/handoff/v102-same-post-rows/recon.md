# recon: 同じ投稿の同じ商品の行（便SP）

基準: origin/main 81f3f5869（2026-10-12 fetch）。本番は読み取りだけ（2026-10-12）。
仕入元の原文は社外秘です。そのため、ここには集計と識別子だけを書きます。原文付きの根拠は手元の /tmp/CC報告ファイル/merge-rule-recon/（recon.md・recon2.md・c5.out ほか）にあります。

## 1. 既存 ADR の検索
- 検索: `git grep -i -l 'is_current\|重複\|統合' origin/main -- docs/adr` と docs/adr/FEATURE-INDEX.md。
- 該当: docs/adr/ADR-158-product-level-supersession.md
  - :21 is_current の追加
  - :26 「旧 analysis_results のうち新メッセージにも存在する product_id の行を is_current=FALSE」
  - :27 配信を ar.is_current=TRUE に
  - :40-42 部分更新の例
- ADR-158 は「メッセージ単位」で新旧を決める。新しいメッセージの行は、残す前提で書かれている。
- v102 と、同じ投稿の中の重複を扱う ADR は無い（`git grep -i v102 origin/main -- docs/adr` は0件）。

## 2. is_current の決め方（今のコード）
- backend/app/services/tcg_analyzer_svc.py:1744 `_merge_supplier_products`
  - 呼び出しは v102 が backend/app/services/line_analysis_v102_svc.py:1204、旧 v6 が backend/app/services/tcg_analyzer_svc.py:1736。
  - 付け直す組は、前の組を backend/app/services/line_analysis_v102_svc.py:1189 `_load_resolved_pairs` から受け取る。
- 鍵の決め方
  - 仕入元の絞り込み: backend/app/services/tcg_analyzer_svc.py:1824 `sm.supplier_channel_id = :channel_id`
  - 並べる単位: :1850 `PARTITION BY c.product_id, c.condition_id`
  - 並べ方: :1851 `ORDER BY c.received_at DESC, c.computed_at DESC, (c.id IS NULL)` で、先頭の1行だけを TRUE にする。
- 同じ投稿の行は received_at が同じで、v102 では computed_at もジョブ内で同じ（実測）。そのため本物の行どうしは同じ順位になり、ROW_NUMBER の結果は決まらない。【事実】2026-10-12 05:20Z の再解析で、表示する行が26行入れ替わった（/tmp/CC報告ファイル/preorder-design/apply/cmp_all.txt）。
- 仮の行（〆の2つ目以降の完売の相手。id は NULL）は :1832-1847 にあり、順位の鍵は親の行と同じ。
- is_current を書くのは :1856 の UPDATE だけ。backend/app/services/v102_transcription_svc.py:85,325 は、削除するときに組を渡して付け直すだけ。
- 一意の制約は無い。migrations/20260924_120000_add_analysis_results_is_current.sql:24-26 にあるのは、部分索引だけ。

## 3. 配信（在庫一覧）
- backend/app/services/tcg_distribution_svc.py:224 `fetch_output_rows` が、:292 `ar.is_current = TRUE` の行をそのまま1行ずつ出す。DISTINCT も GROUP BY も無い。
  - 並び順は :299 `ORDER BY result_order_sql()`（backend/app/services/tcg_result_order.py:20-31）。
  - 出力は13列で、単位の列は無い。
- 呼び出し元
  - backend/app/services/tcg_distribution_svc.py:801（配信の本体。:812 で行数を数える）
  - backend/app/line_import_admin.py:117
- 配信候補の件数: backend/app/services/tcg_distribution_svc.py:354-371（`fetch_preview_data`。条件は配信と同じ）
- 除外の内訳: :374-405
- 在庫一覧 GAS（~/tcg-client-viewer）
  - src/Code.js:60-91 は11列をヘッダー名で取り出す。行をまとめる処理・重複を除く処理は無い。
  - src/index.html:480-491 は、配信の1行を表の1行として出す。

## 4. ランクと括弧の置き場（実物）
- ランク
  - 状態: analysis_results.condition_id / condition_canonical（backend/app/services/line_analysis_v102_svc.py:604 `_condition_columns`）。「状態A-」と「状態B」は、どちらも Damaged sealed box になる。
  - 状態の根拠: analysis_results.condition_basis（backend/app/services/line_analysis_v102_svc.py:670）。Damaged sealed box の行には R2:状態A- が318行、R2:状態B が55行ある。
  - extraction_items の raw_state・raw_memo・raw_unit は、v102 では INSERT しない（backend/app/services/line_analysis_v102_svc.py:483-488）。実測では3,149行すべて NULL。
- 括弧の発送条件: analysis_results.note_ja（backend/app/services/line_analysis_v102_svc.py:673、#4161）。

## 5. 本番の実測
組 = 同じ投稿・同じ product_id・同じ condition_id・同じ unit_canonical の行。対象は v102、product_id あり、is_current は問わない。

| 型 | 組 | 行 | 中身 |
|---|---|---|---|
| N | 46 | 100 | note_ja が互いに違う（発売日発送／発送日要相談 21組 ほか） |
| R | 39 | 78 | note_ja が同じで、condition_basis が互いに違う（39組すべて R2:状態A- と R2:状態B） |
| S | 20 | 41 | note_ja も condition_basis も同じ（下の内訳を参照） |

- S の内訳（原文で確認）。同じ行の重複や取り違えは0組。
  - S-a: 発送の括弧が原文にあるのに、note_ja が両方とも空（6組）
  - S-b: 買取品とポケセン品の違い（3組）
  - S-c: ダメージの程度（小・大）の違い（6組）
  - S-d: 第二版の有無（1組）
  - S-e: 付記語（3組）
  - S-f: 同じ見出しが2回あり、価格と数量が別（1組）
- 設計者が c5.out を集計し直した結果:
  - note_ja が同じ組のうち、condition_basis が組の中で全部違う組は39組で、すべて R だった。
  - 全部同じ組は20組で、すべて S だった。
  - 一部だけ違う組は0組。
- 現在の行の数（組の中で）: N は0行が38組・1行が8組、R は0行が35組・1行が4組。2行以上の組は無い。

## 6. is_current を読むところ（変更の影響先）
- 配信: backend/app/services/tcg_distribution_svc.py:292・:363・:405
- ダッシュボードの件数: backend/app/services/tcg_analysis_dashboard_svc.py:713
- 相場の確認（ほかの投稿の現在の行の中央値）: backend/app/services/v102_unit_price_check_svc.py:62
- 付け直し: backend/app/services/line_analysis_v102_svc.py:967、backend/app/tasks/tcg_extraction.py:826
- 名前が同じだけで別物のもの: backend/app/routers/analytics.py:743 ほか（売上の当月フラグ）
