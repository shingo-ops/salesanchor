# Design: schedule settings, bin 3b (personal defaults: first view, week start, event length, Meet, whose events to show)

- Status: design draft (written by Opus). Review runs on the cloud, and the result is recorded in §12 "Review".
- Parent: `docs/handoff/schedule-settings/design.md` §7 (bin 3 skeleton). Requirements: `docs/handoff/schedule-settings/requirements.md` (PO approved 2026-11-25 "1", G4–G7). This bin is **G7** and the row 「開いたときの形」「新しい予定の初期値」 of the requirements table.
- Depends on bin 3a (`design-bin3a.md`), which changes `calendar_owner_settings` to `staff_id, color_key, updated_at`. **Implementation starts only after bin 3a is merged to main**; the branch is then rebuilt from the new origin/main.
- Line numbers below are from origin/main 314eeef1e unless marked "after 3a".

## 0 What this bin does and does not do

Does:
- Each person can set, for themselves only: the first view (day / 3 days / week / month / list), the first day of the week (Sunday / Monday), the length of a new event (15 / 30 / 45 / 60 / 90 / 120 minutes), whether Meet is added to new events, and whose events are shown when the schedule opens (only me / everyone / one team).
- The schedule screen opens with those values. Today they are fixed (recon §7).
- The settings page and the gear button open for every logged-in user. The personal section is visible to everyone; the admin sections keep their current conditions.

Does not:
- Change any company-wide setting, category, color or sharing rule.
- Change the secretary chat. It still uses 1 hour when no end is given (`backend/app/routers/assistant.py:391`). Recorded as a follow-up in §6.
- Change the time grid slot size (`CalendarView.tsx:253`, 1 hour) or the snap (15 minutes).

## 1 Current state (actual code)

| # | Fact | Where |
|---|---|---|
| F1 | First view is fixed to week | `frontend/src/pages/schedule/SchedulePageImpl.tsx:881` `useState<ScheduleView>("week")`; views are day/threeDay/week/month/list (`schedule-utils.ts:4`) |
| F2 | Week start is fixed to Sunday | `SchedulePageImpl.tsx:1636` `weekStart={0}`; the component default is Monday (`frontend/src/components/CalendarView.tsx:68`); the prop type is `0 \| 1` (`frontend/src/components/calendarView.utils.ts:74`) |
| F3 | Whose events are shown at open is fixed to "me" | `SchedulePageImpl.tsx:970` and the effect at `:986-990` |
| F4 | New event length is fixed to 1 hour, in 2 places | button / month cell: `SchedulePageImpl.tsx:1008` `addHours(start, 1)`; a click (≤15 min) in the time grid becomes 1 hour in `calendarView.utils.ts:254-265` `normalizeSelectedRange` (`MS_PER_HOUR`) |
| F5 | Meet starts off on every new event | `SchedulePageImpl.tsx:1019` and `:1271` `addMeet: false`; Meet is only sent when `meetAvailable` (`:1072`), which is true only for the person who connected Google (`:876-879`) |
| F6 | The gear shows only for `staff.view` or tenant admin | `SchedulePageImpl.tsx:1538` |
| F7 | The settings page refuses everyone else | `frontend/src/pages/schedule/ScheduleSettingsPage.tsx:306-314` |
| F8 | One per-person calendar row already exists: `calendar_owner_settings`, key `staff_id` = `public.users.id` (FK) | `backend/app/services/tenant.py:1649-1659`; after 3a its columns are `staff_id, color_key, updated_at` |
| F9 | Team membership is `team_members(team_id, user_id)`; active teams are `teams.is_active IS TRUE` | `tenant.py:530-548`; `/calendar/teams` returns only id and name, no members (`backend/app/routers/calendar.py:282-293`) |
| F10 | The owners list returns everyone only with `staff.view`; otherwise only me | `calendar.py:384-443`; the picker shows others only with `canManageOthers` (`SchedulePageImpl.tsx:629`) |
| F11 | Other per-person UI settings live in `staff_ui_preferences` (key `staff.id`, dark mode and menus) | `tenant.py:638-648`; written through `PUT /staff/{id}` (`backend/app/routers/staff.py:574-610`) |

