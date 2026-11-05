# 設計: Discord の自社サーバーを、設計図とボタンでシステムと Bot が管理する

> この文書は何か：KGI 1〜7 を満たすための作り方です。実装役（クラウドの Sonnet）が迷わず作れる粒度で書きます。

- 親: [docs/specs/discord-server-management/README.md](../../specs/discord-server-management/README.md)
- あるべき姿: [ideal-state.md](../../specs/discord-server-management/ideal-state.md)　／　KGI: [kgi.md](../../specs/discord-server-management/kgi.md)
- 下調べ: [recon.md](recon.md)（以下「R§n」は recon.md の節）
- 対象 ADR: ADR-091（Bot 権限の正本・変えない）、ADR-072（commit 後の reset_tenant_context）、ADR-027（画面の文字は t()）、ADR-144（画面部品の金型）、ADR-135・ADR-136（migrations を含む PR の GO 手順）、ADR-1037（移行のロック待ち 1 秒）、ADR-1024（ai_ro ビュー）。新規 ADR 案は §10
- 状態: 2026-11-04 PO 承認済み（PO「1」＝この設計で承認し、自社用サーバーの登録から作り始める）。PO 決定「1」（設計図はプログラムと同じ場所に履歴付きで置く）を反映。便1a の実装カード: [card-bin1a-purpose-column.md](card-bin1a-purpose-column.md)（便1b は便1a の本番反映後に出す）

## 1. 目的と合格条件

目的：PO が「こう作りたい」と話すだけで、自社サーバーのチャンネル・ロール・見せ方が変わる。人が Discord の設定画面を触らない。

合格条件は kgi.md の KGI 1〜7 をそのまま使う。検証方法は §8 の表。

## 2. 対象と対象外

対象（段階1）：
- 1 社に「顧客用」「自社用」の 2 つのサーバーを登録する
- 自社用サーバーの カテゴリ・テキストチャンネル・ロール・部屋ごとの見せ方（permission overwrites）を、設計図どおりに作る・名前を変える・見せ方を変える
- 設計図に無い物を「消す候補」として出す（消さない）

対象外（段階1ではやらない）：
- チャンネルとロールの並び順（KGI に無い。並べ替えは他の物の順番も動かすため、段階2で別に設計する）
- 人へのロール付与、ボイスチャンネル、スレッド、サーバー自体の設定（名前・アイコン）
- 顧客用サーバーの自動作成・部屋の外の通知の変更（変えない約束）
- 自動で消すこと（変えない約束）
- 支払いの通知（別テーマ）

## 3. 全体の流れ

```
(1) PO が話す → Opus が設計図（JSON）を書き直す → PR・審査・マージ・本番反映
(2) PO が自社用タブで「確認する」を押す
      → アプリが Discord の今の姿を読み、設計図と比べて「変わる一覧」「できない一覧」「消す候補」を出す
(3) PO が「反映する」を押す → 確認の小窓 → Bot が一覧どおりに直す → 結果を表示
(4) もう一度「確認する」→ 変わる数 0
```

最初の 1 回だけ：
- 自社用サーバーに SA Bot を招待する
- Bot のロールを一番上の近くへ動かす（R§5 の手順書。KGI-7 の手作業）
- 「今のサーバーを読み取る」を押す。アプリが今の姿を記録し、Opus が読み取り専用の鍵で読んで最初の設計図を作る。これを反映すれば変わる数は 0 になる（KGI-3）

## 4. 変更の中身

### 4-1. DB：登録の表に「用途」を足す（migrations/20261105_100000_tenant_discord_config_purpose.sql 新規）

- `public.tenant_discord_config` に `purpose VARCHAR(16) NOT NULL DEFAULT 'customer'` を足す
  - 決まり `ck_tenant_discord_config_purpose CHECK (purpose IN ('customer','own'))`
- 主キーを `(tenant_id)` から `(tenant_id, purpose)` に替える。`uq_tenant_discord_config_guild_id`（guild_id 一意）は残す（同じサーバーを顧客用と自社用に二重登録できない）
- 今の 3 行は既定値で `customer` になる → 顧客用の行は変わらない（KGI-1）
- ロック待ちは ADR-1037 のとおり `SET lock_timeout = '1s'`。表は 3 行だけ
- 戻し方：`DELETE … WHERE purpose='own'` → 主キーを `(tenant_id)` に戻す → 列を消す（ファイル末尾にコメントで書く）

