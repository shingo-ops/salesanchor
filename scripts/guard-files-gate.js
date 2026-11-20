"use strict";
// 見張りを外す PR を止める関所（K10）。設計: docs/handoff/tenant-owner-login-approval/design.md「便7」・card-7.md。
// 守る一覧の分け方（組A・組B）と守りの強さは PO 2026-11-20「1」で決まった。
const {readFileSync} = require("node:fs");

// 組A: GO を書けるのは shingo-ops だけ（22件）。完全一致で照合する。
const GROUP_A = [
  ".github/workflows/guard-files-gate.yml",
  ".github/workflows/guard-files-gate-unit.yml",
  "scripts/guard-files-gate.js",
  "scripts/tests/test-guard-files-gate.js",
  ".github/workflows/lint-tenant-schema.yml",
  ".github/workflows/workflow-lint.yml",
  ".github/workflows/process-artifacts-gate.yml",
  "scripts/lint_tenant_schema.py",
  "scripts/migration-dryrun-report.py",
  "scripts/migration-guard/dryrun-exclusions.tsv",
  "scripts/check_public_tenant_rls.py",
  "backend/app/ops/tenant_rls_allowlist.py",
  "backend/app/ops/tenant_rls_checks.py",
  "backend/app/tasks/tenant_isolation_daily_check.py",
  "backend/tests/test_tenant_login_requests.py",
  "backend/tests/test_check_public_tenant_rls.py",
  "backend/tests/test_tenant_isolation_daily_check.py",
  "scripts/agent-hooks/go-identity-guard/guard.py",
  "scripts/agent-hooks/go-identity-guard/guard-manifest.json",
  "scripts/agent-hooks/go-identity-guard/test_guard.py",
  "scripts/agent-hooks/cloud/go_comment_guard.py",
  "scripts/agent-hooks/cloud/test_go_comment_guard.py",
];
// 組B: GO を書けるのは shingo-ops か shingo-cc（11件）。最後の4件は今は無い（作られる PR を止めるため）。
const GROUP_B = [
  ".github/workflows/test.yml",
  ".github/workflows/migration-test.yml",
  "scripts/check-process-artifacts.js",
  "backend/pyproject.toml",
  "scripts/agent-hooks/cloud/dispatch.sh",
  ".github/workflows/agent-hooks-test.yml",
  ".claude/settings.json",
  "backend/pytest.ini",
  "backend/.pytest.ini",
  "backend/pytest.toml",
  "backend/.pytest.toml",
];

const SELF_WORKFLOW = ".github/workflows/guard-files-gate.yml";
const SHA40 = /^[0-9a-f]{40}$/;
const REPO_RE = /^[a-zA-Z0-9][a-zA-Z0-9_.-]*\/[a-zA-Z0-9][a-zA-Z0-9_.-]*$/;
const GO_RE = /^GO #(\d+) ([0-9a-f]{7,40})(\s.*)?$/;
const PAGE = 100;
const MAX_PAGES = 30;

function changedProtected(files) {
  const found = new Set();
  for (const f of files || []) {
    for (const name of [f.filename, f.previous_filename]) {
      if (typeof name === "string" && (GROUP_A.includes(name) || GROUP_B.includes(name))) found.add(name);
    }
  }
  return [...found];
}

function requiredWriters(changed) {
  return changed.some(n => GROUP_A.includes(n)) ? ["shingo-ops"] : ["shingo-ops", "shingo-cc"];
}

// 書き手・書式・番号・SHA を満たす GO を集める。書き直したものは rewritten に分ける。
function findGo(number, comments, commits, writers) {
  const valid = [];
  let rewritten = false;
  for (const c of comments || []) {
    if (!c || !c.user || !writers.includes(c.user.login)) continue;
    const first = String(c.body || "").trim().split(/\r?\n/)[0].trim();
    const m = GO_RE.exec(first);
    if (!m || Number(m[1]) !== number) continue;
    const hits = (commits || []).filter(k => typeof k.sha === "string" && k.sha.startsWith(m[2]));
    if (hits.length !== 1 || !SHA40.test(hits[0].sha)) continue;
    if (c.updated_at !== c.created_at) { rewritten = true; continue; }
    valid.push({goSha: hits[0].sha, login: c.user.login});
  }
  return {valid, rewritten};
}

