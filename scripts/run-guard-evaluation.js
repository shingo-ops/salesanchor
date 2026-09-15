"use strict";
const {execFileSync} = require("node:child_process");
const {readFileSync} = require("node:fs");
const {validate} = require("./check-guard-evaluations");
const CONTEXT = "guard-authoring/evaluation";
const SHA = /^[0-9a-f]{40}$/;
async function runGate(config, io) {
  if (!/^[a-zA-Z0-9][a-zA-Z0-9_.-]*\/[a-zA-Z0-9][a-zA-Z0-9_.-]*$/.test(config.repo) || !Number.isSafeInteger(config.number) || config.number <= 0)
    throw new Error("Invalid repository/PR number");
  const endpoint = "/repos/" + config.repo;
  const route = endpoint + "/pulls/" + config.number;
  const pr = await io.request("GET", route);
  if (pr.state !== "open" || pr.base?.ref !== "main") return {ok: true, skipped: "not-open-main-PR"};
  const base = pr.base.sha, head = pr.head?.sha;
  if (!SHA.test(base) || !SHA.test(head)) throw new Error("Invalid PR commit SHA");
  const trusted = io.git(["rev-parse", "HEAD"]).trim();
  if (trusted !== base) return {ok: true, skipped: "stale-base-checkout"};
  const publish = (state, description) => io.request("POST", endpoint + "/statuses/" + head, {
    state, context: CONTEXT, description, target_url: config.runUrl,
  });
  await publish("pending", "Checking guard evaluation against trusted main");
  let state = "error", detail = "Guard evaluation could not complete", result;
  try {
    io.git(["fetch", "--no-tags", "origin", head]);
    io.git(["merge-base", "--is-ancestor", base, head]);
    try {
      result = io.validate(base, head);
      if (!result || result.ok !== true) throw new Error("Validator did not return success");
      state = "success"; detail = "Guard evaluation matches reviewed files and evidence";
    } catch (error) {
      state = "failure"; detail = "Guard evaluation missing or inconsistent";
      result = {error: String(error.message)};
    }
  } catch (error) {
    state = "error";
  }
  const latest = await io.request("GET", route);
  if (latest.state !== "open" || latest.base?.ref !== "main" || latest.base.sha !== base || latest.head?.sha !== head)
    return {ok: true, skipped: "PR-changed-during-evaluation", head, base};
  await publish(state, detail);
  return {ok: state === "success", state, head, base, result};
}
function runtime(env = process.env) {
  if (!env.GITHUB_TOKEN || !env.GITHUB_EVENT_PATH || env.GITHUB_API_URL !== "https://api.github.com")
    throw new Error("Required GitHub runtime configuration missing");
  if (env.GITHUB_EVENT_NAME !== "pull_request_target") throw new Error("Trusted pull_request_target runtime required");
  const event = JSON.parse(readFileSync(env.GITHUB_EVENT_PATH, "utf8"));
  const number = event.number;
  const repo = env.GITHUB_REPOSITORY;
  const request = async (method, path, body) => {
    const response = await fetch(env.GITHUB_API_URL + path, {
      method,
      headers: {
        Authorization: "Bearer " + env.GITHUB_TOKEN,
        Accept: "application/vnd.github+json",
        "X-GitHub-Api-Version": "2026-03-10",
        "Content-Type": "application/json",
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: AbortSignal.timeout(30000),
    });
    if (!response.ok) throw new Error("GitHub request failed: HTTP " + response.status);
    return response.json();
  };
  const repoDir = process.cwd();
  return runGate({repo, number, runUrl: "https://github.com/" + repo + "/actions/runs/" + env.GITHUB_RUN_ID}, {
    request,
    git: args => execFileSync("git", args, {cwd: repoDir, encoding: "utf8", timeout: 60000, stdio: ["ignore", "pipe", "pipe"]}),
    validate: (base, head) => validate(repoDir, base, head),
  });
}
module.exports = {runGate, runtime, CONTEXT};
if (require.main === module) runtime().then(result => {
  console.log(JSON.stringify(result));
  if (!result.ok) process.exitCode = 1;
}).catch(() => {
  console.error("Guard evaluation runtime failed; inspect the target commit status"); process.exitCode = 1;
});
