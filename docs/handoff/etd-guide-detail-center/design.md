# design: ETD ガイド 右詳細中央寄せ＋タブ切替スクロール固定

## 参照
- recon: `docs/handoff/etd-guide-detail-center/recon.md`
- ADR-129（FedEx Label Validation ウィザード）
- ADR-067（デザイントークン強制）

## 変更方針

### 変更1: 右詳細を中央寄せに戻す

**問題**: `.etd-guide__substep-detail` に `max-width` はあるが `margin-inline: auto` がなく、`1fr` セル内で左詰めになっている。

**方針**:
- `.etd-guide__substep-detail` に `margin-inline: auto` と `width: 100%` を追加
- `margin-inline: auto` で `1fr` セル内（ナビ右の残余スペース）に対して中央寄せ
- `width: 100%` で max-width 以下では全幅を占有（コンテンツが少ない場合でも安定）

### 変更2: タブ切替でスクロール位置を固定

**問題**: `setActiveIndex` でコンテンツ高が変わりスクロール位置が飛ぶ。

**方針**: `onClick` でスクロール位置を保存し `requestAnimationFrame` で復元。
```tsx
onClick={() => {
  const scrollY = window.scrollY;
  setActiveIndex(i);
  requestAnimationFrame(() => window.scrollTo(0, scrollY));
}}
```
`requestAnimationFrame` により React の re-render コミット後に復元するため、高さ変動によるスクロール変位を打ち消せる。

## KGI/KPI

| 基準 | 検証方法 |
|------|---------|
| 右詳細（説明文＋スクショ）が `1fr` セル内で中央寄せされている | ブラウザ目視: 詳細ブロックが左ナビ直後ではなく中央寄りに配置 |
| 左ナビ（1-1/1-2…）は左端のまま | ブラウザ目視: ナビ列の左端が見出しと揃っている |
| タブ切替でスクロール位置が動かない | 1-1→1-3 等を切り替えてビューポートが固定されることを確認 |
| 768px 縦積みフォールバック維持 | ブラウザ幅 768px 以下で目視 |
| `npm run lint` 通過 | CI 確認 |

## 外部・過去事例の参照と我々への応用

CSS Grid で「子要素を grid セル内で中央寄せ」する手法は `margin: auto` パターンとして MDN にも記載。
`requestAnimationFrame` でのスクロール復元は React コミュニティで広く使われるタブパネル切替の標準対策
（例: Radix UI Tabs の内部実装でも類似アプローチが採用されている）。
今後 DHL/UPS ガイドでも同じ `SubstepPane` コンポーネントを使う場合にも自動適用される。
