# recon — ADR-127 Phase 1: 配送先追加フォーム整備

**仕事名**: adr127-phase1-address-form
**日付**: 2026-06-11
**対象ADR**: ADR-127 §3
**担当**: generator

## 削除根拠の確認

| 確認事項 | 引用 |
|---------|------|
| `emptyAddress()` が `address_type: "delivery"` 固定 | `frontend/src/pages/register/RegisterAddressPage.tsx:41` |
| `emptyAddress()` が `is_default: false` 固定 | `frontend/src/pages/register/RegisterAddressPage.tsx:55` |
| 言語切り替え（`toggleLang`）実装済み | `frontend/src/pages/register/RegisterAddressPage.tsx:255` |
| `searchParams.get("lang")` で英語デフォルト実装済み | `frontend/src/pages/register/RegisterAddressPage.tsx:175` |
| `emptyAddress()` を初期値として使用（delivery 固定が起動時から適用） | `frontend/src/pages/register/RegisterAddressPage.tsx:188` |

## 変更内容と根拠

`frontend/src/pages/register/RegisterAddressPage.tsx` の develop 版 L308-L320 に存在していた address_type select（billing / delivery を選べる UI）を削除する。

- `emptyAddress():41` が `address_type: "delivery"` を固定しているため、UI select は不要
- `is_default: false`:55 も固定済みで、billing 行が重複生成される余地をなくす
- 言語切り替え（`toggleLang`:255）・電話 dial code は PR #1881（コミット 6e376491）で実装済み
- Phase 1 の残作業は select 削除のみ（ADR-127 §3）

## 既実装（変更不要）

- `toggleLang():255` — 言語切り替えボタン実装済み
- `searchParams.get("lang"):175` — 英語デフォルト実装済み
- 電話 dial code Combobox — 実装済み

## 不明点リスト

なし。
