<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# Phase 3 設計 — アプリ入れ替え中に在庫表が止まらないようにする（便1）

**対象ADR**: ADR-1037（新規）。関連 ADR-1005・ADR-1003・ADR-135・ADR-136  
**recon**: docs/handoff/migration-lock-timeout/recon.md  
**日付**: 2026-10-21  
**担当**: Planner（Opus）。状態: 設計案 → 審査は review-design.md

---

## 1. 目的（PO の言葉）
- 「アプリの入れ替え中に在庫表を開いても、1回の表示が2秒を超えない（作り替えの作業がほかを待たせるのは最大1秒まで）」
- 「待たせ合いで入れ替えが失敗する回数を0にする（今は週4回）」
- 確かめ方: 試験用の DB で再現 → 本番の次の数回の入れ替えの記録（recon §0）。

## 2. 原因（recon §3・§4 の事実）
入れ替えのたびに全 migration を流し直す（ADR-1005 段階2 未着手）。その中の `DROP TABLE IF EXISTS public.parse_logs` が FK 先の products に最強のロックを取りに行き、稼働中の読み取りが終わるまで無期限に待つ。待っている間は後から来た在庫表の読み取りも全部その後ろに並ぶ（再現で 8912ms）。読み取り側とお互いを待つ形になると deadlock で入れ替えが落ちる。

## 3. 変更前 → 変更後（便1）
| | 変更前 | 変更後 |
|---|---|---|
| run_sql のロック待ち | 無期限 | 1秒で諦める（`PGOPTIONS=-c lock_timeout=1s`） |
| 再試行する失敗 | "deadlock detected" のみ | "deadlock detected" と "canceling statement due to lock timeout" |
| 再試行の回数・間隔 | 1ファイル最大3回（初回含む）・5秒 | 1ファイル最大10回（初回含む）・3秒。1回の入れ替え全体で再試行は合計40回まで |
| 上限に達したとき | 停止（今と同じ） | 停止（今と同じ）。上限に達したことをログに書く |
| ほかのエラー | 即停止 | 即停止（変えない） |

最悪の追加時間: 40回 ×（待ち1秒＋間隔3秒）＝160秒。通常の最大138秒と足して約300秒で、ssh-action の打ち切り10分（recon §2）に収まる。`SET LOCAL lock_timeout = '5s'` の8ファイルが毎回上限まで待つ最悪でも 40×(5+3)+138＝458秒で収まる（審査 review-code.md の指摘）。

## 4. 変更内容（file:line と変更前後）
### 4-1. `scripts/run_all_migrations.sh` :62-87 を置き換える
変更前: recon §2 の :62-87（`SQL_DEADLOCK_MAX_ATTEMPTS=3` と run_sql）。
変更後（コメントの密度・書き方は今の :62-63 に合わせる）:
```bash
# 稼働中のアプリとロックを取り合ったら、同じファイルを流し直す（全 migration は冪等で、
# CI のドライラン2周目で再実行が通ることを確かめている）。ほかのエラーは今までどおり即停止。
# ロック待ちは1秒で諦める。待っている間は後から来た在庫表などの読み取りも止まるため（ADR-1037）。
# 再試行はファイルごとに初回含め最大10回・3秒あけ、1回の実行全体で合計40回まで（移行ステップの打ち切り10分に収める）。
SQL_LOCK_TIMEOUT="${SQL_LOCK_TIMEOUT:-1s}"
SQL_RETRY_MAX_ATTEMPTS="${SQL_RETRY_MAX_ATTEMPTS:-10}"
SQL_RETRY_SLEEP_SEC="${SQL_RETRY_SLEEP_SEC:-3}"
SQL_RETRY_BUDGET="${SQL_RETRY_BUDGET:-40}"
SQL_RETRY_USED=0
run_sql() {
  local file="$1"
  STEP=$((STEP + 1))
  echo ">>> [${STEP}/${TOTAL}] psql < ${file}"
  local attempt=1 rc errlog
  errlog="$(mktemp)"
  while true; do
    rc=0
    docker exec -e PGOPTIONS="-c lock_timeout=${SQL_LOCK_TIMEOUT}" -i "${POSTGRES}" ${PSQL} < "${REPO_DIR}/${file}" 2>"${errlog}" || rc=$?
    cat "${errlog}" >&2
    if [ "${rc}" -eq 0 ]; then
      rm -f "${errlog}"
      return 0
    fi
    if grep -qE "deadlock detected|canceling statement due to lock timeout" "${errlog}"; then
      if [ "${attempt}" -lt "${SQL_RETRY_MAX_ATTEMPTS}" ] && [ "${SQL_RETRY_USED}" -lt "${SQL_RETRY_BUDGET}" ]; then
        attempt=$((attempt + 1))
        SQL_RETRY_USED=$((SQL_RETRY_USED + 1))
        echo ">>> [${STEP}/${TOTAL}] lock conflict; retry ${attempt}/${SQL_RETRY_MAX_ATTEMPTS} in ${SQL_RETRY_SLEEP_SEC}s (total ${SQL_RETRY_USED}/${SQL_RETRY_BUDGET}): ${file}"
        sleep "${SQL_RETRY_SLEEP_SEC}"
        continue
      fi
      echo ">>> [${STEP}/${TOTAL}] lock conflict; retry limit reached (file ${attempt}/${SQL_RETRY_MAX_ATTEMPTS}, total ${SQL_RETRY_USED}/${SQL_RETRY_BUDGET}): ${file}"
    fi
    rm -f "${errlog}"
    return "${rc}"
  done
}
```
- 値の正本はこの4行だけ（環境変数で上書きできるのは試験のため。deploy.yml・.env には書かない）。
- 触らない範囲: :25 PSQL、:49-59 run_py、:108-127 EXIT trap（ai_ro 作成。失敗してもデプロイは続く作りで、今回の失敗記録に出ていない）、migration の登録行、migrations/ の中身。

