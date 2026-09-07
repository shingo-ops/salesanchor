# データ保全（data-durability）

この文書は何か（専門用語なしの1行）: 商売のデータが消えないようにする仕組みと、消えたときに元に戻す手順をまとめた表紙。

## 子文書

- [ideal-state.md](ideal-state.md) — あるべき姿（POの言葉のみ・正本）
- [kgi.md](kgi.md) — 合格条件を数で書いたもの
- [../../handoff/data-durability-spec/recon.md](../../handoff/data-durability-spec/recon.md) — 2026-09-01 時点の現状調査
- [../../handoff/data-durability-spec/design.md](../../handoff/data-durability-spec/design.md) — 起票便の設計記録
- [../../adr/ADR-153-data-durability.md](../../adr/ADR-153-data-durability.md) — 独立テーマ化と目標値の設計判断
- [../../handoff/data-durability-design/design.md](../../handoff/data-durability-design/design.md) — 技術手段の設計（4工程・道具選定）

## このテーマが扱うもの

- 営業データ（リードから受注まで）の複製をどこに何本持つか
- 壊れたときに、いつの時点まで、どれだけの時間で戻すか
- 戻せることを定期的に確かめる演習
- 失敗したときに人へ知らせる仕組み

## このテーマが扱わないもの

- ディスクの空き容量を増やすためのゴミ掃除（docs/specs/server-resource-optimization/ が担当）
- 鍵・権限そのものの台帳管理（docs/specs/secrets-permission-ssot/ が担当。保管先としての接点のみ本テーマで扱う）

## 状態

あるべき姿・KGI承認済（2026-09-01）。recon 済（不明点3件が未解消）。技術手段の design 済（2026-09-02）。実装は未着手。
