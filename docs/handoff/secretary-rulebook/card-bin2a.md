# 実装カード 便2a: 秘書の容器 2 つが「決まり」を受け取り、指示文の後ろに入れる（画面は変わらない）

- 設計: [design.md](design.md) §3（容器への頼み・AI に渡す文の組み立て・大きさ）・§11「上限いっぱいでも届く」「組み立てが 2 つで同じ」・§12 便2a。ADR: `docs/adr/ADR-1077-secretary-rulebook.md`（Proposed のまま）。基準値: [baseline.md](baseline.md)。
- 状態: 手順書の案（Opus 作成・2026-11-13）。**PO の実装承認はまだ無い。** 承認があるまで実装役に渡さない。
- ブランチ: `release/secretary-rulebook-bin2a`（実装役が origin/main から作る）。PR は作らない（Opus が作る）。危険 PR ではない（`migrations/`・`deploy.yml`・本番 `scripts/` を触らない）。
- 行番号は origin/main fce60d9f5（2026-11-13）で読んだもの。
- 便2a では backend・画面・指示文（prompt.txt）・答えの形（schema.json）を変えない。backend はまだ `rules` を送らないので、本番の秘書の動きは変わらない（`rules` が無い頼みは今と 1 文字も違わない文を AI に渡す）。

## 読んだ節（設計パートナーの照合）

- docs/handoff/design-partner-card-ops/guards/00-common.md: コマンドは作業場所の `cd` から始める・1 手順 1 コマンド・置き換えの印を残さない（ファイル名・行・中身をすべて実名で書いた）・報告に無い出力を成功と扱わない（commit と push は `git log` と push の生出力で確かめる）。○
- docs/handoff/design-partner-card-ops/guards/03-file.md: 新しいファイルは中身を丸ごと書く・既存ファイルの直しは 1 か所ずつ（「前」と「後」を逐語で書いた。「前」は origin/main fce60d9f5 で実測）。○
- docs/handoff/design-partner-card-ops/guards/10-executor.md: 迷ったら補わずに停止して報告する（分かれ道に書いた）。○
- docs/handoff/design-partner-card-ops/guards/11-lint.md: `scripts/card-lint.sh` を発行前に流す（Opus）。○

## 受領確認

着手前に、報告の 1 行目へ「受領確認: card-bin2a を読んだ」と書く。

## この便で決めたこと（Opus・設計からの細部）

| 決めたこと | 理由・出典 |
|---|---|
| 便2 を 2a（容器・容器の CI・測る台本）と 2b（backend の口・決まりの出し入れの窓口・試しの仕組み・使いみち）に分ける | 2a だけで「決まり 20 件を付けたときの速さと当たり」を本番の容器で測れる（便0 と同じ道）。測った数を見てから 2b を作れる。2a は backend が `rules` を送らない限り動きが変わらない |
| 容器は `rules` の形（文字の配列・空の文字が無い）だけを見る。件数・長さ・制御文字は見ない | 件数 20・150 字・15,000 バイト・制御文字は backend が守る（design.md §3「大きさ」）。決まりを 2 か所に書かない |
| `rules` が無い頼みは今のまま通す（[] と同じ） | 2a を本番に出した後も、backend（2b 前）は `rules` を送らない。送らない頼みが 400 になると秘書が止まる |
| `rules` が [] のとき AI に渡す文は今と 1 文字も違わない | 便0 の基準値（baseline.md）と同じ条件を保つ。試験で今の式と同じ文字列かを確かめる |
| 組み立ては新しい 1 ファイル `secretary-agent/compose.mjs` に置き、codex は `SECRETARY_ASSET_DIR` から動的 import で読む | design.md §3「AI に渡す文の組み立て」。prompt.txt と同じ配り方（`secretary-codex/server.mjs:11-13`・`:21`） |
| 容器の node の試験を PR ごとに流す workflow を足す（`secretary-agent/**`・`secretary-codex/**` を触った PR だけ） | design.md 維持の仕組み「今は無く便2で足す」・recon.md §4。必須チェックにはしない（paths で走らない PR が止まらないように） |
| `.github/workflows/deploy.yml:738` の注記「4ファイル」は直さない | deploy.yml は危険パス（ADR-135/136）。注記だけのために 2a を危険 PR にしない。次に deploy.yml を触る便で直す（Opus が控えを持つ） |
| 測る台本 `docs/handoff/secretary-rulebook/bin0/run_baseline.py` に `--rules` を足す | 便0 と同じ道・同じ判定で、決まり 20 件の有無だけを変えて比べる |

