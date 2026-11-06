# design: 他社の人の番号と、持ち主の証明のない Discord サーバー番号を保存させない

- 状態: 設計案 r4（Opus 作成）。Architect r1〜r4 は REVISE（13 節）。r4 の指摘を反映済み・r5 審査前
- 基準: origin/main 133808dce（5fda4152b からの差分に、本設計が触る・引用するファイルの変更は無い: `git diff --stat 5fda4152b origin/main -- backend/app/routers backend/app/services frontend/src/pages/admin frontend/api-contract backend/tests/...` が空）
- 根拠: 同じフォルダの recon.md（1・4・6 節）
- 関係する ADR: ADR-1008（会社に属さない担当者を入れない）・ADR-072（commit 後の reset_tenant_context）・ADR-146（Discord は共通 bot 1台・guild_id から会社を引く）・ADR-027（画面の文字は t()）・ADR-144（画面部品は金型）

## 0. PO の言葉（原文）

- 「不透明さをなくして対策してほしい、50箇所はどうなっている？」
- 「fableが最終評価、DBのSSOTとセキュリティリスクで問題がなければGO」

- 「1、推測は禁止して事実確認を怠らずに確実性を重視して最も効果があり、現状把握の粒度が細く、精度が高いエビデンスを確立して安全に進めてくれ。（以下、常設の条件）」（r1 審査後、Opus が示した選択肢「1. 今回の便は6入口と手で打つ Discord の登録口を閉じる。連携ボタンの戻り口の証明は次の便（PO が Discord の秘密の鍵を設定する）」への回答）

この設計の GO 条件は2つ目の原文のとおり。Fable の最終評価で「DB の正本（SSOT）」と「セキュリティの危険」に問題が無いこと。

## 1. 目的と、利用者に見える変化

- 目的: ある会社の画面から、別の会社の人の番号を担当者などとして保存できないようにする。Discord サーバー番号を手で打って登録する口を閉じる（持ち主の証明の無い登録口を1つ減らす）
- この便で閉じきれないもの: 連携ボタンの戻り口（backend/app/routers/discord_oauth.py:160-254）も持ち主の証明をしていない。戻り口は Discord から返る `code` を交換せず（:161-165 の引数に code が無い）、URL の `guild_id`（:162）をそのまま保存する（:219-230）。開始口は1回札を呼び手に返す（:150）。よって channels.manage 権限の人は、戻り口を直接開いて未登録の任意のサーバー番号を登録できる。直すには Discord の秘密の鍵（client secret）が要り、今どこにも配線されていない（:51 に `_DISCORD_CLIENT_ID` だけ）。PO の選択「1」により次の便（G3・8 節）
- 利用者に見える変化:
  - 普段の操作（自社の人を選んで保存）は今までと同じ
  - 別の会社の人の番号を送ると、保存されずに「指定された担当者が見つかりません」が返る
  - Discord の設定画面で、サーバー番号を手で打つ欄が無くなる。代わりに「チャネル画面で連携する」ボタンを置き、今ある連携ボタンへ案内する。連携済みの会社の設定はそのまま残る

## 2. 成功条件（KGI）

| # | 成功条件 | 今 | 目標 | 判定 |
|---|---|---|---|---|
| G1 | 会社の照合なしで人の番号を保存できる入口の数 | 6（recon.md 6-3） | 0 | 6入口すべてで「他社の人の番号 → 422・行が増えない／変わらない」の自動試験が緑 |
| G2 | Discord サーバー番号を手で打って登録できる入口の数 | 1（recon.md 4） | 0 | PUT /admin/discord-config が 405 を返し、表が変わらない自動試験が緑 |
| G3（次の便・この便の対象外） | 持ち主の証明なしで連携の戻り口から登録できること | ある（discord_oauth.py:160-254） | ない | 次の便の設計で決める。この便では数えない |

KPI（G1・G2 を支える観測値）:

| # | 観測値 | 目標 | 測り方 |
|---|---|---|---|
| K1 | 自社の人の番号での保存（6入口） | 今までどおり 2xx | 自動試験 |
| K2 | 本番の4欄で自社の人でない番号の数 | 0 のまま（今 0: recon.md 6-4） | 読み取りの道で 6-4 と同じ SQL を反映後に流す |
| K3 | routers 内の照合の直書きの数 | 今 5 → 5 のまま（新しい6入口は共通の1関数だけを呼ぶ） | `git grep -n "FROM public.users WHERE id = :uid AND tenant_id" backend/app/routers` の件数。今の5件: bots.py:125・companies.py:362・roles.py:511・roles.py:545・teams.py:266（origin/main 133808dce）。notice_fallback は `_users_ref` を使うので数に入らない |

