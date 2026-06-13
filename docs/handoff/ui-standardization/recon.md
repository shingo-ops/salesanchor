# UI標準化 PR-0 全体recon

**作成日**: 2026-06-13  
**ブランチ**: feature/morimoto/ui-std-pr0-recon  
**ワークツリー**: /Users/tanizawashingo/worktrees/salesanchor/feature-morimoto-ui-std-pr0-recon/

---

## 1. 実施した調査コマンド

```bash
# 1. raw <button> タグ（pages/ + components/、stories除外）
rg -g "*.tsx" --count "<button" frontend/src/pages/ frontend/src/components/ \
  | grep -v "stories" | sort -t: -k2 -rn

# 2. raw <input> タグ
rg -g "*.tsx" --count "<input" frontend/src/pages/ frontend/src/components/ \
  | grep -v "stories" | sort -t: -k2 -rn

# 3. raw <select> タグ
rg -g "*.tsx" --count "<select" frontend/src/pages/ frontend/src/components/ \
  | grep -v "stories" | sort -t: -k2 -rn

# 4. raw <textarea> タグ
rg -g "*.tsx" --count "<textarea" frontend/src/pages/ frontend/src/components/ \
  | grep -v "stories" | sort -t: -k2 -rn

# 5. btn-* クラス使用数
rg -g "*.tsx" --count 'btn-' frontend/src/pages/ frontend/src/components/ \
  | grep -v "stories" | sort -t: -k2 -rn

# 6. 標準 <Button> コンポーネント使用数
rg -g "*.tsx" --count "<Button" frontend/src/ | grep -v "stories" | sort -t: -k2 -rn

# 7. 標準 <TextField> 使用数
rg -g "*.tsx" "<TextField" frontend/src/ | grep -v "stories"

# 8. 標準 <Select> 使用数
rg -g "*.tsx" "<Select" frontend/src/ | grep -v "stories"

# 9. 標準 <Textarea> 使用数
rg -g "*.tsx" "<Textarea" frontend/src/ | grep -v "stories"

# 10. インラインstyle警告パターン
rg -g "*.tsx" 'style=.*color.*red|style=.*color.*warn|style=.*#[Ff][A-Fa-f0-9][A-Fa-f0-9]' \
  frontend/src/pages/ frontend/src/components/

# 11. error-banner クラス
rg -g "*.tsx" 'error-banner' frontend/src/

# 12. ADR検索
git grep -i "design token" docs/adr/
git grep -i "component" docs/adr/ | grep "ADR-" | grep -v "#" | head -30
git grep -i "button" docs/adr/ | grep "ADR-" | head -20
git grep -i "form" docs/adr/ | grep "ADR-" | head -20
git grep -i "i18n" docs/adr/ | grep "ADR-" | head -10
```

---

## 2. 集計サマリー

| 要素 | 総数（stories除外） | 備考 |
|------|---------------------|------|
| `<button>` raw | 501 | pages/ + components/ |
| `<input>` raw | 470 | 同上 |
| `<select>` raw | 124 | 同上 |
| `<textarea>` raw | 51 | 同上 |
| `btn-*` className | 419 | raw button以外のspan等含む |
| `<Button>` 標準 | 70 | design-preview含む |
| `<TextField>` 標準 | 0 | design-preview/FormSection.tsxのみ（本番ゼロ） |
| `<Select>` 標準 | 0 | 同上 |
| `<Textarea>` 標準 | 0 | 同上 |

---

## 3. 既存標準コンポーネント一覧（本番使用分）

### 3-1. `<Button>` — 70件（本番 production スクリーン分のみ抜粋）

