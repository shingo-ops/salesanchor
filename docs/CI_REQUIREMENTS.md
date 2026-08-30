# CI 要件仕様書

最終更新: 2026-08-30  
根拠調査: `.github/workflows/` 全ファイル棚卸し

---

## 概要

SalesAnchor CI は **63 ワークフロー** で構成。  
マージ前に必須チェックを全て green にすること。

---

## 1. ブランチ命名ルール（重要）

### main 行き PR は `release/*` または `hotfix/*` からのみ

```
feature/xxx → develop/integrate → release/xxx → main
                                   hotfix/xxx → main
```

- `feat/*`, `fix/*`, `docs/*` など通常ブランチ → main への PR は **base-branch-guard が自動 FAIL**
- 対応: `release/<name>` ブランチを作成し、そこから PR を作る

---

## 2. 必須チェック一覧（ブランチ保護で必須）

| チェック | ワークフロー | 内容 | ローカル再現コマンド |
|---------|------------|------|-------------------|
| pytest (SQLite + PostgreSQL RLS) | test.yml | 全バックエンドテスト | `cd backend && make test` |
| テナントスキーマ整合性チェック | schema-check.yml | テナント差分検査 | テナント4件作成 + dry-run |
| Lint & Dark Mode Check (ADR-067) | e2e.yml | `npm run check:all` (25+ チェック) | `cd frontend && npm run check:all` |
| lint-backend-internal | test.yml | ruff + bandit + mypy | `cd backend && make lint-ci` |
| requirements.txt lint | requirements-lint.yml | テストパッケージ混入検査 | `pip install check-requirements` |
| ADR-072 tenant schema lint | lint-tenant-schema.yml | strict mode | `python3 scripts/lint_tenant_schema.py --mode strict` |
| base-branch-guard | pr-base-check.yml | main 行き PR のブランチ名制約 | 手動確認 |

---

## 3. ゲート一覧（安定確認中・違反はブロックになり得る）

| ゲート | 内容 | ローカル再現 |
|--------|------|------------|
| migration-guard | migration 5段階検査 | 後述 |
| guard-hex-increase (design-token-guard) | frontend hex カラー増加ラチェット | `BASE_SHA=x HEAD_SHA=y bash scripts/check-design-token-ratchet.sh` |
| UI governance gate | pages/ の生 UI 部品検出 | `BASE_SHA=x HEAD_SHA=y node scripts/check-ui-governance.js` |
| process-artifacts gate | SOP/KPI2 宣言、Canonical Docs、外部API 準備確認 | `node scripts/check-process-artifacts.js` |
| dangling-route gate | 削除ルート × 参照残留検査 | `BASE_SHA=x HEAD_SHA=y node scripts/check-dangling-routes.js` |

---

## 4. フロントエンドカスタムチェック詳細

`npm run check:all` が並列実行する主なルール:

| チェック | ルール |
|---------|--------|
| `check:jsx-emoji` | JSX 内の絵文字・▼▲ 等の直書き禁止 → `constants/icons.tsx` の `TABLE_ICONS.sortAsc/sortDesc` を使う |
| `check:css-var-fallbacks` | `var(--xxx, #hex)` フォールバックに hex 禁止 → 変数を `index.css` の `:root` と `:root.force-dark` 両方に追加してから `var(--xxx)` のみ使う |
| `check:dark-parity` | ダーク用変数が `:root.force-dark` に存在するか確認 |
| `check:css-colors` | インライン hex カラーの新規混入禁止 |
| `check:page-layout` | ページレイアウト規約 |
| `check:icon-sync` | アイコン参照同期 |
| `lint` | ESLint (`--max-warnings=0`) |

---

## 5. バックエンド lint 設定

設定: `backend/pyproject.toml` `[tool.ruff]`

- ルール: `E, F, W, I`（基本ルールのみ）
- 除外: `E501, E402, E702, E712`
- 対象: `backend/app/`
- 修正: `ruff check app/ --fix`

よくある違反:
- `I001`: import ブロック未ソート → `ruff check --fix` で自動修正
- `F401`: 未使用 import → `ruff check --fix` で自動修正

---

## 6. migration-guard 5段階検査

新規 migration ファイル追加時は全段階を手動確認:

| 段階 | チェック内容 | 確認方法 |
|------|------------|---------|
| 1 | `models.py` に新 `Column(` → `deploy.yml` に migrate ステップ追記 | `git diff HEAD~1 backend/app/models.py | grep 'Column('` |
| 2 | 新 `migrations/*.sql` → `deploy.yml` または `run_all_migrations.sh` に登録 | ファイル名 `YYYYMMDD_HHMMSS_*.sql` 形式必須 |
| 3 | migration 内に `{schema}` テンプレートリテラル禁止 | `grep '{schema}' migrations/新ファイル.sql` |
| 4 | `REFERENCES public.X` の X が許可リストに存在 | 許可テーブル: tenants, users, products, suppliers 等 24 種 |
| 5 | タイムスタンプ重複なし（main 既存 + PR 内同士） | `git log --oneline main..HEAD` でファイル名確認 |

---

## 7. push 前チェックリスト（必須実行）

```bash
# === バックエンド変更がある場合 ===
cd backend
ruff check app/             # I001/F401 等
bandit -r app/ -lll         # セキュリティ HIGH/CRITICAL
mypy app/ --no-error-summary

# pytest は CI で自動実行されるが、重要変更時はローカルでも実行
# docker-compose up -d postgres redis
# pytest -q --tb=short

# === フロントエンド変更がある場合 ===
cd frontend
npm run check:all           # ADR-067 全25+チェック

# === migration 追加がある場合 ===
# migration-guard 5段階を手動確認（§6 参照）

# === main 行き PR を作成する前 ===
# release/xxx ブランチを経由すること（base-branch-guard §1 参照）
```

---

## 8. PR #3163 (feat/tcg-migration-phase4 → main) の失敗原因と修正方針

| # | 失敗チェック | 原因 | 修正方針 |
|---|------------|------|---------|
| 1 | base-branch-guard | `feat/tcg-migration-phase4` → main は禁止 | `release/tcg-migration-phase4` ブランチを作成し PR を作り直す |
| 2 | guard-hex-increase | 新規ページの hex カラー増加 | hex をトークン変数に置換 |
| 3 | lint-backend-internal | ruff I001/F401 7件 | `ruff check app/ --fix` で自動修正 |
| 4 | Frontend lint (jsx-emoji) | `TcgParallelReportPage.tsx` の ▼▲ 直書き | `TABLE_ICONS.sortAsc/sortDesc` に置換 |
| 5 | Frontend lint (css-var-fallbacks) | `TcgLineImportPage.tsx` の `var(--xxx, #hex)` | `index.css` に変数追加後 hex フォールバック除去 |
| 6 | pytest-run-internal | `test_real_gemini_call_returns_structured_items` — CI に GEMINI_API_KEY なし | 既存テスト。CI シークレットに GEMINI_API_KEY 追加 **または** テストに `@pytest.mark.skipif` を付与 |
| 7-10 | UI governance / process-artifacts / Dark Mode / etc. | frontend lint 失敗の連鎖 / 4・5の修正で解消見込み | 4・5修正後に再確認 |
