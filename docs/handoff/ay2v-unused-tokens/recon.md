# AY-2v recon: 未使用トークン30件の確定

基準 SHA: e6923ba61 (origin/main, 2026-10-14 fetch 後。実装時 HEAD は a39fb988f で tokens.css・index.css は同一)
生出力: 本文の件数は実装時に再取得した ay2v-grep18.txt / ay2v-audit-before.txt で再確認済み（docs/handoff/design-system-recon/evidence-20260910/）

## 1. 監査スクリプトの仕様 (frontend/scripts/check-unused-tokens.js)
- 定義抽出: tokens.css と index.css の `^\s*(--x)\s*:` (:49-58, :21-24)。
- 走査対象: frontend/src 配下の .css/.tsx/.ts のみ (:18, :27)。lp/・scripts/・.github/・docs/・public/・index.html・.stories(.tsx は走査される)・tests-e2e/(src外) は走査外。
- 「使用」判定: 正規表現 `var\((--[\w-]+)` の一致のみ (:90)。定義側の var() も数える。
- 検出できない形: `var(${name})` テンプレート、`'--x'` 文字列、getPropertyValue/setProperty、コメント内言及。
- 除外: EXEMPT_PREFIXES `--ds-` `--breakpoint-` (:30-33) / EXEMPT_NAMES 8件 (:38-47: --icon-sm/md, --z-sidebar-overlay, --z-toast, --ease-*, --inbox-hover)。
- 件数: 30件 (期待どおり)。
- 実在する動的参照: frontend/src/pages/design-system/DesignSystemPage.tsx:72 `style={{ background: \`var(${t.name})\` }}` (COLOR_TOKENS :14-62 の名前を実行時に var() 化)。
  frontend/scripts/check-color-token-sync.js:44-52,60-70 は index.css :root の bg/text/accent/border/success/warning/danger/info 接頭辞トークンが COLOR_TOKENS に全て載ることを要求 (CI exit 1)。
- 動的組み立て調査 (dynamic.txt): `--${...}` 型の変数名組み立ては DesignSystemPage 以外に無し。テンプレート文字列は全て className 用 (`comp-*--${variant}` 等)。PipelineMapPanel の badgeType は manual/auto のみ (PipelineMapPanel.tsx:242-317)、CSS は manual/auto/mixed だけ (PipelineMapPanel.css:52-62) なので --cat-import 等は動的にも使われない。
- getPropertyValue 利用: DashboardPage.tsx:176 は --accent のみ、design-preview/sections/_shared.tsx:28 は渡されたトークン名 (ModalSection 等の一覧に 30件の名前は無い)。
- Storybook/テスト/lp/.astro/.github/public: 30件の名前のヒット無し (hits.txt 全体確認)。他トークンからの var() 参照: 30件とも無し (定義側ヒットは index.css/tokens.css の定義行のみ)。

## 2. 30件の表
略: コード0 = frontend/src・lp・scripts・.github・tests に定義行以外のヒット無し。docs = docs/handoff 以外。handoff は過去の調査記録 (件数は hits.txt 参照)。
index.css は :root (8-219) と :root.force-dark (220-414) の2ブロック。メディアクエリ定義無し。tokens.css は :root (11-) + @media(max-width:1279px) (582-) + :root.force-dark (590-)。

