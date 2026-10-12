# nontext-after（非 text input の変更前後。Chromium 147.0.7727.15、light）

方法: before = 92db2c38b の frontend/src 全 CSS 68 ファイル、after = PR HEAD の全 CSS（作業ツリー）。@import は除去して結合。読み込み順が不定のため 18 通りの並べ順（alpha・reverse・競合規則を持つ 8 ファイルを先頭/末尾に置いた順）で、幅 1280・375 × normal・focus、fixture 113 要素（A: 実 DOM の 9 件、B: 競合クラス × .form-group の全組み合わせ 104 要素）を描画し、computed style 全項目（594 項目）と getBoundingClientRect・offset 寸法・親 .form-group の寸法を比較。

測定: 8136 比較（要素×並べ順×幅×状態）。差のある数: A（実 DOM 9 件と祖先連鎖どおりの実在の組み合わせ）**0**、B（網羅用の仮想の組み合わせ）**1248**

検出力の確認: components.css の .form-group input[type=checkbox...] の padding を意図的に変えた after を比べ、差が検出されること（検出力の確認） → 差が出た要素数 53（0 でなければ検出できている）。

## 差分

- B toggle-switch inner / form-group outer / checkbox | inline-size,inset-inline-end,perspective-origin,right,transform-origin,width,#rect-in-fg,#offset (72件; 例 1280/alpha/normal): inline-size 0px -> 1280px; inset-inline-end 1280px -> 0px; perspective-origin 0px 0px -> 640px 0px; right 1280px -> 0px; transform-origin 0px 0px -> 640px 0px; width 0px -> 1280px
- B toggle-switch inner / form-group outer / radio | inline-size,inset-inline-end,perspective-origin,right,transform-origin,width,#rect-in-fg,#offset (72件; 例 1280/alpha/normal): inline-size 0px -> 1280px; inset-inline-end 1280px -> 0px; perspective-origin 0px 0px -> 640px 0px; right 1280px -> 0px; transform-origin 0px 0px -> 640px 0px; width 0px -> 1280px
- B toggle-switch inner / form-group outer / range | inline-size,inset-inline-end,perspective-origin,right,transform-origin,width,#rect-in-fg,#offset (72件; 例 1280/alpha/normal): inline-size 2px -> 1280px; inset-inline-end 1278px -> 0px; perspective-origin 1px 1px -> 640px 1px; right 1278px -> 0px; transform-origin 1px 1px -> 640px 1px; width 2px -> 1280px
- B toggle-switch inner / form-group outer / file | inline-size,inset-inline-end,perspective-origin,right,transform-origin,width,#rect-in-fg,#offset (72件; 例 1280/alpha/normal): inline-size 2px -> 1280px; inset-inline-end 1278px -> 0px; perspective-origin 1px 1px -> 640px 1px; right 1278px -> 0px; transform-origin 1px 1px -> 640px 1px; width 2px -> 1280px
- B inbox-toggle outer / form-group inner / checkbox | inline-size,perspective-origin,transform-origin,width,#rect-in-fg,#offset,#fg-size (60件; 例 1280/alpha/normal): inline-size 0px -> 13px; perspective-origin 0px 0px -> 6.5px 0px; transform-origin 0px 0px -> 6.5px 0px; width 0px -> 13px; #rect-in-fg 0,18,0,0 -> 0,18,13,0; #offset 0x0 -> 13x0
- B inbox-toggle inner / form-group outer / checkbox | inline-size,perspective-origin,transform-origin,width,#rect-in-fg,#offset (60件; 例 1280/alpha/normal): inline-size 0px -> 1280px; perspective-origin 0px 0px -> 640px 0px; transform-origin 0px 0px -> 640px 0px; width 0px -> 1280px; #rect-in-fg 0,18,0,0 -> 0,18,1280,0; #offset 0x0 -> 1280x0
- B inbox-toggle outer / form-group inner / radio | inline-size,perspective-origin,transform-origin,width,#rect-in-fg,#offset,#fg-size (60件; 例 1280/alpha/normal): inline-size 0px -> 13px; perspective-origin 0px 0px -> 6.5px 0px; transform-origin 0px 0px -> 6.5px 0px; width 0px -> 13px; #rect-in-fg 0,18,0,0 -> 0,18,13,0; #offset 0x0 -> 13x0
- B inbox-toggle inner / form-group outer / radio | inline-size,perspective-origin,transform-origin,width,#rect-in-fg,#offset (60件; 例 1280/alpha/normal): inline-size 0px -> 1280px; perspective-origin 0px 0px -> 640px 0px; transform-origin 0px 0px -> 640px 0px; width 0px -> 1280px; #rect-in-fg 0,18,0,0 -> 0,18,1280,0; #offset 0x0 -> 1280x0
- B inbox-toggle outer / form-group inner / range | inline-size,perspective-origin,transform-origin,width,#rect-in-fg,#offset,#fg-size (60件; 例 1280/alpha/normal): inline-size 2px -> 131px; perspective-origin 1px 1px -> 65.5px 1px; transform-origin 1px 1px -> 65.5px 1px; width 2px -> 131px; #rect-in-fg 0,16,2,2 -> 0,16,131,2; #offset 2x2 -> 131x2
- B inbox-toggle inner / form-group outer / range | inline-size,perspective-origin,transform-origin,width,#rect-in-fg,#offset (60件; 例 1280/alpha/normal): inline-size 2px -> 1280px; perspective-origin 1px 1px -> 640px 1px; transform-origin 1px 1px -> 640px 1px; width 2px -> 1280px; #rect-in-fg 0,16,2,2 -> 0,16,1280,2; #offset 2x2 -> 1280x2
- B inbox-toggle outer / form-group inner / file | inline-size,perspective-origin,transform-origin,width,#rect-in-fg,#offset,#fg-size (60件; 例 1280/alpha/normal): inline-size 2px -> 305px; perspective-origin 1px 1px -> 152.5px 1px; transform-origin 1px 1px -> 152.5px 1px; width 2px -> 305px; #rect-in-fg 0,0,2,2 -> 0,0,305,2; #offset 2x2 -> 305x2
- B inbox-toggle inner / form-group outer / file | inline-size,perspective-origin,transform-origin,width,#rect-in-fg,#offset (60件; 例 1280/alpha/normal): inline-size 2px -> 1280px; perspective-origin 1px 1px -> 640px 1px; transform-origin 1px 1px -> 640px 1px; width 2px -> 1280px; #rect-in-fg 0,0,2,2 -> 0,0,1280,2; #offset 2x2 -> 1280x2
- B topbar-search outer / form-group inner / checkbox | background-color (60件; 例 1280/alpha/normal): background-color rgba(0, 0, 0, 0) -> rgb(255, 255, 255)
- B topbar-search inner / form-group outer / checkbox | background-color (60件; 例 1280/alpha/normal): background-color rgba(0, 0, 0, 0) -> rgb(255, 255, 255)
- B topbar-search outer / form-group inner / radio | background-color (60件; 例 1280/alpha/normal): background-color rgba(0, 0, 0, 0) -> rgb(255, 255, 255)
- B topbar-search inner / form-group outer / radio | background-color (60件; 例 1280/alpha/normal): background-color rgba(0, 0, 0, 0) -> rgb(255, 255, 255)
- B topbar-search outer / form-group inner / range | background-color,block-size,border-block-end-color,border-block-end-style,border-block-end-width,border-block-start-color,border-block-start-style,border-block-start-width,border-bottom-color,border-bottom-style,border-bottom-width,border-inline-end-color,border-inline-end-style,border-inline-end-width,border-inline-start-color,border-inline-start-style,border-inline-start-width,border-left-color,border-left-style,border-left-width,border-right-color,border-right-style,border-right-width,border-top-color,border-top-style,border-top-width,height,inline-size,perspective-origin,transform-origin,width,#rect-in-fg,#offset,#fg-size (29件; 例 1280/alpha/normal): background-color rgba(0, 0, 0, 0) -> rgb(255, 255, 255); block-size 16px -> 18px; border-block-end-color rgb(26, 32, 44) -> rgb(226, 232, 240); border-block-end-style none -> solid; border-block-end-width 0px -> 1px; border-block-start-color rgb(26, 32, 44) -> rgb(226, 232, 240)
- B topbar-search inner / form-group outer / range | background-color,block-size,border-block-end-color,border-block-end-style,border-block-end-width,border-block-start-color,border-block-start-style,border-block-start-width,border-bottom-color,border-bottom-style,border-bottom-width,border-inline-end-color,border-inline-end-style,border-inline-end-width,border-inline-start-color,border-inline-start-style,border-inline-start-width,border-left-color,border-left-style,border-left-width,border-right-color,border-right-style,border-right-width,border-top-color,border-top-style,border-top-width,height,perspective-origin,transform-origin,#rect-in-fg,#offset,#fg-size,#wrap-size (29件; 例 1280/alpha/normal): background-color rgba(0, 0, 0, 0) -> rgb(255, 255, 255); block-size 16px -> 18px; border-block-end-color rgb(26, 32, 44) -> rgb(226, 232, 240); border-block-end-style none -> solid; border-block-end-width 0px -> 1px; border-block-start-color rgb(26, 32, 44) -> rgb(226, 232, 240)
- B topbar-search outer / form-group inner / file | background-color,block-size,border-block-end-color,border-block-end-style,border-block-end-width,border-block-start-color,border-block-start-style,border-block-start-width,border-bottom-color,border-bottom-style,border-bottom-width,border-inline-end-color,border-inline-end-style,border-inline-end-width,border-inline-start-color,border-inline-start-style,border-inline-start-width,border-left-color,border-left-style,border-left-width,border-right-color,border-right-style,border-right-width,border-top-color,border-top-style,border-top-width,height,inline-size,perspective-origin,transform-origin,width,#rect-in-fg,#offset,#fg-size,#wrap-size (29件; 例 1280/alpha/normal): background-color rgba(0, 0, 0, 0) -> rgb(255, 255, 255); block-size 24px -> 26px; border-block-end-color rgb(26, 32, 44) -> rgb(226, 232, 240); border-block-end-style none -> solid; border-block-end-width 0px -> 1px; border-block-start-color rgb(26, 32, 44) -> rgb(226, 232, 240)
- B topbar-search inner / form-group outer / file | background-color,block-size,border-block-end-color,border-block-end-style,border-block-end-width,border-block-start-color,border-block-start-style,border-block-start-width,border-bottom-color,border-bottom-style,border-bottom-width,border-inline-end-color,border-inline-end-style,border-inline-end-width,border-inline-start-color,border-inline-start-style,border-inline-start-width,border-left-color,border-left-style,border-left-width,border-right-color,border-right-style,border-right-width,border-top-color,border-top-style,border-top-width,height,perspective-origin,transform-origin,#rect-in-fg,#offset,#fg-size,#wrap-size (29件; 例 1280/alpha/normal): background-color rgba(0, 0, 0, 0) -> rgb(255, 255, 255); block-size 24px -> 26px; border-block-end-color rgb(26, 32, 44) -> rgb(226, 232, 240); border-block-end-style none -> solid; border-block-end-width 0px -> 1px; border-block-start-color rgb(26, 32, 44) -> rgb(226, 232, 240)
- B topbar-search outer / form-group inner / range | background-color,block-size,border-block-end-style,border-block-end-width,border-block-start-style,border-block-start-width,border-bottom-style,border-bottom-width,border-inline-end-style,border-inline-end-width,border-inline-start-style,border-inline-start-width,border-left-style,border-left-width,border-right-style,border-right-width,border-top-style,border-top-width,height,inline-size,perspective-origin,transform-origin,width,#rect-in-fg,#offset,#fg-size (29件; 例 1280/alpha/focus): background-color rgba(0, 0, 0, 0) -> rgb(255, 255, 255); block-size 16px -> 18px; border-block-end-style none -> solid; border-block-end-width 0px -> 1px; border-block-start-style none -> solid; border-block-start-width 0px -> 1px
- B topbar-search inner / form-group outer / range | background-color,block-size,border-block-end-style,border-block-end-width,border-block-start-style,border-block-start-width,border-bottom-style,border-bottom-width,border-inline-end-style,border-inline-end-width,border-inline-start-style,border-inline-start-width,border-left-style,border-left-width,border-right-style,border-right-width,border-top-style,border-top-width,height,perspective-origin,transform-origin,#rect-in-fg,#offset,#fg-size,#wrap-size (29件; 例 1280/alpha/focus): background-color rgba(0, 0, 0, 0) -> rgb(255, 255, 255); block-size 16px -> 18px; border-block-end-style none -> solid; border-block-end-width 0px -> 1px; border-block-start-style none -> solid; border-block-start-width 0px -> 1px
- B topbar-search outer / form-group inner / file | background-color,block-size,border-block-end-style,border-block-end-width,border-block-start-style,border-block-start-width,border-bottom-style,border-bottom-width,border-inline-end-style,border-inline-end-width,border-inline-start-style,border-inline-start-width,border-left-style,border-left-width,border-right-style,border-right-width,border-top-style,border-top-width,height,inline-size,perspective-origin,transform-origin,width,#rect-in-fg,#offset,#fg-size,#wrap-size (29件; 例 1280/alpha/focus): background-color rgba(0, 0, 0, 0) -> rgb(255, 255, 255); block-size 24px -> 26px; border-block-end-style none -> solid; border-block-end-width 0px -> 1px; border-block-start-style none -> solid; border-block-start-width 0px -> 1px
- B topbar-search inner / form-group outer / file | background-color,block-size,border-block-end-style,border-block-end-width,border-block-start-style,border-block-start-width,border-bottom-style,border-bottom-width,border-inline-end-style,border-inline-end-width,border-inline-start-style,border-inline-start-width,border-left-style,border-left-width,border-right-style,border-right-width,border-top-style,border-top-width,height,perspective-origin,transform-origin,#rect-in-fg,#offset,#fg-size,#wrap-size (29件; 例 1280/alpha/focus): background-color rgba(0, 0, 0, 0) -> rgb(255, 255, 255); block-size 24px -> 26px; border-block-end-style none -> solid; border-block-end-width 0px -> 1px; border-block-start-style none -> solid; border-block-start-width 0px -> 1px
- B topbar-search outer / form-group inner / range | background-color,border-block-end-color,border-block-end-style,border-block-end-width,border-block-start-color,border-block-start-style,border-block-start-width,border-bottom-color,border-bottom-style,border-bottom-width,border-inline-end-color,border-inline-end-style,border-inline-end-width,border-inline-start-color,border-inline-start-style,border-inline-start-width,border-left-color,border-left-style,border-left-width,border-right-color,border-right-style,border-right-width,border-top-color,border-top-style,border-top-width (2件; 例 375/company-forms.css last/normal): background-color rgba(0, 0, 0, 0) -> rgb(255, 255, 255); border-block-end-color rgb(26, 32, 44) -> rgb(226, 232, 240); border-block-end-style none -> solid; border-block-end-width 0px -> 1px; border-block-start-color rgb(26, 32, 44) -> rgb(226, 232, 240); border-block-start-style none -> solid
- B topbar-search inner / form-group outer / range | background-color,border-block-end-color,border-block-end-style,border-block-end-width,border-block-start-color,border-block-start-style,border-block-start-width,border-bottom-color,border-bottom-style,border-bottom-width,border-inline-end-color,border-inline-end-style,border-inline-end-width,border-inline-start-color,border-inline-start-style,border-inline-start-width,border-left-color,border-left-style,border-left-width,border-right-color,border-right-style,border-right-width,border-top-color,border-top-style,border-top-width (2件; 例 375/company-forms.css last/normal): background-color rgba(0, 0, 0, 0) -> rgb(255, 255, 255); border-block-end-color rgb(26, 32, 44) -> rgb(226, 232, 240); border-block-end-style none -> solid; border-block-end-width 0px -> 1px; border-block-start-color rgb(26, 32, 44) -> rgb(226, 232, 240); border-block-start-style none -> solid
- B topbar-search outer / form-group inner / file | background-color,border-block-end-color,border-block-end-style,border-block-end-width,border-block-start-color,border-block-start-style,border-block-start-width,border-bottom-color,border-bottom-style,border-bottom-width,border-inline-end-color,border-inline-end-style,border-inline-end-width,border-inline-start-color,border-inline-start-style,border-inline-start-width,border-left-color,border-left-style,border-left-width,border-right-color,border-right-style,border-right-width,border-top-color,border-top-style,border-top-width (2件; 例 375/company-forms.css last/normal): background-color rgba(0, 0, 0, 0) -> rgb(255, 255, 255); border-block-end-color rgb(26, 32, 44) -> rgb(226, 232, 240); border-block-end-style none -> solid; border-block-end-width 0px -> 1px; border-block-start-color rgb(26, 32, 44) -> rgb(226, 232, 240); border-block-start-style none -> solid
- B topbar-search inner / form-group outer / file | background-color,border-block-end-color,border-block-end-style,border-block-end-width,border-block-start-color,border-block-start-style,border-block-start-width,border-bottom-color,border-bottom-style,border-bottom-width,border-inline-end-color,border-inline-end-style,border-inline-end-width,border-inline-start-color,border-inline-start-style,border-inline-start-width,border-left-color,border-left-style,border-left-width,border-right-color,border-right-style,border-right-width,border-top-color,border-top-style,border-top-width (2件; 例 375/company-forms.css last/normal): background-color rgba(0, 0, 0, 0) -> rgb(255, 255, 255); border-block-end-color rgb(26, 32, 44) -> rgb(226, 232, 240); border-block-end-style none -> solid; border-block-end-width 0px -> 1px; border-block-start-color rgb(26, 32, 44) -> rgb(226, 232, 240); border-block-start-style none -> solid

