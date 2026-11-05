# 実装カード: 便3a 設計図の形と検査・最初の設計図・確認（差分を出す）・画面の「確認する」

- 設計: docs/handoff/discord-server-management/design.md §4-5・§4-7・§4-9（「確認する」と 3 つの一覧だけ）・§5・§8 改訂4
- PO 承認: 「1」（2026-11-04、この設計で承認）。「1」（2026-11-05、次の段階の設計に進む）。便2 は 2026-11-05 に本番反映済み・読み取り 1 行（ロール 2・チャンネル 4）を Opus が本番の読み取りで確かめた
- ブランチ: release/discord-own-server-bin3（origin/main 63cadad20 にこのカードと設計の改訂4を足したもの。実際の先頭は Opus が依頼文で伝える）
- 実物の行番号はすべて origin/main 63cadad20 で Opus が読んで確かめたもの
- この便は Discord に書かない。呼ぶのは GET だけ。DB にも書かない。migrations なし

## 触ってよいファイル（これと報告書 docs/handoff/discord-server-management/impl-report-bin3a.md だけ）

プログラム:
- backend/app/services/discord_blueprint.py（新規）
- backend/app/discord_blueprints/tenant_1.json（新規・中身は §2 をそのまま）
- `backend/app/routers/discord_own_server.py`（§3 の API を足すだけ。今の読み取りの関数は 1 文字も変えない）

試験:
- backend/tests/test_discord_blueprints.py（新規）
- backend/tests/test_discord_own_server_plan.py（新規）

画面:
- `frontend/src/pages/admin/DiscordOwnServerPanel.tsx`
- `frontend/src/pages/admin/DiscordOwnServerPanel.test.tsx`（試験を足すだけ。今の試験は消さない）
- `frontend/src/locales/ja.json`・`frontend/src/locales/en.json`（§5-2 のキーだけ）
- `frontend/api-contract/openapi.json`（生成した結果だけ。手で書かない）

触らない: `.github/` の全部・migrations の全部・`scripts/` の全部・`backend/app/main.py`（ルーターは登録済み）・`backend/app/realtime/topics.py`（GET は対応表の対象外。`backend/tests/test_realtime_topics.py:26-29` は書き込みの方法だけを数える）・`backend/tests/conftest.py`・`frontend/src/components/` の金型・CSS ファイル（新しい CSS を作らない）・`DiscordConfigPage.tsx`・本番

## 読んだ節（guards/）

- docs/handoff/design-partner-card-ops/guards/00-common.md：報告は生出力・推測で埋めない
- docs/handoff/design-partner-card-ops/guards/03-file.md：触るファイルを列挙 → 上の一覧だけ
- docs/handoff/design-partner-card-ops/guards/05-pr.md：PR は Opus が作る → 実行役は push まで
- docs/handoff/design-partner-card-ops/guards/10-executor.md：作業前に preflight → 下の §0
- 便1b・便2 の教訓：試験の中に表の定義を書かない（この便の試験は DB の表を作らない。登録の表は conftest の今の SQLite 版を使う）

## 受領確認

作業を始める前に、報告書の先頭に次の 3 行を書く:
- 受領確認: card-bin3a-blueprint-plan.md を読んだ
- origin/release/discord-own-server-bin3 の先頭 sha（git rev-parse の生出力）
- 触るファイルは上の一覧と報告書だけ、と理解した

## §0 準備

- リポジトリの根で `./scripts/dev/executor-preflight.sh` を流し、生出力を報告書に貼る
  - クラウドでは [1/3] network と [2/3] gh auth の FAIL は起こるものとして、生出力を貼るだけで先へ進む。[3/3] と [4/4] が OK でなければ停止して BLOCKED:
- `git fetch origin` のあと `release/discord-own-server-bin3` を取り出す（新しく作らない）

## §1 設計図の形と比べ方 backend/app/services/discord_blueprint.py（新規）

### §1-1 権限の名前の表（この 1 か所だけに置く・設計 §4-5）

