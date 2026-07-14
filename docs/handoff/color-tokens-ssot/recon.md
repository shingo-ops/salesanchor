# recon.md — color tokens SSoT 調査

> 作成: 2026-07-09 | 担当: Codex | 鮮度: `git fetch origin` → `git rev-parse origin/main` = `9c7f004a5ada0f1ec5b14818d0a367c0051f0b2d`

---

## 1. 全体像

- `git fetch origin && git rev-parse origin/main` の結果: `9c7f004a5ada0f1ec5b14818d0a367c0051f0b2d`
- `frontend/src` の対象ファイル数: `333`
- `frontend/src` の `*.css` / `*.scss` ファイル数: `42`
- 前回報告の `39件` とは不一致。現行は `42件`。

### 対象ファイル一覧（CSS/SCSS 42件）

```text
frontend/src/company-forms.css
frontend/src/components/Badge.css
frontend/src/components/Button.css
frontend/src/components/Card.css
frontend/src/components/DataTable.css
frontend/src/components/Drawer.css
frontend/src/components/EmptyState.css
frontend/src/components/FormField.css
frontend/src/components/Modal.css
frontend/src/components/SubMenu.css
frontend/src/components/Tabs.css
frontend/src/components.css
frontend/src/constants/platform-icon.css
frontend/src/hub-shell.css
frontend/src/index.css
frontend/src/loading-animations.css
frontend/src/mobile-shell.css
frontend/src/pages/account-settings/account-settings.css
frontend/src/pages/admin/admin-hub.css
frontend/src/pages/crm/CustomerHubPage.css
frontend/src/pages/dashboard/DashboardPage.css
frontend/src/pages/dashboard/FollowUpsPage.css
frontend/src/pages/dashboard/FunnelReasonsPage.css
frontend/src/pages/dashboard/FunnelRevenuePage.css
frontend/src/pages/dashboard/FunnelSection.css
frontend/src/pages/dashboard/PriorityProspectsSection.css
frontend/src/pages/dashboard/WeeklyAdvisorSection.css
frontend/src/pages/design-preview/DesignPreviewPage.css
frontend/src/pages/design-system/DesignSystemPage.css
frontend/src/pages/goal-setting/GoalSettingPage.css
frontend/src/pages/inbox/InboxPage.css
frontend/src/pages/integrations/CarrierIntegrationPage.css
frontend/src/pages/integrations/FedexLabelValidationTab.css
frontend/src/pages/management-center/ManagementCenterPage.css
frontend/src/pages/schedule.css
frontend/src/pages/super-admin/ParseReviewPage.css
frontend/src/pages/teams/TeamsPage.css
frontend/src/pages-layout.css
frontend/src/responsive.css
frontend/src/sidebar.css
frontend/src/tokens.css
frontend/src/topbar.css
```

### 読み込み起点

```text
frontend/src/main.tsx:4: import './index.css'
frontend/src/pages/schedule/SchedulePageImpl.tsx:6: * ADR-067: 色・寸法は CSS 変数参照のみ。
frontend/src/pages/schedule/SchedulePageImpl.tsx:15: import { CALENDARS, CALENDAR_MAP, type CalendarId, cssVar } from "../../features/schedule/calendars.config";
```

## 2. 共用部品（正引き・逆引きの突合）

- 色-bearing custom prop: `159` unique names / `306` declaration occurrences / `1927` `var()` reference occurrences
- 分類: 生きている `125` / 孤児 `34` / 要調査 `0`

### 2-a. 生きているパーツ

