# 設計 — FedEx 自社出荷 Stage 2（Ship API / Pickup API）

**対象ADR**: ADR-128
**recon**: docs/handoff/fedex-ship-stage2/recon.md
**日付**: 2026-06-11
**担当**: Hikky-dev（Generator）

---

## 外部・過去事例の参照と我々への応用

- **事例1: Flexport / Shipwire 等の他社 FedEx Ship API 統合**
  - `labelResponseOptions="LABEL"` + Base64 decode → PDF 保存 の方式は FedEx 公式サンプルおよびサードパーティガイド（doc.oneentry.cloud）で標準的に採用されている
  - 応用: `encodedLabel` → `base64.b64decode()` → Google Drive `upload_pdf()` の pipeline を採用
- **事例2: FedEx Label Validation（Shipper track）の先行事例**
  - Shipper 申請は `label@fedex.com` 提出 → 3営業日（developer.fedex.com 公式記載）
  - Pickup は Validation 不要（certification ページに記載なし）→ 先行リリース可能
  - 応用: Pickup 先行リリース（D4）により審査待ち期間中も機能提供できる設計を採用
- **事例3: マルチキャリア抽象化（FedEx/DHL/UPS）**
  - Protocol パターン（`dimensions_required: bool` 等のキャリア別プロパティ）は CargoWise/ShipStation 系統の実装で標準的
  - 応用: `carrier_adapter.py` に `CarrierShipAdapter` Protocol を定義し、今回は `FedExShipperAdapter` のみ実装。DHL 追加時はアダプタ 1 ファイル追加のみ

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| `fedex_ship.create_shipment()` が tracking 番号・label_bytes・確定送料を返す | `pytest backend/tests/test_fedex_ship.py -k test_create_shipment` |
| `fedex_ship.create_pickup()` が confirmation_code を返す | `pytest backend/tests/test_fedex_ship.py -k test_create_pickup` |
| auth エラー時に `FedExAuthError` を raise する | `pytest backend/tests/test_fedex_ship.py -k auth_error` |
| `ShippingCalcRequest` に dimensions / address_type / order_id フィールドが存在する | `pytest backend/tests/test_fedex_ship.py -k schema` |
| `ShippingCalcResult` に `surcharges` フィールドが存在する | `pytest backend/tests/test_fedex_ship.py` 全 PASS |
| migration が `order_shipping_details` に 6 カラムを追加する（冪等） | CI「マイグレーションSQL 実行（内部）」「マイグレーションSQL 実行テスト（実DB）」PASS |
| `POST /shipping/shipments` がラベル発行 + GDrive 保存 + DB 更新を行う | Sandbox 手動テスト（CI 緑後） |
| `POST /shipping/pickups` が集荷確認番号を DB に記録する | Sandbox 手動テスト（CI 緑後） |
| ADR-072 準拠: 全 write エンドポイントで `db.commit()` 直後に `reset_tenant_context()` を呼ぶ | コードレビュー + `grep -n reset_tenant_context backend/app/routers/shipping.py` |

---

## 技術 How・KPI

- Ship API: `POST /ship/v1/shipments` — `labelResponseOptions="LABEL"` で Base64 直返し → `base64.b64decode()` → Google Drive `upload_pdf()`
- Pickup API: `POST /pickup/v1/pickups` — `pickupConfirmationCode` を `order_shipping_details.pickup_confirmation_code` に記録
- キャリアアダプタ: `backend/app/services/carrier_adapter.py` に `CarrierShipAdapter` Protocol（`dimensions_required: bool`）
- KPI: pytest 全 PASS（12 テスト）、CI 全グリーン、Sandbox でラベル取得確認

---

## 弊害・トレードオフ

- **Google Drive 接続（tenant_004）**: `upload_pdf()` はテナントの GDrive OAuth が必要。HIGH LIFE JPN（tenant_004）接続済みを確認済み（shingo@treasureislandjp.com）
- **Label Validation 差し戻しリスク**: DPI・バーコード形式が FedEx 基準外の場合は差し戻し。Sandbox でラベル生成後にフォーマット確認してから `label@fedex.com` 提出
- **migration 本番 DB 投入**: `order_shipping_details` の 6 カラム追加は Shingo GO 必要（CLAUDE.md 不可逆操作ルール）

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | `carrier_adapter.py` 新規作成（Protocol + dataclass） | Generator |
| 2 | `fedex_ship.py` 新規作成（create_shipment / create_pickup / check_pickup_availability） | Generator |
| 3 | `schemas/shipping.py` 拡張（SurchargeDetail / ShipPartyInfo / CreateShipment* / CreatePickup*） | Generator |
| 4 | `fedex_rates.py` 拡張（dimensions / address_type / surcharges 対応） | Generator |
| 5 | `routers/shipping.py` 拡張（POST /shipping/shipments・pickups） | Generator |
| 6 | `test_fedex_ship.py` 新規作成（12 テスト） | Generator |
| 7 | migration SQL（DO $$ pg_namespace 形式）作成・run_all_migrations.sh 追記 | Generator |
| 8 | CI 緑確認 → Pickup 先行 develop マージ | Hikky-dev → Shingo APPROVE |
| 9 | Sandbox テスト → label@fedex.com 提出 | Shingo 実施 |
| 10 | Label Validation 承認後 → Ship 本番リリース | Shingo GO |

---

## 継続

- **Pickup 先行リリース**: CI 緑 + Reviewer APPROVE 後に develop マージ可能（migration 本番 DB は Shingo GO 待ち）
- **Ship 本番リリース**: Label Validation 承認（3営業日）後に本番クレデンシャルで有効化
- **次フェーズ**: 出荷管理 UI（別スプリント）、DHL アダプタ（別 ADR）
