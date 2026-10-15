# AY-4c-2b 設計: 予定表のカレンダーのチェック欄 2 件を、カレンダーの色のまま金型へ

- 作成: 2026-10-16 Opus（Planner）/ 基点 origin/main（AY-4c-2a マージ後）/ ブランチ release/checkbox-ay4c2b
- recon: docs/handoff/ay4c2-checkbox/recon.md 項目 8・9（行番号は origin/main 52b8a4003 のもの。2a は schedule 系のファイルに触れていない）
- 前便: docs/handoff/ay4c2-checkbox/design.md（AY-4c-2a）
- 対象ADR: ADR-144（UI ガバナンス）、ADR-067（デザイントークン）
- 状態: 設計審査済み（r2 APPROVE）・実装済み（422b01d74）・コード審査 Opus APPROVE（/tmp/CC報告ファイル/ssot-checkbox/ay4c2b/code-review.md）

## 1. 目的（PO の言葉）

- 2026-10-16 PO「y」: 予定表のカレンダーのチェック欄は、各カレンダーの色のまま残す（金型に「データの色を受け取る口」を1つ足し、今の色のまま金型に載せかえる）。
- 2026-10-15 PO「y」: 表の中などの単独の欄は CheckboxControl。
- 利用者に見える変化: 色は今と同じ（スタッフごとのカレンダー色）。この便が終わると、アプリの生のチェック欄が 0 件になる。

## 2. 対象と対象外

- 対象: frontend/src/pages/schedule/SchedulePageImpl.tsx:522-529（マイカレンダー、自分の行）と :553-560（他のカレンダー）。行番号は 2a 入りのブランチで審査役が実測。
- 金型に足す口: CheckboxControl の `dataColor?: string`（docs/specs/design-system/design.md:826「Checkboxのデータ由来accentColorは用途が限定されたdataColor入口へ移す。通常UIの固定色をこの入口で免除しない」、:828「dataColor は AY-4c」）。
- 対象外: label 型 Checkbox には口を足さない（使う場所が無い）。色見本（`.schedule-calendar-item__swatch` の style background）はチェック欄ではないので触らない。frontend/src/company-forms.css:100・:135 のコメント見直し（.form-row 内の checkbox の話で予定表と無関係。コメントだけなので残件のまま）。

## 3. 変更前後

### 3-1. 金型 frontend/src/components/CheckboxControl.tsx

```tsx
// 前 :12-16
export interface CheckboxControlProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, "type" | "className" | "style" | "size" | "role"> {
  size?: "md" | "sm";
  indeterminate?: boolean;
}
// 後
export interface CheckboxControlProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, "type" | "className" | "style" | "size" | "role"> {
  size?: "md" | "sm";
  indeterminate?: boolean;
  /** データ由来の色（例: カレンダーの持ち主の色）だけを渡す。通常 UI の色は渡さない（design.md:826）。未指定なら --accent。 */
  dataColor?: string;
}
```
```tsx
// 前 :19
  { size = "md", indeterminate, ...rest },
// 後
  { size = "md", indeterminate, dataColor, ...rest },
```
```tsx
// 前 :36-41
    <input
      ref={setRef}
      type="checkbox"
      className={`comp-checkbox-control${size === "sm" ? " comp-checkbox-control--sm" : ""}`}
      {...rest}
    />
// 後
    <input
      ref={setRef}
      type="checkbox"
      className={`comp-checkbox-control${size === "sm" ? " comp-checkbox-control--sm" : ""}`}
      style={dataColor ? { accentColor: dataColor } : undefined}
      {...rest}
    />
```
- ファイル冒頭のコメント（:6）「className・style・type・role・size(native) は受けない」の次に「データ由来の色だけ dataColor で受け、accent-color に使う」を1行足す。
- 前例: frontend/src/components/loading/Spinner.tsx:10・:27（色を文字列で受け、内部で style にする）。
- `style` は Omit のままなので、呼び出し側から style は渡せない（rest に入らない）。

