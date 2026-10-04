---
mode: handoff
---
# 実装カード 便C-1: API型契約の土台（スキーマと型の生成＋ずれ検査）

- 根拠: ADR-1005（Accepted 2026-10-04）、design.md の便C
- 現状調査（2026-10-04、origin/main 基準。Sonnet が実行した結果）:
  - `from app.main import app; app.openapi()` は、DBも Redis もない状態で `ENVIRONMENT=test` を付ければ成功する。結果は paths 442、schemas 554。
    - Python 3.12.8 で実行し、入れた依存は `backend/requirements.txt` だけ。
    - lifespan、Firebase の初期化、Redis への接続は、どれも走らない。
    - `app.services.email_sender` と `app.tasks.data_deletion` は import されない。
  - `scripts/` の下は、process-artifacts gate の DANGEROUS_PATTERNS に当たる（`scripts/check-process-artifacts.js:110-135`）。そのため、生成スクリプトは `scripts/` に置かない。
  - `.github/workflows/workflow-lint.yml` は PO 本人の GO が必要なので触らない。job は別ファイルとして新しく作る。
  - `frontend/eslint.config.js` には ignores が無い。生成物を `frontend/src` に置くと lint の対象になる。
  - CI の Node は 22、Python は 3.12、依存の導入には uv を使っている（`.github/workflows/test.yml:72,82,153,165`）。
- この便の範囲: 生成とずれ検査の土台を作るところまで。手書き型の置き換えと、ruleset への必須登録は別の便で行う。
- この便で保証すること: backend の API の形を変えたのに生成物を更新していない PR は赤になる。PR の差分に API の形の変化が必ず出る。
- この便では保証しないこと: 画面のビルドが赤になること。手書き型を生成型に置き換えた画面にしか効かないため、次の便以降になる。

## 変更するファイル（変更前 → 変更後）

### 1. 新規: backend/tools/export_openapi.py
```python
"""FastAPI の OpenAPI スキーマを、サーバーを起動せずに書き出す（ADR-1005）。"""
import json
import sys
from pathlib import Path

from app.main import app


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python -m tools.export_openapi <output.json>", file=sys.stderr)
        return 2
    out = Path(sys.argv[1])
    out.parent.mkdir(parents=True, exist_ok=True)
    schema = app.openapi()
    out.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```
- 実行方法: `cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/src/api/generated/openapi.json`

### 2. 変更: frontend/package.json
- devDependencies に `openapi-typescript` を追加する。
  - 版は、実装の時点で `npm view openapi-typescript version` の結果を確認し、`^` を付けずに固定する。カードの記録欄にその版を残す。
  - lockfile は Single-Writer Rule に従う。worktree の中で `npm install -D -E openapi-typescript@<版>` を1回だけ実行する。
- scripts に次の2つを追加する。
  - `"generate:api-types": "openapi-typescript src/api/generated/openapi.json -o src/api/generated/schema.d.ts"`
  - `"check:api-types": "openapi-typescript src/api/generated/openapi.json -o src/api/generated/schema.d.ts --check"`
  - `--check` が使えることは、実装時に `npx openapi-typescript --help` の出力で確認する。使えなかった場合は止まって報告する。

### 3. 新規（生成物）: frontend/src/api/generated/openapi.json と frontend/src/api/generated/schema.d.ts
- 上の 1 と 2 で生成し、そのままコミットする。手で編集してはいけない。

### 4. 変更: frontend/eslint.config.js
- 配列の先頭に `{ ignores: ["src/api/generated/**"] },` を1行追加する。生成物を lint の対象から外すため。
- それ以外の行は変えない。

### 5. 新規: .github/workflows/api-contract-check.yml
- job 名は `API contract is up to date`。
- `on: pull_request: branches: [main]` とし、paths は指定しない。毎回動かすのは、将来必須チェックにしたとき skipped で詰まらないようにするため。
- 手順:
  1. `actions/checkout@v5` を使う。
  2. `actions/setup-python@v5` で `python-version: '3.12'` を指定し、`astral-sh/setup-uv@v4` を入れて、`working-directory: backend` で `uv pip install --system -r requirements.txt` を実行する。
  3. `cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/src/api/generated/openapi.json` を実行する。
  4. `actions/setup-node@v5` で `node-version: '22'` を指定し、`cd frontend && npm ci` を実行してから `npm run generate:api-types` を実行する。
  5. `git diff --exit-code -- frontend/src/api/generated/` を実行する。差があれば、「`backend/tools/export_openapi.py` と `npm run generate:api-types` を実行して、生成物をコミットしてください」と表示して exit 1 にする。

## 触らない範囲
- 既存の型ファイルと、画面のコード。
- ruleset（必須登録は別の便で行い、PO本人の permit-danger が必要）。
- `.github/workflows/workflow-lint.yml`、`deploy.yml`、`scripts/` の下。
- backend のルーター（`response_model` の追加は別の便で行う）。

## 検証（実装役が実行し、生出力を貼る）
| 基準 | 検証方法 |
|---|---|
| 生成が同じ結果になる | 生成を2回実行し、2回目に `git diff --exit-code frontend/src/api/generated/` が 0 で終わる |
| ずれを検出できる | 確認用のブランチ（PR にしない）で backend の response_model のフィールド名を1つ変え、生成すると diff が出ること（＝CIが赤になる条件）を確認し、変更を戻す |
| 既存の検査が壊れていない | `cd frontend && npx tsc --noEmit`、`npm run lint`（エラー0件、警告数が変わらない）、`npm run check:all` |
| backend は変わっていない | `git diff --stat origin/main...HEAD -- backend/app` が空 |
| CI | PR で `API contract is up to date` が pass になる |

## 分岐（止まる条件）
- 生成が2回で一致しない場合（スキーマが毎回変わる）: 止まって報告する。sort_keys で解決しない場合は、設計者が判断する。
- `--check` が使えない場合、または openapi-typescript が生成に失敗した場合: エラーの全文を貼って止まる。
- `npm install` で依存の衝突が起きた場合: 止まる。`--force` や `--legacy-peer-deps` は使わない。
- CI で import が失敗した場合（ローカルと違う結果になった場合）: ログの全文を貼って止まる。

## GO
- frontend/src と .github/workflows を変更するので、process-artifacts gate は GO 記録を必要とする。マージの前に、PO本人の「GO #<PR番号>」を受け取ってから転記する。

## 戻し方
- PR を revert する。実行時に動くコードには影響しない。

## 記録欄（実装時に記入する）
- openapi-typescript の版:
- 生成物の行数（openapi.json / schema.d.ts）:
