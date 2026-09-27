# recon — knowledge-menu-connect

## 変更対象ファイル（パス:行番号）

### 1. AnalysisRulesSidebar.tsx
`frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx`

- 行10-33: `AnalysisRulesSidebarKey` union 型。`"extraction-rules"` の直後に `"knowledge-aliases"` を追加（行17-18）
- 行93-98: ルール管理グループの navItem 列挙。`extraction-rules` の後に `knowledge-aliases` を追加（行94-95）

### 2. AnalysisRulesPage.tsx
`frontend/src/pages/super-admin/AnalysisRulesPage.tsx`

- 行39-40: 既存コンポーネントのインポート群（eager import パターン）。`KnowledgeAliasesTab` を同パターンで追加
- 行200-201: `analysis-panel-content` 内の条件レンダリング群。`extraction-rules` の直後に `knowledge-aliases` を追加

### 3. i18n
- `frontend/src/locales/ja.json:4015` — `extractionRules` の直後に `knowledgeAliases` を追加
- `frontend/src/locales/en.json:4015` — 同上

### 4. 既存コンポーネント（変更なし）
- `frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx` — 接続先コンポーネント。変更対象外

## ADR 参照

- ADR-027: UI文字列 i18n 強制（`t("key")` 経由）
- ADR-144: UIガバナンス（金型クラス使用・生select/生input禁止）

## 検索結果

`KnowledgeAliasesTab` は既存コンポーネントとして存在済み。サイドバーへの接続のみ未実装。
