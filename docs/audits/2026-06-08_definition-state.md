# 定義レイヤー現状監査

**監査日**: 2026-06-08  
**対象**: `frontend/src/` トークン・命名・semantic層・lint・部品初期値  
**手法**: 読み取りのみ（コード変更なし）  

---

## 3行サマリ

1. **最も整っている軸**: 軸6（enforcement）— CSS変数ハードコード排除を `check-css-*` × 9スクリプト＋ ESLint × 8ルールで完全自動化。commit前に全チェックが走る
2. **最大の穴**: 軸5（定義の穴）— 「Button variant をいつ使うか」「Card density をどのページで使うか」「Icon サイズをどの場面で選ぶか」がどこにも明文化されておらず、各ページで case-by-case に判断されている
3. **まず手を付けるべき軸**: 軸5 → `constants/componentMaps.ts` にステータス値→Badge/Button/カラーのマッピング SSoT を作成。次に軸8（拡張・例外手順）の整備

---

## 軸1: トークン層構造 [できている]

### 3層が明確に実装されている

| 層 | 場所 | 例 |
|---|---|---|
| **Primitive** | `tokens.css` line 12–99 | `--font-xs`, `--space-4`, `--radius-md` |
| **Semantic（色）** | `index.css` line 7–175 | `--text-primary`, `--danger`, `--bg-surface` |
| **Semantic（typography role）** | `tokens.css` line 42–65 | `--role-page-title-size`, `--role-body-color` |
| **Component** | `tokens.css` line 349–417 | `--comp-btn-radius`, `--comp-card-padding` |

### コンポーネントの参照パスが正しい

- `Button.tsx` (line 39–72): variant → CSS クラス → `var(--comp-btn-radius)` → `var(--radius-md)`
- `Card.tsx` (line 27–45): `var(--comp-card-padding)` → `var(--space-6)`
- `Badge.tsx` (line 36–59): `var(--comp-badge-radius)` → `var(--radius-full)`
- `DataTable.tsx` (line 70–122): `var(--comp-table-row-h-default)` → primitive なし（単独 44px 定義）

**判定**: primitive を直参照するコンポーネントは確認されず。層構造の整合性は維持されている。

---

## 軸2: 命名 [部分的]

### 基本方針（一貫）

| 層 | パターン | 例 |
|---|---|---|
| Primitive | スケール値ベース | `--font-xs`, `--space-4`, `--radius-md` |
| Semantic | 意味ベース | `--text-primary`, `--bg-hover`, `--danger` |
| Component | コンポーネント+役割 | `--comp-btn-radius`, `--comp-card-padding-compact` |

### 不揃い 1: page-layout 寸法トークンの prefix 混在

`tokens.css` 内で同種のレイアウト制約トークンが異なる prefix を持つ:

| トークン | prefix | 行 |
|---|---|---|
| `--page-padding-x` | `page-` | line 169 |
| `--max-width-page` | `max-width-` | line 165 |
| `--width-inbox-panel` | `width-` | line 233 |
| `--sidebar-logo-h` | `sidebar-` | line 270 |
| `--topbar-height` | コンポーネント名 | line 153 |

→ リファクタ候補。`--layout-*` か `--comp-<name>-*` に統一すべき。

### 不揃い 2: opacity トークンの近似値乱立

`tokens.css` line 219–228:

| トークン | 値 | 用途 |
|---|---|---|
| `--opacity-muted` | 0.70 | タイムスタンプ |
| `--opacity-hover` | 0.75 | hover 軽減 |
| `--opacity-dim` | 0.80 | ラベル・メタ情報 |
| `--opacity-secondary` | 0.85 | セカンダリラベル |
| `--opacity-soft` | 0.90 | アクセントラベル軽減 |
| `--opacity-disabled` | 0.60 | disabled |
| `--opacity-skipped` | 0.55 | スキップ行 |
| `--opacity-archived` | 0.50 | アーカイブ行 |

→ 0.05刻み 8種。ADR-073 line 64 で「統廃合予定」と明記済みだが未着手。

### 不揃い 3: radius の非グリッド例外

- `--radius-xs: 2px` と `--radius-2xs: 3px` → 1px差（`tokens.css` line 88–89）
- `--radius-bubble-out: 20.8px` / `--radius-bubble-in: 20.8px` → Meta 実測値（line 97–98）

→ ビジネス要件上の例外だが命名方針に記載がない。