```text
--accent | defs:2 | frontend/src/index.css:26, frontend/src/index.css:219 | refs:179 | frontend/src/company-forms.css:68, frontend/src/company-forms.css:69 | 生きている
--accent-bg | defs:2 | frontend/src/index.css:145, frontend/src/index.css:334 | refs:2 | frontend/src/components/InventorySearchBar.tsx:310, frontend/src/components/InventorySearchBar.tsx:326 | 生きている
--accent-bg-subtle | defs:2 | frontend/src/index.css:76, frontend/src/index.css:256 | refs:19 | frontend/src/components/Button.stories.tsx:98, frontend/src/loading-animations.css:319 | 生きている
--accent-bright | defs:2 | frontend/src/index.css:186, frontend/src/index.css:375 | refs:1 | frontend/src/tokens.css:350 | 生きている
--accent-hover | defs:2 | frontend/src/index.css:27, frontend/src/index.css:220 | refs:12 | frontend/src/components.css:65, frontend/src/components.css:163 | 生きている
--avatar-bg | defs:2 | frontend/src/index.css:30, frontend/src/index.css:223 | refs:2 | frontend/src/pages/inbox/InboxPage.css:314, frontend/src/pages/inbox/InboxPage.css:777 | 生きている
--banner-error-bg | defs:2 | frontend/src/index.css:57, frontend/src/index.css:239 | refs:1 | frontend/src/pages/channels/ChannelsPage.tsx:314 | 生きている
--banner-error-text | defs:2 | frontend/src/index.css:58, frontend/src/index.css:240 | refs:2 | frontend/src/pages/channels/ChannelsPage.tsx:320, frontend/src/pages/channels/ChannelsPage.tsx:326 | 生きている
--banner-success-bg | defs:2 | frontend/src/index.css:53, frontend/src/index.css:235 | refs:1 | frontend/src/pages/channels/ChannelsPage.tsx:311 | 生きている
--banner-success-text | defs:2 | frontend/src/index.css:54, frontend/src/index.css:236 | refs:2 | frontend/src/pages/channels/ChannelsPage.tsx:317, frontend/src/pages/channels/ChannelsPage.tsx:323 | 生きている
--banner-warning-bg | defs:2 | frontend/src/index.css:55, frontend/src/index.css:237 | refs:1 | frontend/src/pages/channels/ChannelsPage.tsx:313 | 生きている
--banner-warning-text | defs:2 | frontend/src/index.css:56, frontend/src/index.css:238 | refs:2 | frontend/src/pages/channels/ChannelsPage.tsx:319, frontend/src/pages/channels/ChannelsPage.tsx:325 | 生きている
--bg-active | defs:2 | frontend/src/index.css:13, frontend/src/index.css:209 | refs:7 | frontend/src/components.css:425, frontend/src/loading-animations.css:103 | 生きている
--bg-badge | defs:2 | frontend/src/index.css:146, frontend/src/index.css:335 | refs:1 | frontend/src/components/InventorySearchBar.tsx:465 | 生きている
--bg-disabled | defs:2 | frontend/src/index.css:138, frontend/src/index.css:326 | refs:3 | frontend/src/pages/super-admin/ParseReviewPage.tsx:541, frontend/src/pages/super-admin/ParseReviewPage.tsx:712 | 生きている
--bg-hover | defs:2 | frontend/src/index.css:12, frontend/src/index.css:208 | refs:49 | frontend/src/company-forms.css:64, frontend/src/components/DataTable.css:122 | 生きている
--bg-primary | defs:2 | frontend/src/index.css:9, frontend/src/index.css:205 | refs:30 | frontend/src/components/NavDropdown.stories.tsx:16, frontend/src/components/NavItemList.stories.tsx:46 | 生きている
--bg-row-zero-stock | defs:2 | frontend/src/index.css:141, frontend/src/index.css:330 | refs:1 | frontend/src/components.css:245 | 生きている
--bg-row-zero-stock-hover | defs:2 | frontend/src/index.css:142, frontend/src/index.css:331 | refs:1 | frontend/src/components.css:249 | 生きている
--bg-subtle | defs:2 | frontend/src/index.css:11, frontend/src/index.css:207 | refs:67 | frontend/src/components/ContactChannelForm.tsx:282, frontend/src/components/DataTable.css:71 | 生きている
--bg-surface | defs:2 | frontend/src/index.css:10, frontend/src/index.css:206 | refs:128 | frontend/src/company-forms.css:82, frontend/src/company-forms.css:107 | 生きている
--border | defs:2 | frontend/src/index.css:21, frontend/src/index.css:215 | refs:177 | frontend/src/company-forms.css:43, frontend/src/company-forms.css:136 | 生きている
--border-color | defs:2 | frontend/src/index.css:143, frontend/src/index.css:332 | refs:10 | frontend/src/components/InventoryPicker.tsx:265, frontend/src/components/InventorySearchBar.tsx:295 | 生きている
--border-icon | defs:2 | frontend/src/index.css:23, frontend/src/index.css:217 | refs:6 | frontend/src/components.css:690, frontend/src/components.css:694 | 生きている
--border-light | defs:2 | frontend/src/index.css:144, frontend/src/index.css:333 | refs:9 | frontend/src/components/InventoryPicker.tsx:312, frontend/src/components/InventorySearchBar.tsx:425 | 生きている
--border-strong | defs:2 | frontend/src/index.css:22, frontend/src/index.css:216 | refs:12 | frontend/src/company-forms.css:104, frontend/src/company-forms.css:163 | 生きている
--bubble-inbound-bg | defs:2 | frontend/src/index.css:94, frontend/src/index.css:272 | refs:1 | frontend/src/pages/inbox/InboxPage.css:522 | 生きている
--bubble-outbound-bg | defs:2 | frontend/src/index.css:95, frontend/src/index.css:273 | refs:1 | frontend/src/pages/inbox/InboxPage.css:516 | 生きている
--calendar-google-blue | defs:2 | frontend/src/index.css:176, frontend/src/index.css:365 | refs:2 | frontend/src/pages/schedule.css:18, frontend/src/tokens.css:371 | 生きている
--calendar-google-blue-light | defs:2 | frontend/src/index.css:177, frontend/src/index.css:366 | refs:2 | frontend/src/pages/schedule.css:17, frontend/src/tokens.css:370 | 生きている
--calendar-grid-border | defs:2 | frontend/src/index.css:181, frontend/src/index.css:370 | refs:1 | frontend/src/tokens.css:351 | 生きている
--calendar-status-error-bg | defs:2 | frontend/src/index.css:184, frontend/src/index.css:373 | refs:1 | frontend/src/components/GoogleCalendarStatusBar.tsx:123 | 生きている
--calendar-status-error-text | defs:2 | frontend/src/index.css:185, frontend/src/index.css:374 | refs:2 | frontend/src/components/GoogleCalendarStatusBar.tsx:124, frontend/src/components/GoogleCalendarStatusBar.tsx:134 | 生きている
--calendar-status-ok-bg | defs:2 | frontend/src/index.css:182, frontend/src/index.css:371 | refs:1 | frontend/src/components/GoogleCalendarStatusBar.tsx:114 | 生きている
--calendar-status-ok-text | defs:2 | frontend/src/index.css:183, frontend/src/index.css:372 | refs:1 | frontend/src/components/GoogleCalendarStatusBar.tsx:115 | 生きている
--calendar-today-bg | defs:2 | frontend/src/index.css:178, frontend/src/index.css:367 | refs:2 | frontend/src/index.css:186, frontend/src/index.css:375 | 生きている
--color-chip-count-bg | defs:2 | frontend/src/index.css:82, frontend/src/index.css:261 | refs:1 | frontend/src/pages/dashboard/FollowUpsPage.css:60 | 生きている
--color-hover-overlay | defs:2 | frontend/src/index.css:81, frontend/src/index.css:260 | refs:4 | frontend/src/pages/inbox/InboxPage.css:57, frontend/src/pages/inbox/InboxPage.css:263 | 生きている
--color-separator-subtle | defs:2 | frontend/src/index.css:83, frontend/src/index.css:262 | refs:1 | frontend/src/pages/inbox/InboxPage.css:436 | 生きている
--color-warning | defs:2 | frontend/src/index.css:137, frontend/src/index.css:325 | refs:5 | frontend/src/components/InventoryPicker.tsx:370, frontend/src/components/InventorySearchBar.tsx:497 | 生きている
--comp-badge-danger-solid | defs:2 | frontend/src/index.css:114, frontend/src/index.css:292 | refs:1 | frontend/src/components/Badge.css:69 | 生きている
--comp-badge-success-solid | defs:2 | frontend/src/index.css:112, frontend/src/index.css:290 | refs:1 | frontend/src/components/Badge.css:67 | 生きている
--danger | defs:2 | frontend/src/index.css:44, frontend/src/index.css:226 | refs:41 | frontend/src/components/FormField.css:40, frontend/src/components/FormField.css:118 | 生きている
--danger-bg | defs:2 | frontend/src/index.css:45, frontend/src/index.css:227 | refs:30 | frontend/src/components/Badge.css:62, frontend/src/components/DataTable.css:152 | 生きている
--danger-bg-subtle | defs:2 | frontend/src/index.css:75, frontend/src/index.css:255 | refs:6 | frontend/src/components/FormField.css:187, frontend/src/pages/dashboard/DashboardPage.css:338 | 生きている
--danger-text | defs:2 | frontend/src/index.css:46, frontend/src/index.css:228 | refs:16 | frontend/src/components/Badge.css:62, frontend/src/components/FedExRateModal.tsx:258 | 生きている
--focus-ring-shadow | defs:2 | frontend/src/index.css:86, frontend/src/index.css:265 | refs:12 | frontend/src/company-forms.css:125, frontend/src/company-forms.css:189 | 生きている
--inbox-action-icon-color | defs:2 | frontend/src/index.css:123, frontend/src/index.css:301 | refs:1 | frontend/src/pages/inbox/InboxPage.css:480 | 生きている
--inbox-bulk-icon-color | defs:2 | frontend/src/index.css:124, frontend/src/index.css:302 | refs:1 | frontend/src/pages/inbox/InboxPage.css:194 | 生きている
--inbox-separator | defs:2 | frontend/src/index.css:121, frontend/src/index.css:299 | refs:1 | frontend/src/pages/inbox/InboxPage.css:751 | 生きている
--indicator | defs:2 | frontend/src/index.css:31, frontend/src/index.css:224 | refs:1 | frontend/src/pages/inbox/InboxPage.css:302 | 生きている
--info | defs:2 | frontend/src/index.css:109, frontend/src/index.css:287 | refs:1 | frontend/src/components/Badge.css:66 | 生きている
--info-bg | defs:2 | frontend/src/index.css:102, frontend/src/index.css:280 | refs:10 | frontend/src/components/Badge.css:59, frontend/src/components/DataTable.css:127 | 生きている
--info-text | defs:2 | frontend/src/index.css:103, frontend/src/index.css:281 | refs:8 | frontend/src/components/Badge.css:59, frontend/src/components/FedExRateModal.tsx:75 | 生きている
--karte-field-bd | defs:1 | frontend/src/tokens.css:303 | refs:1 | frontend/src/pages/inbox/InboxPage.css:1161 | 生きている
--karte-field-bg | defs:1 | frontend/src/tokens.css:302 | refs:1 | frontend/src/pages/inbox/InboxPage.css:1161 | 生きている
--karte-ok | defs:1 | frontend/src/tokens.css:304 | refs:1 | frontend/src/pages/inbox/InboxPage.css:1366 | 生きている
--lead-contact-bg | defs:2 | frontend/src/index.css:132, frontend/src/index.css:320 | refs:1 | frontend/src/pages-layout.css:461 | 生きている
--lead-contact-text | defs:2 | frontend/src/index.css:133, frontend/src/index.css:321 | refs:1 | frontend/src/pages-layout.css:461 | 生きている
--link | defs:2 | frontend/src/index.css:28, frontend/src/index.css:221 | refs:2 | frontend/src/components/FedExRateModal.tsx:281, frontend/src/pages/inbox/InboxPage.css:845 | 生きている
--link-active-bg | defs:2 | frontend/src/index.css:29, frontend/src/index.css:222 | refs:12 | frontend/src/company-forms.css:74, frontend/src/components/Tabs.css:107 | 生きている
--neutral | defs:2 | frontend/src/index.css:108, frontend/src/index.css:286 | refs:1 | frontend/src/components/Badge.css:65 | 生きている
--neutral-bg | defs:2 | frontend/src/index.css:106, frontend/src/index.css:284 | refs:2 | frontend/src/components/Badge.css:25, frontend/src/components/Badge.css:58 | 生きている
--neutral-text | defs:2 | frontend/src/index.css:107, frontend/src/index.css:285 | refs:2 | frontend/src/components/Badge.css:26, frontend/src/components/Badge.css:58 | 生きている
--on-accent | defs:2 | frontend/src/index.css:127, frontend/src/index.css:315 | refs:37 | frontend/src/components/GoogleCalendarStatusBar.tsx:135, frontend/src/components/InventorySearchBar.tsx:311 | 生きている
--on-solid | defs:1 | frontend/src/tokens.css:455 | refs:15 | frontend/src/components/Badge.css:65, frontend/src/components/Badge.css:66 | 生きている
--overlay-bg | defs:2 | frontend/src/index.css:72, frontend/src/index.css:252 | refs:10 | frontend/src/components/Drawer.css:17, frontend/src/components/Modal.css:15 | 生きている
--platform-mail-bg | defs:2 | frontend/src/index.css:160, frontend/src/index.css:349 | refs:1 | frontend/src/constants/platform-icon.css:15 | 生きている
--platform-unknown-bg | defs:2 | frontend/src/index.css:161, frontend/src/index.css:350 | refs:1 | frontend/src/constants/platform-icon.css:28 | 生きている
--purple-bg | defs:2 | frontend/src/index.css:117, frontend/src/index.css:295 | refs:4 | frontend/src/components.css:401, frontend/src/components.css:407 | 生きている
--purple-text | defs:2 | frontend/src/index.css:118, frontend/src/index.css:296 | refs:4 | frontend/src/components.css:401, frontend/src/components.css:407 | 生きている
--rank-bg | defs:2 | frontend/src/index.css:98, frontend/src/index.css:276 | refs:1 | frontend/src/pages/inbox/InboxPage.css:925 | 生きている
--rank-text | defs:2 | frontend/src/index.css:99, frontend/src/index.css:277 | refs:1 | frontend/src/pages/inbox/InboxPage.css:926 | 生きている
--role-body-color | defs:1 | frontend/src/tokens.css:60 | refs:1 | frontend/src/pages-layout.css:177 | 生きている
--role-caption-color | defs:1 | frontend/src/tokens.css:65 | refs:1 | frontend/src/pages-layout.css:184 | 生きている
--role-card-title-color | defs:1 | frontend/src/tokens.css:55 | refs:1 | frontend/src/pages-layout.css:169 | 生きている
--role-page-title-color | defs:1 | frontend/src/tokens.css:44 | refs:4 | frontend/src/company-forms.css:29, frontend/src/pages-layout.css:21 | 生きている
--role-section-title-color | defs:1 | frontend/src/tokens.css:50 | refs:1 | frontend/src/pages-layout.css:161 | 生きている
--row-hover | defs:2 | frontend/src/index.css:91, frontend/src/index.css:269 | refs:3 | frontend/src/components.css:237, frontend/src/components.css:279 | 生きている
--schedule-calendar-item-swatch-shadow | defs:2 | frontend/src/index.css:187, frontend/src/index.css:376 | refs:1 | frontend/src/pages/schedule.css:309 | 生きている
--schedule-cell-border | defs:2 | frontend/src/pages/schedule.css:12, frontend/src/tokens.css:366 | refs:12 | frontend/src/pages/schedule.css:434, frontend/src/pages/schedule.css:448 | 生きている
--schedule-color-swatch-shadow | defs:2 | frontend/src/index.css:188, frontend/src/index.css:377 | refs:2 | frontend/src/pages/schedule.css:1202, frontend/src/pages/schedule.css:1206 | 生きている
--schedule-control-border | defs:2 | frontend/src/pages/schedule.css:19, frontend/src/tokens.css:372 | refs:1 | frontend/src/pages/schedule.css:125 | 生きている
--schedule-empty-icon-bg | defs:2 | frontend/src/pages/schedule.css:17, frontend/src/tokens.css:370 | refs:1 | frontend/src/pages/schedule.css:392 | 生きている
--schedule-empty-icon-color | defs:2 | frontend/src/pages/schedule.css:18, frontend/src/tokens.css:371 | refs:1 | frontend/src/pages/schedule.css:393 | 生きている
--schedule-gridline | defs:2 | frontend/src/tokens.css:351, frontend/src/tokens.css:540 | refs:3 | frontend/src/pages/schedule.css:12, frontend/src/pages/schedule.css:1033 | 生きている
--schedule-hour-bg | defs:2 | frontend/src/pages/schedule.css:13, frontend/src/tokens.css:367 | refs:2 | frontend/src/pages/schedule.css:449, frontend/src/pages/schedule.css:544 | 生きている
--schedule-hour-label | defs:2 | frontend/src/pages/schedule.css:14, frontend/src/tokens.css:368 | refs:2 | frontend/src/pages/schedule.css:446, frontend/src/pages/schedule.css:552 | 生きている
--schedule-now-line | defs:1 | frontend/src/tokens.css:352 | refs:2 | frontend/src/pages/schedule.css:585, frontend/src/pages/schedule.css:596 | 生きている
--schedule-overlay-scrim | defs:2 | frontend/src/index.css:189, frontend/src/index.css:378 | refs:2 | frontend/src/pages/schedule.css:755, frontend/src/pages/schedule.css:1213 | 生きている
--schedule-rail-bg | defs:2 | frontend/src/pages/schedule.css:10, frontend/src/tokens.css:364 | refs:1 | frontend/src/pages/schedule.css:181 | 生きている
--schedule-rail-border | defs:2 | frontend/src/pages/schedule.css:11, frontend/src/tokens.css:365 | refs:1 | frontend/src/pages/schedule.css:182 | 生きている
--schedule-slot-hover | defs:2 | frontend/src/tokens.css:353, frontend/src/tokens.css:541 | refs:1 | frontend/src/pages/schedule.css:608 | 生きている
--schedule-today | defs:1 | frontend/src/tokens.css:350 | refs:4 | frontend/src/pages/schedule.css:267, frontend/src/pages/schedule.css:500 | 生きている
--search-focus-glow | defs:2 | frontend/src/index.css:88, frontend/src/index.css:267 | refs:1 | frontend/src/components.css:204 | 生きている
--shadow-accent-hover | defs:2 | frontend/src/index.css:69, frontend/src/index.css:250 | refs:2 | frontend/src/pages/goal-setting/GoalSettingPage.css:167, frontend/src/pages-layout.css:647 | 生きている
--shadow-drop-sm | defs:2 | frontend/src/index.css:68, frontend/src/index.css:249 | refs:2 | frontend/src/pages/account-settings/account-settings.css:131, frontend/src/pages-layout.css:350 | 生きている
--shadow-dropdown | defs:2 | frontend/src/index.css:67, frontend/src/index.css:248 | refs:3 | frontend/src/components.css:861, frontend/src/pages/inbox/InboxHeaderMenu.stories.tsx:115 | 生きている
--shadow-lg | defs:2 | frontend/src/index.css:64, frontend/src/index.css:245 | refs:8 | frontend/src/components/ChannelTypeCombobox.tsx:156, frontend/src/components/CountryCombobox.tsx:155 | 生きている
--shadow-md | defs:2 | frontend/src/index.css:63, frontend/src/index.css:244 | refs:14 | frontend/src/components/Card.css:56, frontend/src/components/InventoryPicker.tsx:267 | 生きている
--shadow-modal | defs:2 | frontend/src/index.css:66, frontend/src/index.css:247 | refs:5 | frontend/src/components/Drawer.css:32, frontend/src/components/Modal.css:31 | 生きている
--shadow-sm | defs:2 | frontend/src/index.css:62, frontend/src/index.css:243 | refs:35 | frontend/src/company-forms.css:85, frontend/src/components/Card.css:10 | 生きている
--shadow-xl | defs:2 | frontend/src/index.css:65, frontend/src/index.css:246 | refs:3 | frontend/src/pages/inbox/InboxPage.css:1029, frontend/src/pages/inbox/InboxPage.css:1151 | 生きている
--shadow-xs | defs:2 | frontend/src/index.css:61, frontend/src/index.css:242 | refs:3 | frontend/src/pages/dashboard/DashboardPage.css:28, frontend/src/pages/schedule.css:184 | 生きている
--sidebar-bg | defs:2 | frontend/src/index.css:34, frontend/src/index.css:305 | refs:4 | frontend/src/components/DesktopShell.stories.tsx:29, frontend/src/components/DesktopShell.stories.tsx:77 | 生きている
--sidebar-border | defs:2 | frontend/src/index.css:35, frontend/src/index.css:306 | refs:3 | frontend/src/components/DesktopShell.stories.tsx:30, frontend/src/components/DesktopShell.stories.tsx:78 | 生きている
--sidebar-item-active-bg | defs:2 | frontend/src/index.css:37, frontend/src/index.css:308 | refs:6 | frontend/src/components/SubMenu.css:95, frontend/src/components/SubMenu.css:121 | 生きている
--sidebar-item-active-border | defs:2 | frontend/src/index.css:39, frontend/src/index.css:310 | refs:2 | frontend/src/mobile-shell.css:231, frontend/src/sidebar.css:160 | 生きている
--sidebar-item-active-color | defs:2 | frontend/src/index.css:38, frontend/src/index.css:309 | refs:8 | frontend/src/mobile-shell.css:223, frontend/src/mobile-shell.css:229 | 生きている
--sidebar-item-hover-bg | defs:2 | frontend/src/index.css:36, frontend/src/index.css:307 | refs:4 | frontend/src/mobile-shell.css:222, frontend/src/mobile-shell.css:308 | 生きている
--spinner-on-accent-head | defs:2 | frontend/src/index.css:129, frontend/src/index.css:317 | refs:1 | frontend/src/loading-animations.css:97 | 生きている
--spinner-on-accent-track | defs:2 | frontend/src/index.css:128, frontend/src/index.css:316 | refs:1 | frontend/src/loading-animations.css:96 | 生きている
--success | defs:2 | frontend/src/index.css:136, frontend/src/index.css:324 | refs:28 | frontend/src/index.css:112, frontend/src/loading-animations.css:151 | 生きている
--success-bg | defs:2 | frontend/src/index.css:49, frontend/src/index.css:231 | refs:21 | frontend/src/components/Badge.css:60, frontend/src/components.css:399 | 生きている
--success-bg-subtle | defs:2 | frontend/src/index.css:78, frontend/src/index.css:258 | refs:8 | frontend/src/pages/dashboard/PriorityProspectsSection.css:6, frontend/src/pages/dashboard/PriorityProspectsSection.css:21 | 生きている
--success-text | defs:2 | frontend/src/index.css:50, frontend/src/index.css:232 | refs:23 | frontend/src/components/Badge.css:60, frontend/src/components.css:399 | 生きている
--text-muted | defs:2 | frontend/src/index.css:18, frontend/src/index.css:213 | refs:189 | frontend/src/company-forms.css:36, frontend/src/components/Button.stories.tsx:85 | 生きている
--text-primary | defs:2 | frontend/src/index.css:16, frontend/src/index.css:211 | refs:173 | frontend/src/company-forms.css:63, frontend/src/company-forms.css:108 | 生きている
--text-secondary | defs:2 | frontend/src/index.css:17, frontend/src/index.css:212 | refs:243 | frontend/src/company-forms.css:56, frontend/src/company-forms.css:97 | 生きている
--tooltip-bg | defs:2 | frontend/src/index.css:172, frontend/src/index.css:361 | refs:3 | frontend/src/components.css:634, frontend/src/components.css:651 | 生きている
--tooltip-text | defs:2 | frontend/src/index.css:173, frontend/src/index.css:362 | refs:1 | frontend/src/components.css:633 | 生きている
--warning | defs:2 | frontend/src/index.css:110, frontend/src/index.css:288 | refs:2 | frontend/src/components/Badge.css:68, frontend/src/pages/dashboard/FunnelSection.css:81 | 生きている
--warning-bg | defs:2 | frontend/src/index.css:47, frontend/src/index.css:229 | refs:43 | frontend/src/components/Badge.css:61, frontend/src/components/ContactChannelForm.tsx:241 | 生きている
--warning-bg-subtle | defs:2 | frontend/src/index.css:77, frontend/src/index.css:257 | refs:4 | frontend/src/pages/dashboard/DashboardPage.css:346, frontend/src/pages/dashboard/PriorityProspectsSection.css:119 | 生きている
--warning-text | defs:2 | frontend/src/index.css:48, frontend/src/index.css:230 | refs:59 | frontend/src/components/Badge.css:61, frontend/src/components/ContactChannelForm.tsx:242 | 生きている
```

