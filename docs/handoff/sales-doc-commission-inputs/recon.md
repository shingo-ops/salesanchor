# recon: 請求書詳細と報酬ページの入力欄6件の標準化（AY-2o）

調査全文: /tmp/CC報告ファイル/ssot-ay2o/recon-b.md（origin/main 0aef04b30 時点。実装時の基準は 37194570b。行番号は変更前のもの）。

## 現在地（変更前）
- A1 frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx:241 `<input readOnly value={invoice.paypal_approval_url} style={{ flex: 1, padding, borderRadius, border, fontSize }} />`。PayPal の顧客支払い URL の読み取り専用表示。親は frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx:240（flex・gap space-2・alignItems center）、兄弟は :242 ButtonLink size="md"（h36）。表示条件は :232 付近（paypal_approval_url が真かつ status≠paid）。
- A2 frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx:290-291 `<input style={{ width: "100%", padding, borderRadius, border }} value={voidReason} onChange placeholder={t("invoices.voidReasonPlaceholder")} />`。無効化理由の入力。試験 frontend/src/components/CommerceNavigationButtonMigration.test.tsx:98-102 が placeholder で参照。
- B1/B2 frontend/src/pages/commissions/CommissionsPage.tsx:141,153、B3/B4 frontend/src/pages/commission-settings/CommissionSettingsPage.tsx:277,289。`<label>年:<input type="number" ... style={{ width: "var(--input-width-year)", marginLeft: "var(--space-2)" }} data-testid="..."/></label>`（月は --input-width-month）。testid は commissions-year/-month、monthly-year/-month（試験・e2e の参照0）。
- 6件に当たる CSS 規則は0（祖先に .form-group 等なし）。変更前の実測: A は Arial＋inline（h33）、B はブラウザ既定（padding 0・2px inset・角0・Arial 13.33px・h19）。
- トークン: frontend/src/tokens.css:429（--input-width-year 90px）、:433（--input-width-month 60px）。
- 同じ画面の金型: frontend/src/pages/commission-settings/CommissionSettingsPage.tsx:208（SelectControl）・:221（TextFieldControl type=number）はどちらも md（h39.6）。frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx:210 の date も金型 md。
- import: frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx:19 と frontend/src/pages/commission-settings/CommissionSettingsPage.tsx:18 は TextFieldControl を import 済み。frontend/src/pages/commissions/CommissionsPage.tsx は未 import（:16-22 に他の components の import）。
- 金型: frontend/src/components/TextField.tsx:41-54（TextFieldControl）、frontend/src/components/FormField.css:47-62（standard md: padding space-2 space-3・font-size font-base・line-height 1.5）。
- 検出の穴: scripts/check-ui-governance.js:213-218（isDetectableInput）は type=number の生 input を検出しない。
- 月の欄 60px は md だと内容幅 34px（左右余白 12px×2＋枠 2px）。値「12」が切れないかは実装前に未測定だった（after で実測）。

## ADR 検索結果
- ADR-144（UIガバナンス）: 生 input の新規追加禁止。今回は生 input を金型へ置き換える側。docs/CC_UI_GOVERNANCE.md。
- ADR-067（デザイントークン強制）: 新トークンなし。残す inline style は flex・width・marginLeft（配置）のみ。
- ADR-027（i18n）: placeholder・label の t() キーは変えない。
- ADR-1003（GO の委任）: GO は Claude Opus が発行。
