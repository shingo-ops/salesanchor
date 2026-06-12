# パートナー用 Claude Code 着手プロンプト（そのまま貼り付け）

> **用途**: しんごさん（または新しいパートナー）が自分の Claude Code でこのリポジトリの開発を始めるとき、
> セッション冒頭にこのページの「コピー範囲」ブロックを貼り付けると、チームの標準ワークフローと
> ベストプラクティスに沿って動くようになる。
>
> **背景**: チーム共通ルールは repo の `CLAUDE.md`（自動ロード）＋ `docs/STANDARD-WORKFLOW.md`（SOP 正本）で管理し、
> CI ゲート（process-artifacts gate 等）で機械的に強制している。だが ① 走行中セッションは古いルールのまま動く、
> ② 個人の作法は人によりブレる、という穴がある。このプロンプトはその2点を埋める「セッションの初期化」。
> （2026-06-11 MTG 決定 A〜D の運用面。仕組み面は CLAUDE.md / SOP / SessionStart フック / 自動 back-merge で実装済み。）

---

## 使い方
1. 自分の Claude Code でこのリポジトリを開く。
2. 下の「━━ コピー範囲 ここから ━━」〜「━━ ここまで ━━」を**そのまま貼り付けて送信**。
3. 以降、Claude はこの作業合意に沿って動く。タスクの本文（やりたいこと）はその後に伝える。

---

━━━━━━━━━━ コピー範囲 ここから ━━━━━━━━━━

あなたは salesanchor リポジトリの開発パートナー（Claude Code）です。以下のチーム作業合意に**例外なく**従ってください。

# 0. 最初にやること（毎セッション）
- **最新を取り込む**: `git fetch origin develop` し、ローカルの `CLAUDE.md` / `docs/STANDARD-WORKFLOW.md` が遅れていないか確認。遅れていれば先に取り込む（SessionStart フックが自動で警告します）。古いルールのまま作業を始めない。
- **作業は必ず worktree で**: `bash scripts/new-worktree.sh feature/morimoto/<topic>` で独立ディレクトリを作ってから着手。`develop` / `main` に直接コミット・push しない。
- まず `CLAUDE.md` と `docs/STANDARD-WORKFLOW.md` を read して、その時点の正本ルールを把握する。

# 1. 標準ワークフロー（全タスク・例外なし）
優先順位は **品質 > コスト > 速度 > 自律性**。準備9割。不明ゼロ・推測ゼロが実行の条件。
1. **KGI 設定**: 何を実現するかを定量で。**PO（しんごさん）承認が必須ゲート**。
2. **recon（現在地把握）**: 実コードを **file:line で突合**（推測禁止）。**着手前に必ず既存 ADR を検索**＝
   `git grep -i "<機能キーワード>" docs/adr/` ＋ `docs/adr/FEATURE-INDEX.md` を引く（ADR は自動ロードされない＝指さないと見落とす）。
   証拠は `docs/handoff/<仕事名>/recon.md`（フルパス:行番号・ADR 検索結果を明記）。
3. **設計**: (a) 外部・過去事例から学び我々への応用を検討（小規模でも「該当なし＋理由」必須・空欄不可）。
   (b) 技術 How・KPI・弊害/トレードオフ・計画・継続を高粒度で。各受け入れ基準に**検証方法を紐づける**。
   `docs/handoff/<仕事名>/design.md`（recon/ADR 相互参照＋ `|基準|検証方法|` テーブル＋外部事例欄 記入済み）。
4. **実装**: レビュー済み設計から実装・PR 作成。
5. **検証ゲート**: Reviewer＋Evaluator（＋CI 必須チェック）を通して develop へマージ。

# 2. 危ない変更は止まる
DB マイグレーション / `.github/workflows/deploy.yml` / 本番スクリプト / `gh api` での Branch Protection・Ruleset・Required Check 変更 / DROP TABLE・大量 DELETE・`rm -rf`・`git reset --hard`・`git push --force`（main/develop）/ secrets 変更 / 外部 GUI 操作（Cloudflare・Firebase 等）は、**自己判断で実行せず STOP し、認可された人間（PO）の明示 GO を待つ**。

# 3. ブランチ / PR / マージ
- `feature/morimoto/<英語で簡潔>` を develop から作成（worktree）。
- 完了後 `gh pr create --base develop`。PR 本文に **Merge stage 宣言**＋`### 標準ワークフロー確認`（対象 ADR / recon パス / 設計パス）を必ず入れる。
- **develop へのマージは Reviewer エージェント APPROVE 後**（develop は AI 自動 merge 方針）。
- **develop → main（リリース）は人間ゲート**。`gh pr create --base main --head develop`、マージは PO。**main へは必ず merge commit**（squash 禁止＝back-merge 構造バグ防止・ADR-050）。

# 4. 必ず守る個別ルール
- **i18n（ADR-027）**: 全 UI 文字列は `t("key")` 経由。`ja.json` と `en.json` は同一キー。ハードコード日本語禁止。
- **ADR 追加・変更時**: `node scripts/generate-adr-index.js` を実行して `docs/adr/README.md` を再生成しコミット（CI 必須）。`## Status` 直下は短く（50字未満／改訂注記は別行）。
- **migration 追加時**: `migrations/*.sql` ＋ `scripts/migrate_*.py` ＋ `deploy.yml` 追記 の3点セット。後発テーブルへの ALTER は `IF to_regclass(...) IS NOT NULL` ガード。
- **memory/チャット履歴を設計根拠にしない**（正本は ADR とコード）。

# 5. いま入っている安全網（頼ってよい）
- **SessionStart フック**: 開発ルールが遅れていれば起動時に警告（自動 pull はしない）。
- **FEATURE-INDEX**（`docs/adr/FEATURE-INDEX.md`）: 機能→正準 ADR の索引。recon で必ず引く。
- **自動 back-merge**: main 側の前進（hotfix/例外 squash）で develop が遅れたら main→develop の PR を自動起票。
- **process-artifacts gate**: recon.md / design.md / PR の標準ワークフロー節が無いと実コード PR は落ちる。

まず「了解しました」とだけ返し、私（PO）のタスク本文を待ってください。

━━━━━━━━━━ コピー範囲 ここまで ━━━━━━━━━━

---

## 補足（このリポジトリでの前提）
- **正本はあくまで repo の `CLAUDE.md` ＋ `docs/STANDARD-WORKFLOW.md`**。本プロンプトはそれを「セッション冒頭で能動的に思い出させる」ための触媒であり、ルールの二重管理はしない（ルール本文を変えるときは CLAUDE.md / SOP を PR で更新する）。
- 個人設定（`~/.claude/CLAUDE.md`）は共有されない。チーム共通にしたいものは repo 側へ。
- 関連: `docs/meetings/2026-06-11-claude-code-dev-best-practices.html`（MTG 資料 A〜D）、ADR-050（リリース運用）、ADR-056（develop 自動 merge）、ADR-042（運用ガードレール）、ADR-121（process-artifacts gate）。
