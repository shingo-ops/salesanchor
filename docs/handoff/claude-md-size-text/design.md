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

## 外部・過去事例の参照と我々への応用
該当なし（文言の誤り修正で、方式の選択がないため）。

## 戻し方
このPRを revert。

## 維持の仕組み
上限値は frontend/scripts/check-claude-size.js:23 が正本。pre-commit（frontend/.husky/pre-commit:52）と CI（.github/workflows/check-claude-size.yml:40）が超過を検査する。記述側の値の再ズレは今回の修正後も自動検出されない（新規の仕組みは追加しない。範囲外）。
