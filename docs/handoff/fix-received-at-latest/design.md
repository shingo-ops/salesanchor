# design: 受信時刻（received_at）を「採用した本文の投稿時刻」に直す

- 状態: 設計案作成済み／設計審査済み（§9）／**PO の実装承認済み（2026-09-29、Draft PR まで）**／マージ・本番反映は未承認
- PO の決定（2026-09-29、選択肢への回答）
  - 実装の承認:「時刻修正→〆判定＋Y (Recommended)」＝この便では時刻の修正だけを実装して Draft PR にする。〆の判定と Y は次の便で扱う
  - 値段のない新しい投稿の扱い:「B. 前の値段を引き継ぐ」、見せ方は「Y. 値段のある直前の投稿」。**この便には入れない**（§11）
- 調査: `docs/handoff/fix-received-at-latest/recon.md`
- 起点: PR #3840 の調査記録（docs/handoff/line-import-missed-0928/recon.md。未マージ）
- 対象ADR: `docs/adr/ADR-158-product-level-supersession.md`
- PO の決定（2026-09-29、チャットの原文）:「受信時刻を正しくする：すでに間違って入っている時刻も直します。」

## 1. 目的（PO から見える変化）
同じ仕入元から新しい投稿が来たら、**その投稿の商品・価格が配信される**ようにする。今は受信時刻が数週間前の値になっているため、新しい投稿が古い投稿に負けて「現在の情報」から外れる。そのうえ古い投稿は48時間の絞り込みで配信から外れるので、**結果としてどちらも配信されない**（実測: 平田光希は配信0行。修正を再現すると4行。配信全体は 249行 → 852行。recon §6-2）。

## 2. 対象と対象外
- 対象
  1. 新しく取り込む分: received_at に、採用した本文（最新1通）の投稿時刻を入れる
  2. 既存の行: received_at を line_posted_at にそろえる（1,196行）
  3. 既存の is_current: 正しい時刻で選び直す（試算: TRUE→FALSE が 1,452行、FALSE→TRUE が 1,453行）
- 対象外（別の便で扱う）: 〆・完売の判定（「状態」欄だけを照合する問題）、〆を違う商品に結び付ける問題、確認画面と配信の判定基準の違い、ADR-158 本文の更新、完売ルールページの導線、送信取り消しの反映、`_merge_supplier_products` のロジックそのもの

## 3. 変更前後
| 項目 | 変更前 | 変更後 |
|---|---|---|
| `backend/app/services/tcg_line_import_svc.py:309` | `received_at = sorted_msgs[0]["timestamp"]`（最古） | `received_at = latest_msg["timestamp"]`（採用した本文＝line_posted_at と同じ値） |
| 同ファイル:289 の docstring | 「最初の timestamp」 | 「採用した最新メッセージの timestamp（line_posted_at と同じ値）」 |
| 既存の source_messages | 1,196行が最古の時刻 | 全行で received_at = line_posted_at |
| 既存の analysis_results.is_current | 誤った時刻で選ばれている | (チャネル, 商品, 状態) ごとに、投稿時刻が最新の1行だけ TRUE |
| `backend/tests/test_tcg_line_import.py:347-364` | 最古を期待している | 最新を期待する |

## 4. 方式と選んだ理由
- **採用: 取り込み時の値を直し、既存の行をマイグレーションで補正して is_current を選び直す**
  - received_at を使う5か所（recon §2）がすべて正しくなる。`_merge_supplier_products` を変えなくて済む
  - デプロイでは新しいコードが先に起動し、そのあとにマイグレーションが走る（recon §5）。その間に新しく取り込まれた行は正しい時刻で入るので、マイグレーションは既存の行だけを直せばよい。マイグレーションは何度実行しても同じ結果になる（冪等）
- 不採用 A: `_merge_supplier_products` の並べ替えを line_posted_at に変えるだけ → ダッシュボードの「最終受信日時」と「最新原文」を選ぶ処理（recon §2）が間違ったまま残る
- 不採用 B: 手作業の SSH で補正し、記録だけのマイグレーションを残す（`migrations/20260924_060000_cleanup_supplier_name_duplicates.sql` の方式）→ コードの修正と補正の実行を1回のデプロイでそろえられない。冪等な SQL なので、自動で実行してかまわない

