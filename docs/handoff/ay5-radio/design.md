# AY-5 設計: ラジオボタンの金型（Radio・RadioControl）を作り、生のラジオボタン 7 件を載せかえる

- 作成: 2026-10-16 Opus（Planner）/ 基点 origin/main b6435490b / ブランチ release/ay5-radio-control
- recon: docs/handoff/ay5-radio/recon.md（生出力 /tmp/CC報告ファイル/ssot-radio/recon/）
- 前便: docs/handoff/ay4d-checkbox-guard/design.md（AY-4d）、docs/handoff/ay4c2b-checkbox/design.md（AY-4c-2b）
- 対象ADR: ADR-144（UI ガバナンス）、ADR-067（デザイントークン）、ADR-027（i18n）
- 状態: 設計審査 r1 REVISE → r2 REVISE（N1〜N3 は文言の食い違いのみ。審査役「直した差分を Opus が目で確かめれば APPROVE 相当」）→ N1〜N3 を反映し Opus が確認（/tmp/CC報告ファイル/ssot-radio/review/design-r1.md・design-r2.md）

## 1. 目的（PO の言葉）

- 2026-10-16 PO「y」: ラジオボタンの金型を、チェック欄の金型と同じ形（選択色は --accent）で作り、7 件を載せかえる便に進める。設計を作り、載せかえ前後の画面比較を見せてから、マージと本番反映まで進める。
- 前提の PO 決定: 2026-10-02 Checkbox/Toggle/Radio の新規金型登録を許可（docs/specs/design-system/design.md:1953）。2026-10-15 チェック欄の色は全部 --accent（同 :4202）。
- 利用者に見える変化:
  - 統合の小窓 3 種（会社・担当者・リード）の丸ボタンが 13px 前後の標準の青から 16px のアプリの基本色になる。
  - 登録画面の配送先の 2 択は、文字の大きさ・太さと丸と文字の間が金型の形になる。
  - ロールの色選びは見た目が変わらない（丸ボタンは透明で、色の四角だけが見えている）。
- この便が終わると、frontend/src の生のラジオボタン（金型の中を除く）は 7 件 → 0 件。

## 2. 対象と対象外

- 対象: recon §2 の R1〜R7。
- 新しい金型: frontend/src/components/Radio.tsx・Radio.css（文字と並ぶ欄。Checkbox と同じ形）、frontend/src/components/RadioControl.tsx・RadioControl.css（表の中・色見本など単独の欄。CheckboxControl と同じ形）。
- 使い分け（2026-10-15 のチェック欄と同じ決め方）: R1・R2 は Radio、R3〜R7 は RadioControl。
- 対象外（理由）
  - ChoiceCardGroup.tsx:39: すでに金型の中。
  - 自動チェック（scripts/check-ui-governance.js）への radio 種別の追加: 変更は一度に1つ。この便のあと AY-5b として別に提案する。
  - RegisterPage.tsx の未定義トークン `--spacing-*` 22 か所（R1・R2 以外）: 画面全体の余白の話で、別の便。残件に書く。
  - pages-layout.css の `.color-swatch-legacy::after` の直書き「現在」（ADR-027 違反）: 文言の扱いは別判断。残件に書く。
  - R1・R2 の質問文を fieldset/legend にする、R5〜R7 に aria-label を足す: 読み上げの改善で、今の形を変えないこの便の範囲外。残件に書く。
  - 寸法 sm の口・dataColor の口: 使う場所が無い（必要になった便で足す）。
  - Radio を .form-group の中に置いたときの崩れ（審査 r1 M5）: frontend/src/components.css:11 の `.form-group label:where(:not(.comp-checkbox))` が .comp-radio を除外せず、:19 の `.form-group input[type="radio"]`（width 100% など）が金型に勝つ。今回 Radio を使う R1・R2 は .form-group の外なので起きない。:19 を外すと .form-group の中の R3・R4 の規則も変わるため、この便では触らず、Radio.tsx の冒頭コメントと残件に書く。
- design.md:807 の「RadioControl7」は棚卸し時点の生ラジオ 7 件を指す。今回はそのうち文字と並ぶ R1・R2 を Radio、残り 5 件を RadioControl にする（チェック欄の使い分けと同じ）。

