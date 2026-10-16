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

## 戻し方

コードの PR を revert → Bulk で保存された行を reanalyze_v102_job でやり直す → rollback.sql でマスタ行を is_active=false にする（この順）。

## 維持の仕組み

単体テスト（バルク系の分岐・他区分の不変・Bulk 行が何にも当たらないこと）が CI で毎回走る。