## 2 Acceptance criteria

| # | Criterion | How to check |
|---|---|---|
| B1 | Saving each of the 5 values and reopening the schedule shows that view, that week start, that length on a new event, Meet on or off, and those people checked | Front-end test per value (render with mocked `/calendar/preferences`), and PO visual check in production (§11) |
| B2 | A person with no saved row gets today's behavior: week, Sunday, 60 minutes, Meet off, only me | Back-end test: GET with no row returns exactly these 5 defaults; front-end test with that response matches today's snapshot assertions |
| B3 | A person can only read and write their own row | Back-end test: GET/PUT use `current_user.id` only; the body has no user field; a real PostgreSQL test shows that PUT by user A leaves user B's row unchanged |
| B4 | Saving preferences does not change the color, and saving a color does not change preferences | Real PostgreSQL test: PUT preferences, then PATCH owner color, then read both back |
| B5 | Out-of-range values are refused | API: building `CalendarPreferences(...)` with view `year`, week_start 2, length 50, `open_owners` `x` raises pydantic `ValidationError` (FastAPI turns this into 422; a handler-level test does not run the body check, so the test checks the model directly); DB CHECKs refuse the same values (real PostgreSQL test) |
| B6 | "One team" with a team that is inactive or deleted falls back to "only me"; a team list that arrives after the owners still applies "one team" | Front-end tests: (a) team not in `/calendar/teams` → only me; (b) `/calendar/teams` resolves after owners and preferences → the team's people are checked, not only me; (c) permissions still loading → nothing is applied until they load. DB: `ON DELETE SET NULL` checked in the real PostgreSQL test; API: PUT with an inactive or unknown team id → 422 `invalid_team` |
| B7 | Everyone can open the gear and the settings page; the admin sections keep their conditions | Front-end tests: a user with no `staff.view` and not admin sees the gear, the page, and only the personal section (no Meet row, because the Google status is read only for admins today) |
| B8 | Meet default is applied only when Meet is available | Front-end test: `auto_meet: true` and `meet_available: false` → new draft has `addMeet: false`; with `meet_available: true` → `true` |
| B9 | No hard-coded UI text; tokens and components only | i18n check, UI governance gate (ADR-144), Lint & Dark Mode Check (ADR-067) |

## 3 Back-end changes

### 3-1 Where the values live (decision)

Add 6 columns to the existing per-person calendar row `calendar_owner_settings` (F8) instead of a new table:

| column | type | default | CHECK name / rule |
|---|---|---|---|
| `default_view` | `text NOT NULL` | `'week'` | `calendar_owner_settings_default_view_check`: `IN ('day','threeDay','week','month','list')` |
| `week_start` | `smallint NOT NULL` | `0` | `calendar_owner_settings_week_start_check`: `IN (0,1)` |
| `event_minutes` | `smallint NOT NULL` | `60` | `calendar_owner_settings_event_minutes_check`: `IN (15,30,45,60,90,120)` |
| `auto_meet` | `boolean NOT NULL` | `false` | — |
| `open_owners` | `text NOT NULL` | `'self'` | `calendar_owner_settings_open_owners_check`: `IN ('self','all','team')` |
| `open_team_id` | `integer NULL` | `NULL` | FK `fk_calendar_owner_settings_open_team` → `{schema}.teams(id) ON DELETE SET NULL` |

Why (the parent skeleton said a new table `calendar_user_preferences`; this design changes that):
- The row is already "one per person, for the calendar", keyed by `public.users.id`. A second per-person calendar table would split one person's calendar settings into two places.
- No value is copied: each value is stored once, in this row.
- Fewer new objects (no new table, RLS, AI-view table entry, template block), so less risk.
- The writers are separate by column: color is written by `PATCH /calendar/owners/{user_id}` (staff.view), preferences by `PUT /calendar/preferences` (self only). Each UPSERT updates only its own columns (B4).