### 2-b. 孤児

```text
--cal-billing | defs:2 | frontend/src/tokens.css:379, frontend/src/tokens.css:536 | refs:0 | (none) | 孤児
--cal-billing-text | defs:2 | frontend/src/tokens.css:379, frontend/src/tokens.css:536 | refs:0 | (none) | 孤児
--cal-billing-tint | defs:2 | frontend/src/tokens.css:379, frontend/src/tokens.css:536 | refs:0 | (none) | 孤児
--cal-holiday | defs:2 | frontend/src/tokens.css:381, frontend/src/tokens.css:538 | refs:0 | (none) | 孤児
--cal-holiday-text | defs:2 | frontend/src/tokens.css:381, frontend/src/tokens.css:538 | refs:0 | (none) | 孤児
--cal-holiday-tint | defs:2 | frontend/src/tokens.css:381, frontend/src/tokens.css:538 | refs:0 | (none) | 孤児
--cal-meeting | defs:2 | frontend/src/tokens.css:376, frontend/src/tokens.css:533 | refs:0 | (none) | 孤児
--cal-meeting-text | defs:2 | frontend/src/tokens.css:376, frontend/src/tokens.css:533 | refs:0 | (none) | 孤児
--cal-meeting-tint | defs:2 | frontend/src/tokens.css:376, frontend/src/tokens.css:533 | refs:0 | (none) | 孤児
--cal-personal | defs:2 | frontend/src/tokens.css:375, frontend/src/tokens.css:532 | refs:0 | (none) | 孤児
--cal-personal-text | defs:2 | frontend/src/tokens.css:375, frontend/src/tokens.css:532 | refs:0 | (none) | 孤児
--cal-personal-tint | defs:2 | frontend/src/tokens.css:375, frontend/src/tokens.css:532 | refs:0 | (none) | 孤児
--cal-purchase | defs:2 | frontend/src/tokens.css:377, frontend/src/tokens.css:534 | refs:0 | (none) | 孤児
--cal-purchase-text | defs:2 | frontend/src/tokens.css:377, frontend/src/tokens.css:534 | refs:0 | (none) | 孤児
--cal-purchase-tint | defs:2 | frontend/src/tokens.css:377, frontend/src/tokens.css:534 | refs:0 | (none) | 孤児
--cal-release | defs:2 | frontend/src/tokens.css:380, frontend/src/tokens.css:537 | refs:0 | (none) | 孤児
--cal-release-text | defs:2 | frontend/src/tokens.css:380, frontend/src/tokens.css:537 | refs:0 | (none) | 孤児
--cal-release-tint | defs:2 | frontend/src/tokens.css:380, frontend/src/tokens.css:537 | refs:0 | (none) | 孤児
--cal-shipping | defs:2 | frontend/src/tokens.css:378, frontend/src/tokens.css:535 | refs:0 | (none) | 孤児
--cal-shipping-text | defs:2 | frontend/src/tokens.css:378, frontend/src/tokens.css:535 | refs:0 | (none) | 孤児
--cal-shipping-tint | defs:2 | frontend/src/tokens.css:378, frontend/src/tokens.css:535 | refs:0 | (none) | 孤児
--calendar-today-cell-bg | defs:2 | frontend/src/index.css:180, frontend/src/index.css:369 | refs:0 | (none) | 孤児
--calendar-today-text | defs:2 | frontend/src/index.css:179, frontend/src/index.css:368 | refs:0 | (none) | 孤児
--color-amber-50 | defs:2 | frontend/src/index.css:155, frontend/src/index.css:344 | refs:0 | (none) | 孤児
--color-amber-800 | defs:2 | frontend/src/index.css:156, frontend/src/index.css:345 | refs:0 | (none) | 孤児
--color-blue-100 | defs:2 | frontend/src/index.css:149, frontend/src/index.css:338 | refs:0 | (none) | 孤児
--color-blue-700 | defs:2 | frontend/src/index.css:150, frontend/src/index.css:339 | refs:0 | (none) | 孤児
--color-border-subtle | defs:2 | frontend/src/index.css:157, frontend/src/index.css:346 | refs:0 | (none) | 孤児
--color-gray-100 | defs:2 | frontend/src/index.css:151, frontend/src/index.css:340 | refs:0 | (none) | 孤児
--color-gray-600 | defs:2 | frontend/src/index.css:152, frontend/src/index.css:341 | refs:0 | (none) | 孤児
--color-red-50 | defs:2 | frontend/src/index.css:153, frontend/src/index.css:342 | refs:0 | (none) | 孤児
--color-red-700 | defs:2 | frontend/src/index.css:154, frontend/src/index.css:343 | refs:0 | (none) | 孤児
--inbox-hover | defs:2 | frontend/src/index.css:122, frontend/src/index.css:300 | refs:0 | (none) | 孤児
--karte-ok-bg | defs:1 | frontend/src/tokens.css:305 | refs:0 | (none) | 孤児
```

