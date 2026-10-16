# AY-4c-2a 設計: 残り 9 件のチェック欄のうち、口を足さずに金型へ移せる 7 件

- 作成: 2026-10-16 Opus（Planner）/ 基点 origin/main 52b8a4003（#4346 AY-4c-1 マージ後）/ ブランチ release/checkbox-ay4c2
- recon: docs/handoff/ay4c2-checkbox/recon.md（「項目 1〜9」は recon の番号。行番号はすべて origin/main 52b8a4003 のもの）
- 手本: docs/handoff/ay4c-checkbox/design.md（PR #4346、本番反映済み）
- 対象ADR: ADR-144（UI ガバナンス）、ADR-067（デザイントークン）
- 状態: 設計審査済み（r2 APPROVE、2026-10-16）・実装未着手

## 1. 目的（PO の言葉）

- 2026-10-15 PO「y」: チェック欄の色を全部 --accent にそろえる。画面ごとに順に載せかえ、マージ前に前後比較を見せる。
- 2026-10-15 PO「y」: 文字と並ぶ欄は label 型 Checkbox（frontend/src/components/Checkbox.tsx）、表の中などの単独の欄は CheckboxControl（frontend/src/components/CheckboxControl.tsx）。
- 利用者に見える変化: 在庫表の仕入先の絞り込み、担当者・スタッフの編集、スタッフの新規登録、受信箱のプロフィールと営業形態、ロールの権限カードのチェック欄が、AY-4b・AY-4c-1 で本番に入った形と同じ大きさ・色になる。あわせて、通知設定の「イベント種別」のチェック欄（既に金型だが古い CSS に上書きされている）が金型どおりの形に戻る。

## 2. 対象と対象外

**本便（AY-4c-2a）7 件**

| 型 | recon 項目 | 載せかえ先 | 包み方 |
|---|---|---|---|
| H1 行・カードの label はそのまま、input だけ金型 | 1 MultiSelect.tsx:79 / 6 SalesFormMultiSelect.tsx:135 / 7 RolesPage.tsx:421 | CheckboxControl（md） | 外側の label・class・testid・hover は今のまま |
| H2 `.form-group` の中の文字付き欄 | 2 ContactEditPage.tsx:171 / 3 StaffEditPage.tsx:213 / 4 StaffPage.tsx:289 | Checkbox（md） | `div.form-group` は残す（下の間隔 space-4 を保つ） |
| H3 右パネルの行 | 5 InboxProfileModal.tsx:255 | Checkbox（md） | インライン style の label を捨てる |
| 副作用の手当て | （既存の金型）NotificationsPage.tsx:131・:157 | Checkbox のまま | class なしの div で1つずつ包む（§3-2） |

**対象外（AY-4c-2b、PO 判断待ち）2 件**: 項目 8・9 frontend/src/pages/schedule/SchedulePageImpl.tsx:523・:554。チェック欄の色がスタッフごとのデータ色（`owner.color`、frontend/src/pages/schedule/schedule-owner.ts:34・:43）で、CheckboxControl は色を受ける口を持たない（CheckboxControl.tsx:13）。色を残すか（金型に dataColor の口を足す。docs/specs/design-system/design.md:826 の予定）、--accent にそろえるかは PO が決める。

**Checkbox の className（root）は使わない**。理由: docs/specs/design-system/design.md:910 が配置の口を layoutClassName に統一すると定めており、Checkbox の className は移行中の互換口にあたる（recon §1）。H1 は外側の label を残して input だけを替えるので口が要らない。

## 3. 変更前後

### 3-1. H1（CheckboxControl。外側はそのまま）

「前」は実ファイルの文字列を写したもの。置き換えは実ファイルの該当範囲（行番号）を正とする。

import の置き場所（全ファイル共通）: そのファイルの `../../components/`（MultiSelect は `./`）からの import の並びの最後の行の次に1行足す。

