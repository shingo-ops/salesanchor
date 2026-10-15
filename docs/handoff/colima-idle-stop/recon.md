# Colima 使い終わり自動停止 recon（2026-10-15）

親（設計仕様書）: [docs/specs/colima-idle-stop/README.md](../../specs/colima-idle-stop/README.md)

基準: origin/main 93a671476621cf79779f682f9adf85a08dcdccd7（fetch 済）。生出力: /tmp/CC報告ファイル/ac-heavy/docker-idle/ と recon2/（読み取りのみ）。

## 既存 ADR の検索
- `git grep -il "colima" origin/main -- docs/adr/` → 該当なし（grep 済み・該当なし）。
- `git grep -il "disk-janitor" origin/main -- docs/adr/` → docs/adr/ADR-114-worktree-auto-cleanup.md:83, :161 のみ（Mac の自動片付けの前例）。
- docs/adr/FEATURE-INDEX.md に Colima/Docker の自動停止の項目なし。

## 現在地（事実）
- Mac は RAM 8GB（hw.memsize 8589934592）。10/15 08:37 時点で PhysMem 7482M used・unused 149M、Colima の VM（com.apple.Virtualization.VirtualMachine PID 30161）が 2060M（/tmp/CC報告ファイル/ac-heavy/now-status.txt）。
- Colima 0.10.3。profile default は Running（2CPU/2GiB/100GiB）、sa-private-ci は Stopped（docker-idle/4-colima-list.txt）。~/.colima/default/colima.yaml: memory 2・autoActivate true（9-colima-yaml.txt）。
- 起動時刻 10/15 04:14:55（limactl usernet PID 28575）。起動した主体は未確認（docker-idle/4-ps.txt）。
- 動いているコンテナは salesanchor-postgres-1 の1つ（postgres:16, healthy）。RestartPolicy=unless-stopped、compose project=salesanchor、config=/Users/tanizawashingo/salesanchor/docker-compose.yml（5-inspect.txt）。
- 使用状況: docker stats CPU 0.00〜0.03%（6-stats.txt, recon2/docker-stats.txt）、自分以外の client backend 0（recon2/pg-conn.txt）。接続数の確認コマンド: `docker exec salesanchor-postgres-1 sh -c 'psql -U "$POSTGRES_USER" -d postgres -Atc "select count(*) from pg_stat_activity where backend_type = '"'"'client backend'"'"' and pid <> pg_backend_pid()"'`（読み取りのみ）。
- Colima を起動・停止する仕組みはリポジトリ・~/.claude・~/Library/LaunchAgents・brew services のどこにも無い（1-grep.txt: `colima start|stop` 0件、3-brew.txt: colima none、2-claude-la.txt）。
- `docker compose up` を使うのはリハーサル用のみ: scripts/test_rollback_simulation.sh:156,287,351,408、scripts/rehearsal_phase2.sh:310,334,373,379（1-grep.txt）。
- docs の colima 参照9件はすべて専用 profile を作って終了後に stop する運用の記録（例 docs/handoff/dist01-ar-created-at/design.md:112）。default を常時動かす規定は無い（8-colima-refs.txt）。
- 判定コマンドの実測（recon2/）: `colima status -p default` 起動中 exit 0／停止中の profile は exit 1（colima-default.txt, colima-sa.txt）。`colima stop --help`: 「Stop Colima to free up resources. The state of the VM is persisted at stop.」

## 前例（同じ作り方に揃える）
- scripts/disk-janitor.sh（404行）: 設定は1か所・環境変数で上書き（:23-48）、ログ自前ローテーション 1MB（:337-344）、mkdir ロック＋trap（:33, :360-365）、source 可能で試験が関数を呼ぶ（:19）。
- ops/launchd/jp.salesanchor.disk-janitor.plist: 道具専用コピー ~/.salesanchor-tools を origin/main に更新・きれいさ確認してから実行（plist-repo.txt）。設置済みと同一（diff SAME）。
- scripts/tests/test-disk-janitor.sh（256行）: mktemp 領域＋check 関数（:28, :35, :185, :222-230）。
- 設置手順の正本: docs/ops/runner-commands.md:220-263。
- 短間隔の前例: jp.salesanchor.ops-intake-watchdog（StartInterval 300, RunAtLoad true, KeepAlive false）。
- 危険パス分類: scripts/check-process-artifacts.js:117-118（scripts/・ops/launchd/）→ GO 必須（ADR-136）。

## 未確認
- 10/15 04:14:55 に Colima を起動した主体。
- コンテナ0件のときの `docker ps --format json` の出力形。
- `colima stop` の所要時間。
