# 実装カード: 便3b 反映（ボタン）・審査役の指摘 3 件（M1〜M3）の直し

- 設計: docs/handoff/discord-server-management/design.md §4-8・§4-9（「反映する」と結果の表）・§5・§8 改訂5
- PO 承認: 「1」（2026-11-04、この設計で承認）。便3a は 2026-11-05 に本番反映済みで、PO が画面で 0 件・0 件・0 件を確かめた（KGI-3 合格）。「進める」（2026-11-05、便3b に進む）
- ブランチ: release/discord-own-server-apply（origin/main f07c538ea にこのカードと設計の改訂5を足したもの。実際の先頭は Opus が依頼文で伝える）
- 実物の行番号はすべて origin/main a7a66a2cc で Opus が読んで確かめた（f07c538ea でも該当ファイルに差が無い）
- この便で初めて Discord に書く（POST・PATCH・PUT）。DELETE は書かない。migrations なし（表 `discord_server_apply_runs` は便2 の migrations/20261106_120000_create_discord_server_snapshot_tables.sql:35-48 で作成済み）

## 触ってよいファイル（これと報告書 docs/handoff/discord-server-management/impl-report-bin3b.md だけ）

プログラム:
- `backend/app/services/discord_blueprint.py`（§1 の M1 と、§2 の「実行の中身」を足す）
- backend/app/services/discord_blueprint_apply.py（新規・§3）
- `backend/app/routers/discord_own_server.py`（§4。今の読み取りの関数 101-174 行の中身は変えない）
- `backend/app/realtime/topics.py`（§4-4 の 1 行だけ）

試験:
- `backend/tests/conftest.py`（§5-1 の 3 か所だけ）
- `backend/tests/test_discord_own_server_snapshot.py`（§5-2 の M3。258-262 行の試験 1 本を置き換えるだけ）
- `backend/tests/test_discord_own_server_plan.py`（§5-3 を足すだけ）
- backend/tests/test_discord_blueprint_apply.py（新規・§5-4）
- backend/tests/test_discord_own_server_apply.py（新規・§5-5）

画面:
- `frontend/src/pages/admin/DiscordOwnServerPanel.tsx`
- `frontend/src/pages/admin/DiscordOwnServerPanel.test.tsx`（131-137 行の試験 1 本を §6-3 の 1 に置き換え、ほかは足すだけ）
- `frontend/src/locales/ja.json`・`frontend/src/locales/en.json`（§6-2 のキーだけ）
- `frontend/api-contract/openapi.json`（生成した結果だけ。手で書かない）

触らない: `.github/` の全部・migrations の全部・`scripts/` の全部・`backend/app/main.py`（ルーターは登録済み）・`backend/app/services/discord_rest.py`・`backend/app/cache.py`・`backend/app/discord_blueprints/` の全部（設計図は変えない）・`frontend/src/components/` の金型・CSS ファイル（新しい CSS を作らない）・`DiscordConfigPage.tsx`・本番

## 読んだ節（guards/）

- docs/handoff/design-partner-card-ops/guards/00-common.md：報告は生出力・推測で埋めない
- docs/handoff/design-partner-card-ops/guards/03-file.md：触るファイルを列挙 → 上の一覧だけ
- docs/handoff/design-partner-card-ops/guards/05-pr.md：PR は Opus が作る → 実行役は push まで
- docs/handoff/design-partner-card-ops/guards/10-executor.md：作業前に preflight → 下の §0
- 便1b・便2 の教訓：試験の中に表の定義を書かない。`discord_server_apply_runs` の SQLite 版は conftest に足す（§5-1。`scripts/check_test_schema_dup.py:23-26` で conftest は対象外）

## 受領確認

作業を始める前に、報告書の先頭に次の 3 行を書く:
- 受領確認: card-bin3b-apply.md を読んだ
- origin/release/discord-own-server-apply の先頭 sha（git rev-parse の生出力）
- 触るファイルは上の一覧と報告書だけ、と理解した

## §0 準備

- リポジトリの根で `./scripts/dev/executor-preflight.sh` を流し、生出力を報告書に貼る
  - クラウドでは [1/3] network と [2/3] gh auth の FAIL は起こるものとして、生出力を貼るだけで先へ進む。[3/3] と [4/4] が OK でなければ停止して BLOCKED:
- `git fetch origin` のあと `release/discord-own-server-apply` を取り出す（新しく作らない）

## §1 M1 の直し（`backend/app/services/discord_blueprint.py:441-445`）

今は、親のカテゴリが blocked のチャンネルで `continue` する前に Discord の物を探していない。そのチャンネルが `used_chans` に入らず、「消す候補」に間違って出る。

変更前（442-445 行）:
```python
        parent_state = cat_state.get(ch.category) if ch.category else None
        if parent_state and parent_state.startswith("blocked:"):
            emit(2, _row("update_channel", ch.key, ch.name, None, None, None), parent_state.split(":", 1)[1])
            continue
```
変更後:
```python
        parent_state = cat_state.get(ch.category) if ch.category else None
        if parent_state and parent_state.startswith("blocked:"):
            # 親が分からないので直さない。ただし Discord にある物は「消す候補」に出さない
            if ch.discord_id:
                used_chans.update(str(c.get("id")) for c in d_chans if str(c.get("id")) == ch.discord_id)
            else:
                used_chans.update(str(c.get("id")) for c in d_chans if c.get("name") == ch.name)
            emit(2, _row("update_channel", ch.key, ch.name, None, None, None), parent_state.split(":", 1)[1])
            continue
```
- 名前で探すときは親を見ない（親が分からないため）。同じ名前の物は全部、消す候補に出さない側に入れる（消す候補は少なく出す側に倒す）

## §2 実行の中身（`build_plan` に足す・同じファイル）

確認の一覧と反映の中身を 1 か所（`build_plan`）で作る。反映のために比べ方を別に書かない（SSOT）。

### §2-1 戻り値に `"actions"` を足す

- `emit(stage, row, reason=None, action=None)` にする。`reason is None` のとき（changes に入る行）は `action` が必ずある（`None` なら `AssertionError`）。`changes[stage]` に row、新しい `actions[stage]` に action を同じ順で足す。blocked の行は action を持たない
- 戻り値：`{"changes", "blocked", "delete_candidates", "plan_digest", "actions"}`。`actions` は `out_changes` と同じ長さ・同じ順（`[a for stage in actions for a in stage]`）
- `plan_digest` の作り方は変えない（`actions` は含めない。507-512 行のまま）

### §2-2 action の形

```
{"method": "POST" | "PATCH" | "PUT", "path": str, "json": dict, "creates": str | None}
```
- 置き換えの印（反映のときに §3 が本物の番号に直す。戻り値にサーバーの番号を入れないため：今の試験 test_discord_own_server_plan.py の 12）
  - `{guild}`：サーバーの番号。path の中の文字、または json の値がちょうど `"{guild}"` のとき
  - `{ref:role:<key>}`・`{ref:category:<key>}`：同じ反映の中で先に作る物の番号。path の中の文字、または json の値がちょうどその文字のとき
- @everyone の番号（＝サーバーの番号）を path や json に書くときは `"{guild}"` と書く
- `creates`：作る行だけ `"role:<key>"`・`"category:<key>"`・`"channel:<key>"`。ほかは `None`

### §2-3 行ごとの中身（出典：Discord 公式 github.com/discord/discord-api-docs `developers/resources/guild.mdx` の Create Guild Role・Modify Guild Role・Create Guild Channel、`developers/resources/channel.mdx` の Modify Channel・Edit Channel Permissions、`developers/topics/permissions.mdx` の Role Colors Object。2026-11-05 に Opus が直接読んだ。Context7 は月の上限で使えなかった）

`KNOWN_MASK` の外のビット（表に無いビット）は今の値をそのまま残す（設計 改訂4）。下の `keep(x, want)` は `(x & ~KNOWN_MASK) | (want & KNOWN_MASK)`。数は Discord の決まりどおり 10 進の文字で送る。