項目 1 frontend/src/components/MultiSelect.tsx:78-84
```tsx
// 前
            <input
              type="checkbox"
              className="comp-multiselect__check"
              checked={selected.includes(o.value)}
              onChange={() => toggle(o.value)}
              data-testid={tid(`option-${o.value}`)}
            />
// 後
            <CheckboxControl
              checked={selected.includes(o.value)}
              onChange={() => toggle(o.value)}
              data-testid={tid(`option-${o.value}`)}
            />
```
- import: MultiSelect.tsx:14 `import { Popover } from "./Popover";` の次に `import { CheckboxControl } from "./CheckboxControl";`
- CSS: frontend/src/components/MultiSelect.css:34-39（`.comp-multiselect__check` の規則）と、その直前の空行 1 行を削除。使い手は MultiSelect.tsx だけ（recon 項目 1）。
- 見た目の差: 色が未定義の `--primary` → `--accent`。寸法は 16px のまま（`--size-checkbox`）。

項目 6 frontend/src/pages/inbox/SalesFormMultiSelect.tsx:134-139
```tsx
// 前
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => toggleOption(option)}
                  aria-label={option.label}
                />
// 後
                <CheckboxControl
                  checked={checked}
                  onChange={() => toggleOption(option)}
                  aria-label={option.label}
                />
```
- 外側の `label.sales-form-option`（:129-133 の key・className・data-testid）と `span.sales-form-option-label`（:140）はそのまま。
- import: SalesFormMultiSelect.tsx:17 `import { TextFieldControl } ...` の次に `import { CheckboxControl } from "../../components/CheckboxControl";`
- CSS: frontend/src/pages/inbox/InboxPage.css:1862-1865（`.sales-form-option input[type="checkbox"]` = accent-color accent / cursor pointer）と、その直後の空行 1 行を削除。金型が同じ色・cursor を持つ（CheckboxControl.css:2）。
- 見た目の差: 色・cursor は同じ。寸法が既定の大きさ → 16px（`--size-checkbox`）になる（§5 で測る）。

項目 7 frontend/src/pages/roles/RolesPage.tsx:420-425
```tsx
// 前
                            <input
                              type="checkbox"
                              checked={editedPermIds.has(p.id)}
                              disabled={!canEditPerms}
                              onChange={() => togglePerm(p.id)}
                            />
// 後
                            <CheckboxControl
                              checked={editedPermIds.has(p.id)}
                              disabled={!canEditPerms}
                              onChange={() => togglePerm(p.id)}
                            />
```
- 外側の `label.permission-item` と `div.permission-item-text` はそのまま。
- import: RolesPage.tsx:28 の `Checkbox` の import の次の行に `import { CheckboxControl } from "../../components/CheckboxControl";`
- CSS: frontend/src/pages-layout.css:635-638（`.permission-item input[type="checkbox"]` = margin-top space-1 / flex-shrink 0）は**残す**。カードの中で文字の1行目と高さを合わせる配置の指定で、金型の外側（カード）の都合だから。
- 見た目の差: 色が既定 → `--accent`、寸法 16px が付く。
- アクセシブル名: label の中の文字（p.description）のまま。frontend/src/components/PurchaseAdminEditorButtonMigration.test.tsx:33 の `findByRole('checkbox', { name: /View customers/ })` はそのまま通る。

### 3-2. H2（Checkbox。`.form-group` は残す）

