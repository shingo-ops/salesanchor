# 実装カード — ロール画面の配置の直し

| 項目 | 内容 |
|------|------|
| ブランチ | `release/role-page-layout`（push 済み。docs の commit が先頭にある） |
| 設計 | `docs/handoff/role-page-layout/design.md`（§3 が変更の全部） |
| 実装の承認 | PO 2026-11-08「修正してくれ」＋常時委譲（設計者 Opus／実装 Sonnet） |
| 範囲 | 画面だけ。API・DB・処理の中身は触らない |

## 手順

1. `bash scripts/new-worktree.sh release/role-page-layout` を流す。
2. `cd /root/worktrees/salesanchor/release-role-page-layout && git switch -C release/role-page-layout origin/release/role-page-layout` を流す。
3. 作業前点検 `executor-preflight.sh` はクラウドでは流さない（Opus が手元で流し済み）。
4. design.md §3-1〜§3-6 をそのとおりに入れる。§2「変更しない」に書いた所は触らない。
5. `cd frontend && npm ci`（未導入なら）→ `npx tsc --noEmit -p .` → `npx eslint src/pages/roles` → `npm run check:all`（無ければ package.json の check:* を全部）→ `npx vitest run src/pages/roles src/components/SubMenu` を流す。生の出力を `docs/handoff/role-page-layout/impl-checks.txt` に保存する。
6. 全部緑なら1つの commit にして `git push origin release/role-page-layout`。commit の文の最後は `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`。

## 止まる条件（推測で進めない）

- design.md の変更前の行が、実物と食い違う。
- 検査が1つでも赤で、直し方が design.md の範囲に無い。
- `SubMenu` の型が design.md §3-1 の書き方を受け付けない。

止まったら、何が・どの行で・生の出力を書いて `BLOCKED:` で終える。終わったら `DONE` と commit の番号を書く。
