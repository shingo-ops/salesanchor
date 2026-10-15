# AY-4c-1 設計: 一般画面のチェック欄のうち、金型をそのまま使える 24 件を金型へ

- 作成: 2026-10-16 Opus（Planner）/ 基点 origin/main 5cda22071 / ブランチ release/checkbox-ay4c
- recon: docs/handoff/ay4c-checkbox/recon.md（行番号 #1〜#33 は recon の表の番号）
- 手本: docs/handoff/ay4b-checkbox/design.md（PR #4343、本番反映済み）
- 対象ADR: ADR-144（UI ガバナンス）、ADR-067（デザイントークン）
- 状態: 設計審査済み（r2 APPROVE、2026-10-16）・実装未着手

## 1. 目的（PO の言葉）

- 2026-10-15 PO「y」: チェック欄の色を全部 --accent にそろえる。画面ごとに順に載せかえ、マージ前に前後の比較を見せる。
- 2026-10-15 PO「y」: 金型2つを役割で分ける。文字と並ぶ欄は label 型 Checkbox（frontend/src/components/Checkbox.tsx）、表の中などの単独の欄は CheckboxControl（frontend/src/components/CheckboxControl.tsx）。残りをこの分け方で載せかえる。
- 利用者に見える変化: 一般画面のチェック欄の大きさ・色・文字の太さが、AY-4b で本番に入った管理画面と同じ形になる。

## 2. 対象と対象外

AY-4c を2便に分ける。理由: 33 件のうち 9 件は、今の金型の口（props）では今の見た目・試験・構造を保てず、金型に口を足すか（新しい金型の形＝PO 判断）、包み方を個別に決める必要がある（recon.md「金型の props で受けられない／変わるもの」）。残り 24 件は AY-4b と同じ形でそのまま載せかえられる。

**AY-4c-1（本便）24 件**

| 型 | recon # | 件数 |
|---|---|---|
| G1 form-row（.form-grid > .form-row の label） | #1, #4, #5, #6, #10 | 5 |
| G2 flex の label（インライン style の label） | #15, #16, #17, #18, #19, #20, #21, #22, #32, #33 | 10 |
| G3 grid 全幅（gridColumn: 1 / -1） | #8, #31 | 2 |
| G4 Roles の一括（.chk-label） | #24, #25 | 2 |
| G5 表のセル（CheckboxControl md） | #3, #7, #23 | 3 |
| G6 Inbox 一括選択（CheckboxControl sm） | #11, #12 | 2 |

**対象外（AY-4c-2 で別に設計する）9 件**: #2 MultiSelect（root に別部品のクラス）、#9・#29・#30（`.form-group label` の display:block が金型を上書き）、#13 InboxProfileModal・#14 SalesFormMultiSelect・#26 RolesPage:422（label の中身が文字列でない／label 側の testid・クラス）、#27・#28 schedule（データの色。金型に色の口が無い）。

**本便で触らない CSS**: frontend/src/components.css:19・:33（`.form-group input[type="checkbox"]`。#9・#29・#30 がまだ使う）、frontend/src/company-forms.css:102-106・:137-142（`.form-row input:focus`。checkbox 以外の input にも当たる）。

## 3. 変更前後

### 3-1. G1・G2 共通の型（15 件）

変更前（例 frontend/src/pages/units/UnitsPage.tsx:301 付近。外側 label の class・style は箇所ごとに違う）:

```tsx
<label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
  <input type="checkbox" checked={X} onChange={Y} /* data-testid / disabled があればそのまま */ />
  {LABEL_TEXT}
</label>
```

変更後:

```tsx
<Checkbox label={LABEL_TEXT} checked={X} onChange={Y} /* 元の data-testid / disabled をそのまま */ />
```