出典: Discord 公式 github.com/discord/discord-api-docs `developers/topics/permissions.mdx`（e3ea58903、2026-10-29 更新）の表。次の 52 個をそのまま `PERMISSION_BITS: dict[str, int]`（名前 → 何番目のビット）にする。47 番は無い。

```
CREATE_INSTANT_INVITE 0, KICK_MEMBERS 1, BAN_MEMBERS 2, ADMINISTRATOR 3, MANAGE_CHANNELS 4, MANAGE_GUILD 5,
ADD_REACTIONS 6, VIEW_AUDIT_LOG 7, PRIORITY_SPEAKER 8, STREAM 9, VIEW_CHANNEL 10, SEND_MESSAGES 11,
SEND_TTS_MESSAGES 12, MANAGE_MESSAGES 13, EMBED_LINKS 14, ATTACH_FILES 15, READ_MESSAGE_HISTORY 16,
MENTION_EVERYONE 17, USE_EXTERNAL_EMOJIS 18, VIEW_GUILD_INSIGHTS 19, CONNECT 20, SPEAK 21, MUTE_MEMBERS 22,
DEAFEN_MEMBERS 23, MOVE_MEMBERS 24, USE_VAD 25, CHANGE_NICKNAME 26, MANAGE_NICKNAMES 27, MANAGE_ROLES 28,
MANAGE_WEBHOOKS 29, MANAGE_GUILD_EXPRESSIONS 30, USE_APPLICATION_COMMANDS 31, REQUEST_TO_SPEAK 32,
MANAGE_EVENTS 33, MANAGE_THREADS 34, CREATE_PUBLIC_THREADS 35, CREATE_PRIVATE_THREADS 36,
USE_EXTERNAL_STICKERS 37, SEND_MESSAGES_IN_THREADS 38, USE_EMBEDDED_ACTIVITIES 39, MODERATE_MEMBERS 40,
VIEW_CREATOR_MONETIZATION_ANALYTICS 41, USE_SOUNDBOARD 42, CREATE_GUILD_EXPRESSIONS 43, CREATE_EVENTS 44,
USE_EXTERNAL_SOUNDS 45, SEND_VOICE_MESSAGES 46, SET_VOICE_CHANNEL_STATUS 48, SEND_POLLS 49,
USE_EXTERNAL_APPS 50, PIN_MESSAGES 51, BYPASS_SLOWMODE 52
```

- `KNOWN_MASK` = 上の全ビットの和
- `names_to_bits(names: list[str]) -> int`（表に無い名前は ValueError）
- `bits_to_names(value: int) -> list[str]`（表にあるビットだけ。並びは表の順。表に無いビットは捨てる）
- 表に無いビット（例 1<<47）は比べない。設計 改訂4

### §1-2 設計図の形（pydantic v2・余分な項目は拒否 `model_config = ConfigDict(extra="forbid")`）

```
Blueprint:   version: Literal[1]; roles: list[BpRole]; categories: list[BpCategory]; channels: list[BpChannel]
BpRole:      key: str; discord_id: str | None = None; name: str; color: int = 0; hoist: bool = False;
             mentionable: bool = False; permissions: list[str] = []
BpOverwrite: target: str; allow: list[str] = []; deny: list[str] = []
BpCategory:  key: str; discord_id: str | None = None; name: str; overwrites: list[BpOverwrite] = []
BpChannel:   key: str; discord_id: str | None = None; name: str; type: Literal["text"];
             category: str | None = None; topic: str | None = None; overwrites: list[BpOverwrite] = []
```

