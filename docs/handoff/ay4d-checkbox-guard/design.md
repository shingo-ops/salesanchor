# AY-4d design: 生チェック欄の見張りを UI governance gate に足す

- 作成: 2026-10-16 Opus（Planner）/ 基点 origin/main 6b316f7f7
- 現在地: docs/handoff/ay4d-checkbox-guard/recon.md
- 関連 ADR: docs/adr/ADR-144-ui-component-governance.md（§2 CI ゲート、2026-09-10 改訂案は Proposed のまま触らない）

## 1. 目的（PO 決定）

- 2026-10-16 PO「y」: 画面ルールの自動チェック（check-ui-governance）に「金型を使わないチェック欄を止める」項目を足す。
- KGI: `frontend/src/pages/` の .tsx に生の `<input type="checkbox">` を新しく書いた PR は、必須チェック `UI governance gate` が赤になり main へマージできない。

## 2. 対象と対象外

対象:
1. scripts/check-ui-governance.js に種別 `checkbox` を足す。
2. scripts/tests/test-ui-governance.js に checkbox の試験を足す。
3. docs/CC_UI_GOVERNANCE.md:19-27 の禁止表に1行足す。
4. docs/adr/ADR-144-ui-component-governance.md に追記節を足す（本文は書き換えない）。
5. frontend/src/company-forms.css:100・:135 のコメントを今の事実に直す（規則そのものは触らない）。
6. docs/specs/design-system/design.md に §AY-4d の記録を足し、:4246 の残り③を「済」にする。

対象外（理由）:
- 生 radio（pages/ に4件）: PO の y はチェック欄だけ。
- features/・components/ の検査: 関所の範囲を広げると select・input・tab の判定も変わる。ADR-144 改訂案（全件検査）の切替で扱う。
- company-forms.css の focus 規則の撤去: 金型 Checkbox 5件と文字入力欄に今も当たる。消すと見た目が変わり得るので、前後実測の便で別に判断する。
- .github/workflows/ui-governance-gate.yml:6 の古い「非必須」コメントと ADR-144:103 の「（非必須）」: CI 設定ファイルは触らない。ADR-144 の追記節に事実（必須チェックに登録済み）を書くだけにする。
- 動的な type（`type={kind}` など）: 値が決まらないので数えない。
- 検出対象を列挙している他の記載（.github/workflows/ui-governance-gate.yml:3-4、docs/BRANCH_PROTECTION_SETUP.md:314、CLAUDE.md:119）: CI 設定と全員向けの規則文なので今回は触らない。checkbox を含まないまま古くなることを ADR 追記節と design.md §AY-4d の残りに書く。
- PO への報告（PR 本文・完了報告）には「features/ と components/ に書いたチェック欄は止まらない（今はどちらも金型本体以外 0 件）」を1行入れる。

## 3. 変更前後

### 3-1 scripts/check-ui-governance.js

変更前 :213-218 `isDetectableInput` は text・search・省略だけを true にする（このまま残す）。

追加（:232 の `countInput` の後ろ）:

```js
// ---------------------------------------------------------------------------
// 検出ロジック: 生 <input type="checkbox">（AY-4d）
// ---------------------------------------------------------------------------

/**
 * 抽出した <input> タグが生チェック欄かどうか判定する。
 * type="checkbox" / type='checkbox' / type={"checkbox"} / type={'checkbox'} を対象にする。
 * type={kind} のような動的な値は判定できないので数えない。
 */
function isCheckboxInput(tagStr) {
  return /\btype\s*=\s*(?:\{\s*)?["']checkbox["']/i.test(tagStr);
}

/**
 * コンテンツ内の生チェック欄の件数を返す（ui-allow 除外済み）。
 */
function countCheckbox(content) {
  const lines = content.split('\n');
  let count = 0;
  for (const { tagStr, pos } of extractInputTags(content)) {
    if (!isCheckboxInput(tagStr)) continue;
    const lineIdx = getLineIndex(content, pos);
    if (!hasUiAllowBefore(lines, lineIdx)) count++;
  }
  return count;
}
```

変更 :285-291 `countAll` に `checkbox: countCheckbox(content),` を足す。
変更 :326-330 `typeLabels` に `checkbox: '生<input type="checkbox">',` を足す。
変更 :332 `['select', 'input', 'tab']` を `['select', 'input', 'tab', 'checkbox']` にする。
変更 :389-397 export に `countCheckbox`、`isCheckboxInput` を足す。
変更 :8 `検出対象（3種）:` を `検出対象（4種）:` にし、:10 の `生 <input type="text"|"search"|type省略>` の行の次に ` *   - 生 <input type="checkbox">（AY-4d）` を1行足す。

