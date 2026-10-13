# Inventory Aggregation Fixtures

PR-2' のゴールデンテスト用 fixture 置き場。

- `ver41_output.csv`: 正規化済みオファー入力
- `ver41_aggregation.csv`: 集計後の期待値
- `notetrack_output.csv`: note-track 検証用の正規化済みオファー入力
- `notetrack_aggregation.csv`: note-track 検証用の集計後期待値

ver4.1 の実 export をもとに、仕入元名を仮名（提供者A…）に置き換えて配置している（社外秘のため、2026-10-13）。
ゴールデンテストは fixture が存在すれば自動で実行される。
