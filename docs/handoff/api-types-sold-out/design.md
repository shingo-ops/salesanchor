# design: 生成型の初採用（便C-2、TcgSoldOutPage）

- 参照:
  - 現状調査: docs/handoff/api-types-sold-out/recon.md
  - ADR: ADR-1005（PR #3942 で PO 承認済み。main にはまだマージしていない）、関連する ADR-144
- 実装カード: PR #3942 の docs/handoff/cross-dept-integrity-foundation/card-c2.md
- 承認: 2026-10-06、PO がカードどおりの実装と PR 作成を承認（チャット）。マージ前に PO 本人の「GO #番号」が必要。

## 変更前 → 変更後
| ファイル | 変更前 | 変更後 |
|---|---|---|
| `frontend/package.json` | predev・prebuild は `npm run generate:icon-sizes` だけ | 末尾に `&& npm run generate:api-types` を追加。本番の Docker ビルドでも、型の生成が tsc より先に走る |
| `.github/workflows/frontend-check.yml` | tsc の前に型の生成が無い | `npm ci` の直後に `npm run generate:api-types` の step を1つ追加 |
| `frontend/src/features/tcg-sold-out/soldOutApi.ts` | `SoldOutItem` と `SoldOutResponse` は手書きの interface。`supplier_id` と `product_id` が `string | null` になっていて、実際の形と違っていた | 生成型 `SoldOutResultItem` と `SoldOutResultsResponse` の別名にする。`SourceScope` は operation の query パラメータから導出する |

## 触らない範囲
- backend
- 画面 `frontend/src/pages/super-admin/TcgSoldOutPage.tsx`（型の名前を変えないので、import はそのまま）
- `frontend/Dockerfile`
- ruleset
- deploy.yml
- `scripts/` 配下

## 受入基準
| 基準 | 検証方法 |
|---|---|
| 生成物が無い状態からビルドできる | `git clean -f -X frontend/src/api/generated/` のあとに `npm run build` を実行して成功する（実測済み。`✓ built`） |
| API の形がずれると、画面のビルドが赤になる | backend の `raw_memo` を一時的に別名にして生成し直すと、`npx tsc --noEmit` が exit 2 で失敗する（TcgSoldOutPage.tsx の TS2551 と test の TS2561）。元に戻すと exit 0（実測済み） |
| 既存の検査が壊れていない | lint は 0 errors・警告139（main と同数）。`check:all` の25本がすべて成功。TcgSoldOutPage.test.tsx は 8/8 成功（実測済み） |
| CI | PR で `Frontend lint & custom checks` と frontend-check が pass |
| 本番 | マージ後に deploy が success になり、app が 200 を返す。PO が実機で /super-admin/tcg-sold-out の表示を確認する |

## 外部・過去事例の参照と我々への応用
- 外部（公式ドキュメント）: openapi-typescript は、`components["schemas"]` と `operations` から型を参照する方式（Context7 /websites/openapi-ts_dev）。我々への応用: 手書きの名前を残したまま、中身だけ生成型の別名にする。こうすると画面側の変更が0行で済む。
- 社内の過去事例（便C-1、PR #3971）: 生成物の型ファイルを commit すると hex 検査と deprecated 列の検査に当たったため、生成物は commit せずに、その都度生成する方式にした。我々への応用: この方式のままだと、ビルド前と tsc 前に生成を必ず入れる必要がある。今回の配線はそのためのもの。

## 維持の仕組み
- 守り手: `.github/workflows/frontend-check.yml`（PR で生成と tsc を行い、型のずれを赤にする）
- 守り手: `.github/workflows/api-contract-check.yml`（openapi.json が backend とずれていたら赤にする。main の必須チェック）

## リスクと戻し方
- リスク: 本番の Docker ビルドで型の生成に失敗すると、デプロイが止まる。点検で、devDependencies と api-contract がビルドに含まれることは確認した。マージ後は deploy run の結果で確かめる。
- 戻し方: この PR を revert する。
