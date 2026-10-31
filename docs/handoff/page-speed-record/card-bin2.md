カード名: page-speed 便2（測れなかった画面と、止めた通信で秒が膨らむ画面を直す）

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md（全コマンドを cd で始める・出力に上限・sleep しない）、docs/handoff/design-partner-card-ops/guards/04-worktree.md（作業場所は new-worktree.sh・作成後に実在を確かめる）、scripts/agent-hooks/cloud/rules.md（クラウドは push まで）

受領確認: 実行の前に、返事の最初で「カード page-speed 便2 を受領した」と書く。

カード発行前チェック（docs/ai-agents/design-partner.md 5.5）
- 0 照合結果を出す: ○（この表）
- 1 記号を壊さない: ○（パス・コード・記号はすべてバッククォートかコードブロック）
- 2 下書き禁止: ○（PR はクラウドでは作らない。push まで）
- 3 報告の宛先: ○（手順ごとの短い返事で生出力を貼る。最後の返事は 600 字以内）
- 4 1便1目的: ○（速さの記録で測れなかった画面を測れるようにする。今の点検の合否は変えない）
- 5 既存ブランチは起点明示: ○（既存の枝 `release/page-speed-coverage`。このカードを置いた commit が先頭・その前が審査記録の `4e97c7a29`）
- 6 書式は実例で: ○（直す所は置き換え前後をそのまま示す）
- 7 合格基準を出力まで縛る: ○（手順6・7に期待する出力）
- 8 数値と名前を対で: ○
- 9 出力量の上限: ○（tail で絞る）
- 10 報告様式3点: ○（末尾の「報告の形」）
- 11 期待値は実測から: ○（行番号・件数は設計担当が origin/main 20e50ac2f で数えた。置き換え 20 か所は設計担当が写しに当てて全部 1 件一致・tsc-exit=0・route 135・時間上限 46/60 を確かめた）
- 12 停止条件は2段: ○（置き換え前の文が見つからない・型の誤り・見張りで止まる）
- 13 定型4点: ○（下の「守ること」）

あなたは Sales Anchor の実装役（Sonnet）です。このカードだけを実行し、push までします。PR は作りません。最初に `scripts/agent-hooks/cloud/rules.md` を読み、従ってください。

守ること
- sleep しない
- ファイルの編集は Edit ツールで行う。ヒアドキュメント・sed・echo でファイルを書かない
- PR は作らない
- フックや自動判定に止められたら、言い換えて再試行しない。止まった手順番号・最後のコマンド・理由の原文を報告して終える
- カードに無い変更はしない。Edit の置き換え前の文が見つからなければ、変えずに `BLOCKED:` で止まる
- reset・rebase・force・`--no-verify`・`git merge` は使わない
- 本番に向けて点検を動かさない（`--list` だけ）
- 触るのは次の 4 つだけ: `tests/prod-check/settle.ts`・`tests/prod-check/page-speed.spec.ts`・`tests/prod-check/page-speed-targets.ts`・`.github/workflows/prod-ui-check.yml`。`tests/prod-check/prod-ui.spec.ts`・`tests/prod-check/fixtures.ts`・backend・frontend・`docs/`・`.claude-pipeline/` は触らない

目的
設計 `docs/handoff/page-speed-record/design.md` の 5-8 のとおり、(1) 在庫表の「見えなくなっただけの読み込み中の印」を数えない (2) 開くだけで書き込む GET は abort でなく 409 で返し、アプリの送り直しの待ちを秒に入れない (3) 中の画面へ移るだけの 3 画面を「移った先で測れた」にする (4) 番号を拾えなかった理由を 5 つに分け、403 が返った API を表の下に出す (5) 表に「止めた送信」の列を足す (6) 速さの段に `timeout-minutes: 46` を付ける。