検査（`load_blueprint` で全部確かめ、1 つでも外れたら ValueError。理由の文に key を入れる）:
1. key は roles・categories・channels を通して重ならない。key は `^[a-z0-9_]+$`
2. `discord_id` は数字だけの文字、または roles の 1 つだけ `"@everyone"`。`"@everyone"` のロールは `name` も `"@everyone"`
3. 権限の名前（permissions・allow・deny）は §1-1 の表にある。同じ上書きで allow と deny に同じ名前を置かない
4. 上書きの `target` は `"@everyone"`・`"@bot"`・`"role:<roles の key>"` のどれか。同じ物の中で target は重ならない
5. チャンネルの `category` は categories の key
6. @everyone の VIEW_CHANNEL を deny する上書きがある物には、`"@bot"` の allow に VIEW_CHANNEL がある（設計 改訂4）
7. 文字のチャンネルの `name` に空白・英大文字を入れない（Discord が文字のチャンネル名を小文字・ハイフンに直すため。直された名前と比べて「変わる」が出続けるのを防ぐ）

関数:
- `BLUEPRINT_DIR = Path(__file__).resolve().parents[1] / "discord_blueprints"`
- `blueprint_path(tenant_id: int) -> Path` → `BLUEPRINT_DIR / f"tenant_{tenant_id}.json"`
- `load_blueprint(path: Path) -> Blueprint`（JSON を読み、形と §1-2 の検査）

### §1-3 比べ方 `build_plan(bp, roles, channels, guild_id, bot_role_ids) -> dict`

入力は Discord の返事そのもの（`GET /guilds/{g}/roles`・`GET /guilds/{g}/channels`）と、Bot のロールの番号の集まり。純粋な関数（Discord も DB も呼ばない）にする。

前処理:
- @everyone のロール＝番号が `guild_id` と同じロール
- Bot の権限 `bot_perms` ＝ @everyone と `bot_role_ids` のロールの permissions の和。ADMINISTRATOR（1<<3）が立っていれば `bot_admin=True`
- Bot の順番 `bot_top` ＝ `bot_role_ids` のロールの position の最大（無ければ 0）
- `"@bot"` の相手＝ `bot_role_ids` のうち managed=true のロール（1 つ。無ければ「@bot を使う行」はすべて blocked・理由 `bot_role_missing`）
- 扱う Discord の物：managed=false のロール、type 4 のカテゴリ、type 0 のチャンネル。ほかの種類と managed=true のロールはどの一覧にも出さない（設計 改訂4）

突き合わせ（設計 §4-5）:
- `discord_id` があればそれで探す（`"@everyone"` は @everyone のロール）。設計図に discord_id があるのに Discord に無い → blocked・理由 `missing_on_discord`（作り直さない）
- 無ければ ロールは name、カテゴリは name＋type 4、チャンネルは name＋type 0＋親（親のカテゴリが見つかった時だけ。親が新しく作る物なら「無い」）で探す（`backend/app/routers/discord_auto_setup.py:478-502` と同じ見分け方）。同じ条件の物が 2 つ以上 → blocked・理由 `ambiguous`

行の作り方（1 行の単位は設計 改訂4）。行は dict で `{"kind", "key", "name", "field", "before", "after"}`、blocked はこれに `"reason"`:

| kind | 起きるとき | field | before / after |
|---|---|---|---|
| create_role | 設計図のロールが Discord に無い | null | null / 設計図の中身の要約（名前・色・表示・メンション・権限の名前の並び） |
| update_role | 見つかったロールの name・color・hoist・mentionable・permissions が違う | 違う項目の名前（1 項目 1 行） | 今の値 / 設計図の値（permissions は名前の並び。比べるのは KNOWN_MASK の中だけ） |
| create_category | カテゴリが Discord に無い | null | null / 名前と上書きの要約 |
| update_category | name が違う | "name" | 今 / 設計図 |
| create_channel | チャンネルが Discord に無い | null | null / 名前・親・話題・上書きの要約 |
| update_channel | name・topic・親が違う（topic は null と "" を同じとみなす） | "name" / "topic" / "parent" | 今 / 設計図（親はカテゴリの名前で出す） |
| update_overwrite | 見つかった物の上書きが、設計図に書いた相手で違う（Discord に無い相手は allow 0・deny 0 とみなす。比べるのは KNOWN_MASK の中だけ） | "overwrite:<target>" | 今の allow/deny の名前 / 設計図の allow/deny の名前 |

