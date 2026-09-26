分類: 6-1
出所: （2026-07-20 本店掃除便で実測）
- `git checkout -- <file>` は作業ツリーのみ戻し、ステージ済み（index）の変更は戻さない。
  MM状態（staged+unstaged両方）のファイルは `git checkout HEAD -- <file>` で両方戻す。
  誤ると pull --ff-only が「local changes would be overwritten」で拒否され続ける（掃除便で5回連続拒否）。
