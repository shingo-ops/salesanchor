# AY-5b 設計: 生ラジオの見張りを UI governance gate に足す

- 作成: 2026-10-16 Opus（Planner・Architect を兼ねる自己審査）
- 現在地: docs/handoff/ay5b-radio-guard/recon.md
- 手本: docs/handoff/ay4d-checkbox-guard/design.md（checkbox 種別を足した便）
- 対象 ADR: ADR-144（追記節を1つ足す）

## 1. 目的

金型を使わない生ラジオを AY-5 で 0 件にした。新しく書かれても止まるように、画面ルールの自動チェックに radio 種別を足す。2026-10-16 PO「y」。

## 2. 対象と対象外

- 対象: scripts/check-ui-governance.js、scripts/tests/test-ui-governance.js、docs/CC_UI_GOVERNANCE.md、docs/adr/ADR-144-ui-component-governance.md（追記節）、docs/specs/design-system/design.md（§AY-5b）。
- 対象外: 関所が見る範囲（今と同じ pages/ の .tsx だけ）。features/・components/ は今も 0 件（金型本体と試験を除く）。種別を列挙している古い 3 か所（.github/workflows/ui-governance-gate.yml:3-4 は CI 設定、docs/BRANCH_PROTECTION_SETUP.md:314、CLAUDE.md:119 は全員向けの規則文）。AY-4d と同じ扱いで、ADR の追記節に記録だけする。

## 3. 変更前後

### 3-1 scripts/check-ui-governance.js

- :8-12 冒頭コメント: 「検出対象（4種）」→「検出対象（5種）」。:11 の下に `*   - 生 <input type="radio">（AY-5b）` を1行足す。
- :260 countCheckbox の直後に、checkbox と同じ形で2つ足す。

```js
/**
 * 抽出した <input> タグが生ラジオかどうか判定する。
 * type="radio" / type='radio' / type={"radio"} / type={'radio'} を対象にする。
 * type={kind} のような動的な値は判定できないので数えない。
 */
function isRadioInput(tagStr) {
  return /\btype\s*=\s*(?:\{\s*)?["']radio["']/i.test(tagStr);
}

/**
 * コンテンツ内の生ラジオの件数を返す（ui-allow 除外済み）。
 */
function countRadio(content) {
  const lines = content.split('\n');
  let count = 0;
  for (const { tagStr, pos } of extractInputTags(content)) {
    if (!isRadioInput(tagStr)) continue;
    const lineIdx = getLineIndex(content, pos);
    if (!hasUiAllowBefore(lines, lineIdx)) count++;
  }
  return count;
}
```

- :313-320 countAll に `radio: countRadio(content),` を checkbox の次に足す。
- :355-360 typeLabels に `radio: '生<input type="radio">',` を足す。
- :362 の並びを `['select', 'input', 'tab', 'checkbox', 'radio']` にする。
- :419-429 export に `countRadio,` と `isRadioInput,` を足す。
- 触らない: extractInputTags・isDetectableInput・countInput・ui-allow の判定・対象範囲（:36・:88-90）。

### 3-2 scripts/tests/test-ui-governance.js

- :13-19 の require に countRadio を足す。
- T29 の後に、T21〜T29 と同じ形で T30〜T37 を足す（31 件→39 件）。
  - T30: `<input type="radio" checked={x} onChange={f} />` → countRadio 1
  - T31: type が別行 `<input\n  type="radio"\n  checked={x}\n/>` → 1
  - T32: `<input type={"radio"} />` と `<input type={'radio'} />` → 2
  - T33: `{/* ui-allow: 移行のため (#123) */}\n<input type="radio" />` → 0
  - T34: 金型 `<Radio checked={x} label="a" />\n<RadioControl checked={x} />\n<ChoiceCardGroup options={o} />` → 0
  - T35: `<input type="checkbox" />\n<div role="radio" />\n<div role="radiogroup" />` → 0
  - T36: `countInput('<input type="radio" />')` → 0（既存の input 種別と重ならない）
  - T37: `<input type={kind} />` → countRadio 0

### 3-3 docs/CC_UI_GOVERNANCE.md

- :25 の checkbox 行の次に行を足す: `| 生 \`<input type="radio">\` | \`<Radio>\`（文字と並ぶ欄）/ \`<RadioControl>\`（表の中・色見本など単独の欄）を使うこと |`
- :30 の注記「生 `<input type="radio">` も使わない…（CI ではまだ止まらない。AY-5b で提案）」は表に移したので消す。