| ファイル | 件数 | 主な用途 |
|----------|------|----------|
| `frontend/src/components/Drawer.tsx` | 1 | 閉じるボタン |
| `frontend/src/components/FedExRateModal.tsx` | 3 | 送料計算ボタン類 |
| `frontend/src/components/MergeCompanyModal.tsx` | 4 | マージ実行・キャンセル |
| `frontend/src/components/MergeContactModal.tsx` | 4 | 同上 |
| `frontend/src/components/CommissionPanel.tsx` | 2 | 手数料操作 |
| `frontend/src/components/OrderFinancialPanel.tsx` | 3 | 財務操作 |
| `frontend/src/components/ContactChannelForm.tsx` | 5 | チャンネル追加・削除 |
| `frontend/src/components/PriorityScoreOverride.tsx` | 2 | スコア上書き |
| `frontend/src/components/MergeLeadModal.tsx` | 4 | リードマージ |
| `frontend/src/components/InboxSettingsModal.tsx` | 3 | 設定保存・キャンセル |
| `frontend/src/components/CompanyAddressModal.tsx` | 3 | 住所操作 |
| design-preview 系 | ~36 | カタログ・プレビュー専用 |

### 3-2. `<Modal>` 標準 — 約15件（本番）

`frontend/src/components/` 以下の Modal 使用コンポーネント群（MergeCompanyModal, MergeContactModal, MergeLeadModal, FedExRateModal, InboxSettingsModal, CompanyAddressModal 等）。

### 3-3. `<TextField>` / `<Select>` / `<Textarea>` — **本番ゼロ**

`frontend/src/components/design-preview/sections/FormSection.tsx` のみで使用。全本番画面は未移行。

---

## 4. 非標準使用 — ファイル別集計（上位30件）

### 4-1. `<button>` raw（上位）

| ファイル | <button> 数 | リスク |
|----------|------------|--------|
| `pages/SchedulePage.tsx` | 15 | HIGH |
| `pages/InboxMessageThread.tsx` | 14 | HIGH |
| `components/InboxKartePanel.tsx` | 14 | HIGH |
| `pages/CompanyDetailPage.tsx` | 14 | HIGH |
| `components/KnowledgeAliasesTab.tsx` | 13 | HIGH |
| `components/SuppliersAdminTab.tsx` | 12 | HIGH |
| `components/CompanyContactsTab.tsx` | 7 | MED（PR-A対象） |
| `components/ContactChannelForm.tsx` | 5 | MED（PR-A対象） |
| `components/MergeContactModal.tsx` | 3 | LOW（PR-A対象） |
| `pages/ContactDetailPage.tsx` | 8 | MED |
| `pages/OrderDetailPage.tsx` | 9 | MED |
| `pages/LeadsPage.tsx` | 11 | HIGH |

### 4-2. `<input>` raw（上位）

| ファイル | <input> 数 | リスク |
|----------|-----------|--------|
| `pages/CompaniesPage.tsx` | 28 | HIGH |
| `pages/RegisterPage.tsx` | 25 | MED（認証系・別途検討） |
| `pages/ProductEditPage.tsx` | 25 | HIGH |
| `components/InboxProfileModal.tsx` | 21 | HIGH |
| `components/InboxKartePanel.tsx` | 21 | HIGH |
| `components/CompanyContactsTab.tsx` | 9 | MED（PR-A対象） |
| `components/ContactChannelForm.tsx` | 4 | MED（PR-A対象） |
| `components/MergeContactModal.tsx` | 3 | LOW（PR-A対象） |

### 4-3. `<select>` raw（上位）

| ファイル | <select> 数 | リスク |
|----------|------------|--------|
| `pages/CompaniesPage.tsx` | 12 | HIGH |
| `components/InboxKartePanel.tsx` | 9 | HIGH |
| `pages/ProductEditPage.tsx` | 8 | HIGH |
| `pages/OrderDetailPage.tsx` | 6 | MED |

### 4-4. `<textarea>` raw（上位）

| ファイル | <textarea> 数 | リスク |
|----------|--------------|--------|
| `components/InboxKartePanel.tsx` | 8 | HIGH |
| `pages/ProductEditPage.tsx` | 5 | HIGH |
| `pages/CompanyDetailPage.tsx` | 4 | MED |

---

## 5. インライン警告スタイル hotspot

### 5-1. `MergeCompanyModal.tsx`

| 行 | パターン |
|----|---------|
| 145, 149 | `style={{ color: "..." }}` — テキスト色 |
| 165–171 | `style={{ background: ..., border: ... }}` — 警告ボックス |
| 182, 213 | `style={{ color: "..." }}` |
| 272–273, 302 | `style={{ color: ... }}` |

### 5-2. `MergeContactModal.tsx`

