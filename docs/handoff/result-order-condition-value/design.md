# 設計: 同じ商品の中の並びを「状態の価値の高い順」にする（並び順の正本1か所を状態マスタの価値の順位へ）

- recon: docs/handoff/result-order-condition-value/recon.md
- 対象ADR: docs/adr/ADR-1023-condition-value-rank.md（改訂: value_rank を並び順にも使う）、ADR-1021（Bulk の位置）、ADR-1014（在庫表の最終キー sort_ord）

## PO の言葉
- 「同じ商品内では価値の高い順に並べてほしい」（2026-10-18）
- Opus「価値＝状態の価値の順（ADR-1023）と読んでよいか。同じ状態の中は今の安い順のまま」→ PO「y」
- Opus「解析の結果画面・取込進捗の一覧・GAS 在庫一覧へ送るデータの順も同じく価値順に変わってよいか」→ PO「y」（2026-10-18）

## 目的（利用者に見える変化）
在庫表・閲覧ページ・LINE解析の結果画面・取込進捗の一覧・GAS 在庫一覧で、同じ商品の行が状態の価値の高い順に並ぶ。
- カートン: Case → Damaged case → Opened case
- ボックス: Sealed box → Damaged sealed box → No shrink box → Opened box → Searched box
- パック: Unsearched pack → Searched pack → AR confirmed pack
- 群の順はカートン → ボックス → パック（今の固定表と同じ）。順位の無い状態は最後で、Bulk を先頭に、残りは文字順（今と同じ）
- 同じ状態の中は今のまま安い順

## 変更前 → 変更後
- 変更前: backend/app/services/tcg_result_order.py の固定の表 RESULT_CONDITION_ORDER（9値）の CASE。表に無い Opened case・Searched box・AR confirmed pack は Bulk より後ろ
- 変更後: 状態の位置を、状態マスタ（public.conditions＝public.line_conditions の view）の value_group / value_rank から引く。値の正本は状態マスタの1か所で、コードには群の順（case, box, pack）と Bulk の特例だけを置く

## 実装指示（Generator 向け）
1. backend/app/services/tcg_result_order.py
   - RESULT_CONDITION_ORDER の表を廃止し、群の順の定数 `VALUE_GROUP_ORDER = ("case", "box", "pack")` と、順位の無い状態の先頭に置く `UNRANKED_FIRST = "Bulk"` を置く
   - result_order_sql の状態の部分を、状態マスタを引く相関副問い合わせ1つで作る（呼び出し元3か所の SQL・JOIN は変えない）:
     ```
     COALESCE((
       SELECT (CASE lc.value_group WHEN 'case' THEN 0 WHEN 'box' THEN 1 WHEN 'pack' THEN 2 END) * 1000 + lc.value_rank
       FROM public.conditions lc
       WHERE lc.canonical = cr.canonical AND lc.value_group IS NOT NULL AND lc.value_rank IS NOT NULL
       ORDER BY lc.id LIMIT 1
     ), 9000 + CASE WHEN cr.canonical = 'Bulk' THEN 0 ELSE 1 END)
     ```
     の後に、今と同じ `cr.canonical COLLATE "C" ASC NULLS LAST, ar.price_normalized ASC NULLS LAST, ei.id ASC`。先頭の `p.release_date DESC NULLS LAST, p.id ASC NULLS LAST` も今のまま
     - 群の CASE 式は VALUE_GROUP_ORDER から組み立てる（文字列は定数由来のみ。利用者入力なし）
     - ORDER BY lc.id LIMIT 1 は canonical の重複があっても行が増えないための保険（本番は重複なし、recon）
   - 未確認だった canonical の UNIQUE 制約と、副問い合わせの schema（配信の fenced 版でも public.conditions を引けるか）を実装時に確かめ、報告に書く
