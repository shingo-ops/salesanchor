# アプリ内のチャット秘書（仕様書の表紙）

この文書は、アプリの右下のチャットで AI に請求書や予定の作成を頼める機能の表紙です。

## 概要
- テナント001・004の画面の右下に吹き出しの印を出す。押すとチャットの窓が開き、AI が秘書と営業事務をする。
- AI は下書きを作るだけ。利用者が「作る」を押したときに、今のアプリの機能で作る（PO 決定 2026-11-01）。
- あるべき姿: [ideal-state.md](ideal-state.md)（PO の言葉のみ）
- KGI: [kgi.md](kgi.md)

## なぜ既存の仕様書で足りないか
- 索引（docs/specs/README.md）に、利用者向けの AI チャットの仕様書が無いため。相談係 AI（ADR-1052）は保守用で、利用者向けではない。

## 境界
- 対象: 右下の印とチャットの窓、AI の置き場（本番サーバー内の専用の容器）、名前を探す道、下書きの形、「作る」で今の機能を呼ぶ流れ、会社ごとの出し分け、使用量の記録。
- 対象外: 請求書・予定そのものの作りの変更（quote-invoice・予定の仕様のまま）、AI 会社との契約の約束の調査（PO 禁止 2026-11-01）。

## 関連
- ADR-1052（相談係 AI。保守用。本テーマとは別の道）、ADR-1024、ADR-1042、ADR-1004（使用量台帳）、ADR-1016（変わった合図）、ADR-027、ADR-144、ADR-067
- 本テーマの ADR: [ADR-1056](../../adr/ADR-1056-secretary-chat.md)

## ぶら下がる文書（子）
- [../../handoff/secretary-chat/recon.md](../../handoff/secretary-chat/recon.md)（現状の調べ）
- [../../handoff/secretary-chat/recon2.md](../../handoff/secretary-chat/recon2.md)（現状の調べ 第2回）
- [../../handoff/secretary-chat/design.md](../../handoff/secretary-chat/design.md)（設計 第3版）

## ステータス
- あるべき姿: PO 発言を転記（2026-11-01）
- KGI: PO 承認済み（2026-11-01「1」）
- 設計: 第3版（第2版への審査役の REVISE に全部答えた。再審査中）（2026-11-01・同じ AI の審査）