- 外側 label の class・インライン style は捨てる（見た目は金型が決める）。#15 の fontWeight semi も捨てる（金型の medium になる。§5 で提示）。
- 外側 label に `key` が付いている箇所（frontend/src/pages/inventory/InventoryFilterPanel.tsx:150・:181・:218・:240・:259 の `.map` の中）は、`key` を `<Checkbox key={...}>` へそのまま移す（落としても lint・tsc は検出しないので、実装後に5か所を目で確認する）。
- G1 の 5 件（#1,#4,#5,#6,#10）は文字の前に `{" "}` がある。空白を捨てて `t(...)` だけを label に渡す。外側の div.form-row は残し、その中の label だけを Checkbox に替える。label の中にある古いコメント（frontend/src/components/ContactChannelForm.tsx:226・frontend/src/pages/company-detail/CompanyContactsTab.tsx:205）は label と一緒に消す。
- #20 の label は `t(..., { defaultValue: o })`（文字列）をそのまま渡す。
- G1（#1,#4,#5,#6,#10）は Checkbox の root（label）が `.form-row` の直下に来るので、frontend/src/company-forms.css:94-98・:128-133 の `.form-row > label` 規則（詳細度 0,2,1。font-size sm・weight medium・color text-secondary）が今と同じく当たる。文字色は今と同じ text-secondary のまま。この規則は display・align・gap を指定しないので金型の inline-flex は保たれる。frontend/src/company-forms.css:102・:137 の `.form-row input:focus` も金型より強く当たり、押したときに枠が光る動きは今と同じ。

### 3-1-2. 対象ファイルと import（全グループ共通）

import は各ファイルの既存の components の import と同じ書き方で1行足す（Checkbox は `{ Checkbox } from ".../Checkbox"`、CheckboxControl は `{ CheckboxControl } from ".../CheckboxControl"`）。

| ファイル | 足す import |
|---|---|
| frontend/src/components/ContactChannelForm.tsx | `./Checkbox` |
| frontend/src/pages/company-detail/CompanyAddressModal.tsx | `../../components/Checkbox` |
| frontend/src/pages/company-detail/CompanyContactsTab.tsx | `../../components/Checkbox` |
| frontend/src/pages/company-detail/CompanyDiscordTab.tsx | `../../components/Checkbox` |
| frontend/src/pages/contacts/ContactsPage.tsx | `../../components/Checkbox` |
| frontend/src/pages/inventory/InventoryFilterPanel.tsx | `../../components/Checkbox` |
| frontend/src/pages/note-master/NoteMasterPage.tsx | `../../components/Checkbox` |
| frontend/src/pages/product-categories/ProductCategoriesPage.tsx | `../../components/Checkbox` |
| frontend/src/pages/units/UnitsPage.tsx | `../../components/Checkbox` |
| frontend/src/pages/conditions/ConditionsPage.tsx | `../../components/Checkbox` と `../../components/CheckboxControl` |
| frontend/src/pages/status-master/StatusMasterPage.tsx | `../../components/Checkbox` |
| frontend/src/pages/roles/RolesPage.tsx | `../../components/Checkbox` |
| frontend/src/pages/admin/InventoryVisibilityPage.tsx | `../../components/CheckboxControl` |
| frontend/src/pages/products/ProductsPage.tsx | `../../components/CheckboxControl` |
| frontend/src/pages/inbox/InboxConversationList.tsx | `../../components/CheckboxControl` |
| frontend/src/pages/inbox/InboxConversationListMobile.tsx | `../../components/CheckboxControl` |

CSS: frontend/src/pages-layout.css（.chk-label 削除）、frontend/src/pages/inbox/InboxPage.css（.inbox-bulk-check-all 削除）。

### 3-2. G3 grid 全幅（#8 frontend/src/pages/conditions/ConditionsPage.tsx:352-359、#31 frontend/src/pages/status-master/StatusMasterPage.tsx:300-307）

変更後（#8）:

```tsx
<div style={{ gridColumn: "1 / -1" }}>
  <Checkbox label={t(`${f}.fields.isActive`)} checked={form.is_active} onChange={e => setForm({ ...form, is_active: e.target.checked })} />
</div>
```

#31 は `form.enabled`・`` t(`${f}.enabled`) ``・`setForm({ ...form, enabled: e.target.checked })` で同じ形。

- 包む div の style は gridColumn だけ（AY-4b #7 と同じ「配置だけを包む div が持つ」形）。
- div は grid の全幅を占めるが、中の Checkbox の root は inline-flex（frontend/src/components/Checkbox.css:9）なので文字の分の幅になる。今は label が全幅で、行の右側の空白を押してもチェックが切り替わる。変更後は、チェック欄と文字の上だけで切り替わる（AY-4b #7 と同じ変化。§5 で幅を測って提示）。