### 2-c. 動的組み立ての気配

- `var(--...)` 参照は静的抽出のみ。テンプレートリテラルや JS 文字列連結で name を組み立てる箇所は、今回の grep ベース抽出では補足できない。
- 現在の確認範囲で、`frontend/src` 内に `var(--` を組み立てる明示的な動的名生成は見つかっていない。

## 3. 非共用部品（ベタ書き）

- 直接色リテラル: `229` unique values / `371` occurrences

```text
#1e3a8a | count:14 | frontend/src/index.css:26
#ffffff | count:9 | frontend/src/index.css:10
#147 | count:8 | frontend/src/components/CompanyContactSelector.tsx:19
#5b8dd9 | count:8 | frontend/src/index.css:219
#334155 | count:7 | frontend/src/index.css:208
#145 | count:5 | frontend/src/components/MergeCompanyModal.tsx:2
rgba(0, 0, 0, 0.4) | count:5 | frontend/src/index.css:72
#0f172a | count:4 | frontend/src/index.css:205
#1a73e8 | count:4 | frontend/src/features/schedule/calendars.config.ts:23
#1e3a5f | count:4 | frontend/src/index.css:280
#475569 | count:4 | frontend/src/index.css:209
#e2e8f0 | count:4 | frontend/src/index.css:12
rgba(0, 0, 0, 0.08) | count:4 | frontend/src/index.css:62
rgba(255, 255, 255, 0.4) | count:4 | frontend/src/index.css:128
#164 | count:3 | frontend/src/components/MergeCompanyModal.tsx:44
#166 | count:3 | frontend/src/App.tsx:131
#1e293b | count:3 | frontend/src/index.css:206
#2624 | count:3 | frontend/src/pages/inbox/InboxMessageThread.tsx:265
#2d3b52 | count:3 | frontend/src/index.css:269
#2e7d32 | count:3 | frontend/src/index.css:111
#374151 | count:3 | frontend/src/features/schedule/calendars.config.ts:65
#4ade80 | count:3 | frontend/src/index.css:289
#64748b | count:3 | frontend/src/index.css:286
#93c5fd | count:3 | frontend/src/index.css:281
#94a3b8 | count:3 | frontend/src/index.css:213
#d97706 | count:3 | frontend/src/index.css:110
#e6f4ea | count:3 | frontend/src/features/schedule/calendars.config.ts:40
#e8f0fe | count:3 | frontend/src/features/schedule/calendars.config.ts:24
#ea4335 | count:3 | frontend/src/index.css:160
#ebeff8 | count:3 | frontend/src/index.css:29
#f3f4f6 | count:3 | frontend/src/features/schedule/calendars.config.ts:64
#f87171 | count:3 | frontend/src/index.css:226
rgba(0, 0, 0, 0.05) | count:3 | frontend/src/index.css:61
rgba(30, 58, 138, 0.15) | count:3 | frontend/src/index.css:69
#14432b | count:2 | frontend/src/index.css:231
#1d4ed8 | count:2 | frontend/src/index.css:150
#243046 | count:2 | frontend/src/index.css:207
#2563eb | count:2 | frontend/src/index.css:109
#2601 | count:2 | frontend/src/pages/integrations/CarrierCredentialForm.tsx:93
#3b82f6 | count:2 | frontend/src/index.css:287
#4a5568 | count:2 | frontend/src/index.css:17
#4c1d1d | count:2 | frontend/src/index.css:227
#6b21a8 | count:2 | frontend/src/features/schedule/calendars.config.ts:33
#718096 | count:2 | frontend/src/index.css:18
#744210 | count:2 | frontend/src/index.css:48
#8ab4f8 | count:2 | frontend/src/index.css:365
#92400e | count:2 | frontend/src/features/schedule/calendars.config.ts:57
#999999 | count:2 | frontend/src/index.css:161
#b91c1c | count:2 | frontend/src/features/schedule/calendars.config.ts:49
#cbd5e0 | count:2 | frontend/src/index.css:13
#e53e3e | count:2 | frontend/src/index.css:44
#fbd38d | count:2 | frontend/src/index.css:132
#fca5a5 | count:2 | frontend/src/index.css:240
#fcd34d | count:2 | frontend/src/index.css:238
#fce8e6 | count:2 | frontend/src/features/schedule/calendars.config.ts:48
#fde68a | count:2 | frontend/src/index.css:230
rgb(250, 241, 241) | count:2 | frontend/src/index.css:168
rgb(30, 20, 20) | count:2 | frontend/src/index.css:357
rgba(0, 0, 0, 0.2) | count:2 | frontend/src/index.css:66
rgba(0, 0, 0, 0.3) | count:2 | frontend/src/index.css:242
rgba(0, 0, 0, 0.35) | count:2 | frontend/src/index.css:248
rgba(0, 0, 0, 0.5) | count:2 | frontend/src/index.css:246
rgba(15, 23, 42, 0.12) | count:2 | frontend/src/index.css:189
rgba(255, 255, 255, 0.16) | count:2 | frontend/src/index.css:188
rgba(255, 255, 255, 0.25) | count:2 | frontend/src/index.css:82
rgba(91, 141, 217, 0.3) | count:2 | frontend/src/index.css:265
#000000 | count:1 | frontend/src/index.css:23
#06b6d4 | count:1 | frontend/src/pages/roles/RolesPage.tsx:82
#0b6e66 | count:1 | frontend/src/tokens.css:380
#0c322d | count:1 | frontend/src/tokens.css:537
#0d9488 | count:1 | frontend/src/tokens.css:380
#0f9d58 | count:1 | frontend/src/features/schedule/calendars.config.ts:39
#0f9d77 | count:1 | frontend/src/tokens.css:304
#131c2c | count:1 | frontend/src/index.css:330
#137333 | count:1 | frontend/src/index.css:54
#142c1b | count:1 | frontend/src/tokens.css:534
#14b8a6 | count:1 | frontend/src/pages/roles/RolesPage.tsx:81
#152 | count:1 | frontend/src/components/MergeCompanyModal.tsx:2
#15803d | count:1 | frontend/src/index.css:290
#16263f | count:1 | frontend/src/tokens.css:533
#163171 | count:1 | frontend/src/index.css:27
#166534 | count:1 | frontend/src/features/schedule/calendars.config.ts:41
#174ea6 | count:1 | frontend/src/features/schedule/calendars.config.ts:25
#1a202c | count:1 | frontend/src/index.css:16
#1a3a25 | count:1 | frontend/src/index.css:235
#1b2536 | count:1 | frontend/src/index.css:331
#1c2742 | count:1 | frontend/src/tokens.css:532
#1e7e34 | count:1 | frontend/src/index.css:183
#1f2937 | count:1 | frontend/src/index.css:340
#1f2a3a | count:1 | frontend/src/tokens.css:538
#22543d | count:1 | frontend/src/index.css:50
#22613f | count:1 | frontend/src/tokens.css:377
#22c55e | count:1 | frontend/src/pages/roles/RolesPage.tsx:80
#271a45 | count:1 | frontend/src/tokens.css:535
#2b6cb0 | count:1 | frontend/src/index.css:103
#2dd4bf | count:1 | frontend/src/tokens.css:537
#3a1515 | count:1 | frontend/src/index.css:239
#3a2300 | count:1 | frontend/src/index.css:237
#3a2a10 | count:1 | frontend/src/tokens.css:536
#3b1f6e | count:1 | frontend/src/index.css:295
#3b2d5c | count:1 | frontend/src/index.css:335
#3c4043 | count:1 | frontend/src/index.css:370
#3d2200 | count:1 | frontend/src/index.css:276
#3d2b00 | count:1 | frontend/src/index.css:320
#3d2f0c | count:1 | frontend/src/index.css:229
#431407 | count:1 | frontend/src/index.css:344
#450a0a | count:1 | frontend/src/index.css:342
#4b5563 | count:1 | frontend/src/index.css:152
#4d7fc8 | count:1 | frontend/src/index.css:220
#553c9a | count:1 | frontend/src/index.css:118
#5b3aa8 | count:1 | frontend/src/tokens.css:378
#5bb36a | count:1 | frontend/src/tokens.css:534
#5f6368 | count:1 | frontend/src/features/schedule/calendars.config.ts:63
#6366f1 | count:1 | frontend/src/pages/roles/RolesPage.tsx:84
#6c757d | count:1 | frontend/src/pages/roles/RolesPage.tsx:262
#6d28d9 | count:1 | frontend/src/index.css:273
#6f8fd6 | count:1 | frontend/src/tokens.css:532
#7baee0 | count:1 | frontend/src/index.css:221
#7c3aed | count:1 | frontend/src/tokens.css:378
#7e22ce | count:1 | frontend/src/features/schedule/calendars.config.ts:71
#84cc16 | count:1 | frontend/src/pages/roles/RolesPage.tsx:79
#86efac | count:1 | frontend/src/index.css:236
#888 | count:1 | frontend/src/components/FormField.css:73
#8B2EF5 | count:1 | frontend/src/index.css:95
#8de6da | count:1 | frontend/src/tokens.css:537
#9333ea | count:1 | frontend/src/features/schedule/calendars.config.ts:31
#9a5800 | count:1 | frontend/src/tokens.css:379
#9b2c2c | count:1 | frontend/src/index.css:46
#9ca3af | count:1 | frontend/src/index.css:341
#9dc0ef | count:1 | frontend/src/tokens.css:533
#E4E4E7 | count:1 | frontend/src/index.css:35
#E65100 | count:1 | frontend/src/index.css:99
#EFEFEF | count:1 | frontend/src/index.css:94
#FFF3E0 | count:1 | frontend/src/index.css:98
#a45a00 | count:1 | frontend/src/index.css:56
#a50e0e | count:1 | frontend/src/index.css:58
#a78bfa | count:1 | frontend/src/tokens.css:535
#a7e0b2 | count:1 | frontend/src/tokens.css:534
#a855f7 | count:1 | frontend/src/pages/roles/RolesPage.tsx:85
#aac3ef | count:1 | frontend/src/tokens.css:532
#bbf7d0 | count:1 | frontend/src/index.css:232
#bee3f8 | count:1 | frontend/src/index.css:102
#c08a00 | count:1 | frontend/src/index.css:137
#c2cdda | count:1 | frontend/src/tokens.css:538
#c5221f | count:1 | frontend/src/index.css:185
#c6f6d5 | count:1 | frontend/src/index.css:49
#cbd5e1 | count:1 | frontend/src/index.css:212
#cccccc | count:1 | frontend/src/index.css:143
#cdb6fb | count:1 | frontend/src/tokens.css:535
#d6dde8 | count:1 | frontend/src/index.css:142
#d8b4fe | count:1 | frontend/src/index.css:296
#d93025 | count:1 | frontend/src/features/schedule/calendars.config.ts:47
#dadce0 | count:1 | frontend/src/index.css:181
#dbeafe | count:1 | frontend/src/index.css:149
#dc2626 | count:1 | frontend/src/index.css:292
#dde0e4 | count:1 | frontend/src/tokens.css:303
#e0a35a | count:1 | frontend/src/tokens.css:536
#e0f1ef | count:1 | frontend/src/tokens.css:380
#e3e8f0 | count:1 | frontend/src/index.css:141
#e4e6eb | count:1 | frontend/src/index.css:121
#e6f3e8 | count:1 | frontend/src/tokens.css:377
#e7eefc | count:1 | frontend/src/tokens.css:376
#e7f6f0 | count:1 | frontend/src/tokens.css:305
#e9d8fd | count:1 | frontend/src/index.css:117
#e9edf7 | count:1 | frontend/src/tokens.css:375
#eab308 | count:1 | frontend/src/pages/roles/RolesPage.tsx:78
#ec4899 | count:1 | frontend/src/pages/roles/RolesPage.tsx:86
#edf2f7 | count:1 | frontend/src/index.css:91
#eeeeee | count:1 | frontend/src/index.css:144
#eeeeff | count:1 | frontend/src/index.css:146
#eef1f4 | count:1 | frontend/src/tokens.css:381
#ef4444 | count:1 | frontend/src/pages/roles/RolesPage.tsx:76
#efe8fb | count:1 | frontend/src/tokens.css:378
#f1c48e | count:1 | frontend/src/tokens.css:536
#f1f4f7 | count:1 | frontend/src/index.css:30
#f1f5f9 | count:1 | frontend/src/index.css:211
#f29900 | count:1 | frontend/src/features/schedule/calendars.config.ts:55
#f2f3f5 | count:1 | frontend/src/index.css:122
#f3e8ff | count:1 | frontend/src/features/schedule/calendars.config.ts:32
#f5f3ff | count:1 | frontend/src/features/schedule/calendars.config.ts:72
#f5f7fa | count:1 | frontend/src/index.css:9
#f7f7f7 | count:1 | frontend/src/index.css:138
#f7fafc | count:1 | frontend/src/index.css:11
#f97316 | count:1 | frontend/src/pages/roles/RolesPage.tsx:77
#fafbfc | count:1 | frontend/src/tokens.css:302
#fb923c | count:1 | frontend/src/index.css:277
#fbeede | count:1 | frontend/src/tokens.css:379
#fdecea | count:1 | frontend/src/index.css:57
#fecaca | count:1 | frontend/src/index.css:228
#fed7d7 | count:1 | frontend/src/index.css:45
#fef2f2 | count:1 | frontend/src/index.css:153
#fef3c7 | count:1 | frontend/src/features/schedule/calendars.config.ts:56
#fefcbf | count:1 | frontend/src/index.css:47
#fff4e5 | count:1 | frontend/src/index.css:55
#fffbeb | count:1 | frontend/src/index.css:155
rgb(10,120,190) | count:1 | frontend/src/pages/inbox/InboxPage.css:256
rgb(15, 30, 45) | count:1 | frontend/src/index.css:358
rgb(20, 40, 30) | count:1 | frontend/src/index.css:355
rgb(225,237,247) | count:1 | frontend/src/pages/inbox/InboxPage.css:256
rgb(229, 240, 250) | count:1 | frontend/src/index.css:169
rgb(234, 248, 239) | count:1 | frontend/src/index.css:166
rgb(243, 237, 245) | count:1 | frontend/src/index.css:169
rgb(25, 20, 35) | count:1 | frontend/src/index.css:358
rgb(28,43,51) | count:1 | frontend/src/pages/inbox/InboxPage.css:241
rgba(0, 0, 0, 0.04) | count:1 | frontend/src/index.css:65
rgba(0, 0, 0, 0.15) | count:1 | frontend/src/index.css:67
rgba(0, 0, 0, 0.6) | count:1 | frontend/src/index.css:252
rgba(0,0,0,0.05) | count:1 | frontend/src/pages/inbox/InboxPage.css:291
rgba(148, 163, 184, 0.4) | count:1 | frontend/src/index.css:262
rgba(183, 121, 31, 0.06) | count:1 | frontend/src/index.css:77
rgba(20, 40, 30, 0) | count:1 | frontend/src/index.css:355
rgba(203, 210, 217, 0.6) | count:1 | frontend/src/index.css:83
rgba(203,210,217,0.6) | count:1 | frontend/src/pages/inbox/InboxPage.css:433
rgba(229, 62, 62, 0.06) | count:1 | frontend/src/index.css:75
rgba(229, 62, 62, 0.12) | count:1 | frontend/src/index.css:255
rgba(234, 248, 239, 0) | count:1 | frontend/src/index.css:166
rgba(241, 245, 249, 0.94) | count:1 | frontend/src/index.css:361
rgba(253, 230, 138, 0.10) | count:1 | frontend/src/index.css:257
rgba(255, 255, 255, 0.06) | count:1 | frontend/src/index.css:260
rgba(26, 32, 44, 0.92) | count:1 | frontend/src/index.css:172
rgba(30, 58, 138, 0.06) | count:1 | frontend/src/index.css:76
rgba(30, 58, 138, 0.18) | count:1 | frontend/src/index.css:88
rgba(37, 99, 235, .045) | count:1 | frontend/src/tokens.css:353
rgba(72, 187, 120, 0.05) | count:1 | frontend/src/index.css:78
rgba(74, 222, 128, 0.10) | count:1 | frontend/src/index.css:258
rgba(91, 141, 217, .10) | count:1 | frontend/src/tokens.css:541
rgba(91, 141, 217, 0.12) | count:1 | frontend/src/index.css:256
rgba(91, 141, 217, 0.2) | count:1 | frontend/src/index.css:250
rgba(91, 141, 217, 0.25) | count:1 | frontend/src/index.css:267
```

