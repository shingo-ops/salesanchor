# AY-4b 設計: super-admin 専用・未到達のチェック欄 24 件を金型へ

- 親の仕様書: docs/specs/design-system/design.md（デザインシステムのあるべき姿。§AY-4a に CheckboxControl、§3-6(a) に Checkbox の定義）
- 状態: 設計審査済み。r1 REVISE（/tmp/CC報告ファイル/ssot-checkbox/ay4b/design-review.md）→ r2 条件付き APPROVE（design-review-r2.md、指摘1・2と LOW を反映済み）。
- recon: docs/handoff/ay4b-checkbox/recon.md（件数・到達根拠・マークアップ・CSS）
- 対象ADR: ADR-144（UI ガバナンス・金型先確認）、ADR-067（デザイントークン）、ADR-027（i18n）
- 前便: docs/handoff/ay4a-checkbox/design.md（#4328・#4339）

## 1. 目的（PO の言葉）

- 2026-10-15 PO「y」: チェック欄の色を全部 --accent にそろえる。画面ごとに順に載せかえ、マージ前に前後の比較を見せる。
- 2026-10-15 PO「y」: 金型は役割で分ける。文字と並ぶ欄は label 型 Checkbox（frontend/src/components/Checkbox.tsx）、表の中などの単独の欄は CheckboxControl（frontend/src/components/CheckboxControl.tsx）。super-admin の 20 件から順に。

利用者に見える変化: super-admin の各マスタ画面の「有効」欄などで、チェック欄の色が --accent になり、文字の太さ・大きさ・縦の位置が Checkbox 金型の形にそろう（§5 で前後を実測して PO に見せる）。

## 2. 対象と対象外

対象 24 件・20 ファイル（recon.md の表の番号）:

| 区分 | 件数 | 番号 | 置き換え先 |
|---|---|---|---|
| A: 文字と並ぶ・label のインライン style（flex, gap）だけ | 15 | #1, #10, #11〜#24 のうち RuleTestPanel を除く 13 | Checkbox |
| A': 同上・文字を span(font-sm) で包み cursor:pointer 付き | 1 | RuleTestPanel.tsx:485 | Checkbox |
| B/C/D: 文字と並ぶ・専用 class | 5 | #2 .pmd-confirm-check（規則なし）、#3 .dist-checkbox-row、#4〜#6 .lv-check-label | Checkbox |
| E: 文字と並ぶ・インライン style に余白・色・字の大きさ | 1 | #7 ExtractionPromptConfigTab.tsx:210 | Checkbox（§3-4） |
| F: 表のセルで単独・aria-label 付き | 2 | #8 KnowledgeAliasesTab.tsx:341、#9 :417 | CheckboxControl |

対象外: 一般画面の 33 件（AY-4c）。Checkbox.tsx・CheckboxControl.tsx の中身は変えない（props 追加なし）。components.css:19-42 の `.form-group input[type="checkbox"]` は対象 24 件に掛からないので本便では触らない（AY-4c で撤去）。表の例外の ui-allow（SupplierDetailDrawer.tsx:433、SupplierMasterPanel.tsx:399）は触らない。

## 3. 変更前後

### 3-1. Checkbox へ（22 件共通の型）

変更前（例 frontend/src/pages/super-admin/components/ConditionDefsMasterPanel.tsx:226-233）:

```tsx
<label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
  <input
    type="checkbox"
    checked={form.is_active}
    onChange={e => setForm({ ...form, is_active: e.target.checked })}
  />
  {t(`${f}.isActive`)}
</label>
```

変更後:

```tsx
<Checkbox
  label={t(`${f}.isActive`)}
  checked={form.is_active}
  onChange={e => setForm({ ...form, is_active: e.target.checked })}
/>
```