### 4-2. 新しい試験 `tests/sandbox/migration-run-sql-retry.sh`
- 使い捨て postgres:16 だけを使う（`tests/sandbox/lock-timeout-repro.sh` と同じ起動・待ち方）。本番・secrets に触れない。
- **本物の run_sql を使う**: `scripts/run_all_migrations.sh` から `SQL_LOCK_TIMEOUT=` の行〜 run_sql の終わりの `^}` までを sed で抜き出して読み込む（写しを作らない＝正本1か所）。POSTGRES・PSQL（postgres ユーザー）・REPO_DIR・STEP・TOTAL は試験側で決める。
- 各試験は PASS/FAIL を1行で出し、1つでも FAIL なら最後に exit 1。
  - T1 待たせる時間: A が products を6秒読み続ける間に run_sql で本物の DROP の migration（`migrations/20261002_170000_drop_discord_inventory_tables.sql`）を流し、その間0.5秒ごとに C（`SELECT count(*) FROM products`）を測る（A 開始から10秒、または run_sql 終了まで）。C の最大値 ≤ 1500ms で PASS。
  - T2 流し直しで通る: T1 の run_sql が rc 0、ログに "lock conflict; retry" が1回以上、parse_logs が消えている。
  - T3 上限で止まる: A が30秒読み続ける間に `SQL_RETRY_MAX_ATTEMPTS=3 SQL_RETRY_SLEEP_SEC=1` で同じ DROP を流す → rc≠0、ログに "retry limit reached"、所要 < 10秒。
  - T4 deadlock も流し直す: sequence を使い「1回目だけ ERRCODE 40P01・MESSAGE 'deadlock detected' を出し、2回目は成功する」SQL ファイル（試験の中で一時ファイルとして作る）→ rc 0、retry 1回。
  - T5 ほかのエラーは即停止: `SELECT 1/0;` のファイル → rc≠0、retry の行が0回。
  - T6 全体の上限: `SQL_RETRY_BUDGET=2` で T4 型のファイル（3回目まで失敗する版）を流す → retry 2回で停止、rc≠0。
- parse_logs の準備は `migrations/20260604_120000_create_parse_logs.sql` と `migrations/20260604_130000_create_supplier_parse_stats_view.sql` を流す（`tests/sandbox/lock-timeout-repro.sh` の setup_base / recreate_parse_logs と同じ手順）。

### 4-3. 文書
- `docs/adr/ADR-1037-migration-lock-timeout.md`（新規）と `docs/adr/README.md`（`node scripts/generate-adr-index.js` で再生成）。
- `.claude-pipeline/active-work.d/release-migration-lock-timeout.md`（台帳）。

## 5. 外部・過去事例の参照と我々への応用
- 事例1: GitLab の migration 指針（docs.gitlab.com「Migration Style Guide」、2026-10-21 閲覧）。本番は statement_timeout 15秒。ロックを取る migration は with_lock_retries で短い lock_timeout（例 100ms）を付けて最大50回まで間を空けて試し直す。待っているロックの後ろに後続の問い合わせが並ぶことを理由に挙げている。→ 我々への応用: 「短く諦めて、間を空けて試し直す」形をそのまま採る。回数と間隔は我々の打ち切り10分と通常の所要（最大138秒）から決めた（§3）。GitLab の数値は我々の実測ではないので、成功の証明には使わない。
- 事例2: PostgreSQL 16 公式文書（lock_timeout・明示的ロック・libpq の PGOPTIONS）。→ 我々への応用: サーバー全体ではなく、移行の接続だけに付ける（全体設定は非推奨と明記されているため）。
- 過去事例: c072445cf（10/20）で deadlock だけの再試行を入れたが、無期限のロック待ちは残り、10/19 の遅い時間帯Aの形（待っている間に後続が並ぶ）は防げない。

## 6. 受け入れ基準
| 基準 | 検証方法 |
|------|---------|
| K1 移行がロックを待つ間、在庫表の代わりの読み取りが待たされるのは1.5秒以内（1秒＋接続の往復） | sandbox-test `tests/sandbox/migration-run-sql-retry.sh` T1 PASS（GitHub の run のログ） |
| K2 ロックが取れなかったファイルは流し直して通る | 同 T2 PASS |
| K3 取れないまま上限に達したら、今までどおり入れ替えを止める（時間内に） | 同 T3・T6 PASS |
| K4 deadlock も流し直す／ほかのエラーは即停止のまま | 同 T4・T5 PASS |
| K5 今ある migration が全部これまでどおり流れる | CI（migration-test・migration-guard ほか必須チェック）緑。加えて本番の入れ替えで移行ステップ success |
| K6 本番: この PR を含む入れ替えから、移行ステップのある入れ替え3回で、deadlock・lock timeout による失敗が0回 | 各 Deploy to VPS run のログ: 移行ステップの成否、"lock conflict; retry" と "retry limit reached" の回数を記録 |
| K7 本番: 同じ3回の移行ステップの時間帯に、在庫表 GET で2秒を超えたものが0件 | Prometheus `http_request_duration_seconds_bucket{handler="/api/v1/inventory"}` を移行ステップの開始〜終了で集計。2秒の境界が無ければ、使った境界を記録し「その境界以下」として判定（境界の差は報告に明記）。その時間帯に GET が0件なら、その回は「判定不能」と記録して次の回で数える |

## 7. 技術 How・KPI
- KPI: 入れ替え1回あたりの「移行が在庫表を待たせた最大時間」（K1・K7）と「待たせ合いでの失敗回数」（K6）。基準値は recon §3（最大13.5秒平均の時間帯あり・失敗週4回）。
- 技術選択: lock_timeout を接続ごとに付ける（理由: 再現で 1085ms で諦め、流し直しで通ったことを確かめた＝recon §4。サーバー全体設定は公式に非推奨。アプリの接続には影響させない）。

