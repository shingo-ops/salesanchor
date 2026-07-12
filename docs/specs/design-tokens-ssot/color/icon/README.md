# 単色アイコンのcurrentColor化

> この文書は何か（専門用語なしの1行）:
> 単色 SVG アイコンを `currentColor` に寄せ、親要素の CSS 変数 `color` で一括制御できるようにするための設計の表紙。

配置: `docs/specs/design-tokens-ssot/color/icon/README.md`
親: [../README.md](../README.md)

## 子文書
- [design.md](design.md)

## 境界
- 対象は単色 SVG アイコンの `fill` / `stroke` を `currentColor` に寄せる設計。
- 対象外: 複数色 SVG アイコン、ロゴの多色表現、カレンダー色、ロール色、DB 変更、バックエンド変更。
- 実装コードはこの文書では変更しない。ここでは設計の正本だけを定める。

## recon 証拠
- [recon-icon-mono-multi.md](../../../../handoff/color-tokens-ssot/recon-icon-mono-multi.md)
- [recon-svg-icons.md](../../../../handoff/color-tokens-ssot/recon-svg-icons.md)

## 参照メモ
- `recon-icon-mono-multi.md` を根拠に、単色アイコンの currentColor 化対象と親 `color` トークンを確定する。
- 複数色アイコンは本 design の対象外とする。
