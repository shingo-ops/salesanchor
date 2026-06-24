# recon — send-guard-phase-a

**仕事名**: send-guard-phase-a
**日付**: 2026-06-24
**対象ADR**: ADR-143
**担当**: Hikky-dev (Claude Code)

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/pages/inbox/useInboxState.ts:119` | `UseInboxStateReturn` interface に `recipientLanguageSetting` / `setRecipientLanguage` 追加済み |
| `frontend/src/pages/inbox/useInboxState.ts:215` | `languageOverrideByLead: Record<number, "auto"\|"ja"\|"en">` state 定義 |
| `frontend/src/pages/inbox/InboxMessageThread.tsx:103` | `showSendGuardDialog` state + `draftHasKana` / `shouldFireGuard` 定数 |
| `frontend/src/pages/inbox/InboxMessageThread.tsx:107` | `checkAndSend` — 発火条件チェックして送信かダイアログ分岐 |
| `frontend/src/pages/inbox/InboxMessageThread.tsx:116` | `handleKeyDownGuarded` — `isComposing` 判定でIME Enter を無視 |
| `frontend/src/pages/inbox/InboxMessageThread.tsx:419` | `SendGuardDialog` JSX（3ボタン: 英訳して送る / 原文で送る / キャンセル） |
| `frontend/src/pages/inbox/InboxPage.css:1653` | `.send-guard-lang-toggle` — スレッドヘッダー言語トグルスタイル |
| `frontend/src/pages/inbox/InboxPage.css:1681` | `.send-guard-overlay` — ダイアログオーバーレイ（`position: fixed; /* fixed-ok: */`） |
| `frontend/src/locales/ja.json:2933` | `translation.sendGuard.*` キー（dialogTitle / dialogBody / 3ボタンラベル / トグルラベル） |
| `docs/adr/ADR-143-send-guard.md:1` | ADR-143 本文（Phase A 発火条件表 / ダイアログ選択肢 / Phase B 予告） |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | `requestOutboundPreview` の 3rd 引数 `target_language` は既存 API 対応済みか | `frontend/src/pages/inbox/OutboundTranslationPreview.tsx` の API 呼び出し確認 + バックエンドは ADR-110 実装済み | ✅ 解消済み |
| 2 | `languageOverrideByLead` の localStorage 永続化は Phase A スコープか | ADR-143 §言語トグル: セッション内のみ（Phase B 検討）と明記 | ✅ 解消済み（スコープ外） |

**未解決ゼロ確認**: 全て解消済み
