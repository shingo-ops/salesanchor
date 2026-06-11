# recon — ADR-127 Phase 1: 配送先追加フォーム整備

**仕事名**: adr127-phase1-address-form
**日付**: 2026-06-11
**対象ADR**: ADR-127 §3
**担当**: generator

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/pages/register/RegisterAddressPage.tsx:40-56` | `emptyAddress()`: `address_type: "delivery"`, `is_default: false` が既に固定 |
| `frontend/src/pages/register/RegisterAddressPage.tsx:312-323` | address_type select が露出（billing も選択可）— 削除対象 |
| `frontend/src/pages/register/RegisterAddressPage.tsx:254-258` | `toggleLang()` 関数: 言語切り替え実装済み |
| `frontend/src/pages/register/RegisterAddressPage.tsx:292-297` | 言語切り替えボタン: JSX に実装済み |
| `frontend/src/pages/register/RegisterAddressPage.tsx:337-364` | 電話番号 dial code コンボ + 番号欄: 実装済み |
| `frontend/src/pages/register/RegisterAddressPage.tsx:173-180` | `useEffect` で `searchParams.get("lang") || "en"` — 英語デフォルト実装済み |

## 変更概要

ADR-127 §3 で要求された配送先追加フォームの整備:
- **言語切り替え**: 実装済み（既存コードで対応完了）
- **電話 dial code 分割**: 実装済み（既存コードで対応完了）
- **address_type 選択削除**: billing / delivery を選べる select を削除し delivery 固定にする（今回の変更）

`emptyAddress()` が既に `address_type: "delivery"`, `is_default: false` 固定のため、
UI select を削除するだけで ADR-127 §3 の意図が完全に満たされる。

## 不明点リスト

未解決なし。