2. 試験
   - backend/tests/test_tcg_result_order.py: 試験用 DB の状態マスタへ value_group / value_rank を試験内で入れて（本番の値と同じ11行）期待値を作る。:67 の8状態の順は変わらない。Opened case・Searched box・AR confirmed pack がそれぞれの群の最後に来ること、価値の順位が空の DB では Bulk → 文字順になることを足す。:359-363 は新しい定数・SQL に合わせて書き直す
   - backend/tests/test_inventory_distribution_rows.py の `_GOLDEN`（4通り）を再生成し、コメントに理由を書く
   - backend/tests/test_inventory_distribution_rows_pg.py ほか sort_ord を使う試験は、期待が変わるものだけ直す（全走査して一覧で報告）
3. docs/adr/ADR-1023-condition-value-rank.md に「改訂 2026-10-18」節を足す（value_rank を、v102 の判定に加えて並び順の正本としても使う。群の順・Bulk の特例・影響する画面）。`node scripts/generate-adr-index.js` を実行

## 触らない範囲
- 状態マスタの値（読むだけ。書き換えない）、v102 の判定（_resolve_condition）、review_joins と呼び出し元3か所の SQL、配信行の列・GAS 出力14列、在庫表の ORDER BY（別便 release/inventory-sort-release-date-groups）、画面のコード、DB の構造・migrations

## 代替案
- A. 固定の表 RESULT_CONDITION_ORDER に3値を書き足す: 価値の順位が状態マスタとコードの2か所に分かれ、マスタを直しても並びが変わらないので不採用（データの分散を避ける）
- B. 呼び出し元3か所の SQL に状態マスタの JOIN を足す: 3か所の変更と配信 SQL の再試験が要るので不採用。副問い合わせなら result_order_sql の1か所で済む

## リスクと対処
- 状態マスタに値が無い環境では、全状態が「順位なし」になり Bulk → 文字順で並ぶ（壊れはしない）。本番は値あり（recon）。試験で両方の場合を固定する
- 配信行の重い計算に相関副問い合わせが加わる。状態マスタは16行で、1行あたり主キー以外の検索1回。CI の実 PG 試験（4097行のページ境界 :183）の所要時間を変更前後で記録して報告し、2倍を超えたら停止して Opus へ
- 解析の結果画面のページの切れ目が変わる（同じ商品の中の順が変わるため）。PO 承認済みの影響

## 受入条件
| 基準 | 検証方法 |
|---|---|
| 同じ商品の中が群（カートン→ボックス→パック）→価値の順位→（順位なしは Bulk→文字順）→安い順 | test_tcg_result_order.py（実 PG・CI）pass |
| 状態マスタに値が無いときも並びが壊れない | 同上の追加試験 pass |
| 配信 SQL の固定値の更新 | test_inventory_distribution_rows.py pass（_GOLDEN 再生成） |
| 型・lint | ruff・pytest（変更関連）pass |
| ADR 索引 | CI「ADR index is up to date」pass |
| 処理時間 | CI の :183 試験の所要時間が変更前の2倍以内（担当報告に前後の値） |
| 本番反映 | デプロイ success。本番の配信行の並びを ADR-1024 の読み取りで1商品分（複数状態を持つもの）確認し、価値順になっていること。画面は PO 目視 |

## 外部・過去事例の参照と我々への応用
- 過去事例（社内）: ADR-1021 で Bulk を足したとき、固定の表 RESULT_CONDITION_ORDER と _GOLDEN の再生成が要った（test_inventory_distribution_rows.py:190 のコメント）。状態を足すたびにコードの表を直す運用をやめ、状態マスタの値だけで並びが決まるようにする
- 過去事例（社内）: ADR-1023 で value_rank を状態マスタに持たせ、本番に値を入れ済み（11状態）。同じ値を並びの正本に使い、2つ目の表を作らない
- 外部事例: 使わない。理由: 並びの順は PO の決定と状態マスタが正本で、外部の数値根拠で決める性質のものではないため

## 維持の仕組み
- 守り手: test_tcg_result_order.py（実 PG・CI 毎回）が群の順・価値の順位・順位なしの扱いを固定する。価値の順位の正本は状態マスタ（public.line_conditions の value_group / value_rank）で、変更は ADR-1023 の手順（記録した SQL）で行う

