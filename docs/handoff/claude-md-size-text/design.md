# design: CLAUDE.md 行数上限の記述を実際の値に合わせる

recon: docs/handoff/claude-md-size-text/recon.md ／ 対象ADR: ADR-076

## 目的
CLAUDE.md の記述と check-claude-size.js の実際の上限（120）を一致させる。

## 変更前後（CLAUDE.md:117 の1行のみ）
- 前: `**ファイル全体が 90 行を超えたら ...`
- 後: `**ファイル全体が 120 行を超えたら ...`

## 触らない範囲
frontend/scripts/check-claude-size.js、他の CLAUDE.md、CLAUDE.md の行数（120のまま）。

## 検証
|基準|検証方法|
|---|---|
|CLAUDE.md の記述が 120 行|`grep -n "120 行を超えたら" CLAUDE.md`|
|行数が 120 のまま|`wc -l CLAUDE.md`|
|check が PASSED|`node frontend/scripts/check-claude-size.js`|

## 外部事例
該当なし（文言の誤り修正で、方式の選択がないため）。

## 戻し方
このPRを revert。
