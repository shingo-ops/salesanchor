# design: 他社の人の番号と、持ち主の証明のない Discord サーバー番号を保存させない

- 状態: 設計案（Opus 作成）。審査前
- 基準: origin/main c481f5e7d
- 根拠: 同じフォルダの recon.md（1・4・6 節）
- 関係する ADR: ADR-1008（会社に属さない担当者を入れない）・ADR-072（commit 後の reset_tenant_context）・ADR-146（Discord は共通 bot 1台・guild_id から会社を引く）・ADR-027（画面の文字は t()）・ADR-144（画面部品は金型）

## 0. PO の言葉（原文）

- 「不透明さをなくして対策してほしい、50箇所はどうなっている？」
- 「fableが最終評価、DBのSSOTとセキュリティリスクで問題がなければGO」

この設計の GO 条件は2つ目の原文のとおり。Fable の最終評価で「DB の正本（SSOT）」と「セキュリティの危険」に問題が無いこと。

## 1. 目的と、利用者に見える変化

- 目的: ある会社の画面から、別の会社の人の番号を担当者などとして保存できないようにする。持ち主だと証明していない Discord サーバーを、自社のものとして登録できないようにする
- 利用者に見える変化:
  - 普段の操作（自社の人を選んで保存）は今までと同じ
  - 別の会社の人の番号を送ると、保存されずに「指定された担当者が見つかりません」が返る
  - Discord の設定画面で、サーバー番号を手で打つ欄が無くなる。代わりに「チャネル画面で連携する」ボタンを置き、今ある連携ボタン（Discord で持ち主が許可する道）へ案内する。連携済みの会社の設定はそのまま残る

## 2. 成功条件（KGI）

| # | 成功条件 | 今 | 目標 | 判定 |
|---|---|---|---|---|
| G1 | 会社の照合なしで人の番号を保存できる入口の数 | 6（recon.md 6-3） | 0 | 6入口すべてで「他社の人の番号 → 422・行が増えない／変わらない」の自動試験が緑 |
| G2 | 持ち主の証明なしで Discord サーバー番号を登録できる入口の数 | 1（recon.md 4） | 0 | PUT /admin/discord-config が 405 を返し、表が変わらない自動試験が緑 |

KPI（G1・G2 を支える観測値）:

| # | 観測値 | 目標 | 測り方 |
|---|---|---|---|
| K1 | 自社の人の番号での保存（6入口） | 今までどおり 2xx | 自動試験 |
| K2 | 本番の4欄で自社の人でない番号の数 | 0 のまま（今 0: recon.md 6-4） | 読み取りの道で 6-4 と同じ SQL を反映後に流す |
| K3 | 照合の書き方の置き場 | 新しい6入口は共通の1関数だけを呼ぶ | `git grep -n "FROM public.users WHERE id = :uid AND tenant_id" backend/app/routers` で新しい直書きが増えていない |

## 3. 対象と対象外

対象:
- backend/app/routers/leads.py:411 create_lead・:499 update_lead の assigned_to
- backend/app/routers/shifts.py:79 create_shift の user_id
- backend/app/routers/goals.py:111 create_goal の user_id
- backend/app/routers/teams.py:102 create_team・:147 update_team の leader_id
- backend/app/routers/discord_guild_config.py:108-145 PUT /admin/discord-config（削除）
- frontend/src/pages/admin/DiscordConfigPage.tsx の「① サーバー接続」カード（:403-446）と、それだけが使う状態・関数（:143-146・:197-224）
- 新しい共通の関数 1つ（backend/app/services/tenant_users.py）と試験

対象外（理由）:
- 照合済みの6入口（companies・teams のメンバー追加・roles・notice_fallback・bots・order_commissions）の書き換え。動いていて、返す番号（422/400）や文面が試験で決まっている。共通の関数へ寄せるのは別便（8. 維持の仕組み）
- badges.py・buddy.py。本番で登録されていない（recon.md 6-1）。ファイルの片付けは別便
- 自社用サーバー（purpose=own）の登録。連携の道（discord_oauth.py）だけで、手で打つ道は無い
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

- 有効（is_active）かは見ない。前例 companies.py:357 と同じ。休止中の人が担当のまま残る行を、ほかの項目の保存で止めないため
- 文面は前例 companies.py:357 の関数が返す文と同じ

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
- 消すもの: `editingGuild`・`guildSaving`・`guildError`・`guildSaved` の状態、`handleGuildSave`・`handleGuildCancel`、`isGuildFormOpen`、`guildId` のうちこのカードだけが使う部分。`SNOWFLAKE_RE` はチケット設定（:232・:236）で使うので残す
- 文字: 新しいキー `discordConfig.connectViaChannels`（ボタン）と `discordConfig.connectViaChannelsHint`（説明）を ja.json・en.json の両方に足す。使わなくなるキー（serverIdLabel・serverIdPlaceholder・serverIdHint・invalidGuildId など）は、`git grep` でほかに使う所が無いものだけ両方から消す
- 色・余白の直書きをしない。既存の class（dc-row・dc-actions 等）と金型だけを使う

