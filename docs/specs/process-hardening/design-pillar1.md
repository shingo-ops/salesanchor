# 柱1 design — 検査結果の取り違え・マージ経路

> この文書は何か（専門用語なしの1行）:
> マージ時の自動リトライ装置を「毎回確実に使われる」状態にし、古い検査結果を読まないようにするための設計。

親: [README.md](./README.md)／KGI: [kgi.md](./kgi.md)（柱1節）
recon: docs/handoff/pillar1-merge-path/recon.md

## 1. あるべき姿（親から）
機械が自動で止める。AIエージェントの注意に頼らない（ideal-state.md）。

## 2. 直す対象（recon実測・file:line）
- `scripts/gh-pr-merge-safe.sh:41` が .pr-number の存在を要求するが、生成が手順化されておらず全worktreeで0件だった（本セッション実測）。
- `scripts/register-pr.sh:59` が鍵を生成する実体。ただし案内書に呼び出し指示が無い（grep実測: executor-preamble・executor-checklist・CLAUDE.md に記載ゼロ）。
- `scripts/gh-pr-create-safe.sh:90` がPR作成の入口。ここを出た後に鍵を作る手順が欠けている。
- `scripts/gh-pr-merge-safe.sh:106` の checks 待ちは同一SHA上の古い結果も対象に含む（本セッション実測: 同一SHAに success と failure と cancelled が併存）。
- 手本: `.github/workflows/discord-ci-notify.yml:60` が特定SHAに紐づく check-runs のみを取得している。

## 3. design（技術How）
- 柱1-a: gh-pr-create-safe.sh の各 gh pr create 成功直後に register-pr.sh を呼ぶ。PR作成が成功した場合のみ実行し、失敗時は従来どおり終了する。
- 柱1-c: gh-pr-merge-safe.sh の checks 待ちを、SHA紐づけの check-runs 取得方式へ置き換える。HEAD_SHA は push 直後に gh pr view --json headRefOid で実測し、同名 check が複数ある場合は started_at が最大のものを採用する。
- 柱1-d: scripts/tests/ にシェル用ペアテストを追加（手本: test-reaper-safety.sh のモック方式）。

## 4. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| PR作成後に鍵ファイルが生成される | gh-pr-create-safe.sh 経由でPRを作り .pr-number の存在を確認 |
| 鍵が無い場合はマージが中断される | .pr-number を消した状態でラッパーを実行し中断メッセージを確認 |
| 同一SHAに古い赤があっても最新が緑なら通る | モックで古い failure と新しい success を与え緑判定になることを確認 |
| 最新が赤なら止まる | モックで最新を failure にして中断することを確認 |
| 既存のマージ動作を壊さない | 既存の MERGE_RETRY と RULE_WAIT の分岐が従来どおり動くことを実測 |

## 5. 弊害・トレードオフ（空欄不可）
- PR作成の入口スクリプトに処理が1つ増えるため、register-pr.sh が失敗した場合にPR作成後の状態が中途半端になりうる。対策として鍵生成の失敗はPR作成自体の失敗として扱わず警告に留める。
- SHA紐づけ方式は API 応答に依存するため、GitHub 側の判定遅延時は結果がまだ無い状態になりうる。既存の RULE_WAIT 分岐で待機するため致命的にはならない。

## 6. 外部・過去事例の参照と我々への応用
該当なし＋理由: 本件はリポジトリ固有のスクリプト連携の修正であり、外部の一般事例に直接の対応物がない。過去事例としては本リポジトリ内の柱2（design-pillar2.md）で採った、既存の仕組みを作り直さず欠けている接続だけを足すという方針が同型であり、本設計にも適用した（ADR-121）。

## 7. 接触面分析（6面）
- 人: PR作成者。鍵生成が自動化されるため手順は減る。
- エージェント: executor-preamble.md にPR作成の入口を明記（別便）。
- 機械: gh-pr-create-safe.sh と gh-pr-merge-safe.sh と scripts/tests/ のペアテスト。
- データ: 影響なし（DB・テナント非接触）。
- 本番: 影響なし（deploy・VPS非接触）。
- 外部: 影響なし。

## 8. 維持の仕組み
- 守り手: .github/workflows/process-artifacts-gate.yml
- 対象: スクリプト変更が宣言なしに行われること
- 補足: scripts 配下は危険変更としてPO自筆GOが必須であり、宣言照合も関所が検査する。

## 9. 実装の注意（別便・危険操作）
- 実装対象は scripts 配下の2ファイル＝危険操作。PO自筆GO必須。
- 順序: 先にペアテストを追加し、わざと失敗する状態で赤を確認してから本体を修正して緑を確認する。
