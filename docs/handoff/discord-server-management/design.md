# 設計: Discord の自社サーバーを、設計図とボタンでシステムと Bot が管理する

> この文書は何か：KGI 1〜7 を満たすための作り方です。実装役（クラウドの Sonnet）が迷わず作れる粒度で書きます。

- 親: [docs/specs/discord-server-management/README.md](../../specs/discord-server-management/README.md)
- あるべき姿: [ideal-state.md](../../specs/discord-server-management/ideal-state.md)　／　KGI: [kgi.md](../../specs/discord-server-management/kgi.md)
- 下調べ: [recon.md](recon.md)（`docs/handoff/discord-server-management/recon.md`。以下「R§n」は recon.md の節）
- 対象 ADR: ADR-091（Bot 権限の正本・変えない）、ADR-072（commit 後の reset_tenant_context）、ADR-027（画面の文字は t()）、ADR-144（画面部品の金型）、ADR-135・ADR-136（migrations を含む PR の GO 手順）、ADR-1037（移行のロック待ち 1 秒）、ADR-1024（ai_ro ビュー）。新規 ADR 案は §10
- ADR の文書: `docs/adr/ADR-027-ui-internationalization.md`・`docs/adr/ADR-135-release-stowaway-prevention.md`・`docs/adr/ADR-144-ui-component-governance.md`
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
- 新しい 2 表は、§4-1 の「同じ移行ファイル」ではなく便2 の新しい移行 migrations/20261106_120000_create_discord_server_snapshot_tables.sql（新規）に置く。改訂1 で移行を便1a・便1b に分けたため、便1 の移行には入っていない（事実：`migrations/` の最後は `migrations/20261106_100000_tenant_discord_config_purpose_pk.sql`）
- §4-6 の「設計図と同じ形に直して」を「Discord の返事から必要な項目だけを抜いた形（`version: 1`）」に読み替える。権限の名前と数字の対応は便3 の discord_blueprint.py（新規）1 か所だけに置く約束（§4-5）なので、便2 で同じ対応を別に持たない。設計図の tenant_<id>.json（新規）へは Opus が便3 の対応表で直す
- サーバーの番号を記録に入れない約束（§4-1）を守るため、@everyone のロール（番号がサーバーの番号と同じ。Context7 /discord/discord-api-docs）は `"@everyone"` と書く
- 人を記録に入れない約束（§4-1）を守るため、チャンネルの人ごとの上書き（`type=1`）は外して数だけ残す
- §4-1 の「ai_cloud のビューに新しい表の列の扱いを足す」は行わない。§11 U2 のとおり分類の無い文字の列は自動で伏せる側に倒れ、Opus は ai_ro で読むため。ai_cloud の移行と分類表は触らない
- `tenant_id` に `public.tenants(id)` への外部キーを付ける（登録の表 `tenant_discord_config_tenant_id_fkey` と同じ）。行の制限（RLS）は付けない（登録の表と同じで、プログラムが tenant_id で絞る）
- CI の許可リストと対応表を更新する：`.github/workflows/migration-guard.yml:224` の `PUBLIC_TABLES`（223 行の注記「新しいテーブルを public に追加した場合はここを更新すること」）、`backend/app/realtime/topics.py` の `NO_SIGNAL_ROUTES`（便1b の改訂4 で載せ忘れが CI 赤になった）
- JSONB への書き込みは、試験の SQLite で `CAST(… AS JSONB)` が使えないため、`backend/app/routers/meta_inbox.py:152-158` と同じく方言で分ける
- 便2 の確かめ方（KGI-3 の前半）：テナント001の自社用テストサーバーで「今のサーバーを読み取る」を押す → 「読み取りました（ロール n・チャンネル n）」が出る → `ai_ro.public__discord_server_snapshots` に 1 行増え、n が Discord の画面のロールとチャンネルの数と同じ
- 実装カード：docs/handoff/discord-server-management/card-bin2-own-server-snapshot.md

