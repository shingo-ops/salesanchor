# recon: 文書・説明文・テストの仕入元名を仮名に置き換える（社外秘・10社）

基準: origin/main 199b7dbe4（再スキャン時点）。スキャン手順は /tmp/CC報告ファイル/supplier-names-scan/scan.sh と同じ（`git grep -n -F`、inventory_aggregation fixture は除外）。

## 既存 ADR の検索

- `docs/adr/` を「仮名」「匿名」で検索 → 該当する方針 ADR なし（ADR-143・ADR-SA-17 は無関係）。
- 関連: ADR-099（在庫モデル。文中の実データ例に仕入元名が出ていたため本 PR で置換対象）。

## 現在地（ヒット件数）

全体ヒットは 123 行（先行スキャンの hits.tsv と同数・差分なし）。

| 区分 | 行数 |
|---|---|
| 提供者G（対象外。migrations・locales 以外） | 49 |
| migrations/（対象外） | 9 |
| frontend/src/locales/（対象外） | 4 |
| 対象（A〜F・H〜K の10社） | 61 |

合計 49+9+4+61=123。対象 61 行の内訳（ファイル別・仮名ごとの行数）:

| 区分 | ファイル | 行数 |
|---|---|---|
| K-doc | docs/ 配下 17 ファイル | 43 |
| K-code-text | backend/app/services/tcg_line_import_svc.py:87（提供者I） | 1 |
| K-test | backend/tests/test_tcg_line_import.py（提供者I） | 9 |
| JSON | docs/handoff/design-system-recon/evidence-20260910/ay2j-oneline.json（提供者I） | 8 |

## 対象外とその理由

- 提供者G のすべて: 画面に店名として表示している買取店のため。
- migrations/ のすべて: 適用済み SQL は書き換えない。
- frontend/src/locales/: 画面の表示文言。
- git の履歴: 書き換えない（過去の履歴には実名が残る）。

## 個別判断

- 提供者I の複合名（姓 名）は、姓を「提供者I」に、名を汎用の「太郎」に置換して「提供者I 太郎」とした（スペース含む複合名の先頭一致という test_split_sender_multiword_master_name の意図を維持するため。実名の名の部分は残さない）。文書中の同名は「提供者I」のみ。
- 提供者C・提供者E は、行内で姓に名が続く完全な氏名として出ていたため、氏名全体を仮名にした（姓だけを置換すると名が残るため）。
- 範囲外として置換しなかったもの（マッピングに無い語。実名は書かない）: 他の仕入元の名前、提供者F の担当者の氏名、提供者G と同じ行にある G の名前。別途 PO 判断が必要。
