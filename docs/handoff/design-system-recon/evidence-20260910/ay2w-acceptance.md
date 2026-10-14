# AY-2w 受入結果（CommissionPanel の担当者 select を SelectControl へ）

- 基準: f353bb437（origin/main）。設計: docs/handoff/ay2w-commission-select/design.md §6。
- 実測の生出力: /tmp/CC報告ファイル/ssot-ay2w/impl/measure-before/・measure-after/（JSON・スクショ、8条件 = 幅390/1280 × ja/en × ライト/ダーク）。要約 JSON は docs/handoff/design-system-recon/evidence-20260910/ay2w-measure-before.json と ay2w-measure-after.json。
- 実測方法: 一時 spec（frontend/tests-e2e/ay2w-measure.spec.ts、コミットせず /tmp/CC報告ファイル/ssot-ay2w/impl/ay2w-measure.spec.ts へ退避）。Chromium、vite dev（port 5199、E2E 用ダミー Firebase env）、installAuthBypass + mockApi。ログ: pw-before.txt、pw-after.txt（各 8 件 pass）。
- mock: /me/permissions（ALL_PERMISSIONS + orders.update）、/staff/me（locale・theme を条件ごとに設定）、/financials/orders（frontend/src/pages/commissions/CommissionsPage.tsx:120-122）、/orders/101/commissions、/staff（frontend/src/components/CommissionPanel.tsx:89-92）、/commissions/monthly（frontend/src/pages/commissions/CommissionsPage.tsx:77-78）。足りなかった API として GET /conversations?unread_only=true と GET /conversations/stream（frontend/src/components/DesktopShell.tsx:136）を追加（Layout が呼ぶ）。
- fixture: 担当者 user_id=2「山田 太郎」（is_employee）、user_id=3「Bartholomew-Alexander Montgomery」（長い英語名）、user_id=null 1 名。役割は sales/trouble=2、ship=3、order/purchase=null。

## 受入表

| 基準 | 結果 | 数値・根拠 | 生出力 |
|---|---|---|---|
| 製品差分は CommissionPanel.tsx のタグ名2か所・`size="sm"`・import 1行のみ | ○ | 追加 3 行（import 1・`size="sm"` 1・開きタグ置換）と閉じタグ置換のみ。diff 全文は報告に記載 | git-diff-commissionpanel.txt |
| 生 select が CommissionPanel.tsx に 0 件 | ○ | `git grep -n "<select" -- frontend/src/components/CommissionPanel.tsx` が 0 件（exit 1） | （コマンド出力） |
| DOM の属性・選択肢が不変（ja/en） | ○ | 8 条件 × 5 役割で aria-label・data-testid・value・disabled・option(value, 文字列) の差分 0 | compare.txt（"DOM diffs: []"） |
| 意図した見た目の変化を提示 | ○（意図した変化） | 下の computed style 表 | measure-before/・measure-after/ |
| 表の横 overflow が増えない（B1） | ○（判定式どおり）。ただし下記の注記あり | 下の B1 表。document・table とも scrollWidth − clientWidth は前後とも 0 | b1-table.md、compare.txt |
| 試験 | ○ | SharedButtonMigration.test.tsx 単独 21 passed（追加 1 件を含む） | vitest-single.txt |
| 新規トークン・直書き 0 | ○ | check:all exit 0、check:new-tokens exit 0、scripts/check-ui-governance.js exit 0（「新規ハードコードなし」） | q-check-all.txt、q-check-new-tokens.txt、q-ui-governance.txt |
| 品質 | 一部 ×（無関係の timeout）。下記 | tsc 0、lint 0、build 0、build-storybook 0、test:coverage exit 1（無関係 2 件、1 回目と再実行で別のテストが 5000ms timeout。単独再実行は全て pass） | quality-exit.txt、q-test-coverage.txt、q-test-coverage-rerun.txt、q-rerun-unrelated.txt、q-rerun-unrelated2.txt |
| 本番 | 未実施（反映後に Opus が grep・health を確認） | - | - |

## computed style の前後表（先頭の select = 営業。before → after）

