# design — 見た目改善（B）方向A「クリーン＆カーム」

**仕事名**: 見た目改善（B）— クリーン＆カーム  
**日付**: 2026-06-11  
**対象ADR**: ADR-067  
**担当**: Generator

---

## recon 参照

`docs/handoff/ui-consistency-b/recon.md`

---

## 変更概要

`frontend/src/index.css` の色トークン（`:root` + `:root.force-dark`）のみを差し替える。  
ファイル数: 2（`index.css` + `DashboardPage.tsx` フォールバック hex）。

### 変更トークン（ライトモード）

| トークン | 旧値 | 新値 | 根拠 |
|---------|------|------|------|
| `--accent` | `#1877F2` | `#1e3a8a` | SalesAnchor ブランドネイビー（`favicon.svg:2`） |
| `--accent-hover` | `#166FE5` | `#163171` | `#1e3a8a` より約 5% 暗いシェード |
| `--link` | `#1877F2` | `#1e3a8a` | アクセントと統一 |
| `--link-active-bg` | `#E7F3FF` | `#ebeff8` | `#1e3a8a` の約 8% tint on white |
| `--indicator` | `#1877F2` | `#1e3a8a` | アクセントと統一 |
| `--sidebar-item-hover-bg` | `#E7F3FF` | `#ebeff8` | ホバー背景をネイビー tint に |
| `--sidebar-item-active-bg` | `#E7F3FF` | `#ebeff8` | アクティブ背景をネイビー tint に |
| `--sidebar-item-active-color` | `#1877F2` | `#1e3a8a` | アクティブテキスト |
| `--sidebar-item-active-border` | `#1877F2` | `#1e3a8a` | アクティブ左帯 |
| `--accent-bg` | `#2d6cdf` | `#1e3a8a` | アクセントと統一 |
| rgba 直埋め 4 箇所 | `rgba(24,119,242,…)` | `rgba(30,58,138,…)` | rgb を `#1e3a8a` に変換 |

### 変更トークン（ダークモード）

| トークン | 旧値 | 新値 | 根拠 |
|---------|------|------|------|
| `--accent` | `#818cf8` | `#5b8dd9` | 暗背景でのコントラスト確保（明るめネイビー） |
| `--accent-hover` | `#6366f1` | `#4d7fc8` | 1段暗いネイビー |
| `--link` | `#93c5fd` | `#7baee0` | リンク色をネイビー系に |
| `--sidebar-item-active-border` | `#818cf8` | `#5b8dd9` | ダーク accent と統一 |
| `--accent-bg` | `#818cf8` | `#5b8dd9` | ダーク accent と統一 |
| rgba 直埋め 4 箇所 | `rgba(129,140,248,…)` | `rgba(91,141,217,…)` | `#5b8dd9` の rgb |

### 変更しないトークン（PO 決定）

- `--bg-primary: #f5f7fa` — ページ背景
- `--inbox-bg-gradient` — Meta 風グラデーション
- `--sidebar-item-hover-bg / active-bg` (dark): `#1e3a8a` — 既にブランドネイビー
- `--sidebar-item-active-color` (dark): `#93c5fd` — 暗ネイビー背景上の白テキスト読みやすさ維持

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| ライトモード: リンク・btn-primary・サイドメニュー選択中がネイビー系で表示 | Playwright スクリーンショット / Chromatic snapshot |
| ダークモード: ネイビー差し色が読める（コントラスト確保） | Chromatic snapshot + 目視 |
| 背景（`--bg-primary` / Meta グラデ）が不変 | git diff で `--bg-primary` / `--inbox-bg-gradient` に変更なし |
| `check:dark-parity` 通過 | CI `Lint & Dark Mode Check (ADR-067)` グリーン |
| `check:css-colors` 通過（ハードコード色なし） | CI `Frontend lint & custom checks` グリーン |
| ビルド成功 | CI `Storybook build check` グリーン |

---

## 外部・過去事例の参照と我々への応用

本変更は CSS カスタムプロパティの値差し替えのみ（構造変更なし）であり、外部事例の調査対象となる新規アーキテクチャ・ライブラリ選定は発生しない。

**該当なし＋理由**: 既存のデザイントークン体系（ADR-067）に従い、`:root` と `:root.force-dark` の色変数を差し替えるだけ。Shopify Polaris / Tailwind 等の実績あるトークン設計パターンの範囲内であり、net-new な設計判断は不要。

---

## 弊害 / トレードオフ

- `--shadow-accent-hover` / `--focus-ring-shadow` / `--search-focus-glow` の rgba は `--accent` を参照せず hex 直埋めのため、手動で一致させる必要がある（ADR-067 の既知制約）。今回は rgb を `30,58,138`（= `#1e3a8a`）に揃えた。
- ダークモードの `--accent: #5b8dd9` は以前のインディゴ (`#818cf8`) より低彩度のため、ダッシュボードのプログレスバー等が地味になる可能性がある。実機確認後に必要なら別 PR で微調整。

---

## 継続事項

- 本番反映後に実機で余白・サイドメニューの可読性を確認し、必要なら次ステップ（recon→設計）を起票する（PO 決定）。
