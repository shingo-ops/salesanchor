# recon — 見た目改善（B）方向A「クリーン＆カーム」

**仕事名**: 見た目改善（B）— クリーン＆カーム  
**日付**: 2026-06-11  
**対象ADR**: 未起案（本 recon を受けて Planner が起案）  
**担当**: architect  

---

## 調査1: SalesAnchor ブランドカラー

### 定義元

| `path:line` | 内容 |
|-------------|------|
| `frontend/public/favicon.svg:2` | `fill="#1e3a8a"` — ロゴアイコン背景色（ダークネイビーブルー） |
| `frontend/public/favicon.svg:3` | `stroke="#eff6ff"` — ロゴアイコン内のアンカー記号色（ほぼ白） |
| `frontend/src/components/Layout.tsx:182` | `<img src="/favicon.png">` — collapsed 時のサイドバーアイコン |
| `frontend/src/components/Layout.tsx:184` | `<img src="/logo.png">` — expanded 時のサイドバーテキストロゴ |

### 確定値

- **SalesAnchor ブランドプライマリ**: `#1e3a8a`（Tailwind blue-900 相当のダークネイビー）
- **ロゴ内アイコン色**: `#eff6ff`（Tailwind blue-50 相当）

### 現行 `--accent` との差

| 変数 | 現行値 | 出典コメント |
|------|--------|------------|
| `--accent` | `#1877F2` | `frontend/src/index.css:26` — コメント「Meta Business Suite 青系」と明記 |
| `--accent-hover` | `#166FE5` | `frontend/src/index.css:27` |
| `--link` | `#1877F2` | `frontend/src/index.css:28` |

**結論**: 現行アクセントは Meta の青（`#1877F2`）。SalesAnchor ブランドカラー `#1e3a8a` はアプリの CSS 変数としてまだ定義されていない。差し色として採用するには `--accent` 系トークンの差し替えが必要。

---

## 調査2: 現行ページ背景（Meta風）

### 背景の実態（2層構造）

| `path:line` | 変数 / 値 | 役割 |
|-------------|----------|------|
| `frontend/src/index.css:9` | `--bg-primary: #f5f7fa` | `.app-shell` と `body` の背景色 |
| `frontend/src/index.css:10` | `--bg-surface: #ffffff` | カード・モーダル・テーブル等のサーフェス |
| `frontend/src/sidebar.css:14` | `.app-shell { background: var(--bg-primary) }` | シェル全体の土台色 |
| `frontend/src/sidebar.css:244` | `.app-body { background-color: var(--bg-surface) }` | コンテンツエリアのベース（白） |
| `frontend/src/sidebar.css:245` | `.app-body { background-image: var(--inbox-bg-gradient) }` | 白ベースの上に乗るグラデーション |
| `frontend/src/index.css:160–166` | `--inbox-bg-gradient: radial-gradient(...)` | Meta Business Suite 実測値のグラデーション（緑・ピンク・薄紫・淡青） |

### グラデーションの正確な定義（`index.css:160–166`）

```css
--inbox-bg-gradient:
  radial-gradient(103.89% 81.75% at 95.41% 106.34%,
    rgb(234, 248, 239) 6%, rgba(234, 248, 239, 0) 79.68%),
  radial-gradient(297.85% 151.83% at -21.39% 8.81%,
    rgb(250, 241, 241) 0%, rgb(250, 241, 241) 15.29%,
    rgb(243, 237, 245) 21.39%, rgb(229, 240, 250) 40.79%);
```

**これは PO 決定により維持する（変更しない）。**

---

## 調査3: 現行サイドメニュー

### 実装場所

| `path:line` | 内容 |
|-------------|------|
| `frontend/src/sidebar.css:1–265` | サイドバー全体のスタイル定義 |
| `frontend/src/components/Layout.tsx:182–184` | ロゴ画像の差し込み |

### 見た目を決めている CSS（A方向の整備対象）

| 役割 | CSS 変数 | 定義場所 `path:line` | 現行値 |
|------|---------|---------------------|--------|
| サイドバー背景 | `--sidebar-bg` | `index.css:34` | `#ffffff` |
| サイドバーボーダー | `--sidebar-border` | `index.css:35` | `#E4E4E7` |
| 通常項目テキスト | `color: var(--text-secondary)` | `sidebar.css:119` | `#4a5568` |
| ホバー背景 | `--sidebar-item-hover-bg` | `index.css:36` | `#E7F3FF`（Meta青薄め） |
| アクティブ背景 | `--sidebar-item-active-bg` | `index.css:37` | `#E7F3FF` |
| アクティブテキスト | `--sidebar-item-active-color` | `index.css:38` | `#1877F2`（Meta青） |
| アクティブ左ボーダー | `--sidebar-item-active-border` | `index.css:39` | `#1877F2` |
| ブランド文字（expanded）| `color: var(--accent)` | `sidebar.css:73` | `#1877F2` |
| アコーディオン内背景 | `background: var(--bg-subtle)` | `sidebar.css:190` | `#f7fafc` |
| サブ項目アクティブ背景 | `var(--link-active-bg)` | `sidebar.css:213` | `#E7F3FF` |

### アクティブ項目の表示方法（`sidebar.css:137–143`）

```css
.sidebar-item.active {
  background: var(--sidebar-item-active-bg);     /* #E7F3FF */
  color: var(--sidebar-item-active-color);       /* #1877F2 */
  font-weight: var(--font-weight-semi);          /* 600 */
  border-left-color: var(--sidebar-item-active-border); /* #1877F2 — 3px左ライン */
}
```

**A方向整備のポイント**: `--sidebar-item-active-color` と `--sidebar-item-active-border` を Meta青 → SalesAnchor ネイビー（`#1e3a8a`）に差し替えることで、アクティブ項目の印象が変わる。ホバー背景（`#E7F3FF`）も合わせて `#eff6ff` または `#dbeafe` に調整する。

