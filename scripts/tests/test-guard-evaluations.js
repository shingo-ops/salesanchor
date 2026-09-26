"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const {execFileSync} = require("node:child_process");
const {validate} = require("../check-guard-evaluations");
const {runGate, CONTEXT} = require("../run-guard-evaluation");
const THEME = "docs/handoff/design-partner-card-ops/";
const GUARDS = THEME + "guards/";
const RECORDS = THEME + "guard-evaluations/";
const READS = [THEME + "guards.md", GUARDS + "00-common.md", GUARDS + "11-lint.md", GUARDS + "12-guard-authoring.md"];
function fixture(t, withoutAuthoring = false) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "guard-eval-test-"));
  t.after(() => fs.rmSync(dir, {recursive: true, force: true}));
  const git = (...args) => execFileSync("git", ["--literal-pathspecs", ...args], {cwd: dir, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"]}).trim();
  const write = (name, text) => { fs.mkdirSync(path.dirname(path.join(dir, name)), {recursive: true}); fs.writeFileSync(path.join(dir, name), text); };
  git("init", "-q"); git("config", "user.email", "guard-test@example.invalid"); git("config", "user.name", "Guard Test");
  for (const name of READS) if (!withoutAuthoring || !name.endsWith("12-guard-authoring.md")) write(name, "# Required reading\n");
  write(GUARDS + "01-read.md", "# Read guard\n"); write("scripts/card-lint.sh", "#!/bin/sh\nexit 0\n");
  const commit = () => { git("add", "--all"); git("commit", "-qm", "fixture"); return git("rev-parse", "HEAD"); };
  write("docs/ordinary-source.md", "# Read guard\n");
  for (const name of ["scripts/check-guard-evaluations.js", "scripts/run-guard-evaluation.js", "scripts/tests/test-guard-evaluations.js", ".github/workflows/guard-authoring-gate.yml"]) write(name, "trusted fixture\n");
  const base = commit();
  const blob = (rev, name) => { try { return git("rev-parse", "--verify", rev + ":" + name); } catch { return null; } };
  function record(paths, logic = false) {
    const changed = commit();
    const readPaths = [...new Set([...READS, ...paths.filter(p => p.startsWith(GUARDS) && p.endsWith(".md"))])].sort();
    const doc = {
      version: 1, base_commit: base,
      changes: paths.sort().map(name => ({path: name, old_blob: blob(base, name), new_blob: blob(changed, name)})),
      reads: readPaths.map(name => ({path: name, ref: blob(base, name) ? "base" : "head", blob: blob(base, name) || blob(changed, name)})),
      assessment: Object.fromEntries(["purpose", "impact", "false_positives", "future_costs", "alternatives", "decision", "rollback", "owner", "normal_example", "violation_example"].map(k => [k, "Recorded fixture assessment for " + k])),
      verification: {kind: "documentation", reason: "Only explanatory guard text changes"},
    };
    if (logic) {
      write(RECORDS + "proof.txt", "normal example passed; expected rejection observed\n");
      const reportBlob = git("hash-object", RECORDS + "proof.txt");
      const proof = {command: "node scripts/tests/example.js", expected_exit: 0, actual_exit: 0, report_path: RECORDS + "proof.txt", report_blob: reportBlob};
      doc.verification = {kind: "logic", normal: {...proof}, negative: {...proof}};
    }
    write(RECORDS + "evaluation.json", JSON.stringify(doc));
    return {doc, head: commit()};
  }
  const save = doc => { write(RECORDS + "evaluation.json", JSON.stringify(doc)); return commit(); };
  return {dir, git, write, commit, base, record, save};
}
for (const name of ["docs/ordinary.md", "frontend/src/example.ts", "backend/app/example.py"]) {
  test("normal: unrelated " + name, t => {const f = fixture(t); f.write(name, "ordinary change\n"); assert.equal(validate(f.dir, f.base, f.commit()).kind, "outside-scope");});
}
test("normal: evaluated documentation", t => {const f = fixture(t); f.write(GUARDS + "01-read.md", "# Updated guidance\n"); const r = f.record([GUARDS + "01-read.md"]); assert.equal(validate(f.dir, f.base, r.head).checked, 1);});
for (const kind of ["add", "change", "delete", "rename-out", "rename-in"]) {
  test("negative: evaluation missing for " + kind, t => {
    const f = fixture(t), old = GUARDS + "01-read.md";
    if (kind === "add") f.write(GUARDS + "new.md", "# New\n");
    if (kind === "change") f.write(old, "# Changed\n");
    if (kind === "delete" || kind === "rename-out") fs.unlinkSync(path.join(f.dir, old));
    if (kind === "rename-out") f.write("docs/moved.md", "# Read guard\n");
    if (kind === "rename-in") fs.renameSync(path.join(f.dir, "docs/ordinary-source.md"), path.join(f.dir, GUARDS + "new.md"));
    assert.throws(() => validate(f.dir, f.base, f.commit()), /evaluation JSON/);
  });
}
test("normal: rename retains both sides", t => {const f = fixture(t); fs.renameSync(path.join(f.dir, GUARDS + "01-read.md"), path.join(f.dir, GUARDS + "renamed.md")); const r = f.record([GUARDS + "01-read.md", GUARDS + "renamed.md"]); assert.equal(validate(f.dir, f.base, r.head).checked, 2);});
for (const key of ["path", "old_blob", "new_blob"]) test("negative: stale change " + key, t => {
  const f = fixture(t); f.write(GUARDS + "01-read.md", "# Updated\n"); const r = f.record([GUARDS + "01-read.md"]); r.doc.changes[0][key] = "wrong";
  assert.throws(() => validate(f.dir, f.base, f.save(r.doc)), /Changes mismatch/);
});
for (const mutate of ["base", "read-blob", "missing-read", "head-instead-of-base", "unknown-kind"]) test("negative: " + mutate, t => {
  const f = fixture(t); f.write(GUARDS + "00-common.md", "# Updated\n"); const r = f.record([GUARDS + "00-common.md"]);
  if (mutate === "base") r.doc.base_commit = "0".repeat(40);
  if (mutate === "read-blob") r.doc.reads[0].blob = "0".repeat(40);
  if (mutate === "missing-read") r.doc.reads.pop();
  if (mutate === "head-instead-of-base") r.doc.reads[0].ref = "head";
  if (mutate === "unknown-kind") r.doc.verification.kind = "exempt";
  assert.throws(() => validate(f.dir, f.base, f.save(r.doc)));
});
test("normal: new authoring guide can be read from head during installation", t => {const f = fixture(t, true); f.write(GUARDS + "12-guard-authoring.md", "# New authoring guide\n"); const r = f.record([GUARDS + "12-guard-authoring.md"]); assert.equal(validate(f.dir, f.base, r.head).ok, true);});
test("normal: logic with paired executed evidence", t => {const f = fixture(t); f.write("scripts/card-lint.sh", "#!/bin/sh\nexit 1\n"); const r = f.record(["scripts/card-lint.sh"], true); assert.equal(validate(f.dir, f.base, r.head).kind, "logic");});
for (const mutate of ["documentation", "normal", "negative", "exit", "proof-blob", "empty-proof"]) test("negative: incomplete logic proof " + mutate, t => {
  const f = fixture(t); f.write("scripts/card-lint.sh", "#!/bin/sh\nexit 1\n"); const r = f.record(["scripts/card-lint.sh"], true);
  if (mutate === "documentation") r.doc.verification = {kind: "documentation", reason: "not enough"};
  if (["normal", "negative"].includes(mutate)) delete r.doc.verification[mutate];
  if (mutate === "exit") r.doc.verification.negative.actual_exit = 1;
  if (mutate === "proof-blob") r.doc.verification.normal.report_blob = "0".repeat(40);
  if (mutate === "empty-proof") f.write(RECORDS + "proof.txt", "");
  assert.throws(() => validate(f.dir, f.base, f.save(r.doc)));
});
for (const field of ["purpose", "impact", "false_positives", "future_costs", "alternatives", "decision", "rollback", "owner", "normal_example", "violation_example"]) test("negative: missing assessment " + field, t => {
  const f = fixture(t); f.write(GUARDS + "01-read.md", "# Updated\n"); const r = f.record([GUARDS + "01-read.md"]); r.doc.assessment[field] = " "; assert.throws(() => validate(f.dir, f.base, f.save(r.doc)), /Required assessment/);
});
for (const name of ["scripts/check-guard-evaluations.js", "scripts/run-guard-evaluation.js", "scripts/tests/test-guard-evaluations.js", ".github/workflows/guard-authoring-gate.yml"]) test("negative: gate cannot remove itself without evaluation " + name, t => {
  const f = fixture(t); fs.unlinkSync(path.join(f.dir, name)); assert.throws(() => validate(f.dir, f.base, f.commit()), /evaluation JSON/);
});
test("negative: head changed after evaluation", t => {const f = fixture(t); f.write(GUARDS + "01-read.md", "# Updated\n"); f.record([GUARDS + "01-read.md"]); f.write(GUARDS + "01-read.md", "# Updated again\n"); assert.throws(() => validate(f.dir, f.base, f.commit()), /Changes mismatch/);});
test("negative: guarded file cannot become symlink", t => {const f = fixture(t); const file = path.join(f.dir, GUARDS + "01-read.md"); fs.unlinkSync(file); fs.symlinkSync("/etc/passwd", file); const r = f.record([GUARDS + "01-read.md"]); assert.throws(() => validate(f.dir, f.base, r.head), /symlinks/);});
test("normal: literal bracket filename", t => {const f = fixture(t); const name = GUARDS + "guide[1].md"; f.write(name, "# literal\n"); const r = f.record([name]); assert.equal(validate(f.dir, f.base, r.head).ok, true);});
test("negative: malformed JSON", t => {const f = fixture(t); f.write(GUARDS + "01-read.md", "# Updated\n"); f.write(RECORDS + "evaluation.json", "{"); assert.throws(() => validate(f.dir, f.base, f.commit()), SyntaxError);});
function runtimeFixture(overrides = {}) {
  const base = "a".repeat(40), head = "b".repeat(40);
  const pr = {state: "open", base: {ref: "main", sha: base}, head: {sha: head}};
  const calls = [], gitCalls = [];
  let gets = 0;
  const io = {
    request: async (method, route, body) => { calls.push({method, route, body}); if (method === "GET") return structuredClone(++gets === 1 ? pr : (overrides.latest || pr)); return {}; },
    git: args => {gitCalls.push(args); if (args[0] === "rev-parse") return overrides.checkout || base; if (overrides.gitFailure) throw new Error("git failed"); return "";},
    validate: () => { if (overrides.invalid) throw new Error("evaluation missing"); return {ok: true, checked: 1}; },
  };
  return {base, head, pr, calls, gitCalls, io, config: {repo: "shingo-ops/salesanchor", number: 1, runUrl: "https://github.com/shingo-ops/salesanchor/actions/runs/1"}};
}
test("normal: runner publishes success only to inspected head", async () => {
  const f = runtimeFixture(); const r = await runGate(f.config, f.io); assert.equal(r.ok, true);
  assert.deepEqual(f.calls.filter(c => c.method === "POST").map(c => [c.route, c.body.context, c.body.state]), [["/repos/shingo-ops/salesanchor/statuses/" + f.head, CONTEXT, "pending"], ["/repos/shingo-ops/salesanchor/statuses/" + f.head, CONTEXT, "success"]]);
  assert.deepEqual(f.gitCalls, [["rev-parse", "HEAD"], ["fetch", "--no-tags", "origin", f.head], ["merge-base", "--is-ancestor", f.base, f.head]]);
});
for (const kind of ["head", "base", "closed"]) test("negative: runner discards stale " + kind, async () => {
  const f = runtimeFixture(); const latest = structuredClone(f.pr); if (kind === "closed") latest.state = "closed"; else latest[kind].sha = "c".repeat(40);
  let gets = 0; const original = f.io.request; f.io.request = async (m, p, b) => {if (m === "GET" && ++gets === 2) return latest; return original(m, p, b);};
  const r = await runGate(f.config, f.io); assert.equal(r.skipped, "PR-changed-during-evaluation"); assert.deepEqual(f.calls.filter(c => c.method === "POST").map(c => c.body.state), ["pending"]);
});
test("negative: stale trusted checkout cannot publish", async () => {const f = runtimeFixture({checkout: "c".repeat(40)}); const r = await runGate(f.config, f.io); assert.equal(r.skipped, "stale-base-checkout"); assert.equal(f.calls.filter(c => c.method === "POST").length, 0);});
for (const invalid of [true, false]) test("negative: runner reports " + (invalid ? "validation failure" : "fetch error"), async () => {const f = runtimeFixture({invalid, gitFailure: !invalid}); const r = await runGate(f.config, f.io); assert.equal(r.ok, false); assert.equal(r.state, invalid ? "failure" : "error");});
test("negative: API read failure cannot publish success", async () => {const f = runtimeFixture(); const original = f.io.request; let gets = 0; f.io.request = (m, p, b) => {if (m === "GET" && ++gets === 2) throw new Error("API failure"); return original(m, p, b);}; await assert.rejects(runGate(f.config, f.io)); assert.equal(f.calls.some(c => c.body?.state === "success"), false);});
for (const number of [0, -1, "1;exit", 1.5]) test("negative: invalid PR number " + number, async () => {const f = runtimeFixture(); f.config.number = number; await assert.rejects(runGate(f.config, f.io)); assert.equal(f.calls.length, 0);});
test("negative: untrusted SHA is never passed to git", async () => {const f = runtimeFixture(); f.pr.head.sha = "--upload-pack=unsafe"; await assert.rejects(runGate(f.config, f.io)); assert.equal(f.gitCalls.length, 0);});

test("normal: changed mandatory reading still uses its base version", t => {const f = fixture(t); f.write(GUARDS + "00-common.md", "# Changed common\n"); const r = f.record([GUARDS + "00-common.md"]); assert.equal(validate(f.dir, f.base, r.head).ok, true);});
test("negative: proposed validator code is data and cannot execute", t => {const f = fixture(t); const marker = path.join(f.dir, "executed"); f.write("scripts/check-guard-evaluations.js", "require('node:fs').writeFileSync(" + JSON.stringify(marker) + ", 'executed');\n"); assert.throws(() => validate(f.dir, f.base, f.commit()), /evaluation JSON/); assert.equal(fs.existsSync(marker), false);});
for (const state of ["closed", "develop"]) test("normal: runner ignores " + state + " PR", async () => {const f = runtimeFixture(); if (state === "closed") f.pr.state = state; else f.pr.base.ref = state; const r = await runGate(f.config, f.io); assert.equal(r.skipped, "not-open-main-PR"); assert.equal(f.calls.filter(c => c.method === "POST").length, 0);});
test("negative: invalid repository is rejected before API", async () => {const f = runtimeFixture(); f.config.repo = "owner/../../other"; await assert.rejects(runGate(f.config, f.io)); assert.equal(f.calls.length, 0);});
for (const state of ["pending", "success"]) test("negative: failed " + state + " publication never returns success", async () => {const f = runtimeFixture(); const original = f.io.request; f.io.request = (m, p, b) => {if (m === "POST" && b.state === state) throw new Error("API unavailable"); return original(m, p, b);}; await assert.rejects(runGate(f.config, f.io));});

test("normal: shallow trusted checkout can fetch and inspect a head without checkout", async t => {
  const f = fixture(t); f.write(GUARDS + "01-read.md", "# Changed\n"); const record = f.record([GUARDS + "01-read.md"]);
  const area = fs.mkdtempSync(path.join(os.tmpdir(), "guard-eval-clone-")); t.after(() => fs.rmSync(area, {recursive: true, force: true}));
  const bare = path.join(area, "remote.git"), checkout = path.join(area, "checkout");
  execFileSync("git", ["clone", "--bare", "--quiet", f.dir, bare], {stdio: "pipe"}); fs.mkdirSync(checkout);
  const git = args => execFileSync("git", args, {cwd: checkout, encoding: "utf8", stdio: "pipe"}).trim();
  git(["init", "-q"]); git(["remote", "add", "origin", "file://" + bare]); git(["fetch", "--depth=1", "origin", f.base]); git(["checkout", "--detach", "FETCH_HEAD"]);
  const calls = []; const pr = {state: "open", base: {ref: "main", sha: f.base}, head: {sha: record.head}};
  const result = await runGate({repo: "owner/repo", number: 1, runUrl: "https://github.com/owner/repo/actions/runs/1"}, {
    request: async (method, route, body) => {if (method === "GET") return pr; calls.push(body); return {};},
    git, validate: (base, head) => validate(checkout, base, head),
  });
  assert.equal(result.ok, true); assert.equal(git(["rev-parse", "HEAD"]), f.base); assert.deepEqual(calls.map(x => x.state), ["pending", "success"]);
});

test("normal: manifest command emits measured blobs but no invented assessment", t => {
  const f = fixture(t); f.write(GUARDS + "01-read.md", "# Changed\n"); const head = f.commit();
  const output = execFileSync(process.execPath, [require.resolve("../check-guard-evaluations"), "--manifest", f.base, head], {cwd: f.dir, encoding: "utf8"});
  const doc = JSON.parse(output); assert.equal(doc.base_commit, f.base); assert.equal(doc.changes[0].path, GUARDS + "01-read.md"); assert.equal(doc.changes[0].new_blob, f.git("rev-parse", "--verify", head + ":" + GUARDS + "01-read.md"));
  assert.equal(doc.assessment.decision, ""); assert.equal(doc.verification.reason, ""); assert.throws(() => validate(f.dir, f.base, f.save(doc)), /Required assessment/);
});

test("negative: dot repository segments cannot change API routes", async () => {const f = runtimeFixture(); f.config.repo = "../repo"; await assert.rejects(runGate(f.config, f.io)); assert.equal(f.calls.length, 0);});
