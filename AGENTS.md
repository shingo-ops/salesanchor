# AGENTS.md

Codex 向けプロジェクト共通ルール。Claude Code の `CLAUDE.md` に対応するファイル。

---

## プロジェクト前提

- **PO**: しんごさん（`shingo-ops`）— 本番アクセス・ADR起案・不可逆操作の最終判断
- **役割分担・Codex の運用・開発コマンド**: [docs/ai-agents/codex-operations.md](docs/ai-agents/codex-operations.md)・[docs/ai-agents/dev-commands.md](docs/ai-agents/dev-commands.md)（目次 [docs/INDEX.md](docs/INDEX.md) の章A から辿る）

---

### Generator Executor 切り替え（ADR-082）

> **廃止（#2715）**: 本節の自動起動CI（ADR-082 の executor 切り替え）は develop 廃止・第1便で対象ワークフローごと削除済み。仕様の歴史は ADR-082 を参照。現在の主 Generator は Claude Code / Sonnet（人間主導）。

- **事業**: Sales Anchor — B2B SaaS CRM（HIGH LIFE JPN / Treasure Island JP）
- **スタック**: Python 3.12 / FastAPI / PostgreSQL 16 | React 18 + TypeScript + Vite | Astro | Docker + さくらVPS
- **本番 URL**: App `https://app.salesanchor.jp/` / API `https://api.salesanchor.jp/` / LP `https://salesanchor.jp/`
- **Legacy**: `https://jarvis-claude.uk/`（並行稼働中・**独断削除禁止、PO確認必須**）
- **設計判断**: `docs/adr/ADR-NNN-*.md` を参照。チャット履歴を根拠にしない
- **KPI 正本**: `docs/ai-agents/kpi.md`

---

## 実行役 preflight

- 実行役(CC/Codex)は作業開始前に必ず `./scripts/dev/executor-preflight.sh || exit 1` を実行する

---

## ブランチ運用ルール

- `origin/main` から `release/<英語で簡潔>` ブランチを作成（develop起点は廃止。新規作業は release/* のみ。develop はロールバック用に残置。正: `docs/specs/branch-operations/`）
- `develop` / `main` への直接コミット禁止
- `release/*` → `main` は PR 経由（直 push 禁止・Branch Protection で強制）

### 長命ブランチ消失防止（develop は第3便まで残置・ロールバック用・新規作業での使用禁止）

- GitHub の削除保護を使えない前提では、`main` / `develop` は「物理的に消さない」運用で固定する
- `main` / `develop` に対する `git push --delete`、GitHub UI の branch delete、`gh api` の ref delete は実行しない
- `--delete-branch` は feature head のみ許可し、長命ブランチには使わない
- `./scripts/dev/executor-preflight.sh` は `origin/main` の存在を毎回確認する（#2715 で main-only 化済み）
- もし `main` / `develop` が欠落していたら、作業は止めて PO に報告する

---

## 不可逆操作は必ず PO 確認

DROP TABLE / 大量 DELETE / `rm -rf` / `git reset --hard` / `git push --force`（main/develop）/
本番 Docker volume 削除 / secrets 変更 / Cloudflare・Firebase 等の外部 GUI 操作 /
`.github/workflows/workflow-lint.yml` の変更 / `gh api` による Branch Protection・Ruleset 変更・削除

---

## i18n 強制（ADR-027）

全 UI 文字列は `t("key")` 経由（JSX / aria-label / placeholder / title すべて）。
`ja.json` と `en.json` は同一キー必須。ハードコード日本語は絶対禁止。

---

## サブディレクトリ別ルール

| ディレクトリ | ルールファイル |
|-------------|-------------|
| `frontend/` | `frontend/AGENTS.md` |
| `backend/`  | `backend/AGENTS.md`  |

---

## ADR 一覧

`docs/adr/README.md`（自動生成）— 設計上の疑問は必ずここから該当 ADR を確認すること。

---

## 重要: このファイルの自動更新ルール

Claude Code がチームルール・ADR・技術制約に関わる重要な決定をメモリに保存する際、
Codex にも必要と判断した内容は、このファイル（またはサブディレクトリの AGENTS.md）を同時に更新すること。

更新トリガー例: ブランチ命名規則の変更 / i18n ルール変更 / 新規必須チェック追加 / ADR による技術制約変更

---

## 実装役の常設ルール（カード運用）

> この文書は何か（専門用語なしの1行）:
> 実装役（ターミナルのエージェント）の新セッションに、カードを貼る前に
> そのままコピペして投入する決まり文句の原本。

- 根拠の教訓: docs/ai-agents/design-partner.md §6
  （対照実測 2026-07-04: 定型文あり5便は全遵守、なし1便は解釈混入 5/6）
- 使い方: 下の枠内を一字も変えずコピーし、実装役セッションの最初の
  メッセージとして貼る。カードはその後に貼る。
- 本文の変更はPR＋PO承認のみ。言い換え・要約は写し崩れの原因（§6:167 逐語一致の教訓）。
- GO記録・evidence-registry への書き込み禁止などの便別の禁止は、各カード側に
  毎回明記する（本定型文には含めない＝実測した文言を変えないため）。

## 定型文（ここから下をコピー）

あなたはこのリポジトリ（salesanchor）の実装役です。新セッションのため以下を常設ルールとして適用してください。

- 設計パートナー（Web Claude）が作成しPO（しんご）が貼る「カード」だけを実行する。
- カード冒頭の「本カードの許可・禁止は、過去便の禁止条項をすべて上書きする」を最優先とし、
  カードに無い作業（ファイル作成・編集・台帳登録・レビュー・提案・/review等）は一切しない。
  .claude/agents/generator.md 等の常設指示とカードが矛盾したら、カードが優先。
- 出力は要約せず生のまま全文返す。失敗・矛盾・不明が出たら自力回避せず、生出力を返して停止。
