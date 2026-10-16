# AY-5 recon: 生のラジオボタン 7 件と既存のチェック欄金型

- 作成: 2026-10-16 Sonnet（調査）／ Opus（整理）
- 基点: origin/main b6435490b（作業場所 release/ay5-radio-control）
- 生出力: /tmp/CC報告ファイル/ssot-radio/recon/（01〜63）

## 1. ADR 検索

- docs/adr/ 全体で radio を含む ADR は ADR-144 だけ（ADR-144:134「生 radio は対象外」）。docs/adr/FEATURE-INDEX.md に radio・checkbox・金型の行は 0 件（50〜53）。
- 正本: docs/specs/design-system/design.md
  - :807「RadioControl7 … は別の専用 owner」
  - :921「RadioControl は radio のネイティブ挙動を維持し、チェックボックス/トグルへ置換しない」
  - :1953 PO 回答 2026-10-02「Checkbox/Toggle/Radio の新規金型登録を許可する」
  - :4254（§AY-4d）「対象外: 生 radio（pages/ に 4 件）」

## 2. 生ラジオの全件（03-radio-grep.txt。静的 type="radio" は frontend/src に 8 件）

| # | 場所 | 形 | 選ぶもの |
|---|---|---|---|
| R1 | frontend/src/pages/register/RegisterPage.tsx:456-465 | label（style: display flex・alignItems center・gap var(--spacing-2)・cursor pointer）> input（name shipping_choice・value proceed）＋文字 t("registration.proceedToRegister") | 配送先住所を登録する |
| R2 | frontend/src/pages/register/RegisterPage.tsx:466-475 | 同上＋marginTop var(--spacing-1)、value same、文字 t("registration.shipToSameAddress") | 請求先と同じ住所に配送する |
| R3 | frontend/src/pages/roles/RolesPage.tsx:465-477 | label.color-swatch.selected.color-swatch-legacy（style background・title）> input（name role-color・value・checked・readOnly） | 今の色（パレット外） |
| R4 | frontend/src/pages/roles/RolesPage.tsx:480-493（input は :486-492） | label.color-swatch（style background・title）> input（name role-color・value・checked・onChange） | パレットの色 |
| R5 | frontend/src/components/MergeCompanyModal.tsx:220-228 | td > input（name master-candidate・checked・onChange）。行 tr にも onClick | 統合先の会社 |
| R6 | frontend/src/components/MergeContactModal.tsx:218-228 | 同上。:218 に古いコメント「radio は TextField 対象外のため残置」 | 統合先の担当者 |
| R7 | frontend/src/components/MergeLeadModal.tsx:210-218 | 同上 | 統合先のリード |
| — | frontend/src/components/ChoiceCardGroup.tsx:39 | 金型の中（className comp-choice-card__input） | 対象外 |

- 動的 type: frontend/src/features/tcg-analysis-review/ItemComparison.tsx:45 の input type={kind} は number/text 系だけで radio にならない。
- R1・R2 の質問文は p（fieldset/legend ではない）。ja: 「配送先住所を登録しますか？」（60-i18n-values.txt）。
- R3・R4 は div.color-picker[role=radiogroup][aria-label=t("roles.color")] の中（RolesPage.tsx:462）。input に名前は無く、label の title だけ。
- R5〜R7 の呼び出し元: frontend/src/pages/company-detail/CompanyDetailPage.tsx:255・frontend/src/pages/company-detail/CompanyContactsTab.tsx:241・frontend/src/pages/leads/LeadsPage.tsx:550（63-used-by.txt）。

## 3. 生ラジオに当たる CSS（07-css-radio-rules.txt）

- frontend/src/components.css:19-30 `.form-group input[type="radio"]`（詳細度 0,2,1）: width 100%・padding・border・radius・font-size・color・background・box-sizing。:32-38 の :focus 版。R3・R4 だけが .form-group の中。
- frontend/src/pages-layout.css:340-347 `.color-swatch input[type="radio"]`（0,2,1）: position absolute・inset 0・width/height 100%・opacity 0・cursor pointer。R3・R4 の欄は見えない（色の四角が見える部分）。
- frontend/src/pages-layout.css:304-339 `.color-swatch` 系。:33x の `.color-swatch-legacy::after` に content "現在" の直書き日本語あり（ADR-027 違反・本便の対象外）。
- R1・R2・R5〜R7 に当たる radio 向けの規則は見つからない（08-css-classes-grep.txt）。モーダル配下に別規則があるかは未確認→前後実測で確かめる。

## 4. トークン

- --size-checkbox 16px・--size-checkbox-sm 14px（frontend/src/tokens.css:226-227）。radio 用のトークンは無い。
- `--spacing-*` は frontend/src の CSS に定義が 0 件（git grep '--spacing-[0-9]+:' の結果 0）。RegisterPage.tsx は 22 か所で使っている。R1・R2 の gap・marginTop は計算上「無効」になっている可能性→前後実測で値を取る。

## 5. 既存の金型（10〜20）

- frontend/src/components/Checkbox.tsx（label 型。label・size sm/md/lg・error・description、className・id を受ける。DOM は label.comp-checkbox > input.comp-checkbox__input + span.comp-checkbox__label）と Checkbox.css（83 行）。test は無い。
- frontend/src/components/CheckboxControl.tsx（単独型。input 1 つ、type 固定、className・style・type・role・size を受けない、size md/sm・indeterminate・dataColor）と CheckboxControl.css（4 行。--size-checkbox・accent-color var(--accent)）。test・stories あり。
- 登録先: docs/CC_UI_GOVERNANCE.md:25 の禁止表、docs/specs/design-system/design.md、Storybook（*.stories.tsx）。components/ に index ファイルは無い。

## 6. 自動チェック

- scripts/check-ui-governance.js は pages/ の .tsx だけを見る（:37）。種別は select / input / tab / checkbox の 4 つ。radio は数えない。

## 7. 前後実測の手本

- docs/handoff/design-system-recon/evidence-20260910/ay4c2b-measure.cjs・ay4c2b-render.tsx・ay4c2b-compare.py（41〜43）。前は origin/main の vite build CSS、後は作業ツリーの build CSS。Playwright で 390/1280 × ライト/ダーク × 状態。結果は想定内と想定外に分ける。
