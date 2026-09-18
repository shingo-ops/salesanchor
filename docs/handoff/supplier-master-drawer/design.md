# design: 仕入元マスタ Drawer化・ボタン整理

## 参照 ADR

- ADR-027: i18n強制（全UI文字列 `t()` 経由）
- ADR-144: UIガバナンス（生select/input禁止、例外は `ui-allow` コメント）

## 変更サマリ

| 項目 | 変更前 | 変更後 |
|------|--------|--------|
| 検索ボタン | ContentToolbar right に HeaderButton | 削除（Enter キーで発火）|
| ヘッダーボタン | 「新規作成」＋「削除」 | 「新規作成」(`common.create`) のみ |
| 行「編集」列 | `_edit` 列 + HeaderButton | 削除（行クリックで Drawer 開く）|
| DataTable selectable | あり | なし |
| 詳細表示 | Modal ポップアップ | Drawer（右スライドパネル）|
| Discord routing | 別 Modal | Drawer 内インライン |

## 新規ファイル

- `frontend/src/features/supplier-master/SupplierDetailDrawer.tsx` — TcgProductDetailDrawer パターンに準拠
- `frontend/src/features/supplier-master/index.ts` — re-export

## KGI/KPI（検証方法）

| 基準 | 検証方法 |
|------|----------|
| 検索フィールドに入力後 Enter で一覧が絞り込まれる | UI 操作で確認 |
| ヘッダーに「新規作成」ボタンのみ表示（削除ボタンなし） | UI で確認 |
| 行クリックで Drawer が右から開く | UI で確認 |
| Drawer 内で保存・削除・Discord routing が動作する | UI で確認 |
| ハードコード日本語なし | grep で確認 |

## 外部事例

- 同プロジェクト内: TcgProductDetailDrawer.tsx（同パターン）
- 同プロジェクト内: TcgProductMasterPage.tsx（ページ側の Drawer 使用パターン）
