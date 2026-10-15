# AY-4a 受入結果（チェック欄の共通部品 CheckboxControl・一覧表の選択欄 2 件）

- 設計: docs/handoff/ay4a-checkbox/design.md。基準: origin/main（作業ツリーの起点）。
- 方式: AY-3b（ay3b-acceptance.md）と同じ。「前」= origin/main の frontend を `git archive` で取り出し `npx vite build` した CSS（index-CXcTNyy5.css）と、その DataTable.tsx。「後」= 作業ツリーの `npm run build` の CSS（index-B0qRJiO-.css）と、その DataTable.tsx。DOM はどちらも DataTable を renderToStaticMarkup した HTML（手書きしない。ay4a-render.tsx）。本番 CSS は使っていない（origin/main の build と本番が同一とは限らないため、コードの出どころが同じ origin/main の build を採用）。
- 条件: 幅 390/1280 × ライト/ダーク × 未選択/全選択/一部選択（見出しの input に indeterminate=true を前後同じ手順でページ側から設定。静的 HTML には DOM プロパティが出ないため）。欄は見出し 1 + 行 2 の 3 つ。計 12 条件 × 3 欄。
- 比較した項目: width/height/margin 4 辺/cursor/accent-color/outline（style・width・color）/display/vertical-align と実測の矩形幅・高さ、checked、indeterminate。比較した値の数 612。
- スクリプト: ay4a-measure.cjs（+ ay4a-render.tsx）。生 JSON: ay4a-measure.json。比較: ay4a-measure-compare.txt。スクリーンショット（1280、見出し付き表の左上）: ay4a-before-*.png・ay4a-after-*.png（light/dark × none/all/some）。
- 未実施: 実アプリ画面での撮影（fixture のみ。表以外の外側の枠は再現していない）。フォーカス時の輪（focus-visible）は設計の比較項目外。

## 結果

| 項目 | 前 → 後 | 件数 |
|---|---|---|
| accent-color（ライト） | auto → rgb(30, 58, 138)（--accent） | 18 |
| accent-color（ダーク） | auto → rgb(91, 141, 217)（--accent） | 18 |
| width/height（16×16）・margin（0）・cursor（pointer）・outline・display（inline-block）・vertical-align（baseline）・矩形・checked・indeterminate | 差 0 | 0 |

## 判定
- 差があった項目は accent-color の 1 つだけ（36 欄すべて。auto → --accent の値）。設計「見た目の差が設計どおり」に合致。
- 注: accent-color はチェックが入った・一部選択のときに見た目へ出る（未選択では見えない）。
- 注: SSR 描画時に useLayoutEffect の警告が出る（測定用の静的描画だけ。アプリは client のみで描画）。