### 3-3. G4 Roles（frontend/src/pages/roles/RolesPage.tsx:396-415）

変更後（:396 の1件目。2件目 :406 は menuVisible / toggleMenuVisibility / roles.menuVisibilityTitle / roles.showMenu で同じ形）:

```tsx
<span title={t("roles.toggleAllTitle")}>
  <Checkbox
    label={t("roles.selectAll")}
    checked={allChecked}
    disabled={!canEditPerms}
    onChange={(e) => toggleCategory(category, e.target.checked)}
  />
</span>
```

- title は今と同じく文字を含む全体にかかるよう、包む span に置く（Checkbox に渡すと input だけにかかるため）。
- frontend/src/pages-layout.css:614-625 の `.chk-label` と `.chk-label input[type="checkbox"]` を削除（使用は上の2か所のみ: `git grep -n chk-label -- frontend`）。:610-613 の `.permission-group-toggles` は残す。

### 3-4. G5 表のセル（#3 frontend/src/pages/admin/InventoryVisibilityPage.tsx:153、#7 frontend/src/pages/conditions/ConditionsPage.tsx:254、#23 frontend/src/pages/products/ProductsPage.tsx:356）

```tsx
<CheckboxControl checked={X} onChange={Y} /* 元の aria-label・data-testid・onClick をそのまま */ />
```

- `<input type="checkbox"` を `<CheckboxControl` に替え、`type="checkbox"` の行を消すだけ。td・renderCell の構造は触らない。

### 3-5. G6 Inbox（#11 frontend/src/pages/inbox/InboxConversationList.tsx:120-126、#12 frontend/src/pages/inbox/InboxConversationListMobile.tsx:144 付近）

```tsx
<CheckboxControl
  size="sm"
  checked={isAllSelected}
  onChange={toggleSelectAll}
  aria-label={t("inbox.selectAll")}
/>
```

- className="inbox-bulk-check-all" を外し、frontend/src/pages/inbox/InboxPage.css:159-165 の `.inbox-bulk-check-all` を削除（使用は2か所のみ）。寸法・色・cursor は CheckboxControl --sm と同じ（recon.md「Inbox の現状」）。flex-shrink:0 は無くなる（§5 で幅を測る）。

### 3-6. 文書

- docs/specs/design-system/design.md の §AY-4b の後に §AY-4c-1 を追記する（対象 24 件・削除した CSS・前後実測の場所）。あわせて、AY-4c-2 へ回すものを「残り」として明記する: 9 件（#2,#9,#13,#14,#26,#27,#28,#29,#30）、frontend/src/components.css:19・:33 の checkbox 行、frontend/src/company-forms.css:100・:135 のコメントと :102-106・:137-142 の `.form-row input:focus`（checkbox のために残すというコメントの理由は本便で薄れるが、規則は他の input にも当たるので AY-4c-2 で扱う）、予定の色（dataColor は frontend/src に実在しない。金型に色の口を足すかは PO 判断）、生 checkbox の再発検出。
- recon.md は変更しない（必要な訂正があれば実装便で行番号だけ直す）。

## 4. 影響範囲

- 画面: 連絡先・会社（モーダルのフォーム）、条件・状態・単位・備考・商品カテゴリの各マスタ画面、在庫の絞り込み、在庫の表示権限、商品一覧の選択、ロールの一括、受信箱の一括選択。
- 試験: 対象 16 ファイルを import・描画する試験を `git grep -lw` で全部洗い出し、全部回す（AY-4b と同じ）。審査時点で分かっているもの:
  - frontend/src/components/PurchaseAdminEditorButtonMigration.test.tsx（Roles。getByRole の name は label 文字のまま）
  - frontend/src/components/MasterSearchButtonMigration.test.tsx
  - frontend/src/components/AllLegacyButtonDynamicMigration.test.tsx
  - frontend/src/components/CommerceNavigationButtonMigration.test.tsx
  - frontend/src/components/RoleKnowledgeButtonMigration.test.tsx
  - frontend/src/components/PageFormButtonMigration.test.tsx
  - frontend/src/components/CheckboxControl.test.tsx
  - e2e（CI で回る。ローカルでは実行しない）: frontend/tests-e2e/tenant-inventory-visibility.spec.ts:86-89（testid は CheckboxControl が input に渡す）、frontend/tests-e2e/visual-language/inbox-single-column.spec.ts
