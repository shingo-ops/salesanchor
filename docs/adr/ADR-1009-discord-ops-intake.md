# ADR-1009: Discord の監視通知を Claude Code の常駐受付で受け、不具合ごとの担当が承認チャンネルで対応する

| 項目 | 内容 |
|------|------|
| ステータス | Accepted（PO 2026-10-13「確立したなら進める」「PRマージ、デプロイまで完走させてくれ」。試作で E1〜E6 成立・独立レビュー REVISE 指摘を反映） |
| 作成日 | 2026-10-13 |
| 起案 | Claude Opus（設計担当） + しんごさん（PO 運用像・委任方針） |
| 関連 | ADR-080（監視 VPS 分離・監視通知の出どころ）、ADR-136（危険 PR の GO）、ADR-1003（GO 委任） |
| 根拠 | docs/handoff/discord-ops-intake/recon.md、docs/handoff/discord-ops-intake/design.md、docs/specs/discord-ops-intake/ |

---

## Context

- 監視（Alertmanager・Grafana・デプロイ通知）は Discord の監視チャンネルへ webhook で通知している。2026-10-12 の本番では監視チャンネルに 10 時間で 50 件届いていた（recon）。
- Claude Code の channels 機能（研究プレビュー）で Discord ボットのメッセージを常駐セッションに届けられる。ただし公式 Discord プラグインはボット・webhook の投稿を捨てる（server.ts:806、実測で確定）。
- 公式の許可リストに無い改変版は `--dangerously-load-development-channels` で起動する必要があり、起動のたびに確認画面が出る。
- 担当（バックグラウンドのサブエージェント）の許可確認は Discord に中継されない（2026-10-13 実測）。受付役自身の許可確認は中継される。

## Decision

1. 公式 discord プラグイン 0.0.4 を複写した `discord-ops` を `tools/claude-channels/` に置き、変更は P0〜P9 と判定ロジックの lib.ts への切り出し（単体テスト付き）に限る（許可 webhook だけ通す・webhook は承認できない・embed を読む・返信先は承認チャンネルとその子スレッド・許可確認と解決策のボタンは承認チャンネルへ・承認は保存した操作の原文に結び付ける・停止中のアラートを拾う）。
2. 受付役は PO の Mac 上の常駐 Claude Code セッション 1 つ（manual モード）。不具合ごとに custom agent `ops-worker`（書き込み道具を持たない・dontAsk・background）を立て、承認チャンネルの不具合スレッドで対応させる。
3. 承認後の実行は受付役だけが行い、実行するのは decision 通知に付いた操作の原文だけ。委任表の外の操作は承認チャンネルの許可確認で PO が押すまで止まる。
4. AI が承認なしで行える範囲は委任表（docs/specs/discord-ops-intake/delegation.md）で定め、受付の許可設定とツール単位で 1 対 1 にする。委任の拡大は PO の言葉を起点に履歴を残す。
5. 監視側（Alertmanager・Grafana・Deploy 通知）の設定は変更しない。

## Why

- 公式プラグインの部品（ペアリング・許可の中継・ボタン認可）は動作確認済みで、変更を最小にすると公式更新の取り込みが容易。
- 担当の許可確認が中継されない実測のため、承認が要る操作は受付役に集約するしかない。
- 承認を ID だけに結ぶと、通知本文を読んだ担当が注入を受けて別の操作を同じ ID で依頼できる（独立レビュー HIGH-2）。PO が画面で読んだ原文だけを実行すれば防げる。

## Consequences

- 受付は Mac が起きていてセッションが開いている間だけ動く。停止は番人（launchd）が別の webhook で PO に通知し、再起動は PO が起動確認画面に 1 回答える。
- 研究プレビューの仕様変更で動かなくなりうる。退避先は定期確認方式（design.md 代替案 B）。
- 承認チャンネルの閲覧者には許可確認の中身（コマンド全文）が見えるため、本番の承認チャンネルは非公開にする（PO の Discord 操作）。

## 追記（2026-10-22）

- ADR-1039（Proposed）で全部置き換える（PO 2026-10-21「1」）。ADR-1039 が採用になったときに、このステータスを ADR-1039 による置き換え済みに直す。
