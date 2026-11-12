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
  - `/Users/tanizawashingo/worktrees/salesanchor/release-shime-bundle-close/backend/app/services/line_analysis_v102_svc.py:104` `V102_ENGINE_VERSION = "v102-f_dm"`
  - `/Users/tanizawashingo/worktrees/salesanchor/release-shime-bundle-close/backend/app/services/line_analysis_v102_svc.py:106` `V102_PROMPT_KEY = "raw_copy_v101_f_dm"`
  - `backend/app/prompts/raw_copy_v101_e.txt` は本番では使われない。
- 読み取り鍵で、本番の `public.extraction_prompt_config` の key `raw_copy_v101_f_dm` の本文を取った。本文の sha256 は 84afd2e4e0094b542d5f1dada1fef39290aa6d997135296e78601fc945ac8b0c で、`docs/specs/line-analysis-tuning/README.md:40` の値と一致した（生出力は社外秘の作業記録 daily/20261112_1202/pdm.txt。復元した本文は pdm_decoded.txt）。
- 手順1の〆の決まりは2つだけある（pdm_decoded.txt:12-13）。
  - 「価格が無く『完売』『残りN』などだけが書かれた商品も1件にする」
  - 「商品名〆」のように、商品名のすぐ後ろに〆が付いた行を1件にする。
- 「〆だけの行の上に、商品名だけの行が何行も並ぶ」形の決まりは無い。

## 3. 受け取り側（コード）
- 価格が none の件の「価格の行」は、売り切れの言葉か数量を含む最初の行。無ければ lines の最後の行。
  - `/Users/tanizawashingo/worktrees/salesanchor/release-shime-bundle-close/backend/app/services/gemini_raw_copy_v101.py:189-196` `_unpriced_line`
- 2つの件の価格の行が同じだと、後の件は落とされ、要確認（「同じ価格の行が重なっている」）に回る。
  - `/Users/tanizawashingo/worktrees/salesanchor/release-shime-bundle-close/backend/app/services/gemini_raw_copy_v101.py:255`（`seen_price_lines`）
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
- 同じ投稿の〆で在庫を閉じる規則13: `/Users/tanizawashingo/worktrees/salesanchor/release-shime-bundle-close/backend/app/services/line_analysis_v102_svc.py:1135-1165`。〆の件の行の範囲に入る、同じ商品・同じ状態の在庫の件を Sold out にする。今回の閉じ漏れは前の投稿の在庫なので、規則13は関係しない。この投稿で1行目の商品の Sold out の件が作られれば、在庫の最新の状態は Sold out になる。

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

## 7. 未確認
- Gemini の生の応答（なぜ1件しか返さなかったか）は読んでいない。
- 直近30日で「型番だけの行が2行以上並び、その下に〆だけの行」という形の投稿が何件あるかは、まだ数えていない（設計 §5 の K2 の準備で数える）。
- 今の f_dm で、価格 none の件どうしが同じ〆の行を取り合って落ちた件（duplicate_price_line）が直近30日に何件あるかは、まだ数えていない（設計 §5 の K0 で数える）。
