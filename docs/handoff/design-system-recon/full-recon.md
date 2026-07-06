# design-system 網羅recon

> この文書は何か: フロント見た目層を 5 問で漏れなく調べ、共通部品・自前実装・規約・KGI・CI の接点をまとめた記録。

測定時点:
- `origin/main` SHA: `cbaee615f7853b00278021f16cda9d4d1eb6ab5c`

## ① 現状のフロントはどう書かれているか

### frontend/src の構造

| top-level | files |
|---|---:|
| `pages` | 177 |
| `components` | 104 |
| `hooks` | 10 |
| `lib` | 10 |
| `constants` | 6 |
| `contexts` | 4 |
| `locales` | 2 |
| `utils` | 2 |
| その他（`api` / `App.tsx` / CSS / config / features / etc.） | 21 |

### 2階層の上位

| second-level | files |
|---|---:|
| `pages/dashboard` | 16 |
| `pages/design-preview` | 15 |
| `pages/inbox` | 14 |
| `pages/super-admin` | 14 |
| `components/loading` | 12 |
| `pages/company-detail` | 10 |
| `pages/integrations` | 10 |
| `pages/admin` | 8 |
| `pages/account-settings` | 6 |
| `pages/orders` | 6 |
| `pages/schedule` | 6 |
| `pages/register` | 4 |
| `pages/teams` | 4 |

### ファイル種別

| type | count |
|---|---:|
| `.tsx` | 242 |
| `.ts` | 49 |
| `.css` | 42 |
| `.jsx` | 0 |
| その他 | 3 |

### スタイルの持ち方

| 方式 | 観測値 | 補足 |
|---|---:|---|
| CSSファイル方式 | 42 files | `frontend/src/**/*.css` |
| CSS変数 `var()` 方式 | 148 files | `var(--...)` を含むファイル数 |
| TSX インライン色直書き | 0 hits | `style={{ ... }}` で hex を含む実ラインは 0 |
| CSS 生hex直書き（`index.css` / `tokens.css` 除外） | 0 hits | 実色ヒットは 0。残り 2 件はコメント由来 |

### raw grep の補足

- `#[0-9a-fA-F]{3,8}` の raw grep は 62 hits / 42 unique
- ノイズ除外後は 36 hits / 34 unique actual color
- ノイズ例:
  - `#1234`
  - `#145`
  - `#147`
  - `#164`
  - `#166`
  - `#2601`
  - `#2624`
  - `#888`
- ノイズの理由:
  - PR番号・ID文字列・コメント内断片
  - `#888` は URL エンコード由来のコメント

## ② 共用パーツはどう書かれているか

| 部品 | 金型ファイル | Storybook | ページ採用数 | KGI照合 |
|---|---|---|---:|---|
| プルダウン（Select） | `frontend/src/components/Select.tsx` | あり | 19 | KGI① / migration.md 行1 |
| 検索欄 | `frontend/src/components/InventorySearchBar.tsx` | あり | 11 | KGI① の候補 / migration.md 行2 |
| ボタン（Button） | `frontend/src/components/Button.tsx` | あり | 7 | KGI① / migration.md 行3 |
| アイコン | `frontend/src/constants/icons.tsx` + `frontend/src/constants/iconSizes.ts` | なし | 27 | KGI① の候補 / migration.md 行4 |
| テキスト書式（日付・金額） | 共通金型なし（ページローカル helper） | なし | 43 | KGI① の候補だが未集約 / migration.md 行5 |
| ページ骨格（PageLayout） | `frontend/src/components/PageLayout.tsx` | あり | 62 | KGI① / migration.md 行6 |
| カード（Card） | `frontend/src/components/Card.tsx` | あり | 2 | KGI① / migration.md 行7 |
| データ表（DataTable） | `frontend/src/components/DataTable.tsx` | あり | 22 | KGI① / migration.md 行8 |
| バッジ（Badge） | `frontend/src/components/Badge.tsx` | あり | 2 | KGI① / migration.md 行9 |
| 空状態（EmptyState） | `frontend/src/components/EmptyState.tsx` | あり | 1 | KGI① / migration.md 行10 |

