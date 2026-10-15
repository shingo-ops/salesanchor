# AY-3b recon（切替スイッチ8か所を共通部品 Toggle へ）

基準: origin/main 0fa5f5caa（設計の基準 3d41e0c86 と対象範囲の差なし。`git diff 3d41e0c86 0fa5f5caa` で components.css・schedule.css・account-settings・inbox の CSS に差が無いことを確認）。生出力: /tmp/CC報告ファイル/ssot-toggle/（summary.md ほか）、/tmp/CC報告ファイル/ssot-ay3b/。設計: docs/handoff/ay3b-toggle/design.md（正本は /tmp/CC報告ファイル/ssot-toggle/ay3b-design.md r2・APPROVE）。

## 既存 ADR の検索
- 継承元は ADR-144（UI 部品は金型へ）、ADR-067（デザイントークン）、ADR-027（i18n。本便は新キーなし）。ADR-069（トグルスイッチ: frontend/src/components.css の旧コメント）は旧規則の出典。
- docs/specs/design-system/design.md の §AY-2z・§AY-3a が前例（旧規則を同便で撤去し前後実測）。新規金型の登録自体は 2026-10-02 の PO 回答で許可済み（docs/specs/design-system/design.md:1953）。2026-10-15 PO「Y」で 8 か所を 1 部品に統一、幅は --size-toggle-w（44px）。

## 旧規則（変更前、origin/main）
- frontend/src/components.css:710-726 `.toggle-switch`（A: 40×22・つまみ16・移動18）。
- frontend/src/pages/account-settings/account-settings.css:101-149 `.toggle-switch`・`.toggle-slider`（B: 全宣言トークン、focus-visible あり）。
- frontend/src/pages/inbox/InboxPage.css:1675-1690 `.inbox-toggle`（使用 0）。
- frontend/src/pages/schedule.css:1201-1223 `.schedule-page`・`.schedule-settings` 配下の上書き（42×24）。
- JSX 8 か所: frontend/src/pages/account-settings/PreferencesSection.tsx:24、frontend/src/pages/inbox/InboxSettingsModal.tsx:29・:52・:65・:83、frontend/src/pages/schedule/SchedulePageImpl.tsx:307、frontend/src/pages/schedule/ScheduleSettingsPage.tsx:165・:222。
- 本番 CSS（/tmp/CC報告ファイル/ssot-ay3a/prod/idx.css = index-DDKExstm.css）の順は schedule 上書き → account-settings B → components A。origin/main の vite build CSS（index-BwIsH5wu.css）は本番 CSS と同じ実測結果（B1 該当なし）。

## 確認した事実（m9 を含む）
- class の使用: `toggle-switch|toggle-slider|inbox-toggle` は frontend/src の上記 8 JSX と CSS 4 ファイルだけ（grep 生出力 /tmp/CC報告ファイル/ssot-ay3b/ の作業ログ、B3 該当なし）。
- tests-e2e の参照 0: `grep -rn "toggle-switch\|toggle-slider\|inbox-toggle" frontend/tests-e2e` は 0 件。frontend/CLAUDE.md の E2E 更新ルール（画面の class・文言を変えたら tests-e2e を更新）の対象外。
- ui-allow が不要な根拠: scripts/check-ui-governance.js:7-11 の検出対象は生 select・生 input（text 系）・自作タブ・色直値であり、checkbox は検出対象外。Toggle は金型そのものなので ui-allow コメントは付けない。check-ui-governance への checkbox 検出追加は本便では行わない（別判断）。
- トークン: `--toggle-width`・`--toggle-thumb-offset`・`--toggle-translate` は撤去後に参照 0（AY-2v と同じ範囲の grep、/tmp/CC報告ファイル/ssot-ay3b/token-grep2.txt）→ tokens.css から削除（B9 該当なし）。`--toggle-height` は docs/specs/design-system/visual-language/design.md:136 などで名指しされるため残す。`--toggle-thumb-size` は frontend/src/pages/inbox/InboxPage.css:1478 が使うため残す。audit:unused-tokens の未使用件数は 16 → 13（3 件削除。--toggle-height は未使用のまま残る）。
- onChange は 8 か所すべて `e.target.checked` のみ使用（B2 該当なし）。InboxSettingsModal の通知許可は `await Notification.requestPermission()` の後に `next` を使う（取り出した値は変わらず、DOM の checked と同じ）。
- 名前の無かった 5 か所（InboxSettingsModal 4・SchedulePageImpl 1）には隣の文言と同じ既存キーを aria-label に付ける。新キーなし。
- 試験 (b)（InboxSettingsModal の描画）は i18n（en 初期化）以外の Provider が不要だったため実施。Modal は Portal で document.body に描画する。

## 実測の事実
- 数値は docs/handoff/design-system-recon/evidence-20260910/ay3b-acceptance.md と ay3b-compare.txt。
