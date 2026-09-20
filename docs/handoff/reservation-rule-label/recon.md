<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# recon — reservation-rule-label

**仕事名**: reservation-rule-label  
**日付**: 2026-09-20  
**対象ADR**: ADR-027  
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/locales/ja.json:3846` | sidebar.dateRule = "日付ルール"（変更対象） |
| `frontend/src/locales/ja.json:3909` | dateRule.title = "日付ルール"（変更対象） |
| `frontend/src/locales/en.json:3846` | sidebar.dateRule = "Date Rules"（変更対象） |
| `frontend/src/locales/en.json:3909` | dateRule.title = "Date Rules"（変更対象） |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | 他箇所に「日付ルール」の表示文字列があるか | grep -rn "日付ルール" frontend/src/ で確認 | ✅ 解消済み（コメントのみ・翻訳ファイル外なし） |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

- `frontend/src/App.tsx:310` および frontend/src/pages/super-admin/components/DateRulesPanel.tsx:2、frontend/src/pages/super-admin/AnalysisRulesPage.tsx:5 にコメント内「日付ルール」が残っているが、画面非表示のため変更不要
- 内部キー名 dateRule は変更しない（コンポーネント名・i18nキーの変更は対象外）
