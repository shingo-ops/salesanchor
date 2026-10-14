# AY-2t 受入表（設計 §4 ＋ 改訂1）。実測: preview(開発ビルド) を Playwright で before/after。生データ before.json / after.json / cmp.txt

|基準|判定|根拠（before → after）|
|---|---|---|
|3種とも class comp-field__input、gs-input 単独 class 0 件|OK|after.json allInputsClass: 全16行入力=`comp-field__input`、月次KGI=`comp-field__input gs-advisor__monthly-input`、週次3個=`comp-field__input gs-advisor__metric-input`（4画面とも）。`git grep -nE "gs-input([\"' ]|$)\|\.gs-input([ :{,]\|$)" -- frontend/src` 0件|
|背景・文字・高さが §3 の後の値|OK|背景 rgb(245,247,250)→rgb(255,255,255)、文字 13.6→14.4px、行入力の高さ 33→39.61px（1280/1440）・375は 33→44px。月次KGI・週次3個の高さは 44→44（1280/1440/375）|
|幅・角・枠・padding 差0|OK|cmp.txt の diff に width/border-radius/border-top-width/padding の項目なし（4画面×5要素）。rect.width は全要素 before==after|
|saved 枠 success・背景 success-bg-subtle・focus 時も枠 success|OK|1280/1440/375: normal・focus とも border rgb(46,125,50)・bg rgba(72,187,120,0.05)（before と同値）。dark: rgb(74,222,128)・rgba(74,222,128,0.1)（before と同値）。focus 時 box-shadow は金型リング（before は none）|
|`.gs-saved-mark` が入力 rect 内、縦中心差 ±1px 以内|OK|insideInput=true（4画面）。centerYDiff before 0 → after -0.01(1280/1440/dark)・0(375)|
|月次KGI fill→生成→週次指標に値、POST /goals body 前後一致|OK|weeklyValues before/after とも ['50','10','5']。postBodies 前後一致（`{"user_id":6,"period_type":"monthly","period_year":2026,"period_num":10,"kpi_type":"revenue","target_value":3000000}`）|
|id/testid/aria-label が input 自身に残る|OK|after: monthly id=advisor-monthly-kgi・testid=goal-advisor-monthly-kgi。週次3個 aria-label=リード/商談/成約。type=number・min=0・step=1 維持|
|doc scrollWidth==clientWidth|OK|1280/1280、1440/1440、375/375、dark 1280/1280|
|console error|OK|before/after とも 0件（4画面）|
|D1 saved×focus（アプリ）|OK|上記 saved focus 行。Storybook SavedInputState も light: border rgb(46,125,50)、dark: rgb(74,222,128)（storybook-saved.json）|
|D2 min-height / 高さ 44px|OK|月次KGI・週次指標 44px 維持|
|D3 CSS 順序（dist）|OK|dist/assets/index-DHY1Ra-y.css: `.comp-field__input:focus` offset 42271 < `.comp-field__input.gs-input-saved,...:focus` offset 94456。`.gs-input{` 0件|
|dark（LOW-1）|OK|背景 rgb(15,23,42)→rgb(30,41,59)（--bg-surface dark）、saved bg rgba(74,222,128,0.1)、枠・focus リングは金型 dark 値|
|品質|OK（注記）|generate・tsc・lint・check:all・build・build-storybook 成功。test:coverage は 5000ms で 3 failed（StaffFormButtonMigration 2件・SubMenu 1件 = Test timed out、本変更無関係）→ --testTimeout=60000 で再実行し成功。ログ q-test-coverage.txt / q-test-coverage-t60.txt|
|本番 CSS に `.comp-field__input.gs-input-saved` あり、`.gs-input{` 0件（prod bundle grep）|未確認|マージ・本番反映後の確認。ビルド出力では確認済み（D3）|
