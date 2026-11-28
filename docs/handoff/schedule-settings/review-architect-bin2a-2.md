# 審査報告 便2a 設計（第2回）

本報告は design-bin2a.md 第2版（4415dadd9）の設計審査である。

- 審査役: クラウドの Architect（コードは直さない）。審査日 2026-11-25
- 対象: `docs/handoff/schedule-settings/design-bin2a.md` 第2版（枝 `release/schedule-settings-bin2a`）。作業場所で `git log -1 --oneline` が `4415dadd9` を確認し、`git rev-parse HEAD` と `origin/release/schedule-settings-bin2a` が同じ `4415dadd9a51ba4a1415a54072dcc68f68b72c2a` であることも確認した
- 前回: `review-architect-bin2a-1.md`（REVISE・必須 R1〜R7・推奨 S1〜S8）
- 実物の基準: 設計の基準 `b4940fe2e` と、いまの `origin/main`（`9dc912ade`）の間で、設計が触るファイル群（`calendar_service.py`・`routers/calendar.py`・`tenant.py`・`frontend/src/pages/schedule`・`frontend/src/features/schedule`・`migrations`・`run_all_migrations.sh`）の差は 0（`git diff --stat b4940fe2e origin/main -- <それらのファイル>` が空）。下の行番号は、この作業場所（`4415dadd9`）の実物
- 本番の値（F3・F9）と本番で読む手段は、この審査では本番を読んでいないため「未確認」と書く

## 1 前回の指摘 R1〜R7・S1〜S8 が入ったか

### 必須 R1〜R7（すべて ○）

| # | ○× | 第2版の場所 | 実物の行で確かめたこと |
|---|---|---|---|
| R1 単発の直しが種類を保存しない | ○ | §3-4「サービスで種類を通す 5 か所」の 1（設計 L127）・F5・§5・A3 | `calendar_service.py:502-512` の `field_map` は 9 キー（title〜color_key）で `category` が無い。設計が指す `:502-512` と一致。ここに `"category": "category"` を足す指定が入っている |
| R2 繰り返し 3 か所 | ○ | §3-4 の 2〜5（L128-131）・F5・A3（5 通り）・§5 | `:682` `_TEXT_FIELDS` に `category` 無し（設計 2）／`:1055-1056` `row_fields` の並びが `("title","description","location","color_key")`（設計 3）／`:1122` `category=master["category"]`（設計 4 が `fields.get("category", master["category"])` に指定）／`:1224` の並びに `category` 無し（設計 5）。5 か所すべて実物の行と一致。「すべて」は `_TEXT_FIELDS` で効く。`_row_values`（`:969`）は `category=` を `**over` で受けられる形で、`:1122` の指定と整合 |
| R3 `meeting` を止めると作成が 422 | ○ | §3-3 `update_category`（L109）・A4・§7 の最終行 | `:423` の既定 `payload.get("category", "meeting")` が残るので、`meeting` を使わなくできない（422 `category_not_disableable`）案 1 を採っている。Google 取り込みの `upsert_from_google`（`:1488`）は DB の既定 `meeting` に頼るので、外部キーの相手行が常に有効になり整合する |
| R4 AI 用の写しの分類 | ○ | §3-2 の「AI 用の写しの分類」5 項目（L96-101） | 下の (3)。mask/allow の分け方・件数・許可一覧・tsv・試験の 4 点が入った |
| R5 古い CHECK の名前 | ○（方式は (a) と少し違う。§3 (4) で扱う） | §3-2 の手順 1・5・F9・§8 | 推奨した (a)「`pg_constraint` から引いて外す」は採らず、(b) の本番の制約名の読み取り（F9）＋「CHECK が残れば失敗」の確かめ（手順 5）＋`ADD COLUMN IF NOT EXISTS`（手順 1）の組。残ったまま黙って通る道は無いので、必須としては満たす |
| R6 読み方の正本 | ○ | §4-1 の `useCalendarCategories.ts`（L139） | `useApiQuery("/calendar/categories")` と書換え後の `useInvalidateApi` 取り直しが書いてある。`frontend/src/lib/query/apiQuery.ts:52`（`useApiQuery`）・`:105`（`useInvalidateApi`）が実在。`ScheduleSettingsPage.tsx:54`・`:64` も同じ使い方で実在 |
| R7 `calendars.config` の使い先 | ○ | F7・§4-1（L138・L141）・§5・A10 | `git grep -n "calendars.config" -- . ':!docs' ':!.claude-pipeline'` は 4 行: `calendars.config.test.ts:4`・`ScheduleDraftFields.tsx:20`・`SchedulePageImpl.tsx:28`・`schedule-utils.ts:62`。F7 の 3 ファイル＋自分の試験と全数一致。F7 の細かい行も確かめた: `SchedulePageImpl.tsx:94`（型）・`:153`（`item?.category ?? "meeting"`）・`:222-223`（`getCalendarMeta`）・`:319`・`:344-345`（`Badge variant={meta.badgeVariant}`）・`:399-400`（詳細の「種類」行）・`:723`・`:736`、`schedule-utils.ts:359`・`:398` |