## 3. 対象と対象外

対象:
- backend/app/routers/leads.py:411 create_lead・:499 update_lead の assigned_to
- backend/app/routers/shifts.py:79 create_shift の user_id
- backend/app/routers/goals.py:111 create_goal の user_id
- backend/app/routers/teams.py:102 create_team・:147 update_team の leader_id
- backend/app/routers/discord_guild_config.py:108-145 PUT /admin/discord-config（削除）
- frontend/src/pages/admin/DiscordConfigPage.tsx の「① サーバー接続」カード（:403-447）と、それだけが使う状態・関数（:143-146・:195・:197-225）
- 新しい共通の関数 1つ（backend/app/services/tenant_users.py）と試験

対象外（理由）:
- 照合済みの6入口（companies・teams のメンバー追加・roles・notice_fallback・bots・order_commissions）の書き換え。動いていて、返す番号（422/400）や文面が試験で決まっている。共通の関数へ寄せるのは別便（8. 維持の仕組み）
- badges.py・buddy.py。本番で登録されていない（recon.md 6-1）。ファイルの片付けは別便
- 連携の戻り口（discord_oauth.py:160-254）の持ち主の証明（code の交換）。customer・own の両方がこの戻り口を通る。秘密の鍵の設定が要るので次の便（G3）
- 自社用サーバー（purpose=own）の手で打つ道は元から無い（own の登録は戻り口だけ）
- Meta のページ番号の会社をまたぐ一意の決まり（recon.md 5。未確認のまま。別に調べる）
- DB の外部キーや制約の追加（会社ごとの表から public.users へ「同じ会社」を強制する制約は、PostgreSQL の外部キーでは書けない。7. 代替案）

## 4. 変更前と変更後

### 4-1. 共通の関数（新規）

backend/app/services/tenant_users.py（新規）:

```python
"""人の番号（public.users.id）がその会社の人かを確かめる（ADR-1008）。"""
from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

USER_NOT_IN_TENANT = "指定された担当者が見つかりません"


async def ensure_user_in_tenant(db: AsyncSession, user_id: int | None, tenant_id: int) -> None:
    """user_id が tenant_id の人でなければ 422。None は通す（担当なし）。"""
    if user_id is None:
        return
    row = await db.execute(
        text("SELECT 1 FROM public.users WHERE id = :uid AND tenant_id = :tid"),
        {"uid": user_id, "tid": tenant_id},
    )
    if row.first() is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=USER_NOT_IN_TENANT)
```

- 有効（is_active）かは見ない。前例 companies.py:357 `_ensure_sales_rep_in_tenant` と同じ。休止中の人が担当のまま残る行を、ほかの項目の保存で止めないため
- 文面は前例（companies.py:368）と同じ
- public.users の読み取りは RLS が `USING (true)`（migrations/20261016_180000_add_users_write_rls.sql:10）なので、会社の絞り込みは SQL の `tenant_id = :tid` が担う。この条件を外さない

### 4-2. 6つの入口

各入口で、DB に書く前（INSERT/UPDATE の前）に1行足す。

| 入口 | 足す行 | 置く場所 |
|---|---|---|
| leads.py create_lead | `await ensure_user_in_tenant(db, data.assigned_to, tenant_id)` | 関数の先頭（:418 `rank = compute_prospect_rank(` の前） |
| leads.py update_lead | `if "assigned_to" in update_data: await ensure_user_in_tenant(db, update_data["assigned_to"], tenant_id)` | :516 `update_data = data.model_dump(exclude_unset=True)` の直後 |
| shifts.py create_shift | `await ensure_user_in_tenant(db, data.user_id, tenant_id)` | `try:` の前 |
| goals.py create_goal | `await ensure_user_in_tenant(db, body.user_id, tenant_id)` | :118-122 の「どちらか一方」の確かめの直後 |
| teams.py create_team | `await ensure_user_in_tenant(db, data.leader_id, tenant_id)` | `try:` の前 |
| teams.py update_team | `if "leader_id" in update_data: await ensure_user_in_tenant(db, update_data["leader_id"], tenant_id)` | :160 の `_UPDATABLE_COLUMNS` で絞った直後 |