### 3-2. 使い手 frontend/src/pages/schedule/SchedulePageImpl.tsx

```tsx
// 前 :522-529
                <input
                  type="checkbox"
                  className="schedule-calendar-checkbox"
                  style={{ accentColor: owner.color }}
                  checked={checked || owner.isSelf}
                  disabled
                  aria-label={owner.name}
                />
// 後
                <CheckboxControl
                  dataColor={owner.color}
                  checked={checked || owner.isSelf}
                  disabled
                  aria-label={owner.name}
                />
```
```tsx
// 前 :553-560
                  <input
                    type="checkbox"
                    className="schedule-calendar-checkbox"
                    style={{ accentColor: owner.color }}
                    checked={checked}
                    onChange={() => owner.userId != null && onToggleOwner(key)}
                    aria-label={owner.name}
                  />
// 後
                  <CheckboxControl
                    dataColor={owner.color}
                    checked={checked}
                    onChange={() => owner.userId != null && onToggleOwner(key)}
                    aria-label={owner.name}
                  />
```
- import: SchedulePageImpl.tsx:18 `import { Toggle } from "../../components/Toggle";` の次に `import { CheckboxControl } from "../../components/CheckboxControl";`
- `owner.color` は schedule-owner.ts:43 で必ず文字列（既定 #1a73e8）。

### 3-3. 配置 frontend/src/pages/schedule.css:242-248

```css
/* 前 */
.schedule-calendar-checkbox {
  width: var(--size-checkbox);
  height: var(--size-checkbox);
  margin: 0;
  flex: none;
  cursor: pointer;
}
/* 後（寸法・cursor は金型が持つので外す。行の中の配置だけ残す） */
.schedule-calendar-item > input[type="checkbox"] {
  margin: 0;
  flex: none;
}
```
- 理由: margin:0・flex:none は行（`.schedule-calendar-item` の flex・space-between）の中の配置で、金型の外側の都合。AY-4c-2a で残した frontend/src/pages-layout.css:635（`.permission-item input[type="checkbox"]`）と同じ扱い。金型の class を画面の CSS から指さない。
- 詳細度 0,2,1 ＞ `.comp-checkbox-control`（0,1,0）だが、金型は margin・flex を指定していないので衝突しない。
- `.schedule-calendar-checkbox` の class は tsx から消えるので規則ごと置き換える。

### 3-4. 守り（通常 UI の色をこの口で通さない）

frontend/src/components/CheckboxControl.test.tsx に2つ足す:
1. `dataColor="#123456"` を渡すと input の `style.accentColor` が `rgb(18, 52, 86)`（試験環境の jsdom は色を rgb に直して持つ。審査 r1 で実測: /tmp/CC報告ファイル/ssot-checkbox/ay4c2b/review-sim-vitest.txt）。未指定なら `input.hasAttribute("style") === false`。
2. 登録制の試験（前例 frontend/src/components/ToggleMigration.test.tsx:21-26 の files 表の形）。frontend/src 以下の .tsx と .ts をすべて読み（`*.test.tsx`・`*.test.ts`・`*.stories.tsx`・`components/CheckboxControl.tsx` を除く）、`/\bdataColor\b\s*[=:]/g`（JSX の `dataColor=` と、createElement 等のオブジェクトの `dataColor:` の両方）が出るファイルと件数が、登録表 `[["pages/schedule/SchedulePageImpl.tsx", 2]]` とちょうど一致すること。さらに登録ファイルの中の出現がすべて `dataColor={owner.color}` の形であること（`/\bdataColor\b\s*=\s*\{owner\.color\}/g` の件数が 2）。
   - 理由: 文字列リテラルだけを数える案は、一重引用符・空白・定数・三項演算子・`??`・spread の 7 通りを見逃した（審査 r1、review-sim-grep.txt）。登録制なら新しい使い手は必ずこの表を書き換える PR になり、審査で止められる（design.md:919「完全パス＋exportName の登録で許可を広げない」と同じ考え方）。
   - この試験は dataColor という名前の口だけを数える。別の部品が同じ名前の口を持つ場合は登録表を部品ごとに分ける（Badge は dataBackground / dataForeground で色を受けるので対象外、design.md:874）。試験の冒頭コメントにこの1行を書く。
   - spread（`{...props}` で dataColor を流す）は件数に出ないが、CheckboxControl の使い手で spread を使うものは今 0。spread 経由を許すかは新しい使い手が出たときに審査で判断する（残件として design.md に書く）。

