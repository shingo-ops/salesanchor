# AY-4a チェック欄の共通部品 CheckboxControl を作り、一覧表の選択欄2件を載せる

mode: handoff。親: docs/specs/design-system/design.md §Z（:807 / :826 / :898 / :921）。recon: docs/handoff/ay4a-checkbox/recon.md。ADR-144 / ADR-067 / ADR-027 を継承。

## 目的とPO決定

- PO 原文（2026-10-14）「フロントエンドのパーツもデザイントークンとデザインシステム を遵守して、金型登録のないハードコードを禁止する」。
- PO 回答（2026-10-02、design.md:1953）: Checkbox/Toggle/Radio の新規金型登録を「許可する」。
- PO 回答（2026-10-15「y」）: チェック欄の色を、全部アプリの基本色 `--accent`（ライト #1e3a8a・ダーク #5b8dd9）にそろえる。画面ごとに順に載せかえ、マージ前に変わる前後の比較を見せる。

## 便の分け方（1便1目的）

| 便 | 内容 | 見た目 |
|---|---|---|
| AY-4a（本便） | 金型 CheckboxControl を新設し、DataTable の選択欄2件（全選択・行選択）を載せる | 一覧表の選択欄の色: ブラウザ標準の青 → `--accent`（チェックが入ったときだけ） |
| AY-4b | super-admin 専用の20件と、どの画面からも使われない4件 | 便ごとに前後表 |
| AY-4c | 一般画面の33件。`.form-group input[type=checkbox]`（components.css:19-41）と `.form-row input:focus`（company-forms.css:102-106・:137-141）の撤去、Inbox の 14px（sm）、予定のデータ色（dataColor 入口） | 便ごとに前後表 |

本節で実装してよいのは AY-4a だけです。

## 変更ファイル（AY-4a）

新設: frontend/src/components/CheckboxControl.tsx・CheckboxControl.css・CheckboxControl.stories.tsx・CheckboxControl.test.tsx、docs/handoff/ay4a-checkbox/recon.md・design.md（git add 必須）。変更: frontend/src/components/DataTable.tsx・DataTable.css・DataTable.test.tsx、docs/specs/design-system/design.md。削除: なし。docs/handoff/design-system-recon/evidence-20260910/*.json の `comp-table__check` は過去の監査記録なので触らない。

## 変更の要点（AY-4a）

### 新規 frontend/src/components/CheckboxControl.tsx

```tsx
/**
 * CheckboxControl — チェック欄金型（design.md §AY-4a、§Z :807/:921）
 *
 * ネイティブ checkbox 1つを返す（div/label を増やさない）。
 * native 属性・イベント（checked/onChange/disabled/id/name/value/aria-* /data-*）はそのまま同じ要素へ渡す。
 * className・style・type・role・size(native) は受けない（見た目はこの部品が決める）。
 * indeterminate は prop で受け、DOM プロパティへ反映する。
 */
import { forwardRef, useCallback, useLayoutEffect, useRef, type InputHTMLAttributes } from "react";
import "./CheckboxControl.css";

export interface CheckboxControlProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, "type" | "className" | "style" | "size" | "role"> {
  size?: "md" | "sm";
  indeterminate?: boolean;
}

export const CheckboxControl = forwardRef<HTMLInputElement, CheckboxControlProps>(function CheckboxControl(
  { size = "md", indeterminate, ...rest },
  ref,
) {
  const innerRef = useRef<HTMLInputElement | null>(null);
  const setRef = useCallback(
    (el: HTMLInputElement | null) => {
      innerRef.current = el;
      if (typeof ref === "function") ref(el);
      else if (ref) ref.current = el;
    },
    [ref],
  );
  // 毎回の描画で反映する（旧 DataTable の ref コールバックと同じ頻度。クリックでブラウザが外した後も prop に戻す）
  useLayoutEffect(() => {
    if (innerRef.current) innerRef.current.indeterminate = !!indeterminate;
  });
  return (
    <input
      ref={setRef}
      type="checkbox"
      className={`comp-checkbox${size === "sm" ? " comp-checkbox--sm" : ""}`}
      {...rest}
    />
  );
});
CheckboxControl.displayName = "CheckboxControl";
```

### 新規 frontend/src/components/CheckboxControl.css

```css
/* CheckboxControl — チェック欄金型（design.md §AY-4a）。詳細度の低い順。 */
.comp-checkbox { width: var(--size-checkbox); height: var(--size-checkbox); cursor: pointer; accent-color: var(--accent); }
.comp-checkbox--sm { width: var(--size-checkbox-sm); height: var(--size-checkbox-sm); }
.comp-checkbox:disabled { cursor: not-allowed; }
```

- margin・focus の輪は指定しない（ブラウザ標準のまま。今の DataTable と同じ）。AY-4c で既存の行に合わせて判断する。
- 新しいトークンは足さない（--size-checkbox・--size-checkbox-sm・--accent は既存）。
- checkbox は native の数値 size を持たないため、§Z :803 の nativeSize は設けない（size は部品寸法 md/sm のみ）。
- 配置用 class（§Z :856 の layoutClassName）は本便では設けない。AY-4c の33件で要る場合にそこで足す。

### 新規 CheckboxControl.stories.tsx / CheckboxControl.test.tsx

- stories: 未選択・選択・indeterminate・disabled・sm・label で包んだ例（文言は t() を使わない stories の既存の書き方に合わせる。Toggle.stories.tsx が手本）。
- test（Toggle.test.tsx が手本）:
  1. input type=checkbox が1つだけ描画され、wrapper が無い（container.firstChild が input）。
  2. checked/onChange/disabled/aria-label/data-testid/name/value が同じ input に渡る。
  3. indeterminate=true で DOM の indeterminate が true、false に戻すと false。
  4. 関数 ref・オブジェクト ref の両方で、渡されるのが input 要素そのもの。
  5. size="sm" で comp-checkbox--sm が付く。
  6. className・style・type を渡すと型エラー（@ts-expect-error）。type は `type="radio"` を渡す（`type="checkbox"` の文字列を test に書かない。下の grep 判定のため）。

### 変更 frontend/src/components/DataTable.tsx

変更前（input 本体 :180-189）:
```tsx
<input
  type="checkbox"
  className="comp-table__check"
  checked={allSelected}
  ref={(el) => {
    if (el) el.indeterminate = someSelected;
  }}
  onChange={toggleAll}
  aria-label="select all rows"
