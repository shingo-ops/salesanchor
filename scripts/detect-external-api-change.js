#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const DEFAULT_BASE = process.env.BASE_SHA || 'origin/develop';
const DEFAULT_HEAD = process.env.HEAD_SHA || 'HEAD';

const IGNORED_PATH_PREFIXES = [
  '.github/workflows/',
  'backend/tests/',
  'frontend/tests/',
  'frontend/tests-e2e/',
  'scripts/smoke/',
  'scripts/tests/',
  'docs/',
  'tests/',
];

const IGNORED_FILE_NAMES = new Set([
  'recon.md',
  'design.md',
  'design-b-ssh-isolation.md',
  'design-inc1.md',
  'design-inc4.md',
  'detect-external-api-change.js',
  'test-detect-external-api-change.js',
]);

const API_RULES = [
  {
    api: 'paypal',
    patterns: [
      /paypal_payments/i,
      /paypal[_-]/i,
      /paypal\.com/i,
      /\/v[12]\/invoicing\//i,
      /oauth2\/token/i,
      /recipient_view_url/i,
    ],
  },
  {
    api: 'fedex',
    patterns: [
      /\bfedex\b/i,
      /apis-sandbox\.fedex\.com/i,
      /apis\.fedex\.com/i,
      /\/rate\/v1\/rates\/quotes/i,
      /\/ship\/v1\/shipments/i,
      /fedex_(rates|ship|etd)/i,
    ],
  },
  {
    api: 'dhl',
    patterns: [
      /\bdhl\b/i,
      /express\.api\.dhl\.com/i,
      /mydhlapi/i,
    ],
  },
  {
    api: 'ups',
    patterns: [
      /\bups\b/i,
      /onlinetools\.ups\.com/i,
      /wwwcie\.ups\.com/i,
    ],
  },
  {
    api: 'meta',
    patterns: [
      /meta_graph/i,
      /graph\.facebook\.com/i,
      /facebook\.com\/v\d+\/dialog\/oauth/i,
      /tenant_meta_config/i,
      /subscribed_apps/i,
      /instagram_business_account/i,
      /instagram:/i,
    ],
  },
  {
    api: 'firebase',
    patterns: [
      /firebase_admin/i,
      /firebase_auth/i,
      /identitytoolkit/i,
      /GOOGLE_APPLICATION_CREDENTIALS/,
    ],
  },
  {
    api: 'discord',
    patterns: [
      /discord\.com\/api/i,
      /DISCORD_BOT_TOKEN/i,
      /ADMIN_NOTIFICATION_DISCORD_WEBHOOK/i,
      /send_discord_notification/i,
      /send_discord_dm/i,
      /discord_role_sync/i,
      /discord_gateway/i,
      /discord_rest/i,
      /discord_sender/i,
      /discord_notifier/i,
      /import\s+discord\b/i,
      /from\s+discord\b/i,
      /discord_user_id/i,
      /discord_dm_channel_id/i,
      /discord_guild_channel_id/i,
      /discord_role_sync_status/i,
      /discord_role_sync_at/i,
      /platform\s*==\s*["']discord["']/i,
      /pattern=.*discord/i,
    ],
  },
  {
    api: 'google_drive',
    patterns: [
      /google_drive_oauth/i,
      /GOOGLE_DRIVE_CLIENT_ID/i,
      /GOOGLE_DRIVE_CLIENT_SECRET/i,
      /GOOGLE_DRIVE_REDIRECT_URI/i,
      /drive\.file/i,
      /drive\.google/i,
      /google-drive/i,
    ],
  },
  {
    api: 'google_calendar',
    patterns: [
      /GOOGLE_CALENDAR_CLIENT_ID/i,
      /GOOGLE_CALENDAR_CLIENT_SECRET/i,
      /GOOGLE_CALENDAR_REDIRECT_URI/i,
      /calendar\.google/i,
      /tenant_google_calendar_config/i,
      /google_cal_oauth_state:/i,
      /https:\/\/www\.googleapis\.com\/auth\/calendar/i,
    ],
  },
  {
    api: 'google_ai',
    patterns: [
      /google\.generativeai/i,
      /google-generativeai/i,
    ],
  },
  {
    api: 'pokeapi',
    patterns: [
      /pokeapi/i,
      /pokeapi\.co/i,
    ],
  },
  {
    api: 'fx_rate',
    patterns: [
      /open\.er-api\.com/i,
      /ExchangeRate-API/i,
      /FX_RATE_API_KEY/i,
      /\bfx_rate\b/i,
    ],
  },
];

function normalizePath(filePath) {
  return filePath.replace(/\\/g, '/');
}

function shouldIgnorePath(filePath) {
  const normalized = normalizePath(filePath);
  if (!normalized || normalized.startsWith('.git/')) {
    return true;
  }
  if (IGNORED_FILE_NAMES.has(path.basename(normalized))) {
    return true;
  }
  return IGNORED_PATH_PREFIXES.some((prefix) => normalized.startsWith(prefix));
}

function extractChangedLines(diffText) {
  const lines = diffText.split(/\r?\n/);
  const changed = [];
  for (const line of lines) {
    if (!line || line.startsWith('+++') || line.startsWith('---')) {
      continue;
    }
    if (line.startsWith('+') || line.startsWith('-')) {
      const content = line.slice(1);
      if (content.startsWith('@')) {
        continue;
      }
      changed.push(content);
    }
  }
  return changed;
}

function matchApisInLine(line) {
  const matched = [];
  for (const rule of API_RULES) {
    if (rule.patterns.some((pattern) => pattern.test(line))) {
      matched.push(rule.api);
    }
  }
  return matched;
}

function scanLines(lines) {
  const matchedApis = new Map();
  const evidence = [];

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();
    if (!line) {
      continue;
    }
    const apis = matchApisInLine(line);
    if (!apis.length) {
      continue;
    }
    evidence.push({ line, apis });
    for (const api of apis) {
      if (!matchedApis.has(api)) {
        matchedApis.set(api, []);
      }
      matchedApis.get(api).push(line);
    }
  }

  return {
    hasExternalChange: matchedApis.size > 0,
    detectedApis: [...matchedApis.keys()].sort(),
    matchedApis: Object.fromEntries([...matchedApis.entries()].sort(([a], [b]) => a.localeCompare(b))),
    evidence,
  };
}