| kind / field | method | path | json |
|---|---|---|---|
| create_role | POST | `/guilds/{guild}/roles` | `{"name": role.name, "permissions": str(want_perms), "colors": {"primary_color": role.color}, "hoist": role.hoist, "mentionable": role.mentionable}`、creates `role:<key>` |
| update_role name | PATCH | `/guilds/{guild}/roles/<id>` | `{"name": role.name}` |
| update_role color | PATCH | 同上 | `{"colors": {"primary_color": role.color}}`（`color` は送らない。公式で非推奨） |
| update_role hoist | PATCH | 同上 | `{"hoist": role.hoist}` |
| update_role mentionable | PATCH | 同上 | `{"mentionable": role.mentionable}` |
| update_role permissions | PATCH | 同上 | `{"permissions": str(keep(have_perms, want_perms))}` |
| create_category | POST | `/guilds/{guild}/channels` | `{"name": cat.name, "type": 4, "permission_overwrites": OW}`、creates `category:<key>` |
| update_category name | PATCH | `/channels/<id>` | `{"name": cat.name}` |
| create_channel | POST | `/guilds/{guild}/channels` | `{"name": ch.name, "type": 0, "permission_overwrites": OW}`。`ch.topic` があれば `"topic"`、親があれば `"parent_id": PARENT`。creates `channel:<key>` |
| update_channel name | PATCH | `/channels/<id>` | `{"name": ch.name}` |
| update_channel topic | PATCH | 同上 | `{"topic": ch.topic or ""}` |
| update_channel parent | PATCH | 同上 | `{"parent_id": PARENT}`（親が無い設計なら `None`） |
| update_overwrite | PUT | `/channels/<物の id>/permissions/<TID>` | `{"type": 0, "allow": str(keep(cur_allow, allow)), "deny": str(keep(cur_deny, deny))}` |

- `<id>`：見つかった物の番号。@everyone のロールなら `{guild}`
- `TID`：§2-4 の相手の番号
- `OW`：設計図の overwrites を順に `{"id": TID, "type": 0, "allow": str(allow), "deny": str(deny)}` にした並び
- `PARENT`：親のカテゴリが見つかっていればその番号、この反映で作るなら `"{ref:category:<key>}"`

### §2-4 相手の番号 `TID`（今の `target_id` 334-344 行はそのまま。新しい小さな関数を足す）

- `"@everyone"` → `"{guild}"`
- `"@bot"` → `bot_target_id`（無いときはもう blocked・理由 `bot_role_missing` なので action は作られない）
- `"role:<key>"` → 見つかっていれば `role_ids[key]`、`role_state[key] == "new"` なら `"{ref:role:<key>}"`

### §2-5 親が新しく作るカテゴリの場合（今のずれの直し）

今は 446 行の `parent_id = cat_ids.get(ch.category)` が、親が新しく作るカテゴリのとき `None` になる。discord_id で見つかったチャンネルでは 477-480 行の比べ方で「親を外す」行のように扱われ、action にすると親が外れてしまう。

- 比べ方（478 行 `cur_parent != parent_id`）の行は今のまま出す（after は `parent_name`。行の文は変わらない）
- action の `PARENT` だけは §2-3 のとおり `"{ref:category:<key>}"` にする（`cat_state[ch.category] == "new"` のとき）
- 試験 §5-3 の 3 で確かめる

## §3 反映する係 backend/app/services/discord_blueprint_apply.py（新規）

```python
from app.services.discord_rest import DiscordAPIError, discord_api_request

async def apply_plan(plan: dict, guild_id: str, bot_token: str) -> list[dict]:
```
- `plan["changes"]` と `plan["actions"]` を前から順に 1 行ずつ。前の行で作った物の番号を `created: dict[str, str]`（`"role:<key>"` → 番号）に持つ
- 1 行の流れ:
  1. 印を直す：path の `{guild}` と `{ref:…}`、json の中の値（入れ子の dict と list も見る）がちょうど `"{guild}"`・`"{ref:…}"` の物。`{ref:…}` が `created` に無ければ Discord を呼ばずに `failed`・理由 `depends_failed`
  2. `await discord_api_request(method=action["method"], path=…, bot_token=bot_token, json=…, expected_statuses=(200, 201, 204))`（429 と 5xx の待ちは中で済む。`backend/app/services/discord_rest.py:34-42`）
  3. `DiscordAPIError` なら `failed`・理由 `discord_error`・`discord_status` にその `status_code`（`discord_rest.py:26-31`）。ほかの例外は受けずに上へ出す
  4. 成功：`creates` があり返事に `id` があれば `created[creates] = str(返事["id"])`、結果の `discord_id` に入れる
  5. 1 行失敗しても残りの行を続ける（設計 §4-8）
