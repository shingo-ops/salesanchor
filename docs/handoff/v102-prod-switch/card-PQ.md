# 実装カード PQ: v102 の価格・数量を Gemini の写しの数字で補う＋数字にできない時は要確認（便PQ）

設計者: Opus（2026-10-10）。PO 承認: 「数字以外を消す必要があると考える…数字のみに整形することは出来る？」「→対策が必要」（安全網）、続けて「確立したなら進める…PRマージ、デプロイまで完走させてくれ」。
根拠の調査: /tmp/CC報告ファイル/v102-pq-recon/recon.md（基準 origin/main 853be509c）、/tmp/CC報告ファイル/v102-unit-check/err7/rootcause.md。社外秘の原文はリポジトリ・PR に書かない（テストは合成した文で作る）。

## 1. 何を直すか（観測事実）
- v102 は price_normalized / quantity_normalized を原文の目印から取り直す（gemini_raw_copy_v101.py:854-874 → extraction_judgement_svc.py:599 resolve_price_quantity）。Gemini の写し（"42個"・"在庫数：17"）は検算にしか使わない。
- 本番 1,079件で数字があるのに NULL: 数量 9件（うち6件は要確認にならず配信）、価格 4件。原因は (a) 1行に「個」付きの数が2つ（:636-638 multiple_values）、(b) 行頭「■」の在庫行が商品名に入り _mask_product_name（extraction_judgement_svc.py:526-538）で消える。
- resolve_price_quantity の reasons（price_reasons）を読む本番コードは 0件。数量 NULL を要確認にする理由が無い。

## 2. 変更（v102 だけ。resolve_price_quantity 本体・v10.1・v10・shadow・付け直し `_price_of` は変えない）
### 2-1. 補い（_extract_one の `if v102:` 枝、v101:854-874 の pq を受けた直後。v101:826 の v102 引数で分岐）
- pq.price が None なら `_single_number(item["price"])`、pq.quantity が None なら `_single_number(item["quantity"])` を採用候補にする。pq が値を持つ時は変えない。
- `_single_number(s)`（新しい小さな関数、gemini_raw_copy_v101.py 内）:
  - s が文字列でなければ None。NFKC 正規化。
  - 万・千・億・k・K のどれかを含めば None（"2万" を 2 にしない）。
  - 数字列 `\d[\d,]*`（小数点は区切り扱い→"1.5" は2つ）を全部取り、ちょうど1つの時だけ、カンマを除いて数にする。0個・2個以上は None。
- 採用の条件（両方満たす時だけ）: ①上の数が1つに決まる ②その数（カンマ除去後）が、その件の行（own_text、NFKC・カンマ除去後）に独立した数として現れる（既存の照合関数があればそれを使う。recon §1 の _digits_agree / _quantity_not_in_text の判定と同じ考え方。前後が数字でないこと）。
- 採用した時は price_reasons に "gemini_digits" のような印を足さない（表に無いコードを増やさない）。どの件で補ったかはテストと置き換え試験で確かめる。

### 2-2. 安全網（_extract_v102.build() の F4 と同じ置き場 v101:1214-1226、または _item_reasons v101:1144-1155）
- Gemini の quantity に数字がある（`_has_no_digit` が False）のに、補いの後も quantity_normalized が None → 理由 `quantity_unresolved` を付ける。
- Gemini の price に数字があるのに、補いの後も price_normalized が None → 理由 `price_unresolved`（既存コード）を保存値に付ける。
- review_joins（tcg_condition_review_svc.py:~143-144）が読み取り時に price_unresolved を足す処理と二重にならないこと（既に含まれていれば足さない）をコードで確認し、二重になるならそこで重複を除く。テストで示す。
- 理由が1つでも付けば needs_review=True（svc:559）→ 配信から除外（tcg_distribution_svc.py:262）。既存の流れで伝わることをテストで示す。

### 2-3. 理由コード quantity_unresolved（SSOT は public.review_reason_codes。値はここ1か所）
- コード側の定数（既存の理由コード定数と同じ場所・書き方）と tests/test_review_reason_codes_consistency.py の `_code_side_constants`（:33-47）に追加。
- frontend の ja.json / en.json に `reviewReason.quantity_unresolved`: 「数量を読み取れない」／「Quantity not readable」（price_unresolved の訳と同じ形）。
- docs/handoff/v102-prod-switch/data/review_reason_codes/ に既存 qty_*.sql と同じ型で:
  - seed_20261010_quantity_unresolved.sql: ('quantity_unresolved','system','analysis')
  - qu_precheck.sql（ROWS|30・HAS_QU|0・PRECHECK_DONE、読み取り）／qu_dryrun.sql（1行 INSERT→件数検査 CHECK_OK 1→ROLLBACK・DRYRUN_OK）／qu_commit.sql（CHECK_OK 1・COMMIT_DONE）／qu_verify.sql（quantity_unresolved|system|analysis・ROWS|31・VERIFY_DONE）／qu_rollback.sql（その1コードだけ削除・ROLLBACK_DONE）
  - README.md に「追加: quantity_unresolved（便PQ）」節（手順・戻し方・記録欄）。