改訂4（2026-11-05、便3 のカード作成時の実物確認による。Opus の技術判断。origin/main 63cadad20 で確かめた）
- 便3 を 2 つに分ける（変更は一度に 1 つ）。便3a＝§4-5 設計図の形と検査・最初の設計図 tenant_1.json・§4-7 確認・画面の「確認する」（KGI-3）。便3b＝§4-8 反映・画面の「反映する」（KGI-4〜6）。便3a は Discord に書かない（呼ぶのは GET だけ）。どちらも migrations なし
- 事実（本番の読み取り、`ai_ro.public__discord_server_snapshots` id=1、2026-11-05 02:50 UTC）：テナント001の自社用サーバーは ロール 2（@everyone・Bot の「Sales Anchor」managed=true）、チャンネル 4（カテゴリ「テキストチャンネル」「ボイスチャンネル」・文字の「一般」・声の「一般」）。上書きは 0 件
- 扱う種類は ロール・カテゴリ（type 4）・文字のチャンネル（type 0）だけ。ほかの種類（声 type 2 など）は §2 の対象外なので、確認の 3 つの一覧のどれにも出さない（消す候補にも出さない）
- managed=true のロール（Bot 自身・連携が作るロール）は設計図に書かず、一覧のどれにも出さない。Bot 自身のロールは上書きの相手として `"@bot"` と書ける（Bot の利用者番号を `GET /users/@me`、その人のロールを `GET /guilds/{guild}/members/{bot}` で読む。後者は特別な許可が要らない：Discord 公式 developers/topics の Get Guild Member、List Guild Members だけが GUILD_MEMBERS を要る）
- 権限の名前と数字の対応は Discord 公式の表（github.com/discord/discord-api-docs `developers/topics/permissions.mdx`、2026-10-29 更新 e3ea58903 を 2026-11-05 に取得。Context7 は月の上限で使えなかったため公式を直接読んだ）の 52 個（1<<0〜1<<52、47 番は表に無い）。表に無い数字（今の @everyone には 1<<47 が立っている）は比べず、反映のときも今の値をそのまま残す。名前に直せないために「変わる」が出続けることを防ぐ
- 設計図の `sync_with_category` は使わない。Discord にその項目は無い。チャンネルの見せ方は各チャンネルの `overwrites` に書いた分だけを比べる
- 上書きは書いた相手だけを比べる。Discord にあって設計図に無い相手（managed のロールのうち Bot 以外を除く）は「消す候補」に出す（自動で外さない）
- 「できない」の判定（Discord 公式 permissions.mdx「Permission Hierarchy」と channel.mdx「Edit Channel Permissions」）：Bot の一番上のロールの順番と同じか上のロールを変える行／Bot が持たない権限（@everyone と Bot のロールの権限を合わせたもの。ADMINISTRATOR があれば全部持つ）をロールに付ける行・上書きで許す/拒む行／ADMINISTRATOR の無い Bot が上書きで MANAGE_ROLES を書く行／@everyone の名前を変える行
- 設計図の検査に 1 つ足す：@everyone の VIEW_CHANNEL を拒む上書きがあるカテゴリ・チャンネルには、`"@bot"` に VIEW_CHANNEL を許す上書きも書く。無いと Bot がその中を見られなくなり、続きの反映が 403 になる（事実：`backend/app/routers/discord_auto_setup.py` の「Cause F」の注記と同じ理由）
- 色は `color`（数字）で比べる。反映で送るときは公式の勧めどおり `colors.primary_color` で送る（`color` は非推奨。guild.mdx Modify Guild Role）
- 確認の一覧の 1 行の単位：作る物は 1 物 1 行（作るときの上書きも含む）。直す物は 1 物 1 項目 1 行。上書きは 1 物 1 相手 1 行。KGI-4 の「4 種類で 4 件」はこの単位で数える
- 確認の API は `tenant.profile.edit` を要る（ボタンを押すと Discord に読みに行くため。読み取りのボタンと同じ）
- 設計図の検査にもう 1 つ足す：文字のチャンネルの名前に空白・英大文字を入れない（Discord が文字のチャンネル名を小文字・ハイフンに直すため、直された名前と比べて「変わる」が出続けるのを防ぐ）
- 実装カード：docs/handoff/discord-server-management/card-bin3a-blueprint-plan.md
- 便3a カードの審査（2026-11-05、Opus の自己審査。独立した第二者の審査ではない）：APPROVE。根拠：カードに書いた行の目印（`backend/app/routers/discord_own_server.py` の guild_id の SQL・`backend/tests/test_realtime_topics.py:29`・`frontend/src/lib/api.ts:13-21` の `ApiError.status`・`backend/tools/export_openapi.py`・`scripts/check_test_schema_dup.py`・guards の 4 ファイル・画面の試験 2 ファイル）を実物で確かめた。審査で直した点：`discord_server_apply_runs` は試験の共通表（conftest）に無いので、行が増えない試験は `discord_server_snapshots` だけにし、書き込みが無いことは差分の検索で確かめる形にした。未解決：無し（tenant_1.json で 0 件になることは試験 §4-2 の 1 と本番の「確認する」で確かめる）

