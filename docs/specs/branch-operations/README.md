# branch operations spec

> worktree / PR / merge の正本。入口は1つ、例外は記録付きで扱う。

---

## 1. 目的

複数ターミナル・複数 worktree でも、作業開始・記録・push・merge の手順を1本化する。

---

## 2. 基本方針

- 作業は worktree から始める
- 占有状況は `active-work.md` を見る
- 共有台帳の更新は手作業で重複させない
- gate に止められたら、こじ開けずに止まる

---

## 3. worktree / active-work

### 3-1. worktree の前提

worktree はエージェントごとの個室として扱う。1 ブランチ = 1 worktree を守る。

### 3-2. 台帳

進行中の作業は `.claude-pipeline/active-work.md` に残す。worktree 作成時は自動登録を前提にする。

### 3-3. 標準入口

作業開始は `bash scripts/new-worktree.sh <branch>` から行う。手で worktree を組み立てず、この入口を起点にする。

---

## 4. 参照

- [docs/handoff/branch-operations/worktree-guardrail-close-recon.md](/Users/tanizawashingo/salesanchor/docs/handoff/branch-operations/worktree-guardrail-close-recon.md)
- [docs/PARALLEL_TERMINAL_GUIDE.md](/Users/tanizawashingo/salesanchor/docs/PARALLEL_TERMINAL_GUIDE.md)
- [docs/adr/ADR-086-parallel-development-standardization.md](/Users/tanizawashingo/salesanchor/docs/adr/ADR-086-parallel-development-standardization.md)
- [scripts/new-worktree.sh](/Users/tanizawashingo/salesanchor/scripts/new-worktree.sh)
