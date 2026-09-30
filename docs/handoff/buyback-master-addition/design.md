# Design: buyback-master-addition（マスタ追加前の影響試運転スクリプト）

- recon: docs/handoff/buyback-master-addition/recon.md
- 区分: 既存の延長（読み取り専用ツールの新設。本番コード・migration・deploy・CI は触らない）

## PO 方針（原文）
「昔の商品を登録する、マスタはSSOTさせたいので、ただし追加する前に解析の影響の有無を調査して確実に不具合を起こさないエビデンスを確立したものからリストを追加していく」

## ADR・設計との相互参照
- ADR-157（docs/adr/ADR-157-buyback-price-logger.md）— 買取の商品マッチャーは LINE 解析と同じ `public.products` と同じ照合関数を使う（recon §A）。マスタ追加は買取側にも効く。買取側の効果確認（関門4）は登録便で行い、本 PR は解析側の安全確認のみ。
- ADR-154 キーワード品質（docs/handoff/tcg-keyword-quality/design.md）— 関門1のワード重複判定は R3 と同じ正規化（`collapse_product_spaces(normalize_en(kw))`）を使う。照合ロジックは変えず、既存の純関数を呼ぶだけ。
- gemini-extract-role-split（docs/handoff/gemini-extract-role-split/design.md）— 新解析（Gemini は書き写しのみ、判定はシステム）。判定関数 `match_product` を新系統として試運転する。

## 何を作るか（1ファイル＋テスト）
- backend/scripts/replay_master_addition.py（新規）
- backend/tests/test_replay_master_addition.py（新規）
- docs/handoff/buyback-master-addition/recon.md・design.md（新規）

## 入出力
- 入力: 商品マスタ CSV と同じ形式（`tcg_product_import_svc.parse_rows`）。`--days`（既定 90）、`--out`（省略時は標準出力）。
- 出力: JSON。旧解析（legacy）と新解析（new）を分けて報告する。いずれかの関門件数が 0 でなければ終了コード 1。
- DB: `SET TRANSACTION READ ONLY` → `SET LOCAL app.is_operator='true'` → `SHOW transaction_read_only` が on であることを確認 → 最後に rollback。書き込み文は無い。

## 関門と対象システム

| 関門 | legacy（match_pid_with_work） | new（match_product） |
|---|---|---|
| 1 書き方の点検 | 共通: 候補の work_id が NULL／有効作品でない件数、検索語が既存商品の語と一致・被包含・包含する件数、CSV ファイルエラー件数 | 同左（共通） |
| 2 過去の解き直し | 過去 N 日の extraction_items を前後で解き直し、結果（product_id・pid_resolved・候補集合）が変わった件数と明細 | (a) extraction_shadow_results の全ブロック（マスタ整備前に作られたもの）と (b) 過去 N 日の原文ブロックを別々に報告。status 遷移（matched/ambiguous/unmatched）または product_id の変化を変化として数える |
| 3 過去の原文に出たか | 過去 N 日の原文で、候補の名前・型番・検索語が旧解析の規則（normalize_en）で当たる原文の件数 | 同・新解析の規則（normalize_for_match／match_product）で当たる原文の件数 |

Gemini の選び方のリスク: 新解析には存在しない。根拠 = docs/handoff/gemini-extract-role-split/design.md:25「渡すのは、共通の指示・その仕入元のルール・原文だけで、マスタは渡さない」。したがって新解析の影響は `match_product` の再計算で決定的に測れる。旧解析の Gemini 選択（v6 系）は本試運転で再現できないため、関門3 で出現を数えて確認する。

## 母集団ゲート（空の再生を合格にしない）
- 旧解析の items・新解析の shadow ブロック・新解析の原文ブロック・原文の 4 母集団のいずれかが `--min-population`（既定 1）未満（0 を含む）なら不合格（終了コード 1）。shadow 停止中（#3864）で母集団 (a) が小さくても、0 なら不合格として報告する。
- `--min-population 0` は母集団ゲートを無効にする。可否判定（登録の GO 根拠）には使ってはならない。負の値は引数エラー（終了コード 2）。
- 候補が 0 件の CSV は `candidates.error = NO_CANDIDATES` で不合格（終了コード 1）。
- JSON の `population_gate` に最小件数・各母集団の件数・下回った母集団名・`dropped_items_missing_source`（原文が取れず落とした items 件数）を出す。

## 既知の限界（候補の登録後の値を読み取り専用では再現できない項目）
- product_code: 登録時に `nextval('public.product_code_seq')` で採番される（backend/app/services/tcg_product_master_svc.py:297）ため、登録前には決まらない。試運転では None（RAWCODE 判定に参加しない）。自動採番コード（PMxxxx 形式）が過去の原文に出るかは `meta.pm_code_like_raw_texts` で実行時に実測して報告する。リスクが小さいという主張は、この実測値が 0 のときのみ成立する。【未確認】実 DB 未実行のため現時点の値は不明。
- category_class: 登録は type_master.name_ja（作品名）を保存する（tcg_product_master_svc.py:374-380）が、旧解析が単品／Box 判定に使う値は「商品区分（product_category_id）の kubun_type が 箱系・箱系大 なら Box、なければ category_class」（tcg_work_comparison_svc の classes と同じ規則）。CSV の product_category_code は必須列なので、登録後の候補は kubun_type 側で判定される。試運転は同じ規則で kubun_type から導出する。create_product の導出そのものは async の書き込み関数内で再利用できないため複製していない。

