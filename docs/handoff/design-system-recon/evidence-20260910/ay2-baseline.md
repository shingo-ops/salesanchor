# ay2-baseline

Chromium 147.0.7727.15（headless shell）、viewport 1280x800 light。FormField.css appended last after all other CSS (same assumption as ax2-baseline)。

手法: ax2-baseline.cjs と同一。各 input を「祖先連鎖 + 実際に読み込まれる CSS + 自身の className/inline style」で再現して computed style を採取（before）。同じ祖先・同じ CSS・同じ type で className を `comp-field__input`（md）/ `comp-field__input comp-field__input--sm`（sm）に差し替えたものを after とした（inline style・既存 className は除去した「完全に標準にした」想定）。

測定対象: 件数5以下のグループは全メンバー、6件以上は先頭1件のみ。祖先連鎖が複数ある場合は最大20通り（variants）を全て測定。状態: normal / focus（常時）/ disabled（disabled属性があるメンバーのみ）。

生データ: ay2-baseline.json

## 金型単体（祖先なし、index.css + FormField.css のみ）

| type/size | offsetHeight | width | padding(T R B L) | border-width/style/color | radius | font-size | line-height | color | background | focus: border-color / box-shadow / outline | disabled: color / background / cursor / opacity |
|---|---|---|---|---|---|---|---|---|---|---|---|
| text/md | 40 | 1280px | 8px 12px 8px 12px | 1px solid rgb(226, 232, 240) | 6px | 14.4px | 21.6px | rgb(26, 32, 44) | rgb(255, 255, 255) | rgb(30, 58, 138) / rgba(30, 58, 138, 0.15) 0px 0px 0px 3px / none 3px rgb(26, 32, 44) | rgb(26, 32, 44) / rgb(226, 232, 240) / not-allowed / 0.5 |
| text/sm | 30 | 1280px | 4px 8px 4px 8px | 1px solid rgb(226, 232, 240) | 6px | 13.6px | 20.4px | rgb(26, 32, 44) | rgb(255, 255, 255) | rgb(30, 58, 138) / rgba(30, 58, 138, 0.15) 0px 0px 0px 3px / none 3px rgb(26, 32, 44) | rgb(26, 32, 44) / rgb(226, 232, 240) / not-allowed / 0.5 |
| text/lg | 50 | 1280px | 12px 16px 12px 16px | 1px solid rgb(226, 232, 240) | 6px | 16px | 24px | rgb(26, 32, 44) | rgb(255, 255, 255) | rgb(30, 58, 138) / rgba(30, 58, 138, 0.15) 0px 0px 0px 3px / none 3px rgb(26, 32, 44) | rgb(26, 32, 44) / rgb(226, 232, 240) / not-allowed / 0.5 |
| number/md | 40 | 1280px | 8px 12px 8px 12px | 1px solid rgb(226, 232, 240) | 6px | 14.4px | 21.6px | rgb(26, 32, 44) | rgb(255, 255, 255) | rgb(30, 58, 138) / rgba(30, 58, 138, 0.15) 0px 0px 0px 3px / none 3px rgb(26, 32, 44) | rgb(26, 32, 44) / rgb(226, 232, 240) / not-allowed / 0.5 |
| number/sm | 30 | 1280px | 4px 8px 4px 8px | 1px solid rgb(226, 232, 240) | 6px | 13.6px | 20.4px | rgb(26, 32, 44) | rgb(255, 255, 255) | rgb(30, 58, 138) / rgba(30, 58, 138, 0.15) 0px 0px 0px 3px / none 3px rgb(26, 32, 44) | rgb(26, 32, 44) / rgb(226, 232, 240) / not-allowed / 0.5 |
| number/lg | 50 | 1280px | 12px 16px 12px 16px | 1px solid rgb(226, 232, 240) | 6px | 16px | 24px | rgb(26, 32, 44) | rgb(255, 255, 255) | rgb(30, 58, 138) / rgba(30, 58, 138, 0.15) 0px 0px 0px 3px / none 3px rgb(26, 32, 44) | rgb(26, 32, 44) / rgb(226, 232, 240) / not-allowed / 0.5 |
| date/md | 42 | 1280px | 8px 12px 8px 12px | 1px solid rgb(226, 232, 240) | 6px | 14.4px | 21.6px | rgb(26, 32, 44) | rgb(255, 255, 255) | rgb(30, 58, 138) / rgba(30, 58, 138, 0.15) 0px 0px 0px 3px / none 3px rgb(26, 32, 44) | rgb(26, 32, 44) / rgb(226, 232, 240) / not-allowed / 0.5 |
| date/sm | 32 | 1280px | 4px 8px 4px 8px | 1px solid rgb(226, 232, 240) | 6px | 13.6px | 20.4px | rgb(26, 32, 44) | rgb(255, 255, 255) | rgb(30, 58, 138) / rgba(30, 58, 138, 0.15) 0px 0px 0px 3px / none 3px rgb(26, 32, 44) | rgb(26, 32, 44) / rgb(226, 232, 240) / not-allowed / 0.5 |
| date/lg | 52 | 1280px | 12px 16px 12px 16px | 1px solid rgb(226, 232, 240) | 6px | 16px | 24px | rgb(26, 32, 44) | rgb(255, 255, 255) | rgb(30, 58, 138) / rgba(30, 58, 138, 0.15) 0px 0px 0px 3px / none 3px rgb(26, 32, 44) | rgb(26, 32, 44) / rgb(226, 232, 240) / not-allowed / 0.5 |
| time/md | 42 | 1280px | 8px 12px 8px 12px | 1px solid rgb(226, 232, 240) | 6px | 14.4px | 21.6px | rgb(26, 32, 44) | rgb(255, 255, 255) | rgb(30, 58, 138) / rgba(30, 58, 138, 0.15) 0px 0px 0px 3px / none 3px rgb(26, 32, 44) | rgb(26, 32, 44) / rgb(226, 232, 240) / not-allowed / 0.5 |
| time/sm | 32 | 1280px | 4px 8px 4px 8px | 1px solid rgb(226, 232, 240) | 6px | 13.6px | 20.4px | rgb(26, 32, 44) | rgb(255, 255, 255) | rgb(30, 58, 138) / rgba(30, 58, 138, 0.15) 0px 0px 0px 3px / none 3px rgb(26, 32, 44) | rgb(26, 32, 44) / rgb(226, 232, 240) / not-allowed / 0.5 |
| time/lg | 52 | 1280px | 12px 16px 12px 16px | 1px solid rgb(226, 232, 240) | 6px | 16px | 24px | rgb(26, 32, 44) | rgb(255, 255, 255) | rgb(30, 58, 138) / rgba(30, 58, 138, 0.15) 0px 0px 0px 3px / none 3px rgb(26, 32, 44) | rgb(26, 32, 44) / rgb(226, 232, 240) / not-allowed / 0.5 |
| datetime-local/md | 42 | 1280px | 8px 12px 8px 12px | 1px solid rgb(226, 232, 240) | 6px | 14.4px | 21.6px | rgb(26, 32, 44) | rgb(255, 255, 255) | rgb(30, 58, 138) / rgba(30, 58, 138, 0.15) 0px 0px 0px 3px / none 3px rgb(26, 32, 44) | rgb(26, 32, 44) / rgb(226, 232, 240) / not-allowed / 0.5 |
| datetime-local/sm | 32 | 1280px | 4px 8px 4px 8px | 1px solid rgb(226, 232, 240) | 6px | 13.6px | 20.4px | rgb(26, 32, 44) | rgb(255, 255, 255) | rgb(30, 58, 138) / rgba(30, 58, 138, 0.15) 0px 0px 0px 3px / none 3px rgb(26, 32, 44) | rgb(26, 32, 44) / rgb(226, 232, 240) / not-allowed / 0.5 |
| datetime-local/lg | 52 | 1280px | 12px 16px 12px 16px | 1px solid rgb(226, 232, 240) | 6px | 16px | 24px | rgb(26, 32, 44) | rgb(255, 255, 255) | rgb(30, 58, 138) / rgba(30, 58, 138, 0.15) 0px 0px 0px 3px / none 3px rgb(26, 32, 44) | rgb(26, 32, 44) / rgb(226, 232, 240) / not-allowed / 0.5 |
| email/md | 40 | 1280px | 8px 12px 8px 12px | 1px solid rgb(226, 232, 240) | 6px | 14.4px | 21.6px | rgb(26, 32, 44) | rgb(255, 255, 255) | rgb(30, 58, 138) / rgba(30, 58, 138, 0.15) 0px 0px 0px 3px / none 3px rgb(26, 32, 44) | rgb(26, 32, 44) / rgb(226, 232, 240) / not-allowed / 0.5 |
| email/sm | 30 | 1280px | 4px 8px 4px 8px | 1px solid rgb(226, 232, 240) | 6px | 13.6px | 20.4px | rgb(26, 32, 44) | rgb(255, 255, 255) | rgb(30, 58, 138) / rgba(30, 58, 138, 0.15) 0px 0px 0px 3px / none 3px rgb(26, 32, 44) | rgb(26, 32, 44) / rgb(226, 232, 240) / not-allowed / 0.5 |
| email/lg | 50 | 1280px | 12px 16px 12px 16px | 1px solid rgb(226, 232, 240) | 6px | 16px | 24px | rgb(26, 32, 44) | rgb(255, 255, 255) | rgb(30, 58, 138) / rgba(30, 58, 138, 0.15) 0px 0px 0px 3px / none 3px rgb(26, 32, 44) | rgb(26, 32, 44) / rgb(226, 232, 240) / not-allowed / 0.5 |
| password/md | 40 | 1280px | 8px 12px 8px 12px | 1px solid rgb(226, 232, 240) | 6px | 14.4px | 21.6px | rgb(26, 32, 44) | rgb(255, 255, 255) | rgb(30, 58, 138) / rgba(30, 58, 138, 0.15) 0px 0px 0px 3px / none 3px rgb(26, 32, 44) | rgb(26, 32, 44) / rgb(226, 232, 240) / not-allowed / 0.5 |
| password/sm | 30 | 1280px | 4px 8px 4px 8px | 1px solid rgb(226, 232, 240) | 6px | 13.6px | 20.4px | rgb(26, 32, 44) | rgb(255, 255, 255) | rgb(30, 58, 138) / rgba(30, 58, 138, 0.15) 0px 0px 0px 3px / none 3px rgb(26, 32, 44) | rgb(26, 32, 44) / rgb(226, 232, 240) / not-allowed / 0.5 |
| password/lg | 50 | 1280px | 12px 16px 12px 16px | 1px solid rgb(226, 232, 240) | 6px | 16px | 24px | rgb(26, 32, 44) | rgb(255, 255, 255) | rgb(30, 58, 138) / rgba(30, 58, 138, 0.15) 0px 0px 0px 3px / none 3px rgb(26, 32, 44) | rgb(26, 32, 44) / rgb(226, 232, 240) / not-allowed / 0.5 |
| tel/md | 40 | 1280px | 8px 12px 8px 12px | 1px solid rgb(226, 232, 240) | 6px | 14.4px | 21.6px | rgb(26, 32, 44) | rgb(255, 255, 255) | rgb(30, 58, 138) / rgba(30, 58, 138, 0.15) 0px 0px 0px 3px / none 3px rgb(26, 32, 44) | rgb(26, 32, 44) / rgb(226, 232, 240) / not-allowed / 0.5 |
| tel/sm | 30 | 1280px | 4px 8px 4px 8px | 1px solid rgb(226, 232, 240) | 6px | 13.6px | 20.4px | rgb(26, 32, 44) | rgb(255, 255, 255) | rgb(30, 58, 138) / rgba(30, 58, 138, 0.15) 0px 0px 0px 3px / none 3px rgb(26, 32, 44) | rgb(26, 32, 44) / rgb(226, 232, 240) / not-allowed / 0.5 |
| tel/lg | 50 | 1280px | 12px 16px 12px 16px | 1px solid rgb(226, 232, 240) | 6px | 16px | 24px | rgb(26, 32, 44) | rgb(255, 255, 255) | rgb(30, 58, 138) / rgba(30, 58, 138, 0.15) 0px 0px 0px 3px / none 3px rgb(26, 32, 44) | rgb(26, 32, 44) / rgb(226, 232, 240) / not-allowed / 0.5 |
| url/md | 40 | 1280px | 8px 12px 8px 12px | 1px solid rgb(226, 232, 240) | 6px | 14.4px | 21.6px | rgb(26, 32, 44) | rgb(255, 255, 255) | rgb(30, 58, 138) / rgba(30, 58, 138, 0.15) 0px 0px 0px 3px / none 3px rgb(26, 32, 44) | rgb(26, 32, 44) / rgb(226, 232, 240) / not-allowed / 0.5 |
| url/sm | 30 | 1280px | 4px 8px 4px 8px | 1px solid rgb(226, 232, 240) | 6px | 13.6px | 20.4px | rgb(26, 32, 44) | rgb(255, 255, 255) | rgb(30, 58, 138) / rgba(30, 58, 138, 0.15) 0px 0px 0px 3px / none 3px rgb(26, 32, 44) | rgb(26, 32, 44) / rgb(226, 232, 240) / not-allowed / 0.5 |
| url/lg | 50 | 1280px | 12px 16px 12px 16px | 1px solid rgb(226, 232, 240) | 6px | 16px | 24px | rgb(26, 32, 44) | rgb(255, 255, 255) | rgb(30, 58, 138) / rgba(30, 58, 138, 0.15) 0px 0px 0px 3px / none 3px rgb(26, 32, 44) | rgb(26, 32, 44) / rgb(226, 232, 240) / not-allowed / 0.5 |
| search/md | 40 | 1280px | 8px 12px 8px 12px | 1px solid rgb(226, 232, 240) | 6px | 14.4px | 21.6px | rgb(26, 32, 44) | rgb(255, 255, 255) | rgb(30, 58, 138) / rgba(30, 58, 138, 0.15) 0px 0px 0px 3px / none 3px rgb(26, 32, 44) | rgb(26, 32, 44) / rgb(226, 232, 240) / not-allowed / 0.5 |
| search/sm | 30 | 1280px | 4px 8px 4px 8px | 1px solid rgb(226, 232, 240) | 6px | 13.6px | 20.4px | rgb(26, 32, 44) | rgb(255, 255, 255) | rgb(30, 58, 138) / rgba(30, 58, 138, 0.15) 0px 0px 0px 3px / none 3px rgb(26, 32, 44) | rgb(26, 32, 44) / rgb(226, 232, 240) / not-allowed / 0.5 |
| search/lg | 50 | 1280px | 12px 16px 12px 16px | 1px solid rgb(226, 232, 240) | 6px | 16px | 24px | rgb(26, 32, 44) | rgb(255, 255, 255) | rgb(30, 58, 138) / rgba(30, 58, 138, 0.15) 0px 0px 0px 3px / none 3px rgb(26, 32, 44) | rgb(26, 32, 44) / rgb(226, 232, 240) / not-allowed / 0.5 |
| omitted/md | 40 | 1280px | 8px 12px 8px 12px | 1px solid rgb(226, 232, 240) | 6px | 14.4px | 21.6px | rgb(26, 32, 44) | rgb(255, 255, 255) | rgb(30, 58, 138) / rgba(30, 58, 138, 0.15) 0px 0px 0px 3px / none 3px rgb(26, 32, 44) | rgb(26, 32, 44) / rgb(226, 232, 240) / not-allowed / 0.5 |
| omitted/sm | 30 | 1280px | 4px 8px 4px 8px | 1px solid rgb(226, 232, 240) | 6px | 13.6px | 20.4px | rgb(26, 32, 44) | rgb(255, 255, 255) | rgb(30, 58, 138) / rgba(30, 58, 138, 0.15) 0px 0px 0px 3px / none 3px rgb(26, 32, 44) | rgb(26, 32, 44) / rgb(226, 232, 240) / not-allowed / 0.5 |
| omitted/lg | 50 | 1280px | 12px 16px 12px 16px | 1px solid rgb(226, 232, 240) | 6px | 16px | 24px | rgb(26, 32, 44) | rgb(255, 255, 255) | rgb(30, 58, 138) / rgba(30, 58, 138, 0.15) 0px 0px 0px 3px / none 3px rgb(26, 32, 44) | rgb(26, 32, 44) / rgb(226, 232, 240) / not-allowed / 0.5 |

