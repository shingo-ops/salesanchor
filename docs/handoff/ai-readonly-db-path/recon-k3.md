# recon-k3: AUDIT 行が Loki に届かない件（ADR-1024 K3 改訂）

基準: origin/main（fetch 済）。設計: [design-k3.md](design-k3.md)。ADR 検索: `docs/adr/ADR-1024-ai-readonly-db-path.md`（Decision 3・5、K3）。生出力の原本は /tmp/CC報告ファイル/readonly-db-path/bin8/recon-audit/。

## A. 事実（file:line はリポジトリルートからのフルパス）
1. 【事実】K3 ×: 23 回中 1 回しか Loki に無い（docs/handoff/ai-readonly-db-path/k-results.md:9、原本 bin5/results.md:39-45）。
2. 【事実】AUDIT は stderr に 1 行書くだけ: backend/app/ops/readonly_query.py:175-179。改行置換は backend/app/ops/readonly_query.py:177。_log の呼び出しは backend/app/ops/readonly_query.py:193・:200・:206・:225・:242・:255。stdout 書き込みは backend/app/ops/readonly_query.py:233-243（DB の try の中）。
3. 【事実】ai-reader は `run --rm` の短命コンテナ（docker-compose.ai-reader.yml:4）、logging の設定なし（docker-compose.ai-reader.yml:1-31）。他の本番 compose は json-file。journald/loki/syslog 指定は repo に前例なし。
4. 【事実】ADR-1024 Decision 3 は「volumes なし」（docs/adr/ADR-1024-ai-readonly-db-path.md:32）。
5. 【事実】promtail は /var/lib/docker/containers/*/*log をファイルとして拾う（monitoring/promtail/promtail.yml:56-62）。auth.log の収集は monitoring/promtail/promtail.yml:41-53。nginx error.log は monitoring/promtail/promtail.yml:24-37。
6. 【事実】promtail の動作場所は prod1。/var/log を ro マウント（docker-compose.exporters.yml:89）、/var/lib/docker/containers を ro マウント（docker-compose.exporters.yml:90）。起動は .github/workflows/deploy.yml:441。
7. 【事実】直近 24h の Loki に ai-reader コンテナ 14 個分の行があり、うち 9 個は stdout（結果表）も入っていた。計 308 行（bin8/recon-audit/reader-stdout-summary.txt）。中身は件数・表名・区分名の集計で、個人情報は見当たらない。
8. 【事実】/var/log/auth.log は Loki に届いている。{job="sshd"} に CRON・sshd 行がある（bin8/recon-audit/loki-sshd.json）。CRON・sshd は /dev/log へ書くので、「/dev/log → auth.log → Loki」の道は prod1 で動いている。
9. 【事実】backend イメージの実行ユーザーは appuser（backend/Dockerfile:28-29）。
10. 【事実】本番の compose は /home/ubuntu/salesanchor/docker-compose.ai-reader.yml。deploy.yml:253-254 の git reset で更新され、.github/workflows/deploy.yml:399-400 の `docker compose build` でイメージが作り直される。
11. 【事実】readonly_query を import するのは backend/tests/ops/test_readonly_query.py:12 だけ。"AUDIT ts=" の依存は backend/app/ops/readonly_query.py:179 と docs/handoff/ai-readonly-db-path/usage.md:22 だけ。テストの run() は backend/tests/ops/test_readonly_query.py:17-20。
12. 【事実】Loki の保持は monitoring/loki/loki-config.yaml:29 の retention_period 30d。
13. 【事実（公式文書）】compose の bind は、元のパスが無いとホストにディレクトリを作る。`create_host_path: false` で作らない。journald の流量制限は 30 秒に 10000 行。

## B. 仮説（推測）
- 【推測】取りこぼしの原因: コンテナが消えるとログファイルも消え、promtail が見つける前に消える（--rm: docker-compose.ai-reader.yml:4）。

## C. 未確認（sandbox G5・本番 G1 で確かめる）
- 【未確認】logging none で attach の stdout・stderr が届くか。
- 【未確認】非 root の appuser から bind した /dev/log へ書けるか。prod1 の /dev/log のパーミッション。

## D. 確実に届ける候補（repo 前例）
- ファイル追記＋file 収集は、書込みマウントが要る（read_only: true、docker-compose.ai-reader.yml:17）。前例なし。
- journald／syslog ドライバは repo に前例なし。結果表も流れる。
- /dev/log へ直接送る案が、既存の sshd と同じ道で、ホスト側の変更なし（採用、design-k3.md §3）。