改訂5（2026-11-05、便3b のカード作成時の実物確認による。Opus の技術判断。origin/main a7a66a2cc で確かめ、f07c538ea でも該当ファイルに差が無いことを確かめた）
- 便3a の審査役の指摘 3 件を便3b の最初に直す：M1 親のカテゴリが「できない」のチャンネルが「消す候補」に間違って出る（`backend/app/services/discord_blueprint.py:442-445` で探す前に飛ばしている）／M2 設計図のファイルが読めないと 500 になる（`backend/app/routers/discord_own_server.py:233-236` が `ValueError` だけ受ける）／M3 「GET だけ」の試験が文字の数え方で、`_READ` の変数を通すと書き込みを見落とす（`backend/app/routers/discord_own_server.py:179`・`backend/tests/test_discord_own_server_snapshot.py:258-262`）→ ast で `method=` に渡す値を全部調べる形にする
- 反映の中身（何を Discord に送るか）は確認と同じ `build_plan` が 1 行ごとに作る（比べ方を 2 か所に書かない）。確認の返事と `plan_digest` には入れない（今の digest と試験がそのまま通る）。サーバーの番号は `{guild}`、同じ反映の中で先に作る物は `{ref:role:<key>}` の印で持ち、反映する係がその場で本物の番号に直す
- 親が新しく作るカテゴリのチャンネル：今の比べ方の行はそのまま、送る中身だけ `{ref:category:<key>}` にする（そのままだと親を外す操作になる）
- 送り方（Discord 公式 github.com/discord/discord-api-docs の guild.mdx Create/Modify Guild Role・Create Guild Channel、channel.mdx Modify Channel・Edit Channel Permissions、permissions.mdx Role Colors Object を 2026-11-05 に Opus が直接読んだ。Context7 は月の上限で使えなかったため、起動指示で許された公式の直接確認に代えた）：ロールの色は `colors.primary_color`、権限の数は 10 進の文字、上書きは `PUT /channels/{id}/permissions/{相手}` に `type 0`・`allow`・`deny`。`lock_permissions` は Modify Channel に無いので使わない
- 表に無いビット（今の @everyone の 1<<47）は、ロールの権限でも上書きでも今の値を残して送る（改訂4 の続き）
- 同時に 1 本だけ：Redis の `SET NX EX 600`（前例 `backend/app/tasks/viewer_inventory_cache.py:74`）。Redis につながらないときは 503 で止める（同時に 2 本走る道を残さない）。鍵は終わったら必ず外す
- 1 行失敗しても続ける。作る行が失敗したら、それを使う行は Discord を呼ばずに「失敗（先に作る物が失敗）」にする
- 消す処理は書かない：API と反映する係のファイルに `"DELETE"` の文字が無いことと、method が POST・PATCH・PUT の外なら呼ばないことを試験で確かめる
- 反映の記録の表 `discord_server_apply_runs` の試験用の形は共通の試験の準備（conftest）に足す（`scripts/check_test_schema_dup.py:23-26` で conftest は対象外。便1b の CI 赤の再発防止）
- 実装カード：docs/handoff/discord-server-management/card-bin3b-apply.md
- 便3b カードの審査（2026-11-05、Opus の自己審査。独立した第二者の審査ではない）：APPROVE。根拠：カードに書いた行の目印（`backend/app/services/discord_blueprint.py:441-446`・`:477-480`・`:507-512`、`backend/app/routers/discord_own_server.py:90-98`・`:156-166`・`:179`・`:212-276`、`backend/app/services/discord_rest.py:26-42`、`backend/app/cache.py:62-64`、`backend/app/services/audit.py:277-286`、`backend/app/realtime/topics.py:104`、`backend/tests/test_realtime_topics.py:35-40`、`backend/tests/conftest.py:313-314`・`:1244-1253`・`:1744`、`backend/tests/test_discord_own_server_snapshot.py:258-262`、`frontend/src/pages/admin/DiscordOwnServerPanel.test.tsx:131-137`、`frontend/src/components/Badge.tsx:4`、移行の表の定義 `migrations/20261106_120000_create_discord_server_snapshot_tables.sql:35-48`）を実物で確かめた。KGI-4〜6 を試験で機械に確かめさせ、本番の確かめはテナント001の自社用テストサーバーで PO が画面で見る。未解決：U4（HIGH LIFE JPN に使う前に PO に確かめる。便3b はテナント001だけで確かめるので止めない）

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
- 守り手: `backend/tests/test_discord_blueprints.py`（CI の pytest で毎回、設計図の形と権限の名前の表を検査する）

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
- 実物との照合：カードの行の目印（`backend/tests/conftest.py:311-312`・`:1230`・`:1730`、`scripts/run_all_migrations.sh:1227`（ab8a6f725）、`backend/app/main.py:51`・`:325`、`backend/app/realtime/topics.py:103`、`.github/workflows/migration-guard.yml:223-224`、`backend/app/routers/meta_inbox.py:152-158`、`frontend/src/pages/admin/discord-config.css:57` の `dc-actions`、`frontend/src/locales/ja.json:3494`（ab8a6f725）の `discordOwnServer`）を origin/main 3175aca5e で読んで確かめた
- 便1b の CI 赤 3 件（試験の中の表の定義・即時反映の対応表・試しの移行の仮の表）をカードの中で先に塞いだ
- 約束（読むだけ・サーバーの番号を記録しない・人を記録しない・消す処理なし）を試験 9 本で機械に確かめさせる
- U3 は解決（テナント001の自社用テストサーバーは PO が用意・登録済み、2026-11-05）。U4 は HIGH LIFE JPN に使う前に確かめる（便2 はテナント001だけで確かめるので止めない）

---

# 第2段 設計（2026-11-05 作成・Fable 審査 4 回目で APPROVE・2026-11-06 PO 承認）

根拠: recon の「第2段 recon」（R2-1〜R2-7）。要件: `docs/specs/discord-server-management/ideal-state.md` 2026-11-05 節。KGI: `docs/specs/discord-server-management/kgi.md` 第2段 8〜16。

## S2-1 目的（PO の言葉から）
自社サーバーのロールと知らせを、人が Discord で直さずアプリの登録どおりに保つ。アプリの役割を変えれば Discord のロールが付け外しされ、担当決定・お客さんの返信・部屋の外の書き込みが決まった部屋に担当者のメンションつきで届く。

## S2-2 対象と対象外
- 対象: 自社用サーバー（purpose='own'）だけ。顧客用サーバーの今の動き（`backend/app/services/discord_role_sync.py` の規模ロール・auto-setup・部屋の外の通知の中身）は変えない
- 対象外: アプリに登録していない人のロール全部（アプリの役割と同じ名前のロールでも）。Bot は触らない。Discord での手の操作は各社の責任（PO 決定 2026-11-05「2」）
- 対象: アプリで消したスタッフ（辞めた人）。Bot が管理するロールを外し、自社サーバーから外す（PO 決定 2026-11-05「1」「1,消したときだけ外す」＝D2-7）。消したあとのこの扱いは「登録していない人」の対象外より先に決めた例外で、消した時点の番号 1 つだけに行う
- 対象外: 配信の失敗の知らせを管理側へ移す直し（別テーマ。R2-5）

## S2-3 決めた作り（代替案と選んだ理由）

### D2-1 アプリの役割と Discord のロールを番号でつなぐ
- 変更: 各テナントの `{schema}.roles` に `discord_role_id TEXT NULL` を足す（部分一意索引 WHERE discord_role_id IS NOT NULL）。つなぎの正本はここ 1 か所。設計図ファイルにアプリの役割を書かない（DB の SSOT）
- 確認画面（build_plan）の入力に「アプリの役割の一覧（隠す役割を除く＝`backend/app/routers/roles.py:53` と同じ条件）」を足す。1 件ずつ:
  - discord_role_id あり → その番号のロールを探す。名前・色が違えば「変える」（PATCH）。見つからなければ「できない（Discord で消された）」と理由を出す
  - なし → 同じ名前を探す。1 件なら「つなぐ」（Discord は変えず番号を保存）。2 件以上なら「できない（名前が重なっている）」＝KGI-11。0 件なら「作る」（POST。返ってきた番号を保存）
  - 色はアプリの '#rrggbb' を数に直して送る