改訂1（2026-11-04、カード作成時の実物確認による。Opus の技術判断）：移行を 2 つに分ける
- 事実：本番への出し方は「①新しいプログラムを入れて起動（`.github/workflows/deploy.yml` の `Deploy to VPS (code + env + docker compose)`）→ ②DB の移行（`Run database migrations`、`scripts/run_all_migrations.sh`）」の順（deploy.yml:224-235 のコメントと手順名）
- 1 つの PR で列とプログラムを一緒に出すと、①と②の間は新しいプログラムが無い列 `purpose` を読む。受け取り係の逆引き（`backend/app/discord_gateway/client.py:101-128`）は失敗すると None を返すので、その間の顧客用サーバーの書き込みを取りこぼす
- 対処：
  - 便1a（移行だけ・`migrations/20261105_100000_tenant_discord_config_purpose.sql`）：列 `purpose`（既定 `customer`）・決まり `ck_tenant_discord_config_purpose`・一意 `uq_tenant_discord_config_tenant_purpose (tenant_id, purpose)` を足すだけ。主キーは `(tenant_id)` のまま。今のプログラムはこの列を知らなくても動く（足すだけ）
  - 便1b（プログラム＋移行 migrations/20261106_100000_tenant_discord_config_purpose_pk.sql（新規））：主キーを `(tenant_id, purpose)` に替え、便1a の一意を消す。新しいプログラムの `ON CONFLICT (tenant_id, purpose)` は便1a の一意で、移行の前でも後でも動く。移行の前に自社用を登録しようとすると主キー `(tenant_id)` に当たって失敗するが、自社用の登録はこの便で初めて画面に出るので影響は無い
- この表を別の表から参照する外部キー・見張り・行の制限は 0 件（§11 U1）なので、主キーの付け替えは 3 行の表で 1 回の短い書き換え

新しい表（同じ移行ファイル）：
- `public.discord_server_snapshots`（今の姿の記録。Opus が最初の設計図を作るためだけに使う）
  - 列：`id BIGSERIAL PK`、`tenant_id INTEGER NOT NULL`、`purpose VARCHAR(16) NOT NULL CHECK (purpose='own')`、`body JSONB NOT NULL`、`taken_by INTEGER`、`taken_at TIMESTAMPTZ NOT NULL DEFAULT now()`
  - サーバーの番号（guild_id）は持たない。サーバーの番号は登録の表 1 か所（変えない約束）
  - `body` はロールとチャンネルの構成だけ。人の名前・書き込みは入れない
- `public.discord_server_apply_runs`（反映の記録）
  - 列：`id BIGSERIAL PK`、`tenant_id`、`purpose`、`plan_digest VARCHAR(64) NOT NULL`、`started_at`、`finished_at`、`applied_by INTEGER`、`result JSONB`（各行の結果。成功/できない/失敗と理由）
  - 列名に `hash`・`token`・`secret` を使わない。ai_ro は拒否リストに当たる列を外すため（`migrations/20261017_130100_create_ai_ro_views.sql:24`）、使うと Opus が読めない
- 両方の表に `salesanchor_app` への GRANT（`viewer_discord_config` と同じ書き方、R§2）
- ai_cloud（相談係用）のビューに新しい表の列の扱いを足す（`migrations/20261024_100300_create_ai_cloud_views.sql:262-275` の並び）。`body`・`result` は伏せる

### 4-2. 登録の表を読む 8 か所に「顧客用だけ」を足す（R§3）

