# design: 試験用テナント（tenant_001）だけに書き込める AI の道

> 状態: 設計案 第2版（2026-11-27、Claude Opus）。成功条件は PO 承認済み（2026-11-27「1」）。第1回審査 REVISE（review-architect-1.md）の R1〜R5・L1〜L7 を反映。第2回審査待ち。実装未着手。
> 前提の決定（PO の言葉）:
> - 2026-11-27「テナント001は開発で使用するテストアカウントなのでdevのテナントである。そのためdev環境では自由に動作させて良いようにしたい」
> - 2026-11-27「1」（テナント001専用の鍵を作る形で進める）
> - 2026-11-27「1」（つながっている Discord 2 つ・Google カレンダー・Google Drive・PayPal は 4 つとも試験用）
> - 2026-11-27「1」（成功条件の見分け方で進める）
> 現在地: recon.md（同じフォルダ）。型の元: ADR-1024（読むだけの道）。

## 1. 目的（PO にとって何が変わるか）
- いま: 本番の tenant_001 に試験の行を入れる・直すたびに、PO の `!` 実行か使い捨て許可が要る。
- これから: AI が tenant_001 の中の行だけを、同意なしで足す・直す・消すことができる。
- 本物のお客さま（tenant_004）と全社の表（public）は、この道からは 1 行も書けない。

## 2. 対象と対象外
| 対象 | 対象外（この道では書けない） |
|---|---|
| tenant_001 の表の行の SELECT・INSERT・UPDATE・DELETE（§3-2 の規則で決めた表と列） | 表の作成・変更・削除（DDL）、TRUNCATE |
| tenant_001 の連番の USAGE（番号を進めるだけ） | public・tenant_003〜006 の全部 |
| | `tenant_001.tenant_meta_config`（public を書き換える引き金があるため。recon §3） |
| | 秘密の列（§3-2 の規則に当たる列）の読み書き（ADR-025 常時厳禁） |

## 3. 仕組み
### 3-1. 部品（読むだけの道は変えない）
| 部品 | 読むだけの道（今） | 新しい道 |
|---|---|---|
| DB ロール | `ai_reader`（`migrations/20261017_130000_create_ai_reader_role.sql:10-17`） | `ai_dev001_writer`: LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 2。既にあって属性が違えば止める（同ファイル :10-17 と同じ形）。`log_statement=all`・`statement_timeout=60s`・`lock_timeout=1s`（ADR-1037 と同じ値） |
| 権限 | `ai_ro` のビューに SELECT | §3-2 の規則で表ごと・列ごとに付ける（一括付与しない） |
| 行の制限 | ビューで絞る | 台本が毎回 `SET LOCAL app.tenant_id = '1'` と `SET LOCAL search_path = tenant_001` を入れる。`public.current_tenant_id()` は `current_setting('app.tenant_id', true)::INTEGER` を返すだけ（`migrations/014_create_current_tenant_id_function.sql:15-21`）なので、これで RLS の 64 枚が開く |
| 台本 | `backend/app/ops/readonly_query.py`（1 文だけ・`-- limit=N`・AUDIT を /dev/log へ） | `backend/app/ops/dev001_write.py`。1 文だけ。`tenant_001.` 以外のスキーマ名、`SET`・`RESET`・`set_config(`・DDL の語を拒む（事故よけ。`readonly_query.py:49`・`:55` と同じ語を含める）。順番は「文を流す → AUDIT を送る → 送れたら commit、送れなければ rollback」 |
| 実行場所 | `docker-compose.ai-reader.yml` | `docker-compose.ai-dev001-writer.yml`（同じ守り: read_only・cap_drop ALL・no-new-privileges・mem 256m・環境変数 1 つ・/dev/log だけ） |
| 鍵 | `~/.ssh/salesanchor-reader`（restrict・command=・expiry-time） | `~/.ssh/salesanchor-dev001-writer`（同じ制限、期限は 2027-01-15 で reader とそろえる） |
| 危険パス | `scripts/check-process-artifacts.js:1033-1035` | 同じ一覧に `^docker-compose\.ai-dev001-writer\.yml$` を足す（台本は `:1033` の `^backend\/app\/ops\//` で入る）。ADR-1024 Decision 7 と同じ理由 |
| Mac の見張り | 免除なしで通る | 本文に INSERT・DELETE が入るため止まる見込み → この鍵のパスで始まる ssh だけを通す免除を、PO 本人が `~/.claude/scripts/agent-danger-hook.sh` に入れる（AI は入れない） |