## やること（この順）

1. 作業場所を公式の台本で作る（card-bin1.md のやること 1 と同じ形）。`<main>` はクラウドが最初に置いた場所。1 つずつ流し、出力を報告に書く。
   - (1a) `cd <main> && git fetch origin main`
   - (1b) `cd <main> && git branch --list release/secretary-rulebook-bin2a`。空であること。空でなければ消さずに BLOCKED:。
   - (1c) `cd <main> && bash scripts/new-worktree.sh release/secretary-rulebook-bin2a`（`--claude` は付けない）。
   - (1d) `cd <main> && git worktree list`。`$HOME/worktrees/salesanchor/release-secretary-rulebook-bin2a` が出ること。以後の `<repo>` はこの絶対パス。
   - (1e) `cd <repo> && ./scripts/dev/executor-preflight.sh`。生出力を報告に貼る。クラウドでは [1/3] network と [2/3] gh auth の FAIL は起こるものとして先へ進む。[3/3] と [4/4] が OK でなければ BLOCKED:。
   - (1f) `cd <repo> && git diff --stat fce60d9f5 HEAD -- secretary-agent secretary-codex tests/sandbox/secretary-codex.sh docs/handoff/secretary-rulebook/bin0/run_baseline.py`。空であること（行番号を読んだ後に誰も触っていない）。空でなければ BLOCKED:（差分の生出力を添える）。
2. 新しいファイル `secretary-agent/compose.mjs` を作る。中身は下の「compose.mjs の中身」を 1 文字も変えずに使う。
3. 新しいファイル `secretary-agent/compose.test.mjs` を作る。中身は下の「compose.test.mjs の中身」を 1 文字も変えずに使う。
4. `secretary-agent/server.mjs` を 5 か所直す（下の「agent の直し」）。
5. `secretary-codex/server.mjs` を 5 か所直す（下の「codex の直し」）。
6. `secretary-agent/server.test.mjs` の最後（今は 303 行目で終わる）の後ろに、下の「agent の試験に足す」を足す。ファイルの先頭の import の並び（今は 2〜9 行目）の最後の行 `import { fileURLToPath } from "node:url";` の次の行に `import { compose } from "./compose.mjs";` を 1 行足す。ほかの行は変えない。
7. `secretary-codex/server.test.mjs` の最後（今は 391 行目で終わる）の後ろに、下の「codex の試験に足す」を足す。ファイルの先頭の import の並びの最後の行（`import { fileURLToPath } from "node:url";`）の次の行に `import { compose } from "../secretary-agent/compose.mjs";` を 1 行足す。ほかの行は変えない。
8. 容器の試験を流す: `cd <repo> && node --test secretary-agent/compose.test.mjs secretary-agent/server.test.mjs secretary-codex/server.test.mjs > /tmp/CC報告ファイル/bin2a-node-test.txt 2>&1; echo "exit=$?"`。exit=0 であること。結果ファイルの最後の 12 行（`tail -12`）を報告に貼る。0 でなければ直さずに NEEDS_DECISION:（落ちた試験の題と、そのあたりの 40 行）。
9. 配り方の 4 か所を直す（下の「配り方の直し」）。
10. 試験場の台本 `tests/sandbox/secretary-codex.sh` を 4 か所直す（下の「試験場の台本の直し」）。
11. 新しいファイル `.github/workflows/secretary-containers-test.yml` を作る。中身は下の「workflow の中身」を 1 文字も変えずに使う。
12. 測る台本 `docs/handoff/secretary-rulebook/bin0/run_baseline.py` を 3 か所直す（下の「測る台本の直し」）。直した後に `cd <repo>/backend && PYTHONPATH=. uv run --no-project --with httpx==0.28.1 --with pydantic==2.10.6 python ../docs/handoff/secretary-rulebook/bin0/run_baseline.py --cases app/assistant_regression/cases.json --model x --url http://127.0.0.1:9 --rounds 1 --rules ../docs/handoff/secretary-rulebook/bin2/dummy-rules.json > /tmp/CC報告ファイル/bin2a-baseline-dry.txt 2>&1; echo "exit=$?"` を流し（つながらない宛先なので 1 件 5 秒待ってやり直し、全体で約 2 分かかる）、exit=0 と、結果ファイルの `grep -E '^(group=|rules_count=)'` の生出力を報告に貼る。`rules_count=20` の行があり、4 つの group の行の unmeasured の和が 23（ほかの数は 0）であること。`docs/handoff/secretary-rulebook/bin2/dummy-rules.json` が無ければ BLOCKED:（Opus が手順書と同じ PR で置く）。
13. commit（1 つ）。`git add` は 12 ファイルを名前で指定する: `secretary-agent/compose.mjs`・`secretary-agent/compose.test.mjs`・`secretary-agent/server.mjs`・`secretary-agent/server.test.mjs`・`secretary-agent/Dockerfile`・`secretary-codex/server.mjs`・`secretary-codex/server.test.mjs`・`secretary-codex/Dockerfile`・`secretary-codex/Dockerfile.dockerignore`・`tests/sandbox/secretary-codex.sh`・`.github/workflows/secretary-containers-test.yml`・`docs/handoff/secretary-rulebook/bin0/run_baseline.py`（12 個。数え直して 12 であること）。commit の前に `cd <repo> && git status --short` を報告に貼る（この 12 個だけであること。違えば commit せずに BLOCKED:）。題は `feat(secretary): 容器が会社の決まりを受け取り指示文の後ろに入れる（ADR-1077 便2a）`。末尾に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`。`git log --oneline -1` を報告に貼る。
14. 提出前: `cd <repo> && bash scripts/dev/check-before-submit.sh > /tmp/CC報告ファイル/bin2a-check.txt 2>&1; echo "exit=$?"`。パスと最後の 5 行を報告する。通ったら `cd <repo> && git push origin release/secretary-rulebook-bin2a`。push の生出力を報告に貼る。

## compose.mjs の中身

```js
// ADR-1077 便2a: AI に渡す文の組み立て。secretary-agent と secretary-codex の server.mjs が同じこのファイルを読む（写しを作らない・design.md §3）。
// 決まりの件数・長さ・制御文字は backend が守る（design.md §3「大きさ」）。ここは形だけを見る。

