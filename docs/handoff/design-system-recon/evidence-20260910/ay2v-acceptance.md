# AY-2v 受入結果

基準: 実装時 HEAD a39fb988f（設計時 e6923ba61。tokens.css・index.css は同一）。

| 基準 | 結果 | 根拠 |
|---|---|---|
| frontend の差分が設計 §3 の 23 行の削除のみ | 合格 | tokens.css 15 行・index.css 8 行（4名 x :root と :root.force-dark）の削除のみ。削除前に各行の名前一致を確認、ずれなし |
| 18 件の名前が §2 範囲で 0 件（B1） | 合格 | ay2v-grep18.txt。docs/handoff・docs/audits を除くヒットは全て定義行 23 行のみ。docs/specs・docs/adr・コード・lp・scripts・.github にヒット 0 |
| 監査 30→12、消えた名前が 18 件と一致 | 合格 | ay2v-audit.diff（先頭の件数行と 18 名の行のみ。追加行は件数行の 1 行のみ）。残 12 名は設計 §3「触らない」と一致 |
| dev build CSS の差分が 18 名の定義 23 行の削除のみ（B2） | 合格 | ay2v-css.diff（`<` 23 行・`>` 0 行）。残す 12 名と --calendar-today-bg・--schedule-allday-row-h の件数は前後同一 |
| 画面の見た目が変わらない | 合格（根拠は CSS 差分） | 18 名以外の差分 0 |
| 品質（B3） | 条件付き合格 | generate:api-types・tsc・lint・check:all（dark-parity・color-token-sync を含む）・build・build-storybook は exit 0。test:coverage は既定 5000ms で 102 件失敗（65 件が 5000ms タイムアウト、機械負荷による）。--testTimeout=60000 で再実行し 1 件のみ失敗（BotFormButtonMigration.test.tsx、要素待ちの失敗）。同ファイルを単独で再実行すると 32 件全て成功 |
| 本番 CSS | 未実施 | マージ後に Opus が prod CSS を grep |

同梱: ay2v-audit-before.txt / ay2v-audit-after.txt / ay2v-audit.diff / ay2v-css.diff / ay2v-grep18.txt