項目 2 frontend/src/pages/contacts/ContactEditPage.tsx:169-174
```tsx
// 前
<div className="form-group">
  <label>
    <input type="checkbox" checked={form.is_primary_contact} onChange={(e) => setForm({ ...form, is_primary_contact: e.target.checked })} />
    {" "}{t("contacts.primaryContactHint")}
  </label>
</div>
// 後
<div className="form-group">
  <Checkbox
    label={t("contacts.primaryContactHint")}
    checked={form.is_primary_contact}
    onChange={(e) => setForm({ ...form, is_primary_contact: e.target.checked })}
  />
</div>
```
項目 3 frontend/src/pages/staff/StaffEditPage.tsx:211-218（`div.form-group` の中身）
```tsx
// 前
                <label>
                  <input
                    type="checkbox"
                    checked={form.ui_preferences[k]}
                    onChange={(e) => setForm({ ...form, ui_preferences: { ...form.ui_preferences, [k]: e.target.checked } })}
                  />
                  {" "}{label}
                </label>
// 後
                <Checkbox
                  label={label}
                  checked={form.ui_preferences[k]}
                  onChange={(e) => setForm({ ...form, ui_preferences: { ...form.ui_preferences, [k]: e.target.checked } })}
                />
```
項目 4 frontend/src/pages/staff/StaffPage.tsx:288-291（`div.form-group` の中身）
```tsx
// 前
                <label>
                  <input type="checkbox" checked={createForm.ui_preferences[k as keyof StaffUIPreferences]} onChange={(e) => setCreateForm({ ...createForm, ui_preferences: { ...createForm.ui_preferences, [k]: e.target.checked } })} />
                  {" "}{label}
                </label>
// 後
                <Checkbox
                  label={label}
                  checked={createForm.ui_preferences[k as keyof StaffUIPreferences]}
                  onChange={(e) => setCreateForm({ ...createForm, ui_preferences: { ...createForm.ui_preferences, [k]: e.target.checked } })}
                />
```
- `key={k}` は外側の `div.form-group`（StaffEditPage.tsx:210、StaffPage.tsx:287）に残す（div を外さないので移さない）。`{" "}` は捨てる（間隔は金型の gap）。
- import: 3 ファイルとも、`../../components/` からの import の並びの最後の行の次に `import { Checkbox } from "../../components/Checkbox";`
- 見た目の差（H2 共通。§5 で測って提示）: ①押せる範囲が `.form-group` の全幅（label が display:block）→ 欄と文字の幅だけ（root が inline-flex）に縮む。②文字色 text-secondary → text-primary。③label の margin-bottom space-1 が無くなる（`.form-group` の margin-bottom space-4 は残る）。④欄の幅 100%・padding・枠（components.css:19-30 が当たっていた）→ 1.1em の金型の欄。⑤縦の位置が上寄せ。

**古い CSS の側で金型を外す**（frontend/src/components.css）
```css
/* 前 :11 */
.form-group label {
/* 後 :11（詳細度は 0,1,1 のまま。:where の中は詳細度 0） */
.form-group label:where(:not(.comp-checkbox)) {
```
```css
/* 前 :19-22 */
.form-group input[type="checkbox"],
.form-group input[type="radio"],
.form-group input[type="range"],
.form-group input[type="file"] {
/* 後（checkbox の行だけ削除） */
.form-group input[type="radio"],
.form-group input[type="range"],
.form-group input[type="file"] {
```
:33-36 の `:focus` も同じく checkbox の行だけ削除。radio/range/file の行は残す（frontend/src/components/PriorityScoreOverride.tsx:76-82 の range が使う。recon §4-1）。
- 理由: この 2 つの規則は `.form-group` の子孫の checkbox 全部に当たり、金型の display・幅・枠・文字色を上書きする（recon 項目 2 の 1〜3）。本便の後、`.form-group` の中に生の checkbox は残らない（項目 8・9 は `.form-group` の外）。よって checkbox の行を消して当たるのは金型だけになり、金型が正本として効く。
- `.form-group label` を `:where(:not(.comp-checkbox))` にする理由: 同じ規則が、`.form-group` の見出し用の label（例 NotificationsPage.tsx:129 `<label>{t("notifications.eventTypesLabel")}</label>`）には今どおり当たり、金型の root だけを外すため。`:where` で詳細度を 0,1,1 のまま保ち、他の規則との勝ち負けを変えない。