- 外側の label・その style・className を消し、文字は `label` prop へ。文字はどれも string で渡せる: 21 件は t() 1つ、#7 は三項で t() のどちらか（§3-4）、RuleTestPanel は span の中の t() 1つ（span は消す）。
- input にあった属性（checked・onChange・disabled（#1 のみ）・data-testid（#7））はそのまま Checkbox に渡す（Checkbox は className・id 以外を input に渡す＝frontend/src/components/Checkbox.tsx:54）。
- size は既定 md（font-sm）。
- import は `import { Checkbox } from "<相対パス>/components/Checkbox";`。
- 金型が無いことを理由にした ui-allow コメント 2 件だけを削除する: frontend/src/features/supplier-master/SupplierDetailDrawer.tsx:411 (#3564)、frontend/src/pages/super-admin/components/UnitIgnorePhrasesPanel.tsx:168 (#4032)。

### 3-2. 専用 class の後始末

- #2 ProductMasterDrawer.tsx:233 の `pmd-confirm-check`: 規則が無い class。消すだけ。
- #3 DistributionTargetForm.tsx:238 の `dist-checkbox-row`: 使用はこの1か所。frontend/src/features/tcg-distribution/distribution.css:322-328 の規則を削除。
- #4〜#6 FedexLabelValidationTab.tsx:288/302/316 の `lv-check-label`: 使用はこの3か所。frontend/src/pages/integrations/FedexLabelValidationTab.css:430-439 の規則（見出しコメント「── チェックラベル ──」を含む）を削除し、包む要素は作らない。上の説明文との間隔は margin-top 8px が無くなり、p.form-hint の下余白（frontend/src/components.css:462）だけになる。この部品はどの画面からも使われていない（recon.md の到達表）ので利用者への影響は無く、変わってよいとする。新しい class は作らない。

### 3-3. RuleTestPanel.tsx:483-490

span(font-sm) と cursor:pointer は Checkbox md が同じ値を持つ（frontend/src/components/Checkbox.css:8-16 の font-size var(--font-sm)・cursor:pointer）ので、そのまま §3-1 の型にする。

### 3-4. #7 ExtractionPromptConfigTab.tsx:199-221

- 下の TextareaControl との間の余白 marginBottom var(--space-3) は保つ: Checkbox を `<div style={{ marginBottom: "var(--space-3)" }}>` で包む（同ファイルは余白をトークン参照のインライン style で書いている。色・字の指定は持ち込まない）。
- color var(--text-secondary) は持ち込まない（金型の --text-primary になる）。この差は §5 で PO に見せる。
- label は `configs[key].is_active ? t(`${p}.active`) : t(`${p}.inactive`)` をそのまま渡す。data-testid は input に付く（Checkbox.tsx:54）。

### 3-5. CheckboxControl へ（#8・#9）

```tsx
<td style={{ textAlign: "center" }}>
  <CheckboxControl
    checked={ruleSelected.has(r.id)}
    onChange={() => toggleRule(r.id)}
    aria-label={r.pattern}
    data-testid={`rule-select-${r.id}`}
  />
</td>
```

#9 は aliasSelected / toggleAlias / a.alias_text / `alias-select-${a.id}` で同じ形。td はそのまま。

### 3-6. 文書

- docs/specs/design-system/design.md に §AY-4b を追記（役割分けの PO 決定・対象 24 件・削除した規則・前後実測の場所）。
- 本 design.md・recon.md（recon.md の LOW 指摘: ay4b_markup.txt で切れていた #7 の文字の行 :220 と、CheckboxControl の行番号を実ファイルに合わせて直す）。

## 4. 影響範囲

- 画面: /super-admin 配下（AnalysisRulesPage・TcgDistributionPage・TcgLineImportPage ほか recon.md の到達表）。一般利用者の画面は変わらない。
- 未到達 4 件（SupplierDetailDrawer・FedexLabelValidationTab）は描画されないので、利用者への影響なし。
- 試験（実行して確かめる）: 対象を描く試験ファイルを全部回す。少なくとも frontend/src/features/tcg-analysis-review/ProductMasterDrawer.test.tsx（:119 getByRole("checkbox")）、frontend/src/pages/super-admin/components/UnitIgnorePhrasesPanel.test.tsx（:65）、RoleKnowledgeButtonMigration.test.tsx（KnowledgeAliasesTab を描く）、DistributionTargetForm.test.tsx、CheckboxControl.test.tsx。実装役は `git grep -l` で対象 20 ファイルの部品名を import する試験を洗い出し、全部回す。Checkbox.test.tsx は存在しない。

## 5. 前後実測（マージ前に PO へ提示する）

作り方（前便 evidence-20260910/ay4a-measure.cjs・ay4a-render.tsx を手本、ファイル名は ay4b-*）:

1. CSS: 変更前は origin/main を build した dist の CSS、変更後は作業ツリーを build した dist の CSS を使う（どちらもアプリ全体の CSS 1 枚。トークンと components.css を含む）。
2. 型ごとに、実物の親を再現した HTML 断片を前後で同じに作り、中のチェック欄だけを「変更前のマークアップ（実ファイルからそのまま写す）」と「変更後の金型が描く DOM」に差し替える。変更後の DOM は本物の金型（Checkbox・CheckboxControl）を renderToStaticMarkup して作る（手書きしない）。親は実ファイルの親要素の class とインライン style をそのまま写す（file:line を断片の横に記録）:
   - A-同じ行（5 件）: 2 列 grid で TextField と同じ行の右列に入るもの。ProductCategoriesMasterPanel.tsx・UnitMasterPanel.tsx・NoteMasterPanel.tsx（label :300）・QuantityUnitsMasterPanel.tsx（:241）・TypeMasterPanel.tsx（:268）。親 grid は例 ProductCategoriesMasterPanel.tsx:256。左列に TextField（comp-field の DOM）も置いて描く。
   - A-単独行（10 件）: grid でチェック欄だけの行になる 8 件（ConditionDefsMasterPanel.tsx・ConditionsMasterPanel.tsx（:446）・ProductFormatsMasterPanel.tsx・ProductKindsMasterPanel.tsx・ProductLinesMasterPanel.tsx・SupplierMasterPanel.tsx（:377）・UnitIgnorePhrasesPanel.tsx・WeightClassesMasterPanel.tsx）、#1 SupplierDetailDrawer.tsx（flex の縦並び）、#10 KnowledgeAliasesTab.tsx:481（実装役が親を実ファイルで確かめて記録）。
   - A': RuleTestPanel の実物の親。
   - B: .dist-checkbox-row の親（DistributionTargetForm.tsx の親要素）。
   - C: .lv-step.card の中、p.form-hint の下。
   - D: .pmd-warning の中。
   - E: ExtractionPromptConfigTab の親、下に TextareaControl の DOM を置く。
   - F: 表の td（text-align center）。
3. 画面の幅 1280 と 390 のそれぞれで、ライト・ダーク × 未チェック・チェックの 4 通りを Playwright により測る。
4. 測る値: input の幅・高さ・accent-color、文字の font-size・font-weight・color・line-height、input と文字の間隔、label（金型の root）の幅・高さ、input の縦の中心と文字の縦の中心のずれ、A-同じ行では「チェック欄の縦の中心と左の TextField の入力枠の縦の中心のずれ」、C・E では上下の要素との間隔。
5. 出力: evidence-20260910/ay4b-measure-compare.txt に表で出す。列は「型｜項目｜前｜後｜差｜金型どおりの差か（○/×と理由1行）」。差が 0 の項目も行として出す。前後の画像（型ごと・ライト/ダーク・チェック時）も保存する。
6. PO への提示は、差がある項目だけを型ごとにまとめた短い表（画像の場所付き）にする。

## 6. 代替案と選択理由

- 案1（採用）: PO 決定どおり、文字と並ぶ欄は Checkbox、表の単独欄は CheckboxControl。
- 案2: 全部 CheckboxControl にして外側 label は残す → PO が役割分けを選んだので不採用。
- 案3: Checkbox に style/余白/縦位置の props を足す → 1〜2 件のために金型の口を増やすことになり、AY-4c の結果を見てから判断する。本便は #7 だけ包む div で余白を保つ。

## 7. リスクと対処

| リスク | 対処 |
|---|---|
| A-同じ行で、縦の位置が中央寄せ（今の align-items:center）から上寄せ（Checkbox.css:10 の flex-start）に変わり、左の入力欄と縦がずれる | §5 の A-同じ行で縦のずれを px で測り PO に見せる |
| #7 は div で包むため root が inline-flex で文字の分の幅になり、クリックできる幅が縮む | §5 の E で label の幅を測る |
| 文字が font-weight medium・--text-primary になる | §5 で提示（PO 決定「金型の形にそろえる」の範囲） |
| input の大きさが 1.1em（font-sm の 1.1 倍）になる | §5 で提示 |
| 試験の取り方（role・testid）が変わる | §4 の試験を全部実行 |
| クラス名の重複（#4339 の教訓） | 本便は新しい class を作らない |

## 8. 受入条件と検証方法

| 基準 | 検証方法 |
|---|---|
| 対象 20 ファイルの生 `type="checkbox"` が 0 件 | 対象 20 ファイルを `git grep -n 'type="checkbox"'` して 0 件 |
| frontend/src の生 checkbox が 57→33 件 | `git grep -n 'type="checkbox"' -- frontend/src` の行数から、CSS セレクタ 5 行と金型・既製部品の自身 3 行（Checkbox.tsx・CheckboxControl.tsx・Toggle.tsx）を引いて 33（素の行数は 41） |
| 22 件が Checkbox、2 件が CheckboxControl | 対象ファイルで `git grep -n '<Checkbox$\|<Checkbox '` が 22、`git grep -n '<CheckboxControl'` が 2 |
| 消した class が 0 件 | `git grep -n 'dist-checkbox-row\|lv-check-label\|pmd-confirm-check' -- frontend/src` が 0 件 |
| 金型未登録を理由にした ui-allow 2 件だけが消え、表の例外 2 件は残る | SupplierDetailDrawer の (#3564)・UnitIgnorePhrasesPanel の (#4032) が 0 件、SupplierDetailDrawer.tsx・SupplierMasterPanel.tsx の表の ui-allow が各 1 件残る（git grep -n 'ui-allow' で前後比較） |
| 試験・型・lint・ビルドが通る | tsc・lint・vitest（§4 の試験全部、unit project 直列）・check:all・check:i18n-missing-keys・build が exit 0 |
| 前後の差が §5 の表で全部見える | evidence に ay4b-measure-compare.txt と前後画像。PO に提示し「y」を得てからマージ |

## 9. 外部・過去事例の参照と我々への応用

不要。社内の既存金型2つへの載せかえで、外部の事例は判断材料にならない。過去事例は §AY-4a（#4328・#4339）と §AY-3b（#4313、前後実測を PO に提示）。

## 10. 切り戻し

本便の merge commit を revert する。DB・API への影響なし。

## 11. 維持の仕組み

- 守り手: frontend/src/components/Checkbox.tsx・frontend/src/components/CheckboxControl.tsx（金型）、frontend/scripts/check-stories-count.js。
- 生 checkbox の新規追加を止める自動検査は未整備（AY-4c 完了後に検討。本便では作らない）。
