# 入口に決まりを足す前に


> この節は入口から写した決まり（doc-agenda-nav 段3b）。節の中の「このファイル」は入口の AGENTS.md を指す（段3c で本文の正本を CLAUDE.md から AGENTS.md へ移した）。

以下に順番に答える:

1. CI / ESLint / Husky が既に強制しているか？ → YES: **書かない**（CSS変数・アイコン・デザイントークン規約はこれ）
2. `frontend/` だけに関係するか？ → YES: **`frontend/AGENTS.md`** に追加
3. `backend/` だけに関係するか？ → YES: **`backend/AGENTS.md`** に追加
4. frontend と backend 両方に等しく関係するか？ → YES: **このファイル** に追加（不可逆操作・ブランチ運用 等）
5. Generator / Evaluator / Reviewer の動作手順か？ → YES: **`~/.claude/agents/`** の該当ファイルに追加
6. `~/.claude/rules/` に同等の内容が既にあるか？ → YES: **書かない**（Git workflow・coding-style 等）
7. 全セッションで Claude が知る必要があるか？ → NO: **書かない**（ADRリンクか docs/ 参照で十分）
8. 上記をすべて通過した場合のみ追加。既存セクションへの統合を最優先（新セクション追加は最後の手段）。
**入口の AGENTS.md が 80 行、CLAUDE.md が 10 行、この目次が 60 行を超えたら `frontend/scripts/check-claude-size.js` がコミットをブロックする。**
