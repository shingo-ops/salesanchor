#!/usr/bin/env node
'use strict';

const assert = require('assert');
const { execSync } = require('child_process');
const { readFileSync } = require('fs');
const { join } = require('path');

const repoRoot = execSync('git rev-parse --show-toplevel', { encoding: 'utf8' }).trim();
const SCRIPT = join(repoRoot, 'scripts/detect-external-api-change.js');

const {
  analyzeRepositoryDiff,
  classifyDiffText,
  classifySourceText,
  shouldIgnorePath,
} = require(SCRIPT);

let passed = 0;
let failed = 0;

function test(name, fn) {
  try {
    fn();
    console.log(`  ✅ ${name}`);
    passed += 1;
  } catch (error) {
    console.error(`  ❌ ${name}`);
    console.error(`     ${error.message}`);
    failed += 1;
  }
}

function readRepoFile(relativePath) {
  return readFileSync(join(repoRoot, relativePath), 'utf8');
}

function expectClassified(relativePath, expectedApis) {
  const content = readRepoFile(relativePath);
  const report = classifySourceText(content);
  assert.deepStrictEqual(
    report.detectedApis,
    [...expectedApis].sort(),
    `${relativePath} detectedApis mismatch`,
  );
  assert.ok(report.hasExternalChange, `${relativePath} should be detected as external change`);
}

console.log('\n=== detect-external-api-change テスト ===\n');

test('無関係ファイルは ignore 対象', () => {
  assert.ok(shouldIgnorePath('docs/handoff/incident-paypal-invoicing-false-complete/design.md'));
  assert.ok(shouldIgnorePath('.github/workflows/external-api-smoke.yml'));
  assert.ok(shouldIgnorePath('backend/tests/sandbox/test_paypal_sandbox.py'));
  assert.ok(shouldIgnorePath('frontend/tests-e2e/example.spec.ts'));
  assert.ok(shouldIgnorePath('scripts/detect-external-api-change.js'));
  assert.ok(shouldIgnorePath('scripts/tests/test-detect-external-api-change.js'));
  assert.ok(!shouldIgnorePath('frontend/src/components/Tabs.tsx'));
});

test('diff から PayPal を検出', () => {
  const diff = [
    '@@ -0,0 +1,3 @@',
    '+import httpx',
    '+base_url = "https://api-m.sandbox.paypal.com"',
    '+resp = httpx.post(f"{base_url}/v1/oauth2/token")',
  ].join('\n');
  const report = classifyDiffText(diff);
  assert.ok(report.detectedApis.includes('paypal'));
});

test('diff から Discord を検出', () => {
  const diff = [
    '@@ -0,0 +1,3 @@',
    '+import httpx',
    '+url = "https://discord.com/api/v10/channels/123/messages"',
    '+token = os.environ["DISCORD_BOT_TOKEN_1"]',
  ].join('\n');
  const report = classifyDiffText(diff);
  assert.ok(report.detectedApis.includes('discord'));
});

test('既知の PayPal 呼び出しファイルを検出', () => {
  const cases = [
    ['backend/app/services/paypal_payments.py', ['paypal']],
    ['backend/app/routers/integrations.py', ['dhl', 'fedex', 'google_drive', 'paypal', 'ups']],
    ['backend/app/routers/invoices.py', ['fx_rate', 'paypal']],
  ];
  assert.strictEqual(cases.length, 3);
  for (const [filePath, expectedApis] of cases) {
    expectClassified(filePath, expectedApis);
  }
});

test('既知の FedEx 呼び出しファイルを検出', () => {
  const cases = [
    ['backend/app/services/carrier_credentials.py', ['dhl', 'fedex', 'ups']],
    ['backend/app/services/fedex_rates.py', ['fedex']],
    ['backend/app/services/fedex_ship.py', ['fedex']],
    ['backend/app/routers/shipping.py', ['dhl', 'fedex', 'google_drive', 'ups']],
  ];
  assert.strictEqual(cases.length, 4);
  for (const [filePath, expectedApis] of cases) {
    expectClassified(filePath, expectedApis);
  }
});

test('既知の Meta 呼び出しファイルを検出', () => {
  const cases = [
    ['backend/app/services/meta_graph.py', ['meta']],
    ['backend/app/routers/meta_inbox.py', ['discord', 'meta']],
    ['backend/app/routers/webhook.py', ['discord', 'meta']],
    ['backend/app/routers/leads.py', ['discord', 'meta']],
    ['backend/app/tasks/refresh_meta_tokens.py', ['meta']],
    ['backend/app/tasks/verify_meta_subscriptions.py', ['meta']],
    ['backend/app/tasks/avatar.py', ['meta']],
    ['backend/app/tasks/sa02_recon_monitor.py', ['discord']],
  ];
  assert.strictEqual(cases.length, 8);
  for (const [filePath, expectedApis] of cases) {
    expectClassified(filePath, expectedApis);
  }
});