## 追補1（2026-10-18・実装前の調査結果による）
- 事実（担当調査 /tmp/CC報告ファイル/inventory-value-order/impl/fixture_survey.txt）: 実 PG 試験の DB は migrations/20260919_020000_master_ssot_public_tables.sql だけで public.conditions を作り、value_group / value_rank 列が無い（列を足す migrations/20261017_120000_line_conditions_value_rank.sql は public.line_conditions が BASE TABLE のときだけ動くため、試験 DB では何もしない）。本番には列がある。設計どおりの列参照だと、result_order_sql を通る実 PG 試験（約40ファイル）が「列が無い」で失敗する
- 決定: 試験 DB を本番の形に合わせる。backend/tests/ に試験用の小さな helper を1つ新設し、本番 migration と同じ型・制約（value_group TEXT CHECK IN ('box','case','pack')、value_rank INTEGER CHECK >= 1）で public.conditions へ2列を足す。20260919 の読み込み直後に、次の4つの fixture の根から呼ぶ
  - backend/tests/test_tcg_work_matching_integration.py:292
  - backend/tests/test_tcg_condition_review.py:77
  - backend/tests/test_tcg_distribution_pg.py:82
  - backend/tests/test_tcg_import_progress_pg.py:77
- 不採用: (A) SQL を to_jsonb(lc)->>'value_group' で引く。列名が文字列になり、試験 DB と本番の形の違いを隠すため。(B-2) 4ファイルへの直書き。同じ SQL が4か所に分かれるため。(C) migrations の変更。触らない範囲で、本番の適用順を崩すため
- 触る範囲の追加: 上記の試験5ファイル（既存4＋新規1）。製品コードと migrations の範囲は変えない
- 値: helper は列を足したあと、本番と同じ11状態の値（recon の表）を canonical で UPDATE する（試験 DB に該当行がある場合だけ当たる。行を新たに作らない）。試験がその後に状態の行を自分で INSERT する場合は、その行は値なし（順位なし）になる。試験 DB を本番の値に揃えることで、既存の8状態の順（:67）を変えずに済む見込み。期待が変わる試験は担当が全走査して一覧で報告し、5ファイルを超えて期待を直す必要が出たら停止して Opus へ
- 状態マスタに値が無い場合の扱い（Bulk→文字順）は test_tcg_result_order.py の中で値を NULL に戻して確かめる

## 追補2（2026-10-18・CI 失敗の修正による）
- 事実（担当調査 /tmp/CC報告ファイル/inventory-value-order/fix1/）: CI run 39055281510 の pytest-run-internal が 15分の上限でキャンセルされた。原因として確定したもの3つ
  - 試験 DB の public.conditions に match_type / effect 列が無く、value_rank 列があると backend/app/services/tcg_analyzer_svc.py:663-697 が両列も読む版へ分岐して失敗した（本番は両列あり）
  - 新規試験2件の期待値に、配信に出ない Empty box が含まれていた
  - 行ごとの相関副問い合わせで、4097行の試験の EXPLAIN ANALYZE 合計が変更前の約2.2倍（ローカル 10510 ms → 22962 ms）になり、設計の停止条件（2倍）を超えた
- 決定:
  - helper に match_type TEXT NOT NULL DEFAULT 'KEYWORD'、effect TEXT NOT NULL DEFAULT 'OUTPUT' を足す（migrations/20260925_010000_conditions_add_match_type.sql と同じ型・既定値）
  - result_order_sql の状態の位置は、public.conditions を jsonb_object_agg(canonical, 位置 ORDER BY lc.id DESC) で1回だけ集計し（InitPlan）、行側は ->> cr.canonical で引く。canonical が重複したら id の小さい方が勝つ（旧案の ORDER BY lc.id LIMIT 1 と同じ規則）。並びの意味は変えない
  - 試験の期待値から Empty box を除く
- 処理時間（同じローカル機・単発）: 変更前 10510 ms / 旧案 22962 ms / 本案 12427 ms（約1.18倍で停止条件内）。CI での値は CI 完了後に記録する
- 範囲: 触るファイルは既存の11ファイルの中だけ。migrations・他の製品コード・CI 設定は変えない
