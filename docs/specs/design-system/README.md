# UI/UXデザインシステム（design-system）— 表紙

> この文書は何か（専門用語なしの1行）:
> 画面の色や部品の設計図を1ヵ所に集め、1ヵ所直せば全ページが変わる仕組みの正本一式の入口。

配置: docs/specs/design-system/README.md
日付: 2026-07-04
PO: しんご
状態: あるべき姿・KGI・理想設計 PO承認済（2026-07-04）

## 境界
- 対象: フロントエンドUI全般（トークン・共通部品・ページの参照構造・カタログ・関所）
- 対象外: 見た目の質（配色・デザインの良し悪し）の判断は部品デザイン確定時に別途行う

## 子文書一覧（親→子リンク）
- [ideal-state.md](ideal-state.md) — あるべき姿（PO自筆・正本。書き換え禁止）
- [kgi.md](kgi.md) — KGI 6項目（承認済）
- [design.md](design.md) — 理想の設計図（承認済）
- [../component-standard.md](../component-standard.md) — 画面部品の確定値（既存・本テーマの子）
- [../../handoff/design-system-recon/recon.md](../../handoff/design-system-recon/recon.md) — 現状実測(recon)
- [migration.md](migration.md) — 移行計画（既存→理想・便0〜6・部品台帳）
- [track-record.md](track-record.md) — 便履歴と逸脱ログ

## 後続予定（未作成・在るだけ詐称をしないための明記）
- 関所実装（design.md 維持の仕組み欄参照）

## 2026-09-10 再設計の草案

既存の承認済み設計に対して、[追加実測](../../handoff/design-system-recon/recon.md#2026-09-10-追加調査と訂正) と [統一定義の全体案](design.md#2026-09-10-統一定義全体設計案未承認) を追補。草案は未承認・自己審査REVISE・製品実装未着手。


## CI補強の詳細設計

POからCI補強方針への「合意進める」を受領。全体の具体的設計・実装開始の一括承認とは扱わない。
- [ci-guard-design.md](ci-guard-design.md) — 検査不能時の誤合格防止。第一便のみ同一AI自己審査APPROVE、実装未着手。

- [ci-registry-design.md](ci-registry-design.md) — 共通部品の所有元と移行残件の管理案。自己審査REVISE。
- [実装前確認カード](../../handoff/design-system-recon/CARD-FRONTEND-MOLD-CI-RECON-01.txt) — 読み取りのみ・カード検査済み・別セッション未起動。
