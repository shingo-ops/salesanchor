# design: tcg-diagnostics-drawer

**対象ADR**: ADR-154, ADR-144
**recon**: docs/handoff/tcg-diagnostics-drawer/recon.md

## 設計方針

TcgSupplierQualityPage の headerAction に「データ健全性チェック」ボタンを追加し、
押下で DiagnosticsDrawer を開く。4セクションを独立 useEffect で並列取得し、
1セクション失敗でも他は正常表示されるよう設計。

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| ヘッダーに「データ健全性チェック」ボタンが表示される | `frontend/src/pages/super-admin/TcgSupplierQualityPage.tsx` に `headerAction` prop がある |
| ボタン押下でDrawerが開く | `diagOpen` state と `setDiagOpen(true)` がある |
| 4セクション（supplier-channels / suppliers / supplier-name-dupes / orphan-messages）が表示される | `DiagnosticsDrawer.tsx` に4つの `DiagnosticsSection` がある |
| 各セクションがAPI `/tcg/diagnostics/{key}` を呼び出す | `useEffect` 内で `api.get(\`/tcg/diagnostics/${diagKey}\`)` を呼び出している |
| supplier-channelsでchannel_count>=2の行が赤表示 | `highlight` prop で `typeof row.channel_count === "number" && row.channel_count >= 2` |
| orphan-messagesでnull_channel_count!=0の行が赤表示 | `highlight` prop で `Number(row.null_channel_count) !== 0` |
| ja.json / en.json キー数が一致 | `superAdmin.diagnostics` セクションの同一キー構造 |
| ビルドがエラーなく通る | `npm run build` 成功 |

## 設計選択

### 独立セクション方式
各セクションが独立して `useState` / `useEffect` を持つ。
1セクションのAPIエラーが他に波及しない。

### 既存Drawerコンポーネントを再利用
`components/Drawer.tsx` を使用。Portal + Esc制御を自前実装しない。

### インラインスタイル（CSS変数のみ）
テーブルのスタイルはインラインで CSS 変数（`var(--color-*)` 等）を使用。
ページ固有の1回限りのスタイルのため専用CSSクラス不要。

### ボタン配置
`PageLayout` の `headerAction` prop 経由（ADR-144: `position: fixed` 直接配置禁止）。

## 外部・過去事例

- ADR-154 の固定SQL診断API設計（バックエンド）: セキュリティ上の理由で任意SQL実行不可、`_ALLOWED_KEYS` frozenset で制限
- OWASP: Fixed SQL / Stored SQL Map standard — SQL文字列補間を避け、固定クエリのみ許可するパターン
- 既存の Drawer 使用例: `frontend/src/features/tcg-analysis-review/SupplierDetailView.tsx`

## 維持の仕組み

守り手: `frontend/src/features/tcg-analysis-review/DiagnosticsDrawer.tsx` — 型定義で `SectionProps.diagKey` の型を文字列にしているため、バックエンドキーの変更は手動追従が必要（backend/tests/test_tcg_diagnostics.py がバックエンド側を守る）
