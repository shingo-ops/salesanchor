# AT Sol2 final cross-review

**Verdict: APPROVE**

Read-only review scope: Sol2-owned six product files / seven targets and the two new suites. No Sol2 file was edited by this reviewer.

## Product boundary

- Formal inverse audit reports 6/6 files and 7/7 targets byte-equal after reversing only the prescribed Button migration.
- Full AT audit separately reports all 9 files inverse-equal, target count 11, outside legacy 221 and shared 18 unchanged, with zero syntax errors.
- The seven Sol2 nodes retain `type`, external `form`, disabled expressions, children and parent handlers exactly; only tag/class-to-variant/size and required imports changed.

## Contract suites

- `AccountCompanySaveButtonMigration.test.tsx` SHA-256 `9abc58b873eddd070a70709fbef73f869e4635447c98b66556ed784d42f734b9`.
  - Profile uses the real `UiPrefsProvider` and real `patchMyProfile`, enumerates the seven-key PATCH payload, proves pending duplicate suppression, failure retention, identical retry, and exactly one success refresh.
  - Company Basic enumerates the 14-key normalized PATCH, native required/dirty/permission guards, pending duplicate suppression, exact company/contact reload increments and returned-state reset. Failure retry now explicitly compares the second call with the captured first payload.
  - Channels enumerates normalized separators, preserves failure input/no early reload, explicitly compares retry payload, proves pending duplicate suppression, both reload increments, reset and denied-permission hiding.
- `AdminMasterSaveButtonMigration.test.tsx` SHA-256 `a22340c8a1cd3e22441268a98fd66e56640bda42201b18f3c23147ae649312a8`.
  - PO covers distinct supplier/item guards, exact two-item payload, pending Save/Cancel inertness, ordered success callbacks, failure retention, identical retry, and now awaits `created` then `closed` for retry success.
  - Dex covers pokemon and trainer schemas/URLs, failure retention/retry and exact reload. The deliberately unlocked pending case dispatches twice, settles both, now proves exact GET `+2` and editor closure.
  - TCG covers type/series required guards, normalized full create/update payloads, exact reload/reset, failure retention and the existing unlocked double-dispatch semantics with both promises settled and GET `+2`.
- No `skip`, `todo`, or `only` marker was found. API is mocked and global fetch rejects unexpected network calls.

## Validation evidence read

- `/tmp/at-sol2-validation/13-unit-cross-review-fixes.log`: 2 files, 14 tests passed.
- `/tmp/at-sol2-validation/14-eslint-cross-review-fixes.log`: empty; owner reports exit 0.
- `/tmp/at-sol2-validation/08-inverse-audit.log`: 6/6 files, 7/7 targets.
- `/tmp/at-sol2-validation/09-diff-check.log`: empty; owner reports exit 0.
- Preserved initial failure log reports 4 failed / 6 passed before fixture correction.

The four preliminary review gaps—Company Basic retry equality, Channels retry equality, PO retry success callbacks, and Dex double-success completion—are resolved in the final hashes. No remaining acceptance gap or false-positive path was found within Sol2 scope.