blocked にする行（changes には入れない。理由はこの語で返す。画面で日本語に直す）:
- `role_above_bot`：update_role の相手の position が `bot_top` 以上
- `everyone_name`：@everyone の name を変える行
- `permission_bot_lacks`：`bot_admin` でなく、ロールの作る/直す後の権限、または上書きの allow|deny に、`bot_perms` に無いビットがある
- `overwrite_manage_roles`：`bot_admin` でなく、上書きの allow か deny に MANAGE_ROLES がある（Discord 公式 guild.mdx Create Guild Channel の注記）
- `bot_role_missing`・`missing_on_discord`・`ambiguous`：上の前処理・突き合わせのとおり

消す候補 `delete_candidates`（`{"kind": "role"|"category"|"channel"|"overwrite", "discord_id", "name", "parent_name", "target"}`）:
- 突き合わせで使われなかった managed=false のロール（@everyone を除く）・type 4・type 0
- 見つかった物の上書きのうち、設計図に書いていない相手（相手が @everyone・`"@bot"` のロール・managed=false のロールのとき。ほかの managed のロールは出さない）。`target` は `"@everyone"`・`"@bot"`・ロールの名前

戻り値: `{"changes": [...], "blocked": [...], "delete_candidates": [...], "plan_digest": <下>}`
- 並び：changes と blocked は ロール → カテゴリ → チャンネル → 上書き の順、その中は設計図の順。delete_candidates は ロール → カテゴリ → チャンネル → 上書き、その中は Discord の番号の順
- `plan_digest` ＝ `hashlib.sha256(json.dumps({"changes":…, "blocked":…, "delete_candidates":…}, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()`
- 戻り値と行の中に サーバーの番号（guild_id）を入れない（@everyone は `"@everyone"`）

## §2 最初の設計図 backend/app/discord_blueprints/tenant_1.json（新規）

本番の読み取り（`ai_ro.public__discord_server_snapshots` id=1）から Opus が作った。そのまま置く（1 文字も変えない）。@everyone の権限は表にあるビットだけを名前にした（1<<47 は表に無いので書かない）。Bot のロール（managed）と声のチャンネルは書かない（設計 改訂4）。

```json
{
  "version": 1,
  "roles": [
    {
      "key": "everyone",
      "discord_id": "@everyone",
      "name": "@everyone",
      "color": 0,
      "hoist": false,
      "mentionable": false,
      "permissions": [
        "CREATE_INSTANT_INVITE", "ADD_REACTIONS", "STREAM", "VIEW_CHANNEL", "SEND_MESSAGES",
        "EMBED_LINKS", "ATTACH_FILES", "READ_MESSAGE_HISTORY", "MENTION_EVERYONE", "USE_EXTERNAL_EMOJIS",
        "CONNECT", "SPEAK", "USE_VAD", "CHANGE_NICKNAME", "USE_APPLICATION_COMMANDS", "REQUEST_TO_SPEAK",
        "CREATE_PUBLIC_THREADS", "CREATE_PRIVATE_THREADS", "USE_EXTERNAL_STICKERS", "SEND_MESSAGES_IN_THREADS",
        "USE_EMBEDDED_ACTIVITIES", "USE_SOUNDBOARD", "CREATE_GUILD_EXPRESSIONS", "CREATE_EVENTS",
        "USE_EXTERNAL_SOUNDS", "SEND_VOICE_MESSAGES", "SET_VOICE_CHANNEL_STATUS", "SEND_POLLS", "USE_EXTERNAL_APPS"
      ]
    }
  ],
  "categories": [
    {"key": "text_cat", "discord_id": "1567709769337409726", "name": "テキストチャンネル", "overwrites": []},
    {"key": "voice_cat", "discord_id": "1567709769337409727", "name": "ボイスチャンネル", "overwrites": []}
  ],
  "channels": [
    {"key": "general", "discord_id": "1567709769337409728", "name": "一般", "type": "text",
     "category": "text_cat", "topic": null, "overwrites": []}
  ]
}
```