### 推奨 S1〜S8（すべて ○）

| # | ○× | 第2版の場所 | 実物 |
|---|---|---|---|
| S1 直すときに色を上書きしない | ○ | §4-2（L147）・A6 | `ScheduleDraftFields.tsx:284-290` の `changeCategory` は今 `mode === "create"` のときだけ共有を替える。設計は色も同じ条件にし、直すときは種類だけと書いた |
| S2 採番の競合・名前の空白 | ○（細部は N5・N6） | §3-3（L108・L110）・§4-3（L156） | 409 `category_conflict`・前後の空白を落としてから 1〜50 字、が入っている |
| S3 A10 の測り方 | ○ | A10 | 3 本の `git grep` に分けた。確かめ: 今 `git grep -n '"procurement"' -- frontend/src ':!frontend/src/locales'` は `calendars.config.ts`・同 test の 2 ファイルだけ＝消せば 0 件になる（変更を測れる）。`git grep -n "'procurement'" -- backend/app` は今 `tenant.py:1579` の 1 行で、設計どおり作ると 2 行（7 行の INSERT が 1 行に収まれば。N8 参照）。`schedule.calendarLabels.*` を数えない理由も書いてある |
| S4 A1〜A11 の測り方 | ○（A1・A2 の本番側は §5 で扱う） | §2 | 検証方法が各行に入った |
| S5 トリガ関数・形の差 | ○ | §3-1（L82）・A12・F14 | 手本 `tenant.py:2139`（関数 `set_updated_at_calendar_events`）・`:2241`（トリガ）が実在。A12 が新設 |
| S6 戻し方 | ○ | §3-2 の「戻し方」（L102） | `meta &&` で守られる点と、古い画面で保存すると種類が変わりうる注意が入った |
| S7 見え方の言葉 | ○ | §0 の表（L14）・§8（L200） | 「変えない（札の見た目は変わる。§8）」と、`personal` の種類でも「全員」なら全員に見える注記が入った |
| S8 軽い点 | ○ | §3-1（L81）・§3-2（L94-95） | 登録 5 行を F10 に列挙。`protected-tables.txt` に `calendar` を含む行は 0（`grep -c calendar` = 0）で、L95 の記述と一致。`tenant.py:1577` のコメント直しも入った。移行の置き場所は `run_all_migrations.sh:1483`（color_key）の後ろ、末尾の `:1489`（`20261122_100000`）の後・`:1492`（`mr_report_summary`）の前で、設計の書きぶりと実物が合う |

## 2 §1 の F12〜F14 の照合

