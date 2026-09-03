# PARITY-03 ProductMasterDrawer FE — design.md

作成日: 2026-09-03  
ブランチ: release/parity03-product-master-drawer-fe  
参照: docs/handoff/parity03-product-master-drawer-fe/recon.md  
対象ADR: ADR-154（GAS→Python マイグレーション方針）、ADR-067（CSS デザイントークン）

---

## 目的

GAS `ProductMasterDrawer.tsx` を React に移植し、仕入元詳細ページの  
「修正する → (Phase 3)」ボタンからドロワーを開けるようにする。

---

## KGI

仕入元詳細ページで `review_issues` に `PRODUCT_MASTER_UNREGISTERED` / `PRODUCT_ID_UNRESOLVED` / `EXCLUDED` を持つアイテムに対して、ドロワーが正常に開き、各モードの操作が完了できること。

---

## コンポーネント構成

```
SupplierDetailView
└── ProductMasterDrawer（overlay: fixed drawer）
    ├── pmd-backdrop（クリックで閉じる）
    └── pmd-drawer（aside）
        ├── pmd-head（タイトル・閉じるボタン）
        └── pmd-body
            └── MasterMaintenanceSection（review_issues でモード切替）
                ├── RegistrationSection（PRODUCT_MASTER_UNREGISTERED）
                ├── SearchKeywordSection（PRODUCT_ID_UNRESOLVED）
                └── ExcludedSection（EXCLUDED）
```

---

## API マッピング

| エンドポイント | メソッド | 用途 |
|---|---|---|
| `/tcg/products/registration-form` | GET | B-1: 登録フォーム（ルックアップ選択肢取得） |
| `/tcg/products/check-duplicates` | POST | B-2: 重複候補チェック |
| `/tcg/products` | POST | B-3: 商品マスタ新規登録 |
| `/tcg/products/search` | GET | B-4: 商品名検索 |
| `/tcg/products/:id/search-keywords` | POST | B-5: 検索KW追記 |

---

## CSS 設計

- クラスプレフィックス: `pmd-*`（既存 CSS との衝突回避）
- 値はすべて CSS 変数（ADR-067）
- コンポーネントローカルトークン: `--pmd-max-w: 480px`、`--pmd-textarea-min-h: 72px`
- stylelint `no-descending-specificity` 対応: `pmd-*` セクションを `.supplier-detail-items` より前に配置

---

## 検証方法

| KGI項目 | 観測可能な事象 |
|---|---|
| PRODUCT_MASTER_UNREGISTERED | 「修正する」ボタン押下 → 商品マスタ新規登録フォームが表示される |
| PRODUCT_ID_UNRESOLVED | 「修正する」ボタン押下 → マスタ検索・検索KW追記フォームが表示される |
| EXCLUDED | 「修正する」ボタン押下 → 除外対象メッセージが表示される |
| 登録完了 | 「商品マスタに登録」→「登録が完了しました」メッセージ表示 |
| KW追記完了 | 「キーワードを追記」→「検索キーワードを追記しました」メッセージ表示 |
