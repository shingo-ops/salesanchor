# recon — 動作実測ゲート（現在地・file:line実測）

> この文書は何か（専門用語なしの1行）: 今の関所が何を検査していて、動作実測欄をどこに足せるかを実物で調べた記録。

親: ../../specs/process-hardening/proof-of-behavior/README.md

## 実測（origin/main SHA f55d4db8 時点）
- 関所本体: scripts/check-process-artifacts.js（全881行）
- 危険変更判定: check-process-artifacts.js:53 DANGEROUS_PATTERNS ／ :69 /^\.github\/workflows\// ／ :83 classifyFile ／ :90 hasDangerous。scripts/・.github/workflows/ が危険変更扱い。
- PR本文セクション抽出: check-process-artifacts.js:188（### 標準ワークフロー確認）／ :256（### GO記録）。見出しベースで切り出す既存パーサあり＝「### 動作実測」も同方式で流用可能。
- 現状の穴: 既存検査（:294 GO記録／:396 受け入れ基準表／:448 維持の仕組み 等）は「書類が揃うか」のみ。「動くか」を見る検査は皆無（file:line で不在を確認）。
- 既存重複: proof-of-behavior と同名の独立ADR・仕様書は無し（新規作成の正当性あり）。親 process-hardening（ADR-121）の子としてぶら下げる。

## 設計送り（design便で決める）
- 「### 動作実測」欄の必須化を hasDangerous 分岐（:814付近）に相乗りさせる形。
- 段階導入（警告→停止）の切替方法。