## 8. 選ばなかった案と理由
- 案A: parse_logs を毎回作って消すのをやめる。毎回全件流す作り自体（ADR-1005 段階2）の話で、PO の判断が要る。今回は「どの migration がロックで待っても1秒で離す」形にして、同じ形の別の migration（conditions のビュー作り直しなど）にも効かせる。
- 案B: DB やロール全体に lock_timeout を付ける。アプリの接続も同じロールで、アプリ側の待ちの挙動が変わる。公式でも全体設定は非推奨。
- 案C: Python の移行（run_py）にも付ける。asyncpg が PGOPTIONS を読むかは【未確認】で、20本それぞれの接続を変える必要がある。観測した deadlock 4件は全部 run_sql 側（recon §3・§5）。便2以降の候補に残す。

## 9. 弊害・トレードオフ
- 途中まで流れたファイルを流し直す → 全件2周の CI（`.github/workflows/migration-test.yml:1828-1839`）で再実行が通ることを確かめ済み。BEGIN を持つ13本は失敗時に巻き戻る。
- 長い読み取りが続くと上限に達して入れ替えが止まる → 今の deadlock 停止と同じ扱い（止まる＝古い版のまま動き続ける）。ログに "retry limit reached" が出るので原因が分かる。
- `SET LOCAL lock_timeout = '5s'` の 8 ファイルは、そのトランザクションの中だけ5秒待つ（今回は変えない）。そのうち2本は DROP TABLE/COLUMN を含み、変更すると ADR-1003 で PO 本人の GO が要る。→ 便2として PO に確認する（§11）。
- ロックを取った後に長く走る DDL（表の書き直しなど）は lock_timeout では防げない。今回の記録に該当は無い。
- 再試行で入れ替えが最大160秒長くなる → 打ち切り10分に収まる（§3）。

## 10. 戻し方
- この PR を revert して main にマージ → 次の入れ替えから今の形（無期限待ち・deadlock のみ3回）に戻る。DB の中身は変えないので、DB 側の戻しは無い。

## 11. 計画票
| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | 設計審査（review-design.md） | Opus（Architect） |
| 2 | 4-1・4-2 の実装、sandbox-test 実行、CI | Sonnet |
| 3 | 差分と試験ログの審査 | Opus（reviewer） |
| 4 | PR・GO 記録（委任 GO。DROP を含む migration の追加・変更は無い）・マージ | Opus |
| 5 | 入れ替え後の K6・K7 測定（3回分） | Sonnet が集計、Opus が判定 |
| 便2（未承認） | 5秒の8ファイルを1秒へ。DROP を含む2本は PO 本人の GO | PO 判断 |
| 便3（未承認） | run_py の接続にも付ける | 設計から |

## 12. 継続（維持の仕組み）
- 守り手: `scripts/run_all_migrations.sh`（値の正本と再試行）、`tests/sandbox/migration-run-sql-retry.sh`（挙動の試験。run_sql を変えたら流す）、`docs/adr/ADR-1037-migration-lock-timeout.md`（決まり）。
- 完了後の監視: K6・K7 を3回分記録して ADR-1037 の「結果」欄に追記する。
- 次フェーズへの引き継ぎ: 便2・便3、遅い時間帯B（再解析中）の原因は未確認のまま別テーマ。

## 13. 便1.1（入れ替え1回目の失敗を受けた補正）

### 13-1. 起きたこと（事実）
- PR #4610 を含む入れ替え（Deploy to VPS run 39575250541、2026-10-21 09:13〜09:23 UTC）で移行ステップが失敗した。
  - 止まったのは `migrations/082_extend_products_box_attributes.sql`（products に ADD COLUMN IF NOT EXISTS。ACCESS EXCLUSIVE を取りに行く）。
  - 09:22:17〜09:22:55 の約38秒、10回続けて lock timeout になり、1ファイルの上限（10回）で止まった。
  - 全体の再試行は 9/40 しか使っていない。ログは `/tmp/CC報告ファイル/migration-lock-timeout/merge/mig-step.txt` の末尾。
- 失敗時の後始末で、ai_ro のビューが外れたまま残った。`scripts/run_all_migrations.sh` の EXIT trap は、rc≠0 だとビューを作り直さない。
- 次の入れ替え run 39575404756（他の PR、09:23〜09:30 UTC）は全手順 success だった。"lock conflict" は0行で、ビューは 09:32Z に 511 本で戻っていた。
- 成功した入れ替えで 082 にかかった時間は、約0.2秒（39575404756）と約0.13秒（39565734963）。
- 38秒以上 products の鍵を離さなかった接続が何だったかは【未確認】。
  - 失敗の約6分後の調査では、products の鍵は0行だった。
  - reader の権限では他人の接続の中身が見えない（`/tmp/CC報告ファイル/migration-lock-timeout/incident/report.md`）。
- K6 の判定: 便1は「3回で失敗0」を満たさなかった（1回目が失敗）。

### 13-2. 補正の考え方
- 鍵の待ちは1回1秒のままにする（K1・K7 の守り。在庫表を待たせるのは最大1秒）。
- 止まった理由は、1ファイルの上限が全体の予算より先に尽きたこと。そこで、1ファイルでも全体の予算（40回）まで粘れるようにする。
  - 最悪の追加時間は今と同じ160秒（全体の予算で決まる）で、打ち切り10分に収まる（§3 の計算のまま）。
- 何が鍵を持っていたかを次から確かめられるよう、鍵が取れなかったときに、長く開いている接続の一覧をログに書く。

### 13-3. 変更前 → 変更後
| | 便1 | 便1.1 |
|---|---|---|
| `SQL_RETRY_MAX_ATTEMPTS` の既定 | 10 | 40（＝ `SQL_RETRY_BUDGET`。1ファイルでも全体の予算まで使える） |
| 鍵が取れなかったときのログ | 「lock conflict; retry …」の1行 | ファイルごとの1回目の衝突時と、上限に達したときに、開始から1秒を超えて開いている接続を書く（下の `log_lock_holders`） |
| 待ち1秒・間隔3秒・全体40回・ほかのエラー即停止 | — | 変えない |

