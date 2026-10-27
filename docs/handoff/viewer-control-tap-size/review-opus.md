# review-opus: 便10（検索欄とプルダウンをお手本の48dpにそろえる）の独立審査記録

審査担当: Opus（設計担当とは別文脈の独立審査。ADR-1015 の B 区分）／審査日 2026-10-27
対象: docs/handoff/viewer-control-tap-size/recon.md ・ docs/handoff/viewer-control-tap-size/design.md
**実装前に2回実施**（v1 → BLOCK、v2 → REVISE）。この端末には Playwright のブラウザが無いため、
審査はコード・CSS の読み取りと算数の検算で行い、ブラウザでの実測はしていない。

## 第1回（設計 v1）: **VERDICT: BLOCK**

v1 は「操作ボタンを `size="lg"`＋余白を詰める＝文字16px・行48px」という設計だった。

| # | 重大度 | 指摘 | 結末 |
|---|---|---|---|
| 1 | ブロック | 横幅の算数が約30px 甘い。①ボタンの枠線 `border: 1px solid transparent`（`frontend/src/components/Button.css:10`）は幅に入り **+2px／ボタン** ②絞り込みボタンの既定表示は「絞り込み **(1)**」（`frontend/src/pages/viewer/InventoryView.tsx:73`・`:131-136`。既存検査 `frontend/tests-e2e/visual-language/viewer-top-compact.spec.ts:181-184` が証拠）。採用案は 360px で **22px 不足**＝シリーズ名が消える | **訂正**。recon §4 の表を作り直した |
| 2 | ブロック | recon の「幅が足りなければ既存検査 A2・A3 が赤になる」は誤り。シリーズが `flex: 1 1 0`（`frontend/src/pages/viewer/viewer.css:37-43`）＝**flex-basis 0 は折り返し判定に寄与しない**ので全部緑のまま | **訂正**。recon §5 を書き換え、「切れを直接測る検査だけが歯止め」に改めた |
| 3 | 修正要 | `MAX_TOP_Y = 128` は**3本の spec に複製**されている。1本だけ直すと残り2本が赤 | **反映**。3本同時に更新する設計にした |
| 4 | 修正要 | 128→136 に上げる4px に根拠が無い。`B1` が「48px 以上」の下限なので抜け道が残る | **反映**。上限は計算値どおり **132**、B1・B4 は「48px ちょうど」の等値にした |
| 5 | 修正要 | 並び替えに最長項目を選んだときの悪化が未測定 | **反映**。B7b として基準に入れた |
| 6 | 助言 | `tightPadding` と `variant="tab"` の干渉・`ButtonLink` との非対称 | **解消**。`size` の値を足す方式に変えたので tab 除外を自動継承 |
| 7 | 助言 | 第4の案の探索（ページCSS・既存 variant・既存トークンなど7通りを自分で試した結果、他に道は無い） | **確認**。金型に足す方針は妥当と判定 |
| 8 | 助言 | ⑤ の測り忘れ（`npx tsc --noEmit` が CI に無いこと等） | **反映**。U4 に明記 |

## 第2回（設計 v2）: **VERDICT: REVISE**

v2 は PO 判断を受けて「文字 13.6px・新しい `size="tap"`・入力欄の高さに段を追加」に変えた設計。
**第1回の指摘1〜8 は8件すべて潰れている**と判定された。採用案の合計 **320.0px ≤ 328px** は
審査担当の独立計算と一致。お手本 13.4dp の逆算も「原文と整合し、独立な2経路が一致する妥当な読み」と判定。