test('既知の Firebase 呼び出しファイルを検出', () => {
  const cases = [
    ['backend/app/auth/dependencies.py', ['firebase']],
    ['backend/app/auth/utils.py', ['firebase']],
  ];
  assert.strictEqual(cases.length, 2);
  for (const [filePath, expectedApis] of cases) {
    expectClassified(filePath, expectedApis);
  }
});

test('既知の Discord 呼び出しファイルを検出', () => {
  const cases = [
    ['backend/app/services/discord_rest.py', ['discord']],
    ['backend/app/services/discord_sender.py', ['discord']],
    ['backend/app/services/discord_notifier.py', ['discord']],
    ['backend/app/routers/discord_announcement.py', ['discord']],
    ['backend/app/routers/discord_remove.py', ['discord']],
    ['backend/app/routers/discord_channel_invite.py', ['discord']],
    ['backend/app/routers/discord_role_resync.py', ['discord']],
    ['backend/app/discord_gateway/client.py', ['discord']],
    ['backend/app/discord_gateway/ticket_channel_creator.py', ['discord']],
    ['backend/app/discord_gateway/ticket_channel_writer.py', ['discord']],
  ];
  assert.strictEqual(cases.length, 10);
  for (const [filePath, expectedApis] of cases) {
    expectClassified(filePath, expectedApis);
  }
});

test('既知のその他APIファイルを検出', () => {
  const cases = [
    ['backend/app/services/pokeapi_dex.py', ['pokeapi']],
    ['backend/app/services/google_calendar.py', ['google_calendar']],
    ['backend/app/services/google_drive_oauth.py', ['google_drive']],
    ['backend/app/services/fx_rate.py', ['fx_rate']],
  ];
  assert.strictEqual(cases.length, 4);
  for (const [filePath, expectedApis] of cases) {
    expectClassified(filePath, expectedApis);
  }
});

test('無関係な UI ファイルは検出されない', () => {
  const content = readRepoFile('frontend/src/components/Tabs.tsx');
  const report = classifySourceText(content);
  assert.strictEqual(report.hasExternalChange, false);
  assert.deepStrictEqual(report.detectedApis, []);
});

test('repository diff helper は現在ブランチ差分が空なら空レポートを返す', () => {
  const report = analyzeRepositoryDiff({ baseRef: 'HEAD', headRef: 'HEAD' });
  assert.strictEqual(report.hasExternalChange, false);
  assert.deepStrictEqual(report.detectedApis, []);
});

test('recon 既知ファイル 31 件をすべて個別検出する', () => {
  const cases = [
    ['backend/app/services/paypal_payments.py', ['paypal']],
    ['backend/app/routers/integrations.py', ['dhl', 'fedex', 'google_drive', 'paypal', 'ups']],
    ['backend/app/routers/invoices.py', ['fx_rate', 'paypal']],
    ['backend/app/services/carrier_credentials.py', ['dhl', 'fedex', 'ups']],
    ['backend/app/services/fedex_rates.py', ['fedex']],
    ['backend/app/services/fedex_ship.py', ['fedex']],
    ['backend/app/routers/shipping.py', ['dhl', 'fedex', 'google_drive', 'ups']],
    ['backend/app/services/meta_graph.py', ['meta']],
    ['backend/app/routers/meta_inbox.py', ['discord', 'meta']],
    ['backend/app/routers/webhook.py', ['discord', 'meta']],
    ['backend/app/routers/leads.py', ['discord', 'meta']],
    ['backend/app/tasks/refresh_meta_tokens.py', ['meta']],
    ['backend/app/tasks/verify_meta_subscriptions.py', ['meta']],
    ['backend/app/tasks/avatar.py', ['meta']],
    ['backend/app/tasks/sa02_recon_monitor.py', ['discord']],
    ['backend/app/auth/dependencies.py', ['firebase']],
    ['backend/app/auth/utils.py', ['firebase']],
    ['backend/app/services/discord_rest.py', ['discord']],
    ['backend/app/services/discord_sender.py', ['discord']],
    ['backend/app/services/discord_notifier.py', ['discord']],
    ['backend/app/routers/discord_announcement.py', ['discord']],
    ['backend/app/routers/discord_remove.py', ['discord']],
    ['backend/app/routers/discord_channel_invite.py', ['discord']],
    ['backend/app/routers/discord_role_resync.py', ['discord']],
    ['backend/app/discord_gateway/client.py', ['discord']],
    ['backend/app/discord_gateway/ticket_channel_creator.py', ['discord']],
    ['backend/app/discord_gateway/ticket_channel_writer.py', ['discord']],
    ['backend/app/services/pokeapi_dex.py', ['pokeapi']],
    ['backend/app/services/google_calendar.py', ['google_calendar']],
    ['backend/app/services/google_drive_oauth.py', ['google_drive']],
    ['backend/app/services/fx_rate.py', ['fx_rate']],
  ];

  assert.strictEqual(cases.length, 31);
  for (const [filePath, expectedApis] of cases) {
    expectClassified(filePath, expectedApis);
  }
});

console.log(`\n✅ ${passed} passed / ${failed} failed\n`);
process.exitCode = failed === 0 ? 0 : 1;