## 4. ルールの所在

```text
ADR-067 (Design Token Enforcement):
  - docs/adr/ADR-067-design-token-enforcement.md:1
  - docs/adr/ADR-067-design-token-enforcement.md:29
  - docs/adr/ADR-067-design-token-enforcement.md:99
  - docs/adr/ADR-067-design-token-enforcement.md:102
  - docs/adr/ADR-067-design-token-enforcement.md:122
  - docs/adr/ADR-067-design-token-enforcement.md:135
  - docs/adr/ADR-067-design-token-enforcement.md:146
ADR-073 (Unused token audit):
  - docs/adr/ADR-073-design-system-kgi-rubric.md:24
  - docs/adr/ADR-073-design-system-kgi-rubric.md:63
FEATURE-INDEX.md:
  - docs/adr/FEATURE-INDEX.md:1-8
  - docs/adr/FEATURE-INDEX.md:33-41
  - docs/adr/FEATURE-INDEX.md:52-58
ADR-067 / 073 以外の color-token 専用 ADR は、今回の grep 範囲では追加で見つからなかった。
```

## 5. 維持の仕組み

```text
frontend/package.json:15-16
frontend/package.json:19
frontend/package.json:32
frontend/package.json:43
frontend/package.json:54-63
frontend/.husky/pre-commit:34-58
frontend/scripts/check-dark-parity.js:3-11
frontend/scripts/.github/workflows/design-token-guard.yml:3-9
frontend/scripts/check-css-hardcoded-values.js:3-12
frontend/scripts/check-unused-tokens.js:3-9
```

