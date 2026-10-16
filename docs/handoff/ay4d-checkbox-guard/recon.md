# AY-4d recon: 生チェック欄の見張りを UI governance gate に足す

- 作成: 2026-10-16 Opus / 基点 origin/main 6b316f7f7863bd9e9729bbd942b8822489ea5e01（AY-4c-2b #4350 マージ後）
- 調査は Sonnet。生出力は /tmp/CC報告ファイル/ssot-checkbox/ay4d/（01〜11、20-、30-、31-）

## 既存 ADR 検索

- `git grep -n -i "ui-governance\|check-ui-governance" docs/adr/` は ADR-144 のみ当たる。docs/adr/FEATURE-INDEX.md は governance・ADR-144・金型で 0 件。
- docs/adr/ADR-144-ui-component-governance.md:41-50 「2. CI ゲート」: 対象は PR の変更ファイル中 `frontend/src/pages/**/*.tsx`、除外は stories・design-system・design-preview、BASE と HEAD の種別ごと件数を比べ、増えたら赤。例外口は ui-allow（理由と番号の両方）。
- docs/adr/ADR-144-ui-component-governance.md:108 に「2026-09-10 改訂案: 画面統一完了後の全件検査」（:110 状態 Proposed）。本文に「既存Accepted本文の運用はCI切替まで維持」とある。今回は Accepted 本文の仕組みに種別を1つ足すだけで、改訂案の全件検査への切替はしない。

## 現在地

- scripts/check-ui-governance.js:36 対象は `frontend/src/pages/`。:88-90 で stories・design-system・design-preview を除く。
- scripts/check-ui-governance.js:153-163 生 select、:174-232 生 input（:213-218 で type が text・search・省略だけを数える。checkbox・radio は数えない）、:243-279 自作タブ。
- scripts/check-ui-governance.js:285-291 `countAll` は select・input・tab の3種。:326-342 種別ごとに BASE と HEAD を比べ、増えたら違反。:386-398 試験用の export。
- scripts/tests/test-ui-governance.js:14-19 で検出関数を require。今は 22 件で全部通る（/tmp/CC報告ファイル/ssot-checkbox/ay4d/09-test-run.txt）。checkbox の試験は無い。
- .github/workflows/ui-governance-gate.yml:17 ジョブ名 `UI governance gate`。:33 で試験、:39 で関所を実行。:6 のコメントは「非必須」と書いている。
- ルールセット「main branch protection」（id 15777895）の必須チェックに `UI governance gate` が入っている（/tmp/CC報告ファイル/ssot-checkbox/ay4d/31-ruleset-detail.json）。つまり :6 のコメントは古い。関所が赤なら main へマージできない。
- 生チェック欄の今の数（07-checkbox-type.txt）: frontend/src の `type="checkbox"` は3件で、すべて金型本体（components/Checkbox.tsx:50、components/CheckboxControl.tsx:41、components/Toggle.tsx:30）。pages/ は 0 件。`type={'checkbox'}`・`type: "checkbox"` の形は 0 件。pages/inbox/InboxConversationRows.tsx:83 に `role="checkbox"`（input ではない）。
- 参考: 生 radio は pages/ に4件（register/RegisterPage.tsx:458・:468、roles/RolesPage.tsx:471・:487）。今回の対象外。
- tsx の数（Opus 実測）: pages/ 210、features/ 57、components/ 166。関所は pages/ しか見ないので features/ に書いた生チェック欄は止まらない。
- frontend/src/company-forms.css:100 と :135 のコメントは「この focus 規則は .form-row 内の checkbox のフォーカス表示を保つために残す」。規則は :102-106 `.form-grid > .form-row input:focus` と :137-142 `.modal-content .form-row input:focus, .modal-content-wide .form-row input:focus`（20-css-95-145.txt）。
- form-row 内の部品（20-formrow-blocks.txt）: 金型 Checkbox 5件（ContactChannelForm.tsx:226、ContactsPage.tsx:333、CompanyDiscordTab.tsx:43、CompanyContactsTab.tsx:205、CompanyAddressModal.tsx:147）、TextFieldControl 49・TextField 13（中で input を描く）。生の input は 0 件。規則はいまも金型の Checkbox と文字入力欄の input に当たる。
- components/Checkbox.css:52-56 は `:focus-visible` だけ。company-forms.css の規則は `:focus` なので、form-row 内の Checkbox はマウスで押したときも枠が出ている可能性がある（未実測）。規則を消すと見た目が変わり得る。

## 未確認

- 規則 :102 の `.form-grid >` 直下に実際に当たる数（DOM 構造は見ていない）。
- 文字入力欄の focus で company-forms.css と FormField.css のどちらが勝つか。
