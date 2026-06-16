# FedEx APAC APIチーム 確認質問リスト

**宛先**: apacfedexapi@fedex.com  
**件名**: FedEx Ship API — ETD (Electronic Trade Documents / Paperless Trade) 利用要件確認  
**作成日**: 2026-06-16  
**起案者**: Hikky-dev  
**背景**: FedEx Integrator Provider 審査（Label Validation）申請準備中。ETD 機能の必要性と実装要件を確認する。

---

## Q1: Label Validation における ETD の必須・任意区分

**質問**:
FedEx Label Validation（PIW / Cover Sheet 提出）を完了するにあたり、
ETD（Paperless Trade / Electronic Trade Documents）の送付は **必須** ですか、それとも任意ですか？

**現状**:
- 弊社アプリケーションでは現在 `customsClearanceDetail` を Ship API リクエストに含めています
- `shippingDocumentSpecification.etdDetail` は未実装です
- APAC 向け国際配送（IP / IE / IPE / FICP）を対象としています

**期待する回答形式**: 必須 / 任意 / サービスタイプ別（内訳付き）

---

## Q2: レターヘッド・署名画像のスコープ（テナント単位 vs 出荷単位）

**質問**:
`POST /ship/v1/shipments/images` でアップロードする LETTER_HEAD（会社レターヘッド）および SIGNATURE（署名）は、
**テナント（会社）ごとに1回だけ登録**して以降は `docId` を再利用できますか？
それとも **出荷のたびに毎回アップロード**する必要がありますか？

**補足**:
- テナントごとに事前登録→DB保存→以後の Ship リクエストで `docId` を参照、という実装を想定しています

---

## Q3: アップロード済み画像 ID の有効期限・有効範囲

**質問**:
`POST /ship/v1/shipments/images` で返却される `docId` には有効期限がありますか？

- FedEx サーバー側で定期削除される場合、その期間を教えてください
- アカウント番号（account number）をまたいで `docId` を共有できますか？
- Sandbox で発行した `docId` は Production 環境でも有効ですか？

---

## Q4: `stampType` の使い分け（INCLUSIVE vs EXCLUSIVE）

**質問**:
`shippingDocumentSpecification.stampType` について、
`"INCLUSIVE"` と `"EXCLUSIVE"` の使い分け基準を教えてください。

- APAC 向け国際配送（IP / IE / IPE）ではどちらを推奨しますか？
- どちらを使用しても Label Validation の合否には影響しませんか？

---

## Q5: ETD 有効化のための FedEx アカウント設定

**質問**:
Paperless Trade を Ship API から利用するために、
FedEx アカウント側（FedEx.com または FedEx Ship Manager Server）で
事前に有効化が必要な設定はありますか？

- あるとすれば、手順または担当部門を教えてください
- 弊社は FedEx Integrator Provider 申請中（審査中）の状態ですが、
  Sandbox 環境でのみ ETD をテストする場合も同様の設定が必要ですか？

---

## Q6: Validation 提出物リストにおける ETD の位置づけ

**質問**:
Label Validation 申請（PIW / Cover Sheet 提出）のチェックリストには
「Ship トランザクション 3 形式（PDF / PNG / ZPL）」「インボイス」が含まれています。
これらとは別に、**ETD を使った出荷のトランザクションも提出を求められますか？**

---

## 補足情報（弊社環境）

| 項目 | 値 |
|-----|----|
| アプリ環境 | Web アプリ（SaaS / マルチテナント） |
| API バージョン | Ship API v1 |
| 対象サービスタイプ | FEDEX_INTERNATIONAL_PRIORITY, INTERNATIONAL_ECONOMY, INTERNATIONAL_PRIORITY_EXPRESS, FEDEX_INTERNATIONAL_CONNECT_PLUS |
| 現在の対象地域 | APAC（日本発） |
| 参照 ADR | ADR-123（キャリア連携基盤）/ ADR-129（Label Validation ウィザード） |
