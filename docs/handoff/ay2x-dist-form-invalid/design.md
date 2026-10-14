# AY-2x 設計: 配信先フォームの text 入力3件を TextFieldControl へ移し、金型に invalid を足す

状態: 設計審査済み（Fable APPROVE、/tmp/CC報告ファイル/ssot-ay2x/design-review.md。MEDIUM-1・LOW-1〜3 を反映）。PO「y」2026-10-14（「赤枠の機能を足して3つの入力欄を移す。文字 13.6→14.4px・選択中の枠が共通の見た目になる。チェックボックスとボタンは別便」）。
mode: handoff。親: docs/specs/design-system/README.md。ADR-144 / ADR-067 / ADR-027 を継承。仕様の正: docs/specs/design-system/design.md:815（`invalid?: boolean`｜既存のエラー条件のまま外観へつなぐ。aria-invalid は呼び出し側が明示した属性だけを通し、自動付与・上書きしない）。:2369（invalid は AY-2 以降の便で設計する）を TextFieldControl について実装する便。
recon: docs/handoff/ay2x-dist-form-invalid/recon.md（生出力 /tmp/CC報告ファイル/ssot-ay2x/recon/、/tmp/CC報告ファイル/ssot-dtf/）。

## 1. 目的（PO が見える変化）
- スーパー管理 → 配信先管理 → 配信先の追加・編集ドロワーにある「クライアント名」「スプレッドシートID」「タブ名」の3欄が、ほかの画面の入力欄と同じ金型の見た目になる。
- 未入力のまま保存すると、今と同じ3欄が赤枠になる。赤はアプリ共通のエラー色（--danger）にそろう。
- 動き（入力・保存・エラー文・ヒント文・必須印）は変わらない。

## 2. 変更前後（実装はこの3ファイルと試験・story・docs だけ）

### 2-1. frontend/src/components/TextField.tsx:35-54
変更前（:41-52）:
```tsx
  function TextFieldControl({ size = "md", variant = "standard", className, id, ...rest }, ref) {
    const controlClass = [
      "comp-field__input",
      size !== "md" ? `comp-field__input--${size}` : "",
      variant !== "standard" ? `comp-input--${variant}` : "",
      className ?? "",
    ]
```
変更後:
- :35 の型 `TextFieldControlProps` の共通部に `{ invalid?: boolean }` を足す（`Omit<InputHTMLAttributes<HTMLInputElement>, "size"> & { invalid?: boolean } & (...)`）。
- 分割代入に `invalid = false` を足し、`rest` から外す（DOM 属性として出さない）。
- class の配列で、variant 行の直後に `invalid ? "comp-field__input--invalid" : "",` を足す。
- `aria-invalid` は付けない（design.md:815）。呼び出し側が渡した `aria-invalid` は `rest` でそのまま通る。
- ラベル付き `TextField`（:57-103）は変更しない。TextField は内部の TextFieldControl に invalid を渡さない（外側の comp-field--error で赤枠を出す今の作りのまま。TextField.test.tsx:34-38 の完全一致が変わらないこと）。
- ヘッダコメント（:1-）に invalid の1行を足す。

### 2-2. frontend/src/components/FormField.css
- §5（:114-119）の selector 一覧に `.comp-field__input.comp-field__input--invalid` を足す（詳細度 (0,2,0)。:47 の基本 (0,1,0) より強く、§5 と同じ強さ）。
- §7（:433-440）の selector 一覧に `.comp-field__input.comp-field__input--invalid:focus` を足す（(0,3,0)。:95 の focus (0,2,0) に勝つ）。
- 新しい色・数値は使わない（`var(--danger)`、`var(--danger-bg-subtle)` と、既存の `0 0 0 3px` の並びに足すだけ）。
- :10 付近の目次コメントの §5 に「invalid」と書き足す。
- invalid の見た目は variant="standard" で保証する（variant≠standard と併用すると、非 focus 時は variant の border-color が勝つ。本便は standard のみ）。design.md の §AY-2x にもこの1行を書く。
- stylelint の no-descending-specificity で止まる場合は、:434 と同じ書式の `-- intentional` コメントで受ける（新しい無効化方式は作らない）。それ以外で止まったら停止。

