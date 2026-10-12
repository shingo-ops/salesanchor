# recon: v102 で「〆（完売）の件」の商品を、同じ仕入元の過去48時間の投稿から決める

- 基準: origin/main 1a574a779（#4012）。読み取りのみ（Sonnet 調査、Opus 確認）。
- 既存 ADR 検索（`git grep -il -E "〆|sold.?out|完売|followup" origin/main -- docs/adr/`）: docs/adr/ADR-158-product-level-supersession.md（「〆」だけのメッセージで全商品が消える問題を (商品,状態) 単位の置き換えにした）。ほかのヒット ADR-061・ADR-109・ADR-124 は別件。docs/adr/FEATURE-INDEX.md に該当行なし。
- 前便: docs/handoff/v102-followup-post-ref/design.md（#4090、直前の投稿1件・1時間・10行で決める matched_followup）。

## 1. PO の決定
- 2026-10-10「y」: 〆の投稿は「その仕入元のいまの在庫」と照らし、数が合うときだけ決める方向で設計する。
- 2026-10-10: 試算を見て、さかのぼる時間は 48 時間（「72時間は遡りすぎ」→24h と比較→「検索範囲を48時間以内に変更」）。
- 2026-10-10「y」: 複数を指す言葉 4 語（両方・全部・全て・どちらも）を public.knowledge_rules（category=followup_plural_word）に登録する。本便ではこの言葉がある〆は決めない（要確認）。
- 対象外（PO 確認待ち・別便）: 決まった〆で前の在庫情報を残したまま状態・数量だけ変える書き方（前の価格を写すか）。

## 2. v102 の流れ（事実）
- 件ごとの〆の判定: backend/app/services/gemini_raw_copy_v101.py:846 `status, effect = resolve_status_v2(block, ctx.status_entries, raw_memo=block)`。〆＝`status_effect == "excluded"`（同ファイル :163-164 `_is_sold_out` と同じ判定）。
- 〆の言葉の一覧: backend/app/services/gemini_raw_copy_v101.py:326-330 `_sold_out_words`（status_entries の effect=EXCLUDE・match_type=LITERAL）、:333 `build_context` が `V101Context.sold_out_words` に入れる。
- 商品を決める段の順: backend/app/services/gemini_raw_copy_v101.py:1159 `_extract_v102` → :1198 `_apply_context_work` → `_apply_followup`（:1055-1077、人が決めた件 fixed_products は上書きしない）。
- 前便の部品: backend/app/services/gemini_raw_copy_v102_followup.py:42 `build_reference_lines`、:54 `extract_tokens`、:61 `unit_words`、:70 `_is_clue`、:76 `_hits`、:90 `_decide_one`、:115 `decide_followup`。
- 直前の投稿を読む関数: backend/app/services/line_analysis_v102_svc.py:701-738 `load_followup_reference`（同じ supplier_channel_id、line_posted_at が前、is_active を問わない）、:741 `masters_with_followup`、呼び出し :782（run_v102_analysis）と backend/app/tools/prompt_ab_recompute.py:80-81。
- 商品照合: backend/app/services/gemini_raw_copy_v102_product_first.py:248 `match_text_g2`。複数語の読み込み :111-115（knowledge_rules）・:268。
- 書き込み: backend/app/services/line_analysis_v102_svc.py:533 `_RESOLVED_MATCH_STATUSES`、:536 `_analysis_values`（pid_basis=`V102:<match_status>`）。
- **1件＝1行**: backend/app/services/line_analysis_v102_svc.py:487-506 `_map_to_rows` は v102 の件と extraction_items を1対1で対応させ、数が違えば `_MappingError`。:638 `_write_results` は extraction_item_id ごとに UPSERT 1回。→ 1件から複数の商品の行を出すには書き込みの作りを変える必要がある。本便は1商品に決まる〆だけを扱う。
- ADR-158: backend/app/services/tcg_analyzer_svc.py:1744 `_merge_supplier_products` は同じチャンネルの全投稿で (商品,状態) ごとに最新を is_current にする。期間の制限は無い。配信側の期間は backend/app/services/tcg_distribution_svc.py の max_age_hours（既定0＝制限なし）。

## 3. 試算（手元・社外秘、~/CC報告ファイル-keep/session-20261007b/shime-inventory-sim/）
- 対象: source_messages の写し 2,329 投稿（2026-08-28〜10-09）。〆の言葉を含み、その行だけで商品が1つに決まらない行 1,626。
- sim → sim2 → sim3 で規則を直した（opus-verify.md）。sim3-48h：決まる 37（1商品 34・複数 3）、決めない 1,589（語なし 1,460・当たり0 116・数が合わない 11・すでに〆 2）。72h との差 0。
- Opus の原文照合（決まる行を全件）: 違う商品 0、一部だけ 2（1行に2商品の〆、ドラゴンボールの ST01 漏れ）、判断できない 1。
- 1日以上前の投稿への〆（本番 SELECT で確認）: むらお 32h25m・oyama 38h32m・ヨシヤス 24h23m。三海・シンソクの 2 回目の〆は間に投稿 0 件。
- 試算と本実装の違い: 試算は行単位・状態ごとの消し込み。本実装は件単位（件の行の結合）・商品単位の消し込み（§design 2-4）。件数は実装後に同じ写しで測り直す。

## 4. 本番の今
- 本番の解析は v6（docker-compose.yml の `LINE_ANALYSIS_ENGINE=${LINE_ANALYSIS_ENGINE:-v6}`）。本便は本番の配信を変えない。
- knowledge_rules の followup_plural_word は 0 行（登録は本便と並行で、データ変更として行う）。
