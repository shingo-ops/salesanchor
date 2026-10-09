# design: v102 で「分けて届く投稿」の商品を直前の投稿から決める

- 状態: 設計案（Opus 自己審査。独立した第二者レビューではない）。PO 決定 2026-10-09「y」の実装。
- 参照: docs/handoff/v102-followup-post-ref/recon.md、docs/adr/ADR-158-product-level-supersession.md、docs/adr/ADR-154。

## 1. 目的
同じ仕入元が続けて送った短い投稿（例：1通目に商品一覧、数十分後に「◯◯ 追加」）で、今の投稿だけでは商品が決まらない件を、直前の投稿で決まっていた商品から決める。

## 2. 規則（PO 承認済み、recon.md §1）
1. 直前の投稿 = 同じ supplier_channel_id の source_messages のうち、今の投稿より line_posted_at が前で最も新しい1件（is_active は問わない＝取り込みで無効化された投稿も含む）。時刻の差が 3600 秒以下のときだけ使う。
2. 今の投稿の空でない行（strip して空でない行）が10行以下のときだけ使う。
3. 直前の投稿の「参照行」= 直前の投稿の raw_text を `split("\n")` した各行のうち、v102 と同じ商品照合（match_product_g2、照合文の作り方も resolve_product_first と同じ）で商品が1つに決まる行。
4. 今の投稿で match_status が unmatched / ambiguous の件について、件の行（item の lines）から
   - 型番: fold_for_match した行に `[a-z0-9]+(?:[-_.'・][a-z0-9]+)*` を当て、_strict_code_pattern が None でない語
   - 名前: 元の行に `[ァ-ヴー]{4,}|[一-龥々]{4,}|[A-Za-zＡ-Ｚａ-ｚ]{4,}` を当て normalize_for_match した4文字以上の語
   を取り出し、型番は参照行（fold 後）に厳格パターンで、名前は参照行（normalize 後）に部分一致で当たる参照行の商品を集める。
5. 集めた商品がちょうど1つなら決める。0なら決めない、2つ以上なら決めない。
6. 安全条件（試算の「疑い」A に対応）：今の件が ambiguous で、決める商品がその件の候補に無いときは決めない。
7. （2026-10-09 追加、PO「n、自動で更新が必要」）語の取り出しで、単位マスタの単位名・別名（v102 が単位の照合に使う表、SSOT）に一致する語と数字だけの語は手がかりにしない。残った語が0なら決めない。
8. （同）取り出した語が全て、決める商品の参照行のどれかに当たること。1語でも当たらない語があれば決めない（直前に無い商品名が混ざる件、例「30th CELEBRATION エーフィブラッキー〆」）。
9. （同）件の行に複数を指す言葉があれば決めない（例「30th 両方〆」）。言葉の一覧はコードに直書きせず、既存の表 public.knowledge_rules（migrations/058_create_knowledge_rules.sql:25-37、category 列に CHECK 制約なし、管理画面 backend/app/routers/super_admin_knowledge.py で追加・CSV 入出力可）の category=`followup_plural_word`・pattern_type=`substring`・is_active=TRUE の行の pattern を NFKC 後の件の行に部分一致で当てる。行が0なら本条件は働かない。行の登録は候補表を PO に見せて y を得てから、1回だけのデータ変更（precheck→dryrun→commit→verify・rollback あり）で行う（[[feedback_show_candidates_before_master_write]]）。
- 語は件の行（item の lines を連結した block）から取り出す（v102 は件単位。試算の行単位の近似で出た価格行の誤りは件単位では起きにくいが、§6 の再計算と原文照合で確かめる）。

### 2-1 測定（試算、行単位の近似、手元 ~/CC報告ファイル-keep/session-20261007b/followup-ref-sim2〜4/）
- §2-1〜6 だけ（sim2）：決まる 20 行。Opus が原文で全件照合 → 誤り：「BOX」の語で別商品 2（OP-09 の価格行が Pokemon GO）、直前に無い名前の混在 1（エーフィブラッキー）、「両方」1、行単位の近似による誤り 2。
- §2-7〜9 を足す（sim4、単位マスタは本番 public.unit_aliases/units を 2026-10-09 21:59 JST に取得）：対象 316 行 → 決まる 12・語なし 293・衝突 8・名前の混在 2・複数語 1。決まる 12 行は Opus が原文と参照行で全件照合し誤り 0（16 行中 12 行が〆の続き投稿、見出し「◆30th CELEBRATION」の3件も直下の BOX と確認）。