## 3. 変更前後

### 3-1. 新規 frontend/src/components/RadioControl.tsx

CheckboxControl.tsx（recon §5）から indeterminate・dataColor・size を除いた形。

```tsx
/**
 * RadioControl — ラジオボタン金型（単独の欄）（design.md §AY-5、§Z :807/:921）
 *
 * ネイティブ radio 1つを返す（div/label を増やさない）。radio のネイティブ挙動（name で1つだけ選ぶ・矢印キー）はそのまま。
 * native 属性・イベント（checked/onChange/readOnly/disabled/id/name/value/aria-* /data-*）はそのまま同じ要素へ渡す。
 * className・style・type・role・size(native) は受けない（見た目はこの部品が決める）。
 */
import { forwardRef, type InputHTMLAttributes } from "react";
import "./RadioControl.css";

export type RadioControlProps = Omit<InputHTMLAttributes<HTMLInputElement>, "type" | "className" | "style" | "size" | "role">;

export const RadioControl = forwardRef<HTMLInputElement, RadioControlProps>(function RadioControl(props, ref) {
  return <input ref={ref} type="radio" className="comp-radio-control" {...props} />;
});
RadioControl.displayName = "RadioControl";
```

- 注意: `{...props}` を type・className の後に置いても、型で type・className を受けないので上書きされない（CheckboxControl と同じ）。

### 3-2. 新規 frontend/src/components/RadioControl.css

```css
/* RadioControl — ラジオボタン金型（design.md §AY-5）。寸法はチェック欄と同じ --size-checkbox を使う（新しいトークンは足さない・ADR-067）。 */
.comp-radio-control { width: var(--size-checkbox); height: var(--size-checkbox); cursor: pointer; accent-color: var(--accent); }
.comp-radio-control:disabled { cursor: not-allowed; }
```

- 詳細度は (0,1,0)。R3・R4 では `.color-swatch input[type="radio"]`（0,2,1）と `.form-group input[type="radio"]`（0,2,1）が勝つので、幅・高さ・cursor は今のまま（透明の欄が色の四角いっぱいに広がる）。前後実測で確かめる（§5）。

### 3-3. 新規 frontend/src/components/Radio.tsx・Radio.css

- Radio.tsx は Checkbox.tsx（recon §5・全 67 行）を写し、次だけ変える。
  - 名前: Checkbox → Radio、CheckboxSize → RadioSize、CheckboxOwnProps → RadioOwnProps、CheckboxProps → RadioProps。
  - `type="checkbox"` → `type="radio"`。
  - class: comp-checkbox → comp-radio（comp-radio--sm・--lg・--error、comp-radio__input・__label・__description）。
  - 冒頭コメント: 「Radio — 標準ラジオボタン金型（文字と並ぶ欄）（design.md §AY-5、Checkbox と同じ形）」。手本の行（SalesFormMultiSelect.tsx の記述）は消す。
- Radio.css は Checkbox.css（全 83 行）を写し、class 名を同じ規則で置き換え、次だけ変える（審査 r1 M4: Chromium のネイティブ radio は border・border-radius が 0 に強制され background は描かれず、box-shadow は四角になる。実測 /tmp/CC報告ファイル/ssot-radio/review/probe/probe-result.txt）。
  - `.comp-radio__input` から `border`・`border-radius`・`background`・`transition` の4行を消す。残すのは flex-shrink・margin 0・width/height 1.1em・accent-color var(--accent)・cursor。
  - `.comp-radio__input:hover`・`.comp-radio__input:focus-visible`・`.comp-radio--error .comp-radio__input` の3規則は写さない（フォーカスの輪はブラウザ標準の丸のまま）。`.comp-radio__input:disabled` は cursor だけ残す。
  - error は `.comp-radio--error .comp-radio__description` の文字色 var(--danger) だけで示す。
  - 冒頭コメントを「Radio — 標準ラジオボタン金型（design.md §AY-5）。Checkbox.css と同じ形。ネイティブ radio に効かない border・background・box-shadow は持たない」にする。
- Radio.tsx の冒頭コメントに1行足す: 「.form-group の中では使えない（components.css:11・:19 の規則が勝って崩れる。残件 §2）」。
- props・状態（size sm/md/lg・error・description・disabled）は Checkbox と同じ。

