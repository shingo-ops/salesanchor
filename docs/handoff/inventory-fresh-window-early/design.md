# design: 在庫表「24時間以内」の絞り込みを配信行の計算の内側へ移す（在庫表の高速化 便2）

recon: docs/handoff/inventory-fresh-window-early/recon.md ／ 関連 ADR: ADR-1014（改訂を足す）

## 目的（PO の言葉）
在庫表のタブを開いたとき早く開くようにする（PO 2026-10-18）。便2は表のデータを取る時間を約1.3秒→約0.8秒にする。
PO 決定 2026-10-18「y」: 「24時間以内」ON のとき、絞り込みの選択肢（仕入元・カテゴリ・状態・形態）を24時間以内の在庫にあるものだけに絞ってよい。

## 変更前 → 変更後
- 変更前: dist_base は 48h などの年齢窓（`max_age_hours`）で全行を重く計算し、そのあと rows_f で `d.posted_ts >= NOW() - 24h` を絞る（`backend/app/routers/inventory_offers.py:258`）
- 変更後: fresh_only=true のときは年齢窓そのものを24hにする。`backend/app/routers/inventory_offers.py:374` を次の形にする（新しい SQL 文字列を足さない。窓の SQL は `_age_window` の1か所のまま）
  ```python
  window_hours = max_age_hours
  if fresh_only:  # 「24時間以内」は配信行の計算の内側で絞る（便2・ADR-1014 改訂 2026-10-18（3））
      window_hours = FRESH_WINDOW_HOURS if max_age_hours is None else min(max_age_hours, FRESH_WINDOW_HOURS)
  age_condition, age_params = _age_window(window_hours)
  ```
  （`max_age_hours` の型と None の可否は実装時に実物で確認し、None を取らないなら None 分岐を書かない）
  - 実装時の確認結果（2026-10-18）: 変更箇所では None を取らない（`backend/app/routers/inventory_offers.py:367` で先に return）。0 は `_age_window` で「絞らない」の意味（`backend/app/services/tcg_distribution_svc.py:217`）なので、`min(max_age_hours, FRESH_WINDOW_HOURS) if max_age_hours else FRESH_WINDOW_HOURS`（0 のときは24）とする。Opus 確認済み
- `_build_view_filters` から fresh_only の条件（`backend/app/routers/inventory_offers.py:258` から3行）と引数を外す。呼び出し `backend/app/routers/inventory_offers.py:376` も合わせる。条件を二重に持たない（定義1か所）

## 触らない範囲
- `distribution_rows_parts` の引数・本文、`_age_window`、`FRESH_WINDOW_HOURS`（配信プレビュー・閲覧ページ・原文の経路に影響を出さない）
- 画面（frontend）・migration・tasks・deploy.yml
- fresh_only=false のときの SQL（変更前と同じ文字列であること）

## 等しさの根拠（recon「変わるもの・変わらないもの」）
並び・まとめ・件数・ページは不変。絞り込み候補だけが24h内に縮む。前提は「rows_f の `d.posted_ts` が dist_base の `sm.line_posted_at` と同じ値」であること。確認済み（2026-10-18）: dist_base の `sm.line_posted_at AS posted_ts`（`backend/app/services/tcg_distribution_svc.py:321`）が rows_f の d.posted_ts と同じ列。

## 受入条件
|基準|検証方法|
|---|---|
|K1 本番データで、新旧の1文の page 行（50行・順番含む）と total が一致する（fresh_only=true、まとめ OFF / ON の2通り）|reader で新旧 SQL を実行し、行を比べた結果をファイルに残す|
|K2 新しい facet は旧 facet の部分集合で、24h 内の行の値と一致する|同上|
|K3 新 SQL の時間（中央値）が 1,000ms 以下、かつ旧より短い|reader で新旧を交互に各5回|
|K4 fresh_only=false の SQL 文字列が変更前と同一|単体試験|
|K5 試験更新後の pytest（影響する6試験含む）・ruff が通り、CI が緑|ローカル実行＋PR の CI|
|K6 本番反映後、/api/v1/inventory の応答時間の中央値が反映前（7日 約1.9秒）より下がる|Prometheus（反映後に数時間分を観測）|

## 試験の更新
recon「影響する試験」の6本。facet の試験は「fresh_only=true のとき facet は24h内の値だけ」「fresh_only=false では従来どおり絞り込みの影響を受けない」に改める。

## ADR
ADR-1014 に「改訂 2026-10-18（3）」を追記: 「24時間以内」ON のときは年齢窓自体を24hにし、絞り込み候補も24h内の在庫の値だけになる（PO 決定 2026-10-18）。前の改訂節は書き換えない。`node scripts/generate-adr-index.js` を実行する。

## 代替案
- 作り置き（viewer の Redis）を流用: 審査2本で却下済み（列不足・まとめ行・古さ）
- ROW_NUMBER を外す: 約950ms だが並びの決着が変わりうる。便2では行わない
- facet を旧のまま別に計算: 重い計算が2回になり速くならない

## リスクと対処
- 24h 前後ぴったりの行の扱い: 新旧とも `NOW() - 24h` 以上で同じ比較。実行時刻の違いでずれる分は K1 で同時刻実行して比べる
- 戻し方: 本 PR を revert（DB 変更なし）

## 外部・過去事例の参照と我々への応用
- 該当なし：今回は SQL の絞り込みを重い計算より前に置く一般的な最適化で、効果は外部事例ではなく本番 reader の実測（recon の 1,319→801ms、measure2.md の中央値 1418→501ms）を根拠にするため、外部事例の参照は不要と判断

## 維持の仕組み
守り手: `backend/tests/test_inventory_distribution_rows.py`（fresh_only の窓が年齢窓に入ることと false 時の SQL 不変を固定）、`backend/tests/test_inventory_distribution_rows_pg.py`（新旧の結果の等しさと facet の振る舞いを固定）
