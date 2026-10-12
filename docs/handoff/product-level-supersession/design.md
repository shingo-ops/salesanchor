# Design: Product-Level Supersession (ADR-158)

## KGI

「〆」だけのメッセージが到着しても、同一仕入元の旧商品が配信から消えないこと。
PO画面（配信一覧）で旧商品行が残存していることで確認可能。

| 基準 | 検証方法 |
|------|---------|
| 「〆」メッセージ受信後、旧商品が配信クエリに残ること | APIレスポンスまたはSQL直接確認 |
| 新メッセージに含まれる商品のみis_current=FALSEになること | analysis_results テーブル直確認 |
| Migration適用後、全既存行がis_current=TRUEであること | SELECT COUNT(*) WHERE is_current=FALSE = 0 |

## 設計

### 変更方針

`analysis_results` に `is_current BOOLEAN NOT NULL DEFAULT TRUE` を追加し、配信可視性を商品単位で制御。

### 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `migrations/20260924_120000_add_analysis_results_is_current.sql` | is_current カラム追加 |
| `backend/app/services/tcg_analyzer_svc.py` | `_merge_supplier_products()` 追加・解析後に呼出 |
| `backend/app/services/tcg_distribution_svc.py` | 配信クエリ3箇所を is_current=TRUE 条件に変更 |
| `backend/app/services/tcg_condition_review_svc.py` | source_cte の include_inactive パラメータ追加 |

### 変更しないもの

| ファイル | 理由 |
|---------|------|
| `backend/app/services/tcg_line_import_svc.py` | is_active はメッセージ管理用として継続使用 |
| `backend/app/services/tcg_analysis_review_svc.py` | レビュー画面は最新メッセージ基準で正しい |
| `backend/app/services/tcg_supplier_quality_svc.py` | 品質モニタリングも最新メッセージ基準 |

## 外部・過去事例の参照と我々への応用

- **Soft Delete パターン（一般的なRDBMS設計）**: is_current フラグによる論理削除は、物理削除せずに参照履歴を保持する標準的なアプローチ。analysis_results に適用することで、旧データの追跡とデバッグが容易になる。
- **tcg-line-message-integrity handoff**: 過去にメッセージ整合性設計を行った際、is_active の責務分離を検討した経緯あり（`docs/handoff/tcg-line-message-integrity/design.md`）。今回はその設計をさらに具体化し、商品単位の粒度で実装。

## 維持の仕組み

守り手: しんごさん（PO）・パイプライン担当エージェント

- `is_current` の更新は `_merge_supplier_products()` のみが行う（他箇所での更新禁止）
- 配信クエリは `ar.is_current=TRUE` のみを条件とする（is_active への逆戻り禁止）
- ADR-158 を参照し、変更理由を必ず記録する
