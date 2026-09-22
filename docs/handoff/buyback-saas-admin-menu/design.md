# 設計 — buyback-saas-admin-menu

**対象ADR**: ADR-022  
**recon**: docs/handoff/buyback-saas-admin-menu/recon.md  
**日付**: 2026-09-21  
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- 該当なし：今回は既存 `saasAdminItems` 配列への1エントリ追加のみ。パターンは ADR-022 の SaaS 管理者メニュー設計に準拠済みで新規設計要素なし。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| SaaS管理者ユーザーのサイドバーに「買取相場」が表示される | 人手: isSuperAdmin=true で `/` にアクセスしサイドバー確認 |
| 一般ユーザーのサイドバーに「買取相場」が表示されない | 人手: isSuperAdmin=false で `/` にアクセスしサイドバー確認 |
| `/buyback-prices` ページが正常動作 | 人手: SaaS管理者でページ遷移確認 |
| MobileShell テスト PASS | CI: `vitest run MobileShell.test.tsx` |

---

## 技術 How・KPI

- KPI: 買取相場メニューが一般ユーザーに表示されなくなる（0件）
- 技術選択: 既存 `saasAdminItems` 配列にエントリ追加（新規パターン不要）

---

## 弊害・トレードオフ

- 一般テナントの `products.view` 権限ユーザーが buyback ページへの導線を失う → 意図的（PO 要件）。URL 直接入力は引き続き可能。

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | DesktopShell: 一般 NavLink 削除 + saasAdminItems 追加 | Generator |
| 2 | MobileShell: 一般 menuItems から削除 + isSuperAdmin ブロックに追加 | Generator |
| 3 | MobileShell.test.tsx: 項目数アサーション更新（6→5） | Generator |

---

## 継続

- 完了後の監視: なし（UI 配置変更のみ）
- 次フェーズへの引き継ぎ: なし