const RULES_HEADING = "この会社の決まり（会社の人が承認したもの。上の決まりと食い違うときは上の決まりを守る）:";

// 決まりが無いときは今までと 1 文字も違わない文を返す（便0 の基準値と同じ条件）。
export function compose(prompt, now, text, rules = []) {
  const head = rules.length === 0 ? prompt : `${prompt}\n\n${RULES_HEADING}\n${rules.map((r) => `- ${r}`).join("\n")}`;
  return `${head}\n\n今の日時: ${now}\n\n利用者の文:\n${text}`;
}

// 頼みの rules を読む。無ければ []、空でない文字の配列ならそのまま、それ以外は null（呼ぶ側が 400 bad_request にする）。
export function readRules(value) {
  if (value === undefined) return [];
  if (!Array.isArray(value)) return null;
  return value.every((r) => typeof r === "string" && r.length > 0) ? value : null;
}
```

## compose.test.mjs の中身

```js
// ADR-1077 便2a: compose.mjs の試験（node --test）。
import { test } from "node:test";
import assert from "node:assert/strict";
import { compose, readRules } from "./compose.mjs";

const P = "指示文の1行目\n指示文の2行目";

test("決まりが無いときは今までの組み立てと 1 文字も違わない", () => {
  const old = `${P}\n\n今の日時: N\n\n利用者の文:\nT`;
  assert.equal(compose(P, "N", "T"), old);
  assert.equal(compose(P, "N", "T", []), old);
});

test("決まりは指示文の後・日時の前に、渡した順で 1 行ずつ入る", () => {
  assert.equal(
    compose(P, "N", "T", ["一つ目", "二つ目"]),
    `${P}\n\nこの会社の決まり（会社の人が承認したもの。上の決まりと食い違うときは上の決まりを守る）:\n- 一つ目\n- 二つ目\n\n今の日時: N\n\n利用者の文:\nT`,
  );
});

