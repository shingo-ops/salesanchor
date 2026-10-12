---
mode: handoff
---
# design: 商品名を書いた〆で、前の在庫の状態を引き継ぐ（便3）

- 状態: 設計案・Opus 自己審査済み（§12。独立した第二者レビューではない）。PO 2026-10-11「確立したなら進める」（recon.md §1）。
- 参照: docs/handoff/v102-shime-direct-inherit/recon.md、docs/handoff/v102-shime-multi-targets/design.md（便2・規則11b）、docs/adr/ADR-158-product-level-supersession.md。

## 1. 目的と成功の判定
仕入元が「ガンダムGD01完売〆」のように商品名を書いて〆たとき、〆の行に状態（ケース・BOX・シュリンク有無など）が書かれていなくても、直前まで在庫に出ていたその商品の状態を完売にする。今は〆の状態が単位の既定（BOX など）になり、ケースの在庫が「在庫あり」で残る（recon.md §3-1）。

| KGI（○×） | 判定 |
|---|---|
| G1 新しい判定関数を保存済み解析結果の全件（S 880）に当てて、引き継ぐ件が recon.md §3-2 の 53 件と完全に一致（過不足 0） | §7 V2 の突き合わせ |
| G2 53 件の原文照合で誤り 0（済み）、反例2件（ボックス〆→パック在庫、シュリあり〆→シュリなし在庫）は引き継がない | V2 で2件が「引き継がない」 |
| G3 既存のテストが全て通り、便1/便2（matched_soldout_ref）の結果が変わらない | CI 全緑・V1 |
| G4 本番で商品名を書いた〆が来たとき、前の在庫行が is_current=FALSE になる | §7 V4 の本番観測 |

## 2. 規則（便2の規則1〜11b に足す。番号は続ける）
規則12（商品名を書いた〆の状態の引き継ぎ）。次を全て満たす件だけ、状態を引き継ぐ。
- 12a 件が完売: `status_effect == "excluded"` かつ `status == "Sold out"`。
- 12b 商品が直接決まった: `match_status in (matched, matched_context, matched_followup)` かつ `product_id` あり。すでに `soldout_targets` がある件（便1/便2）は触らない。人が商品を決めた件（fixed_products）は触らない。
- 12c 〆の状態が語で決まっていない: `condition_decided_by_word(condition_basis)` が False（`backend/app/services/gemini_raw_copy_v102_soldout_ref.py:33-40`、便2と同じ関数）。
- 12d 〆と同じ状態の在庫が前に無い: 同じ仕入元・前48時間（既存の読み込み窓）の投稿の在庫行（Sold out 以外）に、同じ商品で、〆の件の状態と同じ状態の行が無い。〆の件の状態は `condition`（未解決・空は `FLAG_SINGLE`）で比べる。
- 12e 取り残しの状態がちょうど1種類: 同じ商品について、状態ごとに「その状態の行（在庫・完売を問わない）がある最も新しい投稿」を見て、そこに在庫行がある状態を「取り残し」とする。取り残しの状態が1種類のときだけ、その状態を引き継ぐ。参照はその投稿のその状態の在庫行（行番号が最小のもの）。〆と同じ投稿の他の件（同じ商品）は、その状態を「より新しい行」として扱う（取り残しにはしない）。
満たせば、件に `soldout_targets=[{product_id, condition_id, ref_message_id, ref_line}]` と `soldout_target_basis="SOLDOUT_INHERIT"` を載せる。書き込み段は便2の `_apply_soldout_targets` がそのまま状態を上書きする（人の判断がある件は上書きしない）。

## 3. 変えない範囲
- 便1/便2 の規則・`decide_soldout_ref`・`build_ref_rows`・`_targets_of`・`_narrow_by_condition`。
- `StockItem` とその読み込み `_STOCK_ITEMS_SQL`（便2が使う在庫の中身は変えない）。
- 配信 SQL・ADR-158 のマージ・migration・画面（フロントエンドは触らない）。
- 表・列の追加なし（`analysis_results` の既存列だけを書く。正本は1か所のまま）。

