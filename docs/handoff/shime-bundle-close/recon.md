# recon: まとめて〆る投稿で、上の商品が閉じない件

出どころ: 毎朝の〆の点検（2026-11-12 12:02 JST の回）の × 1件と、クラウドの読み取り調べ2回（ブランチ `release/shime-bundle-close-recon` a9ba3a58 の cause-recon.md、`release/shime-bundle-close-recon2` 241cd193 の recon-raw.md）。仕入元の名前・人の名前・投稿の本文はここに書かない（社外秘の作業記録にだけある）。

基準のコミット: origin/main 9d4b1e728。

## 1. 起きたこと（観測事実）
- 投稿の形: 3行。1行目と2行目に型番だけの行（価格・数量・売り切れの言葉なし）、3行目に「〆」だけの行。
- Gemini の応答から作られた件は1件だけ（lines [2,3]、Sealed box、Sold out）。1行目の商品の件は作られなかった。
- そのため、1行目の商品は前の投稿で In Stock のまま残った（点検の記録 daily/20261112_1202 の rows.txt・raw.txt・prior_state.txt。社外秘の作業記録）。
- 毎朝の点検では、これを「まとめ〆の閉じ漏れ」として × に数えた（PO 2026-11-12「1」）。

## 2. 本番の指示書
- 本番の v102 は、ファイルではなく DB の指示書を使う。
  - `backend/app/services/line_analysis_v102_svc.py:104` `V102_ENGINE_VERSION = "v102-f_dm"`
  - `backend/app/services/line_analysis_v102_svc.py:106` `V102_PROMPT_KEY = "raw_copy_v101_f_dm"`
  - `backend/app/prompts/raw_copy_v101_e.txt` は本番では使われない。
- 読み取り鍵で、本番の `public.extraction_prompt_config` の key `raw_copy_v101_f_dm` の本文を取った。本文の sha256 は 84afd2e4e0094b542d5f1dada1fef39290aa6d997135296e78601fc945ac8b0c で、`docs/specs/line-analysis-tuning/README.md:40` の値と一致した（生出力は社外秘の作業記録 daily/20261112_1202/pdm.txt。復元した本文は pdm_decoded.txt）。
- 手順1の〆の決まりは2つだけある（pdm_decoded.txt:12-13）。
  - 「価格が無く『完売』『残りN』などだけが書かれた商品も1件にする」
  - 「商品名〆」のように、商品名のすぐ後ろに〆が付いた行を1件にする。
- 「〆だけの行の上に、商品名だけの行が何行も並ぶ」形の決まりは無い。

## 3. 受け取り側（コード）
- 価格が none の件の「価格の行」は、売り切れの言葉か数量を含む最初の行。無ければ lines の最後の行。
  - `backend/app/services/gemini_raw_copy_v101.py:189-196` `_unpriced_line`
- 2つの件の価格の行が同じだと、後の件は落とされ、要確認（「同じ価格の行が重なっている」）に回る。
  - `backend/app/services/gemini_raw_copy_v101.py:255`（`seen_price_lines`）
  - 同 `:266-270`（`REJECTED_DUPLICATE` = "duplicate_price_line"）
- したがって、指示書だけ直して Gemini が [1,3] と [2,3] の2件を返しても、どちらの価格の行も3行目になり、2件目は落ちる。指示書と受け取り側の両方を直す必要がある。
- 価格の行を鍵にした辞書（同じ値が2件あると、後の件が前の件を上書きする）:
  - 同 `:602` `by_price_line = {it["price_line"]: i for i, it in enumerate(items)}`（迷う行の付け直し）
  - 同 `:1212` `by_price_line`（F2 名前の無い件に前の件の名前を付ける）
  - 同 `:1474` `owners = {it["price_line"]: it for it in items}`（v102 の経路）
  - 同 `:1571` `owners = {it["price_line"]: it for it in adjusted}`（v102 でない経路）
- 価格の行を集合で使うだけの所（重なっても壊れない）: 同 `:528`・`:543`・`:1081`・`:1115`、`backend/app/services/line_analysis_v102_svc.py:253`、`backend/app/services/v102_gap_lines.py:132`。
- DB の行との対応付けは価格の行ではなく gemini_index を使う（`backend/app/services/line_analysis_v102_svc.py:654-666` `_items_by_position`）。価格の行が重なっても対応付けは壊れない。
- 名前は、価格の行（〆の行）からは価格・数量・売り切れの語を除いた残りを使い、商品名の行は丸ごと使う。〆の行が価格の行のとき、名前は商品名の行になる（既存の試験 `backend/tests/test_gemini_raw_copy_v101.py:331-335`）。
- 同じ投稿の〆で在庫を閉じる規則13: `backend/app/services/line_analysis_v102_svc.py:1135-1165`。〆の件の行の範囲に入る、同じ商品・同じ状態の在庫の件を Sold out にする。今回の閉じ漏れは前の投稿の在庫なので、規則13は関係しない。この投稿で1行目の商品の Sold out の件が作られれば、在庫の最新の状態は Sold out になる。