### 13-4. 変更内容（`scripts/run_all_migrations.sh`）
- `SQL_RETRY_MAX_ATTEMPTS="${SQL_RETRY_MAX_ATTEMPTS:-10}"` → `SQL_RETRY_MAX_ATTEMPTS="${SQL_RETRY_MAX_ATTEMPTS:-40}"`
- その2行上のコメント `# 再試行はファイルごとに初回含め最大10回・3秒あけ、1回の実行全体で合計40回まで（移行ステップの打ち切り10分に収める）。` → `# 再試行は3秒あけ、1回の実行全体で合計40回まで。1ファイルでもその40回まで使える（移行ステップの打ち切り10分に収める。ADR-1037 便1.1）。`
- `SQL_RETRY_USED=0` の次の行（`run_sql() {` の前）に次を足す:
```bash
# 鍵が取れなかったときの手がかり: 開始から1秒を超えて開いている接続（ADR-1037 便1.1）
# 公開リポジトリの Actions ログに出るため、SQL の文面・接続元アドレスは出さない（命令の先頭1語と表名だけ）
log_lock_holders() {
  echo ">>> [${STEP}/${TOTAL}] lock holders (xact > 1s):"
  docker exec -e PGOPTIONS="-c lock_timeout=1s -c statement_timeout=5s" "${POSTGRES}" ${PSQL} -At -F ' | ' -c "SELECT a.pid, a.usename, a.application_name, a.state, coalesce(a.wait_event_type, '-'), round(extract(epoch FROM now() - a.xact_start))::int AS xact_sec, upper(coalesce(substring(a.query from '^[[:space:]]*([A-Za-z]+)'), '-')) AS cmd, coalesce((SELECT string_agg(DISTINCT c.relname || ':' || l.mode, ',') FROM pg_locks l JOIN pg_class c ON c.oid = l.relation WHERE l.pid = a.pid AND l.granted AND l.database = (SELECT oid FROM pg_database WHERE datname = current_database()) AND c.relkind IN ('r', 'p', 'v')), '-') AS locks FROM pg_stat_activity a WHERE a.pid <> pg_backend_pid() AND a.backend_type = 'client backend' AND a.xact_start < now() - interval '1 second' ORDER BY a.xact_start" 2>&1 | sed "s/^/>>> [${STEP}\/${TOTAL}]   /" || true
}
```
- 審査 review-code-1-1.md の R1・S1〜S3 を受けた形にしてある。
  - 命令は先頭の英字の並びだけを取る。区切りが改行・タブ・記号でも、値や文面が出ない。
  - 鍵は今の DB の分だけを出す。
  - 一覧を取る問い合わせ自体にも待ち1秒・実行5秒の上限を付ける。
  - `-i` を付けない。スクリプトの標準入力を docker exec に吸わせないため。
- run_sql の中:
  - `if grep -qE "deadlock detected|canceling statement due to lock timeout" "${errlog}"; then` の次の行に `[ "${attempt}" -eq 1 ] && log_lock_holders` を足す。
  - `echo ">>> [${STEP}/${TOTAL}] lock conflict; retry limit reached …"` の次の行に `log_lock_holders` を足す。
- ほかの行は変えない。

### 13-5. 試験（`tests/sandbox/migration-run-sql-retry.sh` に足す）
- 抽出範囲: `sed -n '/^SQL_LOCK_TIMEOUT=/,/^}/p'` は最初の `}`（`log_lock_holders` の終わり）で止まってしまう。そこで、`^SQL_LOCK_TIMEOUT=` から `^run_sql() {` の後の最初の `^}` まで取る。抽出行数を表示する。
- T3 に足す判定: ログに `lock holders (xact > 1s):` が出ていて、そのあとの行のどれかに `products:AccessShareLock` が含まれる。あわせて、ログに `pg_sleep` の文字が出ていないこと（SQL の文面を出していないことの確認）。
- T3d（新）: T3 の持ち主の行の7列目（cmd）が英大文字か `-` だけ（`^[A-Z]+$|^-$`）。T3 の持ち主の SQL は `BEGIN; …` なので `BEGIN` になること。
- T7（新）: 既定値の確認。`SQL_RETRY_MAX_ATTEMPTS` が 40、`SQL_RETRY_BUDGET` が 40。
- T8（新）: T4 と同じ「1回目だけ deadlock」で、ログに `lock holders` が1回だけ出る（2回目以降の再試行では出さない）。
- T1〜T6 は今の判定のまま全部 PASS すること。

### 13-6. 受け入れ基準（追加）
| 基準 | 検証方法 |
|------|---------|
| K8 1ファイルでも全体の予算まで流し直せる | sandbox-test T7 PASS |
| K9 鍵が取れなかったとき、開いている接続がログに出る（出なくても移行の成否は変わらない） | sandbox-test T3 の追加判定・T8 PASS |
| K6 の数え直し | 便1.1 を含む入れ替えから、移行ステップのある入れ替え3回で、deadlock・lock timeout による失敗0回。止まった場合は `lock holders` の行で持ち主を特定して次の手を決める |

### 13-7. 弊害・戻し方
- このリポジトリは公開設定で（`gh repo view shingo-ops/salesanchor --json visibility` = PUBLIC）、Actions のログは外から読める。
  - そのため、ログには SQL の文面・接続元アドレス・値を出さない。
  - 出すのは、接続番号・利用者名・アプリ名・状態・待ちの種類・開いている秒数・命令の先頭1語・鍵を持つ表名と鍵の種類だけ。表名はリポジトリの migration に既に載っている。
- 一覧を取る問い合わせが失敗しても、`|| true` で移行の成否は変えない。
  - `set -e`（`scripts/run_all_migrations.sh:20`）の下でも、`[ ... ] && log_lock_holders` の左辺が偽のときは止まらない。bash の仕様で、&& の左辺の失敗は errexit の対象外。
  - ただし、関数の最後の文が `[ ... ] && …` で偽になると、関数は rc=1 を返す。そのため、この形は run_sql の中の途中の行にだけ置く（呼び出し結果は使わない）。
