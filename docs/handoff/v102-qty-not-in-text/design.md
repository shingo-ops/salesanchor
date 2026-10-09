# design: v102 の数量の写しが原文に無い件を要確認にする

- 状態: 設計案（Opus 自己審査。独立した第二者レビューではない）。PO の条件（recon.md §1、2026-10-08）の実装。
- 参照: recon.md §2-§4、docs/adr/ADR-154、docs/handoff/v102-prod-switch/design.md（便A の理由コード表に本コードを追加する）。

## 1. 目的
Gemini が写した数量の数字が、その件の行の原文に無いとき、黙って配信に流さず要確認にして理由を添える。

## 2. 変更（1か所の考え方だけ）
- backend/app/services/gemini_raw_copy_v101.py：件の要確認の理由を作る所（quantity_no_number を作る所と同じ関数・同じ条件）で、件の欄 `quantity_not_in_text` が True のとき理由 `{"kind": "quantity_not_in_text", "field": "quantity", "copied": <数量の写し>}` を足す（既存の review 要素の形に合わせる）。
- 判定は既存の `_quantity_not_in_text`（:781-792）をそのまま使う。新しい判定は作らない。
- line_analysis_v102_svc.py は変えない（review の kind は既に review_reasons に流れる：:507-518）。
- 触らない: 価格の判定、v6 の経路、migration、画面、配信。

## 3. 代替案
- 価格の部分一致を数の境目つきにする：行探しの結果が変わり得るため、別の便で測ってから（本件に混ぜない。変更は一度に1つ）。

## 4. 弊害
- 要確認が増える：手元の 147 投稿では 0 件の見込み（recon.md §4）。
- 理由コード表（便A）の初期行に `quantity_not_in_text` を足す必要がある → v102-prod-switch の便A で反映。

## 5. 受入基準
| 基準 | 検証方法 |
|---|---|
| 数量の写しの数が件の行に無い v102 の件に review kind `quantity_not_in_text`（field=quantity、copied=写し）が付く | 新規単体テスト（RED→GREEN） |
| 数量が件の行に在る件・数量 none の件・数字の無い件には付かない | 単体テスト |
| 付いた件は line_analysis_v102_svc の review_reasons に入り needs_review=True | 単体テスト |
| 既存の backend テストが全て通る | CI |
| 本番デプロイ後、手元の保存応答で再計算（after25）して after24 と比べ、quantity_not_in_text の件数が実装前の True 件数（0）と一致し、他の理由・決定の差が 0 | prompt_ab_recompute＋比較 |

## 6. 戻し方
PR を revert（データ変更なし）。

## 7. 維持の仕組み
単体テストが CI（backend tests）で毎回走る。

## 8. 外部事例
自社の正解表・保存応答での実測で判断する。外部事例は直接の根拠にならないため使わない。
