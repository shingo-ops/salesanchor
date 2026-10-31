<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# Phase 3 設計 — 本番の点検のブラウザで、ログイン直後の顔・指紋の登録案内を出さない

**対象ADR**: ADR-1051, ADR-1013  
**recon**: docs/handoff/prod-check-no-passkey-prompt/recon.md  
**日付**: 2026-11-01  
**担当**: 設計担当（Claude Opus）。実装はクラウドの Sonnet

---

## 目的

ログインした直後に「顔・指紋でログインを登録しますか」の案内が出るようになった（ADR-1013）。点検用の人はまだ登録していないので、毎回この案内で止まり、本番の点検と速さの記録が進めない（recon.md）。点検のブラウザだけ「顔・指紋が使えないブラウザ」として扱い、案内を出さずに今までどおりダッシュボードへ進める。

## 外部・過去事例の参照と我々への応用

- 該当なし：試験の中のブラウザの扱いを 1 か所ずつ決めるだけで、外部の事例で決める判断がない。判定の式は部品（@simplewebauthn/browser 14.0.0）の実物を読んで確かめた（recon.md）。

## 代わりの案と選んだ理由

| 案 | 中身 | 採否 |
|---|---|---|
| A | 案内が出たら「あとで」を押す | 採らない。押すたびに本番の表に 1 行増え、3 回で案内が出なくなる（auth.py:762・:777）。回によって流れが変わり、点検が毎回同じにならない |
| B | 点検用の人に顔・指紋を登録する | 採らない。試験のブラウザで本物の登録はできない。本番のデータも変わる |
| C | 点検のブラウザで顔・指紋の機能を見えなくする | **採る**。本番に何も書かない。毎回同じ流れになる。直すのはログインの手順の 2 ファイルだけ |

- C の弊害: 点検は「ログイン直後の案内」を通らない。案内そのものの確かめは ADR-1013 の受け入れ（PO の実機ログイン）で行い、今も同じ。ログイン画面の「顔・指紋でログイン」ボタンも、login() を通る試験では出なくなる。S1（ログイン画面が開く）は login() を通らないので、今のまま本物の画面を見る。

## 実装カード（この 2 か所に 4 行ずつ足すだけ。ほかの行・ファイルは触らない）

### 1. `tests/prod-check/login.ts:35-36`

変更前:
```ts
export async function login(page: Page, email: string, password: string): Promise<void> {
  await page.goto("/login");
```

変更後:
```ts
export async function login(page: Page, email: string, password: string): Promise<void> {
  // 点検のブラウザでは顔・指紋（パスキー）を使えない扱いにし、ログイン直後の登録案内を出さない（本番に記録を残さない・ADR-1013）
  await page.addInitScript(() => {
    Object.defineProperty(globalThis, "PublicKeyCredential", { value: undefined, configurable: true });
  });
  await page.goto("/login");
```

### 2. `tests/qa-smoke/utils/real-backend.ts:27-29`

変更前:
```ts
export async function login(page: Page, role: QaRole): Promise<void> {
  const cred = QA_USERS[role];
  await page.goto("/login", { waitUntil: "domcontentloaded" });
```

変更後:
```ts
export async function login(page: Page, role: QaRole): Promise<void> {
  const cred = QA_USERS[role];
  // 点検のブラウザでは顔・指紋（パスキー）を使えない扱いにし、ログイン直後の登録案内を出さない（本番に記録を残さない・ADR-1013）
  await page.addInitScript(() => {
    Object.defineProperty(globalThis, "PublicKeyCredential", { value: undefined, configurable: true });
  });
  await page.goto("/login", { waitUntil: "domcontentloaded" });
```

- 触らない範囲: frontend/、backend/、.github/、上の 2 か所以外。字下げは 2 つの空白。
- 想定分岐: 「変更前」の文字と行が一致しなければ、直さずに止めて BLOCKED: で報告する。

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 変わったのは上の 2 か所だけ | `git diff origin/main...HEAD -- tests/` が 8 行の追加・0 行の削除 |
| 読み込みの誤りがない | 実装役の手元で `cd frontend && npm ci` の後、リポジトリの根で `NODE_PATH=$PWD/frontend/node_modules ./frontend/node_modules/.bin/playwright test --list --config tests/prod-check/playwright.config.ts` と `--config tests/qa-smoke/playwright.config.ts` が、どちらも試験の一覧を出して誤り 0 |
| マージ後の毎朝の点検が S1〜S8 とも合格する | マージ後に prod-ui-check を手で 1 回動かし、「本番の画面点検を実行」が success |
| 同じ回の速さの記録でログインでき、表が出る | 同じ回の要約に「画面の速さ」の表と「記録係の精度の試し」の行が出る |
| 本番に案内の「あとで」の記録が増えない | 直し方 C は「あとで」を押さない（コードに skip の呼び出しが無いことを差分で確認） |

## 技術 How・KPI

- KPI: 毎朝の点検（prod-ui-check）の結果が success に戻る（1 回）。
- 技術選択: `page.addInitScript` で `PublicKeyCredential` を undefined にする（理由: 部品の判定式がこの 1 つだけを見る（recon.md）。同じ点検で `addInitScript` を既に使っている（`tests/prod-check/page-speed.spec.ts:441`））。

## 弊害・トレードオフ

- 点検がログイン直後の案内を通らない → 案内の確かめは ADR-1013 の受け入れ側で行う（今と同じ）。
- 画面側で顔・指紋の判定の仕方が変わると、また案内で止まる → それは画面が変わったという正しい知らせとして扱う。

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | 上の 2 か所を直して push | クラウドの Sonnet |
| 2 | マージ前の審査 | 審査役（Claude Opus） |
| 3 | マージ・prod-ui-check を手で 1 回 | 設計担当（Claude Opus） |

## 継続

### 維持の仕組み
守り手: `.github/workflows/prod-ui-check.yml`（毎朝 07:00 の点検。ログインの流れが変わると、この点検が落ちて知らせる）

- 次フェーズへの引き継ぎ: 合格したら、画面の速さの基準取り（docs/handoff/line-like-speed/stage0-card.md §5 の A5〜A10）へ戻る。
