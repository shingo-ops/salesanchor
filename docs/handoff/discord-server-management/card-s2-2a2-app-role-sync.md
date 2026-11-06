# 実装カード: 第2段 2a-2 アプリの役割を確認画面に出し、反映でロールを作る・つなぐ・名前と色を変える／役割を消したら番号を「消した番号の表」へ移す

- 設計: docs/handoff/discord-server-management/design.md S2-3 D2-1・D2-3・S2-5・S2-9（Fable 審査 4 回目 APPROVE）
- PO 承認: 第2段 KGI 8〜16 と設計を承認（2026-11-06）。2a-1（表と列）は本番反映済み。このカードは移行を含まない（DB の形は変えない）
- このカードで満たす KGI: 8（アプリの役割が全部「作る」「変わらない」等で確認画面に出て、数がアプリの役割の数と同じ）・10a（名前を変えると同じ番号のロールの名前が変わり、ロールの数は増えない）・11（つないでいない役割に同じ名前のロールが 2 つあると「できない」と出て、何も反映しない）
- ブランチ: release/discord-own-server-s2-2a2（origin/main 0bda3caaf にこのカードと ADR-091 の表の文書を足したもの。実際の先頭は Opus が依頼文で伝える）
- 触ってよいファイル（この 11 個と報告書 docs/handoff/discord-server-management/impl-report-s2-2a2.md だけ）:
  - backend/app/services/discord_blueprint.py（§1）
  - backend/app/services/discord_blueprint_apply.py（§2）
  - backend/app/routers/discord_own_server.py（§3）
  - backend/app/routers/roles.py（§4。delete_role の 1 か所だけ）
  - backend/tests/conftest.py（§5。3 か所だけ）
  - backend/tests/test_discord_own_server_app_roles.py（新規・§6）
  - frontend/src/pages/admin/DiscordOwnServerPanel.tsx（§7）
  - frontend/src/pages/admin/DiscordOwnServerPanel.test.tsx（§7。試験を足すだけ）
  - frontend/src/locales/ja.json・frontend/src/locales/en.json（§8。`discordOwnServer` の中に足すだけ）
  - frontend/api-contract/openapi.json（§9。コマンドで作り直すだけ。手で書かない）
- 触らない: migrations・scripts・backend のほかのファイル（ほかの試験ファイルを含む）・docs/adr（Opus が直し済み）・.github・deploy.yml・本番

## 読んだ節（guards/）

- docs/handoff/design-partner-card-ops/guards/00-common.md：報告は生出力・推測で埋めない → 報告書に生出力を貼る形にした
- docs/handoff/design-partner-card-ops/guards/03-file.md：触るファイルを列挙 → 上の 11 個と報告書だけ
- docs/handoff/design-partner-card-ops/guards/05-pr.md：PR は Opus が作る → 実行役は push まで
- docs/handoff/design-partner-card-ops/guards/10-executor.md：作業前に preflight → 下の §0
- ADR-027（画面の文字は t() 経由・ja と en は同じキー）・ADR-144（画面の部品は金型）→ §7 は既にある DataTable・EmptyState だけを使い、新しい部品・色の直書き・CSS を足さない
- ADR-072（commit のあと reset_tenant_context）→ §3・§4 は既にある commit と reset の前に文を足すだけ。新しい commit を足さない

## 受領確認

作業を始める前に、報告書の先頭に次の 3 行を書く:
- 受領確認: card-s2-2a2-app-role-sync.md を読んだ
- origin/release/discord-own-server-s2-2a2 の先頭 sha（git rev-parse の生出力）
- 触るファイルは 11 個と報告書だけ、と理解した

## §0 準備

- リポジトリの根で `./scripts/dev/executor-preflight.sh` を流し、生出力を報告書に貼る
  - クラウドで動かすとき: [1/3] network と [2/3] gh auth の FAIL は起こるものとして、生出力を貼るだけで先へ進む。[3/3] git config user.name と [4/4] origin/main が OK でなければ停止して BLOCKED（2a-1 §0 と同じ扱い）
