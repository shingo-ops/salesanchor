# 実装カード PR-B: 名簿を読む所を、全社1つの表へ付け替える（コード）

> この文書は何か（専門用語なしの1行）:
> 会社ごとの名簿を読んでいるアプリの所を、全社1つの名簿（共用6行＋会社独自の行）を読むように直し、会社ごとに「隠す」切り替えを設定画面に足す作業の指示書。

- 親: design.md §2-2・§4・§5・§7・§12（PO 実装承認 2026-11-06「1」）
- 基準: origin/main 74453510e（2026-11-06 23:3x JST 取得）。行番号はすべてこの版で Opus が読んで確かめた
- ブランチ: `release/channel-master-shared-b`（`bash scripts/new-worktree.sh release/channel-master-shared-b --claude`）
- 読んだ決まり: docs/handoff/design-partner-card-ops/guards/00-common.md（1手順1コマンド・空欄を残さない）・04-worktree.md（作業の置き場）・05-pr.md（PR の作り方）・10-executor.md（実行役の制約）
- 受領確認: 着手の前に、このカードの §0 の2つを満たしたかを1行で返してから始める
- 起票: Draft・`--base main`・`shingo-cc` 名義。危険パス（migrations/・deploy.yml・本番 scripts/）は**含まない**（下の「触らない」を守れば含まれない）

## 0. 着手条件（満たさなければ止まって BLOCKED: で返す）

- 本番に共用6行がある。Opus が 2026-11-06 23:38 JST に読み取り専用の鍵で確かめた: id 7〜12（messenger・instagram・discord・phone・in_person・whatsapp）、会社行0（`/tmp/CC報告ファイル/chm-six-recheck.txt`）
- PR-A の migration `migrations/20261106_190000_create_public_channel_masters.sql` が origin/main にある（#5206）

## 1. やること（この順）

1. `./scripts/dev/executor-preflight.sh || exit 1`
2. §2 の読み口を `backend/app/services/channel_masters.py` に作る
3. §3 の表の順に付け替える（バックエンド）
4. §4 の画面を直す
5. §5 の試験を直す・足す
6. API の形の写しを作り直す: `cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json`（`.github/workflows/api-contract-check.yml:35・:53` と同じ命令）
7. §6 の検索を流し、期待どおりの件数か確かめる
8. 試験は手元の Mac で回さない（PO 11/2）。push して GitHub の CI で確かめる
9. PR 本文に「消すファイル」欄: `scripts/migrate_20260621_030000_backfill_lead_channel_type.py`。`### 標準ワークフロー確認` 欄も書く

## 2. 1か所の読み口（`backend/app/services/channel_masters.py`）

消す: `:10-17` `DEFAULT_CHANNEL_MASTERS`・`:19` `ACTIVE_CHANNEL_PLATFORMS`。
残す: `:21-24` `CHANNEL_TYPE_ALIASES`・`:27-37` `normalize_channel_type_value`（入力の言い換え）。

足す（形。中身の書き方は自由、ただし下の決まりは守る）:

```python
CHANNEL_MASTERS_TABLE = "public.channel_masters"
CHANNEL_SETTINGS_TABLE = "public.channel_master_tenant_settings"
CONVERSION_ITEM_VALUES = frozenset({"baseline", "channel_whatsapp", "channel_instagram"})

async def list_channels(db, tenant_id: int, *, active_only: bool = True) -> list[dict]:
    """共用行＋自社行。各行に is_shared（tenant_id IS NULL）と is_hidden（自社の設定。行が無ければ False）を付ける。ORDER BY platform。"""

async def get_channel(db, tenant_id: int, platform: str) -> dict | None:
    """platform が一致し is_active の行（共用か自社）。無ければ None。"""

async def list_channels_for_picker(db, tenant_id: int, *, keep_platform: str | None = None) -> list[dict]:
    """list_channels から is_hidden の行を外す。ただし platform == keep_platform の行は残す。"""

async def get_channel_by_id(db, tenant_id: int, channel_master_id: int) -> dict | None:
    """id が一致し、共用か自社の行。他社行は None（＝404 にする）。"""

async def set_hidden(db, tenant_id: int, channel_master_id: int, is_hidden: bool, user_id: int) -> None:
    """UPSERT。ON CONFLICT (tenant_id, channel_master_id) DO UPDATE SET is_hidden, updated_at, updated_by_user_id。"""

async def conversion_items(db) -> dict[str, str]:
    """WHERE tenant_id IS NULL AND conversion_item IS NOT NULL AND is_active → {platform: conversion_item}"""

async def platforms_by_store(db, store: str) -> list[str]:
    """分析用。WHERE tenant_id IS NULL AND conversion_item IS NOT NULL AND is_active AND conversation_store = :store"""
```

