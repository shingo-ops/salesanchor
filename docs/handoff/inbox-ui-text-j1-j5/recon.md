# recon: inbox-ui-text-j1-j5（便1 UI文言調整）

対象PR: #2614  
ブランチ: release/morimoto/inbox-ui-text-j1-j5（base=main）  
実施日: 2026-06-26

---

## R1: 送信ガード ダイアログ JSX と i18n キー

### コマンド
```
grep -n "dialogTitle\|dialogBody" frontend/src/pages/inbox/InboxMessageThread.tsx
```

### 出力
```
407:              {t("translation.sendGuard.dialogTitle")}
409:            <p className="send-guard-body">{t("translation.sendGuard.dialogBody")}</p>
```

### 引用元
- `frontend/src/pages/inbox/InboxMessageThread.tsx:407-409`

### 確認事項
- `dialogTitle` / `dialogBody` は `t()` 経由のみ。ハードコード文字列なし。
- i18n キー: `translation.sendGuard.dialogTitle`, `translation.sendGuard.dialogBody`
- 変更前 ja.json (origin/main): `"dialogTitle": "かな文字が含まれています"`, `"dialogBody": "この下書きにかな文字が含まれています。英語圏の受信者に送信しますか？"`

---

## R2: OutboundTranslationPreview.tsx 全体確認

### コマンド
```
Read frontend/src/pages/inbox/OutboundTranslationPreview.tsx
```

### 引用元（変更箇所）
- `frontend/src/pages/inbox/OutboundTranslationPreview.tsx:12` — import行（useEffect, useRef 追加）
- `frontend/src/pages/inbox/OutboundTranslationPreview.tsx:32` — `disabled: _disabled` リネーム
- `frontend/src/pages/inbox/OutboundTranslationPreview.tsx:41` — `hasRequestedRef = useRef(false)` 追加
- `frontend/src/pages/inbox/OutboundTranslationPreview.tsx:60-65` — useEffect自動生成ブロック
- `frontend/src/pages/inbox/OutboundTranslationPreview.tsx:102-107` — 生成中ローディング div（プレビューボタン削除跡）
- `frontend/src/pages/inbox/OutboundTranslationPreview.tsx:121` — `t("translation.outbound.draftLabel")` 使用箇所
- `frontend/src/pages/inbox/OutboundTranslationPreview.tsx:163-171` — 戻るボタン（旧: 再生成ボタン）
- `frontend/src/pages/inbox/OutboundTranslationPreview.tsx:178-180` — 送信ボタン `t("translation.outbound.confirmSend")`

### 変更前後
| 箇所 | 変更前 | 変更後 |
|------|--------|--------|
| :12 import | `useCallback, useState` | `useCallback, useEffect, useRef, useState` |
| :32 disabled | `disabled` | `disabled: _disabled` |
| :41 | なし | `hasRequestedRef = useRef(false)` |
| :60-65 | なし（プレビューボタンで手動実行） | useEffect 自動実行ブロック |
| :99-109 | `<button … outbound-translation-preview-btn>` | `<div … outbound-translation-generating>` |
| :163-170 | `outbound-translation-regenerate-btn`（再生成） | `outbound-translation-back-btn`（戻る） |

---

## R3: InboxMessageThread.tsx モーダル開閉・onConfirmedSend 結線

### コマンド
```
grep -n "showOutboundPreview\|setShowOutboundPreview\|OutboundTranslationPreview\|onConfirmedSend\|submitSend\|draftId" frontend/src/pages/inbox/InboxMessageThread.tsx
```

### 出力
```
7:   import { OutboundTranslationPreview } from "./OutboundTranslationPreview";
37:  submitSend: (opts?: { draftId?: number }) => void;
61:  trimmedDraft, submitSend, handleKeyDown,
100: const [showOutboundPreview, setShowOutboundPreview] = useState(false);
112:     submitSend();
114: }, [canSend, sendDisabled, shouldFireGuard, submitSend]);
388:     {showOutboundPreview && (
389:       <OutboundTranslationPreview
392:         onClose={() => setShowOutboundPreview(false)}
395-397:    onConfirmedSend={(finalText, draftId) => {
                setShowOutboundPreview(false);
                submitSend({ draftId });
            }}
416:          setShowOutboundPreview(true);
514:          onClick={() => setShowOutboundPreview(true)}
426:          submitSend();
```

### 引用元
- `frontend/src/pages/inbox/InboxMessageThread.tsx:37` — Props型定義
- `frontend/src/pages/inbox/InboxMessageThread.tsx:100` — useState showOutboundPreview
- `frontend/src/pages/inbox/InboxMessageThread.tsx:388-397` — モーダルレンダリング + onConfirmedSend
- `frontend/src/pages/inbox/InboxMessageThread.tsx:407-409` — sendGuard ダイアログ

---

## R4: requestOutboundPreview API 関数

### コマンド
```
grep -n "requestOutboundPreview\|confirmOutboundDraft" frontend/src/lib/messages.ts
```

### 出力
```
269: export async function requestOutboundPreview(
286: export async function confirmOutboundDraft(
```

### 引用元
- `frontend/src/lib/messages.ts:269` — requestOutboundPreview 定義
- `frontend/src/lib/messages.ts:286` — confirmOutboundDraft 定義

---

## R5: Stage-A 結線（onConfirmedSend / submitSend / draft_id）

### コマンド
```
grep -n "submitSend\|draftId\|onConfirmedSend" frontend/src/pages/inbox/InboxMessageThread.tsx
grep -n "submitSend\|draftId" frontend/src/pages/inbox/useInboxState.ts
```

### 出力（InboxMessageThread.tsx）
```
37:  submitSend: (opts?: { draftId?: number }) => void;
395:  onConfirmedSend={(finalText, draftId) => {
397:    submitSend({ draftId });
426:    submitSend();  ← sendAsIs（翻訳なし送信）
112:    submitSend();  ← checkAndSend（通常送信）
```

### 引用元
- `frontend/src/pages/inbox/InboxMessageThread.tsx:395-397` — onConfirmedSend クロージャ

---

## R6: i18n vs JSX直接文字列の判定

### コマンド
```
grep -n "\"translation\." frontend/src/pages/inbox/OutboundTranslationPreview.tsx
grep -rn "[^a-z]\"[あ-ん]" frontend/src/pages/inbox/OutboundTranslationPreview.tsx
```

### 確認結果
- JSX内の全UI文字列は `t("translation.outbound.*")` / `t("translation.sendGuard.*")` 経由
- ハードコード日本語: なし（ADR-027 準拠）
- 変更対象キー（ja.json）:
  - `frontend/src/locales/ja.json:2937` — `translation.sendGuard.dialogTitle`
  - `frontend/src/locales/ja.json:2938` — `translation.sendGuard.dialogBody`
  - `frontend/src/locales/ja.json:2951` — `translation.outbound.draftLabel`
  - `frontend/src/locales/ja.json:2954` — `translation.outbound.confirmSend`
  - `frontend/src/locales/ja.json:2955` — `translation.outbound.back`（新規追加）
- 対応 en.json キー: 同一キー・同一構造（ADR-027 必須）
  - `frontend/src/locales/en.json:2937-2938` — dialogTitle/dialogBody
  - `frontend/src/locales/en.json:2951` — draftLabel
  - `frontend/src/locales/en.json:2954-2955` — confirmSend/back
