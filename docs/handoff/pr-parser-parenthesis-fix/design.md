# Design: PR artifact parser parenthesis support

## Objective

Support both full-width and half-width parentheses in PR body comment text without breaking file path parsing.

## Root Cause (from recon.md)

Regex at `scripts/check-process-artifacts.js:224` only matches full-width parentheses `（）`.

## Solution

Update the character class to match both:

**Before**:
```javascript
.replace(/（[^）]*）/g, '')
```

**After**:
```javascript
.replace(/[（(][^）)]*[）)]/g, '')
```

This pattern:
- `[（(]` - Match either full-width `（` or half-width `(`
- `[^）)]` - Match any character except closing bracket (full or half)
- `[）)]` - Match either full-width `）` or half-width `)`

## Verification Criteria

| Input | Expected Output | Status |
|-------|-----------------|--------|
| `file.sql (22行削除)` | `file.sql` | ✓ PASS |
| `file.sql （22行削除）` | `file.sql` | ✓ PASS |
| `file.sql` | `file.sql` | ✓ PASS (no comment) |

## Impact

### Positive
- PR #3556 CI checks will now pass
- Future PRs using half-width parentheses in file comments will be recognized correctly
- Supports internationalized documentation patterns

### Neutral
- No behavioral change for existing PRs using full-width parentheses
- No external API changes
- No database changes

### Testing
- Unit test: manual JavaScript execution confirms both patterns are parsed correctly
- Integration test: Next PR submission with half-width parentheses will validate

## External References

None. This is a localized regex pattern improvement in CI infrastructure.

## Rollback Plan

If issues arise, revert to single-bracket pattern: `/（[^）]*）/g`

## Measurement

Success = PR #3556 and similar PRs with half-width parentheses in file comments pass CI checks without modification.
