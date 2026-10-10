# design: v102 の〆（完売）で複数の商品・状態を完売にする（便2）

- 状態: 設計案（Opus 自己審査。独立した第二者レビューではない）。PO 2026-10-10「確立したなら進める」（recon.md §1）。
- 参照: docs/handoff/v102-shime-multi-targets/recon.md、docs/handoff/v102-shime-inventory-ref/design.md（#4106・便1）、docs/adr/ADR-158-product-level-supersession.md。

## 1. 目的と成功の判定
仕入元の「〇〇全て〆」「両方〆」「ドラゴンボール全て〆」を、人と同じく「直近にその言葉で出ていた在庫の行（商品×状態）を全部完売」と扱う。あわせて、〆で決まった件が、参照した在庫の行の状態（例: シュリンク無し）を引き継ぐようにする（便1の穴、recon.md §3）。

| KGI（○×） | 判定 |
|---|---|
| G1 本番の全投稿で新しい判定関数を回し、決まった〆の完売の相手（商品×状態）のうち違うものが 0 | Opus が原文と保存済みの解析結果で全件照合（§7 の測定） |
| G2 便1で決まっていた34件の商品が1件も変わらない | 測定の突き合わせ（差 0） |
| G2b 1回目の測定（2026-10-10）で見つかった「ストーム シュリ有り〆」がシュリンク無し（No shrink box）を相手にしない | 測定 |
| G3 「ドラゴンボール全て〆」が、直前の在庫のドラゴンボールの商品（id 226・227）を完売の相手にする | 測定 |
| G4 「30th 両方〆」は自動で決めない（相手の1行が商品未決のため） | 測定 |
| G5 完売の相手の在庫の行が、在庫一覧（is_current）から外れる。〆より新しい在庫の投稿が来たら戻る | DB テスト |

## 2. 規則（便1 の規則 1〜7 に足す。番号は便1の design §2 と続ける）
8. 複数を指す言葉（knowledge_rules followup_plural_word。今は 両方・全部・全て・どちらも）を含む〆の件も対象にする（便1の規則5「決めない」を置き換える）。語を取る前に〆の言葉に加えて複数を指す言葉も取り除く。
9. 作品名: 〆の件の文字（normalize_for_match）に、有効な中分類（type_master is_active=TRUE）の name_ja か name_en（normalize_for_match）が含まれ、かつ複数を指す言葉を含むときだけ「作品名の〆」。含まれる中分類が2つ以上なら決めない。作品名の〆では、その作品名と同じ名前の語は手がかりの語から外し、参照行のうち商品の中分類（products.work_id）がその中分類の行だけを当たりの候補にする（残った語があれば、それも全て当たること）。作品名の〆でないときは手がかりの語が0なら決めない（便1と同じ）。
10. 最初に当たる投稿で止める（便1の規則6と同じ）。その投稿の当たりの在庫の行（すでに〆でない）について:
    - 複数を指す言葉なし: 商品がちょうど1つのときだけ決める（便1と同じ）。
    - 複数を指す言葉あり: 商品が1つ以上なら決める。ただし作品名の〆でないときは、その投稿の行のうち「〆の言葉を含まず、語が全て当たるのに商品が決まらない行」が1つでもあれば決めない（「30th 両方〆」で片方だけ完売にしない）。
    - 件が ambiguous のときは、決める商品が全てその件の候補にあること（便1の規則7を複数に広げる）。
11. 完売の相手（商品×状態）: 当たりの在庫の行ごとに、その投稿の保存済みの解析結果（その投稿の最新の job の extraction_items × analysis_results、pid_resolved かつ status が 'Sold out' でない行）のうち、件の行番号（v102 は source_lines、v6 は line_start〜line_end）にその行番号を含み、商品が同じ行の (product_id, condition_id) を相手にする（行の順、重複は最初だけ）。
    - 複数を指す言葉あり: 相手が見つからない在庫の行が1つでもあれば決めない。
    - 複数を指す言葉なし: 相手が見つからない在庫の行があれば相手は空（便1と同じ決め方、状態は〆の行の文字から）。
11b. 状態の絞り込み（2026-10-10 の1回目の本番測定で追加。「ストーム シュリ有り〆」で同じ商品のシュリンク無しまで相手にした誤りの再発防止）:
    - 〆の件の状態が「文字の語で決まった」とき（condition_basis から先頭の「単品語あり・要確認(…),」と「R4c:商品分類既定>」を除いた残りが、`R<数字>:<語>`（`R4:単位既定…`・`R5:パック既定` を除く）・`R3:MEMO:<語>`・`EMPTY_BOX:explicit` のいずれか）: 相手のうち、状態の canonical が〆の件の状態と同じものだけを残す。残りが0なら、複数語なしは相手を空（商品だけ決める）、複数語ありは決めない。
    - 〆の件の状態が語で決まっていないとき: 同じ商品の相手の状態が2つ以上なら、複数語なしは相手を空（商品だけ決める）、複数語ありは全部残す（「両方〆」「全て〆」は全ての状態）。