- 確認画面の行に「つなぐ」という DB だけの行種を足す（method は `"DB"`。Discord には送らない）。`apply_plan`（`backend/app/services/discord_blueprint_apply.py:72`）は Discord への送信だけを扱い DB に書かない（R2-6b）ため、書き戻しは反映の呼び出し元（反映ボタンの API）で、`apply_plan` の結果を受けてから行う:
  - 書き戻す単位: アプリの役割 1 件につき 1 回の `UPDATE {schema}.roles SET discord_role_id = :did WHERE id = :rid AND discord_role_id IS NULL`。「作る」は結果の新しい番号、「つなぐ」は確認画面で見つけた番号。全件を 1 回の commit にまとめ、テナントの文脈を付けて行い、commit のあと付け直す（ADR-072）
  - 「作る」が Discord で通ったのに書き戻しが失敗したとき: 次の確認で同じ名前が 1 件見つかり「つなぐ」になるので、二重には作らない
- 消された役割（KGI-10b）: 役割を消すと、その役割の行と discord_role_id は消え（`backend/app/routers/roles.py:357`、user_roles は CASCADE＝R2-2）、点検はその番号を知る手段を失う（Fable 審査 N1）。そこで:
  - 新しい表 `{schema}.discord_retired_roles`（discord_role_id TEXT PRIMARY KEY、retired_at）を足す。役割の DELETE と同じ commit で、消す行に discord_role_id があればその番号を 1 行入れる
  - 中身は「以前アプリの役割だった Discord のロールの番号」だけ。roles と同じ番号を同時には持たない（DB の SSOT。消したあとにだけ移る）
  - 点検（D2-3）はこの番号も「Bot が管理するロール」に入れ、全員から外す。Discord のロール自体は残し、確認画面の「消す候補」に出す
  - 同じ名前の役割をアプリで作り直したときは、確認画面で「つなぐ」になり、その番号を discord_retired_roles から消して roles に戻す（同じ commit）
- 代替案: 名前だけでつなぐ（先例 `discord_role_sync.py:93-95` の型）→ 名前を変えると別のロールを作ってしまうので不採用（KGI-10a を満たせない）

### D2-2 「スタッフ」ロール 1 つで 3 つの知らせの部屋を見せる
- 設計図ファイルに Bot が管理するロール「スタッフ」を 1 つ書く（番号は第1段の取り込みの仕組みで設計図に入る）。アプリの役割ではないので DB には持たない
- 知らせの 3 部屋は @everyone に VIEW_CHANNEL 拒否、「スタッフ」と `"@bot"` に VIEW_CHANNEL 許可（`"@bot"` が無いと Bot が部屋を見られず webhook を作れない。設計図の検査も止める＝R2-6b。Fable 審査 N3）
- 代替案: 部屋の見せ方に「アプリの役割の全部」を並べる → 役割が増えるたびに見せ方が変わり、ボタンを押すまで新しい役割の人が部屋を見られない。顧客用の auto-setup にも「Sales Anchor Staff」1 つで見せる先例がある（`docs/adr/ADR-091-discord-bot-scope-definition.md:60`）ため、1 つのロールに寄せる

### D2-3 スタッフのロールの付け外し（点検して合わせる型）
- 新しい処理 `sync_own_server_staff_roles(tenant_id)` を 1 つ作る。やること:
  1. 欲しい姿 = 状態が active で discord_user_id のあるスタッフごとに、user_roles（staff.user_id = user_roles.user_id）の役割の discord_role_id ＋「スタッフ」
  2. Bot が管理するロール = そのテナントの roles.discord_role_id の全部 ＋ discord_retired_roles の番号の全部 ＋「スタッフ」の番号
     - 「スタッフ」の番号の引き方: 会社の設計図（`blueprint_path(tenant_id)`）のロール「スタッフ」の discord_id。まだ書き足されていなければ、Discord のロール一覧から同じ名前を探す（1 件ならそれ、0 件・2 件以上なら点検を止めて記録に理由を残す）。第1段 4-8 の見分け方と同じ（Fable 審査 N6）
  3. 見る相手は「アプリに登録したスタッフ（discord_user_id のある人。状態を問わない）」と「discord_retired_members の人」だけ（PO 決定 2026-11-05「2」＝案B、と辞めたときの決定＝D2-7）。1 人ずつ Get Guild Member（`GET /guilds/{g}/members/{u}`）で今のロールを読む。サーバーにいなければ（404）飛ばす
     - 先に片付け: discord_retired_members の番号が今の staff にもある（同じ人を登録し直した）なら、その行を消して staff として扱う（staff の discord_user_id はテナント内で 1 つだけ＝`migrations/019_create_staff_tables.sql:55`）
     - 状態が active の人: 手順1 の欲しい姿と、管理するロールだけを比べる。足りなければ PUT、余れば DELETE
     - 状態が active でない人（inactive・pending）: 管理するロールを全部外す。サーバーからは外さない
     - discord_retired_members の人: 管理するロールを全部外す。kick が true の行（消したスタッフ）は、続けて自社サーバーから外す（D2-7）。終えたら（または 404 なら）その行を消す
     - 管理していないロール（手作りのロール）は見ない＝KGI-10
  4. アプリに登録していない人には何もしない。全員の一覧（List Guild Members）は読まない。アプリの役割と同じ名前のロールを手で付けられていても外さない（PO 決定「Discordのサーバー先で手動操作を行うのはそのテナントごとの責任なのでそこは関与しなくて良い」）
     - スタッフを消すとき（`backend/app/routers/staff.py:755` の DELETE と同じ commit。commit は :761）と、スタッフの discord_user_id を変えるとき（`backend/app/routers/staff.py:665` の PATCH で、元の値があり新しい値と違うとき）は、同じ commit で元の discord_user_id を `{schema}.discord_retired_members`（discord_user_id TEXT PRIMARY KEY、kick BOOLEAN NOT NULL、retired_at）に入れる。消すときは kick=true、番号を変えるときは kick=false（番号を変えたときに元の番号からロールを外す＝PO 決定 2026-11-05「1,アプリ側でdiscordのIDを変更したら元のIDからはロールは自動で外す」）。行が消えたあとも、次の点検でその人を扱える
     - 同じ番号が 2 度入るとき（Fable 審査 N11）: `INSERT ... ON CONFLICT (discord_user_id) DO UPDATE SET retired_at = now(), kick = {schema}.discord_retired_members.kick OR EXCLUDED.kick`。staff の DELETE が重なりで失敗しない。一度 kick=true になった行は false に戻さない
     - 消した役割の番号（discord_retired_roles）も、見る相手からだけ外す。登録していない人に付いていても外さない
     - 1 回の点検で送る GET はスタッフの人数分。回数制限は discord_rest の待ちに任せる（R2-3）