手順1 作業場所を作る
  cd "$(git rev-parse --show-toplevel)" && git fetch origin release/page-speed-coverage
  cd "$(git rev-parse --show-toplevel)" && bash scripts/new-worktree.sh release/page-speed-coverage 2>&1
  cd "$HOME/worktrees/salesanchor/release-page-speed-coverage" && git branch --show-current
  cd "$HOME/worktrees/salesanchor/release-page-speed-coverage" && git log --oneline -2
期待する出力: ブランチは `release/page-speed-coverage`。log の先頭が `docs: add page-speed bin2 implementation card`、その次が `4e97c7a29 docs: record cloud review of page-speed coverage design`。違えば `BLOCKED:` で止まる

手順2 `tests/prod-check/settle.ts` を Edit で直す（1 か所）

置き換え前:
```ts
async function visibleLoadingCount(page: Page): Promise<number> {
  try {
    return await page.evaluate(
      (sel) =>
        Array.from(document.querySelectorAll(sel)).filter((el) => el.getClientRects().length > 0).length,
      LOADING_SELECTOR,
    );
```
置き換え後:
```ts
/** 見えている読み込み中の印の数。visibility: hidden で残っているだけの印（在庫表の印など）は数えない（設計 5-8） */
async function visibleLoadingCount(page: Page): Promise<number> {
  try {
    return await page.evaluate(
      (sel) =>
        Array.from(document.querySelectorAll(sel)).filter(
          (el) => el.getClientRects().length > 0 && getComputedStyle(el).visibility === "visible",
        ).length,
      LOADING_SELECTOR,
    );
```

手順3 `tests/prod-check/page-speed-targets.ts` を Edit で直す（4 か所）

3-1 置き換え前:
```ts
export type SpeedTarget =
  | { route: string; kind: "" | "carrier" | "section" }
  | { route: string; kind: "needs-id"; listPage: string; listApi: string };
```
置き換え後:
```ts
export type SpeedTarget =
  | { route: string; kind: "" | "carrier" | "section" }
  | { route: string; kind: "redirect"; to: string }
  | { route: string; kind: "needs-id"; listPage: string; listApi: string };
```
3-2 置き換え前: `  { route: "/crm", kind: "" },`
置き換え後: `  { route: "/crm", kind: "redirect", to: "/crm/leads" },`
3-3 置き換え前: `  { route: "/admin", kind: "" },`
置き換え後: `  { route: "/admin", kind: "redirect", to: "/admin/tenant-profile" },`
3-4 置き換え前: `  { route: "/management-center", kind: "" },`
置き換え後: `  { route: "/management-center", kind: "redirect", to: "/management-center/staff" },`

手順4 `tests/prod-check/page-speed.spec.ts` を Edit で直す（9 か所）

4-1 置き換え前:
```ts
type Status = "測れた" | "時間切れ" | "番号を拾えず" | "別の画面へ移った" | "エラー" | "時間切れで未測定";
type Row = {
  route: string;
  seconds: number | null;
  status: Status;
  api: number;
  forbidden: number;
  serverError: number;
```
置き換え後:
```ts
/** 番号の要る画面で、一覧から番号を拾えなかった理由（設計 5-8） */
type MissReason =
  | "番号を拾えず（一覧が 403）"
  | "番号を拾えず（一覧がほかの失敗）"
  | "番号を拾えず（一覧が空）"
  | "番号を拾えず（一覧の形が違う）"
  | "番号を拾えず（一覧の応答なし）";
type Status = "測れた" | "時間切れ" | MissReason | "別の画面へ移った" | "エラー" | "時間切れで未測定";
type Row = {
  route: string;
  seconds: number | null;
  status: Status;
  api: number;
  forbidden: number;
  serverError: number;
  /** その画面を開くあいだに関所が止めた数 */
  blocked: number;
```

4-2 置き換え前:
```ts
    forbidden: 0,
    serverError: 0,
    slowest: "",
```
置き換え後:
```ts
    forbidden: 0,
    serverError: 0,
    blocked: 0,
    slowest: "",
```