確かめ（Opus が手で照合した結果。試験 §4-1 の 6 で機械にも確かめさせる）: @everyone の permissions 2248473465835073 の立っているビットは 0,6,9,10,11,14,15,16,17,18,20,21,25,26,31,32,35,36,37,38,39,42,43,44,45,46,47,48,49,50。47 を除く 29 個が上の並び。

## §3 確認の API（`backend/app/routers/discord_own_server.py` に足す）

- `GET /admin/discord/own-server/plan`、`dependencies=[Depends(require_permission("tenant.profile.edit"))]`（設計 改訂4）
- 手順:
  1. 自社用の guild_id を読む（今の読み取りの関数 111-121 行と同じ SQL。無ければ 422・同じ文）
  2. 設計図のファイルが無ければ 404「設計図がまだありません。」。読めない・検査に外れたら 500 にせず 422「設計図の形が正しくありません。」（理由の文はログに出す。返事には出さない）
  3. Bot の鍵（今と同じ・無ければ 503）
  4. Discord を GET で 4 回読む：`/guilds/{g}/roles`・`/guilds/{g}/channels`・`/users/@me`・`/guilds/{g}/members/{bot の id}`（全部 `discord_api_request`・`expected_statuses=(200,)`。失敗は 502「Discord から読み取れませんでした。」）
  5. `build_plan` を呼んで返す
- DB に書かない・commit しない・監査ログを書かない（読むだけ）
- 返事の形（pydantic）：`OwnServerPlanResponse { plan_digest: str; changes: list[PlanRow]; blocked: list[PlanRow]; delete_candidates: list[DeleteCandidate] }`。PlanRow の before/after は `str | None`（要約は文字にする）、`reason: str | None = None`
- このファイルに Discord への POST・PATCH・PUT・DELETE を書かない（便2 の試験 `test_discord_own_server_snapshot.py` の「GET だけ」の試験がそのまま通ること）

## §4 試験

### §4-1 backend/tests/test_discord_blueprints.py（新規）

1. `BLUEPRINT_DIR` の全 `tenant_*.json` が `load_blueprint` を通る（今は tenant_1.json の 1 つ）
2. key が重なると ValueError
3. 表に無い権限の名前で ValueError
4. 無い category・無い `role:<key>` を指すと ValueError
5. @everyone の VIEW_CHANNEL を deny して `"@bot"` の allow が無いと ValueError
6. tenant_1.json の @everyone の `names_to_bits(permissions)` が `2248473465835073 & KNOWN_MASK` と同じ
7. `bits_to_names(names_to_bits(x)) == x`（表の順の並びで）
8. 文字のチャンネル名に空白か英大文字があると ValueError

### §4-2 backend/tests/test_discord_own_server_plan.py（新規）

`build_plan` を Discord の返事の作り物で直接呼ぶ試験（純粋な関数）:
1. 本番の読み取り id=1 と同じ形（@everyone 2248473465835073・Bot の managed ロール 805432407 position 1・カテゴリ 2・文字 1・声 1、上書き 0）と tenant_1.json → changes 0・blocked 0・delete_candidates 0（KGI-3 を機械で）
2. 声のチャンネル（type 2）と managed のロールは、設計図に無くても delete_candidates に出ない
3. KGI-4 の 4 種類：設計図に 新しい文字のチャンネル 1・既存チャンネルの名前の変更 1・既存カテゴリへの上書き 1（`"@everyone"` deny VIEW_CHANNEL と `"@bot"` allow VIEW_CHANNEL の 2 相手なら 2 行になるので、試験では `role:<新しいロール>` ではなく既存の相手 1 つだけを変える形にする）・新しいロール 1 → changes がちょうど 4 行で kind が create_channel・update_channel・update_overwrite・create_role
4. KGI-5：設計図から文字のチャンネルを 1 つ外す → delete_candidates に kind "channel" が 1 行、changes 0
5. KGI-6：position が `bot_top` 以上のロールの name を変える → blocked に `role_above_bot` 1 行、changes に入らない
6. @everyone の name を変える → blocked `everyone_name`
7. Bot に無い権限（例 ADMINISTRATOR）をロールに付ける → blocked `permission_bot_lacks`。Bot のロールに ADMINISTRATOR があれば changes に入る
8. 上書きに MANAGE_ROLES → blocked `overwrite_manage_roles`
9. 表に無いビット（1<<47）だけが違う → changes 0
10. discord_id が Discord に無い → blocked `missing_on_discord`
11. 同じ入力で 2 回呼ぶと plan_digest が同じ。changes が 1 つ違えば違う
12. 戻り値を `json.dumps` した文字に guild_id の数字が入っていない
13. topic が null と "" は同じとみなす

