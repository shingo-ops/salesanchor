# ADR-1021: バルク系の商品で状態語が無いときは状態「Bulk」（配信可）にする。価格は1枚単価にそろえ、セット情報は備考に出す（価格は便2）

| 項目 | 内容 |
|------|------|
| ステータス | Proposed（便1 の実装 PR 付き。KGI B1〜B3 と便2 の KGI は PO 承認待ち） |
| 備考 | PO 2026-10-16「バルク商品の状態として新しく『バルク』を作り配信に出す」y。同日、KGI と実装開始 y（便1 のコードとマスタ行の SQL まで）。マスタ行の本番投入は Opus が DRY-RUN → COMMIT で行う |
| 起案日 | 2026-10-16 |
| 方針の決定者 | Shingo（PO） |
| 関連 | ADR-1007（値は migration でなく記録した SQL で入れる）、ADR-093・ADR-099・ADR-100（在庫・解析の土台）、ADR-1014（在庫表は配信行を見せる）、ADR-1019（閲覧ページ）、ADR-027（i18n。新しい文言なし）、ADR-1015（区分 A） |

---

## What（何を決めたか）

1. 商品区分がバルク系（public.tcg_product_categories の kubun_type「バルク系」）の商品で、状態語が無く、今は FLAG_SINGLE かつ basis が「R4:単位既定:単位不明」になる行は、状態を **Bulk** にする。basis は「R6:バルク既定」（R4 で始めない＝買取換算の候補に入れない）。
   - 状態語で決まった行（R1:PSA など）は変えない。バルク系以外と商品が決まらない行も変えない。
2. 状態 Bulk はマスタ public.line_conditions の1行（code=CN0014、effect=OUTPUT、priority=10、is_active=true、app_kubun 空、match_type=KEYWORD、search_kw 空、unit_id NULL）。search_kw が空の KEYWORD 行はどの文にも当たらず、コードの R6 分岐だけが返す。DEFAULT は常に当たるので使わない。
3. マスタ行は migration で入れず、docs/handoff/g28-bulk-price/data/ の SQL（dry_run → commit → verify、戻しは rollback）で入れる（ADR-1007）。
4. マスタ行が無いとき、コードは従来どおり Error に落ちる（安全側）。
5. 価格（便2）: 単価を1枚の値段にそろえ、セット情報は備考に出す。便2 は別の設計・別の PR で行う（本 ADR は方針だけを決める）。

## Why

- 今のバルク系の配信は0行。48時間以内の現行行は v102 の Error 8行だけで、全件要確認（docs/handoff/g28-bulk-price/recon.md §1）。語が無いだけで Error になり、配信に出ない。
- バルクは「状態の違いがほぼ無い束売り」で、箱・単品の状態語になじまない。PO が独立した状態を決めた。

## 便2 価格の決まり（2026-10-16 追記。設計: docs/handoff/g28-bulk-price/design.md「便2」）

PO 承認済みの KGI（価格は1枚の値段・まとめ売りは備考「N枚セット単位（1セットX円）」・決まらない行は配信しない・バルク以外は変えない・2回に分けて反映）の実装の決まり。

1. 規則は純関数モジュール backend/app/services/v102_bulk_price_svc.py（`convert`）に置く。投稿の原文ブロック（件の source_lines の行を改行でつないだもの）から piece（価格は1枚の値段）/ set（価格は1セット N 枚の値段）/ review（決まらない）に分ける。
2. 呼ぶのは line_analysis_v102_svc.py の `_write_results` の1か所（`_analysis_values` の直後・人の手直しの前）。対象は product_category がバルク系かつ商品が決まった行。状態（Error 等）は問わない。
> 追記（ADR-1027）: set の換算（3）は ADR-1027 で置き換え（piece・review はそのまま）。
3. set: 単価 = 価格 ÷ N（割り切れなければ review）、数量 = 数量 × N、単位 Piece（unit_id・unit_resolved もそろえる）、備考 note_ja =「N枚セット単位（1セットX円）」（X は3桁区切り）、price_basis = `V102:bulk:set:N`。
4. piece: 価格・数量はそのまま、単位だけ Piece にそろえる、備考なし、price_basis = `V102:bulk:piece`。
5. review: 値は変えず、理由 `bulk_price_basis_unknown` を足して needs_review=true。「このままで良い」では外せない（NON_ACKABLE）。人が価格か数量を直した行は、この理由だけ外れる。Piece の単位 id が引けないときも review（id を作らない）。
6. 価格の引き継ぎ（`_inherit_price`）はバルク系を対象外にする（別サイズのセット価格が混ざるため）。
7. analysis_results に note_en の列は無いので、英語側の備考は作らない。
8. 反映は2回: ①理由コードの行の投入と CN0014 無効のままのコード反映（バルクは状態 Error で配信されない）、②デプロイ確認後に CN0014 を有効化し、バルク行を含む job を再解析する。

## 戻し方

コードの PR を revert → Bulk で保存された行を reanalyze_v102_job でやり直す → rollback.sql でマスタ行を is_active=false にする（この順）。

## 維持の仕組み

単体テスト（バルク系の分岐・他区分の不変・Bulk 行が何にも当たらないこと、便2 の換算・要確認・人の手直し・引き継ぎ除外・NON_ACKABLE）が CI で毎回走る。
