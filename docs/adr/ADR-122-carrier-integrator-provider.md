# ADR-122: 配送キャリア連携 — 外部販売を見据えた Integrator Provider 対応アーキテクチャ

- **Status**: Proposed
- **Date**: 2026-06-09
- **Deciders**: shingo-ops（PO）, Hikky-dev（Dev）

## Context

salesanchor を外部企業へ販売する B2B SaaS として展開する方針が決定（[[project_salesanchor_productization_carrier]]）。これに伴い配送キャリア連携は「自社利用」から「各導入企業が自社の配送アカウントを連携する Integrator モデル」へ拡張する必要がある。

現状（実装済み）:
- 管理センター > API連携に FedEx / DHL / UPS の**接続テストページ**（本番稼働）。
- `public.tenant_carrier_credentials`（テナント別・Fernet 暗号化・接続テストのみ）。

外部販売（Integrator Provider）には FedEx の認定が必要で、認定には「単なるAPIキー」を超える実装エビデンス（エンドカスタマー登録 + MFA、ラベル PDF/PNG/ZPL・600DPI、EULA/免責文、Ship/Rate/Track、インボイス）が求められる。日本企業の実例（Ship&co＝APAC初 FedEx Compatible / AnyLogi）が「各顧客が自社アカウントを連携」モデルで実現済み＝本 ADR の方向性は妥当。

決定の背景・要件詳細・申請手順・スケジュールは `docs/research/fedex-integrator-provider-application-2026-06-09.md` を参照。

## Decision

### D1. モデル: テナント別・自社アカウント連携（per-tenant bring-your-own-account）
各導入企業（テナント）が自社の配送キャリア認証情報を連携し、salesanchor が送料見積・送り状・インボイス・追跡を代行する。既存 `tenant_carrier_credentials` の延長線。アプリ共通の単一アカウントには集約しない（Ship&co / AnyLogi と同型）。

### D2. FedEx 区分: Integrator Provider
developer.fedex.com の組織タイプは **Integrator Provider**（ソフトを顧客に提供）で登録。本番キーは Integrator Provider Validation の承認を条件に取得。FedEx Compatible 認定（事業提携）は市場投入後に取得。

### D3. データモデル（拡張）
- `tenant_carrier_credentials` に **account_number_encrypted**（配送アカウント番号・Rate/Ship に必須）を追加。
- 新規 `tenant_shipments`（テナント別の出荷記録・ラベル/トラッキング/ステータス保管。受注 order との関連は nullable）。
- エンドカスタマー登録の検証ステータス（MFA 済み等）を保持するカラム/テーブル（Validation エビデンス要件）。

### D4. 実装レイヤ
- **接続/認証**: 既存 `carrier_credentials.py` を延長（account_number 対応）。
- **配送 API（Rate/Ship/Track）**: 新規 `carrier_shipping`（FedEx REST: OAuth2 + Ship/Rate/Track）。既存 `shipping_carriers/`（eLogi CSV 出力アダプタ・ADR-021）とは別レイヤ（用途が異なる）。
- **ラベル/インボイス**: 既存 PDF 基盤（`test_pdf` / `po_renderer`・IPAゴシック）を活用。ZPL は FedEx 応答をそのまま保存。
- **エンドカスタマー登録 + MFA**: 各テナントが自社 FedEx を登録・本人確認する正式フロー（手入力から昇格）。

### D5. UI/法務
- 製品画面に FedEx サービス表示・**免責文（disclaimer）**・**EULA** を組み込む（Validation 必須）。EULA 本文は法務レビュー前提（本 ADR ではプレースホルダ）。

### D6. ロードマップ（フェーズ）
- **Phase 0（完了）**: 接続テストページ（per-tenant 認証）。
- **Phase A（即時）**: Integrator 組織登録 + Agreement + テストキー + FedEx Japan 問い合わせ。
- **Phase B**: Rate / Ship + ラベル(PDF/PNG/ZPL・600DPI・国際AWB・複数個口) / インボイス / Track。
- **Phase C**: エンドカスタマー登録 + MFA / EULA・disclaimer / 外部販売向け設定 UI。
- **Phase D**: 実 cred 検証 + 物理ラベルスキャン + エビデンス収集 + PIW/Cover Sheet → `validationmtp@fedex.com` 提出。
- **Phase E**: FedEx 審査 → 本番キー。**Phase F**: 市場投入後に FedEx Compatible 認定。

## Consequences

### 良い点
- 既存の per-tenant 暗号化認証モデル（実証済み）をそのまま土台にできる。
- DHL / UPS / ヤマト / 佐川 / 日本郵便へ同型でマルチキャリア拡張可能。
- 認定取得で外部販売時の信頼性・FedEx Compatible ディレクトリ掲載・共同マーケが得られる。

### 留意・リスク
- 律速は **FedEx 側の応答/審査時間**・**600DPI ラベルの物理印刷+スキャン**・**しんごさんの登録/承認**（Claude では縮まない）。
- 国際出荷（通関・品目・AWB・ZPL）は複雑で**実認証情報での反復**が必要（差戻し→再提出リスク）。
- DHL/UPS/ヤマト/佐川 もそれぞれ別の認定/契約が要る（FedEx と同時並行ではない）。
- account_number 等の追加収集は**実機能（Rate/Ship）と同時に UI 投入**する（接続テストのみの現状に未使用フィールドを先行投入して混乱させない）。

## 実装の事前準備（登録完了を待たずに進められるもの）
- 設計の確定（本 ADR）＝最大の前倒し。テストキー到着で Phase B を即発火できる状態にする。
- FedEx 応答に依存しない安全な先行作業のみ着手（PDF テンプレート設計、データモデル設計）。実 API の応答パース等はテストキー取得後（手戻り回避）。

## References
- 申請ガイド: `docs/research/fedex-integrator-provider-application-2026-06-09.md`
- FedEx Integrator Provider Validation: https://developer.fedex.com/api/en-us/certification/integrator-provider.html
- 関連 ADR: ADR-021（受注管理・eLogi CSV アダプタ層）
- 既存実装: `backend/app/services/carrier_credentials.py`, `backend/app/routers/integrations.py`, `frontend/src/pages/integrations/CarrierIntegrationPage.tsx`