- `git fetch origin` のあと `release/discord-own-server-s2-2a2` を取り出す（新しく作らない）
- 次の「変更前」の行が今の実物と同じことを `grep -n` で確かめ、生出力を貼る。違えば「想定分岐」に従う
  - backend/app/services/discord_blueprint.py:235 `def build_plan(` ／ :291 `    for role in bp.roles:` ／ :362 `    # ---- 上書き（カテゴリ・チャンネル共通）` ／ :588-589 の `return {"changes": …, "actions": out_actions}`
  - backend/app/services/discord_blueprint_apply.py:78 `    for row, action in zip(plan["changes"], plan["actions"]):`
  - backend/app/routers/discord_own_server.py:200 `class OwnServerPlanResponse(BaseModel):` ／ :259 `async def _read_and_plan(` ／ :365 `        results = await apply_plan(plan, guild_id, bot_token)`
  - backend/app/routers/roles.py:359 `    await db.execute(text("DELETE FROM roles WHERE id = :id"), {"id": role_id})`
  - backend/tests/conftest.py:895 `                system_key TEXT,` ／ :1815 `        await conn.execute(text("DELETE FROM roles"))`

## 決まり（このカード全体）

- アプリの役割の行の key は `app_role:<役割の id>`。この文字の頭（`app_role:`）は §1 の定数 `APP_ROLE_KEY_PREFIX` 1 か所だけに書き、ほかのファイルはこの定数を import する（同じ文字を 2 か所に書かない）
- 設計図のロールの key は `^[a-z0-9_]+$`（コロンを含まない）なので、`app_role:` とぶつからない
- 確認の「指紋」（plan_digest）は今のまま changes・blocked・delete_candidates だけから作る。§1 で足す `app_roles` は指紋に入れない（`backend/tests/test_discord_own_server_plan.py:336-347` がこの形を確かめている）。アプリの役割の変化は changes・blocked の行に出るので指紋で守られる
- 反映は今のまま「作る・変えるだけで消さない」。`"DELETE"` という文字（二重引用符つき）を discord_own_server.py と discord_blueprint_apply.py に書かない（`backend/tests/test_discord_own_server_snapshot.py:261-262`・`backend/tests/test_discord_blueprint_apply.py:156` が確かめている）。`_ALLOWED_METHODS` は変えない
- 管理者の隠しロール（`TENANT_HIDDEN_SYSTEM_KEYS`）は、見る人が誰でも Discord の対象にしない（確認画面にも出さない）

## §1 backend/app/services/discord_blueprint.py

（１）`_action` の定義（:230-232）のすぐ下に、次を足す（1 文字も変えない）:

```python


# アプリの役割の行の key の頭（第2段 2a-2）。設計図の key は ^[a-z0-9_]+$ なのでぶつからない
APP_ROLE_KEY_PREFIX = "app_role:"
_HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


def hex_color_to_int(value: Any) -> int:
    """アプリの役割の色（'#RRGGBB'）を Discord の色の数にする。空や形が違うときは 0（色なし）。"""
    if isinstance(value, str) and _HEX_COLOR.match(value):
        return int(value[1:], 16)
    return 0


def _app_state(app: dict[str, Any], state: str, reason: str | None = None) -> dict[str, Any]:
    return {"role_id": int(app["id"]), "name": str(app["name"]), "state": state, "reason": reason}
```

（２）`build_plan` の引数の最後に `app_roles: list[dict[str, Any]] | None = None,` を足す（`bot_role_ids: Any,` の次の行）。docstring の下に 1 行足す: `    app_roles: アプリの役割（id・name・color・discord_role_id）。None なら今までと同じ結果（第2段 2a-2）。`（docstring の中の 2 行目として）

（３）:362 `    # ---- 上書き（カテゴリ・チャンネル共通）` の直前（設計図のロールの for の後）に、次を足す:

```python
    # ---- アプリの役割（第2段 2a-2・設計 S2-3 D2-1）。設計図のロールの後に見る
    app_role_states: list[dict[str, Any]] = []
    if app_roles is not None:
        bp_role_names = {role.name for role in bp.roles}
        linked_ids = {str(a["discord_role_id"]) for a in app_roles if a.get("discord_role_id")}
        d_roles_by_id = {str(r.get("id")): r for r in d_roles}
        for app in sorted(app_roles, key=lambda a: int(a["id"])):
            key = f"{APP_ROLE_KEY_PREFIX}{int(app['id'])}"
            name = str(app["name"])
            color = hex_color_to_int(app.get("color"))
            linked = str(app["discord_role_id"]) if app.get("discord_role_id") else None
            if name in bp_role_names:
                emit(0, _row("update_role", key, name, None, None, None), "name_in_blueprint")
                app_role_states.append(_app_state(app, "blocked", "name_in_blueprint"))
                continue
            if linked is not None:
                found = d_roles_by_id.get(linked)
                if found is None:
                    emit(0, _row("update_role", key, name, None, None, None), "app_role_missing_on_discord")
                    app_role_states.append(_app_state(app, "blocked", "app_role_missing_on_discord"))
                    continue
                if linked in used_roles:
                    emit(0, _row("update_role", key, name, None, None, None), "ambiguous")
                    app_role_states.append(_app_state(app, "blocked", "ambiguous"))
                    continue
                used_roles.add(linked)
                app_diffs: list[tuple[str, str, str]] = []
                if found.get("name") != name:
                    app_diffs.append(("name", str(found.get("name")), name))
                if _int(found.get("color")) != color:
                    app_diffs.append(("color", str(_int(found.get("color"))), str(color)))
                if not app_diffs:
                    app_role_states.append(_app_state(app, "unchanged"))
                    continue
                app_above = _int(found.get("position")) >= bot_top
                for field, before, after in app_diffs:
                    body = {"name": name} if field == "name" else {"colors": {"primary_color": color}}
                    emit(0, _row("update_role", key, name, field, before, after),
                         "role_above_bot" if app_above else None,
                         _action("PATCH", "/guilds/{guild}/roles/" + linked, body))
                if app_above:
                    app_role_states.append(_app_state(app, "blocked", "role_above_bot"))
                else:
                    app_role_states.append(_app_state(app, "update"))
                continue
            same = [r for r in d_roles if r.get("name") == name
                    and str(r.get("id")) not in used_roles and str(r.get("id")) not in linked_ids]
            if len(same) > 1:
                used_roles.update(str(r.get("id")) for r in same)
                emit(0, _row("update_role", key, name, None, None, None), "ambiguous")
                app_role_states.append(_app_state(app, "blocked", "ambiguous"))
                continue
            if same:
                fid = str(same[0].get("id"))
                used_roles.add(fid)
                emit(0, _row("link_role", key, name, None, None, fid), None,
                     _action("DB", "", {"discord_role_id": fid}))
                app_role_states.append(_app_state(app, "link"))
                continue
            emit(0, _row("create_role", key, name, None, None, f"name={name}; color={color}"), None,
                 _action("POST", "/guilds/{guild}/roles",
                         {"name": name, "permissions": "0", "colors": {"primary_color": color},
                          "hoist": False, "mentionable": False}, key))
            app_role_states.append(_app_state(app, "create"))

```

- 意味: つないだロールは名前と色だけを比べる（権限・並び順・表示は人が Discord で決めるので触らない）。つないでいない役割は、ほかで使っていない同じ名前のロールが 1 つならそれにつなぐ（Discord には送らず、反映のときにアプリの側に番号を書くだけ）。0 なら作る。2 つ以上なら止める（KGI-11）
- つなぐ行の色の違いは、つないだあとの次の確認で「色を変える」として出る（1 回の反映で 2 つのことをしない）

（４）最後の `return {...}`（:588-589）を、次に置き換える:

```python
    out: dict[str, Any] = {"changes": out_changes, "blocked": out_blocked, "delete_candidates": out_deletes,
                           "plan_digest": digest, "actions": out_actions}
    if app_roles is not None:
        out["app_roles"] = app_role_states
    return out
```

