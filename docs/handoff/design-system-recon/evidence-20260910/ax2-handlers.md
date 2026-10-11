# AX-2 ref / onKeyDown の使用箇所（origin/main dfcd31c05、事実のみ）

## 1. InboxMessageThread.tsx（送信欄）

textarea 開始タグ: `frontend/src/pages/inbox/InboxMessageThread.tsx:736`（`ref` 属性は :737、`onKeyDown` は :741）

```tsx
// :736-753
              <textarea
                ref={textareaRef}
                className="inbox-textarea"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={handleKeyDownGuarded}
                placeholder={ ...discordChannelMissing / canSend / sendDisabled7d の3分岐... }
                rows={2}
                disabled={!canSend || sending}
              />
```

### textareaRef の使用箇所（grep -n textareaRef。全4行）
- `InboxMessageThread.tsx:98` `const textareaRef = useRef<HTMLTextAreaElement>(null);`（直前コメント :93-97「添付後に入力欄へフォーカスを戻すための参照。クリップボタンにフォーカスが残ると Enter がボタン押下になり、ファイル選択が再度開く（2026-09-04 に実測）。」）
- `InboxMessageThread.tsx:112` `textareaRef.current?.focus();` — `handleFileChange`（ファイル選択後。:106-113）の末尾
- `InboxMessageThread.tsx:125` `textareaRef.current?.focus();` — `acceptDroppedFile`（ドラッグ&ドロップ添付。:121-126）の末尾
- `InboxMessageThread.tsx:737` `ref={textareaRef}`
- 読むのは `.focus()` のみ。`.value` や `selectionStart` などは参照していない（textareaRef の grep は上記4行のみ）。他に textarea を DOM から直接取る箇所: `.inbox-textarea` を querySelector する src コードは 0 件（grep）。tests-e2e は `page.locator(".inbox-textarea")` を使う（ax2-test-refs.md）。

### onKeyDown ハンドラ（Enter の動作）
`InboxMessageThread.tsx:228-235`
```tsx
  const handleKeyDownGuarded = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      checkAndSend();
      return;
    }
    handleKeyDown(e);
  }, [checkAndSend, handleKeyDown]);
```
- Enter（Shift なし・IME 変換中でない）→ `preventDefault()` して `checkAndSend()`。
- `checkAndSend`（:219-226）: `if (!canSend || sendDisabled) return;` → かな検出ガード（`draftHasKana && recipientLanguageSetting !== "ja"`）が立てば `setShowSendGuardDialog(true)`、それ以外は `submitSend()`。
- それ以外のキーは `handleKeyDown(e)`（props。`InboxPage.tsx:170` で `state.handleKeyDown` を渡す）へ委譲。
- 委譲先 `useInboxState.ts:702-707`:
```tsx
  const handleKeyDown = useCallback((e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      submitSend();
    }
  }, [submitSend]);
```
  （同じ Enter 条件。Guarded 側が先に Enter を処理して return するため、Enter では呼ばれない）
- 型: ハンドラの引数は `React.KeyboardEvent<HTMLTextAreaElement>`（:228, :53, useInboxState.ts:121）。TextareaControl は `onKeyDown` を `...rest` で素通し、`ref` は forwardRef（Textarea.tsx:36-52）。

## 2. ManualRecordSection.tsx（手動記録）

textarea 開始タグ: `frontend/src/pages/inbox/ManualRecordSection.tsx:159`（`onKeyDown` は :163）

```tsx
// :159-168
      <textarea
        className="manual-record-textarea"
        value={contentText}
        onChange={(e) => setContentText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={t("inbox.manualRecord.contentPlaceholder")}
        rows={3}
        disabled={saving}
        aria-label={t("inbox.manualRecord.contentPlaceholder")}
      />
```
- **ref は無い**。このファイルに `ref` / `textareaRef` は 0 件（grep -n "textareaRef\|ref=" の出力は空）。
- onKeyDown: `ManualRecordSection.tsx:96-104`
```tsx
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSave(false);
      }
    },
    [handleSave]
  );
```
- Enter（Shift なし）→ `preventDefault()` して `handleSave(false)`（:68）。**IME 変換中の判定（`isComposing`）は無い**（InboxMessageThread 側は有る）。
- `handleSave(allowDuplicate=false)` は `contentText.trim()` と `channelType` が空なら何もしない。`api.post('/api/v1/leads/${leadId}/conv-logs', ...)`（:68-）。

## 3. その他（ref を持つ textarea の有無）
- ページ側53件のうち `ref` 属性を持つのは InboxMessageThread.tsx:736 の1件のみ（ax0 の記録と同じ。再走査で変化なし）。
- `onKeyDown` を持つのは InboxMessageThread.tsx:736 と ManualRecordSection.tsx:159 の2件のみ。
- 参考: `useInboxState.ts:743-747` は `profileModalRef.current?.querySelector("button, input, select, textarea")` の `first?.focus()`（プロフィールモーダルを開いたとき最初に見つかった要素へ focus。要素種別 `textarea` はセレクタ文字列で参照）。