| 条件 | width | height | min-height | padding | font-size | border | background-image |
|---|---|---|---|---|---|---|---|
| 1280-en-dark | 243px → 266px | 19px → 30.3906px | 0px → 28px | 0px → 4px 20px 4px 8px | 13.3333px → 13.6px | 1px solid rgb(133, 133, 133) → 1px solid rgb(51, 65, 85) | none → svg(矢印) |
| 1280-en-light | 243px → 266px | 19px → 30.3906px | 0px → 28px | 0px → 4px 20px 4px 8px | 13.3333px → 13.6px | 1px solid rgb(118, 118, 118) → 1px solid rgb(226, 232, 240) | none → svg(矢印) |
| 1280-ja-dark | 243px → 266px | 19px → 30.3906px | 0px → 28px | 0px → 4px 20px 4px 8px | 13.3333px → 13.6px | 1px solid rgb(133, 133, 133) → 1px solid rgb(51, 65, 85) | none → svg(矢印) |
| 1280-ja-light | 243px → 266px | 19px → 30.3906px | 0px → 28px | 0px → 4px 20px 4px 8px | 13.3333px → 13.6px | 1px solid rgb(118, 118, 118) → 1px solid rgb(226, 232, 240) | none → svg(矢印) |
| 390-en-dark | 243px → 266px | 19px → 44px | 0px → 44px | 0px → 4px 20px 4px 8px | 13.3333px → 13.6px | 1px solid rgb(133, 133, 133) → 1px solid rgb(51, 65, 85) | none → svg(矢印) |
| 390-en-light | 243px → 266px | 19px → 44px | 0px → 44px | 0px → 4px 20px 4px 8px | 13.3333px → 13.6px | 1px solid rgb(118, 118, 118) → 1px solid rgb(226, 232, 240) | none → svg(矢印) |
| 390-ja-dark | 243px → 266px | 19px → 44px | 0px → 44px | 0px → 4px 20px 4px 8px | 13.3333px → 13.6px | 1px solid rgb(133, 133, 133) → 1px solid rgb(51, 65, 85) | none → svg(矢印) |
| 390-ja-light | 243px → 266px | 19px → 44px | 0px → 44px | 0px → 4px 20px 4px 8px | 13.3333px → 13.6px | 1px solid rgb(118, 118, 118) → 1px solid rgb(226, 232, 240) | none → svg(矢印) |

- クラス: 変更前 なし → 変更後 `comp-select__control comp-select__control--sm`（全条件）。
- 同じ行の解除ボタン（Button sm）の高さ: 1280px で 28px → 28px、390px で 44px → 44px（前後同値。1280px の select は 30.39px で解除ボタン 28px とは 2.39px 差）。
- 390px では select 高さが 19px → 44px（FormField.css の 767px 以下規則による意図した変化）。

## B1 表（横 overflow、390px・英語を含む全条件）

| 条件 | document の scrollWidth − clientWidth（前 → 後） | commission-table の scrollWidth − clientWidth（前 → 後） | commission-table の scrollWidth（前 → 後） | document の scrollWidth（前 → 後） |
|---|---|---|---|---|
| 1280-en-dark | 0 → 0 | 0 → 0 | 752 → 752 | 1280 → 1280 |
| 1280-en-light | 0 → 0 | 0 → 0 | 752 → 752 | 1280 → 1280 |
| 1280-ja-dark | 0 → 0 | 0 → 0 | 752 → 752 | 1280 → 1280 |
| 1280-ja-light | 0 → 0 | 0 → 0 | 752 → 752 | 1280 → 1280 |
| 390-en-dark | 0 → 0 | 0 → 0 | 605 → 628 | 390 → 390 |
| 390-en-light | 0 → 0 | 0 → 0 | 605 → 628 | 390 → 390 |
| 390-ja-dark | 0 → 0 | 0 → 0 | 504 → 527 | 390 → 390 |
| 390-ja-light | 0 → 0 | 0 → 0 | 504 → 527 | 390 → 390 |

- 注記: 390px で commission-table 自体の幅（scrollWidth=clientWidth）は 605 → 628（英語）、504 → 527（日本語）と 23px 増えた。table は 390px のビューポートより元から広く（前 605 / 後 628 > 390）、document の scrollWidth は 390 のまま。判定式（scrollWidth − clientWidth）は前後とも 0 のため停止条件は成立しない。設計 §6 の文言「scrollWidth/clientWidth 後 ≤ 前」を table の scrollWidth 単独と読む場合は後が大きい。この解釈の判断は Opus に委ねる。モーダル本文の横スクロール有無は未測定。
- B2: select 型エラーなし（tsc exit 0）。children モードで aria-label・data-testid・value・disabled が select 要素に届いた（DOM 差分 0）。
