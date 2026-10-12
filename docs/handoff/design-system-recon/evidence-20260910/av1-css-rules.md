# AV-1 page select class CSS

基準 SHA: 55d99a97e441b4c0604f2b8f42418d2a7bc8ffab / TypeScript 5.9.3

### .right-panel-field
- frontend/src/pages/inbox/InboxPage.css:1195
  `.right-panel-field` { width: 100%; box-sizing: border-box; background: var(--karte-field-bg); border: 0.5px solid var(--karte-field-bd); /* 見本 .fbox: tokens にて定義 */ border-radius: var(--radius-md); padding: var(--karte-field-py) var(--karte-field-px); /* 見本 .fbox: 7px 9px, radius 6px */ font-size: var(--font-sm); color: var(--text-primary); font-family: inherit; transition: border-color var(--transition-micro); }
- frontend/src/pages/inbox/InboxPage.css:1204
  `.right-panel-field::placeholder` { color: var(--text-muted); }
- frontend/src/pages/inbox/InboxPage.css:1207
  `.right-panel-field:focus` { outline: none; border-color: var(--accent); }

### .field
- 該当ルールなし（このsnapshotのCSSに無い）

### .field-h-md
- frontend/src/components/field-size.css:8
  `.field-h-md` { min-height: var(--field-h-md, 36px); box-sizing: border-box; }

### .field-w-sm
- frontend/src/components/field-size.css:11
  `.field-w-sm` { width: var(--field-w-sm, 160px); }
- frontend/src/components/field-size.css:16
  `.content-toolbar .field-w-sm, .content-toolbar .field-w-md, .content-toolbar .field-w-lg` { margin-bottom: 0; }

### .schedule-input
- frontend/src/pages/schedule.css:813
  `.schedule-input, .schedule-textarea` { width: 100%; border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--bg-surface); color: var(--text-primary); font-size: var(--font-sm); }
- frontend/src/pages/schedule.css:823
  `.schedule-input` { min-height: var(--comp-input-height-sm); padding: 0 var(--space-3); }
- frontend/src/pages/schedule.css:833
  `.schedule-input:focus, .schedule-textarea:focus` { outline: none; border-color: var(--accent); box-shadow: var(--focus-ring-shadow); }

### .page-header-select
- frontend/src/components.css:583
  `.page-header-select` { appearance: none; -webkit-appearance: none; box-sizing: border-box; /* border込みで 36px: content 34px + border 1px×2 */ height: var(--size-icon-btn); /* btn-ghost / icon-btn と高さを統一 (36px) */ padding: var(--space-1) var(--space-5) var(--space-1) var(--space-3); border: 1px solid var(--border); border-radius: var(--radius-pill); background: var(--bg-surface) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%23888' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E") no-repeat right var(--space-2) center; color: var(--text-primary); font-size: var(--font-sm); cursor: pointer; transition: border-color var(--transition-fast), background-color var(--transition-fast); white-space: nowrap; }
- frontend/src/components.css:600
  `.page-header-select:hover` { background-color: var(--bg-hover); border-color: var(--border-strong); }
- frontend/src/components.css:604
  `.page-header-select:focus` { outline: none; border-color: var(--accent); box-shadow: var(--focus-ring-shadow); }

### .inbox-platform-select
- frontend/src/pages/inbox/InboxPage.css:68
  `.inbox-platform-select` { margin-left: auto; flex-shrink: 0; height: var(--height-tab-item); padding: 0 var(--space-2); border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--bg-surface); color: var(--text-secondary); font-size: var(--font-xs); font-family: inherit; cursor: pointer; }
- frontend/src/pages/inbox/InboxPage.css:82
  `.inbox-platform-select:focus` { outline: none; border-color: var(--accent); color: var(--text-primary); }

### .account-settings-lang-select
- frontend/src/pages/account-settings/account-settings.css:151
  `.account-settings-lang-select` { padding: var(--space-1) var(--space-3); border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--bg-surface); color: var(--text-primary); font-size: var(--font-sm); cursor: pointer; min-width: var(--size-lang-select-min); }
- frontend/src/pages/account-settings/account-settings.css:163
  `.account-settings-lang-select:focus` { outline: none; border-color: var(--accent); box-shadow: var(--focus-ring-shadow); }

### .conv-logs-filter-select
- 該当ルールなし（このsnapshotのCSSに無い）

### .search-input
- 該当ルールなし（このsnapshotのCSSに無い）

### .gs-select
- frontend/src/pages/goal-setting/GoalSettingPage.css:555
  `.gs-select` { flex: 1; padding: var(--space-2) var(--space-3); border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--bg-surface); color: var(--text-primary); font-size: var(--font-sm); cursor: pointer; }

### .inbox-page-filter-select
- frontend/src/pages/inbox/InboxPage.css:412
  `.inbox-page-filter-select` { width: 100%; padding: var(--space-1) var(--space-2); font-size: var(--font-xs); border-radius: var(--radius-xl); border: 1px solid var(--border); background: var(--bg-surface); color: var(--text-primary); font-family: inherit; box-sizing: border-box; }

### .inbox-settings-select
- frontend/src/pages/inbox/InboxPage.css:1440
  `.inbox-settings-select` { background: var(--bg-primary); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: var(--space-1) var(--space-2); font-size: var(--font-sm); color: var(--text-primary); cursor: pointer; }

### .manual-record-select
- 該当ルールなし（このsnapshotのCSSに無い）
