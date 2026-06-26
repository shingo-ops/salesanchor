# design: inbox-ui-text-j1-j5（便1 UI文言調整）

対象PR: #2614  
対象ADR: ADR-110（送信下訳プレビューサブシステム）  
recon: docs/handoff/inbox-ui-text-j1-j5/recon.md  
実施日: 2026-06-26

---

## 変更概要（J1〜J5）

### J1: 送信ガード ダイアログ文言変更

**変更ファイル**: `frontend/src/locales/ja.json:2937-2938`, `frontend/src/locales/en.json:2937-2938`

| キー | 変更前 | 変更後 |
|------|--------|--------|
| `translation.sendGuard.dialogTitle` (ja) | かな文字が含まれています | 翻訳して送りますか？ |
| `translation.sendGuard.dialogBody` (ja) | この下書きにかな文字が含まれています。英語圏の受信者に送信しますか？ | 日本語が含まれていますが翻訳して送信しますか？ |
| `translation.sendGuard.dialogTitle` (en) | Kana characters detected | Translate before sending? |
| `translation.sendGuard.dialogBody` (en) | Your draft contains kana characters. Are you sending to an English-speaking recipient? | This message contains Japanese. Translate and send? |

JSX側: `frontend/src/pages/inbox/InboxMessageThread.tsx:407-409`（変更なし・t()経由）

---

### J2: 英訳プレビュー自動生成（ボタン削除 → useEffect）

**変更ファイル**: `frontend/src/pages/inbox/OutboundTranslationPreview.tsx`

- `useEffect` + `hasRequestedRef`（二重呼び出し防止）でモーダル開時に自動API呼び出し（`:60-65`）
- プレビューボタン（`outbound-translation-preview-btn`）を削除（`:99-109`）
- 生成中は `<div aria-live="polite">` でローディング表示（`:102-107`）
- `disabled` prop は `_disabled` にリネーム（API互換維持・`:32`）

---

### J3: 見出し文言変更（draftLabel）

**変更ファイル**: `frontend/src/locales/ja.json:2951`, `frontend/src/locales/en.json:2951`

| キー | 変更前 | 変更後 |
|------|--------|--------|
| `translation.outbound.draftLabel` (ja) | 英訳下訳（編集可） | 英訳下書き（編集可） |
| `translation.outbound.draftLabel` (en) | English Draft (editable) | English draft (editable) |

JSX側: `frontend/src/pages/inbox/OutboundTranslationPreview.tsx:121`（変更なし）

---

### J4: 戻るボタン追加（再生成ボタン削除）

**変更ファイル**: `frontend/src/pages/inbox/OutboundTranslationPreview.tsx:163-171`

- `outbound-translation-regenerate-btn`（再生成）→ `outbound-translation-back-btn`（戻る）
- `onClick`: `handlePreview` → `onClose`（モーダルを閉じる・日本語下書きはそのまま残る）
- i18n キー追加: `translation.outbound.back` = "戻る" / "Back"
  - `frontend/src/locales/ja.json:2955`, `frontend/src/locales/en.json:2955`

---

### J5: 送信ボタン表記変更（confirmSend）

**変更ファイル**: `frontend/src/locales/ja.json:2954`, `frontend/src/locales/en.json:2954`

| キー | 変更前 | 変更後 |
|------|--------|--------|
| `translation.outbound.confirmSend` (ja) | 確認して送信 | 送信 |
| `translation.outbound.confirmSend` (en) | Confirm & Send | Send |

JSX側: `frontend/src/pages/inbox/OutboundTranslationPreview.tsx:180`（変更なし）

---

## 触らない範囲

以下は本PRで変更しない（ADR-110 Stage-A 実装は #2606 でマージ済み）:

- `handleConfirmSend` ロジック（`OutboundTranslationPreview.tsx:67-79`）
- `onConfirmedSend` / `submitSend` の型・動作（`InboxMessageThread.tsx:37, 395-397`）
- `requestOutboundPreview` / `confirmOutboundDraft` API呼び出し（`messages.ts:269, 286`）
- 通常送信（checkAndSend）・画像送信（`InboxMessageThread.tsx:112, 426`）
- `backend/` 配下すべて（routers/services/models）
- `migrations/` 配下すべて
- `scripts/` 配下すべて

---

## 外部・過去事例の参照と我々への応用

該当なし：本変更はi18nキー値の修正とuseEffect自動実行化のみ（frontend文言/UI）。DB非接触・API仕様変更なし・新規ライブラリ導入なし。外部事例を参照するまでもなく既存ADR-110実装の延長として完結する。

---

## 受け入れ基準（ADR-110 § 実機検証）

recon参照: docs/handoff/inbox-ui-text-j1-j5/recon.md §R1〜R6

| 基準 | 検証方法 |
|------|----------|
| J1 ダイアログが新文言 | 実機: 日本語下書き送信時のダイアログ表示 |
| J2 ボタンなしで自動英訳表示 | 実機: プレビュー開いた瞬間に英訳が出る |
| J3 「英訳下書き（編集可）」表示 | 実機: 見出し確認 |
| J4 「戻る」で閉じ日本語が残る/再生成ボタン無し | 実機: 戻る押下→入力欄に日本語維持 |
| J5 「送信」表記 | 実機: ボタン文言確認 |
| J6 英訳送信(K1-K4)・通常/画像送信が従来どおり | 実機: 各送信が成功 |
