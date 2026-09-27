# recon — knowledge-labels-fix

**仕事名**: knowledge-labels-fix
**日付**: 2026-09-27
**対象ADR**: ADR-093
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:44` | RULE_CATEGORIES に block_delimiter/skip_condition/status_keyword が未含有 |
| `frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:381` | t() の defaultValue: r.category によるフォールバック実装を確認 |
| `frontend/src/locales/ja.json:2456` | categories に message_exclude/message_exclude_no_digit は既存だが block_delimiter/skip_condition/status_keyword が欠落 |
| `frontend/src/locales/ja.json:2479` | pattern: 「変換前ワード」、normalizedTo: 「変換後ワード」 — 直感的でないため修正対象 |
| `frontend/src/locales/en.json:2456` | 英語版 categories 同様に3キー欠落確認 |
| `frontend/src/locales/en.json:2479` | pattern: "From word"、normalizedTo: "To word" — 修正対象 |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | RULE_CATEGORIES に追加対象カテゴリを確認 | `frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:44` 参照 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
