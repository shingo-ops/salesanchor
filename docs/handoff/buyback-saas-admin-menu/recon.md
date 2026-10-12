# recon — buyback-saas-admin-menu

**仕事名**: buyback-saas-admin-menu  
**日付**: 2026-09-21  
**対象ADR**: ADR-022  
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/components/DesktopShell.tsx:190` | `saasAdminItems` 配列定義箇所（isSuperAdmin 専用メニュー） |
| `frontend/src/components/DesktopShell.tsx:273` | 削除対象の buyback NavLink（`hasPermission("products.view")` で制御） |
| `frontend/src/components/MobileShell.tsx:156` | 削除対象の buyback エントリ（一般 menuItems 内） |
| `frontend/src/components/MobileShell.tsx:172` | `isSuperAdmin` ブロック（追加先） |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | buyback route 自体の変更が必要か | App.tsx を確認、route は `/buyback-prices` のまま変更不要と確認 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

- `nav.buybackPrices` i18n キーは ja.json / en.json 共に既存。変更不要。
- route `/buyback-prices` は App.tsx で引き続き定義済み。表示制御はサイドバーのみ。