## 実装方針
- 現在の有効マスタは既存ローダで読む（`load_lookup_maps`／`load_product_keywords`／`load_product_kubun_type_map`／`load_work_master`／`load_normalization_rules`／`load_work_reference`／`load_product_entries`）。SQL の複製は、既存に無い最小の 4 本のみ（work_code→id、category→kubun、products.category_class、過去データの抽出）。
- 「追加後」はメモリ上で作る（元の辞書・リストは変更せず新しいものを返す）。候補には負の仮 ID を振り、実商品 ID と衝突させない。
- 旧解析の解き直しは `tcg_work_comparison_svc.match_item` を再利用。作品 ID は保存済み `resolved_work_id`、無ければ `resolve_work_evidence`（`old_work` と同じ分岐）。前後で同じ作品 ID を使う。
- 新解析のブロックは `block_text` で切り出し、`match_product` に渡す（新パイプラインの `extraction_shadow_svc._judge_block` と同じ呼び方）。原文集団（b）のブロックは extraction_items の行範囲（メッセージごと重複除去）を代用する。Gemini v7 のブロック境界は再現できないため（recon 未確認事項）。
- 関数は小さく分け、閾値は定数（DEFAULT_DAYS・SAMPLE_LIMIT など）にする。

## 受け入れ基準

|基準|検証方法|
|---|---|
| 無関係な候補で全関門 0 件・終了コード 0 | backend/tests/test_replay_master_addition.py::TestCaseAUnrelatedCandidate |
| 既存商品と同じ検索語の候補を関門1・関門2で検出 | 同 TestCaseBSharedKeyword |
| work_id が NULL／無効な候補を関門1で検出 | 同 TestCaseCInvalidWorkId |
| 過去原文に候補の名前が出たら関門3で数える | 同 TestCaseDRawTextHit |
| 新解析だけが変わる候補（作品違いで旧解析は除外、新解析は ambiguous）を検出 | 同 TestNewSystemOnlyChange::test_candidate_changing_new_result_but_not_legacy_is_detected |
| status 遷移を変化として数える／shadow 集団と原文集団を別々に報告 | 同 TestNewSystemOnlyChange の 2 ケース |
| DB は READ ONLY で開き、最後に rollback する | 同 TestReadOnlySession |
| 既存テストを壊さない（本番コード無変更） | `git diff --name-only origin/main...HEAD` が scripts/・tests/・docs/handoff/ 配下のみ |
| 実 DB での実行 | 本 PR の範囲外（登録便の手順 1 で PO 操作または人間仲介。未確認として記録） |

## 外部・過去事例の参照と我々への応用
- 外部事例: 該当なし。理由: 社内の LINE 解析マスタ（旧解析 match_pid_with_work と新解析 match_product の 2 系統）に固有の前後比較ツールであり、外部の汎用ツールで代替できない。既存の社内前例（`tcg_keyword_lint` の「登録内容を機械が読む」型、`tcg_work_comparison_svc.match_item` の解き直し）を再利用する。
- 社内の過去事例: docs/handoff/tcg-keyword-quality/design.md（登録内容を機械が読んで止める型）→ 応用: 同じ型で「追加前に過去データで解き直して止める」関所にする。

## 本番での実行手順（【未確認】初回実行まで未検証）
1. 候補 CSV をコンテナの /tmp に置く（コンテナ再起動で消える。/app は書込不可）。
2. `docker compose exec -T backend python scripts/replay_master_addition.py /tmp/candidates.csv --out /tmp/result.json`
3. `docker compose exec -T backend cat /tmp/result.json > result.json`（`docker compose cp` は tmpfs のため使えない）
4. `gate_counts` が全て 0 であることと、`population_gate.below_minimum` が空であることを確認する。終了コード 1 なら登録しない。
- 実行には無制限鍵・VPS 直作業が絡む場合があり、CLAUDE.md の VPS 規則に従う（許可は PO の都度承認）。

## 維持の仕組み
- 守り手: backend/scripts/replay_master_addition.py（終了コード 1 が関所）と docs/handoff/buyback-master-addition/design.md（手順の正本）。Hikky-dev（実装役）が登録便ごとに実行し、PO が gate_counts を確認する。
- 登録便ごとに、束の CSV を本スクリプトに通し、`gate_counts` が全て 0 であることを PR 本文・報告に貼ることを手順化する（docs/handoff/buyback-master-addition/design.md をこの手順の正本とする）。
- 終了コード 1 を返すため、シェル手順・将来の CI 化でそのまま関所にできる。
- 新しい判定系統（match_pid_with_work・match_product 以外）を増やす便は、`evaluate()` に系統を足し、対応テストを追加する。
- 弊害: 過去 N 日の全件を読むためメモリを使う（items と原文）。長期間・大量の場合は `--days` を絞る。
