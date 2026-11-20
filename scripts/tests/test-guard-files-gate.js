"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const {decide, collect, runtime, GROUP_A, GROUP_B} = require("../guard-files-gate.js");

const ROOT = path.resolve(__dirname, "..", "..");
const HEAD = "a".repeat(40);
const OLD = "b".repeat(40);
const OLD2 = "b".repeat(7) + "c".repeat(33);
const A_FILE = "backend/app/ops/tenant_rls_allowlist.py";
const B_FILE = ".github/workflows/migration-test.yml";
const T = "2026-11-20T00:00:00Z";

function go(login, number, sha, extra = {}) {
  return {user: {login}, body: "GO #" + number + " " + sha, created_at: T, updated_at: T, ...extra};
}
function input(over = {}) {
  return {
    number: 7, eventHead: HEAD,
    pr: {state: "open", baseRef: "main", headSha: HEAD, changedFiles: 1, commits: 2},
    files: [{filename: "docs/readme.md", status: "modified"}],
    commits: [{sha: OLD}, {sha: HEAD}],
    comments: [], workflows: {}, blobs: {},
    ...over,
  };
}
function protectedInput(file, comments, blobs, over = {}) {
  return input({files: [{filename: file, status: "modified"}], comments, blobs, ...over});
}
const SAME = {[HEAD]: {[A_FILE]: "x1"}, [OLD]: {[A_FILE]: "x1"}};