| ファイル:行 | 変更前 | 変更後 |
|---|---|---|
| `backend/app/routers/discord_oauth.py:192-203` | `ON CONFLICT (tenant_id)` | 列 `purpose` を足し `ON CONFLICT (tenant_id, purpose)`。purpose は state の中身（§4-4）から取る。無ければ `customer` |
| `backend/app/routers/discord_guild_config.py:66-73` | `WHERE tenant_id = :tid` | `AND purpose = 'customer'`（顧客用の GET はそのまま） |
| `backend/app/routers/discord_guild_config.py:118-126` | `ON CONFLICT (tenant_id)` | 列 `purpose='customer'` を入れ `ON CONFLICT (tenant_id, purpose)` |
| `backend/app/routers/discord_guild_config.py:157-160` | `WHERE tenant_id = :tid` | `AND purpose = 'customer'`（自社用は消えない） |
| `backend/app/routers/discord_auto_setup.py:100-110` | 同上 | `AND purpose = 'customer'` |
| `backend/app/routers/discord_remove.py:61-69` | 同上 | `AND purpose = 'customer'` |
| `backend/app/routers/discord_ticket_config.py:237-245` | `LEFT JOIN … ON d.tenant_id = c.tenant_id` | `… AND d.purpose = 'customer'` |
| `backend/app/services/discord_role_sync.py:61-72` | `WHERE dc.tenant_id = :tid` | `AND dc.purpose = 'customer'` |

漏れを機械で止める：試験 backend/tests/test_discord_config_purpose_guard.py（新規）が `backend/app` の中で `tenant_discord_config` を含む SQL 文字列を全部探し、同じ文に `purpose` が無ければ落ちる。新しい読み方が増えても漏れない。

### 4-3. 受け取り係：自社用サーバーではお客さん向けの処理を全部止める（R§4）

- `backend/app/discord_gateway/client.py:101-126` `_resolve_tenant_id(guild_id)` を `_resolve_guild(guild_id) -> tuple[int, str] | None`（会社と用途）に替える。SQL は `SELECT tenant_id, purpose …`
- 呼び出し 5 か所（`:198-216` 起動時の部屋の復旧、`:217-247` 部屋が消されたとき、`:256-343` 受付ボタン、`:345-392` リアクション、`:408-434` 書き込み）で、用途が `own` なら何もせず `logger.info("[discord-gateway] own server — customer handlers skipped …")` だけ残して戻る
- 顧客用（`customer`）の動きは今と同じ（KGI-2）

改訂1（2026-11-04、カード作成時の実物確認による）：関数の名前と形は変えない
- 事実：既存の試験 8 か所が `_resolve_tenant_id` を差し替えている（`backend/tests/test_discord_bot_texts.py:107,123,134,146`・`backend/tests/test_discord_reaction_wiring.py:172`・`backend/tests/test_discord_ticket_channel_delete_restore.py:257,275,296`）
- 対処：`_resolve_tenant_id` の名前と戻り値（`int | None`）はそのままにし、SQL に `AND purpose = 'customer'` を足すだけにする。自社用サーバーは「顧客用として登録されていないサーバー」になり、5 か所すべてが今ある「未登録なら止める」道を通る（起動時の復旧・部屋の削除・リアクション・書き込みは何もしない。受付ボタンは「登録されていない」の一言だけ返す。自社用サーバーに受付ボタンは置かない）
- 上の `_resolve_guild` と専用の記録の一文は作らない。効き目（自社用でお客さん向けの処理が動かない）は同じで、変える行が 1 か所で済む
- 試験：自社用サーバーの書き込みで `ticket_channel_writer.process_ticket_channel_message` が呼ばれないこと。顧客用では今までどおり呼ばれること

### 4-4. 自社用の登録（Bot の招待）

- `backend/app/routers/discord_oauth.py:105-130` 招待の開始で、受け取る本文に `purpose`（`customer` か `own`。既定は `customer`）を足す。`oauth_state.issue_state` に入れる中身へ purpose を足す
- 戻り（`:140-219`）で purpose を取り出して §4-2 の書き方で登録する
  - 登録できたあとの戻り先：顧客用は今のまま `/channels?discord_status=connected`。自社用は `/admin/discord-config?tab=own&discord_status=connected`（自社用の登録の Card がある画面へ戻す）
  - 中身の purpose が `customer`・`own` 以外なら `customer` とせず `invalid_payload` で戻す（決まりにない値を黙って顧客用に入れない）
