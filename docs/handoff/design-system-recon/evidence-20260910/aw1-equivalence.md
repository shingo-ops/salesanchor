# AW-1 外観同等性

chromium 147.0.7727.15／条件数 48（3種類×4状態×2幅×2テーマ。各条件で旧・新の 42 項目を比較）／console 警告: なし

旧要素と aw1-baseline.json の差（opacity 以外）: 0件

判定対象: normal/focus/hover（disabled は判定から除外）

差分0

## 想定差分（disabled 状態。13 利用先は disabled を使わず、使う場合は金型の disabled に従う）

12 条件

- karte/disabled/1280/light: opacity: 旧=0.7 新=0.5
- header/disabled/1280/light: background-color: 旧=rgb(255, 255, 255) 新=rgb(226, 232, 240); background-image: 旧=url("data:image/svg+xml,%3Csvg xmlns='ht 新=none; background-position: 旧=calc(100% - 8px) 50% 新=0% 0%; background-repeat: 旧=no-repeat 新=repeat; cursor: 旧=pointer 新=not-allowed; opacity: 旧=0.7 新=0.5
- tabbar/disabled/1280/light: background-color: 旧=rgb(255, 255, 255) 新=rgb(226, 232, 240); cursor: 旧=pointer 新=not-allowed; opacity: 旧=0.7 新=0.5
- karte/disabled/1280/dark: opacity: 旧=0.7 新=0.5
- header/disabled/1280/dark: background-color: 旧=rgb(30, 41, 59) 新=rgb(51, 65, 85); background-image: 旧=url("data:image/svg+xml,%3Csvg xmlns='ht 新=none; background-position: 旧=calc(100% - 8px) 50% 新=0% 0%; background-repeat: 旧=no-repeat 新=repeat; cursor: 旧=pointer 新=not-allowed; opacity: 旧=0.7 新=0.5
- tabbar/disabled/1280/dark: background-color: 旧=rgb(30, 41, 59) 新=rgb(51, 65, 85); cursor: 旧=pointer 新=not-allowed; opacity: 旧=0.7 新=0.5
- karte/disabled/390/light: opacity: 旧=0.7 新=0.5
- header/disabled/390/light: background-color: 旧=rgb(255, 255, 255) 新=rgb(226, 232, 240); background-image: 旧=url("data:image/svg+xml,%3Csvg xmlns='ht 新=none; background-position: 旧=calc(100% - 8px) 50% 新=0% 0%; background-repeat: 旧=no-repeat 新=repeat; cursor: 旧=pointer 新=not-allowed; opacity: 旧=0.7 新=0.5
- tabbar/disabled/390/light: background-color: 旧=rgb(255, 255, 255) 新=rgb(226, 232, 240); cursor: 旧=pointer 新=not-allowed; opacity: 旧=0.7 新=0.5
- karte/disabled/390/dark: opacity: 旧=0.7 新=0.5
- header/disabled/390/dark: background-color: 旧=rgb(30, 41, 59) 新=rgb(51, 65, 85); background-image: 旧=url("data:image/svg+xml,%3Csvg xmlns='ht 新=none; background-position: 旧=calc(100% - 8px) 50% 新=0% 0%; background-repeat: 旧=no-repeat 新=repeat; cursor: 旧=pointer 新=not-allowed; opacity: 旧=0.7 新=0.5
- tabbar/disabled/390/dark: background-color: 旧=rgb(30, 41, 59) 新=rgb(51, 65, 85); cursor: 旧=pointer 新=not-allowed; opacity: 旧=0.7 新=0.5

## DPR2 ピクセル比較（幅1280・normal/focus/hover・light/dark、旧新とも幅200px固定の clip スクリーンショット）

| 種類 | 状態 | テーマ | サイズ(px) | 差分ピクセル数 |
|---|---|---|---|---|
| karte | normal | light | 424x88 | 0 |
| karte | focus | light | 424x88 | 0 |
| karte | hover | light | 424x88 | 0 |
| header | normal | light | 424x96 | 0 |
| header | focus | light | 424x96 | 0 |
| header | hover | light | 424x96 | 0 |
| tabbar | normal | light | 424x96 | 0 |
| tabbar | focus | light | 424x96 | 0 |
| tabbar | hover | light | 424x96 | 0 |
| karte | normal | dark | 424x88 | 0 |
| karte | focus | dark | 424x88 | 0 |
| karte | hover | dark | 424x88 | 0 |
| header | normal | dark | 424x96 | 0 |
| header | focus | dark | 424x96 | 0 |
| header | hover | dark | 424x96 | 0 |
| tabbar | normal | dark | 424x96 | 0 |
| tabbar | focus | dark | 424x96 | 0 |
| tabbar | hover | dark | 424x96 | 0 |

ピクセル判定: 差分0（18 件）