### 観察メモ

- `EmptyState` は design-preview で 1 ページだけ採用されている
- 実ページの空状態は別実装がまだ残る
- `Select` / `PageLayout` / `DataTable` は採用面積が大きい
- `Text format` は共通金型が見当たらず、分散実装のまま

## ③ 共用でないパーツはどう書かれているか

### 素の見た目要素

| 種別 | raw件数 | 実件数 | 対象ファイル | ノイズ / 除外 |
|---|---:|---:|---|---|
| 素の `<h1>`（PageLayout 未使用） | 6 | 6 | `pages/company-detail/CompanyDetailPage.tsx`, `pages/login/LoginPage.tsx`, `pages/register/RegisterAddressPage.tsx`, `pages/register/RegisterChangeBillingPage.tsx`, `pages/register/RegisterPage.tsx`, `pages/schedule/SchedulePageImpl.tsx` | なし |
| 素の `<table>`（DataTable 未使用） | 28 | 28 | `pages/admin/ChannelMastersPage.tsx`, `pages/admin/InventoryVisibilityPage.tsx`, `pages/badges/BadgesPage.tsx`, `pages/buddy/BuddyPage.tsx`, `pages/commission-settings/CommissionSettingsPage.tsx`, `pages/company-detail/CompanyAddressesTab.tsx`, `pages/company-detail/CompanyContactsTab.tsx`, `pages/design-preview/sections/ModalSection.tsx`, `pages/design-preview/sections/TokenSection.tsx`, `pages/design-system/DesignSystemPage.tsx`, `pages/inventory/InventoryPage.tsx`, `pages/invoice-create/InvoiceCreatePage.tsx`, `pages/invoice-detail/InvoiceDetailPage.tsx`, `pages/products/ProductsPage.tsx`, `pages/purchase-orders/PurchaseOrdersFormModal.tsx`, `pages/quote-create/QuoteCreatePage.tsx`, `pages/quote-detail/QuoteDetailPage.tsx`, `pages/staff-reports/StaffReportsPage.tsx`, `pages/super-admin/DexTab.tsx`, `pages/super-admin/DiscordInboundPage.tsx`, `pages/super-admin/FxRatePage.tsx`, `pages/super-admin/InventoryOffersPage.tsx`, `pages/super-admin/KnowledgeAliasesTab.tsx`, `pages/super-admin/LLMBudgetTab.tsx`, `pages/super-admin/ParseReviewPage.tsx`, `pages/super-admin/ProductMastersTab.tsx`, `pages/super-admin/SuppliersAdminTab.tsx`, `pages/super-admin/TcgSeriesTab.tsx` | なし |
| 独自 card CSS | 0 | 0 | なし | なし |
| 独自 badge CSS | 0 | 0 | なし | なし |
| 空状態独自実装 | 5 raw / 3 actual | 3 | `pages/inbox/InboxMessageThread.tsx`, `pages/super-admin/DiscordInboundPage.tsx`, `pages/super-admin/FxRatePage.tsx` | `pages/design-preview/sections/EmptyStateSection.tsx` は shared component、`pages/design-preview/sections/registry.ts` はメタデータ |

### 生値直書き

| 種別 | raw件数 | 実件数 | 対象ファイル | ノイズ / 除外 |
|---|---:|---:|---|---|
| TSX インラインの色直書き | 38 raw / 14 files | 0 | なし | `style={{ ... }}` で hex を含む実ラインは 0。raw ヒットはコメント・ID・文字列断片が中心 |
| CSS 生hex（`index.css` / `tokens.css` 除外） | 2 raw | 0 | `frontend/src/components/FormField.css`, `frontend/src/components.css` | コメント内断片のみ |