**判定**: semantic/primitive 命名は一貫。ただし layout 系トークンの prefix と opacity 近似値が bloat・混乱の種。

---

## 軸3: semantic層カバレッジ [できている（色のみ）]

### 定義済み semantic ロール

| カテゴリ | 定義状況 | 場所 |
|---|---|---|
| テキスト | ✅ primary / secondary / muted | `index.css` line 16–18 |
| 背景・表面 | ✅ primary / surface / subtle / hover / active | line 9–13 |
| アクション | ✅ accent / accent-hover / link | line 26–28 |
| 状態色 3段 | ✅ danger / warning / success（bg / text / bg-subtle × 3） | line 44–50 |
| Border | ✅ border / border-strong / border-icon | line 21–23 |
| Typography roles | ✅ page-title / section-title / card-title / body / caption × 3–4属性 | `tokens.css` line 42–65 |
| Shadow | ✅ shadow-sm / shadow-md / shadow-lg / shadow-modal | `index.css` line 55–60 |
| Z-index | ✅ z-base ～ z-toast 9階層 | `tokens.css` line 120–129 |

### 未定義 semantic ロール（穴）

| カテゴリ | 状況 | 詳細 |
|---|---|---|
| **Icon size semantic** | ❌ primitive のみ | `iconSizes.ts` は "ステータスアイコン=sm" とコメントするが rule ではない |
| **Icon line / solid の semantic 区別** | ❌ コード規約のみ | `component-standard.md` に追記済みだが token 層に定義なし |
| **Button variant → ユースケース** | ❌ | "CTA=primary / 削除=danger" 等の mapping が 1ヶ所にない |
| **Card density → ユースケース** | ❌ | "ダッシュボード=compact" 等が implicit |
| **Modal size → ユースケース** | ❌ | `--modal-max-w-sm/md/lg` を定義したが「いつ sm か」未記述 |

**判定**: 色・typography は完全。icon/button/card/modal の semantic rule（"どの場面でどれを使うか"）が未定義。

---

## 軸4: トークン規模と肥大 [健全・やや bloat 兆候]

### 総数

| ファイル | カスタムプロパティ数 |
|---|---|
| `tokens.css`（非色） | 約 **170** 個 |
| `index.css`（ライト+ダーク） | 約 **120** 個（パリティで重複） |
| **合計 unique** | 約 **290** 個 |

### カテゴリ別

| カテゴリ | 数 | 所見 |
|---|---|---|
| Typography (size/weight/lh/role) | 32 | ✅ reasonable |
| Spacing | 18 | ⚠️ 4px grid 外の例外 px 6種（line 80–85）が bloat 寸前 |
| Border radius | 13 | ⚠️ `--radius-xs(2px)` と `--radius-2xs(3px)` の 1px差 |
| Z-index | 9 | ✅ |
| Motion / Transition | 9 | ✅ |
| Icon sizes | 5 | ✅ |
| Component tokens | 35 | ✅ 適切に分割 |
| Layout / Page-level sizes | 42 | ⚠️ page 固有寸法が bloat 寸前（`--modal-commission-w` 等） |
| Color (semantic) | 約 100 | ✅ ライト+ダーク分 |
| **合計** | **約 263** | |

### 近似値フラグ

| 対象 | 値 | リスク |
|---|---|---|
| `--radius-xs: 2px` / `--radius-2xs: 3px` | 1px差 | 混用リスク。用途コメントのみで区別 |
| `--neutral-bg: #e2e8f0` / `--bg-subtle: #f7fafc` | 視覚的同系 | badge背景 vs テーブルヘッダ背景だが、意図が分かりにくい |
| `--warning-bg: #fefcbf` / `--banner-warning-bg: #fff4e5` | warning 系2種 | 使い分け基準不明（`index.css` line 66 / 74） |

**判定**: スケール・semantic カテゴリは健全。ただし page-level 固有サイズトークン（42個）が増殖しており、将来的な整理が必要。

---

## 軸5: 定義の穴（1ヶ所に定義されていない決定）

### 穴1: Button variant の選択ルール ← **最優先**

**状況**: `component-standard.md` line 40–44 には "variant → CSS class マッピング" だけ。「CTA には primary / キャンセルには secondary / 削除確認には danger」等の SSoT がない。

**実例（都度判断の形跡）**:
- `ConfirmModal.tsx` line 38: `className={danger ? "btn-danger" : "btn-primary"}` ← danger は prop で動的
- `MergeLeadModal.tsx`: 「確認する」= `btn-primary`（暗黙ルール）
- `MergeCompanyModal.tsx`: 同様に `btn-primary`