12. 書き込み: 〆の件の行（analysis_results 1行）は相手の1つ目の商品・状態にする（condition_basis='SOLDOUT_REF'）。2つ目以降は新しい表 analysis_soldout_extra_targets に1組1行で書く。人の判断（商品または状態）がある件は相手を使わない（人の判断が優先。便1と同じ）。先頭の相手の状態が FLAG_（未決）のときは状態だけそろえ、要確認の理由は外さない。
13. 在庫一覧（ADR-158 マージ）: analysis_soldout_extra_targets の組を「その〆の件と同じ投稿・同じ計算時刻の行」として順位付けに加える（仮の行。is_current の更新は本物の行だけ）。組の単位 (product_id, condition_id) は変えない。

## 3. 変えない範囲
配信 SQL、本番タブ・投稿タブ・訂正の画面と API、extraction_items、analysis_results の列と一意制約、v6 の解析、#4090 の規則、48時間（SOLDOUT_REF_MAX_GAP_SECONDS）、複数を指す言葉の表の中身（knowledge_rules）、理由コード表、フロントエンド（変更なし）。

## 4. 便2-1: 表を作る（migration のみ）
- 新規 migrations/20261010_120000_create_analysis_soldout_extra_targets.sql:
```sql
-- 便2-1（docs/handoff/v102-shime-multi-targets/design.md §4）。構造のみ。値の操作は含めない（ADR-1007）。
CREATE TABLE IF NOT EXISTS public.analysis_soldout_extra_targets (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_result_id UUID NOT NULL REFERENCES public.analysis_results(id) ON DELETE CASCADE,
    product_id         INTEGER NOT NULL,
    condition_id       INTEGER NOT NULL,
    ref_message_id     UUID NOT NULL,
    ref_line           INTEGER NOT NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (analysis_result_id, product_id, condition_id)
);
CREATE INDEX IF NOT EXISTS analysis_soldout_extra_targets_pair_idx
    ON public.analysis_soldout_extra_targets (product_id, condition_id);
COMMENT ON TABLE public.analysis_soldout_extra_targets IS 'v102: 1つの〆の件が完売にする2つ目以降の (商品, 状態)。1つ目は analysis_results の行そのもの。ADR-158 のマージが仮の行として順位付けに使う';
COMMENT ON COLUMN public.analysis_soldout_extra_targets.ref_message_id IS '根拠: 参照した在庫の投稿 source_messages.id';
COMMENT ON COLUMN public.analysis_soldout_extra_targets.ref_line IS '根拠: 参照した在庫の行番号（1始まり）';
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='salesanchor_app') THEN
        GRANT SELECT, INSERT, DELETE ON public.analysis_soldout_extra_targets TO salesanchor_app;
    END IF;
END $$;
```
- product_id・condition_id に外部キーを付けない理由: analysis_results.product_id にも外部キーが無く（recon.md §2-2）、値は analysis_results の保存済みの行から写すだけのため。消える経路は analysis_results の削除（CASCADE）に揃える。
- scripts/run_all_migrations.sh の末尾（:897 の次）に1行コメント＋`run_sql migrations/20261010_120000_create_analysis_soldout_extra_targets.sql`。
- この便ではコードを変えない（表は空のまま）。デプロイ後に表・索引・権限を本番で確認してから便2-2 を出す（recon.md §2-7 のデプロイの順番のため）。

## 5. 便2-2: コード
### 5-1. backend/app/services/gemini_raw_copy_v102_soldout_ref.py（純粋関数）
- 追加: `StockItem`（frozen: lines: frozenset[int], product_id: int, condition_id: int）、`SoldoutTarget`（frozen: product_id, condition_id, ref_message_id: str, ref_line: int）、`WorkName`（frozen: work_id: int, names: tuple[str, ...]）。
- `SoldoutRefPost` に `stock_items: tuple[StockItem, ...] = ()` を末尾に足す（既定値で既存の呼び出しは変わらない）。
- `SoldoutRefDecision` に `targets: tuple[SoldoutTarget, ...] = ()` を末尾に足す。複数のとき product_id は targets[0].product_id。
- `decide_soldout_ref(extracted, lines, rows, *, units, plural_words, sold_out_words, posts=(), works=(), product_works=None)`：posts は build_ref_rows に渡したのと同じ並び（新しい順。RefRow.post_index がその添字）、product_works は product_id → work_id。規則 8〜11 を `_decide_one` に入れる。50行を超えるなら、作品名の判定・投稿の未決行の検査・相手の対応付けを小さな関数に分ける。
- 語の当て方・正規化は既存の `_row_hits_all`・`extract_tokens`・`_is_clue`・`normalize_for_match`・`fold_for_match` を使う（複製しない）。