---

## 調査4: 色トークンの一覧と定義場所

### 定義場所のルール（ADR-067準拠）

| ファイル | 内容 |
|---------|------|
| `frontend/src/index.css` | **色関連 CSS 変数のみ**（`:root` + `:root.force-dark` 両方必須） |
| `frontend/src/tokens.css` | **非色トークン**（タイポグラフィ・スペーシング・レイアウト等、`:root` のみ） |

### A方向で変更対象となる色トークン一覧

以下はすべて `frontend/src/index.css` の `:root` ブロック。ダークモード対応は `:root.force-dark` も同時変更が必須（`frontend/CLAUDE.md` 規定）。

| トークン名 | 現行値 `path:line` | A方向での変更理由 |
|-----------|-------------------|------------------|
| `--accent` | `#1877F2` `index.css:26` | Meta青 → SalesAnchor ネイビー差し替え |
| `--accent-hover` | `#166FE5` `index.css:27` | 同上（ホバー） |
| `--link` | `#1877F2` `index.css:28` | 同上（リンク色） |
| `--link-active-bg` | `#E7F3FF` `index.css:29` | SalesAnchor ネイビー系の薄い背景へ |
| `--sidebar-item-hover-bg` | `#E7F3FF` `index.css:36` | 同上（ホバー背景） |
| `--sidebar-item-active-bg` | `#E7F3FF` `index.css:37` | 同上（アクティブ背景） |
| `--sidebar-item-active-color` | `#1877F2` `index.css:38` | SalesAnchor ネイビーへ |
| `--sidebar-item-active-border` | `#1877F2` `index.css:39` | 同上（左ライン） |

### 変更しないトークン（確認済み）

| トークン名 | 値 | 変更しない理由 |
|-----------|-----|--------------|
| `--bg-primary` | `#f5f7fa` `index.css:9` | ページ背景（PO決定：現行維持） |
| `--bg-surface` | `#ffffff` `index.css:10` | カード白背景（クリーン方向と一致） |
| `--inbox-bg-gradient` | radial-gradient `index.css:160` | Meta風グラデーション（PO決定：維持） |
| `--danger` | `#e53e3e` `index.css:44` | ステータス色（意味予約済み） |
| `--sidebar-bg` | `#ffffff` `index.css:34` | 白基調サイドバー（A方向と一致） |

---

## ダークモード対応範囲

上記変更対象トークンはすべて `frontend/src/index.css` の `:root.force-dark` ブロックにも対応値が定義されている。A方向実装時は light/dark 両方を同時変更すること（片方のみ禁止: `frontend/CLAUDE.md` ルール）。

現行ダークモードのアクセント: `--accent: #818cf8` `index.css:212`（インディゴ系。SalesAnchorネイビーをダーク用に明るくした値への変更が必要）

---

## 不明点リスト

| # | 不明点 | 状態 |
|---|-------|------|
| 1 | `logo.png` の実際の色が favicon `#1e3a8a` と一致するか | ✅ **解消（→ズレあり）** — 下記参照 |
| 2 | SalesAnchor の正式ブランドカラー hex（Notion/Figma等）が別途存在するか | ⚠️ **未確認** — PO に確認必須（下記参照） |
| 3 | `--accent` 変更時に波及するコンポーネント数（btn-primary / focus-ring / badge 等が全て参照） | ✅ 波及範囲は `grep --accent` で追跡可能。設計フェーズで明細化 |

### 不明点1 解消結果: logo.png の色解析（PIL）

`logo.png`（640×128px）をピクセル解析した結果：

| 指標 | 値 |
|------|----|
| 不透明ピクセル（α≥200） | 18,202px（全 81,920px の 22%）→ 透過 PNG |
| ブルー系ピクセル比率 | 95.1%（ほぼ全ピクセルが青系） |
| グラデーション最暗端 | `#0a3158`（R:10 G:49 B:88） |
| 中彩度・中明度の代表色平均 | `#205c8c`（R:32 G:92 B:140） |
| 最多バケット（16刻み） | `~#2070a0`（R:32 G:112 B:160） |

**logo.png はグラデーションロゴ（単色でない）。** ダーク端 `#0a3158` → 主役色 `#205c8c` → 明端 `#2070a0` の青系グラデーション。

**favicon.svg `#1e3a8a` との比較:**
- favicon: R:30 G:58 B:138（ダークネイビー、高B・低G）
- logo 主役色: R:32 G:92 B:140（中程度の青、G が約 34 高い）
- **ユークリッド距離 ≈ 40 → 明確にズレあり**

**結論**: logo.png と favicon.svg は**同系の青だが異なる値**。favicon はネイビー寄り、logo はより明るいスチールブルー寄り。グラデーションロゴの「代表色」は `#205c8c` 付近。

**PO 確認事項**: `logo.png` と `favicon.svg` のどちらがブランドプライマリか、または公式 hex を確定すること。候補: `#1e3a8a`（favicon）/ `#205c8c`（logo代表）/ 別途指定。

---

## 補足

- `--shadow-accent-hover: 0 2px 6px rgba(24, 119, 242, 0.15)` (`index.css:69`) は `--accent` の hex 埋め込みコメントで定義。`--accent` 変更時はこの rgba 値も合わせて更新すること（トークン参照でなく固定 rgba のため）。
- `--focus-ring-shadow: 0 0 0 3px rgba(24, 119, 242, 0.15)` (`index.css:85`) 同様。
- `--search-focus-glow` (`index.css:87`) 同様。
- ダークモードの focus ring は `rgba(129, 140, 248, 0.3)` (`index.css:258`)（インディゴ系）— こちらも一緒に変更対象。
