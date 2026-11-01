// ADR-1056 段2: つながりの試し（K4）。deploy が 1 回動かし、結果を Actions のログに残す。
// TCP の宛先は PROBE_TARGETS_TCP（host:port のカンマ区切り。既定 postgres:5432,redis:6379）、
// HTTPS の宛先は PROBE_HTTPS_URL（既定 https://api.anthropic.com/）。
// 終了コードの決め: TCP の宛先のどれかが connected なら 1（DB か redis に届いた＝不合格）。それ以外は 0。
// トークンは読まない・出さない。node の標準 node:net・node:https だけ。
import net from "node:net";
import https from "node:https";

const TCP_TARGETS = (process.env.PROBE_TARGETS_TCP || "postgres:5432,redis:6379")
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);
const HTTPS_URL = process.env.PROBE_HTTPS_URL || "https://api.anthropic.com/";

function tcp(target) {
  const idx = target.lastIndexOf(":");
  const host = target.slice(0, idx);
  const port = Number(target.slice(idx + 1));
  return new Promise((resolve) => {
    const sock = net.connect({ host, port });
    let done = false;
    const end = (result) => {
      if (done) return;
      done = true;
      sock.destroy();
      resolve({ target, result });
    };
    sock.setTimeout(3000, () => end("timeout"));
    sock.on("connect", () => end("connected"));
    sock.on("error", (e) => {
      if (e.code === "ENOTFOUND" || e.code === "EAI_AGAIN") end("dns_fail");
      else if (e.code === "ECONNREFUSED") end("refused");
      else end("timeout");
    });
  });
}

function head(url) {
  const target = new URL(url).hostname;
  return new Promise((resolve) => {
    const req = https.request(url, { method: "HEAD", timeout: 10000 }, (res) => {
      res.resume();
      resolve({ target, result: res.statusCode });
    });
    req.on("timeout", () => {
      req.destroy();
      resolve({ target, result: "timeout" });
    });
    req.on("error", (e) => resolve({ target, result: e.code || "error" }));
    req.end();
  });
}

const tcpResults = await Promise.all(TCP_TARGETS.map(tcp));
for (const r of tcpResults) console.log(JSON.stringify(r));
console.log(JSON.stringify(await head(HTTPS_URL)));
process.exit(tcpResults.some((r) => r.result === "connected") ? 1 : 0);
