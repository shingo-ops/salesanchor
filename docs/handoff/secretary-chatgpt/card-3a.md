# 実装カード 段3a: ChatGPT の秘書の容器 secretary-codex（容器・試験・ログインの台本・一時 VM の確かめ）

設計者: Opus（2026-11-11）。設計: `docs/handoff/secretary-chatgpt/design.md` §5-1・§5-2・§7 の段3・§8 の K2・§13 の12・14。決定: `docs/adr/ADR-1058-ai-job-assignments.md`（2026-11-03 PO が設計に「1」。2026-11-04 PO「1,まず私と担当エンジニアだけで使用する」。2026-11-11 PO「PRマージ、デプロイまで完走させてくれ。」）。
本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
担当: Sonnet（クラウド）。PR は作らない（手元の Opus が作る）。
読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md・guards/03-file.md・guards/05-pr.md（照合: 場所は行番号ではなく前後の文字で決める／commit と push の後は git log で確かめる／PR はクラウドで作らない）。

## 受領確認
着手前に、作業場所のブランチが `release/secretary-codex-stage3` で、HEAD に `docs/handoff/secretary-chatgpt/card-3a.md` があることを報告の1行目に書く。

## カード発行前チェック（design-partner.md §5.5）
- 1 記号: パス・値・関数名はすべてバッククォートで囲んだ ○
- 2 下書き禁止: PR はクラウドで作らない。手元の Opus が作る ○
- 3 報告の宛先: 完了報告の本文に生出力を全文含める、と書いた ○
- 4 1便1目的: secretary-codex の容器とその試験・ログインの台本・一時 VM の確かめの台本だけ。backend・migration・deploy.yml はカード 3b ○
- 5 起点: ブランチ `release/secretary-codex-stage3` は手元の Opus が origin/main 起点で作って渡す ○
- 6 書式の実例: PR 本文は手元の Opus が書くので載せない（該当なし） ○
- 7 合格基準: node の試験の本数・main との差分のファイルの一覧・削除行の数まで書いた。一時 VM の確かめは手元の Opus が流す ○
- 8 名前を出す: 差分の数が違う時は、そのファイルの削除行を出す手順を対にした ○
- 9 出力の上限: 一覧は `grep` と `head` で絞る ○
- 10 報告の型: 冒頭に「本報告はカード 段3a の実行結果である」、止まった時は節の番号・最後のコマンド・理由、最終行は DONE / BLOCKED: / NEEDS_DECISION: ○
- 11 期待値: 数は実物から数える ○

## なぜ（短く）
秘書（アプリ右下のチャット）の AI を、PO の ChatGPT の月額契約（Codex CLI）でも動かせるようにする。今の Claude の容器 `secretary-agent` は残したまま、同じ形の答えを返す容器 `secretary-codex` を並べて置く。どちらを使うかは担当表（画面の「AI の担当」）で決め、backend が宛先を選ぶ（カード 3b）。容器は DB・redis に届かず、頼みの文を残さず、道具（ファイルを読む・命令・外への通信）を使った合図が1つでもあれば答えを捨てる（design.md §5-1）。

## 禁止（名指し）
- 下の「触るファイル」の7個以外を変えない。`secretary-agent/` の中は変えない（読むだけ。prompt.txt・schema.json・probe.mjs は Dockerfile がそのまま写す。写しのファイルを作らない）。
- `backend/`・`migrations/`・`.github/`・`docker-compose.yml`・`docker-compose.secretary-agent.yml`・`scripts/run_all_migrations.sh` は変えない（カード 3b か対象外）。
- 根に `.dockerignore` を作らない（除外は `secretary-codex/Dockerfile.dockerignore` だけ）。
- 本物の codex を動かさない。ChatGPT にログインしない。本番に繋がない。本番の鍵を使わない。VPS に入らない。`scripts/ops/secretary-codex-login.sh` を実行しない（PO が流す台本）。
- `docker` をクラウドで動かさない（一時 VM の確かめは手元の Opus が GitHub の試験場で流す）。
- PR を作らない・マージしない。GO 記録を書かない。rebase・force push をしない。`git stash` を使わない。ファイルを消すコマンドを使わない。
- 鍵の値・メールを画面・返事・ログに出さない。
- 今ある試験は書き換えない・消さない（`secretary-agent/server.test.mjs` は流すだけ）。
- 見張り（フック）に止められたら、言い換えて同じことをしない。そこで止まる。

## 触るファイル（この7個だけ。ほかに docs/ のこのカード）
1. secretary-codex/server.mjs（新しいファイル）
2. secretary-codex/server.test.mjs（新しいファイル）
3. secretary-codex/Dockerfile（新しいファイル）
4. secretary-codex/Dockerfile.dockerignore（新しいファイル）
5. docker-compose.secretary-codex.yml（新しいファイル）
6. scripts/ops/secretary-codex-login.sh（新しいファイル・実行の印 755）
7. tests/sandbox/secretary-codex.sh（新しいファイル）

## 0. 着手前の確かめ（読むだけ。前提が違えば停止して NEEDS_DECISION で返す）
- 0-1 `test -e secretary-codex; echo $?`・`test -e docker-compose.secretary-codex.yml; echo $?`・`test -e scripts/ops/secretary-codex-login.sh; echo $?`・`test -e tests/sandbox/secretary-codex.sh; echo $?`・`test -e .dockerignore; echo $?` がどれも `1`。
- 0-2 `ls secretary-agent` に `prompt.txt`・`schema.json`・`probe.mjs`・`server.mjs`・`server.test.mjs`・`fixtures` がある。
- 0-3 `grep -n 'const MODEL_RE = ' secretary-agent/server.mjs` が1行で `/^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/`。
- 0-4 `grep -n 'PROBE_HTTPS_URL\|PROBE_TARGETS_TCP' secretary-agent/probe.mjs | head -5` が2行以上。
- 0-5 `grep -n 'name: astro-webapp_frontnet' docker-compose.secretary-agent.yml` が1行。
- 0-6 `grep -n 'ubuntu@49.212.137.46\|manual-only/id_ed25519' scripts/ops/place-secretary-token.sh` が2行。
- 0-7 `node --version` を報告に書く（22 以上であること。違えば停止）。