## 3. 変更
- 新しい部品 backend/app/services/gemini_raw_copy_v102_followup.py（純粋関数。DB を持たない）：参照行の作成・語の取り出し・決定（§2-3〜6）。定数 `MATCH_STATUS_MATCHED_FOLLOWUP = "matched_followup"`。
- backend/app/services/gemini_raw_copy_v101.py：`_apply_context_work` の後に、文脈に直前の投稿の参照があるときだけ適用する段を足す。決まった件は context work と同じく `build(i, product_id)` で作り直し、`match_status=matched_followup`、`product_followup={"ref_message_id", "ref_line", "tokens"}` を付ける。参照が無いときは何もしない（今の結果と同じ）。
- 直前の投稿を読む関数（DB）を1つ作り、`run_v102_analysis` と prompt_ab_recompute（測定用）の両方から同じ関数を呼ぶ：今の job の source_message から supplier_channel_id・line_posted_at・空でない行数を読み、§2-1・§2-2 を満たすときだけ直前の投稿の id と raw_text を返す。v6 の `load_extraction_context` は変えない。
- backend/app/services/line_analysis_v102_svc.py `_analysis_values`：matched_followup を matched_context と同じ扱い（product_id・pid_resolved=True・pid_basis=`V102:matched_followup`）。
- backend/app/services/line_analysis_v102_svc.py `load_v102_masters`：knowledge_rules の category=`followup_plural_word` の有効な pattern を読み、文脈に渡す（読み込みは1か所）。単位マスタの語は既存の `unit_alias_to_info`（load_lookup_maps）をそのまま使う（複製しない）。
- 触らない: 配信 SQL、ADR-158 のマージ、v6 経路、migration、画面、理由コード表（新しい理由コードは作らない）。

## 4. 代替案
- 直前の投稿の DB 上の結果（analysis_results）を読む：v6 と v102 で結果の形が違い、件の行の原文も DB に残らない（recon.md §2）ため採らない。原文（source_messages.raw_text、正本）とマスタから同じ照合でその場で作るので、データを写さない。
- 直前の投稿の時間窓を広げる：PO 承認は1時間・10行（試算で疑い 0）。

## 5. 弊害とリスク
| # | 弊害 | 対策 |
|---|---|---|
| 1 | 直前の投稿の商品に誤って決める | 1時間・10行・1商品だけ・ambiguous は候補内だけ。実装後に決まった件を Opus が原文で全件照合 |
| 2 | 価格の無い続きの投稿（残り数・完売）で商品が決まると、ADR-158 で前の価格の行が現在でなくなる | v102 は本番未使用（recon.md §4）。PO 追加要件（数量・状態だけ変える）は別便で設計 |
| 3 | 直前の投稿を読む DB 照会が1件増える | job ごとに SELECT 1〜2本 |

## 6. 受入基準
| 基準 | 検証方法 |
|---|---|
| 規則 §2 の各分岐（1時間超・10行超・参照なし・0商品・2商品以上・ambiguous で候補外・決まる）を単体テストで固定 | pytest（RED→GREEN） |
| 直前の投稿が無い・条件外の投稿では結果が今と同じ | 単体テスト＋保存応答の再計算で差0（対象外の投稿） |
| 決まった件は product_id・pid_resolved=True・pid_basis=V102:matched_followup | 単体テスト |
| 本番デプロイ後、保存応答の再計算 after26 と after25-post2 の差は matched_followup への変化だけ | compare_runs.py |
| 決まった件は Opus が原文で全件照合し、誤り 0 | 照合表（手元） |
| 既存テスト全て通る | CI |

## 7. 戻し方
PR を revert（データ変更なし）。

## 8. 維持の仕組み
- 守り手: backend/tests/test_gemini_raw_copy_v102_followup.py（規則の各分岐）と test_line_analysis_v102_svc.py の matched_followup のテスト（CI の backend tests が必須チェック）。

## 9. 外部・過去事例の参照と我々への応用
- 外部事例：該当なし（自社の投稿データでの試算で判断）。
- 過去事例（自社）：#4037「前後の商品で作品を決める」（matched_context）。同じ「作り直し」の型を使い、決まった根拠を件に残す。
