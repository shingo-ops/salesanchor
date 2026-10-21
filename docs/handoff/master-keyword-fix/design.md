# design: 共用マスタの語の修正（A7 は別便）

関連: [recon.md](./recon.md) / [README.md](./README.md) / ADR-155（docs/adr/ADR-155-product-master-ssot-csv-app.md）/ ADR-1020（docs/adr/FEATURE-INDEX.md:19）/ 前例 docs/handoff/deckbuild-master-fix/README.md

## KGI
同じ投稿文で、取り違え 0・悪化 0 のまま、今は当たらない 8 行が当たり、迷っていた 2 行が確定する（シミュレーション値。recon.md §5）。

## 方法（How）
語の追加のみ。既存行は触らない。1 本のトランザクションで「照合 → 変更 → 再照合 → audit_log → COMMIT」。照合が 1 つでも外れたら例外で全部戻る。dryrun.sql は同じ本体で最後だけ ROLLBACK。

## 触るファイル / 触らない範囲
- 触る: docs/handoff/master-keyword-fix/ の gen_sql.py・precheck.sql・dryrun.sql・apply.sql・postcheck.sql・README.md・recon.md・design.md（新規・docs のみ）
- 触らない: backend/・frontend/・migrations/・.github/、A5（ゴールデンボックス）、A7、424595

## 受け入れ基準
| 基準 | 検証方法 |
|---|---|
| 変更前の値が README の表どおり | precheck.sql が OK (before) を商品ごと・作品ごとに出す |
| 変更が追加のみ | dryrun 出力で OK (after) の件数一致、既存行の id / position が不変 |
| 失敗時は何も残らない | dryrun 後に postcheck.sql を流し、値が変わっていないこと |
| 対象外の商品が動かない | touched = 5 の確認が DONE 行に出る |
| 監査が残る | apply 後に audit_log が 商品 5 行 + type_master 1 行 |
| 悪化 0 | recon.md §5 のシミュレーション（実行前）＋再解析後の差分確認（別便） |
| 文書に削除文がない | `grep -ci delete docs/handoff/master-keyword-fix/*.sql`（対象は *.sql）が全 0 |

## 外部・過去事例
- 前例: docs/handoff/deckbuild-master-fix/（直接 SQL・dryrun・precheck/postcheck の型）
- 外部事例（検索辞書への語追加を、照合付き・同一トランザクション・事前試走で行う運用は一般的な変更管理の型）。数値を伴う外部事例の調査はこの変更の規模（語 9 個）では行わない。

## 弊害
- 除外語「4周年」「四皇」等で、将来の正しい投稿が外れる可能性。シミュレーション 1498 文では悪化 0。母集団外（30 日より古い行）は未検証。
- 作品 8982 の型番だけ当てを有効にすると、名前が当たらない投稿が型番で当たる。シミュレーションで増えたのは意図した行のみ。
- SQL はローカル DB で未実行。本番 dryrun が最初の実行確認。

## 計画票
1. 本 PR をマージ（docs のみ）
2. PO が dryrun 台本を実行 → 出力を確認
3. PO が commit 台本を実行（dryrun と同じ sha のときだけ進む）
4. 再解析（別便）
5. A7（別便）

## 継続
語の追加は台帳（audit_log）に残る。次回以降の語追加も同じ型（gen_sql.py の表に足す）。rollback と再解析台本は別便の TODO。
