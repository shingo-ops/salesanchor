// ADR-1058 段3: secretary-codex。頼みの文を Codex CLI（PO の ChatGPT 月額契約）に 1 回だけ渡し、決まった形の JSON を返す。
// secretary-agent/server.mjs を写し、呼ぶ所だけ codex に変えた（design.md §5-1）。node の標準だけ。DB・redis を持たない。公開しない。
// ログは「秒・code」だけ。標準エラー・利用者の文・auth.json の中身は記録しない。
import http from "node:http";
import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

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
// 頼みの文の組み立ては secretary-agent/compose.mjs を同じファイルとして使う（ADR-1077 便2a。容器では /app に並ぶ。試験では secretary-agent を指す）。
const { compose, readRules } = await import(pathToFileURL(path.join(ASSET_DIR, "compose.mjs")).href);

// 止め設定（recon §5-2 の手元の試しの18組に、一時 VM で見つけた shell_snapshot を足した19組。card-3e）。web_search の値は引用符ごと渡す（手元の試しと同じ形）。
const DISABLED_FEATURES = [
  "shell_tool", "unified_exec", "view_image", "multi_agent", "apps", "plugins",
  "browser_use", "browser_use_external", "computer_use", "image_generation", "goals",
  "hooks", "sleep_tool", "code_mode_host", "tool_suggest", "skill_search", "remote_plugin",
  "shell_snapshot",
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
function runCodex(text, now, model, rules) {
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
    child.stdin.end(compose(PROMPT, now, text, rules));
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
      let text, now, model, rules;
      try {
        ({ text, now, model, rules } = JSON.parse(raw));
      } catch {
        return send(res, 400, { code: "bad_request" });
      }
      if (typeof text !== "string" || typeof now !== "string" || !text) {
        return send(res, 400, { code: "bad_request" });
      }
      if (typeof model !== "string" || !MODEL_RE.test(model)) {
        return send(res, 400, { code: "bad_request" });
      }
      rules = readRules(rules);
      if (rules === null) return send(res, 400, { code: "bad_request" });
      if (busy) return send(res, 429, { code: "busy" });
      busy = true;
      const started = process.hrtime.bigint();
      try {
        const { status, body } = await runCodex(text, now, model, rules);
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