- そのあと `plan["blocked"]` の行を全部 `blocked`（理由は行の `reason`）にする。Discord は呼ばない（KGI-6）
- 結果の 1 行：`{"kind", "key", "name", "field", "status": "success"|"blocked"|"failed", "reason": str|None, "discord_id": str|None, "discord_status": int|None}`。並びは changes の順 → blocked の順
- このファイルの `method=` に渡すのは `action["method"]` だけ。DELETE の文字を置かない。`action["method"]` が `("POST", "PATCH", "PUT")` の外なら Discord を呼ばずに `failed`・理由 `method_not_allowed`（念のための止め）

## §4 API（`backend/app/routers/discord_own_server.py`）

### §4-1 確認と反映で同じ手順を 1 か所に（M2・M3 の直しも兼ねる）

今の `check_own_server_plan`（212-276 行）の中身を、次の 2 つの関数に移す（同じ動き。返事の文も変えない）:
- `async def _load_own_context(db, tenant_id) -> tuple[str, Blueprint, str]`：guild_id の SQL（217-227 行）→ 設計図（229-236 行）→ Bot の鍵（238-243 行）。返すのは (guild_id, blueprint, bot_token)
- `async def _read_and_plan(guild_id, blueprint, bot_token) -> dict`：Discord を GET で 4 回読み（245-272 行）、`build_plan`（274-275 行）の戻り値をそのまま返す
- `check_own_server_plan` は上の 2 つを呼び、`OwnServerPlanResponse(plan_digest=…, changes=…, blocked=…, delete_candidates=…)` を返す（`actions` は返事に入れない）
- M2：233-236 行の `except ValueError` を `except (ValueError, OSError)` にする（ファイルが読めないときも 500 にせず 422 の同じ文）
- M3：179 行の `_READ = "GET"` を消し、`method=_READ` の 4 か所を `method="GET"` と文字で書く（試験 §5-2 で、method に渡すのが文字だけであることを確かめる）

### §4-2 反映の API

- `POST /admin/discord/own-server/apply`、`dependencies=[Depends(require_permission("tenant.profile.edit"))]`
- 本文 `class OwnServerApplyRequest(BaseModel): plan_digest: str`
- 手順:
  1. `_load_own_context`（422・404・422・503 は確認と同じ）
  2. 同時に 1 本だけ：`r = get_redis()`（`from app.cache import get_redis`。`backend/app/cache.py:62-64`、未接続なら `None`）。`None` なら 503「同時に反映しないための仕組みにつながりません。少し待ってからやり直してください。」。`await r.set(f"discord_own_apply:{tenant_id}", "1", nx=True, ex=600)` が真でなければ 409「反映が動いています。終わってから確認し直してください。」（前例 `backend/app/tasks/viewer_inventory_cache.py:74`）
  3. ここから先は `try:` … `finally: await r.delete(f"discord_own_apply:{tenant_id}")`（鍵を必ず外す。外すのに失敗したらログに warning を出し、10 分で自然に消える）
  4. `started_at = datetime.now(timezone.utc)`。`_read_and_plan`（502 は確認と同じ）。`plan["plan_digest"] != body.plan_digest` なら 409「確認したあとにサーバーか設計図が変わりました。確認し直してください。」（Discord に書かない・記録を入れない）
  5. `results = await apply_plan(plan, guild_id, bot_token)`
  6. `discord_server_apply_runs` に 1 行：`tenant_id`・`purpose='own'`・`plan_digest`・`started_at`・`finished_at`（今の時刻）・`applied_by=current_user.id`・`result`（`json.dumps({"rows": results}, ensure_ascii=False)`）。`RETURNING id`。JSONB の CAST は `_insert_sql`（90-98 行）と同じ分け方で、新しい関数 `_apply_insert_sql(db)` に書く（`_insert_sql` は変えない）
  7. `record_audit_log(db=db, tenant_id=tenant_id, user_id=current_user.id, action="create", table_name="discord_server_apply_runs", record_id=run_id, new_data={"success": n, "blocked": n, "failed": n})`（`backend/app/services/audit.py:277-286`）
  8. `await db.commit()` → `await reset_tenant_context(db, tenant_id)`（ADR-072。156-166 行と同じ並び）
  9. ログ：`logger.info("[discord_own_server] apply tenant=%d run=%d success=%d blocked=%d failed=%d", …)`
