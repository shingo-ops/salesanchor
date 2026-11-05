# Discord サーバーをシステムと Bot で管理する（discord-server-management）

> この文書は何か：会社ごとの Discord サーバー（自社用・顧客用）のチャンネルとロールを、人が手で直さず、アプリの設計図と SA Bot で管理する仕組みの表紙です。

## 概要

PO が「こうしたい」と話す → 設計パートナーが設計図と仕組みを直す → 審査と反映のあと PO がアプリのボタンを押す → SA Bot が Discord サーバーの違うところだけを直す。

## 境界

- 対象（第1段）: 自社用サーバー（社内の連絡用）のカテゴリ・チャンネル・ロール・チャンネルの見せ方（権限の上書き）
- 対象外（第1段）: 顧客用サーバーの今の自動作成（`/admin/discord/auto-setup`）は変えない。メンバーへのロール付与。通知の新設（支払いの通知などは別テーマ）
- 自動では消さない: 設計図に無いチャンネル・ロールは「消す候補」として出すだけ
- 対象（第2段・案）: アプリの役割と同じロールの用意とスタッフへの自動の付け外し、「アサイン連絡」「返信連絡」「部屋の外の書き込み」の知らせの部屋（KGI 8〜15）
- 対象外（第2段）: アプリに登録していない人（その他関係者）のロール。各テナントが Discord で作って手で付ける（サポート対象外）。Bot は自分が管理するロール以外を付けも外しも消しもしない

## ステータス

| 日付 | 状態 |
|---|---|
| 2026-11-04 | あるべき姿（PO の言葉）記録・KGI 1〜7 PO 承認（「1」） |
| 2026-11-04 | recon（[../../handoff/discord-server-management/recon.md](../../handoff/discord-server-management/recon.md)）・設計図の置き場所 PO 決定「1」（リポジトリに履歴付き）・設計案（[../../handoff/discord-server-management/design.md](../../handoff/discord-server-management/design.md)、自己審査 APPROVE）・設計 PO 承認「1」（この設計で承認し、自社用サーバーの登録から作り始める）・便1a 実装カード（[../../handoff/discord-server-management/card-bin1a-purpose-column.md](../../handoff/discord-server-management/card-bin1a-purpose-column.md)） |

| 2026-11-05 | 便3b（反映するボタン）本番反映。要件定義（誰を入れるか・ロール・知らせの部屋）を PO の言葉で記録。第2段 KGI 8〜15 を案として起こした（PO 承認待ち） |

## 文書

- [ideal-state.md](ideal-state.md) — あるべき姿（PO の言葉）
- [kgi.md](kgi.md) — KGI
- 関連 ADR: ADR-091（Bot の担当業務と権限）、ADR-009、ADR-098
