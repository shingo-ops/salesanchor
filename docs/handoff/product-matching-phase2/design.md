# ADR-158 Phase 2 — Design

## KGI

| 基準 | 検証方法 |
|------|---------|
| 本番で pid_basis=RAWCODE が1件以上記録される | SELECT pid_basis, count(*) FROM public.analysis_results WHERE pid_basis LIKE 'RAWCODE%' GROUP BY pid_basis |
| v6ジョブ（raw-extraction-v6-rawcode-p1）が正常完了する | SELECT status, count(*) FROM public.extraction_jobs WHERE prompt_version='raw-extraction-v6-rawcode-p1' GROUP BY status |
| 既存v5ジョブの再解析で GEMINI/FALLBACK/NONE は変化しない | Phase 1 PO確認 + 本番ログ比較 |

## 変更概要

### Gemini v6 プロンプト（12列）
v5（11列）に RAW_PRODUCT_CODE を1列追加。Geminiが原文中の型番・製品コード（例: OP-14, SV8a）を原文のまま転記する。RESOLVED_PRODUCT_CODEとは異なり正準化せず原文字面のみ。

### Gate 1 マッチング
優先順位:
1. GEMINI + rawcode 一致 → GEMINI（変化なし）
2. GEMINI + rawcode 矛盾（＋filterコード内）→ RAWCODE_OVERRIDE（原文型番優先）
3. GEMINI 除外 + rawcode 有効 → RAWCODE または GEMINI_EXCLUDED|RAWCODE
4. Gemini なし + rawcode 有効 → RAWCODE
5. rawcode も除外語一致 → RAWCODE_EXCLUDED|KW_BASIS（キーワード照合）
6. rawcode なし → 従来のキーワード照合（FALLBACK|/GEMINI|/WORK_HEADER:|等）

### pid_basis プレフィックス一覧（本番モニタリング用）
- RAWCODE — 原文型番でマスタ直接一致
- RAWCODE_OVERRIDE — 原文型番がGemini解決と矛盾→型番優先
- GEMINI_EXCLUDED|RAWCODE — Gemini除外後に型番で一致
- RAWCODE_EXCLUDED|... — 型番一致だが除外語に引っかかり→KW照合
- GEMINI_EXCLUDED|RAWCODE_EXCLUDED|... — 両方除外→KW照合

## 外部・過去事例の参照と我々への応用
- Phase 1 (PR #3783): GEMINI_EXCLUDED 2件確認済み（アノテーションログで観測）。同パターンの安全ガード（exclude_keywords + unit kubun フィルタ）をGate 1にも適用する。
- 仕入元メッセージの型番は原文に "OP-14" "SV8a" 等の形式で明示されることが多い（TCGパイプライン実測）。Gemini が誤判定した場合でも型番が原文に残るためGate 1が救済できる。

## 守り手
- rawcode_to_id: mark と product_code 両方からビルド（product_code 優先）
- unit kubun フィルタ（filtered_codes）を Gate 1 にも適用
- exclude_keywords チェックを Gate 1 にも適用
- single_card_marker チェックは GEMINI パスのみ（Gate 1 は product_code/mark 直接一致なので不要）

## 維持の仕組み
- pid_basis の RAWCODE/RAWCODE_OVERRIDE/RAWCODE_EXCLUDED プレフィックスで本番モニタリング
- 既存テスト（test_tcg_work_id.py / test_tcg_work_matching_integration.py）が v6 フォーマットを検証
- WORK_ID_PROMPT_VERSIONS に v5 を残存させ後方互換を保証

## 影響範囲
- 呼び出し元: tcg_extraction.py（INSERT）、tcg_analyzer_svc.py（SELECT＋照合）
- DB: public.extraction_items.raw_product_code カラム追加（NULL許容・ADD COLUMN IF NOT EXISTS）
- 後方互換: v4/v5ジョブはDBの raw_product_code=NULL → Gate 1 スキップ → 従来と同一動作

## 戻し方
1. WORK_ID_PROMPT_VERSION を "raw-extraction-v5-product-p1" に戻す
2. WORK_ID_PROMPT_VERSIONS/PRODUCT_ID_PROMPT_VERSIONS を v5 のみに戻す
3. RAW_CODE_PROMPT_VERSIONS を削除
4. gemini_extraction_svc.py の v6 変更を revert
5. tcg_extraction.py の INSERT から raw_product_code を除去
6. tcg_analyzer_svc.py の Gate 1 ブロックを除去
7. extraction_items.raw_product_code カラムは DROP COLUMN（データ損失リスク→PO確認必須）

## 測り方
デプロイ後 24h で:
SELECT prompt_version, count(*) FROM public.extraction_jobs WHERE created_at > now() - interval '24h' GROUP BY prompt_version;
SELECT pid_basis, count(*) FROM public.analysis_results WHERE updated_at > now() - interval '24h' AND pid_basis LIKE 'RAWCODE%' GROUP BY pid_basis;
