# ケースA 実機検証ノート

**目的**: 古い develop 地点から作られたブランチで、docs のみ変更した場合に
          GO を要求されないことを GitHub Actions で確認する。

**ブランチ構造**:
- ベース (gate-diff-3dot-verify): rebase 済み develop + 3点fix + workflow拡張
- この PR: docs のみ追加

**期待 CI 結果**:
`process-artifacts gate` → `✅ 書類のみの変更 — 自動スキップ（pass）`

**確認ポイント**:
- `scripts/reaper-worktree.sh` が changedFiles に含まれない（3点diff が正しく機能）
- GO が要求されない
