# Recon: Product-Level Supersession (ADR-158)

## 調査日
2026-09-24

## 問題の発端

PO指示: 「〆になった商品だけを消す。全商品は消してはいけない」

現状のパイプラインは「メッセージ単位の全入れ替え」方式。新メッセージ到着時に同一仕入元の旧メッセージを全件 `is_active=FALSE` にし、配信クエリが `sm.is_active=TRUE` で JOIN するため旧商品が全消えする。

## 現行フロー

```
LINE受信
  └─ tcg_line_import_svc.py:425-436  # 旧メッセージ is_active=FALSE
       └─ tcg_gemini_svc.py           # 抽出
            └─ tcg_analyzer_svc.py:1373-1468  # analysis_results へ UPSERT
                 └─ tcg_distribution_svc.py:213-251  # 配信クエリ
```

## 調査結果: ファイル・行番号

| ファイル | 行 | 内容 |
|---------|---|------|
| `backend/app/services/tcg_line_import_svc.py` | 425-436 | 旧メッセージ is_active=FALSE 処理 |
| `backend/app/services/tcg_analyzer_svc.py` | 1373-1468 | analysis_results UPSERT (ON CONFLICT extraction_item_id) |
| `backend/app/services/tcg_distribution_svc.py` | 213-251 | 配信クエリ（sm.is_active=TRUE JOIN） |
| `backend/app/services/tcg_condition_review_svc.py` | - | source_cte() 配信用パス |

## 根本原因

`source_messages.is_active` が2責務を兼務:
1. メッセージ最新性管理
2. 商品配信可視性

## 既存ADR確認

- ADR-100: パイプライン設計（参照済み）
- `docs/handoff/tcg-line-message-integrity/design.md`: メッセージ整合設計（参照済み）
