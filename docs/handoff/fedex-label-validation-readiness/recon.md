# recon: FedEx Label Validation 申請 — 棚卸し

**仕事名**: fedex-label-validation-readiness  
**調査日**: 2026-06-16  
**対象ADR**: ADR-123 / ADR-125 / ADR-129  
**目的**: Label Validation 申請に必要なものを ETD に依存しない範囲で棚卸しし、「今すぐ準備できるもの」と「APAC 回答待ちのもの」を分離する。  
**スコープ**: 実装変更なし・docs-only

---

## 既存 ADR 検索結果

| キーワード | 検索結果 |
|---|---|
| `git grep -i "fedex" docs/adr/` | ADR-123 / ADR-125 / ADR-129 該当 |
| `git grep -i "label" docs/adr/FEATURE-INDEX.md` | ADR-103/ADR-123/ADR-128（FEATURE-INDEX.md） |
| ADR-123 | キャリア連携アーキテクチャ・Integrator Provider 対応。Phase D = Validation 提出。 |
| ADR-125 | FedEx Rates Stage 1。Ship API / Pickup API はスコープ外（第2段）と明記。 |
| ADR-129 | Label Validation ウィザード（J1〜J5 決定済み）。Sprint 3.1〜3.5 実装済み。 |

---

## A. 現状把握（file:line 突合）

### A1. FedEx Ship API 実装状況

| 確認事項 | file:line | 結果 |
|---|---|---|
| create_shipment() | `backend/app/services/fedex_ship.py:57` | 実装済み。shipper / recipient / service_type / weight_kg / customs_clearance / label_image_type を受け取り ShipmentResult を返す |
| label_image_type パラメータ | `backend/app/services/fedex_ship.py:69` | デフォルト "PDF"。PNG / ZPL を渡せば API は対応する（パラメータ受け口あり） |
| imageType のリクエスト組み立て | `backend/app/services/fedex_ship.py:120` | `"imageType": label_image_type` で動的にセット済み |
| customs_clearance (国際便) | `backend/app/services/fedex_ship.py:126-127` | `requested_shipment["customsClearanceDetail"] = customs_clearance` で送付 |
| etdDetail フィールド | `backend/app/services/fedex_ship.py:57-133` | 存在しない（ETD 未実装） |
| OAuth トークン共用 | `backend/app/services/fedex_ship.py:19` | fedex_rates.get_or_refresh_token() を import して共用 |

### A2. FedEx Pickup API 実装状況

| 確認事項 | file:line | 結果 |
|---|---|---|
| create_pickup() | `backend/app/services/fedex_ship.py:198` | 実装済み。集荷予約。carrier_code=FDXE(Express)/FDXG(Ground) 対応 |
| check_pickup_availability() | `backend/app/services/fedex_ship.py:295` | 実装済み。集荷可能日時・締切確認 |
| エンドポイント紐付け | `backend/app/routers/shipping.py:1` | pickup 系エンドポイントあり（shipping.py 内） |

### A3. OAuth / 認証情報管理

| 確認事項 | file:line | 結果 |
|---|---|---|
| get_or_refresh_token() | `backend/app/services/fedex_rates.py:230` | インメモリキャッシュ (tenant_id, environment) → (token, expires_at) |
| get_credentials() | `backend/app/services/carrier_credentials.py:114` | environment パラメータあり（default="production"）。production / sandbox 個別取得 |
| save_credentials() | `backend/app/services/carrier_credentials.py:152` | environment カラムに保存 |
| UNIQUE 制約 | `migrations/20260612_200000_fedex_creds_unique_env.sql:1` | (tenant_id, carrier, environment) の UNIQUE 制約追加済み |
| account_number_encrypted | `migrations/20260609_100000_add_carrier_account_number.sql:15` | additive migration 済み |
| RLS ポリシー | `migrations/20260609_090000_add_carrier_credentials_rls.sql:1` | FORCE ROW LEVEL SECURITY + ポリシー設定済み |

### A4. Label Validation ウィザード（ADR-129 実装状況）

