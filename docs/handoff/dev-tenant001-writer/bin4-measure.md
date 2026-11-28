# 便3・便4 測定結果（本番・生の値）

> 測った日: 2026-11-28 03:26〜03:48 JST（2026-11-27 18:26〜18:48 UTC）。測った場所: 本番 prod1（49.212.137.46）の DB。
> 測った人: Claude Opus（PO の委任に基づく。ccopusgo）。書く鍵は `~/.ssh/salesanchor-dev001-writer`、読む鍵は `~/.ssh/salesanchor-reader`。
> 判定の基準は design.md §6（K1〜K8）。K8 は 14 日後（2026-12-12 ごろ）に数える。

## 便3 で入れた物（PO が Mac で `!` 実行。4 本）

| # | 中身 | 結果 | 控え（戻し方） |
|---|---|---|---|
| (1) | `ai_dev001_writer` の合言葉を VPS の上で作り、`/home/ubuntu/.config/salesanchor/ai-dev001-writer.env`（600・ubuntu・1 行）に置く。記録に残さない設定にしてから ALTER ROLE | ○ すべて | ― |
| (2) | Mac に鍵 `~/.ssh/salesanchor-dev001-writer` を作り、本番の `authorized_keys` に 1 行足す（6→7 行・既存 6 行は控えと同じ） | ○ すべて（最後の表示 1 行だけ台本の誤りで出ず。処理は済み） | `authorized_keys.bak-dev001-writer-20261128025620` |
| (3) | Mac の見張り `agent-danger-hook.sh` に、決まった 1 つの形だけ危険語の照合を外す免除（22 行）。ほかの見張りは変えない | ○ | `agent-danger-hook.sh.bak-dev001-writer-20261128025641` |
| (4) | 直し: 書く鍵の固定コマンドに本番の `.env` を先に足す | ○ すべて | `authorized_keys.bak-dev001-writer-fix-20261128032527` |

### (4) の直しが要った理由（設計 §3-1 との違い）

- 設計 §3-1 の固定コマンドは `--env-file <書く役の env>` の 1 つだけだった。docker compose は `--env-file` を渡すと既定の `.env` を読まない。
- そのため `BACKEND_IMAGE` が空になり、compose の既定の名前 `astro-webapp-backend`（2026-11-16 に作られた古い完成品）で動き、`No module named app.ops.dev001_write` で止まった（2026-11-28 02:58 JST）。入れ忘れが原因。
- 今の固定コマンド:
  `docker compose -f /home/ubuntu/salesanchor/docker-compose.ai-dev001-writer.yml --env-file /home/ubuntu/salesanchor/.env --env-file /home/ubuntu/.config/salesanchor/ai-dev001-writer.env run --rm -T --no-deps ai-dev001-writer`（`restrict`・`expiry-time="20270115"`）
- `config --format json` で確かめた: 容器に渡る環境変数は `AI_DEV001_WRITER_DATABASE_URL` の 1 つだけ・env_file 無し・完成品は本番と同じ ghcr の digest。`.env` は完成品の名前を決めるのにだけ使われる。
- 同じ理由で、読む鍵（ai-reader）も古い完成品で動いている（未対応・別のテーマ）。

## 便4 測定

### K1（tenant_001 に足す・直す・消す。Mac で止まり 0 回）— ○

| 文 | AUDIT ts（UTC） | sha | rows | result |
|---|---|---|---|---|
| `INSERT INTO leads (customer_name) VALUES ('dev001-k1-20261128') RETURNING id` → id 954 | 18:26:48 | 34083cbcf6a2 | 1 | ok |
| `UPDATE leads SET customer_name = 'dev001-k1-20261128-b' WHERE id = 954 RETURNING id, customer_name` | 18:29:21 | bcb8f1044ee4 | 1 | ok |
| `DELETE FROM leads WHERE id = 954 AND customer_name = 'dev001-k1-20261128-b' RETURNING id` | 18:29:46 | c4d703a4091d | 1 | ok |

