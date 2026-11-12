# 設計審査の記録 — analysis-tx-release

## 1 回目（2026-11-12 07:58〜08:00 UTC・クラウド architect・claude-opus-5-5・読むだけ）

- 対象: 枝の先頭 115028481（審査役が `git log -1` で確かめた）。
- 試験は読むだけの約束で流していない。(3)(4) はコードを読んでの判断。

### 結論
VERDICT: REVISE — 中 2 つ（例外を受け止める範囲、K3 の非同期の書き方）を設計に書き足せば実装に渡せる。高は無し。

### 確かめて問題なしとした点（審査役の記録の要約）
- (1) 書く時は必ず鍵を取り直し、読み直した入力で書く。比べる入力に抜けは無い。人の値の直し（`backend/app/services/v102_human_decisions_svc.py` :593-633）は item_corrections に書くので decisions で見つかる。除外の確認（ack）も decisions に入る（:59-60）。書き写しの直しは extraction_items を変えるので rows で見つかる。計算（`backend/app/services/line_analysis_v102_svc.py` :355-401）は session を使わない。
- (2) 呼び出し元 5 か所は、計算の前の commit で書きかけを確定させない。
- (3) 既存の試験は壊れない見込み。`backend/tests/test_line_analysis_v102_svc.py` :600-663 は計算で例外を出すので読み直しの前で止まる。commit は `.called` で見ている。`backend/tests/test_analysis_failed_record.py` は run_v102_analysis を丸ごと差し替えている。
- (5) マスタは辞書と dataclass で返る（`backend/app/services/line_analysis_v102_svc.py` :217-245）。commit の後に DB を読む道は見つからない。
- (6) K1〜K5 は○×で判定できる。区分 A の理由も合う。

### 指摘と直した場所（design.md）
| 重さ | 指摘 | 直した場所 |
|---|---|---|
| 中 | 例外を受け止める範囲が「2・6 の間」。7〜8 も同じ try に入れると明記 | §5-1 の 4・9（4〜8 を 1 つの try に。今の try の外／中の境目を保つため読む関数を head と tail に分けた） |
| 低 | 2 回目の読みで job が消えて ValueError が出る場合の扱い | §5-1 の 9（except で受けて empty_stats） |
| 中 | K3: `save_value_override` は非同期。`create_async_engine` と `asyncio.run` で呼ぶ形を明記（前例 `backend/tests/test_line_analysis_v102_pg.py` :273-280）。直す前は lock_timeout で例外 → empty_stats で赤 | §5-2 K3 |
| 低 | §6: tcg_extraction :476 の前の commit は :455 ではなく `backend/app/services/line_analysis_v102_svc.py` :596 | §6 の表（Planner が a3e93f053 で :590-597 を読んで確かめた） |
| 低 | §5 の表に K3b が抜け。赤になるのは K2・K3 だけ | §5 の表 |
| 低 | やり直したとき previous_pairs・prior_current は 2 回目の値を使うと明記 | §5-1 の 7・10 |
| 低 | recon §2-3 は 4 か所、design §6 は 5 か所で数え方がそろわない | §6 の表に数え方を書いた |

## 2 回目
（審査待ち）
