# Codex の運用（役割分担・AEON・UI/UX補助・引き継ぎ）

> この文書は何か：Codex（ChatGPT・Codex app / CLI）と Claude Code の役割分担、AEON の呼び出し方、Codex app の許可と禁止、会話をまたぐ引き継ぎの決まりです。2026-10-23 に入口（AGENTS.md・CLAUDE.md）から文を変えずに移しました（ADR-1040 段3a）。目次 [docs/INDEX.md](../INDEX.md) の章A から辿ります。

## 役割の一覧

（下の1行目は CLAUDE.md、2行目は AGENTS.md にあった文です。2つの食い違いは移した時点のままにしています。）
- **Dev**: Hikky-dev（Claude Code）— 設計・実装・PR起票
- **Dev**: Claude Code / Sonnet (Hikky-dev) — 主Generator・実装・PR起票 | ChatGPT — Planner・Architect・Reviewer | Codex app / CLI — UI/UX補助・第二レビュー・Fallback

## 役割分担（ChatGPT / Claude Code / Codex）

| ステージ | 担当 | 責務 |
|---------|------|------|
| **Research** | ChatGPT | 外部導入事例を5W2H＋数値エビデンスで収集。成功事例・失敗事例を数値化してPlannerへ渡す |
| **Planner** | ChatGPT | Researchエビデンスを受け取り、開発ルール（CLAUDE.md/ADR/CI）と照合し、「なぜこの設計が成功するか」のエビデンスを確立してADR/仕様書を設計する |
| **Architect** | ChatGPT | 開発ルール確認＋Plannerのエビデンス確立が十分か検証＋トレードオフ言語化。APPROVE / REVISE の判定を返す |
| **Generator** | **Claude Code / Sonnet**（主担当） | レビュー済みADR/仕様書に忠実にコード実装・PR起票。設計の再解釈・独断変更は禁止 |
| **UI/UX補助・第二レビュー** | Codex app / CLI | UI/UXの視覚検証・プロトタイプ・read-only差分レビュー・UI-only spike。詳細は「Codex app UI/UX補助運用」参照 |
| **Reviewer** | ChatGPT（最終ゲート）/ Codex app（第二レビュー） | コードレビュー・PR審査。ChatGPTが最終承認ゲートを担う |
| **Evaluator** | Claude Code | Playwright等で動作検証 |