触らない: getChangedFiles・showFile・対象ディレクトリ・除外・ui-allow の判定・select/input/tab の判定。

### 3-2 scripts/tests/test-ui-governance.js

:14-19 の require に `countCheckbox` を足す。:211 の後ろ（結果サマリの前）に足す:

| 番号 | 入力 | 期待 |
|---|---|---|
| T21 | `<input type="checkbox" checked={x} onChange={f} />` | countCheckbox 1 |
| T22 | `<input\n  type="checkbox"\n  checked={x}\n/>`（type が別行） | 1 |
| T23 | `<input type={"checkbox"} />` と `<input type={'checkbox'} />` を並べた文字列 | 2 |
| T24 | 直前行に `{/* ui-allow: 移行のため (#123) */}` を置いた `<input type="checkbox" />` | 0 |
| T25 | `<Checkbox checked={x} label="a" />` と `<CheckboxControl checked={x} />` | 0 |
| T26 | `<input type="radio" />` と `<div role="checkbox" />` | 0 |
| T27 | `<input type="checkbox" />` を countInput に渡す（文字列の形の type は既存の input 種別と重ならない） | countInput 0 |
| T28 | `<input type={kind} />`（動的な type） | countCheckbox 0 |
| T29 | `<input type={"checkbox"} />` を countInput に渡す（既存の動きを固定: :214 の正規表現は波括弧を見ないので type 省略扱いになる） | countInput 1 |

各行とも assert は1回（T23・T25・T26 は2つの要素を1つの文字列に並べて1回）。試験は 22 件から 31 件になる。

### 3-3 docs/CC_UI_GOVERNANCE.md

:24 の生 input 行の次に `| 生 \`<input type="checkbox">\` | \`<Checkbox>\`（文字と並ぶ欄）/ \`<CheckboxControl>\`（表の中など単独の欄）を使うこと |` を足す。

### 3-4 docs/adr/ADR-144-ui-component-governance.md

末尾に追記節「2026-10-16 追記: 生チェック欄を種別に追加（AY-4d）」。書くこと: PO 決定（2026-10-16 y）、種別 checkbox の判定（type が checkbox の文字列・波括弧付き文字列、動的は対象外）、対象は §2 と同じ pages/、試験 31 件（改訂案 :126 の「22ケース」は 31 件になった。全件検査へ切り替えるときは 31 件と checkbox 種別を引き継ぐ）、波括弧付きは input 種別でも数えること、§6 の既知の穴、他の古くなる列挙3か所、関所は main のルールセットで必須チェック（UI governance gate、ruleset 15777895）に登録済みであり :103 と workflow:6 の「非必須」は古い記載であること。追記後に `node scripts/generate-adr-index.js` を実行する。

### 3-5 frontend/src/company-forms.css:100・:135

変更前: `/* 一行入力は金型（FormField.css）が正本。この focus 規則は .form-row 内の checkbox のフォーカス表示を保つために残す（§AY AY-2c） */`
変更後（2か所とも）: `/* 一行入力は金型（FormField.css）が正本。この focus 規則は .form-row 内の金型 Checkbox と文字入力欄の input にも当たっているため残す。撤去は見た目の前後実測をしてから判断する（§AY AY-2c・AY-4d） */`

### 3-6 docs/specs/design-system/design.md

:4246 の後ろに `#### AY-4d 生チェック欄を UI governance gate の種別に追加（2026-10-16）` 節。PO 決定・設計の場所・変更・試験件数・対象外・残り（features/ の検査は全件検査の切替で、focus 規則の撤去は前後実測の便で、checkbox を含まないまま古くなる列挙3か所＝ui-governance-gate.yml:3-4・BRANCH_PROTECTION_SETUP.md:314・CLAUDE.md:119）を書く。:4246 の③に「→ AY-4d で済」と足す。①は「コメントを今の事実に直した（AY-4d）。規則の撤去は別判断」と足す。

## 4. 影響範囲

- 関所は PR の pages/ 変更ファイルにだけ働く。pages/ の生チェック欄は今 0 件なので、既存のファイルを触る PR が新たに赤になることは無い（ファイルごとに BASE と HEAD を比べるため）。
- 呼び出し元は .github/workflows/ui-governance-gate.yml:33・:39 だけ（frontend/package.json・husky には無い、04-callers.txt）。
- 画面・API・DB は変わらない。CSS はコメントだけ。

## 5. 代替案