- `app_roles` を渡さないときの戻り値は、今と 1 文字も同じ（既存の試験はそのまま通る）

## §2 backend/app/services/discord_blueprint_apply.py

`for row, action in zip(plan["changes"], plan["actions"]):`（:78）の直後、`if action.get("method") not in _ALLOWED_METHODS:` の前に、次を足す:

```python
        if action.get("method") == "DB":
            # アプリの側に番号を書くだけの行（第2段 2a-2 のロールをつなぐ）。Discord には送らない
            results.append(_result(row, "success", discord_id=str(action["json"]["discord_role_id"])))
            continue
```

- `_ALLOWED_METHODS` は変えない。`method=` の引数の数（1 つ）は変えない

## §3 backend/app/routers/discord_own_server.py

（１）import（:35-36）を次にする:

```python
from app.auth.system_roles import TENANT_HIDDEN_SYSTEM_KEYS
from app.routers.roles import _visible_role_sql, _visible_text
from app.services.discord_blueprint import (
    APP_ROLE_KEY_PREFIX,
    Blueprint,
    blueprint_path,
    build_plan,
    load_blueprint,
)
from app.services.discord_blueprint_apply import apply_plan
```

- `app.routers.roles` からの import は `backend/app/routers/staff.py:33` と同じ形（隠しロールの条件を 1 か所に保つため。同じ条件を書き写さない）
- ruff の import 並び（isort）に合わせて並べ替えが要るなら `ruff check --fix` で並べるだけにする

（２）`OwnServerPlanResponse`（:200）の直前に次を足し、`OwnServerPlanResponse` の最後に `app_roles: list[AppRoleState] = []` を足す:

```python
class AppRoleState(BaseModel):
    role_id: int
    name: str
    state: str
    reason: str | None = None
```

（３）`check_own_server_plan` の中:
- `plan = await _read_and_plan(guild_id, blueprint, bot_token)` を `plan = await _read_and_plan(db, guild_id, blueprint, bot_token)` にする
- `return OwnServerPlanResponse(` の引数に `app_roles=plan.get("app_roles", []),` を足す

（４）`_read_and_plan` を `async def _read_and_plan(db: AsyncSession, guild_id: str, blueprint: Blueprint, bot_token: str) -> dict[str, Any]:` にし、docstring を「Discord を GET で 4 回読み、アプリの役割を DB から読み、設計図との差（build_plan の戻り値）を返す。」にする。最後の 2 行（`bot_role_ids = …` と `return build_plan(...)`）を次にする:

```python
    bot_role_ids = [str(r) for r in (member.get("roles") or [])]
    # アプリの役割（第2段 2a-2）。管理者の隠しロールは見る人が誰でも Discord の対象にしない
    app_result = await db.execute(
        _visible_text(f"SELECT id, name, color, discord_role_id FROM roles WHERE {_visible_role_sql()} ORDER BY id"),
        {"show_hidden": False, "hidden_keys": sorted(TENANT_HIDDEN_SYSTEM_KEYS)},
    )
    app_roles = [dict(r) for r in app_result.mappings().all()]
    return build_plan(blueprint, roles, channels, guild_id, bot_role_ids, app_roles=app_roles)
```

（５）`_apply_insert_sql` の定義の直前に次を足す:

```python
_APP_ROLE_WRITE_KINDS = ("create_role", "link_role")


async def _write_back_app_roles(db: AsyncSession, results: list[dict[str, Any]]) -> int:
    """反映で作った・見つけたロールの番号をアプリの役割に書く（第2段 2a-2）。書いた数を返す。

    既に番号がある役割は書き換えない。その番号を「消した番号の表」から外す（つなぎ直したロールを外さないため）。
    """
    written = 0
    for x in results:
        key = str(x.get("key") or "")
        if (x.get("status") != "success" or x.get("kind") not in _APP_ROLE_WRITE_KINDS
                or not key.startswith(APP_ROLE_KEY_PREFIX) or not x.get("discord_id")):
            continue
        role_id = int(key[len(APP_ROLE_KEY_PREFIX):])
        res = await db.execute(
            text("UPDATE roles SET discord_role_id = :did WHERE id = :rid AND discord_role_id IS NULL"),
            {"did": str(x["discord_id"]), "rid": role_id},
        )
        written += int(res.rowcount or 0)
        await db.execute(
            text("DELETE FROM discord_retired_roles WHERE discord_role_id = :did"),
            {"did": str(x["discord_id"])},
        )
    return written
```