- 返事 `OwnServerApplyResponse { run_id: int; success_count: int; blocked_count: int; failed_count: int; results: list[ApplyResultRow] }`。`ApplyResultRow` は §3 の結果の 1 行と同じ項目（`field`・`reason`・`discord_id`・`discord_status` は `| None = None`）
- このファイルの Discord への呼び出しは GET だけのまま（書くのは §3 の係）

### §4-3 守ること

- 消す処理は書かない。`backend/app/routers/discord_own_server.py` と `backend/app/services/discord_blueprint_apply.py` に `"DELETE"` の文字を置かない（鍵を外す `r.delete(` は Redis の呼び出しで、Discord の呼び出しではない）
- 返事にも記録にもサーバーの番号（guild_id）を入れない

### §4-4 即時反映の対応表（`backend/app/realtime/topics.py:104`）

`("POST", "/api/v1/admin/discord/own-server/snapshot"): _PENDING,` の次の行に同じ形で 1 行:
```python
    ("POST", "/api/v1/admin/discord/own-server/apply"): _PENDING,
```
（`backend/tests/test_realtime_topics.py:35-40` が、書き込みのルートを表に載せるまで赤にする）

## §5 試験

### §5-1 `backend/tests/conftest.py`（3 か所だけ）

1. 313-314 行の `public.discord_server_snapshots` の書き換えの次に、同じ形で `public.discord_server_apply_runs` → `discord_server_apply_runs`
2. 1245-1253 行の `discord_server_snapshots` の SQLite 版の次に、同じ形で:
```sql
            CREATE TABLE IF NOT EXISTS discord_server_apply_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id INTEGER NOT NULL,
                purpose VARCHAR(16) NOT NULL CHECK (purpose = 'own'),
                plan_digest VARCHAR(64) NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                finished_at TIMESTAMP,
                applied_by INTEGER,
                result TEXT
            )
```
（上に 1 行の注記「discord-server-management 便3b: 反映の記録（本番は JSONB。SQLite は文字で持つ）」）
3. 1744 行の `DELETE FROM discord_server_snapshots` の前の行に `await conn.execute(text("DELETE FROM discord_server_apply_runs"))`

### §5-2 M3：`backend/tests/test_discord_own_server_snapshot.py:258-262` の試験を置き換える

`test_router_has_only_get_calls_to_discord` を次の形に（名前は同じ）:
- `ast.parse` で `discord_own_server.py` を読み、`method=` の引数を持つ呼び出しを全部集める
- 全部の `method=` が文字の定数（`ast.Constant` で `str`）で、値がすべて `"GET"`。変数や式を渡していたら赤
- 数：`take_own_server_snapshot` の中に 2、`_read_and_plan` の中に 4、ほかの関数に 0
- 文字 `"DELETE"` がファイルに無い（今の 260 行の検査のうち `'"DELETE"'` は残す）

### §5-3 `backend/tests/test_discord_own_server_plan.py` に足す（今の試験はそのまま通ること）

1. M1：カテゴリが blocked（`missing_on_discord`）で、その中のチャンネルが discord_id で Discord にある → そのチャンネルは delete_candidates に出ない。discord_id の無い同じ名前のチャンネルでも出ない
2. KGI-4 の 4 種類（今の試験の 3 と同じ入力）→ `actions` が 4 つで、method と path が §2-3 の表どおり。create_role の json に `"colors": {"primary_color": …}` があり `"color"` が無い
3. 親が新しく作るカテゴリで、discord_id で見つかったチャンネル → parent の action の json が `{"parent_id": "{ref:category:<key>}"}`
4. 新しいロールを既存のカテゴリの上書きの相手にする → update_overwrite の action の path の末尾が `{ref:role:<key>}`
5. 表に無いビット（1<<47）が立っている @everyone の permissions を直す → action の `permissions` に 1<<47 が残る。上書きの allow/deny も同じ
6. 戻り値（`actions` を含む）を `json.dumps` した文字に guild_id の数字が入っていない
7. `plan_digest` が `actions` を足す前と同じ値（今の試験 11 の入力で、`actions` を除いた 3 つの一覧から §1-3 の式で作り直した値と一致）

### §5-4 backend/tests/test_discord_blueprint_apply.py（新規・`apply_plan` を直接呼ぶ。`app.services.discord_blueprint_apply.discord_api_request` を AsyncMock に差し替える）

