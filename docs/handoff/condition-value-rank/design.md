# design: 状態の価値順（condition value rank）

起案: Opus（Planner）2026-10-17。審査: Opus（Architect・同一AIの自己審査）APPROVE。recon: ./recon.md。ADR: ADR-1023。

## 目的（PO の言葉）
- 「状態は悪いものから優先的に採用するように出来る？」
- 「状態全体の順位を調整する列を新設することは出来る？BoxはSealed box>Damaged sealed box>No shrink box>Opened boxの価値順なので価値の低いものの検索ワードが含まれる場合は価値の低い順番に割り当てをする」
- 「Unsearched pack>Searched pack>AR confirmed pack」
- 「Sealed box > Damaged sealed box > No shrink box  > Opened box > Searched box」

例: 「シュリンク無し美品」は「美品」（Damaged sealed box）と「シュリンク無し」（No shrink box）の両方に当たる。今は並びが先の Damaged sealed box になる。価値の低い No shrink box を採るようにする。

## 対象と対象外
- 対象: v102 の状態の判定（`_resolve_condition`）、状態マスタの列 2 つ、値を入れる記録 SQL。
- 対象外: v102 以外の経路（v6・v10・単位の復元・道具）、検索語の変更、管理画面での表示・編集（別便）。

## 変更前後
| 項目 | 前 | 後 |
|---|---|---|
| マスタ | priority のみ | `value_group`（box/case/pack、NULL=対象外）・`value_rank`（1=価値が高い）を追加 |
| 判定（v102） | 並びで最初に当たった行 | 当たった行が全部同じ群なら value_rank が一番大きい行。群をまたぐ・NULL を含む→今と同じ |
| 判定（他の経路） | 今のまま | 今のまま（引数の既定 False） |
| 値が空のとき | — | 今と同じ結果（コードの反映と値の投入を分けて測れる） |

## 値（記録 SQL で入れる。migration には書かない＝ADR-1007）
- box: CN0003 Sealed box 1・CN0004 Damaged sealed box 2・CN0005 No shrink box 3・CN0006 Opened box 4・CN20261008072213 Searched box 5
- case: CN0001 Case 1・CN0002 Damaged case 2・CN0009 Opened case 3
- pack: CN0007 Unsearched pack 1・CN0010 Searched pack 2・CN0013 AR confirmed pack 3
- NULL: Empty box・FLAG_SINGLE・Error・Bulk・空箱 Case

## 代替案
- A. 検索語から「美品」を外す: PO の 2026-10-08 の決定（美品＝傷あり）を覆すため不採用。
- B. priority の並びを入れ替える: priority は R1〜R4 の規則の段を兼ねていて、入れ替えると別の判定が変わるため不採用。
- C. 価値順の列（採用）: 既定 NULL で今と同じ、v102 だけに効かせられる。

## リスクと対処
- 反映の順番（アプリが先、migration が後）: 列が無い DB では列を読まない（information_schema で確かめる）。
- 他の経路への波及: 引数の既定を False にし、v102 の 2 か所だけ True。
- 再解析の副作用: 対象の job だけ再解析し、前後で現行行の数・状態・単位を数える。

## 受入条件
| 基準 | 検証方法 |
|---|---|
| K1 既定（False）の結果が今と同じ | 既存テスト全合格・列なし entries で True/False 同一のテスト |
| K2 v102 で「シュリンク無し美品」が No shrink box | 単体テスト（共通関数・v102 の両方） |
| K3 群またぎ・対象外は今と同じ | 単体テスト |
| K4 列が無い DB でも動く | load_condition_entries の 2 経路のテスト |
| K5 migration は構造だけ・view に列が出る | migration 全文・CI migration-guard |
| K6 反映後、値の SQL と再解析で対象の行だけが変わる | 本番の前後測定（data/ に記録） |

## 戻し方
- 値: `data/value_rank_rollback.sql`（11 行を NULL に戻す）→ 今の判定に戻る。
- コード: PR を revert。列は残っても害が無い（NULL）。

## 維持の仕組み
- テスト（TestResolveConditionValueRank）が規則を固定する。
- 状態を足すときは、群と順位を決めて値を入れる（便2 で管理画面から編集できるようにする）。

## 外部事例
- 該当なし。社内の状態マスタの判定順の規則で、外部の事例が判断材料にならないため。