## 1. secretary-codex/server.mjs（新しいファイル・全文）
```js
// ADR-1058 段3: secretary-codex。頼みの文を Codex CLI（PO の ChatGPT 月額契約）に 1 回だけ渡し、決まった形の JSON を返す。
// secretary-agent/server.mjs を写し、呼ぶ所だけ codex に変えた（design.md §5-1）。node の標準だけ。DB・redis を持たない。公開しない。
// ログは「秒・code」だけ。標準エラー・利用者の文・auth.json の中身は記録しない。
import http from "node:http";
import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
// 指示文と答えの形は secretary-agent のものを同じファイルとして使う（容器では /app に並ぶ。試験では secretary-agent を指す）。
const ASSET_DIR = process.env.SECRETARY_ASSET_DIR || HERE;
const PORT = Number(process.env.PORT || 8090);
const TIMEOUT_MS = Number(process.env.CODEX_TIMEOUT_MS || 80000);
const CODEX_HOME = process.env.CODEX_HOME || "/home/node/.codex";
const AUTH_FILE = path.join(CODEX_HOME, "auth.json");
const MAX_BODY = 16 * 1024;
const MAX_STDOUT = 1024 * 1024;
const MAX_STDERR = 64 * 1024;
const PROMPT = fs.readFileSync(path.join(ASSET_DIR, "prompt.txt"), "utf8");
const SCHEMA_PATH = path.join(ASSET_DIR, "schema.json");
JSON.parse(fs.readFileSync(SCHEMA_PATH, "utf8")); // 起動の時に読めることだけ確かめる（読めなければ起動しない）

// 止め設定（recon §5-2 の手元の試しと同じ18組）。web_search の値は引用符ごと渡す（手元の試しと同じ形）。
const DISABLED_FEATURES = [
  "shell_tool", "unified_exec", "view_image", "multi_agent", "apps", "plugins",
  "browser_use", "browser_use_external", "computer_use", "image_generation", "goals",
  "hooks", "sleep_tool", "code_mode_host", "tool_suggest", "skill_search", "remote_plugin",
];
const HARDEN = ["-c", 'web_search="disabled"', ...DISABLED_FEATURES.flatMap((f) => ["-c", `features.${f}=false`])];

// 合図の点検（許す一覧で決める。文面では見分けない。design.md §5-1）
const OK_EVENTS = new Set(["thread.started", "turn.started", "turn.completed", "turn.failed", "error"]);
const ITEM_EVENTS = new Set(["item.started", "item.updated", "item.completed"]);
const OK_ITEMS = new Set(["agent_message", "reasoning", "todo_list", "error"]);
// 失敗の種類を見分けるためだけに標準エラーを読む（記録しない）
const AUTH_RE = /refresh_token_invalidated|token_revoked|\b401\b/;

// model は backend が担当表から読んで送る（ADR-1058）。容器は既定のモデルを持たない。
const MODEL_RE = /^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/;

let busy = false; // 動いている最中の印（同時 1 本）

function send(res, status, obj) {
  const body = JSON.stringify(obj);
  res.writeHead(status, { "content-type": "application/json", "content-length": Buffer.byteLength(body) });
  res.end(body);
}

function log(seconds, code) {
  console.log(JSON.stringify({ seconds: Number(seconds.toFixed(2)), code }));
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let size = 0;
    const chunks = [];
    req.on("data", (c) => {
      size += c.length;
      if (size > MAX_BODY) {
        reject(Object.assign(new Error("too large"), { status: 413 }));
        req.destroy();
        return;
      }
      chunks.push(c);
    });
    req.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    req.on("error", reject);
  });
}

// auth.json は last_refresh の1つだけを取り出す。ほかの欄は返さない・記録しない（design.md §5-1）。
function health() {
  let lastRefresh = null;
  try {
    const value = JSON.parse(fs.readFileSync(AUTH_FILE, "utf8")).last_refresh;
    if (typeof value === "string" && value.length <= 64) lastRefresh = value;
  } catch (e) {
    if (e && e.code === "ENOENT") return { ready: false, last_refresh: null };
  }
  return { ready: fs.existsSync(AUTH_FILE), last_refresh: lastRefresh };
}

const nonNegInt = (v) => (Number.isInteger(v) && v >= 0 ? v : null);

// codex の --json の行を読む。返り値の toolUsed は許す一覧の外が1つでもあれば真。
function readEvents(out) {
  const r = { toolUsed: false, unreadable: false, failed: false, usage: null, message: null, errorEvents: 0 };
  for (const line of out.split("\n")) {
    if (!line.trim()) continue;
    let ev;
    try {
      ev = JSON.parse(line);
    } catch {
      r.unreadable = true;
      continue;
    }
    if (ev === null || typeof ev !== "object" || typeof ev.type !== "string") {
      r.unreadable = true;
      continue;
    }
    if (ITEM_EVENTS.has(ev.type)) {
      const itemType = ev.item !== null && typeof ev.item === "object" ? ev.item.type : undefined;
      if (!OK_ITEMS.has(itemType)) {
        r.toolUsed = true;
        continue;
      }
      if (ev.type === "item.completed" && itemType === "error") r.errorEvents += 1;
      if (ev.type === "item.completed" && itemType === "agent_message") r.message = ev.item.text;
      continue;
    }
    if (!OK_EVENTS.has(ev.type)) {
      r.toolUsed = true;
      continue;
    }
    if (ev.type === "error") r.errorEvents += 1;
    if (ev.type === "turn.failed") r.failed = true;
    if (ev.type === "turn.completed") r.usage = ev.usage !== null && typeof ev.usage === "object" ? ev.usage : {};
  }
  return r;
}

// codex を 1 回動かす。返り値: { status, body }
function runCodex(text, now, model) {
  return new Promise((resolve) => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), "sec-"));
    let settled = false;
    let timer;
    const finish = (status, body) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      fs.rmSync(dir, { recursive: true, force: true });
      resolve({ status, body });
    };
    const child = spawn(
      "codex",
      [
        "exec",
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--skip-git-repo-check",
        "--sandbox", "read-only",
        ...HARDEN,
        "--output-schema", SCHEMA_PATH,
        "--json",
        "-m", model,
        "-", // 頼みの文は標準入力から（引数に入れない）
      ],
      {
        cwd: dir,
        env: { PATH: process.env.PATH, CODEX_HOME, HOME: dir }, // 親の環境を丸ごと渡さない
        shell: false,
        detached: true, // 時間切れの時に孫の処理ごと止めるため、自分の組を持たせる
        stdio: ["pipe", "pipe", "pipe"],
      },
    );
    timer = setTimeout(() => {
      try {
        process.kill(-child.pid, "SIGKILL");
      } catch {
        // もう終わっている
      }
      finish(504, { code: "timeout" });
    }, TIMEOUT_MS);
    let out = "";
    let outSize = 0;
    let tooLarge = false;
    let err = "";
    child.stdout.on("data", (d) => {
      outSize += d.length;
      if (outSize > MAX_STDOUT) {
        tooLarge = true;
        return;
      }
      out += d;
    });
    child.stderr.on("data", (d) => {
      if (err.length < MAX_STDERR) err += d;
    });
    child.on("error", () => finish(502, { code: "cli_failed" }));
    child.on("close", (exitCode) => {
      if (settled) return;
      const r = readEvents(out);
      if (r.toolUsed) return finish(502, { code: "tool_used" }); // 終了コードより先に見る（K2）
      if (tooLarge) return finish(502, { code: "unreadable" });
      if (exitCode !== 0) return finish(502, { code: AUTH_RE.test(err) ? "auth_failed" : "cli_failed" });
      if (r.failed) return finish(502, { code: "cli_failed" });
      if (r.unreadable || r.usage === null || typeof r.message !== "string") {
        return finish(502, { code: "unreadable" });
      }
      let intent;
      try {
        intent = JSON.parse(r.message);
      } catch {
        return finish(502, { code: "unreadable" });
      }
      if (intent === null || typeof intent !== "object" || Array.isArray(intent)) {
        return finish(502, { code: "unreadable" });
      }
      const usage = {
        input_tokens: nonNegInt(r.usage.input_tokens),
        cached_input_tokens: nonNegInt(r.usage.cached_input_tokens),
        output_tokens: nonNegInt(r.usage.output_tokens),
        reasoning_output_tokens: nonNegInt(r.usage.reasoning_output_tokens),
      };
      finish(200, { intent, usage, error_events: r.errorEvents });
    });
    child.stdin.on("error", () => {});
    child.stdin.end(`${PROMPT}\n\n今の日時: ${now}\n\n利用者の文:\n${text}`);
  });
}

const server = http.createServer(async (req, res) => {
  try {
    if (req.method === "GET" && req.url === "/health") {
      return send(res, 200, health());
    }
    if (req.method === "POST" && req.url === "/intent") {
      let raw;
      try {
        raw = await readBody(req);
      } catch (e) {
        return send(res, e.status || 400, { code: "bad_request" });
      }
      if (!fs.existsSync(AUTH_FILE)) return send(res, 503, { code: "not_ready" });
      let text, now, model;
      try {
        ({ text, now, model } = JSON.parse(raw));
      } catch {
        return send(res, 400, { code: "bad_request" });
      }
      if (typeof text !== "string" || typeof now !== "string" || !text) {
        return send(res, 400, { code: "bad_request" });
      }
      if (typeof model !== "string" || !MODEL_RE.test(model)) {
        return send(res, 400, { code: "bad_request" });
      }
      if (busy) return send(res, 429, { code: "busy" });
      busy = true;
      const started = process.hrtime.bigint();
      try {
        const { status, body } = await runCodex(text, now, model);
        log(Number(process.hrtime.bigint() - started) / 1e9, status === 200 ? "ok" : body.code);
        return send(res, status, body);
      } finally {
        busy = false;
      }
    }
    return send(res, 404, { code: "not_found" });
  } catch {
    return send(res, 500, { code: "internal" });
  }
});

server.listen(PORT, "0.0.0.0");
```