1. 4 行すべて成功 → status が 4 つとも `success`、呼んだ method と path が順に正しい（`{guild}` が本物の番号に直っている）
2. ロールを作る → 返事の `id` が、あとの上書きの PUT の path の末尾に入る
3. カテゴリを作る → 返事の `id` が、あとのチャンネルを作る json の `parent_id` に入る
4. ロールを作る行が `DiscordAPIError(status_code=403)` → その行は `failed`・`discord_error`・`discord_status` 403。そのロールを使う上書きの行は Discord を呼ばずに `failed`・`depends_failed`。ほかの行は続けて `success`
5. blocked の行（`role_above_bot`）→ `blocked`・理由そのまま。Discord を呼ばない（KGI-6）
6. method が `"DELETE"` の action を渡す → 呼ばずに `failed`・`method_not_allowed`
7. ファイルの中身を ast で読み、`method=` に渡すのが `action["method"]` の 1 か所だけ。文字 `"DELETE"` が無い

### §5-5 backend/tests/test_discord_own_server_apply.py（新規・`test_discord_own_server_snapshot.py:94-140` の作り物の作り方に合わせる。Discord は `app.routers.discord_own_server.discord_api_request`（GET）と `app.services.discord_blueprint_apply.discord_api_request`（書き込み）を別の AsyncMock に、`record_audit_log` は 129 行と同じく差し替え、Redis は `app.routers.discord_own_server.get_redis` を `set`・`delete` を持つ作り物に差し替える。設計図は試験の中で一時フォルダに置き `blueprint_path` を差し替える）

1. KGI-4：4 種類の差が出る設計図 → まず `GET …/plan` の `plan_digest` を取り、それで `POST …/apply` → 200、`success_count` 4、書き込みの mock が 4 回、`discord_server_apply_runs` に 1 行（`plan_digest` が同じ・`result` の rows が 4）。Redis の `delete` が 1 回呼ばれる
2. KGI-5：設計図から文字のチャンネルを 1 つ外した形 → apply しても書き込みの mock に DELETE が無い（呼ばれた method が POST/PATCH/PUT だけ）。apply のあとの `GET …/plan` の delete_candidates に同じチャンネルが残る
3. KGI-6：Bot より上のロールの名前を変える設計図 → `blocked_count` 1、そのロールへの PATCH が無い
4. 違う `plan_digest` → 409、書き込みの mock が呼ばれない、`discord_server_apply_runs` の行が増えない、Redis の `delete` が 1 回
5. Redis の `set` が偽 → 409、Discord を呼ばない（GET も呼ばない）
6. `get_redis` が `None` → 503
7. 自社用が未登録 → 422 / 設計図が無い → 404
8. 設計図を読むときに `OSError`（`load_blueprint` を差し替えて投げる）→ 422（M2。確認の API でも同じことを 1 本）
9. `tenant.profile.view` だけ → 403、Discord を呼ばない
10. 返事と `discord_server_apply_runs.result` の文字に guild_id の数字が入っていない

既存の試験は 1 本も消さない・飛ばさない（置き換えは §5-2 と §6-3 の 1 の 2 本だけ）。

## §6 画面

### §6-1 `frontend/src/pages/admin/DiscordOwnServerPanel.tsx`

使う部品は今の `Button`・`Badge`・`ConfirmModal`・`DataTable`・`EmptyState` だけ。クラスは `discord-config.css` に今ある `dc-actions`・`dc-result`・`dc-group`・`dc-group-title`・`dc-hint` だけ。`style=`・色の直書き・新しい CSS は使わない（ADR-144）。

