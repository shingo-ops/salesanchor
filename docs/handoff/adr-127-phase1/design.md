# design — ADR-127 Phase 1: 配送先追加フォーム整備

**仕事名**: adr127-phase1-address-form
**日付**: 2026-06-11
**対象ADR**: ADR-127 §3
**担当**: generator

参照: `docs/handoff/adr-127-phase1/recon.md`

## 設計方針

`RegisterAddressPage` から address_type 選択 UI を削除し、配送先追加専用フォームとして確立する。
言語切り替え・電話 dial code 分割は既存実装で対応済み。

## 変更箇所と設計根拠

| 変更箇所 | 変更内容 | 根拠 |
|---------|---------|------|
| `frontend/src/pages/register/RegisterAddressPage.tsx:312-323` | address_type select ブロック削除 | ADR-127 §3「配送先追加専用化」。billing を選べる余地を残さない（重複行の温床）|

## 受け入れ条件と検証方法

| 基準 | 検証方法 |
|------|---------|
| フォームに address_type 選択が表示されない | ブラウザ確認 / grep で select が残っていないこと |
| 送信ペイロードの address_type が "delivery" 固定 | Network タブで POST body 確認 |
| billing 住所が作られない | 送信後 company_addresses に billing 行が存在しないこと |
| ESLint `local/no-japanese-literal` を通過 | `cd frontend && npm run lint` |

## 外部・過去事例の参照と我々への応用

- ADR-097「上書きせず追加（住所帳）」: append-only 方針は現状維持。
- ADR-127 §3: address_type 選択削除・billing 選択の余地なし。
