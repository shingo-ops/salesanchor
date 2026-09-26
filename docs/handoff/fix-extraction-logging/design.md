<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# 設計 — fix-extraction-logging

**対象ADR**: ADR-027  
**recon**: docs/handoff/fix-extraction-logging/recon.md  
**日付**: 2026-09-19  
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- 該当なし：`logger.error` → `logger.exception` は Python 標準ログの定型修正。外部事例参照不要。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 内側 except Exception に logger.exception が追加されている | `grep -n "logger.exception" backend/app/tasks/tcg_extraction.py` |
| ロジック変更なし | git diff で +1行のみ確認 |

---

## 技術 How・KPI

- KPI: デプロイ後、Celery ログに RECORD_WRITE_FAILED の traceback が出力されること
- 技術選択: `logger.exception()` を使用（`logger.error()` と異なり `exc_info=True` が自動付与される）

---

## 弊害・トレードオフ

- ログ量が増加するリスク → 対策: エラー時のみ出力のため通常運用に影響なし

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | line 182 に logger.exception 追加 | Generator |
| 2 | commit & push | Generator |
| 3 | PR 作成 | Generator |

---

## 継続

- 完了後の監視: デプロイ後 Celery ログで traceback を確認し、根本原因を特定
- 次フェーズへの引き継ぎ: traceback から判明した原因に応じて次 PR を起票

## 維持の仕組み

守り手: 人手で守る（コードレビュー時に except Exception のログ漏れを確認）
