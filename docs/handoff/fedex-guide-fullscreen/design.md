# design — fedex-guide-fullscreen

**仕事名**: fedex-guide-fullscreen  
**日付**: 2026-06-23  
**対象ADR**: ADR-087  
**担当**: Hikky-dev

---

## What（何を）

FedEx ETD セットアップガイド専用ページを独立レイアウト化し、ステップインジケーターを常時表示固定（sticky）にする。

## How（どう実装するか）

### Change 1: fullscreen route (App.tsx)

React Router v6 の layout route パターンを使用。`ShellSwitch` ブロックの**前**に新しい layout route を追加:

```tsx
<Route element={<ProtectedRoute><Outlet /></ProtectedRoute>}>
  <Route path="/management-center/integrations/:carrier/setup-guide" element={<CarrierSetupGuidePage />} />
</Route>
```

- `ProtectedRoute` を維持 → auth guard は保持
- `ShellSwitch`（サイドバー＋ヘッダー）は含まない → 全画面表示
- 元の `ManagementCenterPage` 内の setup-guide route を削除

### Change 2: sticky stepper (FedexLabelValidationTab.css)

```css
.etd-stepper {
  position: sticky;
  top: 0;
  z-index: var(--z-dropdown);
  background: var(--bg-primary);  /* ADR-067: CSS var トークン使用 */
  padding-top: var(--space-2);
  padding-bottom: var(--space-2);
}
```

- `--bg-primary` は既存トークン（`#f5f7fa` light / `#0f172a` dark）
- `--z-dropdown: 50` は既存 z-index トークン
- scroll chain: fullscreen = body scroll のため `overflow: hidden/auto` 祖先なし → sticky 正常動作

## KPI / 検証方法

| 基準 | 検証方法 |
|------|---------|
| 認証なしアクセスで `/login` にリダイレクト | 手動確認 |
| ガイドページにサイドバー・ヘッダーが表示されない | 画面確認 |
| スクロール時に①②③④が上端に貼り付く | 画面確認 |
| lint 0 errors / build success | CI |

## 外部事例

React Router v6 のネスト layout route パターン（公式ドキュメント）: 複数の layout を同一ルート階層に並べることで auth を維持しつつシェルを切り替える標準手法。