## fixture 一覧

- A1 PriorityScoreOverride:81 range
- A2 ContactEditPage:171 checkbox
- A3 FedexEtdSetupGuide:509 file
- A4 FedexEtdSetupGuide:538 file
- A5 RolesPage:506 radio legacy
- A6 RolesPage:522 radio palette
- A7 RolesPage:562 checkbox
- A8 StaffEditPage:220 checkbox
- A9 StaffPage:293 checkbox
- B search-bar outer / form-group inner / checkbox
- B search-bar inner / form-group outer / checkbox
- B search-bar outer / form-group inner / radio
- B search-bar inner / form-group outer / radio
- B search-bar outer / form-group inner / range
- B search-bar inner / form-group outer / range
- B search-bar outer / form-group inner / file
- B search-bar inner / form-group outer / file
- B toggle-switch outer / form-group inner / checkbox
- B toggle-switch inner / form-group outer / checkbox
- B toggle-switch outer / form-group inner / radio
- B toggle-switch inner / form-group outer / radio
- B toggle-switch outer / form-group inner / range
- B toggle-switch inner / form-group outer / range
- B toggle-switch outer / form-group inner / file
- B toggle-switch inner / form-group outer / file
- B source-search outer / form-group inner / checkbox
- B source-search inner / form-group outer / checkbox
- B source-search outer / form-group inner / radio
- B source-search inner / form-group outer / radio
- B source-search outer / form-group inner / range
- B source-search inner / form-group outer / range
- B source-search outer / form-group inner / file
- B source-search inner / form-group outer / file
- B pmd-field outer / form-group inner / checkbox
- B pmd-field inner / form-group outer / checkbox
- B pmd-field outer / form-group inner / radio
- B pmd-field inner / form-group outer / radio
- B pmd-field outer / form-group inner / range
- B pmd-field inner / form-group outer / range
- B pmd-field outer / form-group inner / file
- B pmd-field inner / form-group outer / file
- B inbox-toggle outer / form-group inner / checkbox
- B inbox-toggle inner / form-group outer / checkbox
- B inbox-toggle outer / form-group inner / radio
- B inbox-toggle inner / form-group outer / radio
- B inbox-toggle outer / form-group inner / range
- B inbox-toggle inner / form-group outer / range
- B inbox-toggle outer / form-group inner / file
- B inbox-toggle inner / form-group outer / file
- B topbar-search outer / form-group inner / checkbox
- B topbar-search inner / form-group outer / checkbox
- B topbar-search outer / form-group inner / radio
- B topbar-search inner / form-group outer / radio
- B topbar-search outer / form-group inner / range
- B topbar-search inner / form-group outer / range
- B topbar-search outer / form-group inner / file
- B topbar-search inner / form-group outer / file
- B color-swatch outer / form-group inner / checkbox
- B color-swatch inner / form-group outer / checkbox
- B color-swatch outer / form-group inner / radio
- B color-swatch inner / form-group outer / radio
- B color-swatch outer / form-group inner / range
- B color-swatch inner / form-group outer / range
- B color-swatch outer / form-group inner / file
- B color-swatch inner / form-group outer / file
- B chk-label outer / form-group inner / checkbox
- B chk-label inner / form-group outer / checkbox
- B chk-label outer / form-group inner / radio
- B chk-label inner / form-group outer / radio
- B chk-label outer / form-group inner / range
- B chk-label inner / form-group outer / range
- B chk-label outer / form-group inner / file
- B chk-label inner / form-group outer / file
- B permission-item outer / form-group inner / checkbox
- B permission-item inner / form-group outer / checkbox
- B permission-item outer / form-group inner / radio
- B permission-item inner / form-group outer / radio
- B permission-item outer / form-group inner / range
- B permission-item inner / form-group outer / range
- B permission-item outer / form-group inner / file
- B permission-item inner / form-group outer / file
- B sales-form-option outer / form-group inner / checkbox
- B sales-form-option inner / form-group outer / checkbox
- B sales-form-option outer / form-group inner / radio
- B sales-form-option inner / form-group outer / radio
- B sales-form-option outer / form-group inner / range
- B sales-form-option inner / form-group outer / range
- B sales-form-option outer / form-group inner / file
- B sales-form-option inner / form-group outer / file
- B form-grid>form-row outer / form-group inner / checkbox
- B form-grid>form-row inner / form-group outer / checkbox
- B form-grid>form-row outer / form-group inner / radio
- B form-grid>form-row inner / form-group outer / radio
- B form-grid>form-row outer / form-group inner / range
- B form-grid>form-row inner / form-group outer / range
- B form-grid>form-row outer / form-group inner / file
- B form-grid>form-row inner / form-group outer / file
- B modal-content form-row outer / form-group inner / checkbox
- B modal-content form-row inner / form-group outer / checkbox
- B modal-content form-row outer / form-group inner / radio
- B modal-content form-row inner / form-group outer / radio
- B modal-content form-row outer / form-group inner / range
- B modal-content form-row inner / form-group outer / range
- B modal-content form-row outer / form-group inner / file
- B modal-content form-row inner / form-group outer / file
- B modal-content-wide form-row outer / form-group inner / checkbox
- B modal-content-wide form-row inner / form-group outer / checkbox
- B modal-content-wide form-row outer / form-group inner / radio
- B modal-content-wide form-row inner / form-group outer / radio
- B modal-content-wide form-row outer / form-group inner / range
- B modal-content-wide form-row inner / form-group outer / range
- B modal-content-wide form-row outer / form-group inner / file
- B modal-content-wide form-row inner / form-group outer / file