- 送り方: 先例と同じ `backend/app/services/discord_rest.py` の `discord_api_request` を使う（R2-3。429 の待ち・再試行を持つ）
- いつ動くか: (a) 役割を書く所（`backend/app/routers/roles.py` PUT/DELETE、`backend/app/services/role_assignment.py`、`backend/app/routers/staff.py` の POST:582/PATCH:665/DELETE:741）の commit のあとに `asyncio.create_task` で（先例 `backend/app/routers/leads.py:728` と同じ）。(b) Celery の定期作業で 5 分ごとに全テナントの自社サーバー分（取りこぼし・あとからサーバーに入った人の分）＝KGI-9・KGI-16 の「5 分以内」
  - 利用者を作るときの既定の役割（`backend/app/routers/auth.py:156` の user_roles への INSERT。`/register`＝:62 の中）は (a) に入れず、(b) の定期で拾う（Fable 審査 N14）
- 同時に 2 本走らないよう、テナントごとに Redis の短い鍵で 1 本にする
- DELETE の範囲: この処理の `/guilds/{g}/members/{u}/roles/{r}`（ロールを外す）と、D2-7 の `/guilds/{g}/members/{u}`（自社サーバーから外す。kick=true の行だけ）の 2 つだけ。設計図の反映（`_ALLOWED_METHODS`＝`backend/app/services/discord_blueprint_apply.py:17`）には DELETE を足さない。チャンネル・ロールそのものは今までどおり消さない
- 代替案: 書いたときだけ送る → スタッフの削除やサーバーへの後からの参加を取りこぼす。点検型は先例よりも 1 段強い

### D2-4 知らせの部屋と送り先のつなぎを自動で作る
- 設計図ファイルに「アサイン連絡」「返信連絡」「部屋の外の書き込み」の 3 チャンネルを書く（D2-2 の見せ方つき）
- 反映で部屋を作ったあと（またはつなぎが無い部屋に）、Bot が webhook を 1 本作り（`POST /channels/{id}/webhooks`、Manage Webhooks は付与済み＝ADR-091:76）、`{schema}.notification_channels` に行を作る
- 部屋の Discord の番号の引き方（Fable 審査 N12）: 反映の直後は、その反映の結果の discord_id（`backend/app/services/discord_blueprint_apply.py:104`）。以後は、設計図に書き足された discord_id。まだ書き足されていなければ、Discord のチャンネル一覧から同じ名前の文字のチャンネルを探す（1 件ならそれ、0 件・2 件以上なら作らずに確認画面に理由を出す）。D2-3 手順2 の「スタッフ」と同じ見分け方
- `notification_channels` に `blueprint_key TEXT NULL`（設計図の部屋の key。例 `assign_notice`）を足し、部分一意索引で 1 部屋 1 行にする（二重作成の防止）。部屋の Discord の番号は設計図（とその番号の書き足し）だけに持ち、notification_channels には持たない（Fable 審査 N7。番号の二重持ちを避ける）。event_types は部屋ごとに固定: アサイン連絡=lead_assigned、返信連絡=customer_reply_received、部屋の外=discord_outside_ticket_post
- 今ある手で作った行は触らない（blueprint_key が NULL の行）。同じ種類が手作りの行にもあれば 2 か所に届くので、確認画面に「同じ種類の知らせの送り先がほかにもある」と出す
- webhook_url は今の列のまま平文（R2-5。今の画面から入れる行も平文）。暗号化は今の仕組み全体の直しとして別に扱う（残るリスクに書く）

### D2-5 お客さんの返信の知らせ
- 種類を 1 つ足す: `customer_reply_received`（`backend/app/schemas/notification.py` に追加。今の 4 つのどれとも部分文字列が重ならない）
- 送る所（保存が新しい行のときだけ＝二重に送らない）:
  - Discord のお客さんの部屋: `backend/app/discord_gateway/ticket_channel_writer.py:248` の commit と :250-257 の重なりの戻りのあと（:259 の前。新しい行で commit 済みのときだけ）
  - Discord の DM: `backend/app/discord_gateway/dm_writer.py:252` の commit のあと、`msg_row is not None` のときだけ（:231 の中で送ると commit 前に送ってしまう。Fable 審査 N4）
  - Messenger・Instagram: `backend/app/routers/webhook.py:938-947` の今の送信のとなり（今の meta_message_received は変えない）
