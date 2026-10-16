# AY-5d 設計: UIガバナンス検出種別の説明を5種に揃える
- 目的: 検出は5種なのに説明が3種のまま残り、読んだ人・AIが checkbox と radio も止まることを知らない状態を無くす。
- 根拠: recon.md、ADR-144、AY-4d（#4360）・AY-5b（#4375）で checkbox・radio を追加。
- 対象: 3行の文字置換（yml:3 コメント、BRANCH_PROTECTION_SETUP.md:314、CLAUDE.md:119）。動作・CI判定は変えない。
- 対象外: docs/handoff/ 配下、check-ui-governance.js 本体。
- 代替案: CC_UI_GOVERNANCE.md への参照だけにして列挙を消す → CLAUDE.md は常時読み込みのため列挙を残す方が誤りにくい。不採用。
- リスク: CLAUDE.md の行数超過 → 同じ行内の置換で行数120を維持。
- 切り戻し: merge commit を revert。
- 維持の仕組み: 種別の正本は docs/CC_UI_GOVERNANCE.md の表。種別を増やすときは本3か所も同時に直す（ADR-144 追記節に従う）。
- 外部事例: 不要（文書の文言修正のみ）。
## 受入条件
|基準|検証方法|
|---|---|
|3か所すべてに checkbox と radio が入る|git diff で各1行置換|
|旧列挙「生select/生input/自作タブ」が CLAUDE.md・.github・BRANCH_PROTECTION_SETUP.md で0件|git grep|
|CLAUDE.md が120行のまま|wc -l|
|CI 必須チェックが全て緑|gh pr checks|
## 審査
Opus 自己審査: APPROVE（変更は文字のみ、根拠は recon の行番号で確認済み）。