| # | ○× | 実物 |
|---|---|---|
| F12 | ○ | `apiQuery.ts:1-8` に「取り方は useApiQuery だけ」。`:52` `export function useApiQuery`・`:105` `export function useInvalidateApi`。`pages/schedule/ScheduleSettingsPage.tsx:54`（`useApiQuery("/calendar/owners")`）・`:64`（`useInvalidateApi()`）。ただし設計は `ScheduleSettingsPage.tsx` とだけ書き、置き場所 `frontend/src/pages/schedule/` を省いている（軽い・S9） |
| F13 | ○ | `create_ai_cloud_views.sql:3` に「下の 1165 行」。`test_ai_cloud_views.py:486` は `== n0 == 1165`。`reference-allowlist.tsv:7` の sha256 `e36ff1500ef3644073f9aaadcb029d577e73f3586a55aec7c810a10504dc48b1` は、いまの `sha256sum migrations/20261024_100300_create_ai_cloud_views.sql`（先頭 16 文字 `e36ff1500ef36440`）と一致 |
| F14 | ○（行の指し方が 1 行ずれ） | `.github/workflows/migration-test.yml:2221` は job 直前の説明のコメント行。実際に流すのは `:2277` `python3 scripts/check_tenant_template_shape.py --db tenant_shape_check --out-dir …`（job 名 `tenant-template-shape` は `:2222` 付近）。`scripts/check_tenant_template_shape.py:1-14` の docstring に「表・列・索引・制約（外部キーは指す表の置き場所つき）・トリガ・関数・権限」を比べるとあり、A12 が測る内容と合う。推奨 S9 に回す |

F1〜F11 は第1回で照合済み。今回、前回「未確認」だった F3・F9 は、設計が「読むだけの鍵で読んだ（Opus）」と書き換えている。この審査は本番を読んでいないので、F3・F9 は引き続き**未確認**（設計担当の記録として受け取る）。

## 3 審査

### (1) R1〜R7・S1〜S8

上の §1 のとおり、全 15 項目 ○。

### (2) F12〜F14

上の §2 のとおり。食い違いは F14 の行番号 1 つだけ（軽い）。

### (3) 分類表の件数 1169 は、欄ごとの数え方で正しいか — ○

- `create_ai_cloud_views.sql:13-14` の `INSERT … SELECT … FROM (VALUES … ARRAY[…] …)` は、`ARRAY` を欄ごとに分けて入れる（ヘッダ `:7` も「unnest で入れる」）。行ごとに `ARRAY[…]` の要素数を数え上げる小さなスクリプトで、全 `('tenant_*'|'public', 表, ARRAY[…], class, 理由)` の要素を数えた結果は **1165**。注記（`:3`）・試験（`test_ai_cloud_views.py:486`）と一致する。
- 新しい表の足し分: `ARRAY['key','name']` mask（2 欄）＋ `ARRAY['color_key']` allow（1 欄）＋ `ARRAY['default_share']` allow（1 欄）＝ **4 欄**。1165 + 4 = **1169**。設計の「3 行」は VALUES の行数、「4 行」は tsv の行数、「1169」は欄ごとの合計で、3 つとも矛盾しない。
- 分け方も規則に合う: `key`（CHECK が正規表現）と `name`（自由な文字）が mask、`color_key`（24 値の CHECK）と `default_share`（2 値の CHECK）が allow。`sort_order`・`is_active`・`created_at`・`updated_at` は `_PASS_TYPES`（`test_ai_cloud_views.py:52-55`、int4・bool・timestamptz）で行が要らない。
- 参考: `calendar_events.category` は今 mask（`create_ai_cloud_views.sql:374`）。CHECK を外しても mask のままで変えなくてよい。
- 注意点: `docs/handoff/cloud-case-ai/stage1-column-class.tsv` は 1072 行（見出し 1 行＋1071 行）で、SQL の 1165 とは 94 行ずれている（この審査では原因は未確認。tsv と SQL を突き合わせる試験は `git grep` で見つからなかった）。設計が「tsv に 4 行足す」と書くのは正しいが、tsv の列は 6 つ（`schema_pattern・table・column・class・reason・data_type`）なので、`data_type`（`key` は character varying、`name` は character varying、`color_key` は text、`default_share` は character varying）まで書く旨を足すと実装者が迷わない（S10）。
- 設計の `test_ai_cloud_views.py:6` を「ARRAY は unnest で欄ごとに分かれる」の根拠にしている点（設計 L98）は、実際の同ファイル `:6` が T10b の説明で、unnest の記述は `create_ai_cloud_views.sql:7`。根拠の指し先が違う（S9）。