- 注意: 文の中の `DELETE FROM` は二重引用符の直後に空白が続くので、`"DELETE"` の点検には当たらない。`"DELETE"` だけの文字は書かない

（６）`apply_own_server_plan` の中:
- `plan = await _read_and_plan(guild_id, blueprint, bot_token)` を `plan = await _read_and_plan(db, guild_id, blueprint, bot_token)` にする
- `results = await apply_plan(plan, guild_id, bot_token)` の次の行に `app_roles_written = await _write_back_app_roles(db, results)` を足す（反映の記録の INSERT・監査・commit と同じ 1 回の commit に入る。新しい commit は足さない）
- `record_audit_log(` の `new_data=counts,` を `new_data={**counts, "app_roles_written": app_roles_written},` にする

## §4 backend/app/routers/roles.py（delete_role の 1 か所だけ）

:359 `    await db.execute(text("DELETE FROM roles WHERE id = :id"), {"id": role_id})` の直前に、次を足す:

```python
    # 第2段 2a-2: つないでいた Discord のロールの番号を「消した番号の表」へ移す（点検がその番号のロールを登録した人から外す・設計 S2-3 D2-3）
    await db.execute(
        text(
            "INSERT INTO discord_retired_roles (discord_role_id)"
            " SELECT discord_role_id FROM roles WHERE id = :id AND discord_role_id IS NOT NULL"
            " ON CONFLICT (discord_role_id) DO NOTHING"
        ),
        {"id": role_id},
    )
```

- 監査（record_audit_log）・commit・reset は今のまま（同じ 1 回の commit に入る）

## §5 backend/tests/conftest.py（3 か所だけ）

（１）roles の CREATE TABLE の `                system_key TEXT,`（:895）の次の行に `                discord_role_id TEXT,` を足す

（２）roles の CREATE TABLE の文（`""")` と `))` で閉じる所。:900）の直後、role_permissions の CREATE TABLE の前に、次を足す（本番は migrations/20261106_150000 と tenant.py。SQLite は文字と時刻で持つ）:

```python
        # discord-server-management 第2段 2a-1: つないだロールの番号はテナント内で一意・消した番号の表
        await conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_roles_discord_role_id"
            " ON roles (discord_role_id) WHERE discord_role_id IS NOT NULL"
        ))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS discord_retired_roles (
                discord_role_id TEXT PRIMARY KEY,
                retired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
```

（３）:1815 `        await conn.execute(text("DELETE FROM roles"))` の直前に `        await conn.execute(text("DELETE FROM discord_retired_roles"))` を足す

- `scripts/check_test_schema_dup.py` は conftest.py を対象外にしている（同ファイル `EXCLUDE_FILES`）。新しい試験ファイルには CREATE TABLE を書かない

## §6 backend/tests/test_discord_own_server_app_roles.py（新規）

- 道具立て（engine・factory・perms・world・discord_mock・write_mock・redis_holder・bp_file・client・_insert_config）は `backend/tests/test_discord_own_server_apply.py:1-230` と同じ形で、このファイルの中に書く（ほかの試験ファイルを import しない・変えない）。違うのは次だけ:
  - テナントの番号は 7 のまま（既存と同じ。試験はテナントごとに順に動く）
  - engine の前後の片付けに `DELETE FROM user_roles`・`DELETE FROM role_permissions`・`DELETE FROM discord_retired_roles`・`DELETE FROM roles` を足す（この順）
  - 役割は試験の中で `INSERT INTO roles (id, tenant_id, name, color, priority, is_system, system_key, discord_role_id) VALUES (...)` で入れる
