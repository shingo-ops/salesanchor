# 柱2 design — 宣言漏れ（書類スキップの穴を塞ぐ）

> この文書は何か（専門用語なしの1行）:
> 「書類だけのPRは検査を飛ばす」抜け穴を塞ぎ、正本を触るPRは必ず宣言照合にかける設計。

親: [README.md](./README.md)／KGI: [kgi.md](./kgi.md)（柱2節）

## 1. あるべき姿（親から）
機械が自動で止める。AIエージェントの注意に頼らない（ideal-state.md）。

## 2. 直す対象（recon実測・file:line）
- scripts/check-process-artifacts.js:671-672 `if (hasDocsOnly) { process.exit(0) }` が、書類のみPRを照合前に終了させる。
- そのため到達不能になる検査: 触るファイル照合(746-767)・削除ファイル照合(771-)・新規重複・作者・外部API・GO判定。
- 既に自己保護済みの正本（DANGEROUS_PATTERNS 53-60）: STANDARD-WORKFLOW.md／process-artifacts-gate.yml／PULL_REQUEST_TEMPLATE.md。これらは穴なし。
- 穴が開いている正本: design-partner.md／各 kgi.md・ideal-state.md／ADR類（.md で docs 分類され素通り）。
- 猶予閾値 GRACE_THRESHOLD_PR=2600 は、最新PR番号3018のため将来PRには実質かからない（recon実測）。正本例外の追加ロジックは不要。

## 3. design（技術How）
- classifyChanges は変更しない。671行の `if (hasDocsOnly)` の判定に、CANONICAL 条件を1つ加える:
  変更ファイルに `docs/` 配下 または `.md` が1件でも含まれるなら、hasDocsOnly でも exit させず後続の照合へ進む。
- 判定はパス前方一致のみ。AI・人の意味判断はゼロ（「機械で白黒」要件）。
- 既存の TOUCH_FILE_EXCLUDE_PATTERNS（active-work.md 等の作業ファイル）は継続適用。雑音は除外し正本だけ照合。

## 4. なぜ実害が小さいか（recon実測）
- 過去の書類のみPR5件（#3012/#3005/#3004/#3002/#2991）にB案を試算 → 5件とも宣言完備で pass 想定・fail 0件。
- 照合は変更ファイルのみ対象。書類PRの変更数は平均2.8ファイル（重くならない）。

## 5. 受入基準（ペアテストで検証・test-process-artifacts.js に新規追加）
- 欠落版: 正本(.md)を触る書類PRで宣言なし → fail する。
- 充足版: 同PRで触る/削除欄が実diffと一致 → pass する。
- 中立版: 正本を含まない純書類PR → 従来どおりスキップ(pass)。
- 3本すべてが期待どおり動くことを実測（KGI 柱2-c）。

## 6. 弊害・トレードオフ（空欄不可）
- 書類PRでも正本を含むと宣言(触る/削除欄)記入が必須になる＝作成の手間が増える。ただし過去5件で全pass、実害は小。
- .md を一律対象にするため、正本でない設計メモ(.md)も照合対象になる。ただし宣言を書けば通るだけで、fail にはならない（誤爆でなく厳格化）。作業ファイルは除外パターンで免除。

## 7. 接触面分析（6面）
- ①人: 書類PR作成者。正本を触る時は宣言必須に。
- ②エージェント: executor-preamble.md に「正本(.md/docs)を含む書類PRは宣言照合が走る」を1行追記（周知）。
- ③機械: check-process-artifacts.js（本体・本設計の対象）＋ test-process-artifacts.js（ペアテスト新規）。
- ④データ: 影響なし（DB・テナント非接触）。
- ⑤本番: 影響なし（deploy・VPS非接触）。
- ⑥外部: 影響なし。

## 8. 維持の仕組み
- 守り手: .github/workflows/process-artifacts-gate.yml（DANGEROUS_PATTERNS で自己保護済み＝本ガード改変も検査対象）。
- 対象: 書類スキップの穴が再び開くこと。
- 効き目の担保: 受入基準§5のペアテスト（欠落版で赤・充足版で緑）を実条件で実測。

## 9. 実装の注意（別便・危険操作）
- 実装は check-process-artifacts.js（関所本体）改変＝危険操作。PO自筆GO必須。
- 順序: 先にペアテストを書く → わざと欠落版で赤を確認 → 本体にCANONICAL条件を追加 → 充足版で緑を確認。
- 柱1（再採点漏れ）と同一ファイル群のため、柱2実装の後に柱1を続ける（kgi.md 実装順序1）。