| # | 重大度 | 指摘 | 対応 |
|---|---|---|---|
| 1 | 修正要 | `field-h-xl` はメディアクエリの外なので **PC も 36px→48px になる**。PC の操作台には 36px の兄弟が並ぶ（`frontend/src/components/ContentToolbar.tsx:78`・`:90`、`frontend/src/pages/viewer/InventoryView.tsx:543`・`:604`）＝PC に新しい不ぞろいを作る。PO の GO はスマホの話で PC に及んでいない | **設計変更**。段を `field-h-tap` に改名し **`@media (max-width: 767px)` の中だけ**に置き、呼び出し側は `field-h-md` と**併記**（PC=36px・スマホ=48px）＝**PC は1px も動かない** |
| 2 | 修正要 | `frontend/tests-e2e/visual-language/viewer-inventory-mobile-filter.spec.ts:26-27` の「一度に見える行が8〜20件」への影響が未検討。本便で選択画面の検索欄 +4px・フッタ +4px になる | **反映**。B11 として「変更しない・確認のみ」で基準に入れた |
| 3 | 修正要 | recon §4 の「いま」の行が2か所まちがい（枠線2pxの落ち・隙間24の足し忘れ）。**現状の余りは 38px ではなく 12px** | **訂正**。recon §4 と ⑩ を 12px に直した |
| 4 | 修正要 | B6 が測る「決定する」は**先頭画面に存在しない**（`frontend/src/pages/viewer/InventoryView.tsx:328` が `filterView === "root"` のとき `undefined`）。locator が見つからず「赤」の意味が壊れる | **反映**。B5・B6 に「絞り込みを開く→`viewer-provider-row` を押す→測る」の道順を明記 |
| 5 | 助言 | 136 の4px は依然ゼロ根拠。計算値は決定論的に 132 | **反映**。132 にした |
| 6 | 助言 | B7b の閾値「0px より大きい」は緩すぎる（見込み 21.6px）。1文字分にすべき | **反映**。13.6px 以上にした |
| 7 | 助言 | `size="tap"` と `iconOnly` の併用で 48px にならない（`@media` の `.comp-btn.comp-btn--icon-only` が勝つ） | **反映**。`.comp-btn--tap.comp-btn--icon-only` を1規則足し、見本は文字ボタンだけにする |
| 8 | 助言 | 段のセレクタに `.comp-select__control` / `.comp-field__select` の併記が無い。横展開先（`frontend/src/pages/inventory/InventoryToolbar.tsx:72`・`:85`）に `SelectControl` が居るので必ず踏む | **反映**。最初から4本立てで書く |
| 9 | 助言 | 13.4dp の逆算は「`sort_menu` と `filter` の余白＋絵文字が同幅」という**仮定1つ**に依存し、独立検証は不可能（原文が「フォントサイズの正確な値は原理的に取得不能」と明記）。「販売中のみ」の一致は恒等式なので検証になっていない | **反映**。recon §1 に仮定と限界を明記。PO 決定（13.6px）は2経路一致により妥当として維持 |
| 10 | 助言 | 小さな事実誤り3件（既存テストの件数・呼び出し側の行番号・お手本 146dp の出典行） | **訂正**。現物で確認して直した |

## 審査が「問題なし」と確認した項目（抜粋）

- `size="tap"` を `frontend/src/components/buttonAppearance.ts:36` の三項に足すと `variant="tab"` では付かない（既存規則の継承）。
- `@media (max-width: 767px)` の中に `.comp-btn--tap` を足す必要があること（`.comp-btn` の44pxが後勝ちするため）。
- `.comp-btn--icon-only { padding: 0 }` は `.comp-btn--tap` より後ろなので余白0が勝つ（意図どおり）。
- `ButtonSize` を `Record` で網羅している箇所は0件＝値の追加で型が壊れる場所は無い。
- `.comp-field__input.field-h-tap`（0,2,0）は `.comp-field__input`（0,1,0）に**詳細度で勝つ**ので読み込み順に依存しない。`TextFieldControl` は裸の `<input>` で `.comp-field` 祖先を持たないため `.comp-field--sm/--lg` との競合も起きない。
- 「決定する」は `size="lg"` で 48px ちょうどになる（`.comp-btn--full` は幅だけ・`frontend/src/components/Drawer.css:100-108` のフッタは引き伸ばさない）。
- B7b の経路は実在（`viewer-sort-option-<value>`。最長は「在庫が多い順」6字。既存 `frontend/tests-e2e/visual-language/viewer-choice-sheet.spec.ts:289` が同じ形で押している）。
- `MAX_TOP_Y` を使う3本の他のテストは、48px 化・13.6px 化で**赤にならない**（唯一の未検証が B11）。
- `frontend/scripts/` を全部読み、本便で引っかかる関所は `frontend/scripts/check-new-tokens.js` だけ。

## 設計担当の最終対応

第2回の指摘1〜10 を**すべて設計に反映**した。加えて、審査が指摘した「B7a は直した後も緑なので
それだけでは空振りか分からない」問題に対し、**壊した状態を spec の中で作る** B7c・B7d を自分で追加した
（`page.addStyleTag` で文字16px／山形24pxに差し替え、**切れること**を assert する）。
これにより、ブラウザが無い端末でも「同じ測り方が切れを検出できる」ことを本物の Chromium の中で証明できる。