| 確認事項 | file:line | 結果 |
|---|---|---|
| 9 ステップウィザード UI | `frontend/src/pages/integrations/FedexLabelValidationTab.tsx:49` | 実装済み。Step 1〜9 |
| Step 2: サンプルラベル発行エンドポイント | `backend/app/routers/shipping.py:686-745` | POST /shipping/label-validation/samples — Sandbox で 4 サービス分発行 |
| サンプルラベル固定データ | `backend/app/routers/shipping.py:643-669` | _LV_SHIPPER / _LV_RECIPIENT / _LV_CUSTOMS / _LV_SERVICES 定義済み |
| Step 2: ラベル形式 | `backend/app/routers/shipping.py:691` | `label_image_type` を渡していない → デフォルト PDF のみ発行 |
| Step 6: カバーシート PDF 生成 | `backend/app/routers/shipping.py:749-800` | GET /shipping/label-validation/cover-sheet — reportlab+pypdf オーバーレイ |
| カバーシートテンプレート | `backend/app/services/label_validation.py:39` | FedEx 公式フォーム v7.0 を assets/ に同梱済み |
| generate_cover_sheet_pdf() | `backend/app/services/label_validation.py:109` | 実装済み。会社名英語優先・座標実測済み |
| Step 7: メール文面 | `backend/app/routers/shipping.py:805-820` | GET /shipping/label-validation/email-template — 英文メール生成 |
| generate_email_template() | `backend/app/services/label_validation.py:222` | 件名＋本文（英文）を返す |
| CarrierIntegrationPage 環境タブ | `frontend/src/pages/integrations/CarrierIntegrationPage.tsx:64` | FedEx 用 sandbox/production 切替タブ実装済み |

### A5. PDF / PNG / ZPL ラベル生成の現状

| 形式 | create_shipment() 対応 | lv_issue_sample_labels() | 申請提出時要否 |
|---|---|---|---|
| PDF | ✅ 実装済み（デフォルト） | ✅ 発行済み | 必須（3形式の1つ） |
| PNG | ✅ パラメータ受口あり（label_image_type="PNG"） | ❌ 未ワイヤリング | 必須（3形式の1つ） |
| ZPL (ZPLII) | ✅ パラメータ受口あり（label_image_type="ZPLII"） | ❌ 未ワイヤリング | 必須（3形式の1つ） |

**根拠**: `backend/app/services/fedex_ship.py:69` — `label_image_type: str = "PDF"` で任意形式を受け取れる。`backend/app/routers/shipping.py:691` — `lv_issue_sample_labels` は `label_image_type` を渡していない（PDF のみ）。

### A6. Invoice / Commercial Invoice の現状

| 種別 | 実装状況 | file:line |
|---|---|---|
| 見積書 PDF | ✅ 実装済み | `backend/app/services/invoice_renderer.py:520` |
| 請求書 PDF（HS コード表示あり） | ✅ 実装済み | `backend/app/services/invoice_renderer.py:435` — HS Code 固定表示含む |
| FedEx 向け Commercial Invoice（ETD / Paperless Trade 用） | ❌ 未実装 | ADR-ETD-draft に設計候補あり |
| `_LV_CUSTOMS`（サンプルラベル用関税情報） | ✅ 実装済み | `backend/app/routers/shipping.py:651` — commodities / unitPrice / customsValue 含む |

**注記**: `invoice_renderer.py:303` に "HS Code" フィールドあり。ただし FedEx ETD が要求する Commercial Invoice (CI) は別フォーマット（FedEx フォーム 057P）—— 現状の invoice_renderer.py は FedEx CI としては未対応。

### A7. ETD（Electronic Trade Documents / Paperless Trade）の現状

| 確認事項 | file:line | 結果 |
|---|---|---|
| etdDetail フィールド | `backend/app/services/fedex_ship.py:57-133` | 未実装。requested_shipment に etdDetail なし |
| レターヘッド/署名アップロードエンドポイント | `backend/app/routers/shipping.py` | 未実装 |
| fedex_etd_images テーブル | `migrations/` 全体 | 未作成（ADR-ETD-draft の設計候補のみ） |
| ETD 実装 ADR | `docs/handoff/fedex-etd-adr-draft/adr-draft.md` | DRAFT（APAC Q1〜Q6 回答待ち・起案前） |
| APAC 質問リスト | `docs/handoff/fedex-etd-adr-draft/fedex-apac-questions.md` | Q1（ETD 必須か）〜 Q6（提出物リスト） |

### A8. エンドカスタマー登録 + MFA / EULA・免責文の現状

