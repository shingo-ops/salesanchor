# AY-2e 実画面 前後比較（幅1280、DPR2）

## discord-announce

- 描画 before=true after=true、scrollWidth/clientWidth before=1280/1280 after=1280/1280
- 重なり(操作要素) before=0 after=0、入力と文字の重なり before=0 after=0、右はみ出し(操作要素) before=["BUTTON:閉じる","BUTTON:","BUTTON:","BUTTON:","BUTTON:"] after=["BUTTON:閉じる","BUTTON:","BUTTON:","BUTTON:","BUTTON:"]

### discord-announce / 例: 1288437029213835356 (text)

| 項目 | before | after |
|---|---|---|
| bbox | 215.67,99.59 149x19 | 78,121.19 1178x39.61 |
| className | input w-full | comp-field__input |
| style属性 |  |  |
| computed差(項目) | 14 項目 | padding-top, padding-right, padding-bottom, padding-left, border-top-width, border-top-style, border-top-color, border-top-left-radius, font-size, font-family, line-height, color, height, width |

| computed | before | after |
|---|---|---|
| padding-top | 0px | 8px |
| padding-right | 0px | 12px |
| padding-bottom | 0px | 8px |
| padding-left | 0px | 12px |
| border-top-width | 2px | 1px |
| border-top-style | inset | solid |
| border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| border-top-left-radius | 0px | 6px |
| font-size | 13.3333px | 14.4px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| line-height | normal | 21.6px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| height | 19px | 39.6094px |
| width | 149px | 1178px |

同じ行の兄弟（親 div.space-y-2）:

| 兄弟 | before | after |
|---|---|---|
| label "投稿先チャンネル ID" | 78,98.59 137.67x18 | 78,98.59 137.67x18 |
| p "投稿したいDiscordチャンネルを右クリック " | 78,121.19 1178x25.59 | 78,160.8 1178x25.59 |
| 文字 "投稿先チャンネル ID" | 78,98.59 137.67x18 | 78,98.59 137.67x18 |
| 文字 "投稿したいDiscordチャンネルを右クリック " | 78,124.19 536.92x18 | 78,163.8 536.92x18 |
| 親 bbox | 78,95.59 1178x51.19 | 78,95.59 1178x90.8 |

## manual-record

- 描画 before=true after=true、scrollWidth/clientWidth before=1280/1280 after=1280/1280
- 重なり(操作要素) before=0 after=0、入力と文字の重なり before=0 after=0、右はみ出し(操作要素) before=["BUTTON:閉じる","BUTTON:","BUTTON:","BUTTON:","BUTTON:"] after=["BUTTON:閉じる","BUTTON:","BUTTON:","BUTTON:","BUTTON:"]

### manual-record / manual-occurred-at (datetime-local)

| 項目 | before | after |
|---|---|---|
| bbox | 541,759.23 222.33x21.33 | 509,741.38 361x41.61 |
| className | manual-record-datetime | comp-field__input |
| style属性 |  |  |
| computed差(項目) | 14 項目 | padding-top, padding-right, padding-bottom, padding-left, border-top-width, border-top-style, border-top-color, border-top-left-radius, font-size, font-family, line-height, color, height, width |

| computed | before | after |
|---|---|---|
| padding-top | 0px | 8px |
| padding-right | 0px | 12px |
| padding-bottom | 0px | 8px |
| padding-left | 0px | 12px |
| border-top-width | 2px | 1px |
| border-top-style | inset | solid |
| border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| border-top-left-radius | 0px | 6px |
| font-size | 13.3333px | 14.4px |
| font-family | monospace | "SF Pro Text", "Segoe UI", Roboto, Helvetica, Arial, sans-serif |
| line-height | normal | 21.6px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| height | 21.3281px | 41.6094px |
| width | 222.328px | 361px |

同じ行の兄弟（親 div.manual-record-row）:

| 兄弟 | before | after |
|---|---|---|
| label "日時" | 509,760.39 32x18 | 509,718.78 32x18 |
| 文字 "日時" | 509,760.39 32x18 | 509,718.78 32x18 |
| 親 bbox | 509,757.39 361x25.59 | 509,715.78 361x67.2 |