- 戻し方: この PR を revert する（便1の形に戻る）。DB は変えない。
- 外部事例: GitLab の with_lock_retries も、ロック待ちの1回分は短く、試す回数は多く取る形（§5 と同じ出典）。今回は1回分の待ちを変えず、回数の配り方だけを変える。

## 14. 便1.2（K7 を毎回測れるようにする：移行中の読み取り計測）

### 14-1. 起きたこと（事実）
- K7 の測り方（§6）は、Prometheus の `http_request_duration_seconds_bucket{handler="/api/v1/inventory"}` を移行の時間帯で数えるものだった。2回の入れ替えのどちらでも、その時間帯にこの GET は0件で、判定できなかった。
  - 対象は run 39584411250（10:25〜10:32 UTC）と run 39604739864（13:05〜13:12 UTC）。
  - 根拠は ADR-1037 の結果欄（#4622 で訂正済み）と、生の出力 `/tmp/CC報告ファイル/ai-ro-restore/k7/windows.txt`。
- 計測の仕組みは `backend/app/metrics.py:10-20,83-109` にある。系列はプロセスの中に持ち、1件目の要求で作られ、再起動で0に戻る。このため、移行中に誰かが在庫表を開かない限り、何も数えられない。
- PO の選択（2026-10-21「1」）は「入れ替えのたびに、数秒おきに在庫表を自動で開いて時間を記録する手順を入れ替えに足す」。

- 設計審査（Opus architect、1回目）は REVISE だった。指摘8点と生の証拠は `/tmp/CC報告ファイル/k7-probe-review/`。下の 14-2 以降は、指摘を受けて書き直したもの。表の範囲の実物確認は `/tmp/CC報告ファイル/k7-probe-recon2/`。

### 14-2. 方針（どこで、何を測るか）
- 測る場所は移行を流している `scripts/run_all_migrations.sh` の中にする。移行の一覧（`trap _ai_ro_create_on_exit EXIT` の後）の間、裏で読み取りの計測を回す。
- 1回の計測では、在庫表の GET が読む表を1表1文で `SELECT 1 FROM public.<表> LIMIT 1` と読み、全体にかかった時間を測る。
- 移行が表に強い鍵（ACCESS EXCLUSIVE）を取りに行っている間は、後から来た読み取りもその後ろに並ぶ。これは PostgreSQL 16 の文書（pg_blocking_pids の soft block）で確かめた。ADR-1037 が短くしたのはこの「待ち」なので、この計測で測れるのは「在庫表を開いた人が、移行の鍵のせいで何ミリ秒待たされたか」になる。
- **K7 の意味が変わる**（PO の確認が要る。14-7）
  - これまでの K7 は「在庫表の表示が2秒以内」だった。
  - この計測の K7 は「移行の鍵による待ちが2秒以内」になる。
  - 鍵を待たない部分（在庫表のクエリそのものの時間）は、移行と関係なく、Prometheus の普段の値で見る。
- 計測の間隔は2秒。1文ごとの上限は lock_timeout=3s と statement_timeout=3s。1回（表の数だけ文がある）の上限は、表の数×3秒になる。
- 2秒を超えた回は、止めるときに時刻つきで1行ずつ書く（20行まで。超えた分は数だけ）。最後にまとめを1行書く: `>>> [final] read probe: n=<回数> slow=<2秒超の回数> error=<失敗した文の数> invalid=<時刻が取れなかった回数> max=<最大ms>ms`。

### 14-3. 選ばなかった案と理由
| 案 | 選ばなかった理由 |
|---|---|
| 在庫表の API（GET /api/v1/inventory）を外から本当に呼ぶ | 認証が要る。今あるスモーク用の利用者は、ADR-1017 で「送料計算だけ」に絞ってある（`docs/handoff/smoke-auth-least-privilege/design.md:36`）。在庫を読めるように権限を足すと、二段階認証を通らない鍵で在庫が読めるようになり、ADR-1017 の最小権限に反する。さらに、1回が画面表示と同じ重さになる（COUNT と DISTINCT を全行にかける。`backend/app/routers/inventory_offers.py:331-347`。source_messages は全件に sha256 をかける。`backend/app/services/tcg_condition_review_svc.py:99`）。その間、products などの鍵を約1秒持つので、移行の鍵の取り合いを自分で増やし、K6 を悪くするおそれがある |
| バックエンドの中で在庫表の本物のクエリを流す | 上と同じで重く、鍵を長く持つ |
| 誰かが開いた回を待つ（今のまま） | 2回続けて0件だった。いつ測れるか分からない |
| ai_ro を外す行（:119）から測る | 在庫表は ai_ro のビューを読まない（14-5 の一覧に無い）。測り始めを trap の後に置けば、止める処理が必ず走る（14-4） |

### 14-4. 変更内容（`scripts/run_all_migrations.sh`）
- 置き場所
  - 定数と2つの関数 `read_probe_start` / `read_probe_stop` は、`preflight_registered_files() {` の定義（今の :107）の直前に置く。つまり run_sql の閉じ括弧（:105）より後、`AI_RO_CREATE_SQL=`（:126）より前。
    - :65-105 は `tests/sandbox/migration-run-sql-retry.sh:40` の切り出し範囲なので、そこには置かない。
    - 目印の行で囲む: 始まり `# >>> read-probe begin`、終わり `# <<< read-probe end`。試験はこの2行の間を切り出す。
    - 関数名は `run_` で始めない。`TOTAL` は `^run_(sql|py)[[:space:]]` の行を数えるため（:47）。
  - `read_probe_start` は、`trap _ai_ro_create_on_exit EXIT`（今の :148）の直後で呼ぶ。trap が先に張られているので、移行のどこで落ちても止める処理が走る。
  - `read_probe_stop` は `_ai_ro_create_on_exit` の中、`trap - EXIT` の次の行で、`if declare -F read_probe_stop >/dev/null; then read_probe_stop || true; fi` として呼ぶ。
    - `|| true` で呼ぶと、関数の中では set -e が効かない。中のどの1行が失敗しても、ai_ro の作成と元の rc が守られる（再審査の試し）。中の各行の `|| true` も残す。
    - 関数が無い環境では何もしない。`tests/sandbox/ai-ro-restore-on-failure.sh:39` は `AI_RO_CREATE_SQL=` から trap の行までを切り出して eval する。そこには呼び出しの1行だけが入り、read_probe_stop の定義は入らない。`declare -F` が偽になって何もしないので、この形なら既存の試験は変えずに通る。
    - ai_ro の作成は ACCESS SHARE しか取らない（ADR-1024 改訂の T5）ので、計測の外でよい。