### 3-2. 権限を付ける規則（R1・R3・R5）
- 規則 A（表）: tenant_001 の表（本番 112 枚。recon §2）のうち `tenant_meta_config` を除く全部に、表ごとの GRANT を書く。
- 規則 B（秘密の列）: 列の名前が ADR-1024 の拒否の型（`migrations/20261017_130100_create_ai_ro_views.sql:23`: `^password|_encrypted$|_secret|_token|hash|^secret|^api_key|private_key|credential|account_number|^iban$`）に当たる列には、権限を付けない。その列を持つ表は、表全体ではなく列ごとに SELECT・INSERT・UPDATE を付け、DELETE は表に付ける。
  - 本番の tenant_001 で当たる列（reader 鍵・pg_attribute で数えた。2026-11-27 12:21 JST、q17）: `bots.api_key_hash`・`discord_channel_webhooks.webhook_token_encrypted`・`staff.avatar_token`・`tcg_distribution_targets.sa_key_secret_name`・`tenant_invoice_payment_bank.bank_account_number`・`tenant_invoice_payment_wise.iban`（6 表 6 列）。ほかに `tenant_meta_config` の 3 列（表ごと除外）。
  - よって 列ごとに付ける表 6 枚、表ごとに付ける表 105 枚、付けない表 1 枚（合計 112）。
- 規則 C（連番）: `USAGE ON ALL SEQUENCES IN SCHEMA tenant_001`。一括でよい理由: USAGE は番号を進めるだけで、行は書けず `setval` もできない（UPDATE が要る）。
- 規則 D（無い物は飛ばす）: tenant_001 や表・列が無い DB（CI・試験用）では、その分を飛ばす（`migrations/20261127_100000_add_calendar_team_share.sql:18-27` の形）。migration は 1 つの DO にまとめ、規則 A〜C を pg_catalog から組み立てる。表の名前を手で並べない（新しい表が増えても、次の migration を流すまで自動では付かない）。
- 規則 E（public は 0 から）: public には何も付けない。便2の pytest（クラウドの使い捨て PostgreSQL）で、public を参照する外部キーを持つ表に 1 行足せるかを先に測る。足りなければ設計に付ける表と権限を書き足してから migration を書く（PO 承認の範囲外になる場合は止めて聞く）。

### 3-3. PUBLIC から受け継ぐ権限（R3。本番を reader 鍵で読んだ。2026-11-27 12:21 JST）
| 物 | 本番の値 | 新しいロールへの効き |
|---|---|---|
| public スキーマ | `=U/pg_database_owner`（PUBLIC は USAGE だけ。CREATE なし。q14） | public に表を作れない |
| DB `jarvis_db` | `=Tc/jarvis`（PUBLIC は TEMP と CONNECT。CREATE なし。q15） | スキーマを作れない。一時表は作れる（接続が切れると消え、ほかの表に触れない） |
| SECURITY DEFINER の関数 | 6 個（q16）: `ops_case.unmask_fetch`（PUBLIC から外し済み）と各テナントの `sync_meta_page_routing`（引き金の関数。直接は呼べない） | 呼べる SECURITY DEFINER の関数は 0 個 |