## グループ別: 標準（TextFieldControl md/sm）にした場合に変わるもの

表の読み方: 「before」= 現状、「md」「sm」= 標準化後。同じ値の行は省略（差分のみ）。

### G01（136 件、測定 1 件＝先頭のみ）

- 適用規則: `components.css:19 .form-group input` / `components.css:30 .form-group input:focus`
- inline style: なし

#### components/ChannelTypeCombobox.tsx:91  type=text  祖先連鎖 6 通り  disabled属性あり

- 祖先(variant0, 内側から): `div < div < div.form-group < form < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `なし` / own class: `input`

[normal] 差分 5 項目

| property | before | md | sm |
|---|---|---|---|
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 21.6px |
| height | 34px | 39.6094px | 39.6094px |
| offsetHeight | 34 | 40 | 40 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 5 項目

| property | before | md | sm |
|---|---|---|---|
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 21.6px |
| height | 34px | 39.6094px | 39.6094px |
| offsetHeight | 34 | 40 | 40 |
| min-height | 0px | 0px (=) | 28px |

[disabled] 差分 8 項目

| property | before | md | sm |
|---|---|---|---|
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 21.6px |
| background-color | rgb(255, 255, 255) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| height | 34px | 39.6094px | 39.6094px |
| cursor | default | not-allowed | not-allowed |
| opacity | 1 | 0.5 | 0.5 |
| offsetHeight | 34 | 40 | 40 |
| min-height | 0px | 0px (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: 
- variant1: before差=width,offsetWidth / md差=width,offsetWidth
- variant3: before差=width,offsetWidth / md差=width,offsetWidth
- variant4: before差=width,offsetWidth / md差=width,offsetWidth
- variant5: before差=width,offsetWidth / md差=width,offsetWidth

### G02（61 件、測定 1 件＝先頭のみ）

- 適用規則: (なし)
- inline style: なし

#### components/master-list-editor/MasterListEditor.tsx:157  type=omitted  祖先連鎖 1 通り

- 祖先(variant0, 内側から): `form < div < div.product-masters-tab`  未解決: no JSX usage found for ProductMastersTab (frontend/src/pages/super-admin/ProductMastersTab.tsx)
- 反映した inline: `なし` / own class: `なし`

[normal] 差分 30 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 149px | 1280px | 1280px |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 149 | 1280 | 1280 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 33 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 149px | 1280px | 1280px |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 149 | 1280 | 1280 |
| min-height | 0px | 0px (=) | 28px |

### G03（32 件、測定 1 件＝先頭のみ）

- 適用規則: `company-forms.css:100 .form-grid > .form-row input:not([type="checkbox"]):not([type="radio"])` / `company-forms.css:113 .form-grid > .form-row input:focus` / `company-forms.css:147 .modal-content-wide .form-row input:not([type="checkbox"]):not([type="radio"])` / `company-forms.css:163 .modal-content-wide .form-row input:focus`
- inline style: なし

#### pages/companies/CompaniesPage.tsx:452  type=omitted  祖先連鎖 4 通り

- 祖先(variant0, 内側から): `div.form-row < form.form-grid < div.modal-content-wide < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell < main.mobile-content < div.mobile-shell`
- 反映した inline: `なし` / own class: `なし`

[normal] 差分 4 項目

| property | before | md | sm |
|---|---|---|---|
| line-height | normal | 21.6px | 21.6px |
| height | 35px | 39.6094px | 39.6094px |
| offsetHeight | 35 | 40 | 40 |
| min-height | auto | auto (=) | 28px |

[focus] 差分 4 項目

| property | before | md | sm |
|---|---|---|---|
| line-height | normal | 21.6px | 21.6px |
| height | 35px | 39.6094px | 39.6094px |
| offsetHeight | 35 | 40 | 40 |
| min-height | auto | auto (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: なし（全 4 通りで同一）

### G04（22 件、測定 1 件＝先頭のみ）

- 適用規則: `pages/inbox/InboxPage.css:1160 .right-panel-field` / `pages/inbox/InboxPage.css:1168 .right-panel-field::placeholder` / `pages/inbox/InboxPage.css:1169 .right-panel-field:focus`
- inline style: なし

#### pages/inbox/InboxKartePanel.tsx:372  type=text  祖先連鎖 2 通り

- 祖先(variant0, 内側から): `div.right-panel-row < div.right-panel-section < div.right-panel-tab-content < div.right-panel-card < aside.inbox-right-panel < div.inbox-wrapper < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `なし` / own class: `right-panel-field`

[normal] 差分 14 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 7px | 8px | 4px |
| padding-right | 9px | 12px | 8px |
| padding-bottom | 7px | 8px | 4px |
| padding-left | 9px | 12px | 8px |
| border-top-color | rgb(221, 224, 228) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(221, 224, 228) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(221, 224, 228) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(221, 224, 228) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| font-size | 13.6px | 14.4px | 13.6px (=) |
| line-height | normal | 21.6px | 20.4px |
| background-color | rgb(250, 251, 252) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 31px | 39.6094px | 30.3906px |
| offsetHeight | 31 | 40 | 30 |
| min-height | auto | auto (=) | 28px |