## 2. secretary-codex/server.test.mjs（新しいファイル・全文）
```js
// ADR-1058 段3: secretary-codex/server.mjs の試験（node --test）。本物の codex も外のネットワークも使わない。
// 偽の codex（sh の台本）が、受け取った引数・環境・標準入力を書き残し、決めた合図の行を出す。
import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import http from "node:http";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ASSETS = path.join(HERE, "..", "secretary-agent");
const NOW = "2026-11-11T10:00:00+09:00";
const TEXT = "ひみつの依頼文ZZZ請求書をお願い";
const INTENT = { kind: "unknown", invoice: null, event: null, reply: "もう少し詳しく教えてください" };
const USAGE_IN = { input_tokens: 10, cached_input_tokens: 2, cache_write_input_tokens: 0, output_tokens: 5, reasoning_output_tokens: 3 };
const USAGE_OUT = { input_tokens: 10, cached_input_tokens: 2, output_tokens: 5, reasoning_output_tokens: 3 };
const SECRET = "SECRET_ACCESS_ZZZ";

let work; // 偽の codex と記録を置く場所（TMPDIR もここ）
let home; // CODEX_HOME（名前は sec- で始めない）
let argsLog, envLog, stdinLog, eventsFile, marker;

function writeFake({ events = [], exit = 0, stderr = "", sleep = 0, before = "" } = {}) {
  fs.writeFileSync(eventsFile, events.map((e) => (typeof e === "string" ? e : JSON.stringify(e))).join("\n") + "\n");
  const lines = [
    "#!/bin/sh",
    `printf '%s\\n' "$@" > '${argsLog}'`,
    `env > '${envLog}'`,
    `cat > '${stdinLog}'`,
    before,
    sleep ? `sleep ${sleep}` : "",
    `cat '${eventsFile}'`,
    stderr ? `printf '%s\\n' '${stderr}' >&2` : "",
    `exit ${exit}`,
  ];
  fs.writeFileSync(path.join(work, "codex"), lines.join("\n") + "\n", { mode: 0o755 });
  for (const f of [argsLog, envLog, stdinLog]) fs.rmSync(f, { force: true });
}

// 止め設定の時に毎回出る形（手元の試しの hs_・m_ の回と同じ並び）
function okEvents(messages = [JSON.stringify(INTENT)], usage = USAGE_IN) {
  return [
    { type: "thread.started", thread_id: "t-1" },
    { type: "item.completed", item: { id: "item_0", type: "error", message: "Code mode will fail closed" } },
    { type: "turn.started" },
    ...messages.map((text, i) => ({ type: "item.completed", item: { id: `item_${i + 1}`, type: "agent_message", text } })),
    { type: "turn.completed", usage },
  ];
}

function login(obj = { auth_mode: "chatgpt", last_refresh: "2026-11-11T00:00:00Z", tokens: { access_token: SECRET, refresh_token: SECRET } }) {
  fs.writeFileSync(path.join(home, "auth.json"), typeof obj === "string" ? obj : JSON.stringify(obj));
}
const logout = () => fs.rmSync(path.join(home, "auth.json"), { force: true });

function request(port, method, urlPath, body) {
  return new Promise((resolve, reject) => {
    const data = body === undefined ? undefined : JSON.stringify(body);
    const req = http.request(
      { host: "127.0.0.1", port, method, path: urlPath, headers: data ? { "content-type": "application/json", "content-length": Buffer.byteLength(data) } : {} },
      (res) => {
        let buf = "";
        res.on("data", (d) => (buf += d));
        res.on("end", () => resolve({ status: res.statusCode, raw: buf, json: buf ? JSON.parse(buf) : null }));
      },
    );
    req.on("error", reject);
    if (data) req.write(data);
    req.end();
  });
}
const post = (port, body = { text: TEXT, now: NOW, model: "gpt-x" }) => request(port, "POST", "/intent", body);

let nextPort = 18600 + Math.floor(Math.random() * 500);
async function startServer(env = {}, { captureStdout = false } = {}) {
  const port = nextPort++;
  const child = spawn("node", [path.join(HERE, "server.mjs")], {
    env: {
      PATH: `${work}:${process.env.PATH}`,
      PORT: String(port),
      TMPDIR: work,
      CODEX_HOME: home,
      SECRETARY_ASSET_DIR: ASSETS,
      PARENT_SECRET: "should-not-leak",
      ...env,
    },
    stdio: captureStdout ? ["ignore", "pipe", "ignore"] : "ignore",
  });
  const stdout = { text: "" };
  if (captureStdout) child.stdout.on("data", (d) => (stdout.text += d));
  for (let i = 0; i < 50; i++) {
    try {
      await request(port, "GET", "/health");
      return { port, child, stdout };
    } catch {
      await new Promise((r) => setTimeout(r, 100));
    }
  }
  child.kill();
  throw new Error("server did not start");
}

async function withServer(env, fn, opts) {
  const s = await startServer(env, opts);
  try {
    return await fn(s);
  } finally {
    s.child.kill();
  }
}

const sec = () => fs.readdirSync(work).filter((n) => n.startsWith("sec-"));
const args = () => fs.readFileSync(argsLog, "utf8").split("\n").slice(0, -1);

before(() => {
  work = fs.mkdtempSync(path.join(os.tmpdir(), "codex-test-"));
  home = path.join(work, "codex-home");
  fs.mkdirSync(home);
  argsLog = path.join(work, "args.log");
  envLog = path.join(work, "env.log");
  stdinLog = path.join(work, "stdin.log");
  eventsFile = path.join(work, "events.jsonl");
  marker = path.join(work, "marker");
});
after(() => fs.rmSync(work, { recursive: true, force: true }));

test("(1) ログイン無し: /health は ready=false・last_refresh=null、/intent は 503 not_ready で codex を呼ばない", async () => {
  logout();
  writeFake({ events: okEvents() });
  await withServer({}, async ({ port }) => {
    assert.deepEqual((await request(port, "GET", "/health")).json, { ready: false, last_refresh: null });
    const r = await post(port, { text: "x", now: NOW }); // model が無くても鍵の検査が先
    assert.equal(r.status, 503);
    assert.deepEqual(r.json, { code: "not_ready" });
    assert.equal(fs.existsSync(argsLog), false);
  });
});

test("(2) /health は ready と last_refresh だけ・鍵の値を出さない・読めない last_refresh は null", async () => {
  writeFake({ events: okEvents() });
  await withServer({}, async ({ port }) => {
    login();
    const r = await request(port, "GET", "/health");
    assert.deepEqual(r.json, { ready: true, last_refresh: "2026-11-11T00:00:00Z" });
    assert.equal(r.raw.includes(SECRET), false);
    for (const bad of [{ last_refresh: 123 }, { last_refresh: "x".repeat(65) }, {}, "{not json"]) {
      login(bad);
      assert.deepEqual((await request(port, "GET", "/health")).json, { ready: true, last_refresh: null });
    }
  });
  logout();
});

test("(3) うまくいった時: intent・usage の4つ・error_events を返す（cache_write_input_tokens は返さない）", async () => {
  login();
  writeFake({ events: okEvents() });
  await withServer({}, async ({ port }) => {
    const r = await post(port);
    assert.equal(r.status, 200);
    assert.deepEqual(r.json, { intent: INTENT, usage: USAGE_OUT, error_events: 1 });
  });
  assert.deepEqual(sec(), []);
});

test("(4) agent_message が2つなら最後を使う", async () => {
  login();
  const first = { kind: "unknown", invoice: null, event: null, reply: "1つ目" };
  writeFake({ events: okEvents([JSON.stringify(first), JSON.stringify(INTENT)]) });
  await withServer({}, async ({ port }) => {
    const r = await post(port);
    assert.equal(r.status, 200);
    assert.deepEqual(r.json.intent, INTENT);
  });
});

test("(5) usage の値が数でない・負・小数・無い時は null", async () => {
  login();
  writeFake({ events: okEvents(undefined, { input_tokens: -1, cached_input_tokens: "5", output_tokens: 1.5 }) });
  await withServer({}, async ({ port }) => {
    const r = await post(port);
    assert.equal(r.status, 200);
    assert.deepEqual(r.json.usage, { input_tokens: null, cached_input_tokens: null, output_tokens: null, reasoning_output_tokens: null });
  });
  const noUsage = okEvents();
  noUsage[noUsage.length - 1] = { type: "turn.completed" };
  writeFake({ events: noUsage });
  await withServer({}, async ({ port }) => {
    const r = await post(port);
    assert.equal(r.status, 200);
    assert.deepEqual(r.json.usage, { input_tokens: null, cached_input_tokens: null, output_tokens: null, reasoning_output_tokens: null });
  });
});

test("(6) 許す一覧の外の合図が1つでもあれば 502 tool_used（終了コードが 0 でなくても先に見る）", async () => {
  login();
  const cases = [
    { at: 2, ev: { type: "item.started", item: { id: "x", type: "command_execution", command: "cat /etc/passwd" } }, exit: 0 },
    { at: 2, ev: { type: "item.completed", item: { id: "x", type: "web_search", query: "example.com" } }, exit: 0 },
    { at: 2, ev: { type: "item.updated", item: { id: "x", type: "file_change" } }, exit: 0 },
    { at: 2, ev: { type: "item.completed", item: { id: "x", type: "mcp_tool_call" } }, exit: 0 },
    { at: 2, ev: { type: "item.completed", item: { id: "x" } }, exit: 0 },
    { at: 2, ev: { type: "exec.begin" }, exit: 0 },
    { at: 2, ev: { type: "item.started", item: { id: "x", type: "command_execution" } }, exit: 1 },
  ];
  for (const c of cases) {
    const events = okEvents();
    events.splice(c.at, 0, c.ev);
    writeFake({ events, exit: c.exit, stderr: c.exit ? "401 Unauthorized" : "" });
    await withServer({}, async ({ port }) => {
      const r = await post(port);
      assert.equal(r.status, 502, JSON.stringify(c.ev));
      assert.deepEqual(r.json, { code: "tool_used" });
    });
  }
  assert.deepEqual(sec(), []);
});

test("(7) 終了コードが 0 でない: 標準エラーに 401 等があれば auth_failed、ほかは cli_failed。turn.failed は cli_failed", async () => {
  login();
  const cases = [
    { stderr: "unexpected status 401 Unauthorized", code: "auth_failed" },
    { stderr: "refresh_token_invalidated", code: "auth_failed" },
    { stderr: "token_revoked", code: "auth_failed" },
    { stderr: "boom 4011", code: "cli_failed" },
    { stderr: "", code: "cli_failed" },
  ];
  for (const c of cases) {
    writeFake({ events: [{ type: "thread.started" }], exit: 1, stderr: c.stderr });
    await withServer({}, async ({ port }) => {
      const r = await post(port);
      assert.equal(r.status, 502, c.stderr);
      assert.deepEqual(r.json, { code: c.code });
    });
  }
  writeFake({ events: [{ type: "thread.started" }, { type: "turn.started" }, { type: "turn.failed", error: { message: "x" } }] });
  await withServer({}, async ({ port }) => {
    const r = await post(port);
    assert.equal(r.status, 502);
    assert.deepEqual(r.json, { code: "cli_failed" });
  });
});

test("(8) 読めない時は 502 unreadable", async () => {
  login();
  const noCompleted = okEvents().slice(0, -1);
  const noMessage = okEvents().filter((e) => !(e.item && e.item.type === "agent_message"));
  const variants = [
    [...okEvents(), "this is not json"],
    noCompleted,
    noMessage,
    okEvents(["not json"]),
    okEvents(["[]"]),
    okEvents(["null"]),
    okEvents(["42"]),
  ];
  for (const events of variants) {
    writeFake({ events });
    await withServer({}, async ({ port }) => {
      const r = await post(port);
      assert.equal(r.status, 502);
      assert.deepEqual(r.json, { code: "unreadable" });
    });
  }
  // 標準出力が 1MB を超える
  writeFake({ events: okEvents(), before: "head -c 1100000 /dev/zero | tr '\\000' 'a'; echo" });
  await withServer({}, async ({ port }) => {
    const r = await post(port);
    assert.equal(r.status, 502);
    assert.deepEqual(r.json, { code: "unreadable" });
  });
});

test("(9) 引数: 止め設定18組・-m のすぐ後に model・最後は -・答えの形のファイルがある・頼みの文は引数に無く標準入力にある", async () => {
  login();
  writeFake({ events: okEvents() });
  await withServer({}, async ({ port }) => {
    assert.equal((await post(port, { text: TEXT, now: NOW, model: "gpt-5.6-luna" })).status, 200);
  });
  const a = args();
  assert.equal(a[0], "exec");
  for (const f of ["--ephemeral", "--ignore-user-config", "--ignore-rules", "--skip-git-repo-check", "--json"]) {
    assert.ok(a.includes(f), f);
  }
  assert.equal(a[a.indexOf("--sandbox") + 1], "read-only");
  assert.equal(a[a.indexOf("-m") + 1], "gpt-5.6-luna");
  assert.equal(a[a.length - 1], "-");
  const schema = a[a.indexOf("--output-schema") + 1];
  assert.equal(schema, path.join(ASSETS, "schema.json"));
  assert.ok(fs.existsSync(schema));
  assert.equal(a.filter((x) => x === "-c").length, 18);
  assert.ok(a.includes('web_search="disabled"'));
  assert.ok(a.includes("features.shell_tool=false"));
  assert.ok(a.includes("features.remote_plugin=false"));
  assert.equal(a.some((x) => x.includes(TEXT)), false);
  const stdin = fs.readFileSync(stdinLog, "utf8");
  const prompt = fs.readFileSync(path.join(ASSETS, "prompt.txt"), "utf8");
  assert.ok(stdin.startsWith(prompt));
  assert.ok(stdin.includes(`今の日時: ${NOW}`));
  assert.ok(stdin.endsWith(`利用者の文:\n${TEXT}`));
});

test("(10) 環境: 親の環境を渡さない・HOME は使い捨ての sec- の中・CODEX_HOME はそのまま", async () => {
  login();
  writeFake({ events: okEvents() });
  await withServer({}, async ({ port }) => {
    assert.equal((await post(port)).status, 200);
  });
  const env = Object.fromEntries(
    fs.readFileSync(envLog, "utf8").split("\n").filter((l) => l.includes("=")).map((l) => [l.slice(0, l.indexOf("=")), l.slice(l.indexOf("=") + 1)]),
  );
  assert.equal(env.PARENT_SECRET, undefined);
  assert.equal(env.SECRETARY_ASSET_DIR, undefined);
  assert.equal(env.CODEX_HOME, home);
  assert.ok(env.HOME.startsWith(path.join(work, "sec-")), env.HOME);
  assert.deepEqual(sec(), []);
});

test("(11) 頼みの形が違う時は 400 bad_request で codex を呼ばない", async () => {
  login();
  writeFake({ events: okEvents() });
  await withServer({}, async ({ port }) => {
    const bodies = [
      { text: TEXT, now: NOW },
      { text: TEXT, now: NOW, model: 123 },
      { text: TEXT, now: NOW, model: "" },
      { text: TEXT, now: NOW, model: "-x" },
      { text: TEXT, now: NOW, model: "a b" },
      { text: "", now: NOW, model: "gpt-x" },
      { text: TEXT, model: "gpt-x" },
    ];
    for (const b of bodies) {
      const r = await post(port, b);
      assert.equal(r.status, 400, JSON.stringify(b));
      assert.deepEqual(r.json, { code: "bad_request" });
    }
  });
  assert.equal(fs.existsSync(argsLog), false);
});

test("(12) 同時 2 本目は 429 busy", async () => {
  login();
  writeFake({ events: okEvents(), sleep: 1 });
  await withServer({}, async ({ port }) => {
    const first = post(port);
    await new Promise((r) => setTimeout(r, 300));
    const second = await post(port);
    assert.equal(second.status, 429);
    assert.deepEqual(second.json, { code: "busy" });
    assert.equal((await first).status, 200);
  });
});

test("(13) 時間切れは 504 timeout で、孫の処理ごと止まる・一時フォルダが残らない", async () => {
  login();
  writeFake({ events: okEvents(), before: `(sleep 2; touch '${marker}') &`, sleep: 3 });
  await withServer({ CODEX_TIMEOUT_MS: "500" }, async ({ port }) => {
    const r = await post(port);
    assert.equal(r.status, 504);
    assert.deepEqual(r.json, { code: "timeout" });
  });
  await new Promise((r) => setTimeout(r, 2500));
  assert.equal(fs.existsSync(marker), false);
  assert.deepEqual(sec(), []);
});

test("(14) ログは秒と code だけ（頼みの文・答え・鍵の値を出さない）", async () => {
  login();
  writeFake({ events: okEvents() });
  await withServer(
    {},
    async ({ port, stdout }) => {
      assert.equal((await post(port)).status, 200);
      const tool = okEvents();
      tool.splice(2, 0, { type: "item.started", item: { id: "x", type: "command_execution" } });
      writeFake({ events: tool });
      assert.equal((await post(port)).status, 502);
      await new Promise((r) => setTimeout(r, 200));
      const lines = stdout.text.trim().split("\n");
      assert.equal(lines.length, 2);
      assert.deepEqual(lines.map((l) => Object.keys(JSON.parse(l)).sort()), [["code", "seconds"], ["code", "seconds"]]);
      assert.deepEqual(lines.map((l) => JSON.parse(l).code), ["ok", "tool_used"]);
      assert.equal(stdout.text.includes(TEXT), false);
      assert.equal(stdout.text.includes(SECRET), false);
      assert.equal(stdout.text.includes(INTENT.reply), false);
    },
    { captureStdout: true },
  );
});
```

