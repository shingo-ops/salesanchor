# design: fix-supplier-table-name

## KGI

解析精度管理パネルで「データベースエラー」（relation "tcg_suppliers" does not exist）が0件になること。

## 変更方針

`tcg_suppliers` を `tenant_suppliers` に全置換（文字列置換のみ・ロジック変更なし）。

| 基準 | 検証方法 |
|------|---------|
| backend/app/ および backend/tests/ に `tcg_suppliers` が残らない | `grep -rn 'tcg_suppliers' backend/app/ backend/tests/` が空 |
| 解析パネルDBエラーが消える | 本番デプロイ後に解析精度管理パネルを開いてエラーなし確認 |

## 外部事例

PostgreSQLテーブルリネーム後のコード追従。手法: `ALTER TABLE ... RENAME TO` 適用済み → コード側の文字列参照を一括更新。

## 守り手（ロールバック）

`git revert <commit>` で即時ロールバック可能。DBには触らない。

## 触らないもの

- `backend/migrations/` 配下（既適用済み）
- フロントエンド一切