### 5-2. backend/app/services/gemini_raw_copy_v102_product_first.py
- `ProductFirstMasters` の末尾に `work_names: tuple[WorkName, ...] = ()` を足し、読み込み（:268-269 付近）で `SELECT id, name_ja, name_en FROM public.type_master WHERE is_active = TRUE ORDER BY id` を読んで入れる（name_en が NULL・空なら除く）。WorkName の定義場所は循環 import にならない方（product_first 側に置き、soldout_ref が import）を実装者が選び、報告する。

### 5-3. backend/app/services/gemini_raw_copy_v101.py `_apply_soldout_ref`（:1087-1110）
- `decide_soldout_ref` に posts=soldout_posts、works=masters.work_names、product_works={e.product_id: e.work_id for e in masters.product_entries}（ProductEntry の id の列名は実物に合わせる）を渡す。
- 決まった件に、targets があれば `"soldout_targets": [{"product_id", "condition_id", "ref_message_id", "ref_line"}, …]` を足す（product_soldout_ref はそのまま）。

### 5-4. backend/app/services/line_analysis_v102_svc.py
- `load_soldout_ref_posts`（:755-768）: 投稿を読んだ後、1回の SELECT でその投稿たちの在庫の件を読み、各 SoldoutRefPost の stock_items に入れる:
```sql
SELECT ej.source_message_id, ei.source_lines, ei.line_start, ei.line_end, ar.product_id, ar.condition_id
FROM {schema}.extraction_jobs ej
JOIN {schema}.extraction_items ei ON ei.extraction_job_id = ej.id
JOIN {schema}.analysis_results ar ON ar.extraction_item_id = ei.id
WHERE ej.source_message_id = ANY(CAST(:ids AS uuid[]))
  AND ej.id = (SELECT j2.id FROM {schema}.extraction_jobs j2 WHERE j2.source_message_id = ej.source_message_id
               ORDER BY j2.created_at DESC, j2.id DESC LIMIT 1)
  AND ar.pid_resolved = TRUE AND ar.product_id IS NOT NULL AND ar.status IS DISTINCT FROM 'Sold out'
```
  行番号: source_lines があればその集合、無ければ line_start〜line_end（どちらかが NULL なら空集合）。'Sold out' はコード内に既存の定数があればそれを使う。
- `_write_results`（:641-668）:
  - ループの前に、この job の件の analysis_results に付いた analysis_soldout_extra_targets を全て消す（job で絞る）。
  - `_UPSERT_SQL` に `RETURNING id` を足し、行の id を受け取る。
  - item に soldout_targets があり、その件に人の判断（商品または状態）が無ければ: values の condition_id・condition_canonical を targets[0] の状態にし（canonical は既存の `_load_condition_canonicals` で引く。引けなければ上書きしない）、condition_basis='SOLDOUT_REF'（定数 CONDITION_BASIS_SOLDOUT_REF）。書いた行の (product_id, condition_id) と違う targets を analysis_soldout_extra_targets に1組1行で入れる。
- `_load_resolved_pairs`（:690-701）: この job の analysis_soldout_extra_targets の組も UNION で返す（やり直しで消えた相手の在庫の行を戻すため）。

### 5-5. backend/app/services/v102_transcription_svc.py
- `_PAIRS_OF_ITEMS_SQL`（:85-87 付近）: 消す件の analysis_results に付いた analysis_soldout_extra_targets の組も UNION で返す（件を消すと CASCADE で相手も消えるため、先に読む）。

### 5-6. backend/app/services/tcg_analyzer_svc.py `_merge_supplier_products`（:1744-1854）
- :1779-1789 の new_pairs と :1800-1808 の touched_triples に、この job の analysis_soldout_extra_targets の組を UNION で足す。
- :1810-1827 の ranked: 候補を「本物の行（今と同じ条件）」と「仮の行（analysis_soldout_extra_targets の組。id=NULL、順位の鍵は親の analysis_results の行と同じ sm.received_at・ar.computed_at、同じ channel・touched の組だけ）」の UNION ALL にしてから順位を付ける。UPDATE は本物の行（id が NULL でない）だけ。
- extra の表が空なら結果は今と同じ（v6 は常に空）。

