#!/usr/bin/env node
/**
 * sop-health-collector.js — SOP ヘルス指標収集 & Prometheus Pushgateway push
 *
 * 収集指標（5 件）:
 *   sop_exempt_pr_total            直近 LOOKBACK_DAYS の免除 PR 件数
 *   sop_dangerous_approved_total   直近 LOOKBACK_DAYS の危険パス変更 PR 件数
 *   sop_emergency_total            sop-followup issues alltime 累計件数
 *   sop_overdue_homework_count     sop-followup open + 期限超過の件数（ゼロ許容）
 *   sop_gate_friction_rate         ゲート失敗→成功を持つ PR 率（0.0–1.0）
 *
 * 環境変数:
 *   GH_TOKEN            GitHub token（必須）
 *   PUSHGATEWAY_URL     Prometheus Pushgateway エンドポイント（必須）
 *   DISCORD_WEBHOOK_URL Discord 通知先（省略時は通知スキップ）
 *   REPO                owner/repo（デフォルト: shingo-ops/salesanchor）
 *   LOOKBACK_DAYS       週次集計対象日数（デフォルト: 7）
 */

'use strict';

const GH_TOKEN = process.env.GH_TOKEN;
const PUSHGATEWAY_URL = process.env.PUSHGATEWAY_URL;
const DISCORD_WEBHOOK_URL = process.env.DISCORD_WEBHOOK_URL;
const REPO = process.env.REPO || 'shingo-ops/salesanchor';
const LOOKBACK_DAYS = parseInt(process.env.LOOKBACK_DAYS || '7', 10);

const API_BASE = 'https://api.github.com';
const HEADERS = {
  Authorization: `Bearer ${GH_TOKEN}`,
  Accept: 'application/vnd.github+json',
  'X-GitHub-Api-Version': '2022-11-28',
};

// ADR-121 と同じ危険パスパターン（check-process-artifacts.js:43-51 と同期）
const DANGEROUS_PATTERNS = [
  /^migrations\//,
  /^\.github\/workflows\/deploy\.yml$/,
  /^scripts\/.*migrat/i,
  /^scripts\/.*deploy/i,
  /^scripts\/aeon-dispatch\.sh$/,
  /^scripts\/run_all_migrations\.sh$/,
  /^scripts\/smoke_test_post_deploy\.sh$/,
];

// 免除マーカー正規表現（check-process-artifacts.js:86 と同期）
const EXEMPT_PATTERN = /- \[x\]\s*免除/i;

function log(msg) {
  process.stdout.write(`[sop-health] ${msg}\n`);
}

/**
 * GitHub API のページネーション対応 GET
 * @param {string} path
 * @param {URLSearchParams} [params]
 * @returns {Promise<Array>}
 */
async function ghGetAll(path, params = new URLSearchParams()) {
  const results = [];
  let page = 1;
  while (true) {
    params.set('page', String(page));
    params.set('per_page', '100');
    const url = `${API_BASE}${path}?${params}`;
    const res = await fetch(url, { headers: HEADERS });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`gh API ${url} → ${res.status}: ${text}`);
    }
    const data = await res.json();
    if (!Array.isArray(data) || data.length === 0) break;
    results.push(...data);
    if (data.length < 100) break;
    page++;
  }
  return results;
}

/**
 * 直近 LOOKBACK_DAYS 日の closed PR を取得
 */
async function fetchRecentClosedPRs() {
  const since = new Date(Date.now() - LOOKBACK_DAYS * 86400 * 1000).toISOString();
  const params = new URLSearchParams({ state: 'closed', sort: 'updated', direction: 'desc' });
  const allPRs = await ghGetAll(`/repos/${REPO}/pulls`, params);
  return allPRs.filter((pr) => {
    if (!pr.merged_at) return false;
    return new Date(pr.merged_at) >= new Date(since);
  });
}

/**
 * PR が危険パスを変更しているか確認
 * @param {number} prNumber
 * @returns {Promise<boolean>}
 */