決まり:
- 会社を受け取る関数（list_channels・get_channel・list_channels_for_picker・get_channel_by_id・set_hidden）は SQL に `(tenant_id IS NULL OR tenant_id = :tenant_id)` を**明示で書く**。会社を受け取らない conversion_items・platforms_by_store は `tenant_id IS NULL`（共用の行だけ）で絞る（試験の SQLite には RLS が無いため。本番は RLS と二重の守り）
- `public.channel_masters`・`public.channel_master_tenant_settings` の文字は、このファイルの定数2つにだけ書く。他のファイルは定数を import して使う（§12・§6 の検索 K7）
- SQLite と PostgreSQL の両方で動く SQL にする（`= ANY(:list)` は使わない。必要なら IN を展開する）。UPSERT の `ON CONFLICT ... DO UPDATE` は両方で動く
- 呼ぶ前の `set_tenant_context` は呼び出し側（ルーター）の今のやり方のまま

## 3. 付け替える所（バックエンド）

| 場所（origin/main 74453510e） | 変更前 | 変更後 |
|---|---|---|
| `backend/app/routers/conv_logs.py:77-95` `_get_channel_master` | `tenant_table_ref(db, tenant_id, "channel_masters")` を直接読む | 関数を消し、呼んでいる所は `channel_masters.get_channel` を使う（返す形は id・platform・display_name・connection_type を含む） |
| `backend/app/routers/conv_logs.py:189-217` `GET /channel-masters` | 自社表の is_active 行を全部 | 引数 `for_: str \| None = Query(None, alias="for")`・`keep: str \| None = Query(None)` を足す。`for_ == "picker"` なら `list_channels_for_picker(keep_platform=keep)`、それ以外は `list_channels`。返す項目は今の5つ（id・platform・display_name・connection_type・is_active）に `is_shared`・`is_hidden` を足す。権限は今のまま（ログインだけ。選択欄で全員が読むため） |
| `backend/app/routers/conv_logs.py:492-518` `POST /admin/channel-masters` | `{schema}.channel_masters` に INSERT。権限なし | `dependencies=[Depends(require_permission("tenant.profile.edit"))]` を足す。`get_channel` 相当で同じ platform（共用か自社）が既にあれば 409「同じ名前の連絡手段が既にあります」。無ければ `CHANNEL_MASTERS_TABLE` に `tenant_id`＝自社・`connection_type='manual'`・`conversation_store='conversation_logs'`・`is_verbatim=TRUE`・`conversion_item=NULL` で INSERT。commit の直後に `reset_tenant_context`（今のまま） |
| 新 `PUT /admin/channel-masters/{master_id}/visibility`（同じファイル） | なし | 本文モデル `ChannelVisibilityUpdate(is_hidden: bool)`。`require_permission("tenant.profile.edit")`。`get_channel_by_id` が None→404、`connection_type == "auto"`→400「自動連携チャネルは隠せません」。`set_hidden` → `record_audit_log(db, tenant_id, current_user.id, "update", "channel_master_tenant_settings", master_id, old_data={"is_hidden": 前}, new_data={"is_hidden": 後})` → commit → `reset_tenant_context`。返す `{"id": master_id, "is_hidden": 後}` |
| `backend/app/routers/conv_logs.py:526-557` `DELETE /admin/channel-masters/{master_id}` | 自社表で 404・auto は 400・それ以外 is_active=false | `require_permission("tenant.profile.edit")` を足す。`get_channel_by_id` が None→404、auto→400（今の文言のまま）、`is_shared`→403「共用の連絡手段は消せません。隠す切り替えを使ってください」。自社行だけ `UPDATE {CHANNEL_MASTERS_TABLE} SET is_active=false, updated_at=now() WHERE id=:id AND tenant_id=:tenant_id` |
| `backend/app/routers/leads.py:205-215` `_ensure_channel_type_in_master` | 自社表を直接読む | `await channel_masters.get_channel(db, tenant_id, normalized)` が None でなければ通す。422 の文言・`existing_value` の扱いは今のまま。隠したかは**見ない**（design D1-2） |
| `backend/app/routers/analytics.py:2484-2507` `_fetch_lead_conversion_inputs` の会話2つ | `l.channel_type IN ('instagram', 'messenger')`・`l.channel_type = 'whatsapp'` | 関数の頭で `meta_platforms = await channel_masters.platforms_by_store(db, "meta_messages")`・`log_platforms = await ...("conversation_logs")`。SQL は IN をその場の値で展開（例 `:p0, :p1`）。どちらかが空なら、その問い合わせは流さず0行とする。読む行は今と同じ（instagram・messenger → Meta、whatsapp → 会話記録） |
| `backend/app/routers/analytics.py:2537-2538` | `lcf.analyze(leads, messages)` | `items = await channel_masters.conversion_items(db)`、`lcf.analyze(leads, messages, items)`。`ValueError`（下の検査）は 409「分析の設定が名簿にそろっていません」 |
| `backend/app/services/lead_conversion_factors.py:42-47` | `CHANNEL_*`・`META_CHANNELS`・`CHANNELS` | 消す |
| `backend/app/services/lead_conversion_factors.py:173` `prepare`・`:187-188` | `prepare(leads, messages)`・`lead.channel_type not in CHANNELS` | `prepare(leads, messages, channel_items: dict[str, str])`・`lead.channel_type not in channel_items` |
| `backend/app/services/lead_conversion_factors.py:229-230` | `CHANNEL_WHATSAPP`・`CHANNEL_INSTAGRAM` と比べる | `channel_items.get(lead.channel_type) == "channel_whatsapp"`／`"channel_instagram"` |
| `backend/app/services/lead_conversion_factors.py:387-388` `analyze` | `analyze(leads, messages)` | `analyze(leads, messages, channel_items)`。最初に `set(channel_items.values()) != {"baseline","channel_whatsapp","channel_instagram"}` なら `ValueError`。`prepare` に渡す |
| `backend/app/services/lang_judge.py:31`・`:84`・`:92`・`:122`・`:127` | `_EXCLUDED_MANUAL_CHANNELS` と `cl.channel_type <> ALL(:excluded_channels)` | 定数と params を消し、2つの問い合わせの両方で `AND NOT EXISTS (SELECT 1 FROM {CHANNEL_MASTERS_TABLE} cm WHERE cm.platform = cl.channel_type AND cm.is_verbatim = FALSE AND (cm.tenant_id IS NULL OR cm.tenant_id = :tenant_id))`。`:tenant_id` を params に足す（`:61` の tenant_id） |
| `backend/app/services/tenant.py:34` | `DEFAULT_CHANNEL_MASTERS` の import | 消す |
| `backend/app/services/tenant.py:1100-1113`（DDL）・`:1262`（RLS 有効化の行）・`:1303-1306`（ポリシー）・`:1597-1614` `seed_default_channel_masters`・`:1787-1788`（呼び出し） | 新しい会社に表を作り6行を写す | すべて消す（新しい会社には作らない）。既存会社の古い表は PR-C まで残す（この PR では消さない） |
| `backend/app/realtime/topics.py:96-97` の並び | POST・DELETE が `_PENDING` | `("PUT", "/api/v1/admin/channel-masters/{master_id}/visibility"): _PENDING,` を足す |
| `scripts/migrate_20260621_030000_backfill_lead_channel_type.py` | 2026-06 の1回きりの台本（消す定数を読む） | ファイルごと消す（`scripts/run_all_migrations.sh` からは呼ばれていない。Opus が `git grep` で確かめた） |
| `scripts/lead_regression/generate.py:80・:157・:174-175・:305・:313-314・:546・:552・:568` | `lcf.CHANNEL_*` | 台本の頭に `CHANNEL_MESSENGER = "messenger"` 等の定数と `CHANNEL_ITEMS = {"messenger":"baseline","instagram":"channel_instagram","whatsapp":"channel_whatsapp"}` を置き、置き換える |
| `scripts/lead_regression/k3_run.py:54・:72・:101` | `lcf.analyze(a, b)` | `lcf.analyze(a, b, CHANNEL_ITEMS)`（generate.py から import） |