## 4. 落とす件の既存の試験（変えてはいけない動き）
- `backend/tests/test_gemini_raw_copy_v101.py:820-870`: 価格のある件どうしで価格の行が重なったら duplicate_price_line で落とす（keep_rejected のときは後ろに残す）。
- `backend/tests/test_v102_gap_lines.py:70`: rejected="duplicate_price_line" の件を受理した件から外す。

## 5. 指示書の入れ方（前例）
- 指示書の行は、migration ではなく、手元の書き込み台本を PO が `!` で流して足してきた（社外秘の作業記録 prompts/write_fct/README.md。precheck → dryrun → commit → verify の4段。新しい key の行を1行足すだけで、既存の行は触らない）。
- 既定の指示書の切り替えは、定数を替える PR で行った（`docs/handoff/v102-prompt-fdm/design.md` §3）。backend/app/services を触るので、関所が GO 記録を求める（同 §6）。
- 試験は prompt_ab で、DB の key を `--prompt-key` で指定して流す（`backend/app/tools/prompt_ab.py:493-501`）。DB に行が無いと試験できない。

## 6. 既存 ADR の検索
- `git grep -il "〆\|shime\|duplicate_price_line" docs/adr/` と `docs/adr/FEATURE-INDEX.md` を見た。指示書の既定 key や価格の行の重なりを定める ADR は無い。
- 関係する ADR: ADR-1003（PO の委任に基づく Claude Opus の GO 発行）、ADR-136-cc-bot-github-identity.md（危険 PR の GO 手順と GO 記録の形）、ADR-135（main にマージ＝本番投入可）。
- 関係する設計: `docs/handoff/v102-shime-same-post-stock/design.md`（規則13）、`docs/handoff/v102-prompt-fdm/design.md`（指示書の切り替えの前例）。

## 7. 数えた結果（読み取り鍵、2026-11-12）
生出力と仕分けは社外秘の作業記録 shime-auto-check/bundle-design/（k0_cand.txt・k2_cand.txt・k2_labels.md）。件数の生出力は手元の /tmp/CC報告ファイル/shime-bundle/k0_count.txt・k2_count.txt。
- 母数: `extraction_jobs` で `prompt_version LIKE 'v102:%'` かつ `created_at >= now() - interval '30 days'` のジョブ 2738 件（AUDIT ts=2026-11-12T11:25:29Z）。
- K0（価格 none の件どうしの重なり）:
  - 問い合わせ: 同じジョブの extraction_items の2件で、`raw_price` が none（NULL・空も含む）どうし、かつ `source_lines` が重なる（`&&`）組を数える。
  - 問い合わせの全文（K0 の後の測定でも同じものを流す。30 days を「便1の反映から」に替える）:

```sql
WITH j AS (SELECT id FROM ai_ro.public__extraction_jobs WHERE prompt_version LIKE 'v102:%' AND created_at >= now()-interval '30 days'),
p AS (SELECT a.extraction_job_id jid, a.gemini_index ga, b.gemini_index gb
      FROM ai_ro.public__extraction_items a JOIN ai_ro.public__extraction_items b
        ON a.extraction_job_id=b.extraction_job_id AND a.gemini_index<b.gemini_index
      WHERE a.extraction_job_id IN (SELECT id FROM j)
        AND coalesce(a.raw_price,'none') IN ('none','') AND coalesce(b.raw_price,'none') IN ('none','')
        AND a.source_lines && b.source_lines)
SELECT (SELECT count(*) FROM j) jobs30, count(DISTINCT jid) cand_jobs, count(*) cand_pairs FROM p
```
  - 結果: 9ジョブ・12組。12組を全部目で見た。どの組も、重なっているのは上の見出し（商品名）の行で、各件は自分の売り切れや残り数の行を持っていた。`_unpriced_line`（`backend/app/services/gemini_raw_copy_v101.py:189-196`）で価格の行を出すと、12組とも別の行になる。
  - よって「価格 none の2件が同じ価格の行を持つ」ジョブ N0 = 0。今の f_dm でこの形は直近30日に出ていない。11/12 の投稿は、Gemini が1件しか返さなかったので、この数には入らない。
- K2（まとめ〆の形の候補）:
  - 問い合わせ: 上の母数の投稿の原文で、「〆」「〆切」「〆切り」「完売」だけの行のすぐ上の2行が空でなく、価格らしい語（円・¥・@・〆・完売・3桁以上の数字）を含まないところ（AUDIT ts=2026-11-12T11:25:40Z）。
  - 結果: 34投稿・51か所。Opus が全部を目で仕分けた。
    - 正（並んだ行がそれぞれ別の商品）: 4投稿。11/12 の × の投稿を含む。
    - 負（商品名の行＋補足の行＋完売。1商品）: 27投稿。
    - 迷う（原文だけでは別の商品か補足か決められない）: 3投稿。
  - 補足: `extraction_items.raw_price` は NULL が700件、'none' が1967件ある（全期間）。K0 の問い合わせはどちらも none として数えた。

## 8. 未確認
- Gemini の生の応答（なぜ1件しか返さなかったか）は読んでいない。
- K2 の候補の問い合わせは、上の2行だけを見る粗い絞り方なので、4行以上並ぶ形や、価格らしい語を含む型番の行を取りこぼしている可能性がある。取りこぼしは K4（本番の毎朝の点検）で見る。