- 純粋な試験（build_plan を直接呼ぶ。Discord の返事は辞書で作る。Bot のロールは position 10、ほかのロールは position 1。設計図はロール `everyone` だけのもの）。各 1 つずつ、次の名前で書く:
  1. `test_app_role_none_keeps_plan_identical`：`app_roles` を渡さない結果と、渡さない今までの結果が `==` で同じで、`"app_roles"` の key が無い
  2. `test_app_role_create_when_no_same_name`：つないでいない「営業」・Discord に同じ名前なし → changes に kind `create_role`・key `app_role:<id>` が 1 行、actions の該当は POST `/guilds/{guild}/roles`・body の permissions は `"0"`・creates は `app_role:<id>`。app_roles は state `create`
  3. `test_app_role_link_when_one_same_name`：同じ名前のロールが 1 つ → kind `link_role`・after がそのロールの番号・action の method は `"DB"`。そのロールは delete_candidates に出ない。state `link`
  4. `test_app_role_ambiguous_blocks_and_sends_nothing`（KGI-11）：同じ名前が 2 つ → blocked に reason `ambiguous` が 1 行、changes にその key の行が 0 行、2 つのロールは delete_candidates に出ない。state `blocked`
  5. `test_app_role_rename_patches_same_id`（KGI-10a）：discord_role_id=<A>・Discord の A の名前は「営業」・アプリは「セールス」→ changes は field `name`・before「営業」・after「セールス」の 1 行だけ、action は PATCH `/guilds/{guild}/roles/<A>`、POST の行は 0。state `update`
  6. `test_app_role_color_patch`：色だけ違う（アプリ `#ff0000`・Discord 0）→ field `color`・body `{"colors": {"primary_color": 16711680}}`
  7. `test_app_role_unchanged`（KGI-8）：名前も色も同じ役割 2 つ → changes 0 行・app_roles の数 2・どちらも state `unchanged`
  8. `test_app_role_linked_missing_on_discord`：discord_role_id の番号が Discord に無い → reason `app_role_missing_on_discord`
  9. `test_app_role_name_in_blueprint`：設計図のロールと同じ名前（設計図に `staff` という名前のロールを足した形で）→ reason `name_in_blueprint`
  10. `test_app_role_above_bot_is_blocked`：つないだロールの position が Bot と同じ 10 で名前が違う → blocked に reason `role_above_bot`、changes に 0 行
  11. `test_app_role_name_search_skips_linked_ids`：役割 X が番号 A につながっていて、つないでいない役割 Y の名前が A の今の名前と同じ → Y は `create`（A につながない）
  12. `test_hex_color_to_int`：`"#6c757d"`→7108989、`None`→0、`"red"`→0
- 反映の係の試験:
  13. `test_apply_db_row_does_not_call_discord`：changes 1 行（link_role）・actions 1 行（method `"DB"`）で `apply_plan` を呼ぶと、Discord を呼ぶ関数（discord_api_request を monkeypatch した物）が 0 回、結果は status `success`・discord_id がその番号
- 画面の口の試験（client で叩く）:
  14. `test_plan_lists_app_roles_without_hidden_admin`：役割を 3 つ入れる（「営業」・「事務」・system_key `admin` の「管理者」）→ GET plan の `app_roles` は 2 件で、名前は「営業」「事務」だけ
  15. `test_apply_writes_discord_role_id_for_create_and_link`：「営業」（Discord に無い）・「事務」（Discord に同じ名前が 1 つ、番号 <B>）、`discord_retired_roles` に <B> を 1 行入れておく → 確認 → 反映 → roles の「営業」の discord_role_id が write_mock の返した番号（901 から）、「事務」が <B>。`discord_retired_roles` に <B> が無い。write_mock の呼ばれた回数は 1（POST だけ）
  16. `test_second_check_after_apply_is_unchanged`：15 のあと world に作ったロールを足してから（write_mock の返事を world のロールに足す形で）もう一度確認 → 2 件とも state `unchanged`・changes 0 行
  17. `test_delete_role_moves_linked_id_to_retired`：discord_role_id のある役割を `DELETE /api/v1/roles/<id>` で消す → `discord_retired_roles` に 1 行。つないでいない役割を消す → 0 行のまま。（roles の削除は `roles.delete` の権限と priority の点検がある。`backend/tests/test_roles.py` の削除の試験の準備の仕方をそのまま使う。分からなければ BLOCKED:）

