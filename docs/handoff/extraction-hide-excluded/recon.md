<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# recon — extraction-hide-excluded

**仕事名**: extraction-hide-excluded  
**日付**: 2026-09-28  
**対象ADR**: ADR-027  
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/services/tcg_analysis_dashboard_svc.py:190` | 直近抽出ジョブ10件取得クエリ（WHERE句なし） |
| `backend/app/services/tcg_analysis_dashboard_svc.py:209` | WHERE句追加箇所（status NOT IN ('empty', 'filtered')） |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | empty/filtered ステータスを直近ジョブから除くと何が表示されるか | ソース確認（:190-215） | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
