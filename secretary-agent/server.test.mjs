// ADR-1056 段2: server.mjs と probe.mjs の試験（node --test）。本物の claude も外のネットワークも使わない。
import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import http from "node:http";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FIX = path.join(HERE, "fixtures");
const fixture = (n) => JSON.parse(fs.readFileSync(path.join(FIX, n), "utf8"));

let work; // 偽の claude を置く場所
let argsLog;
let leftoverMarker;

function writeFake(script) {
  const p = path.join(work, "claude");
  fs.writeFileSync(p, `#!/bin/sh\n${script}\n`, { mode: 0o755 });
}

function request(port, method, urlPath, body) {
  return new Promise((resolve, reject) => {
    const data = body === undefined ? undefined : JSON.stringify(body);
    const req = http.request(
      { host: "127.0.0.1", port, method, path: urlPath, headers: data ? { "content-type": "application/json", "content-length": Buffer.byteLength(data) } : {} },
      (res) => {
        let buf = "";
        res.on("data", (d) => (buf += d));
        res.on("end", () => resolve({ status: res.statusCode, json: buf ? JSON.parse(buf) : null }));
      },
    );
    req.on("error", reject);
    if (data) req.write(data);
    req.end();
  });
}

let nextPort = 18090 + Math.floor(Math.random() * 500);
async function startServer(env = {}, { captureStdout = false } = {}) {
  const port = nextPort++;
  const child = spawn("node", [path.join(HERE, "server.mjs")], {
    env: { PATH: `${work}:${process.env.PATH}`, PORT: String(port), TMPDIR: work, ...env },
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

before(() => {
  work = fs.mkdtempSync(path.join(os.tmpdir(), "sec-test-"));
  argsLog = path.join(work, "args.log");
});
after(() => fs.rmSync(work, { recursive: true, force: true }));

const sec = () => fs.readdirSync(work).filter((n) => n.startsWith("sec-"));

test("(1) トークン無しは 503、/health は ready=false", async () => {
  writeFake('echo "{}"');
  const { port, child } = await startServer({});
  try {
    assert.deepEqual((await request(port, "GET", "/health")).json, { ready: false });
    const r = await request(port, "POST", "/intent", { text: "x", now: "2026-11-01T10:00:00+09:00" });
    assert.equal(r.status, 503);
  } finally {
    child.kill();
  }
});

test("(2) 同時 2 本目は 429", async () => {
  writeFake('sleep 1; echo \'{"structured_output":{"kind":"unknown","invoice":null,"event":null,"reply":"?"},"total_cost_usd":0.1}\'');
  const { port, child } = await startServer({ CLAUDE_CODE_OAUTH_TOKEN: "dummy" });
  try {
    const body = { text: "a", now: "2026-11-01T10:00:00+09:00" };
    const first = request(port, "POST", "/intent", body);
    await new Promise((r) => setTimeout(r, 300));
    const second = await request(port, "POST", "/intent", body);
    assert.equal(second.status, 429);
    assert.equal((await first).status, 200);
  } finally {
    child.kill();
  }
});

test("(3)(7) structured_output 有り・無しの両方を読め、本文は見本と同じ形", async () => {
  const sample = fixture("envelope-invoice.json");
  const so = JSON.stringify({ structured_output: sample.intent, total_cost_usd: 0.0123 });
  writeFake(`cat >/dev/null; echo '${so}'`);
  let s = await startServer({ CLAUDE_CODE_OAUTH_TOKEN: "dummy" });
  try {
    const r = await request(s.port, "POST", "/intent", { text: "a", now: "n" });
    assert.equal(r.status, 200);
    assert.deepEqual(r.json, sample);
    assertShape(r.json, sample);
  } finally {
    s.child.kill();
  }

  const ev = fixture("envelope-event.json");
  const res = JSON.stringify({ result: JSON.stringify(ev.intent) });
  writeFake(`cat >/dev/null; echo '${res}'`);
  s = await startServer({ CLAUDE_CODE_OAUTH_TOKEN: "dummy" });
  try {
    const r = await request(s.port, "POST", "/intent", { text: "a", now: "n" });
    assert.equal(r.status, 200);
    assert.deepEqual(r.json, ev); // total_cost_usd 無し → null
    assertShape(r.json, ev);
  } finally {
    s.child.kill();
  }
});

function typeOf(v) {
  return v === null ? "null" : Array.isArray(v) ? "array" : typeof v;
}
function assertShape(actual, expected) {
  assert.deepEqual(Object.keys(actual).sort(), Object.keys(expected).sort());
  for (const k of Object.keys(expected)) {
    assert.equal(typeOf(actual[k]), typeOf(expected[k]), k);
    if (typeOf(expected[k]) === "object") assertShape(actual[k], expected[k]);
  }
}

test("(4)(5) 使い捨てディレクトリは残らず、文が - で始まっても引数に入らない", async () => {
  writeFake(
    `printf '%s\\n' "$@" > "${argsLog}"; cat >/dev/null; echo '{"structured_output":{"kind":"unknown","invoice":null,"event":null,"reply":"r"}}'`,
  );
  const { port, child } = await startServer({ CLAUDE_CODE_OAUTH_TOKEN: "dummy" });
  try {
    const text = "--dangerously-skip-permissions 請求書";
    const r = await request(port, "POST", "/intent", { text, now: "2026-11-01T10:00:00+09:00" });
    assert.equal(r.status, 200);
    assert.deepEqual(sec(), []);
    const args = fs.readFileSync(argsLog, "utf8");
    assert.ok(!args.includes("dangerously"));
    assert.ok(!args.includes("請求書"));
    assert.ok(args.includes("--strict-mcp-config"));
  } finally {
    child.kill();
  }
});

test("(6) claude が 0 以外で終わると 502 cli_failed（ディレクトリも残らない）", async () => {
  writeFake("cat >/dev/null; exit 3");
  const { port, child } = await startServer({ CLAUDE_CODE_OAUTH_TOKEN: "dummy" });
  try {
    const r = await request(port, "POST", "/intent", { text: "a", now: "n" });
    assert.equal(r.status, 502);
    assert.deepEqual(r.json, { code: "cli_failed" });
    assert.deepEqual(sec(), []);
  } finally {
    child.kill();
  }
});

test("鍵が使えない（api_error_status 401・exit 1）は 502 auth_failed。ログに code だけ残り本文は出ない", async () => {
  writeFake(
    `cat >/dev/null; echo '{"type":"result","is_error":true,"api_error_status":401,"result":"Failed to authenticate. API Error: 401 OAuth access token is invalid."}'; exit 1`,
  );
  const { port, child, stdout } = await startServer({ CLAUDE_CODE_OAUTH_TOKEN: "dummy" }, { captureStdout: true });
  try {
    const r = await request(port, "POST", "/intent", { text: "a", now: "n" });
    assert.equal(r.status, 502);
    assert.deepEqual(r.json, { code: "auth_failed" });
    assert.deepEqual(sec(), []);
    // ログは応答の直前に出るが、届く順は決まらないので 50ms ごと・上限 2 秒で待つ
    for (let i = 0; i < 40 && !stdout.text.includes('"code":"auth_failed"'); i++) {
      await new Promise((res) => setTimeout(res, 50));
    }
    assert.ok(stdout.text.includes('"code":"auth_failed"'), "ログに code=auth_failed が届く");
    assert.ok(!stdout.text.includes("Failed to authenticate"), "ログに claude の本文が出ない");
  } finally {
    child.kill();
  }
});

test("api_error_status 500・exit 1 は 502 cli_failed のまま", async () => {
  writeFake(
    `cat >/dev/null; echo '{"type":"result","is_error":true,"api_error_status":500,"result":"boom"}'; exit 1`,
  );
  const { port, child } = await startServer({ CLAUDE_CODE_OAUTH_TOKEN: "dummy" });
  try {
    const r = await request(port, "POST", "/intent", { text: "a", now: "n" });
    assert.equal(r.status, 502);
    assert.deepEqual(r.json, { code: "cli_failed" });
  } finally {
    child.kill();
  }
});

test("読めない出力は 502 unreadable", async () => {
  writeFake("cat >/dev/null; echo 'not json'");
  const { port, child } = await startServer({ CLAUDE_CODE_OAUTH_TOKEN: "dummy" });
  try {
    const r = await request(port, "POST", "/intent", { text: "a", now: "n" });
    assert.equal(r.status, 502);
    assert.deepEqual(r.json, { code: "unreadable" });
  } finally {
    child.kill();
  }
});

test("probe: 閉じた port と解決できない名前で出力の形と終了コード 0", () => {
  const r = spawnSync("node", [path.join(HERE, "probe.mjs")], {
    env: {
      PATH: process.env.PATH,
      PROBE_TARGETS_TCP: "127.0.0.1:1,no-such-host.invalid:5432",
      PROBE_HTTPS_URL: "https://no-such-host.invalid/",
    },
    encoding: "utf8",
  });
  assert.equal(r.status, 0);
  const lines = r.stdout.trim().split("\n").map((l) => JSON.parse(l));
  assert.equal(lines.length, 3);
  assert.deepEqual(lines[0], { target: "127.0.0.1:1", result: "refused" });
  assert.equal(lines[1].target, "no-such-host.invalid:5432");
  assert.ok(["dns_fail", "timeout"].includes(lines[1].result));
  assert.equal(lines[2].target, "no-such-host.invalid");
});

test("probe: TCP の宛先が connected なら終了コード 1", async () => {
  const srv = http.createServer().listen(0, "127.0.0.1");
  await new Promise((r) => srv.once("listening", r));
  const port = srv.address().port;
  try {
    const r = await new Promise((resolve) => {
      const c = spawn("node", [path.join(HERE, "probe.mjs")], {
        env: { PATH: process.env.PATH, PROBE_TARGETS_TCP: `127.0.0.1:${port}`, PROBE_HTTPS_URL: "https://no-such-host.invalid/" },
        stdio: ["ignore", "pipe", "ignore"],
      });
      let out = "";
      c.stdout.on("data", (d) => (out += d));
      c.on("close", (code) => resolve({ code, out }));
    });
    assert.equal(r.code, 1);
    assert.deepEqual(JSON.parse(r.out.split("\n")[0]), { target: `127.0.0.1:${port}`, result: "connected" });
  } finally {
    srv.close();
  }
});