### 3-4 docs/adr/ADR-144-ui-component-governance.md

- ファイルの末尾（AY-4d 追記節の後）に節を足す。

```md
## 2026-10-16 追記: 生ラジオを種別に追加（AY-5b）

- PO 決定: 2026-10-16「y」。CI ゲート（§2）の検出種別に `radio`（生 `<input type="radio">`）を足した。種別は 4 から 5 になった。仕組みは AY-4d 追記と同じで、改訂案（全件検査）への切替ではない。AY-4d 追記の「生 radio は対象外」はこの節で置き換える。
- 判定・対象・既知の穴は AY-4d 追記の checkbox と同じ（type の値が radio であることだけが違う）。今の pages/ の生ラジオは 0 件（AY-5 #4365 で載せかえ済み）。
- 試験: scripts/tests/test-ui-governance.js は 31 件から 39 件（T30〜T37）。
- 種別の列挙が古い 3 か所（AY-4d 追記に記載）は radio も含まないまま。今回も触らない。
- 設計: docs/handoff/ay5b-radio-guard/design.md。
```

- 見出しの追加は無い（追記節は本文中の ## 見出し。ADR の題・状態は変えない）。それでも `node scripts/generate-adr-index.js` を走らせ、docs/adr/README.md に差分が出たら一緒にコミットする。

### 3-5 docs/specs/design-system/design.md

- §AY-5 の残件⑤（:4265）の次に `#### AY-5b 生ラジオの見張り（2026-10-16）` を足す。内容は PO 決定・変更（3-1〜3-4 の要約）・試験 39 件・範囲（pages/ のみ）・設計リンク。:4264 の「AY-5b として別に提案」は書き換えない（その時点の記録）。

## 4. 影響範囲

- 関所は PR の変更ファイルだけを見て、BASE と HEAD の件数を比べる。今の pages/ の生ラジオは 0 件なので、既存の PR が新たに赤になることは無い。
- 画面・API・DB は変わらない。
- 呼び出し元: check-ui-governance.js は .github/workflows/ui-governance-gate.yml:39 からだけ実行される。export を使うのは試験ファイルだけ。

## 5. 代替案

- ESLint の規則で止める: 今の関所と二重になる。既存の関所に種別を足すほうが小さい（AY-4d と同じ判断）。
- 全件検査（ADR-144 改訂案）へ切り替える: 範囲が大きいため今回はしない。

## 6. リスクと対処

- 波括弧付きの `type={"radio"}` は input 種別でも数えられ、違反が2行出る（AY-4d 追記の checkbox と同じ動き）。止める側に倒れるので直さない。
- 誤検知（JSX コメントの中など）が出たら ui-allow（理由と番号）で外せる。

## 7. 受入条件

| 基準 | 検証方法 |
|---|---|
| 試験 39 passed / 0 failed | `node scripts/tests/test-ui-governance.js` |
| pages/ に生ラジオを1行足すと関所が exit 1、違反行に `生<input type="radio">` が出る | 使い捨ての複製（/tmp）でコミットを作り、BASE_SHA・HEAD_SHA を渡して `node scripts/check-ui-governance.js` を実行 |
| 同じ行に ui-allow を付けると exit 0 | 同上 |
| 今の main 相当（BASE=HEAD=origin/main）で exit 0 | 同上 |
| CI の UI governance gate が緑 | PR の checks |
| ADR index に差分なし、または差分をコミット済み | `node scripts/generate-adr-index.js` の後に git status |

## 8. 維持の仕組み

- 守り手: scripts/check-ui-governance.js（必須チェック UI governance gate、main ルールセット 15777895）と scripts/tests/test-ui-governance.js（同じ workflow の :33 で実行）。
- 切り戻し: この PR の merge commit を revert する（DB への影響なし）。

## 9. 外部・過去事例

- 外部事例: 不要。自社の既存の関所に同じ形の種別を1つ足すだけで、新しい技術を選ばないため。
- 過去事例: AY-4d（#4360）の checkbox 種別。

## 10. 設計審査（Opus 自己審査）

- 判定: APPROVE。
- 根拠: 変更前後を行番号付きで書いた（recon の行番号と一致）。受入条件はすべてコマンドで○×が決まる。対象外とその理由を書いた。PO の判断が要る点は無い（PO「y」で範囲が決まっている）。
- 未解決事項: なし。