test("readRules: 無い→[]・空でない文字の配列→そのまま・それ以外→null", () => {
  assert.deepEqual(readRules(undefined), []);
  assert.deepEqual(readRules([]), []);
  assert.deepEqual(readRules(["a", "b"]), ["a", "b"]);
  for (const bad of [null, "a", 1, {}, [1], ["a", ""], ["a", null], [["a"]]]) {
    assert.equal(readRules(bad), null, JSON.stringify(bad));
  }
});
```

## agent の直し（`secretary-agent/server.mjs`）

1 か所ずつ Edit で直す。「前」が 1 つだけ見つかること。見つからない・2 つ以上なら BLOCKED:。

- (a) 9 行目の後ろに 1 行足す。前: `import { fileURLToPath } from "node:url";` → 後: `import { fileURLToPath } from "node:url";` の次の行に `import { compose, readRules } from "./compose.mjs";`
- (b) 53 行目。前: `function runClaude(text, now, model) {` → 後: `function runClaude(text, now, model, rules) {`
- (c) 121 行目。前: ``    child.stdin.end(`${PROMPT}\n\n今の日時: ${now}\n\n利用者の文:\n${text}`);`` → 後: `    child.stdin.end(compose(PROMPT, now, text, rules));`
- (d) 138〜140 行目。前: `let text, now, model;` と `({ text, now, model } = JSON.parse(raw));` → 後: `let text, now, model, rules;` と `({ text, now, model, rules } = JSON.parse(raw));`（2 行とも。インデントは変えない）
- (e) 147〜149 行目の model の検査（`if (typeof model !== "string" || !MODEL_RE.test(model)) {` から次の `}` まで）の直後、`if (busy) return send(res, 429, { code: "busy" });` の前に、次の 2 行を同じインデント（6 空白）で足す。続けて 154 行目の `await runClaude(text, now, model);` を `await runClaude(text, now, model, rules);` に直す。

```js
      rules = readRules(rules);
      if (rules === null) return send(res, 400, { code: "bad_request" });
```

## codex の直し（`secretary-codex/server.mjs`）

1 か所ずつ Edit で直す。扱いは agent と同じ。

- (a) 9 行目。前: `import { fileURLToPath } from "node:url";` → 後: `import { fileURLToPath, pathToFileURL } from "node:url";`
- (b) 23 行目（`JSON.parse(fs.readFileSync(SCHEMA_PATH, "utf8")); // 起動の時に…`）の次の行に、次の 2 行を足す。

```js
// 頼みの文の組み立ては secretary-agent/compose.mjs を同じファイルとして使う（ADR-1077 便2a。容器では /app に並ぶ。試験では secretary-agent を指す）。
const { compose, readRules } = await import(pathToFileURL(path.join(ASSET_DIR, "compose.mjs")).href);
```

- (c) 126 行目。前: `function runCodex(text, now, model) {` → 後: `function runCodex(text, now, model, rules) {`
- (d) 213 行目。前: ``    child.stdin.end(`${PROMPT}\n\n今の日時: ${now}\n\n利用者の文:\n${text}`);`` → 後: `    child.stdin.end(compose(PROMPT, now, text, rules));`
- (e) 230〜232 行目の `let text, now, model;` と `({ text, now, model } = JSON.parse(raw));` を agent の (d) と同じに直す。239〜241 行目の model の検査の直後、`if (busy) return send(res, 429, { code: "busy" });` の前に agent の (e) と同じ 2 行を足す。246 行目の `await runCodex(text, now, model);` を `await runCodex(text, now, model, rules);` に直す。

（(b) で 3 行増えるので、(c) 以後の実際の行番号は 2 つずつ後ろにずれる。「前」の文字で探す。）

## agent の試験に足す（`secretary-agent/server.test.mjs` の最後）

```js
test("(11) rules: 無いときは今までと同じ文・あるときは指示文の後に入る・形が違えば 400 で claude を呼ばない（ADR-1077 便2a）", async () => {
  const stdinLog = path.join(work, "stdin.log");
  writeFake(`cat > "${stdinLog}"; echo '{"structured_output":{"kind":"unknown","invoice":null,"event":null,"reply":"r"}}'`);
  const { port, child } = await startServer({ CLAUDE_CODE_OAUTH_TOKEN: "dummy" });
  const prompt = fs.readFileSync(path.join(HERE, "prompt.txt"), "utf8");
  try {
    assert.equal((await request(port, "POST", "/intent", { text: "a", now: "n", model: "sonnet" })).status, 200);
    assert.equal(fs.readFileSync(stdinLog, "utf8"), `${prompt}\n\n今の日時: n\n\n利用者の文:\na`);
    const rules = ["決まりA", "決まりB"];
    assert.equal((await request(port, "POST", "/intent", { text: "a", now: "n", model: "sonnet", rules })).status, 200);
    const stdin = fs.readFileSync(stdinLog, "utf8");
    assert.equal(stdin, compose(prompt, "n", "a", rules));
    assert.ok(stdin.includes("\n- 決まりA\n- 決まりB\n\n今の日時: n"));
    fs.rmSync(stdinLog);
    for (const bad of [null, "決まり", [1], [""]]) {
      const r = await request(port, "POST", "/intent", { text: "a", now: "n", model: "sonnet", rules: bad });
      assert.equal(r.status, 400, JSON.stringify(bad));
      assert.deepEqual(r.json, { code: "bad_request" });
    }
    assert.equal(fs.existsSync(stdinLog), false);
  } finally {
    child.kill();
  }
});

test("(12) 上限いっぱい: 絵文字で決まり 20 件×150 字＋文 1000 字の頼みが 16KB に収まり 200 で通る（design.md §3「大きさ」）", async () => {
  writeFake(`cat >/dev/null; echo '{"structured_output":{"kind":"unknown","invoice":null,"event":null,"reply":"r"}}'`);
  const { port, child } = await startServer({ CLAUDE_CODE_OAUTH_TOKEN: "dummy" });
  try {
    const body = {
      text: "😀".repeat(1000),
      now: "2026-11-16T10:00:00+09:00",
      model: "sonnet",
      rules: Array.from({ length: 20 }, () => "😀".repeat(150)),
    };
    const bytes = Buffer.byteLength(JSON.stringify(body));
    assert.ok(bytes > 16000 && bytes < 16384, String(bytes));
    assert.equal((await request(port, "POST", "/intent", body)).status, 200);
  } finally {
    child.kill();
  }
});
```

## codex の試験に足す（`secretary-codex/server.test.mjs` の最後）

```js
test("(15) rules: 無いときは今までと同じ文・あるときは指示文の後に入る・形が違えば 400 で codex を呼ばない（ADR-1077 便2a）", async () => {
  login();
  const prompt = fs.readFileSync(path.join(ASSETS, "prompt.txt"), "utf8");
  writeFake({ events: okEvents() });
  await withServer({}, async ({ port }) => {
    assert.equal((await post(port)).status, 200);
  });
  assert.equal(fs.readFileSync(stdinLog, "utf8"), `${prompt}\n\n今の日時: ${NOW}\n\n利用者の文:\n${TEXT}`);
  const rules = ["決まりA", "決まりB"];
  writeFake({ events: okEvents() });
  await withServer({}, async ({ port }) => {
    assert.equal((await post(port, { text: TEXT, now: NOW, model: "gpt-x", rules })).status, 200);
  });
  const stdin = fs.readFileSync(stdinLog, "utf8");
  assert.equal(stdin, compose(prompt, NOW, TEXT, rules));
  assert.ok(stdin.includes(`\n- 決まりA\n- 決まりB\n\n今の日時: ${NOW}`));
  writeFake({ events: okEvents() });
  await withServer({}, async ({ port }) => {
    for (const bad of [null, "決まり", [1], [""]]) {
      const r = await post(port, { text: TEXT, now: NOW, model: "gpt-x", rules: bad });
      assert.equal(r.status, 400, JSON.stringify(bad));
      assert.deepEqual(r.json, { code: "bad_request" });
    }
  });
  assert.equal(fs.existsSync(argsLog), false);
});

test("(16) 上限いっぱい: 絵文字で決まり 20 件×150 字＋文 1000 字の頼みが 16KB に収まり 200 で通る（design.md §3「大きさ」）", async () => {
  login();
  writeFake({ events: okEvents() });
  const body = {
    text: "😀".repeat(1000),
    now: NOW,
    model: "gpt-x",
    rules: Array.from({ length: 20 }, () => "😀".repeat(150)),
  };
  const bytes = Buffer.byteLength(JSON.stringify(body));
  assert.ok(bytes > 16000 && bytes < 16384, String(bytes));
  await withServer({}, async ({ port }) => {
    assert.equal((await post(port, body)).status, 200);
  });
});
```

## 配り方の直し

1 か所ずつ Edit で直す。

- `secretary-agent/Dockerfile` 6 行目。前: `COPY server.mjs probe.mjs prompt.txt schema.json /app/` → 後: `COPY server.mjs probe.mjs prompt.txt schema.json compose.mjs /app/`
- `secretary-codex/Dockerfile` 3 行目。前: `# 入れる物は secretary-codex/Dockerfile.dockerignore の許す一覧の4つだけ（指示文・答えの形・つながりの試しは secretary-agent と同じファイル）。` → 後: `# 入れる物は secretary-codex/Dockerfile.dockerignore の許す一覧の5つだけ（指示文・答えの形・つながりの試し・頼みの文の組み立ては secretary-agent と同じファイル）。`
- `secretary-codex/Dockerfile` 12 行目。前: `COPY secretary-agent/prompt.txt secretary-agent/schema.json secretary-agent/probe.mjs secretary-codex/server.mjs /app/` → 後: `COPY secretary-agent/prompt.txt secretary-agent/schema.json secretary-agent/probe.mjs secretary-agent/compose.mjs secretary-codex/server.mjs /app/`
- `secretary-codex/Dockerfile.dockerignore` 2 行目。前: `# 全部外し、COPY する4つだけを戻す。BuildKit が secretary-codex/Dockerfile の隣のこのファイルを読む。` → 後: `# 全部外し、COPY する5つだけを戻す。BuildKit が secretary-codex/Dockerfile の隣のこのファイルを読む。`
- `secretary-codex/Dockerfile.dockerignore` 6 行目 `!secretary-agent/probe.mjs` の次の行に `!secretary-agent/compose.mjs` を 1 行足す。

## 試験場の台本の直し（`tests/sandbox/secretary-codex.sh`）

1 か所ずつ Edit で直す。

- 31 行目。前: `node --test secretary-agent/server.test.mjs secretary-codex/server.test.mjs` → 後: `node --test secretary-agent/compose.test.mjs secretary-agent/server.test.mjs secretary-codex/server.test.mjs`
- 33 行目。前の文中の `許す一覧の4つだけ` → 後: `許す一覧の5つだけ`（行のほかの文字は変えない）。
- 39 行目。前: `test "$(wc -l < "$OUT/ctx_files.txt")" -eq 4 || { echo "NG: build の入力が4ファイルでない"; exit 1; }` → 後: `test "$(wc -l < "$OUT/ctx_files.txt")" -eq 5 || { echo "NG: build の入力が5ファイルでない"; exit 1; }`
- 40 行目。前: `for f in ./secretary-agent/prompt.txt ./secretary-agent/schema.json ./secretary-agent/probe.mjs ./secretary-codex/server.mjs; do` → 後: `for f in ./secretary-agent/prompt.txt ./secretary-agent/schema.json ./secretary-agent/probe.mjs ./secretary-agent/compose.mjs ./secretary-codex/server.mjs; do`
- 49 行目。前: `test "$(docker run --rm --entrypoint sh "$IMG" -c 'ls -1 /app | wc -l')" -eq 4 || { echo "NG: /app が4ファイルでない"; exit 1; }` → 後: `test "$(docker run --rm --entrypoint sh "$IMG" -c 'ls -1 /app | wc -l')" -eq 5 || { echo "NG: /app が5ファイルでない"; exit 1; }`

## workflow の中身（`.github/workflows/secretary-containers-test.yml`）

```yaml
name: Secretary containers test

# ADR-1077 便2a: 秘書の容器 2 つ（secretary-agent・secretary-codex）の node の試験を PR ごとに流す（design.md 維持の仕組み）。
# 本物の claude・codex・secrets は使わない（偽のコマンドで試す）。必須チェックにはしない（paths に当たらない PR では走らない）。
on:
  pull_request:
    branches: [main]
    paths:
      - 'secretary-agent/**'
      - 'secretary-codex/**'
      - '.github/workflows/secretary-containers-test.yml'

permissions:
  contents: read

jobs:
  node-test:
    name: secretary containers node test
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09 # v5
        with:
          persist-credentials: false
      - uses: actions/setup-node@a0853c24544627f65ddf259abe73b1d18a591444 # v5
        with:
          node-version: '22'
          package-manager-cache: false
      - run: node --test secretary-agent/compose.test.mjs secretary-agent/server.test.mjs secretary-codex/server.test.mjs
```

（checkout と setup-node の版の印は `.github/workflows/guard-authoring-gate.yml:34-36` と同じ。node は容器と同じ 22（`secretary-agent/Dockerfile:3`）。）

## 測る台本の直し（`docs/handoff/secretary-rulebook/bin0/run_baseline.py`）

1 か所ずつ Edit で直す。

- (a) 2 行目。前: `"""便0: 秘書の今の当たり具合を測る台本（card-bin0.md）。` → 後: `"""便0: 秘書の今の当たり具合を測る台本（card-bin0.md）。便2a で --rules（決まりの JSON の配列）を足した（card-bin2a.md）。`
- (b) `parser.add_argument("--rounds", type=int, default=3)` の次の行に `    parser.add_argument("--rules")` を足す。
- (c) `    if args.rounds < 1:` から `        return 2` までの 3 行の直後に、次を足す（4 空白のインデント）。

```python
    rules: list[str] = []
    if args.rules:
        try:
            with open(args.rules, encoding="utf-8") as f:
                rules = json.load(f)
        except (OSError, ValueError):
            print("rules が読めません", file=sys.stderr)
            return 2
        if not isinstance(rules, list) or not all(isinstance(r, str) and r for r in rules):
            print("rules は空でない文字の配列にする", file=sys.stderr)
            return 2
    print(f"rules_count={len(rules)}", file=sys.stderr)
```

- (d) 前: `                payload = {"text": case["text"], "now": fixed_now, "model": args.model}` → 後: その行のまま、次の行に同じインデントで `                if rules:` と、その次の行に `                    payload["rules"] = rules` を足す（決まりが無いときの頼みは便0 と同じ形のまま）。

## 触らない

- `backend`・`frontend`・`migrations`・`scripts`・`.github/workflows/deploy.yml`（4 ファイルの注記も直さない・上の「決めたこと」）・`.github/workflows/build-images.yml`・`docker-compose*.yml`。
- `secretary-agent/prompt.txt`・`secretary-agent/schema.json`・`secretary-agent/probe.mjs`（指示文と答えの形は便3 で直す・design.md §12）。
- design.md・kgi.md・recon.md・baseline.md・ADR・`docs/handoff/secretary-rulebook/bin2/dummy-rules.json`（Opus が直す・置く）。
- 本番のサーバー（本番での測定は Opus）。

## 想定される分かれ道

- やること 8 で今ある試験（(1)〜(10)・codex の (1)〜(14)）が落ちる → 直さずに NEEDS_DECISION:（今の組み立てを変えてしまった恐れ。落ちた題と 40 行）。
- codex の試験で「top-level await」が使えないという誤り → Node の版（`node --version`）を添えて BLOCKED:（容器も CI も 22 の前提）。
- (12)・(16) の bytes の検査が落ちる（16,000 以下・16,384 以上）→ 数を添えて NEEDS_DECISION:（設計の計算は 16,143 バイト）。
- (12)・(16) が 413 など 200 以外で返る → 容器の上限 `MAX_BODY`（`secretary-agent/server.mjs:14`）は変えずに、返った状態と bytes を添えて NEEDS_DECISION:。
- check-before-submit が落ちる → 直さずに、落ちた検査の名前とログの最後 30 行を添えて NEEDS_DECISION:。
- 「前」の文字が見つからない（誰かが先に直した）→ 補わずに BLOCKED:（その行の今の中身を添える）。

## Opus が合流の前に確かめること（実装役はしない）

- PR の CI で新しい workflow「secretary containers node test」が走り、緑であること。
- 試験場で codex の容器を作り、/app が 5 ファイルで compose.mjs を読めること（`tests/sandbox/secretary-codex.sh` を sandbox-test.yml で流す）。codex の build の失敗は本番反映で警告だけになるため（design.md §3）。
- 合流と本番反映の後: 反映の記録に秘書の容器の警告が無いこと・本番の秘書に 1 回頼んで今まで通り答えること・決まり 20 件を付けた測定（23 件 × 3 回・便0 と同じ道）を流し baseline.md に足すこと。

## 終わりの報告（停止したときも同じ形で報告する）

- DONE: 受領確認の行・preflight の生出力・(1f) の出力・やること 8 と 12 の結果・commit 前の `git status --short`・commit の sha・check-before-submit の結果ファイルのパスと最後の 5 行・push の生出力。
- BLOCKED: 止まった手順・コマンド・生の出力。
- NEEDS_DECISION: 迷った点・選べる形・それぞれの影響。

END OF CARD