### 2-3. frontend/src/features/tcg-distribution/DistributionTargetForm.tsx:182-189 / :199-208 / :223-230
- import に `import { TextFieldControl } from "../../components/TextField";` を足す（ファイル内の既存 import の相対パス書式に合わせる。実ファイルで確認）。
- 3つの `<input` を `<TextFieldControl` に替え、`className={...dist-input...}` 行を `invalid={Boolean(errors.name)}`（spreadsheet_id、sheet_name も同様）に替える。
- id・type="text"・value・onChange・placeholder・autoComplete="off"・spellCheck={false} は逐語でそのまま。size は指定しない（md）。
- 触らない: label（:178-181 等）、必須印 span、`dist-field-hint`（:209-211）、`dist-field-error`（:190 等）、checkbox（:237-）、ボタン4件、ドロワー（:131-）、検証ロジック・保存処理。

### 2-4. frontend/src/features/tcg-distribution/distribution.css:322-342
- `.dist-input`、`.dist-input:focus`、`.dist-input--error` の3規則を削除する（使っていたのはこのフォームだけ。recon の dist-class-users.txt で、frontend 内の利用は2ファイルだけ）。
- `.dist-field`、`.dist-field label`、`.dist-field-hint`、`.dist-field-error`、`.dist-checkbox-row` は残す。

## 3. 触らない範囲
ラベルの見た目（.dist-field label の太字）、必須印、エラー文の色（--color-error のまま）、checkbox、ボタン、ドロワー、i18n キー、API・backend・DB・migrations・deploy.yml・scripts、ほかの TextFieldControl 利用 76 ファイル（invalid 未指定＝class が変わらない）、Select.tsx・Textarea.tsx（invalid の横展開はしない）。

## 4. 停止条件（該当したら直さずに止まり、Opus へ NEEDS_DECISION）
- B1: 390px または 1280px で、ドロワー本体（実物で最も近いスクロール祖先）の横 overflow（scrollWidth - clientWidth）が変更前より増える。
- B2: 3欄の DOM 属性（id・type・value・placeholder・autocomplete・spellcheck・aria-*）が、class 以外で変わる。または `invalid` という属性が DOM に出る。
- B3: TextFieldControl を使うほかの画面の class が変わる（invalid 未指定で comp-field__input--invalid が出る）。
- B4: TextField.test.tsx の既存試験が1件でも変わる・落ちる。
- B5: stylelint・check:all・check:new-tokens・check-ui-governance のどれかが、§2-2 の注記以外の理由で失敗する。

## 5. 試験
- frontend/src/components/TextField.test.tsx に追加:
  1. `<TextFieldControl invalid />` は class に `comp-field__input--invalid` を持ち、`invalid` 属性と `aria-invalid` 属性を持たない。
  2. `<TextFieldControl />` は `comp-field__input--invalid` を持たない。
  3. `<TextFieldControl invalid aria-invalid="true" />` は `aria-invalid="true"` を通す。
- DistributionTargetForm の試験（新規 frontend/src/features/tcg-distribution/DistributionTargetForm.test.tsx）: 実ファイルの props（form.txt :32 付近）に合わせて描画し、3欄が `comp-field__input` を持つこと、空のまま保存操作したとき3欄が `comp-field__input--invalid` を持ち、文字を入れた欄は外れること。API は既存試験の mock 書式（frontend/src 内の vi.mock の前例）に合わせる。描画に必要な mock が既存の前例で作れない場合は、この試験だけ省いて BLOCKED ではなく報告に書く。
- 既存の既知フレーク（test:coverage の無関係な timeout）は CI の必須チェックで判定する。

