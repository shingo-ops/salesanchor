# ADR-1043: 精度測定の正解表を本番 DB の専用表に置き、クラウドは読むだけの窓口から取り出す

| 項目 | 内容 |
|------|------|
| ステータス | Accepted（2026-10-23） |
| 備考 | PO 2026-10-23 チャット「1」：選択肢1「本番のデータの中に答え合わせ表を新しく作り、クラウドは『読むだけの窓口』から読む…作業は私が設計して進めます」 |
| 起案日 | 2026-10-23 |
| 方針の決定者 | Shingo（PO）。方式の選択は Opus（PO の委任に基づく。ADR-1003） |
| 関連 | ADR-1042（クラウドから本番を読む窓口）、ADR-1024（ai_ro）、ADR-1007（migration に値を書かない）、ADR-1037（ロック待ち） |
| 設計 | `docs/handoff/accuracy-gold-db/design.md`、現状 `docs/handoff/accuracy-gold-db/recon.md` |

---

## What（何を決めたか）
- 正解表の正本を本番 DB の `public.accuracy_gold_versions`（1 行 = 1 版）と `public.accuracy_gold_rows`（1 行 = 正解表の 1 行、16 列すべて）に置く。鍵は (版, ファイル上の行番号)。
- RLS は ENABLE＋FORCE、読み書きとも `app.is_operator` のときだけ。AI は ai_ro のビュー経由（ADR-1024）でだけ読む。
- 値は migration に書かず、リポジトリ外で作った投入 SQL を Opus が流す。道具（gold_to_sql.py・fetch_gold.py）は値を含まない。
- クラウドは fetch_gold.py で窓口（ADR-1042）から取り出し、sha256 と行数を版の記録と照合して一致したときだけファイルにする。採点（score_v102.py）は変えない。

## Why（なぜ）
- クラウドの AI が正答率を測るには正解表が要るが、正解表は Mac にしかなく、社外秘なので公開リポジトリに置けない。
- 本番 DB はもともと社外秘の投稿本文の正本で、クラウドから読む道（窓口）もある。ここに置けば正本は 1 か所で、新しい置き場（Drive・別リポジトリ）を増やさない。
- 16 列すべてを入れる。12 列だけだと残り 4 列の正本が Mac に残り、2 か所に分かれる。
- (投稿id, price_line) は一意でない（同じ組が 3 行ある。recon §1）。採点は行の順で区別するので、行番号を鍵にして順番を保つ。
- 既存表への FK を張らない。既存表にロックを取らず（ADR-1037）、投稿や商品が消えても当時の正解は記録として残す。

## 不採用の案
- Google Drive に置く: 正本が 2 か所。読むたびに文脈を通る。
- 非公開の別リポジトリ: クラウドで見張り（hooks）が読まれなくなる。
- score_v102.py に DB 読みを足す: 手元のファイル採点と道が分かれる。

## 戻し方
- データ: versions からその版の行を消す（rows は CASCADE で消える）。手順は design.md §7。
- 表: `DROP TABLE IF EXISTS public.accuracy_gold_rows; DROP TABLE IF EXISTS public.accuracy_gold_versions;`（不可逆。PO 確認）。

## 検証
design.md §8 の K1〜K8。
