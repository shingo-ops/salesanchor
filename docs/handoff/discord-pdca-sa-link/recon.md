# recon — discord-pdca-sa-link

**仕事名**: discord-pdca-sa-link
**日付**: 2026-10-26
**対象ADR**: ADR-1039, ADR-114
**担当**: Sonnet（設計者の指示書 docs/handoff/discord-pdca/bin2b2-sa-link-card.md に基づく）

## file:line 引用表

| 引用先 path:line | 確認内容 |
|---|---|
| `scripts/git-safe.sh:56` | 追加した git_safe_link_ok の定義 |
| `scripts/disk-janitor.sh:307` | 追加した dj_link_known の定義（R2 が使う） |
| `scripts/reaper-worktree.sh:115` | 追加した SKIP_LINK の入れ物（部屋ごとの確かめ） |
| `scripts/new-worktree.sh:65` | REAPER_SCRIPT を自分と同じ置き場から決める |

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|---|---|---|
| 1 | 偽の置き場の作り方（worktrees を写さない） | rsync --exclude で再現し印ファイルで対照 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