触らない: 各入口の権限、SQL、監査記録、commit・reset_tenant_context の位置。

### 4-3. Discord の手で打つ道を閉じる

backend/app/routers/discord_guild_config.py:
- :108-145 の `@router.put("/admin/discord-config")` と `update_discord_config` を消す。`DiscordConfigUpdate`（:47-）も、ほかで使っていなければ消す（`git grep -n DiscordConfigUpdate` で確かめる）
- 冒頭の説明（:8 の PUT の行）を消す
- frontend/api-contract/openapi.json を作り直してコミットする（.github/workflows/api-contract-check.yml:35-53 が、API の形とこのファイルのずれを止める。作り方は同ファイル :53 の文のとおり）
- 同じ道に GET と DELETE があるので、PUT は FastAPI が 405 を返す

frontend/src/pages/admin/DiscordConfigPage.tsx の「① サーバー接続」カード:
- 変更前: 未接続または「変更」中は番号を打つ欄（TextField）と「接続／保存」ボタン。接続済みは番号と「変更」ボタン
- 変更後:
  - 未接続: 説明の文と、金型 `ButtonLink`（:20 で読み込み済み）で `/channels` へ案内するボタン
  - 接続済み: 番号の表示はそのまま。「変更」ボタンは同じく `/channels` への `ButtonLink`
  - どちらの `ButtonLink` も今の「変更」ボタン（:440）と同じく `canEdit` のときだけ出す
- 消すもの: `editingGuild`・`guildSaving`・`guildError`・`guildSaved` の状態、`handleGuildSave`・`handleGuildCancel`、`isGuildFormOpen`。番号を打つ欄が無くなるので、欄の値 `guildId` も持たない: `useSeededForm` の guild 側（:140-142）、`fetchAll` の :189 の1行、使い手が無くなる `toGuildId`（:111）を消す。`fetchAll` の CONFIG_PATH の取り直し（:186）は残す（表示の `savedGuildId`（:193）は今と同じく `configQ.data` から読む）。:374 の `!guildReady` は `!configQ.data` に置き換える（読めなかった時に「未接続」と誤って出さず、今と同じく誤りの文だけを出すため）。`useSeededForm` の読み込み（:16）はチケット設定（:154）が使うので残す。`SNOWFLAKE_RE` はチケット設定（:232・:236）で使うので残す
- 文字: 新しいキー `discordConfig.connectViaChannels`（ボタン）と `discordConfig.connectViaChannelsHint`（説明）を ja.json・en.json の両方に足す。使わなくなるキー（serverIdLabel・serverIdPlaceholder・serverIdHint・invalidGuildId など）は、`git grep` でほかに使う所が無いものだけ両方から消す
- 色・余白の直書きをしない。既存の class（dc-row・dc-actions 等）と金型だけを使う

## 5. 影響範囲（呼び出し元の全走査）