| # | トークン | 定義 (file:line) | 定義行以外のヒット | 動的組立 | 他token var() | 判定 |
|---|---|---|---|---|---|---|
| 1 | --size-avatar-sm | frontend/src/tokens.css:231 | InboxPage.css:1193 (コメント) / docs/specs/design-system/visual-language/benchmark/whatsapp-reproduction-spec.md:223 (「32pxはこのトークン」と指す設計表) | 無 | 無 | 保留: コード0だがspecが推奨トークンとして名指し。消すなら spec 側修正が要る |
| 2 | --cat-import | tokens.css:256 | 無 (handoff/pipeline-map-flowchart/recon.md:21 のみ) | 無(badgeTypeは3種) | 無 | 消せる |
| 3 | --cat-discord | tokens.css:257 | 無 | 無 | 無 | 消せる |
| 4 | --cat-distribution | tokens.css:258 | 無 (handoff recon.md:21) | 無 | 無 | 消せる |
| 5 | --cat-inventory | tokens.css:259 | 無 | 無 | 無 | 消せる |
| 6 | --max-width-modal-sm | tokens.css:295 | docs/audits/2026-06-08_definition-state.md:212,222,246,367 (過去監査・時点記録) | 無 | 無 | 消せる (audits は履歴) |
| 7 | --inbox-collapsed-panel-w | tokens.css:312 | 無 (handoff 2件) | 無 | 無 | 消せる |
| 8 | --karte-ok-bg | tokens.css:331 | 無 | 無 | 無 | 消せる |
| 9 | --topnav-email-max-w | tokens.css:343 | 無 | 無 | 無 | 消せる |
| 10 | --schedule-cell-icon-size | tokens.css:368 | 無 | 無 | 無 | 消せる |
| 11 | --schedule-min-h | tokens.css:369 | 無 (schedule.css:7-24 の別名 --schedule-month-cell-min-h 等は別トークン) | 無 | 無 | 消せる |
| 12 | --schedule-mini-col-min-w | tokens.css:370 | 無 | 無 | 無 | 消せる |
| 13 | --schedule-slot-h | tokens.css:371 (既定) と :584 (@media ≤1279px 上書き) | 無 | 無 | 無 | 消せる (2か所とも消す) |
| 14 | --schedule-nav-btn-size | tokens.css:372 | 無 | 無 | 無 | 消せる |
| 15 | --schedule-row-height-compact | tokens.css:380 | 無 | 無 | 無 | 消せる |
| 16 | --table-col-min-width | tokens.css:437 | frontend/eslint.config.js:95,197 (lintエラー文の推奨記述 `minWidth: 'var(--table-col-min-width)'`) / docs/adr/ADR-067-design-token-enforcement.md:65 | 無 | 無 | 保留: lint文が利用者に勧めている。消すなら eslint文言と ADR-067 を同時修正 |
| 17 | --modal-commission-w | tokens.css:452 | docs/adr/ADR-067-design-token-enforcement.md:71 / docs/audits/2026-06-08_definition-state.md:141 | 無 | 無 | 消せる (ADR-067 の行削除が必要) |
| 18 | --modal-detail-max-w | tokens.css:453 | docs/adr/ADR-067-design-token-enforcement.md:72 | 無 | 無 | 消せる (同上) |
| 19 | --bg-disabled | frontend/src/index.css:146 / :349 | DesignSystemPage.tsx:34 (COLOR_TOKENS、:72 で var(${name}) 実行時参照) / components.css:88 (コメント) | 有(DS見本帳) | 無 | 消さない: 実行時に参照され、check-color-token-sync(CI)が掲載を要求 |
| 20 | --accent-bg | index.css:153 / :357 (どちらも var(--accent)) | DesignSystemPage.tsx:44 (同上) | 有 | 無 | 消さない: 同上 |
| 21 | --color-blue-100 | index.css:157 / :361 | 無 (handoff 3件) | 無 | 無 | 消せる |
| 22 | --color-blue-700 | index.css:158 / :362 | docs/specs/design-system/design.md:30 (命名規則の例示文のみ) | 無 | 無 | 消せる (例示文は値の説明。実在参照ではない) |
| 23 | --color-gray-100 | index.css:159 / :363 | docs/specs/design-system/design.md:76 / docs/specs/design-tokens-ssot/color/calendar/design.md:37 (calendar-release-tint の参照先として確定値埋め込み) | 無 | 無(計画書側のみ) | 保留: 計画書が var(--color-gray-100) を使う前提 |
| 24 | --color-gray-600 | index.css:160 / :364 | design.md:157 / calendar/design.md:36,89 (calendar-release-color の参照先) | 無 | 無 | 保留: 同上 |
| 25 | --color-red-700 | index.css:162 / :366 | design.md:71 / calendar/design.md:34 (calendar-shipping-text) | 無 | 無 | 保留: 同上 |
| 26 | --color-amber-50 | index.css:163 / :367 | 無 (handoff 2件) | 無 | 無 | 消せる |
| 27 | --color-amber-800 | index.css:164 / :368 | design.md:74 / calendar/design.md:35 (calendar-billing-text) | 無 | 無 | 保留: 同上 |
| 28 | --color-border-subtle | index.css:165 / :369 | design.md:77 / calendar/design.md:38 (calendar-release-text) | 無 | 無 | 保留: 同上 |
| 29 | --calendar-today-text | index.css:187 / :391 (ダークは var(--palette-ink-deep)) | 無 (handoff 1件) | 無 | 無(兄弟 --calendar-today-bg は :202 から参照されるが別) | 消せる |
| 30 | --calendar-today-cell-bg | index.css:188 / :392 | 無 | 無 | 無 | 消せる |

