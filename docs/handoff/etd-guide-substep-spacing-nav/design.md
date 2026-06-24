# design: ETD ガイド タブ上余白追加＋「次へ」サブ手順末尾のみ表示

## 参照
- recon: `docs/handoff/etd-guide-substep-spacing-nav/recon.md`
- ADR-129（FedEx Label Validation ウィザード）
- ADR-067（デザイントークン強制）

## 変更方針

### 変更1: 見出し行とサブ手順ペインの間に余白追加（CSS）

**方針**: `.etd-guide__substep-pane` に `margin-top: var(--space-3)` を追加。
親 `.etd-guide__step` の `gap: var(--space-4)` に加算され、見出し行との視覚的距離を広げる。

```css
.etd-guide__substep-pane {
  ...
  margin-top: var(--space-3);
}
```

### 変更2: 「次へ」をサブ手順末尾（1-6）でのみ表示（TSX）

**方針**: SubstepPane に `onLastReached?: (isLast: boolean) => void` コールバックを追加。
タブ切替時に `i === substeps.length - 1` を親へ通知。
親は `portalAtEnd` state で「最後のサブ手順に到達済みか」を管理し、「次へ」ボタンの表示制御に使う。

```tsx
// SubstepPane
onLastReached?.(i === substeps.length - 1);

// FedexEtdSetupGuide
const [portalAtEnd, setPortalAtEnd] = useState(false);
useEffect(() => { setPortalAtEnd(false); }, [activeStepIndex]); // ステップ切替でリセット

const canAdvance = currentStep.key !== "portal" || portalAtEnd;

// ナビゲーション
{canAdvance && (
  <button type="button" className="btn-primary" onClick={advance}>
    ...
  </button>
)}
```

**リセット**: `activeStepIndex` が変化するたびに `portalAtEnd` を `false` にリセット。
これにより、ステップ1に戻った際は再度 1-6 まで進まないと「次へ」が現れない。

**ステップ2以降**: `currentStep.key !== "portal"` で `canAdvance = true` になるため、
既存の動作（常に「次へ」表示）を維持。

**「戻る」ボタン**: 変更なし（`disabled={activeStepIndex === 0}` の既存ロジック維持）。

## KGI/KPI

| 基準 | 検証方法 |
|------|---------|
| 見出し行とタブ（1-1, 1-2…）の間に視覚的余白がある | ブラウザ目視: step-header の下に適度なスペースが入っている |
| ステップ1の 1-1〜1-5 では「次へ」が表示されない | ブラウザ: タブ 1-1 ～ 1-5 をクリックして「次へ」が消えていること |
| 1-6 をクリックすると「次へ」が現れる | ブラウザ: 「1-6」タブ選択で「次へ」ボタンが出現 |
| ステップ2以降では「次へ」が常に表示 | ブラウザ: ステップ2〜最終ステップで「次へ」は常に表示 |
| 「戻る」の出し分けは従来どおり | ブラウザ: step1 で「戻る」disabled・step2+ で有効 |
| 既存レイアウト（intro同一行・左ナビ左端・右詳細中央）変化なし | 目視確認 |
| `npm run lint` 0 errors | CI |
| `npm run build` 通過 | CI |

## 外部・過去事例の参照と我々への応用

コールバックで「末尾到達」を親へ通知するパターンは、Tabs/Stepper UIの標準アプローチ。
`useEffect` でのステップ変化時リセットにより、「戻って来たら再度全手順を経由させる」UX を一貫して担保できる。