### audit:unused-tokens 実測

```text
> salesanchor-frontend@1.0.0 audit:unused-tokens
> node scripts/check-unused-tokens.js

⚠️  audit:unused-tokens — 31 件の未使用トークンが見つかりました:

   --max-width-modal-sm                          (src/tokens.css)
   --inbox-collapsed-panel-w                     (src/tokens.css)
   --karte-ok-bg                                 (src/tokens.css)
   --topnav-email-max-w                          (src/tokens.css)
   --schedule-cell-icon-size                     (src/tokens.css)
   --schedule-min-h                              (src/tokens.css)
   --schedule-mini-col-min-w                     (src/tokens.css)
   --schedule-slot-h                             (src/tokens.css)
   --schedule-nav-btn-size                       (src/tokens.css)
   --schedule-row-height-compact                 (src/tokens.css)
   --cal-personal                                (src/tokens.css)
   --cal-meeting                                 (src/tokens.css)
   --cal-purchase                                (src/tokens.css)
   --cal-shipping                                (src/tokens.css)
   --cal-billing                                 (src/tokens.css)
   --cal-release                                 (src/tokens.css)
   --cal-holiday                                 (src/tokens.css)
   --col-width-wide                              (src/tokens.css)
   --modal-commission-w                          (src/tokens.css)
   --modal-detail-max-w                          (src/tokens.css)
   --color-blue-100                              (src/index.css)
   --color-blue-700                              (src/index.css)
   --color-gray-100                              (src/index.css)
   --color-gray-600                              (src/index.css)
   --color-red-50                                (src/index.css)
   --color-red-700                               (src/index.css)
   --color-amber-50                              (src/index.css)
   --color-amber-800                             (src/index.css)
   --color-border-subtle                         (src/index.css)
   --calendar-today-text                         (src/index.css)
   --calendar-today-cell-bg                      (src/index.css)

対処: 不要なトークンは削除、または使用箇所がある場合は検索パターンを確認してください。
     意図的に未使用の場合は EXEMPT_PREFIXES に prefix を追加してください。
```

