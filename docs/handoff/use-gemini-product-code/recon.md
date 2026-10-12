# recon: Gemini resolved_product_code を pid 照合の第一候補に採用

## 調査対象ファイル

- `backend/app/services/tcg_analyzer_svc.py:1323-1354` — Gemini direct hit ロジック
- `backend/app/services/tcg_work_reference.py:13-16` — PRODUCT_ID_PROMPT_VERSIONS 定義

## 現状（調査済み事実）

### 既存実装 (コミット 749006586 / 2026-09-23)

`backend/app/services/tcg_analyzer_svc.py:1331` の Gemini direct hit チェック（変更前）:
```python
if gemini_product_id and gemini_product_id in product_code_to_uuid:
    matched_code = gemini_product_id
    pid_basis = f"GEMINI_DIRECT|WORK:{work_id}|ID:{matched_code}"[:100]
```

- Gemini が返したコードを product_code_to_uuid（全商品マスタ）に含まれるかで検証
- unit kubun フィルタ（filtered_codes）を通さないため、種別誤りのコードが採用される可能性がある
- pid_basis が GEMINI_DIRECT|WORK:...|ID:... と長い形式

### 問題点

- filtered_codes は unit kubun でフィルタ済みの商品コードセット。Gemini が誤った unit kubun の商品コードを返した場合、product_code_to_uuid チェックでは通過してしまう
- pid_basis = "GEMINI" が指示の期待値だが、現在は詳細な複合文字列

## ADR 調査

- ADR-1001（public.products 統一後の analyzer 実装改善）: `backend/app/services/tcg_analyzer_svc.py:92` に参照あり

参照: `backend/app/services/tcg_work_reference.py:13-16` の PRODUCT_ID_PROMPT_VERSIONS 定義

## 変更対象

- `backend/app/services/tcg_analyzer_svc.py:1331-1333` — チェック条件と pid_basis を変更
- `backend/tests/test_tcg_work_matching_integration.py:1585` — v5 パスのテスト追加
