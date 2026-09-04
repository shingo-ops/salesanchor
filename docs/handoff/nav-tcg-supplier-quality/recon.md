# recon — nav-tcg-supplier-quality（SaaS管理者メニュー削減）

**仕事名**: SaaS管理者サイドメニューを2項目に絞り込み・不要4ページ削除  
**日付**: 2026-09-04  
**対象ADR**: ADR-154  
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/components/DesktopShell.tsx:190` | `saasAdminItems` 配列定義（SQ-02実施後: 2項目 tcg-supplier-quality / fx-rate） |
| `frontend/src/App.tsx:282` | `/super-admin/tcg-supplier-quality` ルート定義（TcgSupplierQualityPage） |
| `frontend/src/App.tsx:267` | `/super-admin/inbound/:id/review` ParseReviewPage ルート（保持） |
| `frontend/src/pages/super-admin/ParseReviewPage.tsx:246` | phase-switch バックエンドAPI呼び出し（削除対象外の根拠） |
| `frontend/src/locales/ja.json:148` | `superAdminFxRate` / `superAdminTcgSupplierQuality` キー（残存・残り4キー削除済み） |
| `frontend/src/locales/en.json:148` | 同上（英語版） |

---

## SQ-01 調査内容

### 1. サイドメニュー定義箇所

`frontend/src/components/DesktopShell.tsx:190` に `saasAdminItems` 配列があり、SQ-01時点では5項目あった。

SQ-02実施後の現在は以下2項目のみ:
```
{ to: "/super-admin/tcg-supplier-quality", labelKey: "nav.superAdminTcgSupplierQuality" }
{ to: "/super-admin/fx-rate",              labelKey: "nav.superAdminFxRate" }
```

### 2. 削除対象4ページ（SQ-01調査時点の状態）

SQ-01時点に存在したが SQ-02 で削除した5ファイル:

| ページ名 | ルートパス | コンポーネントファイル |
|---------|-----------|---------------------|
| SaaS管理マスタ | `/super-admin/masters` | `frontend/src/pages/super-admin/MastersPage.tsx`（削除済み） |
| Discord受信箱 | `/super-admin/inbound` | `frontend/src/pages/super-admin/DiscordInboundPage.tsx`（削除済み） |
| フェーズ切替 | `/super-admin/phase-switch` | `frontend/src/pages/super-admin/PhaseSwitchPage.tsx`（削除済み） |
| 在庫オファー | `/super-admin/inventory-offers` | `frontend/src/pages/super-admin/InventoryOffersPage.tsx`（削除済み） |
| (内部タブ) | MastersPage子要素 | `frontend/src/pages/super-admin/SupplierParseStatsTab.tsx`（削除済み） |

### 3. ParseReviewPage が phase-switch バックエンドAPIを参照している事実

`frontend/src/pages/super-admin/ParseReviewPage.tsx:246` にて:
```
/super-admin/phase-switch/${me.tenant_id}
```
を呼び出している。このバックエンドAPIは PhaseSwitchPage が使っていた同じエンドポイント。ParseReviewPage は独自にこのAPIを参照するため、PhaseSwitchPage 削除後もバックエンド `super_admin_phase_switch.py` は削除不可。

### 4. SupplierParseStatsTab の参照元

SQ-01調査時: `SupplierParseStatsTab` は `MastersPage.tsx` からのみ import されていた。他コンポーネントからの参照なし。MastersPage 削除とともに孤立するため、共に削除対象とした。

### 5. テストファイルの不存在

SQ-01 時点で削除対象5ファイルに対応するテストファイル（`*.test.tsx` 等）は存在しなかった。削除による既存テストの破壊リスクなし。

### 6. 翻訳キー（`frontend/src/locales/ja.json:148`）

SQ-01時点に存在した削除対象キー（現在削除済み）:
- `nav.superAdminMasters`
- `nav.superAdminInbound`
- `nav.superAdminPhaseSwitch`
- `nav.superAdminInventoryOffers`

残存キー（現在も存在）:
- `nav.superAdminFxRate`（148行目）
- `nav.superAdminTcgSupplierQuality`（150行目）

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | ParseReviewPage が phase-switch API を参照しているか | `frontend/src/pages/super-admin/ParseReviewPage.tsx:246` で確認 | ✅ 解消済み |
| 2 | SupplierParseStatsTab の参照元が MastersPage のみか | SQ-01 で grep 確認済み | ✅ 解消済み |
| 3 | 削除対象5ファイルにテストが存在するか | SQ-01 で確認。存在しない | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
