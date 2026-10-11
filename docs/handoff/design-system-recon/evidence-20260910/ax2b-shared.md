# AX-2b 共有規則の確認（取り除くのは textarea 側の選択子だけ）

方法: ax2b-visual.cjs の変換（postcss）が各規則の選択子リストから textarea 側だけを外す。変換前後の規則を下に列挙し、さらに同じ祖先の input を before/after の CSS で実測比較した（ax2b-input-check.cjs）。

## components.css

- L19 `.form-group input, .form-group textarea`
  - before の宣言: width:100%;padding:var(--space-2) var(--space-3);border:1px solid var(--border);border-radius:var(--radius-sm);font-size:var(--font-base);color:var(--text-primary);background:var(--bg-surface);box-siz
  - 変換: 選択子リストから textarea 側だけ外す。残る選択子: `.form-group input`
- L31 `.form-group input:focus, .form-group textarea:focus`
  - before の宣言: outline:none;border-color:var(--accent);box-shadow:var(--focus-ring-shadow)
  - 変換: 選択子リストから textarea 側だけ外す。残る選択子: `.form-group input:focus`
- L39 `.form-group textarea`
  - before の宣言: min-height:var(--textarea-min-h);resize:vertical
  - 変換: 規則ごと削除（textarea 専用）

## company-forms.css

- L100 `.form-grid > .form-row input:not([type="checkbox"]):not([type="radio"]), .form-grid > .form-row textarea`
  - before の宣言: padding:var(--space-2) var(--space-3);border:1px solid var(--border-strong);border-radius:var(--radius-md);font-size:var(--font-base);background:var(--bg-surface);color:var(--text-primary);width:100%;
  - 変換: 選択子リストから textarea 側だけ外す。残る選択子: `.form-grid > .form-row input:not([type="checkbox"]):not([type="radio"])`
- L113 `.form-grid > .form-row textarea`
  - before の宣言: min-height:var(--textarea-min-h);resize:vertical
  - 変換: 規則ごと削除（textarea 専用）
- L119 `.form-grid > .form-row input:focus, .form-grid > .form-row textarea:focus`
  - before の宣言: outline:none;border-color:var(--accent);box-shadow:var(--focus-ring-shadow)
  - 変換: 選択子リストから textarea 側だけ外す。残る選択子: `.form-grid > .form-row input:focus`
- L154 `.modal-content .form-row input:not([type="checkbox"]):not([type="radio"]), .modal-content .form-row textarea, .modal-content-wide .form-row input:not([type="checkbox"]):not([type="radio"]), .modal-content-wide .form-row textarea`
  - before の宣言: padding:var(--space-2) var(--space-3);border:1px solid var(--border-strong);border-radius:var(--radius-md);font-size:var(--font-base);background:var(--bg-surface);color:var(--text-primary);width:100%;
  - 変換: 選択子リストから textarea 側だけ外す。残る選択子: `.modal-content .form-row input:not([type="checkbox"]):not([type="radio"]), .modal-content-wide .form-row input:not([type="checkbox"]):not([type="radio"])`
- L169 `.modal-content .form-row textarea, .modal-content-wide .form-row textarea`
  - before の宣言: min-height:var(--textarea-min-h);resize:vertical
  - 変換: 規則ごと削除（textarea 専用）
- L177 `.modal-content .form-row input:focus, .modal-content .form-row textarea:focus, .modal-content-wide .form-row input:focus, .modal-content-wide .form-row textarea:focus`
  - before の宣言: outline:none;border-color:var(--accent);box-shadow:var(--focus-ring-shadow)
  - 変換: 選択子リストから textarea 側だけ外す。残る選択子: `.modal-content .form-row input:focus, .modal-content-wide .form-row input:focus`
- L254 `.product-edit-form .form-group input:not([type="checkbox"]):not([type="radio"]), .product-edit-form .form-group textarea`
  - before の宣言: border:1px solid var(--border-strong)
  - 変換: 選択子リストから textarea 側だけ外す。残る選択子: `.product-edit-form .form-group input:not([type="checkbox"]):not([type="radio"])`

## features/tcg-analysis-review/supplier-detail-view.css

- L244 `.pmd-field input, .pmd-field textarea`
  - before の宣言: border:1px solid var(--border);border-radius:var(--radius-md);background:var(--bg-surface);padding:var(--space-2);font:inherit;width:100%;box-sizing:border-box
  - 変換: 選択子リストから textarea 側だけ外す。残る選択子: `.pmd-field input`
- L255 `.pmd-field textarea`
  - before の宣言: min-height:var(--pmd-textarea-min-h);resize:vertical
  - 変換: 宣言変更（resize を落とし min-height だけ残す）

## pages/inbox/InboxPage.css

- L633 `.inbox-textarea`
  - before の宣言: flex:1;min-width:0
  - 変換: 選択子リストから textarea 側だけ外す。残る選択子: `.inbox-textarea`
- L1517 `.outbound-translation-edit`
  - before の宣言: width:100%;padding:var(--space-3);resize:vertical;border:1px solid var(--border);border-radius:var(--radius-sm);background:var(--bg-input);color:var(--text);font-size:var(--font-sm);line-height:1.5;fo
  - 変換: 規則ごと削除（textarea 専用）
- L1523 `.outbound-translation-edit:focus`
  - before の宣言: outline:none;border-color:var(--accent)
  - 変換: 規則ごと削除（textarea 専用）

追加規則: company-forms.css に商品編集の独立規則 2 本（ax2b-visual.md §先頭）。

規則の総数（変換対象）: 15

## input 側の無影響の実測

祖先 7 通り（.form-group / .form-grid>.form-row / .modal-content-wide .form-row / .modal-content .form-row / .pmd-field / .product-edit-form .form-group / .outbound-translation-section）× input type 5 種（text, email, number, date, checkbox）× normal・focus = 70 条件で、before と after の computed style（23 項目＋offsetHeight/offsetWidth）の差: **0 条件**。

注: 実装は `.form-group input` 等を一切編集しない（選択子リストから textarea を外すだけ）。`:not([type="checkbox"]):not([type="radio"])` を含む input 側の選択子は文字列として不変。