## 5. マイグレーション（完成形。実装役は一字一句このとおり作る）
ファイル: migrations/20260929_120000_fix_source_messages_received_at.sql
```sql
-- 受信時刻（received_at）を採用本文の投稿時刻（line_posted_at）にそろえ、
-- ADR-158 の is_current を正しい投稿順で選び直す。
-- 詳細: docs/handoff/fix-received-at-latest/design.md
-- 冪等: 2回目以降は更新0行

UPDATE public.source_messages
   SET received_at = line_posted_at
 WHERE line_posted_at IS NOT NULL
   AND received_at IS DISTINCT FROM line_posted_at;

WITH ranked AS (
    SELECT ar.id,
           (ROW_NUMBER() OVER (
               PARTITION BY sm.supplier_channel_id, ar.product_id, ar.condition_id
               ORDER BY sm.received_at DESC NULLS LAST, ar.computed_at DESC
           ) = 1) AS should_be_current
      FROM public.analysis_results ar
      JOIN public.extraction_items ei ON ei.id = ar.extraction_item_id
      JOIN public.extraction_jobs ej ON ej.id = ei.extraction_job_id
      JOIN public.source_messages sm ON sm.id = ej.source_message_id
     WHERE sm.supplier_channel_id IS NOT NULL
       AND ar.pid_resolved = TRUE
       AND ar.product_id IS NOT NULL
)
UPDATE public.analysis_results ar_target
   SET is_current = ranked.should_be_current,
       updated_at = NOW()
  FROM ranked
 WHERE ar_target.id = ranked.id
   AND ar_target.is_current IS DISTINCT FROM ranked.should_be_current;
```
- 並べ替えは `_merge_supplier_products`（`backend/app/services/tcg_analyzer_svc.py:1769-1772`）と同じ（`received_at DESC, computed_at DESC`）。チャネルは、コードでは WHERE で絞っているところを、ここでは PARTITION に入れている
- product_id が NULL の行と、pid が未解決の行は、コードと同じく対象にしない（今の値のまま）

## 6. 受入条件
| 基準 | 検証方法 |
|---|---|
| 新しい取り込みで received_at = line_posted_at になる | ユニットテスト: `test_build_timestamp_ascending_order` が最新を期待し、`received_at == line_posted_at` を確認する（CI `pytest (SQLite + PostgreSQL RLS)` が緑） |
| 既存の行のずれが0件 | デプロイ後に本番で読み取り照会: `SELECT count(*) FROM public.source_messages WHERE line_posted_at IS NOT NULL AND received_at IS DISTINCT FROM line_posted_at;` → 0 |
| (チャネル, 商品, 状態) ごとに TRUE がちょうど1件 | 読み取り照会（recon §4 と同じ集計）: zero_true=0、multi_true=0 |
| TRUE の行が、そのグループで投稿時刻が最新の行 | 読み取り照会: TRUE の行の line_posted_at が、そのグループの最大値より小さいグループの数 → 0 |
| PO が画面で確認できる | 次の配信のあと、配信シート（在庫集計）で、48時間以内に投稿した仕入元の商品が出ていることを確認する。例: デプロイの直前に投稿した仕入元を1社選び、その投稿の商品と価格がシートにある（○×）。配信の行数が、デプロイ前の再現値（recon §6-2 の方法）より増えている |
| マイグレーションが冪等 | 同じ SQL をもう一度流して、更新が0行になる（ローカルの PG で確認） |

## 7. リスクと対処
| リスク | 対処 |
|---|---|
| 配信の中身が一度に大きく変わる（配信SQLで再現した値: 249行 → 852行。新しく出る 607件、消える 4件、価格が変わる 5件） | 意図した変化（48時間以内の新しい投稿が配信される）。GO の直前に、同じ方法でもう一度再現し、件数を PO に提示する。消える4件は理由が未確認なので、GO の前に確認する |
| 補正する前の値が失われる | マイグレーションを適用する前に、`source_messages(id, received_at)` と `analysis_results(id, is_current)` を退避する（手順はカード。PO の GO 対象） |
| デプロイ中に、古いコードが誤った時刻で取り込む | マイグレーションは新しいコードの起動後に走り（recon §5）、冪等。デプロイ後の検証で0件を確認する |
| 同じ投稿時刻の行が2つある（例: 平田 23:15 の2行） | computed_at DESC で1行に決まる（コードと同じ） |