Not in `staff_ui_preferences` (F11): it is keyed by `staff.id` (not `users.id` like every calendar table, ADR-1008), and it is written through the staff edit API, which needs staff permissions.

No CHECK ties `open_owners='team'` to a non-null `open_team_id`: `ON DELETE SET NULL` would then fail when a team is deleted. The screen treats `team` with a null or inactive team as `self` (B6).

### 3-2 Migration `migrations/20261129_100000_owner_settings_preferences.sql`

- Same form as the bin 3a migration (`20261128_100000_owner_color_key_drop_dead_columns.sql`): one `DO` block, the tenant loop on one line `FOR schema_rec IN SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_\d+$' LOOP`, skip a tenant without `calendar_owner_settings` or `teams`.
- Per tenant: `ALTER TABLE %I.calendar_owner_settings ADD COLUMN IF NOT EXISTS …` for each column with its default; add each CHECK and the FK only if no constraint of that name exists (`pg_constraint` by `conname` and `conrelid`).
- Final check in the same loop: all 6 columns exist with the types above and the 4 CHECKs and the FK exist; otherwise `RAISE EXCEPTION` (the whole block rolls back).
- Runs twice with no change.
- Register exactly where bin 3a registered its migration (the implementer reads the 3a commit for the exact lines):
  - `scripts/run_all_migrations.sh`: a `run_sql` line after the 3a line.
  - `backend/tests/rls_bootstrap.py`: the migration-count map (near `:190`), count 1.
  - `backend/tests/test_calendar_sync_tenant_reset_pg.py`: the `_MIGRATIONS` tuple (near `:56`), `True`.
  - `backend/tests/test_tenant_loop_migration_guard.py`: `_REVIEWED` is one dict keyed by test file name. Add the migration name to the `rls_bootstrap.py` set (near `:53`) and the `test_calendar_sync_tenant_reset_pg.py` set (near `:74`), and add one new key `test_calendar_owner_preferences_pg.py` as `scoped` with this migration.
- Template `backend/app/services/tenant.py` (the `calendar_owner_settings` block, after 3a): add the 6 columns and the 4 CHECKs inline, and the FK, and name this migration in the comment above the block (as 3a did). The template shape check (`scripts/check_tenant_template_shape.py`) must pass.

### 3-3 API (`backend/app/routers/calendar.py`)

- `GET /calendar/preferences` → `CalendarPreferences` (all 6 fields). Reads `calendar_owner_settings WHERE staff_id = :uid` with `uid = current_user.id`. No row → the defaults of §3-1. Any logged-in user.
- `PUT /calendar/preferences` body `CalendarPreferences`:
  - `default_view: Literal["day","threeDay","week","month","list"]`, `week_start: Literal[0,1]`, `event_minutes: Literal[15,30,45,60,90,120]`, `auto_meet: bool`, `open_owners: Literal["self","all","team"]`, `open_team_id: int | None`.
  - If `open_owners == "team"`: `open_team_id` must be an active team (`SELECT 1 FROM teams WHERE id = :id AND is_active IS TRUE`), else 422 `invalid_team`. If not `team`, store `open_team_id = NULL`.
  - `INSERT … (staff_id, <6 columns>) VALUES (:uid, …) ON CONFLICT (staff_id) DO UPDATE SET <6 columns>, updated_at = now()` — the color column is not in the SET list (B4).
  - After the write: `await db.commit()` then `reset_tenant_context(...)` (ADR-072), the same form as the 3a PATCH.
  - Returns the saved values.
- `PATCH /calendar/owners/{user_id}` (after 3a): its UPSERT must not touch the 6 columns. The implementer checks the 3a SQL; a new row inserted by it gets the column defaults.
- `GET /calendar/owners`: add `team_ids: list[int]` to `OwnerRosterItem` — the ids of **active** teams the person belongs to (`team_members` join `teams` on `is_active IS TRUE`, ordered by id). Read from the tables each time; no copy (F9).
- Error reason `invalid_team` (a new name; do not confuse it with the existing `invalid_team_ids`): add `invalid_team: "apiError.invalidTeam"` to `frontend/src/lib/apiErrorReason.ts` (after `invalid_team_ids` at `:39`), add `"invalid_team"` to the list in `backend/tests/test_api_error_reason_sync.py` (after `:70`), and add `apiError.invalidTeam` to ja/en.
- Contract file `frontend/api-contract/openapi.json`: regenerate with `cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json` (same as bin 3a); the diff is the 2 new paths, the new schema, and `team_ids`.

