# ADR-XXX: FedEx ETD（Electronic Trade Documents）実装 — たたき台

> **ステータス**: DRAFT（起案前・Shingo GO待ち）  
> **番号**: 未確定（ADR-136 が現在の最終番号。実際の番号は PO が確定すること）  
> **日付**: 2026-06-16  
> **起案者**: Hikky-dev  
> **依存 ADR**: ADR-123（キャリア連携基盤）/ ADR-125（FedEx Rates OAuth）/ ADR-129（Label Validation ウィザード）  
> **前提条件**: APAC FedEx API チームへの Q1〜Q6 回答受領後に正式起案する（`fedex-apac-questions.md` 参照）

---

## ⚠️ Shingo GO 必須の変更一覧

このADRを実装に進める前に、以下のすべてについて Shingo の承認が必要。

| # | 変更内容 | 理由 | GO 条件 |
|---|---------|------|---------|
| G1 | `migrations/YYYYMMDD_HHMMSS_add_fedex_etd_images.sql` — DB migration 追加 | 本番 DB への schema 変更 | APAC 確認済み + Shingo コメント「GO: Shingo YYYY-MM-DD」 |
| G2 | `deploy.yml` — ETD migration ステップ追記 | deploy.yml 変更は不可逆操作リストに準ずる | G1 GO 後に同一 PR で承認 |
| G3 | FedEx 側アカウント設定（Paperless Trade 有効化） | FedEx.com 等の外部 GUI 操作（CLAUDE.md §不可逆操作） | APAC Q5 回答 + Shingo 直接操作 |
| G4 | Sandbox ETD 動作確認後の本番切替 | 本番 FedEx アカウントへの設定変更 | Sandbox PASS + Shingo 確認 |

> **コード変更**（`fedex_ship.py` への etdDetail 追加）は通常 PR。危険変更には該当しない。

---

## 背景

FedEx ETD（Paperless Trade）は、国際出荷時にラベルと共に税関向け書類（インボイス等）を
電子的に FedEx へ提出する仕組み。物理的な書類同梱が不要になり、通関時間の短縮が見込まれる。

**現状の問題**:
- `create_shipment()`（`backend/app/services/fedex_ship.py:112-133`）に `etdDetail` フィールドが存在しない
- レターヘッド・署名のアップロードエンドポイント呼び出しロジックが存在しない
- DB にレターヘッド/署名の `docId` を保存するテーブル/列が存在しない
- ETD を Label Validation の必須要件とするかどうかが FedEx 未確認（→ APAC Q1）

**調査元**: `docs/handoff/fedex-etd-stamp-recon/recon.md`（PR #2234 recon）

---

## 決定（起案予定・APAC 回答後に確定）

### J1: DB 設計（`fedex_etd_images` テーブル追加）

レターヘッド・署名の `docId` をテナントごとに1レコードで保持する専用テーブルを作成する。

```sql
-- migrations/YYYYMMDD_HHMMSS_add_fedex_etd_images.sql
-- ⚠️ Shingo GO 必須（G1）

CREATE TABLE IF NOT EXISTS fedex_etd_images (
    id              SERIAL PRIMARY KEY,
    tenant_id       INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    image_type      VARCHAR(20) NOT NULL CHECK (image_type IN ('LETTER_HEAD', 'SIGNATURE')),
    doc_id          TEXT NOT NULL,
    environment     VARCHAR(20) NOT NULL CHECK (environment IN ('production', 'sandbox')),
    uploaded_at     TIMESTAMP NOT NULL DEFAULT NOW(),
    uploaded_by     INTEGER REFERENCES users(id),
    UNIQUE (tenant_id, image_type, environment)
);
```

**却下案**: `tenant_carrier_credentials` に列追加
→ 画像は複数種類（LETTER_HEAD / SIGNATURE）あるため列追加では対応不可。専用テーブルが適切。

**注意**: additive-only migration のため既存データへの影響なし。
ただし `deploy.yml` への migration ステップ追記（G2）が必須。

---

### J2: 画像アップロード API 実装

```
POST /integrations/fedex/etd-images
  body: { image_type: "LETTER_HEAD" | "SIGNATURE", image_base64: string, environment: "sandbox" | "production" }
  → FedEx POST /ship/v1/shipments/images を呼び出し
  → 返却 docId を fedex_etd_images テーブルに upsert
  → レスポンス: { doc_id, image_type, uploaded_at }
```

**APAC Q2 の回答によって変わる点**:
- 「毎回アップロード必須」の場合 → DB 保存不要、Ship リクエスト時にオンデマンド送信
- 「事前登録1回でOK」の場合 → 本設計（DB 保存）を採用

---

### J3: Ship リクエストへの etdDetail 組み込み

`backend/app/services/fedex_ship.py:112-133` の `requested_shipment` 構築に以下を追加:

