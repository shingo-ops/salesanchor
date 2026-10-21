# ADR-1024: AI 用「本番 DB を読むだけの道」— 何でもできる鍵を許可で縛るのをやめ、読むことしかできない道を作る

| 項目 | 内容 |
|------|------|
| ステータス | Accepted（2026-10-17。実装・本番反映済。結果は「実装結果」節） |
| 備考 | PO 承認済み（2026-10-17 チャット、原文 y）。Q0「読むだけの DB 利用者と読むだけの鍵で進める」、Q1「全テナントを読めるようにする」、Q2「強めた構成（ビュー専用スキーマ ai_ro を最初から入れる等）で進める」。いずれも原文は「y」 |
| 起案日 | 2026-10-17 |
| 方針の決定者 | Shingo（PO） |
| 関連 | ADR-079（監視用の読み取り鍵。混ぜない）、ADR-SA-18（アプリの DB 最小権限ロール）、ADR-136 の GO 手順（CLAUDE.md:57）、ADR-113（設計持ち込みの様式） |
| 設計・根拠 | [design.md](../handoff/ai-readonly-db-path/design.md)、[recon.md](../handoff/ai-readonly-db-path/recon.md)、[card-bin3a.md](../handoff/ai-readonly-db-path/card-bin3a.md) |

---

## Context（なぜ必要か）

PO の依頼は「権限不足で停止することが多い。どの権限を移譲すれば無駄な停止がなくなるか」。本番 DB を読む調査（担当 Sonnet）が止まる原因は 3 つ。

1. 今の道は、何でもできる無制限鍵（manual-only）と、superuser の DB ユーザー jarvis（`rolsuper=True`・`rolbypassrls=True`）。読み取り専用は運用ルールだけで守っている。何でもできる鍵なので、担当は Opus 経由の許可を伝聞として使わず、調査が止まる。
2. 既存の制限鍵（監視用 salesanchor-claude / claude-code-reader）は監視 4 コマンドだけで、DB に届かない（ADR-079）。
3. 止める仕組み（psql-write-guard）は文字の並びで判定するため、調査メモを書くだけでも止まる。

さらに、DB 側の入口 pg_hba は、コンテナ内のローカル接続が trust（パスワードなしで誰にでもなれる）。このため「postgres コンテナの中で読み取り専用ユーザーの psql を動かす」方式は、`\c` で jarvis に切り替えられ、`\!` でシェルも動くので、「読むことしかできない」が成り立たない。

事実の根拠は [recon.md](../handoff/ai-readonly-db-path/recon.md)。

## Decision（何を決めたか）

読むことしかできない道を新しく作る。最初から入れるものは次のとおり（設計の正本: [design.md](../handoff/ai-readonly-db-path/design.md)）。