- API・DB・i18n キー: 変更なし。

## 5. 前後実測（マージ前に PO へ提示する）

AY-4b の §5 と同じ作り方（evidence-20260910/ay4b-measure.cjs・ay4b-render.tsx を手本、ファイル名は ay4c-*）:

1. CSS は、変更前 = origin/main を build した CSS、変更後 = 作業ツリーを build した CSS。
2. 型 G1〜G6 ごとに実物の親を再現した HTML 断片を作り、チェック欄だけを「変更前のマークアップ（実ファイルから写す）」と「本物の金型を renderToStaticMarkup した DOM」に差し替える。親の class・インライン style は実ファイルから写し、file:line を記録する:
   - G1: `.modal-content-wide > form.form-grid > div.form-row`（#4 CompanyAddressModal の実物の親）。
   - G2: #15 と #16（InventoryFilterPanel の親 div。#16 は flex wrap の中に3つ並べる）。
   - G2-同じ行: #21（NoteMasterPage の親 grid 2 列）。左列に同じ行の TextField（comp-field の DOM）を置いて描く。#22・#32・#33 も同じ形であることを実ファイルで確かめて記録する（AY-4b の A-同じ行と同じ）。
   - G3: #8 の親 grid（2 列）。
   - G4: `.permission-group-toggles` の中に2つ。
   - G5: 表の td（#23 は rowSpan と text-align を写す）。
   - G6: `.inbox-bulk-bar` の中（右に .inbox-bulk-count の文字）。390 幅では長い件数の文字にして、チェック欄が縮まないかを見る。
3. 幅 1280 と 390、ライト・ダーク × 未チェック・チェックの 4 通りを Playwright で測る。
4. 測る値: input の幅・高さ・accent-color、文字の font-size・font-weight・color・line-height、input と文字の間隔、root の幅・高さ、input と文字の縦の中心のずれ、G2-同じ行は「チェック欄の縦の中心と左の TextField の入力枠の縦の中心のずれ」、G3 は包む div の幅（grid の全幅）と root の幅（クリックできる幅）、G4 は title がどの要素にあるか、G6 は input の幅（縮んでいないか）。
5. 出力: evidence-20260910/ay4c-measure-compare.txt。列は「型｜項目｜前｜後｜差｜金型どおりの差か（○/×と理由1行）」。前後の画像（型ごと・ライト/ダーク・チェック時）も保存。
6. PO への提示は、差がある項目だけを型ごとにまとめた短い表（画像の場所付き）。

## 6. 代替案と選択理由

- 案1（採用）: 金型をそのまま使える 24 件を先に載せかえ、残り 9 件は金型の口の追加を含めて AY-4c-2 で設計し PO に聞く。PO の「画面ごとに順に」に合い、1 便の判断点を減らせる。
- 案2: 33 件を1便で → schedule の色の口（新しい金型の形）など PO 判断が要る点が混ざり、24 件の反映まで止まる。不採用。
- 案3: G4 の title を Checkbox に渡す（input に付く）→ ツールチップの出る範囲が狭くなる。包む span で今の範囲を保つ方を採用。

## 7. リスクと対処

| リスク | 対処 |
|---|---|
| G2 の文字が font-weight medium・text-primary に、#15 は semi → medium に変わる | §5 で提示（PO 決定「金型の形にそろえる」の範囲） |
| G2・G3 の縦の位置が中央寄せから上寄せ（Checkbox.css:10）に変わる。G2-同じ行（#21,#22,#32,#33）は左の入力欄と縦がずれる（AY-4b #4343 で同じ変化（約 -42px）を PO に前後比較で提示し、PO が 2026-10-16 にチャットで y と回答して本番反映済み） | §5 で左の入力枠とのずれを測って提示 |
| G3 のクリックできる幅が行の全幅から文字の分に縮む | §5 で root の幅を測って提示。金型どおりの差として ○ と判定する（全幅を保つには金型に口が要るので AY-4c-2 で扱う） |
| G4 の文字色が text-secondary → text-primary、間隔が space-1 → space-2、user-select:none が無くなり文字を選べるようになる | §5 で提示（金型の形） |
| G6 の flex-shrink:0 が無くなり、390 幅で欄が縮む | §5 で input の幅を測る。縮んだら実装を止めて NEEDS_DECISION |
| G1 の `.form-row > label` 規則が金型の root に当たり、金型と違う色・太さになる | 今と同じ見た目が続くことを §5 で確認（root の color・weight を測る） |
| 削除する CSS が他で使われている | 削除前に `git grep -n "chk-label\|inbox-bulk-check-all" -- frontend` が対象の行だけであることを確認 |
| クラス名の重複（#4339 の教訓） | 本便は新しい class を作らない |