/>
```
変更後:
```tsx
<CheckboxControl
  checked={allSelected}
  indeterminate={someSelected}
  onChange={toggleAll}
  aria-label="select all rows"
/>
```
変更前（input 本体 :268-274）:
```tsx
<input
  type="checkbox"
  className="comp-table__check"
  checked={isSelected}
  onChange={() => toggleRow(key)}
  aria-label={`select row ${key}`}
/>
```
変更後:
```tsx
<CheckboxControl
  checked={isSelected}
  onChange={() => toggleRow(key)}
  aria-label={`select row ${key}`}
/>
```
import に `import { CheckboxControl } from "./CheckboxControl";` を追加。

### 変更 frontend/src/components/DataTable.css

`/* ── チェックボックス ── */` と `.comp-table__check { ... }`（コメント込み :147-153）を削除する（未定義の `--primary` 参照3件のうち、この1件が消える。残り2件は事実として recon に記録し、本便では触らない）。

### 変更 docs/specs/design-system/design.md

§AY-3b の後に §AY-4a の節を追加（目的・PO 決定・変更・実測・残り）。:826 の行末「CheckboxControl は §AY-4a で新設」を足す。

## 触らない範囲

- DataTable の selectable/toggleAll/toggleRow/allSelected/someSelected の計算、th/td の class、aria-label の文言（英語のまま。i18n 化は本便の目的外）。
- 金型外の生 checkbox 57件、components.css・company-forms.css・InboxPage.css・schedule.css・pages-layout.css。
- `var(--primary)` の残り2件（DataTable.css 内の別規則）。recon に場所を記録するだけ。
- check-ui-governance.js（checkbox 検出の追加は別判断）。

## 受入条件

| 基準 | 検証方法 |
|---|---|
| CheckboxControl の単体テスト6項目が通る | frontend で `npx vitest run --config vitest.unit.config.ts --project unit src/components/CheckboxControl.test.tsx` exit 0 |
| DataTable の選択の働きが変わらない | DataTable.test.tsx に4項目を追加し、同じ形のコマンドで exit 0。(a) 何も選んでいない状態で全選択を押すと onSelectChange が全キーの Set で呼ばれる (b) 2件中1件を選んだ状態でヘッダーの input が checked=false かつ indeterminate=true (c) 行の欄を押すと、そのキーを含む Set で呼ばれる (d) 全件選択済みで全選択を押すと空の Set で呼ばれる |
| components 内の生 checkbox が DataTable から消える | `git grep -n 'type="checkbox"' -- frontend/src/components ':!*.test.tsx' ':!*.stories.tsx'` が CheckboxControl.tsx・Toggle.tsx・ContactChannelForm.tsx の3件だけ（変更前は DataTable.tsx:181/:269 を含む4件） |
| 必須チェックが通る | frontend で `npx tsc --noEmit`・`npm run lint`・`npm run check:all`・`npm run check:i18n-missing-keys`・`npm run build`・`npm run build-storybook` の exit 0、PR の必須チェック全件 pass |
| 見た目の差が設計どおり | 本番 CSS と PR の build CSS で、DataTable の選択欄の computed style（width/height/margin/cursor/accent-color/outline）を 390・1280 × ライト・ダーク × 未選択・選択・一部選択で比べ、差が accent-color だけ（auto → --accent の値）であること。マージ前に PO に表で見せる |

## 外部・過去事例の参照と我々への応用

- 過去事例（社内）: AY-3b（#4313）で Toggle を同じ形（native input 1つ、className/style を受けない、forwardRef、stories＋test）で新設し、本番反映まで不具合 0。同じ型を使う。
- 外部事例: 不要（native checkbox の accent-color は CSS 標準の機能で、社内の部品の作り方の判断に外部の前例は判断材料にならない）。

## 維持の仕組み

- 守り手: CheckboxControl.tsx の型（className/style を受けない）と CheckboxControl.test.tsx、check:stories。
- 生 checkbox の再発検出は CI に無い（AY-4c 完了後に check-ui-governance へ追加するかを別判断）。

## 切り戻し

本 PR の merge commit を revert する（DB・API の変更なし）。

## 設計審査

- r1 REVISE（must 0 / should 3 / minor 5）: /tmp/CC報告ファイル/ssot-checkbox/ay4a/design-review.md
- r2 APPROVE（must 0 / should 0。minor: check:all に lint と i18n が含まれ二重実行、害なし）: /tmp/CC報告ファイル/ssot-checkbox/ay4a/design-review-r2.md
- 審査は Opus（2026-10-15 PO 決定）。同一系統の AI による審査で、独立した第二者レビューではない。
