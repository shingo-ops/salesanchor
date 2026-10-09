# 非 text input に当たりうる CSS 規則（詳細度 (0,1,1)〜(0,3,1)）

走査: frontend/src の CSS 68 ファイル、規則 2144、セレクタ 2302。主語が input、または type 属性だけ、または * / 疑似クラスだけ（クラス・id を持たない input に当たりうる）規則のうち、候補全体 34 件。
範囲の根拠: 通常状態は旧 .form-group input (0,1,1) → 新 .form-group input[type] (0,2,1)、:focus は旧 (0,2,1) → 新 (0,3,1)。この間にある規則は勝敗が変わりうる。

対象範囲内: 23 件

| file:line | selector | 詳細度 | at-rule | 宣言 |
|---|---|---|---|---|
| frontend/src/components.css:56 | `.search-bar input` | (0,1,1) | - | padding: var(--space-2) var(--space-3); border: 1px solid var(--border); border-radius: var(--radius-sm); font-size: var(--font-base); min-width: var(--input-select-min-w); background: var(--bg-surface); color: var(--text-primary) |
| frontend/src/components.css:727 | `.toggle-switch input` | (0,1,1) | - | opacity: 0; width: 0; height: 0 |
| frontend/src/features/tcg-analysis-review/source-raw-pane.css:48 | `.source-search input` | (0,1,1) | - | min-width: 0 |
| frontend/src/features/tcg-analysis-review/supplier-detail-view.css:244 | `.pmd-field input` | (0,1,1) | - | border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--bg-surface); padding: var(--space-2); font: inherit; width: 100%; box-sizing: border-box |
| frontend/src/pages/account-settings/account-settings.css:111 | `.toggle-switch input` | (0,1,1) | - | opacity: 0; width: 0; height: 0; position: absolute |
| frontend/src/pages/inbox/InboxPage.css:1410 | `.inbox-toggle input` | (0,1,1) | - | opacity: 0; width: 0; height: 0 |
| frontend/src/topbar.css:44 | `.topbar-search input` | (0,1,1) | - | flex: 1; border: none; background: transparent; padding: var(--space-10px) 0; font-size: var(--font-base); color: var(--text-primary); outline: none |
| frontend/src/topbar.css:54 | `.topbar-search input::placeholder` | (0,1,2) | - | color: var(--text-muted) |
| frontend/src/components.css:19 | `.form-group input[type="checkbox"]` | (0,2,1) | - | width: 100%; padding: var(--space-2) var(--space-3); border: 1px solid var(--border); border-radius: var(--radius-sm); font-size: var(--font-base); color: var(--text-primary); background: var(--bg-surface); box-sizing: border-box |
| frontend/src/components.css:19 | `.form-group input[type="radio"]` | (0,2,1) | - | width: 100%; padding: var(--space-2) var(--space-3); border: 1px solid var(--border); border-radius: var(--radius-sm); font-size: var(--font-base); color: var(--text-primary); background: var(--bg-surface); box-sizing: border-box |
| frontend/src/components.css:19 | `.form-group input[type="range"]` | (0,2,1) | - | width: 100%; padding: var(--space-2) var(--space-3); border: 1px solid var(--border); border-radius: var(--radius-sm); font-size: var(--font-base); color: var(--text-primary); background: var(--bg-surface); box-sizing: border-box |
| frontend/src/components.css:19 | `.form-group input[type="file"]` | (0,2,1) | - | width: 100%; padding: var(--space-2) var(--space-3); border: 1px solid var(--border); border-radius: var(--radius-sm); font-size: var(--font-base); color: var(--text-primary); background: var(--bg-surface); box-sizing: border-box |
| frontend/src/pages-layout.css:340 | `.color-swatch input[type="radio"]` | (0,2,1) | - | position: absolute; inset: 0; width: 100%; height: 100%; opacity: 0; cursor: pointer |
| frontend/src/pages-layout.css:595 | `.chk-label input[type="checkbox"]` | (0,2,1) | - | margin: 0 |
| frontend/src/pages-layout.css:619 | `.permission-item input[type="checkbox"]` | (0,2,1) | - | margin-top: var(--space-1); flex-shrink: 0 |
| frontend/src/pages/inbox/InboxPage.css:1619 | `.sales-form-option input[type="checkbox"]` | (0,2,1) | - | accent-color: var(--accent); cursor: pointer |
| frontend/src/company-forms.css:113 | `.form-grid > .form-row input:focus` | (0,3,1) | - | outline: none; border-color: var(--accent); box-shadow: var(--focus-ring-shadow) |
| frontend/src/company-forms.css:163 | `.modal-content .form-row input:focus` | (0,3,1) | - | outline: none; border-color: var(--accent); box-shadow: var(--focus-ring-shadow) |
| frontend/src/company-forms.css:163 | `.modal-content-wide .form-row input:focus` | (0,3,1) | - | outline: none; border-color: var(--accent); box-shadow: var(--focus-ring-shadow) |
| frontend/src/components.css:33 | `.form-group input[type="checkbox"]:focus` | (0,3,1) | - | outline: none; border-color: var(--accent); box-shadow: var(--focus-ring-shadow) |
| frontend/src/components.css:33 | `.form-group input[type="radio"]:focus` | (0,3,1) | - | outline: none; border-color: var(--accent); box-shadow: var(--focus-ring-shadow) |
| frontend/src/components.css:33 | `.form-group input[type="range"]:focus` | (0,3,1) | - | outline: none; border-color: var(--accent); box-shadow: var(--focus-ring-shadow) |
| frontend/src/components.css:33 | `.form-group input[type="file"]:focus` | (0,3,1) | - | outline: none; border-color: var(--accent); box-shadow: var(--focus-ring-shadow) |

## 参考: 範囲外の候補（詳細度が範囲外、勝敗は絞り込み前後で変わらない）: 11 件
