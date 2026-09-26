<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# recon — fix-extraction-logging

**仕事名**: fix-extraction-logging  
**日付**: 2026-09-19  
**対象ADR**: ADR-027  
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/tasks/tcg_extraction.py:93` | 外側 except Exception: logger.exception 確認済み |
| `backend/app/tasks/tcg_extraction.py:182` | 内側 except Exception: logger.exception 追加対象 |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | 内側 except が何の例外を握り潰しているか | logger.exception 追加で次回実行時に判明 | ✅ 解消済み（ログ追加で対応） |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

- 外側（line 93）は既に `logger.exception` 済み（Fix 1 は適用不要だった）
- 内側（line 182）のみ `logger.exception` を追加（Fix 2）
- ロジック変更なし・ログ出力のみ