- 値の正本（目印の間に置く。環境変数での上書きは試験のためだけに使う）
  - `READ_PROBE_INTERVAL_SEC="${READ_PROBE_INTERVAL_SEC:-2}"`
  - `READ_PROBE_SLOW_MS="${READ_PROBE_SLOW_MS:-2000}"`
  - `READ_PROBE_STMT_TIMEOUT="${READ_PROBE_STMT_TIMEOUT:-3s}"`（lock_timeout と statement_timeout の両方に使う）
  - `READ_PROBE_TABLES="${READ_PROBE_TABLES:-<14-5 の14表を空白区切り>}"`
- 計測の子（`read_probe_start` の中）
  - `( … ) </dev/null >/dev/null 2>&1 &` として動かし、PID を `READ_PROBE_PID` に、結果ファイルを `READ_PROBE_OUT`（mktemp）に入れる。
    - 子の標準出力・標準エラーは全部捨てる。結果は子が `>>"${READ_PROBE_OUT}"` で明示して書く。これで SQL の文面・表名・psql のエラーが公開ログに出ず、ssh が子の出力を待つこともない。
  - 子の中は `set +e`。毎回の先頭で `kill -0 "${READ_PROBE_PARENT}" 2>/dev/null || exit 0`（親の PID は起動前に `READ_PROBE_PARENT=$$` で取る）。親が居なくなったら自分で終わる。
  - 1回分の読み方（psql は `${PSQL}` を使わない。ON_ERROR_STOP を付けないため）
    ```
    docker exec -e PGOPTIONS="-c lock_timeout=${READ_PROBE_STMT_TIMEOUT} -c statement_timeout=${READ_PROBE_STMT_TIMEOUT}" \
      -e PGAPPNAME=sa_read_probe "${POSTGRES}" \
      psql -X -q -At -U jarvis -d jarvis_db -c "SELECT 1 FROM public.<表1> LIMIT 1" -c "SELECT 1 FROM public.<表2> LIMIT 1" …
    ```
    - `-c` を表ごとに繰り返す。psql の文書（app-psql.html）どおり、1つの `-c` が1トランザクションになるので、前の表の鍵を持ったまま次の表を待つことがない。移行と deadlock の相手になる形を作らない。
    - `PGAPPNAME=sa_read_probe`: `log_lock_holders` の出力で、計測とアプリの接続を見分けられる。
    - psql の標準エラーは `${READ_PROBE_OUT}.err` に受け（毎回上書き）、`grep -c 'ERROR:'` の数を「失敗した文の数」とする。
    - psql か docker exec の終了コードが0でなく、ERROR: が0件の回（つなぐ段階の失敗）は、失敗の数に1を足す。
  - 時間は bash の `$EPOCHREALTIME`（bash 5 の組み込み。外部の date を使わない）を前後で取る。
    - 変換は `t=${EPOCHREALTIME/[.,]/}` で整数のマイクロ秒にし、`[[ $t =~ ^[0-9]+$ ]]` で確かめてから `ms=$(( (t1 - t0) / 1000 ))` とする。
    - 秒と小数を分けて `$(( ))` に入れる書き方は禁止。0で始まる値が8進数として読まれ、子が黙って止まる（再審査の試し）。
    - 値が空か数字でなければ、その回は invalid に数え、時間は記録しない。
    - 【未確認】prod1 の bash の版。Ubuntu（`scripts/setup_unattended_upgrades.sh:12` に Ubuntu 24.04 LTS）なら bash 5.2 のはず。初回の入れ替えで invalid=0 を確かめる（K10）。
  - 結果は1回1行: `<開始の epoch 秒> <ms または -> <失敗した文の数>`。
  - 回のあと `sleep "${READ_PROBE_INTERVAL_SEC}"`。
- 止める処理（`read_probe_stop`）。1行ずつ、どれが失敗しても終了コードを変えない
  ```
  [ -n "${READ_PROBE_PID:-}" ] || return 0
  kill "${READ_PROBE_PID}" 2>/dev/null || true
  wait "${READ_PROBE_PID}" 2>/dev/null || true
  ```
  - `wait` の標準エラーを捨てるのは、kill した子の終了を bash が中身つきで表示し、SQL の文面がログに出るため（審査の試し: `/tmp/CC報告ファイル/k7-probe-review/t.out` と `t2.out`）。
  - kill の後に、子が起動した docker exec が1つ残りうる。上限は表の数×3秒で、出力は捨ててあるのでログにもssh にも影響しない。鍵は ACCESS SHARE だけで、続く ai_ro の作成（ACCESS SHARE）とは衝突しない。
  - そのあと awk で結果ファイルをまとめ、2秒超えの行（20行まで）とまとめの行を書き、`${READ_PROBE_OUT}` と `${READ_PROBE_OUT}.err` を消す。結果ファイルが無い・空なら `n=0`。awk の失敗も `|| true`。
    - 2秒超えの行の形: `>>> [final] read probe slow: 2026-10-22T10:25:31Z 2350ms`。時刻は UTC。awk の strftime は使わず、bash の `TZ=UTC printf '%(%Y-%m-%dT%H:%M:%SZ)T' <epoch秒>` で作る。