## 4. 便3: コード（migration なし）
### 4-1. backend/app/services/gemini_raw_copy_v102_soldout_ref.py（純粋関数）
- `SoldItem(product_id: int, condition_canonical: str)` を追加（frozen dataclass）。
- `SoldoutRefPost` の末尾に `sold_items: tuple[SoldItem, ...] = ()` を追加（既定値つき＝既存の生成箇所・テストは変わらない）。
- `decide_soldout_inherit(extracted, posts, fixed_products) -> dict[int, SoldoutTarget]` を追加。規則12a〜12e。投稿の新旧は `posts` の並び（新しい順、`load_soldout_ref_posts` の順）で決める。
- 定数 `SOLD_OUT_STATUS = "Sold out"`・`CONDITION_BASIS_SOLDOUT_INHERIT = "SOLDOUT_INHERIT"`・`FLAG_SINGLE = "FLAG_SINGLE"` はこのファイルに置く（同じ値が既にあるなら import して使い、二重定義しない。実装役が `git grep` で確認）。
### 4-2. backend/app/services/line_analysis_v102_svc.py（読み込み）
- `_SOLD_ITEMS_SQL` を `_STOCK_ITEMS_SQL`（:893-905）の隣に追加。同じ「各投稿の最新 job」の結合で、条件だけ `ar.status = :sold_out`、列は product_id・condition_canonical。
- `load_soldout_ref_posts`（:876-890）で各投稿に `sold_items` を足す。
### 4-3. backend/app/services/gemini_raw_copy_v101.py（差し込み）
- `_extract_v102` の `if soldout_posts:`（:1321-1325）の中、`_apply_soldout_ref(...)` の直後に `extracted = _apply_soldout_inherit(extracted, soldout_posts, fixed_products)` を足す。
- `_apply_soldout_inherit` は決まった件に `soldout_targets`（1件）と `soldout_target_basis` を足した新しい dict を返す（元の dict は変えない）。
### 4-4. backend/app/services/line_analysis_v102_svc.py（書き込み）
- `_apply_soldout_targets`（:690-712）の :707 の `CONDITION_BASIS_SOLDOUT_REF` を `item.get("soldout_target_basis") or CONDITION_BASIS_SOLDOUT_REF` にする。他は変えない。

## 5. 代替案と選んだ理由
| 案 | 内容 | 採否と根拠 |
|---|---|---|
| A 素朴 | 語で決まらなければ前の在庫の状態を引き継ぐ | 不採用。原文照合で誤り2件（recon.md §3-2） |
| B 書き込み段で判定 | `_write_results` で在庫を読み直して判定 | 不採用。抽出段に入れれば `prompt_ab_recompute` で書かずに確かめられる。便2と同じ「抽出段で載せて書き込み段で適用」の型に合わせる |
| C 採用 | 規則12（12d・12e で絞る） | 53件・誤り0・反例2件は引き継がない |
| D 直前の投稿だけを見る | 時刻で直前の1投稿 | 不採用。間に関係ない投稿が挟まる〆が実在（opus-verify 記録、24〜38時間前） |

## 6. 弊害とリスク
| # | 弊害 | 対策 |
|---|---|---|
| R1 | 状態の比較を canonical の文字で行う（測定は condition_id）。1対1でなければずれる | V2 で 53 件と過不足 0 を確認してからマージ |
| R2 | 在庫の読み込みは `pid_resolved=TRUE` と状態ありの行だけ（測定は商品ありの全行） | V2 で差が出たら停止して報告 |
| R3 | 過去48時間の完売の行を追加で読む分、1投稿あたりの SQL が1本増える | 既存の在庫 SQL と同じ索引経路。測定は V3 |
| R4 | 書き換え後の (商品,状態) の組が変わり、元の組の在庫の is_current も付け直される | 既存のやり直し経路（`_load_resolved_pairs` :805-822）が前の組を拾う。PG テストで確認（V1） |
| R5 | 引き継いだ状態が FLAG_ で始まる | 便2と同じく理由・要確認は変えない（:709-710） |