API の試験（`test_discord_own_server_snapshot.py` の作り方に合わせる。Discord は AsyncMock、表は conftest の SQLite 版）:
14. 自社用が登録済み・設計図あり → 200、`plan_digest` が 64 文字
15. 自社用が未登録 → 422
16. 設計図のファイルが無いテナント → 404（`blueprint_path` を試験の中で一時フォルダに差し替える）
17. 設計図が検査に外れる → 422
18. Discord の失敗（`DiscordAPIError`）→ 502
19. `tenant.profile.view` だけ → 403
20. 呼ばれた Discord の method がすべて "GET"
21. 呼んだあと `discord_server_snapshots` の行が増えない（`discord_server_apply_runs` は conftest に無い。足さない。この API の関数の中に INSERT・UPDATE・DELETE・commit が無いことは §6 の git grep で確かめる）

既存の試験は 1 本も消さない・飛ばさない。

## §5 画面

### §5-1 `frontend/src/pages/admin/DiscordOwnServerPanel.tsx`

使う部品：今の `Button`・`Card`・`Badge`・`ConfirmModal`・`LoadingBlock` に、金型の `DataTable`（`frontend/src/components/DataTable.tsx`）と `EmptyState`（`frontend/src/components/EmptyState.tsx`）を足す。クラスは `discord-config.css` に今ある `dc-actions`・`dc-result`・`dc-group`・`dc-group-title` だけ。`style=`・色の直書き・新しい CSS は使わない。

- 先頭の説明の権限の行に「tenant.profile.edit → 確認（設計図と今のサーバーの差）」を 1 行足す
- `const PLAN_PATH = "/admin/discord/own-server/plan";`
- 状態：`const [checking, setChecking] = useState(false);`・`const [plan, setPlan] = useState<OwnServerPlan | null>(null);`
- `handleCheck`：`api.get<OwnServerPlan>(PLAN_PATH)` → `setPlan`。失敗は `notice` に danger。404 のときは `t("discordOwnServer.planNoBlueprint")`、それ以外は `t("discordOwnServer.planFailed")`（404 の見分け方：`frontend/src/lib/api.ts:13-21` の `ApiError` の `status === 404`。`instanceof ApiError` で見る）
- 「今のサーバーを読み取る」の `dc-actions` の中、そのボタンの次に `<Button variant="primary" onClick={() => void handleCheck()} loading={checking}>{t("discordOwnServer.check")}</Button>`（同じ `isConnected && canEdit` の中）
- `plan` があるとき、Card の中の最後（ConfirmModal の前）に `<div className="dc-result">` で 3 つの組を並べる。各組は `<div className="dc-group">` に `<h4 className="dc-group-title">{t("discordOwnServer.changesTitle", { count })}</h4>` と DataTable
  - 変わる一覧：列 = 種類（`t("discordOwnServer.kind.<kind>")`）・名前・項目（`field` を `t("discordOwnServer.field.<name>")` に。`overwrite:<target>` は `t("discordOwnServer.field.overwrite", { target })`）・前・後
  - できない一覧：上の列＋理由（`t("discordOwnServer.reason.<reason>")`）。見出しは `blockedTitle`
  - 消す候補：列 = 種類（`t("discordOwnServer.deleteKind.<kind>")`）・名前・親・相手。見出しは `deleteTitle`。組の下に `<p className="dc-hint">{t("discordOwnServer.deleteNote")}</p>`
  - 0 件の組は DataTable の `emptyState` に `<EmptyState size="compact" title={t("discordOwnServer.emptyRows")} />`
  - rowKey は `${kind}:${key ?? discord_id}:${field ?? ""}`
