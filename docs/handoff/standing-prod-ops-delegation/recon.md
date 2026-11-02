# recon：本番サーバー上の作業を Opus に委任する前の現在地（2026-11-02）

## 既存 ADR の検索
- `git grep -n -E '無制限鍵|manual-only' origin/main -- docs/adr AGENTS.md`、`docs/adr/FEATURE-INDEX.md` で確認。
- 該当: docs/adr/ADR-1003-go-delegation-to-opus.md（GO の委任）、docs/adr/ADR-1034-opus-permission-delegation-ledger.md（権限の足し引きと記録帳）、docs/adr/ADR-1033-conversation-consent-ticket.md（会話の同意票）。

## 今の決まり（【事実】）
- /Users/tanizawashingo/worktrees/.salesanchor-tools/release-standing-prod-ops-delegation/AGENTS.md:26（変更前）: 無制限鍵での「変更を伴う作業（ファイル作成・コンテナ起動停止・設定変更・再起動・DB 書き込み）は作業ごとに PO の GO が必要」。
- /Users/tanizawashingo/worktrees/.salesanchor-tools/release-standing-prod-ops-delegation/docs/handoff/go-record-transcription/opus-delegation.md:34: 10/15 の委任の追加は「無制限鍵での本番の変更は含めない。含めるには ADR と CLAUDE.md の改訂が要るので、別の PR で扱う」。
- /Users/tanizawashingo/worktrees/.salesanchor-tools/release-standing-prod-ops-delegation/docs/handoff/gas-viewer-fresh-fast/design.md:606: 2026-10-17 PO「n」（閲覧者の操作の GO は委任しない）。この PR はこれを広げる新しい PO の決定（2026-11-02）に基づく。
- /Users/tanizawashingo/.salesanchor-tools/scripts/dev/perm-change.py:42: 自動の安全判定の許可の行（user-automode-allow）は道具では「外す」だけ。足すのは PO の `!` 実行。

## 実測（【事実】・根拠 ~/CC報告ファイル-keep/autonomy-inventory/20261102.md）
- 2026-10-26〜11-02 に自動の安全判定が止めた操作 約50件のうち、本番サーバー上の書き込み・停止は 7 件（Remote Shell Writes 6・Interfere With Workloads 1）。すべて PO の `!` 実行が要った。
- 同じ期間に許可の行を足した2件（shingo-ops 名義の Approve・クラウドの担当の起動）は、足した後の止まりが 0 件。
- 期限付きの同じ形の許可 FNT-1・FNX-1 は、2026-11-02 の週次点検で期限切れのため外した（~/CC報告ファイル-keep/consent-weekly/20261102-changes-analysis.md）。

## 【未確認】
- 7 件のそれぞれが、その時点で審査済みの作業手順に書かれていたか（会話記録を Bash で数えると見張りが止めるため未集計）。委任後は ADR-1003 追記の条件6の記録で毎回確かめる。