**副作用と対処（NotificationsPage、本便の対象に入れる）**: 既に `.form-group` の中にある Checkbox（frontend/src/pages/notifications/NotificationsPage.tsx:131-136・:157-162、`.map` で並ぶ）は、包む要素なしで `.form-group` の直下に並んでいる。今は `.form-group label` の display:block（components.css:12）で縦に並んでいる。上の CSS 変更の後は金型の inline-flex（Checkbox.css:9）が効き、横に詰めて並ぶ。縦の並びを保つため、各 Checkbox を class なしの div で包む（AY-4c-1 G3 と同じ形。新しい class・style は作らない）:
```tsx
// 前（:131-136。:157-162 は form → editForm、setForm → setEditForm で同じ形）
            {eventTypes.map((et) => (
              <Checkbox
                key={et.code}
                label={eventTypeLabel(et.code)}
                checked={form.event_types.includes(et.code)}
                onChange={() => setForm({ ...form, event_types: toggleEventType(form.event_types, et.code) })}
              />
            ))}
// 後
            {eventTypes.map((et) => (
              <div key={et.code}>
                <Checkbox
                  label={eventTypeLabel(et.code)}
                  checked={form.event_types.includes(et.code)}
                  onChange={() => setForm({ ...form, event_types: toggleEventType(form.event_types, et.code) })}
                />
              </div>
            ))}
```
- key は div へ移す。
- 見た目の差（§5 で測って提示）: 欄が幅 100%・枠付き → 金型の欄、文字色 text-secondary → text-primary、行どうしの間隔 space-1（label の margin-bottom）→ 0（行の高さのみ）、押せる範囲が全幅 → 欄と文字の幅、縦の位置が上寄せ。見出しの label（:129・:155）は今のまま。
- ほかに `.form-group` を祖先に持つ金型があるかは実装時に全数を確かめる（§5-2）。

### 3-3. H3（Checkbox。インライン style を捨てる）

項目 5 frontend/src/pages/inbox/InboxProfileModal.tsx:254-263
```tsx
// 前
<label style={{ display: "flex", alignItems: "center", gap: "var(--space-1)" }}>
  <input type="checkbox" checked={cardForm.competitor_check ?? false}
    onChange={(e) => { handleCardFieldChange("competitor_check", e.target.checked); setTimeout(handleCardFieldBlur, 0); }} />
  <span className="right-panel-value">
    {cardForm.competitor_check ? t("leads.competitorDone") : t("leads.competitorNotDone")}
  </span>
</label>
// 後
<Checkbox
  label={cardForm.competitor_check ? t("leads.competitorDone") : t("leads.competitorNotDone")}
  checked={cardForm.competitor_check ?? false}
  onChange={(e) => { handleCardFieldChange("competitor_check", e.target.checked); setTimeout(handleCardFieldBlur, 0); }}
/>
```
- 外側の `div.right-panel-row` と `span.right-panel-label` はそのまま。
- import: `import { Checkbox } from "../../components/Checkbox";`
- 見た目の差: 間隔 space-1 → space-2、縦の位置 中央 → 上寄せ（Checkbox.css:10）、色 既定 → --accent、文字 weight 500・sm・text-primary は同じ値（InboxPage.css:817-822 と Checkbox.css:12-14・:72）。`.right-panel-value` の word-break（InboxPage.css:821）が外れる（文字は「済」「未」相当の短い 2 通りのため、折り返しの差は §5 で確認）。

### 3-4. company-forms.css のコメント（変更しない）

frontend/src/company-forms.css:100・:135 のコメントと規則は本便では触らない。この規則は `.form-row` 内の TextField 系と AY-4c-1 の Checkbox に当たっており（審査 r1 MEDIUM-2）、本便の 7 件は `.form-row` の外にあるため、本便の変更で当たり方は変わらない。コメントの見直しは AY-4c-2b の後の残件整理で扱う。

### 3-5. 文書

- docs/specs/design-system/design.md の AY-4c の記録に、AY-4c-2a の結果（件数と残り 2 件）を追記する（AY-4c-1 と同じ場所・同じ書き方）。

## 4. 影響範囲

- 画面: 在庫表（仕入先の絞り込み、PC とスマホ）、担当者の全画面編集、スタッフの全画面編集と新規登録モーダル、受信箱（プロフィールモーダルの競合チェック、商談カルテの営業形態）、ロール・権限の権限カード、通知設定の Discord 追加・編集モーダル（副作用）。
- 試験: 対象 7 ファイルと NotificationsPage を import・描画する試験は `git grep -lw` で拾えない親画面経由のものがあるため、unit を全部回す。recon で分かっているもの:
  - frontend/src/components/MultiSelect.test.tsx（:72・:74・:76 で input を testid で取る。CheckboxControl は testid を input へ渡す）
  - frontend/src/pages/inventory/InventoryPage.*.test.tsx（singlefetch・noechopatch・settings・tablelayout）
  - frontend/src/components/StaffFormButtonMigration.test.tsx:105-106（`getByRole('checkbox', { name: tr(key) })`。金型でも名前は label の文字）
  - frontend/src/components/FullPageFormButtonMigration.test.tsx（ContactEditPage）
  - frontend/src/components/PurchaseAdminEditorButtonMigration.test.tsx・RoleKnowledgeButtonMigration.test.tsx（RolesPage）
  - frontend/src/components/AllLegacyButtonDynamicMigration.test.tsx・CommerceNavigationButtonMigration.test.tsx・CheckboxControl.test.tsx
  - frontend/src/components/FormActionButtonMigration.test.tsx（NotificationsPage）
  - e2e（CI で回る。ローカルでは実行しない）: 受信箱を開く spec（recon 項目 5）。チェック欄を操作するものは 0。