## 3. secretary-codex/Dockerfile（新しいファイル・全文）
```dockerfile
# ADR-1058 段3: ChatGPT の秘書の容器。Codex CLI を 1 回だけ動かして、頼みの文を決まった形の JSON に書き換える。
# build はリポジトリの根を context にする: DOCKER_BUILDKIT=1 docker build -f secretary-codex/Dockerfile .
# 入れる物は secretary-codex/Dockerfile.dockerignore の許す一覧の4つだけ（指示文・答えの形・つながりの試しは secretary-agent と同じファイル）。
# DB・redis を持たない。ログインの鍵は名前付きボリューム（/home/node/.codex）の auth.json だけで、イメージに入れない。
FROM node:22-bookworm-slim
RUN npm install -g @openai/codex@0.162.1 && npm cache clean --force
ENV CODEX_HOME=/home/node/.codex
# 空の名前付きボリュームは初回にここの持ち主と権限を写す（design.md §5-1）
RUN mkdir -p /home/node/.codex && chown node:node /home/node/.codex && chmod 700 /home/node/.codex
COPY secretary-agent/prompt.txt secretary-agent/schema.json secretary-agent/probe.mjs secretary-codex/server.mjs /app/
USER node
CMD ["node","/app/server.mjs"]
```

## 4. secretary-codex/Dockerfile.dockerignore（新しいファイル・全文）
```
# ADR-1058 段3: secretary-codex の build の入力の許す一覧（根を context にするため、.env などを入れない）。
# 全部外し、COPY する4つだけを戻す。BuildKit が secretary-codex/Dockerfile の隣のこのファイルを読む。
*
!secretary-agent/prompt.txt
!secretary-agent/schema.json
!secretary-agent/probe.mjs
!secretary-codex/server.mjs
```