### 3-4 AI copy classification

- In `migrations/20261024_100300_create_ai_cloud_views.sql`, add one row per new column for `calendar_owner_settings`, following the existing row form and Japanese reasons:
  - `default_view`, `week_start`, `event_minutes`, `auto_meet`, `open_owners` → `allow` (fixed value lists by CHECK).
  - `open_team_id` → `allow` (a team number in the same company).
- Update the count in `backend/tests/ops/test_ai_cloud_views.py` (after 3a it is 1169 → **1175**) and the count comment at line 3 of the SQL.
- Put the new `sha256sum` of the SQL into `scripts/migration-guard/reference-allowlist.tsv` and add `/ schedule-settings 便3b（個人の初期値）` to the reason.
- Add the 6 rows to `docs/handoff/cloud-case-ai/stage1-column-class.tsv`.

## 4 Screen changes

### 4-1 Preferences hook: new `frontend/src/features/schedule/useCalendarPreferences.ts`

- `useApiQuery<ApiCalendarPreferences>("/calendar/preferences")`.
- Exports `DEFAULT_CALENDAR_PREFERENCES` (the same 5 defaults as §3-1; the only place on the screen side) and `normalizePreferences(raw)` which returns the defaults for any missing or unknown value.

### 4-2 `SchedulePageImpl.tsx`