- API・DB・i18n キー: 変更なし（使う t() キーはすべて既存）。

## 5. 前後実測（マージ前に PO へ提示する）

### 5-1. 測り方（AY-4c-1 §5 と同じ。ファイル名は ay4c2-*）

1. CSS は 変更前 = origin/main を build した CSS、変更後 = 作業ツリーを build した CSS。
2. 型ごとに実物の親を再現した HTML 断片を作り、チェック欄だけを「変更前のマークアップ（実ファイルから写す）」と「本物の金型を renderToStaticMarkup した DOM」に差し替える。親の class・インライン style は実ファイルから写し、file:line を記録する:
   - H1-1: Popover の中の `.comp-multiselect__option` の行を 3 つ（MultiSelect.tsx:76-87）。
   - H1-6: `.sales-form-option` の行を 3 つ、うち 1 つは `--checked`（SalesFormMultiSelect.tsx:129-141）。
   - H1-7: `.permission-group-body` の grid に `.permission-item` を 3 つ、うち 1 つは disabled、1 つは 2 行に折れる長い文字（RolesPage.tsx:419-429）。
   - H2: `div.form-group` を 2 つ縦に並べ、1 つ目が項目 2 の形、2 つ目が次の兄弟（TextFieldControl の `.form-group`）。項目 3・4 は同じ形であることを実ファイルで確かめて記録する。
   - H2-副作用: NotificationsPage.tsx:128-138 の `.form-group`（見出しの label ＋ Checkbox 3 つ。後は §3-2 の div で包んだ形）。見出しの label の見た目が変わらないこと（display:block・text-secondary・margin-bottom）、3 つが縦に並ぶこと（各 root の top が増えていく・left が同じ）、行どうしの間隔を測る。
   - H3: `.right-panel-row`（縦 flex）の中に `span.right-panel-label` ＋ 欄（InboxProfileModal.tsx:252-264）。
3. 幅 1280 と 390、ライト・ダーク × 未チェック・チェックの 4 通りを Playwright で測る。
4. 測る値: input の幅・高さ・accent-color・margin・枠・背景、文字の font-size・font-weight・color・line-height、input と文字の間隔、root の display・幅・高さ、input と文字の縦の中心のずれ、H2 は `.form-group` の下の間隔（次の兄弟までの距離）、H1-7 は input の上端とカードの文字の1行目の上端のずれ、H1-1・H1-6 は行の高さ（増えていないか）。
5. 出力: evidence-20260910/ay4c2-measure-compare.txt。列は「型｜項目｜前｜後｜差｜金型どおりの差か（○/×と理由1行）」。前後の画像（型ごと・ライト/ダーク・チェック時）も保存。
6. PO への提示は、差がある項目だけを型ごとにまとめた短い表（画像の場所付き）。

### 5-2. `.form-group` の中の金型の全数（実装時）