- 画面側の呼び出し：今の顧客用（`frontend/src/pages/channels/ChannelsPage.tsx:194`、本文 `{}`）は変えない。自社用の Card だけが本文 `{"purpose":"own"}` で呼ぶ
- 招待の開始は権限 `channels.manage`（`backend/app/routers/discord_oauth.py:107`）。自社用の招待ボタンは `tenant.profile.edit` と `channels.manage` の両方を持つ人にだけ出す
- 自社用の削除：`DELETE /admin/discord-config/own`（新規）。`purpose='own'` の行だけ消す
- 自社用の取得：`GET /admin/discord-config/own`（新規）。`{guild_id, connected_at}` を返す

### 4-5. 設計図（PO 決定「1」）

- 置き場所：backend/app/discord_blueprints/tenant_<tenant_id>.json（新規）
  - バックエンドの入れ物は `COPY . .` でこのフォルダごと入る（`backend/Dockerfile:24`）
  - YAML の道具は入っていない（`backend/requirements*.txt` に無い）。新しい部品を足さず JSON にする
- 形（pydantic で検査。backend/app/services/discord_blueprint.py（新規））：

```json
{
  "version": 1,
  "roles": [
    {"key": "sales", "discord_id": "123…", "name": "営業", "color": 3447003,
     "hoist": true, "mentionable": true, "permissions": ["VIEW_CHANNEL", "SEND_MESSAGES"]}
  ],
  "categories": [
    {"key": "sales_cat", "discord_id": "456…", "name": "営業",
     "overwrites": [{"target": "@everyone", "deny": ["VIEW_CHANNEL"]},
                    {"target": "role:sales", "allow": ["VIEW_CHANNEL"]}]}
  ],
  "channels": [
    {"key": "sales_notice", "discord_id": "789…", "name": "営業通知", "type": "text",
     "category": "sales_cat", "topic": "…", "sync_with_category": true}
  ]
}
```

- 物の見分け方：`discord_id` があればそれで見分ける（名前を変えても同じ物と分かる）。無ければ「新しく作る物」
- 権限は名前で書く（数字で書かない）。名前と数字の対応は Discord の公式の表に合わせ、discord_blueprint.py（新規） に 1 か所だけ置く
- 試験 backend/tests/test_discord_blueprints.py（新規）：フォルダの全ファイルが形の検査を通ること、key が重ならないこと、参照先（category・role）があること
- 新しい物を作ったあとの `discord_id`：反映の結果に新しい番号が出る。Opus が `discord_server_apply_runs.result` を読み、次の PR で設計図に書き足す。書き足すまでの間は、名前と種類と親が同じ物を「同じ物」とみなす（今の自動作成と同じ見分け方、`backend/app/routers/discord_auto_setup.py:478-502`）。二重には作らない

### 4-6. 今の姿の読み取り（最初の 1 回）

- `POST /admin/discord/own-server/snapshot`（新規・`backend/app/routers/discord_own_server.py`）
- 自社用サーバーのロール一覧とチャンネル一覧を `discord_api_request` の GET で読み、設計図と同じ形に直して `discord_server_snapshots` に 1 行入れる
- Opus は読み取り専用の鍵で `ai_ro.public__discord_server_snapshots` を読み、tenant_<id>.json（新規） を作って PR にする

### 4-7. 確認（差分を出す）

- `GET /admin/discord/own-server/plan`（新規）
- Discord の今の姿をその場で読み（保存しない）、設計図と比べる
- 出す一覧：
  - 変わる一覧：ロールを作る・ロールを直す（名前・色・権限・表示・メンション可）・カテゴリ/チャンネルを作る・名前を変える・話題を変える・親を変える・見せ方を変える。行ごとに「前」「後」
  - できない一覧（実行しない）：Bot の一番上のロールと同じかそれより上のロールを変える行／Bot が持っていない権限を付ける行／@everyone の名前を変える行。行ごとに理由（KGI-6）
  - 消す候補：Discord にあって設計図に無いロール・カテゴリ・チャンネル。Bot 自身のロールと、Discord が自動で作るロールは除く。「消さない」と表示（KGI-5）
- 一覧の中身から `plan_digest`（SHA-256 の16進）を作って返す

### 4-8. 反映（ボタン）