### (4) 第2版で新しく入った記述が壊れないか

| 記述 | 判定 | 根拠・指摘 |
|---|---|---|
| 古い CHECK が残れば失敗の確かめ（手順 5） | ○ 壊れない | `tenant.py:1579` の CHECK 名 `calendar_events_category_check` を外し、残りを `category` を使う CHECK の有無で確かめる。F9 は本番 5 社が同じ名前としている。`calendar_events` には他に `category` を定義に含む CHECK は無い（`tenant.py:1579-1590` の CHECK は `color_key`・`calendar_type`・`source`・`sync_status` など）ので、誤検出はしない。**推奨 N1**: 確かめの条件を `contype = 'c'`（外部キーを含めない）と明記し、全部屋を **1 つの `DO` ブロック**にして `RAISE` で全体が戻る形にする（手本 `20261119_120000_add_calendar_events_color_key.sql` は 1 つの `DO` で、psql は文ごとに確定するため、`DO` を分けると FK だけ付いて落ちる途中の状態が残る） |
| `ADD COLUMN IF NOT EXISTS`（手順 1） | ○ 壊れない（細部あり） | 型 `varchar(50) NOT NULL DEFAULT 'meeting'` は `tenant.py:1578` と同じ。外部キーの両側も `varchar(50)` で型が合う。**推奨 N2**: `ADD COLUMN IF NOT EXISTS` は列が有っても表のロックを取りにいく（ロックを取ってから「有るから飛ばす」）ので、ロック待ちを 1 秒で諦める運用（ADR-1037）では、本番の全 5 社に列が有るのに、空の命令でロック待ちに当たる可能性がある。手本どおり `pg_attribute` に列が無いときだけ `ALTER` する形（制約・`to_regclass` と同じ守り）に変えると、有る会社は何も取らない |
| 外部キー `NOT VALID` → `VALIDATE`（手順 3） | ○ 壊れない | 手本 `20261119_120000_…sql:16-23` と同じ形（名前が無いときだけ足し、`VALIDATE`）。F9 のとおり 7 種は CHECK で限られていたので、7 行を先に入れれば通る |
| `ON UPDATE RESTRICT ON DELETE RESTRICT` とひな形 | ○ | ひな形と移行で同じ文字に揃えれば、形の差の検査（`pg_get_constraintdef`）は同じ文字になる。A12 で測れる |
| 409 `category_conflict`（§3-3 L108） | △ 推奨 N5 | `IntegrityError` のあとは、同じセッションが失敗状態のままなので `await db.rollback()` が要り、その後の後始末（接続を戻すときの `clear_tenant_context`・ADR-131 の流れ）が動くようにする。設計は「`commit` の直後に `reset_tenant_context`（ADR-072）」とだけ書き、失敗側の手順が無い。`calendar.py`・`calendar_service.py` には `IntegrityError` の既存の扱いが無い（`git grep -n IntegrityError` が両ファイルで 0 件）ので、手本が無い。「`rollback` してから 409 を返す」を 1 行足し、試験は 2 つの同時の作成を `IntegrityError` で再現する形にする |
| 鍵の採番 `custom_` ＋最大の数＋1 | △ 推奨 N6 | 「最大の数」は、鍵の文字の並び順で取ると `custom_9` が `custom_10` より大きくなる。数に直して最大を取る旨と、`custom_9` がある状態で作ると `custom_10` になる試験を 1 つ足す |
| `meeting` を止めない | ○ 壊れない | `meeting` が使えなくならないので、`calendar_service.py:423` の既定（種類を送らない作成）・Google の取り込み・秘書の作成は、どれも外部キーに当たらず `invalid_category` にもならない。`PATCH` の `is_active=false` を `meeting` に送ると 422 `category_not_disableable`（A4）。直接 DB から `meeting` を無効にする道は設計外（管理者の画面と API だけ） |
| 直すときの「今の種類のまま」（A4） | △ 推奨 N7 | 繰り返しの「この予定だけ」「これ以降」で、「今の種類」はどの行のものか（その回の例外の行か、元の行か）が書いていない。画面は種類が変わったときだけ送る（§4-2 L149）ので実害は小さいが、裏側の試験（§5）に「元の行の種類が使わなくした種類のとき、この予定だけを直しても通る」を 1 つ足し、比べる相手を `row if row is not None else master`（`:1049-1054` の色の比べ方と同じ形）に決めて書く |

