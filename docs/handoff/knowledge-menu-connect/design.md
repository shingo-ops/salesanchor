# design — knowledge-menu-connect

## 変更概要

`KnowledgeAliasesTab`（既存コンポーネント）をLINE解析管理ページ（`/super-admin/analysis-rules`）のサイドメニューに接続する。

## 変更前後の差分

### AnalysisRulesSidebar.tsx

**変更前（型）:**
```
| "extraction-rules"
| "product-master"
```

**変更後（型）:**
```
| "extraction-rules"
| "knowledge-aliases"
| "product-master"
```

**変更前（ルール管理グループ）:**
```tsx
{navItem("extraction-rules", t("analysisRules.sidebar.extractionRules"))}
{navItem("prompt-config", t("analysisRules.sidebar.promptConfig"))}
```

**変更後:**
```tsx
{navItem("extraction-rules", t("analysisRules.sidebar.extractionRules"))}
{navItem("knowledge-aliases", t("analysisRules.sidebar.knowledgeAliases"))}
{navItem("prompt-config", t("analysisRules.sidebar.promptConfig"))}
```

### AnalysisRulesPage.tsx

**追加インポート:**
```tsx
import KnowledgeAliasesTab from "./KnowledgeAliasesTab";
```

**追加パネルレンダリング:**
```tsx
{activeSection === "knowledge-aliases" && <KnowledgeAliasesTab />}
```
（`extraction-rules` の直後に配置）

### i18n

| キー | ja | en |
|------|----|----|
| `analysisRules.sidebar.knowledgeAliases` | 抽出フィルタ / ルール | Extraction Filter / Rules |

## 受入条件テーブル

| # | 基準 | 検証方法 |
|---|------|----------|
| 1 | LINE解析管理ページのサイドメニューに「抽出フィルタ / ルール」が表示される | ブラウザで `/super-admin/analysis-rules` を開いてルール管理グループを確認 |
| 2 | メニュー項目クリックで `KnowledgeAliasesTab` が表示される | クリック後に右パネルの内容が変わることを目視確認 |
| 3 | `npm run build` がエラーなしで通る | CIログ確認（TypeScriptエラーゼロ） |
| 4 | `npm run lint` でエラー（error）がゼロ | lintログ確認（warnings は既存・許容） |
| 5 | ja/en 両方に `knowledgeAliases` キーが存在する | ja.json / en.json のキー一致確認 |

## 外部・過去事例の参照と我々への応用

既存サイドバーの他メニュー接続パターン（例: `extraction-rules` → `SupplierExtractionRulesPage`、`prompt-config` → `ExtractionPromptConfigTab`）をそのまま踏襲。新規実装なし。同一ファイル内の既存コードが事例。

## 維持の仕組み

- `AnalysisRulesSidebarKey` 型による静的チェック：存在しないキーを `navItem()` に渡すとTypeScriptコンパイルエラー
- ADR-027 ESLintルールによりハードコード日本語文字列は自動検出
- ADR-144: `hub-subnav-item` 金型クラスを使用しており、デザイントークン整合性が維持される
- 守り手: TypeScript型チェック（CI `tsc`）+ ADR-027 ESLint

## ADR 参照

- ADR-027: UI文字列 i18n 強制
- ADR-144: UIガバナンス

## 相互参照

- recon: docs/handoff/knowledge-menu-connect/recon.md