[focus] 差分 11 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 7px | 8px | 4px |
| padding-right | 9px | 12px | 8px |
| padding-bottom | 7px | 8px | 4px |
| padding-left | 9px | 12px | 8px |
| font-size | 13.6px | 14.4px | 13.6px (=) |
| line-height | normal | 21.6px | 20.4px |
| background-color | rgb(250, 251, 252) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 31px | 39.6094px | 30.3906px |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 31 | 40 | 30 |
| min-height | auto | auto (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: なし（全 2 通りで同一）

### G05（16 件、測定 1 件＝先頭のみ）

- 適用規則: `company-forms.css:100 .form-grid > .form-row input:not([type="checkbox"]):not([type="radio"])` / `company-forms.css:113 .form-grid > .form-row input:focus`
- inline style: なし

#### pages/company-detail/CompanyBasicTab.tsx:38  type=omitted  祖先連鎖 4 通り  disabled属性あり

- 祖先(variant0, 内側から): `div.form-row < form.form-grid < div < div.page-layout < div.page-container-detail < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell < main.mobile-content < div.mobile-shell`
- 反映した inline: `なし` / own class: `なし`

[normal] 差分 4 項目

| property | before | md | sm |
|---|---|---|---|
| line-height | normal | 21.6px | 21.6px |
| height | 35px | 39.6094px | 39.6094px |
| offsetHeight | 35 | 40 | 40 |
| min-height | auto | auto (=) | 28px |

[focus] 差分 4 項目

| property | before | md | sm |
|---|---|---|---|
| line-height | normal | 21.6px | 21.6px |
| height | 35px | 39.6094px | 39.6094px |
| offsetHeight | 35 | 40 | 40 |
| min-height | auto | auto (=) | 28px |

[disabled] 差分 6 項目

| property | before | md | sm |
|---|---|---|---|
| line-height | normal | 21.6px | 21.6px |
| height | 35px | 39.6094px | 39.6094px |
| cursor | default | not-allowed | not-allowed |
| opacity | 1 | 0.5 | 0.5 |
| offsetHeight | 35 | 40 | 40 |
| min-height | auto | auto (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: 
- variant1: before差=width,offsetWidth / md差=width,offsetWidth
- variant2: before差=width,offsetWidth / md差=width,offsetWidth
- variant3: before差=width,offsetWidth / md差=width,offsetWidth

### G06（14 件、測定 1 件＝先頭のみ）

- 適用規則: `company-forms.css:238 .product-edit-form .form-group input:not([type="checkbox"]):not([type="radio"])` / `components.css:19 .form-group input` / `components.css:30 .form-group input:focus`
- inline style: なし

#### pages/products/ProductEditPage.tsx:215  type=omitted  祖先連鎖 2 通り

- 祖先(variant0, 内側から): `div.form-group.form-group-full < form.product-edit-form < div.page.page--full < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `なし` / own class: `なし`

[normal] 差分 5 項目

| property | before | md | sm |
|---|---|---|---|
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 21.6px |
| height | 34px | 39.6094px | 39.6094px |
| offsetHeight | 34 | 40 | 40 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 5 項目

| property | before | md | sm |
|---|---|---|---|
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 21.6px |
| height | 34px | 39.6094px | 39.6094px |
| offsetHeight | 34 | 40 | 40 |
| min-height | 0px | 0px (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: 
- variant1: before差=width,offsetWidth / md差=width,offsetWidth

### G07（7 件、測定 1 件＝先頭のみ）

- 適用規則: `features/tcg-analysis-review/supplier-detail-view.css:244 .pmd-field input`
- inline style: なし

#### features/tcg-analysis-review/ProductMasterDrawer.tsx:68  type=omitted  祖先連鎖 3 通り

- 祖先(variant0, 内側から): `label.pmd-field < div.pmd-fields < div.pmd-body < aside.pmd-drawer < div.analysis-panel-content < div.hub-content < div.hub-shell < div < div.page-layout`  未解決: depth limit
- 反映した inline: `なし` / own class: `なし`

[normal] 差分 3 項目

| property | before | md | sm |
|---|---|---|---|
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| min-height | auto | auto (=) | 28px |

[focus] 差分 10 項目

| property | before | md | sm |
|---|---|---|---|
| border-top-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| min-height | auto | auto (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: なし（全 3 通りで同一）

### G08（6 件、測定 1 件＝先頭のみ）

- 適用規則: `pages/schedule.css:813 .schedule-input` / `pages/schedule.css:822 .schedule-input` / `pages/schedule.css:827 .schedule-input:focus`
- inline style: なし

#### pages/schedule/SchedulePageImpl.tsx:280  type=omitted  祖先連鎖 2 通り

- 祖先(variant0, 内側から): `label.schedule-field < div.schedule-popover__body.schedule-popover__body--form < div.schedule-popover < div.schedule-page < main.mobile-content < div.mobile-shell`
- 反映した inline: `なし` / own class: `schedule-input`

[normal] 差分 10 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-bottom | 0px | 8px | 4px |
| font-size | 13.6px | 14.4px | 13.6px (=) |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| height | 28px | 39.6094px | 30.3906px |
| min-height | 28px | auto | 28px (=) |
| offsetHeight | 28 | 40 | 30 |
| padding-right | 12px | 12px (=) | 8px |
| padding-left | 12px | 12px (=) | 8px |

[focus] 差分 10 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-bottom | 0px | 8px | 4px |
| font-size | 13.6px | 14.4px | 13.6px (=) |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| height | 28px | 39.6094px | 30.3906px |
| min-height | 28px | auto | 28px (=) |
| offsetHeight | 28 | 40 | 30 |
| padding-right | 12px | 12px (=) | 8px |
| padding-left | 12px | 12px (=) | 8px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: なし（全 2 通りで同一）

### G09（6 件、測定 1 件＝先頭のみ）

- 適用規則: (なし)
- inline style: `style{width:var(--input-width-weight)}`

#### pages/invoice-create/InvoiceCreatePage.tsx:367  type=omitted  祖先連鎖 2 通り

- 祖先(variant0, 内側から): `td < tr < tbody < table.data-table < div < form < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `width:var(--input-width-weight)` / own class: `なし`

[normal] 差分 30 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 80px | 1248px | 1248px |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 80 | 1248 | 1248 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 33 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 80px | 1248px | 1248px |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 80 | 1248 | 1248 |
| min-height | 0px | 0px (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: 
- variant1: before差=- / md差=width,offsetWidth

### G10（4 件、測定 4 件＝全メンバー）

- 適用規則: (なし)
- inline style: `style{flex:1}`

#### pages/register/RegisterAddressPage.tsx:344  type=tel  祖先連鎖 1 通り

- 祖先(variant0, 内側から): `div < div < fieldset < form < div.page-container`
- 反映した inline: `flex:1` / own class: `input`

[normal] 差分 32 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 149px | 1132px | 1132px |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| flex-grow | 1 | 0 | 0 |
| flex-basis | 0% | auto | auto |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 149 | 1132 | 1132 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 35 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 149px | 1132px | 1132px |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| flex-grow | 1 | 0 | 0 |
| flex-basis | 0% | auto | auto |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 149 | 1132 | 1132 |
| min-height | 0px | 0px (=) | 28px |

#### pages/register/RegisterChangeBillingPage.tsx:284  type=tel  祖先連鎖 1 通り

- 祖先(variant0, 内側から): `div < div < fieldset < form < div.page-container`
- 反映した inline: `flex:1` / own class: `input`

[normal] 差分 32 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 149px | 1132px | 1132px |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| flex-grow | 1 | 0 | 0 |
| flex-basis | 0% | auto | auto |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 149 | 1132 | 1132 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 35 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 149px | 1132px | 1132px |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| flex-grow | 1 | 0 | 0 |
| flex-basis | 0% | auto | auto |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 149 | 1132 | 1132 |
| min-height | 0px | 0px (=) | 28px |

#### pages/register/RegisterPage.tsx:337  type=tel  祖先連鎖 1 通り

- 祖先(variant0, 内側から): `div < div < fieldset < form < div.page-container`
- 反映した inline: `flex:1` / own class: `input`

[normal] 差分 32 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 149px | 1132px | 1132px |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| flex-grow | 1 | 0 | 0 |
| flex-basis | 0% | auto | auto |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 149 | 1132 | 1132 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 35 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 149px | 1132px | 1132px |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| flex-grow | 1 | 0 | 0 |
| flex-basis | 0% | auto | auto |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 149 | 1132 | 1132 |
| min-height | 0px | 0px (=) | 28px |

#### pages/register/RegisterPage.tsx:596  type=tel  祖先連鎖 1 通り

- 祖先(variant0, 内側から): `div < div < fieldset < form < div.page-container`
- 反映した inline: `flex:1` / own class: `input`

[normal] 差分 32 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 149px | 1132px | 1132px |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| flex-grow | 1 | 0 | 0 |
| flex-basis | 0% | auto | auto |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 149 | 1132 | 1132 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 35 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 149px | 1132px | 1132px |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| flex-grow | 1 | 0 | 0 |
| flex-basis | 0% | auto | auto |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 149 | 1132 | 1132 |
| min-height | 0px | 0px (=) | 28px |

### G11（3 件、測定 3 件＝全メンバー）

- 適用規則: `components.css:19 .form-group input` / `components.css:30 .form-group input:focus` / `pages-layout.css:246 .login-card .form-group input` / `pages-layout.css:255 .login-card .form-group input:focus`
- inline style: なし

#### pages/login/LoginPage.tsx:93  type=email  祖先連鎖 1 通り

- 祖先(variant0, 内側から): `div.form-group < form < div.login-card < div.login-page`
- 反映した inline: `なし` / own class: `なし`

[normal] 差分 5 項目

| property | before | md | sm |
|---|---|---|---|
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 24px | 24px |
| height | 44px | 50px | 50px |
| offsetHeight | 44 | 50 | 50 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 5 項目

| property | before | md | sm |
|---|---|---|---|
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 24px | 24px |
| height | 44px | 50px | 50px |
| offsetHeight | 44 | 50 | 50 |
| min-height | 0px | 0px (=) | 28px |

#### pages/login/LoginPage.tsx:104  type=password  祖先連鎖 1 通り

- 祖先(variant0, 内側から): `div.form-group < form < div.login-card < div.login-page`
- 反映した inline: `なし` / own class: `なし`

[normal] 差分 5 項目

| property | before | md | sm |
|---|---|---|---|
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 24px | 24px |
| height | 44px | 50px | 50px |
| offsetHeight | 44 | 50 | 50 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 5 項目

| property | before | md | sm |
|---|---|---|---|
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 24px | 24px |
| height | 44px | 50px | 50px |
| offsetHeight | 44 | 50 | 50 |
| min-height | 0px | 0px (=) | 28px |

#### pages/login/LoginPage.tsx:136  type=email  祖先連鎖 1 通り

- 祖先(variant0, 内側から): `div.form-group < form < div.login-card < div.login-page`
- 反映した inline: `なし` / own class: `なし`

[normal] 差分 5 項目

| property | before | md | sm |
|---|---|---|---|
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 24px | 24px |
| height | 44px | 50px | 50px |
| offsetHeight | 44 | 50 | 50 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 5 項目

| property | before | md | sm |
|---|---|---|---|
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 24px | 24px |
| height | 44px | 50px | 50px |
| offsetHeight | 44 | 50 | 50 |
| min-height | 0px | 0px (=) | 28px |

### G12（3 件、測定 3 件＝全メンバー）

- 適用規則: `components/field-size.css:15 .field-w-md` / `components/field-size.css:22 .content-toolbar .field-w-md` / `components/field-size.css:8 .field-h-md`
- inline style: なし

#### pages/companies/CompaniesPage.tsx:386  type=text  祖先連鎖 4 通り

- 祖先(variant0, 内側から): `div.content-toolbar__left < div.content-toolbar < div < div.page-layout < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell < main.mobile-content < div.mobile-shell`
- 反映した inline: `なし` / own class: `search-input field-h-md field-w-md`

[normal] 差分 30 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 36px | 39.6094px | 30.3906px |
| min-height | 36px | auto | 28px |
| width | 280px | 192px | 167px |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| offsetHeight | 36 | 40 | 30 |
| offsetWidth | 280 | 192 | 167 |

[focus] 差分 33 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 36px | 39.6094px | 30.3906px |
| min-height | 36px | auto | 28px |
| width | 280px | 192px | 167px |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 36 | 40 | 30 |
| offsetWidth | 280 | 192 | 167 |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: なし（全 4 通りで同一）

#### pages/inventory/InventoryPage.tsx:384  type=search  祖先連鎖 2 通り

- 祖先(variant0, 内側から): `div.content-toolbar__left < div.content-toolbar < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `なし` / own class: `field-h-md field-w-md`

[normal] 差分 30 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 36px | 39.6094px | 30.3906px |
| min-height | 36px | auto | 28px |
| width | 280px | 192px | 167px |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| offsetHeight | 36 | 40 | 30 |
| offsetWidth | 280 | 192 | 167 |

[focus] 差分 33 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 36px | 39.6094px | 30.3906px |
| min-height | 36px | auto | 28px |
| width | 280px | 192px | 167px |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 36 | 40 | 30 |
| offsetWidth | 280 | 192 | 167 |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: なし（全 2 通りで同一）

#### pages/orders/OrdersFilterBar.tsx:32  type=search  祖先連鎖 2 通り

- 祖先(variant0, 内側から): `div < div.content-toolbar__left < div.content-toolbar < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `なし` / own class: `field-h-md field-w-md`

[normal] 差分 30 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 36px | 39.6094px | 30.3906px |
| min-height | 36px | 0px | 28px |
| width | 280px | 1280px | 1280px |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| offsetHeight | 36 | 40 | 30 |
| offsetWidth | 280 | 1280 | 1280 |

[focus] 差分 33 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 36px | 39.6094px | 30.3906px |
| min-height | 36px | 0px | 28px |
| width | 280px | 1280px | 1280px |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 36 | 40 | 30 |
| offsetWidth | 280 | 1280 | 1280 |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: 
- variant1: before差=- / md差=width,offsetWidth

### G13（3 件、測定 3 件＝全メンバー）

- 適用規則: `features/tcg-distribution/distribution.css:322 .dist-input` / `features/tcg-distribution/distribution.css:334 .dist-input:focus` / `features/tcg-distribution/distribution.css:340 .dist-input--error ?conditional-class`
- inline style: なし

#### features/tcg-distribution/DistributionTargetForm.tsx:182  type=text  祖先連鎖 10 通り

- 祖先(variant0, 内側から): `div.dist-field < div.dist-drawer-body < aside.dist-drawer < div < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `なし` / own class: `dist-input`

[normal] 差分 9 項目

| property | before | md | sm |
|---|---|---|---|
| font-size | 13.6px | 14.4px | 13.6px (=) |
| line-height | 21.76px | 21.6px | 20.4px |
| height | 39.75px | 39.6094px | 30.3906px |
| padding-top | 8px | 8px (=) | 4px |
| padding-right | 12px | 12px (=) | 8px |
| padding-bottom | 8px | 8px (=) | 4px |
| padding-left | 12px | 12px (=) | 8px |
| min-height | auto | auto (=) | 28px |
| offsetHeight | 40 | 40 (=) | 30 |

[focus] 差分 14 項目

| property | before | md | sm |
|---|---|---|---|
| font-size | 13.6px | 14.4px | 13.6px (=) |
| line-height | 21.76px | 21.6px | 20.4px |
| height | 39.75px | 39.6094px | 30.3906px |
| outline-style | solid | none | none |
| outline-width | 2px | 3px | 3px |
| outline-color | rgb(30, 58, 138) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| outline-offset | -1px | 0px | 0px |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| padding-top | 8px | 8px (=) | 4px |
| padding-right | 12px | 12px (=) | 8px |
| padding-bottom | 8px | 8px (=) | 4px |
| padding-left | 12px | 12px (=) | 8px |
| min-height | auto | auto (=) | 28px |
| offsetHeight | 40 | 40 (=) | 30 |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: なし（全 10 通りで同一）

#### features/tcg-distribution/DistributionTargetForm.tsx:199  type=text  祖先連鎖 10 通り

- 祖先(variant0, 内側から): `div.dist-field < div.dist-drawer-body < aside.dist-drawer < div < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `なし` / own class: `dist-input`

[normal] 差分 9 項目

| property | before | md | sm |
|---|---|---|---|
| font-size | 13.6px | 14.4px | 13.6px (=) |
| line-height | 21.76px | 21.6px | 20.4px |
| height | 39.75px | 39.6094px | 30.3906px |
| padding-top | 8px | 8px (=) | 4px |
| padding-right | 12px | 12px (=) | 8px |
| padding-bottom | 8px | 8px (=) | 4px |
| padding-left | 12px | 12px (=) | 8px |
| min-height | auto | auto (=) | 28px |
| offsetHeight | 40 | 40 (=) | 30 |

[focus] 差分 14 項目

| property | before | md | sm |
|---|---|---|---|
| font-size | 13.6px | 14.4px | 13.6px (=) |
| line-height | 21.76px | 21.6px | 20.4px |
| height | 39.75px | 39.6094px | 30.3906px |
| outline-style | solid | none | none |
| outline-width | 2px | 3px | 3px |
| outline-color | rgb(30, 58, 138) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| outline-offset | -1px | 0px | 0px |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| padding-top | 8px | 8px (=) | 4px |
| padding-right | 12px | 12px (=) | 8px |
| padding-bottom | 8px | 8px (=) | 4px |
| padding-left | 12px | 12px (=) | 8px |
| min-height | auto | auto (=) | 28px |
| offsetHeight | 40 | 40 (=) | 30 |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: なし（全 10 通りで同一）

#### features/tcg-distribution/DistributionTargetForm.tsx:223  type=text  祖先連鎖 10 通り

- 祖先(variant0, 内側から): `div.dist-field < div.dist-drawer-body < aside.dist-drawer < div < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `なし` / own class: `dist-input`

[normal] 差分 9 項目

| property | before | md | sm |
|---|---|---|---|
| font-size | 13.6px | 14.4px | 13.6px (=) |
| line-height | 21.76px | 21.6px | 20.4px |
| height | 39.75px | 39.6094px | 30.3906px |
| padding-top | 8px | 8px (=) | 4px |
| padding-right | 12px | 12px (=) | 8px |
| padding-bottom | 8px | 8px (=) | 4px |
| padding-left | 12px | 12px (=) | 8px |
| min-height | auto | auto (=) | 28px |
| offsetHeight | 40 | 40 (=) | 30 |

[focus] 差分 14 項目

| property | before | md | sm |
|---|---|---|---|
| font-size | 13.6px | 14.4px | 13.6px (=) |
| line-height | 21.76px | 21.6px | 20.4px |
| height | 39.75px | 39.6094px | 30.3906px |
| outline-style | solid | none | none |
| outline-width | 2px | 3px | 3px |
| outline-color | rgb(30, 58, 138) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| outline-offset | -1px | 0px | 0px |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| padding-top | 8px | 8px (=) | 4px |
| padding-right | 12px | 12px (=) | 8px |
| padding-bottom | 8px | 8px (=) | 4px |
| padding-left | 12px | 12px (=) | 8px |
| min-height | auto | auto (=) | 28px |
| offsetHeight | 40 | 40 (=) | 30 |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: なし（全 10 通りで同一）

### G14（2 件、測定 2 件＝全メンバー）

- 適用規則: `components.css:50 .search-bar input` / `components/field-size.css:13 .field-w-sm` / `components/field-size.css:22 .content-toolbar .field-w-sm` / `components/field-size.css:8 .field-h-md`
- inline style: なし

#### components/master-list-editor/MasterListEditor.tsx:135  type=text  祖先連鎖 1 通り

- 祖先(variant0, 内側から): `form.search-bar < div.content-toolbar__left < div.content-toolbar < div < div.product-masters-tab`  未解決: no JSX usage found for ProductMastersTab (frontend/src/pages/super-admin/ProductMastersTab.tsx)
- 反映した inline: `なし` / own class: `field-h-md field-w-sm`

[normal] 差分 5 項目

| property | before | md | sm |
|---|---|---|---|
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 21.6px |
| height | 36px | 39.6094px | 39.6094px |
| min-height | 36px | 0px | 28px |
| offsetHeight | 36 | 40 | 40 |

[focus] 差分 13 項目

| property | before | md | sm |
|---|---|---|---|
| border-top-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 21.6px |
| height | 36px | 39.6094px | 39.6094px |
| min-height | 36px | 0px | 28px |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 36 | 40 | 40 |

#### pages/products/ProductsPage.tsx:219  type=text  祖先連鎖 2 通り

- 祖先(variant0, 内側から): `div.search-bar < div.content-toolbar__left < div.content-toolbar < main.mobile-content < div.mobile-shell`
- 反映した inline: `なし` / own class: `field-h-md field-w-sm`

[normal] 差分 5 項目

| property | before | md | sm |
|---|---|---|---|
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 21.6px |
| height | 36px | 39.6094px | 39.6094px |
| min-height | 36px | 0px | 28px |
| offsetHeight | 36 | 40 | 40 |

[focus] 差分 13 項目

| property | before | md | sm |
|---|---|---|---|
| border-top-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 21.6px |
| height | 36px | 39.6094px | 39.6094px |
| min-height | 36px | 0px | 28px |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 36 | 40 | 40 |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: なし（全 2 通りで同一）

### G15（2 件、測定 2 件＝全メンバー）

- 適用規則: `pages/dashboard/WeeklyAdvisorSection.css:205 .db-weekly-composer-input` / `pages/dashboard/WeeklyAdvisorSection.css:216 .db-weekly-composer-input:focus`
- inline style: なし

#### pages/dashboard/PriorityProspectsSection.tsx:424  type=date  祖先連鎖 2 通り

- 祖先(variant0, 内側から): `div.db-weekly-composer-field < div.db-weekly-composer < li.db-priority-item < ul.db-priority-list < div.db-section-card.db-priority-card < div.db-content-stack < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `なし` / own class: `db-weekly-composer-input`

[normal] 差分 23 項目

| property | before | md | sm |
|---|---|---|---|
| border-top-width | 0px | 1px | 1px |
| border-right-width | 0px | 1px | 1px |
| border-bottom-width | 0px | 1px | 1px |
| border-left-width | 0px | 1px | 1px |
| border-top-style | none | solid | solid |
| border-right-style | none | solid | solid |
| border-bottom-style | none | solid | solid |
| border-left-style | none | solid | solid |
| border-top-color | rgb(26, 32, 44) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(26, 32, 44) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(26, 32, 44) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(26, 32, 44) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| font-size | 16px | 14.4px | 13.6px |
| line-height | 25.6px | 21.6px | 20.4px |
| background-color | rgb(245, 247, 250) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 43.5938px | 41.6094px | 32.3906px |
| resize | vertical | none | none |
| offsetHeight | 44 | 42 | 32 |
| padding-top | 8px | 8px (=) | 4px |
| padding-right | 12px | 12px (=) | 8px |
| padding-bottom | 8px | 8px (=) | 4px |
| padding-left | 12px | 12px (=) | 8px |
| min-height | auto | auto (=) | 28px |

[focus] 差分 28 項目

| property | before | md | sm |
|---|---|---|---|
| border-top-width | 0px | 1px | 1px |
| border-right-width | 0px | 1px | 1px |
| border-bottom-width | 0px | 1px | 1px |
| border-left-width | 0px | 1px | 1px |
| border-top-style | none | solid | solid |
| border-right-style | none | solid | solid |
| border-bottom-style | none | solid | solid |
| border-left-style | none | solid | solid |
| border-top-color | rgb(26, 32, 44) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(26, 32, 44) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(26, 32, 44) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(26, 32, 44) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| font-size | 16px | 14.4px | 13.6px |
| line-height | 25.6px | 21.6px | 20.4px |
| background-color | rgb(245, 247, 250) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 43.5938px | 41.6094px | 32.3906px |
| resize | vertical | none | none |
| outline-style | solid | none | none |
| outline-width | 2px | 3px | 3px |
| outline-color | rgb(30, 58, 138) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| outline-offset | 1px | 0px | 0px |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 44 | 42 | 32 |
| padding-top | 8px | 8px (=) | 4px |
| padding-right | 12px | 12px (=) | 8px |
| padding-bottom | 8px | 8px (=) | 4px |
| padding-left | 12px | 12px (=) | 8px |
| min-height | auto | auto (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: 
- variant1: before差=width,offsetWidth / md差=width,offsetWidth

#### pages/dashboard/WeeklyAdvisorSection.tsx:395  type=date  祖先連鎖 2 通り

- 祖先(variant0, 内側から): `div.db-weekly-composer-field < div.db-weekly-composer < li.db-weekly-item < ul.db-weekly-list < div.db-section-card.db-weekly-card < div.db-content-stack < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `なし` / own class: `db-weekly-composer-input`

[normal] 差分 23 項目

| property | before | md | sm |
|---|---|---|---|
| border-top-width | 0px | 1px | 1px |
| border-right-width | 0px | 1px | 1px |
| border-bottom-width | 0px | 1px | 1px |
| border-left-width | 0px | 1px | 1px |
| border-top-style | none | solid | solid |
| border-right-style | none | solid | solid |
| border-bottom-style | none | solid | solid |
| border-left-style | none | solid | solid |
| border-top-color | rgb(26, 32, 44) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(26, 32, 44) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(26, 32, 44) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(26, 32, 44) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| font-size | 16px | 14.4px | 13.6px |
| line-height | 25.6px | 21.6px | 20.4px |
| background-color | rgb(245, 247, 250) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 43.5938px | 41.6094px | 32.3906px |
| resize | vertical | none | none |
| offsetHeight | 44 | 42 | 32 |
| padding-top | 8px | 8px (=) | 4px |
| padding-right | 12px | 12px (=) | 8px |
| padding-bottom | 8px | 8px (=) | 4px |
| padding-left | 12px | 12px (=) | 8px |
| min-height | auto | auto (=) | 28px |

[focus] 差分 28 項目

| property | before | md | sm |
|---|---|---|---|
| border-top-width | 0px | 1px | 1px |
| border-right-width | 0px | 1px | 1px |
| border-bottom-width | 0px | 1px | 1px |
| border-left-width | 0px | 1px | 1px |
| border-top-style | none | solid | solid |
| border-right-style | none | solid | solid |
| border-bottom-style | none | solid | solid |
| border-left-style | none | solid | solid |
| border-top-color | rgb(26, 32, 44) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(26, 32, 44) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(26, 32, 44) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(26, 32, 44) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| font-size | 16px | 14.4px | 13.6px |
| line-height | 25.6px | 21.6px | 20.4px |
| background-color | rgb(245, 247, 250) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 43.5938px | 41.6094px | 32.3906px |
| resize | vertical | none | none |
| outline-style | solid | none | none |
| outline-width | 2px | 3px | 3px |
| outline-color | rgb(30, 58, 138) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| outline-offset | 1px | 0px | 0px |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 44 | 42 | 32 |
| padding-top | 8px | 8px (=) | 4px |
| padding-right | 12px | 12px (=) | 8px |
| padding-bottom | 8px | 8px (=) | 4px |
| padding-left | 12px | 12px (=) | 8px |
| min-height | auto | auto (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: 
- variant1: before差=width,offsetWidth / md差=width,offsetWidth

### G16（2 件、測定 2 件＝全メンバー）

- 適用規則: (なし)
- inline style: `style{background:var(--bg-primary);border-radius:4px;border:1px solid var(--border-color);color:var(--text-primary);font-size:0.85rem;min-width:200px;padding:0.4rem 0.6rem}`

#### pages/super-admin/TcgLineImportPage.tsx:374  type=text  祖先連鎖 2 通り

- 祖先(variant0, 内側から): `label < div < section < details < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `padding:0.4rem 0.6rem;border:1px solid var(--border-color);border-radius:4px;font-size:0.85rem;min-width:200px;background:var(--bg-primary);color:var(--text-primary)` / own class: `なし`

[normal] 差分 22 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 6.4px | 8px | 4px |
| padding-right | 9.6px | 12px | 8px |
| padding-bottom | 6.4px | 8px | 4px |
| padding-left | 9.6px | 12px | 8px |
| border-top-color | rgb(204, 204, 204) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(204, 204, 204) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(204, 204, 204) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(204, 204, 204) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-top-left-radius | 4px | 6px | 6px |
| border-top-right-radius | 4px | 6px | 6px |
| border-bottom-right-radius | 4px | 6px | 6px |
| border-bottom-left-radius | 4px | 6px | 6px |
| font-size | 13.6px | 14.4px | 13.6px (=) |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| background-color | rgb(245, 247, 250) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 0px | 39.6094px | 30.3906px |
| width | 200px | 1280px | 1280px |
| min-width | 200px | 0px | 0px |
| offsetHeight | 30 | 40 | 30 (=) |
| offsetWidth | 200 | 1280 | 1280 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 22 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 6.4px | 8px | 4px |
| padding-right | 9.6px | 12px | 8px |
| padding-bottom | 6.4px | 8px | 4px |
| padding-left | 9.6px | 12px | 8px |
| border-top-color | rgb(204, 204, 204) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(204, 204, 204) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(204, 204, 204) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(204, 204, 204) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-top-left-radius | 4px | 6px | 6px |
| border-top-right-radius | 4px | 6px | 6px |
| border-bottom-right-radius | 4px | 6px | 6px |
| border-bottom-left-radius | 4px | 6px | 6px |
| font-size | 13.6px | 14.4px | 13.6px (=) |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| background-color | rgb(245, 247, 250) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 29.7812px | 39.6094px | 30.3906px |
| width | 200px | 1280px | 1280px |
| min-width | 200px | 0px | 0px |
| offsetHeight | 30 | 40 | 30 (=) |
| offsetWidth | 200 | 1280 | 1280 |
| min-height | 0px | 0px (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: 
- variant1: before差=height / md差=width,offsetWidth

#### pages/super-admin/TcgLineImportPage.tsx:395  type=text  祖先連鎖 2 通り

- 祖先(variant0, 内側から): `label < div < section < details < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `padding:0.4rem 0.6rem;border:1px solid var(--border-color);border-radius:4px;font-size:0.85rem;min-width:200px;background:var(--bg-primary);color:var(--text-primary)` / own class: `なし`

[normal] 差分 22 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 6.4px | 8px | 4px |
| padding-right | 9.6px | 12px | 8px |
| padding-bottom | 6.4px | 8px | 4px |
| padding-left | 9.6px | 12px | 8px |
| border-top-color | rgb(204, 204, 204) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(204, 204, 204) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(204, 204, 204) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(204, 204, 204) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-top-left-radius | 4px | 6px | 6px |
| border-top-right-radius | 4px | 6px | 6px |
| border-bottom-right-radius | 4px | 6px | 6px |
| border-bottom-left-radius | 4px | 6px | 6px |
| font-size | 13.6px | 14.4px | 13.6px (=) |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| background-color | rgb(245, 247, 250) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 29.7812px | 39.6094px | 30.3906px |
| width | 200px | 1280px | 1280px |
| min-width | 200px | 0px | 0px |
| offsetHeight | 30 | 40 | 30 (=) |
| offsetWidth | 200 | 1280 | 1280 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 22 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 6.4px | 8px | 4px |
| padding-right | 9.6px | 12px | 8px |
| padding-bottom | 6.4px | 8px | 4px |
| padding-left | 9.6px | 12px | 8px |
| border-top-color | rgb(204, 204, 204) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(204, 204, 204) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(204, 204, 204) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(204, 204, 204) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-top-left-radius | 4px | 6px | 6px |
| border-top-right-radius | 4px | 6px | 6px |
| border-bottom-right-radius | 4px | 6px | 6px |
| border-bottom-left-radius | 4px | 6px | 6px |
| font-size | 13.6px | 14.4px | 13.6px (=) |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| background-color | rgb(245, 247, 250) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 29.7812px | 39.6094px | 30.3906px |
| width | 200px | 1280px | 1280px |
| min-width | 200px | 0px | 0px |
| offsetHeight | 30 | 40 | 30 (=) |
| offsetWidth | 200 | 1280 | 1280 |
| min-height | 0px | 0px (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: 
- variant1: before差=- / md差=width,offsetWidth

### G17（2 件、測定 2 件＝全メンバー）

- 適用規則: (なし)
- inline style: `style{border-radius:4px;border:1px solid var(--border);font-size:13px;padding:6px 8px;width:80px}`

#### components/FedExRateModal.tsx:176  type=text  祖先連鎖 2 通り

- 祖先(variant0, 内側から): `div < div < div < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `width:80px;padding:6px 8px;border:1px solid var(--border);border-radius:4px;font-size:13px` / own class: `なし`

[normal] 差分 18 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 6px | 8px | 4px |
| padding-right | 8px | 12px | 8px (=) |
| padding-bottom | 6px | 8px | 4px |
| padding-left | 8px | 12px | 8px (=) |
| border-top-left-radius | 4px | 6px | 6px |
| border-top-right-radius | 4px | 6px | 6px |
| border-bottom-right-radius | 4px | 6px | 6px |
| border-bottom-left-radius | 4px | 6px | 6px |
| font-size | 13px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 29px | 39.6094px | 30.3906px |
| width | 80px | 1200px | 1200px |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| offsetHeight | 29 | 40 | 30 |
| offsetWidth | 80 | 1200 | 1200 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 25 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 6px | 8px | 4px |
| padding-right | 8px | 12px | 8px (=) |
| padding-bottom | 6px | 8px | 4px |
| padding-left | 8px | 12px | 8px (=) |
| border-top-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-top-left-radius | 4px | 6px | 6px |
| border-top-right-radius | 4px | 6px | 6px |
| border-bottom-right-radius | 4px | 6px | 6px |
| border-bottom-left-radius | 4px | 6px | 6px |
| font-size | 13px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 29px | 39.6094px | 30.3906px |
| width | 80px | 1200px | 1200px |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 29 | 40 | 30 |
| offsetWidth | 80 | 1200 | 1200 |
| min-height | 0px | 0px (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: なし（全 2 通りで同一）

#### components/FedExRateModal.tsx:193  type=text  祖先連鎖 2 通り

- 祖先(variant0, 内側から): `div < div < div < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `width:80px;padding:6px 8px;border:1px solid var(--border);border-radius:4px;font-size:13px` / own class: `なし`

[normal] 差分 18 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 6px | 8px | 4px |
| padding-right | 8px | 12px | 8px (=) |
| padding-bottom | 6px | 8px | 4px |
| padding-left | 8px | 12px | 8px (=) |
| border-top-left-radius | 4px | 6px | 6px |
| border-top-right-radius | 4px | 6px | 6px |
| border-bottom-right-radius | 4px | 6px | 6px |
| border-bottom-left-radius | 4px | 6px | 6px |
| font-size | 13px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 29px | 39.6094px | 30.3906px |
| width | 80px | 1200px | 1200px |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| offsetHeight | 29 | 40 | 30 |
| offsetWidth | 80 | 1200 | 1200 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 25 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 6px | 8px | 4px |
| padding-right | 8px | 12px | 8px (=) |
| padding-bottom | 6px | 8px | 4px |
| padding-left | 8px | 12px | 8px (=) |
| border-top-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-top-left-radius | 4px | 6px | 6px |
| border-top-right-radius | 4px | 6px | 6px |
| border-bottom-right-radius | 4px | 6px | 6px |
| border-bottom-left-radius | 4px | 6px | 6px |
| font-size | 13px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 29px | 39.6094px | 30.3906px |
| width | 80px | 1200px | 1200px |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 29 | 40 | 30 |
| offsetWidth | 80 | 1200 | 1200 |
| min-height | 0px | 0px (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: なし（全 2 通りで同一）

### G18（2 件、測定 2 件＝全メンバー）

- 適用規則: (なし)
- inline style: `style{color:var(--text-secondary);font-size:var(--font-sm);margin-top:var(--space-1);min-width:var(--input-width-product-name);width:100%}`

#### pages/invoice-create/InvoiceCreatePage.tsx:349  type=omitted  祖先連鎖 2 通り

- 祖先(variant0, 内側から): `td < tr < tbody < table.data-table < div < form < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `width:100%;min-width:var(--input-width-product-name);margin-top:var(--space-1);font-size:var(--font-sm);color:var(--text-secondary)` / own class: `なし`

[normal] 差分 30 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.6px | 14.4px | 13.6px (=) |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(74, 85, 104) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| outline-color | rgb(74, 85, 104) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| min-width | 280px | 0px | 0px |
| margin-top | 4px | 0px | 0px |
| offsetHeight | 19 | 40 | 30 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 33 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.6px | 14.4px | 13.6px (=) |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(74, 85, 104) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| min-width | 280px | 0px | 0px |
| margin-top | 4px | 0px | 0px |
| offsetHeight | 19 | 40 | 30 |
| min-height | 0px | 0px (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: 
- variant1: before差=width,offsetWidth / md差=width,offsetWidth

#### pages/quote-create/QuoteCreatePage.tsx:198  type=omitted  祖先連鎖 2 通り

- 祖先(variant0, 内側から): `td < tr < tbody < table.data-table < div < form < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `width:100%;min-width:var(--input-width-product-name);margin-top:var(--space-1);font-size:var(--font-sm);color:var(--text-secondary)` / own class: `なし`

[normal] 差分 30 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.6px | 14.4px | 13.6px (=) |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(74, 85, 104) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| outline-color | rgb(74, 85, 104) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| min-width | 280px | 0px | 0px |
| margin-top | 4px | 0px | 0px |
| offsetHeight | 19 | 40 | 30 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 33 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.6px | 14.4px | 13.6px (=) |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(74, 85, 104) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| min-width | 280px | 0px | 0px |
| margin-top | 4px | 0px | 0px |
| offsetHeight | 19 | 40 | 30 |
| min-height | 0px | 0px (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: 
- variant1: before差=width,offsetWidth / md差=width,offsetWidth

### G19（2 件、測定 2 件＝全メンバー）

- 適用規則: (なし)
- inline style: `style{font-weight:var(--font-weight-semi);min-width:var(--input-width-product-name);width:100%}`

#### pages/invoice-create/InvoiceCreatePage.tsx:342  type=omitted  祖先連鎖 2 通り

- 祖先(variant0, 内側から): `td < tr < tbody < table.data-table < div < form < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `width:100%;min-width:var(--input-width-product-name);font-weight:var(--font-weight-semi)` / own class: `なし`

[normal] 差分 29 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| min-width | 280px | 0px | 0px |
| offsetHeight | 19 | 40 | 30 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 32 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| min-width | 280px | 0px | 0px |
| offsetHeight | 19 | 40 | 30 |
| min-height | 0px | 0px (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: 
- variant1: before差=width,offsetWidth / md差=width,offsetWidth

#### pages/quote-create/QuoteCreatePage.tsx:191  type=omitted  祖先連鎖 2 通り

- 祖先(variant0, 内側から): `td < tr < tbody < table.data-table < div < form < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `width:100%;min-width:var(--input-width-product-name);font-weight:var(--font-weight-semi)` / own class: `なし`

[normal] 差分 29 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| min-width | 280px | 0px | 0px |
| offsetHeight | 19 | 40 | 30 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 32 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| min-width | 280px | 0px | 0px |
| offsetHeight | 19 | 40 | 30 |
| min-height | 0px | 0px (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: 
- variant1: before差=width,offsetWidth / md差=width,offsetWidth

### G20（2 件、測定 2 件＝全メンバー）

- 適用規則: (なし)
- inline style: `style{margin-left:var(--space-2);width:var(--input-width-month)}`

#### pages/commission-settings/CommissionSettingsPage.tsx:287  type=number  祖先連鎖 6 通り

- 祖先(variant0, 内側から): `label < div < fieldset < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `width:var(--input-width-month);margin-left:var(--space-2)` / own class: `なし`

[normal] 差分 31 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 60px | 1276px | 1276px |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| margin-left | 8px | 0px | 0px |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 60 | 1276 | 1276 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 34 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 60px | 1276px | 1276px |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| margin-left | 8px | 0px | 0px |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 60 | 1276 | 1276 |
| min-height | 0px | 0px (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: 
- variant1: before差=- / md差=width,offsetWidth
- variant3: before差=- / md差=width,offsetWidth
- variant4: before差=- / md差=width,offsetWidth
- variant5: before差=- / md差=width,offsetWidth

#### pages/commissions/CommissionsPage.tsx:153  type=number  祖先連鎖 2 通り

- 祖先(variant0, 内側から): `label < div < div.comp-card < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `width:var(--input-width-month);margin-left:var(--space-2)` / own class: `なし`

[normal] 差分 31 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 60px | 1232px | 1232px |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| margin-left | 8px | 0px | 0px |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 60 | 1232 | 1232 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 34 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 60px | 1232px | 1232px |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| margin-left | 8px | 0px | 0px |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 60 | 1232 | 1232 |
| min-height | 0px | 0px (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: 
- variant1: before差=- / md差=width,offsetWidth

### G21（2 件、測定 2 件＝全メンバー）

- 適用規則: (なし)
- inline style: `style{margin-left:var(--space-2);width:var(--input-width-year)}`

#### pages/commission-settings/CommissionSettingsPage.tsx:275  type=number  祖先連鎖 6 通り

- 祖先(variant0, 内側から): `label < div < fieldset < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `width:var(--input-width-year);margin-left:var(--space-2)` / own class: `なし`

[normal] 差分 31 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 90px | 1276px | 1276px |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| margin-left | 8px | 0px | 0px |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 90 | 1276 | 1276 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 34 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 90px | 1276px | 1276px |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| margin-left | 8px | 0px | 0px |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 90 | 1276 | 1276 |
| min-height | 0px | 0px (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: 
- variant1: before差=- / md差=width,offsetWidth
- variant3: before差=- / md差=width,offsetWidth
- variant4: before差=- / md差=width,offsetWidth
- variant5: before差=- / md差=width,offsetWidth

#### pages/commissions/CommissionsPage.tsx:141  type=number  祖先連鎖 2 通り

- 祖先(variant0, 内側から): `label < div < div.comp-card < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `width:var(--input-width-year);margin-left:var(--space-2)` / own class: `なし`

[normal] 差分 31 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 90px | 1232px | 1232px |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| margin-left | 8px | 0px | 0px |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 90 | 1232 | 1232 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 34 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 90px | 1232px | 1232px |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| margin-left | 8px | 0px | 0px |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 90 | 1232 | 1232 |
| min-height | 0px | 0px (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: 
- variant1: before差=- / md差=width,offsetWidth

### G22（2 件、測定 2 件＝全メンバー）

- 適用規則: (なし)
- inline style: `style{max-width:100%;width:SEARCH_WIDTH}`

#### pages/super-admin/KnowledgeAliasesTab.tsx:295  type=omitted  祖先連鎖 2 通り

- 祖先(variant0, 内側から): `div < section < div.super-admin-knowledge-tab < div.analysis-panel-content < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `width:SEARCH_WIDTH;max-width:100%` / own class: `なし`

[normal] 差分 31 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 149px | 1232px | 1232px |
| max-width | 100% | none | none |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 149 | 1232 | 1232 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 34 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 149px | 1232px | 1232px |
| max-width | 100% | none | none |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 149 | 1232 | 1232 |
| min-height | 0px | 0px (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: 
- variant1: before差=- / md差=width,offsetWidth

#### pages/super-admin/KnowledgeAliasesTab.tsx:374  type=omitted  祖先連鎖 2 通り

- 祖先(variant0, 内側から): `div < section < div.super-admin-knowledge-tab < div.analysis-panel-content < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `width:SEARCH_WIDTH;max-width:100%` / own class: `なし`

[normal] 差分 31 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 149px | 1232px | 1232px |
| max-width | 100% | none | none |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 149 | 1232 | 1232 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 34 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 149px | 1232px | 1232px |
| max-width | 100% | none | none |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 149 | 1232 | 1232 |
| min-height | 0px | 0px (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: 
- variant1: before差=- / md差=width,offsetWidth

### G23（2 件、測定 2 件＝全メンバー）

- 適用規則: (なし)
- inline style: `style{width:6rem}`

#### pages/inventory/InventoryFilterPanel.tsx:287  type=number  祖先連鎖 2 通り

- 祖先(variant0, 内側から): `div < div < div < section.inventory-filter-panel < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `width:6rem` / own class: `なし`

[normal] 差分 30 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 96px | 1280px | 1280px |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 96 | 1280 | 1280 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 33 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 96px | 1280px | 1280px |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 96 | 1280 | 1280 |
| min-height | 0px | 0px (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: 
- variant1: before差=- / md差=width,offsetWidth

#### pages/inventory/InventoryFilterPanel.tsx:290  type=number  祖先連鎖 2 通り

- 祖先(variant0, 内側から): `div < div < div < section.inventory-filter-panel < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `width:6rem` / own class: `なし`

[normal] 差分 30 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 96px | 1280px | 1280px |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 96 | 1280 | 1280 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 33 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 96px | 1280px | 1280px |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 96 | 1280 | 1280 |
| min-height | 0px | 0px (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: 
- variant1: before差=- / md差=width,offsetWidth

### G24（2 件、測定 2 件＝全メンバー）

- 適用規則: (なし)
- inline style: `style{width:7rem}`

#### pages/inventory/InventoryFilterPanel.tsx:295  type=number  祖先連鎖 2 通り

- 祖先(variant0, 内側から): `div < div < div < section.inventory-filter-panel < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `width:7rem` / own class: `なし`

[normal] 差分 30 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 112px | 1280px | 1280px |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 112 | 1280 | 1280 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 33 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 112px | 1280px | 1280px |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 112 | 1280 | 1280 |
| min-height | 0px | 0px (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: 
- variant1: before差=- / md差=width,offsetWidth

#### pages/inventory/InventoryFilterPanel.tsx:298  type=number  祖先連鎖 2 通り

- 祖先(variant0, 内側から): `div < div < div < section.inventory-filter-panel < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `width:7rem` / own class: `なし`

[normal] 差分 30 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 112px | 1280px | 1280px |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 112 | 1280 | 1280 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 33 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 112px | 1280px | 1280px |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 112 | 1280 | 1280 |
| min-height | 0px | 0px (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: 
- variant1: before差=- / md差=width,offsetWidth

### G25（2 件、測定 2 件＝全メンバー）

- 適用規則: (なし)
- inline style: `style{width:var(--input-width-qty)}`

#### pages/invoice-create/InvoiceCreatePage.tsx:384  type=number  祖先連鎖 2 通り

- 祖先(variant0, 内側から): `td < tr < tbody < table.data-table < div < form < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `width:var(--input-width-qty)` / own class: `なし`

[normal] 差分 30 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 70px | 1248px | 1248px |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 70 | 1248 | 1248 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 33 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 70px | 1248px | 1248px |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 70 | 1248 | 1248 |
| min-height | 0px | 0px (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: 
- variant1: before差=- / md差=width,offsetWidth

#### pages/quote-create/QuoteCreatePage.tsx:233  type=number  祖先連鎖 2 通り

- 祖先(variant0, 内側から): `td < tr < tbody < table.data-table < div < form < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `width:var(--input-width-qty)` / own class: `なし`

[normal] 差分 30 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 70px | 1248px | 1248px |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 70 | 1248 | 1248 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 33 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 70px | 1248px | 1248px |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 70 | 1248 | 1248 |
| min-height | 0px | 0px (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: 
- variant1: before差=- / md差=width,offsetWidth

### G26（2 件、測定 2 件＝全メンバー）

- 適用規則: (なし)
- inline style: `style{width:var(--input-width-year)}`

#### pages/invoice-create/InvoiceCreatePage.tsx:387  type=number  祖先連鎖 2 通り

- 祖先(variant0, 内側から): `td < tr < tbody < table.data-table < div < form < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `width:var(--input-width-year)` / own class: `なし`

[normal] 差分 30 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 90px | 1248px | 1248px |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 90 | 1248 | 1248 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 33 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 90px | 1248px | 1248px |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 90 | 1248 | 1248 |
| min-height | 0px | 0px (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: 
- variant1: before差=- / md差=width,offsetWidth

#### pages/quote-create/QuoteCreatePage.tsx:236  type=number  祖先連鎖 2 通り

- 祖先(variant0, 内側から): `td < tr < tbody < table.data-table < div < form < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `width:var(--input-width-year)` / own class: `なし`

[normal] 差分 30 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 90px | 1248px | 1248px |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 90 | 1248 | 1248 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 33 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 90px | 1248px | 1248px |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 90 | 1248 | 1248 |
| min-height | 0px | 0px (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: 
- variant1: before差=- / md差=width,offsetWidth

### G27（1 件、測定 1 件＝全メンバー）

- 適用規則: `company-forms.css:147 .modal-content-wide .form-row input:not([type="checkbox"]):not([type="radio"])` / `company-forms.css:163 .modal-content-wide .form-row input:focus`
- inline style: なし

#### components/MergeLeadModal.tsx:146  type=text  祖先連鎖 4 通り

- 祖先(variant0, 内側から): `div.form-row < div.modal-content-wide < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell < main.mobile-content < div.mobile-shell`
- 反映した inline: `なし` / own class: `なし`

[normal] 差分 4 項目

| property | before | md | sm |
|---|---|---|---|
| line-height | normal | 21.6px | 21.6px |
| height | 35px | 39.6094px | 39.6094px |
| offsetHeight | 35 | 40 | 40 |
| min-height | auto | auto (=) | 28px |

[focus] 差分 4 項目

| property | before | md | sm |
|---|---|---|---|
| line-height | normal | 21.6px | 21.6px |
| height | 35px | 39.6094px | 39.6094px |
| offsetHeight | 35 | 40 | 40 |
| min-height | auto | auto (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: なし（全 4 通りで同一）

### G28（1 件、測定 1 件＝全メンバー）

- 適用規則: `components.css:19 .form-group input` / `components.css:30 .form-group input:focus`
- inline style: `style{min-width:var(--min-width-input-sm);padding:var(--space-6px) var(--space-2);width:100%}`

#### components/InventoryPicker.tsx:217  type=text  祖先連鎖 6 通り  disabled属性あり

- 祖先(variant0, 内側から): `div.inventory-picker < td < tr < tbody < table.data-table < div.form-group < form < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `width:100%;min-width:var(--min-width-input-sm);padding:var(--space-6px) var(--space-2)` / own class: `なし`

[normal] 差分 10 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 6px | 8px | 8px |
| padding-right | 8px | 12px | 12px |
| padding-bottom | 6px | 8px | 8px |
| padding-left | 8px | 12px | 12px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 21.6px |
| height | 30px | 39.6094px | 39.6094px |
| min-width | 120px | 0px | 0px |
| offsetHeight | 30 | 40 | 40 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 10 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 6px | 8px | 8px |
| padding-right | 8px | 12px | 12px |
| padding-bottom | 6px | 8px | 8px |
| padding-left | 8px | 12px | 12px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 21.6px |
| height | 30px | 39.6094px | 39.6094px |
| min-width | 120px | 0px | 0px |
| offsetHeight | 30 | 40 | 40 |
| min-height | 0px | 0px (=) | 28px |

[disabled] 差分 13 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 6px | 8px | 8px |
| padding-right | 8px | 12px | 12px |
| padding-bottom | 6px | 8px | 8px |
| padding-left | 8px | 12px | 12px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 21.6px |
| background-color | rgb(255, 255, 255) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| height | 30px | 39.6094px | 39.6094px |
| cursor | default | not-allowed | not-allowed |
| opacity | 1 | 0.5 | 0.5 |
| min-width | 120px | 0px | 0px |
| offsetHeight | 30 | 40 | 40 |
| min-height | 0px | 0px (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: 
- variant1: before差=width,offsetWidth / md差=width,offsetWidth
- variant3: before差=width,offsetWidth / md差=width,offsetWidth
- variant4: before差=width,offsetWidth / md差=width,offsetWidth
- variant5: before差=width,offsetWidth / md差=width,offsetWidth

### G29（1 件、測定 1 件＝全メンバー）

- 適用規則: `components.css:19 .form-group input` / `components.css:30 .form-group input:focus`
- inline style: `style{min-width:var(--min-width-input-sm)}`

#### pages/purchase-orders/PurchaseOrdersFormModal.tsx:191  type=omitted  祖先連鎖 6 通り

- 祖先(variant0, 内側から): `td < tr < tbody < table.data-table < div.form-group < form < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `min-width:var(--min-width-input-sm)` / own class: `なし`

[normal] 差分 6 項目

| property | before | md | sm |
|---|---|---|---|
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 21.6px |
| height | 34px | 39.6094px | 39.6094px |
| min-width | 120px | 0px | 0px |
| offsetHeight | 34 | 40 | 40 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 6 項目

| property | before | md | sm |
|---|---|---|---|
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 21.6px |
| height | 34px | 39.6094px | 39.6094px |
| min-width | 120px | 0px | 0px |
| offsetHeight | 34 | 40 | 40 |
| min-height | 0px | 0px (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: なし（全 6 通りで同一）

### G30（1 件、測定 1 件＝全メンバー）

- 適用規則: `components.css:19 .form-group input` / `components.css:30 .form-group input:focus`
- inline style: `style{width:var(--input-width-qty)}`

#### pages/purchase-orders/PurchaseOrdersFormModal.tsx:194  type=number  祖先連鎖 6 通り

- 祖先(variant0, 内側から): `td < tr < tbody < table.data-table < div.form-group < form < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `width:var(--input-width-qty)` / own class: `なし`

[normal] 差分 7 項目

| property | before | md | sm |
|---|---|---|---|
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 21.6px |
| height | 34px | 39.6094px | 39.6094px |
| width | 70px | 1168px | 1168px |
| offsetHeight | 34 | 40 | 40 |
| offsetWidth | 70 | 1168 | 1168 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 7 項目

| property | before | md | sm |
|---|---|---|---|
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 21.6px |
| height | 34px | 39.6094px | 39.6094px |
| width | 70px | 1168px | 1168px |
| offsetHeight | 34 | 40 | 40 |
| offsetWidth | 70 | 1168 | 1168 |
| min-height | 0px | 0px (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: なし（全 6 通りで同一）

### G31（1 件、測定 1 件＝全メンバー）

- 適用規則: `components.css:19 .form-group input` / `components.css:30 .form-group input:focus`
- inline style: `style{width:var(--input-width-year)}`

#### pages/purchase-orders/PurchaseOrdersFormModal.tsx:197  type=number  祖先連鎖 6 通り

- 祖先(variant0, 内側から): `td < tr < tbody < table.data-table < div.form-group < form < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `width:var(--input-width-year)` / own class: `なし`

[normal] 差分 7 項目

| property | before | md | sm |
|---|---|---|---|
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 21.6px |
| height | 34px | 39.6094px | 39.6094px |
| width | 90px | 1168px | 1168px |
| offsetHeight | 34 | 40 | 40 |
| offsetWidth | 90 | 1168 | 1168 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 7 項目

| property | before | md | sm |
|---|---|---|---|
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 21.6px |
| height | 34px | 39.6094px | 39.6094px |
| width | 90px | 1168px | 1168px |
| offsetHeight | 34 | 40 | 40 |
| offsetWidth | 90 | 1168 | 1168 |
| min-height | 0px | 0px (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: なし（全 6 通りで同一）

### G32（1 件、測定 1 件＝全メンバー）

- 適用規則: `components.css:67 .search-input-field` / `components.css:77 .search-input-field::placeholder` / `components.css:80 .search-input-field:focus` / `pages/inbox/InboxPage.css:116 .inbox-search-input`
- inline style: なし

#### pages/inbox/InboxConversationList.tsx:62  type=text  祖先連鎖 2 通り

- 祖先(variant0, 内側から): `div.inbox-search-wrap < div.inbox-search-row < aside.inbox-left-panel < div.inbox-columns < div.inbox-main-area < div.inbox-wrapper < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `なし` / own class: `search-input-field inbox-search-input`

[normal] 差分 15 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 9.5px | 8px | 4px |
| padding-bottom | 9.5px | 8px | 4px |
| padding-left | 36px | 12px | 8px |
| border-top-color | rgb(203, 213, 224) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(203, 213, 224) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(203, 213, 224) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(203, 213, 224) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| font-family | Arial | "SF Pro Text", "Segoe UI", Roboto, Helvetica, Arial, sans-serif | "SF Pro Text", "Segoe UI", Roboto, Helvetica, Arial, sans-serif |
| line-height | normal | 21.6px | 20.4px |
| background-color | rgb(247, 250, 252) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 37px | 39.6094px | 30.3906px |
| offsetHeight | 37 | 40 | 30 |
| padding-right | 12px | 12px (=) | 8px |
| font-size | 14.4px | 14.4px (=) | 13.6px |
| min-height | auto | auto (=) | 28px |

[focus] 差分 12 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 9.5px | 8px | 4px |
| padding-bottom | 9.5px | 8px | 4px |
| padding-left | 36px | 12px | 8px |
| font-family | Arial | "SF Pro Text", "Segoe UI", Roboto, Helvetica, Arial, sans-serif | "SF Pro Text", "Segoe UI", Roboto, Helvetica, Arial, sans-serif |
| line-height | normal | 21.6px | 20.4px |
| background-color | rgb(247, 250, 252) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 37px | 39.6094px | 30.3906px |
| box-shadow | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px, rgba(30, 58, 138, 0.18) 0p... | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 37 | 40 | 30 |
| padding-right | 12px | 12px (=) | 8px |
| font-size | 14.4px | 14.4px (=) | 13.6px |
| min-height | auto | auto (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: なし（全 2 通りで同一）

### G33（1 件、測定 1 件＝全メンバー）

- 適用規則: `components/field-size.css:13 .field-w-sm` / `components/field-size.css:22 .content-toolbar .field-w-sm` / `components/field-size.css:8 .field-h-md`
- inline style: なし

#### pages/contacts/ContactsPage.tsx:281  type=text  祖先連鎖 4 通り

- 祖先(variant0, 内側から): `div.content-toolbar__left < div.content-toolbar < div < div.page-layout < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell < main.mobile-content < div.mobile-shell`
- 反映した inline: `なし` / own class: `search-input field-h-md field-w-sm`

[normal] 差分 30 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 36px | 39.6094px | 30.3906px |
| min-height | 36px | auto | 28px |
| width | 160px | 192px | 167px |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| offsetHeight | 36 | 40 | 30 |
| offsetWidth | 160 | 192 | 167 |

[focus] 差分 33 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 36px | 39.6094px | 30.3906px |
| min-height | 36px | auto | 28px |
| width | 160px | 192px | 167px |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 36 | 40 | 30 |
| offsetWidth | 160 | 192 | 167 |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: なし（全 4 通りで同一）

### G34（1 件、測定 1 件＝全メンバー）

- 適用規則: `features/tcg-analysis-review/source-raw-pane.css:48 .source-search input`
- inline style: なし

#### features/tcg-analysis-review/SourceRawPane.tsx:30  type=omitted  祖先連鎖 4 通り

- 祖先(variant0, 内側から): `form.source-search < div.source-raw-pane < aside.source-raw < div.supplier-detail-view-body < div.supplier-detail-view < div.analysis-panel-content < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `なし` / own class: `なし`

[normal] 差分 30 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 149px | 187.391px | 167px |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 149 | 187 | 167 |
| min-height | auto | auto (=) | 28px |

[focus] 差分 33 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 0px | 8px | 4px |
| padding-right | 0px | 12px | 8px |
| padding-bottom | 0px | 8px | 4px |
| padding-left | 0px | 12px | 8px |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 19px | 39.6094px | 30.3906px |
| width | 149px | 187.391px | 167px |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 19 | 40 | 30 |
| offsetWidth | 149 | 187 | 167 |
| min-height | auto | auto (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: なし（全 4 通りで同一）

### G35（1 件、測定 1 件＝全メンバー）

- 適用規則: `pages/goal-setting/GoalSettingPage.css:119 .gs-advisor__monthly-input` / `pages/goal-setting/GoalSettingPage.css:510 .gs-input` / `pages/goal-setting/GoalSettingPage.css:522 .gs-input:focus`
- inline style: なし

#### pages/goal-setting/GoalSettingPage.tsx:334  type=number  祖先連鎖 2 通り

- 祖先(variant0, 内側から): `div.gs-advisor__monthly-row < div.gs-advisor__form < div.gs-advisor__main < div.gs-advisor__grid < section.gs-advisor < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `なし` / own class: `gs-input gs-advisor__monthly-input`

[normal] 差分 11 項目

| property | before | md | sm |
|---|---|---|---|
| font-size | 13.6px | 14.4px | 13.6px (=) |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| background-color | rgb(245, 247, 250) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 44px | 39.6094px | 30.3906px |
| min-height | 44px | auto | 28px |
| offsetHeight | 44 | 40 | 30 |
| padding-top | 8px | 8px (=) | 4px |
| padding-right | 12px | 12px (=) | 8px |
| padding-bottom | 8px | 8px (=) | 4px |
| padding-left | 12px | 12px (=) | 8px |

[focus] 差分 12 項目

| property | before | md | sm |
|---|---|---|---|
| font-size | 13.6px | 14.4px | 13.6px (=) |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| background-color | rgb(245, 247, 250) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 44px | 39.6094px | 30.3906px |
| min-height | 44px | auto | 28px |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 44 | 40 | 30 |
| padding-top | 8px | 8px (=) | 4px |
| padding-right | 12px | 12px (=) | 8px |
| padding-bottom | 8px | 8px (=) | 4px |
| padding-left | 12px | 12px (=) | 8px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: 
- variant1: before差=width,offsetWidth / md差=width,offsetWidth

### G36（1 件、測定 1 件＝全メンバー）

- 適用規則: `pages/goal-setting/GoalSettingPage.css:277 .gs-advisor__metric-input` / `pages/goal-setting/GoalSettingPage.css:281 .gs-advisor__metric-input:focus-visible` / `pages/goal-setting/GoalSettingPage.css:510 .gs-input` / `pages/goal-setting/GoalSettingPage.css:522 .gs-input:focus`
- inline style: なし

#### pages/goal-setting/GoalSettingPage.tsx:230  type=number  祖先連鎖 2 通り

- 祖先(variant0, 内側から): `div.gs-advisor__metric < div.gs-advisor__metric-grid < div.gs-advisor__plan < div.gs-advisor__main < div.gs-advisor__grid < section.gs-advisor < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `なし` / own class: `gs-input gs-advisor__metric-input`

[normal] 差分 11 項目

| property | before | md | sm |
|---|---|---|---|
| font-size | 13.6px | 14.4px | 13.6px (=) |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| background-color | rgb(245, 247, 250) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 44px | 39.6094px | 30.3906px |
| min-height | 44px | auto | 28px |
| offsetHeight | 44 | 40 | 30 |
| padding-top | 8px | 8px (=) | 4px |
| padding-right | 12px | 12px (=) | 8px |
| padding-bottom | 8px | 8px (=) | 4px |
| padding-left | 12px | 12px (=) | 8px |

[focus] 差分 11 項目

| property | before | md | sm |
|---|---|---|---|
| font-size | 13.6px | 14.4px | 13.6px (=) |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| background-color | rgb(245, 247, 250) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 44px | 39.6094px | 30.3906px |
| min-height | 44px | auto | 28px |
| offsetHeight | 44 | 40 | 30 |
| padding-top | 8px | 8px (=) | 4px |
| padding-right | 12px | 12px (=) | 8px |
| padding-bottom | 8px | 8px (=) | 4px |
| padding-left | 12px | 12px (=) | 8px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: 
- variant1: before差=width,offsetWidth / md差=width,offsetWidth

### G37（1 件、測定 1 件＝全メンバー）

- 適用規則: `pages/goal-setting/GoalSettingPage.css:510 .gs-input` / `pages/goal-setting/GoalSettingPage.css:522 .gs-input:focus` / `pages/goal-setting/GoalSettingPage.css:527 .gs-input.gs-input-saved ?conditional-class`
- inline style: なし

#### pages/goal-setting/GoalSettingPage.tsx:157  type=number  祖先連鎖 2 通り

- 祖先(variant0, 内側から): `div.gs-input-wrap < div.gs-row < div.gs-rows < div.gs-block < section.gs-section < div.gs-layout < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `なし` / own class: `gs-input`

[normal] 差分 11 項目

| property | before | md | sm |
|---|---|---|---|
| font-size | 13.6px | 14.4px | 13.6px (=) |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| background-color | rgb(245, 247, 250) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 33px | 39.6094px | 30.3906px |
| offsetHeight | 33 | 40 | 30 |
| padding-top | 8px | 8px (=) | 4px |
| padding-right | 12px | 12px (=) | 8px |
| padding-bottom | 8px | 8px (=) | 4px |
| padding-left | 12px | 12px (=) | 8px |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 12 項目

| property | before | md | sm |
|---|---|---|---|
| font-size | 13.6px | 14.4px | 13.6px (=) |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| background-color | rgb(245, 247, 250) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 33px | 39.6094px | 30.3906px |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 33 | 40 | 30 |
| padding-top | 8px | 8px (=) | 4px |
| padding-right | 12px | 12px (=) | 8px |
| padding-bottom | 8px | 8px (=) | 4px |
| padding-left | 12px | 12px (=) | 8px |
| min-height | 0px | 0px (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: 
- variant1: before差=width,offsetWidth / md差=width,offsetWidth

### G38（1 件、測定 1 件＝全メンバー）

- 適用規則: `pages/inbox/InboxPage.css:1160 .right-panel-field` / `pages/inbox/InboxPage.css:1168 .right-panel-field::placeholder` / `pages/inbox/InboxPage.css:1169 .right-panel-field:focus` / `pages/inbox/InboxPage.css:1339 input[type="date"].karte-field-empty:not(:focus)::-webkit-datetime-edit ?conditional-class`
- inline style: なし

#### pages/inbox/InboxKartePanel.tsx:509  type=date  祖先連鎖 2 通り

- 祖先(variant0, 内側から): `div.right-panel-row < div.right-panel-section < div.right-panel-tab-content < div.right-panel-card < aside.inbox-right-panel < div.inbox-wrapper < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `なし` / own class: `right-panel-field`

[normal] 差分 14 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 7px | 8px | 4px |
| padding-right | 9px | 12px | 8px |
| padding-bottom | 7px | 8px | 4px |
| padding-left | 9px | 12px | 8px |
| border-top-color | rgb(221, 224, 228) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(221, 224, 228) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(221, 224, 228) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(221, 224, 228) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| font-size | 13.6px | 14.4px | 13.6px (=) |
| line-height | normal | 21.6px | 20.4px |
| background-color | rgb(250, 251, 252) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 33.5938px | 41.6094px | 32.3906px |
| offsetHeight | 34 | 42 | 32 |
| min-height | auto | auto (=) | 28px |

[focus] 差分 11 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 7px | 8px | 4px |
| padding-right | 9px | 12px | 8px |
| padding-bottom | 7px | 8px | 4px |
| padding-left | 9px | 12px | 8px |
| font-size | 13.6px | 14.4px | 13.6px (=) |
| line-height | normal | 21.6px | 20.4px |
| background-color | rgb(250, 251, 252) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 33.5938px | 41.6094px | 32.3906px |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 34 | 42 | 32 |
| min-height | auto | auto (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: なし（全 2 通りで同一）

### G39（1 件、測定 1 件＝全メンバー）

- 適用規則: `pages/inbox/InboxPage.css:1160 .right-panel-field` / `pages/inbox/InboxPage.css:1168 .right-panel-field::placeholder` / `pages/inbox/InboxPage.css:1169 .right-panel-field:focus` / `pages/inbox/InboxPage.css:1630 .sales-form-other-input`
- inline style: なし

#### pages/inbox/SalesFormMultiSelect.tsx:148  type=text  祖先連鎖 2 通り

- 祖先(variant0, 内側から): `div.sales-form-multi-select < div.right-panel-row.right-panel-row--multiselect < div.right-panel-section < div.right-panel-tab-content < div.right-panel-card < aside.inbox-right-panel < div.inbox-wrapper < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `なし` / own class: `right-panel-field sales-form-other-input`

[normal] 差分 17 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 7px | 8px | 4px |
| padding-right | 9px | 12px | 8px |
| padding-bottom | 7px | 8px | 4px |
| padding-left | 9px | 12px | 8px |
| border-top-color | rgb(221, 224, 228) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(221, 224, 228) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(221, 224, 228) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(221, 224, 228) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| font-size | 13.6px | 14.4px | 13.6px (=) |
| line-height | normal | 21.6px | 20.4px |
| background-color | rgb(250, 251, 252) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 31px | 39.6094px | 30.3906px |
| width | 165px | 176px | 163px |
| margin-top | 4px | 0px | 0px |
| offsetHeight | 31 | 40 | 30 |
| offsetWidth | 165 | 176 | 163 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 14 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 7px | 8px | 4px |
| padding-right | 9px | 12px | 8px |
| padding-bottom | 7px | 8px | 4px |
| padding-left | 9px | 12px | 8px |
| font-size | 13.6px | 14.4px | 13.6px (=) |
| line-height | normal | 21.6px | 20.4px |
| background-color | rgb(250, 251, 252) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 31px | 39.6094px | 30.3906px |
| width | 165px | 176px | 163px |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| margin-top | 4px | 0px | 0px |
| offsetHeight | 31 | 40 | 30 |
| offsetWidth | 165 | 176 | 163 |
| min-height | 0px | 0px (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: なし（全 2 通りで同一）

### G40（1 件、測定 1 件＝全メンバー）

- 適用規則: `pages/super-admin/components/AnalysisDashboardPanel.css:75 .analysis-dashboard-window-input`
- inline style: なし

#### pages/super-admin/components/AnalysisDashboardPanel.tsx:803  type=number  祖先連鎖 2 通り

- 祖先(variant0, 内側から): `div.analysis-dashboard-upload-options < div.comp-card < div.analysis-dashboard < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `なし` / own class: `analysis-dashboard-window-input`

[normal] 差分 18 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 4px | 8px | 4px (=) |
| padding-right | 8px | 12px | 8px (=) |
| padding-bottom | 4px | 8px | 4px (=) |
| padding-left | 8px | 12px | 8px (=) |
| border-top-left-radius | 4px | 6px | 6px |
| border-top-right-radius | 4px | 6px | 6px |
| border-bottom-right-radius | 4px | 6px | 6px |
| border-bottom-left-radius | 4px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 25px | 39.6094px | 30.3906px |
| width | 80px | 1184px | 1184px |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| offsetHeight | 25 | 40 | 30 |
| offsetWidth | 80 | 1184 | 1184 |
| min-height | auto | auto (=) | 28px |

[focus] 差分 25 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 4px | 8px | 4px (=) |
| padding-right | 8px | 12px | 8px (=) |
| padding-bottom | 4px | 8px | 4px (=) |
| padding-left | 8px | 12px | 8px (=) |
| border-top-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-top-left-radius | 4px | 6px | 6px |
| border-top-right-radius | 4px | 6px | 6px |
| border-bottom-right-radius | 4px | 6px | 6px |
| border-bottom-left-radius | 4px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 25px | 39.6094px | 30.3906px |
| width | 80px | 1184px | 1184px |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 25 | 40 | 30 |
| offsetWidth | 80 | 1184 | 1184 |
| min-height | auto | auto (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: 
- variant1: before差=- / md差=width,offsetWidth

### G41（1 件、測定 1 件＝全メンバー）

- 適用規則: (なし)
- inline style: `style{background:var(--bg-primary);border-radius:4px;border:1px solid var(--border-color);box-sizing:border-box;color:var(--text-primary);font-size:0.85rem;margin-bottom:0.5rem;padding:0.4rem 0.6rem;width:100%}`

#### features/tcg-import-review/ReviewSection.tsx:289  type=text  祖先連鎖 4 通り

- 祖先(variant0, 内側から): `div < div < div < section < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `width:100%;padding:0.4rem 0.6rem;border:1px solid var(--border-color);border-radius:4px;font-size:0.85rem;background:var(--bg-primary);color:var(--text-primary);margin-bottom:0.5rem;box-sizing:border-box` / own class: `なし`

[normal] 差分 20 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 6.4px | 8px | 4px |
| padding-right | 9.6px | 12px | 8px |
| padding-bottom | 6.4px | 8px | 4px |
| padding-left | 9.6px | 12px | 8px |
| border-top-color | rgb(204, 204, 204) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(204, 204, 204) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(204, 204, 204) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(204, 204, 204) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-top-left-radius | 4px | 6px | 6px |
| border-top-right-radius | 4px | 6px | 6px |
| border-bottom-right-radius | 4px | 6px | 6px |
| border-bottom-left-radius | 4px | 6px | 6px |
| font-size | 13.6px | 14.4px | 13.6px (=) |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| background-color | rgb(245, 247, 250) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 29.7812px | 39.6094px | 30.3906px |
| margin-bottom | 8px | 0px | 0px |
| offsetHeight | 30 | 40 | 30 (=) |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 24 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 6.4px | 8px | 4px |
| padding-right | 9.6px | 12px | 8px |
| padding-bottom | 6.4px | 8px | 4px |
| padding-left | 9.6px | 12px | 8px |
| border-top-color | rgb(204, 204, 204) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(204, 204, 204) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(204, 204, 204) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(204, 204, 204) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-top-left-radius | 4px | 6px | 6px |
| border-top-right-radius | 4px | 6px | 6px |
| border-bottom-right-radius | 4px | 6px | 6px |
| border-bottom-left-radius | 4px | 6px | 6px |
| font-size | 13.6px | 14.4px | 13.6px (=) |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| background-color | rgb(245, 247, 250) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 29.7812px | 39.6094px | 30.3906px |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| margin-bottom | 8px | 0px | 0px |
| offsetHeight | 30 | 40 | 30 (=) |
| min-height | 0px | 0px (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: 
- variant1: before差=width,offsetWidth / md差=width,offsetWidth
- variant3: before差=width,offsetWidth / md差=width,offsetWidth

### G42（1 件、測定 1 件＝全メンバー）

- 適用規則: (なし)
- inline style: `style{background:var(--bg-primary);border-radius:4px;border:1px solid var(--border-color);color:var(--text-primary);font-size:0.85rem;padding:0.4rem 0.6rem;width:80px}`

#### pages/super-admin/TcgLineImportPage.tsx:353  type=number  祖先連鎖 2 通り

- 祖先(variant0, 内側から): `label < div < section < details < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `padding:0.4rem 0.6rem;border:1px solid var(--border-color);border-radius:4px;font-size:0.85rem;width:80px;background:var(--bg-primary);color:var(--text-primary)` / own class: `なし`

[normal] 差分 21 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 6.4px | 8px | 4px |
| padding-right | 9.6px | 12px | 8px |
| padding-bottom | 6.4px | 8px | 4px |
| padding-left | 9.6px | 12px | 8px |
| border-top-color | rgb(204, 204, 204) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(204, 204, 204) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(204, 204, 204) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(204, 204, 204) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-top-left-radius | 4px | 6px | 6px |
| border-top-right-radius | 4px | 6px | 6px |
| border-bottom-right-radius | 4px | 6px | 6px |
| border-bottom-left-radius | 4px | 6px | 6px |
| font-size | 13.6px | 14.4px | 13.6px (=) |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| background-color | rgb(245, 247, 250) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 29.7812px | 39.6094px | 30.3906px |
| width | 80px | 1280px | 1280px |
| offsetHeight | 30 | 40 | 30 (=) |
| offsetWidth | 80 | 1280 | 1280 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 21 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 6.4px | 8px | 4px |
| padding-right | 9.6px | 12px | 8px |
| padding-bottom | 6.4px | 8px | 4px |
| padding-left | 9.6px | 12px | 8px |
| border-top-color | rgb(204, 204, 204) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(204, 204, 204) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(204, 204, 204) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(204, 204, 204) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-top-left-radius | 4px | 6px | 6px |
| border-top-right-radius | 4px | 6px | 6px |
| border-bottom-right-radius | 4px | 6px | 6px |
| border-bottom-left-radius | 4px | 6px | 6px |
| font-size | 13.6px | 14.4px | 13.6px (=) |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| background-color | rgb(245, 247, 250) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 29.7812px | 39.6094px | 30.3906px |
| width | 80px | 1280px | 1280px |
| offsetHeight | 30 | 40 | 30 (=) |
| offsetWidth | 80 | 1280 | 1280 |
| min-height | 0px | 0px (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: 
- variant1: before差=- / md差=width,offsetWidth

### G43（1 件、測定 1 件＝全メンバー）

- 適用規則: (なし)
- inline style: `style{border-radius:4px;border:1px solid var(--border);font-size:13px;padding:6px 8px;width:100px}`

#### components/FedExRateModal.tsx:210  type=number  祖先連鎖 2 通り

- 祖先(variant0, 内側から): `div < div < div < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `width:100px;padding:6px 8px;border:1px solid var(--border);border-radius:4px;font-size:13px` / own class: `なし`

[normal] 差分 18 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 6px | 8px | 4px |
| padding-right | 8px | 12px | 8px (=) |
| padding-bottom | 6px | 8px | 4px |
| padding-left | 8px | 12px | 8px (=) |
| border-top-left-radius | 4px | 6px | 6px |
| border-top-right-radius | 4px | 6px | 6px |
| border-bottom-right-radius | 4px | 6px | 6px |
| border-bottom-left-radius | 4px | 6px | 6px |
| font-size | 13px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 29px | 39.6094px | 30.3906px |
| width | 100px | 1200px | 1200px |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| offsetHeight | 29 | 40 | 30 |
| offsetWidth | 100 | 1200 | 1200 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 25 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 6px | 8px | 4px |
| padding-right | 8px | 12px | 8px (=) |
| padding-bottom | 6px | 8px | 4px |
| padding-left | 8px | 12px | 8px (=) |
| border-top-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-top-left-radius | 4px | 6px | 6px |
| border-top-right-radius | 4px | 6px | 6px |
| border-bottom-right-radius | 4px | 6px | 6px |
| border-bottom-left-radius | 4px | 6px | 6px |
| font-size | 13px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 29px | 39.6094px | 30.3906px |
| width | 100px | 1200px | 1200px |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 29 | 40 | 30 |
| offsetWidth | 100 | 1200 | 1200 |
| min-height | 0px | 0px (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: なし（全 2 通りで同一）

### G44（1 件、測定 1 件＝全メンバー）

- 適用規則: (なし)
- inline style: `style{border-radius:4px;border:1px solid var(--border);font-size:13px;padding:6px 8px;width:160px}`

#### components/FedExRateModal.tsx:239  type=text  祖先連鎖 2 通り

- 祖先(variant0, 内側から): `div < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `width:160px;padding:6px 8px;border:1px solid var(--border);border-radius:4px;font-size:13px` / own class: `なし`

[normal] 差分 18 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 6px | 8px | 4px |
| padding-right | 8px | 12px | 8px (=) |
| padding-bottom | 6px | 8px | 4px |
| padding-left | 8px | 12px | 8px (=) |
| border-top-left-radius | 4px | 6px | 6px |
| border-top-right-radius | 4px | 6px | 6px |
| border-bottom-right-radius | 4px | 6px | 6px |
| border-bottom-left-radius | 4px | 6px | 6px |
| font-size | 13px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 29px | 39.6094px | 30.3906px |
| width | 160px | 1200px | 1200px |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| offsetHeight | 29 | 40 | 30 |
| offsetWidth | 160 | 1200 | 1200 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 25 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 6px | 8px | 4px |
| padding-right | 8px | 12px | 8px (=) |
| padding-bottom | 6px | 8px | 4px |
| padding-left | 8px | 12px | 8px (=) |
| border-top-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-top-left-radius | 4px | 6px | 6px |
| border-top-right-radius | 4px | 6px | 6px |
| border-bottom-right-radius | 4px | 6px | 6px |
| border-bottom-left-radius | 4px | 6px | 6px |
| font-size | 13px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 29px | 39.6094px | 30.3906px |
| width | 160px | 1200px | 1200px |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 29 | 40 | 30 |
| offsetWidth | 160 | 1200 | 1200 |
| min-height | 0px | 0px (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: なし（全 2 通りで同一）

### G45（1 件、測定 1 件＝全メンバー）

- 適用規則: (なし)
- inline style: `style{border-radius:var(--radius-sm);border:1px solid var(--border);flex:1;font-size:var(--font-sm);padding:var(--space-2)}`

#### pages/invoice-detail/InvoiceDetailPage.tsx:222  type=omitted  祖先連鎖 2 通り

- 祖先(variant0, 内側から): `div < div < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `flex:1;padding:var(--space-2);border-radius:var(--radius-sm);border:1px solid var(--border);font-size:var(--font-sm)` / own class: `なし`

[normal] 差分 20 項目

| property | before | md | sm |
|---|---|---|---|
| padding-right | 8px | 12px | 8px (=) |
| padding-left | 8px | 12px | 8px (=) |
| border-top-left-radius | 4px | 6px | 6px |
| border-top-right-radius | 4px | 6px | 6px |
| border-bottom-right-radius | 4px | 6px | 6px |
| border-bottom-left-radius | 4px | 6px | 6px |
| font-size | 13.6px | 14.4px | 13.6px (=) |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 33px | 39.6094px | 30.3906px |
| width | 163px | 1280px | 1280px |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| flex-grow | 1 | 0 | 0 |
| flex-basis | 0% | auto | auto |
| offsetHeight | 33 | 40 | 30 |
| offsetWidth | 163 | 1280 | 1280 |
| padding-top | 8px | 8px (=) | 4px |
| padding-bottom | 8px | 8px (=) | 4px |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 27 項目

| property | before | md | sm |
|---|---|---|---|
| padding-right | 8px | 12px | 8px (=) |
| padding-left | 8px | 12px | 8px (=) |
| border-top-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-top-left-radius | 4px | 6px | 6px |
| border-top-right-radius | 4px | 6px | 6px |
| border-bottom-right-radius | 4px | 6px | 6px |
| border-bottom-left-radius | 4px | 6px | 6px |
| font-size | 13.6px | 14.4px | 13.6px (=) |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 33px | 39.6094px | 30.3906px |
| width | 163px | 1280px | 1280px |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| flex-grow | 1 | 0 | 0 |
| flex-basis | 0% | auto | auto |
| offsetHeight | 33 | 40 | 30 |
| offsetWidth | 163 | 1280 | 1280 |
| padding-top | 8px | 8px (=) | 4px |
| padding-bottom | 8px | 8px (=) | 4px |
| min-height | 0px | 0px (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: 
- variant1: before差=- / md差=width,offsetWidth

### G46（1 件、測定 1 件＝全メンバー）

- 適用規則: (なし)
- inline style: `style{border-radius:var(--radius-sm);border:1px solid var(--border);padding:var(--space-2);width:100%}`

#### pages/invoice-detail/InvoiceDetailPage.tsx:271  type=omitted  祖先連鎖 2 通り

- 祖先(variant0, 内側から): `div < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `width:100%;padding:var(--space-2);border-radius:var(--radius-sm);border:1px solid var(--border)` / own class: `なし`

[normal] 差分 16 項目

| property | before | md | sm |
|---|---|---|---|
| padding-right | 8px | 12px | 8px (=) |
| padding-left | 8px | 12px | 8px (=) |
| border-top-left-radius | 4px | 6px | 6px |
| border-top-right-radius | 4px | 6px | 6px |
| border-bottom-right-radius | 4px | 6px | 6px |
| border-bottom-left-radius | 4px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 33px | 39.6094px | 30.3906px |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| offsetHeight | 33 | 40 | 30 |
| padding-top | 8px | 8px (=) | 4px |
| padding-bottom | 8px | 8px (=) | 4px |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 23 項目

| property | before | md | sm |
|---|---|---|---|
| padding-right | 8px | 12px | 8px (=) |
| padding-left | 8px | 12px | 8px (=) |
| border-top-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-top-left-radius | 4px | 6px | 6px |
| border-top-right-radius | 4px | 6px | 6px |
| border-bottom-right-radius | 4px | 6px | 6px |
| border-bottom-left-radius | 4px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 33px | 39.6094px | 30.3906px |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 33 | 40 | 30 |
| padding-top | 8px | 8px (=) | 4px |
| padding-bottom | 8px | 8px (=) | 4px |
| min-height | 0px | 0px (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: 
- variant1: before差=width,offsetWidth / md差=width,offsetWidth

### G47（1 件、測定 1 件＝全メンバー）

- 適用規則: (なし)
- inline style: `style{flex:1;min-width:var(--min-width-input-sm);padding:var(--space-6px) var(--space-2)}`

#### components/InventorySearchBar.tsx:272  type=text  祖先連鎖 2 通り  disabled属性あり

- 祖先(variant0, 内側から): `div < div.inventory-search-bar < div < form < div < div.page-layout < main.mobile-content < div.mobile-shell`
- 反映した inline: `flex:1;min-width:var(--min-width-input-sm);padding:var(--space-6px) var(--space-2)` / own class: `なし`

[normal] 差分 33 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 6px | 8px | 4px |
| padding-right | 8px | 12px | 8px (=) |
| padding-bottom | 6px | 8px | 4px |
| padding-left | 8px | 12px | 8px (=) |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 31px | 39.6094px | 30.3906px |
| width | 165px | 1280px | 1280px |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| min-width | 120px | 0px | 0px |
| flex-grow | 1 | 0 | 0 |
| flex-basis | 0% | auto | auto |
| offsetHeight | 31 | 40 | 30 |
| offsetWidth | 165 | 1280 | 1280 |
| min-height | 0px | 0px (=) | 28px |

[focus] 差分 36 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 6px | 8px | 4px |
| padding-right | 8px | 12px | 8px (=) |
| padding-bottom | 6px | 8px | 4px |
| padding-left | 8px | 12px | 8px (=) |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-right-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-bottom-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-left-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 31px | 39.6094px | 30.3906px |
| width | 165px | 1280px | 1280px |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| min-width | 120px | 0px | 0px |
| flex-grow | 1 | 0 | 0 |
| flex-basis | 0% | auto | auto |
| offsetHeight | 31 | 40 | 30 |
| offsetWidth | 165 | 1280 | 1280 |
| min-height | 0px | 0px (=) | 28px |

[disabled] 差分 36 項目

| property | before | md | sm |
|---|---|---|---|
| padding-top | 6px | 8px | 4px |
| padding-right | 8px | 12px | 8px (=) |
| padding-bottom | 6px | 8px | 4px |
| padding-left | 8px | 12px | 8px (=) |
| border-top-width | 2px | 1px | 1px |
| border-right-width | 2px | 1px | 1px |
| border-bottom-width | 2px | 1px | 1px |
| border-left-width | 2px | 1px | 1px |
| border-top-style | inset | solid | solid |
| border-right-style | inset | solid | solid |
| border-bottom-style | inset | solid | solid |
| border-left-style | inset | solid | solid |
| border-top-color | rgba(118, 118, 118, 0.3) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgba(118, 118, 118, 0.3) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgba(118, 118, 118, 0.3) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgba(118, 118, 118, 0.3) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-top-left-radius | 0px | 6px | 6px |
| border-top-right-radius | 0px | 6px | 6px |
| border-bottom-right-radius | 0px | 6px | 6px |
| border-bottom-left-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Can... |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(84, 84, 84) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| background-color | rgba(239, 239, 239, 0.3) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| height | 31px | 39.6094px | 30.3906px |
| width | 165px | 1280px | 1280px |
| outline-color | rgb(84, 84, 84) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| cursor | default | not-allowed | not-allowed |
| opacity | 1 | 0.5 | 0.5 |
| min-width | 120px | 0px | 0px |
| flex-grow | 1 | 0 | 0 |
| flex-basis | 0% | auto | auto |
| offsetHeight | 31 | 40 | 30 |
| offsetWidth | 165 | 1280 | 1280 |
| min-height | 0px | 0px (=) | 28px |

祖先連鎖の違いによる値のばらつき（normal, variant0 との差）: 
- variant1: before差=- / md差=width,offsetWidth