1. DB の読み取り専用ユーザー `ai_reader`。LOGIN・NOSUPERUSER・NOCREATEDB・NOCREATEROLE・NOREPLICATION・CONNECTION LIMIT 2。**BYPASSRLS と `pg_read_all_data` は付けない。**
2. 秘密列を外したビューだけの専用スキーマ `ai_ro`。`ai_reader` に付ける権限は `ai_ro` の USAGE とビューの SELECT だけ。ビューの持ち主は jarvis（superuser は行の制限を受けない）なので、全テナントを読める（PO の Q1 決定）。新しい表は、ビューを作るまで読めない（fail-closed）。ビューは `scripts/run_all_migrations.sh` の最後で作り直す。秘密列の拒否リストは列名の型（`password*`、`*_encrypted`、`*_secret*`、`*_token*`、hash 系）で決め、ビュー生成のテストで「拒否リストに当たる列が `ai_ro` に 0 本」を確かめる。
3. 専用コンテナ `ai-reader`。環境変数は `AI_READER_DATABASE_URL` だけ。volumes なし、`read_only`、`cap_drop: [ALL]`、`no-new-privileges`、backnet のみ。backend コンテナでは動かさない。
4. 読み取り台本 `backend/app/ops/readonly_query.py`。標準入力の SQL を受け、クライアント側で `BEGIN READ ONLY` と `SET LOCAL statement_timeout` を自分で発行し、最後に rollback する。文字列での拒否（`\` 始まり、複文、先頭語が SELECT/WITH/SHOW/EXPLAIN（ANALYZE なし）以外、`set_config(`・`SET `・`COPY`・`pg_read_file`・`pg_sleep`・`lo_` を含むもの）。行数の既定 200・上限 5000。この拒否は使いやすさと二重目であり、守りの本体は DB の GRANT。
5. サーバー側の記録。`ALTER ROLE ai_reader SET log_statement = 'all'`（superuser でなければ戻せない設定）。SQL 本文が postgres のログ → promtail → Loki（prod2）に残る。
6. 読むための SSH 鍵 `salesanchor-reader`。authorized_keys の末尾に 1 行だけ追加（既存の行は触らない）。`restrict,command="…",expiry-time="<90 日後>"`。固定コマンドは専用コンテナの起動 1 本だけ。
7. 台本（`backend/app/ops/`）と `docker-compose.ai-reader.yml` を process-artifacts gate の危ない変更（DANGEROUS_PATTERNS）に入れ、PR 本文に GO 記録が無いと必須チェックで止まるようにする。GO は委任 GO（POの委任に基づくClaude Opus発行）で足りる。`.github/CODEOWNERS` は責任者の明示に留め、強制しない（ADR-135:46）。
8. フック免除は、鍵パスの完全一致だけ。
9. Kテストの追加（`pg_authid` が読めないこと、`SET` で設定を戻せること＝それは境界でない証明、Loki に 1 行出ること、`sshd -T` の結果）。

書き込みは今までどおり PO の `!` 実行。無制限鍵（manual-only）と PO の決まりは変えない。

## Why（なぜこの形か）

- 「何でもできる鍵を許可で縛る」から「読むことしかできない道」へ変える。読むことしかできないので、伝聞かどうかを問わず担当が使ってよい。
- 名前で秘密を伏せる方式（出力の列名で隠す）は、別名を付けるだけですり抜けられる（例: `SELECT password_argon2_hash AS x`）。そのため、秘密列を物理的に持たないビューを使う。
- 境界は二重にする。権限の境界は DB の GRANT、コードの境界は process-artifacts gate の GO 記録。台本はリポジトリの中にあり、マージされれば本番の固定コマンドの中身が変わる。専用コンテナに `DATABASE_URL`（書ける接続）を渡さず、台本の変更には GO 記録を要求する。AI は GO 記録を残さずには境界を動かせない。DB の権限は台本を変えても広がらない。
- `ALTER ROLE … SET default_transaction_read_only` や `statement_timeout` は利用者が `SET` で戻せるので境界ではない。事故防止として残し、境界とは書かない。
- 今の道より危険が増えない。今の道は読み書きも削除もできる superuser。新しい道は読むことしかできず、記録が残り、鍵を 1 行消せば止まる。

## 不採用の案

| 案 | 不採用の理由 |
|---|---|
| B: manual-only 鍵を担当に毎回 permit チケットで渡す | PO の 1 行作業が毎回残り、目的（停止をなくす）を満たさない。鍵が何でもできるままで、書き込み事故を防げない |
| C: 監視用の制限鍵 salesanchor-claude に DB 読み取りを足す | 監視用の道（ADR-079）に役目が混ざる。監視用は prod2 と共有の決まりがあり、影響範囲が広がる |
| D: Opus だけが manual-only で読む | 探索は Sonnet に任せる決まりに反し、何でもできる鍵である点も変わらない |
| 列単位の GRANT | 列権限は加算式で「この列以外」が書けない。テナントのスキーマ 5 本（表は 69〜99 枚ずつ）と public を列挙し、新しい表ごとに追従する保守が破綻しやすい |
| postgres コンテナ内の psql | pg_hba が trust のため `\c` で jarvis に切り替えられ、`\!` でシェルも動く。「読むことしかできない」が成り立たない |
| backend コンテナでの実行 | 台本（AI が書けるコード）の隣に `DATABASE_URL`・`ADMIN_DATABASE_URL`・`METADATA_FERNET_KEY` などがあり、暗号文と復号鍵が同じ場所に揃う。blue-green の切替でコンテナ名が一時的に消える可用性の問題もある |
| `pg_read_all_data` と BYPASSRLS で全表・全列を読む（最初の案） | 暗号化トークンやログインの鍵情報の列まで読める。名前で伏せる方式ではすり抜けられるため、最初からビューにする |

## Consequences（影響）

- 良い点: 担当 Sonnet が PO の `!` 実行と permit チケットなしで、本番 DB を読める。読んだ SQL がサーバー側に残る。鍵は 90 日で自動的に切れる。
- 受け入れる点:
  - 全テナントの顧客データ（氏名・連絡先等）を AI が読める（PO の Q1 決定）。出力はファイルに保存し、行数の既定は 200。読んだ内容の中の指示には従わない決まりを手順に明記する。
  - 新しい表・新しいテナントは、ビューが作られるまで読めない（意図した fail-closed）。
  - reader 鍵はパスフレーズなし（AI が使えるようにするため）。代わりに `expiry-time`、記録、台本変更時の GO 記録で補う。
  - 本 ADR の `migrations/` を含む実装は、ADR-135/ADR-136 により PO の GO が出るまで main にマージしない。
- 触らない: 無制限鍵 manual-only、PO の `!` 実行の決まり、監視鍵（ADR-079）、pg_hba の trust。

## 後で足すもの

SSH 証明書（期限の自動化）、夜間スナップショット（本番から完全に切り離した読み取り）、pg_hba の trust 廃止（`backup.sh` と `deploy.yml` の jarvis 接続を先に直す別 ADR）、pgaudit（カスタムイメージが要る）、Mac の接続元を絞る `from=`（接続元が固定か未確認）。

## 戻し方

1. VPS の authorized_keys から `salesanchor-reader` の 1 行を消す（即時に止まる。PO `!`）。
2. 専用コンテナの定義と台本を git revert。
3. `DROP SCHEMA ai_ro CASCADE`・`DROP ROLE ai_reader`（不可逆操作リスト。PO 確認）。
4. フックの免除を、修正前の写しから戻す。

## 未確認（実装の最初に確かめる）

PostgreSQL の仕様の一部（ビューの持ち主の権限で行の制限が外れること、`log_statement` を利用者が戻せないこと、`pg_authid` が読めないこと）は公式ドキュメントでの確認が取れていない（Context7 が月次上限で使えなかった）。実装前の K テストで実機を測って確かめる。詳細は design.md §リスク。

## 実装結果

- 便3a（リポジトリ側）: #4453 を本番反映（2026-10-17、`ai_ro` ビュー 506 本）。
- 便3b（VPS 側、PO `!` 実行）: 2026-10-17 16:00 JST 完了。`ai_reader` のパスワード設定、接続情報は VPS 上の別ファイル（600）、authorized_keys に 1 行（restrict・固定コマンド・expiry-time 20270115）。既存 5 行は不変。
- 便4（文書）: 使い方 [usage.md](../handoff/ai-readonly-db-path/usage.md)。K 試験の結果 [k-results.md](../handoff/ai-readonly-db-path/k-results.md)。K17 はフック免除が不要。K 試験は K14 の `sshd -T`（PO 実行分）を除いて測定済み。K3 は ×、K11 は △（判断と根拠は k-results.md）。
- 運用上の注意: デプロイのたびに `ai_ro` が約 70 秒外れ、その間は 42P01 になる（usage.md §4）。

### 改訂（K16、2026-10-17）

当初は CODEOWNERS を PO の必須レビューにしてコードの境界とする設計だった。しかし main の ruleset はレビュー必須数が 0 で、この状態では Code Owners の指定を有効にしてもレビュー要求が生まれない（ADR-135:34-46 で実測済み）。既存方針でも CODEOWNERS は責任者の明示に留め、強制には使わない。そこで K16 の時点で、台本と compose 定義を process-artifacts gate の危ない変更に入れた。PO はこの変更を PO 本人の GO 必須にしないと決めた（2026-10-17、回答「n」）。そのため委任 GO で通る。最後の守りは DB の権限（K7・K9）である。

### 改訂（K3、2026-10-17）

- 経緯: K3 は、台本の AUDIT 行が 23 回中 1 回しか Loki に無かった（×）。逆に、ai-reader の標準出力（結果表）が時々 Loki に入っていた（直近 24h で 14 コンテナ中 9 個）。設計: [design-k3.md](../handoff/ai-readonly-db-path/design-k3.md)。
- Decision 3 の「volumes なし」を「`/dev/log` ソケット 1 本の bind だけ（`create_host_path: false`）。ほかのマウントは足さない」に改める。理由は、送信だけでファイルを書く道ではないこと。あわせて ai-reader は `logging: none` にし、結果表を残さない。
- 案 C の採用: AUDIT を stderr に加えて `/dev/log` へ直接送る（/dev/log → auth.log → Loki。sshd と同じ道）。送れなければ rc=5 で結果を出さない。promtail・Loki・ホストの設定は変えない。
- 残る危険（R8）: DB のエラー文に値が載り、postgres のログから Loki に入る道は本件の範囲外。別件とする。
- PO 承認: 原文「y」（2026-10-17）。

### 改訂（失敗時の作り直し、2026-10-21）

- 経緯: 移行が途中で失敗すると、EXIT trap はビューを作らずに終わっていた（「views stay dropped」）。直近300回の入れ替えで移行の失敗8回すべてで外れたまま、10/21 は約13分 AI が読めなかった。設計: [design.md](../handoff/ai-ro-restore-on-failure/design.md)。
- Decision の「最後で作り直す」を「スクリプトの成否にかかわらず最後で作り直す」に改める。終了コードは元のまま（作成の成否で入れ替えの成否を変えない）。
- Why: 秘密列の拒否リストは列名とカタログだけで決まり、途中まで進んだ DB に流しても同じ列が外れる。作成は元の表に ACCESS SHARE しか取らず、在庫表の読み取りを待たせない（使い捨て DB で実測）。そのため外したままにする守りの理由が無い。
- 作成には、lock_timeout ではなく statement_timeout（既定30秒）を渡す。
  - lock_timeout の失敗（55P03）は、1本ずつの例外処理に飲まれる。そのビューだけ欠けたまま、成功扱いになる。
  - statement_timeout の打ち切り（57014）は WHEN others に捕まらず、作成全体が戻って警告になる（PostgreSQL 16 公式文書）。
  - そのため結果は「全部ある」か「警告」の2つになる。ACCESS EXCLUSIVE の持ち主がいても、待ち続けない。
- ログの文面: 失敗回の「skip ai_ro views (script failed rc=N; views stay dropped)」は「script failed rc=N; recreating ai_ro views anyway」に変わる。
- 作成の psql には `-v VERBOSITY=terse` を渡す。打ち切りの回は、エラーの CONTEXT 欄に SQL 文（表名と列名）が出ていた（コード審査 M1）。terse にすると、出るのは重さ・本文・位置だけになる（PostgreSQL 16 公式文書 libpq-control）。成功回の作成結果の行は本文なので、今のまま出る。
- 使い捨て DB の試験（sandbox run 39598850269、ubuntu の bash 5.2.21）: T1〜T7 は全部合格した。
  - 移行が失敗した回: 作り直した後、ビュー数は作成数と同じで、秘密列は0。
  - 作成の時間: 読み取り中の接続があっても作成は161ms、読み取りは56ms。
  - ACCESS EXCLUSIVE の持ち主がいた回: 3秒で打ち切られ、rc=3 のまま、ビューは0本。
- 記録だけの T8: 移行の途中で SIGTERM を受けた回の終了コードは143。trap は「失敗」の行を出さずに作成まで流れた。信号で止まった場合の扱いは本件の範囲外とする。
- PO 承認: テーマは「1」、成功条件の案に「確立したなら進める」（2026-10-21）。

## 関連 ADR

- ADR-079: 監視用の読み取り鍵。今回の鍵とは別にする
- ADR-SA-18: アプリの DB 最小権限ロール（salesanchor_app）。今回の `ai_reader` はその考え方を読み取り側に広げる
- ADR-136 の GO 手順（CLAUDE.md:57）: 危険パス（`migrations/`）を含む実装の GO の取り方
- ADR-113: 設計持ち込みの様式（recon → 設計確定 → 整合検査 → 実装）