- `POST /admin/discord/own-server/apply`。本文は `{plan_digest}`
- サーバー側で差分を作り直し、digest が違えば 409（「確認したあとにサーバーか設計図が変わりました。確認し直してください」）。Terraform の「古くなった計画は捨てる」と同じ考え（§9）
- 1 社につき同時に 1 本だけ。Redis の `SET NX EX 600`（キー `discord_own_apply:{tenant_id}`）。取れなければ 409
- 順番：ロールを作る → ロールを直す → カテゴリを作る/直す → チャンネルを作る/直す → 見せ方を直す。新しく作った物の番号を後の行で使う
- 1 行ずつ `discord_api_request`（429 と 5xx の待ちは中で済む、R§5）。1 行失敗しても残りは続ける。結果は行ごとに 成功／できない／失敗＋理由
- 結果を `discord_server_apply_runs` に入れ、`record_audit_log` を残す。commit のあと `reset_tenant_context`（ADR-072）
- 消す処理は書かない（DELETE の呼び出しをこのファイルに置かない。試験で文字列を探して確かめる）

### 4-9. 画面（`frontend/src/pages/admin/DiscordConfigPage.tsx`）

- 上に Tabs（金型 `frontend/src/components/Tabs.tsx`）。「顧客用」「自社用」
  - 顧客用タブ：今の画面の中身をそのまま入れる（動きは変えない）
  - 自社用タブ（新規の部品ファイル frontend/src/pages/admin/DiscordOwnServerPanel.tsx（新規））
- 自社用タブの中身。すべて既存の部品（R§6）
  - 登録の Card：未登録なら「自社用サーバーに Bot を招待」Button、登録済みなら Badge「接続済み」と解除の Button（ConfirmModal で確かめる）
  - 「今のサーバーを読み取る」Button（最初の 1 回用。結果は「読み取りました（ロール n・チャンネル n）」）
  - 「確認する」Button → 3 つの DataTable（変わる・できない・消す候補）。件数を見出しに出す。0 件は EmptyState
  - 「反映する」Button（変わる行が 1 件以上のときだけ押せる）→ ConfirmModal（「n 件を反映します」）→ 結果の DataTable（Badge で 成功/できない/失敗）
- 文字はすべて `t("discordOwnServer.…")`。`frontend/src/locales/ja.json`・`frontend/src/locales/en.json` に同じキー（ADR-027）
- 色は Badge の variant とデザイントークンだけ。直書きしない（ADR-144）
- 権限：見る `tenant.profile.view`、押す `tenant.profile.edit`（今の自動作成と同じ、`backend/app/routers/discord_auto_setup.py:84-88`）

## 5. 便の分け方

| 便 | 中身 | 確かめる KGI | migrations |
|---|---|---|---|
| 便1a | §4-1 改訂1 の列・決まり・一意を足すだけ（プログラムは変えない） | KGI-1（今の 3 行が `customer` になり、画面と Bot が今のまま） | あり（GO 手順・直前のバックアップ確認） |
| 便1b | §4-1 改訂1 の主キー付け替え、§4-2 の 8 か所と漏れ止め試験、§4-3 改訂1 受け取り係、§4-4 招待、自社用の登録の画面（タブと登録の Card だけ） | KGI-1・KGI-2 | あり（GO 手順・直前のバックアップ確認） |
| 便2 | §4-1 の 2 表、§4-6 読み取り、画面の「読み取る」 | KGI-3 の前半 | あり |
| 便3 | §4-5 設計図の形と検査、§4-7 確認、§4-8 反映、画面の確認と反映 | KGI-3〜6 | なし |
| 試験 | テナント001の自社用テストサーバーで KGI 1〜7 を順に。合格後に HIGH LIFE JPN | KGI-7 | — |

便ごとに 変更 → 反映 → 測る → 次。まとめて評価しない。

## 6. 代替案

| 案 | 選ばない理由 |
|---|---|
| 自社用を別の表にする | 顧客用の 8 か所を触らずに済むが、「サーバーの情報は今の表 1 か所」の約束（kgi.md）に反する。同じサーバーが両方に入るのを DB で止められない |
| 設計図を DB に置く | PO 決定「1」で不採用。Opus が本番に書けないため、変更のたびに PO の手作業が増える |
| 今の自動作成（auto-setup）を広げる | 「足りない物を作る」だけで、名前の変更・見せ方の変更・消す候補を持たない（R§5）。顧客用の動きを変えない約束にも触れる |
| 確認を省いてボタンで直接反映 | KGI-3〜6 は「確認画面の件数」で測るため、確認は欠かせない。押す前に何が変わるかを PO が見られない |

