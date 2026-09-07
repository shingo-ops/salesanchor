# design — 配信の未完了ガード（便1・止血）

この文書は何か（専門用語なしの1行）: 抽出や解析がまだ終わっていないのに在庫が配信されてしまう事故を、機械で止めるための設計。

親（設計仕様書）へのリンク: ../../specs/product-master/README.md
recon: docs/handoff/tcg-product-master-growth/recon.md
対象ADR: ADR-154

## 1. あるべき姿（PO自筆・情景のまま）

「かいせきが完了する前に配信できないとか」

## 2. KGI

| # | 合格条件 | 測り方 | 合格ライン |
|---|---|---|---|
| K1 | 未完了ジョブがある間、配信が実行されない | extraction_jobs に pending/running/extracted が在る状態で run_distribution を呼び、output_count が 0 で errors に安全装置 #8b の文言が入ることを確認 | 1/1 |
| K2 | 既存の analysis_runs チェックを壊していない | git diff origin/main の削除行数 | 0 |
| K3 | 終端状態のジョブが配信を止めない | status が done/empty/error のみのとき配信が実行されること | 1/1 |
| K4 | 止まった理由が内訳つきで分かる | errors の文言に status 別件数が含まれること | 1/1 |

## 3. KPI

達成KGI数 4/4。

## 4. recon（file:line 実物）

- backend/app/services/tcg_distribution_svc.py:645 既存の安全装置 #8。analysis_runs の completed_at IS NULL を数える。
- backend/app/services/tcg_distribution_svc.py:656 その SQL 本体。
- 実測（2026-09-07・tenant_004・読み取り専用）: analysis_runs の最終 started_at は 2026-09-04 08:38。一方 analysis_results は 2026-09-06 に 1449 行が computed_at を持つ。既存 #8 は更新されない表を見ており、素通りする。
- 実測: extraction_jobs.status は6値。done 371 / pending 58 / error 43 / empty 22 / extracted 9 / running 2。
- 実測: 2026-09-06 の配信は 07:04:26Z に実行され、07:04:34Z 以降に完了したジョブが存在する（4b3f3173 は 147 行）。配信された 451 行に含まれていない。

## 5. design（技術How）

backend/app/services/tcg_distribution_svc.py の run_distribution 内、既存 #8 ブロックの直後・設定ロードの直前に安全装置 #8b を挿入する。

- 判定対象: extraction_jobs.status IN ('pending', 'running', 'extracted')
- 終端扱い: done / empty / error。これらは待っても変化しないため止めない。
- 1件以上あれば output_count 0 で早期リターンし、errors に status 別内訳を含む文言を入れる。
- 既存 #8 は削除も無効化もしない。将来 analysis_runs への書き込みが復活したとき保護が効くよう残す。

触らない範囲: fetch_output_rows のフィルター条件、配信先の書き込み処理、フロントエンド、DBスキーマ。

## 6. 弊害・トレードオフ

- error 43 件を終端扱いにするため、本来解析されるべきジョブが error で沈黙していても配信は通る。エラーの可視化は本便の範囲外。
- pending が常時残る運用になると配信が一度も実行できなくなる。運用で pending を減らす前提。
- 判定が1クエリ増えるぶん、配信の実行がわずかに遅くなる。

## 7. 外部・過去事例

2026-09-04 の NR0136 先行投入（backend/tcg_migration/MIGRATION_LOG.md）。承認前の本番変更が翌日のデプロイ障害として表面化した事例。本便は migration を伴わず、コード1ファイルの追加のみで同型のリスクを避ける。

## 8. 受入基準

| 基準 | 検証方法 |
|---|---|
| 削除行がゼロ | git diff origin/main で削除行を数え、diff ヘッダ以外がないことを確認 |
| 構文が壊れていない | python -c "import ast; ast.parse(...)" が SYNTAX_OK を出す |
| 既存テストが通る | python -m pytest tests/ -k "distribution" が 25 passed |
| #8 と #8b が共存 | grep -n "安全装置 #8" が既存3箇所と新規2箇所を返す |
| 本番反映まで到達 | deploy run の headSha が本PRのマージコミットと一致 |

## 9. 維持の仕組み

守り手: Process Artifacts Gate（本設計文書の存在とPR本文の宣言を機械で強制）

Process Artifacts Gate が本設計文書の存在とPR本文の宣言を守る。安全装置 #8b 自体は run_distribution の内部にあり、配信APIを通るすべての経路に効く。ただし DB を直接操作して配信する経路は本ガードの外側であり、人手で守る。

## 10. 接触面分析

1. 人: 配信ボタンを押す運用者。未完了時に配信できなくなる。事前周知が要る。
2. エージェント: 本文書と recon.md を読む後続セッション。便2・便3の前提となる。
3. 機械: Process Artifacts Gate。既存 CI テストは影響なし（25 passed で実測）。
4. データ: tenant_004 の extraction_jobs を読むのみ。書き込みなし。スキーマ変更なし。
5. 本番: blue-green デプロイ経由で反映。配信が止まる方向の変更であり、データを壊す方向の変更はない。
6. 外部: 配信先スプレッドシートへの書き込み頻度が減る。外部APIの呼び出し自体は変わらない。