- 先例: tenant_006 に手で足した `qa_tenant006_rw`（全 79 表に `arwdD`、migration に無い。`docs/handoff/migration-runner-redesign/recon-5-0-opus-prod.md:73-76`）。今回は手で足さず、migration で作る（記録から作り直せるようにするため）。

### 3-4. 境界（何が本当に守るか）
- 守るのは DB の権限だけ。ロールが tenant_001 以外に書き込み権限を持たないこと（K2・K3・K5）。
- 台本の語の拒否と Mac の免除は事故よけで、境界ではない。RLS も境界ではない（tenant_004 には権限が無いので、値を変えても書けない）。
- 鍵の強制コマンドで、その ssh はこの台本しか動かせない（ADR-1024 と同じ）。

## 4. 代替案と選んだ理由
| 案 | 良い点 | 弱い点 | 判断 |
|---|---|---|---|
| A. 専用ロール＋専用鍵（本案） | 書ける範囲を DB が決める。お客さまの行に届かない | 部品が 5 つ増える | 採用（PO「1」） |
| B. 書き込みのたびに使い捨て許可 | 作るものがない | 今の止まりがそのまま | 不採用（目的に合わない） |
| C. アプリの管理 API を AI 用に開ける | 画面と同じ道を通る | 管理の権限がテナントをまたぐ。作りが大きい | 不採用 |
| D. `qa_tenant006_rw` と同じく手で GRANT | すぐできる | 記録に残らず作り直せない | 不採用 |

## 5. リスクと対処
| リスク | 対処 |
|---|---|
| `tenant_meta_config` から public の転送表が書き換わる | その表に権限を付けない（K3） |
| SECURITY DEFINER の関数がほかに足される | K3 で「呼べる SECURITY DEFINER の関数 0 個」を測る。週次の点検に入れる（§8） |
| 外部キーの確かめで public の表の中身が読める | 外部キーの確かめは行の制限を受けない（PostgreSQL 公式 ddl-rowsecurity）。規則 E で public の権限を 0 から始め、要る物だけを足す |
| 外へ送られる（Discord・Google・PayPal） | 4 つとも試験用（PO 2026-11-27）。送られても困らない |
| 鍵が漏れる | 強制コマンド・期限・接続 2 本まで・全文記録 |
| 本番の容量・ロック | 1 文・60 秒で切る。ロック待ち 1 秒 |
| 記録が残らない書き込み | AUDIT を送れなければ rollback（§3-1 台本）。サーバー側も `log_statement=all` |

## 6. 成功条件（KGI・KPI。PO が○×で判定）
| # | 基準 | 検証方法 |
|---|---|---|
| K1 | AI が tenant_001 の試験の行を 1 件足し、直し、消せる。3 つとも同意の画面が出ない | 新しい鍵で INSERT・UPDATE・DELETE を各 1 回（3 文）流す。AUDIT 行 3 本と、Mac の記録の「止まり 0 回」を確かめる |
| K2 | tenant_004 の表に書こうとすると 3 種類とも断られる | 新しい鍵で tenant_004 の表に INSERT・UPDATE・DELETE を各 1 回（3 文）。権限エラー 3 件 |
| K3 | public・`tenant_meta_config`・秘密の列に書けない。新しい物も作れない | (a) public の表と `tenant_meta_config` に INSERT・UPDATE・DELETE を各 1 回（6 文）で権限エラー 6 件。(b) `staff.avatar_token` の UPDATE 1 文で権限エラー。(c) reader 鍵で `has_schema_privilege('ai_dev001_writer','public','CREATE')`・`has_database_privilege('ai_dev001_writer',current_database(),'CREATE')` が両方 false。(d) reader 鍵で、`pg_proc.prosecdef` の関数のうち引き金の関数を除き `has_function_privilege('ai_dev001_writer',oid,'EXECUTE')` が true の物 0 個 |
| K4 | public を参照する外部キーを持つ表に 1 行足せる。public の権限は規則 E で決めた一覧どおり | INSERT 1 文が成功。reader 鍵で public の全表について `has_table_privilege('ai_dev001_writer',表,種類)` が true の物を数え、設計の一覧（今は 0 件）と一致 |
| K5 | 新しいロールの権限が §3-2 の数と一致する（多くも少なくもない） | reader 鍵で `pg_class.relacl`・`pg_attribute.attacl` を `aclexplode` で開き、相手が ai_dev001_writer の行を数える。表ごとの付与 105 枚（各 4 種）・列ごとの付与 6 枚・付けない表 1 枚・tenant_001 以外の表 0 枚。`information_schema.role_table_grants` は他のロールの権限を出さないため使わない |
| K6 | 書き込みが全部記録に残る | K1〜K3(a)(b) の 13 文について、AUDIT 行が Loki に 13 本ある |
| K7 | 読むだけの道は前と同じに動く | reader 鍵で 1 文流し結果が出る |
| K8 | 2 週間で、tenant_001 への書き込みで PO が待たされた回数が 0 回 | 便3が終わった日から 14 日間の Mac の記録で、psql-write の止まりのうち tenant_001 向けを数える |

