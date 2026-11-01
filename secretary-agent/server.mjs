// ADR-1056 段2: secretary-agent。頼みの文を Claude Code に 1 回だけ渡し、決まった形の JSON を返す。
// node の標準だけ（追加の依存なし）。DB・redis を持たない。公開しない（frontnet の中だけ）。
// ログは「秒・code」だけ。標準エラーと利用者の文は記録しない。
import http from "node:http";
import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.PORT || 8090);
const TIMEOUT_MS = Number(process.env.CLAUDE_TIMEOUT_MS || 80000);
const MAX_BODY = 16 * 1024;
const PROMPT = fs.readFileSync(path.join(HERE, "prompt.txt"), "utf8");
const SCHEMA = fs.readFileSync(path.join(HERE, "schema.json"), "utf8");

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

// claude を 1 回動かす。返り値: { status, body }
function runClaude(text, now) {
  return new Promise((resolve) => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), "sec-"));
    let settled = false;
    const finish = (status, body) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      fs.rmSync(dir, { recursive: true, force: true });
      resolve({ status, body });
    };
    const child = spawn(
      "claude",
      [
        "-p",
        "--output-format", "json",
        "--json-schema", SCHEMA,
        "--tools", "",
        "--disallowedTools", "mcp__*",
        "--strict-mcp-config",
        "--no-session-persistence",
        "--model", "sonnet",
      ],
      {
        cwd: dir,
        env: {
          PATH: process.env.PATH,
          CLAUDE_CODE_OAUTH_TOKEN: process.env.CLAUDE_CODE_OAUTH_TOKEN,
          CLAUDE_CONFIG_DIR: dir,
          HOME: dir,
          DISABLE_AUTOUPDATER: "1",
          CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC: "1",
        },
        shell: false,
        stdio: ["pipe", "pipe", "ignore"], // 標準エラーは記録しない
      },
    );
    const timer = setTimeout(() => {
      child.kill("SIGKILL");
      finish(504, { code: "timeout" });
    }, TIMEOUT_MS);
    let out = "";
    child.stdout.on("data", (d) => (out += d));
    child.on("error", () => finish(502, { code: "cli_failed" }));
    child.on("close", (exitCode) => {
      if (settled) return;
      if (exitCode !== 0) return finish(502, { code: "cli_failed" });
      try {
        const parsed = JSON.parse(out);
        let intent = parsed.structured_output;
        if (intent === undefined || intent === null) intent = JSON.parse(parsed.result);
        if (intent === null || typeof intent !== "object") throw new Error("not object");
        const cost = typeof parsed.total_cost_usd === "number" ? parsed.total_cost_usd : null;
        finish(200, { intent, total_cost_usd: cost });
      } catch {
        finish(502, { code: "unreadable" });
      }
    });
    child.stdin.on("error", () => {});
    child.stdin.end(`${PROMPT}\n\n今の日時: ${now}\n\n利用者の文:\n${text}`);
  });
}

const server = http.createServer(async (req, res) => {
  try {
    if (req.method === "GET" && req.url === "/health") {
      return send(res, 200, { ready: Boolean(process.env.CLAUDE_CODE_OAUTH_TOKEN) });
    }
    if (req.method === "POST" && req.url === "/intent") {
      let raw;
      try {
        raw = await readBody(req);
      } catch (e) {
        return send(res, e.status || 400, { code: "bad_request" });
      }
      if (!process.env.CLAUDE_CODE_OAUTH_TOKEN) return send(res, 503, { code: "not_ready" });
      let text, now;
      try {
        ({ text, now } = JSON.parse(raw));
      } catch {
        return send(res, 400, { code: "bad_request" });
      }
      if (typeof text !== "string" || typeof now !== "string" || !text) {
        return send(res, 400, { code: "bad_request" });
      }
      if (busy) return send(res, 429, { code: "busy" });
      busy = true;
      const started = process.hrtime.bigint();
      try {
        const { status, body } = await runClaude(text, now);
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