4-3 置き換え前:
```ts
/** 一覧画面を開き、一覧 API の応答の先頭の id を拾う。番号はメモリの中だけで使い、表にも記録にも出さない */
async function pickId(
  page: Page,
  api: ApiTracker,
  target: Extract<SpeedTarget, { kind: "needs-id" }>,
): Promise<string | null> {
  await leaveIfSame(page, api, target.listPage);
  const responseP = page
    .waitForResponse(
      (r) => {
        if (r.request().method() !== "GET" || r.status() !== 200) return false;
```
置き換え後:
```ts
/** 一覧画面を開き、一覧 API の応答の先頭の id を拾う。番号はメモリの中だけで使い、表にも記録にも出さない。拾えなければ理由を返す */
async function pickId(
  page: Page,
  api: ApiTracker,
  target: Extract<SpeedTarget, { kind: "needs-id" }>,
): Promise<{ id: string } | { miss: MissReason }> {
  await leaveIfSame(page, api, target.listPage);
  const responseP = page
    .waitForResponse(
      (r) => {
        if (r.request().method() !== "GET") return false;
```

4-4 置き換え前:
```ts
  await waitSettled(page, api, { capMs: CAP_MS });
  if (!response) return null;
  const body: unknown = await response.json().catch(() => null);
  if (!Array.isArray(body) || body.length === 0) return null;
  const first: unknown = body[0];
  if (typeof first !== "object" || first === null) return null;
  const id = (first as { id?: unknown }).id;
  if (typeof id !== "string" && typeof id !== "number") return null;
  return String(id);
}
```
置き換え後:
```ts
  await waitSettled(page, api, { capMs: CAP_MS });
  if (!response) return { miss: "番号を拾えず（一覧の応答なし）" };
  if (response.status() === 403) return { miss: "番号を拾えず（一覧が 403）" };
  if (response.status() !== 200) return { miss: "番号を拾えず（一覧がほかの失敗）" };
  const body: unknown = await response.json().catch(() => null);
  if (!Array.isArray(body)) return { miss: "番号を拾えず（一覧の形が違う）" };
  if (body.length === 0) return { miss: "番号を拾えず（一覧が空）" };
  const first: unknown = body[0];
  if (typeof first !== "object" || first === null) return { miss: "番号を拾えず（一覧の形が違う）" };
  const id = (first as { id?: unknown }).id;
  if (typeof id !== "string" && typeof id !== "number") return { miss: "番号を拾えず（一覧の形が違う）" };
  return { id: String(id) };
}
```

4-5 置き換え前:
```ts
function render(rows: Row[], blocked: Map<string, number>, auth429: number, startedAt: Date, loggedIn: boolean): string {
```
置き換え後:
```ts
function render(
  rows: Row[],
  blocked: Map<string, number>,
  forbiddenApis: Map<string, number>,
  auth429: number,
  startedAt: Date,
  loggedIn: boolean,
): string {
```

4-6 置き換え前:
```ts
    `| \`${r.route}\` | ${sec(r.seconds)} | ${r.status} | ${r.api} | ${r.forbidden} | ${r.serverError} | ${r.slowest ? `\`${r.slowest}\`` : "—"} | ${sec(r.slowestSeconds)} |`;
```
置き換え後:
```ts
    `| \`${r.route}\` | ${sec(r.seconds)} | ${r.status} | ${r.api} | ${r.forbidden} | ${r.serverError} | ${r.blocked} | ${r.slowest ? `\`${r.slowest}\`` : "—"} | ${sec(r.slowestSeconds)} |`;
```