### 3-4. frontend/src/pages/register/RegisterPage.tsx（R1・R2）

```tsx
// 前 :456-475
              <label style={{ display: "flex", alignItems: "center", gap: "var(--spacing-2)", cursor: "pointer" }}>
                <input
                  type="radio"
                  name="shipping_choice"
                  value="proceed"
                  checked={shippingChoice === "proceed"}
                  onChange={() => setShippingChoice("proceed")}
                />
                {t("registration.proceedToRegister")}
              </label>
              <label style={{ display: "flex", alignItems: "center", gap: "var(--spacing-2)", cursor: "pointer", marginTop: "var(--spacing-1)" }}>
                <input
                  type="radio"
                  name="shipping_choice"
                  value="same"
                  checked={shippingChoice === "same"}
                  onChange={() => setShippingChoice("same")}
                />
                {t("registration.shipToSameAddress")}
              </label>
// 後
              <div>
                <Radio
                  name="shipping_choice"
                  value="proceed"
                  checked={shippingChoice === "proceed"}
                  onChange={() => setShippingChoice("proceed")}
                  label={t("registration.proceedToRegister")}
                />
              </div>
              <div>
                <Radio
                  name="shipping_choice"
                  value="same"
                  checked={shippingChoice === "same"}
                  onChange={() => setShippingChoice("same")}
                  label={t("registration.shipToSameAddress")}
                />
              </div>
```

- div で包む理由: Radio の根は inline-flex なので、包まないと2つが横に並ぶ。今は縦に並んでいる。div は style を持たない。
- 2つめの marginTop var(--spacing-1) は消える。`--spacing-*` は定義が無い（recon §4）ので、今も 0 のはず。前後実測で確かめる。
- import: :18 `import { TextFieldControl } from "../../components/TextField";` の次の行に `import { Radio } from "../../components/Radio";`。
- 押せる範囲（審査 r1 M3）: 今の label は display flex なので行の幅いっぱいが押せる。金型の根は inline-flex なので、丸と文字の幅だけになる。Checkbox と同じ形。PO に前後比較と一緒に明示する。

### 3-5. frontend/src/pages/roles/RolesPage.tsx（R3・R4）

- :470-476 の `<input type="radio" name="role-color" value={roleForm.color} checked readOnly />` → `<RadioControl name="role-color" value={roleForm.color} checked readOnly />`（属性はそのまま、type だけ消える）。
- :486-492 の `<input type="radio" name="role-color" value={c} checked={...} onChange={...} />` → `<RadioControl ... />`（属性はそのまま、type だけ消える）。
- label・div.color-picker・title・style background は触らない。
- import: :21 `import { Select } from "../../components/Select";` の次の行に `import { RadioControl } from "../../components/RadioControl";`。

### 3-6. frontend/src/components/MergeCompanyModal.tsx・MergeContactModal.tsx・MergeLeadModal.tsx（R5〜R7）

- `<input type="radio" name="master-candidate" checked={...} onChange={...} />` → `<RadioControl name="master-candidate" checked={...} onChange={...} />`（属性はそのまま、type だけ消える）。
- MergeContactModal.tsx:218 の古いコメント `{/* radio は TextField 対象外のため残置 */}` を消す（金型に載せたので事実でなくなる）。
- tr の onClick・背景・td は触らない。
- import: 各ファイルの `import { Button } from "./Button";`（MergeCompanyModal.tsx:22・MergeContactModal.tsx:21・MergeLeadModal.tsx:23）の次の行に `import { RadioControl } from "./RadioControl";`。

### 3-7. 試験と Storybook

- 新規 frontend/src/components/RadioControl.test.tsx（CheckboxControl.test.tsx の書き方に合わせる）
  - type が radio、class が comp-radio-control。
  - name・value・checked・onChange・readOnly・disabled・aria-label がそのまま渡る。
  - 同じ name の 2 つで、片方を押すと onChange が呼ばれる。
  - `// @ts-expect-error` で className・style・type を渡せないこと。
- 新規 frontend/src/components/Radio.test.tsx
  - getByLabelText(label 文字列) で input に届く（label と input がつながる）。type が radio。
  - description を渡すと aria-describedby がその文字の要素を指す。error で aria-invalid と role alert。
  - disabled がそのまま渡る。