- Mac の `~/.claude/logs/agent-events.jsonl` の 18:20〜18:49 UTC に、書く鍵の呼び出し・`psql-write-guard`・`agent-danger-hook` の `hook_blocked` は 0 行（この時間の `hook_blocked` 4 行は別のセッションの git push・PR 本文の止まり）。同意の画面も出なかった。この数えは手元で流した Python の画面の出力（ファイルには残していない）。

### K2（tenant_004 は 3 種類とも断られる）— ○

害の無い形（`WHERE false`）で流した。権限は実行の前に確かめられるので、行が無くても権限エラーになる。

| 文 | ts | result |
|---|---|---|
| `INSERT INTO tenant_004.leads (customer_name) SELECT 'x' WHERE false` | 18:31:09 | db_error:InsufficientPrivilege（42501） |
| `UPDATE tenant_004.leads SET customer_name = 'x' WHERE false` | 18:31:41 | 同上 |
| `DELETE FROM tenant_004.leads WHERE false` | 18:31:57 | 同上 |

### K3 — ○

(a) 6 文とも 42501:

| 文 | ts |
|---|---|
| `INSERT INTO public.tenants (id, tenant_code) SELECT 9999, 'x' WHERE false` | 18:32:31 |
| `UPDATE public.tenants SET tenant_name = 'x' WHERE false` | 18:33:22 |
| `DELETE FROM public.tenants WHERE false` | 18:33:42 |
| `INSERT INTO tenant_001.tenant_meta_config (tenant_id) SELECT 1 WHERE false` | 18:34:11 |
| `UPDATE tenant_001.tenant_meta_config SET tenant_id = 1 WHERE false` | 18:34:26 |
| `DELETE FROM tenant_001.tenant_meta_config WHERE false` | 18:35:00 |

(b) 2 文とも 42501: `UPDATE staff SET avatar_token = 'x' WHERE false`（18:37:22）・`DELETE FROM staff WHERE false RETURNING *`（18:38:03）。

(c)(d) `public_create=False`・`db_create=False`・`t001_create=False`・`secdef_exec=0`（18:47:45）。
- 設計 §6 は reader 鍵で流すとしていたが、reader の台本は文の中の `CREATE`・`trigger` 等の語で断る（`rejected: write keyword is not allowed`）。同じ式を書く鍵の SELECT で流した。`has_*_privilege` は相手のロール名を引数で受けるので、どちらの鍵で流しても同じ値になる。
- 値は流したときの画面の出力（ファイルには残していない）。流れたことは Loki の AUDIT（ts=18:47:45・result=ok）で確かめられる。2026-11-28 の審査のあとファイルに残す形で取り直そうとしたが、出力の書き出しを足したため決まった形から外れ、Mac の見張りが危険語の照合で止めた。言い換えて流し直すことはしていない。

### K4（public を参照する外部キーの表に足せる・public の書く権限 0）— ○

- 1 回目（18:38:44）は `new row violates row-level security policy for table "companies"`（Loki の postgres の記録）。`companies` は `tenant_id` に既定値が無く、行の絞り込み `tenant_id = current_tenant_id()` に合わなかった。権限の不足ではなく文の書き漏れ。PostgreSQL は行の絞り込みの違反にも権限不足と同じ番号 42501 を返すので、AUDIT の result は `db_error:InsufficientPrivilege` になっている。原因は Loki の postgres の記録の文面で見分けた。
- 2 回目（18:44:01）: `tenant_id` を入れた `WITH l AS (INSERT INTO leads ...) INSERT INTO companies (tenant_id, company_code, lead_id, name, status) SELECT 1, ...` が成功（companies id 13・leads id 956）。
- 後片付け（18:44:09）: companies 13 と leads 956 を消した。残り `leads LIKE 'dev001-%'`=0・`companies LIKE 'DEV001-%'`=0（18:44:24）。
- public の表（r・p）で INSERT・UPDATE・DELETE・TRUNCATE のどれかが true の数: 0（18:44:24）。
- 設計 §6 の K4 は reader 鍵で数えるとしていたが、reader の台本は文の中の書き込みの語で断るため、残りの数えと合わせて書く鍵の SELECT で流した（AUDIT の名乗りは `ai-dev001-writer-audit`・result=ok）。`has_table_privilege` は相手のロール名を引数で受けるので、どちらの鍵でも同じ値になる。値は流したときの画面の出力（K3(c)(d) と同じ扱い）。