- ログに出すのは時刻・ミリ秒・回数だけ。SQL の文面と表名は出さない（公開リポジトリ。§13-7）。
- 影響: 計測が持つ鍵は1文あたり数ミリ秒の ACCESS SHARE。移行の ACCESS EXCLUSIVE をその数ミリ秒待たせうるが、待ちの上限1秒（What 1）よりずっと短い。

### 14-5. 読む表の範囲と、在庫表のクエリとずらさない仕組み
- 在庫表の GET（`backend/app/routers/inventory_offers.py:350-475` の `list_inventory_view`）が1回で読む表を、関数ごとに確かめた（`/tmp/CC報告ファイル/k7-probe-recon2/`）。
  | 関数（file:line） | 読む表 |
  |---|---|
  | `load_distribution_settings`（`backend/app/services/tcg_distribution_svc.py:179-184`） | tcg_distribution_settings |
  | `distribution_rows_parts`（同 :304-407） | product_search_keywords・analysis_results・extraction_items・extraction_jobs・source_messages・supplier_channels・suppliers・products・line_units・type_master |
  | `source_cte(latest_stock=False)`（`backend/app/services/tcg_condition_review_svc.py:84-100`） | source_messages |
  | `review_joins(shime=False)`（同 :164-333） | products・conditions（ビュー）・item_corrections |
  | `result_order_sql`（`backend/app/services/tcg_result_order.py:18-42`） | conditions（ビュー） |
  | `_build_inventory_view_sql`（`inventory_offers.py:283-347`） | products・type_master |
  | 認証（`backend/app/auth/dependencies.py:82-109,124-260,565-603`） | users・tenants・user_roles・role_permissions・roles・permissions |
- 計測で読む表は次の14表（すべて public の表）。
  - analysis_results・extraction_items・extraction_jobs・source_messages・supplier_channels・item_corrections・line_conditions・products・line_units・product_search_keywords・suppliers・type_master・tcg_distribution_settings・users
- `conditions` の代わりに `line_conditions` を読む
  - `public.conditions` は `public.line_conditions` を元にしたビュー（`migrations/20260922_080000_rename_line_analysis_tables.sql:83`）。
  - `migrations/20261017_120000_line_conditions_value_rank.sql` は毎回流れ、1つの DO ブロックの中で「表（:13-14）→ ビュー（:47）」の順に強い鍵を取る。
  - ビューを読むと「ビュー → 表」の逆順に鍵を取るので、計測が deadlock の相手になりうる。表を直接読めば鍵は1つだけで、逆順にならない。
  - 待ちの長さは同じになる。ビューと表の鍵は同じトランザクションで取られ、確定（COMMIT）で一緒に外れるため。
- 外す表と理由
  - tenants・user_roles・role_permissions・roles: 権限とテナントは Redis のキャッシュが優先で、当たれば DB に行かない（`dependencies.py:263-314,575`）。user_roles・role_permissions・roles はテナントごとのスキーマ（`migrations/003_add_phase1_tenant_tables.sql:43,56,63`）で、計測からは1つに決められない。
  - permissions: 所有者・管理者のときだけ全件を読み（`dependencies.py:599`）、それ以外はキャッシュ優先。
  - users は毎回読む（`dependencies.py:95`）ので入れる。
- ずれを止める試験 `backend/tests/test_read_probe_tables.py`（CI の pytest で毎回流れる）
  - CI の pytest から `scripts/run_all_migrations.sh` を読めることは確かめてある（`backend/tests/test_supply_category.py:22,130` に実績。`.github/workflows/test.yml` は `scripts/**` の変更でも走る）。
  - 拾う範囲は、上の表の関数のうち認証を除く6つ。`ast` で関数を見つけ、`ast.get_source_segment` で関数全体の文字列を取る。そこから正規表現 `(?:public|\{TCG_SCHEMA\}|\{schema\})\.([a-z_]+)` で表名を拾う。
    - 6関数のどれかが見つからなければ（名前が変わったら）落とす。
    - `READ_PROBE_TABLES` は、目印の間の `READ_PROBE_TABLES="${READ_PROBE_TABLES:-...}"` の1行から読む。その行が1つでなければ落とす。
    - 限界: 6関数が呼ぶ先の関数はたどらない。在庫表の GET が新しい関数を呼ぶようになったら、この6関数の一覧を足す（`list_inventory_view` を変える PR の審査で見る）。
  - 置き換え表は試験の中に1つだけ持つ: `{"conditions": "line_conditions"}`（ビュー → 元の表）。
  - 拾った表名（置き換え後）と `users` が、すべて `READ_PROBE_TABLES` に入っていることを確かめる。在庫表のクエリに表が増えたのに計測に足していなければ、CI が落ちる。
  - 逆向き（計測にあるのに在庫表のクエリに無い表）も落とす。ただし `users` は認証の分として除く。

