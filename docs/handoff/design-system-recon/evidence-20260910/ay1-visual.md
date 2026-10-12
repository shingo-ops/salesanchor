# AY-1 外観一致（TextFieldControl 裸 B ＝ ラベル付き TextField 内 L）

chromium 147.0.7727.15／幅1280と375／light／比較項目 28（+focus 状態）／console 警告: なし

| 幅 | size | 状態 | 差分件数 | height(L/B) | min-height(L/B) |
|---|---|---|---|---|---|
| 1280 | sm | normal | 0 | 30.3906px/30.3906px | 28px/28px |
| 1280 | sm | focus | 0 | 30.3906px/30.3906px | 28px/28px |
| 1280 | sm | disabled | 0 | 30.3906px/30.3906px | 28px/28px |
| 1280 | md | normal | 1 | 39.6094px/39.6094px | auto/0px |
| 1280 | md | focus | 1 | 39.6094px/39.6094px | auto/0px |
| 1280 | md | disabled | 1 | 39.6094px/39.6094px | auto/0px |
| 1280 | lg | normal | 0 | 50px/50px | 44px/44px |
| 1280 | lg | focus | 0 | 50px/50px | 44px/44px |
| 1280 | lg | disabled | 0 | 50px/50px | 44px/44px |
| 375 | sm | normal | 2 | 30.3906px/44px | 28px/44px |
| 375 | sm | focus | 2 | 30.3906px/44px | 28px/44px |
| 375 | sm | disabled | 2 | 30.3906px/44px | 28px/44px |
| 375 | md | normal | 0 | 44px/44px | 44px/44px |
| 375 | md | focus | 0 | 44px/44px | 44px/44px |
| 375 | md | disabled | 0 | 44px/44px | 44px/44px |
| 375 | lg | normal | 0 | 50px/50px | 44px/44px |
| 375 | lg | focus | 0 | 50px/50px | 44px/44px |
| 375 | lg | disabled | 0 | 50px/50px | 44px/44px |

合計差分: 9

## 差分の値

| 幅/size/状態 | 項目 | L | B |
|---|---|---|---|
| 1280/md/normal | min-height | auto | 0px |
| 1280/md/focus | min-height | auto | 0px |
| 1280/md/disabled | min-height | auto | 0px |
| 375/sm/normal | min-height | 28px | 44px |
| 375/sm/normal | height | 30.3906px | 44px |
| 375/sm/focus | min-height | 28px | 44px |
| 375/sm/focus | height | 30.3906px | 44px |
| 375/sm/disabled | min-height | 28px | 44px |
| 375/sm/disabled | height | 30.3906px | 44px |

## 原因確認

① 幅375/sm/通常: FormField.css からモバイル @media (max-width:767px) ブロックを除去（除去対象を検出: true）して L と B を再測定。L: min-height 28px height 30.3906px / B: min-height 28px height 30.3906px。差分項目: 0件 → B が L と一致（想定どおり）

② 幅1280/md/通常: L の親 .comp-field が flex（既定）のとき L min-height=auto。親を display:block にすると L min-height=0px（B は 0px）。display:block 後の L と B の差分項目: 0件 → 想定どおり（flex 子の computed 値の差）

## 既知の例外（設計 §AY 受入の①②）

- ① 幅375px（767px以下）の sm: 裸の本体はモバイル用タップ領域の規則（FormField.css の @media (max-width:767px)）が後勝ちで min-height 44px（height 44px）。L は 28px（height 30.3906px）。
- ② 幅1280px の md: L の min-height は親 .comp-field が flex のため computed で auto、裸の本体は 0px。height は両者 39.6094px で同じ。