### K5（aclexplode）— ○

| 項目 | 測った値 | 期待 |
|---|---|---|
| (i) nspacl | tenant_001 の 1 行 | 1 |
| (ii) relacl r・p | 426 行・111 表 | 426・111 |
| (ii) tenant_meta_config | 0 | 0 |
| (iii) attacl | 207 | 207 |
| (iii) 秘密の列（migration の deny の正規表現に合う列） | 0 | 0 |
| (iii) tenant_meta_config | 0 | 0 |
| (iv) 連番 | 74（tenant_001 の連番の数 74） | 同じ数 |
| (v) tenant_001 以外 | 0（どの項目も tenant_001 の行しか出ない） | 0 |
| grantor の人数 | 1 | 1 |

reader 鍵・18:47:35・rows=10・result=ok。

### K6（Loki に 14 本）— ○

- `{job=~".+"} |= "dev001-writer-audit"`・18:26〜18:50 UTC で 19 本（取り出した結果は 21 行。差の 2 行は Grafana の受付の記録にこの検索の URL そのものが引っかかった行で、AUDIT ではない）。K1 の 1 文目（18:26:48）から K3(b) の 2 文目（18:38:03）までの幅で 14 本: result=ok 3 本・`db_error:InsufficientPrivilege` 11 本。
- 幅の外の 5 本は K4 の 1 回目・2 回目・後片付け・数え・K3(c)(d)。

### K7（読むだけの道）— ○

- reader 鍵で K5 の文が結果を返した（result=ok）。

### K8 — 未測定

- 2026-11-28 から 14 日間（〜2026-12-12）の Mac の記録で、tenant_001 向けの psql-write の止まりを数える。

## 追い: 読む鍵（salesanchor-reader）の完成品の直し（2026-11-28）

- 見つけたこと（09:5x JST・無制限鍵で読むだけ）: `authorized_keys` 6 行目の読む鍵の固定コマンドも `--env-file <ai-reader.env>` の 1 つだけで、`docker compose ... config --images` は `astro-webapp-backend`（2026-11-16 の古い完成品）を返した。本番の `.env` を先に足すと `ghcr.io/gen-ryu-system/salesanchor-backend@sha256:b265cb4f...`（画面やクラウドの読む道 ai-reader-http・ai-reader-cloud-http と同じ）になる。容器に渡る環境変数は `AI_READER_DATABASE_URL` の 1 つ・env_file 無し・read_only・backnet のままで、足す前後で同じ（`config --format json` で比べた）。
- 直し: PO が Mac で台本 `e-reader-image-fix.sh` を `!` 実行（2026-11-28 09:56 JST）。読む鍵の行だけに `--env-file /home/ubuntu/salesanchor/.env` を先に足した。点検 6 つ（7 行のまま・ほかの 6 行は控えと同じ・本番の .env が入った・鍵は同じ・期限 20270115 のまま・権限と持ち主は同じ）すべて ○。控え: `authorized_keys.bak-reader-image-fix-20261128095605`。
- 確かめ: 直したあと読む鍵で `SELECT current_user, now()` が `ai_reader` を返した（AUDIT ts=2026-11-28T00:56:19Z・sha=a72c8718b628・result=ok）。同じ時刻の `docker events`（create）で、その容器 `astro-webapp-ai-reader-run-6394989391d9` の完成品は `ghcr.io/gen-ryu-system/salesanchor-backend@sha256:b265cb4f...` だった。
- 今の固定コマンド: `docker compose -f /home/ubuntu/salesanchor/docker-compose.ai-reader.yml --env-file /home/ubuntu/salesanchor/.env --env-file /home/ubuntu/.config/salesanchor/ai-reader.env run --rm -T --no-deps ai-reader`（`restrict`・`expiry-time="20270115"`）。
- 同じ直しで、`docker-compose.ai-reader.yml` と `docker-compose.ai-dev001-writer.yml` の頭の説明に書かれた古い固定コマンドを今の形に直した（説明の行だけ。動きは変わらない）。
