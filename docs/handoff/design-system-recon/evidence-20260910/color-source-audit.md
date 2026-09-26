# 同値色alias監査
基準main 4734fe7f353a07df7ac1608b362f1d61524c79ab。3412以後frontend変更: 0ファイル。
全CSS 50ファイルをPostCSSで宣言解析。設計migration.md:155–168、design.md:790–792/926/930/969。
## 既存9宣言
|file:line|theme/token|before|after|値|
|---|---|---|---|---|
|frontend/src/index.css:32|light --indicator|#1e3a8a|var(--accent)|#1e3a8a|
|frontend/src/index.css:226|dark --indicator|#5b8dd9|var(--accent)|#5b8dd9|
|frontend/src/index.css:40|light --sidebar-item-active-border|#1e3a8a|var(--accent)|#1e3a8a|
|frontend/src/index.css:312|dark --sidebar-item-active-border|#5b8dd9|var(--accent)|#5b8dd9|
|frontend/src/index.css:39|light --sidebar-item-active-color|#1e3a8a|var(--accent)|#1e3a8a|
|frontend/src/index.css:35|light --sidebar-bg|#ffffff|var(--bg-surface)|#ffffff|
|frontend/src/index.css:307|dark --sidebar-bg|#1e293b|var(--bg-surface)|#1e293b|
|frontend/src/index.css:147|light --accent-bg|#1e3a8a|var(--accent)|#1e3a8a|
|frontend/src/index.css:337|dark --accent-bg|#5b8dd9|var(--accent)|#5b8dd9|
## 追加8用途（明暗各1、計16宣言）
|名前|参照|light|dark|元index.css行 light/dark|
|---|---|---|---|---|
|--icon-action|var(--text-secondary)|#4a5568|#cbd5e1|{'light': 18, 'dark': 214}|
|--icon-action-hover|var(--text-primary)|#1a202c|#f1f5f9|{'light': 17, 'dark': 213}|
|--icon-action-danger|var(--danger)|#e53e3e|#f87171|{'light': 45, 'dark': 228}|
|--icon-empty|var(--text-muted)|#718096|#94a3b8|{'light': 19, 'dark': 215}|
|--icon-decorative|var(--accent)|#1e3a8a|#5b8dd9|{'light': 27, 'dark': 221}|
|--icon-search|var(--text-secondary)|#4a5568|#cbd5e1|{'light': 18, 'dark': 214}|
|--icon-status-success|var(--success-text)|#22543d|#bbf7d0|{'light': 51, 'dark': 234}|
|--icon-platform-mail|var(--on-accent)|#ffffff|#ffffff|{'light': 128, 'dark': 317}|
## 使用先（index.cssと合わせ7製品ファイル）
|file:line|before|after|
|---|---|---|
|frontend/src/components.css:738|var(--text-secondary)|var(--icon-action)|
|frontend/src/components.css:753|var(--text-primary)|var(--icon-action-hover)|
|frontend/src/components.css:754|var(--danger)|var(--icon-action-danger)|
|frontend/src/components/EmptyState.css:31|var(--text-muted)|var(--icon-empty)|
|frontend/src/pages/dashboard/DashboardPage.css:99|var(--accent)|var(--icon-decorative)|
|frontend/src/pages/inbox/InboxPage.css:122|var(--text-secondary)|var(--icon-search)|
|frontend/src/pages/inbox/InboxPage.css:1379|var(--success-text)|var(--icon-status-success)|
|frontend/src/constants/icons.tsx:320|EnvelopeIcon color="white"|color属性のみ削除、数値size/DOM保持|
|frontend/src/constants/platform-icon.css:14|mailのcolor指定なし|color: var(--icon-platform-mail)追加|
## 特殊scope宣言
[]
## 除外
- Badge/sidebar/mobile/CalendarStatusBarの全体文字をアイコン専用用途へ移さない
- GoogleCalendarStatusBar useEffect変更を除外
- link/accent-hover/link-active-bgとsidebar背景・dark active文字の配色変更を除外
- color-mixの影/focus/glow/subtle変更は別便
- tokens.css --cal-*削除は動的参照未確認につき除外、calendar別便
- CLAUDE.md/旧recon/末尾空行整理を除外
- 使わない8用途は追加しない
## 限界と追加確認
- 静的CSS解決値。ブラウザーcomputed/目視未実施。
- 全50CSSで候補source/destinationの特殊scope宣言0。src全体のsetProperty/removeProperty/insertRule/replaceSync/cssText一致0。対象TS文字列はDashboard読取とDesignSystem表示名で、候補の動的上書きは検出0。未使用削除の一般的安全性を証明するものではない。
- 補助コマンド初回はroot cwdでPostCSS解決失敗、別rgでoption順序誤り。修正再実行成功。製品変更0。
旧PRの実gh pr diff全文とhead/baseSHA、再測定ログはJSONに保存。mailは旧on-solidではなく設計§Zのon-accent。