## 7. 危険と対処・戻し方・測り方

| 危険 | 対処 | 測り方 |
|---|---|---|
| 8 か所のどれかに「顧客用だけ」が漏れて顧客用が壊れる | 漏れ止め試験（§4-2）。便1 の試験で KGI-2 | CI の試験・部屋の外の通知 1 件 |
| 自社用の書き込みで「部屋の外の通知」が飛ぶ | §4-3 で用途 own を止める。試験で確かめる | 自社用に 1 回書いて通知 0 件（便1 の試験の手順に入れる） |
| 主キーの付け替えで表が止まる | 3 行だけ・lock_timeout 1 秒（ADR-1037）。失敗したら移行全体が止まり今のまま | 移行の記録 |
| 反映の途中で失敗して半分だけ変わる | 行ごとに独立。次の確認で残りが出る。もう一度押せば続きだけ直る | 再確認の件数 |
| 設計図の書き間違い | 形の検査の試験・PR の審査・押す前の確認画面 | CI・確認画面 |
| Bot の順番が低くてロールを直せない | 確認の段階で「できない」に出して実行しない（KGI-6） | 確認画面の「できない」件数 |
| 間違えて大事な物を消す | 消す処理を作らない。消す候補を出すだけ | 試験で DELETE 呼び出しが無いこと |
| 確認のあとに誰かが手で変えた | digest が変わり 409。確認し直し | 409 の表示 |

戻し方：便ごとに PR を戻す。便1 の DB は §4-1 の戻し方。Discord 側で反映した変更は、設計図を前の形に戻して PR → もう一度反映（反映の記録に前の値が残る）。

## 8. 合格の判定（基準と検証方法）

| 基準 | 検証方法 |
|---|---|
| KGI-1 テナント001で顧客用・自社用の 2 つが出て、顧客用の行が変わらない | 登録前後で `ai_ro.public__tenant_discord_config` の tenant 1 customer 行の guild_id が同じ／画面の 2 つのタブ |
| KGI-2 顧客用の部屋の外に 1 回書くと通知 1 件 | Discord の通知と `notification_logs` 1 件 |
| 自社用に書いても お客さん向けの処理が動かない | 自社用に 1 回書いて 部屋の外の通知 0 件・受け取り係の記録に「own server」1 行 |
| KGI-3 読み取り → 設計図 → 確認で 変わる数 0 | 確認画面の件数 |
| KGI-4 4 種類の変更で 4 件 → 反映 → Discord で 4 件変化 → 再確認 0 件 | 確認画面・Discord の目視・`discord_server_apply_runs.result` の成功 4 |
| KGI-5 外したチャンネルが残り、消す候補に 1 件 | Discord の目視・確認画面 |
| KGI-6 Bot より上のロールを変える行が実行されず理由が出る・他は反映 | 結果の表示・`result` の「できない」1 |
| KGI-7 手作業は Bot ロールの移動 1 回だけ | 試験の手順書で数える |
| 画面の文字が t() 経由・ja/en 同じキー | 既存の i18n 検査（CI） |
| 消す処理が無い | 試験で discord_own_server.py（新規） に `"DELETE"` の Discord 呼び出しが無いこと |

改訂2（2026-11-04、便1b のカード作成時の実物確認による。Opus の技術判断）
- 3 行目の検証方法を「自社用に 1 回書いて 部屋の外の通知 0 件・受け取り係の記録に `unknown guild_id=<自社用サーバーの番号> — 未登録 guild のため無視` 1 行」に読み替える。§4-3 改訂1 で専用の記録の一文を作らないことにしたため（事実：`backend/app/discord_gateway/client.py:411-416` に今ある一文）
- 同じサーバーを二重に登録しようとしたとき（`uq_tenant_discord_config_guild_id` に当たる）、今は 500 になる。便1b で招待の戻りがこれを受け、`reason=guild_already_registered` で画面に返す（顧客用・自社用の両方。成功の道は変えない）
- 自社用の招待の開始は、`channels.manage` に加えて `tenant.profile.edit` も要る（§4-9 の「変えるのは tenant.profile.edit」と揃える）。既存の `require_permission` はどれか 1 つで通る形なので、`load_user_permissions`（`backend/app/auth/dependencies.py:598`）で 2 つ目を確かめる
- 実装カード：docs/handoff/discord-server-management/card-bin1b-own-server-register.md

