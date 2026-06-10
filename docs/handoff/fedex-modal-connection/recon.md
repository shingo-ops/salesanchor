# Phase 2 Recon — FedExRateModal 見積書作成ページ導線接続

**実施日**: 2026-06-10
**対象ADR**: ADR-125
**担当**: Hikky-dev

---

## A. FedExRateModal コンポーネントの現状

| 項目 | file:line | 内容 |
|------|-----------|------|
| コンポーネント定義 | `frontend/src/components/FedExRateModal.tsx:47` | Props: `open`, `onClose`, `destinationCountryCode: string`（旧: 必須）, `weightKg: number`, `onSelectRate(fee, currency, serviceType)` |
| API呼び出し | `frontend/src/components/FedExRateModal.tsx:123` | `POST /shipping/calculate` に `country_code`, `weight_kg`, `carrier`, `origin_country_code` を送信 |
| 未連携チェック | `frontend/src/components/FedExRateModal.tsx:147` | `live_error.includes("未連携")` で設定ページ誘導を分岐 |

## B. QuoteCreatePage の重量計算

| 項目 | file:line | 内容 |
|------|-----------|------|
| totalWeight 計算 | `frontend/src/pages/quote-create/QuoteCreatePage.tsx:116` | `items.reduce((sum, item) => sum + item.quantity * (item.weight ?? 0), 0)` |
| 形態別重量引き込み | `frontend/src/pages/quote-create/QuoteCreatePage.tsx:91` | `weightForUnit(unit, box_weight_kg, case_weight_kg, null)` — box/case のみマスタ重量を設定、他は null |
| blankItem の重量 | `frontend/src/pages/quote-create/quoteDraft.ts:82` | `weight: null` — 空行追加時は重量なし → totalWeight=0 になる可能性あり |

**判断**: totalWeight=0 の事故を防ぐため、モーダル内に重量入力欄を追加して手動補正を可能にする。

## C. i18n の現状（fedexRateModal セクション）

| 項目 | file:line | 内容 |
|------|-----------|------|
| ja.json fedexRateModal | `frontend/src/locales/ja.json:246` | `originLabel`, `getQuote`, `selectRate` 等が定義済み。`destinationLabel` / `weightLabel` は未定義 |
| en.json fedexRateModal | `frontend/src/locales/en.json:246` | 同上 |

## D. 宛先国コードの取得経路

| 項目 | file:line | 内容 |
|------|-----------|------|
| CompanyContactSelector の返却型 | `frontend/src/components/CompanyContactSelector.tsx:1` | `{companyId: number | null, contactId: number | null}` — 国コードは含まない |
| CompanyMini 型 | `frontend/src/components/CompanyContactSelector.tsx:1` | `{id, company_code, name}` — country_code フィールドなし |

**判断**: QuoteCreatePage から宛先国コードを渡せないため、モーダル内部に入力欄を追加する。