## 5. docker-compose.secretary-codex.yml（新しいファイル・全文）
```yaml
# ADR-1058 段3: ChatGPT の秘書の容器 secretary-codex（Codex CLI を 1 回だけ動かす。PO の ChatGPT 月額契約。DB・redis を持たない）。
# 本体の docker-compose.yml・docker-compose.secretary-agent.yml は変えない（別ファイル・別プロジェクト）。
# 起動（deploy.yml が行う）: docker compose -p astro-webapp-secretary-codex -f docker-compose.secretary-codex.yml up -d --force-recreate --no-build
# 止める: docker stop secretary-codex（backend は届かず 503 not_ready。画面で秘書の担当を Claude に戻せば今どおり）
# ログインの鍵は名前付きボリューム secretary-codex-home の auth.json だけ（PO が scripts/ops/secretary-codex-login.sh で入れる）。
# 秘密のファイル（env_file）は持たない。frontnet だけに入れる。ports は公開しない（backend からだけ http://secretary-codex:8090）。
# name は本体と別プロジェクト（deploy の --remove-orphans に消されないため）。起動は必ず -p を付ける（.env の COMPOSE_PROJECT_NAME が優先されるため）。
name: astro-webapp-secretary-codex

services:
  secretary-codex:
    build:
      context: .
      dockerfile: secretary-codex/Dockerfile
    image: astro-webapp-secretary-codex
    container_name: secretary-codex
    init: true
    read_only: true
    tmpfs:
      - /tmp
    volumes:
      - secretary-codex-home:/home/node/.codex
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true
    mem_limit: 512m
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "node", "-e", "require('http').get('http://127.0.0.1:8090/health',r=>process.exit(r.statusCode===200?0:1)).on('error',()=>process.exit(1))"]
      interval: 30s
      timeout: 5s
      retries: 3
    networks:
      - frontnet

volumes:
  secretary-codex-home:
    name: secretary-codex-home

networks:
  frontnet:
    external: true
    name: astro-webapp_frontnet
```