## 8. 外部・過去事例の参照と我々への応用
外部の事例は該当なし。理由: 社内のパイプラインで、列の値を取り違えていた不具合の修正であり、外部の事例で判断が変わる要素がないため。過去の社内事例: `docs/handoff/fix-distribution-posted-at/recon.md` では、received_at を直さずに配信側だけを line_posted_at に切り替えた。その後に ADR-158 の is_current が received_at を使うようになり、同じ誤りが別の場所で表に出た。**症状が出た場所ではなく、値の出どころを直す**という教訓を、今回の方式に反映した。

## 9. 設計審査（Architect、同じ AI による自己審査）
- 判定: **APPROVE（設計合格）**。PO の承認・実装の開始・マージ・本番反映の承認は含まない
- 確認した点
  - 既存の仕様・ADR との整合: ADR-158 の「received_at の新しい順」という前提を、値の側で成り立たせる。ADR-158 の決定は変えない
  - 実物との照合: 書き込みは1か所（recon §1）。一意制約と reused 判定に received_at は関係しない（recon §1）
  - CI: 変わるテストは1件（recon §6）。必須チェック名は確認済み
  - 受入条件: すべて SQL の件数か、画面の○×で判定できる
  - 実装の範囲: コード2行（:289 と :309）、テスト1件、マイグレーション1ファイル
- 未解決（GO の前に PO が確認する）: 本番のバックアップの取り方（recon §7 未確認）。(チャネル, 商品, 状態) で TRUE が0件の1グループの原因（マイグレーションで1件になる見込み。原因は未確認のまま）

## 12. 審査のやり直し（2026-09-29）
- Reviewer（別のエージェント、同じ系統の AI）の判定: REQUEST_CHANGES。必須の CI が2つ赤だった
  - `backend/tests/test_tcg_import_progress_pg.py:143` が、旧仕様（5時間の差）を固定していた。recon §6 では「影響なし」と誤って判断していた
  - `.github/workflows/migration-test.yml` のモックに、この migration が使うテーブルがなかった（段階的拡充ルール）
- 対応: カード第2版（テスト1行、モック、main への追従）。§9 の「変わるテストは1件」は誤りだったので、2件に訂正する
- 教訓（設計担当）: 影響するテストを grep の読みで判断しない。受入条件に「必須 CI が緑」を入れ、CI の結果で確かめる

## 11. 次の便に回すもの（事実と決定）
- Y（前の値段を引き継ぐ）を試算した結果（本番の配信SQLを読み取り専用で再現、48時間の絞り込みあり）: 今 249行、時刻の修正だけ 852行、時刻の修正と Y 858行
- Y で新しく出る6件のうち5件は、新しい投稿が「〆」なのに完売と判定されていない行（Nexus「30th 〆」、平田光希「EB03〆」、星野 良介「『30th CELEBRATION』〆切ります。」、たいき OP-14／OP-15「OP-14 BOX / OP-15 BOX / OP-16 BOX 〆」）。残りの1件は在庫の更新（kaishi「残り31BOX」）→ **〆の判定を直す前に Y を入れると、完売の商品が配信される**。そのため PO は「時刻の修正 → 〆の判定と Y」の順を選んだ
- 並べ替えが1行に決まらないグループ（上位2行の line_posted_at と computed_at が同じ）が347件ある。例:「美品」と「難あり」が同じ condition になる。今のコードも、§5 のマイグレーションも同じ並べ替えを使う。**この便では変えない**（コードと補正で並べ替えを一致させるため）。次の便で、どの行を選ぶかを決めて扱う
- 既存のテストには、値段のない新しい投稿の分岐を確かめるものがない。Y を入れる便でテストを追加する
- is_current を読む箇所: `backend/app/services/tcg_distribution_svc.py:255`、`backend/app/services/tcg_distribution_svc.py:326`、`backend/app/services/tcg_distribution_svc.py:368`、`backend/app/services/tcg_analysis_dashboard_svc.py:713`

## 10. 維持の仕組み
- 守り手: `backend/tests/test_tcg_line_import.py` の `test_build_timestamp_ascending_order`。received_at が採用した本文の投稿時刻であることを固定する。CI の必須チェックで守られる
- 設計担当は、ADR-158 の本文を更新する便で、「received_at = 採用した本文の投稿時刻」を明記する（別便）
