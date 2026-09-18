# Recon: PR artifact parser parenthesis recognition

## Current Issue

PR #3556 has the following in the 「削除するファイル」section:

```
削除するファイル:
- migrations/20260906_120000_create_tcg_tables_t001.sql (22行削除)
```

The CI check script expects to parse this as a single file path: `migrations/20260906_120000_create_tcg_tables_t001.sql`.

### Root Cause

**File**: `scripts/check-process-artifacts.js:224`

**Current regex**:
```javascript
.replace(/（[^）]*）/g, '')  // Only matches full-width （）
```

**Issue**: The comment text `(22行削除)` uses half-width parentheses `()`, which are not matched by the full-width pattern. Result: the parsed file name includes the comment: `migrations/20260906_120000_create_tcg_tables_t001.sql (22行削除)`.

## Related Files

- `scripts/check-process-artifacts.js` (line 224)
  - Used by CI workflow to validate PR bodies against commit diffs
  - Called as part of `.github/workflows/check-artifacts.yml`
  - Enforces consistency between declared files and actual git changes

## PR Convention

PR body format recommendation:
- English files: use half-width `(22行削除)`
- Supports both full-width and half-width for flexibility and internationalization

## Verification Method

Test the regex with both styles:
```javascript
const testCases = [
  '- file.sql (22行削除)',      // half-width
  '- file.sql （22行削除）',     // full-width
];

testCases.forEach(tc => {
  const result = tc
    .replace(/^[-*]\s*/, '')
    .replace(/[（(][^）)]*[）)]/g, '')
    .trim();
  console.log(result);  // Should output: file.sql
});
```