test("T1 守るファイル無し → 通す", () => assert.equal(decide(input()).ok, true));
test("T2 組A・GO 無し → 落とす", () => {
  const r = decide(protectedInput(A_FILE, [], {}));
  assert.equal(r.ok, false);
  assert.deepEqual(r.changed, [A_FILE]);
  assert.match(r.reason, /PO 本人（shingo-ops）/);
});
test("T3 組A・shingo-cc の GO → 落とす", () => {
  assert.equal(decide(protectedInput(A_FILE, [go("shingo-cc", 7, HEAD)], SAME)).ok, false);
});
test("T4 組A・shingo-ops の GO（40桁）→ 通す", () => {
  const r = decide(protectedInput(A_FILE, [go("shingo-ops", 7, HEAD)], {[HEAD]: {[A_FILE]: "x1"}}));
  assert.equal(r.ok, true);
  assert.equal(r.approver, "shingo-ops");
  assert.match(r.reason, /GO #7 a{40} by shingo-ops/);
});
test("T5 古い commit の7桁 SHA・blob 同じ → 通す", () => {
  const r = decide(protectedInput(A_FILE, [go("shingo-ops", 7, OLD.slice(0, 7))], SAME));
  assert.equal(r.ok, true);
});
test("T6 T5 で blob が違う → 落とす", () => {
  const blobs = {[HEAD]: {[A_FILE]: "x2"}, [OLD]: {[A_FILE]: "x1"}};
  const r = decide(protectedInput(A_FILE, [go("shingo-ops", 7, OLD.slice(0, 7))], blobs));
  assert.equal(r.ok, false);
  assert.match(r.reason, /GO の後に守るファイルが変わった/);
});
test("T7 組B だけ・shingo-cc の GO → 通す", () => {
  const blobs = {[HEAD]: {[B_FILE]: "y"}};
  assert.equal(decide(protectedInput(B_FILE, [go("shingo-cc", 7, HEAD)], blobs)).ok, true);
});
test("T8 組B だけ・highlifejpn-debug の GO → 落とす", () => {
  const blobs = {[HEAD]: {[B_FILE]: "y"}};
  assert.equal(decide(protectedInput(B_FILE, [go("highlifejpn-debug", 7, HEAD)], blobs)).ok, false);
});
test("T9 組A と組B の両方・shingo-cc の GO → 落とす", () => {
  const files = [{filename: A_FILE, status: "modified"}, {filename: B_FILE, status: "modified"}];
  const r = decide(input({files, pr: {state: "open", baseRef: "main", headSha: HEAD, changedFiles: 2, commits: 2},
    comments: [go("shingo-cc", 7, HEAD)], blobs: {[HEAD]: {[A_FILE]: "1", [B_FILE]: "2"}}}));
  assert.equal(r.ok, false);
});
test("T10 名前の変更: previous_filename が組A → GO 無しで落とす", () => {
  const files = [{filename: "docs/new.md", previous_filename: A_FILE, status: "renamed"}];
  const r = decide(input({files}));
  assert.equal(r.ok, false);
  assert.deepEqual(r.changed, [A_FILE]);
});
test("T11 GO の番号が別の PR → 落とす", () => {
  assert.equal(decide(protectedInput(A_FILE, [go("shingo-ops", 8, HEAD)], SAME)).ok, false);
});
test("T12 SHA が6桁 → 落とす", () => {
  assert.equal(decide(protectedInput(A_FILE, [go("shingo-ops", 7, "aaaaaa")], SAME)).ok, false);
});
test("T13 SHA の先頭が2件の commit と一致 → 落とす", () => {
  const commits = [{sha: OLD}, {sha: OLD2}, {sha: HEAD}];
  const r = decide(protectedInput(A_FILE, [go("shingo-ops", 7, "bbbbbbb")], SAME,
    {commits, pr: {state: "open", baseRef: "main", headSha: HEAD, changedFiles: 1, commits: 3}}));
  assert.equal(r.ok, false);
});
test("T14 SHA が PR の commits に無い → 落とす", () => {
  assert.equal(decide(protectedInput(A_FILE, [go("shingo-ops", 7, "d".repeat(40))], SAME)).ok, false);
});
test("T15 引用や前置き・2行目以降の GO → 落とす", () => {
  for (const body of ["> GO #7 " + HEAD, "ok GO #7 " + HEAD, "よろしく\nGO #7 " + HEAD]) {
    const c = {user: {login: "shingo-ops"}, body, created_at: T, updated_at: T};
    assert.equal(decide(protectedInput(A_FILE, [c], SAME)).ok, false, body);
  }
});
test("T16 今の head が eventHead と違う → 落とす", () => {
  const r = decide(input({pr: {state: "open", baseRef: "main", headSha: "e".repeat(40), changedFiles: 1, commits: 2}}));
  assert.equal(r.ok, false);
  assert.match(r.reason, /新しい push/);
});
test("T17 削除された組A（無い同士）: GO があれば通す・無ければ落とす", () => {
  const files = [{filename: A_FILE, status: "removed"}];
  const blobs = {[HEAD]: {[A_FILE]: null}, [OLD]: {[A_FILE]: null}};
  assert.equal(decide(input({files, comments: [go("shingo-ops", 7, OLD.slice(0, 7))], blobs})).ok, true);
  assert.equal(decide(input({files, comments: [], blobs})).ok, false);
});
test("T18 closed または base が main 以外 → 通す", () => {
  assert.equal(decide(input({pr: {state: "closed", baseRef: "main", headSha: HEAD, changedFiles: 1, commits: 2}})).ok, true);
  assert.equal(decide(input({pr: {state: "open", baseRef: "develop", headSha: HEAD, changedFiles: 1, commits: 2}})).ok, true);
});
test("T25 updated_at が違う GO → 落とす", () => {
  const r = decide(protectedInput(A_FILE, [go("shingo-ops", 7, HEAD, {updated_at: "2026-11-21T00:00:00Z"})], SAME));
  assert.equal(r.ok, false);
  assert.match(r.reason, /書き直した GO は使えない/);
});
test("T26 files の件数が changed_files より少ない → 落とす", () => {
  const r = decide(input({pr: {state: "open", baseRef: "main", headSha: HEAD, changedFiles: 5, commits: 2}}));
  assert.equal(r.ok, false);
});
test("T27 commits が 250件 → 落とす", () => {
  const commits = Array.from({length: 250}, (_, i) => ({sha: String(i).padStart(40, "0")}));
  const r = decide(input({commits, pr: {state: "open", baseRef: "main", headSha: HEAD, changedFiles: 1, commits: 250}}));
  assert.equal(r.ok, false);
});
test("T28 同じ名前の job を足す workflow → GO があっても落とす・自身は対象外", () => {
  const files = [{filename: ".github/workflows/x.yml", status: "added"}, {filename: A_FILE, status: "modified"}];
  const base = {files, pr: {state: "open", baseRef: "main", headSha: HEAD, changedFiles: 2, commits: 2},
    comments: [go("shingo-ops", 7, HEAD)], blobs: {[HEAD]: {[A_FILE]: "1"}}};
  const bad = decide(input({...base, workflows: {".github/workflows/x.yml": 'name: "Guard-Files   Gate"\n'}}));
  assert.equal(bad.ok, false);
  assert.match(bad.reason, /x\.yml/);
  const self = decide(input({...base, workflows: {".github/workflows/guard-files-gate.yml": "name: guard-files gate\n"}}));
  assert.equal(self.ok, true);
});
test("T29 組B だけ・shingo-ops の GO → 通す", () => {
  assert.equal(decide(protectedInput(B_FILE, [go("shingo-ops", 7, HEAD)], {[HEAD]: {[B_FILE]: "y"}})).ok, true);
});
test("T33 守るファイル無しでも同じ名前の workflow は落とす", () => {
  const r = decide(input({
    files: [{filename: ".github/workflows/x.yml", status: "added"}],
    workflows: {".github/workflows/x.yml": "jobs:\n  a:\n    name: guard-files gate\n"},
  }));
  assert.equal(r.ok, false);
});
test("T34 commits の件数が PR の commits と違う → 落とす", () => {
  const r = decide(input({pr: {state: "open", baseRef: "main", headSha: HEAD, changedFiles: 1, commits: 9}}));
  assert.equal(r.ok, false);
});
test("T35 .yaml の文でも落とす", () => {
  const r = decide(input({files: [{filename: ".github/workflows/x.yaml", status: "added"}],
    workflows: {".github/workflows/x.yaml": "name: Guard-files   gate"}}));
  assert.equal(r.ok, false);
});
test("T36 x-guard-files-gate.yml の文も落とす（除外は完全な道だけ）", () => {
  const p = ".github/workflows/x-guard-files-gate.yml";
  const r = decide(input({files: [{filename: p, status: "added"}], workflows: {[p]: "name: guard-files gate"}}));
  assert.equal(r.ok, false);
});

// ---- collect ----
function ghFile(i) { return {filename: "docs/f" + i + ".md", status: "modified"}; }
function router(handlers, seen) {
  return async (method, p) => {
    seen.push(p);
    for (const [prefix, fn] of handlers) if (p.startsWith(prefix)) return fn(p);
    throw new Error("unexpected " + p);
  };
}
function page(list, p) {
  const n = Number(/&page=(\d+)/.exec(p)[1]);
  return list.slice((n - 1) * 100, n * 100);
}
const R = "/repos/o/r/pulls/7";
const prRaw = (over = {}) => ({state: "open", base: {ref: "main"}, head: {sha: HEAD}, changed_files: 101, commits: 101, ...over});

test("T19 files のページ送りで101件目の組A を拾う", async () => {
  const files = Array.from({length: 100}, (_, i) => ghFile(i)).concat([{filename: A_FILE, status: "modified"}]);
  const seen = [];
  const io = {request: router([
    [R + "/files", p => page(files, p)],
    [R + "/commits", () => [{sha: HEAD}]],
    ["/repos/o/r/issues/7/comments", () => []],
    [R, () => prRaw({commits: 1})],
    ["/repos/o/r/contents/", () => ({sha: "blob1"})],
  ].sort((a, b) => b[0].length - a[0].length), seen)};
  const out = await collect({repo: "o/r", number: 7, eventHead: HEAD}, io);
  assert.equal(out.files.length, 101);
  assert.ok(decide({...out}).changed.includes(A_FILE));
});
test("T20 contents の 404 を「無い」とする", async () => {
  const seen = [];
  const io = {request: router([
    [R + "/files", () => [{filename: A_FILE, status: "removed"}]],
    [R + "/commits", () => [{sha: HEAD}]],
    ["/repos/o/r/issues/7/comments", () => []],
    [R, () => prRaw({changed_files: 1, commits: 1})],
    ["/repos/o/r/contents/", () => ({status: 404})],
  ].sort((a, b) => b[0].length - a[0].length), seen)};
  const out = await collect({repo: "o/r", number: 7, eventHead: HEAD}, io);
  assert.equal(out.blobs[HEAD][A_FILE], null);
});
test("T21 request の例外は外へ投げる", async () => {
  const io = {request: async () => { throw new Error("boom"); }};
  await assert.rejects(collect({repo: "o/r", number: 7, eventHead: HEAD}, io), /boom/);
});
test("T30 commits と comments もページ送りで101件目を拾う", async () => {
  const commits = Array.from({length: 100}, (_, i) => ({sha: String(i).padStart(40, "1")})).concat([{sha: HEAD}]);
  const comments = Array.from({length: 100}, () => ({user: {login: "x"}, body: "hi", created_at: T, updated_at: T}))
    .concat([{user: {login: "shingo-ops"}, body: "last", created_at: T, updated_at: T}]);
  const seen = [];
  const io = {request: router([
    [R + "/files", () => [ghFile(1)]],
    [R + "/commits", p => page(commits, p)],
    ["/repos/o/r/issues/7/comments", p => page(comments, p)],
    [R, () => prRaw({changed_files: 1, commits: 101})],
  ].sort((a, b) => b[0].length - a[0].length), seen)};
  const out = await collect({repo: "o/r", number: 7, eventHead: HEAD}, io);
  assert.equal(out.commits.length, 101);
  assert.equal(out.comments.length, 101);
  assert.equal(out.comments[100].body, "last");
});
test("T31 contents の ref は 40文字の sha（GO の短い SHA ではない）", async () => {
  const seen = [];
  const io = {request: router([
    [R + "/files", () => [{filename: A_FILE, status: "modified"}]],
    [R + "/commits", () => [{sha: OLD}, {sha: HEAD}]],
    ["/repos/o/r/issues/7/comments", () => [go("shingo-ops", 7, OLD.slice(0, 7))]],
    [R, () => prRaw({changed_files: 1, commits: 2})],
    ["/repos/o/r/contents/", () => ({sha: "blob1"})],
  ].sort((a, b) => b[0].length - a[0].length), seen)};
  const out = await collect({repo: "o/r", number: 7, eventHead: HEAD}, io);
  const refs = seen.filter(p => p.includes("/contents/")).map(p => p.split("?ref=")[1]);
  assert.ok(refs.length >= 2);
  for (const r of refs) assert.match(r, /^[0-9a-f]{40}$/);
  assert.ok(refs.includes(OLD));
  assert.equal(decide(out).ok, true);
});

// ---- runtime ----
function envWith(over = {}, eventHead = HEAD) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gfg-"));
  const file = path.join(dir, "event.json");
  fs.writeFileSync(file, JSON.stringify({pull_request: {number: 7, head: {sha: eventHead}}}));
  return {GITHUB_TOKEN: "t", GITHUB_EVENT_PATH: file, GITHUB_API_URL: "https://api.github.com",
    GITHUB_EVENT_NAME: "pull_request_target", GITHUB_REPOSITORY: "o/r", ...over};
}
test("T32 runtime は設定が外れると例外", () => {
  assert.throws(() => runtime(envWith({GITHUB_TOKEN: ""})));
  assert.throws(() => runtime(envWith({GITHUB_EVENT_NAME: "pull_request"})));
  assert.throws(() => runtime(envWith({GITHUB_API_URL: "https://example.com"})));
  assert.throws(() => runtime(envWith({}, "abc123")));
});

