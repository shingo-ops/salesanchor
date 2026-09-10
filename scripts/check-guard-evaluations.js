"use strict";
const {execFileSync} = require("node:child_process");
const THEME = "docs/handoff/design-partner-card-ops/";
const RECORDS = THEME + "guard-evaluations/";
const OWN_PATHS = new Set([
  "scripts/check-guard-evaluations.js", "scripts/run-guard-evaluation.js",
  "scripts/tests/test-guard-evaluations.js", ".github/workflows/guard-authoring-gate.yml",
  THEME + "guard-authoring-design.md", THEME + "guard-authoring-recon.md",
]);
const SHA = /^[0-9a-f]{40}$/;
function requireThat(condition, message) { if (!condition) throw new Error(message); }
function git(repo, args) {
  return execFileSync("git", ["--literal-pathspecs", ...args], {cwd: repo, encoding: "utf8", maxBuffer: 16 * 1024 * 1024});
}
function managed(path) {
  return OWN_PATHS.has(path) || path === THEME + "guards.md" ||
    path.startsWith(THEME + "guards/") || path === "scripts/card-lint.sh" ||
    path.startsWith("scripts/tests/card-lint/");
}
function entry(repo, revision, path) {
  const raw = git(repo, ["ls-tree", "-z", revision, "--", path]);
  if (!raw) return null;
  const rows = raw.split("\0").filter(Boolean);
  requireThat(rows.length === 1, "Expected one file at " + path);
  const tab = rows[0].indexOf("\t");
  requireThat(rows[0].slice(tab + 1) === path, "Path mismatch");
  const [mode, type, blob] = rows[0].slice(0, tab).split(" ");
  return {mode, type, blob};
}
function contents(repo, revision, path) {
  const e = entry(repo, revision, path);
  requireThat(e && e.type === "blob" && ["100644", "100755"].includes(e.mode), "Regular file required: " + path);
  const data = git(repo, ["cat-file", "blob", e.blob]);
  requireThat(Buffer.byteLength(data) <= 1024 * 1024, "Evaluation input exceeds 1 MiB");
  return data;
}
function changes(repo, base, head) {
  requireThat(SHA.test(base) && SHA.test(head), "Full commit SHA required");
  return git(repo, ["diff", "--no-renames", "--name-only", "-z", base, head])
    .split("\0").filter(Boolean).sort();
}
function reads(repo, base, head, paths) {
  const names = new Set([THEME + "guards.md", ...["00-common", "11-lint", "12-guard-authoring"].map(n => THEME + "guards/" + n + ".md")]);
  for (const path of paths) if (path.startsWith(THEME + "guards/") && path.endsWith(".md")) names.add(path);
  return [...names].sort().flatMap(path => {
    const old = entry(repo, base, path), current = old || entry(repo, head, path);
    requireThat(current, "Required reading missing: " + path);
    requireThat(current.type === "blob" && ["100644", "100755"].includes(current.mode), "Reading must be a regular file");
    return [{path, ref: old ? "base" : "head", blob: current.blob}];
  });
}
function nonempty(value, field) {
  requireThat(typeof value === "string" && value.trim().length > 0 &&
    !/^(TBD|TODO|未記入|\.\.\.)$/i.test(value.trim()), "Required assessment: " + field);
}
function sameRecords(actual, expected, keys, label) {
  requireThat(Array.isArray(actual) && actual.length === expected.length, label + " count mismatch");
  const ordered = [...actual].sort((a, b) => String(a?.path).localeCompare(String(b?.path), "en"));
  const wanted = [...expected].sort((a, b) => a.path.localeCompare(b.path, "en"));
  for (let i = 0; i < wanted.length; i++) {
    requireThat(ordered[i] && typeof ordered[i] === "object", label + " record required");
    for (const key of keys) requireThat(ordered[i][key] === wanted[i][key], label + " mismatch: " + key);
  }
}
function proof(repo, head, value, name) {
  requireThat(value && typeof value === "object", "Missing " + name + " verification");
  nonempty(value.command, name + " command");
  requireThat(Number.isInteger(value.expected_exit) && value.expected_exit >= 0 && value.expected_exit <= 255 &&
    value.actual_exit === value.expected_exit, name + " exit mismatch");
  requireThat(typeof value.report_path === "string" && value.report_path.startsWith(RECORDS) &&
    /^[-a-zA-Z0-9_./]+$/.test(value.report_path) && !value.report_path.split("/").includes("..") &&
    /\.(txt|log|md)$/.test(value.report_path), "Invalid proof report path");
  const data = contents(repo, head, value.report_path);
  requireThat(data.trim().length > 0 && !data.includes("\0"), "Empty/binary proof report");
  requireThat(entry(repo, head, value.report_path).blob === value.report_blob, "Proof blob mismatch");
}
function manifest(repo, base, head) {
  const paths = changes(repo, base, head).filter(managed);
  const expected = paths.map(path => {
    const old = entry(repo, base, path), next = entry(repo, head, path);
    requireThat(!next || (next.type === "blob" && ["100644", "100755"].includes(next.mode)), "Managed files cannot become symlinks/submodules");
    return {path, old_blob: old?.blob ?? null, new_blob: next?.blob ?? null};
  });
  const assessment = Object.fromEntries(["purpose", "impact", "false_positives", "future_costs", "alternatives", "decision", "rollback", "owner", "normal_example", "violation_example"].map(k => [k, ""]));
  return {version: 1, base_commit: base, changes: expected,
    reads: paths.length ? reads(repo, base, head, paths) : [], assessment,
    verification: paths.some(p => !p.startsWith("docs/")) ? {kind: "logic", normal: null, negative: null} : {kind: "documentation", reason: ""}};
}
function validate(repo, base, head) {
  const all = changes(repo, base, head), paths = all.filter(managed);
  if (!paths.length) return {ok: true, kind: "outside-scope", checked: 0};
  const candidates = all.filter(p => p.startsWith(RECORDS) && /^[-a-zA-Z0-9_]+\.json$/.test(p.slice(RECORDS.length)) && entry(repo, head, p));
  requireThat(candidates.length === 1, "Exactly one changed evaluation JSON required");
  const document = JSON.parse(contents(repo, head, candidates[0]));
  requireThat(document.version === 1 && document.base_commit === base, "Evaluation version/base mismatch");
  const expected = manifest(repo, base, head).changes;
  sameRecords(document.changes, expected, ["path", "old_blob", "new_blob"], "Changes");
  sameRecords(document.reads, reads(repo, base, head, paths), ["path", "ref", "blob"], "Reading");
  for (const field of ["purpose", "impact", "false_positives", "future_costs", "alternatives", "decision", "rollback", "owner", "normal_example", "violation_example"])
    nonempty(document.assessment?.[field], field);
  const verification = document.verification;
  requireThat(verification && typeof verification === "object", "Verification required");
  const logic = paths.some(p => !p.startsWith("docs/"));
  if (logic || verification.kind === "logic") {
    requireThat(verification.kind === "logic", "Logic changes need executed examples");
    proof(repo, head, verification.normal, "normal");
    proof(repo, head, verification.negative, "negative");
  } else {
    requireThat(verification.kind === "documentation", "Unknown verification kind");
    nonempty(verification.reason, "documentation reason");
  }
  return {ok: true, kind: logic ? "logic" : "documentation", checked: paths.length, evaluation: candidates[0]};
}
module.exports = {manifest, validate, changes, entry, reads, managed, THEME, RECORDS};
if (require.main === module) {
  try {
    const result = process.argv[2] === "--manifest" ? manifest(process.cwd(), process.argv[3], process.argv[4]) : validate(process.cwd(), process.argv[2], process.argv[3]);
    console.log(JSON.stringify(result, null, 2));
  }
  catch (error) { console.error(error.message); process.exitCode = 1; }
}
