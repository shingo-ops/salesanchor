# 開発コマンド（手元の venv・セットアップ・実行）

> この文書は何か：手元の Python の venv の作り方と、frontend・backend のセットアップ・検査・試験のコマンドです。2026-10-23 に AGENTS.md から文を変えずに移しました（ADR-1040 段3a）。目次 [docs/INDEX.md](../INDEX.md) の章A から辿ります。

## 手元の venv

- 手元の venv は `/usr/local/bin/python3.12 -m venv <場所>` で作る。Sales Anchor の作業場所で 3.12 以外の venv 作成・pip install は見張り（`~/.claude/scripts/python-version-guard.py`）が止める。変数経由などは防げない

## セットアップ & 実行コマンド

### Frontend
```bash
cd frontend && npm install
npm run dev        # 開発サーバー（port 5173）
npm run build      # 本番ビルド（tsc + vite build）
npm run check:all  # 全静的チェック（CI と同一）
npm run test:unit  # ユニットテスト（vitest）
```

### Backend
```bash
cd backend && pip install -r requirements-dev.txt
make lint-ci   # ruff / bandit / mypy（Docker 不要）

# pytest を含む全チェック（postgres + redis の Docker 起動が必要）
docker compose up -d postgres redis
make check     # lint-ci + pytest（カバレッジ 60% 以上）
```

> **重要**: `make test`（pytest）は Docker が必須。Docker なし環境では `make lint-ci` のみ実行すること。

> 仮想マシンが要る試験は Mac で作らず docs/ops/runner-commands.md の該当節（§10）に従う。