## 5. 影響範囲（呼び出し元の全走査）

- 6入口の呼び出し元は画面だけ。返事が 422 になるのは他社の番号を送ったときだけで、画面は自社の人の一覧から選ぶ
- 本番の4欄に他社の番号は 0件（recon.md 6-4）。既存の行の保存は止まらない
- PUT /admin/discord-config を呼ぶのは DiscordConfigPage.tsx:206 だけ（`git grep -n "admin/discord-config" frontend/src` の全件: routeTitles.ts:41・InboxKartePanel.tsx:115 GET・discordSendError.ts:29 道の文字・DiscordOwnServerPanel.tsx・DiscordConfigPage.tsx:96/:206・ChannelsPage.tsx:117 GET）。PUT は :206 の1件
- 試験 backend/tests/test_discord_d2.py:307-339 の PUT の試験4本（test_put_saves_guild_id・test_get_after_put_returns_saved・test_put_invalid_guild_id_rejected・test_put_too_short_guild_id_rejected）は消し、「PUT は 405・表が変わらない」の試験1本に置き換える。backend/tests/test_discord_own_server.py は GET と戻り先の文字だけで PUT を使わない（:206・:248・:263）。触らない
- frontend/api-contract/openapi.json の DiscordConfigUpdate（:9456-）と PUT の道（:40337 付近）が消える
- tests/prod-check/page-speed-targets.ts は画面の道を測るだけ。影響なし

## 6. リスクと対処

| リスク | 対処 |
|---|---|
| 照合の SELECT が1回増えて遅くなる | 主キー（id）で1行引くだけ。前例 companies と同じ |
| 手で番号を打っていた会社が困る | 連携ボタンは今もチャネル画面にあり、連携済みの設定は残る。画面で案内する |
| 連携の道（discord_oauth.py）まで壊す | 触らない。試験で連携の戻り口の既存試験が緑のままを確かめる |
| 照合の書き方が増えてばらばらになる（コードの正本が割れる） | 新しい入口は共通の関数だけを呼ぶ（K3）。既存6件の寄せ替えは別便で行う |

DB の正本（SSOT）について: 人の正本は public.users のまま。新しい表・列・写しは作らない。照合は正本を読むだけ。

## 7. 代替案と選んだ理由

| 案 | 内容 | 選ばない理由 |
|---|---|---|
| A. DB の制約で止める | 会社ごとの表から public.users へ「同じ会社」の外部キー | 外部キーは「同じ会社」の条件を書けない。複合の外部キーにするには users に (id, tenant_id) の一意と各表に tenant_id 列の揃えが要り、移行が大きい。本番 DB の変更になる |
| B. 各入口に SQL を直書き | 前例と同じ書き方を6か所 | 同じ照合が6か所増え、直し漏れの元になる |
| C. 共通の関数（採用） | 1関数を6入口から呼ぶ | 変更が小さく、DB を変えない。後で既存6件も寄せられる |
| D. Discord の PUT に照合を足す | bot がそのサーバーに入っているかを確かめる | bot が入っていることは持ち主の証明にならない。連携（Discord で持ち主が許可）だけが証明になる |

## 8. 維持の仕組み

- 自動試験（10. の表）を残す。入口を変えたら試験が赤になる
- 別便（台帳に積む）: 照合済みの既存6件を共通の関数へ寄せ、`FROM public.users WHERE id = :... AND tenant_id` の直書きを routers から無くす。その後、直書きを lint で止める
- 別便: badges.py・buddy.py の片付け

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

## 11. 外部事例

該当事例なし。理由: この変更は「保存の前に、参照する番号が同じ会社のものか確かめる」という、前例（ADR-1008・companies.py:357）と同じ型の適用で、新しい方式を選ぶ判断を含まない。Discord 側も、既にある連携の道に一本化するだけ。

## 12. 実装の進め方（1便）

- 1便・1 PR（backend と frontend）。DB の移行・deploy.yml・本番 scripts を含まない
- 実装はクラウドの Sonnet。実装カードは本設計の審査が通ってから書く

## 13. 審査（Architect）

（審査後に記入）