- A（採用）: 今の関所に種別を1つ足す。小さく、ADR-144 の Accepted 本文の形のまま。
- B: features/ も対象に広げる。select・input・tab の判定範囲も変わるため PO の y の範囲を超える。
- C: ESLint の no-restricted-syntax で `input[type=checkbox]` を禁止する。全ディレクトリに効くが、既存の ESLint 設定（ADR-067）を変える別の判断になる。

## 6. リスクと対処

| リスク | 対処 |
|---|---|
| 正規表現が金型の `<Checkbox>` を数える | extractInputTags は `<input` の直後が空白・`>`・`/` のときだけ拾う（:181-186）。T25 で確認 |
| `role="checkbox"` を数える | input タグだけを見る。T26 で確認 |
| 既存種別 input の件数が変わる | isDetectableInput は触らない。T27 と既存 T1〜T20 で確認。波括弧付き `type={"checkbox"}` は今も input 種別で数えられ（:214-215）、足すと違反が2行出る。止める側に倒れるので直さず、T29 で今の動きを固定する |
| 正規表現の既知の穴（審査 r1 実測 /tmp/CC報告ファイル/ssot-checkbox/ay4d/review/cases-out.txt） | 誤検知: JSX コメント・文字列の中・`data-type="checkbox"`。取りこぼし: type より前の文字列属性に `>` がある、テンプレートリテラル（後者は input 種別が赤にする）。今の pages/ では両方 0 件（K3）。ADR 追記節に書く |
| 関所が通らなくなりマージできない | この PR は pages/ を触らないので関所はスキップで緑。試験は CI の :33 で走る |

## 7. 受入条件

| 基準 | 検証方法 |
|---|---|
| K1 試験が 31 件すべて通る | `node scripts/tests/test-ui-governance.js` が exit 0、「31 passed / 0 failed」 |
| K2 pages/ に生チェック欄を1つ足すと関所が赤、ui-allow を付けると緑 | 実装コミット後、/tmp/CC報告ファイル/ssot-checkbox/ay4d/k2/ に `git clone --local` で使い捨ての複製を作る（作業場所と本店は触らない）。複製で pages/ の .tsx 1つに `<input type="checkbox" />` を1行足してコミットし、`BASE_SHA=HEAD~1 HEAD_SHA=HEAD node scripts/check-ui-governance.js` が exit 1 で「生<input type="checkbox">」と出ることを確かめる。続けて直前行に ui-allow を足してコミットし、`BASE_SHA=HEAD~2 HEAD_SHA=HEAD` で exit 0 になることを確かめる。期待: 赤の回は違反の行が `[生<input type="checkbox">] BASE=0 → HEAD=1` の1行だけ（2行出たら設計違い）。注意: 複製は消さずに置く（削除は禁止）。やり直すときは別名のフォルダ（k2-2/ など）。コマンドは `git -C <複製の絶対パス>` と `cd <複製の絶対パス> && node scripts/check-ui-governance.js` の形 |
| K3 今の pages/ 全 .tsx で countCheckbox の合計が 0 | `node -e` で pages/ 配下の .tsx（stories・design-system・design-preview を除く）を全部読み、走査本数と合計を出す。期待「走査 189 本・合計 0」（本数が違えば止めて報告） |
| K4 金型本体3件は数える形である（判定の正しさ） | components/Checkbox.tsx・CheckboxControl.tsx・Toggle.tsx を countCheckbox に渡すと各1以上（pages/ ではないので関所の対象外であることも併記） |
| K5 CI の UI governance gate が緑 | PR の checks |
| K6 文書の記載 | CC_UI_GOVERNANCE.md の表に1行、ADR-144 追記節、design.md §AY-4d がある。`node scripts/generate-adr-index.js` 実行後に `git diff --exit-code docs/adr/README.md` が 0、または差分をコミット済み |

## 8. 維持の仕組み

- 守り手: /Users/tanizawashingo/salesanchor/scripts/check-ui-governance.js（必須チェック UI governance gate）と /Users/tanizawashingo/salesanchor/scripts/tests/test-ui-governance.js（同じジョブで毎回走る）。
- 将来 ADR-144 改訂案の全件検査に切り替えるときは、checkbox の種別も引き継ぐ（追記節に書く）。

## 9. 外部・過去事例の参照と我々への応用

- 外部事例: 不要。既存の自社の関所に同じ形の種別を1つ足すだけで、新しい技術の選択が無い。
- 過去事例: ADR-144 の生 select・生 input の検出（scripts/check-ui-governance.js:153-232）。同じ抽出関数 extractInputTags と ui-allow の判定をそのまま使い、種別だけを足す。