## 4. 画面

| 場所 | 変更 |
|---|---|
| `frontend/src/components/ChannelTypeCombobox.tsx:7-13` | `ChannelMasterOption` に `is_shared?: boolean`・`is_hidden?: boolean` を足す |
| `frontend/src/components/ChannelTypeCombobox.tsx:41-57` | 最初の値を `const keepRef = useRef(value)` で覚え、`api.get(\`/channel-masters?for=picker${keepRef.current ? \`&keep=${encodeURIComponent(keepRef.current)}\` : ""}\`)` を読む。依存配列は `[]` のまま（1回だけ読む）。`is_active` の絞り込みは今のまま |
| `frontend/src/pages/inbox/ManualRecordSection.tsx:45-69` | `/channel-masters?for=picker` に `&keep=${encodeURIComponent(currentPlatform)}`（currentPlatform があるとき）を付ける。あとは今のまま |
| `frontend/src/pages/admin/ChannelMastersPage.tsx:19-25` | `is_shared: boolean`・`is_hidden: boolean` を足す |
| `frontend/src/pages/admin/ChannelMastersPage.tsx:84-113` | 生の `<table>` を金型 `frontend/src/components/DataTable.tsx` に替える（列: platform・displayName・type・visible・actions。`renderCell` で中身を出す）。生の `<button>`（`:101-107`・ADR-144 違反）は金型 `Button`（variant `danger`・size `sm`）に替え、`connection_type === "manual" && !ch.is_shared` のときだけ出す |
| 同じ表の type 列 | `ch.is_shared` のとき金型 `Badge`（variant `neutral`・size `sm`）で `t("channelMasters.shared")` を添える |
| 同じ表の visible 列 | `connection_type === "manual"` の行に金型 `Toggle`（`checked={!ch.is_hidden}`・`onCheckedChange={(v) => handleVisibility(ch.id, !v)}`・`aria-label={t("channelMasters.visibleAriaLabel", { name: ch.display_name })}`）。auto 行は空。`handleVisibility` は `api.put(\`/admin/channel-masters/${id}/visibility\`, { is_hidden })` → `invalidate(CHANNEL_MASTERS_HEAD)`、失敗は `t("channelMasters.visibilityError")` |
| 同じ画面の追加の失敗 | 409 のとき `t("channelMasters.duplicateError")`、それ以外は今の `saveError` |
| 列見出しの下の説明 | `t("channelMasters.visibleHelp")` を表の上に1行（`<p>` に既存の文字の色トークン。色の直書き禁止） |
| `frontend/src/locales/ja.json:3905-` と `en.json:3905-` の `channelMasters` | 同じキーを ja/en 同時に足す: `visible`（この会社で使う／Use in this company）・`visibleHelp`（切ると、リードの連絡手段の選択欄に出なくなります。昔のリードの値と分析はそのままです／Turned off channels are hidden from the lead channel picker. Existing leads and analytics are unchanged.）・`visibleAriaLabel`（{{name}} をこの会社で使う／Use {{name}} in this company）・`visibilityError`（切り替えに失敗しました／Failed to update visibility）・`shared`（共用／Shared）・`duplicateError`（同じ名前の連絡手段が既にあります／A channel with the same name already exists） |
| `frontend/src/components/LeadFormButtonMigration.test.tsx:80`・`OrderLeadButtonMigration.test.tsx:38` | `url === '/channel-masters'` を `url.startsWith('/channel-masters')` に（引数が付くため） |
| `frontend/src/lib/query/stage2Pages.test.tsx:45・:150・:169・:174` | 設定画面の読み口・追加・削除の期待は変えない。表を DataTable にしても通ることを CI で確かめる（落ちたら fixture に `is_shared: false, is_hidden: false` を足すだけにする） |
| `frontend/tests-e2e/lead-channel-control.spec.ts:78` | 道の一致は引数を無視する（`frontend/tests-e2e/utils/api-mock.ts:66` が pathname だけ見る）ので変えない |

