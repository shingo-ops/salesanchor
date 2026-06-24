# recon: ETD ガイド 左ナビ項目ラベル中央揃え

## 参照 ADR
- ADR-129（FedEx Label Validation ウィザード）
- ADR-067（デザイントークン強制）

## 調査対象

- `frontend/src/pages/integrations/FedexLabelValidationTab.css:291`

## 現状

```css
.etd-guide__substep-nav-item {
  width: 100%;
  text-align: left;   /* ← 左寄せ */
  ...
}
```

1-1〜1-6 のボタンラベルが枠内左寄せになっている。

## 触らない範囲

- ナビ列の位置（左端固定）
- アクティブ時 border・color・background
- 他コンポーネント一切
