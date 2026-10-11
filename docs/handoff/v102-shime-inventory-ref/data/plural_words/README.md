# 複数を指す言葉 4 語の登録（followup_plural_word）

## 目的
v102 の「直前・過去の投稿から商品を1つに決める処理」で、複数を指す言葉（両方・全部・全て・どちらも）が含まれる投稿では1つに決めないようにする。
読む側: `backend/app/services/gemini_raw_copy_v102_product_first.py:111-115`

## PO 決定
2026-10-10 y（設計者経由）。

## 登録内容
`public.knowledge_rules` に 4 行。category=`followup_plural_word` / pattern_type=`substring` / priority=100 / language=`ja` / is_active=TRUE。
pattern は 両方・全部・全て・どちらも。同じ category と pattern が既にあれば入れない（WHERE NOT EXISTS）。

## 事前に確認済みの本番の事実（2026-10-10、設計者の SELECT）
- category=followup_plural_word の行と、pattern が 4 語に一致する行は 0 行。
- 既存 category は priority すべて 100、language すべて ja（block_delimiter 18 / message_exclude 9 / message_exclude_no_digit 2 / status_keyword 4）。
- 一意制約なし（主キー id のみ）。CHECK は language(ja/en/ko/zh) と pattern_type(regex/prefix/substring/exact)。

## 手順（実行は PO の GO 後。本番書き込みは commit.sql のみ）
1. `precheck.sql` — 1・2 が 0 行であること
2. `dryrun.sql` — 4 行が見えて最後に ROLLBACK（何も残らない）
3. `commit.sql` — 登録
4. `verify.sql` — 読む側と同じ SELECT が 4 行（両方・全部・全て・どちらも）、他 category の件数が変わっていないこと

実行記録: 2026-10-09T23:10Z（UTC）に Opus が precheck→dryrun（INSERT 0 4→ROLLBACK）→commit（INSERT 0 4）→verify（4行・他カテゴリ不変）を実行

## 戻し方
`rollback.sql` — category・pattern・description が一致する 4 行だけを DELETE。DELETE 4 を確認してから COMMIT。

## 測り方
`verify.sql` の件数 = 4。戻した後は category=followup_plural_word が 0 行。
