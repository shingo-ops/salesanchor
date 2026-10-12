# AY-2a 外観同等性（Chromium 147.0.7727.15、light、幅1280・375）

## FormField.css を最後に読む順

条件 408（対象33件 × 幅2 × 祖先シグネチャ × 通常・focus・disabled、G38 は空値あり/なしの2通り。各 68 項目）。console 警告: なし

### 判定対象（通常・focus）の computed 差分: 0 条件

種類×幅×状態の差分条件数: {}


### 参考（33件とも disabled 属性なし。disabled を付けた状態）: 差分 136 条件

- frontend/src/pages/inbox/InboxKartePanel.tsx:372|w1280|default|sig0: cursor: default -> not-allowed; opacity: 1 -> 0.5
- frontend/src/pages/inbox/InboxKartePanel.tsx:372|w1280|default|sig1: cursor: default -> not-allowed; opacity: 1 -> 0.5
- frontend/src/pages/inbox/InboxKartePanel.tsx:379|w1280|default|sig0: cursor: default -> not-allowed; opacity: 1 -> 0.5
- frontend/src/pages/inbox/InboxKartePanel.tsx:379|w1280|default|sig1: cursor: default -> not-allowed; opacity: 1 -> 0.5
- frontend/src/pages/inbox/InboxKartePanel.tsx:386|w1280|default|sig0: cursor: default -> not-allowed; opacity: 1 -> 0.5
- frontend/src/pages/inbox/InboxKartePanel.tsx:386|w1280|default|sig1: cursor: default -> not-allowed; opacity: 1 -> 0.5

### DPR2 画素比較（karte 1件・search 1件、幅240px固定の clip、幅1280・375、通常・focus）

| 対象 | サイズ(px) | 差分ピクセル |
|---|---|---|
| frontend/src/pages/inbox/InboxKartePanel.tsx:372|w1280|normal | 504x88 | 0 |
| frontend/src/pages/inbox/InboxKartePanel.tsx:372|w1280|focus | 504x88 | 0 |
| frontend/src/pages/inbox/InboxKartePanel.tsx:372|w375|normal | 504x88 | 0 |
| frontend/src/pages/inbox/InboxKartePanel.tsx:372|w375|focus | 504x88 | 0 |
| frontend/src/pages/inbox/InboxConversationList.tsx:62|w1280|normal | 504x98 | 0 |
| frontend/src/pages/inbox/InboxConversationList.tsx:62|w1280|focus | 504x98 | 0 |
| frontend/src/pages/inbox/InboxConversationList.tsx:62|w375|normal | 504x98 | 0 |
| frontend/src/pages/inbox/InboxConversationList.tsx:62|w375|focus | 504x98 | 0 |

## FormField.css を最初（index.css の次）に読む順

条件 408（対象33件 × 幅2 × 祖先シグネチャ × 通常・focus・disabled、G38 は空値あり/なしの2通り。各 68 項目）。console 警告: なし

### 判定対象（通常・focus）の computed 差分: 0 条件

種類×幅×状態の差分条件数: {}


### 参考（33件とも disabled 属性なし。disabled を付けた状態）: 差分 136 条件

- frontend/src/pages/inbox/InboxKartePanel.tsx:372|w1280|default|sig0: cursor: default -> not-allowed; opacity: 1 -> 0.5
- frontend/src/pages/inbox/InboxKartePanel.tsx:372|w1280|default|sig1: cursor: default -> not-allowed; opacity: 1 -> 0.5
- frontend/src/pages/inbox/InboxKartePanel.tsx:379|w1280|default|sig0: cursor: default -> not-allowed; opacity: 1 -> 0.5
- frontend/src/pages/inbox/InboxKartePanel.tsx:379|w1280|default|sig1: cursor: default -> not-allowed; opacity: 1 -> 0.5
- frontend/src/pages/inbox/InboxKartePanel.tsx:386|w1280|default|sig0: cursor: default -> not-allowed; opacity: 1 -> 0.5
- frontend/src/pages/inbox/InboxKartePanel.tsx:386|w1280|default|sig1: cursor: default -> not-allowed; opacity: 1 -> 0.5

### DPR2 画素比較（karte 1件・search 1件、幅240px固定の clip、幅1280・375、通常・focus）

| 対象 | サイズ(px) | 差分ピクセル |
|---|---|---|
| frontend/src/pages/inbox/InboxKartePanel.tsx:372|w1280|normal | 504x88 | 0 |
| frontend/src/pages/inbox/InboxKartePanel.tsx:372|w1280|focus | 504x88 | 0 |
| frontend/src/pages/inbox/InboxKartePanel.tsx:372|w375|normal | 504x88 | 0 |
| frontend/src/pages/inbox/InboxKartePanel.tsx:372|w375|focus | 504x88 | 0 |
| frontend/src/pages/inbox/InboxConversationList.tsx:62|w1280|normal | 504x98 | 0 |
| frontend/src/pages/inbox/InboxConversationList.tsx:62|w1280|focus | 504x98 | 0 |
| frontend/src/pages/inbox/InboxConversationList.tsx:62|w375|normal | 504x98 | 0 |
| frontend/src/pages/inbox/InboxConversationList.tsx:62|w375|focus | 504x98 | 0 |
