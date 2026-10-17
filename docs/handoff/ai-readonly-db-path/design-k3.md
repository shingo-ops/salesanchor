# 設計: ADR-1024 K3 改訂 — 読み取り台本の AUDIT を確実に監視へ届け、台本の結果表を監視へ流さない（v1.4）

作成: Opus（2026-10-17）／PO 依頼原文: 「最適な構成に整備してくれ」
状態: 設計審査済み（3回目 APPROVE 条件付き、review-audit-3.md。L-1〜L-5 反映済み）・PO 確認待ち（Decision 3 改訂と KGI）
- KGI の承認区分: PO 承認が要る。理由は、ADR-1024 Decision 3 の境界条件を変えるため（H-2）。ADR-1015 の B 区分としては扱わない。PO への y/n で、G1〜G5 と Decision 3 の改訂を一緒に確認する。
- 置き場所: マージ前に docs/handoff/ai-readonly-db-path/recon-k3.md・design-k3.md として commit する。
  - recon-k3.md は bin8/recon-audit/recon.md と本書 §2 から作る。
  - 仕様書（docs/specs）は作らない。理由は、K3 × の不具合修正で、STANDARD-WORKFLOW §1.5 の対象外であるため。
- 関連: ADR-1024、k-results.md、usage.md。根拠は bin8/recon-audit/、bin8/recon-audit2/（担当は recon2.md を書いたと報告したが、ファイルは実在しない。要点は本書 §2 に Opus が写した）、bin5/results.md。

## 1. 目的と成功条件
- 目的
  - AI が reader 鍵で本番 DB を読むたびに、台本の AUDIT 行が 1 回につき 1 行、取りこぼしなく監視（Loki）に残る。
  - 台本の stdout（結果表）を、ホストのディスクにも監視にも残さない。
  - DB 自身のエラー文に値が載る道は、本件の範囲外（R8）。
- KGI（○×で判定）
  | # | 基準 | 検証方法 |
  |---|---|---|
  | G1 | 本番で §8 の 5 本の SQL を 1 回ずつ流すと、Loki の `{job="sshd"}` から正規表現 `ai-reader-audit: AUDIT ts=\S+ sha=([0-9a-f]{12}) ` で取った sha が、5 本の sha とちょうど 1 対 1 で一致する（実行後 5 分以内）。5 本はすべて別の sha にする | Opus が reader 鍵で実行し、Grafana Viewer トークンで Loki の query_range を読む。生出力は bin9/ に保存 |
  | G2 | 5 本のうち 1 本を `SELECT md5('<seed>') AS v` にする。DB が計算した md5 値（結果にだけ出て、SQL 本文には出ない値）が、Loki の全 job `{job=~".+"}` で 0 件。seed の文字列は AUDIT 行（sshd job）と postgres の LOG 行にだけある | 同上 |
  | G3 | §8 の決定的な 4 本（1・2・5・6）で、変更前の基準値（bin8/baseline/）と次の 3 点が一致する | 生出力を突き合わせる |
  |    | ・stdout がバイト一致 | |
  |    | ・stderr のうち台本が出す行（AUDIT・rejected:・db error:・打ち切り:・error: で始まる行）が、ts= と ms= を除いて一致。compose 自身の行（Pseudo-terminal…・time=…・Container …）は比べない | |
  |    | ・rc が一致 | |
  | G4 | 単体テストで次の 3 点を確かめる | pytest（必須チェック pytest-run） |
  |    | ・送り口を開けない／送信が失敗する／送信が時間切れになるとき、rc=5 | |
  |    | ・開けないときは DB に接続しない | |
  |    | ・ok の経路で送信が失敗したら stdout は空 | |
  | G5 | GitHub の sandbox-test で、出荷する docker-compose.ai-reader.yml と backend の Dockerfile のイメージ（appuser）をそのまま使い、次の 4 点を確かめる | tests/sandbox/ai-reader-audit.sh を PR ブランチで実行。run ID を記録 |
  |    | (a) rejected で rc=2、呼び出し側に stderr の AUDIT 行が届く | |
  |    | (b) `journalctl -t ai-reader-audit` に同じ行が 1 行ある | |
  |    | (c) command を echo に上書きして、stdout・stderr の両方が呼び出し側に届く（logging none でも attach で届く） | |
  |    | (d) source の /dev/log が無いとき、rc≠0 で、ホストにディレクトリが作られない | |