## 7. 計画（便）
1. 便1（設計の文書だけ。この PR）: recon・design・審査の記録。
2. 便2（実装・危険パス。GO 記録が要る）: クラウドの Sonnet が作る。
   - 先に pytest で規則 E を測る（public 0 で外部キーのある表に 1 行足せるか）。結果を設計に書き足す。
   - migration 1 本（ロール＋規則 A〜D）。`scripts/run_all_migrations.sh` の `mr_report_summary`（:1504）の上に `run_sql` を 1 行足す。deploy.yml は変えない。一度流すと書き換えできない（`scripts/check_migration_freeze.py`）ので、直すときは新しい migration を足す。
   - 台本 `backend/app/ops/dev001_write.py` と試験、compose ファイル、`scripts/check-process-artifacts.js` の危険パスに 1 行。
3. 便3（PO の手作業）: ロールの合言葉の設定、鍵を作って本番の authorized_keys に入れる、Mac の見張りの免除。台本は AI が用意し PO が `!` で流す。
4. 便4: K1〜K7 を測る。K8 は便3の終わりから 14 日後。

## 8. 維持する担当と仕組み
- 新しい表が tenant_001 に増えたとき: 自動では書けない。要るときに新しい migration を足す（規則 D で組み立て直す形）。
- 鍵の期限 2027-01-15: reader 鍵の更新と同じ日に見直す。
- 権限のずれ: K3(c)(d)・K5 の数えを週次の点検に入れる（便4で入れ先を決める）。

## 9. 外部事例
- PostgreSQL 公式「Row Security Policies」（Context7 /websites/postgresql、2026-11-27 取得）: 外部キー・一意の確かめは行の制限を受けない。→ §5 の対処の根拠。
- 自社の先例: `qa_tenant006_rw`（手で足した試験用テナントの読み書きロール。recon-5-0-opus-prod.md:73-76）。手で足したため記録から作り直せないと分かっている → 案 D を不採用にした根拠。
- 他社の数値つき事例は使わない。理由: 判断の根拠は自社の権限の実測（K2〜K5）で足り、外の数字では成功を示せない。

## 10. 戻し方
1. すぐ止める（PO の `!`）: `ALTER ROLE ai_dev001_writer NOLOGIN` を流し、今の接続を `pg_terminate_backend` で切る。台本は AI が用意する。
2. 鍵を止める（PO）: 本番の authorized_keys から鍵の 1 行を消す。
3. Mac の見張りの免除を元に戻す（PO。ADR-1024 戻し方 4 と同じ）。
4. 完全に戻す: 権限を外しロールを無効にする migration を足す。読むだけの道には触れない。

## 11. 審査
- 第1回（クラウド architect、2026-11-27）: REVISE。R1〜R5・L1〜L7 → 本版で反映。記録: review-architect-1.md。
- 第2回: 待ち。