async function prTouchesDangerousPath(prNumber) {
  const files = await ghGetAll(`/repos/${REPO}/pulls/${prNumber}/files`);
  return files.some((f) => DANGEROUS_PATTERNS.some((p) => p.test(f.filename)));
}

/**
 * 指標1: 免除 PR 件数（週次）
 */
async function countExemptPRs(prs) {
  return prs.filter((pr) => pr.body && EXEMPT_PATTERN.test(pr.body)).length;
}

/**
 * 指標2: 危険パス変更 PR 件数（週次）
 */
async function countDangerousApprovedPRs(prs) {
  let count = 0;
  for (const pr of prs) {
    const isDangerous = await prTouchesDangerousPath(pr.number);
    if (isDangerous) count++;
  }
  return count;
}

/**
 * 指標3: sop-followup issues alltime 累計件数
 * 指標4: 宿題期限超過件数（ゼロ許容）
 */
async function countFollowupIssues() {
  const allIssues = await ghGetAll(`/repos/${REPO}/issues`, new URLSearchParams({
    labels: 'sop-followup',
    state: 'all',
  }));

  const total = allIssues.length;
  const todayS = Math.floor(Date.now() / 1000);

  let overdue = 0;
  const overdueList = [];
  for (const issue of allIssues) {
    if (issue.state !== 'open') continue;
    const deadlineMatch = issue.title.match(/宿題期限:\s*(\d{4}-\d{2}-\d{2})/);
    if (!deadlineMatch) continue;
    const deadlineS = Math.floor(new Date(deadlineMatch[1]).getTime() / 1000);
    if (todayS >= deadlineS) {
      overdue++;
      overdueList.push(`#${issue.number} ${issue.title}`);
    }
  }

  return { total, overdue, overdueList };
}

/**
 * 指標5: ゲート摩擦率（週次）
 * process-artifacts-gate.yml で failure run を持つ PR 数 / 全 closed PR 数
 */
async function calcGateFrictionRate(prs) {
  if (prs.length === 0) return 0;

  const workflowRuns = await ghGetAll(
    `/repos/${REPO}/actions/runs`,
    new URLSearchParams({
      workflow_id: 'process-artifacts-gate.yml',
      per_page: '100',
    }),
  );

  // 失敗 run と紐づく PR 番号を収集
  const failedPRNums = new Set();
  for (const run of workflowRuns) {
    if (run.conclusion !== 'failure') continue;
    for (const pr of run.pull_requests || []) {
      failedPRNums.add(pr.number);
    }
  }

  const prNums = new Set(prs.map((p) => p.number));
  let frictionCount = 0;
  for (const n of failedPRNums) {
    if (prNums.has(n)) frictionCount++;
  }

  return frictionCount / prs.length;
}

/**
 * Prometheus テキスト形式にシリアライズ
 */
function buildMetricsText(metrics) {
  const label = `repo="${REPO}"`;
  return [
    `# HELP sop_exempt_pr_total 直近 ${LOOKBACK_DAYS} 日の免除 PR 件数`,
    '# TYPE sop_exempt_pr_total gauge',
    `sop_exempt_pr_total{${label}} ${metrics.exemptPRs}`,
    '',
    `# HELP sop_dangerous_approved_total 直近 ${LOOKBACK_DAYS} 日の危険パス変更 PR 件数`,
    '# TYPE sop_dangerous_approved_total gauge',
    `sop_dangerous_approved_total{${label}} ${metrics.dangerousPRs}`,
    '',
    '# HELP sop_emergency_total sop-followup issues alltime 累計件数',
    '# TYPE sop_emergency_total gauge',
    `sop_emergency_total{${label}} ${metrics.emergencyTotal}`,
    '',
    '# HELP sop_overdue_homework_count 宿題期限超過の sop-followup open issues 件数',
    '# TYPE sop_overdue_homework_count gauge',
    `sop_overdue_homework_count{${label}} ${metrics.overdueCount}`,
    '',
    `# HELP sop_gate_friction_rate 直近 ${LOOKBACK_DAYS} 日のゲート摩擦率 (0.0–1.0)`,
    '# TYPE sop_gate_friction_rate gauge',
    `sop_gate_friction_rate{${label}} ${metrics.frictionRate.toFixed(4)}`,
    '',
  ].join('\n');
}