## 7. 受入基準と検証
| 基準 | 検証方法 |
|---|---|
| V1 単体: 規則12の各分岐（12a〜12e の不成立それぞれ・反例2型・k=2・人の判断・便1/便2の件は不変）と、`_apply_soldout_targets` の basis | `backend/tests/test_gemini_raw_copy_v102_soldout_ref.py`・`backend/tests/test_line_analysis_v102_svc.py` に追加、CI |
| V1' DB越し: 引き継いだ〆で前の在庫行が is_current=FALSE、やり直しで戻る | `backend/tests/test_v102_soldout_extra_targets_pg.py` の流儀で追加、CI |
| V2 等価: 手元の保存済み解析結果（recon.md §3-2 と同じ書き出し）から `SoldoutRefPost` を組み、ブランチの `decide_soldout_inherit` を S 880 件に当てる。引き継ぐ件の集合が 53 件と完全一致、反例2件は引き継がない | Sonnet が手元で実行（repo 外の道具）、Opus が突き合わせ |
| V3 既存不変: CI 全緑。便1/便2のテストに差分なし | CI |
| V4 本番: デプロイ後、商品名を書いた〆の件で `condition_basis='SOLDOUT_INHERIT'` が付き、参照した在庫行が is_current=FALSE | Opus が本番 SELECT（新しい投稿が来たとき） |

## 8. 戻し方
コードのみの変更。PR を revert してデプロイすれば元に戻る。それまでに書かれた `SOLDOUT_INHERIT` の件は、次のやり直し（再解析）で元の状態に戻る。表・列の変更は無い。

## 9. 維持の仕組み
- 守り手: §7 V1 のテスト（規則12の各分岐・反例2型）。
- 正本: 状態は `analysis_results.condition_id` の1か所、在庫の最新は `is_current` の1か所（ADR-158）。新しい表・保存先は作らない。

## 10. 外部・過去事例の参照と我々への応用
- 外部事例: 該当なし（仕入元 LINE の書き方に固有。本番の全件測定と原文照合で判断）。
- 過去事例（自社）: 便2 規則11b（〆で商品未決の件が参照在庫の状態を引き継ぐ、#4117）。本番で初回の matched_soldout_ref が在庫行を正しく外したことを 2026-10-11 に確認（recon.md §3-1）。同じ部品（`_apply_soldout_targets`）を使う。

## 11. 対象外（別便）
recon.md §3-3 の2つの型（価格の行と完売の行が分かれる型、価格の無い在庫更新）。
今も残っている取り残し13件（多くは旧エンジン v9 の行）は、このコードでは直らない（v102 で解析し直せない投稿のため）。扱いは別途 PO 判断。

## 12. 設計審査（Opus 自己審査）
- 判定: APPROVE（実装可）。
- 根拠: 規則は全件測定の定義（recon.md §3-2）をそのまま写した。反例は原文で確認済み。差し込み位置・書き込み部品は既存（便2）の file:line を実物で確認。
- 未解決: R1・R2 は V2 で確かめる（差が出たらマージしない）。

## 13. V2 等価確認の結果（2026-10-11、ブランチ ec5796608、手元・DB 書き込みなし）
- 保存済み解析結果から本番の読み込みと同じ意味で過去投稿を組み、`decide_soldout_inherit` を import して完売の件 899 件（900 − SOLDOUT_REF 1。語で決まった 19 件は規則12c で外れる）に当てた。
- 結果: 決まった 56 件。測定の 53 件は全件一致（相手の状態も 53/53 一致）、測定にあって決まらない件 0、反例2件は決まらない。
- 測定に無い 3 件は、全て「〆と同じ時刻の別の投稿」に同じ商品の行がある件。測定は同時刻の行を「より新しい行」に数え、本番の読み込みは〆より厳密に前の投稿だけを読む（`backend/app/services/line_analysis_v102_svc.py:867-873` の `line_posted_at < :posted_at`）ための差。3 件とも原文で引き継ぐ状態が正しい（「30th CELEBRATION BOX 100@22,000 完売」→ Sealed box、「FB06 完売 (B品)1BOX@11,000円」→ Sealed box、「〆 15個@11500 完売中」→ FLAG_SINGLE で、同時刻の別投稿が同じ状態を完売にしている）。誤り 0。
- 途中の修正: 最初の実装は同じ投稿の他の件を見ず、測定に無い 13 件を引き継いだ（パック在庫を消す形を含む）。規則12e に同じ投稿の件を足して解消（ec5796608）。
- 判定: G1 は「誤り 0・測定の 53 件を全て含む・差 3 件は読み込みの時刻境界で説明でき原文で正しい」として合格とする。