- 「反映する」ボタンはこの便では作らない（便3b）

### §5-2 文言（`frontend/src/locales/ja.json`・`frontend/src/locales/en.json` に同じキー・ADR-027）

`discordOwnServer` のブロックの `"snapshotFailed"` の次に足す:

| キー | ja | en |
|---|---|---|
| check | 確認する | Check |
| planFailed | 確認できませんでした | Could not check |
| planNoBlueprint | 設計図がまだありません | No blueprint yet |
| changesTitle | 変わる（{{count}} 件） | Changes ({{count}}) |
| blockedTitle | できない（{{count}} 件・実行しません） | Not allowed ({{count}}, will not run) |
| deleteTitle | 消す候補（{{count}} 件） | Delete candidates ({{count}}) |
| deleteNote | 消す候補は自動では消しません。 | Delete candidates are never deleted automatically. |
| emptyRows | ありません | None |
| col.kind | 種類 | Type |
| col.name | 名前 | Name |
| col.field | 項目 | Field |
| col.before | 前 | Before |
| col.after | 後 | After |
| col.reason | 理由 | Reason |
| col.parent | 親 | Parent |
| col.target | 相手 | Target |
| kind.create_role | ロールを作る | Create role |
| kind.update_role | ロールを直す | Update role |
| kind.create_category | カテゴリを作る | Create category |
| kind.update_category | カテゴリを直す | Update category |
| kind.create_channel | チャンネルを作る | Create channel |
| kind.update_channel | チャンネルを直す | Update channel |
| kind.update_overwrite | 見せ方を直す | Update permissions |
| field.name | 名前 | Name |
| field.color | 色 | Color |
| field.hoist | 別に表示 | Display separately |
| field.mentionable | メンションできる | Mentionable |
| field.permissions | 権限 | Permissions |
| field.topic | 話題 | Topic |
| field.parent | 親のカテゴリ | Parent category |
| field.overwrite | 見せ方（{{target}}） | Permissions ({{target}}) |
| reason.role_above_bot | Bot と同じか上の順番のロールなので変えられません | The role is at or above the bot's role |
| reason.everyone_name | @everyone の名前は変えられません | @everyone cannot be renamed |
| reason.permission_bot_lacks | Bot が持っていない権限は付けられません | The bot does not have this permission |
| reason.overwrite_manage_roles | 見せ方で「ロールの管理」は付けられません | Manage Roles cannot be set in overwrites |
| reason.bot_role_missing | Bot のロールが見つかりません | The bot role was not found |
| reason.missing_on_discord | 設計図にある物が Discord にありません | Not found on Discord |
| reason.ambiguous | 同じ名前の物が 2 つ以上あります | More than one item has this name |
| deleteKind.role | ロール | Role |
| deleteKind.category | カテゴリ | Category |
| deleteKind.channel | チャンネル | Channel |
| deleteKind.overwrite | 見せ方 | Permission overwrite |

（`col`・`kind`・`field`・`reason`・`deleteKind` は入れ子のオブジェクトにする）

### §5-3 試験（`frontend/src/pages/admin/DiscordOwnServerPanel.test.tsx` に足す）

1. 「Check」を押すと `api.get` が `"/admin/discord/own-server/plan"` で呼ばれ、changes 1・blocked 1・delete_candidates 1 の返事で「Changes (1)」「Not allowed (1, will not run)」「Delete candidates (1)」と各行の文字が出る
2. 3 つとも 0 件 → 「Changes (0)」と「None」が 3 つ
3. 失敗 → 「Could not check」
4. `tenant.profile.edit` が false → 「Check」が出ない
5. 「反映」の文字のボタンが無い