- 6入口の呼び出し元は画面だけ。返事が 422 になるのは他社の番号を送ったときだけで、画面は自社の人の一覧から選ぶ
- 本番の4欄に他社の番号は 0件（recon.md 6-4）。既存の行の保存は止まらない
- PUT /admin/discord-config を呼ぶのは DiscordConfigPage.tsx:206 だけ（`git grep -n "admin/discord-config" frontend/src` の画面のコード: routeTitles.ts:41 題名・InboxKartePanel.tsx:115 GET・discordSendError.ts:29 道の文字・DiscordOwnServerPanel.tsx:86 /own・DiscordConfigPage.tsx:96 GET/:206 PUT・ChannelsPage.tsx:117 GET・:211 GET・:236 DELETE・:589 画面移動。ほかは試験ファイル）。PUT は DiscordConfigPage.tsx:206 の1件
- 照合を足すと赤になる既存の試験（r1 指摘 Q3。origin/main で確かめた）:
  - backend/tests/test_inbox_new_assignment_badge.py:355（assigned_to 20）・:368（assigned_to 10）。この試験は自前の SQLite（:64-93 INBOX_BADGE_SQLITE_DDL）で users の表が無い。:476（None）は通る
  - backend/tests/test_analytics.py:689・:762（assigned_to 321。users の行が無い）
  - backend/tests/test_notification_event_routing.py:246・:266・:285（assigned_to 7・7・9。:91-101 で staff の行だけを入れ、users の行が無い。:266 は値が同じでも update_data に assigned_to があれば照合が走るので赤）
  - 直し方の決まり: 照合を偽物に差し替えない（mock 禁止）。試験の会社（999。backend/tests/conftest.py:1955）の本物の users 行を足す
  - test_inbox_new_assignment_badge.py の自前 SQLite（:72-81）には conftest.py:301-302 の `public.users`→`users` の書き換えが無い。直し方: (1) users の表の DDL は conftest.py の INBOX_BADGE_SQLITE_DDL に足す（同ファイル :84-86 のとおり、表の定義を試験ごとに重ねない決まり）(2) この engine に before_cursor_execute の仕掛け（retval=True）を足し、`public.users` を `users` に置き換える（conftest.py:296-302 と同じ形。connect の手当て :75-81 は SQL 文を書き換えられないので使わない）(3) assigned_to 10・20 の人を会社 999 で入れる
  - backend/tests/test_shifts_pg.py:90-93（r2 指摘で追加）: create_shift を user_id=2・会社 901（:24・:31 の SCHEMA tenant_901）で直接呼ぶ。この試験の DB の public.users は backend/tests/rls_bootstrap.py:258-264 の (999, 999) の1行だけなので 422 になる。直し方: 試験の中で public.users に (id=2, tenant_id=901) の行を入れてから呼ぶ。あわせて「他社の人（999）なら 422・行が増えない」の試験をこの PostgreSQL の形で足す（10 節）
  - 通るもの（SQLite の client を使う試験だけ）: test_shifts.py・test_audit_goals_carrier.py は user_id 999 を使い、conftest.py:1522-1523 で会社 999 の人として入っている。teams の leader_id を送る試験は無い
- frontend/src/pages/admin/DiscordConfigPage.test.tsx:47-74 は「Server ID」の欄を前提にしているので書き直す。:138-152・:154-162 のチケット設定の試験（discord-ticket-config への api.put）は残す。:164-173 の権限なしの試験は、「変更」がリンクになるので `queryByRole("button", { name: "Change" })` を `queryByRole("link", { name: "Change" })` に直す（ボタンのままだと何も無くても通ってしまうため）。権限ありの試験で `getByRole("link", { name: "Change" })` の行き先が `/channels` であることも確かめる
- 試験 backend/tests/test_discord_d2.py:307-340 の PUT の試験4本（test_put_saves_guild_id・test_get_after_put_returns_saved・test_put_invalid_guild_id_rejected・test_put_too_short_guild_id_rejected）は消し、「PUT は 405・表が変わらない」の試験1本に置き換える。backend/tests/test_discord_own_server.py は PUT を使わない（GET :263・:267・:280 と DELETE :271・:276 だけ）。触らない
- frontend/api-contract/openapi.json の DiscordConfigUpdate（:9490-）と PUT の道（operationId :40374）が消える
- tests/prod-check/page-speed-targets.ts は画面の道を測るだけ。影響なし

## 6. リスクと対処

| リスク | 対処 |
|---|---|
| 照合の SELECT が1回増えて遅くなる | 主キー（id）で1行引くだけ。前例 companies と同じ |
| 手で番号を打っていた会社が困る | 連携ボタンは今もチャネル画面にあり、連携済みの設定は残る。画面で案内する |
| 連携の道（discord_oauth.py）まで壊す | この便では触らない。連携の戻り口の既存試験が緑のままを確かめる |
| 連携の戻り口に証明が無いまま残る（G3） | この便では閉じない。手で打つ口を閉じても、戻り口を直接開けば未登録のサーバー番号を登録できる。他社が登録済みの番号は一意の決まり（:241-248 guild_already_registered）で取れない。次の便を台帳に積み、PO の秘密の鍵の設定を待つ |
| 照合の書き方が増えてばらばらになる（コードの正本が割れる） | 新しい入口は共通の関数だけを呼ぶ（K3）。既存6件の寄せ替えは別便で行う |

DB の正本（SSOT）について: 人の正本は public.users のまま。新しい表・列・写しは作らない。照合は正本を読むだけ。

## 7. 代替案と選んだ理由

