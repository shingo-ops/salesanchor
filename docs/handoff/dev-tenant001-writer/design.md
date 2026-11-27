# design: 試験用テナント（tenant_001）だけに書き込める AI の道

> 状態: 設計案（2026-11-27、Claude Opus）。成功条件は PO 承認待ち。実装未着手。
> 前提の決定（PO の言葉）:
> - 2026-11-27「テナント001は開発で使用するテストアカウントなのでdevのテナントである。そのためdev環境では自由に動作させて良いようにしたい」
> - 2026-11-27「1」（テナント001専用の鍵を作る形で進める）
> - 2026-11-27「1」（つながっている Discord 2 つ・Google カレンダー・Google Drive・PayPal は 4 つとも試験用）
> 現在地: recon.md（同じフォルダ）。型の元: ADR-1024（読むだけの道）。

## 1. 目的（PO にとって何が変わるか）
- いま: 本番の tenant_001 に試験の行を入れる・直すたびに、PO の `!` 実行か使い捨て許可が要る。
- これから: AI が tenant_001 の中の行だけを、同意なしで足す・直す・消すことができる。
- 本物のお客さま（tenant_004）と全社の表（public）は、この道からは 1 行も書けない。

## 2. 対象と対象外
| 対象 | 対象外（この道では書けない） |
|---|---|
| tenant_001 の表の行の INSERT・UPDATE・DELETE（下の除外を除く） | 表の作成・変更・削除（DDL）、TRUNCATE |
| tenant_001 の連番（sequence）の USAGE | public・tenant_003〜006 の全部 |
| 同じ道での SELECT（tenant_001 のみ） | `tenant_001.tenant_meta_config`（public を書き換える引き金があるため。recon §3） |
| | 秘密の列（`*_encrypted`・`*_token*`）を持つ表への書き込み（ADR-025 常時厳禁） |

## 3. 仕組み（変更前 → 変更後）
読むだけの道（ADR-1024）と同じ形を、別のロール・別の鍵・別の台本で作る。読むだけの道は変えない。

| 部品 | 読むだけの道（今） | 新しい道 |
|---|---|---|
| DB ロール | `ai_reader`（`migrations/20261017_130000_create_ai_reader_role.sql:12`） | `ai_dev001_writer`: LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 2、`log_statement=all`、`statement_timeout=60s` |
| 権限 | `ai_ro` のビューに SELECT | `USAGE ON SCHEMA tenant_001`、表ごとに SELECT/INSERT/UPDATE/DELETE（除外表は付けない）、`USAGE ON ALL SEQUENCES IN SCHEMA tenant_001`。public は外部キーの確かめに要る最小（試験 K4 で測る） |
| 行の制限 | ビューで絞る | 台本が毎回 `SET LOCAL app.tenant_id = '1'` と `SET LOCAL search_path = tenant_001` を入れる（RLS 64 枚がこれで開く。recon §2） |
| 台本 | `backend/app/ops/readonly_query.py`（1 文だけ・`-- limit=N`・AUDIT を /dev/log へ） | `backend/app/ops/dev001_write.py`: 同じ AUDIT の形。1 文だけ。`tenant_001.` 以外のスキーマ名の文字、`SET`・`RESET`・DDL の語を拒む（事故よけ。境界は権限） |
| 実行場所 | `docker-compose.ai-reader.yml` | `docker-compose.ai-dev001-writer.yml`（同じ守り: read_only・cap_drop ALL・no-new-privileges・mem 256m・環境変数 1 つ） |
| 鍵 | `~/.ssh/salesanchor-reader`（restrict・command=・expiry-time） | `~/.ssh/salesanchor-dev001-writer`（同じ制限、期限は 2027-01-15 で reader とそろえる） |
| Mac の見張り | 免除なしで通る | 本文に INSERT・DELETE が入るため止まる見込み → この鍵のパスで始まる ssh だけを通す免除を、PO 本人が `~/.claude/scripts/agent-danger-hook.sh` に入れる（AI は入れない） |

### 境界（何が本当に守るか）
- 守るのは DB の権限だけ。ロールが tenant_001 以外に書き込み権限を持たないこと（K2・K3）。
- 台本の語の拒否と Mac の免除は事故よけで、境界ではない。
- 鍵の強制コマンドで、その ssh はこの台本しか動かせない（ADR-1024 と同じ）。

