branch: release/line-auto-export-app-trigger

| ブランチ名 | 担当機能エリア | 開始日時 | 状態 | PR# | main | 備考 |
|-----------|--------------|---------|------|-----|------|------|
| release/line-auto-export-app-trigger | LINE自動書き出しの定期実行（Termux job 4203 の中身をADB操作からアプリへの合図へ／平常時は4203を停止） | 2026-10-08 14:21 | IN_PROGRESS | 4060 | | base=origin/main・tools/line-auto-export のみ・PO決定2026-10-09で平常時は4203を登録しない（緊急手段としてのみ残置）・3時間見張りはPR #4061（job 4201・通知id 4205）へ移設 |
