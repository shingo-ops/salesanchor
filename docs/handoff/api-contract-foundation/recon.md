# recon: API型契約の土台（便C-1）

- 基準: origin/main（worktree 作成時の HEAD は `225c0c0ad`、BASE_OK）
- 親テーマ: cross-dept-integrity-foundation（PR #3942）。根拠の ADR は ADR-1005（Accepted 2026-10-04）
- 調査: Sonnet（読み取りと、ローカルでの試行）。判断: Opus

## 事実
- フロントの API レスポンス型はすべて手書きで、型生成の道具も、CI での照合も無い（`frontend/package.json` の devDependencies に該当なし）。
- エンドポイントは612件ある。`response_model=` が付いているのは377件、戻り値の型注釈だけのものが80件、どちらも無いものが155件（backend/app/routers/ 配下の .py 114ファイルを ast で集計。2026-10-04）。
- サーバーを起動しない形で `from app.main import app; app.openapi()` を、DB と Redis が無い状態、`ENVIRONMENT=test`、Python 3.12.8、`backend/requirements.txt` の依存だけで実行し、成功した。paths は442件、schemas は554件だった。lifespan・Firebase の初期化・Redis への接続は、どれも動かない（lifespan は `backend/app/main.py:112-150` 付近）。
- `scripts/` 配下は process-artifacts gate の危険パスに当たる（`scripts/check-process-artifacts.js:110-135`）。`.github/workflows/workflow-lint.yml` は PO 本人の GO が必要。
- `frontend/eslint.config.js` には ignores の設定が無い。
- CI の版は Node 22、Python 3.12 で、依存の導入には uv を使っている（`.github/workflows/test.yml:72`、`.github/workflows/test.yml:82`、`.github/workflows/test.yml:153`、`.github/workflows/test.yml:165`）。CI に新しいジョブを足すときの見本は `.github/workflows/adr-index-check.yml`。
- 本番の API パス /openapi.json は、外部から 404 になる（2026-10-04、curl で確認）。

## 未確認
- CI 上でも import がローカルと同じ結果になるか（PR の CI で確かめる）。
