# design — data-durability-spec（起票便）

この文書は何か（専門用語なしの1行）: データ保全というテーマを立てるにあたり、何を正本として残すかを決めた記録。

親（仕様書）: [../../specs/data-durability/README.md](../../specs/data-durability/README.md)
recon: docs/handoff/data-durability-spec/recon.md
対象ADR: ADR-153

## 1. この便の範囲

データ保全テーマの起票に限る。あるべき姿・KGI・ADR-153・recon を正本化する。
技術手段の設計と実装は含まない。

## 2. design（技術How）

本便で作る成果物は次の6点である。

| 成果物 | 内容 |
|---|---|
| docs/specs/data-durability/README.md | 表紙。扱うもの・扱わないもの・状態 |
| docs/specs/data-durability/ideal-state.md | あるべき姿。PO自筆の原文のみ |
| docs/specs/data-durability/kgi.md | KGI 8項目と3層の定義 |
| docs/adr/ADR-153-data-durability.md | 独立テーマ化と目標値の設計判断 |
| docs/handoff/data-durability-spec/recon.md | 2026-09-01 の実測記録と不明点8件 |
| docs/specs/README.md | 索引に1行追加 |

## 3. 弊害・トレードオフ

- テーマを独立させることで、サーバーリソース最適化テーマとの境界判断が毎回必要になる。README の「扱わないもの」で線を引いた。
- KGI に「10分前まで」を残したため、後段の design で本番データベースへの手入れが不可避となる。起票段階でこれを緩める選択も取り得たが、PO 自筆の言葉を薄めないことを優先した。
- recon の不明点8件を未解消のまま起票する。design に進む条件は満たしていないが、テーマの器を先に作らないと調査結果の置き場が無い。

## 4. 外部・過去事例

3-2-1ルール（コピー3つ・媒体2種・うち1つは離れた場所）を参照した。scripts/aws-setup/README.md で既にこの原則が引用されており、本テーマはその未達分を埋めるものである。

## 5. 受入基準

| 基準 | 検証方法 |
|---|---|
| あるべき姿がPO自筆の原文と一字一句一致する | ideal-state.md の該当行とチャット発話を目視照合 |
| KGI が8項目そろい、各行に合格ラインの数値がある | kgi.md の表を行数で数える |
| 索引から本テーマへ辿れる | docs/specs/README.md の追加行のリンク先が実在する |
| ADR-153 が docs/adr/ に実在する | ls で確認 |
| recon の file:line 引用先がすべて実在する | docs/handoff/data-durability-spec/recon.md を process-artifacts gate が照合する |

## 6. 維持の仕組み

- 守り手: .github/workflows/process-artifacts.yml
- 対象: 本テーマの正本（あるべき姿・KGI）が、PO承認を経ずに書き換わること
- 関所なしの場合: KGI 8 の「直近の演習が90日以内」を機械で見張る仕組みは未設計。当面は人手で守る。理由は演習の実施記録の置き場が未定のため。
