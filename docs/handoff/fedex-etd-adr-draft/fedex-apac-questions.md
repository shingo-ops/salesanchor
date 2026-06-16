# FedEx APAC APIチーム 確認質問リスト

**宛先**: apacfedexapi@fedex.com  
**件名**: FedEx Ship API — ETD (Electronic Trade Documents / Paperless Trade) 利用要件確認  
**作成日**: 2026-06-16  
**背景**: FedEx Integrator Provider 審査（Label Validation）申請準備中。ETD 機能の必要性と実装要件を確認する。

---

## Q1: Label Validation における ETD の必須・任意区分

FedEx Label Validation（PIW / Cover Sheet 提出）を完了するにあたり、ETD（Paperless Trade / Electronic Trade Documents）の送付は必須ですか、それとも任意ですか？

現状:
- 弊社アプリケーションでは現在 `customsClearanceDetail` を Ship API リクエストに含めています
- `shippingDocumentSpecification.etdDetail` は未実装です
- APAC 向け国際配送（IP / IE / IPE / FICP）を対象としています

期待する回答形式: 必須 / 任意 / サービスタイプ別（内訳付き）

---

## Q2: レターヘッド・署名画像のスコープ

`POST /ship/v1/shipments/images` でアップロードする LETTER_HEAD および SIGNATURE は、テナント（会社）ごとに1回だけ登録して以降は `docId` を再利用できますか？それとも出荷のたびに毎回アップロードする必要がありますか？

---

## Q3: アップロード済み画像 ID の有効期限・有効範囲

`POST /ship/v1/shipments/images` で返却される `docId` には有効期限がありますか？

- FedEx サーバー側で定期削除される場合、その期間を教えてください
- アカウント番号をまたいで `docId` を共有できますか？
- Sandbox で発行した `docId` は Production 環境でも有効ですか？

---

## Q4: `stampType` の使い分け

`shippingDocumentSpecification.stampType` について、`INCLUSIVE` と `EXCLUSIVE` の使い分け基準を教えてください。

---

## Q5: ETD 有効化のための FedEx アカウント設定

Paperless Trade を Ship API から利用するために、FedEx アカウント側で事前に有効化が必要な設定はありますか？

---

## Q6: Validation 提出物リストにおける ETD の位置づけ

Label Validation 申請（PIW / Cover Sheet 提出）のチェックリストには「Ship トランザクション 3 形式（PDF / PNG / ZPL）」「インボイス」が含まれています。これらとは別に、ETD を使った出荷のトランザクションも提出を求められますか？

---

## 補足情報

| 項目 | 値 |
|-----|----|
| アプリ環境 | Web アプリ（SaaS / マルチテナント） |
| API バージョン | Ship API v1 |
| 対象サービスタイプ | FEDEX_INTERNATIONAL_PRIORITY, INTERNATIONAL_ECONOMY, INTERNATIONAL_PRIORITY_EXPRESS, FEDEX_INTERNATIONAL_CONNECT_PLUS |
| 現在の対象地域 | APAC（日本発） |
| 参照 ADR | ADR-123 / ADR-129 |
