# recon — fedex-guide-fullscreen

**仕事名**: fedex-guide-fullscreen  
**日付**: 2026-06-23  
**対象ADR**: ADR-087  
**担当**: Hikky-dev

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/App.tsx:1` | react-router-dom import — `Outlet` が未 import であることを確認 |
| `frontend/src/App.tsx:146` | `ProtectedRoute` + `ShellSwitch` の layout route ブロック開始位置 |
| `frontend/src/App.tsx:341` | `integrations/:carrier/setup-guide` が ManagementCenterPage 内に配置されていたことを確認 |
| `frontend/src/components/ProtectedRoute.tsx:1` | `{children}` を render するシンプルな auth guard コンポーネント |
| `frontend/src/pages/integrations/FedexLabelValidationTab.css:46` | `.etd-stepper` に sticky が未設定であることを確認 |
| `frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:40` | `<nav className="etd-stepper">` が StepIndicator の最上位要素 |
| `frontend/src/index.css:1` | `--bg-primary` トークンが `:root` / `:root.force-dark` 両方に定義済みを確認 |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | fullscreen route で scroll chain が壊れないか | App.tsx で shell なし = body scroll → sticky 動作確認 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