function classifySourceText(text) {
  return scanLines(text.split(/\r?\n/));
}

function classifyDiffText(diffText) {
  return scanLines(extractChangedLines(diffText));
}

function runGit(args) {
  return execFileSync('git', args, { encoding: 'utf8' });
}

function listChangedFiles(baseRef, headRef) {
  const output = runGit([
    'diff',
    '--name-only',
    '--diff-filter=ACMR',
    `${baseRef}...${headRef}`,
  ]);
  return output.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
}

function analyzeRepositoryDiff({ baseRef = DEFAULT_BASE, headRef = DEFAULT_HEAD } = {}) {
  const changedFiles = listChangedFiles(baseRef, headRef);
  const files = [];
  const apis = new Map();

  for (const filePath of changedFiles) {
    if (shouldIgnorePath(filePath)) {
      continue;
    }

    let diffText = '';
    try {
      diffText = runGit([
        'diff',
        '--unified=0',
        '--no-color',
        `${baseRef}...${headRef}`,
        '--',
        filePath,
      ]);
    } catch (error) {
      diffText = '';
    }

    const scan = classifyDiffText(diffText);
    if (!scan.hasExternalChange) {
      continue;
    }

    files.push({
      path: normalizePath(filePath),
      detectedApis: scan.detectedApis,
      evidence: scan.evidence,
    });

    for (const api of scan.detectedApis) {
      if (!apis.has(api)) {
        apis.set(api, []);
      }
      apis.get(api).push(normalizePath(filePath));
    }
  }

  const detectedApis = [...apis.keys()].sort();
  return {
    baseRef,
    headRef,
    changedFiles,
    analyzedFiles: files.map((file) => file.path),
    files,
    detectedApis,
    apiToFiles: Object.fromEntries([...apis.entries()].sort(([a], [b]) => a.localeCompare(b))),
    hasExternalChange: detectedApis.length > 0,
    paypalDetected: detectedApis.includes('paypal'),
    unpreparedApis: detectedApis.filter((api) => api !== 'paypal'),
  };
}

function writeGitHubOutputs(report) {
  const outputPath = process.env.GITHUB_OUTPUT;
  if (!outputPath) {
    return;
  }
  const lines = [
    `has_external=${report.hasExternalChange ? 'true' : 'false'}`,
    `paypal_detected=${report.paypalDetected ? 'true' : 'false'}`,
    `detected_apis=${report.detectedApis.join(',')}`,
    `unprepared_apis=${report.unpreparedApis.join(',')}`,
    `analyzed_files=${report.analyzedFiles.join(',')}`,
  ];
  fs.appendFileSync(outputPath, `${lines.join('\n')}\n`);
}

function parseArgs(argv) {
  const result = {
    baseRef: DEFAULT_BASE,
    headRef: DEFAULT_HEAD,
    json: false,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--base' && argv[i + 1]) {
      result.baseRef = argv[i + 1];
      i += 1;
      continue;
    }
    if (arg === '--head' && argv[i + 1]) {
      result.headRef = argv[i + 1];
      i += 1;
      continue;
    }
    if (arg === '--json') {
      result.json = true;
      continue;
    }
    if (arg === '--help' || arg === '-h') {
      result.help = true;
      continue;
    }
  }
  return result;
}

function printUsage() {
  process.stdout.write([
    'Usage: node scripts/detect-external-api-change.js [--base SHA] [--head SHA] [--json]',
    '',
    'Outputs a JSON report and writes GitHub Action outputs when GITHUB_OUTPUT is set.',
  ].join('\n'));
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    printUsage();
    return 0;
  }

  const report = analyzeRepositoryDiff(args);
  writeGitHubOutputs(report);

  if (args.json) {
    process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
  } else if (!report.hasExternalChange) {
    process.stdout.write('No external API changes detected.\n');
  } else {
    process.stdout.write('External API changes detected:\n');
    for (const api of report.detectedApis) {
      const files = report.apiToFiles[api] || [];
      process.stdout.write(`- ${api}: ${files.join(', ')}\n`);
    }
    if (report.unpreparedApis.length > 0) {
      process.stdout.write(`未整備スモーク: ${report.unpreparedApis.join(', ')}\n`);
    }
  }

  return 0;
}

if (require.main === module) {
  try {
    process.exitCode = main();
  } catch (error) {
    console.error(error.stack || error.message || String(error));
    process.exitCode = 1;
  }
}

module.exports = {
  API_RULES,
  analyzeRepositoryDiff,
  classifyDiffText,
  classifySourceText,
  extractChangedLines,
  matchApisInLine,
  normalizePath,
  shouldIgnorePath,
  scanLines,
};
