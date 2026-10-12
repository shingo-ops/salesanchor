# 設計: 設計審査（architect）とコード審査（reviewer）のモデルを Fable にする

- 状態: 設計者（Opus）が作成。
- PO 承認（2026-10-12）:
  - 「レビュアーだがfableに任せることは出来る？恒久的に」への提案に「y」。
  - 続けて、リポジトリ内の同名定義も Fable に変える PR に「y」。
- 調査: `docs/handoff/agents-model-fable/recon.md`（調査担当の Sonnet が作成）
- 対象ADR: ADR-113（.claude/agents の最終変更 62fab633a の根拠。recon A）

## 0. 事実
- `.claude/agents/architect.md:4` は `model: opus`、`.claude/agents/reviewer.md:4` は `model: sonnet`（recon A）。
- 公式文書の sub-agents（https://code.claude.com/docs/en/sub-agents、Context7 /websites/code_claude、2026-10-12 取得）に、次の記述がある。
  - frontmatter の `model` には `sonnet`、`opus`、`haiku`、`fable`、完全なモデル ID、`inherit` を書ける。
  - 使うモデルは、次の順に決まる。
    1. 呼び出しごとの model 引数
    2. 定義の frontmatter
    3. 環境変数 CLAUDE_CODE_SUBAGENT_MODEL
    4. 会話のモデル
- プロジェクトの .claude/agents は、同じ名前のユーザー設定（~/.claude/agents）より優先される。
  - このセッションの agent 一覧に表示される architect と reviewer の説明文は、リポジトリ内のファイル（`.claude/agents/architect.md:3`、`.claude/agents/reviewer.md:3`）と一致した。
  - ~/.claude/agents 側の説明文とは一致しなかった（設計者が Read で確認）。
- model 行を検査する CI・フック・スクリプトは無い。`.github/workflows/aeon-script-check.yml:66-72` は、6つの役割のファイルがあるかを確かめるだけ（recon D）。
- `.github/CODEOWNERS` には .claude の行が無い（recon D）。
- モデルの割り当てを決めた ADR は無い（recon E）。

## 1. 成功条件
|基準|検証方法|
|---|---|
|K1 `.claude/agents/architect.md` と `.claude/agents/reviewer.md` の4行目が `model: fable` になり、ほかの行は変わらない|`git diff origin/main...HEAD -- .claude/agents` が2行の置き換えだけ|
|K2 ほかの役割（planner, research, generator, evaluator, governance）の model 行は変わらない|`grep -n '^model:' .claude/agents/*.md` の前後比較|
|K3 CI がすべて通る（aeon-script-check を含む）|gh pr checks|
|K4（マージ後）main を取り込んだ salesanchor のセッションで、model を指定せずに architect を呼ぶと Fable で動く|設計者が次回の審査で、呼び出しの結果に表示されるモデル名を確かめる|

## 2. 対象と対象外
- 対象: `.claude/agents/architect.md`、`.claude/agents/reviewer.md`（各4行目だけ）、本書と recon.md。
- 対象外:
  - 審査の手順の本文
  - ほかの役割のモデル
  - docs/agents（Codex 用の別系統。recon C）
  - 過去の handoff の記述（作業の記録なので書き換えない）

## 3. 変更前後
- `.claude/agents/architect.md:4` は `model: opus` から `model: fable` に変える。
- `.claude/agents/reviewer.md:4` は `model: sonnet` から `model: fable` に変える。

## 4. SSOT
- 役割ごとのモデルの正本は、各役割の定義ファイルの frontmatter の1か所にする。
- ユーザー設定（~/.claude/agents）も同じ値に変えてある。ただし、優先されるのはこのリポジトリの定義（§0）。

## 5. 安全・戻し方
- 権限やツールの範囲は変えない（model 行だけ）。
- 戻すときは、2行を元の値（opus と sonnet）に戻す PR を出す。
- PO が「委譲停止」相当の指示を出したときも、同じように戻す。

## 6. 代替案
- 呼び出しのたびに model 引数で Fable を指名するだけにする：指名し忘れると、元のモデルで動いてしまう。PO は「恒久的に」を求めたので不採用。
- 環境変数 CLAUDE_CODE_SUBAGENT_MODEL：すべての役割に効いてしまい、実装（Sonnet）まで変わるので不採用。

## 7. リスク
- 【未確認】Fable による審査の時間と費用は、今と比べてまだ測っていない。
  - 2026-10-12 の機能設計の審査（agent-console v0.4.0）では、3回の審査で問題を見落とさず指摘した（CRITICAL 1件を含む）。
  - 時間と費用は、今後の審査で記録する。

## 外部・過去事例の参照と我々への応用
- 公式文書の sub-agents（§0）。frontmatter で役割ごとにモデルを決める方法が公式に用意されているので、これを使う。
- 過去事例: 2026-10-12 の agent-console v0.4.0 の設計審査。
  - 書いた本人（Opus）の自己審査は APPROVE としたが、根拠のファイルを取り違えていた。
  - Fable の審査がそれを CRITICAL として見つけた（agent-console の docs/handoff/v0.4.0-diff-comments/design.md §9）。
- 適用限界: 1件の事例であり、効果の数値（見落としの率）はまだ無い。

## 維持の仕組み
- 守り手: 設計者（Opus）。
- 記憶 feedback_reviewer_fable に、この決定を残してある。
- モデルを変えるときは、この2ファイルとユーザー設定を同時に変える。