## 6. 設計図との対照

- 比較対象: `docs/specs/design-system/design.md` §5.3.1〜§5.3.3
- 判定方針: design.md の exact name は frontend/src に無いので、現在の実装ではすべて `不足`。
- 近傍の現行実装は、カレンダー系が `frontend/src/features/schedule/calendars.config.ts` の direct hex、ロール色が `frontend/src/pages/roles/RolesPage.tsx` の direct hex 配列。

```text
01 | --calendar-meeting-text | --color-blue-800 | light:#174ea6 | dark:#93c5fd | impl:frontend/src/features/schedule/calendars.config.ts:25 | 不足（design.md 5.3.3 の exact name は frontend/src に未定義）
02 | --calendar-personal-color | --color-purple-600 | light:#9333ea | dark:#c084fc | impl:frontend/src/features/schedule/calendars.config.ts:31 | 不足（design.md 5.3.3 の exact name は frontend/src に未定義）
03 | --calendar-personal-tint | --color-purple-50 | light:#f3e8ff | dark:#2d0e4e | impl:frontend/src/features/schedule/calendars.config.ts:32 | 不足（design.md 5.3.3 の exact name は frontend/src に未定義）
04 | --calendar-personal-text | --color-purple-800 | light:#6b21a8 | dark:#d8b4fe | impl:frontend/src/features/schedule/calendars.config.ts:33 | 不足（design.md 5.3.3 の exact name は frontend/src に未定義）
05 | --calendar-procurement-color | --color-green-700 | light:#0f9d58 | dark:#4ade80 | impl:frontend/src/features/schedule/calendars.config.ts:39 | 不足（design.md 5.3.3 の exact name は frontend/src に未定義）
06 | --calendar-procurement-text | --color-green-800 | light:#166534 | dark:#86efac | impl:frontend/src/features/schedule/calendars.config.ts:41 | 不足（design.md 5.3.3 の exact name は frontend/src に未定義）
07 | --calendar-shipping-color | --color-red-600 | light:#d93025 | dark:#f28b82 | impl:frontend/src/features/schedule/calendars.config.ts:47 | 不足（design.md 5.3.3 の exact name は frontend/src に未定義）
08 | --calendar-billing-color | --color-amber-500 | light:#f29900 | dark:#f8d66d | impl:frontend/src/features/schedule/calendars.config.ts:55 | 不足（design.md 5.3.3 の exact name は frontend/src に未定義）
09 | --calendar-billing-tint | --color-amber-100 | light:#fef3c7 | dark:#362a08 | impl:frontend/src/features/schedule/calendars.config.ts:56 | 不足（design.md 5.3.3 の exact name は frontend/src に未定義）
10 | --calendar-release-color | --color-slate-600 | light:#5f6368 | dark:#94a3b8 | impl:frontend/src/features/schedule/calendars.config.ts:63 | 不足（design.md 5.3.3 の exact name は frontend/src に未定義）
11 | --calendar-holiday-color | --color-violet-700 | light:#7e22ce | dark:#b771f4 | impl:frontend/src/features/schedule/calendars.config.ts:71 | 不足（design.md 5.3.3 の exact name は frontend/src に未定義）
12 | --calendar-holiday-tint | --color-violet-50 | light:#f5f3ff | dark:#1e1b4b | impl:frontend/src/features/schedule/calendars.config.ts:72 | 不足（design.md 5.3.3 の exact name は frontend/src に未定義）
13 | --calendar-holiday-text | --color-violet-800 | light:#6b21a8 | dark:#e9d5ff | impl:frontend/src/features/schedule/calendars.config.ts:73 | 不足（design.md 5.3.3 の exact name は frontend/src に未定義）
14 | --role-palette-1 | --color-red-500 | light:#ef4444 | dark:#fca5a5 | impl:frontend/src/pages/roles/RolesPage.tsx:76 | 不足（design.md 5.3.3 の exact name は frontend/src に未定義）
15 | --role-palette-2 | --color-orange-500 | light:#f97316 | dark:#fdba74 | impl:frontend/src/pages/roles/RolesPage.tsx:77 | 不足（design.md 5.3.3 の exact name は frontend/src に未定義）
16 | --role-palette-3 | --color-yellow-500 | light:#eab308 | dark:#fde68a | impl:frontend/src/pages/roles/RolesPage.tsx:78 | 不足（design.md 5.3.3 の exact name は frontend/src に未定義）
17 | --role-palette-4 | --color-lime-500 | light:#84cc16 | dark:#bef264 | impl:frontend/src/pages/roles/RolesPage.tsx:79 | 不足（design.md 5.3.3 の exact name は frontend/src に未定義）
18 | --role-palette-5 | --color-green-500 | light:#22c55e | dark:#86efac | impl:frontend/src/pages/roles/RolesPage.tsx:80 | 不足（design.md 5.3.3 の exact name は frontend/src に未定義）
19 | --role-palette-6 | --color-teal-500 | light:#14b8a6 | dark:#5eead4 | impl:frontend/src/pages/roles/RolesPage.tsx:81 | 不足（design.md 5.3.3 の exact name は frontend/src に未定義）
20 | --role-palette-7 | --color-cyan-500 | light:#06b6d4 | dark:#67e8f9 | impl:frontend/src/pages/roles/RolesPage.tsx:82 | 不足（design.md 5.3.3 の exact name は frontend/src に未定義）
21 | --role-palette-8 | --color-blue-500 | light:#3b82f6 | dark:#b1cdfb | impl:frontend/src/pages/roles/RolesPage.tsx:83 | 不足（design.md 5.3.3 の exact name は frontend/src に未定義）
22 | --role-palette-9 | --color-indigo-500 | light:#6366f1 | dark:#bcbdfb | impl:frontend/src/pages/roles/RolesPage.tsx:84 | 不足（design.md 5.3.3 の exact name は frontend/src に未定義）
23 | --role-palette-10 | --color-purple-500 | light:#a855f7 | dark:#d8b4fe | impl:frontend/src/pages/roles/RolesPage.tsx:85 | 不足（design.md 5.3.3 の exact name は frontend/src に未定義）
24 | --role-palette-11 | --color-pink-500 | light:#ec4899 | dark:#f9a8d4 | impl:frontend/src/pages/roles/RolesPage.tsx:86 | 不足（design.md 5.3.3 の exact name は frontend/src に未定義）
25 | --role-palette-12 | --color-slate-500 | light:#64748b | dark:#94a3b8 | impl:frontend/src/pages/roles/RolesPage.tsx:87 | 不足（design.md 5.3.3 の exact name は frontend/src に未定義）
26 | --role-palette-fallback | --color-gray-500 | light:#6c757d | dark:#a8b3c2 | impl:frontend/src/pages/roles/RolesPage.tsx:262 | 不足（design.md 5.3.3 の exact name は frontend/src に未定義）
```

## 7. ノイズと境界

- 今回の scan 範囲は `frontend/src` のみ。`node_modules`、`dist`、`coverage`、Storybook build 成果物、`docs/**` は見ない。
- `.github/workflows/design-token-guard.yml` は `index.css` / `tokens.css` を除外しているため、直値スキャンの機械判定対象は主に component/page CSS。
- `frontend/scripts/check-unused-tokens.js` は `tokens.css` と `index.css` のみを対象にするため、今回の recon で数えた `color-bearing custom prop` の `34` 孤児とは一致しない。
- `--cal-*` 系は現行 `tokens.css` にある legacy color token で、design.md §5.3.3 の exact name ではない。
- `PR番号`、`TBD`、テストダミー値のような非色の `#` 表記は、今回の `frontend/src` 実測では色リテラルとしての分類対象に入っていない。

---

## 補足

- `docs/specs/design-system/design.md` §5.3.3 は 26 件の exact name を定義しているが、現行 `frontend/src` にはその exact name はまだ実装されていない。
- `frontend/src` の現行 schedule 実装は `frontend/src/features/schedule/calendars.config.ts` の direct hex と `index.css` の Google Calendar 系 tokens を使っている。

## 8. 追加調査（TS/TSX直書き色の完全棚卸し）

