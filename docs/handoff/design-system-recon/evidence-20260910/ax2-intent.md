# AX-2 意図の証跡（事実のみ。意図の判定はしない。origin/main dfcd31c05）

調べ方: ①CSS・TSX 内コメント ②`git grep -n`（docs/ *.md、ADR）③`git log -S'<語>' --reverse --no-merges`（最初に導入したコミット）と `gh api repos/shingo-ops/salesanchor/commits/<sha>/pulls`（その PR 題）④専用トークンの定義位置。
コミット本文・PR 題の中の「textarea」「入力欄」「メモ欄」の語: 下記の最初の導入コミット10件の本文には 0 行（`git log -1 --format=%B | grep`）。ただし PR #1971 の本文には「見本」「フィールド」の記述あり（後述）。

## 1. `inbox-textarea`（送信欄）— frontend/src/pages/inbox/InboxMessageThread.tsx:736
- CSS: `frontend/src/pages/inbox/InboxPage.css:633-646`（`.inbox-textarea`）、:647（`:disabled`）。`.inbox-textarea` 自体にコメントは無い。親 `.send-input-wrap` の直前 InboxPage.css:621 に `/* 入力ラップ（Meta実測: br=18px → --radius-pill=20px 吸収済み ±2px許容） */`、:649 に `/* 添付ボタン（ピル内右端・Meta と同配置） */`。
- 宣言（事実）: `border:none; padding:0; background:transparent; resize:none; outline:none; line-height:1.4; font-family:inherit; flex:1; min-width:0`。枠・背景は親 `.send-input-wrap`（InboxPage.css:~620-632、`background: var(--bg-subtle); border-radius: var(--radius-pill); padding: var(--space-2) var(--space-14px)`）が持つ。
- 専用トークン: なし（`--inbox-textarea-min-h` は使っていない。:633-646 に var(--font-base)/--text-primary/--opacity-disabled のみ）。
- 最初の導入: `67ba8522a` 2026-05-21 shingo-ops「feat: InboxPageをMeta Business Suite風UI+All/New/Existing/Archiveタブに全面再設計」→ PR #475「feat: Lead ChatをMeta Business Suite風UIに再設計」。次: `2ee9b0a44` 2026-05-22「Inbox構造をMeta準拠に改善（…送信エリア角丸カード化）」、`e31f60aa1` 2026-05-25「INBOX_STYLES CSS-in-JS を InboxPage.css に外出し（ADR-067準拠）」。
- docs: `docs/specs/design-system/design.md:895` CSSI-0209「InboxのTextareaControlはembedded/resize=none。枠0・padding0・transparent・line-height1.4を共通入力用途へ、flex1/min-width0を同nativeの配置入口へ移す。」（同 design.md:818「appearance?: standard/embedded | TextFieldControl/TextareaControlだけ。embeddedは親が枠を所有」）。`docs/handoff/app-visual-language/stage1-baseline.md`（className を列挙した計測表）。
- 注記（事実）: 上記 design.md の appearance=embedded は、出荷済み TextareaControl（components/Textarea.tsx:28-52）には存在しない（props は `size` のみ）。
- 参照するテスト: tests-e2e 4ファイル計27行（ax2-test-refs.md）。

## 2. `right-panel-field`（カルテ右パネルのメモ欄）— InboxKartePanel.tsx:484,503,537,588 / InboxProfileModal.tsx:181,191,210,265（計8 textarea）
- CSS: `InboxPage.css:1170-1181`。コメント（原文）:
  - :1173 `/* 見本 .fbox: tokens にて定義 */`
  - :1174 `/* 見本 .fbox: 7px 9px, radius 6px */`
  - :1181 `textarea.right-panel-field { resize: none; min-height: var(--inbox-textarea-min-h); } /* 見本: リサイズハンドル非表示 */`