- メンション: leads の担当（users.id）→ staff.user_id → discord_user_id（`backend/app/services/lead_assign_notifier.py:32-34` と同じ引き方。共通の小さな関数に寄せる）。担当がいない・discord_user_id が無いときはメンションなしで送る
- 中身: お客さんの名前・どこから（Discord / Messenger / Instagram）・アプリの商談の場所。本文は載せない（今の Meta の知らせが個人情報を載せない作法＝`webhook.py` の注記に揃える）

### D2-6 会社ごとに混ざらない
- サーバーの番号はいつも `public.tenant_discord_config` の tenant_id と purpose='own' から引く（1 社 1 行＝R2-4）。役割・スタッフ・知らせは各社のスキーマから読む
- 自動の試験で 2 社分のデータを置き、1 社の役割を変えても、もう 1 社のサーバー宛ての送信が 0 件であることを確かめる＝KGI-10c

### D2-7 辞めたとき（アプリでスタッフを消したとき）
- 根拠: PO 決定 2026-11-05（ideal-state.md「辞めたときの要件」）。消した＝辞めた。無効・番号の書き換えではサーバーから外さない（番号の書き換えは元の番号からロールだけ外す＝PO 決定「1,アプリ側でdiscordのIDを変更したら…」）
- 画面: スタッフを消すと、今も確認の窓が出る（`frontend/src/pages/staff/StaffPage.tsx:377-385` の `ConfirmModal`、「この操作は取り消せません。」＝`common.irreversible`）。この窓の message に、消す相手に discord_user_id があるときだけ 1 行足す: 「Discord の自社サーバーからも外れます。」（新しい鍵 `staff.deleteDiscordKickNote` を ja.json・en.json の両方に足す＝ADR-027。部品は今の ConfirmModal のまま。新しい部品・色の直書きは足さない＝ADR-144）。discord_user_id は今の一覧の応答に入っている（`backend/app/routers/staff.py:120`）
- サーバー側: D2-3 のとおり、消すときに discord_retired_members に kick=true で 1 行入れる。次の点検（消したあとの create_task か 5 分ごと）で、管理するロールを外してから `DELETE /guilds/{own}/members/{u}`（Discord 公式: Remove Guild Member、KICK_MEMBERS が要る。Bot には付与済み＝`backend/app/routers/discord_oauth.py:63`）
  - 送り先は D2-6 の自社サーバー（purpose='own'）だけ。顧客用サーバーには送らない（今の顧客を外す機能 `backend/app/routers/discord_remove.py:141` とは別の処理で、そちらは変えない）
  - 監査の記録に 1 行残す（先例 `backend/app/routers/discord_remove.py:174-179` の action="delete"・table_name="discord_guild_member" と同じ形。record_id はスタッフの id）
  - 外せなかったとき（403 など）: 点検の記録に理由を残し、行は消す（同じ人に何度も送らない）。ロールは先に外し終えている。サーバーの持ち主は Discord が外させない
  - 404（もうサーバーにいない）は外し済みとして行を消す
- 代替案: 消すボタンの処理の中で Discord に直接送る → Discord が落ちていると消す操作ごと失敗するか、外し漏れが残る。点検で送れば 5 分ごとに取り返せるので不採用

## S2-4 変更前と変更後（利用者に見えること）
| | 今 | 変えたあと |
|---|---|---|
| 自社サーバーのロール | 人が手で作る | アプリの役割と同じロールを Bot が作り、名前と色も合わせる |
| スタッフへのロール | 人が手で付ける | アプリの役割どおりに 5 分以内に付け外し |
| 辞めた人 | 人が手で外す | アプリで消すと確認の窓に「Discord の自社サーバーからも外れます」と出て、5 分以内に自社サーバーから外れる |
| 知らせの部屋 | 人が作り、webhook を画面に貼る | 設計図から作られ、つなぎも自動 |
| お客さんの返信 | Meta だけ・メンションなし | Discord・Messenger・Instagram の 3 つ・担当者にメンション |

## S2-5 便の分け方（1 便 1 つの変更・ADR-135/136 の GO の手順に乗せる）
| 便 | 中身 | 移行（migrations） | KGI |
|---|---|---|---|
| 2a | roles.discord_role_id・discord_retired_roles・discord_retired_members（kick 列つき。表を作るだけで、2a では行を入れない）・確認画面と反映でアプリの役割を作る/つなぐ/変える・役割の削除で番号を移す | あり（全テナントの roles に列、表 2 つ） | 8・10a・11 |
| 2b | 「スタッフ」ロール・付け外しの処理と定期作業・スタッフの DELETE（`backend/app/routers/staff.py:755`）と PATCH（:665）で番号を discord_retired_members に移す・辞めた人を自社サーバーから外す（D2-7）・確認の窓の 1 行（ja/en の鍵）。行を入れる処理・外す処理・窓の 1 行を同じ便で出す（Fable 3 回目 N15: 2a の期間に消した人が、窓で知らされないまま後で外されるのを防ぐ） | なし | 9・10・10b・10c・16 |
| 2c | 3 部屋・webhook の自動作成・notification_channels.blueprint_key | あり | 12・14・15 |
| 2d | 返信の知らせ | なし | 13 |

- 2a の分け方（2026-11-06 Opus。1 回に 1 つの変更・第1段 1a/1b の先例）: 2a-1＝列と表 2 つを作るだけ（移行・`backend/app/services/tenant.py` の新しい会社の DDL・構造の試験。プログラムの動きは変えない。カード `card-s2-2a1-role-link-tables.md`）。2a-2＝確認画面・反映の書き戻し・役割の削除で番号を移すプログラム（2a-1 の本番反映のあとにカードを作る）。KGI 8・10a・11 は 2a-2 で満たす

