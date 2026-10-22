# AGENTS.md

全 AI（Claude Code・Codex ほか）共通の入口。決まりの本文はここが正本。手順・詳細は目次 docs/INDEX.md からたどる。

## プロジェクト前提

- **PO**: しんごさん（`shingo-ops`）— 本番アクセス・ADR起案・不可逆操作の最終判断
- **事業**: Sales Anchor — B2B SaaS CRM（HIGH LIFE JPN / Treasure Island JP）
- **スタック**: Python 3.12 / FastAPI / PostgreSQL 16 | React 18 + TypeScript + Vite | Astro | Docker + さくらVPS
- **本番 URL**: App `https://app.salesanchor.jp/` / API `https://api.salesanchor.jp/` / LP `https://salesanchor.jp/`
- **Legacy**: `https://jarvis-claude.uk/`（並行稼働中・**独断削除禁止、PO確認必須**）
- **設計判断**: `docs/adr/README.md`（自動生成）から該当 ADR を確認。メモリ・チャット履歴を根拠にしない
- **ADRと実装の優先順位**: 食い違いは必ず ADR を優先し、追加の安全なマイグレーションでコードを ADR へ寄せる（逆はしない）

## 不可逆操作は必ず PO 確認

DROP TABLE / 大量DELETE / `rm -rf` / `git reset --hard` / `git push --force`（main/develop） / 本番Docker volume削除 / secrets変更 / Cloudflare・Firebase等の外部GUI操作 / `.github/workflows/workflow-lint.yml` の変更 / `gh api` による Branch Protection・Ruleset・Required Status Check の変更・削除

上記操作を許可する場合: `bash scripts/permit-danger.sh "<op>"`（1回限り有効・30分で自動失効）。会話の同意票でも可（ADR-1033、除外あり）

常時厳禁（ADR-025）: 暗号化済シークレット（`*_token_encrypted`）の手動投入 / destructive操作（DROP TABLE等）のPO確認なし実行

## VPS 直作業禁止（技術的にも制限付き鍵のみ）

- **エージェントは原則として制限付き鍵を使用**（`salesanchor-claude`、ForceCommand 制限）
- **無制限鍵（`~/.ssh/manual-only/id_ed25519`）**: 本番 DB の読み取りは reader 鍵の道（`docs/handoff/ai-readonly-db-path/usage.md`）を使い、manual-only は使わない。DB 以外の読み取りだけの調査（ログ/設定表示・`ss`/`ps`/`systemctl status`・接続確認）は恒常許可。変更を伴う作業（ファイル作成・コンテナ起動停止・設定変更・再起動・DB 書き込み）は作業ごとに PO の GO が必要（設計担当が GO 原文を依頼文と PR に転記）
- 鍵・パスワード・トークンの値は表示しない。人間の無制限鍵（`hitoshi@` 等）は VPS 側で変更しない
- 詳細・ロールバック手順: `docs/handoff/rehearsal-env/design-b-ssh-isolation.md`

## ブランチと作業場所

- `develop` / `main` への直接コミット禁止。`release/*` → `main` は PR 経由（直push禁止・Branch Protection で強制）
- 作業前に必ず（例外なし） `bash scripts/new-worktree.sh release/<topic>` で `origin/main` 起点の作業場所を `~/worktrees` 配下に作る
- `main` / `develop` は消さない（`git push --delete`・UI の branch delete・`gh api` の ref delete は実行しない）
- `migrations/`・`deploy.yml`・本番 `scripts/` を含む PR は PO の「GO #PR番号」まで main にマージしない（ADR-135・ADR-136。GO は ADR-1003 により例外（PO 本人の GO が必須の7種）を除き Claude Opus 設計担当へ常時委譲。PO「委譲停止」で解除）
- 手順の詳細（PR の作り方・Draft・break-glass・リリース PR）: `docs/specs/branch-operations/README.md`

## 作業の型

- 実行役は作業開始前に必ず `./scripts/dev/executor-preflight.sh || exit 1` を実行する
- 全タスクは `docs/STANDARD-WORKFLOW.md` の3フェーズ（KGI→現在地→設計）に従う
- 作業前/commit前/PR前のチェックは `docs/ai-agents/executor-checklist.md`（正本・必読）
- 手順書・作業方法は目次 `docs/INDEX.md` から章→末端の順にたどって読む
- 画面は `frontend/AGENTS.md`、サーバー側は `backend/AGENTS.md` の決まりにも従う
