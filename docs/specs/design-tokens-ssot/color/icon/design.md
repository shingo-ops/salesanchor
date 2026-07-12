# design — 単色アイコンのcurrentColor化

親: [../README.md](../README.md)

> 1行要約: 単色アイコンの `fill` / `stroke` を `currentColor` にし、色を親要素の `color`（CSS 変数）で制御する。既存トークンに寄せられる色は寄せ、アイコン独自色は最小限に留める。複数色アイコンは本 design 対象外。

## 1. あるべき姿

親テーマ `ideal-state.md` を正本とする。単色アイコンは 1 箇所の `color` 指定で全体に反映され、SVG 側には色の直書きが残らない状態。

## 2. KGI（○×）

| # | 合格条件 | 測り方 | 合格ライン |
|---|---|---|---|
| ① | 対象単色アイコンの `fill` / `stroke` 直書き hex が 0 件になったか | grep 件数 | 0 |
| ② | 対象単色アイコンが `fill="currentColor"` / `stroke="currentColor"` になったか | 該当数 ÷ 対象数 | 満数 |
| ③ | 親要素の `color` が CSS 変数（既存 or icon 専用トークン）で指定されたか | 指定済み ÷ 対象数 | 満数 |
| ④ | 新規追加の icon 専用トークンが確定最小セットに限られるか | 新規数 = 最小セット数 | 一致 |

## 3. design（技術 How）

### 3-1. icon 専用トークンの定義（独自色分のみ・最小セット）

icon 専用新規トークン: `0` 件

理由:
- `recon-icon-mono-multi.md` の単色アイコン 18 件のうち、独自色として残るものはなかった。
- 固定色の `PlatformIcon(mail)` は `#ffffff` で、既存 `--on-accent` と値一致だった。

### 3-2. 単色アイコンの currentColor 化対応表

| アイコン | 現在の書き方 | currentColor化後 | 親 color に指定するトークン | file:line |
|---|---|---|---|---|
| `CheckIcon` | `stroke="currentColor"` / `className` あり | 変更不要（既に currentColor） | 親の `color` を継承 | `frontend/src/components/loading/icons.tsx:3-7` |
| `CloseIcon` | `stroke="currentColor"` / `className` あり | 変更不要（既に currentColor） | 親の `color` を継承 | `frontend/src/components/loading/icons.tsx:11-15` |
| `TopBar hamburger` | `stroke="currentColor"` | 変更不要（既に currentColor） | 親の `color` を継承 | `frontend/src/components/MobileShell.stories.tsx:28-34` |
| `DrawerOpen hamburger` | `stroke="currentColor"` | 変更不要（既に currentColor） | 親の `color` を継承 | `frontend/src/components/MobileShell.stories.tsx:53-61` |
| `DrawerOpen close` | `stroke="currentColor"` | 変更不要（既に currentColor） | 親の `color` を継承 | `frontend/src/components/MobileShell.stories.tsx:77-83` |
| `DrawerClosed hamburger` | `stroke="currentColor"` | 変更不要（既に currentColor） | 親の `color` を継承 | `frontend/src/components/MobileShell.stories.tsx:110-120` |
| `ThreeDotButton` | `fill="currentColor"` | 変更不要（既に currentColor） | 親の `color` を継承 | `frontend/src/pages/inbox/InboxHeaderMenu.stories.tsx:26-44` |
| `MenuOpen unread` | `fill="currentColor"` | 変更不要（既に currentColor） | 親の `color` を継承 | `frontend/src/pages/inbox/InboxHeaderMenu.stories.tsx:61-64` |
| `MenuOpen archive` | `fill="currentColor"` | 変更不要（既に currentColor） | 親の `color` を継承 | `frontend/src/pages/inbox/InboxHeaderMenu.stories.tsx:67-70` |
| `MenuOpen delete` | `fill="currentColor"` | 変更不要（既に currentColor） | 親の `color` を継承 | `frontend/src/pages/inbox/InboxHeaderMenu.stories.tsx:73-76` |
| `MenuOpen customer` | `fill="currentColor"` | 変更不要（既に currentColor） | 親の `color` を継承 | `frontend/src/pages/inbox/InboxHeaderMenu.stories.tsx:79-82` |
| `HeaderButton icon`（1） | `stroke="currentColor"` | 変更不要（既に currentColor） | 親の `color` を継承 | `frontend/src/components/HeaderButton.stories.tsx:50-61` |
| `HeaderButton icon`（2） | `stroke="currentColor"` | 変更不要（既に currentColor） | 親の `color` を継承 | `frontend/src/components/HeaderButton.stories.tsx:78-87` |
| `DesignSystem icon-btn`（1） | `stroke="currentColor"` / `fill="currentColor"` | 変更不要（既に currentColor） | 親の `color` を継承 | `frontend/src/pages/design-system/DesignSystemPage.tsx:171-175` |
| `DesignSystem icon-btn`（2） | `stroke="currentColor"` | 変更不要（既に currentColor） | 親の `color` を継承 | `frontend/src/pages/design-system/DesignSystemPage.tsx:419-422` |
| `DesignSystem combined icon` | `stroke="currentColor"` | 変更不要（既に currentColor） | 親の `color` を継承 | `frontend/src/pages/design-system/DesignSystemPage.tsx:431-434` |
| `LeadChatIcon` | `className` あり / `color` 未指定 | 変更不要（Heroicons の既定で currentColor） | 親の `color` を継承 | `frontend/src/constants/icons.tsx:407-408` |
| `PlatformIcon(mail)` | `color="white"` | `currentColor` に変更する場合は親の `color` を使う | `--on-accent` | `frontend/src/constants/icons.tsx:312-320` |

## 4. 弊害・トレードオフ

- 既存トークンに寄せるものは、親の `color` 指定に従って見た目が変わる。
- `currentColor` は 1 色のみ制御可能。複数色アイコンは本 design の対象外で、別途個別設計が必要。
- フロントのみ・バックエンド不変・GO 不要。

## 5. 受入基準

- KGI①〜④を実装後に grep で実測。

## 6. 維持の仕組み

- SVG アイコンに色の直書きを戻さず、`currentColor` と親 `color` の組み合わせで統一する。
- `PlatformIcon(mail)` のような固定色は、既存トークン `--on-accent` との対応を維持する。

## 7. 接触面分析（6面）

- ①人: 利用者はアイコン色のわずかな変化を受ける
- ②エージェント: 実装役
- ③機械: Visual Gate
- ④データ: 影響なし
- ⑤本番: 影響なし（migrations 無し）
- ⑥外部: 影響なし