## channel-masters

- 描画 before=true after=true、scrollWidth/clientWidth before=1280/1280 after=1280/1280
- 重なり(操作要素) before=0 after=0、入力と文字の重なり before=0 after=0、右はみ出し(操作要素) before=["BUTTON:閉じる","BUTTON:","BUTTON:","BUTTON:","BUTTON:"] after=["BUTTON:閉じる","BUTTON:","BUTTON:","BUTTON:","BUTTON:"]

### channel-masters / 例: whatsapp_personal (text)

| 項目 | before | after |
|---|---|---|
| bbox | 78,217.13 149x19 | 78,213.13 192x39.61 |
| className |  | comp-field__input |
| style属性 |  | width: auto; |
| computed差(項目) | 14 項目 | padding-top, padding-right, padding-bottom, padding-left, border-top-width, border-top-style, border-top-color, border-top-left-radius, font-size, font-family, line-height, color, height, width |

| computed | before | after |
|---|---|---|
| padding-top | 0px | 8px |
| padding-right | 0px | 12px |
| padding-bottom | 0px | 8px |
| padding-left | 0px | 12px |
| border-top-width | 2px | 1px |
| border-top-style | inset | solid |
| border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| border-top-left-radius | 0px | 6px |
| font-size | 13.3333px | 14.4px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| line-height | normal | 21.6px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| height | 19px | 39.6094px |
| width | 149px | 192px |

同じ行の兄弟（親 div.channel-masters-add-form）:

| 兄弟 | before | after |
|---|---|---|
| h3 "チャネルを追加" | 78,183.19 1178x29.94 | 78,183.19 1178x29.94 |
| input "" | 227,217.13 149x19 | 270,213.13 192x39.61 |
| button "追加" | 376,214.13 30.67x25 | 462,221.13 30.67x25 |
| 文字 "チャネルを追加" | 78,186.19 120.94x22 | 78,186.19 120.94x22 |
| 文字 "追加" | 378,219.13 26.67x15 | 464,226.13 26.67x15 |
| 親 bbox | 78,183.19 1178x55.94 | 78,183.19 1178x69.55 |

### channel-masters / 例: WhatsApp（個人） (text)

| 項目 | before | after |
|---|---|---|
| bbox | 227,217.13 149x19 | 270,213.13 192x39.61 |
| className |  | comp-field__input |
| style属性 |  | width: auto; |
| computed差(項目) | 14 項目 | padding-top, padding-right, padding-bottom, padding-left, border-top-width, border-top-style, border-top-color, border-top-left-radius, font-size, font-family, line-height, color, height, width |

| computed | before | after |
|---|---|---|
| padding-top | 0px | 8px |
| padding-right | 0px | 12px |
| padding-bottom | 0px | 8px |
| padding-left | 0px | 12px |
| border-top-width | 2px | 1px |
| border-top-style | inset | solid |
| border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| border-top-left-radius | 0px | 6px |
| font-size | 13.3333px | 14.4px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| line-height | normal | 21.6px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| height | 19px | 39.6094px |
| width | 149px | 192px |

同じ行の兄弟（親 div.channel-masters-add-form）:

| 兄弟 | before | after |
|---|---|---|
| h3 "チャネルを追加" | 78,183.19 1178x29.94 | 78,183.19 1178x29.94 |
| input "" | 78,217.13 149x19 | 78,213.13 192x39.61 |
| button "追加" | 376,214.13 30.67x25 | 462,221.13 30.67x25 |
| 文字 "チャネルを追加" | 78,186.19 120.94x22 | 78,186.19 120.94x22 |
| 文字 "追加" | 378,219.13 26.67x15 | 464,226.13 26.67x15 |
| 親 bbox | 78,183.19 1178x55.94 | 78,183.19 1178x69.55 |

表の列幅（th）:

| th | before w | after w | 差 |
|---|---|---|---|
| プラットフォームID | 141.63 | 141.63 | 0 |
| 表示名 | 134.52 | 134.52 | 0 |
| 種別 | 59.11 | 59.11 | 0 |
| 操作 | 30.67 | 30.67 | 0 |
| table | 78,70 375.92x113.19 | 78,70 375.92x113.19 | |

## commission

- 描画 before=true after=true、scrollWidth/clientWidth before=1280/1280 after=1280/1280
- 重なり(操作要素) before=0 after=0、入力と文字の重なり before=0 after=0、右はみ出し(操作要素) before=["BUTTON:閉じる","BUTTON:","BUTTON:","BUTTON:","BUTTON:"] after=["BUTTON:閉じる","BUTTON:","BUTTON:","BUTTON:","BUTTON:"]

### commission / settings-value-sales (number)

| 項目 | before | after |
|---|---|---|
| bbox | 782.98,250.13 149x19 | 782.98,238.84 192x39.61 |
| className |  | comp-field__input |
| style属性 |  | width: auto; |
| computed差(項目) | 14 項目 | padding-top, padding-right, padding-bottom, padding-left, border-top-width, border-top-style, border-top-color, border-top-left-radius, font-size, font-family, line-height, color, height, width |

| computed | before | after |
|---|---|---|
| padding-top | 0px | 8px |
| padding-right | 0px | 12px |
| padding-bottom | 0px | 8px |
| padding-left | 0px | 12px |
| border-top-width | 2px | 1px |
| border-top-style | inset | solid |
| border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| border-top-left-radius | 0px | 6px |
| font-size | 13.3333px | 14.4px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| line-height | normal | 21.6px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| height | 19px | 39.6094px |
| width | 149px | 192px |

同じ行の兄弟（親 td.）:

| 兄弟 | before | after |
|---|---|---|
| 親 bbox | 766.98,225.84 292.19x65.11 | 766.98,225.84 292.19x65.11 |

表の行（td）:

| td | before | after |
|---|---|---|
| 0 | 280,225.84 194.8x65.11 | 280,225.84 194.8x65.11 |
| 1 | 474.8,225.84 292.19x65.11 | 474.8,225.84 292.19x65.11 |
| 2 | 766.98,225.84 292.19x65.11 | 766.98,225.84 292.19x65.11 |
| 3 | 1059.17,225.84 194.83x65.11 | 1059.17,225.84 194.83x65.11 |

### commission / settings-value-order (number)

| 項目 | before | after |
|---|---|---|
| bbox | 782.98,314.73 149x19 | 782.98,303.45 192x39.61 |
| className |  | comp-field__input |
| style属性 |  | width: auto; |
| computed差(項目) | 14 項目 | padding-top, padding-right, padding-bottom, padding-left, border-top-width, border-top-style, border-top-color, border-top-left-radius, font-size, font-family, line-height, color, height, width |

| computed | before | after |
|---|---|---|
| padding-top | 0px | 8px |
| padding-right | 0px | 12px |
| padding-bottom | 0px | 8px |
| padding-left | 0px | 12px |
| border-top-width | 2px | 1px |
| border-top-style | inset | solid |
| border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| border-top-left-radius | 0px | 6px |
| font-size | 13.3333px | 14.4px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| line-height | normal | 21.6px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| height | 19px | 39.6094px |
| width | 149px | 192px |

同じ行の兄弟（親 td.）:

| 兄弟 | before | after |
|---|---|---|
| 親 bbox | 766.98,290.95 292.19x64.61 | 766.98,290.95 292.19x64.61 |

表の行（td）:

| td | before | after |
|---|---|---|
| 0 | 280,290.95 194.8x64.61 | 280,290.95 194.8x64.61 |
| 1 | 474.8,290.95 292.19x64.61 | 474.8,290.95 292.19x64.61 |
| 2 | 766.98,290.95 292.19x64.61 | 766.98,290.95 292.19x64.61 |
| 3 | 1059.17,290.95 194.83x64.61 | 1059.17,290.95 194.83x64.61 |

### commission / settings-value-ship (number)