## S2-6 受入条件と検証方法
|基準|検証方法|
|---|---|
| KGI-8 確認画面のロールの数 = アプリの役割の数（隠す役割を除く） | テナント001 で画面の件数と役割の画面の件数を数える・自動の試験 |
| KGI-9 役割を足す/外すと 5 分以内に付く/外れる | テスト用スタッフで時刻を控えて Discord のメンバー画面を見る |
| KGI-10 手作りのロールが残る・登録していない人に触らない | 同じ人に手作りのロールを付けてから KGI-9 を行い、残っていることを見る。登録していない試験用の人に「営業」を手で付け、点検のあとも残っていることを見る・自動の試験（管理しないロールと登録していない人に DELETE を送らない、List Guild Members を呼ばない） |
| KGI-10a 名前を変えても新しいロールができない | 変える前後の Discord のロールの数・確認画面「変える」1 件 |
| KGI-10b 役割を消すと人から外れ、ロールは残る | Discord の目視・確認画面の消す候補 1 件・自動の試験（役割の DELETE のあと discord_retired_roles に 1 行・点検がその番号に DELETE を送る） |
| KGI-10c 他社に届かない | 自動の試験（2 社分） |
| KGI-11 同じ名前が 2 つで止まる | 確認画面の理由の表示・自動の試験 |
| KGI-12〜14 決まった部屋に 1 件ずつ届く | Discord の目視・notification_logs の行の数・自動の試験（Messenger・Instagram は自動の試験だけ） |
| KGI-15 人の Discord 設定の作業 0 件 | 試験の手順書で数える |
| KGI-16 消すと自社サーバーから外れる・無効と番号の書き換えでは外れない | 前提: テスト用スタッフ 2 人を自社と顧客用の両方のサーバーに入れておく（Fable 3 回目 N16）。確認の窓の文を目視・時刻を控えて Discord のメンバー画面を見る・自動の試験（kick=true の行だけ `DELETE /guilds/{own}/members/{u}` を送る・無効の人と kick=false の行には送らない・顧客用サーバーの番号には送らない・同じ番号の 2 度目で staff の DELETE が失敗しない・PATCH で番号を書き換えると元の番号に kick=false の行が 1 つ入り、点検は元の番号の Bot が管理するロールにだけ DELETE を送り、members の DELETE は送らない＝Fable 4 回目 N17） |
| 顧客用サーバーの今の動きが変わらない | 今の試験（discord_role_sync・auto-setup・部屋の外）が全部通る |

## S2-7 リスクと対処・戻し方・測り方
- 登録していない人にアプリの役割のロールが手で付くと、そのまま残る（アプリの登録と Discord が食い違うことがある）。PO 決定で各社の責任とし、Bot は関与しない
- 全員の一覧を読まないので、GUILD_MEMBERS 特権インテントに頼らない（List Guild Members だけが GUILD_MEMBERS を要る＝Discord 公式 `developers/resources/guild.mdx` の List Guild Members の警告。2026-11-05 に Opus が公式を直接読んで確かめた。注記は design.md 第1段 改訂4・§8＝:259）
- Discord の番号の登録間違いで、別の人を自社サーバーから外すおそれ → 外すのは「消したスタッフに登録されていた番号」1 つだけで、確認の窓で消す相手の名前を出す。外された人は招待で入り直せる（Kick は出入り禁止ではない）。書き込みは消えない
- Bot より上のロールを持つ人・サーバーの持ち主は外せない → 点検の記録に理由を残す（D2-7）
- テナントの物理削除（`backend/app/routers/super_admin_tenants.py:167`、会社のデータをまるごと消す SaaS 管理者の操作）では Discord に何もしない（対象外）。その会社の自社サーバーはその会社のもので、スタッフを 1 人ずつ外す処理は D2-7 のスタッフの DELETE だけに付ける（Fable 4 回目 N18）
- Discord の回数制限 → discord_rest の待ちに任せ、5 分ごとの点検で取り返す。1 回の点検で送る数を記録する
- webhook_url の平文 → 今の作法のまま。Bot が作るのは自社サーバーの部屋だけ。漏れたときは部屋の webhook を消して作り直せば無効になる
- 戻し方: 便ごとに revert。移行で足す列は NULL 許容で、使わなければ今の動きに戻る。定期作業は設定から外せば止まる。Discord に付けたロールは残る（消さない作法）ので、外したいときは点検を止めてから人が外す
- 測り方: 点検ごとに「付けた数・外した数・失敗の数」を記録に出す。5 分の点検の失敗が続けば記録から分かる

## S2-8 外部事例
使わない。理由: 根拠は Discord 公式の API 仕様（R2-6）と、同じ付け外しを本番で動かしている社内の先例（R2-3）で足りるため。

## S2-9 ADR
- `docs/adr/ADR-091-discord-bot-scope-definition.md` の業務の表に「自社サーバーのスタッフのロールをアプリの役割どおりに付け外しする（Bot が管理するロールだけ）」「知らせの部屋の webhook を作る」を足す（便2a の PR で）

## S2-10 維持の仕組み
- 自動の試験: 名前を変えても同じ番号を使う・管理しないロールに触らない・他社に送らない・二重に送らない
- 定期の点検（5 分ごと）が、取りこぼしと人の手での付け外しを毎回アプリの登録に戻す