| 案 | 内容 | 選ばない理由 |
|---|---|---|
| A. DB の制約で止める | 会社ごとの表から public.users へ「同じ会社」の外部キー | 外部キーは「同じ会社」の条件を書けない。複合の外部キーにするには users に (id, tenant_id) の一意と各表に tenant_id 列の揃えが要り、移行が大きい。本番 DB の変更になる |
| B. 各入口に SQL を直書き | 前例と同じ書き方を6か所 | 同じ照合が6か所増え、直し漏れの元になる |
| C. 共通の関数（採用） | 1関数を6入口から呼ぶ | 変更が小さく、DB を変えない。後で既存6件も寄せられる |
| D. Discord の PUT に照合を足す | bot がそのサーバーに入っているかを確かめる | bot が入っていることは持ち主の証明にならない。証明になるのは、Discord が返す code を秘密の鍵で交換し、その応答の guild を使う形。今の連携の戻り口はそれをしていない（G3・次の便） |

## 8. 維持の仕組み

- 自動試験（10. の表）を残す。入口を変えたら試験が赤になる
- 別便（台帳に積む）: 照合済みの既存6件を共通の関数へ寄せ、`FROM public.users WHERE id = :... AND tenant_id` の直書きを routers から無くす。その後、直書きを lint で止める
- 別便: badges.py・buddy.py の片付け
- 次の便（G3・台帳に積む）: 連携の戻り口で code を交換し、Discord の応答の guild だけを保存する。前提は PO が Discord 開発者画面の秘密の鍵（client secret）を本番の secrets に入れること（secrets の変更と外部画面の操作は PO の仕事）

## 9. 戻し方

- 1つの PR を revert する。DB の変更は無いので、戻しは即時
- Discord: PUT と画面の欄が戻る

## 10. 受入条件と検証方法

| 基準 | 検証方法 |
|---|---|
| 6入口それぞれで、他社の人の番号を送ると 422、行が増えない／変わらない | backend の自動試験（PostgreSQL を使う既存の形: 例 backend/tests/test_shifts_pg.py）。2社と各社の人を作り、他社の人の番号で送る |
| 6入口それぞれで、自社の人の番号なら今までどおり成功 | 同じ試験で自社の人の番号で送る |
| 担当なし（None）は今までどおり成功（leads・goals の team 目標・teams） | 同じ試験 |
| PUT /admin/discord-config が 405、public.tenant_discord_config が変わらない | backend の自動試験 |
| GET /admin/discord-config・DELETE /admin/discord-config/own・連携の戻り口の既存試験が緑 | 既存試験 |
| Discord の設定画面に番号を打つ欄が無く、チャネル画面へのボタンがある | frontend の試験（既存の形）＋反映後に PO の画面で目視 |
| 画面の文字が t() 経由、ja/en が同じキー | 既存の CI（i18n の確かめ） |
| openapi.json が API の形と一致 | 既存の CI（api-contract-check） |
| 本番の4欄で自社の人でない番号が 0 | 反映後に読み取りの道で recon.md 6-4 の SQL |
| routers 内の照合の直書きが 5 のまま（K3） | `git grep -n "FROM public.users WHERE id = :uid AND tenant_id" backend/app/routers` が5件 |
| 照合の試験は本物の users 行で通す（mock なし） | 差分に照合関数の差し替え（monkeypatch・mock）が無いことを審査で確かめる |

## 11. 外部事例

該当事例なし。理由: この変更は「保存の前に、参照する番号が同じ会社のものか確かめる」という、前例（ADR-1008・companies.py:357）と同じ型の適用で、新しい方式を選ぶ判断を含まない。Discord 側も、既にある連携の道に一本化するだけ。

## 12. 実装の進め方（1便）

- 1便・1 PR（backend と frontend）。DB の移行・deploy.yml・本番 scripts を含まない
- 実装はクラウドの Sonnet。実装カードは本設計の審査が通ってから書く

## 13. 審査（Architect）

### r1（クラウド Architect・2026-11-06）: REVISE

結果はクラウドの実行記録から読んだ（審査役のコミットは作業場所の見張りに止められ、push されていない）。

| 観点 | 判定 |
|---|---|
| C1 行番号 | × |
| C2 K3 の今の値と 10 節の行 | × |
| C3 ほかの書き込み口（current_user.id か照合済み） | ○ |
| C4 照合の正しさ／連携の戻り口の証明 | ×（照合は正しい。戻り口に証明が無い） |
| C5 | ○ |
| C6 5 節に壊れる試験が無い | × |