- 鮮度: `git fetch origin` → `git rev-parse origin/main` = `9c7f004a5ada0f1ec5b14818d0a367c0051f0b2d`
- 作業ツリー: `git status --short --branch` = `## main...origin/main [behind 40]` / `M .claude-pipeline/active-work.md` / `?? docs/handoff/color-tokens-ssot/`
- 対象ファイル数: `frontend/src` の `.ts` / `.tsx` は `291` 件

### 8-1. 抽出結果

- `hex` / `rgb()` / `rgba()` / `hsl()` / `hsla()` の機械抽出は、TS/TSX では `36` 件の実色を検出した。
- `rgb()` / `rgba()` / `hsl()` / `hsla()` の実ヒットは `0` 件だった。
- `#` 由来の誤検出は `18` 件あった。理由はすべて `PR #...` を含むコメント行で、色リテラルではないため除外した。
- テスト用ダミー値として追加で除外したものは `0` 件だった。

#### 8-1-a. 実色 36 件一覧

```text
frontend/src/features/schedule/calendars.config.ts:23 - colorVar: "#1a73e8", - schedule meeting の色（light 側）
frontend/src/features/schedule/calendars.config.ts:24 - tintVar: "#e8f0fe", - schedule meeting の淡色（light 側）
frontend/src/features/schedule/calendars.config.ts:25 - textVar: "#174ea6", - schedule meeting の文字色（light 側）
frontend/src/features/schedule/calendars.config.ts:31 - colorVar: "#9333ea", - schedule personal の色（light 側）
frontend/src/features/schedule/calendars.config.ts:32 - tintVar: "#f3e8ff", - schedule personal の淡色（light 側）
frontend/src/features/schedule/calendars.config.ts:33 - textVar: "#6b21a8", - schedule personal の文字色（light 側）
frontend/src/features/schedule/calendars.config.ts:39 - colorVar: "#0f9d58", - schedule procurement の色（light 側）
frontend/src/features/schedule/calendars.config.ts:40 - tintVar: "#e6f4ea", - schedule procurement の淡色（light 側）
frontend/src/features/schedule/calendars.config.ts:41 - textVar: "#166534", - schedule procurement の文字色（light 側）
frontend/src/features/schedule/calendars.config.ts:47 - colorVar: "#d93025", - schedule shipping の色（light 側）
frontend/src/features/schedule/calendars.config.ts:48 - tintVar: "#fce8e6", - schedule shipping の淡色（light 側）
frontend/src/features/schedule/calendars.config.ts:49 - textVar: "#b91c1c", - schedule shipping の文字色（light 側）
frontend/src/features/schedule/calendars.config.ts:55 - colorVar: "#f29900", - schedule billing の色（light 側）
frontend/src/features/schedule/calendars.config.ts:56 - tintVar: "#fef3c7", - schedule billing の淡色（light 側）
frontend/src/features/schedule/calendars.config.ts:57 - textVar: "#92400e", - schedule billing の文字色（light 側）
frontend/src/features/schedule/calendars.config.ts:63 - colorVar: "#5f6368", - schedule release の色（light 側）
frontend/src/features/schedule/calendars.config.ts:64 - tintVar: "#f3f4f6", - schedule release の淡色（light 側）
frontend/src/features/schedule/calendars.config.ts:65 - textVar: "#374151", - schedule release の文字色（light 側）
frontend/src/features/schedule/calendars.config.ts:71 - colorVar: "#7e22ce", - schedule holiday の色（light 側）
frontend/src/features/schedule/calendars.config.ts:72 - tintVar: "#f5f3ff", - schedule holiday の淡色（light 側）
frontend/src/features/schedule/calendars.config.ts:73 - textVar: "#6b21a8", - schedule holiday の文字色（light 側）
frontend/src/pages/dashboard/DashboardPage.tsx:175 - const accent = style.getPropertyValue("--accent").trim() || "#1e3a8a"; - accent のフォールバック
frontend/src/pages/roles/RolesPage.tsx:76 - "#ef4444", // 赤 - role palette 1
frontend/src/pages/roles/RolesPage.tsx:77 - "#f97316", // オレンジ - role palette 2
frontend/src/pages/roles/RolesPage.tsx:78 - "#eab308", // 黄 - role palette 3
frontend/src/pages/roles/RolesPage.tsx:79 - "#84cc16", // ライム - role palette 4
frontend/src/pages/roles/RolesPage.tsx:80 - "#22c55e", // 緑 - role palette 5
frontend/src/pages/roles/RolesPage.tsx:81 - "#14b8a6", // ティール - role palette 6
frontend/src/pages/roles/RolesPage.tsx:82 - "#06b6d4", // シアン - role palette 7
frontend/src/pages/roles/RolesPage.tsx:83 - "#3b82f6", // 青 - role palette 8
frontend/src/pages/roles/RolesPage.tsx:84 - "#6366f1", // インディゴ - role palette 9
frontend/src/pages/roles/RolesPage.tsx:85 - "#a855f7", // 紫 - role palette 10
frontend/src/pages/roles/RolesPage.tsx:86 - "#ec4899", // ピンク - role palette 11
frontend/src/pages/roles/RolesPage.tsx:87 - "#64748b", // スレート - role palette 12
frontend/src/pages/roles/RolesPage.tsx:262 - color: r.color || "#6c757d", - role color のフォールバック
frontend/src/pages/schedule/schedule-owner.ts:34 - export const DEFAULT_OWNER_COLOR = "#1a73e8"; - calendar owner のデフォルト色
```

#### 8-1-b. 除外した 18 件

- 除外理由: `PR #166` / `PR #147` / `PR #145` / `PR #152` / `PR #164` などのコメント内表記が、`#[0-9a-fA-F]{3,8}` 形の機械抽出に偶然一致したため。
- 除外件数の内訳: `frontend/src/contexts/UiPrefsContext.tsx` 2 件、`frontend/src/pages/deals/DealsPage.tsx` 2 件、`frontend/src/App.tsx` 1 件、`frontend/src/pages/company-detail/CompanyDetailPage.tsx` 1 件、`frontend/src/pages/company-detail/CompanyBasicTab.tsx` 1 件、`frontend/src/pages/companies/CompaniesPage.tsx` 1 件、`frontend/src/components/MergeCompanyModal.tsx` 4 件、`frontend/src/components/CompanyContactSelector.tsx` 6 件。
- テスト用ダミー値・非色文字列の追加ヒットはなかった。

### 8-2. 既存の守り手（チェックスクリプト）の対象範囲

- `frontend/scripts/.github/workflows/design-token-guard.yml:19-20, 28-35, 41-43` は `frontend/src` 配下の `.css` のみを走査し、`index.css` / `tokens.css` を除外する。TS/TSX は対象外。
- `frontend/scripts/check-css-hardcoded-values.js:22-23, 77-85, 90-91` は `frontend/src` 配下の `.css` のみを走査し、`index.css` / `tokens.css` を除外する。TS/TSX は対象外。
- `frontend/scripts/check-unused-tokens.js:21-27, 60-67, 84-94` は `tokens.css` / `index.css` の定義を `src/` の `.css` / `.tsx` / `.ts` で参照追跡する。TS/TSX の `var(--...)` は見られるが、直書き色は検知しない。
- `frontend/scripts/check-dark-parity.js:19-33, 40-48` は `frontend/src/index.css` のみを走査する。TS/TSX は対象外。
- 上記 4 本のうち、TS/TSX の直書き色を検知できるものは `0` 本。

### 8-3. 371件との関係

- 前回 `371` 件として残っている direct color literal 集計は、`frontend/src` 全体を対象にした結果で、TS/TSX 側の今回 `36` 件はその内訳に含まれる。
- したがって、前回 `371` 件と今回 `36` 件は、ファイル種別で完全分離した別集合ではない。
- ただし、今回の TS/TSX 棚卸しでは `.ts` / `.tsx` のみを対象にしており、`.css` / `.scss` は数えていない。

### 8-4. 使用状況の確認

- `frontend/src/pages/schedule/SchedulePageImpl.tsx:15, 292, 644, 714, 797` で `frontend/src/features/schedule/calendars.config.ts` の `CALENDARS` / `CALENDAR_MAP` / `cssVar()` を参照している。
- `frontend/src/pages/schedule/schedule-owner.ts:34, 43` で `DEFAULT_OWNER_COLOR` を定義・使用している。
- `frontend/src/pages/roles/RolesPage.tsx:76-87, 262, 356, 561` で `COLOR_PALETTE` と `r.color` フォールバックを使っている。
- `frontend/src/pages/dashboard/DashboardPage.tsx:175` で `"#1e3a8a"` を `--accent` のフォールバックとして使っている。
- `frontend/src/features/schedule/calendars.config.ts` と `frontend/src/pages/roles/RolesPage.tsx` 以外の TS/TSX 直書き色については、今回の棚卸しでは全件の依存追跡までは行っていない。
