# recon: パスワード欄の目の印を見本（ChatGPT）に合わせる

区分: B-2（既にある CSS と配置だけを変える。`frontend/src/` の中だけ。ADR-1015）

## 依頼（PO 原文・2026-10-30）
- 「入力内容を確認してください。と出てログインできない、[Image] 目の位置と大きさも見本と違うから修正できる？」
- 見本をどれにするかの問いに「1」（ChatGPT に合わせる）

## 既存 ADR の検索
- `git grep -il "PasswordField" docs/adr/` → 0 件。目の印の寸法を決めた ADR は無い
- 関係する ADR: ADR-067（デザイントークン強制）、ADR-144（UI 部品の金型）、ADR-1013（自社ログイン）
- 目の印の正本の設計: docs/handoff/login-round-inputs/design.md §6.2（:125-137）。寸法の根拠は「ボタンの幅ぶん空ける」だけで、見本の実測は無い（同 §7.4 の ChatGPT 実測に目の印の項目は無い）

## 変更前（origin/main で確認）
- /Users/tanizawashingo/salesanchor/frontend/src/components/PasswordField.tsx:45 `<ToggleIcon size={ICON.md} aria-hidden="true" />`（16px）
- /Users/tanizawashingo/salesanchor/frontend/src/components/PasswordField.css:10 `padding-right: calc(var(--size-icon-btn-sm) + var(--space-2));`
- /Users/tanizawashingo/salesanchor/frontend/src/components/PasswordField.css:17 `right: var(--space-1);`（4px）
- /Users/tanizawashingo/salesanchor/frontend/src/components/PasswordField.css:23 狭い画面 `padding-right: calc(var(--size-icon-btn-lg) + var(--space-2));`
- トークン: /Users/tanizawashingo/salesanchor/frontend/src/tokens.css:74 `--space-1: 4px`・:75 `--space-2: 8px`・:77 `--space-4: 16px`・:83 `--space-12: 48px`・:229 `--icon-md: 16px`・:230 `--icon-base: 20px`
- 使っている画面: /Users/tanizawashingo/salesanchor/frontend/src/pages/login/LoginPage.tsx:116、/Users/tanizawashingo/salesanchor/frontend/src/pages/reset-password/ResetPasswordPage.tsx:67・:77 の3か所だけ

## 見本の実測（2026-10-30 22:37 JST・Playwright・ChatGPT のパスワード入力画面。練習用アドレスで到達しログインはしていない）
| 項目 | 1280px | 390px |
|---|---|---|
| 目の印の大きさ | 20x20 | 20x20 |
| 欄の外側右端 → 目の印の右端 | 21px | 21px |
| 縦のずれ（欄の中央から） | 0 | 0 |
| 入力文字の右端 → 目の印の左端 | 8px | - |

## 変更前のアプリの実測（同日・本番 /login）
- 目の印 16px、欄の外側右端 → 目の印の右端 約10px（PC: ボタン28px が右4px、印は中央）