同パターン（MergeCompanyModal のコピー系）。

### 5-3. `ChannelsPage.tsx`

| 行 | パターン |
|----|---------|
| 311, 317, 323 | `style={{ color: ... }}` |
| 371–373, 469, 473 | 警告テキスト色 |
| 481, 487, 506 | 同上 |
| 537, 551, 580, 584 | 状態表示インラインスタイル |

### 5-4. `error-banner` クラス — 17件（統一済みパターン）

`pages/CompaniesPage.tsx`, `pages/ContactDetailPage.tsx`, `pages/RegisterPage.tsx`, `pages/InboxPage.tsx` 等 17ファイル。  
CSSクラスで統一済みのため **対象外**（正常パターン）。

---

## 6. リスク分類

### LOW（安全・PR-Aから着手可）
- `components/CompanyContactsTab.tsx` — Modal既使用、Button部分移行済み
- `components/ContactChannelForm.tsx` — Button/Modal既使用、input 4件のみ
- `components/MergeContactModal.tsx` — Button/Modal既使用、raw残3件のみ

### MEDIUM
- `pages/ContactDetailPage.tsx` — 中規模ページ、テスト確認必要
- `pages/OrderDetailPage.tsx` — 受注周りのロジック密着度高
- `pages/CompanyDetailPage.tsx` — button 14件、段階的移行が安全

### HIGH（PR-Dまたは後回し推奨）
- `pages/CompaniesPage.tsx` — input 28件 + select 12件、最大規模
- `components/InboxKartePanel.tsx` — 複合UI、input/select/textarea混在21+9+8
- `pages/InboxMessageThread.tsx` — スレッド描画の動作確認が複雑
- `pages/SchedulePage.tsx` — カレンダー系、DOM直操作の可能性
- `pages/ProductEditPage.tsx` — input 25件、商品マスタは手を抜けない
- `pages/RegisterPage.tsx` — **認証フロー。UI標準化スコープ外（別ADR検討）**

---

## 7. 除外対象

| ファイル/ディレクトリ | 除外理由 |
|-----------------------|---------|
| `**/*.stories.tsx` | Storybook カタログ — 本番影響ゼロ |
| `components/design-preview/**` | デザイントークンプレビュー専用 |
| `pages/RegisterPage.tsx` | 認証フロー — UI変更は別途 ADR 検討必要 |
| `pages/LoginPage.tsx` | 同上 |
| `error-banner` クラス使用箇所 | CSS クラス統一済み — 対象外 |

---

## 8. 関連 ADR

| ADR | タイトル | 関連 |
|-----|---------|------|
| ADR-027 | UI国際化 | 全 UI 文字列を `t()` 経由必須 |
| ADR-039 | （component関連） | コンポーネント設計初期 |
| ADR-046 | （component関連） | フォーム系設計 |
| ADR-054 | （component関連） | コンポーネント拡張 |
| ADR-058 | （component関連） | コンポーネント追加 |
| ADR-063 | button関連 | ボタン仕様定義 |
| ADR-067 | デザイントークン強制 | CSS変数・アイコン・トークン規約（**最重要**） |
| ADR-071 | button/component関連 | ボタン・コンポーネント更新 |
| ADR-073 | component関連 | コンポーネント系 |
| ADR-074 | デザイントークン言及 | ADR-067補足 |
| ADR-076 | component関連 | コンポーネント系 |
| ADR-122 | component関連 | 最新コンポーネント系 |

**最重要**: ADR-067（デザイントークン）と ADR-027（i18n）はすべての置き換えで守る必須制約。

---

## 9. 標準コンポーネント 仕様書

`docs/specs/component-standard.md` — Task 2C/2E 引継内容:
- `<Button>`: variant primary/secondary/ghost/danger/outline + size sm/md/lg
- `<TextField>`: label/helperText/error/size/fullWidth + type 全種
- `<Select>`: options配列 `{value,label,disabled?}` + placeholder
- `<Textarea>`: 同 TextField パターン
- `<Modal>`: size sm/md/lg/xl + focus trap + Esc close + portal
- **Note**: TextField/Select/Textarea は Task 2E で 206か所順次置換予定（このPR-0は計画のみ）