## S2-11 未決（PO に戻すもの）
- 決定済み: D2-3 手順4 は案B（PO 2026-11-05「2」。原文は ideal-state.md）
- 決定済み: 辞めたとき＝アプリで消したとき。ロールを外し自社サーバーから外す・消す前に確認の窓（PO 2026-11-05「1」「1,消したときだけ外す」＝D2-7）
- 決定済み: 番号を書き換えたとき、元の番号の人から Bot が管理するロールを自動で外す。サーバーからは外さない（Fable 3 回目 Q7 を PO に聞いた。PO 2026-11-05「1,アプリ側でdiscordのIDを変更したら元のIDからはロールは自動で外す」）。D2-3 のとおり PATCH で kick=false の行を入れる
- 決定済み: KGI 8〜16 とこの設計を承認（PO 2026-11-06 回答「1、推測は禁止して事実確認を怠らずに…確立したなら進める。」＝選択肢 1「承認する」。最初の便2a の作業カードを作る。便2a は移行を含むので、実装を始める前に PO の確認を取る）

## S2-12 審査の記録
- 2026-11-05 Fable（クラウド・読むだけ・HEAD 28a777d22）: REVISE。必須 3 件（Q1 要件より広い／N1 KGI-10b が作れない／N2 S2-2 と D2-3 の食い違い）、推奨 Q2〜Q4・N3〜N8
- 反映: N1→D2-1 discord_retired_roles。N2・Q1→S2-2・D2-3 手順4 を案A/案B に分け PO へ→PO は案B（2026-11-05「2」）。N3→D2-2 `"@bot"`。N4→D2-5 commit 後。N5→D2-1 DB だけの行種と書き戻しの単位。N6→D2-3 手順2。N7→D2-4 blueprint_key。N8→recon の行番号（この版で実物の grep で全部引き直し）。Q2→KGI-14 に配信の失敗が 0 件。Q3→KGI-11 に「つなぐ前」。Q4→PO の決定の原文を ideal-state に残す（案の決定のとき）
- 2026-11-05 Fable（2 回目・HEAD 60a8545b3）: REVISE。前回の Q1〜Q4・N1〜N7 は直った。N8 は 2 件残り（N9・N10）。新しく必須 Q5（消したスタッフ＝登録していない人から外す設計が KGI-10 と PO 決定より広い）、推奨 Q6・N9〜N14
- 反映: Q5→PO に辞めたときを聞き、決定（消したときだけ外す・サーバーから外す・確認の窓）を ideal-state・KGI-16・D2-7 に入れ、KGI-10 から消したスタッフを外した。Q6→kgi.md に「決まったこと」を分けた。N9→S2-7 の注記の場所を第1段 改訂4（:259）に直した。N10→recon R2-5 の場所を `backend/app/tasks/viewer_inventory_cache.py:63` に直した。N11→D2-3 の ON CONFLICT。N12→D2-4 の部屋の番号の引き方。N13→S2-5 便2a。N14→D2-3 の auth.py:156
- 2026-11-05 Fable（3 回目・HEAD eab189b54）: REVISE。前回の Q5・Q6・N9〜N14 は全部直った。指示した行番号は全部実物と一致。新しく必須 Q7（番号を変えたときの扱いが PO の言葉に無いのに「決まったこと」に入っていた）、推奨 N15（便2a の期間に消した人が窓で知らされずに後で外される）・N16（KGI-16 の試験の前提が無い）。審査は見張り（危ない語の検査）で途中停止
- 反映: Q7→ideal-state から Opus が書いた 1 行を消し、kgi.md と S2-11 の「決めていないこと」へ移して PO に聞く。N15→S2-5 で行を入れる処理を便2b へ移し、外す処理・窓の 1 行と同じ便にした（2a は表を作るだけ）。N16→KGI-16 と S2-6 に前提を足した
- 審査が確かめられなかった所を Opus が手元で読んだ（origin/main）: Kick Members は Bot に求める権限の一覧に入っている（`backend/app/routers/discord_oauth.py` の注記、今の顧客を外す機能 discord_remove.py が使用）。`backend/app/schemas/staff.py:124` StaffProfileUpdate に discord_user_id は無い（本人のプロフィール変更では番号を変えられない＝番号が変わる道は PATCH:665 だけ。POST:582 は新規）。`backend/app/services/discord_rest.py:34` discord_api_request は method を引数で受け、DELETE を止める作りは無い。`frontend/src/locales/ja.json:2083` に staff の名前空間がある
- staff 行を消すほかの道（Fable 4 回目が Grep の道具で確かめた・HEAD 8f2156020）: アプリの中は `backend/app/routers/staff.py:755` だけ（ORM の delete は 0 件）。会社ごと消す道が `backend/app/routers/super_admin_tenants.py:167`（DROP SCHEMA CASCADE＝テナントの物理削除）。ほかは試験と QA の道具だけ（`backend/tests/conftest.py:1809`・`scripts/test_lint_tenant_schema.py:80`・`scripts/qa/seed-tenant.sql:93`・`scripts/qa/cleanup-smoke-data.sh:106`）。staff.discord_user_id を書く道は POST（staff.py:602）と PATCH（:710）だけ
- 2026-11-05 Fable（4 回目・HEAD 8f2156020）: APPROVE。Q7・N15・N16 は直った。S2-12 に書いた手元の事実は全部実物と一致。推奨 N17（KGI-16 の自動の試験に番号の書き換えを足す）・N18（上の未確認を結果に置き換え、テナントの物理削除の扱いを書く）
- 反映: N17→S2-6 の KGI-16 の行。N18→この節の上の行と S2-7 の 1 行
- 未確認のまま残すもの: Create Webhook の権限・Kick が Bot のロールの順番に縛られるか。Remove Guild Member（KICK_MEMBERS）と List Guild Members（GUILD_MEMBERS が要る）は 2026-11-05 に Opus が公式（github.com/discord/discord-api-docs `developers/resources/guild.mdx`）を直接読んで確かめた。Context7 は月の上限で使えなかった。残りは便2b・2c のカードの最初の作業で、試験サーバーへの実際の呼び出しで確かめる