4-7 置き換え前:
```ts
    "- 最初に開いた画面だけ、部品の読み込みの時間が入る。測るあいだはブラウザの保存（キャッシュ）を使わない",
    "",
  ];
  if (!loggedIn) out.push("**ログインできなかったため、画面は測っていない。**", "");
  out.push(
    "| 画面 | 秒 | 状態 | API の数 | 403 | 5xx | いちばん遅い API | その秒 |",
    "|---|---|---|---|---|---|---|---|",
```
置き換え後:
```ts
    "- 最初に開いた画面だけ、部品の読み込みの時間が入る。測るあいだはブラウザの保存（キャッシュ）を使わない",
    "- 止めた送信 = その画面を開くあいだに、本番を守るために止めた通信の数。止めた通信の本当の時間は秒に入っていない",
    "- `A → B` の行は、A を開くと中の B へ移る画面。B に着くまでの秒",
    "",
  ];
  if (!loggedIn) out.push("**ログインできなかったため、画面は測っていない。**", "");
  out.push(
    "| 画面 | 秒 | 状態 | API の数 | 403 | 5xx | 止めた送信 | いちばん遅い API | その秒 |",
    "|---|---|---|---|---|---|---|---|---|",
```

4-8 置き換え前:
```ts
  for (const [k, n] of [...blocked.entries()].sort()) out.push(`  - \`${k}\`: ${n} 件`);
  out.push(`- ログイン関係の 429: ${auth429} 件`, "");
```
置き換え後:
```ts
  for (const [k, n] of [...blocked.entries()].sort()) out.push(`  - \`${k}\`: ${n} 件`);
  out.push(`- 403 が返った API（応答の数）: ${[...forbiddenApis.values()].reduce((a, b) => a + b, 0)} 件`);
  for (const [k, n] of [...forbiddenApis.entries()].sort()) out.push(`  - \`${k}\`: ${n} 件`);
  out.push(`- ログイン関係の 429: ${auth429} 件`, "");
```

4-9 置き換え前:
```ts
  const blocked = new Map<string, number>();
  let auth429 = 0;
  let loggedIn = false;
```
置き換え後:
```ts
  const blocked = new Map<string, number>();
  const forbiddenApis = new Map<string, number>();
  let blockedTotal = 0;
  let auth429 = 0;
  let loggedIn = false;
```

4-10 置き換え前:
```ts
    const key = `${method} ${pathShape(path)}`;
    blocked.set(key, (blocked.get(key) ?? 0) + 1);
    await route.abort();
  });
```
置き換え後:
```ts
    const key = `${method} ${pathShape(path)}`;
    blocked.set(key, (blocked.get(key) ?? 0) + 1);
    blockedTotal += 1;
    if (writesOnRead) {
      // abort すると、アプリは通信の失敗として 0.5・1・2 秒待って送り直し、その待ちが秒に入る。409 は送り直さない（設計 5-8）
      await route.fulfill({ status: 409, contentType: "application/json", body: "{}" });
      return;
    }
    await route.abort();
  });
```

4-11 置き換え前:
```ts
    const res = await req.response().catch(() => null);
    const t = req.timing();
    bucket.push({ shape: apiShape(req.url()), ms: t.responseEnd >= 0 ? t.responseEnd : 0, status: res ? res.status() : 0 });
  });
```
置き換え後:
```ts
    const res = await req.response().catch(() => null);
    const t = req.timing();
    const shape = apiShape(req.url());
    const status = res ? res.status() : 0;
    if (status === 403) forbiddenApis.set(shape, (forbiddenApis.get(shape) ?? 0) + 1);
    bucket.push({ shape, ms: t.responseEnd >= 0 ? t.responseEnd : 0, status });
  });
```

4-12 置き換え前:
```ts
        let url = target.route;
        if (target.kind === "needs-id") {
          const id = await pickId(page, api, target);
          if (id === null) {
            rows.push(emptyRow(target, "番号を拾えず"));
            continue;
          }
          url = target.route.replace(":id", encodeURIComponent(id));
        }
        await leaveIfSame(page, api, url);
        const bucket: ApiHit[] = [];
        hits = bucket;
        const navStart = Date.now();
        await goInApp(page, url);
        const r = await waitSettled(page, api, { capMs: CAP_MS });
        hits = [];
        const row = emptyRow(target, "測れた");
        row.api = bucket.length;