### 3検品

- 検品A ノイズ除外: `#145` / `#147` / `#164` / `#166` / `#2601` / `#2624` / `#1234` / `#888` を除外
- 検品B 規約照合: `ADR-067` と `ADR-144` を参照
- 検品C KGI照合: これらは主に KGI①、色直書きは KGI②、関所は KGI⑤ に対応

## ④ 共用パーツのルールはどう書かれているか

### 関連ADR一覧

| ADR | 要点 | この recon への効き方 |
|---|---|---|
| ADR-022 | Meta Business Suite 風 UI と配色統一 | フロント全体の視覚方向 |
| ADR-033 | ライト/ダークテーマ切替、OS 依存を外す | `index.css` のテーマ変数運用 |
| ADR-061 | Inbox の Meta 風左パネル構造 | Inbox の見た目再設計 |
| ADR-063 | Inbox のページヘッダ + 全幅タブバー | ページ骨格の規約 |
| ADR-064 | Inbox 専用カラートークンを `index.css` に追加 | `--inbox-*` の根拠 |
| ADR-067 | デザイントークン SSOT / `:root` + `:root.force-dark` / 直書き禁止 | 色・トークンの中核規約 |
| ADR-073 | design-system KGI 100% ルーブリック | KGI①〜⑥ の正本 |
| ADR-087 | hub-shell 共通シェルレイアウト標準 | 共通 shell の骨格 |
| ADR-110 | Inbox カルテをリファレンスに一致させる是正 | visual gate の比較基準 |
| ADR-120 | ステータス→見た目の SSoT | バッジ色の一元化 |
| ADR-122 | Modal 標準部品への移行 | raw modal 置換の土台 |
| ADR-139 | ダッシュボードで DataTable / Storybook / visual 回帰を採用 | visual と共有部品の実運用 |
| ADR-144 | pages/ での生 UI 増殖を止める | 共通金型の採用圧 |
| ADR-149 | SubMenu の SSOT 集約とリンク型対応 | サイドメニューの共通化 |

### 規約照合メモ

- `ADR-067`: 現状の正本は `index.css` の `:root` / `:root.force-dark`。raw hex の実害はほぼノイズのみだが、TSX インラインの生hexは別途 lint 対象
- `ADR-073`: KGI① は migration.md の部品台帳全行が分母
- `ADR-144`: `Select` / `Button` / `PageLayout` / `Card` / `DataTable` / `Badge` / `EmptyState` は共通金型化の対象
- `ADR-061` / `ADR-063` / `ADR-064` / `ADR-110`: Inbox 系の構造・色・比較基準を縛る
- `ADR-122`: raw modal は標準 `Modal` に移行する流れ

### KGI対応

| 観測数字 | KGI | 判定 |
|---|---|---|
| 共有コンポーネントのページ採用数 | KGI① | 共有部品の分母・分子 |
| raw hex / inline 色直書き | KGI② | ページ側生値残存の指標 |
| 共有部品の採用面積 | KGI③ | 1件変更の波及確認 |
| カタログ掲載の有無 | KGI④ | 部品一覧の網羅性 |
| 関所の有無 | KGI⑤ | `design-token-guard.yml` / `ui-governance-gate.yml` 等 |
| 本テーマの索引と親子リンク | KGI⑥ | migration / README / handoff の導線 |

## ⑤ 共用パーツはどう維持されているか

### 見た目系の主要 workflow