### §5-4 API の形

- `cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json` を流し、変わった `frontend/api-contract/openapi.json` を入れる。流せなかったら停止して BLOCKED: と生出力

## §6 確かめ（生出力を報告書に貼る）

- `cd backend && python -m pytest tests/test_discord_blueprints.py tests/test_discord_own_server_plan.py tests/test_discord_own_server_snapshot.py tests/test_discord_own_server.py tests/test_discord_config_purpose_guard.py tests/test_realtime_topics.py --no-cov -q` の最後の 15 行（失敗 0）
- `python3 -c "import json;json.load(open('backend/app/discord_blueprints/tenant_1.json'))"`（出力なし）
- `git diff origin/main -- backend/app/discord_blueprints/tenant_1.json` と §2 の JSON の照合結果（中身が同じ）
- `git grep -nE "method=\"(POST|PATCH|PUT|DELETE)\"" -- backend/app/routers/discord_own_server.py`（0 行）
- `git diff origin/main -- backend/app/routers/discord_own_server.py | grep -nE "^\+.*(INSERT|UPDATE |DELETE|commit\(|record_audit_log)"`（0 行）
- `git merge-base origin/main HEAD` の sha を BASE_SHA に、HEAD を HEAD_SHA に入れて `python3 scripts/check_test_schema_dup.py` の生出力と rc（0）
- 全体の pytest が流せるなら最後の 5 行（流せなければ「CI に任せる」）
- `cd frontend && npx vitest run src/pages/admin/DiscordOwnServerPanel.test.tsx src/pages/admin/DiscordConfigPage.test.tsx` の最後の 20 行
- `cd frontend && npm run check:i18n-missing-keys && npm run lint -- src/pages/admin/DiscordOwnServerPanel.tsx src/pages/admin/DiscordOwnServerPanel.test.tsx && npx tsc --noEmit -p .` の最後の 20 行
- `git grep -nE "style=|#[0-9a-fA-F]{3,6}\b|rgb\(" -- frontend/src/pages/admin/DiscordOwnServerPanel.tsx`（0 行）
- `git diff --stat origin/main`

## §7 保存

- commit を 2 つに分ける:
  1. `feat(discord): 自社用サーバーの設計図の形と最初の設計図（discord-server-management 便3a）`（§1・§2・§4-1）
  2. `feat(discord): 設計図と今のサーバーの差を出す確認（discord-server-management 便3a）`（§3・§4-2・§5 と報告書）
- `git log --oneline -4` の生出力を報告書に貼る
- `git push origin release/discord-own-server-bin3`（単独で流す）。PR は作らない（Opus が作る）
- 報告書の最後に、push 後の `git rev-parse HEAD` の生出力

## 想定分岐（停止の条件）

- preflight が失敗した → 停止。BLOCKED: と生出力（クラウドの [1/3][2/3] の FAIL を除く）
- 行の目印（`discord_own_server.py:111-121` の SQL、`test_realtime_topics.py:26-29`）が実物と違い、近くにも見つからない → 変えずに停止。BLOCKED: とファイル名・行・実物の生出力
- §4-2 の 1（本番と同じ形で 0 件）が通らない → 比べ方を試験に合わせて曲げない。停止して NEEDS_DECISION: と、出た行の生出力
- 公式の表と違う権限の名前・ビットが要りそうになった → 足さずに停止。NEEDS_DECISION:
- 既存の試験が落ちる → 消したり飛ばしたりせず停止。BLOCKED: と生出力
- 金型にない部品・新しい CSS が要りそうになった → 作らずに停止。NEEDS_DECISION: と理由
- 触ってよいファイル以外を変えたくなった → 変えずに停止。NEEDS_DECISION: と理由
- push が拒否された → 言い換えて再試行しない。停止して BLOCKED: と生出力

報告の最後の行は DONE / BLOCKED: 理由 / NEEDS_DECISION: 理由 のどれか 1 つ。

END OF CARD
