# design: Select金型 SelectControl pilot (#2666)

## 対象ADR
ADR-067, ADR-144

## recon参照
docs/handoff/select-control-pilot/recon.md

## 外部・過去事例の参照と我々への応用

ADR-067（デザイントークン強制）および ADR-144（UI部品ガバナンス）に基づき、
生 `<select>` の直接使用を禁止し `SelectControl` 金型へ段階移行する方針を適用。
InvoicesPage の filter-bar をパイロットとして1か所差し替え、既存 Select wrapper との共存を確認した。

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| SelectControl が InvoicesPage filter-bar で動作する | `npm run build` green + Storybook build green |
| 既存 Select wrapper が壊れていない | Frontend lint & custom checks green |
| CSS変数準拠（ハードコード色なし） | UI Governance Gate green |
| ADR-067 デザイントークン違反なし | ADR-067 CI チェック green |
