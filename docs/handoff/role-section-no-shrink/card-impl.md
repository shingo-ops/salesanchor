# 実装カード — ロール画面の表の区切りがつぶれる不具合

| 項目 | 内容 |
|------|------|
| ブランチ | `release/role-section-no-shrink`（push 済み。docs の commit が先頭にある） |
| 設計 | `docs/handoff/role-section-no-shrink/design.md`（§3 が変更の全部） |
| 実装の承認 | PO 2026-11-08「権限の表だけがスクロールするようにすること」＋常時委譲（設計者 Opus／実装 Sonnet） |
| 範囲 | `frontend/src/pages/roles/RolesPage.css` の1行だけ |

## 手順

1. `bash scripts/new-worktree.sh release/role-section-no-shrink` を流す。
2. `cd /root/worktrees/salesanchor/release-role-section-no-shrink && git switch -C release/role-section-no-shrink origin/release/role-section-no-shrink` を流す。
3. design.md §3 のとおり `.role-perm-section` の先頭に `flex-shrink: 0;` を足す。
4. `cd frontend && npm ci` → `npm run generate:api-types` → `npx tsc --noEmit -p .` → `npm run check:all` → `npm run test:unit`。生の出力を `docs/handoff/role-section-no-shrink/impl-checks.txt` に保存する。
5. 全部緑なら1つの commit にして push。commit の文の最後は `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`。

## 止まる条件

- `frontend/src/pages/roles/RolesPage.css:48-52` が design.md §3 の変更前と違う。
- 検査が1つでも赤。

止まったら `BLOCKED:` と理由・生の出力。終わったら `DONE` と commit の番号。