→ 「確認操作は常に primary」は暗黙的には統一されているが **明文化なし**。

---

### 穴2: Card density の使い分け基準

**状況**: `component-standard.md` line 77–84 に density 定義のみ。「ダッシュボードでは compact」等の適用基準なし。

→ `component-standard.md` line 29 に "ダッシュボードのコンパクト設計は db-* クラスで維持" とあるが density の適用ルールではない。

---

### 穴3: Icon size の選択基準

**状況**: `constants/iconSizes.ts` line 9–15 のコメントは用途の "例示" であり "規則" ではない。

| コンテキスト | 実際の使用 | 根拠 |
|---|---|---|
| サイドバーナビ | `ICON.base(20px)` | `Layout.tsx` line 各所 |
| ヘッダーボタン | `ICON.md(16px)` | `HeaderButton.tsx` |
| 空状態 | `ICON.xl(48px)` | `iconSizes.ts` line 14 コメント |
| テーブル内アイコン | `ICON.sm(14px)` | 上記コメント |

→ 実装は一貫しているが **明文化された rule がない**。新規コンテキストで迷う。

---

### 穴4: 状態色（danger/warning/success）の layer 使い分け

**状況**: `index.css` に 3色 × 3層（`--danger`, `--danger-bg`, `--danger-bg-subtle`, `--danger-text`）が定義されているが、各層を "いつ使うか" が書かれていない。

**実例（implicit ルール）**:
- `--danger-bg-subtle`: 行全体の背景（期限超過行）← `InboxPage.css` 参照
- `--danger-text`: テキスト・アイコン色
- `--danger`: ボタン背景（solid）
- `--danger-bg`: 用途が曖昧（`--warning-bg` との使い分けも不明）

---

### 穴5: Modal size の適用ルール

**状況**: `tokens.css` line 250–257 に 8種の modal 幅トークンが存在:

```
--max-width-modal-sm:    420px  (確認モーダル)
--modal-max-w:           500px  (標準)
--modal-max-w-sm:        420px  (Modal 金型 sm) ← 新旧で重複!
--modal-max-w-md:        600px  (Modal 金型 md)
--modal-max-w-lg:        800px  (Modal 金型 lg)
--modal-profile-min-w:   480px
--modal-profile-max-w:   640px
--inbox-settings-max-w:  480px
```

→ `--max-width-modal-sm(420px)` と `--modal-max-w-sm(420px)` が同値で並存（新旧 2トークン）。

---

### 穴6: Table row density のユースケースルール

**状況**: `DataTable.tsx` line 40 で `density?: 'compact' | 'default' | 'relaxed'` を受け付けるが、「売上テーブルは relaxed / 在庫テーブルは compact」等のルールがない。

---

### 穴7: Sidebar icon-size ↔ `--sidebar-nav-icon-center-x` の連動

**状況**: `tokens.css` line 158–162 のコメントに計算根拠が明記されている:

```
menu border(3) + padding(20) + icon-center(10) = 33px
```

"icon-center(10)" は `ICON.base(20px)` の半径。サイドバーアイコンを別サイズに変更する際に `--sidebar-nav-icon-center-x` の再計算を忘れるリスクがあるが、連動関係は **コメントのみ**で enforcement なし。

---

### 穴8: `--modal-max-w` と `--modal-max-w-sm` の重複

**状況**: 前述の通り同値 420px のトークンが 2個存在。既存実装の `ConfirmModal.tsx` line 31 は `--max-width-modal-sm` を使い続けているため **実質2系統が並存**。

---

## 軸6: enforcement [充実]

### 実装済み check スクリプト一覧

| スクリプト | 実行タイミング | 検査内容 |
|---|---|---|
| `check-css-hardcoded-colors.js` | commit前 + CI | CSS ファイルの hex / rgb / rgba 直書き禁止 |
| `check-dark-parity.js` | commit前（index.css変更時）+ CI | `:root` と `:root.force-dark` のトークンパリティ |
| `check-css-var-fallbacks.js` | commit前 + CI | `var()` フォールバックへの hex 混入禁止 |
| `check-css-hardcoded-values.js` | commit前 + CI | opacity / border-radius / z-index / spacing 数値直書き禁止 |
| `check-css-fixed-position.js` | commit前 + CI | `position:fixed` と `.avatar-btn` 競合検査 |
| `check-icon-sync.js` | CI | `iconSizes.ts` と `tokens.css --icon-*` 値同期検査 |
| `check-breakpoint-sync.js` | CI | `constants/breakpoints.ts` と `tokens.css` 同期 |
| `check-page-layout.js` | CI | `PageLayout` コンポーネント使用の強制 |
| `check-dark-parity.js` (CI) | CI | PR ごとにパリティ再確認 |