/**
 * Prometheus Pushgateway へ push
 */
async function pushToGateway(metricsText) {
  const url = `${PUSHGATEWAY_URL}/metrics/job/sop-health-reporter/instance/${REPO.replace('/', '_')}`;
  log(`Pushing to ${url}`);
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'text/plain' },
    body: metricsText,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Pushgateway ${res.status}: ${body}`);
  }
  log('Push 成功');
}

/**
 * Discord へ通知
 */
async function notifyDiscord(message) {
  if (!DISCORD_WEBHOOK_URL) {
    log('DISCORD_WEBHOOK_URL 未設定 — 通知スキップ');
    return;
  }
  const res = await fetch(DISCORD_WEBHOOK_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content: message }),
  });
  if (!res.ok) {
    log(`Discord 通知失敗: ${res.status}`);
  }
}

async function main() {
  if (!GH_TOKEN) throw new Error('GH_TOKEN が未設定です');
  if (!PUSHGATEWAY_URL) throw new Error('PUSHGATEWAY_URL が未設定です');

  log(`収集開始: repo=${REPO}, lookback=${LOOKBACK_DAYS}d`);

  log('直近 closed PR を取得中...');
  const recentPRs = await fetchRecentClosedPRs();
  log(`対象 PR: ${recentPRs.length} 件`);

  log('指標1: 免除 PR 件数を集計中...');
  const exemptPRs = await countExemptPRs(recentPRs);
  log(`  → sop_exempt_pr_total = ${exemptPRs}`);

  log('指標2: 危険パス変更 PR 件数を集計中...');
  const dangerousPRs = await countDangerousApprovedPRs(recentPRs);
  log(`  → sop_dangerous_approved_total = ${dangerousPRs}`);

  log('指標3&4: sop-followup issues を集計中...');
  const { total: emergencyTotal, overdue: overdueCount, overdueList } = await countFollowupIssues();
  log(`  → sop_emergency_total = ${emergencyTotal}`);
  log(`  → sop_overdue_homework_count = ${overdueCount}`);

  log('指標5: ゲート摩擦率を計算中...');
  const frictionRate = await calcGateFrictionRate(recentPRs);
  log(`  → sop_gate_friction_rate = ${frictionRate.toFixed(4)}`);

  const metrics = { exemptPRs, dangerousPRs, emergencyTotal, overdueCount, frictionRate };
  const metricsText = buildMetricsText(metrics);

  log('Pushgateway へ push 中...');
  await pushToGateway(metricsText);

  // ゼロ許容チェック
  if (overdueCount > 0) {
    log(`⚠️  ゼロ許容アラート: 宿題期限超過 ${overdueCount} 件`);
    const overdueLines = overdueList.map((l) => `- ${l}`).join('\n');
    const msg = [
      `⚠️ **SOP 宿題の期限切れが ${overdueCount} 件あります**（sop-health-reporter 週次チェック）`,
      overdueLines,
      '',
      'recon.md + 設計 doc を揃えて後追い PR を作成してください。',
    ].join('\n');
    await notifyDiscord(msg);
  } else {
    log('✅ ゼロ許容: 異常なし');
  }

  log('収集完了');
  process.stdout.write(JSON.stringify({ ...metrics, frictionRate: parseFloat(frictionRate.toFixed(4)) }, null, 2) + '\n');
}

main().catch((err) => {
  process.stderr.write(`[sop-health] ERROR: ${err.message}\n`);
  process.exit(1);
});
