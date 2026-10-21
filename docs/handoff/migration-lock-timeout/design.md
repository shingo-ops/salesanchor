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