- 見本の実体: `docs/adr/karte_reference.html:48` `.fbox{border:0.5px solid var(--bd2);background:#fafbfc;border-radius:6px;padding:7px 9px;font-size:13px;color:var(--tx);min-height:32px;line-height:1.4;}`
- 専用トークン（定義位置）: `--karte-field-py: 7px` (tokens.css:314)、`--karte-field-px: 9px` (:315)、`--karte-field-bg: #fafbfc` (:323)、`--karte-field-bd: #dde0e4` (:324)、`--inbox-textarea-min-h: 60px` (:309, コメント「カルテメモフィールド最小高」)。tokens.css:310 の見出しコメント「カルテパネル専用値（見本 karte_reference.html 準拠・4pxグリッド非準拠例外）」。
- 最初の導入: class `abfd68930` 2026-05-23「feat: 受信箱カルテ常時編集＋自動保存＋設定モーダル実装」→ PR #639「feat: 受信箱カルテ常時編集＋自動保存＋設定モーダル」。トークン `--karte-field-*` は `e6c0c9f83` 2026-06-12「fix(karte): Phase 5a/5b — カルテ見本一致 + 視覚ゲート稼働（--accent ネイビー統一）」→ PR #1971「fix(karte): Phase 5a — カルテパネル寸法是正（見本準拠・ADR-067 トークン化）」。`--inbox-textarea-min-h` は `13277eafd` 2026-05-26 → PR #817「余白・サイズCIブロック追加 + 全CSS違反修正（ADR-067）」。
- PR #1971 本文（gh pr view 1971）: 「カルテパネル（InboxKartePanel）の描画を見本に一致させる Phase 5a の実装。」、表に「フィールド padding `7px 9px`、radius `6px`、border `0.5px`」。
- docs: `docs/handoff/karte-visual-gate/recon.md:84-92`（§3-6 入力フィールド: 見本 `.fbox` と実装の差を表に記録: padding `7px 9px` 正本 vs 実装 4px 8px、border 0.5px vs 1px、radius 6px vs 4px — 当時の実装値）。`docs/specs/design-system/design.md:897` CSSI-0233「右パネルTextareaControlはresize=none、最小高さは同nativeの配置入口で既存inbox-textarea-min-hを参照」、:2071 karte の select 適用分の記述。`docs/handoff/color-tokens-ssot/recon.md:131-132`（--karte-field-bd/bg は「生きている」）。
- 計測メモ（事実）: border `0.5px` は Chromium 1280px・DPR1 の computed では `1px` に丸められる（ax2-baseline.json: border-top-width 1px）。
- 同じ class は textarea 8件のほかに input 24・a 1・button 1 も使う（ax2-shared-rules.md）。
- 参照するテスト: 0行。

## 3. `db-weekly-composer-input`（ダッシュボード）— PriorityProspectsSection.tsx:410 / WeeklyAdvisorSection.tsx:381
- CSS: `frontend/src/pages/dashboard/WeeklyAdvisorSection.css:205-219`（コメント無し）。`:focus` は `outline: 2px solid var(--accent); outline-offset: 1px`（box-shadow 方式の focus-ring ではない）。
- 宣言: `border:1px solid var(--border-subtle); background:var(--bg-primary); padding: var(--space-2) var(--space-3); font: inherit; resize: vertical`（font-size/line-height は font:inherit で親継承）。
- 専用トークン: なし（--border-subtle, --bg-primary は共通トークン）。
- 最初の導入: `283218f2a` 2026-06-21 shingo-ops「weekly advisor follow-up add」→ PR #2404「[codex] weekly advisor follow-up add」。PriorityProspects 側: `992fbbbd9` 2026-06-22 shingo-cc「w2-pr3 frontend priority prospects」。
- docs: git grep で docs/ *.md に 0 件（意図の記述なし）。同 class は `<input>` 2件にも使われる（PriorityProspectsSection.tsx:423 ほか。ax2-shared-rules.md）。
- 参照するテスト: クラス名は 0行。tests-e2e/scene1-dashboard.spec.ts:419,480 が `composer.locator("textarea")`（testid `weekly-followup-composer` 配下）。

## 4. `schedule-textarea`（予定入力欄）— SchedulePageImpl.tsx:378
- CSS: `frontend/src/pages/schedule.css:813-838`（`.schedule-input, .schedule-textarea` の共有規則 + `.schedule-textarea { padding: var(--space-2) var(--space-3); resize: vertical }` + focus は `outline:none; border-color: var(--accent); box-shadow: var(--focus-ring-shadow)`）。コメント無し。
- 専用トークン: なし（`.schedule-input` 側が `--comp-input-height-sm` を使う）。
- 最初の導入: `1e4c4e7fb` 2026-06-21 shingo-cc「fix schedule parity」→ PR #2399「[codex] fix schedule parity」。
- docs: 0件。参照するテスト: 0行。

