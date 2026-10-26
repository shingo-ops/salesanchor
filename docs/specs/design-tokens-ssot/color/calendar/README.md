# カレンダー色CSS変数化

> この文書は何か（専門用語なしの1行）:
> schedule の 7 カレンダー色を、`calendars.config.ts` の直書きから `index.css` の CSS 変数参照へ切り替えるための設計の表紙。

配置: `docs/specs/design-tokens-ssot/color/calendar/README.md`
親: [../../README.md](../../README.md)（design-tokens-ssot の表紙。color/ 直下に表紙は無い）

## 子文書
- [design.md](design.md)

## 境界
- 対象は `frontend/src/features/schedule/calendars.config.ts` の `colorVar` / `tintVar` / `textVar` と、それを受ける `index.css` のカレンダー色 CSS 変数。
- 対象外: ロール色、SVG 属性、カレンダー以外の色、DB 変更、バックエンド変更。
- 実装コードはこの文書では変更しない。ここでは設計の正本だけを定める。

## recon 証拠
- 色パーツの recon 証拠: [recon.md](../../../../handoff/color-tokens-ssot/recon.md)
- `recon-calendar-current.md`（この記録はリポジトリに無い。2026-10-26 時点で origin/main・手元の全ての枝に追加の履歴なし）
- `recon-calendar-distinguishability.md`（この記録はリポジトリに無い。2026-10-26 時点で origin/main・手元の全ての枝に追加の履歴なし）
- [design-system/design.md](../../../design-system/design.md)

## 参照メモ
- `recon-calendar-mapping.md` は本ワークツリーでは未確認。
- 確定値は上記の current / distinguishability / design-system の calendar 確定表を根拠に転記する。
