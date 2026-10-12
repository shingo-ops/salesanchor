# design: 全マスタパネルDrawer化

参照: [recon.md](docs/handoff/master-panel-detail-view/recon.md)

## 対象ADR
- ADR-144: UIガバナンス（金型準拠）

## あるべき姿
全マスタパネルの操作UIをProductMasterPanelと統一する。
- 行クリック → Drawer（右スライドパネル）で詳細表示・編集
- テーブルからコード列・編集ボタン列・削除ボタン列を廃止
- Drawer footerに戻る・保存（削除対応パネルは削除も）ボタン配置

## KGI / KPI

| 基準 | 検証方法 |
|------|---------|
| 全13マスタで行クリック→Drawer展開が動作する | 手動確認（各パネルで行クリック） |
| テーブルにcode列・編集ボタン・削除ボタンが表示されない | 手動確認（テーブルレンダリング） |
| Drawer内で編集・保存が動作する | 手動確認（値変更→保存→一覧反映） |
| ESLint・型エラーが0件 | `npm run lint` |

## 変更方針

### 共通パターン（ADR-144金型）
1. `import { Modal }` → `import { Drawer }` に変更
2. テーブルcolumnsから `code`, `_edit`, `_delete` 列を削除
3. `<Modal>` → `<Drawer>` に置換
4. Drawer footerに `HeaderButton` で戻る・保存・削除ボタン配置

### 複数Modal使用パネルの注意
- SupplierMasterPanel / ConditionsMasterPanel / UnitMasterPanel は編集Modal以外のModalも保持
- 編集用Modalのみ Drawer に変更し、他Modalは維持

## 外部・過去事例の参照と我々への応用
- ProductMasterPanel（同リポジトリ）: 同じ金型を先行採用済み。13パネルはこのパターンに統一する。
- supplier-master-drawer（過去作業）: Supplier系でのDrawer化実績あり。

## 維持の仕組み
- ADR-144 UIガバナンス: 生Modal使用時はESLintではなくコードレビューでブロック
- 守り手: `frontend/src/pages/super-admin/components/*MasterPanel.tsx` / Hikky-dev (code-reviewer)