function normalizeWorkflow(text) {
  return String(text).replace(/['"]/g, "").replace(/\s+/g, " ").toLowerCase();
}

function decide(input) {
  const {number, eventHead, pr, files, commits, comments, workflows, blobs} = input;
  const fail = (reason, changed = [], approver = null) => ({ok: false, reason, changed, approver});
  // 1
  if (pr.state !== "open" || pr.baseRef !== "main") return {ok: true, reason: "対象外（open の main 向け PR ではない）", changed: [], approver: null};
  // 2
  if (pr.headSha !== eventHead) return fail("新しい push の実行を待つ（今の head が出来事の head と違う）");
  // 3
  if (files.length !== pr.changedFiles) return fail("変わったファイルを全部読めなかった（files " + files.length + " 件・changed_files " + pr.changedFiles + " 件）");
  if (commits.length >= 250 || commits.length !== pr.commits) return fail("commit の一覧を全部読めなかった（commits " + commits.length + " 件・PR の commits " + pr.commits + " 件）");
  // 4
  for (const [path, text] of Object.entries(workflows || {})) {
    if (path === SELF_WORKFLOW) continue;
    if (normalizeWorkflow(text).includes("guard-files gate")) {
      return fail("同じ名前の検査は足せない: " + path);
    }
  }
  // 5
  const changed = changedProtected(files);
  if (changed.length === 0) return {ok: true, reason: "守るファイルの変更なし", changed: [], approver: null};
  // 6
  const writers = requiredWriters(changed);
  const who = writers.length === 1 ? "PO 本人（shingo-ops）" : "shingo-ops か shingo-cc";
  // 7
  const {valid, rewritten} = findGo(number, comments, commits, writers);
  // 8
  let contentMismatch = false;
  for (const go of valid) {
    const atGo = blobs && blobs[go.goSha];
    const atHead = blobs && blobs[pr.headSha];
    const same = !!atGo && !!atHead && changed.every(p =>
      Object.prototype.hasOwnProperty.call(atGo, p) && Object.prototype.hasOwnProperty.call(atHead, p) && atGo[p] === atHead[p]);
    if (same) {
      return {ok: true, reason: "GO #" + number + " " + go.goSha + " by " + go.login, changed, approver: go.login};
    }
    contentMismatch = true;
  }
  // 9
  let reason = "守るファイルが変わっている: " + changed.join(", ") + "。要る書き手: " + who +
    "。GO の書式: 1行目が「GO #" + number + " <SHA 7〜40文字>」（SHA はこの PR の commit のちょうど1件の先頭）。";
  if (contentMismatch) reason += " GO の後に守るファイルが変わった。";
  if (rewritten) reason += " 書き直した GO は使えない。新しく書く。";
  return fail(reason, changed);
}

async function paginate(io, path) {
  const out = [];
  for (let page = 1; page <= MAX_PAGES; page++) {
    const data = await io.request("GET", path + "?per_page=" + PAGE + "&page=" + page);
    if (!Array.isArray(data)) throw new Error("Unexpected list response");
    out.push(...data);
    if (data.length < PAGE) return out;
  }
  throw new Error("Too many pages");
}

function contentsPath(repo, path, sha) {
  if (!SHA40.test(sha)) throw new Error("Invalid SHA for contents");
  return "/repos/" + repo + "/contents/" + path.split("/").map(encodeURIComponent).join("/") + "?ref=" + sha;
}

async function collect(config, io) {
  const {repo, number, eventHead} = config;
  if (!REPO_RE.test(repo) || !Number.isSafeInteger(number) || number <= 0) throw new Error("Invalid repository/PR number");
  const route = "/repos/" + repo + "/pulls/" + number;
  const raw = await io.request("GET", route);
  const pr = {
    state: raw.state, baseRef: raw.base && raw.base.ref, headSha: raw.head && raw.head.sha,
    changedFiles: raw.changed_files, commits: raw.commits,
  };
  const base = {number, eventHead, pr, files: [], commits: [], comments: [], workflows: {}, blobs: {}};
  if (pr.state !== "open" || pr.baseRef !== "main" || pr.headSha !== eventHead) return base;
  const files = (await paginate(io, route + "/files")).map(f => ({
    filename: f.filename, status: f.status, previous_filename: f.previous_filename,
  }));
  const commits = (await paginate(io, route + "/commits")).map(c => ({sha: c.sha}));
  const comments = (await paginate(io, "/repos/" + repo + "/issues/" + number + "/comments")).map(c => ({
    user: {login: c.user && c.user.login}, body: c.body, created_at: c.created_at, updated_at: c.updated_at,
  }));
  const workflows = {};
  for (const f of files) {
    const n = f.filename;
    if (typeof n !== "string" || f.status === "removed" || !n.startsWith(".github/workflows/")) continue;
    if (!(n.endsWith(".yml") || n.endsWith(".yaml")) || n === SELF_WORKFLOW) continue;
    const r = await io.request("GET", contentsPath(repo, n, pr.headSha));
    if (!r || r.status === 404 || typeof r.content !== "string" || r.content === "" || r.encoding !== "base64") {
      throw new Error("Workflow content unavailable: " + n);
    }
    workflows[n] = Buffer.from(r.content, "base64").toString("utf8");
  }
  const blobs = {};
  const changed = changedProtected(files);
  if (changed.length > 0 && files.length === pr.changedFiles) {
    const {valid} = findGo(number, comments, commits, requiredWriters(changed));
    const shas = [pr.headSha, ...new Set(valid.map(g => g.goSha))];
    for (const sha of shas) {
      blobs[sha] = {};
      for (const p of changed) {
        const r = await io.request("GET", contentsPath(repo, p, sha));
        blobs[sha][p] = r && r.status === 404 ? null : (r && r.sha) || null;
      }
    }
  }
  return {...base, files, commits, comments, workflows, blobs};
}

function runtime(env = process.env) {
  if (!env.GITHUB_TOKEN || !env.GITHUB_EVENT_PATH) throw new Error("Required GitHub runtime configuration missing");
  if (env.GITHUB_API_URL !== "https://api.github.com") throw new Error("Unexpected GitHub API URL");
  if (env.GITHUB_EVENT_NAME !== "pull_request_target") throw new Error("Trusted pull_request_target runtime required");
  const event = JSON.parse(readFileSync(env.GITHUB_EVENT_PATH, "utf8"));
  const number = event.pull_request && event.pull_request.number;
  const eventHead = event.pull_request && event.pull_request.head && event.pull_request.head.sha;
  const repo = env.GITHUB_REPOSITORY;
  if (!Number.isSafeInteger(number) || number <= 0) throw new Error("Invalid PR number");
  if (typeof eventHead !== "string" || !SHA40.test(eventHead)) throw new Error("Invalid event head SHA");
  if (typeof repo !== "string" || !REPO_RE.test(repo)) throw new Error("Invalid repository");
  const request = async (method, path) => {
    const response = await fetch(env.GITHUB_API_URL + path, {
      method,
      headers: {
        Authorization: "Bearer " + env.GITHUB_TOKEN,
        Accept: "application/vnd.github+json",
        "X-GitHub-Api-Version": "2026-03-10",
      },
      signal: AbortSignal.timeout(30000),
    });
    if (response.status === 404) return {status: 404};
    if (!response.ok) throw new Error("GitHub request failed: HTTP " + response.status);
    return response.json();
  };
  return collect({repo, number, eventHead}, {request}).then(decide);
}

module.exports = {decide, collect, runtime, GROUP_A, GROUP_B};

if (require.main === module) {
  runtime().then(result => {
    console.log(JSON.stringify({ok: result.ok, reason: result.reason, changed: result.changed}));
    if (!result.ok) process.exitCode = 1;
  }).catch(() => {
    console.error("guard-files gate runtime failed; inspect the workflow run");
    process.exitCode = 1;
  });
}