- migration は作らない（ADR-1007: 値は migration に書かない）。

## 3. テスト（合成した文で。社外秘の原文を使わない）
- `_single_number`: "42個"→42、"在庫数：17"→17、"￥8,500"→8500、"１２BOX"→12、"2万"→None、"1.5"→None、"10～20/セット"→None、"none"→None、None→None、"N/セット"型→N。
- v102 経路（extract_v101_items 等、既存テストの呼び方に合わせる）:
  - 行頭「■商品名：…」「■単価（税込）：￥8,500」「■在庫数：17」の件 → quantity 17、price 8500、quantity_unresolved なし。
  - 「数量：42個（注文6個単位）」「単価：6,000」の件、Gemini quantity "42個" → quantity 42。
  - Gemini quantity "42個" だが原文にその数が無い件 → 補わない（quantity_not_in_text は従来どおり）。
  - 補えない件（Gemini quantity "10～20"、原文も曖昧）→ quantity None ＋ quantity_unresolved ＋ needs_review。
  - price も同様に1件ずつ（補える／補えず price_unresolved）。
- v10.1（v102=False）の同じ入力で結果が変わらないこと（回帰）。
- 理由コード整合テストが通ること。
- ローカルで動かせるテストは全部ローカルで実行。PG テストは CI。

## 4. 置き換え試験（社外秘・リポジトリ外）
- /tmp/CC報告ファイル/v102-unit-check/dump.json の 46投稿（job 12a7e098 を含めてよいが、比較対象の保存値が無い件は除外と明記）を、変更後のコードの v102 システム段（run_v102_pipeline 相当、DB を使わない形）に通し、保存値と件ごとに比べる。マスタは同フォルダの master_*.json を使う。使えない部分（DB 必須）があれば、何が比べられないかを書く。
- 期待（受入条件）:
  - K1 保存値が非 NULL の価格・数量で、値が変わる件 = 0
  - K2 数量 NULL→値: 9件前後、価格 NULL→値: 4件前後（実数を出し、各件を原文の行と並べる）
  - K3 数字があるのに NULL のまま残る件は、すべて quantity_unresolved / price_unresolved が付く
  - K4 価格・数量以外（product_id・unit・condition・review_reasons の他コード）の違い = 0
- 出力: /tmp/CC報告ファイル/v102-pq-recon/replay.md（件数・違いの全件）。

## 5. 文書（リポジトリ）
- docs/handoff/v102-prod-switch/design.md に「§15 便PQ」: 目的・変更前後（file:line）・対象/対象外（v6・v10.1・shadow・`_price_of`・_STOCK_START_RE と _mask_product_name の根本修正は対象外、理由: 共有経路への波及）・受入条件表 |基準|検証方法|（K1〜K4＋テスト）・戻し方（PR を戻す。表の行は qu_rollback.sql）・外部事例（不要の理由）・維持の仕組み（整合テスト・回帰テスト）。
- recon.md に §8 として recon の要点（file:line）を追記（社外秘の原文は書かない、件数のみ）。
- card-PQ.md としてこのカードを docs/handoff/v102-prod-switch/ に置く。

## 6. 手順
1. `bash scripts/new-worktree.sh release/v102-price-quantity-digits --claude` → `./scripts/dev/executor-preflight.sh`。
2. 実装 → テスト → 置き換え試験 → ruff・pytest（関係ファイル）・frontend の i18n 検査（npm run check:all）。
3. commit（feat:）→ push → `gh auth status`（shingo-cc）→ worktree 内で `gh pr create --base main --draft`（PR テンプレ起点、本文はファイルに書いてから --body-file、### 標準ワークフロー確認・触るファイル全列挙・外部・過去事例・維持の仕組み）。GO 記録は書かない。
4. マージ・Ready 化・CI 待ち・本番接続はしない。

## 7. 調べて報告すること（実装と別に）
- 再解析の起動方法: 本番で既存の v102 投稿（job 単位）のシステム段をやり直す既存の手段（celery タスク名・引数・file:line、API があればその経路）。配信の予約（tcg.scheduled_distribution）まで走るか。

## 停止条件
- カードの前提と実物が違う（file:line がずれて意味が変わる、共有経路を変えないと実装できない、二重付与が避けられない 等）→ NEEDS_DECISION で止まる。
- フックに止められたら言い換え再試行せず停止報告。最終行は DONE / BLOCKED: / NEEDS_DECISION:。
