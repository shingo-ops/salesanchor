#!/usr/bin/env node
'use strict';

const { existsSync, readFileSync } = require('fs');
const { execSync } = require('child_process');
const { join } = require('path');

const repoRoot = process.env.CONDITION_VOCAB_SCAN_ROOT
  || execSync('git rev-parse --show-toplevel', { encoding: 'utf8' }).trim();

const CODE_FILES = [
  'backend/app/services/inventory_parser.py',
  'backend/app/services/inventory_parser_llm.py',
  'frontend/src/pages/super-admin/ParseReviewPage.tsx',
];

const JSON_FILES = [
  'frontend/src/locales/ja.json',
  'frontend/src/locales/en.json',
];

const CODE_RULES = [
  { label: 'legacy parser token shrink_yes', pattern: /(["'])shrink_yes\1/ },
  { label: 'legacy parser token shrink_no', pattern: /(["'])shrink_no\1/ },
  { label: 'legacy parser token state_a_minus', pattern: /(["'])state_a_minus\1/ },
  { label: 'legacy parser token state_a', pattern: /(["'])state_a\1/ },
  { label: 'legacy parser token state_b', pattern: /(["'])state_b\1/ },
  { label: 'legacy parser token damaged', pattern: /(["'])damaged\1/ },
  { label: 'duplicate review conditionOptions block', pattern: /superAdmin\.inbound\.review\.conditionOptions/ },
];

function readChangedFiles() {
  if (process.env.CHANGED_FILES) {
    return process.env.CHANGED_FILES.split('\n').filter(Boolean);
  }
  try {
    const base = process.env.BASE_SHA || 'origin/develop';
    const head = process.env.HEAD_SHA || 'HEAD';
    return execSync(`git diff --name-only "${base}" "${head}"`, { encoding: 'utf8' })
      .trim()
      .split('\n')
      .filter(Boolean);
  } catch {
    return [...CODE_FILES, ...JSON_FILES];
  }
}

function parseJsonFile(file) {
  const fullPath = join(repoRoot, file);
  if (!existsSync(fullPath)) return null;
  return JSON.parse(readFileSync(fullPath, 'utf8'));
}

function checkLocaleJson(file) {
  const errors = [];
  const data = parseJsonFile(file);
  if (!data) return errors;

  const review = data?.superAdmin?.inbound?.review ?? {};
  const condition = review.condition ?? {};
  for (const key of ['new', 'usedA', 'opened']) {
    if (Object.prototype.hasOwnProperty.call(condition, key)) {
      errors.push(`❌ ${file}: legacy review condition key "${key}"`);
    }
  }

  if (Object.prototype.hasOwnProperty.call(review, 'conditionOptions')) {
    errors.push(`❌ ${file}: duplicate review conditionOptions block`);
  }

  const setLabel = review.unitOptions?.set;
  if (typeof setLabel === 'string' && /\/\s*バルク|\/\s*Bulk/i.test(setLabel)) {
    errors.push(`❌ ${file}: set label still mixed with bulk (${JSON.stringify(setLabel)})`);
  }

  return errors;
}

function checkCodeFile(file) {
  const errors = [];
  const fullPath = join(repoRoot, file);
  if (!existsSync(fullPath)) return errors;
  const content = readFileSync(fullPath, 'utf8');
  for (const rule of CODE_RULES) {
    if (rule.pattern.test(content)) {
      errors.push(`❌ ${file}: ${rule.label}`);
    }
  }
  return errors;
}

function main() {
  const changed = new Set(readChangedFiles());
  const files = [...CODE_FILES, ...JSON_FILES].filter(
    (file) => changed.size === 0 || changed.has(file) || [...changed].some((p) => p.endsWith(file))
  );

  const errors = [];
  for (const file of files) {
    if (CODE_FILES.includes(file)) {
      errors.push(...checkCodeFile(file));
    } else if (JSON_FILES.includes(file)) {
      errors.push(...checkLocaleJson(file));
    }
  }

  if (errors.length > 0) {
    console.error('');
    console.error('❌ CONDITION VOCAB GATE FAILED');
    console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    for (const error of errors) console.error(error);
    console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    process.exit(1);
  }

  console.log('✅ condition vocab gate PASSED');
}

main();