## §7 frontend/src/pages/admin/DiscordOwnServerPanel.tsx（・同じ名前の .test.tsx）

（１）`interface OwnServerPlan` の前に次を足し、`OwnServerPlan` に `app_roles: AppRoleState[];` を足す:

```tsx
interface AppRoleState {
  role_id: number;
  name: string;
  state: string;
  reason?: string | null;
}
```

（２）`const deleteColumns = [ … ];` の次に足す:

```tsx
  const appRoleColumns = [
    { key: "name", header: t("discordOwnServer.col.name") },
    {
      key: "state",
      header: t("discordOwnServer.col.appRoleState"),
      renderCell: (row: AppRoleState) => t(`discordOwnServer.appRoleState.${row.state}`),
    },
    {
      key: "reason",
      header: t("discordOwnServer.col.reason"),
      renderCell: (row: AppRoleState) => (row.reason ? t(`discordOwnServer.reason.${row.reason}`) : ""),
    },
  ];
```

（３）`{plan && (` の中の `<div className="dc-result">` の直後（「変わる」の群の前）に足す:

```tsx
          <div className="dc-group">
            <h4 className="dc-group-title">{t("discordOwnServer.appRolesTitle", { count: plan.app_roles.length })}</h4>
            <DataTable<AppRoleState>
              columns={appRoleColumns}
              data={plan.app_roles}
              rowKey={(row) => `app_role:${row.role_id}`}
              emptyState={emptyRows}
            />
          </div>
```

- 新しい部品・CSS・色の値を足さない（既にある `dc-group`・`dc-group-title`・DataTable・EmptyState だけ）
- .test.tsx: 既にある確認の試験の返事（plan の模型）に `app_roles` を足し（既存の試験の模型には `app_roles: []`）、新しい試験を 1 つ足す: `app_roles` に「営業」state `create` と「事務」state `blocked` reason `ambiguous` を返すと、画面に「アプリの役割（2 件）」「作る」「できない」「同じ名前の物が 2 つ以上あります」が出る（i18n は試験の既存のやり方に合わせる）

## §8 frontend/src/locales/ja.json・en.json（`discordOwnServer` の中に足すだけ）

| 場所 | ja | en |
|---|---|---|
| `kind.link_role` | ロールをつなぐ | Link role |
| `reason.name_in_blueprint` | 設計図に同じ名前のロールがあります | The blueprint has a role with the same name |
| `reason.app_role_missing_on_discord` | つないでいたロールが Discord で消されています | The linked role was deleted on Discord |
| `appRolesTitle` | アプリの役割（{{count}} 件） | App roles ({{count}}) |
| `appRoleState.create` | 作る | Create |
| `appRoleState.link` | つなぐ | Link |
| `appRoleState.update` | 変える | Change |
| `appRoleState.unchanged` | 変わらない | No change |
| `appRoleState.blocked` | できない | Cannot |
| `col.appRoleState` | Discord では | On Discord |

- 既にあるキーと値は変えない。ja と en のキーは同じにする

## §9 frontend/api-contract/openapi.json

- `cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json` で作り直す（`.github/workflows/api-contract-check.yml:35` と同じ）。手で書かない
- `git diff --stat frontend/api-contract/openapi.json` の生出力を貼る。`AppRoleState` と `OwnServerPlanResponse` の `app_roles` 以外の所が変わっていたら、停止して NEEDS_DECISION: と diff の要約（変わった schema の名前の一覧）

## §10 確かめ（生出力を報告書に貼る）

