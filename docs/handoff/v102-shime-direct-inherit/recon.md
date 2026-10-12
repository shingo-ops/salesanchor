# recon: 商品名を書いた〆で、前の在庫の状態を引き継ぐ（便3）

- 調べた日: 2026-10-11。基準 origin/main 1af58612e（コード）・2605f6696（作業ブランチ起点）。
- 調査: コードの読み取りは Sonnet、本番は Opus が SELECT のみ（制限なし鍵、PO 常時許可の範囲）。原文照合は Opus。
- 社外秘: 仕入元の原文・行ごとの記録は repo に置かない（手元 `~/CC報告ファイル-keep/session-20261011-shime-ref/`）。ここには集計値と、仕入元を特定できない書き方の型だけを書く。

## 0. 既存 ADR の検索
- `git grep -il -E "soldout|〆|supersession" origin/main -- docs/adr/` → `docs/adr/ADR-158-product-level-supersession.md` のみ（README を除く）。
- ADR-158（Status: Proposed）: 在庫の最新は `analysis_results.is_current`、判定は `_merge_supplier_products`。実装の単位は (仕入元, product_id, condition_id)（`backend/app/services/tcg_analyzer_svc.py:1847-1852` `PARTITION BY c.product_id, c.condition_id`）。
- 前便: `docs/handoff/v102-shime-inventory-ref/`（#4106・便1）、`docs/handoff/v102-shime-multi-targets/`（#4115/#4117・便2。〆で商品が決まらない件にだけ、参照した在庫の状態を引き継ぐ＝規則11b）。

## 1. PO の要求
- 2026-10-11「〆も取得できるようになる」「既存のシステムが壊れることなく」「推測せず事実ベースでエビデンス確立」「根拠のない設計はしない」「確立したなら進める」。
- 2026-10-11 Opus の提案「①（商品名を書いた〆）を3条件付きで作る」に対し、PO は上記の方針文で返答（確立したなら進める）。

## 2. 今の作り（事実）
### 2-1. 商品名を書いた〆の件
- 状態の決定: `backend/app/services/gemini_raw_copy_v102_product_first.py:568` `_resolve_condition` → 件の `condition`・`condition_basis`（`backend/app/services/gemini_raw_copy_v101.py:923`）。〆の行に状態の語が無いと単位の既定（`R4:単位既定` 等）か未解決（FLAG_SINGLE）になる。
- 便1/便2 の〆の参照は `status_effect=="excluded"` かつ `match_status in ("unmatched","ambiguous")` の件だけ（`backend/app/services/gemini_raw_copy_v102_soldout_ref.py:128-133`）。商品名を書いた〆（matched）は対象外。
- 過去投稿の読み込みは無条件（`backend/app/services/line_analysis_v102_svc.py:982-984`）で、`_extract_v102` の `if soldout_posts:`（`backend/app/services/gemini_raw_copy_v101.py:1321-1325`）まで届く。
- 読み込む在庫は各投稿の最新 job の解析結果のうち Sold out 以外（`backend/app/services/line_analysis_v102_svc.py:893-905` `_STOCK_ITEMS_SQL`、`ar.status IS DISTINCT FROM :sold_out`）。Sold out の行は読み込まない。
### 2-2. 状態の書き換え（便2の部品）
- `backend/app/services/line_analysis_v102_svc.py:690-712` `_apply_soldout_targets`: 件の `soldout_targets[0]` の状態で上書き、`condition_basis='SOLDOUT_REF'`（:707）。人の判断（商品または状態）がある件は上書きしない（:700、`_has_human_judgement` :685-687）。
- `_extra_targets`（:715-721）は書いた行と違う相手だけを `analysis_soldout_extra_targets` へ。相手が1つで書いた行と同じなら書かない。
### 2-3. 配信
- `backend/app/services/tcg_distribution_svc.py:291-298`: `is_current` かつ `exclusion<>'excluded'` かつ価格あり等。〆の件は出ず、同じ (商品,状態) の古い在庫行は is_current でなくなって出ない。状態が違うと古い在庫行が残って出続ける。
### 2-4. 書かずに確かめる道具
- `backend/app/tools/prompt_ab_recompute.py`: DB を読むだけで抽出段（v102_items）まで再計算。書き込み段（`_apply_soldout_targets`）は通らない。
- `backend/app/tasks/tcg_extraction.py:824-832` `tcg.v102_reanalyze_after_correction` → `run_v102_analysis`: Gemini を呼ばず再計算するが DB に書き、配信予約まで行う。

## 3. 事実の測定（本番 SELECT のみ、2026-10-11 04:25Z）
### 3-1. 本番で起きている誤作動（v102、10/11）
- 「ガンダムGD01完売〆」→ 〆の件は Sealed box（`R4:単位既定`）で Sold out。前の投稿の在庫は Case 1カートン 75,000円で、is_current=TRUE のまま。配信条件の ar 側（pid/unit_resolved・exclusion・price・needs_review）を全て満たす。
- 対照: 「30THカードセット完売〆」（商品未決→便1/便2）は在庫の Sealed box を引き継ぎ、在庫行は is_current=FALSE になった（本番初の matched_soldout_ref、`analysis_soldout_extra_targets` は 0 行）。
### 3-2. 全件測定（保存済み解析結果 36,899 行 = v9 2,035投稿＋v102 83投稿、エンジン重複 0）
- 完売の件（商品あり）S = 900。状態が語で決まった S 19、SOLDOUT_REF 1、語で決まらない S 880。
- 880 のうち、同じ仕入元・前48時間に同じ商品で状態の違う在庫が「取り残される」S = 86（候補の状態が1種類 k=1 79・2種類以上 k≥2 7）。
- 86 件を Opus が原文で全件照合:
  - 「語で決まらなければ引き継ぐ」だけだと誤りが2件。①「〇〇 ボックス/¥… 完売」でパックの在庫を消す、②「〇〇 シュリあり〆切」でシュリンクなしの在庫を消す。どちらも〆と同じ状態の在庫が前にあった。
  - 「〆と同じ状態の在庫が前48時間に無い」かつ「k=1」に絞ると 53 件、全件が原文どおり正しい（誤り 0）。うち取り残しが今も is_current=TRUE は 13 件。
  - 決めない側: 同じ状態の在庫が前にある 27 件（今も最新 4）、k≥2 で同じ状態が前に無い 6 件（今も最新 1）。
- 取り残しの定義: 在庫行 R の投稿時刻より後〜〆の時刻までに、同じ (仕入元,商品,状態) の行（状態を問わない）が他に無い。
### 3-3. 対象外の型（別便。原文照合の結果）
- 同じ投稿で価格の行と「完売」の行が分かれる型（119組、今も最新 15）。真の誤作動は v102-f_c の1投稿4件と v9 の1件。残りは追加分・パック・ぺりぺり無など在庫として正しい行。f_ct で再発するかは未確認。
- 価格の無い在庫更新（「残2」等、243件）。〆の誤読・商品名だけの行・数量更新が混在。PO 決定（2026-09-29「前の値段を引き継ぐ」）の実装は未設計。