| workflow | 何を検査するか | 何を検査しないか |
|---|---|---|
| `.github/workflows/design-token-guard.yml` | `frontend/src/**` の hex 増加をブロック | 既存 debt の解消や visual diff |
| `.github/workflows/frontend-check.yml` | `check:all` / `check:stories` / `check:new-tokens` / `tsc` / `stylelint` / unit test | 画像比較や docs の整合 |
| `.github/workflows/ui-governance-gate.yml` | pages/ の新規生 select/input/tab を止める | 既存の自前実装・色直書きの全体解消 |
| `.github/workflows/karte-gate.yml` | inbox / Karte の Playwright visual diff | それ以外のページの見た目全般 |
| `.github/workflows/process-artifacts-gate.yml` | ADR / recon / design doc / GO記録の書式 | UI 自体の見た目 |
| `.github/workflows/design-token-audit.yml` | 未使用トークンの週次監査（Issue 作成） | PR のブロック |
| `.github/workflows/workflow-lint.yml` | workflow yaml の改ざん検知・整合性 | app UI |
| `.github/workflows/active-work-lint.yml` | `active-work.md` の形式 | UI / token / visual |

### 補足

- `frontend-check.yml` は `check:css-colors` / `check:dark-parity` / `check:css-var-fallbacks` / `check:css-values` / `check:stories` / `check:stylelint` を内包
- `karte-gate.yml` は frontend 変更時に visual diff を走らせる
- `process-artifacts-gate.yml` は docs-only でも関係文書の書式を見張る

## 結論

- 共通金型は `Select` / `Button` / `PageLayout` / `DataTable` / `Badge` / `EmptyState` が揃っている
- `Search field` と `Text format` はまだ共通化が弱い
- `Index.css` の色正本は ADR-067 の通り維持されている
- raw hex の大半はノイズで、実害のある生hexは今回の採取では 0
- naked `h1` / `table` / empty state の自前実装はまだ残る
- 見た目を見張る関所は token / governance / visual / process-artifacts に分かれている

## 追補: 穴埋め（色の確定・ADR準拠・関所隙間）

### 追補1: 色の数の食い違いを確定

再測定時点:

- `origin/main` SHA: `cbaee615f7853b00278021f16cda9d4d1eb6ab5c`
- 同一条件の raw grep:
  - `grep -rEn "#[0-9a-fA-F]{3,8}\b" frontend/src --include="*.css" --include="*.tsx" --include="*.jsx" --include="*.ts" | grep -vE "frontend/src/(index|tokens)\.css" | wc -l`
  - 結果: `62`

仕分け結果:

| 区分 | hits | unique | 代表ファイル |
|---|---:|---:|---|
| 真の色hex | 36 | 34 | `features/schedule/calendars.config.ts` / `pages/roles/RolesPage.tsx` / `pages/dashboard/DashboardPage.tsx` / `pages/schedule/schedule-owner.ts` |
| ノイズ | 26 | - | PR番号・コメント・ID断片・URL エンコード断片 |

真の色hexの内訳:

| ファイル | hits | 内容 |
|---|---:|---|
| `frontend/src/features/schedule/calendars.config.ts` | 21 | 7 色セットの表示用定数 |
| `frontend/src/pages/roles/RolesPage.tsx` | 13 | 役割色パレット 12 件 + fallback 1 件 |
| `frontend/src/pages/schedule/schedule-owner.ts` | 1 | 既定オーナー色 fallback |
| `frontend/src/pages/dashboard/DashboardPage.tsx` | 1 | accent fallback |

ノイズの内訳:

| ファイル | hits | ノイズ種別 |
|---|---:|---|
| `frontend/src/App.tsx` | 1 | PR 番号コメント |
| `frontend/src/contexts/UiPrefsContext.tsx` | 2 | PR 番号コメント |
| `frontend/src/components/CompanyContactSelector.tsx` | 6 | PR 番号コメント |
| `frontend/src/components/ContactChannelForm.stories.tsx` | 1 | `user#1234` 文字列 |
| `frontend/src/components/MergeCompanyModal.tsx` | 4 | PR 番号コメント |
| `frontend/src/components.css` | 1 | PR 番号コメント |
| `frontend/src/pages/inbox/InboxMessageThread.tsx` | 1 | `(#2624)` コメント |
| `frontend/src/pages/deals/DealsPage.tsx` | 2 | PR 番号コメント |
| `frontend/src/pages/integrations/CarrierCredentialForm.tsx` | 2 | `(#2601)` コメント |
| `frontend/src/pages/inventory/InventoryPage.tsx` | 2 | `(#2624)` コメント |
| `frontend/src/pages/company-detail/CompanyBasicTab.tsx` | 1 | PR 番号コメント |
| `frontend/src/pages/company-detail/CompanyDetailPage.tsx` | 1 | PR 番号コメント |
| `frontend/src/pages/companies/CompaniesPage.tsx` | 1 | PR 番号コメント |
| `frontend/src/components/FormField.css` | 1 | `%23888` の URL エンコード断片 |