- **通常の新機能・バグ修正経路**: ChatGPT設計（Planner/Architect）→ Claude Code実装（Generator）→ Codex補助レビュー → ChatGPT最終ゲート → GO（ADR-1003により例外を除きClaude Opus設計担当へ常時委譲。詳細は `docs/adr/ADR-1003-go-delegation-to-opus.md`）→ main マージ（develop経由は廃止。release/* → main が現行）。ADR-1015 の B 区分（危険でない変更）は KGI・設計の PO 承認なしで PR まで進む
- Plannerが確立したエビデンスは ADR の Why セクションに必ず含める

### エビデンス要件（Research → Planner → Architect の鉄則）

**数値なし = 証拠なし。** 以下は採用しない:
- 「多くの企業で成功している」→ ❌
- 「おそらく実現可能」→ ❌
- 「問題なさそう」→ ❌

以下の形式でのみ証拠として認める:
- 「導入後にCVRが23%改善した（Who: Salesforce、When: 2023年）」→ ✅
- 「本番障害3日間・売上損失¥2,000万（Who: 某EC、When: 2022年）」→ ✅

## AI Agent Pipeline

Runtime pipeline は次の順序で運用する。

```text
ChatGPT (Research / Planner / Architect)
  → PO Approval（ADR-1015 の B 区分は不要。Opus 審査 APPROVE で代える）
  → Claude Code / Sonnet (Generator)
  → Codex app (UI/Review assist — 任意)
  → ChatGPT (final gate / Reviewer)
  → Evaluator → GitHub CI
```

- `.claude/agents/*` が runtime の正本
- `docs/agents/*` は同じ役割の詳細参照
- Governance は runtime pipeline の外側で、標準化・継続改善・証跡確認を担う

### AEON 呼び出し（単一エントリポイント）

```bash
bash scripts/aeon-dispatch.sh <role> "プロンプト"
```

| Role | 用途 | 内部で呼ぶスクリプト |
|------|------|------------------|
| `research` | 外部事例調査（5W2H＋数値エビデンス収集） | `scripts/codex-research.sh` → `codex-exec.sh` |
| `planner` | Research結果受け取り＋開発ルール確認＋エビデンス確立＋ADR設計 | `scripts/codex-planner.sh` → `codex-exec.sh` |
| `architect` | 開発ルール確認＋エビデンス検証＋トレードオフ言語化＋APPROVE/REVISE判定 | `scripts/codex-architect.sh` → `codex-exec.sh` |
| `generator` | コード実装・PR作成 | `scripts/codex-generator.sh`（対話モード） |
| `reviewer` | コードレビュー | `scripts/codex-reviewer.sh` → `codex-exec.sh` |
| `evaluator` | 動作検証 | `scripts/codex-evaluator.sh` → `codex-exec.sh` |

Generator のみ対話モード。`--auto` で自動承認モードに切替可。

```bash
bash scripts/aeon-dispatch.sh generator          # 対話モード（推奨）
bash scripts/aeon-dispatch.sh generator --auto   # 自動承認モード
```

詳細手順: `docs/ai-agents/aeon-operation.md` / ルーティング定義: `docs/ai-agents/aeon-routing.md`

## Codex のブランチ名

- Codex が自動生成するブランチ名（例: `abc123-codex/fix-inbox`）はそのまま使ってよい

## Codex app UI/UX補助運用

Codex app / CLI は以下の作業のみ許可する。

### 許可
- UI/UXの視覚レビュー（スクリーンショット・Figma・ローカルプレビューを見た改善案）
- read-only差分レビュー（コードを変更せず意見を出す）
- UI-only spike branch での試作（CSS / レイアウト / 空状態 / カードUI / 文言配置）
- ChatGPT 設計後のフロントエンド実装補助（デザイントークン・i18n・PageLayout ルール遵守が前提）

### 禁止
- ChatGPT 設計ハンドオフの再設計・独断変更
- API仕様変更
- DB migration の作成・実行
- `deploy.yml` の変更
- 本番 `scripts/` の変更
- secrets 変更
- 認証・課金・Webhook など事故コストが高い領域の独断変更
- `develop` / `main` への直接 push
- PO GO なしの危険変更

> i18n、PageLayout、CSS変数、E2E更新ルールは Claude Code と同一基準で遵守すること（`frontend/AGENTS.md` 参照）。

## 引き継ぎルール（忘れ防止）

会話メモリ・チャット履歴を根拠にした状態宣言は禁止。一次情報（ファイル・コマンド出力・PR URL）のみ有効。

### セッション開始時の必須確認（3ファイル）

```bash
cat tasks/todo.md                          # 進行中タスク台帳（正本）
cat .claude-pipeline/active-work.md        # ブランチ占有状況
cat docs/runbooks/<関連runbook>.md         # スプリント状態
```

### 状態変化があったターンの終了前に更新する

1. `tasks/todo.md` の対象行の「現在地」「次の一手」「根拠」「更新日」を書き換える
2. スプリント完了・開始・ブロック時は `docs/runbooks/` の対象スプリント行も更新する
3. 新規タスクは `tasks/todo.md` に追加し、`docs/ai-agents/evidence-registry.md` に根拠を記録する

### 根拠の書き方

根拠列には以下のいずれかを記入する（「〜のはず」は不可）:

| 根拠の種類 | 書き方の例 |
|----------|----------|
| ファイル確認 | `cat tasks/todo.md` 実行済み |
| PR確認 | PR #1134 マージ確認済み |
| コマンド出力 | `docker compose ps` → 全コンテナ healthy |
| ADR | ADR-080 §Phase1 参照 |

### スクリプトによる自動検証

```bash
bash scripts/check-task-state.sh   # tasks/todo.md と runbook の構造チェック
```

CI（task-state-check.yml）が PR ごとに自動実行する。