| 確認事項 | 実装状況 |
|---|---|
| FedEx エンドカスタマー登録フロー（FedEx 側 MFA） | 未実装。ADR-123 Phase C に定義のみ |
| EULA（FedEx サービス利用規約）UI 組み込み | 未実装。ADR-123 D5 に「法務レビュー前提」と記載 |
| 免責文（Disclaimer）UI 組み込み | 未実装。ADR-123 D5 に記載のみ |
| スクリーンショット提出用画面 | 未実装 |

**根拠**: `docs/adr/ADR-123-carrier-integrator-provider.md` D5 — "EULA 本文は法務レビュー前提（本 ADR ではプレースホルダ）"

---

## B. 調査まとめ

### B1. Label Validation 申請提出物リスト（research doc §4 準拠）

| # | 提出物 | 現状 |
|---|---|---|
| V1 | Ship トランザクション PDF | ✅ 発行済み（lv_issue_sample_labels） |
| V2 | Ship トランザクション PNG | ❌ 未ワイヤリング（API 対応済み・エンドポイント未） |
| V3 | Ship トランザクション ZPL | ❌ 未ワイヤリング（API 対応済み・エンドポイント未） |
| V4 | エンドカスタマー登録（MFA 付き）JSON | ❌ 未実装（ADR-123 Phase C） |
| V5 | スクショ（サービス画面/EULA/Disclaimer/登録フロー） | ❌ 未実装（ADR-123 D5） |
| V6 | 物理ラベルスキャン画像（600DPI） | ❌ Shingo 操作必須（実機） |
| V7 | PIW / Integrator Validation Cover Sheet | ✅ 自動生成対応済み（generate_cover_sheet_pdf） |

### B2. ETD 依存 vs 非依存の分類

| 項目 | ETD 依存 | 判断根拠 |
|---|---|---|
| PNG/ZPL ラベル生成 | ❌ 非依存 | label_image_type 変更のみ。etdDetail 不要 |
| カバーシート生成 | ❌ 非依存 | 実装済み |
| メール文面生成 | ❌ 非依存 | 実装済み |
| EULA / Disclaimer UI | ❌ 非依存（ETD とは別要件） | ADR-123 D5。APAC 回答関係なし |
| エンドカスタマー登録 | ❌ 非依存（ETD とは別要件） | ADR-123 Phase C。APAC 回答関係なし |
| Commercial Invoice（FedEx CI フォーム） | ⚠️ APAC Q6 次第 | ETD 有無により提出要否が変わる可能性 |
| etdDetail 実装（Paperless Trade） | ✅ 完全依存 | APAC Q1〜Q5 の全回答が前提 |
| fedex_etd_images テーブル | ✅ 完全依存 | Q2（再利用可否）/ Q3（有効期限）回答待ち |
| stampType（INCLUSIVE/EXCLUSIVE） | ✅ 完全依存 | APAC Q4 回答待ち |
| FedEx アカウント側 ETD 有効化 | ✅ 完全依存 | APAC Q5 + Shingo 操作必須 |

---

## C. 不明点

| # | 不明点 | 解消手段 | ブロッカー |
|---|---|---|---|
| U1 | ETD は Label Validation に必須か否か | APAC Q1 回答 | APAC 回答待ち |
| U2 | Commercial Invoice（FedEx CI フォーム 057P）の提出要否 | APAC Q6 回答 | APAC 回答待ち |
| U3 | エンドカスタマー登録の実装優先度（Sandbox PASS が先か） | Shingo 判断 | 設計保留 |
| U4 | EULA 本文（法務レビュー済みのもの） | Shingo 確認 | 法務対応待ち |

---

## 参照元

- `docs/adr/ADR-123-carrier-integrator-provider.md` — キャリア連携基盤
- `docs/adr/ADR-125-fedex-rates-stage1.md` — FedEx Rates Stage 1
- `docs/adr/ADR-129-fedex-label-validation-wizard.md` — Label Validation ウィザード
- `docs/handoff/fedex-etd-adr-draft/README.md` — ETD APAC 確認待ちの経緯
- `docs/handoff/fedex-etd-adr-draft/fedex-apac-questions.md` — APAC Q1〜Q6
- `docs/handoff/fedex-ship-stage2/recon.md` — Ship API / Pickup API 実装 recon
- `docs/handoff/fedex-label-validation-wizard/recon.md` — ADR-129 実装 recon
- `docs/research/fedex-integrator-provider-application-2026-06-09.md` — 申請要件全体