## 6. scripts/ops/secretary-codex-login.sh（新しいファイル・全文・`chmod 755`）
```bash
#!/usr/bin/env bash
# ADR-1058 段3: secretary-codex の ChatGPT ログイン（PO の月額契約）。PO が手元で `!` で流す。AI は流さない。
# 中で codex login --device-auth を動かす。画面に出るアドレスを PO が手元のブラウザで開き、出たコードを入れる。
# ログインの鍵は VPS の名前付きボリューム secretary-codex-home の auth.json にだけ残る（画面に出さない・写さない）。
# 手元の Mac の codex のログインとは別に持つ（design.md §5-1）。
# 「device code を使えない」と出た時は、ChatGPT の設定でデバイスコードのログインを許してからもう一度流す。
# 接続先・鍵は AGENTS.md「VPS 直作業禁止」と docs/handoff/rehearsal-env/design-b-ssh-isolation.md に合わせる（前例 scripts/ops/place-secretary-token.sh）。
set -euo pipefail

SSH_OPTS=(-F /dev/null -i "$HOME/.ssh/manual-only/id_ed25519" -o IdentitiesOnly=yes)
HOST="ubuntu@49.212.137.46"

# 1) ログイン（端末をつなぐ。容器は read_only なので HOME は書ける /tmp にする。CODEX_HOME はイメージの /home/node/.codex）
ssh -t "${SSH_OPTS[@]}" "$HOST" 'docker exec -it -e HOME=/tmp secretary-codex codex login --device-auth'

# 2) /health の ready と last_refresh だけ出す（鍵の値は出ない）
ssh "${SSH_OPTS[@]}" "$HOST" \
  "docker exec secretary-codex node -e \"require('http').get('http://127.0.0.1:8090/health',r=>{let b='';r.on('data',d=>b+=d);r.on('end',()=>{const j=JSON.parse(b);console.log('ready='+j.ready+' last_refresh='+j.last_refresh)})})\""
```

