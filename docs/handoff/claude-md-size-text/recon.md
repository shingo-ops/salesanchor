# recon: CLAUDE.md 行数上限の記述ズレ

## ADR 検索結果
- `git grep -n -i "check-claude-size" docs/adr/` の該当は docs/adr/ADR-076-claude-md-hierarchy.md:44, :86, :87, :95, :96 のみ（サイズチェックの構成の記述。上限値の記述なし）。
- `docs/adr/FEATURE-INDEX.md` で `claude-size` / `CLAUDE.md` を検索した該当は :4 のみ（索引の説明文。該当 ADR なし）。
- 対象 ADR: ADR-076（docs/adr/ADR-076-claude-md-hierarchy.md）。

## 事実（file:行）
- /Users/tanizawashingo/salesanchor/CLAUDE.md:117（旧文言）: `**ファイル全体が 90 行を超えたら `frontend/scripts/check-claude-size.js` がコミットをブロックする。**`
- /Users/tanizawashingo/salesanchor/frontend/scripts/check-claude-size.js:23: `{ path: 'CLAUDE.md', limit: 120 },`
- /Users/tanizawashingo/salesanchor/frontend/.husky/pre-commit:52: `node "$REPO_ROOT/frontend/scripts/check-claude-size.js"`
- /Users/tanizawashingo/salesanchor/.github/workflows/check-claude-size.yml:40: `run: node scripts/check-claude-size.js`
- `wc -l CLAUDE.md` = 120。

## 経緯（git log の事実のみ）
- be4646944（2026-05-27）fix(ci): ルートCLAUDE.mdのサイズ上限を実際に強制する（120行）
- f43faefaa（2026-07-18）docs: trim blank line in CLAUDE.md (121->120) to satisfy size check

生出力: /tmp/CC報告ファイル/claudemd-size-recon-raw.txt