`.form-group` を祖先に持つ `<Checkbox`・`<CheckboxControl` を全部洗い出す。2 段で行う:
1. 同じファイルの中: frontend/src の tsx を TypeScript の構文木で読み、`<Checkbox`/`<CheckboxControl` の JSX の祖先に `className` が `form-group` を含む要素（文字列・テンプレート文字列の両方）があるものを数える。recon §4-1 の候補 23 ファイル（Checkbox 21・CheckboxControl 2）を必ず含める。
2. ファイルをまたぐもの: 1 の方法で「金型を描く部品」（例 frontend/src/components/DataTable.tsx、ContactChannelForm.tsx、features/tcg-distribution/DistributionTargetForm.tsx、pages/inventory/InventoryFilterPanel.tsx。全部を構文木で洗い出す）を列挙し、その部品を使う JSX の祖先に `form-group` があるかを同じ方法で見る。部品が別の部品に使われる場合は、`form-group` に当たるか画面（pages/ の route 部品）に着くまでたどる。
結果を evidence-20260910/ay4c2-formgroup-ancestors.txt に file:line で残す（1・2 の別、たどった経路）。NotificationsPage の 2 か所と本便の 3 か所（項目 2・3・4）以外が見つかったら、それぞれ §5-1 と同じ方法で前後を測り、表に足す。たどり切れない経路（動的な描画など）があれば NEEDS_DECISION で止める。

## 6. 代替案と選択理由

- 案1（採用）: H2 は `.form-group` を残し、古い CSS（components.css）の側で金型を外す。金型が正本として効き、NotificationsPage の既存の崩れも同時に直る。下の間隔も保てる。
- 案2: H2 の `.form-group` を外して Checkbox を兄弟に置く（UnitsPage.tsx:299-300 の前例）→ 下の間隔 space-4 が無くなる。間隔を戻すには新しい class か style が要る（金型登録のないハードコードになる）。NotificationsPage の崩れも残る。不採用。
- 案3: Checkbox の className（root）に各画面の class を渡す（H1-6・H1-7 を label 型にする）→ design.md:910 の「配置の口は layoutClassName」と合わない。同じ詳細度の衝突で結果が CSS の読み込み順に左右される（recon 項目 6・7）。不採用。
- 案4: schedule の 2 件も本便に入れて --accent にそろえる → 色はデータの意味（どのカレンダーか）を持つため、PO の判断なしに変えない。AY-4c-2b に分ける。

## 7. リスクと対処

| リスク | 対処 |
|---|---|
| components.css の変更で、`.form-group` の中の別の Checkbox の見た目が変わる | §5-2 で全数を洗い出し（ファイルをまたぐものも）、全部の前後を測って提示 |
| NotificationsPage の 3 つの欄が横に並ぶ | §3-2 で div で包む。§5 で縦に並ぶことを測る（× なら止める） |
| H2・NotificationsPage の押せる範囲が全幅から文字の幅に縮む | 金型の形（AY-4c-1 G3 と同じ判断）。§5 で root の幅を測って提示 |
| `:where(:not(.comp-checkbox))` で `.form-group label` の勝ち負けが変わる | `:where` で詳細度 0,1,1 を保つ。§5-1 の H2-副作用で見出しの label の値が前後同じことを測る（× なら止める） |
| radio/range/file の見た目が変わる | checkbox の行だけ消す。変更後の components.css で radio/range/file の 3 行が :19 付近と :33 付近に残ることを差分で確認 |
| H1-7 の margin-top（pages-layout.css:635、詳細度 0,2,1）が金型の input に当たる | 意図どおり（カードの配置）。§5-1 で上端のずれが前後同じことを測る |
| H1-1・H1-6 の行の高さが変わる | §5-1 で行の高さを測る。変わったら差として提示 |
| H3 の root が縦 flex の中で横に伸びる・縮む | §5-1 で root の幅を測って提示 |
| H2 の縦の位置が上寄せになる（AY-4b・AY-4c-1 と同じ金型の形） | §5-1 で提示（PO 決定「金型の形にそろえる」の範囲） |
| 削除する CSS が他で使われている | 削除前に `git grep -n "comp-multiselect__check\|sales-form-option input" -- frontend` が対象の行だけであることを確認 |
| クラス名の重複（#4339 の教訓） | 本便は新しい class を作らない |

## 8. 受入条件と検証方法

