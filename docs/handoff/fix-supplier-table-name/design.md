# design: fix-supplier-table-name

**recon**: `docs/handoff/fix-supplier-table-name/recon.md`

## KGI

解析精度管理パネルで「データベースエラー」（relation "tcg_suppliers" does not exist）が0件になること。

## 変更方針

`tcg_suppliers` を `tenant_suppliers` に全置換（文字列置換のみ・ロジック変更なし）。

| 基準 | 検証方法 |
|------|---------|
| backend/app/ および backend/tests/ に `tcg_suppliers` が残らない | `grep -rn 'tcg_suppliers' backend/app/ backend/tests/` が空 |
| 解析パネルDBエラーが消える | 本番デプロイ後に解析精度管理パネルを開いてエラーなし確認 |

## 外部・過去事例の参照と我々への応用

PostgreSQLテーブルリネーム後のコード追従パターン。
`ALTER TABLE tcg_suppliers RENAME TO tenant_suppliers` 適用済み（ADR-072 テナントスキーマ命名規則に合わせたリネーム）→ コード側の文字列参照を一括更新する手法は標準的な保守作業。

## 守り手（ロールバック）

`git revert <commit>` で即時ロールバック可能。DBには触らない。

## 維持の仕組み

守り手: migration 適用後はコード側の grep チェックをCIに追加する（別途対応）。
テーブルリネーム migration には必ずコード追従PRをセットにする運用で再発防止。

## 触らないもの

- `backend/migrations/` 配下（既適用済み）
- フロントエンド一切
