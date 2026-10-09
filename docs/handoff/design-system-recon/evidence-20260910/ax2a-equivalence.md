# AX-2a 外観同等性（Chromium 147.0.7727.15、幅1280・light）

対象12件、祖先シグネチャ別に 通常・focus・disabled を実測（72 条件、各 53 項目＋::placeholder の color）。console 警告: なし

## 判定対象の computed 差分: 0 条件


## 参考（disabled 属性を持たないものに disabled を付けた状態）: 差分 22 条件

- frontend/src/pages/inbox/InboxKartePanel.tsx:484 [karte] sig0: cursor: default -> not-allowed; opacity: 1 -> 0.5
- frontend/src/pages/inbox/InboxKartePanel.tsx:484 [karte] sig1: cursor: default -> not-allowed; opacity: 1 -> 0.5
- frontend/src/pages/inbox/InboxKartePanel.tsx:503 [karte] sig0: cursor: default -> not-allowed; opacity: 1 -> 0.5
- frontend/src/pages/inbox/InboxKartePanel.tsx:503 [karte] sig1: cursor: default -> not-allowed; opacity: 1 -> 0.5
- frontend/src/pages/inbox/InboxKartePanel.tsx:537 [karte] sig0: cursor: default -> not-allowed; opacity: 1 -> 0.5
- frontend/src/pages/inbox/InboxKartePanel.tsx:537 [karte] sig1: cursor: default -> not-allowed; opacity: 1 -> 0.5
- frontend/src/pages/inbox/InboxKartePanel.tsx:588 [karte] sig0: cursor: default -> not-allowed; opacity: 1 -> 0.5
- frontend/src/pages/inbox/InboxKartePanel.tsx:588 [karte] sig1: cursor: default -> not-allowed; opacity: 1 -> 0.5
- frontend/src/pages/inbox/InboxProfileModal.tsx:181 [karte] sig0: cursor: default -> not-allowed; opacity: 1 -> 0.5
- frontend/src/pages/inbox/InboxProfileModal.tsx:181 [karte] sig1: cursor: default -> not-allowed; opacity: 1 -> 0.5
- frontend/src/pages/inbox/InboxProfileModal.tsx:191 [karte] sig0: cursor: default -> not-allowed; opacity: 1 -> 0.5
- frontend/src/pages/inbox/InboxProfileModal.tsx:191 [karte] sig1: cursor: default -> not-allowed; opacity: 1 -> 0.5
- frontend/src/pages/inbox/InboxProfileModal.tsx:210 [karte] sig0: cursor: default -> not-allowed; opacity: 1 -> 0.5
- frontend/src/pages/inbox/InboxProfileModal.tsx:210 [karte] sig1: cursor: default -> not-allowed; opacity: 1 -> 0.5
- frontend/src/pages/inbox/InboxProfileModal.tsx:265 [karte] sig0: cursor: default -> not-allowed; opacity: 1 -> 0.5
- frontend/src/pages/inbox/InboxProfileModal.tsx:265 [karte] sig1: cursor: default -> not-allowed; opacity: 1 -> 0.5
- frontend/src/pages/dashboard/PriorityProspectsSection.tsx:410 [composer] sig0: cursor: default -> not-allowed; opacity: 1 -> 0.5
- frontend/src/pages/dashboard/PriorityProspectsSection.tsx:410 [composer] sig1: cursor: default -> not-allowed; opacity: 1 -> 0.5
- frontend/src/pages/dashboard/WeeklyAdvisorSection.tsx:381 [composer] sig0: cursor: default -> not-allowed; opacity: 1 -> 0.5
- frontend/src/pages/dashboard/WeeklyAdvisorSection.tsx:381 [composer] sig1: cursor: default -> not-allowed; opacity: 1 -> 0.5
- frontend/src/pages/schedule/SchedulePageImpl.tsx:378 [schedule] sig0: background-color: rgb(255, 255, 255) -> rgb(226, 232, 240); cursor: default -> not-allowed; opacity: 1 -> 0.5
- frontend/src/pages/schedule/SchedulePageImpl.tsx:378 [schedule] sig1: background-color: rgb(255, 255, 255) -> rgb(226, 232, 240); cursor: default -> not-allowed; opacity: 1 -> 0.5

## DPR2 画素比較（karte 1件・embedded 1件、幅240px固定の clip）

| 対象 | 種類 | 状態 | サイズ(px) | 差分ピクセル |
|---|---|---|---|---|
| frontend/src/pages/inbox/InboxKartePanel.tsx:484 | karte | normal | 504x146 | 0 |
| frontend/src/pages/inbox/InboxKartePanel.tsx:484 | karte | focus | 504x146 | 0 |
| frontend/src/pages/inbox/InboxMessageThread.tsx:736 | embedded | normal | 2412x104 | 0 |
| frontend/src/pages/inbox/InboxMessageThread.tsx:736 | embedded | focus | 2412x104 | 0 |