## 2. 現在地（事実と根拠）
- 【事実】K3 ×: 23 回中 1 回しか Loki に無い（bin5/results.md:39-45）。
- 【事実】AUDIT は stderr に 1 行書くだけ（backend/app/ops/readonly_query.py:175-179）。改行は空白に置換済み（:177）。_log の呼び出しは :193・:200・:206・:225・:242・:255（審査で origin/main 3ef45607 と一致を確認済み）。
- 【事実】ai-reader は `run --rm` の短命コンテナで、logging の設定が無い（docker-compose.ai-reader.yml:1-31、:4）。既定の json-file になる。
- 【事実】ADR-1024:32 の Decision 3 は「volumes なし」。
- 【事実】promtail は /var/lib/docker/containers/*/*log をファイルとして拾う（monitoring/promtail/promtail.yml:56-62）。
- 【事実・新規】直近 24h の Loki に、ai-reader コンテナ 14 個分の行がある。
  - うち 9 個は stdout（結果表）も入っていた。計 308 行（bin8/recon-audit/reader-stdout-summary.txt）。
  - 中身は件数・表名・区分名の集計で、個人情報は見当たらない（Opus が該当行を確認）。
- 【事実】/var/log/auth.log は Loki に届いている。{job="sshd"} に 19:23 JST の CRON・sshd 行がある（bin8/recon-audit/loki-sshd.json）。
  - CRON・sshd は /dev/log へ書く。つまり「/dev/log → auth.log → Loki」の道は prod1 で動いている。経路が imuxsock か imjournal かは問わない。
- 【事実】promtail の auth.log 収集は promtail.yml:41-53（:48）。/var/log の ro マウントは docker-compose.exporters.yml:89。
- 【事実】backend イメージの実行ユーザーは appuser（backend/Dockerfile:28-29、adduser --system）。
- 【事実】本番の compose は /home/ubuntu/salesanchor/docker-compose.ai-reader.yml（authorized_keys の固定コマンド、bin3b 記録）。deploy.yml:253-254 の git reset で更新され、:399-400 の `docker compose build` でイメージが作り直される。
- 【事実】readonly_query を import するのは backend/tests/ops/test_readonly_query.py:12 だけ。"AUDIT ts=" の依存は readonly_query.py:179 と usage.md:22 だけ（審査で確認）。
- 【事実】Loki の保持は monitoring/loki/loki-config.yaml:29 の retention_period 30d。compactor の retention_enabled の記述は無い。
- 【事実（公式文書）】
  - compose の bind は、元のパスが無いとホストにディレクトリを作る。長い書き方で `create_host_path: false` にすると作らない（docs.docker.com compose-file services#volumes）。
  - journald の流量制限は 30 秒に 10000 行（journald.conf(5)）。
- 【未確認→G5】logging none で、attach（compose run -T）の stdout・stderr が届くか。公式文書に記載が無く、Mac に Docker daemon が無い。
- 【未確認→G5・G1】非 root の appuser から、bind した /dev/log へ書けるか。prod1 の /dev/log のパーミッション。
- 【推測】取りこぼしの原因: コンテナが消えるとログファイルも消え、promtail が見つける前に消える。

## 3. 案の比較と選択
| 案 | 内容 | AUDIT 確実性 | 台本 stdout の流出 | ホスト変更 | 判定 |
|---|---|---|---|---|---|
| A | logging を syslog／journald ドライバへ | 高 | stdout も流れる | なし | 不採用 |
| B | コンテナ寿命を延ばす | 中 | 流れる | なし | 不採用 |
| C | logging none ＋ /dev/log ソケット 1 本の bind で AUDIT を直接送る | 高（sshd と同じ道） | 止まる | なし | **採用** |
| D | ホストのファイルへ追記＋promtail job 追加 | 高 | 止まる | 書込マウント・権限・logrotate | 部品が多い |
| E | promtail の syslog 受け口へ TCP | 高 | 止まる | ポート公開。promtail 停止で台本も止まる | 不採用 |
- C を選ぶ理由
  - 実績のある道に乗り、promtail・Loki・ホストの設定を変えない。
  - 足すマウントはソケット 1 本で、ファイルを書く道ではない。送るだけ。

## 外部・過去事例の参照と我々への応用
- 外部事例: ソケットを bind して /dev/log へ送る構成は、コンテナの syslog 送信の一般的な形。注意点は、journald を再起動するとソケットの実体が作り直されること。ai-reader は毎回新しく起動して bind し直すので、影響は無い。数値の前例は使わない。根拠は本番の実測で足りる。

## 4. 変更内容（これ以外は触らない）
1. backend/app/ops/readonly_query.py
   - 定数を足す。
     - `AUDIT_SOCKET = "/dev/log"`
     - `AUDIT_IDENT = "ai-reader-audit"`
     - `AUDIT_PRI = 38`（auth=4 × 8 + info=6）
     - `AUDIT_TIMEOUT = 2.0`
   - `_open_audit(path)`
     - AF_UNIX・SOCK_DGRAM で作り、`settimeout(AUDIT_TIMEOUT)` を設定してから connect する。
     - 失敗は OSError をそのまま投げる（timeout も OSError の一種）。
   - `_log(stderr, sql, rows, ms, result, audit) -> bool`
     - 書式を変えずに、AUDIT 行を stderr に書く。
     - 同じ行を `f"<{AUDIT_PRI}>{AUDIT_IDENT}: {line}"`（末尾改行なし、UTF-8）で send する。
     - OSError なら、stderr に `error: audit send failed` を書いて False を返す。成功なら True を返す。
   - `main(..., audit=None, audit_path=AUDIT_SOCKET)`
     - stdin を読む前に、audit が None なら `_open_audit(audit_path)` を呼ぶ。
     - OSError なら、stderr に `error: audit channel unavailable` を書いて rc=5 で返す。DB には接続しない。
     - rejected・env_missing・no_result・db_error の経路: _log が False なら rc=5。
     - ok の経路（M-1 の対処）
       - 結果の行を fetchmany したあと、stdout に書く前に `_log(... "ok")` を送る。
       - rows には、打ち切り後の件数を入れる。
       - False なら stdout に何も書かず、rc=5 で返す。
       - True なら、見出しと行を stdout に書く。
       - stdout への書き込みは DB の try/except（:233-243）の外に出す。書き込みに失敗（BrokenPipeError など）しても AUDIT を 2 回目は出さない。例外はそのまま上げ、rc は Python の既定（1）になる（M-B）。
       - 打ち切りの文（stderr）は今と同じ位置に出す。
     - 最後に try/finally で audit を close する。注入された audit も close する（偽物は close を記録するだけ）。
   - docstring（:9 付近）の終了コード一覧に rc=5 を足す。
2. docker-compose.ai-reader.yml の ai-reader に足す（長い書き方）。
   ```yaml
       logging:
         driver: "none"
       volumes:
         - type: bind
           source: /dev/log
           target: /dev/log
           bind:
             create_host_path: false
   ```
   - 先頭コメントに 1 行足す。「AUDIT は /dev/log → auth.log → Loki。結果は残さない（logging none）。マウントはこのソケット 1 本だけ（ADR-1024 Decision 3 改訂）」。
   - ほかの項目は変えない。
   - bind の `:ro`（bind マウントの読み取り専用。コンテナ全体の read_only: true とは別物）は付けない。ソケットへの送信に ro が効くかは確かめていないので、変数を増やさない。
3. backend/tests/ops/test_readonly_query.py
   - 既存の `run()`（:17-20）を、必ず偽の audit（send・close を記録する物）を渡す形に変える。CI 機に /dev/log があると、注入漏れでも通ってしまうため。
   - 既存テストの期待値（rc・stdout・stderr）は変えない。
   - 足すテスト
     - T1: 5 経路（rejected 64KB 超・rejected 禁止語・env_missing・no_result・db_error）と ok で、send がちょうど 1 回。中身は `<38>ai-reader-audit: AUDIT ts=` で始まり、stderr の AUDIT 行（改行を除く）と同じ。
     - T2: `audit_path` に tmp_path の存在しないパスを渡す（audit は None）。rc=5、connect が呼ばれない、stdout が空。
     - T3: send が OSError を投げる偽物で、db_error の経路は rc=5。stderr に `audit send failed` が出る。
     - T3b: send が `socket.timeout` を投げる偽物で、rc=5。
     - T5: ok の経路で send が OSError のとき、rc=5 で stdout が空。
     - T6: ok の経路で、send の時点では stdout がまだ空（送信が先）。
     - T7: 正常終了・異常終了のどちらでも close が 1 回呼ばれる。
     - T8: ok の経路で、stdout の write が BrokenPipeError を投げる偽物のとき、send はちょうど 1 回（result=ok）。db_error の AUDIT は出ない。
4. tests/sandbox/ai-reader-audit.sh（新規。規則は docs/ops/runner-commands.md §10 と tests/sandbox/README.md）
   - 準備
     - `docker network create astro-webapp_backnet` を作る。
     - `AI_READER_DATABASE_URL=postgresql://x:y@127.0.0.1:1/none` のダミー値を使う。
     - `docker compose -f docker-compose.ai-reader.yml build ai-reader` で、./backend の Dockerfile から作る。
   - (a)(b): 64KB を超える `SELECT 1 -- <埋め草>`（試験内で python3 により生成。禁止語の文字列はフックに止められるので使わない）を標準入力にして `docker compose -f docker-compose.ai-reader.yml run --rm -T --no-deps ai-reader` を流す。
     - rc=2。
     - 保存した stderr に AUDIT 行がある。
     - `sudo journalctl -t ai-reader-audit --since <開始時刻>` に、sha 一致の 1 行がある。
   - (c): 同じ compose で `run --rm -T --no-deps --entrypoint sh ai-reader -c 'echo OUT; echo ERR >&2'` を流す。保存した stdout に OUT、stderr に ERR がある。
   - (d): 一時的な上書き compose（試験内で生成）で、source を `/nonexistent-ai-reader-log` にして同じ run を流す。
     - rc≠0。
     - 実行後に `/nonexistent-ai-reader-log` が存在しない。
   - logging none では docker logs が使えない。このため、README の「失敗時に docker logs を出す」の代わりに、attach の出力をファイルへ保存し、trap で出す。この違いを試験の先頭コメントに書く。
   - 期待と違えば exit 1。
5. docs
   - usage.md
     - :22 の説明に、Loki の見方 `{job="sshd"} |= "ai-reader-audit:"` を足す。
     - 終了コード表（:24-29）に rc=5 と、stdout の書き込み失敗時の rc=1（AUDIT は ok で記録済み）を足す。
     - 「auth.log の AUDIT 行は足すことはできても消すことはできない。正本の記録は DB の log_statement」と 1 行書く。
   - ADR-1024 の「実装結果」の末尾、「関連 ADR」の直前に「### 改訂（K3、2026-10-17）」を足す。中身は次の 4 つ。
     - 経緯: 1/23、結果表が時々監視に入っていた事実。
     - Decision 3 の「volumes なし」を「/dev/log ソケット 1 本の bind だけ（create_host_path: false）。ほかのマウントは足さない」に改める。理由は送信だけでファイルを書く道ではないこと。
     - 案 C の採用。
     - 残る危険（R8）。
   - k-results.md の K3 に「改訂済み。本番測定は K3-2 で追記」と書く。
   - docs/handoff/ai-readonly-db-path/recon-k3.md・design-k3.md を新規に作る。
   - `node scripts/generate-adr-index.js` を実行する。
- 触らないもの
  - promtail.yml・exporters compose・deploy.yml・Loki 設定・authorized_keys・ホストの設定・migrations・ruleset。
  - K14 の記載（別の docs PR、§8）。
  - 既に Loki に入った 308 行（R7）。

## 5. 影響範囲
- 呼び出し元は authorized_keys の固定コマンドだけ。import 元はテストだけ（§2）。
- auth.log が 1 回につき 1 行増える。
- 危険パス（scripts/check-process-artifacts.js:124-126）に当たる。PR 本文に GO 記録が要り、委任 GO で可（ADR-1024:96）。
- マージで本番に反映される（ADR-135）。backend イメージを作り直すが、ops 配下は ai-reader でしか使わない。

## 6. リスクと対処
| # | リスク | 対処 |
|---|---|---|
| R1 | 本番で /dev/log が使えず、毎回 rc=5（読み取りの道が止まる） | G5 で事前に確かめる。本番の G1 が × なら、即 revert PR（委任 GO）で戻す |
| R2 | /dev/log の行が auth.log に入らない | CRON・sshd が同じ道で入っている。G1 で確かめ、× なら R1 と同じく戻す |
| R3 | auth.log に AUDIT に似た行を足される | 足すことはできるが消すことはできない。正本は DB の log_statement。照合は行頭に固定した正規表現で行う |
| R4 | docker logs が見られない | 呼び出し側が stderr を受け取る。DB 側の記録も残る |
| R5 | journald が詰まって台本が止まる | 送信は 2 秒で打ち切り、rc=5 にする（T3b） |
| R6 | /dev/log が一時的に無いときに、ホストにディレクトリが作られて syslog を壊す | create_host_path: false にする（G5 (d)） |
| R7 | 既に Loki に入った台本の結果表 308 行 | 中身は集計値で個人情報なし。retention_period 30d の記述はあるが、実際に消えるかは未確認。消すには prod2 の Loki 削除 API が要るので、本件では行わず PO に事実を報告する。2026-10-17 19:38 の基準値取得（q1・q2）の stdout も同じ道で入った見込み【推測】 |
| R8（残る） | DB のエラー文（型変換の失敗など）に値が載り、postgres のログから Loki に入る道 | 本件の範囲外。PO に事実を報告し、対策（ログの伏せ字など）は別件にする。PostgreSQL の公式文書では未確認 |

## 7. 戻し方
- revert PR を委任 GO でマージ → deploy で compose と台本が元に戻る。ホストは変えていないので、これだけで戻る。

## 8. 計画（便）
- 便 K3-1（本 PR）
  - §4 の 1〜5 を入れる。
  - CI 緑、G5 の sandbox-test の run 緑、Opus の差分審査を確かめる。
  - 委任 GO でマージする。
- 便 K3-2
  - デプロイ成功を確かめてから、Opus が本番で G1〜G3 を測る。
  - 5 本の SQL（すべて別の sha。番号は旧版に合わせ 4 は欠番）
    1. `SELECT 1 AS a, 'k3' AS b`（ok）
    2. `SELECT g FROM generate_series(1,300) g`（打ち切りの ok）
    3. `SELECT md5('k3probe-<乱数>') AS v`（ok、G2 用）
    4. 欠番。禁止語の rejected は本番で流さない。基準値取得で Opus のフック（agent-danger-hook）が禁止語の文字列を含むコマンドを止めたため、言い換えはせず本番測定から外した。この経路は単体テスト T1 で確かめる。
    5. 64KB を超える `SELECT 1 -- <埋め草>`（rejected・64KB 超）
    6. `SELECT * FROM public.users LIMIT 1`（db_error 42501）
  - G3 の比較相手: 今の台本で 1・2・5・6 の 4 本を Opus が本番で流した基準値（bin8/baseline/q1・q2・q5・q6 の .out/.err/.rc、2026-10-17 19:38 JST 取得済み）。rc は 0・0・2・4、stdout は 2 行・201 行・0 行・0 行。3 は乱数のため対象外。4 本すべてで一致すれば ○、1 本でも欠ければ ×。
  - check_sql の拒否経路（readonly_query.py:200）は本番・sandbox では通さず、単体テスト T1 だけで確かめる（審査3 L-1）。
  - sha の照合（審査3 L-2）: G3 は baseline の q*.sql をそのまま（末尾改行込み）流す。G1 は、呼び出し側が受け取った stderr の AUDIT 行の sha と Loki の sha を照合する。
  - 結果を k-results.md に追記する docs PR を出す。
- 便 K14（別の docs PR）
  - k-results.md・ADR-1024 の K14 を、設定ファイル＋公式既定値による ○ で更新する。
  - 測り方の変更なので、PO に y/n で確かめてから出す。

## 維持の仕組み
- process-artifacts gate の危険パスにより、台本・compose の変更には GO 記録が要る。
- 単体テスト T1〜T8 が必須チェック pytest-run で毎回走る。
- usage.md に Loki の見方と正本の位置づけを書く。
