# recon — inbox-header-ui

**仕事名**: inbox-header-ui  
**日付**: 2026-06-24  
**対象ADR**: ADR-143  
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/pages/inbox/InboxMessageThread.tsx:22` | Props interface: handleExclude 定義 |
| `frontend/src/pages/inbox/InboxMessageThread.tsx:23` | Props interface: handleDeleteLead 定義 |
| `frontend/src/pages/inbox/InboxMessageThread.tsx:226` | 旧: send-guard-lang-toggle（3ボタントグル）→ 新: select プルダウン |
| `frontend/src/pages/inbox/InboxMessageThread.tsx:238` | handleMarkUnread ボタン残置確認 |
| `frontend/src/pages/inbox/InboxMessageThread.tsx:270` | 三点メニュー内: handleExclude 参照（残置） |
| `frontend/src/pages/inbox/InboxMessageThread.tsx:275` | 三点メニュー内: handleDeleteLead 参照（残置） |
| `frontend/src/pages/inbox/InboxPage.css:69` | .inbox-platform-select（既存スタイル・再利用） |
| `frontend/src/pages/inbox/useInboxState.ts:133` | handleExclude/handleDeleteLead interface（変更なし） |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | handleExclude/handleDeleteLead の配線が三点メニューに残っているか | file:line 270/275 で確認 | ✅ 解消済み |
| 2 | CSS削除対象（.send-guard-lang-toggle 系）の依存がないか | grep確認・他JSX・CSS参照なし | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
