# design: ETD ガイド 見出し＋intro 同一行化＋上部スペース詰め

## 参照
- recon: `docs/handoff/etd-guide-header-inline/recon.md`
- ADR-129（FedEx Label Validation ウィザード）
- ADR-067（デザイントークン強制）

## 変更方針

### 変更1: 見出しとintroを同一行化

**問題**: `.etd-guide__step-header` はバッジ＋タイトルのみ横並びで、intro 段落は children に縦積みされている。

**方針**:
- `StepCard` に `intro?: ReactNode` prop を追加
- `.etd-guide__step-header` 内に `.etd-guide__step-title-row`（バッジ＋タイトルのラッパー、`flex-shrink: 0`）を追加
- intro は `.etd-guide__step-intro`（`flex: 1; min-width: 0; margin: 0`）として header 内に横並び配置
- `.etd-guide__step-header` に `flex-wrap: wrap` と `gap: var(--space-3)` を設定
- 各ステップの先頭 `<p className="form-hint">` を children から `intro` prop へ移動

```tsx
// StepCard 変更後
function StepCard({ stepNumber, heading, intro, children, isActive }) {
  return (
    <section className="etd-guide__step">
      <div className="etd-guide__step-header">
        <div className="etd-guide__step-title-row">
          <span className="etd-guide__step-number">{stepNumber}</span>
          <strong>{heading}</strong>
        </div>
        {intro && <p className="etd-guide__step-intro">{intro}</p>}
      </div>
      {children}
    </section>
  );
}
```

### 変更2: 進捗バーとコンテンツの間隔を詰める

**問題**: `.etd-stepper` の `margin-bottom: var(--space-4)` と `.etd-guide` の `gap: var(--space-4)` が重なり空白が広い。

**方針**:
- `.etd-stepper` の `margin-bottom` を `var(--space-4)` → `var(--space-2)` に縮小
- `.etd-guide` の `gap` を `var(--space-4)` → `var(--space-2)` に縮小

### 変更3: 768px 縦積みフォールバック

**方針**:
- `@media (max-width: 768px)` に `.etd-guide__step-header { flex-direction: column; align-items: flex-start; gap: var(--space-2); }` を追加

## 新規 CSS クラス

```css
.etd-guide__step-title-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
}

.etd-guide__step-intro {
  flex: 1;
  min-width: 0;
  margin: 0;
  font-size: var(--font-sm);
  color: var(--text-secondary);
}
```

## KGI/KPI

| 基準 | 検証方法 |
|------|---------|
| バッジ「1」＋タイトル「APIの設定」の右隣に intro 文が横並び表示される | ブラウザ目視: step-header 内に title-row と intro が同一行に並ぶ |
| 768px 以下では縦積みに戻る | ブラウザ幅 768px で目視: header が column に切り替わる |
| ステッパー直下のコンテンツとの縦スペースが縮小している | 目視: 進捗バー下の空白が以前より小さい |
| 左ナビ左端・右詳細中央寄せは維持 | 目視: substep-pane の既存レイアウト変化なし |
| `npm run lint` 通過 | CI 確認 |
| `npm run build` 通過 | CI 確認 |

## 外部・過去事例の参照と我々への応用

CSS Flexbox で「サマリー行（タイトル＋補足）を同一行に収める」パターンは `flex: 1; min-width: 0` の組み合わせが標準。
`flex-wrap: wrap` により狭幅時の自然な縦積みを実現（メディアクエリに依存しすぎない設計）。
今後 DHL/UPS ガイドで同じ `StepCard` を使う際も自動適用される。
