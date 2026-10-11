# design: v102 で「〆（完売）の件」の商品を、同じ仕入元の過去48時間の投稿から決める（便1：1商品）

- 状態: 設計案（Opus 自己審査。独立した第二者レビューではない）。PO 決定 2026-10-10（recon.md §1）の実装。
- 参照: docs/handoff/v102-shime-inventory-ref/recon.md、docs/handoff/v102-followup-post-ref/design.md（#4090）、docs/adr/ADR-158-product-level-supersession.md。

## 1. 目的
仕入元は完売を「30th〆」「エーフィブラッキー〆」「ストーム〆」のように略して送る。商品の検索ワードでは決まらないこれらの件を、人と同じく「この仕入元が最近どの投稿でその言葉の商品を出していたか」から決める。
- 成功の判定（○×）: 手元の写し 2,329 投稿で、本実装の判定関数が決める〆の件のうち、違う商品に決まった件が 0（Opus が原文で全件照合）。

## 2. 規則（PO 承認済み、試算 sim3-48h と同じ考え方）
1. 対象の件: 今の投稿の件のうち、`status_effect == "excluded"`（〆）かつ match_status が unmatched / ambiguous、落とした件（rejected）でなく、人が決めた件（fixed_products）でないもの。#4090 の matched_followup の段の後に当てる（followup で決まった件はそのまま）。
2. 参照する投稿: 同じ supplier_channel_id の source_messages のうち、line_posted_at が今の投稿より前で、差が 172,800 秒（48時間）以下のもの（is_active は問わない）。新しい順。今の投稿の行数の制限は無い。
3. 参照行: 参照する投稿の各行（`split("\n")`、空行込みの行番号）を match_text_g2 に通し、商品が1つに決まる行（status=matched）。その行に〆の言葉（`_sold_out_words`＝状態の表 EXCLUDE・LITERAL）が含まれれば「〆の行」、含まれなければ「在庫の行」。
4. 消し込み（商品単位）: 在庫の行より後（投稿の時刻順、同じ投稿の中は行順）に、同じ商品の〆の行があれば、その在庫の行は「すでに〆」。※試算は状態ごとの消し込み。本実装は商品単位にして、決める件を減らす側に倒す（違いは §6 の測定で数える）。
5. 手がかりの語: 件の行の結合（block）を NFKC し、複数を指す言葉（knowledge_rules の followup_plural_word。#4090 規則9 と同じ一覧）を含めば決めない。〆の言葉を取り除いてから #4090 と同じ方法（extract_tokens・単位の語と数字だけの語を除く）で語を取る。語が0なら決めない。
6. 決め方: 参照する投稿を新しい順に見て、「語が全て1つの参照行に当たる（型番は厳格パターン、名前は部分一致＝#4090 `_hits` と同じ当て方）」行を含む最初の投稿で止める（それより古い投稿へは進まない）。その投稿の当たり行のうち「すでに〆」でない在庫の行の商品が
   - ちょうど1つ → その商品に決める
   - 0（当たりが全て〆の行か、すでに〆の在庫の行）→ 決めない（すでに〆）
   - 2つ以上 → 決めない
   どの投稿にも当たらなければ決めない。
7. 安全条件（#4090 規則6 と同じ）: 今の件が ambiguous で、決める商品がその件の候補に無いときは決めない。

## 3. 変更（file:line は recon.md §2）
- 新しい部品 backend/app/services/gemini_raw_copy_v102_soldout_ref.py（純粋関数・DB を持たない）:
  - 定数 `MATCH_STATUS_MATCHED_SOLDOUT_REF = "matched_soldout_ref"`。
  - `SoldoutRefPost`（frozen: message_id: str, posted_at: datetime, raw_text: str）。
  - `RefRow`（frozen: post_index, message_id, line_no, product_id, folded, normalized, is_sold, order）と `build_ref_rows(posts, masters, sold_out_words) -> tuple[RefRow, ...]`（§2-3。posts は新しい順で受け、order は時刻の古い順の通し番号）。
  - `SoldoutRefDecision`（frozen: product_id, ref_message_id, ref_line, tokens）。
  - `decide_soldout_ref(extracted, lines, rows, *, units, plural_words, sold_out_words) -> dict[int, SoldoutRefDecision]`（§2-1・5〜7）。語の取り出しと当て方は gemini_raw_copy_v102_followup.py の `extract_tokens`・`_is_clue`・`_strict_code_pattern` を再利用する（複製しない）。
- backend/app/services/gemini_raw_copy_v101.py:
  - `_apply_soldout_ref(extracted, build, lines, masters, soldout_posts, unit_alias_to_info, sold_out_words, fixed_products)`：`_apply_followup`（:1055）と同じ形。決まった件は `{**build(i, product_id), "match_status": "matched_soldout_ref", "product_soldout_ref": {"ref_message_id", "ref_line", "tokens"}}`。fixed_products の件は飛ばす。
  - `_extract_v102`（:1159）: `_apply_followup` の後に、soldout_posts が空でないときだけ呼ぶ。
  - `extract_v101_items`（:1219）と `_extract_v102` に引数 `soldout_posts: tuple[SoldoutRefPost, ...] | None = None` を足し、docstring に1行足す。None・空なら今と同じ。