改訂3（2026-11-05、便2 のカード作成時の実物確認による。Opus の技術判断。origin/main 3175aca5e で確かめた）
- 新しい 2 表は、§4-1 の「同じ移行ファイル」ではなく便2 の新しい移行 migrations/20261106_120000_create_discord_server_snapshot_tables.sql（新規）に置く。改訂1 で移行を便1a・便1b に分けたため、便1 の移行には入っていない（事実：`migrations/` の最後は `20261106_100000_tenant_discord_config_purpose_pk.sql`）
- §4-6 の「設計図と同じ形に直して」を「Discord の返事から必要な項目だけを抜いた形（`version: 1`）」に読み替える。権限の名前と数字の対応は便3 の discord_blueprint.py（新規）1 か所だけに置く約束（§4-5）なので、便2 で同じ対応を別に持たない。設計図の tenant_<id>.json（新規）へは Opus が便3 の対応表で直す
- サーバーの番号を記録に入れない約束（§4-1）を守るため、@everyone のロール（番号がサーバーの番号と同じ。Context7 /discord/discord-api-docs）は `"@everyone"` と書く
- 人を記録に入れない約束（§4-1）を守るため、チャンネルの人ごとの上書き（`type=1`）は外して数だけ残す
- §4-1 の「ai_cloud のビューに新しい表の列の扱いを足す」は行わない。§11 U2 のとおり分類の無い文字の列は自動で伏せる側に倒れ、Opus は ai_ro で読むため。ai_cloud の移行と分類表は触らない
- `tenant_id` に `public.tenants(id)` への外部キーを付ける（登録の表 `tenant_discord_config_tenant_id_fkey` と同じ）。行の制限（RLS）は付けない（登録の表と同じで、プログラムが tenant_id で絞る）
- CI の許可リストと対応表を更新する：`.github/workflows/migration-guard.yml:224` の `PUBLIC_TABLES`（223 行の注記「新しいテーブルを public に追加した場合はここを更新すること」）、`backend/app/realtime/topics.py` の `NO_SIGNAL_ROUTES`（便1b の改訂4 で載せ忘れが CI 赤になった）
- JSONB への書き込みは、試験の SQLite で `CAST(… AS JSONB)` が使えないため、`backend/app/routers/meta_inbox.py:152-158` と同じく方言で分ける
- 便2 の確かめ方（KGI-3 の前半）：テナント001の自社用テストサーバーで「今のサーバーを読み取る」を押す → 「読み取りました（ロール n・チャンネル n）」が出る → `ai_ro.public__discord_server_snapshots` に 1 行増え、n が Discord の画面のロールとチャンネルの数と同じ
- 実装カード：docs/handoff/discord-server-management/card-bin2-own-server-snapshot.md

## 9. 外部・過去事例の参照と我々への応用

- HashiCorp Terraform の公式文書（Context7 `/websites/developer_hashicorp_terraform` で 2026-11-04 に確認）
  - apply は plan に書かれた変更だけを行う
  - plan の後に状態が変わると、その plan は古くなり捨てられる（HCP Terraform の saved plan）
  - 応用：確認（§4-7）と反映（§4-8）を分け、digest で古い確認を断る
  - 適用の限界：Terraform は状態を保存するが、本設計は Discord の今の姿を毎回その場で読む。数値の効果の根拠には使わない
- 社内の過去事例：顧客用の自動作成（`backend/app/routers/discord_auto_setup.py:536-589`）の「名前・種類・親で既存を探して二重に作らない」をそのまま使う
- Discord の決まり（Context7 `/discord/discord-api-docs`）：Bot は自分より上のロールを変えられない → §4-7 の「できない一覧」