## 6. 実測（AY-2w と同じ方法。一時 spec はコミットしない）
- 条件: 390 / 1280px × ja / en × ライト / ダーク の8条件。dev server で配信先ドロワーを開く（super admin で開ける状態を実物で用意。前例の測定 spec の作り方に従う）。
- 状態: 通常・focus・エラー（空で保存）の3状態。
- 取る値: 3欄の computed style（font-size、height、padding、border-color、border-radius、outline、box-shadow、background）と rect、DOM 属性、ドロワー本体の scrollWidth/clientWidth。
- 生出力は /tmp/CC報告ファイル/ssot-ay2x/impl/。要約は docs/handoff/design-system-recon/evidence-20260910/ay2x-acceptance.md に表で残す（前後の測定 JSON も同じ場所に ay2x-measure-before.json / ay2x-measure-after.json として残す。AY-2w と同じ扱い）。
- 予定の差（PO に提示済み）: 文字 13.6→14.4px、focus は outline 2px → box-shadow のリング（--focus-ring-shadow）、エラー枠は #b91c1c（--color-error）→ --danger、角は --radius-md → --comp-input-radius、390px は高さが 44px（:443-448 のモバイル最小高）。

## 7. 受入条件
| 基準 | 検証方法 |
|---|---|
| 3欄が金型の class を持つ | 試験 §5 と実測 DOM |
| 空で保存すると3欄が赤枠（--danger）、入力すると外れる | 試験 §5、実測のエラー状態の border-color |
| DOM 属性が class 以外で同じ、invalid 属性が出ない | 実測 8条件の差分0（B2） |
| ほかの画面の class が変わらない | TextField.test 既存試験が全件そのまま pass、試験 §5-2 |
| 横 overflow が増えない | 実測 B1 |
| ハードコード文字列・直値の色がない | lint・check:all・check:new-tokens・check-ui-governance が exit 0 |
| 型・ビルド | tsc・build・build-storybook が exit 0 |
| 本番 | merge 後、本番 CSS に `.comp-field__input.comp-field__input--invalid` があり `.dist-input{` が0件、app と api/health（/api/health）が200 |

## 8. Storybook
frontend/src/components/TextField.stories.tsx に `ControlInvalid`（`<TextFieldControl invalid placeholder=... />`）を1件足す。表示文字は既存 story の書式に合わせる。

## 9. docs
- docs/specs/design-system/design.md: :815 の行に「TextFieldControl は AY-2x で実装（class comp-field__input--invalid）」を書き足す。末尾に AY-2w の本番反映記録（観測値だけ: PR #4270 merge 2337378c6 11:30:14Z、deploy 38557035113 success 11:33:13Z、本番 JS index-BWNDl7Dr.js で担当者欄が SelectControl size=sm、app 200・/api/health 200。出典 /tmp/CC報告ファイル/ssot-ay2w/prod/checks.txt）と「§AY-2x」節（目的・変更・実測・PO 決定）を足す。
- docs/handoff/ay2x-dist-form-invalid/{recon,design}.md を置く（パスは必ずフルパスで書く。短縮パスは pr-body-guard が止める）。

## 10. 代替案
- A（採用）: TextFieldControl に invalid を足す。design.md:815 の契約どおりで、ほかの画面にも使い回せる。
- B: ラベル付き TextField（error prop）へ丸ごと置き換える。ラベルの見た目・必須印・エラー文の DOM（span→p role=alert）・ヒント文との排他（TextField.tsx:93-98）まで変わり、PO に示した範囲を超えるため不採用。
- C: dist 側に赤枠 CSS を残し、利用側の className で付ける。金型の外にエラー表現が分かれ、SSOT に反するため不採用。

## 11. 戻し方
本 PR の merge commit を revert する（DB の影響なし）。

## 12. 外部・過去事例の参照と我々への応用
- 過去: §AY-2s〜2t（生 input を TextFieldControl へ逐語で移したもの）と同じやり方を、この3欄に使う。§AY-2w の 390px 横 overflow の測定方法を、停止条件 B1 の基準に使う。
- 外部事例: 不要（仕様書 design.md:815 で決めてある自社の金型の契約を実装する便。自社の実物の前後比較が直接の根拠になる）。

## 維持の仕組み
TextField.tsx と FormField.css（金型）、追加する試験、docs/CC_UI_GOVERNANCE.md、check-ui-governance。
