# 便1 状態の辞書に「切れ込み」を足す SQL（本番未適用）

カートンの傷みの状態（line_conditions id 13・code CN0002・Damaged case）の search_kw の末尾に `,切れ込み` を1語足す。コードは変えない。本番に流すのは Opus（担当は流さない）。足す先は PO の選択（2026-11-14「1」＝傷みのあるカートン）。

| 順 | 作業 | 期待 |
|---|---|---|
| 1 | `01_precheck.sql`（読み取り専用の道で1文として流す） | PRECHECK 行が1行: id 13・CN0002・Damaged case・app_kubun 箱系大・「切れ込み」を含む行が0。KIREKOMI_LINES が 2（直近180日の原文で「切れ込み」を含む行。設計 K2） |
| 2 | `02_apply.sql` を `-v end=ROLLBACK` で DRY-RUN | UPDATED 1・CHECK_OK 1、最後に ROLLBACK |
| 3 | `02_apply.sql` を `-v end=COMMIT` | 手順 2 と同じ、COMMIT |
| 4 | `03_verify.sql`（読み取り専用の道） | VERIFY 行が1行: 「切れ込み」を含む行は id 13 だけ。search_kw の末尾が `,切れ込み` |

戻し: `04_rollback.sql`（ROLLBACK 1）。状態の辞書は解析のたびに読み直される（`backend/app/services/tcg_analyzer_svc.py` の `load_condition_entries` は毎回 `public.conditions` を読む。`public.conditions` は `public.line_conditions` の VIEW：`migrations/20261017_120000_line_conditions_value_rank.sql:47`）ので、再起動は要らない。過去の解析結果は変えない（再解析しない）。

## 見張りの問い合わせ（設計 K4・K5）

`05_detect.sql`（読み取り専用の道で1文として流す）: 直近30日で、1投稿に同じ商品×状態の In Stock が値段違いで2行以上あり、同じ仕入元の次の同じ組の行が Sold out の組を出す。出力には原文の一部が入るので、作業記録（リポジトリ外）にだけ置く。

- K4: 2026-12-13 までに流すと、2026-11-13 の今回の組（product_id 420436）が出る。2026-11-13 の実行では 15 行・11 組（作業記録 dup_soldout.txt）。
- K5: 便1 の反映から14日たった後に1回流す。そのとき `now()-interval '30 days'` を丸ごと、便1 の反映の時刻に書き換える（例: `sm.line_posted_at > timestamptz '2026-11-15 18:00+09'`）。`interval '30 days'` だけを書き換えると、型が合わずに失敗する。出た組を1組ずつ原文で見る。
- 05_detect が数えない物（2026-11-15 設計審査2回目の指摘）:
  - 状態が空（condition_id が NULL）の組。`=` で比べているので外れる。
  - 投稿の順は line_posted_at で決めている。現行の行の決め方は received_at なので、まれに順が違う。
  - pid_resolved で絞っていない。
- `06_k1_posts.sql`（設計 K1、読み取り専用の道で1文として流す）: K5 と同じ日に流す。その前に、`timestamptz '2026-11-15 00:00+09'` を便1 の反映の時刻に書き換える。原文に「切れ込み」を含む行と、その行を件の行に持つ解析行の状態を出す。出力は作業記録にだけ置く。