| 項目 | before | after |
|---|---|---|
| bbox | 782.98,379.34 149x19 | 782.98,368.06 192x39.61 |
| className |  | comp-field__input |
| style属性 |  | width: auto; |
| computed差(項目) | 14 項目 | padding-top, padding-right, padding-bottom, padding-left, border-top-width, border-top-style, border-top-color, border-top-left-radius, font-size, font-family, line-height, color, height, width |

| computed | before | after |
|---|---|---|
| padding-top | 0px | 8px |
| padding-right | 0px | 12px |
| padding-bottom | 0px | 8px |
| padding-left | 0px | 12px |
| border-top-width | 2px | 1px |
| border-top-style | inset | solid |
| border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| border-top-left-radius | 0px | 6px |
| font-size | 13.3333px | 14.4px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| line-height | normal | 21.6px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| height | 19px | 39.6094px |
| width | 149px | 192px |

同じ行の兄弟（親 td.）:

| 兄弟 | before | after |
|---|---|---|
| 親 bbox | 766.98,355.56 292.19x64.61 | 766.98,355.56 292.19x64.61 |

表の行（td）:

| td | before | after |
|---|---|---|
| 0 | 280,355.56 194.8x64.61 | 280,355.56 194.8x64.61 |
| 1 | 474.8,355.56 292.19x64.61 | 474.8,355.56 292.19x64.61 |
| 2 | 766.98,355.56 292.19x64.61 | 766.98,355.56 292.19x64.61 |
| 3 | 1059.17,355.56 194.83x64.61 | 1059.17,355.56 194.83x64.61 |

### commission / settings-value-purchase (number)

| 項目 | before | after |
|---|---|---|
| bbox | 782.98,443.95 149x19 | 782.98,432.67 192x39.61 |
| className |  | comp-field__input |
| style属性 |  | width: auto; |
| computed差(項目) | 14 項目 | padding-top, padding-right, padding-bottom, padding-left, border-top-width, border-top-style, border-top-color, border-top-left-radius, font-size, font-family, line-height, color, height, width |

| computed | before | after |
|---|---|---|
| padding-top | 0px | 8px |
| padding-right | 0px | 12px |
| padding-bottom | 0px | 8px |
| padding-left | 0px | 12px |
| border-top-width | 2px | 1px |
| border-top-style | inset | solid |
| border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| border-top-left-radius | 0px | 6px |
| font-size | 13.3333px | 14.4px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| line-height | normal | 21.6px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| height | 19px | 39.6094px |
| width | 149px | 192px |

同じ行の兄弟（親 td.）:

| 兄弟 | before | after |
|---|---|---|
| 親 bbox | 766.98,420.17 292.19x64.61 | 766.98,420.17 292.19x64.61 |

表の行（td）:

| td | before | after |
|---|---|---|
| 0 | 280,420.17 194.8x64.61 | 280,420.17 194.8x64.61 |
| 1 | 474.8,420.17 292.19x64.61 | 474.8,420.17 292.19x64.61 |
| 2 | 766.98,420.17 292.19x64.61 | 766.98,420.17 292.19x64.61 |
| 3 | 1059.17,420.17 194.83x64.61 | 1059.17,420.17 194.83x64.61 |

### commission / settings-value-trouble (number)

| 項目 | before | after |
|---|---|---|
| bbox | 782.98,508.56 149x19 | 782.98,497.28 192x39.61 |
| className |  | comp-field__input |
| style属性 |  | width: auto; |
| computed差(項目) | 14 項目 | padding-top, padding-right, padding-bottom, padding-left, border-top-width, border-top-style, border-top-color, border-top-left-radius, font-size, font-family, line-height, color, height, width |

| computed | before | after |
|---|---|---|
| padding-top | 0px | 8px |
| padding-right | 0px | 12px |
| padding-bottom | 0px | 8px |
| padding-left | 0px | 12px |
| border-top-width | 2px | 1px |
| border-top-style | inset | solid |
| border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| border-top-left-radius | 0px | 6px |
| font-size | 13.3333px | 14.4px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| line-height | normal | 21.6px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| height | 19px | 39.6094px |
| width | 149px | 192px |