## 5. `outbound-translation-edit`（送信下訳の編集欄）— OutboundTranslationPreview.tsx:147
- CSS: `InboxPage.css:1529-1534`、`:focus` :1535（コメント無し）。宣言: `padding: var(--space-3); border:1px solid var(--border); border-radius: var(--radius-sm); background: var(--bg-input); color: var(--text); font-size: var(--font-sm); line-height:1.5; resize: vertical`。
- 専用トークン: なし。
- 最初の導入: `7a6ca4fd2` 2026-06-04 shingo-ops「feat(adr-110): 会話ログ翻訳サブシステム」→ PR #1641「feat(translation): ADR-110 会話ログ翻訳サブシステム v1 — グロッサリ・確信度・送信下訳・3点セット」。
- docs: ADR-110 は存在（design.md の継承元として :2191 に記載）。textarea の見た目に触れる記述は git grep で 0 件。参照するテスト: 0行。

## 6. `.pmd-field textarea`（商品マスタ修正ドロワー）— ProductMasterDrawer.tsx:217,221
- CSS: `features/tcg-analysis-review/supplier-detail-view.css:244-253`（`.pmd-field input, .pmd-field textarea`）、:255-258（`min-height: var(--pmd-textarea-min-h); resize: vertical`）。
- 専用トークン: `--pmd-textarea-min-h: 72px` — supplier-detail-view.css:113、コメント原文「テキストエリア最小高（--textarea-min-h:80px より小さい専用値）」。:107-109 のブロックコメント「コンポーネント固有トークン — ADR-067: グローバルトークンに相当値なし」。
- 最初の導入: class `4cefe8a60` 2026-09-03 shingo-cc「feat(parity03-fe): ProductMasterDrawer Phase 3 実装」→ PR #3244「feat(parity03-fe): ProductMasterDrawer Phase 3 実装（仕入元詳細 → 商品マスタ修正ドロワー）」。トークンは `6df47fe88` 2026-09-03「fix(parity03-fe): CSS数値ハードコード修正（ADR-067 check:css-values 対応）」（同 PR #3244）。
- docs: `docs/handoff/parity03-product-master-drawer-fe/design.md:35`「コンポーネントローカルトークン: `--pmd-max-w: 480px`、`--pmd-textarea-min-h: 72px`」。

## 7. `ExtractionPromptConfigTab` の等幅 inline style — pages/super-admin/ExtractionPromptConfigTab.tsx:222
- 原文 (:233-238): `rows={16}` / `style={{ width: "100%", fontFamily: "var(--font-mono, monospace)", fontSize: "var(--font-sm)", boxSizing: "border-box" }}`。className 無し。適用される外観規則 0（ax2-applied-css.md: 適用規則なし。枠・padding・背景・color はブラウザ既定）。
- 最初の導入: `ac1c95914` 2026-09-26 shingo-cc「feat: 抽出プロンプトDB管理化 + バグ修正3件」→ PR #3793「feat: 抽出プロンプトDB管理化 + バグ修正3件」。
- docs: `docs/handoff/extraction-prompt-config/design.md` を grep（mono|等幅）: 0件。ExtractionPromptConfigTab への言及は同 design.md:21 他（タブ新設）。コード内に意図コメント無し。
- `--font-mono` の定義: frontend/src 内に `--font-mono:` の宣言は 0 件（`grep -rn -- --font-mono frontend/src` は参照のみ: distribution.css:106,289 / SupplierExtractionRulesPage.css:35,50 / DesignPreviewPage.css:83 ほか / 当該 tsx:235）。フォールバックの `monospace` が使われる。

## 8. `manual-record-textarea`（手動記録の内容欄）— ManualRecordSection.tsx:159
- **CSS 定義が存在しない**: `grep -rn "manual-record" frontend/src --include='*.css'` は 0 件（同ファイルの `manual-record-section/-header/-title/-datetime/-error` も CSS 0 件）。
- 最初の導入: `6190127a0`（ブランチ内）／マージ経由で `bda5239c8` 2026-06-11。PR #1937「feat(sa-02-stage3): 手動記録 API + スレッドUI + 翻訳発火 + 論理削除」。
- docs: design.md:2201 に「CSS 定義の無い class（…ManualRecordSection の `manual-record-textarea`）」の記録（ax0 の事実）。他 0件。
- 現状の見た目 = ブラウザ既定（ax2-baseline.md: 13.3333px 等幅、border 1px rgb(118,118,118)、padding 0、resize both）。