## 維持の仕組み

- 設計図の形の検査と、「顧客用だけ」の漏れ止めは CI の試験で毎回動く
- 設計図の持ち主は Opus。変更は PR と審査を通す
- 反映の記録（`discord_server_apply_runs`）で、いつ誰が何を変えたかを後から読める

## 10. ADR 案（正式な番号は PO 承認のあとに採る）

- 題：Discord の自社サーバーを設計図で管理する
- 決定：
  1. サーバーの登録は `tenant_discord_config` 1 か所に置き、用途（customer/own）で分ける
  2. 自社サーバーの望む形は、リポジトリの設計図（JSON）を正とする
  3. 反映は「確認 → 押す」の 2 段で、確認した内容と違えば実行しない
  4. 自動では消さない。Bot より上のロールは変えない
- Why：PO の言葉（ideal-state.md）。人がサーバーを逐一直さず、話す → ボタンで済ませるため。消すと中の書き込みが戻らないため

## 11. 設計審査（同じ AI による自己審査。独立した第二者審査ではない）

判定：**APPROVE**（設計として実装可能）

根拠：
- 既存仕様・ADR との整合：kgi.md の 4 つの約束を守っている（顧客用の自動作成は触らない／消さない／登録は 1 か所／金型だけ）。ADR-091 の権限の範囲内（ロールの管理・チャンネルの管理で足りる。R§5）
- 実物との照合：登録の表を読む 8 か所すべてを file:line で特定（R§3）。受け取り係の 5 か所の呼び出しを特定（R§4）
- 受入条件：KGI 1〜7 すべてに観測できる判定方法がある（§8）
- 実装範囲：便ごとに触るファイルと変更前後を記した

未解決（実装カードを出す前に片付ける）：
- U1 【解決 2026-11-04】主キーの名前は `tenant_discord_config_pkey`（本番の読み取り。ほかに `tenant_discord_config_tenant_id_fkey`・`uq_tenant_discord_config_guild_id`）。この表を参照するほかの表の外部キー・行の見張り（trigger）・行の制限（policy）は 0 件、行の制限は無効（`relrowsecurity=false`）。列は tenant_id・guild_id・created_at・updated_at・connected_by_staff_id の 5 つ
- U2 【解決 2026-11-04】ai_cloud は分類表に無い文字の列を伏せる（`migrations/20261024_100000_create_ai_cloud_meta.sql` の build_views、分類なしで文字の型は mask に落ちる）。新しい列・表を足しても失敗せず伏せる側に倒れる。便1 では ai_cloud の分類表を変えない（purpose は伏せたままでよい。Opus は ai_ro で読む）
- U3 テナント001の自社用テストサーバーの用意（PO 側。便1 のマージ後でよい）
- U4 HIGH LIFE JPN の今の登録が、PO の画像の自社サーバーと同じか（R§8）。同じなら、HIGH LIFE JPN は今の行を自社用に移し、顧客用を別に登録し直す話になるため、HIGH LIFE JPN に使う前に PO に確かめる

便2 のカードの審査（2026-11-05、同じ AI による自己審査）：**APPROVE**
- 実物との照合：カードの行の目印（`backend/tests/conftest.py:311-312`・`:1230`・`:1730`、`scripts/run_all_migrations.sh:1225`、`backend/app/main.py:51`・`:325`、`backend/app/realtime/topics.py:103`、`.github/workflows/migration-guard.yml:223-224`、`backend/app/routers/meta_inbox.py:152-158`、`frontend/src/pages/admin/discord-config.css:57` の `dc-actions`、`frontend/src/locales/ja.json:3491` の `discordOwnServer`）を origin/main 3175aca5e で読んで確かめた
- 便1b の CI 赤 3 件（試験の中の表の定義・即時反映の対応表・試しの移行の仮の表）をカードの中で先に塞いだ
- 約束（読むだけ・サーバーの番号を記録しない・人を記録しない・消す処理なし）を試験 9 本で機械に確かめさせる
- U3 は解決（テナント001の自社用テストサーバーは PO が用意・登録済み、2026-11-05）。U4 は HIGH LIFE JPN に使う前に確かめる（便2 はテナント001だけで確かめるので止めない）
