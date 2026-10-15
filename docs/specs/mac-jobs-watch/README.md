# Mac の自動お手入れの見張り（mac-jobs-watch）

この文書は何か(専門用語なしの1行): PO の Mac で毎日・15分ごとに動く自動お手入れが、止まったり失敗したりしたら Discord で知らせるテーマの表紙。

## 背景（事実）
2026-10-15 11:48 の実測で、Mac の自動お手入れ2つ（Docker 使い終わり自動停止・毎日の自動片付け）は動いていたが、止まったり失敗したりしても人に知らせる仕組みが無かった（/tmp/CC報告ファイル/ac-heavy/governance/SUMMARY.md、G6.txt）。また、同じ Mac の別の見張り役（受付の番人 jp.salesanchor.ops-intake-watchdog）は、置き場に設定があるのに launchd に読み込まれておらず、止まっていることに誰も気づいていなかった（/tmp/CC報告ファイル/ac-heavy/notify-recon/R2.txt）。

## 境界
- 対象: PO の Mac の launchd 常駐 `jp.salesanchor.colima-idle-stop`（[colima-idle-stop](../colima-idle-stop/README.md)）と `jp.salesanchor.disk-janitor`（毎日の自動片付け）の死活と失敗の通知。Mac 起動後の点検結果の通知。
- 対象外: 受付の番人 ops-intake-watchdog の再開（ADR-1009 の領域。事実だけ PO に報告）／ 本番サーバーの監視（ADR-080）／ 見張り役自身が止まったことの検知（Mac の外に見張りを置く必要があり、本テーマでは扱わない。残る弱点として [design.md](../../handoff/mac-jobs-watch/design.md) §7 に記録）

## ステータス
- 設置済み・K1〜K5 合格（2026-10-15、PR #4315）。K6（再起動後の自動再開）は PO の次の再起動後に観測

## 子文書
- [あるべき姿](./ideal-state.md)
- [KGI](./kgi.md)
- 設計: [docs/handoff/mac-jobs-watch/design.md](../../handoff/mac-jobs-watch/design.md)、recon: [docs/handoff/mac-jobs-watch/recon.md](../../handoff/mac-jobs-watch/recon.md)