- First view (F1): keep `useState("week")`; when preferences are loaded the first time and the person has not changed the view yet, `setView(prefs.default_view)` (a ref keeps it to once; a second ref is set when the person changes the view by hand).
- Week start (F2): `weekStart={prefs.week_start}`.
- Whose events (F3): read `loading: permsLoading` from `usePermissions()` at `:874` (today it is not read). Apply the saved choice to `visibleOwnerIds` once, only when all of these have loaded: permissions (`!permsLoading`), owners, preferences, and, when `open_owners` is `team`, `/calendar/teams` (the existing `useCalendarTeams()` at `:338`). Before that, do nothing (the screen stays at "only me", today's behavior). If the person changed the people selection by hand before that moment, do not apply (a "touched by hand" ref, set in the selection handler, the same idea as the view). The rule:
  - `self` → `[selfKey]` (today's behavior)
  - `all` → every owner's key, only if `canManageOwners`; otherwise `[selfKey]`
  - `team` → keys of owners whose `team_ids` contain `open_team_id`, plus self; only if `canManageOwners` and the team is in `/calendar/teams`; otherwise `[selfKey]`
  - The existing effect at `:986-990` keeps working for the "nothing chosen" case.
- New event length (F4): there is no `addMinutes` today (only the private `addHours(date, amount)` at `:186`). Add a private `addMinutes(date, amount)` next to it and use `addMinutes(start, prefs.event_minutes)` in `openCreate` instead of `addHours(start, 1)`. `CalendarView` gets a new optional prop `clickMinutes` (default 60, so other users of the component do not change), passed to `normalizeSelectedRange(start, end, allDay, clickMinutes)`.
- Meet (F5): `addMeet: meetAvailable && prefs.auto_meet` in `openCreate` and `openCreateRange`. `meetAvailable` comes from `/google-calendar/status`, which is read only for admins (`:877` `enabled: isTenantAdmin`); this bin does not change that read, so today only admins can get Meet on by default. Widening it is a separate bin.
- Gear (F6): always shown.

### 4-3 `ScheduleSettingsPage.tsx`

- Remove the refusal at `:306-314`; every logged-in user gets the page. If the refusal text key `settingsPermissionRequired` is then unused anywhere (`git grep`), remove it from ja and en; if it is still used, keep it.
- Add `"personal"` to `SectionKey` (`:91`), put it first in `menuItems` (`:316-323`), and make it the initial section (`:129` `useState<SectionKey>("personal")`), because a non-admin has no `google` section.
- Team list: change `:145` `useCalendarTeams({ enabled: isTenantAdmin === true })` to `useCalendarTeams()` (the back end at `calendar.py:282-293` lets any logged-in user read it), so a `staff.view` non-admin gets the team choices.
- Add a section `personal` with `SectionCard`, title `schedule.prefsTitle`, using only molds already imported at `:4-13`:
  - First view: `SelectControl` (`components/Select.tsx`) with the 5 views (existing view labels).
  - Week start: `SelectControl`, Sunday / Monday.
  - Event length: `SelectControl`, 6 options.
  - Meet: `Toggle` (`components/Toggle.tsx`), shown only when `meet_available` is true. `/google-calendar/status` keeps its admin-only read (`:120-122`); this bin does not change it. When the row is hidden, the PUT sends the loaded `auto_meet` value unchanged (never drops or resets it).
  - Whose events: `SelectControl`, 3 options; "everyone" and "one team" shown only with `staff.view` (after `!permsLoading`); "one team" shows a `SelectControl` of teams from `/calendar/teams`.
  - One Save button → `api.put("/calendar/preferences", body)` → `await` `useInvalidateApi()(["calendar","preferences"])` (`frontend/src/lib/query/apiQuery.ts:105`; it refetches the active query so the cache holds the new values before the success text shows) → success text; failure text on error.
- Admin sections and the people-color sections keep their current conditions (`isTenantAdmin`, `ownersEnabled`).
- Only existing molds (`components/`); no raw `select`/`input`, no color literals (ADR-144, ADR-067).

### 4-4 New text (ja / en, same keys)

Under `schedule`: `prefsTitle`, `prefsFirstView`, `prefsWeekStart`, `prefsWeekStartSunday`, `prefsWeekStartMonday`, `prefsEventMinutes`, `prefsMinutesValue` (`{{count}}分` / `{{count}} min`), `prefsAutoMeet`, `prefsOpenOwners`, `prefsOpenSelf`, `prefsOpenAll`, `prefsOpenTeam`, `prefsTeam`, `prefsSave`, `prefsSaved`, `prefsSaveError`. Under `apiError`: `invalidTeam` (§3-3). The implementer reuses existing keys where the same words exist (view names, save) and lists any reuse in the report.

## 5 Tests

- Back end:
  - `backend/tests/test_calendar_preferences_api.py` (new, handler level with mocked db): defaults with no row; PUT stores and returns; B5 by building `CalendarPreferences(...)` and expecting `ValidationError`; `team` with inactive id → `HTTPException` 422 `invalid_team`; non-team clears `open_team_id`; the SQL uses `current_user.id`; `reset_tenant_context` is called after commit.
  - `backend/tests/test_calendar_owner_preferences_pg.py` (new, real PostgreSQL): migration twice on an old-shape table (the 3a-shape table built by dropping the 6 columns), defaults filled for existing rows, CHECKs refuse bad values, FK `SET NULL` on team delete, B3 (A's PUT leaves B), B4 (color and preferences independent). Unique tenant number: 978, 979, 981 and 989 are used today; the implementer runs `git grep -n "^_TENANT = " backend/tests` and picks an unused one. `_ensure_public_users` first. Add to `_REVIEWED` as `scoped` (§3-2).
  - Owners: `team_ids` contains only active teams.
- Front end:
  - `SchedulePageImpl.test.tsx`: B1 per value, B2 defaults, B6 (a)(b)(c), B8 Meet, gear for a plain user (B7).
  - `ScheduleSettingsPage.test.tsx`: plain user sees only the personal section and it is the first section shown; saving sends the PUT body (with the loaded `auto_meet` when the Meet row is hidden); Meet toggle hidden without `meet_available`; "everyone"/"team" hidden without `staff.view`; a `staff.view` non-admin gets the team choices.
  - `frontend/src/components/CalendarView.test.tsx` (existing file, where `normalizeSelectedRange` is already exercised): with `clickMinutes` 30 a click makes 30 minutes; without the prop it stays 60.

## 6 Out of scope

- Secretary chat event length (`assistant.py:391`). Follow-up: use the person's `event_minutes` there too (separate small bin, needs its own design).
- Time zone, slot size, working hours.
- Any company-wide default (the PO chose per person).

## 7 Alternatives

| Option | Why it is not taken |
|---|---|
| New table `calendar_user_preferences` (parent skeleton) | Splits one person's calendar settings into two rows in two tables; more objects to secure and classify |
| Columns in `staff_ui_preferences` | Keyed by `staff.id`, unlike the calendar tables (`users.id`); written through the staff API that needs staff permission |
| Browser storage | Not shared across devices; not one source of truth |
| A CHECK that `team` needs a team id | Team delete would fail because of `ON DELETE SET NULL`; the screen fallback is simpler |

## 8 Risks and mitigations

| Risk | Mitigation |
|---|---|
| The view flickers from week to the saved view on first load | Applied once per opening when the query resolves. The query cache (`staleTime` 0, `apiQuery.ts:5`) shows the last saved values first on later opens, and the save step refetches before showing success (§4-3), so the cache is not old after a save. A short flicker on the very first open is accepted |
| "One team" or "everyone" is decided before permissions or the team list load | Applied only after all inputs load (§4-2); B6 (b)(c) tests |
| A plain user saved "everyone" before losing `staff.view` | The screen falls back to "only me" when `canManageOwners` is false (§4-2) |
| Bin 3a and 3b both change the same table | 3b starts only after 3a is in main; its migration runs after 3a's in `run_all_migrations.sh` |
| The PATCH color UPSERT overwrites preferences | B4 real PostgreSQL test |

## 9 External and past examples

- Google Calendar puts week start, default view and default event length in each person's own settings (recon §10; from search summaries, page dates not confirmed, so not numeric evidence).
- Past precedents: migration form bin 3a / 2b; per-person row `calendar_owner_settings`.

## 10 How this is kept in place

- CI: real PostgreSQL tests (§5), `api-contract-check`, migration-guard sha256, `test_ai_cloud_views.py` count, `_REVIEWED`, template shape check, i18n check, UI governance gate, Lint & Dark Mode Check.
- Owner of the design: Opus (the design role).

## 11 PO visual check in production

- Open the settings page from the gear, change the first view to month, week start to Monday, length to 30 minutes, save, go back to the schedule and reload: month view, Monday first, a new event is 30 minutes.

## 12 Review

- Round 1 (cloud architect, `review-architect-bin3b-1.md` on branch `release/schedule-settings-bin3b-review1`, against 69967ed10): REVISE. 2 must-fix (R1, R2) and 10 light (L1–L10).
  - Opus checked the main claims against `origin/main` before applying: `usePermissions.ts:27` `loading`; `SchedulePageImpl.tsx:874` does not read `loading`, `:877` reads Google status only for admins, `:186` has only `addHours`; `ScheduleSettingsPage.tsx:91,129,145`; `apiErrorReason.ts:39`; `test_api_error_reason_sync.py:70`; `frontend/api-contract/openapi.json` exists; tenant numbers 978/979/981/989 in use. All match the review.
  - Applied: R1 → §4-2 "Whose events" waits for permissions, owners, preferences and (for team) the team list, and does not override a hand change; B6 gets (b)(c). R2 → §4-3 reads the team list for every user; Meet stays admin-only (stated in §4-2, §4-3, B7) and the PUT keeps the loaded `auto_meet`. L1 molds `SelectControl`/`Toggle`; L2 contract path and command; L3 `apiError.invalidTeam` in both lists; L4 commit then `reset_tenant_context`; L5 B5 checks the model; L6 registration places; L7 `addMinutes` is new; L8 test goes into `CalendarView.test.tsx`; L9 `personal` section key and first position, unused key removal; L10 refetch after save.