```
置き換え後:
```ts
        let url = target.route;
        if (target.kind === "needs-id") {
          const picked = await pickId(page, api, target);
          if ("miss" in picked) {
            rows.push(emptyRow(target, picked.miss));
            continue;
          }
          url = target.route.replace(":id", encodeURIComponent(picked.id));
        }
        // 中の画面へ移るだけの道すじは、移った先に着いたかで確かめる
        const expected = target.kind === "redirect" ? target.to : url;
        await leaveIfSame(page, api, url);
        const bucket: ApiHit[] = [];
        hits = bucket;
        const blockedBefore = blockedTotal;
        const navStart = Date.now();
        await goInApp(page, url);
        const r = await waitSettled(page, api, { capMs: CAP_MS });
        hits = [];
        const row = emptyRow(target, "測れた");
        if (target.kind === "redirect") row.route = `${target.route} → ${target.to}`;
        row.blocked = blockedTotal - blockedBefore;
        row.api = bucket.length;
```

4-13 置き換え前:
```ts
        } else if (!landed(page, url)) {
```
置き換え後:
```ts
        } else if (!landed(page, expected)) {
```

4-14 置き換え前:
```ts
    writeFileSync(OUT_FILE, render(rows, blocked, auth429, startedAt, loggedIn), "utf8");
```
置き換え後:
```ts
    writeFileSync(OUT_FILE, render(rows, blocked, forbiddenApis, auth429, startedAt, loggedIn), "utf8");
```

手順5 `.github/workflows/prod-ui-check.yml` を Edit で直す（1 か所）
置き換え前:
```yaml
      - name: 画面の速さを記録（判定なし）
        if: always() && steps.gate.outputs.skip != 'true'
        continue-on-error: true
```
置き換え後:
```yaml
      - name: 画面の速さを記録（判定なし）
        if: always() && steps.gate.outputs.skip != 'true'
        continue-on-error: true
        # 試験の上限 45 分 + 1 分。この段が延びても仕事の上限 60 分の中で終わらせる（設計 5-8）
        timeout-minutes: 46
```

手順6 確かめる（出力をすべて貼る）
  cd "$HOME/worktrees/salesanchor/release-page-speed-coverage" && grep -c 'route: "' tests/prod-check/page-speed-targets.ts
  cd "$HOME/worktrees/salesanchor/release-page-speed-coverage" && grep -n 'kind: "redirect"' tests/prod-check/page-speed-targets.ts
  cd "$HOME/worktrees/salesanchor/release-page-speed-coverage" && grep -c '"番号を拾えず"' tests/prod-check/page-speed.spec.ts
  cd "$HOME/worktrees/salesanchor/release-page-speed-coverage" && grep -n -E 'route.fulfill|route.abort|getComputedStyle' tests/prod-check/page-speed.spec.ts tests/prod-check/settle.ts
  cd "$HOME/worktrees/salesanchor/release-page-speed-coverage" && grep -n -i -E 'select |insert |update |delete |DATABASE_URL' tests/prod-check/page-speed.spec.ts | wc -l
  cd "$HOME/worktrees/salesanchor/release-page-speed-coverage" && python3 -c "import yaml; d=yaml.safe_load(open('.github/workflows/prod-ui-check.yml')); s=d['jobs']['check']['steps'][-1]; print(s['name'], s.get('timeout-minutes'), d['jobs']['check']['timeout-minutes'])"
  cd "$HOME/worktrees/salesanchor/release-page-speed-coverage" && git status --short
期待する出力: route は 135。redirect は 3 行（/crm・/admin・/management-center）。`"番号を拾えず"` だけの文字は 0。fulfill 1 行・abort 1 行・getComputedStyle 1 行（settle.ts）。SQL の grep は 0。python の行は `画面の速さを記録（判定なし） 46 60`。`git status --short` は ` M` が 4 行（settle.ts・page-speed.spec.ts・page-speed-targets.ts・prod-ui-check.yml）だけ。違えば `NEEDS_DECISION:` で止まる

手順7 型と一覧を確かめる（本番には向けない）
  cd "$HOME/worktrees/salesanchor/release-page-speed-coverage/frontend" && npm ci > /tmp/npmci.log 2>&1 && echo npmci-ok
  cd "$HOME/worktrees/salesanchor/release-page-speed-coverage" && NODE_PATH="$HOME/worktrees/salesanchor/release-page-speed-coverage/frontend/node_modules" ./frontend/node_modules/.bin/playwright test --config tests/prod-check/playwright.config.ts --list --reporter=list 2>&1 | tail -3
  cd "$HOME/worktrees/salesanchor/release-page-speed-coverage" && NODE_PATH="$HOME/worktrees/salesanchor/release-page-speed-coverage/frontend/node_modules" ./frontend/node_modules/.bin/playwright test --config tests/prod-check/page-speed.config.ts --list --reporter=list 2>&1 | tail -3
  cd "$HOME/worktrees/salesanchor/release-page-speed-coverage" && NODE_PATH="$HOME/worktrees/salesanchor/release-page-speed-coverage/frontend/node_modules" ./frontend/node_modules/.bin/tsc --noEmit --strict --skipLibCheck --target es2022 --module esnext --moduleResolution bundler --types node tests/prod-check/settle.ts tests/prod-check/page-speed.spec.ts tests/prod-check/page-speed.config.ts tests/prod-check/page-speed-targets.ts tests/prod-check/prod-ui.spec.ts tests/prod-check/login.ts tests/prod-check/fixtures.ts tests/prod-check/playwright.config.ts 2>&1 | tail -20; echo "tsc-exit=${PIPESTATUS[0]}"
  cd "$HOME/worktrees/salesanchor/release-page-speed-coverage" && git status --short
期待する出力: npmci-ok。今の点検は `Total: 8 tests in 1 file`。速さは `Total: 1 test in 1 file`。`tsc-exit=0`（`tests/prod-check/` の中の型の誤りなら全文を貼って `BLOCKED:` で止まる。`@playwright/test` や node の型が見つからないという誤りだけなら記録して続ける）。`git status --short` は手順6と同じ 4 行だけ

手順8 commit と push
  cd "$HOME/worktrees/salesanchor/release-page-speed-coverage" && git add tests/prod-check/settle.ts tests/prod-check/page-speed.spec.ts tests/prod-check/page-speed-targets.ts .github/workflows/prod-ui-check.yml
  cd "$HOME/worktrees/salesanchor/release-page-speed-coverage" && git commit -m "fix: measure inventory, redirects and commission pages correctly in page speed record" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
  cd "$HOME/worktrees/salesanchor/release-page-speed-coverage" && git push origin release/page-speed-coverage 2>&1
  cd "$HOME/worktrees/salesanchor/release-page-speed-coverage" && git rev-parse HEAD
  cd "$HOME/worktrees/salesanchor/release-page-speed-coverage" && git ls-remote origin refs/heads/release/page-speed-coverage
期待する出力: rev-parse と ls-remote の SHA が一致する。push が止められたら原文を貼って停止する

報告の形（最後の返事に全部書く）
- 1 行目: 「本報告はカード page-speed 便2 の実行結果である」
- 結果: `DONE` / `BLOCKED:` / `NEEDS_DECISION:` のどれか
- 各手順が終わるたびに、その手順の生出力を 1 回の返事（800 字以内）で貼る。最後の返事は 600 字以内
- push した commit の 40 桁の SHA
- 停止したときは: 停止した手順番号／最後に実行したコマンド／停止した理由の原文
- 最後の行: 「カード page-speed 便2 ここまで」

END OF CARD
