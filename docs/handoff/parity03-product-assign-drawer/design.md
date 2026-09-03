# PARITY-03 商品割り当て変更ドロワー — design.md

**対象ADR**: ADR-154
**recon**: docs/handoff/parity03-product-assign-drawer/recon.md
**日付**: 2026-09-03
**担当**: Dev

---

## 外部・過去事例の参照と我々への応用

- ADR-154（GAS→Python 段階移植）: 人間の判断を優先する原則。MANUAL 保護（PR #3248）と連動。
- PR #3248: `pid_basis='MANUAL'` 保護実装済み。本 PR で初めて MANUAL をセットする仕組みを追加。
- PR #3247: `badge-success` CSS 追加済み。確認済みバッジはこれを利用。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 全行に「修正する」ボタンが表示される | SupplierDetailView で解決済み行を確認 |
| 解決済み行のドロワーに「商品の割り当て変更」が表示される | ドロワーを開いて ProductAssignSection 確認 |
| 「商品を変更する」で item_corrections + analysis_results が更新される | POST /corrections → DB確認（pid_basis='MANUAL'） |
| 「確認済みとして記録」で item_corrections に記録される | POST /corrections → DB確認（system_value=human_value） |
| 確認済み行に「確認済み」緑バッジが表示される | 画面リロード後のバッジ確認 |
| product_title がドロワーに表示される | BE SELECT に p.japanese_title 追加確認 |
| CI pytest が全テスト PASS | CI `pytest-run-internal` ジョブ green |

---

## 技術 How・KPI

- KPI: 7 基準全通過 / lint clean / process-artifacts gate green
- `ProductAssignSection`: 解決済み行向け新コンポーネント
  - 現在商品表示（product_code + product_title）
  - 商品検索 → 候補リスト → 選択
  - 「商品を変更する」: POST /corrections (human_value ≠ system_value) → analysis_results UPDATE（pid_basis='MANUAL'）
  - 「確認済みとして記録」: POST /corrections (human_value = system_value) → 記録のみ
  - 成功後: onSaved() コールバックで一覧リフレッシュ
- `PRODUCT_CONFIRMED` バッジ: `item_corrections` に確認記録がある行に緑バッジ表示
- product_uuid を各所に追加: search results / analysis review response で UUID を渡す

---

## 弊害・トレードオフ

- item_corrections_svc.py が analysis_results を書くことで「修正保存」の責務が広がる
  - 許容：同一トランザクション、PR #3248 の MANUAL 保護で再解析上書き防止済み
- 一覧リフレッシュは全件再取得（max 500件）: 現規模では問題なし

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | recon.md / design.md 作成 | Dev |
| 2 | reviewIssues.ts に PRODUCT_CONFIRMED 追加 | Dev |
| 3 | tcg_analysis_review_svc.py に product_title / product_uuid / product_confirmed 追加 | Dev |
| 4 | tcg_product_master_svc.py + router に product_uuid 追加 | Dev |
| 5 | item_corrections_svc.py に analysis_results UPDATE 追加 | Dev |
| 6 | ProductMasterDrawer.tsx に ProductAssignSection 追加 | Dev |
| 7 | SupplierDetailView.tsx から MASTER_ISSUE_IDS 条件を削除 | Dev |
| 8 | i18n キー追加 (ja/en) | Dev |
| 9 | CI green 確認 → PO GO → merge | PO |