- `cd backend && python -m pytest tests/test_discord_own_server_app_roles.py tests/test_discord_own_server_plan.py tests/test_discord_own_server_apply.py tests/test_discord_blueprint_apply.py tests/test_discord_own_server_snapshot.py tests/test_roles.py tests/test_roles_hidden_system_admin.py tests/test_role_assignment.py -q -p no:cacheprovider --no-cov`（すべて passed）
- `cd backend && ruff check app/services/discord_blueprint.py app/services/discord_blueprint_apply.py app/routers/discord_own_server.py app/routers/roles.py tests/conftest.py tests/test_discord_own_server_app_roles.py`
- `BASE_SHA=$(git merge-base origin/main HEAD) HEAD_SHA=HEAD python3 scripts/check_test_schema_dup.py` の rc=0
- `cd frontend && npx vitest run src/pages/admin/DiscordOwnServerPanel.test.tsx`（すべて passed）
- `cd frontend && npx tsc --noEmit -p .` の rc=0（重ければ `npm run typecheck` 等、package.json にある型の点検。どれを流したか書く）
- `cd frontend && npx eslint src/pages/admin/DiscordOwnServerPanel.tsx src/pages/admin/DiscordOwnServerPanel.test.tsx`
- i18n の点検: `frontend/CLAUDE.md` の grep のセルフチェックを §7 のファイルに流す。ja と en のキーが同じかを `node -e` で `discordOwnServer` の下のキーの一覧を比べて確かめる
- `grep -c '"DELETE"' backend/app/routers/discord_own_server.py backend/app/services/discord_blueprint_apply.py`（どちらも 0）
- `grep -rn '"app_role:"' backend/app`（discord_blueprint.py の 1 行だけ）
- `git diff --name-only origin/main...HEAD`（Opus の文書 4 つ［このカード・ADR-091・docs/adr/README.md・台帳］＋触ってよい 11 個＋報告書であること）

## §11 保存

- commit の文: `feat(discord): アプリの役割を確認画面に出し、反映でロールを作る・つなぐ・名前と色を変える／役割を消したら番号を消した番号の表へ移す（discord-server-management 第2段 2a-2）`
- commit のあと `git log --oneline -3` の生出力を報告書に貼る
- `git push origin release/discord-own-server-s2-2a2`（単独で流す）。PR は作らない（Opus が作る）
- 報告書の最後に、push 後の `git rev-parse HEAD` の生出力

## 想定分岐（停止の条件）

- preflight が失敗した → 停止。BLOCKED: と生出力（クラウドでは [1/3][2/3] の FAIL を除く。§0 のとおり）
- §0 の「変更前」の行が違う（ほかの PR が先に変えた）→ 書いてある文で同じ場所が一意に見つかればそこに足し、報告書に実際の行番号を書く。見つからない・2 か所あるなら停止。NEEDS_DECISION: と前後 10 行
- 既存の試験（§10 の 1 行目のうち、新しいファイル以外）が落ちた → 新しい挙動に合わせて既存の試験を書き換えない。停止して BLOCKED: と生出力。ただし既存の試験の模型に `app_roles` が無いために frontend の型の点検が落ちる所は、§7 のとおり `app_roles: []` を足してよい
- SQLite で `INSERT … SELECT … ON CONFLICT` が通らない → roles.py の文を変えずに停止。BLOCKED: と生出力（本番は PostgreSQL 16 で通る文。試験の側の事情なので Opus が決める）
- `from app.routers.roles import …` で循環 import の誤りが出た → 停止。BLOCKED: と生出力（隠しロールの条件を書き写さない）
- openapi.json の差が §9 の範囲を超える → 停止。NEEDS_DECISION:
- 触ってよいファイル以外を変えたくなった → 変えずに停止。NEEDS_DECISION: と理由
- push が拒否された → 言い換えて再試行しない。停止して BLOCKED: と生出力

報告の最後の行は DONE / BLOCKED: 理由 / NEEDS_DECISION: 理由 のどれか 1 つ。

END OF CARD