| 基準 | 検証方法 |
|---|---|
| 本便の 7 件が金型になり、生の checkbox が 9 → 2 件（schedule の 2 件だけ残る） | `git grep -n 'type="checkbox"' -- ':(glob)frontend/src/**/*.tsx'` から金型・既製部品 3 行（Checkbox.tsx・CheckboxControl.tsx・Toggle.tsx）を除いた行が SchedulePageImpl.tsx の 2 行だけ（9 − 7 = 2。変更前は 12 行 − 3 = 9） |
| checkbox 向けの古い CSS セレクタが 4 → 1 行 | `git grep -n 'type="checkbox"' -- ':(glob)frontend/src/**/*.css'` が変更前 4 行（components.css:19・:33、pages-layout.css:635、InboxPage.css:1862）→ 変更後 pages-layout.css の 1 行だけ |
| components.css に radio/range/file の行が残る | 変更後の components.css で `input[type="radio"]`・`input[type="range"]`・`input[type="file"]` がそれぞれ 2 行ずつ |
| `<CheckboxControl` が 3 件、`<Checkbox` が差し引き 4 件増える | コミット後に `git diff origin/main...HEAD -- frontend/src > diff.txt` を保存し、`grep -cE '^\+.*<CheckboxControl([^A-Za-z]|$)' diff.txt` が 3・`grep -cE '^-.*<CheckboxControl([^A-Za-z]|$)' diff.txt` が 0、`grep -cE '^\+.*<Checkbox([^A-Za-z]|$)' diff.txt` が 6・`grep -cE '^-.*<Checkbox([^A-Za-z]|$)' diff.txt` が 2（NotificationsPage の 2 件は div で包んで字下げが変わるため + と - の両方に出る。差し引き +4 = ContactEditPage・StaffEditPage・StaffPage・InboxProfileModal 各 1）。macOS の grep は -P が無いため -E で書く |
| `.comp-multiselect__check` が 0 件 | `git grep -n "comp-multiselect__check" -- frontend` が 0 行 |
| `.form-group label` の詳細度が変わらない | components.css の差分で `.form-group label:where(:not(.comp-checkbox))` の形であることを確認 |
| 試験・型・lint・ビルド | frontend で npm run build、npx tsc --noEmit -p tsconfig.json、npm run lint、npm run test:unit（全部）、npm run check:all、npm run check:i18n-missing-keys、npm run build-storybook がすべて exit 0 |
| 前後実測 | §5 の表で「金型どおりの差か」が × の行が 0 件。× があれば PR を作らず報告 |
| `.form-group` の中の金型の全数 | evidence-20260910/ay4c2-formgroup-ancestors.txt に同じファイル・ファイルをまたぐ両方の全件の file:line があり、全件が §5 の表に載っている |

## 9. 外部・過去事例の参照と我々への応用

- 過去事例（社内）: AY-4b（#4343、前後実測で金型定義との食い違い 0、本番反映済み）、AY-4c-1（#4346、24 件、本番反映済み）。本便は同じ型と実測方法を使う。
- 外部事例: 不要（社内の既存金型への載せかえと、古い CSS の当たり範囲の修正で、外部の事例は判断材料にならない）。

## 10. 切り戻し

本便の PR の merge commit を revert する。DB・API への影響はない。

## 11. 維持の仕組み

- 守り手: frontend/src/components/CheckboxControl.test.tsx、§4 の既存試験、check:all（ui ガバナンス）。
- 生 checkbox の再発検出は CI に無い。AY-4c-2b で 0 件になった後に、check-ui-governance へ生 checkbox の検出を足すかを別に判断する（docs/specs/design-system/design.md に残件として書く）。

## 12. 審査

- r1（Opus、2026-10-16）: REVISE。HIGH 2（NotificationsPage が横並びになる副作用・§8 の CSS の数え方）・MEDIUM 4・LOW 6。全文 /tmp/CC報告ファイル/ssot-checkbox/ay4c2/design-review.md。金型の props・`:where` の詳細度・削除する CSS の使い手・tsx の式・ADR との整合は実物と一致。
- r1 の指摘は本文に反映済み（§2 表、§3-1 前後の全文と import の位置・空行、§3-2 H2 の差・項目 3・4 の全文・NotificationsPage の div、§3-3 word-break、§3-4、§4、§5-1、§5-2 ファイルをまたぐ確認、§7、§8）。
- r2（Opus、2026-10-16）: APPROVE。全文 /tmp/CC報告ファイル/ssot-checkbox/ay4c2/design-review-r2.md。§8 の変更前の値は実物と一致。LOW 1（§8 の差分はコミット後に数える）は本文に反映済み（再審査不要）。
