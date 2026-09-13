# アイコン色の用途別トークン集約

> この文書は何か（専門用語なしの1行）:
> 10箇所に分散したアイコン色指定を、用途カテゴリ別の `--icon-*` トークンに集約するための設計の表紙。

配置: `docs/specs/design-tokens-ssot/color/icon/README.md`
親: [../README.md](../README.md)

## 子文書
- [design.md](design.md)

## 境界
- 対象は `recon-icon-categories.md` で確定した 10 箇所の色決定ポイントと、それを受ける `index.css` のアイコン色トークン。
- 対象外: SVG の多色ロゴの個別再設計、DB 変更、バックエンド変更、calendar / role の色パーツ再設計。
- 実装コードはこの文書では変更しない。ここでは設計の正本だけを定める。

## recon 証拠
- [recon-icon-categories.md](../../../../handoff/color-tokens-ssot/recon-icon-categories.md)
- [recon-icon-color-centralization.md](../../../../handoff/color-tokens-ssot/recon-icon-color-centralization.md)

## 参照メモ
- 10箇所の色決定ポイントは、ナビゲーション / アクション / セクション装飾 / 補助 / 空状態 / 状態表示 / ブランド・プラットフォームに分かれる。
- `PlatformIcon` の白は `--on-solid` に値ベースで一致する。
- Google Calendar ステータスバーは既存の calendar status text トークンをそのまま参照する。
- 複数色アイコンは本 design の中心対象ではない。必要なら別文書で扱う。