## 5. 試験（バックエンド）

| 場所 | 変更 |
|---|---|
| `backend/tests/conftest.py:43` | `DEFAULT_CHANNEL_MASTERS` の import を消す |
| `backend/tests/conftest.py:311-312` の並び | `public.channel_master_tenant_settings`→`channel_master_tenant_settings` を**先に**、`public.channel_masters`→`channel_masters` を後に足す（どちらも他方を部分文字列に含まないが、読みやすさのためこの順に並べる） |
| `backend/tests/conftest.py:633-641` | SQLite の `channel_masters` を新しい形に: id・tenant_id NULL 可・platform・display_name・connection_type・conversation_store・is_verbatim・conversion_item・is_active・created_at・updated_at。`UNIQUE` は付けない（SQLite で NULL の一意を作れないため。重複は API の 409 と PG の試験で見る）。`channel_master_tenant_settings`（PRIMARY KEY (tenant_id, channel_master_id)）を足す |
| `backend/tests/conftest.py:881-889` | 定数の代わりに design §3 の6行（tenant_id NULL）を試験の中に書いて入れる |
| `backend/tests/rls_bootstrap.py:14-34` `_PG_BOOTSTRAP_MIGRATIONS` | 末尾に `"20261106_190000_create_public_channel_masters.sql"` を足す（PG の試験で表を作るため）。`:35-38` の古い migration は PR-C まで残す |
| `backend/tests/test_channel_type_control.py:19-20` | 2つの import を消す |
| `backend/tests/test_channel_type_control.py:104-149` | `tenant_006.channel_masters` を作って写す部分を消す（共用行は rls_bootstrap の表＋試験で入れる） |
| `backend/tests/test_channel_type_control.py:202-219` | 「写しを呼ぶ」試験を K6 に反転: `seed_default_channel_masters` が tenant_service に無いこと（`hasattr` が False）と、作成で channel_masters の DDL が流れないこと |
| `backend/tests/test_channel_type_control.py:222-340` | 消す台本の試験なので丸ごと消す |
| `backend/tests/test_conv_logs_router.py:366-391`・`:393-420` | 新しい読み口に合わせて patch 先を `app.routers.conv_logs.channel_masters.*` に。追加は 201・同じ名前は 409、削除は auto 400・共用 403・他社 404 |
| `backend/tests/test_system_roles.py:137` | `seed_default_channel_masters` の monkeypatch を消す |
| `backend/tests/test_lang_judge.py:116-145` | `<> ALL(:excluded_channels)` の期待を、`NOT EXISTS` と `is_verbatim = FALSE` を含み `excluded_channels` を params に持たない、に書き換える |
| `backend/tests/test_lead_conversion_factors.py:34・:264・:276` と `prepare` 呼び出し `:68・:77・:114・:122・:127`、`analyze` 呼び出し `:139・:152・:163・:185・:312` | 試験の頭に対応表 `CHANNEL_ITEMS` を置き、全部に渡す。数値の期待は**1つも変えない**（K5 の機械側）。足す: 対応表が3値でないと ValueError |
| `backend/tests/test_lead_regression_generate.py:88・:255-256` | 同じく対応表を渡す。期待は変えない。加えて :246-252 は使い捨て PG（conftest の `LEAD_REGRESSION_PG_DDL`）で `_fetch_lead_conversion_inputs` を呼ぶ。PR-B の後この関数は `platforms_by_store` で `public.channel_masters` を読むため、その DDL に `public.channel_masters`（新しい形）と共用の instagram・messenger・whatsapp の3行を足す（CI では `LEAD_REGRESSION_PG_URL` が無く飛ばされるが、回したとき赤にしないため） |
| 新 `backend/tests/test_channel_masters_shared.py`（SQLite） | K3: A社(1)の追加行がA社の一覧に出てB社(2)に出ない／B社がA社の行を DELETE・PUT すると 404／共用と同じ platform の追加は 409。K6: 会社作成の後、一覧に共用6つ。隠す: A社が phone を隠すと `for=picker` から消え、B社には出る／`keep=phone` なら残る／auto 行の PUT は 400／権限の無い人は 403（`app.auth.dependencies.load_user_permissions` を権限の無い集合に patch）／PUT で監査の記録が1件 |
| 新 `backend/tests/test_channel_masters_shared_pg.py`（`RLS_ADMIN_DATABASE_URL` が無ければ skip。`rls_bootstrap` を使う） | 会社の役で共用行の UPDATE が0件／他社行が見えない／設定の表に他社行の番号を入れると RLS で拒まれる／試しの会社に会社行と設定を1行ずつ入れ `public.tenants` の行を消すと2つの表の行が0件 |
| 新 `backend/tests/test_channel_master_literals.py` | §6 の K4 と K7 を試験にする（ファイルを読んで正規表現で数え、0件でなければ赤） |