- 新規 frontend/src/components/Radio.stories.tsx・RadioControl.stories.tsx（Checkbox.stories.tsx・CheckboxControl.stories.tsx の形を写す。文字は stories の既存の書き方に合わせる）。

### 3-8. 文書

- docs/CC_UI_GOVERNANCE.md: 禁止表（:21-28）は見出しが「CI ゲートが赤にする」で radio は止まらないため、表には入れない（審査 r1 L3）。表の直後（:28 の次、`---` の前）に空行を挟んで1行: `- 生 \`<input type="radio">\` も使わない。\`<Radio>\`（文字と並ぶ欄）/ \`<RadioControl>\`（表の中・色見本など単独の欄）を使うこと（CI ではまだ止まらない。AY-5b で提案）`
- docs/specs/design-system/design.md の §AY-4d（:4248〜）の後ろに `#### AY-5 Radio・RadioControl 金型と生ラジオ 7 件の載せかえ（2026-10-16）` 節。PO 決定・設計の場所・使い分け・前後実測の結果・対象外・残件を書く。:4254 の「対象外: 生 radio（pages/ に 4 件）」の後ろに「→ AY-5 で 0 件」と足す。
- ADR は足さない（ADR-144 の金型登録手順と 2026-10-02 の PO 許可の範囲で、新しい技術判断が無い）。

## 4. 影響範囲

- 呼び出し元: R1 は登録画面（RegisterPage）、R3・R4 はロール画面の編集小窓、R5〜R7 は CompanyDetailPage.tsx:255・CompanyContactsTab.tsx:241・LeadsPage.tsx:550 から開く統合の小窓（recon 63-used-by.txt）。
- 動き（選ぶ・選び直す・統合先の決定・送信の値）は変えない。属性はそのまま渡す。
- API・DB・文言キーは変えない（ja.json・en.json は触らない）。
- 自動チェック: 対象ファイルの生 checkbox・生 select・生 input の件数は増えない（radio は数えない種別）。

## 5. 前後実測（PO に見せる比較）

- 作り方は AY-4c-2b と同じ（docs/handoff/design-system-recon/evidence-20260910/ay4c2b-measure.cjs・ay4c2b-render.tsx・ay4c2b-compare.py を写して ay5-* を作る）。
  - 前の CSS: origin/main の vite build CSS。後の CSS: 作業ツリーの vite build CSS。
  - 前のマークアップ: 実ファイルの JSX を写す。後: 金型を renderToStaticMarkup。どちらも祖先の class の並び（R3・R4 は div.form-group > div.color-picker > label.color-swatch、R5〜R7 は小窓の祖先〜table.data-table > tbody > tr > td）を実ファイルから写す。祖先の写し方を ay5-measure-ancestry.md に file:line で残す。
  - 幅 1280・390 × ライト・ダーク × 選択あり・なし、R1 と R5 は focus（キーボードで当てた状態、:focus-visible）も撮る。R1 は 2 択を並べた状態で測る。
  - 測る値: input の位置と大きさ、computed の width・height・margin・accent-color・cursor・opacity・position、R1 は label の gap・font-size・font-weight・align-items・文字の位置、2 つの行の縦の間隔。
- 想定内の差（これ以外の差は想定外 ×）
  - R1・R2: 丸の大きさ（ブラウザ標準 → 1.1em）・accent-color（auto → --accent）・label の display（flex → inline-flex）と幅（行いっぱい → 中身の幅＝押せる範囲）・gap（今の値 → --space-2）・font-size（継承 → --font-sm）・font-weight（継承 → medium）・align-items（center → flex-start）と、それに伴う文字と丸の位置・行の高さ・2 行の縦の間隔。margin は index.css:411 の `* { margin: 0 }` で前後とも 0（差にならない）。
  - R3・R4: accent-color（auto → --accent。欄が透明なので見た目は変わらない）だけ。幅・高さ・位置・opacity・cursor は差 0。
  - R5〜R7: width・height（標準 → 16px）・accent-color（標準 → --accent）・cursor（標準 → pointer）と、それに伴う行の高さ。
- 画像は ay5-{before,after}-*.png。PO にはこの画像と想定外 0 件の結果を見せてからマージする。

