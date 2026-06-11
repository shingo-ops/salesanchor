# recon — ADR-127 Phase 2c ボタン色修正

**仕事名**: adr-127-phase2c  
**日付**: 2026-06-11  
**対象ADR**: ADR-127  
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/pages/company-detail/CompanyDetailPage.tsx:118` | 登録リンクボタンの className が `btn-sm` のみ（btn-primary 不足） |
| `frontend/src/components.css:60` | `.btn-primary` アクセントカラー定義 |
| `frontend/src/components.css:66` | `.btn-primary:disabled` グレー無効表示定義 |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | `btn-sm` だけでは disabled 時にグレーにならないか | components.css:66 で確認 — `btn-primary:disabled` のみグレー | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