## 6. 終わったときの検索（PR の枝で流し、結果を PR 本文に貼る）

```bash
# K1（0件。今の origin/main では12件）
git grep -nE 'tenant_table_ref\(db, tenant_id, "channel_masters"\)|\{schema(_name)?\}\.channel_masters' HEAD -- backend/app
# K4（0件。今の origin/main では10件）
git grep -nE "['\"](messenger|instagram|whatsapp|discord|phone|in_person)['\"]|CHANNEL_(MESSENGER|INSTAGRAM|WHATSAPP)|META_CHANNELS" HEAD -- backend/app/routers/analytics.py backend/app/services/lead_conversion_factors.py backend/app/services/lang_judge.py
# K7（channel_masters.py の2行だけ）
git grep -nE 'public\.channel_master(s|_tenant_settings)' HEAD -- backend/app
# 定数の残り（0件）
git grep -nE 'DEFAULT_CHANNEL_MASTERS|ACTIVE_CHANNEL_PLATFORMS|seed_default_channel_masters|backfill_lead_channel_type' HEAD -- backend scripts
```

## 7. 触らない

- `migrations/`・`scripts/run_all_migrations.sh`・`.github/workflows/`（PR-C の担当）
- 既存会社の `tenant_NNN.channel_masters` の表と行（PR-C まで残す）
- `backend/tests/rls_bootstrap.py:35-38`・`backend/tests/test_value_migrations_neutralized.py`・`backend/tests/test_tenant_loop_migration_guard.py`（古い migration に頼る。PR-C）
- 連携の部品が自分の名前を書く処理（design §4-3 の一覧）、`backend/app/tasks/avatar.py`
- `leads.channel_type`・`conversation_logs.channel_type`・`meta_messages.platform` の値
- `normalize_channel_type_value` と `CHANNEL_TYPE_ALIASES`

