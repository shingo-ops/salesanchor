# Phase 3 設計 — fedex-guide-ui-fixes

**対象ADR**: ADR-087
**recon**: docs/handoff/fedex-guide-ui-fixes/recon.md
**日付**: 2026-06-23
**担当**: Hikky-dev

---

## 外部・過去事例の参照と我々への応用

- CSS Overflow Module Level 3（MDN）: `overflow-y: auto` は scroll container を形成し、子の `position: sticky` はその container のスクロールに対して動く。container がスクロールしない場合、sticky は無効。フルスクリーンページに `height: 100dvh` を与えることで container を bounded にする標準パターン。
- ADR-087（hub-shell-layout-standard）: サイドバー不要ページはシェル外レイアウトに。その際の height chain の維持が重要。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| スクロール時に ①②③④ バーが上端に固定される | 画面確認 |
| ステップ番号の円が旧比 1.5 倍になっている | 画面確認 |
| サブステップカード内テキストが濃い色（text-primary）になっている | 画面確認 |
| lint 0 errors / build 成功 | CI（Frontend lint & custom checks） |

---

## 技術 How

### 課題1: sticky 修正

`CarrierSetupGuidePage` を `<div className="setup-guide-page">` で包む。CSS:

```css
.setup-guide-page { height: 100dvh; display: flex; flex-direction: column; }
.setup-guide-page > .page-layout { flex: 1; min-height: 0; }
```

これで `.page-layout-content` が実際にスクロールする = sticky 有効。

### 課題2: dot 1.5 倍

```css
.etd-stepper { --etd-dot-size: calc(var(--icon-lg) * 1.5); }
.etd-stepper__dot { width: var(--etd-dot-size); height: var(--etd-dot-size); font-size: calc(var(--font-xs) * 1.5); }
.etd-stepper__item::before, ::after { top: calc(var(--etd-dot-size) / 2); }
```

### 課題3: サブステップ本文色

```css
.etd-guide__substep .form-hint { color: var(--text-primary); }
```

---

## 弊害・トレードオフ

- `height: 100dvh` で `.setup-guide-page` が viewport 高に固定されるが、コンテンツは `.page-layout-content` 内でスクロールするため問題なし
- 他ページの `PageLayout` は無変更

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | CarrierSetupGuidePage.tsx に setup-guide-page wrapper 追加 | Generator |
| 2 | FedexLabelValidationTab.css に3課題の CSS 追加 | Generator |
| 3 | lint / build 確認 | Generator |

---

## 継続

- 完了後: 本番デプロイ後に `/management-center/integrations/fedex/setup-guide` で3点確認
