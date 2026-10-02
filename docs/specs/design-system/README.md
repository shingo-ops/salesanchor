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
- [visual-language/README.md](visual-language/README.md) — アプリ視覚デザイン言語（見た目の質・PC/スマホの使いやすさを扱う子テーマ。草案 2026-10-02）

## 後続予定（未作成・在るだけ詐称をしないための明記）
- 関所実装（design.md 維持の仕組み欄参照）

## 2026-09-10 再設計の草案

既存の承認済み設計に対して、[追加実測](../../handoff/design-system-recon/recon.md#2026-09-10-追加調査と訂正) と [統一定義の全体案](design.md#2026-09-10-統一定義全体設計案未承認) を追補。草案は未承認・自己審査REVISE・製品実装未着手。


## CI補強の詳細設計

POからCI補強方針への「合意進める」を受領。全体の具体的設計・実装開始の一括承認とは扱わない。
- [ci-guard-design.md](ci-guard-design.md) — 検査不能時の誤合格防止。当該CI設計単体は同一AI自己審査APPROVE、実装は画面統一の後・最後に実施。

- [ci-registry-design.md](ci-registry-design.md) — 共通部品の所有元と移行残件の管理案。自己審査REVISE。
- [実装前確認カード](../../handoff/design-system-recon/CARD-FRONTEND-MOLD-CI-RECON-01.txt) — 読み取りのみ・カード検査済み・委任実測完了（既存22成功と誤合格再現）。


現在地: 調査・設計草案PR #3407提出済み。全体設計はREVISE。POは実装/レビュー担当への委任と順次マージを許可、完成後の目視を担当する。既存7PRの採否はmigration.md末尾、実施順序はdesign.md §Y。製品実装は未着手。


## 文書マージ後の操作契約補完

文書PR #3407マージ済み。[design.md §Z](design.md#z-実物照合後の共通部品契約2026-09-10設計担当案)に操作互換・責任別PR分割・材料生成の契約を追補。全体設計REVISE、製品実装未着手。特殊用途と最後のCI契約を照合中。目視は完成後PO。


## 最新の設計審査

全体設計は[§AA](design.md#aa-全体設計の自己審査2026-09-10)で同一AI自己審査APPROVE。これは設計合格でありPOの具体的ADR承認・製品実装/テスト・製品PRマージではない。文書PR #3407は保存済み。追加契約を次の文書PRへ保存し、数値ICON生成の限定実装カードへ進む。CIは最後、画面目視は完成後PO。


## 2026-09-28 最新の実施状況

上記9月10日の「製品未着手」は当時の履歴。現在はAS製品PR #3834と結果文書PR #3835まで本番反映済み。AS時点の共通Button265/旧232、606自動試験成功。証跡は[migration.md](migration.md)と[AS検収](../../handoff/design-system-recon/evidence-20260910/as-implementation.md)。ATは[design.md §AT](design.md#at-既存フォーム11ボタンの共通金型移管2026-09-28)に基づく11件を実装・ローカル検収済み（最新main統合後634試験成功）。画面・本番フォーム操作・PO目視はPO指示で省略・未検証。全体の残件と最後のCI補強は未完了。


2026-09-29 AT本番反映完了: 本人GO #3839、merge a5547fb7、Deploy36488806931 success。11件を共通金型へ移管、統合版共通280/旧221。root本番HEAD/公開asset hash/HTTP200/接続3項目一致を直接確認。根拠docs/handoff/design-system-recon/evidence-20260910/at-implementation.md、at-production-verification.json。画面/本番フォーム/PO目視は省略・未検証。


2026-09-29 AU着手: POは残旧221件の全数移管を依頼。最新基準303c3cfe7で221件/71fileを再測定。設計はdesign.md §AU、証拠は[全数棚卸し](../../handoff/design-system-recon/evidence-20260910/au-inventory.md)。実装前審査中。


AUローカル検収完了: 全旧221→0、661自動試験成功。成果と未検証範囲は[AU実装記録](../../handoff/design-system-recon/evidence-20260910/au-implementation.md)。PR #3855本人GO後マージ・本番反映・公開配信照合済み（Deploy36522989354）。画面省略・未検証。