## B（仮想の組み合わせ）の差分の要約

B は「競合規則の祖先クラスと .form-group が同じ input の祖先に並ぶ」場合を全部作って測ったもの。実在するかは別（nontext-reach.md・nontext-ancestry.md で、実在するのは RolesPage の color-swatch ＋ form-group の 2 件だけで、これは A に含まれ差 0）。

| 祖先クラスの組み合わせ（outer/inner の2配置×4型） | 差の有無 | 差のある型 | 差の出る主な項目（例） |
|---|---|---|---|
| chk-label inner | なし | - | - |
| chk-label outer | なし | - | - |
| color-swatch inner | なし | - | - |
| color-swatch outer | なし | - | - |
| form-grid>form-row inner | なし | - | - |
| form-grid>form-row outer | なし | - | - |
| inbox-toggle inner | あり | checkbox, file, radio, range | inline-size 0px -> 1280px; perspective-origin 0px 0px -> 640px 0px; transform-origin 0px 0px -> 640px 0px; width 0px -> 1280px（1280/alpha/normal） |
| inbox-toggle outer | あり | checkbox, file, radio, range | inline-size 0px -> 13px; perspective-origin 0px 0px -> 6.5px 0px; transform-origin 0px 0px -> 6.5px 0px; width 0px -> 13px（1280/alpha/normal） |
| modal-content form-row inner | なし | - | - |
| modal-content form-row outer | なし | - | - |
| modal-content-wide form-row inner | なし | - | - |
| modal-content-wide form-row outer | なし | - | - |
| permission-item inner | なし | - | - |
| permission-item outer | なし | - | - |
| pmd-field inner | なし | - | - |
| pmd-field outer | なし | - | - |
| sales-form-option inner | なし | - | - |
| sales-form-option outer | なし | - | - |
| search-bar inner | なし | - | - |
| search-bar outer | なし | - | - |
| source-search inner | なし | - | - |
| source-search outer | なし | - | - |
| toggle-switch inner | あり | checkbox, file, radio, range | inline-size 0px -> 1280px; inset-inline-end 1280px -> 0px; perspective-origin 0px 0px -> 640px 0px; right 1280px -> 0px（1280/alpha/normal） |
| toggle-switch outer | なし | - | - |
| topbar-search inner | あり | checkbox, file, radio, range | background-color rgba(0, 0, 0, 0) -> rgb(255, 255, 255)（1280/alpha/normal） |
| topbar-search outer | あり | checkbox, file, radio, range | background-color rgba(0, 0, 0, 0) -> rgb(255, 255, 255)（1280/alpha/normal） |
