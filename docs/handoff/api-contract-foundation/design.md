# design: API型契約の土台（便C-1）

- 参照:
  - 現状調査: docs/handoff/api-contract-foundation/recon.md
  - ADR: ADR-1005（ファイル docs/adr/ADR-1005-api-contract-and-wiring-ledger.md は PR #3942 にあり、PO 承認済みだが main には未マージ）
  - 関連ADR: ADR-067、ADR-144
- 実装カード: PR #3942 の docs/handoff/cross-dept-integrity-foundation/card-c1.md
- 承認:
  - 2026-10-04 PO が ADR-1005 を承認
  - 2026-10-05 PO がこのカードどおりの実装と PR 作成を承認（チャット）
  - マージ前に PO 本人の「GO #番号」が必要

## 変更前 → 変更後
| ファイル | 変更前 | 変更後 |
|---|---|---|
| `backend/tools/export_openapi.py` | 無い | 新規。`app.openapi()` を、キーを並べ替えた JSON（`sort_keys=True`）で書き出す |
| `frontend/package.json` | 型生成の道具が無い | devDependency に `openapi-typescript` を 7.13.0 で固定して追加。scripts に `generate:api-types` と `check:api-types` を追加。lint-staged の `eslint --max-warnings=0` に `--no-warn-ignored` を追加（生成物が ignores 対象のため、commit 時の「File ignored」警告で pre-commit が失敗するのを防ぐ） |
| `frontend/package-lock.json` | — | `npm install -D -E` を1回実行した結果（248行追加・3行削除） |
| `frontend/eslint.config.js` | ignores が無い | 先頭に `{ ignores: ["src/api/generated/**"] }` を1行追加 |
| `frontend/src/api/generated/openapi.json`、`frontend/src/api/generated/schema.d.ts` | 無い | 生成物。手で編集しない |
| `.github/workflows/api-contract-check.yml` | 無い | 新規ジョブ「API contract is up to date」。スキーマと型を作り直し、コミット済みのものと違えば赤にする |

## 触らない範囲
- backend/app 配下の実装（`git diff --stat origin/main...HEAD -- backend/app` が空であること）
- 既存の型ファイルと画面のコード
- ruleset（このジョブを必須チェックに登録するのは別便。PO 本人の permit-danger が必要）
- `.github/workflows/workflow-lint.yml`、`.github/workflows/deploy.yml`、`scripts/` 配下

## このPRで保証すること・しないこと
- 保証すること: backend の API の形を変えたのに生成物を更新していない PR は、赤になる。API の形が変わると、PR の差分に必ず現れる。
- 保証しないこと: 画面のビルドが赤になること。手書きの型を生成された型に置き換えた画面にしか効かないため、次の便以降で扱う。

## 受入基準
| 基準 | 検証方法 |
|---|---|
| 生成が毎回同じ結果になる | 2回目に生成したあと、`git diff --exit-code -- frontend/src/api/generated/` が 0 で終わる（実測済み。shasum が一致） |
| ずれを検出できる | `backend/app/schemas/close_reason.py` の `sort_order` を一時的に変えて生成すると、diff が出る（実測済み。schema.d.ts の差分は `-sort_order` と `+sort_order_x`。変更は元に戻した） |
| 既存のチェックが壊れていない | `npx tsc --noEmit` がエラー0件、`npm run lint` がエラー0件・警告139件（main と同じ数）、`npm run check:all` の25タスクがすべて成功（実測済み） |
| CI | PR で「API contract is up to date」が pass になる |

## 外部・過去事例の参照と我々への応用
- 外部（公式ドキュメント）:
  - FastAPI はサーバーを起動しなくても `app.openapi()` でスキーマを返す（Context7 /websites/fastapi_tiangolo）。
  - openapi-typescript は CLI で型を生成でき、`--check` で生成物が最新かを確かめられる（Context7 /websites/openapi-ts_dev、ローカルの `--help` でも確認）。
  - 我々への応用: 起動しなくてよいので、CI で DB を用意せずに実行できる。
- 社内の過去事例: `scripts/generate-adr-index.js --check` は、必須チェック「ADR index is up to date」として運用されている。我々への応用: 同じ「生成して差分を見る」方式にして、運用の覚え方をそろえる。

## 維持の仕組み
- 守り手: `.github/workflows/api-contract-check.yml`（ずれを赤にする）
- 守り手: `backend/tools/export_openapi.py`（スキーマの正本を書き出す、唯一の入口）

## リスクと戻し方
- リスク: 生成物が大きい（openapi.json 65,055行、schema.d.ts 38,566行）。実行時の動作には影響しない。
- 戻し方: この PR を revert する。
