# recon: ETD ガイド タブ上余白追加＋「次へ」サブ手順末尾のみ表示

## 参照 ADR
- ADR-129（FedEx Label Validation ウィザード）
- ADR-067（デザイントークン強制）

## 調査対象ファイル

- `frontend/src/pages/integrations/FedexEtdSetupGuide.tsx`
- `frontend/src/pages/integrations/FedexLabelValidationTab.css`

## 現状（file:line）

### SubstepPane コンポーネント（tsx:74-132）

`activeIndex` は SubstepPane 内部の `useState` で管理（ローカル状態）。
親コンポーネントはサブ手順の現在位置を知らない。

```tsx
function SubstepPane({ substeps, screenshotAlt }) {
  const [activeIndex, setActiveIndex] = useState(0);
  ...
  onClick={(e) => {
    ...
    setActiveIndex(i);
    requestAnimationFrame(() => { ... });
  }}
}
```

### ナビゲーションボタン（tsx:526-539）

```tsx
<div className="form-actions etd-guide__nav">
  <button ... onClick={retreat} disabled={activeStepIndex === 0}>
    {t("common.back")}
  </button>
  <button ... onClick={advance}>
    {activeStepIndex === stepDefinitions.length - 1
      ? t("...Finished")
      : t("common.next")}
  </button>
</div>
```

「次へ」は常に表示。サブ手順の状態と連動していない。

### CSS：substep-pane（css:254-261）

```css
.etd-guide__substep-pane {
  display: grid;
  grid-template-columns: var(--size-substep-nav) 1fr;
  gap: var(--space-4);
  align-items: start;
}
```

margin-top なし。親 `.etd-guide__step` の `gap: var(--space-4)` のみで見出しと分離。

## 問題

1. 見出し行（step-header）とサブ手順ペイン（substep-pane）の視覚的距離が狭い
2. サブ手順 1-1〜1-5 を見ている間も「次へ」が表示され、全手順を見る前に進めてしまう

## 触らない範囲

- SubstepPane のスクロール固定ロジック（#2565 実装）
- StepCard / step-header の intro 横並びレイアウト（#2568/#2570 実装）
- `.etd-stepper` sticky・`.etd-guide__substep-detail` 中央寄せ
- migration / CI / workflow
