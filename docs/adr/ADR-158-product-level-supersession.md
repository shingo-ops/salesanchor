# ADR-158: 商品単位の差分更新（Product-Level Supersession）

- **Status**: Proposed
- **Date**: 2026-09-24
- **Deciders**: しんごさん（PO）, Claude Opus（設計）

## Context

現在のパイプラインは「メッセージ単位の全入れ替え」方式。新メッセージが到着すると旧メッセージを全件 `is_active=FALSE` にし、配信クエリが `sm.is_active=TRUE` で JOIN するため、旧メッセージの商品は全て配信から消失する。

これにより「〆」だけのメッセージが来ると、その仕入元の全商品が配信から消える問題が発生する。PO指示: 「〆になった商品だけを消す。全商品は消してはいけない」。

### 根本原因

`source_messages.is_active` が2つの責務を兼ねている:
1. メッセージの最新性管理（どのメッセージが最新か）
2. 商品の配信可視性（どの商品を配信に含めるか）

## Decision

`analysis_results` テーブルに `is_current BOOLEAN NOT NULL DEFAULT TRUE` カラムを追加し、配信の可視性を商品単位で制御する。

### 変更概要

1. **Migration**: `analysis_results.is_current` カラム追加（DEFAULT TRUE で既存データは全て有効）
2. **マージ処理**: 解析完了後に `_merge_supplier_products()` を呼び、同一仕入元の旧 analysis_results のうち新メッセージにも存在する product_id の行を `is_current=FALSE` に更新
3. **配信クエリ**: `sm.is_active=TRUE` JOIN 条件を `ar.is_current=TRUE` WHERE 条件に変更
4. **レビュー・品質クエリ**: 変更なし（最新メッセージの抽出結果を見る目的で `is_active` を継続使用）

### 「〆」だけのメッセージが来た場合

1. 抽出結果0件 → status='empty' → 解析・マージ処理は呼ばれない
2. 旧 analysis_results の `is_current=TRUE` はそのまま → 配信に旧商品が残る

### 商品の部分更新

- 旧: 商品A(¥1000), 商品B(¥500)
- 新: 商品A(¥1100)
- 結果: 商品A → ¥1100（新データ）、商品B → ¥500（旧から継続）

## Consequences

### Positive
- 「〆」メッセージによる全商品消失を防止
- 仕入元が一部商品のみ更新しても、未言及の商品は配信に残る
- 既存のインポート・抽出フローは変更不要

### Negative
- 仕入元が2日間メッセージを送らない場合、古い商品データが残り続ける（既存の挙動と同じ・期限切れ機構は別途検討）

### 影響範囲

| ファイル | 変更 |
|---------|------|
| `migrations/` | `is_current` カラム追加 |
| `backend/app/services/tcg_analyzer_svc.py` | `_merge_supplier_products()` 追加 |
| `backend/app/services/tcg_distribution_svc.py` | 配信クエリ3箇所の JOIN/WHERE 変更 |
| `backend/app/services/tcg_condition_review_svc.py` | source_cte の配信用パスを is_current 対応 |

| ファイル | 変更なし（理由） |
|---------|----------------|
| `tcg_line_import_svc.py` | is_active は引き続きメッセージ管理用として使用 |
| `tcg_analysis_review_svc.py` | レビュー画面は最新メッセージの抽出結果を表示する目的 |
| `tcg_supplier_quality_svc.py` | 品質モニタリングも最新メッセージ基準 |

## References

- PO指示: 「全商品は消してはいけない、〆になった商品だけを消すが正解」（2026-09-24 セッション内）
- 現行の旧メッセージ無効化: `tcg_line_import_svc.py:425-436`
- 配信クエリ: `tcg_distribution_svc.py:213-251`
- 解析UPSERT: `tcg_analyzer_svc.py:1373-1468`（ON CONFLICT extraction_item_id）
- メッセージ整合設計: `docs/handoff/tcg-line-message-integrity/design.md`
