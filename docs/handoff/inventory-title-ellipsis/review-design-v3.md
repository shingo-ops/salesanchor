# 設計再審査: 在庫表の商品名を「…」で省く（design.md 第3版）

審査役: Opus（読み取りのみ）。第2版との差分（diff design-v2.md design.md）と、origin/main = 95e623fd3・GAS 版18（sha 8d63c62f2b8e）の実物で確かめた。

## 第2版の指摘の反映（【事実】）
- A1（空のセルの最小幅）: 反映済み。
  - 最小幅は `.inventory-cell__wrap:not(:empty)` と `td.col-wrap .cell-wrap:not(:empty)` のときだけ付く。
  - アプリは空の値を `""`（inventoryColumns.tsx:169・:178）か null／undefined（viewerColumns.tsx:107・:113）で描く。どちらも文字のノードを作らないので、span は空になり `:empty` に当たる。
  - GAS は `'<span class="cell-wrap">' + escHtml('') + '</span>'` で、中身は空文字。空白も入らない。
  - 詳しさ（0,2,0）は元の規則（0,1,0）より後ろにあり、stylelint の no-descending-specificity（frontend/.stylelintrc.json）にも当たらない。
- A2（ADR-1014 の見出しの番号）: 番号なしに直っている。ADR-1014:40・:68 と同じ形。
- A3（K6 (b) の行と段）: 判定に使うのが日本語の段に決まった（約37文字 ＞ 上限の約26文字）。行が実在する根拠には、PO の画面写しが挙がっている。ドラゴンボールのタブも同じ写しが根拠。
- B1〜B3: 反映済み（K5 は任意、短い発送のリスクを明記、ADR-067 の表に式と 100px を並べて書く）。

## 必須の修正
なし。

## 推奨
- B1 空のセルの試験は、`textContent === ""` よりも、`expect(el.matches(":empty")).toBe(true)`（または `toBeEmptyDOMElement()`）で直接確かめるとよい。CSS が当たる条件そのものを見ることになる。
- B2 K6 (a) は、窓の幅によっては × になることがある（設計 1・5 にあるとおり、縮みは残す設計）。× のときは窓の幅と倍率を添えて PO に返し、上限幅のトークンを調整する、と運用で決めておくとよい。

VERDICT: APPROVE
