# Docker（Colima）使い終わり自動停止（colima-idle-stop）

この文書は何か(専門用語なしの1行): PO の Mac で、使い終わった Docker（試験用データベースの入れ物）を自動で止めてメモリを空けるテーマの表紙。

## 背景（事実）
2026-10-15 08:37 JST の実測で、8GB の Mac のうち何にも使われていない分は 149MB、Docker（Colima）が 2.0GB を確保していた（/tmp/CC報告ファイル/ac-heavy/now-status.txt）。09:11 の調査では、試験用データベース1つが CPU 0%・ほかからの接続なしのまま約5時間動いていた（/tmp/CC報告ファイル/ac-heavy/docker-idle/）。

## 境界
- 対象: PO の Mac（開発機）で動く Colima profile `default` の自動停止（15分ごとの見回り役 `scripts/colima-idle-stop.sh` と launchd 登録 `ops/launchd/jp.salesanchor.colima-idle-stop.plist`）
- 対象外: 本番サーバー（prod1・prod2）のメモリ・ディスク（[server-resource-optimization](../server-resource-optimization/README.md)）／ Colima の自動起動／ 他の profile（例: sa-private-ci）／ Mac の毎日の自動片付け（disk-janitor）

## ステータス
- 実装・設置済み: PR #4294 マージ（2026-10-15、merge 0094e6d9a）。launchd に設置し 900 秒ごとに動作中。
- KGI: K1〜K6 のうち K1・K2・K3a・K3・K4・K5 は 2026-10-15 に合格（[kgi.md](./kgi.md)）。K6（放置での自然停止）は観測待ち。
- 経緯: 当初は「Mac 専用の保守道具なので仕様書を作らない」と判断したが、2026-10-15 に PO が「作らない判断でよいか」に N と答えたため本仕様書を作成。

## 子文書
- [あるべき姿](./ideal-state.md)
- [KGI](./kgi.md)
- 設計: [docs/handoff/colima-idle-stop/design.md](../../handoff/colima-idle-stop/design.md)（recon・Fable 審査記録も同じフォルダ）
- 運用手順（設置・確認・戻し方）: [docs/ops/runner-commands.md](../../ops/runner-commands.md) の「Docker（Colima）の自動停止」節