| 指摘 | 対応 |
|---|---|
| Q1（必須）戻り口で code を交換する | PO の選択「1」で次の便（G3）へ。1・2・3・6・7・8 節を直した |
| Q2（必須）行番号 | openapi :9490・:40374、recon の tcg_distribution_svc.py:1175・079 :5 に直した。基準を 133808dce に上げた |
| Q3（必須）試験 | 5 節に赤になる試験と直し方の決まりを書いた |
| Q4（必須）K3 の今の値 | 今 5・目標 5、10 節に行を足した |
| Q5（推奨）試験の人の番号 | 確かめて問題なし（5 節「通るもの」） |

### r2（クラウド Architect・2026-11-06・a76499a9b）: REVISE

結果はクラウドの実行記録から読んだ。指摘は Opus が origin/main 133808dce で読み直し、すべて事実と確かめた。

| 観点 | 判定 |
|---|---|
| C1 行番号 | ×（DiscordConfigPage.tsx の範囲の終わりが1行ずつずれ） |
| C2 G・K の測り方 | ○（K3 は5件で一致） |
| C3 書く入口の漏れ | ○（5fda4152b から変更なし） |
| C4 照合の正しさ・G3 の明記 | ○ |
| C5 DB の正本 | ○ |
| C6 壊れる試験の一覧 | ×（test_shifts_pg.py が漏れ） |

| 指摘 | 対応 |
|---|---|
| Q1（必須）test_shifts_pg.py:90-93 が §5 に無い | 足した。会社901の users 行を入れる直し方と、PostgreSQL の形の他社試験を書いた |
| Q2（必須）:197-224・:403-446 | :197-225・:403-447 に直した（:195 isGuildFormOpen も足した） |
| Q3（推奨）自前 SQLite の書き換えと DDL の置き場 | 直し方を3つの手順で書いた |
| Q4（推奨）「全件」に抜け | ChannelsPage.tsx:211・:236・:589 を足し、試験ファイルは除くと書いた |
| Q5（推奨）test_discord_own_server.py は DELETE も使う | 文を直した |

### r3

結果はクラウドの実行記録から読んだ（審査の担当は Opus・head 99d40d59d）。指摘は Opus が origin/main 133808dce で読み直し、すべて事実と確かめた。

| 観点 | 判定 |
|---|---|
| C1 行番号 | ×（2か所の範囲ずれ。r2 で足した行と recon の82件は一致） |
| C6 壊れる試験の一覧 | ×（一覧に漏れは無い。test_inbox の手順(2)がそのままでは作れない） |
| C7 r1・r2 の必須指摘 | ○（r1 Q1 は PO の選択で次の作業 G3） |

| 指摘 | 対応 |
|---|---|
| Q1（必須）test_discord_d2.py:307-339 は4本目の assert（:340）を外す | :307-340 に直した |
| Q2（必須）DiscordConfigPage.test.tsx:139-160 | :138-152・:154-162 に直した |
| Q3（必須）connect の手当てでは SQL 文を書き換えられない | before_cursor_execute（retval=True）を足す形に直した（conftest.py:296-302 と同じ形） |
| Q4（推奨）own_server は GET も使う | GET :263・:267・:280 を書き足した |

### r4

結果はクラウドの実行記録から読んだ（審査の担当は Opus・head c64ed192c・origin/main 5a8b0dd91 で照合）。指摘は Opus が origin/main で読み直し、すべて事実と確かめた（test_inbox :81 は PRAGMA の行。DiscordConfigPage.tsx :189 は fetchAll の setGuildId、:374 は guildReady。DiscordConfigPage.test.tsx :170 は button で探している）。

| 観点 | 判定 |
|---|---|
| C1 行番号 | ×（:72-80 は :72-81） |
| C6 壊れる試験の一覧 | ○ |
| C7 r1〜r3 の必須指摘 | ○ |
| C8 実装の範囲 | ○ |

| 指摘 | 対応 |
|---|---|
| Q1（必須）test_inbox の自前 SQLite は :72-81 | 直した |
| Q2（推奨）「guildId のうちこのカードだけが使う部分」が曖昧 | 消す所（:140-142・:189・:111）と残す所（:186・:16）、:374 の置き換えを書いた |
| Q3（推奨）権限なしの試験 :164-173 がリンクだと素通りする | link で探す形に直し、権限ありの行き先の確認を足した。リンクは canEdit のときだけ出すと書いた |

### r5

（審査後に記入）