## 6. 代替案

- A（採用）: Checkbox と同じ2つの金型（Radio・RadioControl）。PO の「チェック欄の金型と同じ形」に沿い、使い分けも同じ。
- B: RadioGroup（fieldset/legend＋選択肢の配列）を1つだけ作る。R3・R4（色見本）と R5〜R7（表の行）は選択肢が配列で並ばない形で当てはまらない。
- C: ChoiceCardGroup を使う。カードの形なので見た目が大きく変わる。PO の y の範囲外。

## 7. リスクと対処

| リスク | 対処 |
|---|---|
| R3・R4 の透明な欄の大きさが変わり、色の四角を押しても選べなくなる | 詳細度で色見本の規則が勝つ（§3-2）。前後実測で R3・R4 の幅・高さ・位置の差 0 を確かめる（accent-color の差だけは想定内）。試験ではなく実測で守る |
| R1・R2 の文字の大きさが変わり、PO の想定と違う | 前後の画像を PO に見せてからマージする。n なら Radio の size="lg"（font-base）に切り替えて再実測する |
| 統合の小窓で丸を押したとき、行の onClick と二重に動く | 今も同じ（radio の onChange と tr の onClick が同じ処理）。属性を変えないので変わらない |
| `--spacing-*` が実は別の場所で定義されている | 前後実測で R1 の今の gap・marginTop の computed 値を取る。0 でなければ想定外として止めて報告 |
| 金型が型で受けない属性を呼び出し側が渡している | tsc で落ちる。7 件はすべて name・value・checked・onChange・readOnly だけ（recon §2） |

## 8. 受入条件

| 基準 | 検証方法 |
|---|---|
| K1 生のラジオボタンが金型の中を除いて 0 件 | 表の下の「K1 のコマンド」の出力がちょうど 3 行（Radio.tsx・RadioControl.tsx・ChoiceCardGroup.tsx。今は 8 行） |
| K2 前後実測で想定外の差 0 件 | ay5-measure-compare.txt の「想定外」が 0。R3・R4 の差は accent-color だけ（幅・高さ・位置・opacity・cursor は差 0） |
| K3 試験が通る | RadioControl.test.tsx・Radio.test.tsx が通る。CI の Frontend Check が緑 |
| K4 品質 | build・tsc・lint・check:all・check:i18n-missing-keys・build-storybook が exit 0 |
| K5 動き | R1: 選び直すと配送先の欄が出る・消える（:481）→ Radio.test の onChange と画像。R3・R4: 既存の frontend/src/components/RoleKnowledgeButtonMigration.test.tsx が通る。R5〜R7: Merge*Modal の試験は無いので RadioControl.test の onChange と画像で確かめる |
| K6 文書 | docs/CC_UI_GOVERNANCE.md の禁止表の直後（:28 の次）に radio の1行があり、表の中には無い。design.md に §AY-5 節があり、:4254 の後ろに「→ AY-5 で 0 件」がある |
| K7 本番 | deploy が success・headSha がマージ commit、app と /api/health が 200 |

K1 のコマンド（作業場所で実行。zsh で確認済み）:

```sh
git grep -n -E "type=(\"|\{\"|'|\{')radio" -- 'frontend/src/*.tsx' ':!frontend/src/**/*.test.tsx' ':!frontend/src/**/*.stories.tsx'
```

## 9. 維持の仕組み

- 守り手: frontend/src/components/RadioControl.test.tsx・Radio.test.tsx（CI の Frontend Check で毎回走る）、docs/CC_UI_GOVERNANCE.md の禁止表の直後の1行（表の中ではない）、Storybook の stories。
- 生のラジオボタンを新しく書くことを自動で止める仕組みはまだ無い。AY-5b（check-ui-governance に radio 種別を足す）を次に PO へ提案する。

## 10. 外部・過去事例の参照と我々への応用

- 外部事例: 不要。社内の既存の金型（Checkbox・CheckboxControl）と同じ形の金型を足すだけで、新しい技術の選択が無い。
- 過去事例: AY-4a〜AY-4c-2b（Checkbox・CheckboxControl への載せかえ。前後実測で想定外 0 を確かめてからマージ）。同じ測り方と同じ使い分けを使う。