集計 (判定): 消せる 21件 = #2,3,4,5,6,7,8,9,10,11,12,13,14,15,17,18,21,22,26,29,30 / 消さない 2件 = #19,20 / 保留(別修正が要る) 7件 = #1,16,23,24,25,27,28。

【注意】計画書 (docs/specs/design-tokens-ssot/color/calendar/design.md) が「確定値」として #23,24,25,27,28 を参照先に指定。calendars.config.ts は現状 hex 直書き (calendars.config.ts:23-32)。計画の現行性 (実施中か破棄か) は未確認のため保留。

## 3. 消せる候補の整形影響 (行削除後)
- tokens.css `Pipeline map カテゴリ色` (:254-259): 4行消しても --cat-supplier/pipeline/product/master が残り、見出しコメントは空にならない。PipelineMapPanel.css:6 のコメント「--cat-* 変数を使用」は引き続き真。
- tokens.css `Modal sizes` (:294-): --max-width-modal-sm 削除後も --modal-max-w 系が残る。`Phase 5 モーダル・パネル幅` (:446-): 削除後も --modal-wide-w 他が残る。
- tokens.css `Inbox layout` (:310-): 他3行残る。`Topbar / Responsive`: --search-bar-max-w 残る。カルテ節: --karte-ok 残る。
- tokens.css `Schedule page` (:366-): 6本消しても他が多数残る。@media (max-width:1279px) ブロック (:582-587) は --schedule-slot-h 削除後も --schedule-allday-row-h が残り空にならない。
- index.css FedEx バッジ色ブロック (:156-166 / :360-370, ADR-125): blue-100/blue-700/amber-50 のみ消す場合も他 color-* 行が残る (保留分を残すなら尚更)。全部消す案は --color-red-50 のみ残る。
- index.css Google Calendar ブロック: today-text/today-cell-bg を消しても --calendar-today-bg 他が残る。
- index.css は :root と :root.force-dark の対で消す必要あり (dark-parity)。片側のみ消すと不整合 (ADR-067)。

## 4. docs 更新が要る箇所 (削除時)
- docs/adr/ADR-067-design-token-enforcement.md:65 (--table-col-min-width, 保留時)、:71 (--modal-commission-w)、:72 (--modal-detail-max-w)。
- docs/specs/design-system/design.md:30 (--color-blue-700 例示文。例示を別トークンに差し替え推奨)、:31 は --accent の例で影響無し。
- docs/audits/2026-06-08_definition-state.md:141,212,222,246,367 は過去時点の監査記録 (更新不要が妥当、PO判断)。
- docs/handoff/** の言及は全て過去の調査記録 (件数 hits.txt/handoff-md.txt)。更新対象外が妥当。
- frontend/eslint.config.js:95,197 (--table-col-min-width を勧める文言、保留時の根拠)。
- frontend/scripts/check-unused-tokens.js の EXEMPT_NAMES に --bg-disabled/--accent-bg を追加する案 (--inbox-hover と同じ「cataloged」扱い)。
- docs/specs/design-system/design.md に、30件のトークンを一覧するカタログ表は無い (grep で上記以外ヒット無し)。