### 3-5. カタログ frontend/src/components/CheckboxControl.stories.tsx

`DataColor` の story を1つ足す（`dataColor="var(--accent)"` ではなく、データ色の例として 2 色を並べる。story は 3-4 の 2 の検査対象外）。

### 3-6. 文書

docs/specs/design-system/design.md の AY-4c の記録に AY-4c-2b の結果（口の追加・2 件・生 checkbox 0 件）を追記。:826 の予定文の後ろに「AY-4c-2b で実装済み」を足す。AY-4c-2a の記録の「残り（AY-4c-2b…）」の行は、次の残件だけを残す形に書き換える（消して行方不明にしない）: ①frontend/src/company-forms.css:100・:135 のコメント見直し ②spread 経由の dataColor を許すかの判断 ③check-ui-governance に「金型以外の `type="checkbox"` 禁止」を足すかの判断。

## 4. 影響範囲

- 画面: 予定表 `/schedule` の左サイドバー（マイカレンダー・他のカレンダー）。
- 金型の既存の使い手（DataTable・AY-4a〜4c の CheckboxControl）: dataColor を渡さないので style 属性は付かず、出力は今と同じ（3-4 の 1 で確かめる）。
- 試験: unit 全部。schedule のチェック欄を取る試験は 0（recon 項目 8）。frontend/src/components/ToggleMigration.test.tsx:24 は SchedulePageImpl.tsx のソースを読むが、Toggle の数と旧 class の不在だけを見るので影響なし。
- API・DB・i18n: 変更なし。

## 5. 前後実測（マージ前に PO へ提示する）

AY-4c-2a §5-1 と同じ作り方（ファイル名 ay4c2b-*）。
- 型: `.schedule-calendar-list` の中に `.schedule-calendar-item` を 3 行（自分の行＝disabled・チェック、他の人＝チェック、他の人＝未チェックで `--hidden`）。色は既定 #1a73e8 と、別の 2 色。
- 幅 1280・390、ライト・ダーク × チェック・未チェック。
- 測る値: input の幅・高さ・margin・accent-color（前後同じ色であること）、行の高さ、input の右端と行の右端の距離、色見本と input の色が同じこと、disabled の cursor、行（label）の opacity の computed 値（`--hidden` の行を含む）。
- 画像: disabled でチェック済みの自分の行を必ず含める。
- 予想される差: disabled（自分の行）の cursor が pointer → not-allowed（CheckboxControl.css:4）。ほかは前後同じが期待値。

## 6. 代替案と選択理由

- 案1（採用）: CheckboxControl に dataColor を足す。design.md:826 の予定どおり、口が 1 つで用途を絞れる。
- 案2: --accent にそろえる → PO が 2026-10-16 に n でなく y を選んだため不採用。
- 案3: 画面の CSS で `.schedule-calendar-item > .comp-checkbox-control` に色を当てる → 色はスタッフごとのデータで CSS に書けない。不採用。

## 7. リスクと対処

| リスク | 対処 |
|---|---|
| 口が通常 UI の固定色の抜け道になる | 3-4 の 2 の登録制の試験で、使い手のファイル・件数・値を固定 |
| 既存の CheckboxControl の出力が変わる | 未指定なら style を付けない。3-4 の 1 と §5 で確かめる |
| 行の高さ・位置が変わる | §5 で前後を測る。期待値は同じ。違えば止める |
| disabled の cursor が変わる | 金型の形（AY-4c-2a の Roles の disabled と同じ）。§5 で提示 |

