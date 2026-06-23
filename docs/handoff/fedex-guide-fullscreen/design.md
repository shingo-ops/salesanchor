# Phase 3 設計 — fedex-guide-fullscreen

**対象ADR**: ADR-087
**recon**: docs/handoff/fedex-guide-fullscreen/recon.md
**日付**: 2026-06-23
**担当**: Hikky-dev

---

## 外部・過去事例の参照と我々への応用

- React Router v6 公式ドキュメント（layout routes パターン）→ 複数の layout route を同一階層に並べることで auth を維持しながらシェルを切り替える標準手法。ManagementCenterPage を外したルートを ProtectedRoute+Outlet のみの layout route として追加することで実現。
- ADR-087（hub-shell-layout-standard）→ サイドバー不要な専用ページは hub-shell を外して独立ページとして扱う方針に準拠。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 認証なしで `/management-center/integrations/fedex/setup-guide` にアクセスすると `/login` にリダイレクト | 手動確認 |
| ガイドページにサイドバー・ヘッダーが表示されない | 画面確認 |
| スクロール時に `.etd-stepper`（①②③④）が上端に貼り付く | 画面確認 |
| lint 0 errors / TypeScript build 成功 | CI（Frontend lint & custom checks）|

---

## 技術 How

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
  background: var(--bg-primary);
  padding-top: var(--space-2);
  padding-bottom: var(--space-2);
}
```

- scroll chain: fullscreen = body scroll のため `overflow: hidden/auto` 祖先なし → sticky 正常動作
- `--bg-primary` は既存トークン（ADR-067 準拠）

---

## 弊害・トレードオフ

- fullscreen ページではパンくず・戻るボタンなし → CarrierSetupGuidePage 内の PageLayout が最小ヘッダーを提供するため問題なし

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | App.tsx routing 変更（Outlet import + layout route 追加・旧 route 削除） | Generator |
| 2 | FedexLabelValidationTab.css sticky 追加 | Generator |
| 3 | lint / build 確認 | Generator |

---

## 継続

- 完了後の監視: 本番デプロイ後に `/management-center/integrations/fedex/setup-guide` へのアクセスで正常表示確認
- 次フェーズへの引き継ぎ: 他キャリア（DHL/UPS）対応時は同じ layout route を再利用