### (5) 受入条件 A1〜A12 が ○× で測れるか

| 基準 | ○× | 指摘 |
|---|---|---|
| A1 | △ | 試験側（2 回流して同じ）は ○。本番側「各社の `ai_ro.tenant_00N__calendar_categories` を数え 7 行」は、この審査では読む手段を**未確認**: `docs/handoff/ai-readonly-db-path/usage.md` には `tenant_00N__` の名付けも `pg_constraint` を読む手順も出てこない（`grep -n "pg_\|catalog\|tenant_00\|__"` が 0 件）。ビューの名前と、ビューが無い場合の代わり（括弧の中の「`pg_class` の行の有無」は 7 行の確認にならない）を直す（S11）。本番の確認は反映後に PO・Opus が行うもので、CI の合否ではないので、必須にはしない |
| A2 | △ | 試験側は ○。本番で `pg_constraint` を読めるかは、F9 の「読んだ」という記録が前提。読み方の手順を usage.md か設計に 1 行書く（S11 と同じ） |
| A3 | ○ | 5 通りそれぞれ「正しい行に入る」を測れる（`field_map`・`_TEXT_FIELDS`・`row_fields`・`:1122`・`:1224` の 5 か所と 1 対 1） |
| A4 | ○ | 422 `invalid_category`・同じ種類のまま通る・`meeting` を止めると 422（N7 を足せばより完全） |
| A5 | ○ | 管理者の判定は `calendar.py:523` の `is_tenant_admin(await get_user_system_keys(db, user.id))` と同じ形。403・404・422・201 の試験で測れる |
| A6 | ○ | 画面の試験で測れる（作るときに入る・直すときに変わらない） |
| A7 | ○ | 画面の試験で測れる |
| A8 | ○ | 3 通りで測れる |
| A9 | ○ | `git diff origin/main...HEAD -- backend/app/services/calendar_service.py` で `:238-250`（今は `:242`・`:244`・`:246` の `visibility_sql`）に差が無いこと。ただし本設計は `calendar_service.py` の別の行（`:502`・`:682`・`:1056`・`:1122`・`:1224`）を変えるので `diff` が空にはならない。「見え方の条件の行（`visibility_sql` の 3 行と `where += f" AND {visibility_sql}"`）が差に出ない」と読む旨を足すと○×が一意になる（S12） |
| A10 | ○ | 上の S3 のとおり、3 本の `git grep` で測れる。`tenant.py` の `'procurement'` が 2 行になるのは、7 行の INSERT が 1 行に並ぶ場合。実装者が 1 行ずつ分けて書くと 8 行になり、A10 が落ちる（N8: 「7 種の INSERT は 1 行にまとめる」か、数えるのを「`tenant.py` の中だけ」に変える） |
| A11 | ○ | i18n 点検・UI governance gate・Lint の既存の点検で測れる。`frontend/src/pages/schedule.css:316` に `schedule-month__dot` が実在（設計は置き場所を省いている・S9） |
| A12 | ○ | `.github/workflows/migration-test.yml` の `tenant-template-shape` job（`:2277`）が比べる。外部キー・トリガ・関数を含むので、設計の §3-1 の「ひな形と移行の両方に同じ形で」と一致する |

