# recon: ETD ガイド 見出し＋intro 同一行化＋上部スペース詰め

## 参照 ADR
- ADR-129（FedEx Label Validation ウィザード）
- ADR-067（デザイントークン強制）

## 調査対象ファイル

### TSX
- `frontend/src/pages/integrations/FedexEtdSetupGuide.tsx`

### CSS
- `frontend/src/pages/integrations/FedexLabelValidationTab.css`

## 現状の構造（file:line）

### StepCard コンポーネント（tsx:134-154）
```tsx
function StepCard({ stepNumber, heading, children, isActive }) {
  return (
    <section className="etd-guide__step">
      <div className="etd-guide__step-header">
        <span className="etd-guide__step-number">{stepNumber}</span>
        <strong>{heading}</strong>
      </div>
      {children}
    </section>
  );
}
```
`.etd-guide__step-header` は現在 `flex` で番号バッジ＋タイトルのみ横並び。
intro 段落は `{children}` に含まれているため、見出しの「下」に縦積みされる。

### Step 1 intro（tsx:329-343）
```tsx
<p className="form-hint">
  <Trans i18nKey="carrierIntegration.fedexEtdGuideStep1Desc" components={{portalLink: <a .../>}} />
</p>
```

### Step 2–4 intro（tsx:392, 401, 419）
各ステップ先頭に `<p className="form-hint">` として intro が children に置かれている。

### 上部スペース（css:37, 76）
- `.etd-guide` の `gap: var(--space-4)` → ステッパーとコンテンツの間隔
- `.etd-stepper` の `margin-bottom: var(--space-4)` → ステッパー下マージン

### `.etd-guide__step-header`（css:172-176）
```css
.etd-guide__step-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
```
現在は `flex-wrap` なし、タイトルまでの横並びのみ。

## 触らない範囲
- `.etd-guide__substep-pane` / `__substep-detail`（中央寄せ・左ナビ固定は維持）
- `SubstepPane` コンポーネント（スクロール固定ロジックは維持）
- `.etd-stepper` の sticky / z-index
- migration / CI / workflow 一切含めない
