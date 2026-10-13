# design: 受信時刻の修正マイグレーションから is_current の決め直しを外す

設計者: Opus（2026-10-13）。参照するもの:
- 現状の調査: [recon.md](/docs/handoff/received-at-migration-no-current/recon.md)
- ADR: docs/adr/ADR-158-product-level-supersession.md、ADR-155（マイグレーションは構造変更のみ）
- 前の便: docs/handoff/v102-same-post-rows/design.md（#4169）

PO の決定（2026-10-13）：「その作業ファイルから『表示する行を決め直す』部分だけを削る修正を、新しい PR として出してよいですか？」に「y」。

## 1. 目的
デプロイのたびに、is_current が #4169 より前の決め方（組ごとに1行）に戻るのを止める。在庫一覧に、同じ投稿の同じ商品の行がデプロイの後も全部出続けるようにする。

## 2. 対象と対象外
- 対象
  - migrations/20260929_120000_fix_source_messages_received_at.sql の :11-30（is_current の UPDATE）
  - この docs
- 対象外
  - 同じファイルの :6-9（received_at をそろえる UPDATE）。PO の決定は「表示する行を決め直す部分だけ」。今変える行は0行（recon §2）。
  - `_merge_supplier_products`（正本。変えない）
  - 他のマイグレーション、run_all_migrations.sh、deploy.yml

## 3. 変更前と変更後
- 変更前（:11-30）: `WITH ranked AS (... ROW_NUMBER() ... = 1 ...) UPDATE public.analysis_results ... SET is_current = ...`
- 変更後: その文を消し、前例（#4017）と同じ形のコメントを1つ残す。
  - `-- NEUTRALIZED (ADR-158 / ADR-155, 2026-10-13): is_current の決め直し（組ごとに1行）を外した。2026-09-29 の一度きりの役目は終わり、今の正本は backend/app/services/tcg_analyzer_svc.py の _merge_supplier_products（同じ投稿の組の行をすべて TRUE）。デプロイのたびに流れて古い決め方に戻していた（#4169 の後 2026-10-12 19:51Z に20組が戻った）。`
- 冒頭のコメント :2「ADR-158 の is_current を正しい投稿順で選び直す。」は、上の NEUTRALIZED のコメントを見るよう1行で書き換える。

## 4. 代替案と選んだ理由
| 案 | 中身 | 理由 |
|---|---|---|
| A（採用） | :11-30 を外す（neutralize） | 一度きりの役目は済んでいる。決め方の正本がコード1か所に戻る（SSOT）。ADR-155 の前例と同じ形 |
| B | :11-30 を #4169 と同じ投稿単位の SQL に書き換える | 決め方を SQL とコードの2か所に持つことになり、SSOT に反する。今後コードを変えるたびに、ここもずれる |
| C | ファイル全体を外す | PO の決定（決め直しの部分だけ）を超える |

## 5. 影響範囲
- デプロイのマイグレーション段（run_all_migrations.sh:846）で、is_current を書き換えなくなる。
- is_current を書くのは `_merge_supplier_products` だけになる（解析・解析し直しのたび）。
- 本番の今の値は、このマイグレーションでは直らない。デプロイの後で、直近48時間の投稿を解析し直して付け直す。

## 6. リスクと対処
- R-a: received_at が今後そろわない行が出たとき、is_current が自動では決め直されない。
  → 今の対象は0行（recon §2）。received_at を書く経路は #3845 で直っている。もし出た場合は、その投稿を解析し直すと `_merge_supplier_products` が付け直す。
- R-b: CI の migration-guard（値の書き込み検査）。neutralize は通る作りになっている（check-migration-value-writes.py:9-10）。

## 7. 受入条件と検証方法
| 基準 | 検証方法 |
|---|---|
| U1 ファイルから is_current の UPDATE が無くなる | `grep -c is_current` で、コメント以外に UPDATE が無い。:6-9 は変わらない（git diff で確認） |
| U2 CI が全部通る | PR の必須チェックが緑（migration-guard・migration-test の全件ドライランを含む） |
| U3 デプロイの後、解析し直すと戻る | デプロイ後、直近48時間を解析し直し、「同じ投稿の同じ組で TRUE が一部だけ」の組が 0 |
| U4 次のデプロイでも戻らない | 次に main へ入る別の PR のデプロイの後、同じ数えを取り直して 0 のまま。updated_at がデプロイ中の時刻の行が増えていない |

## 8. 外部・過去事例の参照と我々への応用
- 外部事例は使いません。このリポジトリが毎回すべてのマイグレーションを流し直す作りに固有の問題で、比べられる公開の実測がありません。
- 過去事例: #4017・#4023（値を書くマイグレーションの neutralize）。同じ形で外します。

## 維持の仕組み
- 守り手: CI（.github/workflows/migration-guard.yml の値の書き込み検査 scripts/check-migration-value-writes.py）
- 新しいマイグレーションで analysis_results の値を書くことは、ADR-155 で禁止されています。is_current の正本は `_merge_supplier_products` の1か所です。

## 10. 審査（Opus による自己審査。独立した第二者のレビューではありません）
- 判定: APPROVE。
- 照らし合わせたもの
  - ADR-158:26 → 正本のコードが ADR に沿っている。古い SQL を外すだけ。
  - ADR-155 → neutralize の前例と同じ形。
  - SSOT → 決め方が1か所になる。
- 未解決: なし。U4 は次のデプロイを待って確かめる。
