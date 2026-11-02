# recon：本番サーバー上の作業を Opus に委任する前の現在地（2026-11-02）

## 既存 ADR の検索
- `git grep -n -E '無制限鍵|manual-only' origin/main -- docs/adr AGENTS.md`、`docs/adr/FEATURE-INDEX.md` で確認。
- 該当: docs/adr/ADR-1003-go-delegation-to-opus.md（GO の委任）、docs/adr/ADR-1034-opus-permission-delegation-ledger.md（権限の足し引きと記録帳）、docs/adr/ADR-1033-conversation-consent-ticket.md（会話の同意票）。

## 今の決まり（【事実】）
- `AGENTS.md:26`（変更前）: 無制限鍵での「変更を伴う作業（ファイル作成・コンテナ起動停止・設定変更・再起動・DB 書き込み）は作業ごとに PO の GO が必要」。
- `docs/handoff/go-record-transcription/opus-delegation.md:34`: 10/15 の委任の追加は「無制限鍵での本番の変更は含めない。含めるには ADR と CLAUDE.md の改訂が要るので、別の PR で扱う」。
- `docs/handoff/gas-viewer-fresh-fast/design.md:606`: 2026-10-17 PO「n」（閲覧者の操作の GO は委任しない）。この PR は Q12 を上書きしない（閲覧者のアカウントの操作は ADR-1003 追記の除外に入れた）。
- `scripts/dev/perm-change.py:42`: 自動の安全判定の許可の行（user-automode-allow）は道具では「外す」だけ。足すのは PO の `!` 実行。

## 実測（【事実】・根拠 ~/CC報告ファイル-keep/autonomy-inventory/20261102.md）
- 2026-10-26〜11-02 に自動の安全判定が止めた操作 約50件のうち、本番サーバー上の書き込み・停止は 7 件（Remote Shell Writes 6・Interfere With Workloads 1）。すべて PO の `!` 実行が要った。
- 同じ期間に許可の行を足した2件（shingo-ops 名義の Approve・クラウドの担当の起動）は、足した後の止まりが 0 件。
- 期限付きの同じ形の許可 FNT-1・FNX-1 は、2026-11-02 の週次点検で期限切れのため外した（~/CC報告ファイル-keep/consent-weekly/20261102-changes-analysis.md）。

## ログインの記録（【事実】2026-11-02 16:22 JST、読み取りだけの調査で実測）
- prod1・prod2 とも、ubuntu は adm の組に入っており、`/var/log/auth.log` を sudo なしで読める（`id -nG` の結果に adm）。
- 「Accepted publickey」の行に鍵の指紋が出る。無制限鍵の指紋（`ssh-keygen -lf` の値）での受け入れは、2026-11-01 以降で prod1 64回・prod2 5回。
- 記録は毎週入れ替わり、4週分残る（`/etc/logrotate.d/rsyslog` の `weekly`・`rotate 4`、`auth.log` から `auth.log.4.gz` まで）。
- このため、ログインの数と作業の記録の数は一致しない（読み取りだけの調査でも1回ずつ数えられる）。照合は時刻で並べて行う。

## 今の自動の安全判定の止める行（【事実】2026-11-02、~/.claude/settings.json を読み取り）
- autoMode.soft_deny は3行。そのうち1行（記録用の番号 a2585405）が `Bash(docker compose restart *) — container restarts on prod are forbidden without PO decision; ...` で、本番の容器の再起動を PO の決定なしには止める。
- 足す許可の行は「docker compose の再起動」を含むので、この止める行と重なる。どちらが勝つかは【未確認】。

## 【未確認】
- 7 件のそれぞれが、その時点で審査済みの作業手順に書かれていたか（会話記録を Bash で数えると見張りが止めるため未集計）。委任後は ADR-1003 追記の条件6の記録で毎回確かめる。