## 8. 受入条件と検証方法

| 基準 | 検証方法 |
|---|---|
| 対象 24 件のファイルの、対象行に生の checkbox が 0 件 | `git grep -n 'type="checkbox"' -- <対象 16 ファイル>` の出力が、対象外の #26（RolesPage:422 付近）だけ |
| frontend/src の生 checkbox が 33 → 9 件 | `git grep -n 'type="checkbox"' -- frontend/src` の行数 − CSS セレクタ（components.css 2・pages-layout.css 1（.permission-item）・InboxPage.css 1（.sales-form-option））− 金型・既製部品 3（Checkbox.tsx・CheckboxControl.tsx・Toggle.tsx）= 9 |
| `.map` の key が保たれている | frontend/src/pages/inventory/InventoryFilterPanel.tsx の5か所で `<Checkbox key=` を目で確認し、行を acceptance に記録 |
| `<Checkbox` が 19 件、`<CheckboxControl` が 5 件増える | origin/main との差分で `^\+.*<Checkbox\b` と `^\+.*<CheckboxControl\b` を数える |
| `.chk-label`・`.inbox-bulk-check-all` が 0 件 | `git grep -n "chk-label\|inbox-bulk-check-all" -- frontend` が 0 行 |
| 試験・型・lint・ビルド | frontend で npm run build、npx tsc --noEmit -p tsconfig.json、npm run lint、npm run test:unit（unit 全部。§4 の一覧は名前で拾えない親画面の試験もあるため全部回す）、npm run check:all、npm run check:i18n-missing-keys、npm run build-storybook がすべて exit 0 |
| 前後実測 | §5 の表で「金型どおりの差か」が × の行が 0 件。× があれば PR を作らず報告 |

## 9. 外部・過去事例の参照と我々への応用

- 過去事例（社内）: AY-4a（#4328・クラス名衝突の修正 #4339）、AY-4b（#4343、24 件を同じ形で載せかえ、前後実測 352 項目で金型定義との食い違い 0、本番反映済み）。本便は AY-4b と同じ型と実測方法を使う。
- 外部事例: 不要（社内の既存金型への載せかえで、外部の事例は判断材料にならない）。

## 10. 切り戻し

本便の PR の merge commit を revert する。DB・API への影響はない。

## 11. 維持の仕組み

- 守り手: frontend/src/components/CheckboxControl.test.tsx、§4 の既存試験、check:all（ui ガバナンス）。
- 生 checkbox の再発検出は CI に無い。AY-4c-2 で 0 件になった後に、check-ui-governance へ生 checkbox の検出を足すかを別に判断する（docs/specs/design-system/design.md に残件として書く）。

## 12. 審査

- r1（Opus、2026-10-16）: REVISE。HIGH 1（G3 の幅）・MEDIUM 3（key の移し忘れ・左の入力欄との縦ずれの実測・試験一覧）・LOW 7。全文 /tmp/CC報告ファイル/ssot-checkbox/ay4c/design-review.md。分け方・金型の選び方・§8 の数式は実物と一致。
- r1 の指摘は本文に反映済み（§3-1-2 追加、§3-1・§3-2・§3-6・§4・§5・§7・§8）。
- r2（Opus、2026-10-16）: APPROVE。全文 /tmp/CC報告ファイル/ssot-checkbox/ay4c/design-review-r2.md。LOW 4 件（N-1 G3 幅の判定基準・N-2 試験を unit 全部に・N-3 PO 受け入れの出典・N-4 状態と見出し順）は本文に反映済み（再審査不要と判定）。