## 4 指摘の一覧

### 必須

なし。

### 推奨

| # | 重さ | 指摘 | 直し方 |
|---|---|---|---|
| N1 | 推奨 | 移行の「CHECK が残れば失敗」の確かめを `contype = 'c'` で書く旨と、全部屋を 1 つの `DO` にして `RAISE` で全体が戻ることが書いていない | §3-2 手順 5 に「`contype = 'c'`」「全部屋を 1 つの `DO` ブロック（手本どおり）」を足す |
| N2 | 推奨 | `ADD COLUMN IF NOT EXISTS` は有る列でもロックを取りにいき、ロック待ち 1 秒で諦める運用（ADR-1037）では不要に当たる | 手順 1 を「`pg_attribute` に `category` が無い部屋だけ `ALTER`」に変える |
| N5 | 推奨 | 409 の道で `rollback` と後始末が無い | §3-3 に「`IntegrityError` は `await db.rollback()` してから 409 を返す」を足し、同時作成の試験を §5 に足す |
| N6 | 推奨 | 鍵の採番の「最大の数」が文字の並びで取られると `custom_9` > `custom_10` になる | §3-3 に「数に直して最大を取る」と、`custom_9` の次が `custom_10` になる試験を足す |
| N7 | 推奨 | 繰り返しの「この予定だけ」「これ以降」で、「今の種類」を比べる行が決まっていない | §3-4 の「直す」に「比べる相手は元の行か例外の行か（色の比べ方 `:1049-1054` と同じ）」を書き、A4 の試験に「元の行が使わなくした種類でも、この予定だけを直して通る」を足す |
| N8 | 推奨 | A10 の `'procurement'` 2 行は、INSERT の書き方で 2〜8 行に変わる | A10 を「`tenant.py` 以外が 0 件」に変えるか、INSERT を 1 行にする旨を §3-1 に書く |
| S9 | 推奨 | 根拠の行の指し方の軽いずれ: F14 の `:2221`（コメント行。実際は `:2277`）・設計 L98 の `test_ai_cloud_views.py:6`（実際は `create_ai_cloud_views.sql:7`）・`ScheduleSettingsPage.tsx` と `schedule.css:316` の置き場所（`frontend/src/pages/schedule/`・`frontend/src/pages/`）が無い | 行・パスを直す |
| S10 | 推奨 | `stage1-column-class.tsv` は 6 列（`data_type` を含む）で、SQL と 94 行ずれている（原因未確認） | 設計に 4 行の `data_type`（varchar・varchar・text・varchar）まで書く。ずれの原因は別件として調べる |
| S11 | 推奨 | A1・A2 の本番の読み方（ビュー名・`pg_constraint`）が usage.md に無い | 本番の確認を「反映後に PO・Opus が行う項目（CI の合否ではない）」と書き、読み方を usage.md か設計に 1 行足す |
| S12 | 推奨 | A9 の `diff` は他の行も変えるので「空」にならない | 「見え方の条件の行に差が出ない」と書き換える |

## 5 結論

- 前回の必須 R1〜R7・推奨 S1〜S8 の 15 項目は、第2版のすべてに入った（○ 15・× 0）。実物の行（`calendar_service.py` の 5 か所・`tenant.py:2139`・`:2241`・`apiQuery.ts`・`calendars.config` の使い先）と照合し、食い違いは無い。
- 分類表の件数 1169 は、欄ごとの数え方（1165 + 4 欄）で正しい。
- 第2版で新しく入った記述は、設計のとおりに作って壊れる所は見つからなかった。ただし 409 の後始末・ロック待ち・鍵の採番・A10 の数え方は、実装前に 1 行ずつ決めておくと実装者が迷わない（推奨 N1〜N8）。
- 必須の指摘は無い。推奨は実装カードに入れるか、設計に 1 行ずつ足せば足りる。

判定: APPROVE
