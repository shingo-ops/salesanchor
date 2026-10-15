# AY-3b 受入結果（切替スイッチ8か所を共通部品 Toggle へ）

- 基準: origin/main 0fa5f5caa。設計: docs/handoff/ay3b-toggle/design.md。
- 「前」: 本番 CSS /tmp/CC報告ファイル/ssot-ay3a/prod/idx.css（index-DDKExstm.css）1 本。同時に origin/main 0fa5f5caa の vite build CSS（index-BwIsH5wu.css）でも測り、2 つの結果は完全一致（B1 該当なし）。「後」: 作業ツリー（HEAD となる内容）の vite build CSS（index-Bne_nC5F.css）1 本。手で並べていない。
- fixture: 4 ページ（InboxSettingsModal=トグル 4、PreferencesSection=1、予定の終日ポップオーバー=1、予定設定=2）の祖先の連鎖を再現。「後」のトグル DOM は Toggle を renderToStaticMarkup した結果。
- 条件: 幅 390/1280 × ライト/ダーク × OFF/ON/focus-visible（Tab キー）× 8 か所。比較した値 1536、表の項目外の差 0（ay3b-compare.txt 末尾）。
- 測定スクリプト: ay3b-measure.cjs（+ ay3b-render-toggle.tsx）、比較 ay3b-compare.cjs。生 JSON: ay3b-measure-before.json・ay3b-measure-after.json。スクリーンショット（1280、奇数番目のトグルだけ ON）: ay3b-before-*.png・ay3b-after-*.png（light/dark × modal・pref・allday・settings）。
- 未実施: 実アプリ画面での撮影（fixture のみ）。fixture は PageLayout 等の外側の枠を再現していないため、行の絶対幅は実画面と一致しない。前後の差を見るための比較。

## 場所ごとの前→後（実測値）

| 項目 | Inbox 4（/lead-chat 設定） | Preferences 1（/account/settings） | 予定 3（/schedule 終日・/schedule/settings 2） |
|---|---|---|---|
| 枠 幅×高さ | 40×22 → 44×24 | 40×22 → 44×24 | 42×24 → 44×24 |
| つまみ | 16 → 18 | 18 → 18 | 18 → 18 |
| ON の移動量 | 18 → 20 | 20 → 20（はみ出し: ON の右余白 -1px → 3px） | 18 → 20 |
| つまみの影 | 無 → rgba(0,0,0,0.2) 0 2px 4px（ダーク rgba(0,0,0,0.35)） | 有 → 有（差 0） | 無 → 同左 |
| 枠の角（計算値） | 12px → 9999px | 9999px → 9999px | 12px → 9999px |
| transition（背景・つまみ） | 0.1s → 0.1s | 0.2s → 0.1s | 0.1s → 0.1s |
| focus-visible の輪 | 無 → rgba(30,58,138,0.15) 0 0 0 3px（ダーク rgba(91,141,217,0.3)） | 有 → 有（差 0） | 無 → 同左 |
| display / flex-shrink / input の opacity・幅・position | flex / 0 / 0・0px・absolute → 同（差 0） | 同（差 0） | 同（差 0） |
| 背景色（OFF/ON）・つまみ色（ライト・ダーク） | 差 0 | 差 0 | 差 0 |
| 行の高さ | 39 → 41（+2） | 47 → 49（+2） | 終日 24 → 24、設定の行 差 0 |
| 名前（支援技術） | 無 → input aria-label（4 件: Show right panel・Default unread only・Browser notifications・Sound） | label[for] の文字 → 同（差 0） | 終日: 無 → input aria-label／設定 2: label の aria-label → input の aria-label |
| role | checkbox → switch | checkbox → switch | checkbox → switch |

表の項目の派生として出た差（設計 §1.1 の表には書かれていない行・操作欄の差）:
- 予定設定の操作欄（.schedule-settings__calendar-actions）の幅 195.39 → 197.39px（全 4 条件）、操作欄の scrollWidth 195 → 197（clientWidth と同じ値、操作欄の内側ははみ出さない）。トグル幅 42 → 44 の +2px がそのまま出る。
- 予定設定の行（.schedule-settings__calendar-row）の scrollWidth: 1280px は 1002 → 1002（差 0、clientWidth と同じ）。390px は 219 → 221（+2）。390px の fixture では clientWidth 112 に対し旧の時点で 219 とはみ出している（予定設定の shell は 2 列のまま 767px 以下でも 1 列にならない: frontend/src/pages/schedule.css:887-894、:1278 の media に shell の規則なし）。
- Preferences の行の scrollWidth 341 → 340（390）・1231 → 1230（1280）: ON のつまみの 1px はみ出しが 0 になった分（-1px、clientWidth との差が 1 → 0）。

## 判定
- 表の項目の差は設計 §1.1 どおり。色・display・flex-shrink・input の既定値の差は 0（B4・B5・B6 該当なし）。
- B7（390px で行か操作欄の scrollWidth が増える）: 字面どおり該当。設計者（Opus）判断で許容: 増分 +2px は PO 決定の幅 42→44 の直接の派生、操作欄内側のはみ出し 0、390px 行のはみ出しは旧から（schedule.css:887-894）で本便の範囲外
