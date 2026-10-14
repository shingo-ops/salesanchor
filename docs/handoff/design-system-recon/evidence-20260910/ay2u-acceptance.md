# AY-2u 受入結果

| 基準 | 結果 | 根拠 |
|---|---|---|
| frontend・scripts・.github で 0 件 | 合格 | 変更後 `git grep` は tokens.css 以外 0 件（変更前も 355 行の 1 件のみ） |
| dist CSS の差分は当該宣言 1 つのみ | 合格 | ay2u-css.diff（`--input-select-min-w: 280px;` の 1 行削除のみ）、after に同名 0 件 |
| 監査 31→30、他は同一 | 合格 | ay2u-audit.diff（1 行目の件数と当該 1 行のみ） |
| 品質 | 合格 | generate・tsc・lint・check:all・build・build-storybook は exit 0。test:coverage は既定 5000ms で StaffFormButtonMigration.test.tsx 1 件がタイムアウト、--testTimeout=60000 で再実行し exit 0 |

同梱: ay2u-audit-before.txt / ay2u-audit-after.txt / ay2u-audit.diff / ay2u-css.diff