## 4. 代替案と選んだ理由
| 案 | 良い点 | 弱い点 | 判断 |
|---|---|---|---|
| A. 専用ロール＋専用鍵（本案） | 書ける範囲を DB が決める。お客さまの行に届かない | 部品が 5 つ増える | 採用（PO「1」） |
| B. 書き込みのたびに使い捨て許可 | 作るものがない | 今の止まりがそのまま | 不採用（目的に合わない） |
| C. アプリの管理 API を AI 用に開ける | 画面と同じ道を通る | 管理の権限がテナントをまたぐ。作りが大きい | 不採用 |

## 5. リスクと対処
| リスク | 対処 |
|---|---|
| `tenant_meta_config` から public の転送表が書き換わる | その表に書き込み権限を付けない（K3 で 0 行を確かめる） |
| SECURITY DEFINER の関数がほかに足される | 付ける権限の一覧を migration で表ごとに書く（ALL TABLES で一括付与しない）。新しい表は自動では書けない |
| 外部キーの確かめで public の表の中身が読める | 外部キーの確かめは行の制限を受けない（PostgreSQL 公式 ddl-rowsecurity）。読める列は参照先のキーだけ。K4 で要る権限を測り最小にする |
| 外へ送られる（Discord・Google・PayPal） | 4 つとも試験用（PO 2026-11-27）。送られても困らない |
| 鍵が漏れる | 強制コマンド・期限・接続 2 本まで・全文記録 |
| 本番の容量・ロック | 1 文・60 秒で切る。ロック待ち 1 秒（ADR-1037 と同じ値）を台本で入れる |

## 6. 成功条件（KGI・KPI。PO が○×で判定）
| # | 基準 | 検証方法 |
|---|---|---|
| K1 | AI が tenant_001 の試験の行を 1 件足し、直し、消せる。3 つとも同意の画面が出ない | 新しい鍵で INSERT・UPDATE・DELETE を各 1 回流し、AUDIT 行 3 本と Mac の記録で「止まり 0 回」を確かめる |
| K2 | tenant_004 の表に書こうとすると 3 種類とも断られる（0 行・権限エラー） | 新しい鍵で tenant_004 の表に INSERT・UPDATE・DELETE を 1 回ずつ流し、エラー 3 件 |
| K3 | public の表と `tenant_001.tenant_meta_config` に書こうとすると断られる | 同じく各 1 回、エラー |
| K4 | 外部キーのある表（public を参照する表）に 1 行足せる。そのために足した public の権限が一覧どおり | INSERT 1 回成功＋`has_table_privilege` の一覧を reader 鍵で読む |
| K5 | 新しいロールの権限が設計の一覧と 1 対 1 で一致する（多くも少なくもない） | reader 鍵で `information_schema.role_table_grants` を数え、設計の表と照合 |
| K6 | 書き込みが全部記録に残る | K1〜K3 の 9 文について、AUDIT 行が Loki に 9 本ある |
| K7 | 読むだけの道は前と同じに動く | reader 鍵で 1 文流し結果が出る |
| K8 | 2 週間で、tenant_001 への書き込みで PO が待たされた回数が 0 回 | 11/28〜12/11 の Mac の記録で psql-write の止まりのうち tenant_001 向けを数える |

## 7. 計画（便）
1. 便1（設計の文書だけ。この PR）: recon・design・ADR 案。PO の成功条件の承認。
2. 便2（実装・危険パス。GO 記録が要る）: migration（ロール・権限）、台本と試験、compose ファイル。クラウドの Sonnet が作る。
3. 便3（PO の手作業）: ロールの合言葉の設定、鍵を作って本番の authorized_keys に入れる、Mac の見張りの免除。台本は AI が用意し PO が `!` で流す。
4. 便4: K1〜K7 を測る。K8 は 2 週間後。

## 8. 維持する担当と仕組み
- 新しい表が tenant_001 に増えたとき: 自動では書けない（一覧付与のため）。要るときに migration で足す。
- 鍵の期限 2027-01-15: reader 鍵の更新と同じ日に見直す。
- 権限の一覧のずれ: K5 の数えを週次の点検に入れる（便4で決める）。

## 9. 外部事例
- PostgreSQL 公式「Row Security Policies」（Context7 /websites/postgresql、2026-11-27 取得）: 外部キー・一意の確かめは行の制限を受けない。→ §5 の対処の根拠。
- 他社の数値つき事例は使わない。理由: 判断の根拠は自社の権限の実測（K2〜K5）で足り、外の数字では成功を示せない。

## 10. 戻し方
- すぐ止める: 本番の authorized_keys から鍵の 1 行を消す（PO）。
- 完全に戻す: ロールの権限を外し、ロールを無効にする migration を流す。読むだけの道には触れない。

## 11. 審査（Architect、同じ AI による自己審査）
- 判定: REVISE 待ち（クラウドで別の審査を流してから記入）。
