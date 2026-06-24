# design: ETD ガイド タブ切替スクロール固定（スクロール親修正）

## 参照
- recon: docs/handoff/etd-guide-scroll-fix/recon.md
- ADR-129（FedEx Label Validation ウィザード）
- ADR-067（デザイントークン強制）

## 変更方針

### 変更: スクロール親を `.page-layout-content` に修正

**問題**: `window.scrollY` / `window.scrollTo` はこのページでは無効（実スクロール親は `.page-layout-content`）。

**方針**: `e.currentTarget.closest('.page-layout-content')` でスクロール親要素を取得し、`scrollTop` を保存・復元する。

```tsx
onClick={(e) => {
  const pane = (e.currentTarget as HTMLElement).closest(
    '.page-layout-content'
  ) as HTMLElement | null;
  const scrollTop = pane?.scrollTop ?? 0;
  setActiveIndex(i);
  requestAnimationFrame(() => {
    if (pane) pane.scrollTop = scrollTop;
  });
}}
```

- `closest` は DOM 祖先を辿るため、将来のレイアウト変更でも正しいスクロール親を自動で取得できる。
- `pane` が null（`.page-layout-content` が存在しない環境）のときは復元をスキップするだけで安全に退化する。
- `requestAnimationFrame` により React の re-render コミット後に復元するため、高さ変動によるスクロール変位を打ち消せる。
- フォーカス由来のスクロールは、タブナビボタンが常時画面内に表示されているため非問題（scrollIntoView の対象外）。

## KGI/KPI

| 基準 | 検証方法 |
|------|---------|
| 1-1→1-3 等のタブ切替でビューポートが動かない | ページを少しスクロールしてから 1-1→1-3 を切り替え、スクロール位置が変化しないことを目視確認 |
| `window.scrollY` / `window.scrollTo` を使わない | grep で旧パターン不在を確認 |
| 左ナビ左端・右詳細中央・進捗バー固定・768px縦積みが維持されている | ブラウザ目視 |
| `npm run lint` 通過 | CI 確認 |

## 外部・過去事例の参照と我々への応用

スクロール親が `window` でない SPA（`height: 100dvh` + `overflow-y: auto` の内部コンテナ）では `element.scrollTop` を使う手法が標準。
`closest()` による動的なスクロール親解決は、Radix UI・Headless UI 等のアクセシビリティ実装でも採用されているパターン。
今後 DHL/UPS 等のガイドで同じ `SubstepPane` コンポーネントを使う場合にも自動適用される。