## 6. 代替案と選んだ理由
| 案 | 退けた理由 |
|---|---|
| A. analysis_results の一意制約を変えて1件に複数行 | 本番タブの行キー・訂正・状態確認が件の id 前提で壊れる（recon.md §2-3） |
| B. extraction_items に子の件を足す | 件数・並び・gemini_index を前提にする読み取りが約30か所（recon.md §2-4） |
| C. 在庫の行の is_current を直接 FALSE にする | 次のマージで順位から計算し直され上書きされる。正本（順位の計算）が2つになる |
| D. 便1・便2を1つの便で出す（表とコード同時） | デプロイはコンテナ起動が migration より先（recon.md §2-7）。表ができるまでマージが失敗する |
| 採用 E. 2つ目以降の相手だけを別の表に持ち、マージの順位付けにだけ加える | 読む箇所はマージと「前の組」の2か所だけ。1つ目は既存の行なので二重に持たない |
- 「両方」を「ちょうど2つ」と読む規則は入れない: 言葉ごとの意味を持つ欄が knowledge_rules に無く（normalized_to は別用途）、表に新しい値を入れるには PO の候補確認が要る。代わりに規則10の「語が当たるのに商品が決まらない行があれば決めない」で片方だけの完売を防ぐ。3つ以上に当たる「両方〆」は手元の 2,403 投稿で0件（試算の内訳、recon.md §3）。

## 7. 受入基準と検証
| 基準 | 検証方法 |
|---|---|
| 規則 8〜11b の各分岐（状態が語で決まった〆は同じ状態の相手だけ・語で決まらず同じ商品に状態が2つ以上なら複数語なしは相手を空・複数語ありは全部、作品名の〆で決まる・複数語なしの作品名は使わない・作品名が2つは決めない・複数語で語の当たる未決行があれば決めない・複数語で相手の無い在庫の行があれば決めない・複数語なしで相手が無ければ商品だけ決める・1商品2状態は相手2つ・ambiguous で候補外が混ざれば決めない・すでに〆は相手にしない） | pytest 純粋関数（RED→GREEN） |
| 書き込み: 親の行は targets[0] の状態・condition_basis='SOLDOUT_REF'、2つ目以降は表に1組1行、人の判断がある件は表に書かない、やり直しで古い相手が消える | pytest（DB） |
| マージ: 相手の組の古い在庫の行が is_current=FALSE、〆より新しい在庫の投稿で戻る、件を消すと戻る、表が空なら今と同じ | pytest（DB） |
| G1〜G4 | 本番コンテナで新しい判定関数を全投稿に当てる読み取り専用の測定（手元スクリプト・社外秘、repo に置かない）→ Opus が原文と保存済みの結果で全件照合 |
| 便2-1: 本番に表・索引・権限がある | デプロイ後に information_schema・pg_indexes・role_table_grants を SELECT |
| 便2-2: デプロイ後の v102 の投稿で extract_exception が増えない・マージのエラーが無い | デプロイ後に extraction_jobs.review_reasons と celery-worker のログを確認 |
| 既存テスト全て | CI |

## 8. 弊害とリスク
| # | 弊害 | 対策 |
|---|---|---|
| 1 | 違う在庫の行を完売にして配信から消す（最も害が大きい） | 規則10・11 の決めない条件、測定で全件照合（違い0でなければ出さない） |
| 2 | マージの SQL は v6 と共通 | 表が空なら今と同じことを DB テストで固定 |
| 3 | 表ができる前にコードが動く | 便2-1→本番確認→便2-2 |
| 4 | 投稿ごとに在庫の件を読む SELECT が1回増える | 同じ仕入元の48時間分だけ。測定で所要時間を記録 |
| 5 | 短い作品名が別の語に含まれる | 複数を指す言葉がある時だけ、作品名が2つなら決めない |

## 9. 戻し方
- 便2-2: PR を revert（コードのみ）。表に残った行はマージが読まなくなる。
- 便2-1: 表は空または未使用なら残してよい。消す場合は PO 確認のうえ DROP TABLE（不可逆操作の手順）。

## 10. 維持の仕組み
- 守り手: backend/tests/test_gemini_raw_copy_v102_soldout_ref.py（規則の分岐）、test_line_analysis_v102_svc.py / PG テスト（書き込みとマージ）。CI の backend tests は必須チェック。
- 正本: 1つ目の相手は analysis_results、2つ目以降は analysis_soldout_extra_targets（どちらも1か所）。作品名は type_master、複数を指す言葉は knowledge_rules。

## 11. 外部・過去事例の参照と我々への応用
- 外部事例: 該当なし。社内の投稿データと本番の解析結果の実測（recon.md §3）で判断する。
- 過去事例（自社）: #4106（便1）の「最初に当たる投稿で止める・決めない側に倒す・本番関数で全投稿を測る」をそのまま使う。#4075（便B）の「構造だけの migration を先に出す」型。