```python
# etd_doc_ids = DB から取得した { "LETTER_HEAD": "<id>", "SIGNATURE": "<id>" }
if etd_doc_ids:
    requested_shipment["shippingDocumentSpecification"] = {
        "stampType": "INCLUSIVE",  # APAC Q4 回答後に確定
        "etdDetail": {
            "requestedDocumentCopies": ["COMMERCIAL_INVOICE"],
            "uploadedDocuments": [
                {
                    "id": etd_doc_ids["LETTER_HEAD"],
                    "documentType": "LETTER_HEAD",
                    "referenceIndex": "LETTER_HEAD"
                },
                {
                    "id": etd_doc_ids["SIGNATURE"],
                    "documentType": "SIGNATURE",
                    "referenceIndex": "SIGNATURE"
                }
            ]
        }
    }
```

**etdDetail の有無はオプショナル**: ETD 未登録テナントは従来どおり動作する。

---

### J4: UI（画像アップロード画面）

Label Validation ウィザードタブ（ADR-129 J4）内に「ETD 書類登録」セクションを追加:

- レターヘッド画像（PNG / JPG, 推奨サイズ: 800×200px）アップロードフォーム
- 署名画像（PNG / JPG, 推奨サイズ: 200×100px）アップロードフォーム
- 登録済み画像のプレビューと「再アップロード」ボタン
- 環境（本番 / Sandbox）セレクタ（ADR-129 J1 の環境分離と連動）

---

## スコープ（暫定・APAC 回答後に確定）

| フェーズ | 内容 | 危険変更 |
|---------|------|---------|
| E1 | APAC Q1〜Q6 回答受領・設計確定 | なし |
| E2 | `fedex_etd_images` テーブル migration 作成・Shingo GO 取得 | **G1 / G2 — Shingo GO 必須** |
| E3 | バックエンド: アップロード API + Ship への etdDetail 組み込み | 通常 PR |
| E4 | フロントエンド: 画像登録 UI（ウィザードタブ内） | 通常 PR |
| E5 | Sandbox 動作確認（Label Validation ドライラン） | なし（Sandbox のみ） |
| E6 | 本番 FedEx アカウント設定（Paperless Trade 有効化） | **G3 — Shingo 直接操作** |
| E7 | 本番デプロイ・Label Validation 本番申請 | **G4 — Shingo 確認** |

---

## 未解決事項（Shingo 判断が必要なもの）

| # | 問い | 判断が必要な理由 |
|---|-----|----------------|
| U1 | ETD を Label Validation 申請前に実装するか、申請後に実装するか | APAC Q1 の回答次第。必須なら申請前・任意なら後回し可 |
| U2 | このADRの正式起案タイミング | APAC 回答受領後か、事前たたき台共有後か |
| U3 | ADR 番号（現在の最終: ADR-136） | `node scripts/generate-adr-index.js` 再生成も必要 |
| U4 | 画像ストレージの要否（FedEx 側が永続保持しない場合） | APAC Q3 次第。ローカル保存の要否が変わる |
| U5 | Label Validation 本番申請のタイムライン | ETD 実装完了後でないと申請できない場合は E1〜E5 完了が前提 |

---

## 関連ファイル（現時点・実装前）

| ファイル | 行 | 関係 |
|---------|---|------|
| `backend/app/services/fedex_ship.py:112-133` | `create_shipment()` | etdDetail 追加対象 |
| `backend/app/services/fedex_ship.py:57-195` | 全体 | ETD フィールドなし（確認済み）|
| `backend/tests/test_fedex_ship.py` | — | ETD テストケース未追加（E3 で追加予定）|
| `docs/adr/ADR-123-carrier-integrator-provider.md` | — | キャリア連携基盤・Validation 必須項目にインボイス記載 |
| `docs/adr/ADR-129-fedex-label-validation-wizard.md:49-57` | スコープ表 | ETD は対象外（本 ADR で追加） |
| `docs/handoff/fedex-etd-stamp-recon/recon.md:99-106` | 危険変更判定表 | 本ADRの G1〜G4 の根拠 |
| `docs/handoff/fedex-etd-adr-draft/fedex-apac-questions.md` | — | APAC 確認質問リスト（本 ADR の前提）|

---

## 却下した代替案

| 案 | 却下理由 |
|---|---------|
| ETD を carrier_credentials に列追加で対応 | 画像種別が複数ある（LETTER_HEAD / SIGNATURE）→ 列追加では1画像しか持てない |
| ETD を毎回オンデマンドアップロード（DB保存なし）| APAC Q2 で「事前登録1回で OK」の場合はコスト増・FedEx API 負荷増 |
| ETD 実装を Label Validation 申請後に先送り | APAC Q1 で「必須」と判明した場合は申請不可→先に確認が必要 |
