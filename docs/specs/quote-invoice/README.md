# 見積もり・請求書（quote-invoice）— 設計仕様書（表紙）

> この文書は何か（専門用語なしの1行）:
> 見積書・請求書を発行する独立ページの完成イメージ（PO自筆）とKGIを収めた正本。受信箱（inbox）からは導線（送付ボタン）のみが伸び、ページ本体はここが正本。

- あるべき姿（POの言葉のみ・正本）: [ideal-state.md](./ideal-state.md)
- KGIと運用: [kgi.md](./kgi.md)
- 理想の設計図（To-Be）: [to-be.md](./to-be.md)
- 親: 索引 [docs/specs/README.md](../README.md)
- 技術How層（吸収）: [docs/adr/ADR-101-sa-quotation-invoice-generation.md](../../adr/ADR-101-sa-quotation-invoice-generation.md)（見積・請求の生成・正規化2テーブル・テンプレSSOT・関税ポリシー・PayPal Invoicing方式・PO承認済み）
- ステータス: あるべき姿・KGI 確定（PO自筆・2026-07-08）。ADR-101との整合はrecon便で確認。

## 境界（他テーマとの取り決め）

- 受信箱（inbox）: 会話画面からの送付導線（ボタン）のみを持つ。ページ本体は本テーマが正本。
- 顧客マスタ: 顧客別の関税表示有無・%調整は顧客マスタ側の仕様（本テーマのKGIには含めない・下記「送り状」参照）。
- 取引フロー（transaction-flow）: 見積（quotes・S12）はdeal（deal前ならlead）に紐づき、請求書（invoices・S13）はorderに属する（PO定義2026-07-02）。データ構造の正本は取引フロー側。
- 在庫管理（inventory-management A/B）: 見積・請求の発行は本テーマ（旧記載「受信箱の領分」から本テーマへ委譲・在庫画面は在庫状況確認のみ）。

## 他テーマへの申し送り事項（送り状）

- 顧客マスタ仕様書へ: 「顧客別に関税表示の有無・%を個別調整できる」項目を顧客マスタの仕様に追加する必要がある（PO 2026-07-08指示）。顧客マスタ仕様書が存在しないため、着手時に本項目を追記すること。

## 維持の仕組み

- 本テーマのファイル変更はPR＋PO承認のみ。process-artifacts gate が通過を管理。
- ideal-state.md はPOの言葉のみで構成し、Planner・Generatorは書き換えない。