## 8. 受入条件と検証方法

| 基準 | 検証方法 |
|---|---|
| アプリの生 checkbox が 2 → 0 件 | `git grep -n 'type="checkbox"' -- ':(glob)frontend/src/**/*.tsx'` が Checkbox.tsx・CheckboxControl.tsx・Toggle.tsx の 3 行だけ |
| 画面の CSS の checkbox セレクタが 1 → 2 行（配置だけ） | `git grep -n 'type="checkbox"' -- ':(glob)frontend/src/**/*.css'` が pages-layout.css:635 付近と schedule.css:242 付近の 2 行（コメント行を除く） |
| `.schedule-calendar-checkbox` が 0 件 | `git grep -n "schedule-calendar-checkbox" -- frontend` が 0 行 |
| tsx の `style={{ accentColor` が 0 件 | `git grep -n "accentColor" -- ':(glob)frontend/src/**/*.tsx'` が CheckboxControl.tsx の 1 行と試験だけ |
| 色が前後同じ | §5 で accent-color の前後が全行一致 |
| 口の使い手が登録どおり | §3-4 の 2 の試験が緑（登録表 `[["pages/schedule/SchedulePageImpl.tsx", 2]]`、値はすべて `{owner.color}`） |
| 既存の使い手の出力が変わらない | §3-4 の 1（style 属性なし）と既存の CheckboxControl・DataTable・ToggleMigration の試験が緑 |
| 試験・型・lint・ビルド | AY-4c-2a §8 と同じ 7 つが exit 0 |

## 9. 外部・過去事例の参照と我々への応用

- 社内: Spinner の color（frontend/src/components/loading/Spinner.tsx:10）。AY-4c-2a の配置規則の残し方（pages-layout.css:635）。
- 外部事例: 不要（社内の既存金型への口の追加で、PO が色の扱いを決めている）。

## 10. 切り戻し

本便の PR の merge commit を revert する。DB・API への影響はない。

## 11. 維持の仕組み

- 守り手: CheckboxControl.test.tsx（3-4 の 2 つ。2 は登録制で、新しい使い手は登録表の変更が要る）、Storybook の DataColor story、check:all。
- 生 checkbox が 0 件になるので、check-ui-governance に「金型以外の `type="checkbox"` を禁止」を足すかを別便で判断する（docs/specs/design-system/design.md に残件として書く）。

## 12. 審査

- r1（Opus、2026-10-16）: REVISE。/tmp/CC報告ファイル/ssot-checkbox/ay4c2b/design-review.md
  - HIGH-1 試験 1 の期待値が jsdom の rgb 表記と合わない → §3-4 の 1 を rgb(18, 52, 86) と hasAttribute に変更
  - MEDIUM-1 リテラル禁止の試験は抜け道 7 通り → §3-4 の 2 を登録制に変更、§8 に 1 行追加
  - LOW-1 行番号のずれ 3 か所 → 修正。LOW-2 company-forms.css のコメント → §2 で対象外・残件と明記。LOW-3 opacity と disabled 行の画像 → §5 に追加。LOW-4 → 変更なし
- r2（Opus、2026-10-16）: APPROVE。/tmp/CC報告ファイル/ssot-checkbox/ay4c2b/design-review-r2.md。LOW-A（.ts からの createElement）→ §3-4 の 2 を .ts と `dataColor:` も数える形に。LOW-B（§7 の文面と残件の引き継ぎ）→ §7・§3-6 を修正。LOW-C（Badge の dataColor で赤になる）→ §3-4 に注記。いずれも判定を変えない修正のため r3 は行わない。
- コード審査（Opus、2026-10-16）: APPROVE。LOW 5 件。LOW-1・LOW-5 は本コミットで修正、LOW-2（実測の後の自分の行だけ readOnly、readonly を指す CSS は無く値に影響なし）・LOW-3（試料は1 section）・LOW-4（型キャストで style を持ち込める既存の穴、使い手0）は記録のみ。
