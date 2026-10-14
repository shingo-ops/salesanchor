# AY-2u 設計: 孤児トークン --input-select-min-w の削除

- 対象 ADR: ADR-067（トークンは tokens.css が正本）、ADR-073（未使用トークン監査）
- 相互参照: docs/handoff/ay2u-orphan-token/recon.md

## 変更契約
| 箇所 | 変更前 | 変更後 |
|---|---|---|
| frontend/src/tokens.css:355 | `  --input-select-min-w:      280px;  /* セレクト最小幅 */` | 行ごと削除（前後の行は逐語） |

触らない: 他の未使用トークン 30 件、tokens.css の他の行、evidence の過去記録、docs/specs/design-system/design.md。

## 受入
|基準|検証方法|
|---|---|
|frontend・scripts・.github で `input-select-min-w` 0 件|git grep の出力|
|build 後の CSS に当該宣言 0 件、他の CSS 差分なし|dev build の dist CSS を整形して before/after を diff（ay2u-css.diff）|
|監査出力から当該 1 件のみ消える（31→30）|ay2u-audit.diff|
|品質: generate・tsc・lint・check:all・test:coverage・build・build-storybook 成功|ログ|
|本番 CSS に 0 件|マージ後に prod bundle を grep（Opus 実施）|

## 外部・過去事例の参照と我々への応用
- 外部事例: 不要（参照 0 の宣言削除のみ）。過去: AY-2r で参照元を撤去した際に孤児化を記録済み（docs/handoff/ay2r-search-bar-css/design.md:50）。

## 代替案
- 残す: 使われない値が「セレクト最小幅」として残り、新規実装が誤って使う余地が残る。不採用。

## リスクと戻し方
- 描画差 0（参照 0 の宣言削除）。戻し方: revert。

## 維持の仕組み
- 守り手: frontend/src/tokens.css（トークンの正本）と check:all の CSS 値・変数系チェック。
- 守り手2: frontend/scripts/check-unused-tokens.js（週次監査 design-token-audit.yml、非ブロック）。
- 既知の穴: 参照 0 のトークンを CI でブロックする仕組みは無い（週次監査のみ）。