### ESLint ルール（`eslint.config.js`）

| 対象 | 禁止内容 | scope |
|---|---|---|
| inline style | hex / rgba / rgb 直書き | TSX |
| inline style | opacity 数値 / z-index 数値 / 寸法 px | TSX |
| import | `lucide-react` 直 import 禁止（icons.tsx 経由必須） | TSX |
| JSX | raw `<h2>` 禁止（pages/*.tsx のみ） | pages |
| 文字列 | `no-japanese-literal` ルール（DB定義の例外あり） | TSX |

### NOT enforced（ギャップ）

| 未強制な決定 | 理由 |
|---|---|
| Button variant ルール | semantic decision → 機械検査不可 |
| Card density ルール | 同上 |
| Icon size の context rule | constant 参照は自由 |
| State color 使い分け（subtle/bg/text） | 同上 |
| iconOnly → aria-label 必須 | Button.tsx コメントのみ（`Button.tsx` line 26） |
| Storybook story の必須性 | ADR-073 KGI だが CI block なし |

**判定**: CSS 値の強制は業界トップレベルの自動化。semantic ルールの機械強制は今後の課題。

---

## 軸7: 部品の初期値 [できている]

| コンポーネント | prop | 既定値 | 安全性 |
|---|---|---|---|
| **Button** (`Button.tsx` line 40–51) | variant | "primary" | ✅ |
| | size | "md" | ✅ |
| | fullWidth / loading / iconOnly | false | ✅ |
| | iconOnly 時 aria-label | ─ | ⚠️ TypeScript 強制なし（コメントのみ） |
| **Card** (`Card.tsx` line 27–45) | variant | "container" | ✅ |
| | density | "default" | ✅ |
| **Badge** (`Badge.tsx` line 36–59) | variant | "neutral" | ✅ 意味不明な色を避ける |
| | appearance | "soft" | ✅ 視認性高 |
| | size | "md" | ✅ |
| | dot / icon | false / ─ | ✅ |
| **DataTable** (`DataTable.tsx` line 70–122) | density | "default" | ✅ 44px（WCAG 2.5.5 準拠） |
| | selectable | false | ✅ opt-in |
| | sortDir | "asc" | ✅ |
| **Modal** (`Modal.tsx` line 35–50) | size | "md" | ✅ |
| | dismissOnOverlay | true | ✅ 標準的な動作 |
| **EmptyState** (`EmptyState.tsx` line 33–45) | size | "default" | ✅ |
| | icon / description / action | ─ | ✅ すべて任意 |

**唯一の懸念**: `Button` の `iconOnly=true` 時に `aria-label` を渡さないと a11y 違反になるが、TypeScript レベルで強制されていない（`Button.tsx` line 26 コメントのみ）。

**判定**: 全コンポーネントが safe default を採用。一点、`iconOnly` の aria-label 強制が未実装。

---

## 軸8: 拡張・例外の手順 [部分的]

### 存在する手順

| 手順 | 記載場所 | 強制 |
|---|---|---|
| 新規カラートークン追加 | `docs/adr/ADR-067-*.md` line 120–126 | `check-dark-parity.js` で自動検査 |
| CSS ハードコード例外 | ADR-067 line 108–117（7種の許可例外） | comment 追加で個別許可 |
| デザインプレビュー追加 | `sections/registry.ts` コメント（1行追加） | CI なし（手動） |

### 存在しない手順（穴）

| 手順 | 状況 |
|---|---|
| 新規コンポーネント作成の標準フロー | 不明。Button/Card を手本にするしかない |
| コンポーネント variant 追加（例: Button に 6th variant） | `component-standard.md` 更新？`Button.tsx` 型更新？手順未記載 |
| トークンの統廃合・変更手順 | ADR-073 で「予定」のみ。PR 起案プロセス・影響箇所置換義務が不明 |
| 例外 ESLint disable の付与ルール | どのコメントで許可されるか未記載 |
| Storybook story の要否判断 | ADR-073 KGI だが "story なしでも PR マージ可" という認識が残存 |
| semantic ルール（variant mapping）の追加・変更 | プロセスなし |

**判定**: トークン追加は手順＋機械検査あり。コンポーネント拡張・例外追加・統廃合は手順未整備。

---

## ギャップ表（成熟度）

| 軸 | 成熟度 | 一言 |
|---|---|---|
| 1. 層構造 | **できている** | primitive→semantic→component の3層が明確。参照パスに逸脱なし |
| 2. 命名 | **部分的** | semantic/primitive は一貫。layout 系 prefix 混在・opacity 近似値乱立 |
| 3. semantic 層カバレッジ | **部分的** | 色・typography は完全。icon/button/card/modal のユースケース semantic が未定義 |
| 4. トークン規模・肥大 | **健全** | 約290個。page-level 寸法トークン42個が bloat 兆候あり |
| 5. 定義の穴 | **多い** | 8つの穴。Button variant/Card density/Icon size/状態色/Modal幅/Table density/Sidebar同期/トークン重複 |
| 6. enforcement | **できている** | CSS 値ハードコード排除を完全自動化。semantic ルールの機械強制は未 |
| 7. 部品初期値 | **できている** | 全コンポーネント = safe default。`iconOnly` aria-label 強制のみ未着手 |
| 8. 拡張・例外手順 | **部分的** | カラートークン追加は手順あり。コンポーネント拡張・例外追加・統廃合は未整備 |

---

## 定義の穴 一覧（優先度付き）

| # | 穴の内容 | 根拠（ファイル:行） | リスク | 優先度 |
|---|---|---|---|---|
| 1 | **Button variant 選択ルール不在**（primary/secondary/ghost/danger をいつ使うか） | `ConfirmModal.tsx:38`, `component-standard.md:40` | 新規画面で配色判断がブレる。danger 誤用で UX 破綻 | 🔴 高 |
| 2 | **Card density ルール不在**（default/compact の使い分け基準） | `component-standard.md:29` | 新規ページのカード密度不統一 | 🔴 高 |
| 3 | **Icon size semantic rule 不在**（sm/md/base/lg/xl をいつ使うか） | `iconSizes.ts:9–14` | 新規コンテキストでサイズ選択が曖昧 | 🔴 高 |
| 4 | **状態色 layer 使い分け不在**（`--danger` / `--danger-bg` / `--danger-bg-subtle` / `--danger-text` の使い分け） | `index.css:44–50` | 警告・エラー表示の inconsistency | 🟡 中 |
| 5 | **Modal size ルール不在**（sm/md/lg の選択基準）＋ `--max-width-modal-sm` と `--modal-max-w-sm` の重複 | `tokens.css:250–257` | modal 幅統一困難。同値トークン2本並存 | 🟡 中 |
| 6 | **Table density ルール不在**（compact/default/relaxed の選択基準） | `DataTable.tsx:40` | テーブル行高の inconsistency | 🟡 中 |
| 7 | **Sidebar icon-size と `--sidebar-nav-icon-center-x` の連動未強制** | `tokens.css:158–162` | sidebar リデザイン時に center-x 再計算漏れリスク | 🟡 中 |
| 8 | **コンポーネント拡張・例外追加の手順不在** | ADR-067 例外リスト（line 108）、手順なし | レビュアー依存の判断。規律ドリフト | 🟢 低（短期） |

---

## 付録: 参照ファイル一覧

| ファイル | 主な参照箇所 |
|---|---|
| `frontend/src/tokens.css` | 全体（primitive/semantic/component トークン定義） |
| `frontend/src/index.css` | line 7–300（カラートークン ライト+ダーク） |
| `frontend/src/constants/iconSizes.ts` | 全体 |
| `frontend/src/constants/icons.tsx` | line 88–202（hi()ラッパー・PAGE_ICONS・NAV_ICONS） |
| `frontend/src/components/Button.tsx` | line 17–72 |
| `frontend/src/components/Card.tsx` | line 27–45 |
| `frontend/src/components/Badge.tsx` | line 36–59 |
| `frontend/src/components/DataTable.tsx` | line 40–122 |
| `frontend/src/components/Modal.tsx` | line 35–50 |
| `frontend/src/components/EmptyState.tsx` | line 33–45 |
| `frontend/src/pages/inbox/InboxMessageThread.tsx` | line 160 |
| `frontend/src/components/ConfirmModal.tsx` | line 38 |
| `docs/specs/component-standard.md` | 全体 |
| `docs/adr/ADR-067-*.md` | line 108–126 |
