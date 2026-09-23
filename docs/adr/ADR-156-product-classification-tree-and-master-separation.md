# ADR-156: 商品分類ツリーと共用マスタ分離

- **Status**: Accepted
- **Date**: 2026-09-21
- **Author**: Hikky-dev (Claude Code)
- **Approved by**: Shingo (PO)

---

## 背景

TCG 商品マスタ整備（ADR-155）の結果、`tcg_type_master`（中分類）が TCG 固有のテーブルとして存在するが、
ONE PIECE や他ジャンルの商品追加を見据えると、大分類を持たない2層構造では不十分となった。

また、コンディション定義（PSA グレード・国産状態など）が商品ラインに依存した形で管理されておらず、
将来的な多ジャンル対応時に重複・不整合が生じるリスクがある。

---

## 決定

商品分類を以下の3層ツリー構造で管理する。

```
product_kinds（大分類）
  └── type_master（中分類: 旧 tcg_type_master）
        └── product_lines（小分類）
              └── products（商品）
```

また、コンディション定義を `condition_definitions` テーブルとして独立させ、
`product_lines` に紐付ける形で管理する。

### Phase 1（本 ADR の対象）: DB 基盤（DDL のみ）

| migration | 変更内容 |
|-----------|---------|
| 20260921_010000 | `product_kinds` 新設 |
| 20260921_020000 | `tcg_type_master` → `type_master` リネーム + 互換ビュー + `kind_id` FK 追加 |
| 20260921_030000 | `product_lines` に `type_id` FK 追加 |
| 20260921_040000 | `condition_definitions` 新設 |
| 20260921_050000 | `conditions.condition_def_id` / `units.line_id` FK 追加 |

### 互換ビュー

`public.tcg_type_master` 互換ビューを作成し、既存コードを透過的に動作させる。
廃止予定: 2026-12-21 以降（ADR-156 Phase 2）。

---

## 理由

1. **後方互換**: 互換ビューにより既存コード（50 箇所以上）を一括変更せずに移行できる
2. **冪等性**: 全 migration を `IF NOT EXISTS` / `DO $$ BEGIN...END $$` で実装
3. **DDL のみ**: ADR-155 準拠として INSERT/UPDATE/DELETE を含まず、データ整合性リスクをゼロにする
4. **守り手**: migration-guard.yml がチェック4（PUBLIC_TABLES 照合）・チェック7/8（INSERT 禁止）で保護

---

## 結果

- `product_kinds`・`type_master`・`condition_definitions` が PUBLIC_TABLES に追加される
- 既存の `tcg_type_master` 参照コードは互換ビュー経由で透過動作する
- Phase 2 以降のデータ投入は CSV アプリ（ADR-155）経由で行う

---

## Phase 2 以降の残作業（本 ADR 対象外）

- 互換ビュー廃止（2026-12-21 以降）
- バックエンドコードの `tcg_type_master` → `type_master` 書き換え
- `product_kinds`・`type_master`・`product_lines` に初期データ投入（CSV アプリ経由）
- `condition_definitions` に初期コンディション定義投入（CSV アプリ経由）

---

## 参照

- [ADR-155: 商品マスタデータの更新手段を CSV 取り込みとアプリ画面に一本化する](./ADR-155-product-master-ssot-csv-app.md)
- [ADR-083: 共用マスタ SSOT 方針](./ADR-083-shared-master-ssot.md)
- [design.md](../handoff/product-classification-tree/design.md)
- [recon.md](../handoff/product-classification-tree/recon.md)
