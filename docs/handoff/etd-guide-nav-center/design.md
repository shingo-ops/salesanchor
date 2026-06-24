# design: ETD ガイド 左ナビ項目ラベル中央揃え

## 参照
- recon: `docs/handoff/etd-guide-nav-center/recon.md`
- ADR-129（FedEx Label Validation ウィザード）
- ADR-067（デザイントークン強制）

## 変更方針

`text-align: left` → `text-align: center` に変更（1行）。

```css
.etd-guide__substep-nav-item {
  text-align: center;
}
```

全項目（アクティブ・非アクティブ共通）に適用。枠のサイズ・色・ボーダーは変更なし。

## KGI/KPI

| 基準 | 検証方法 |
|------|---------|
| 1-1〜1-6 ラベルが枠内中央に表示される | ブラウザ目視 |
| 左ナビ列の位置は変わらない | 目視 |
| アクティブ時の囲みは維持 | 目視 |
| `npm run lint` 0 errors | CI |