- backend/app/services/line_analysis_v102_svc.py:
  - 定数 `SOLDOUT_REF_MAX_GAP_SECONDS = 172800`。
  - `load_soldout_ref_posts(session, extraction_job_id) -> tuple[SoldoutRefPost, ...]`：今の投稿（_FOLLOWUP_CURRENT_SQL を再利用）の channel・時刻が無ければ空。あれば `SELECT id, line_posted_at, raw_text FROM {schema}.source_messages WHERE supplier_channel_id=:channel AND line_posted_at < :posted_at AND line_posted_at >= :posted_at - make_interval(secs => :gap) ORDER BY line_posted_at DESC, id DESC`。読み取りのみ。
  - `masters_with_followup` に引数 `soldout_posts=()` を足し、空でなければ `"soldout_posts"` キーを足す（run_v102_pipeline が extract_v101_items にそのまま渡す）。
  - run_v102_analysis（:782）と prompt_ab_recompute（:80-81）の両方から同じ `load_soldout_ref_posts` を呼ぶ。
  - `_RESOLVED_MATCH_STATUSES`（:533）に `MATCH_STATUS_MATCHED_SOLDOUT_REF` を足す（pid_basis は `V102:matched_soldout_ref`）。
- 触らない: 配信 SQL、ADR-158 のマージ、v6 経路、migration、画面、理由コード表、#4090 の規則（直前の投稿1件・1時間・10行）。

## 4. 代替案
- 本番の在庫（analysis_results の is_current）を参照する：v102 は本番未使用で v6 の結果と形が違い、件の行の原文も残らない（#4090 recon.md §2 と同じ理由）。正本の原文（source_messages.raw_text）とマスタから同じ照合でその場で作る。
- 72時間：PO が「遡りすぎ」と判断。48時間と 72時間の試算結果は差 0。
- 状態ごとの消し込み（試算どおり）：状態の判定を件の外の行に当てる部品が v102 に無い。商品単位にして決める件を減らす側に倒す。
- 複数の商品の〆（両方・全て・作品名＋全て）：1件＝1行の書き込み（recon.md §2）を変える必要があるので便2。本便では複数を指す言葉がある件は決めない。

## 5. 弊害とリスク
| # | 弊害 | 対策 |
|---|---|---|
| 1 | 古い一覧で違う商品に決める | 48時間・最初に当たる投稿で止める・すでに〆なら決めない・1商品だけ。§6 で原文全件照合 |
| 2 | 参照行の照合（match_text_g2）が重い（48時間で数十投稿・数千行） | 対象の件（〆で商品未決）が無い件では参照行を作らない（遅延）。§6 で1件あたりの時間を測る |
| 3 | 決まった〆で ADR-158 により前の価格の行が現在でなくなる | v102 は本番未使用。数量・状態だけ変える書き方は別便（PO 確認待ち） |
| 4 | 複数語が未登録だと「両方〆」で1商品だけ決まる | PO y の 4 語を本便と並行で登録（docs/handoff/v102-shime-inventory-ref/data/plural_words/） |

## 6. 受入基準
| 基準 | 検証方法 |
|---|---|
| §2 の各分岐（48時間超は見ない・最初に当たる投稿で止める・すでに〆・2商品以上・語なし・複数語・ambiguous で候補外・人が決めた件・〆でない件は対象外・決まる）を単体テストで固定 | pytest（RED→GREEN） |
| 決まった件は product_id・pid_resolved=True・pid_basis=V102:matched_soldout_ref | 単体テスト |
| 参照する投稿が無い・対象の件が無い投稿では結果が今と同じ | 単体テスト＋保存応答の再計算（after27-pre と post の差が matched_soldout_ref への変化だけ） |
| load_soldout_ref_posts が 48時間以内・同じチャンネル・前の投稿だけを新しい順で返す（is_active 問わず） | DB テスト（pg fixture） |
| 手元の写しで本実装の判定関数を回し、決まる件を Opus が原文で全件照合して違う商品 0。sim3-48h（34件）との差を全件説明 | 手元の測定スクリプト（社外秘、repo に置かない） |
| 既存テスト全て通る | CI |

## 7. 戻し方
PR を revert（コードのみ。データ変更なし）。複数語の4行は data/plural_words/rollback.sql。

## 8. 維持の仕組み
- 守り手: backend/tests/test_gemini_raw_copy_v102_soldout_ref.py（規則の各分岐）、test_line_analysis_v102_svc.py の matched_soldout_ref のテスト、load_soldout_ref_posts の DB テスト（CI の backend tests が必須チェック）。
- 48時間の値は定数1か所（SOLDOUT_REF_MAX_GAP_SECONDS）。

## 9. 外部・過去事例の参照と我々への応用
- 外部事例：該当なし（自社の投稿データでの試算 sim〜sim3-48h で判断）。
- 過去事例（自社）：#4090「分けて届く投稿」（matched_followup）、#4037（matched_context）。同じ「作り直し」の型と根拠の残し方を使う。
