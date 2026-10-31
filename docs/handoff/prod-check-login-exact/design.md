<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# Phase 3 設計 — 本番の点検のログインボタンの探し方を「ちょうどログイン」にする

**対象ADR**: ADR-1051  
**recon**: docs/handoff/prod-check-login-exact/recon.md  
**日付**: 2026-10-31  
**担当**: 設計担当（Claude Opus）。実装はクラウドの Sonnet

---

## 目的

ログイン画面に「顔・指紋でログイン」のボタンが増えた。そのため、本番につなぐ試験がログインのボタンを 1 つに決められず止まっている（recon.md）。探し方を「名前がちょうど『ログイン』のボタン」に直し、毎朝の点検と速さの記録を元どおり動かす。

## 外部・過去事例の参照と我々への応用

- 該当なし：試験の部品の探し方を 1 か所ずつ直すだけで、外部の事例で決める判断がない。直し方は Playwright 自身のエラー文の提案と、同じファイルのパスワード欄の書き方（`tests/prod-check/login.ts:38`）に合わせる。

## 実装カード（変更前 → 変更後。この 5 行だけ。ほかの行・ファイルは触らない）

| # | ファイル:行 | 変更前 | 変更後 |
|---|---|---|---|
| 1 | `tests/prod-check/login.ts:39` | `await page.getByRole("button", { name: "ログイン" }).click();` | `await page.getByRole("button", { name: "ログイン", exact: true }).click();` |
| 2 | `tests/prod-check/prod-ui.spec.ts:30` | `await expect(page.getByRole("button", { name: "ログイン" })).toBeVisible();` | `await expect(page.getByRole("button", { name: "ログイン", exact: true })).toBeVisible();` |
| 3 | `tests/prod-check/prod-ui.spec.ts:119` | `await page.getByRole("button", { name: "ログイン" }).click();` | `await page.getByRole("button", { name: "ログイン", exact: true }).click();` |
| 4 | `tests/qa-smoke/scene-01.spec.ts:45` | `await page.getByRole("button", { name: "ログイン" }).click();` | `await page.getByRole("button", { name: "ログイン", exact: true }).click();` |
| 5 | `tests/qa-smoke/utils/real-backend.ts:33` | `await page.getByRole("button", { name: "ログイン" }).click();` | `await page.getByRole("button", { name: "ログイン", exact: true }).click();` |

- 触らない範囲: frontend/、backend/、.github/、tests/prod-check と tests/qa-smoke の上の 5 行以外。字下げは変えない。
- 想定分岐: 上の「変更前」の文字と行が一致しなければ、直さずに止めて BLOCKED: で報告する。

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 変わったのは上の 5 行だけ | `git diff origin/main...HEAD` の - と + がそれぞれ 5 行 |
| 本番につなぐ試験に、`exact` の無いログインボタンの探し方が残っていない | `git grep -n 'name: "ログイン" })' -- tests/prod-check tests/qa-smoke` が 0 件 |
| マージ後の毎朝の点検が S1〜S8 とも合格する | マージ後に prod-ui-check を手で 1 回動かし、「本番の画面点検を実行」が success |
| 同じ回の速さの記録でログインでき、表が出る | 同じ回の要約に「画面の速さ」の表と「記録係の精度の試し」の行が出る |

## 技術 How・KPI

- KPI: 毎朝の点検（prod-ui-check）の結果が success に戻る（1 回）。
- 技術選択: `exact: true`（理由: 同じファイルで既に使っている書き方。ボタンの文字を変える直しは画面側の変更になり、範囲が広がる）。

## 弊害・トレードオフ

- ログインボタンの文字が「ログイン」から変わると、試験が見つけられず止まる → 対策: それは画面が変わったという正しい知らせとして扱う（今と同じ）。

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | 上の 5 行を直して push | クラウドの Sonnet |
| 2 | マージ前の審査 | 審査役（Claude Opus） |
| 3 | マージ・prod-ui-check を手で 1 回 | 設計担当（Claude Opus） |

## 継続

### 維持の仕組み
守り手: `.github/workflows/prod-ui-check.yml`（毎朝 07:00 の点検。ログイン画面に似た名前のボタンが増えると、この点検が落ちて知らせる）

- 次フェーズへの引き継ぎ: 合格したら、画面の速さの基準取り（docs/handoff/line-like-speed/stage0-card.md §5 の A5〜A10）へ戻る。