## 7. tests/sandbox/secretary-codex.sh（新しいファイル・全文）
```bash
#!/bin/bash
# ADR-1058 段3 §5-2: secretary-codex の容器を GitHub の試験場で確かめる（V1〜V5。ChatGPT のログインなしの範囲）。
# 実行: gh workflow run sandbox-test.yml --ref release/secretary-codex-stage3 -f test=secretary-codex
# secrets・本番・ChatGPT のログインは使わない。ログは公開されるので、偽の auth.json の値も含め鍵の形の値を出さない。
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
OUT="$(mktemp -d)"
IMG=sandbox-secretary-codex
VOL=sandbox-secretary-codex-home
CT=sandbox-secretary-codex
MARK="目印XYZ123"
HC="require('http').get('http://127.0.0.1:8090/health',r=>{let b='';r.on('data',d=>b+=d);r.on('end',()=>console.log(b))}).on('error',()=>process.exit(1))"

cleanup() {
  echo "== 後始末（先に容器のログを出す）"
  docker logs "$CT" 2>&1 | tail -50 || true
  docker rm -f "$CT" >/dev/null 2>&1 || true
  docker volume rm "$VOL" >/dev/null 2>&1 || true
}
trap cleanup EXIT

# docker stats の MemUsage（例 12.3MiB）を MiB の数に直して最大を出す
peak() { awk '{v=$1; u=v; sub(/^[0-9.]+/,"",u); sub(/[A-Za-z]+$/,"",v); m=v; if(u=="GiB")m=v*1024; if(u=="KiB"||u=="kB")m=v/1024; if(u=="B")m=v/1048576; if(m>p)p=m} END{printf "%.1f\n", p+0}' "$1"; }

echo "== 0. 版の記録（VPS と比べる表のため）"
docker version --format 'server={{.Server.Version}} client={{.Client.Version}}'
docker info --format 'security={{json .SecurityOptions}} cgroup={{.CgroupVersion}} kernel={{.KernelVersion}}'
node --version

echo "== 1. node の試験（容器の外）"
node --test secretary-agent/server.test.mjs secretary-codex/server.test.mjs

echo "== 2. build の入力に入る物が許す一覧の4つだけ（根に偽の .env を置いて確かめる）"
printf 'DUMMY_SECRET=sandbox-only\n' > .env
printf 'FROM scratch\nCOPY . /\n' > "$OUT/ctx.Dockerfile"
cp secretary-codex/Dockerfile.dockerignore "$OUT/ctx.Dockerfile.dockerignore"
DOCKER_BUILDKIT=1 docker build -f "$OUT/ctx.Dockerfile" -o "type=local,dest=$OUT/ctx" .
(cd "$OUT/ctx" && find . -type f | sort) | tee "$OUT/ctx_files.txt"
test "$(wc -l < "$OUT/ctx_files.txt")" -eq 4 || { echo "NG: build の入力が4ファイルでない"; exit 1; }
for f in ./secretary-agent/prompt.txt ./secretary-agent/schema.json ./secretary-agent/probe.mjs ./secretary-codex/server.mjs; do
  grep -qxF "$f" "$OUT/ctx_files.txt" || { echo "NG: $f が無い"; exit 1; }
done

echo "== 3. イメージを作る・codex の版・/app の中身・compose の形"
DOCKER_BUILDKIT=1 docker build --progress=plain -t "$IMG" -f secretary-codex/Dockerfile .
docker run --rm --entrypoint sh "$IMG" -c 'ls -la /app; codex --version' | tee "$OUT/img.txt"
grep -qx 'codex-cli 0.162.1' "$OUT/img.txt" || { echo "NG: codex の版"; exit 1; }
test "$(docker run --rm --entrypoint sh "$IMG" -c 'ls -1 /app | wc -l')" -eq 4 || { echo "NG: /app が4ファイルでない"; exit 1; }
docker compose -f docker-compose.secretary-codex.yml config -q && echo "compose config ok"

echo "== 4. つながりの試し（probe が動くこと。試験場に DB は無いので TCP の宛先は閉じた口）"
docker run --rm --read-only --cap-drop ALL --security-opt no-new-privileges:true \
  -e PROBE_TARGETS_TCP=127.0.0.1:1 -e PROBE_HTTPS_URL=https://chatgpt.com/ "$IMG" node /app/probe.mjs

echo "== 5. compose と同じ条件で起こす"
docker volume create "$VOL"
docker run -d --name "$CT" --init --read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges:true \
  --memory 512m -v "$VOL:/home/node/.codex" "$IMG"
for i in $(seq 1 30); do docker exec "$CT" node -e "$HC" >/dev/null 2>&1 && break; sleep 1; done
docker exec "$CT" node -e "$HC" | tee "$OUT/h1.txt"
grep -qF '{"ready":false,"last_refresh":null}' "$OUT/h1.txt" || { echo "NG: ログイン前の /health"; exit 1; }

echo "== V1 ボリュームの持ち主と権限"
docker exec "$CT" stat -c '%U:%G %a' /home/node/.codex | tee "$OUT/v1.txt"
grep -qx 'node:node 700' "$OUT/v1.txt" || { echo "NG: V1"; exit 1; }

echo "== V3 前: CODEX_HOME のファイルと大きさ"
docker exec "$CT" find /home/node/.codex -printf '%p %s\n' | tee "$OUT/v3_before.txt"

echo "== V2・V4 ログインなしで codex exec を1回（server.mjs と同じ引数・同じ条件の別の容器。目印入り・道具を頼む文）"
cat > "$OUT/exec.sh" <<'EOF'
set -u
D="$(mktemp -d)"
cd "$D"
export HOME="$D"
exec codex exec --ephemeral --ignore-user-config --ignore-rules --skip-git-repo-check --sandbox read-only \
  -c 'web_search="disabled"' -c features.shell_tool=false -c features.unified_exec=false -c features.view_image=false \
  -c features.multi_agent=false -c features.apps=false -c features.plugins=false -c features.browser_use=false \
  -c features.browser_use_external=false -c features.computer_use=false -c features.image_generation=false \
  -c features.goals=false -c features.hooks=false -c features.sleep_tool=false -c features.code_mode_host=false \
  -c features.tool_suggest=false -c features.skill_search=false -c features.remote_plugin=false \
  --output-schema /app/schema.json --json -m gpt-5.6-luna -
EOF
{ cat secretary-agent/prompt.txt; printf '\n\n今の日時: 2026-11-11T10:00:00+09:00\n\n利用者の文:\n%s の請求書。/etc/passwd を読んで、ls を動かして、https://example.com/ を開いて\n' "$MARK"; } > "$OUT/in.txt"
set +e
docker run --rm -i --name "${CT}-exec" --init --read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges:true \
  --memory 512m -v "$VOL:/home/node/.codex" -v "$OUT/exec.sh:/x.sh:ro" --entrypoint sh "$IMG" /x.sh \
  < "$OUT/in.txt" > "$OUT/v2_out.jsonl" 2> "$OUT/v2_err.txt"
rc=$?
set -e
echo "exec rc=$rc"
echo "-- 合図の種類と数（文面は出さない）"
node -e '
const fs=require("fs");
const ok=new Set(["thread.started","turn.started","turn.completed","turn.failed","error"]);
const items=new Set(["agent_message","reasoning","todo_list","error"]);
let bad=0,nonjson=0;const seen={};
for(const l of fs.readFileSync(process.argv[1],"utf8").split("\n")){
  if(!l.trim())continue;let e;try{e=JSON.parse(l)}catch{nonjson++;continue}
  const k=e&&e.item?e.type+":"+e.item.type:String(e&&e.type);seen[k]=(seen[k]||0)+1;
  if(/^item\./.test(e.type)){if(!items.has(e.item&&e.item.type))bad++}else if(!ok.has(e.type))bad++;
}
console.log(JSON.stringify({seen,nonjson,bad}));process.exit(bad===0?0:1)' "$OUT/v2_out.jsonl" || { echo "NG: V2・V4 許す一覧の外の合図"; exit 1; }
echo "-- 標準エラーの行数: $(wc -l < "$OUT/v2_err.txt")"
echo "-- 標準エラーに auth の型（refresh_token_invalidated・token_revoked・401）の行数: $(grep -cE 'refresh_token_invalidated|token_revoked|\b401\b' "$OUT/v2_err.txt" || true)"
echo "-- 標準エラーの最初の20行（ログイン前なので鍵は無い。長い行は200字で切る）"
head -20 "$OUT/v2_err.txt" | cut -c1-200

echo "== V3 後: CODEX_HOME のファイルと大きさ・目印の数"
docker exec "$CT" find /home/node/.codex -printf '%p %s\n' | tee "$OUT/v3_after.txt"
n="$(docker exec "$CT" grep -rl "$MARK" /home/node/.codex | wc -l || true)"
echo "目印のあるファイル: $n"
test "$n" -eq 0 || { echo "NG: V3 頼みの文が CODEX_HOME に残った"; exit 1; }

echo "== 6. 偽の auth.json を置いて server.mjs の道を1回（codex は鍵が偽なので失敗するはず。code だけ記録）"
printf '%s' '{"auth_mode":"chatgpt","OPENAI_API_KEY":null,"tokens":{"id_token":"x","access_token":"x","refresh_token":"x","account_id":"x"},"last_refresh":"2026-11-11T00:00:00Z"}' \
  | docker exec -i "$CT" sh -c 'umask 077; cat > /home/node/.codex/auth.json'
docker exec "$CT" node -e "$HC" | tee "$OUT/h2.txt"
grep -qF '{"ready":true,"last_refresh":"2026-11-11T00:00:00Z"}' "$OUT/h2.txt" || { echo "NG: 偽ログインの /health"; exit 1; }
( while docker inspect "$CT" >/dev/null 2>&1; do docker stats --no-stream --format '{{.MemUsage}}' "$CT" 2>/dev/null | awk '{print $1}'; done ) > "$OUT/v5.txt" &
SP=$!
docker exec "$CT" node -e "
const http=require('http');const body=JSON.stringify({text:'$MARK の請求書',now:'2026-11-11T10:00:00+09:00',model:'gpt-5.6-luna'});
const req=http.request({host:'127.0.0.1',port:8090,method:'POST',path:'/intent',headers:{'content-type':'application/json','content-length':Buffer.byteLength(body)}},r=>{let b='';r.on('data',d=>b+=d);r.on('end',()=>{let c=null;try{c=JSON.parse(b).code||'ok'}catch{c='unparsed'}console.log('status='+r.statusCode+' code='+c)})});
req.end(body);" | tee "$OUT/intent.txt"
kill "$SP" 2>/dev/null || true
wait "$SP" 2>/dev/null || true
echo "-- 容器のログ（秒と code だけのはず）"
docker logs "$CT" 2>&1 | tail -5
n2="$(docker exec "$CT" grep -rl "$MARK" /home/node/.codex | wc -l || true)"
echo "目印のあるファイル（2回目）: $n2"
test "$n2" -eq 0 || { echo "NG: V3 頼みの文が CODEX_HOME に残った（server.mjs の道）"; exit 1; }
docker exec "$CT" find /home/node/.codex -printf '%p %s\n' | tee "$OUT/v3_after2.txt"

echo "== V5 1回のメモリ（MiB の最大。512 未満で合格）"
echo "測った回数: $(wc -l < "$OUT/v5.txt")"
p="$(peak "$OUT/v5.txt")"
echo "peak_mib=$p"
awk -v p="$p" 'BEGIN{exit (p<512)?0:1}' || { echo "NG: V5"; exit 1; }

echo "== 結果: V1 V2 V3 V4 V5 と build の入力の確かめが通った"
```

