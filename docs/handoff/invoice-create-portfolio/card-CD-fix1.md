# card-CD-fix1: CI の赤を直す（便C/D・PR #5542）

作成: Opus（Planner）2026-11-16。実装承認は便C/Dの承認の範囲内（同じ PR の CI を通すための直し）。

## 0. 起きたこと（事実）
- CI pytest-run-internal: `FAILED tests/test_error_detail_guard.py::test_detail_guard_no_increase - 増えた: app/routers/invoices.py 基準 25 → 今 27`（run 43775473573）。他は 9715 passed。
- 増えた 2 件は便C で足した行（ADR-1071 W1 違反＝detail に日本語の文）:
  - `backend/app/routers/invoices.py:304`（draft-context の担当者の会社違い）`detail="指定された担当者は指定会社に所属していません"`
  - `backend/app/routers/invoices.py:723`（発行の UPDATE が 0 行のとき）`detail="draft状態の請求書のみ発行できます"`
- guard-authoring/evaluation が error: origin/main がこのブランチの祖先でない（`git merge-base --is-ancestor origin/main HEAD` → 1）。

## 1. 手順
1. `git fetch origin` の後、`git merge --no-edit origin/main`（merge commit。rebase・force push 禁止）。衝突したら BLOCKED: merge conflict <ファイル名> で止まる。
2. `backend/app/routers/invoices.py` を直す（上の 2 行だけ。既存の同じ文の行 534・693 は触らない＝基準 25 のまま）:
   - 変更前 `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="指定された担当者は指定会社に所属していません")`（draft-context の中の 1 行目）
     変更後 `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="contact_company_mismatch")`
   - 変更前 `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="draft状態の請求書のみ発行できます")`（`row = result.mappings().first()` / `if not row:` の直後の方。`old` の状態を見る前の方は触らない）
     変更後 `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invoice_not_draft")`
   - 行番号は merge で動くので、文と前後の行で場所を特定する。各文の残り件数は `grep -c` で 1 になること。
3. `frontend/src/lib/apiErrorReason.ts` の `API_ERROR_REASON_KEYS` の `payment_method` の行の後に 2 行:
   `  contact_company_mismatch: "apiError.contactCompanyMismatch",`
   `  invoice_not_draft: "apiError.invoiceNotDraft",`
4. `frontend/src/lib/apiErrorReason.test.ts` の `toBe(24)` → `toBe(26)`。
5. `backend/tests/test_api_error_reason_sync.py` の一覧の `"payment_method",` の後に `"contact_company_mismatch",` と `"invoice_not_draft",`。
6. `frontend/src/locales/ja.json` の apiError の `"paymentMethod"` の行の後（行末にカンマを足す）:
   `"contactCompanyMismatch": "選んだ担当者はこの会社の人ではないため、請求書の材料を出せません。担当者を選び直してください。",`
   `"invoiceNotDraft": "この請求書は下書きではなくなったため、発行できません。画面を読み直してください。"`
   `frontend/src/locales/en.json` も同じ場所に:
   `"contactCompanyMismatch": "The selected contact does not belong to this company, so the invoice details cannot be loaded. Choose the contact again.",`
   `"invoiceNotDraft": "This invoice is no longer a draft, so it cannot be issued. Reload the page."`
7. 試験の中で上の 2 つの日本語の文を期待している所があれば `grep -rn "所属していません\|のみ発行できます" backend/tests frontend/src` で探し、便C で足した試験（test_invoices_create_flow.py など）の中だけ新しいコードに合わせる。既存の試験は触らない。

## 2. 確かめ
- `cd backend && python -m pytest tests/test_error_detail_guard.py tests/test_api_error_reason_sync.py tests/test_invoices.py tests/test_invoices_create_flow.py tests/test_invoice_totals.py -q --no-cov` が全部通る。
- `cd frontend && npx vitest run --config vitest.unit.config.ts --project unit src/lib/apiErrorReason.test.ts` が通る。`npm run check:all` exit 0。ja/en のキー差 0。
- `git merge-base --is-ancestor origin/main HEAD; echo $?` が 0。

## 3. commit と push
- 1 commit: `fix(invoices): return reason codes instead of Japanese text for two new invoice errors (invoice-create-portfolio bins C/D fix1)`。merge commit とは別。
- `git push -u origin release/invoice-create-portfolio-bin-cd`（--no-verify・force 禁止）。

## 4. 報告
1 行目 `RECEIVED invoice-create-portfolio-CD-fix1 HEAD=<40桁>`、各手順の ○×、最後の行 DONE か BLOCKED: <理由>。

## 触らない範囲
上に書いたファイル以外。既存の日本語 detail の行（基準に入っている 25 件）。migrations/・deploy.yml・scripts/。