## 9. `input w-full resize-y`（DiscordAnnouncePage）— pages/admin/DiscordAnnouncePage.tsx:98
- **CSS 定義が存在しない**: `.input` / `.w-full` / `.resize-y` を定義する CSS 規則は frontend/src/**/*.css に 0 件（grep）。Tailwind 等の導入も package.json / vite.config に無い（grep tailwind|unocss|windi の結果は空）。`className="input"` は ChannelTypeCombobox.tsx:93 / CountryCombobox.tsx:92 にも有る（これらも `.input` の CSS は 0 件）。
- 最初の導入: `5cd35e385` 2026-06-02 shingo-ops「feat(discord): ADR-091 KPI4 — アナウンス投稿 API・UI」→ PR #1408 同題。
- docs: 0件（design.md:2201 の「CSS 定義の無い class」の記録のみ）。
- 現状の見た目 = ブラウザ既定（rows=6 のため height 92px、width 177px = cols 既定、等幅 13.3333px、border rgb(118,118,118)）。

## 10. その他（step 2 で見つけた特殊なもの）
- **ConditionsPage.tsx:340,350**: `className="field field-h-md"` + `style={{ height: "80px", resize: "vertical", width: "100%" }}`。直前コメント（原文）`{/* ui-allow: multi-line keyword input; TextField does not support textarea variant (#3594) */}`（:339,:349）。`.field` の CSS 規則は 0 件、`.field-h-md` は components/field-size.css:8（`min-height: var(--field-h-md, 36px); box-sizing:border-box`）。実際の外観は祖先 `.form-group textarea`（components.css:19/31/39）が決める。最初の導入 `327cfe9de` 2026-09-20 → PR #3599「feat: tenant conditions master page in management center」。
- **ConditionsMasterPanel.tsx:367,380**: `style={{ width: "100%", resize: "vertical" }}` + `rows={3}`。外観は祖先 `.form-group textarea`。導入 `ec86fcf02` 2026-09-20 → PR #3590「feat: conditions master tenant_id + super-admin CRUD panel」。
- **StaffReportsPage.tsx:90**: `style={{ minHeight: 'var(--textarea-min-h-lg)' }}`（120px）。トークン `--textarea-min-h-lg` は tokens.css:444「大テキストエリア最小高」、ADR-067:72 に表あり（`120px`）。導入 `432334a51` 2026-05-26 → PR #869「ADR-067 Phase 5B — width/height/maxWidth/minHeight/maxHeight 数値直書き禁止」。
- **ItemComparison.tsx:27,34**（解析レビュー）: className も inline style も無し。適用 CSS 規則 0（ax2-applied-css.md）。導入 `4b5d526c9` 2026-09-02 → PR #3226「feat(parity03): 解析レビュー FE 第1段階」。:34 は祖先 `.manual-actions`、`.item-extra-grid` を持つが textarea に当たる規則なし。
- **`.form-group textarea`（components.css:19/31/39）／`.form-grid > .form-row textarea` ・`.modal-content[-wide] .form-row textarea`（company-forms.css）**: 最初に現れたのは `87f322b80` 2026-04-06（App.css）、`1e1ecfb32` 2026-05-23 PR #574「refactor: App.css 1999行を6ファイルに分割」で現在のファイルへ。components.css:38 コメント `/* stylelint-disable-next-line no-descending-specificity -- intentional: textarea size after focus state */`。company-forms.css:254 の `.product-edit-form .form-group textarea` 直前コメント「入力枠が薄くて見えない問題の解消（--border → --border-strong で輪郭を明確に）」。
- 汎用トークン `--textarea-min-h: 80px`（tokens.css:170）。金型 FormField.css:66 も同じトークンを参照。

## 11. 全体に関わる記述
- `docs/specs/design-system/design.md:2189-2220`（§AX TextareaControl 本体）— 範囲は「見た目の変化0・利用ページ変更0」（本体追加のみ）。
- `docs/adr/ADR-144-ui-component-governance.md:114`: 製品 textarea53 の記録。
- ui-allow コメントを持つ textarea は ConditionsPage.tsx:340/350 の2件のみ（inventory の uiAllow）。
