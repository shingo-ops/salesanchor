# 写しを窓口から作る道具 fetch_snapshot.py 設計（段階4・Opus 2026-10-24）

- recon: docs/handoff/accuracy-snapshot/recon.md（以下 R）
- 関連 ADR: ADR-1042（読むだけの窓口）、ADR-1043（正解表を本番 DB に置く）
- 上位の設計: 段階4「結果の持ち帰り」案 A（PO 決定 2026-10-24「1」: 非公開のページに置く）
- 区分: A（scripts/accuracy に道具を 1 つ足す。本番・DB・CI は変えない）

## 1. 目的
クラウドの AI が、手元と同じ正答率の採点をできるようにする。採点には「システムの答えの写し」（snapshot）が要るが、今は手元で manual-only の道（fetch.sh）でしか作れない（R §2）。窓口（ADR-1042）から同じ写しを作る道具を足す。

## 2. 変更前 → 変更後
- 前: 写しは手元の fetch.sh（リポジトリ外・社外秘フォルダ）だけ。クラウドでは作れない
- 後: `python3 -I scripts/accuracy/fetch_snapshot.py --gold-version gold_v1 --out-dir DIR` で、正解表の投稿ぶんの写しを `DIR/<投稿id>.tsv` に作る。手元でもクラウドでも同じ道具

## 3. 仕様
1. 投稿の一覧: `select distinct post_id::text as post_id from ai_ro.public__accuracy_gold_rows where gold_version='<版>' order by 1`。各値を UUID の形で検証。数を `accuracy_gold_versions.post_count` と照合し、違えば停止（R §6）
2. 写しの問い合わせ: 投稿を 25 本ずつ、直列で送る（窓口は同時 1 本、R §4・§5）。列は score_v102.py の SNAP_COLS 14 列（score_v102.py:18-21）＋投稿id 1 列。絞り込みと並びは手元の fetch.sh と同じ（`engine_version='<engine>'`、is_current では絞らない、`order by i.line_start, i.gemini_index, ar.computed_at, ar.id`、R §2）。投稿の条件は `j.source_message_id in ('<uuid>', …)`（列を cast しない。索引を効かせるため）
3. 停止の条件（どれか 1 つでもファイルを 1 つも書かない）
   - HTTP が 200 でない／rc が 0 でない
   - 見出しが想定の 15 列と違う
   - 返った行数が limit 以上（打ち切りは本文に出ないため、R §5）
   - どれかの値に `\` を含む（窓口が改行・タブ・`\` を置き換えた印。score はこれを戻さないので、手元の写しと食い違う。R §4）。件数と列名だけを報告し、値は出さない
   - どれかの値の長さが 10240 文字以上（窓口の切り詰め、R §4）
   - 正解表の投稿のうち、写しが 0 行の投稿があっても止めない（score は nocur として数える、R §1）。数だけ報告する
4. 書き方: 全部の問い合わせが通ってから、投稿ごとに `<投稿id>.tsv`（見出し＝14 列、窓口の本文の値をそのまま。csv で書き直さない）。0 行の投稿はファイルを作らない。DIR に既に .tsv があれば停止（混ざらないように）
5. 記録: 最後に 1 行 `posts=<要求> with_rows=<行あり> rows=<合計> fetched_at=<UTC> engine=<engine>` を出す。投稿id は画面に出さない
6. 鍵: fetch_gold.py と同じ（クラウドは自動、手元は環境変数 READ_WINDOW_TOKEN。値を出さない）。post() などの部品は fetch_gold.py から読み込んで使う（同じ処理を 2 か所に書かない）

## 4. 対象外
- 本番への書き込み、窓口・DB・CI の変更
- 採点の道具 score_v102.py の変更
- Artifact で公開する手順の自動化（手順書に書くだけ）

## 5. 受入条件
| 基準 | 検証方法 |
|---|---|
| K1 試験が全部通る | `python3 -m pytest scripts/accuracy -q` が全件合格（窓口は偽物の関数で置き換える） |
| K2 停止の条件 5 つが、それぞれ試験で止まり、ファイルが 0 個 | 試験で、各条件の応答を与えて終了コード 1・DIR の .tsv 0 個 |
| K3 手元で本番から作った写しが、同じ時刻に psql で直接引いた 14 列と一致 | 投稿ごとに並べ替えて diff 0（マージ後に Opus が実施） |
| K4 クラウド（環境 Default）で fetch_gold → fetch_snapshot → score_v102 が通り、result.tsv を非公開ページに出せる | routine のログで rc 0・公開 URL |
| K5 そのページの result.tsv と、同じ時刻に手元で採点した result.tsv が一致 | diff 0 行 |
| K6 GitHub に投稿id と抽出値が 0 件 | PR の差分を UUID の正規表現で grep して 0 |

## 6. 代替案
- 全部を 1 回で取る: 上限内（約 1500 行）だが、行が増えると打ち切りに近づく。25 本ずつにする
- 49 列を全部取る（手元と同じ）: score は 14 列しか使わない。応答が約 3 倍になり、`\` の検査の範囲も増える。14 列にする
- `\` を道具で元に戻す: 戻した値をどう書くかで手元の写しとの差が新しく生まれる。今の 14 列に該当があるかは未確認なので、まず止める形にし、当たったら別の便で決める

## 7. リスクと対処
- 再解析が走ると、同じ問い合わせでも写しが変わる（R §2 未確認）→ K3・K5 は同じ時刻に取る。記録に fetched_at を出す
- 窓口の応答の大きさの上限（R §5 未確認）→ 25 本ずつで約 170KB／回より小さい（14 列なら約 1/3）
- 写しは社外秘 → 出力先はリポジトリの外（クラウドは scratchpad）。手順書に明記

## 8. 戻し方
道具・試験・手順書の節を消す PR（本番に影響なし）。

## 9. 維持
- 試験は scripts/accuracy の pytest（CI には無い。R0 で確認済み）。道具を変えるときは手で回す
- 担当: Opus（段階4 の設計）

## 10. 外部事例
不要。社内の窓口と採点の道具をつなぐだけで、外部の方式を選ぶ判断が無いため。

## 11. 審査（Opus 自己審査・同一 AI）
- 既存との整合: 列は score_v102.py:18-21、絞り込みは fetch.sh、窓口の制約は readonly_query.py・read_window_http.py の実物で確認（R）
- 未確認で設計に影響するもの: `\` を含む値の有無 → 止める形にしたので、設計は成り立つ。当たったら K3 の前に分かる
- 判定: APPROVE（設計合格。PO 承認・マージ・本番反映を兼ねない）
