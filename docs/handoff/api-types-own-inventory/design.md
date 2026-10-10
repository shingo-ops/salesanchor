# design: 生成型の横展開（便C-4、OwnInventoryPage）

- 参照:
  - 現状調査: docs/handoff/api-types-own-inventory/recon.md
  - ADR: ADR-1005、関連する ADR-144
- 実装カード: docs/handoff/cross-dept-integrity-foundation/card-c3.md の「便C-4」と「両便に共通する手順」
- 見本: PR #4009（便C-2）
- 承認: PO の横展開の承認は設計者経由。マージ前に PO 本人の「GO #番号」が必要。

## 変更前 → 変更後
| ファイル | 変更前 | 変更後 |
|---|---|---|
| `frontend/src/pages/inventory/OwnInventoryPage.tsx` | `OwnInventoryRow` は14フィールドの手書き interface | `components["schemas"]["OwnInventoryResponse"]` の別名にする。`import type { components }` を1行足す。POST の部分と `ActionKind`・`PendingAction` は変えない |

## 触らない範囲
- backend
- 他の画面
- `frontend/package.json` と workflow（配線は #4009 で済んでいる）
- ruleset

## 受入基準
| 基準 | 検証方法 |
|---|---|
| tsc が通る | `npx tsc --noEmit` が exit 0（実測済み） |
| 生成物が無い状態からビルドできる | `git clean -f -X frontend/src/api/generated/` のあとに `npm run build` が exit 0 で `✓ built`（実測済み） |
| API の形がずれると、画面のビルドが赤になる | backend の `physical_qty` を一時的に `physical_qty_x` にして export と生成をし直すと、`npx tsc --noEmit` が exit 2（OwnInventoryPage.tsx の2か所で TS2551）。元に戻すと exit 0（実測済み） |
| 既存の検査が壊れていない | lint は 0 errors・警告139（#4009 の記録と同数）。`check:all` の全タスクが exit 0（実測済み）。この画面のテストは無い |
| CI | PR で `Frontend lint & custom checks` と frontend-check が pass |
| 本番 | マージ後に deploy が success になり、app が 200 を返す。PO が実機で /own-inventory の表示を確認する（単価の見え方は変更前と同じ） |

## 外部・過去事例の参照と我々への応用
- 外部（公式ドキュメント）: openapi-typescript は `components["schemas"]` から型を参照する方式（Context7 /websites/openapi-ts_dev）。我々への応用: 手書きの名前を残して中身だけ生成型の別名にするので、画面側の変更は import 1行と型1行で済む。
- 社内の過去事例（便C-2、PR #4009）: 生成物は commit せず、prebuild と frontend-check の step で生成する方式。我々への応用: 配線済みなので、この便では型の置き換えだけを行う。

## 維持の仕組み
- 守り手: `.github/workflows/frontend-check.yml`（PR で生成と tsc を行い、型のずれを赤にする）
- 守り手: `.github/workflows/api-contract-check.yml`（openapi.json が backend とずれていたら赤にする。main の必須チェック）

## リスクと戻し方
- リスク: 型の置き換えだけで実行時の挙動は変わらない。`unit_price` の型が number から string に変わるが、`toLocaleString()` は string でも型エラーにならず、実行時の値も元から string。
- 戻し方: この PR を revert する。