結論:

- `62` は正しい raw 数
- `0` だったのは `CSS 生hex` だけを見た文脈では正しいが、`frontend/src` 全体の raw hex という意味では不正確
- 差分の主因は **測定範囲の違い + ノイズ判定の違い** で、`already replaced` が理由ではない
- `TSX inline` の色直書きは `0 hits`
- `CSS 生hex（index.css / tokens.css 除外）` も `0 actual`

### 追補2: ADR 12 本の準拠 / 違反 / 対象外

| ADR | 判定 | ひとこと根拠 |
|---|---|---|
| ADR-061 | 準拠 | Inbox の左パネル / Meta 風構造は現行実装にある |
| ADR-063 | 準拠 | Inbox のページヘッダ + 全幅タブバーが実装済み |
| ADR-064 | 準拠 | `--inbox-*` 系の色トークンが `index.css` にある |
| ADR-067 | 違反 | `frontend/src` 全体では TS/TSX 側の生 hex が 36 hits 残る |
| ADR-073 | 違反 | KGI 100% は未達で、共用部品 / 監視 / 文書が満点ではない |
| ADR-087 | 準拠 | hub-shell 共通レイアウトの標準化は運用されている |
| ADR-110 | 準拠 | Karte / inbox の visual reference との整合を見張る関所がある |
| ADR-120 | 準拠 | status → 見た目の SSoT がある |
| ADR-122 | 対象外 | modal 標準化は別の移行スコープで、今回の全体 recon では深掘り対象外 |
| ADR-139 | 準拠 | dashboard 側で DataTable / visual regression の使い方が成立している |
| ADR-144 | 違反 | naked `<h1>` / `<table>` / 独自 empty state がまだ残る |
| ADR-149 | 準拠 | SubMenu の SSOT 集約とリンク型対応が機能している |

### 追補3: 関所の隙間

| 関所 | 守るもの | 守らないもの |
|---|---|---|
| `design-token-guard.yml` | `frontend/src/**` の hex 増加 | 既存 debt の解消、visual diff、TS 定数の設計妥当性 |
| `frontend-check.yml` | `check:css-colors` / `check:dark-parity` / `check:css-var-fallbacks` / `check:css-values` / `check:stories` / `check:stylelint` | TS ファイル内の色定数、ページ骨格の統一、raw table / h1 |
| `ui-governance-gate.yml` | `pages/` の新規生 select / input / tab | 既存 debt、table、h1、empty state、色直書き |
| `karte-gate.yml` | inbox / Karte の visual diff | dashboard / roles / schedule など他画面の見た目 |
| `process-artifacts-gate.yml` | ADR / recon / design doc / GO 記録の書式 | UI の見た目そのもの |
| `design-token-audit.yml` | 未使用トークンの週次監査 | PR ブロック、既存 debt の是正 |

関所の隙間の要点:

- TSX の inline 色直書きは `frontend-check` があるが、**TS 定数の色リテラル**（`calendars.config.ts` / `RolesPage.tsx` など）は別穴
- ページ骨格の統一（`<h1>` の正本化）は専用 gate がない
- 素の `<table>` も専用 gate がない
- empty state の統一も専用 gate がない
- visual gate は inbox / Karte に限定され、他画面の色や骨格のゆらぎは自動で止まらない