- 先頭の説明の権限の行に「tenant.profile.edit → 反映」を 1 行足す
- `const APPLY_PATH = "/admin/discord/own-server/apply";`
- 型：`interface ApplyResultRow { kind: string; key: string; name: string; field: string | null; status: "success" | "blocked" | "failed"; reason: string | null; discord_id: string | null; discord_status: number | null }`、`interface OwnServerApplyResult { run_id: number; success_count: number; blocked_count: number; failed_count: number; results: ApplyResultRow[] }`
- 状態：`applyOpen`・`applying`（boolean）、`applyResult`（`OwnServerApplyResult | null`）
- 「確認する」を押したら `applyResult` を `null` に戻す
- `plan` があるとき、3 つの組の下（`dc-result` の中の最後）に `<div className="dc-actions"><Button variant="primary" disabled={plan.changes.length === 0} onClick={() => setApplyOpen(true)}>{t("discordOwnServer.apply")}</Button></div>`（同じ `canEdit` のときだけ出す）
- 2 つ目の `ConfirmModal`（今の解除の ConfirmModal の次）：`open={applyOpen}`・`title={t("discordOwnServer.applyConfirmTitle")}`・`message={t("discordOwnServer.applyConfirmMessage", { count: plan?.changes.length ?? 0 })}`・`confirmLabel={t("discordOwnServer.apply")}`・`confirmLoading={applying}`・`onConfirm={() => void handleApply()}`・`onCancel={() => setApplyOpen(false)}`（`danger` は付けない。消さないため）
- `handleApply`：`api.post<OwnServerApplyResult>(APPLY_PATH, { plan_digest: plan.plan_digest })` → `setApplyResult`、`notice` に success で `t("discordOwnServer.applyDone", { success, blocked, failed })`。失敗は `ApiError` の `status === 409` なら `t("discordOwnServer.applyConflict")`、それ以外は `t("discordOwnServer.applyFailed")`（danger）。どちらも最後に `setApplyOpen(false)`・`setApplying(false)`
- `applyResult` があるとき、`dc-result` の下に `<div className="dc-group">` で見出し `t("discordOwnServer.resultTitle", { count: applyResult.results.length })` と DataTable
  - 列 = 種類（`kind.<kind>`）・名前・項目（今の `fieldLabel`）・結果・理由
  - 結果は `<Badge variant={…}>`：success → `"success"`・`t("discordOwnServer.status.success")`、blocked → `"warning"`・`status.blocked`、failed → `"danger"`・`status.failed`（variant の種類は `frontend/src/components/Badge.tsx:4`）
  - 理由は `reason` があれば `t("discordOwnServer.reason.<reason>")`
  - rowKey は今の `rowKeyOf` と同じ形
  - 0 件は今の `emptyRows`

### §6-2 文言（`frontend/src/locales/ja.json`・`frontend/src/locales/en.json` に同じキー・ADR-027）

`discordOwnServer` のブロックに足す（`reason`・`col`・`status` は今の入れ子に足す・`status` は新しい入れ子）:

| キー | ja | en |
|---|---|---|
| apply | 反映する | Apply |
| applyConfirmTitle | 自社用サーバーに反映しますか？ | Apply to your own server? |
| applyConfirmMessage | {{count}} 件を反映します。消す候補は消しません。 | {{count}} changes will be applied. Delete candidates are not deleted. |
| applyDone | 反映しました（成功 {{success}} 件・できない {{blocked}} 件・失敗 {{failed}} 件） | Applied ({{success}} succeeded, {{blocked}} not allowed, {{failed}} failed) |
| applyFailed | 反映できませんでした | Could not apply |
| applyConflict | 反映できませんでした。もう一度「確認する」を押してから反映してください | Could not apply. Press Check again, then apply |
| resultTitle | 反映の結果（{{count}} 件） | Apply results ({{count}}) |
| col.status | 結果 | Result |
| status.success | 成功 | Succeeded |
| status.blocked | できない | Not allowed |
| status.failed | 失敗 | Failed |
| reason.depends_failed | 先に作る物が失敗したので実行しませんでした | Skipped because an earlier item failed |
| reason.discord_error | Discord が受け付けませんでした | Discord rejected the request |
| reason.method_not_allowed | この操作は実行しません | This operation is not run |

### §6-3 試験（`frontend/src/pages/admin/DiscordOwnServerPanel.test.tsx`）

1. 131-137 行の「has no apply button」を置き換え：changes 0 の確認のあと「Apply」ボタンが押せない（disabled）
2. changes 2 の確認 → 「Apply」を押す → 確かめの窓に「2 changes will be applied. Delete candidates are not deleted.」→ 窓の「Apply」を押す → `api.post` が `"/admin/discord/own-server/apply"` と `{ plan_digest }` で呼ばれる → 「Applied (1 succeeded, 0 not allowed, 1 failed)」と結果の表の「Succeeded」「Failed」
3. 409 → 「Could not apply. Press Check again, then apply」
4. `tenant.profile.edit` が false → 「Apply」が出ない

### §6-4 API の形