## 8. 想定される分かれ道（こうなったらこうする）

| 起きたこと | どうする |
|---|---|
| SQLite の試験で `ON CONFLICT ... DO UPDATE` が通らない | SELECT して UPDATE か INSERT に分ける（同じ取引の中）。PG の試験は UPSERT のまま |
| conftest の書き換えで `public.channel_masters` が `channel_master_tenant_settings` の途中を壊す | 順番（settings を先）を確かめる。直らなければ BLOCKED: |
| `lcf.analyze` を他から呼ぶ所が §3 の外に見つかった | 足さずに NEEDS_DECISION: で場所を返す |
| 分析の数値の期待（test_lead_conversion_factors）が1つでも変わる | 期待を書き換えない。BLOCKED: で差を返す |
| DataTable に替えると stage2Pages の試験が落ち、fixture の足し以外で直らない | 表は替えずに `<button>` だけ金型にし、NEEDS_DECISION: で返す |
| 一覧の SQL で、隠す設定を LEFT JOIN すると SQLite と PG で結果が違う | 設定を別の問い合わせで読み、Python で合わせる |
| api-contract-check が赤 | §1 の 6 の命令で作り直したか確かめる。手で openapi.json を直さない |
| 手元で試験を回したくなる | 回さない。CI の結果を読む |
| 権限の import で循環が起きる | `require_permission` は `app.auth.dependencies` から（他のルーターと同じ） |
| 自社で一度消した（is_active=false）platform をもう一度足すと一意の決まりにぶつかり 500 になる | 今の表も同じ動き（前からある）。この PR では直さず、PR 本文に「既知」と1行書く |

## 9. 終わりの報告

- `DONE`／`BLOCKED: 理由`／`NEEDS_DECISION: 問い` のどれかで始める
- 停止したとき: その場で手を止め、`BLOCKED:` で始めて、止まった手順・命令・生の出力を返す。自分で回り道を作らない
- PR 番号・HEAD・CI の結果（名前と結論の生の一覧）・§6 の4つの検索の生の出力・消したファイル・変えた試験の一覧
- 推測で埋めない。読めなかった出力は「読めなかった」と書く

## 10. 反映の後（Opus が行う。担当はしない）

- K5: 反映の前に取った 001 社の分析の応答と、反映後の応答が全項目一致
- K2: 5社の「チャネル設定」とリード編集の選択欄が同じ6つ
- D1: 試しの会社で電話を切って選択欄から消え、戻すと出る。別の会社では出たまま

END OF CARD