同じ行の兄弟（親 td.）:

| 兄弟 | before | after |
|---|---|---|
| 親 bbox | 766.98,484.78 292.19x64.61 | 766.98,484.78 292.19x64.61 |

表の行（td）:

| td | before | after |
|---|---|---|
| 0 | 280,484.78 194.8x64.61 | 280,484.78 194.8x64.61 |
| 1 | 474.8,484.78 292.19x64.61 | 474.8,484.78 292.19x64.61 |
| 2 | 766.98,484.78 292.19x64.61 | 766.98,484.78 292.19x64.61 |
| 3 | 1059.17,484.78 194.83x64.61 | 1059.17,484.78 194.83x64.61 |

表の列幅（th）:

| th | before w | after w | 差 |
|---|---|---|---|
| ロール | 194.8 | 194.8 | 0 |
| 計算タイプ | 292.19 | 292.19 | 0 |
| 値 | 292.19 | 292.19 | 0 |
|  | 194.83 | 194.83 | 0 |
| table | 280,181.66 974x368.23 | 280,181.66 974x368.23 | |

## own-inventory

- 描画 before=true after=true、scrollWidth/clientWidth before=1280/1280 after=1280/1280
- 重なり(操作要素) before=0 after=0、入力と文字の重なり before=0 after=0、右はみ出し(操作要素) before=["BUTTON:閉じる","BUTTON:","BUTTON:","BUTTON:","BUTTON:"] after=["BUTTON:閉じる","BUTTON:","BUTTON:","BUTTON:","BUTTON:"]

### own-inventory / 数量 (number)

| 項目 | before | after |
|---|---|---|
| bbox | 483.56,462 149x19 | 483.56,450.98 192x39.61 |
| className | qty-input | comp-field__input |
| style属性 |  | width: auto; |
| computed差(項目) | 14 項目 | padding-top, padding-right, padding-bottom, padding-left, border-top-width, border-top-style, border-top-color, border-top-left-radius, font-size, font-family, line-height, color, height, width |

| computed | before | after |
|---|---|---|
| padding-top | 0px | 8px |
| padding-right | 0px | 12px |
| padding-bottom | 0px | 8px |
| padding-left | 0px | 12px |
| border-top-width | 2px | 1px |
| border-top-style | inset | solid |
| border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| border-top-left-radius | 0px | 6px |
| font-size | 13.3333px | 14.4px |
| font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| line-height | normal | 21.6px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| height | 19px | 39.6094px |
| width | 149px | 192px |

同じ行の兄弟（親 label.）:

| 兄弟 | before | after |
|---|---|---|
| 文字 "数量" | 454,461 29.56x18 | 454,460.98 29.56x18 |
| 親 bbox | 454,461 178.56x18 | 454,460.98 221.56x18 |

表の列幅（th）:

| th | before w | after w | 差 |
|---|---|---|---|
| 商品ID | 153.52 | 153.52 | 0 |
| 状態 | 82.78 | 82.78 | 0 |
| 物理在庫 | 116.63 | 116.63 | 0 |
| 引当済み | 116.63 | 116.63 | 0 |
| 利用可能 | 116.63 | 116.63 | 0 |
| 単価 | 101.66 | 101.66 | 0 |
| ステータス | 150.64 | 150.64 | 0 |
| 操作 | 337.53 | 337.53 | 0 |
| table | 79,79.03 1176x132 | 79,79.03 1176x132 | |

## 判定

- #3/#4 入力2つの top: 213.13,213.13、ボタン top 221.13、中心差 0.69 → 1行
- #1 横幅: input 1178 / 親 1178 → 親いっぱい
- #2 横幅: input 361 / 親 361（label の下の行: label 文字 日時 y=718.78、input y=741.38）
- #6 「数量」文字 y中心 469.98、入力 y中心 470.79、入力 x=483.56 文字右端=483.56 → 1行

判定: PASS

