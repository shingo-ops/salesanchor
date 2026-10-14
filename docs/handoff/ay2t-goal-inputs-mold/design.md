# AY-2t 設計: 目標設定ページの数値入力3種（最大18個）→ 金型 TextFieldControl

- 状態: 設計審査済み（APPROVE、改訂1反映）。PO 委任 2026-10-14「金型への登録を全権限委譲」。既存金型の適用のみ（金型無改変・業務挙動不変）。
- 現在地の根拠: docs/handoff/ay2t-goal-inputs-mold/recon.md
- 対象 ADR: docs/adr/ADR-027-ui-internationalization.md / docs/adr/ADR-067-design-token-enforcement.md / docs/adr/ADR-144-ui-component-governance.md

## 1. 変更契約（行番号は変更前 origin/main 基準。import のみ変更後の行）
|箇所|変更前|変更後|
|---|---|---|
|`frontend/src/pages/goal-setting/GoalSettingPage.tsx:162`（行入力）|生 `<input … className={`gs-input${saved ? " gs-input-saved" : ""}`}>`|`<TextFieldControl … className={saved ? "gs-input-saved" : undefined}>`（他 props 逐語）|
|`frontend/src/pages/goal-setting/GoalSettingPage.tsx:235`（週次指標）|`gs-input gs-advisor__metric-input`|`<TextFieldControl … className="gs-advisor__metric-input">`|
|`frontend/src/pages/goal-setting/GoalSettingPage.tsx:339`（月次 KGI）|`gs-input gs-advisor__monthly-input`|`<TextFieldControl id data-testid … className="gs-advisor__monthly-input">`|
|`frontend/src/pages/goal-setting/GoalSettingPage.tsx:19`|—|`import { TextFieldControl } from "../../components/TextField";`（Select の import の直後）|
|`frontend/src/pages/goal-setting/GoalSettingPage.css:510-530`|`.gs-input{…}` `.gs-input:focus{…}` `.gs-input.gs-input-saved{…}`|基底と focus を削除。`.comp-field__input.gs-input-saved, .comp-field__input.gs-input-saved:focus {border-color: var(--success); background: var(--success-bg-subtle);}`|
|`frontend/src/pages/goal-setting/GoalSettingPage.stories.tsx:9, 29`|生 input|`TextFieldControl`（import は `./GoalSettingPage.css` の前）|

触らない: TextField.tsx・FormField.css、i18n、e2e、保存ロジック、`.gs-saved-mark`・`.gs-input-wrap`・`.gs-row`・`.gs-label`。

## 2. 想定分岐と実測結果
- D1 saved×focus の枠: saved が勝つ（`:focus` 側 0,3,0 で順序非依存）。アプリ・Storybook とも枠 success を実測。
- D2 月次 KGI・週次指標の高さ: 44px 維持。
- D3 CSS 順序: dist で金型 focus（offset 42271）より saved 規則（94456）が後。
- D4 e2e: 手元実行は本タスクでは行わず（CI では e2e が無効）、preview 実測（月次 KGI fill→生成→週次指標に値、POST body 一致）を正とした。

## 3. 前後
|項目|前|後|
|---|---|---|
|背景（非 saved）|#f5f7fa|#fff（--bg-surface）|
|文字|13.6px|14.4px|
|行入力の高さ|33px|39.61px（≤767px 44px）|
|月次 KGI・週次指標の高さ|44px|44px|
|focus|枠 accent のみ（週次指標は既にリングあり）|枠 accent＋金型リング|
|saved|枠 success・背景 success-bg-subtle|同じ（focus 時も枠 success）|
|幅・角・枠・padding|差なし|差なし|

## 4. 検証
|基準|検証方法|
|---|---|
|3種とも `comp-field__input`、gs-input 単独 class 0 件|after 実測 ＋ `git grep -nE "gs-input([\"' ]\|$)\|\.gs-input([ :{,]\|$)" -- frontend/src`|
|背景・文字・高さが §3 の後の値、幅・角・枠・padding 差0|before/after 実測（1280/1440/375/dark）|
|saved×focus の枠 success、背景 success-bg-subtle|アプリ・Storybook 実測|
|saved マークが入力内、縦中心差 ±1px|実測|
|POST /goals body 前後一致、id/testid/aria-label 維持|page.route 記録|
|横スクロールなし|doc scrollWidth==clientWidth|
|品質コマンド全成功|ログ（/tmp/CC報告ファイル/ssot-ay2t/impl/q-*.txt）|

詳細: docs/handoff/design-system-recon/evidence-20260910/ay2t-acceptance.md

## 外部・過去事例の参照と我々への応用
- 外部事例: 不要（社内金型の適用のみ）。
- 過去事例: AY-2s（#4254）で生 input を TextFieldControl に移行した手順を踏襲。AY-2p の複合セレクタ（frontend/src/components/field-size.css）に倣い、保存済みの見た目を `.comp-field__input.gs-input-saved`／`:focus` にして読み込み順への依存を避けた。

## 代替案
- 背景 --bg-primary を modifier で残す: 金型標準からの逸脱を新設する（ADR-144）ため不採用。
- ラッパー付き TextField: 自前 label と二重・margin で行が崩れるため不採用。
- size="sm"（文字 13.6px を保つ）: 高さ 28px になり寸法が大きく変わるため不採用。

## 維持の仕組み
守り手: frontend/src/components/TextField.tsx（入力欄の見た目の正本）。frontend/src/pages/goal-setting/GoalSettingPage.stories.tsx（saved の見た目確認）、frontend/tests-e2e/goal-setting-advisor.spec.ts（testid の維持）。既知の穴: type=number は scripts/check-ui-governance.js の検出対象外（残件）。