// ---- 一覧 ----
test("T22 一覧に重複が無く件数が 22 と 11", () => {
  assert.equal(GROUP_A.length, 22);
  assert.equal(GROUP_B.length, 11);
  const all = [...GROUP_A, ...GROUP_B];
  assert.equal(new Set(all).size, 33);
});
const MISSING = ["backend/pytest.ini", "backend/.pytest.ini", "backend/pytest.toml", "backend/.pytest.toml"];
test("T23 33件のうち今は無い4件を除く29件が実在する", () => {
  for (const f of [...GROUP_A, ...GROUP_B]) {
    if (MISSING.includes(f)) assert.equal(fs.existsSync(path.join(ROOT, f)), false, f);
    else assert.equal(fs.existsSync(path.join(ROOT, f)), true, f);
  }
  assert.ok(MISSING.every(f => GROUP_B.includes(f)));
});
test("T24 guard-files-gate.yml の形", () => {
  const dir = path.join(ROOT, ".github/workflows");
  const text = fs.readFileSync(path.join(dir, "guard-files-gate.yml"), "utf8");
  const lines = text.split("\n");
  assert.equal(lines.filter(l => /^\s*name:\s*guard-files gate\s*$/.test(l)).length, 1);
  assert.ok(text.includes("ref: ${{ github.sha }}"));
  assert.equal(lines.filter(l => /^\s*pull_request:/.test(l)).length, 0);
  assert.equal(lines.filter(l => l.includes("github.event.pull_request.head")).length, 0);
  for (const f of fs.readdirSync(dir)) {
    if (f === "guard-files-gate.yml" || !/\.ya?ml$/.test(f)) continue;
    const other = fs.readFileSync(path.join(dir, f), "utf8").split("\n");
    assert.equal(other.filter(l => /^\s*(-\s*)?name:\s*["']?guard-files gate/i.test(l)).length, 0, f);
  }
});