- `cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json` を流し、変わった `frontend/api-contract/openapi.json` を入れる。流せなかったら停止して BLOCKED: と生出力

## §7 確かめ（生出力を報告書に貼る）

- `cd backend && python -m pytest tests/test_discord_blueprints.py tests/test_discord_own_server_plan.py tests/test_discord_own_server_snapshot.py tests/test_discord_own_server_apply.py tests/test_discord_blueprint_apply.py tests/test_discord_own_server.py tests/test_discord_config_purpose_guard.py tests/test_realtime_topics.py --no-cov -q` の最後の 15 行（失敗 0）
- `git grep -n '"DELETE"' -- backend/app/routers/discord_own_server.py backend/app/services/discord_blueprint_apply.py`（0 行）
- `git grep -nE 'method="(POST|PATCH|PUT|DELETE)"' -- backend/app/routers/discord_own_server.py backend/app/services/discord_blueprint_apply.py`（0 行）
- `git diff origin/main -- backend/app/discord_blueprints/`（0 行）
- `git merge-base origin/main HEAD` の sha を BASE_SHA に、HEAD を HEAD_SHA に入れて `python3 scripts/check_test_schema_dup.py` の生出力と rc（0）
- 全体の pytest が流せるなら最後の 5 行（流せなければ「CI に任せる」）
- `cd frontend && npx vitest run src/pages/admin/DiscordOwnServerPanel.test.tsx src/pages/admin/DiscordConfigPage.test.tsx` の最後の 20 行
- `cd frontend && npm run check:i18n-missing-keys && npm run lint -- src/pages/admin/DiscordOwnServerPanel.tsx src/pages/admin/DiscordOwnServerPanel.test.tsx && npx tsc --noEmit -p .` の最後の 20 行
- `git grep -nE "style=|#[0-9a-fA-F]{3,6}\b|rgb\(" -- frontend/src/pages/admin/DiscordOwnServerPanel.tsx`（0 行）
- `git diff --stat origin/main`

## §8 保存

- commit を 2 つに分ける:
  1. `fix(discord): 確認の直し 3 件と反映の中身（discord-server-management 便3b）`（§1・§2・§4-1・§5-2・§5-3）
  2. `feat(discord): 自社用サーバーへの反映ボタン（discord-server-management 便3b）`（§3・§4-2〜§4-4・§5-1・§5-4・§5-5・§6 と報告書）
- `git log --oneline -4` の生出力を報告書に貼る
- `git push origin release/discord-own-server-apply`（単独で流す）。PR は作らない（Opus が作る）
- 報告書の最後に、push 後の `git rev-parse HEAD` の生出力

## 想定分岐（停止の条件）

- preflight が失敗した → 停止。BLOCKED: と生出力（クラウドの [1/3][2/3] の FAIL を除く）
- 行の目印（`discord_blueprint.py:442-445`・`discord_own_server.py:179`・`233-236`・`conftest.py:313-314`・`1245-1253`・`1744`・`topics.py:104`・`test_discord_own_server_snapshot.py:258-262`・`DiscordOwnServerPanel.test.tsx:131-137`）が実物と違い、近くにも見つからない → 変えずに停止。BLOCKED: とファイル名・行・実物の生出力
- 便3a の試験（test_discord_own_server_plan.py の 1〜21）が §1・§2 の変更で落ちる → 試験を曲げない。停止して NEEDS_DECISION: と生出力
- `plan_digest` が変わってしまう（§5-3 の 7 が通らない）→ 停止して NEEDS_DECISION:
- 公式の文書と違う項目（`colors` 以外の色の送り方、`lock_permissions` など）が要りそうになった → 足さずに停止。NEEDS_DECISION:
- Discord の DELETE の呼び出しが要りそうになった → 書かずに停止。NEEDS_DECISION:
- 既存の試験が落ちる → 消したり飛ばしたりせず停止。BLOCKED: と生出力
- 金型にない部品・新しい CSS が要りそうになった → 作らずに停止。NEEDS_DECISION: と理由
- 触ってよいファイル以外を変えたくなった → 変えずに停止。NEEDS_DECISION: と理由
- push が拒否された → 言い換えて再試行しない。停止して BLOCKED: と生出力

報告の最後の行は DONE / BLOCKED: 理由 / NEEDS_DECISION: 理由 のどれか 1 つ。

END OF CARD
