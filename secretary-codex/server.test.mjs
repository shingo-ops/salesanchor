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
import { compose } from "../secretary-agent/compose.mjs";

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

test("(9) 引数: 止め設定19組・-m のすぐ後に model・最後は -・答えの形のファイルがある・頼みの文は引数に無く標準入力にある", async () => {
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
  assert.equal(a.filter((x) => x === "-c").length, 19);
  assert.ok(a.includes('web_search="disabled"'));
  assert.ok(a.includes("features.shell_tool=false"));
  assert.ok(a.includes("features.remote_plugin=false"));
  assert.ok(a.includes("features.shell_snapshot=false"));
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