### 14-6. 試験（新しく `tests/sandbox/migration-read-probe.sh`）
- 使い捨て DB を使う（`tests/sandbox/ai-ro-restore-on-failure.sh` と同じ作り）。本物のスクリプトから `# >>> read-probe begin` 〜 `# <<< read-probe end` を切り出して使う。T7 は run_sql も `tests/sandbox/migration-run-sql-retry.sh:40` と同じ目印で切り出す。
- 流し方: `gh workflow run sandbox-test.yml --ref release/k7-read-probe -f test=migration-read-probe`（`--ref` は必須。`docs/ops/runner-commands.md:355`）。
- 試験の入れ物は `-e POSTGRES_USER=jarvis -e POSTGRES_DB=jarvis_db -e POSTGRES_PASSWORD=sandbox` で起動し、試験の中の `PSQL` と `PSQL_ARR` も jarvis / jarvis_db にする。本体スクリプトの値（:25 と計測の `-U jarvis -d jarvis_db`）は変えない。計測と run_sql が同じ DB に行くので、T7 の鍵の取り合いが起きる。
- 試験では `READ_PROBE_TABLES` を試験用の表で上書きし、`READ_PROBE_INTERVAL_SEC=1` にする。
- 子の PID: 試験の親スクリプトは、`read_probe_start` の直後に `READ_PROBE_PID` をファイルへ書く。T3・T8 はそのファイルの PID に `kill -0` をかけて、子が残っていないことを確かめる。
- T1（普段）: 鍵の取り合いが無いまま6秒回す。n≥2、slow=0、error=0、invalid=0。普段の1回の ms をログに書く（記録用）。
- T2（既に取られた鍵）: 別の接続が products に ACCESS EXCLUSIVE を取って6秒持つ（`READ_PROBE_STMT_TIMEOUT`＝3秒＋間隔2回分以上）。その間に計測を回す。slow≥1、error≥1（3秒で打ち切られた文）、まとめの行と `read probe slow:` の行が出る。
- T7（本番で起きる形）: 別の接続が products を読むトランザクションを6秒開いたままにする（ACCESS SHARE）。その間に、本物の run_sql（`SQL_LOCK_TIMEOUT=1s`、`SQL_RETRY_SLEEP_SEC=0`）で products に ACCESS EXCLUSIVE を取る SQL を流す。移行がその後ろで待ち続け、計測はさらに後ろに並ぶ。
  - 計測が本当に並んだ証拠として、その間に `pg_stat_activity` で `application_name='sa_read_probe'` かつ `wait_event_type='Lock'` の接続が1回以上見えること、かつ max≥300。
  - 合格: 300≤max≤1500、slow=0、run_sql は再試行のあと成功する。
- T3（終了コード）: 本物の切り出し（目印の間）と、本物の `_ai_ro_create_on_exit` の切り出し（`ai-ro-restore-on-failure.sh:39` と同じ目印）を一緒に読み込んだ親を作る。計測を始めた後に rc=3 で終わらせ、trap から止める。rc=3 のまま返り、まとめの行が出る。終了後に計測の子が残っていない（`kill -0` が失敗する）。
- T8（親が先に消える）: 親を `kill -9` で止める（trap が走らない）。計測の子は、間隔の2回分以内に自分で終わる。
- T4（表が無い）: 計測の表のうち1つが無い DB で回す。止まらず、error≥1 になり、まとめの行が出る。
- T4b（つながらない）: `POSTGRES` を存在しない入れ物の名前にして回す。止まらず、error≥1、まとめの行が出る。
- T5（公開ログ）: T1〜T8 の標準出力と標準エラーをすべて1つのファイルに集める（kill の経路と表が無いときのエラーを含む）。そこに `SELECT` と試験用の表名が0行。
- T6（抽出）: 切り出した行数を表示する。0行なら FAIL。
- T9（既存の試験）: `tests/sandbox/ai-ro-restore-on-failure.sh` と `tests/sandbox/migration-run-sql-retry.sh` も、変更後のスクリプトで PASS。あわせて次を確かめる。
  - retry 試験の切り出し（:40 の目印）の中に `read_probe` を含む行が0。
  - ai_ro 試験の切り出し（:39 の目印）の中に `read_probe` を含む行がちょうど1行で、それが `if declare -F read_probe_stop` で始まる行（関数の中は字下げされているので、`^[[:space:]]*if declare -F read_probe_stop` で比べる）。
- slow 行の書式: T2 で `read probe slow:` の行がすべて `^>>> \[final\] read probe slow: [0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z [0-9]+ms$` に合うことを確かめる。

### 14-7. 受け入れ基準（追加）
| 基準 | 検証方法 |
|------|---------|
| K10 入れ替えのたびに、移行中の読み取りの待ちが数えられる | 入れ替えのログに `read probe: n=` の行があり、n≥1、error=0、invalid=0 |
| K7（数え方を変える。PO の確認が要る） 移行ステップのある入れ替え3回で、移行の鍵による待ちが2秒を超えた回が0 | 入れ替えのログの `read probe: … slow=0 error=0` |
| K11 計測を足しても入れ替えの成否・終了コードは変わらない | sandbox T3・T8・T9 PASS、入れ替えの「Run database migrations」が success |
| K12 計測の表が在庫表のクエリとずれない | `test_read_probe_tables.py` が CI で PASS |
| K13 公開ログに SQL の文面・表名を出さない | sandbox T5 PASS、入れ替えのログで `read probe` の行に表名が0 |
| K14 計測が移行を詰まらせない | sandbox T7 PASS（max≤1500）。入れ替えの `lock holders` に `sa_read_probe` が出ても、`retry limit reached` が0 |

- slow が出たときの判定
  - 2秒超えの行の時刻を、同じ入れ替えのログの `[N/NN] psql < <ファイル>` と `lock conflict` の行の時刻（Actions のログの時刻）と突き合わせ、どのファイルの間かを決める。
  - そのファイルが `SET LOCAL lock_timeout='5s'` の8ファイル（§9、便2の対象）なら、「便2で直す分」として記録し、K7 の不合格に数えたうえで便2の根拠に使う。
  - 1つの移行トランザクションが表Aの鍵を取ってから表Bを待つと、表Aを読む側の待ちは1秒を超えうる（PostgreSQL 16 の文書: lock_timeout は鍵を取りに行く1回ごと）。その場合も、ファイルを特定して記録する。

### 14-8. 弊害・戻し方
- 移行の時間が延びる量は、止める処理（kill と wait とまとめ）の分だけで、1秒未満。
- 計測が DB に足す負荷は、2秒ごとに14表へ1行ずつ読む分だけ。
- 計測の表は在庫表のクエリの写しになる。ずれは K12 の試験で止める。
- この変更は `scripts/**` を変えるので、マージ後の入れ替えで移行ステップが走る（`.github/workflows/deploy.yml:38-43`）。それが K10 の1回目になる。
- 戻し方: この PR を revert する。DB は変えない。
