# Opus 審査記録 — review-edit-all-fields（便1）

同じ AI（Claude Opus）による審査。独立した第三者のレビューではない。

## 設計審査
- 1回目は REVISE。指摘は design.md §13 に反映した。
- 2回目は APPROVE（2026-10-15）。

## コード審査（対象 5283ce65f..957424fe9）
- 結論は REVISE。必須の修正は1件（M1）。
  - M1: `frontend/api-contract/openapi.json` を手元の pydantic 2.13.0 / Python 3.14 で出力していた。
  - 直した内容: fa842d40f で、固定版の pydantic 2.10.6 / Python 3.12.8 を使い、CI と同じ `python -m tools.export_openapi` で出し直した。
  - 確かめたこと
    - 5283ce65f と比べて、足した行は139行、消えた行は0行だった。
    - 足されたのは route 2本と schema 2つだけだった。
    - origin/main を取り込んだあとに再出力しても、差は出なかった。
- 設計との一致: §3・§4・§9・§13 の各項目は一致していた。
- 設計との差として申告されたもの
  - (a) 単位の SQL を定数として共有した。妥当。
  - (b) Pre-order も「EXCLUDE 以外」に数え、〆の相手を止める。設計の status_available_by_human の定義と一致する。
  - (c) 一覧 API の PG 試験は無い。許容する。既存の PG 試験が fetch_analysis_results を通る。
- 安全面
  - 権限: 2本の API はどちらも super_admin だけが使える。
  - SQL: 値はすべてバインド変数で渡している。
  - 例外のときは rollback される。
  - migration は無い。
- tsc の4件のエラー
  - どれも origin/main と同じ中身で、今回の差分には入っていない。
  - `frontend/src/api/generated/` は git の管理外で、CI は tsc の前に作る。手元でだけ出るエラーである。
- 任意の指摘（便1では直さない）
  - O1: メモを空にすると、「修正」列は空の欄で表示される。
  - O2: メモの上限2000文字を、frontend と backend の両方に書いている。
  - O3: `review-item-fix__value` には CSS が無い。
  - O4: PG 試験の R2 は、間接的にしか確かめていない。
  - O5: マスタの表が無いときの advisory lock の扱い。
  - O6: "-0" を受け付ける。
  - O7: 同じ参照を2回呼んでいる。
- 試験
  - 新規の pytest: PG なしが76件、PG ありが8件、すべて合格。
  - vitest（tcg-analysis-review）: 合格。手元は負荷が高く、timeout を延ばして実行した。
  - eslint・i18n: 合格。