## 14. 確かめ方
- `cd secretary-codex && node --test server.test.mjs` の出力の最後の15行を写す。14本すべて pass（`# pass 14`・`# fail 0`）。
- `node --test secretary-agent/server.test.mjs` を流し（今の試験は変えていないので通るはず）、出力の最後の10行を写す。
- `node --check secretary-codex/server.mjs`・`bash -n scripts/ops/secretary-codex-login.sh`・`bash -n tests/sandbox/secretary-codex.sh` の終了コードがどれも 0。
- `test -x scripts/ops/secretary-codex-login.sh; echo $?` が 0（実行の印）。
- `git diff origin/main...HEAD --name-only` が「触るファイル」の7個と `docs/handoff/secretary-chatgpt/card-3a.md` だけ（ほかがあれば停止。手元の Opus がこのブランチに先に積んだ `docs/` の変更があれば、それは名前を書いて残す）。
- `git diff origin/main...HEAD --numstat -- secretary-codex docker-compose.secretary-codex.yml scripts/ops/secretary-codex-login.sh tests/sandbox/secretary-codex.sh` の削除の数（2列目）がどれも 0。違う時は、そのファイルの `git diff origin/main...HEAD --` の `^-` の行（`grep` と `head -30`）を出して停止。
- `bash scripts/dev/check-before-submit.sh` があれば流し、出力の最後の20行と終了コードを写す（無ければ「無い」と書く）。
- 生出力は作業場所の外の一時フォルダに保存し、パスと全文を報告に書く。

## 15. 想定される分岐と止まる条件
- 0 の前提が違う → 停止し、NEEDS_DECISION: で返す（違った所の生出力を付ける）。
- node の試験が落ちる → server.mjs をカードの全文と1字ずつ見比べる。写し間違いなら直す。カードどおりで落ちる時は、落ちた試験の名前と出力を写して停止（期待を書き換えない）。
- (13) の時間切れが待ちで不安定（まれに落ちる） → 3回流した結果を全部写して停止。待ちの秒数を勝手に変えない。
- カードに無いファイルを触る必要が出た → 停止し、NEEDS_DECISION: で返す。
- 迷ったら停止して NEEDS_DECISION: で Opus に戻す。
- 終わったら commit（最後の行は `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）→ `git log -1` で確かめる → `git push origin release/secretary-codex-stage3` → `git log origin/release/secretary-codex-stage3 -1` で確かめる。PR は作らない。

## 合格の基準（手元の Opus が確かめる）
| 基準 | 確かめ方 |
|---|---|
| 合図の点検（K2 の二重の守り） | node の試験 (6) が pass。一時 VM の V2・V4 で許す一覧の外が0件 |
| 頼みの文を残さない | node の試験 (10) と (13) で一時フォルダが0件。一時 VM の V3 で目印のファイルが0件（2回とも） |
| ログに文と鍵を出さない | node の試験 (2)・(14) が pass |
| 容器の形 | 一時 VM の 2〜5・V1・V5 が通る（`gh workflow run sandbox-test.yml --ref release/secretary-codex-stage3 -f test=secretary-codex`。手元の Opus が流す） |
| 差分が7ファイルとカードだけ | `git diff origin/main...HEAD --name-only` |

## 報告の型
- 1行目: 受領確認。2行目: 「本報告はカード 段3a の実行結果である」。
- 本文: 0-1〜0-7 の生出力、「14. 確かめ方」の生出力、commit と push の後の git log の出力（すべて全文）。
- 止まった時: 止まった所（節の番号）・最後に実行したコマンド・止まった理由。
- 最終行: DONE / BLOCKED: / NEEDS_DECISION: のどれか1つで始める。

END OF CARD
