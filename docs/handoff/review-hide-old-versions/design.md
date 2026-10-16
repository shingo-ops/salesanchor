# 要確認タブから旧解析版の行を外す — 設計（Opus, 2026-10-16）

状態: 設計案作成済み → 下の審査で APPROVE。PO 依頼「旧解析版は要確認には出さないようにしてくれ」(2026-10-16)。

**対象ADR**: ADR-158
**recon**: docs/handoff/review-hide-old-versions/recon.md

## 目的・KGI（○×で判定）
- K1 反映後、要確認タブ（status_tab=NEEDS_REVIEW）の行のうち prompt_version が `v102:` で始まらない行 = 0。
- K2 反映後、要確認タブの v102 行の件数 = 反映前の基準値（同時刻比較が無理なので、反映直前と直後に測り、差は新着投稿で説明できること）。
- K3 「全件」タブ・仕入元詳細・在庫表の行クリック（ID指定）は不変（旧版の行も今まで通り出る）。

## 現状（recon: ~/CC報告ファイル-keep/review-hide-old/recon/）
- 一覧は backend/app/services/tcg_analysis_review_svc.py の fetch_analysis_results（188-400）。条件は _build_where（87-151）。
  - NEEDS_REVIEW 条件 119-122 `(NOT ar.pid_resolved OR NOT ar.unit_resolved OR cr.needs_review)`。
  - review_only（138-141）は NEEDS_REVIEW 以外のタブで同じ条件を足す。
  - 件数 225-226・仕入元一覧 229-236・ページ 239-246・本体 302 が同じ where を使う。
  - 282 で既に `starts_with(ej.prompt_version, :v102_prefix)` を is_v102 として SELECT に出している（305 で V102_PROMPT_VERSION_PREFIX を渡す）。
- v102 の判定の正: line_analysis_v102_svc.py:82 `V102_PROMPT_VERSION_PREFIX = "v102:"`、:141 is_v102_prompt_version。v102_transcription_svc.py:58,74 も prompt_version の接頭辞で絞る前例。
- 本番: 旧版(v3/v5)で sm.is_active=t の行は 155、要確認の近似条件で 52（/tmp/CC報告ファイル/review-version/）。
- 同じ fetch を NEEDS_REVIEW で呼ぶ: tcg_review_csv_svc.py:75、tcg_review_sheet_svc.py:108（「画面の要確認一覧と同じ」設計）→ 同時に旧版が外れるのは意図どおり。
- ADR-158:63「レビュー画面は最新メッセージの抽出結果を表示する目的」— 矛盾しない。

## 変更（1ファイル＋テスト）
- tcg_analysis_review_svc.py の NEEDS_REVIEW 条件（119-122）を1か所で定義し、v102 の条件を足す:
  `(NOT ar.pid_resolved OR NOT ar.unit_resolved OR cr.needs_review) AND COALESCE(starts_with(ej.prompt_version, :v102_prefix), FALSE)`
  - review_only（138-141）も同じ定義を使う（文字列の重複を作らない）。
  - v102_prefix は V102_PROMPT_VERSION_PREFIX（新しい文字列直書き禁止）。件数(225)・仕入元一覧(229)・ページ(239)・本体(302) の全クエリに v102_prefix を渡す（今は本体だけ）。
- 触らない: _base_from（文字列一致テスト :223 があるため）、他タブ（ACKED・ALL・未登録系）、ID指定、ダッシュボードの needs_review_count（ar.needs_review 列で別定義・今回の対象外）、フロント。

## 代替案
- engine_version LIKE 'v102%'（v102_unit_price_check_svc.py:25）: 一覧は既に prompt_version 接頭辞を使い、定数・関数があるので不採用。
- 全タブで旧版を外す: 依頼は「要確認」。全件タブ・仕入元詳細は過去を見る用途もあるので対象外。必要なら別便。
- データ側で旧版を is_current=false にする: 不可逆に近く配信にも影響。不採用。

## リスク
- 件数クエリに v102_prefix を渡し忘れると SQL エラー → 実DBテストで件数・ページ・仕入元一覧を通す。
- CSV/シート出力の行が減る（意図どおり）。

## 受入条件
| 基準 | 検証方法 |
|---|---|
| 旧版の行は要確認に出ない・全件には出る | 新規 PG テスト: 旧版 prompt_version と v102 の要確認行を作り、NEEDS_REVIEW の items/total に v102 だけ、ALL には両方 |
| review_only でも同じ | 同テストで ACKED 等＋review_only |
| 既存テスト不変 | backend の該当テスト（test_tcg_analysis_review.py・test_tcg_condition_review.py・test_v102_human_decisions_pg.py・test_tcg_result_order.py・test_tcg_review_csv_svc.py・test_tcg_review_sheet_svc.py・test_tcg_is_active_filter.py）緑 |
| K1/K2 | 本番 backend コンテナで fetch_analysis_results(status_tab="NEEDS_REVIEW", limit 大) を読み取りで呼び、is_v102 別の件数を反映前後で記録 |

## 外部・過去事例の参照と我々への応用
該当なし：不要（既存の一覧の絞り込み条件を1つ足すだけで、手法の選択を伴わない）。

## 維持の仕組み
新規 PG テストが、旧版の行が要確認に戻ることを CI で止める。
守り手: backend/tests/test_tcg_condition_review.py

## 審査（Opus 自己審査・独立レビューではない）
APPROVE。根拠: 変更点は1関数・既存定数を使用・全クエリへの引数渡しを受入テストで確認。未解決: ダッシュボードの要確認件数（ar.needs_review 列）は旧版を含み続ける＝画面の数字と一覧の数がずれ得る（今もずれている。別件）。
