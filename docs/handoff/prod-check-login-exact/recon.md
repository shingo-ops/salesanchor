<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# recon — 本番の点検のログインボタンの探し方を「ちょうどログイン」にする

**仕事名**: prod-check-login-exact  
**日付**: 2026-10-31  
**対象ADR**: ADR-1051  
**担当**: 設計担当（Claude Opus）

---

## 起きたこと（観測事実）

- 2026-10-31 14:26 UTC に main（5af9d20c5）で prod-ui-check を手で動かした（run 41210164023）。結果は failure。
  - 「本番の画面点検を実行」の S1〜S8 が全部 ✘（retry 込み 16 件）。
  - 「画面の速さを記録」は、精度の試しが ✓（2.0s）、本体が ✘（7.8s）。
- エラーの文（どれも同じ）: `strict mode violation: getByRole('button', { name: 'ログイン' }) resolved to 2 elements`。
  - 1 つ目は submit の「ログイン」ボタン。
  - 2 つ目は「顔・指紋でログイン」ボタン。
  - Playwright のエラー文は、1 つ目を `getByRole('button', { name: 'ログイン', exact: true })` と書けば当たると示している。
- 同じ workflow の前回 2026-10-31 04:33 UTC（main 55be483a6）は success。
- そのあいだに main へ入ったログイン画面の変更: #4939（release/passkey-b5）、#4944、#4947（git log --first-parent origin/main で確認）。
  - 「顔・指紋でログイン」の文字は commit 102b93574「feat: passkey sign-in, register, list and delete (ADR-1013 b5)」で入った（git log -S で確認）。
- 見本のデータで動く画面の試験（e2e.yml）は、2026-10-31 14:21 UTC の回も success。止まるのは本番につなぐ試験だけ。

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `tests/prod-check/login.ts:39` | `await page.getByRole("button", { name: "ログイン" }).click();`（毎朝の点検 S3〜S6 と速さの記録が使うログイン） |
| `tests/prod-check/prod-ui.spec.ts:30` | `await expect(page.getByRole("button", { name: "ログイン" })).toBeVisible();`（S1） |
| `tests/prod-check/prod-ui.spec.ts:119` | `await page.getByRole("button", { name: "ログイン" }).click();`（S7 間違ったパスワード） |
| `tests/qa-smoke/scene-01.spec.ts:45` | `await page.getByRole("button", { name: "ログイン" }).click();`（手で動かす動作確認） |
| `tests/qa-smoke/utils/real-backend.ts:33` | `await page.getByRole("button", { name: "ログイン" }).click();`（手で動かす動作確認のログイン） |
| `tests/prod-check/login.ts:38` | 同じファイルでパスワード欄は既に `{ exact: true }` で探している（直し方の手本） |

- 本番につなぐ試験で同じ探し方をしている所は、上の 5 か所だけ（`git grep -n 'name: "ログイン"' origin/main -- tests/`）。
- frontend/tests-e2e の同じ探し方（login.spec.ts:34・:84・:100、scene1-dashboard.spec.ts:346）は、見本のデータで動き success なので触らない。

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | `exact: true` で submit のボタンだけに当たるか | Playwright 自身のエラー文が `exact: true` の形で 1 つ目を示した（run 41210164023 の記録） | ✅ 解消済み |
| 2 | Playwright の公式文書での `exact` の説明 | Context7 は月の上限で使えなかった（「Monthly quota exceeded」）。同じリポジトリでパスワード欄に同じ書き方が動いている（login.ts:38、毎朝 success） | ✅ 解消済み（実物で確認） |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

- このままだと 2026-11-01 07:00 JST の毎朝の点検が落ち、間違いの知らせが Discord に届く。
