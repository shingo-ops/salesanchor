# recon: gemini-egress 片付け（PR-4）

対象コミット: origin/main c3fce9326

## 事実

1. `monitoring/prod2/gemini-egress/tunnel/Dockerfile` は未使用の残骸。
   - 根拠: `docs/handoff/gemini-egress-via-prod2/design.md:99`（改訂前）「未削除の残骸：`monitoring/prod2/gemini-egress/tunnel/`（Dockerfile 一式）は、この改訂で使わなくなったが削除していない」
   - 根拠: `monitoring/prod2/gemini-egress/README.md:56`（改訂前）「`tunnel/`（Dockerfile）は 2026-09-30 の方式変更で使わなくなった。compose からは外してある。削除は、あとの片付けの便で行う。」
   - 根拠: `monitoring/prod2/gemini-egress/docker-compose.yml` に `tunnel` サービス定義が無い（grep 0件）。

2. `docs/adr/ADR-080-monitoring-vps-separation.md` は、管理室VPS の prometheus がアプリVPS の exporter を HTTP で直接スクレイプし、ポートをファイアウォールで管理室VPS IP からのみ許可する前提（本文「VPS間通信」「ファイアウォール」の項、旧行番号 89, 93, 95, 135, 155 付近）で書かれている。
   - 実際の prod2 は systemd `monitoring-tunnel.service` による autossh トンネル方式（prod2→prod1、`-L 0.0.0.0:19100/19187/19113/19121`、`-R 0.0.0.0:13100:127.0.0.1:3100`、`Restart=always`、`RestartSec=10`）を使っている。
   - 根拠: `docs/handoff/gemini-egress-via-prod2/recon.md:47`「prod2 の `monitoring-tunnel.service`（`/etc/systemd/system/`）が、autossh で prod2 から prod1 へ常時つないでいる。`-L 0.0.0.0:19100/19187/19113/19121` と `-R 0.0.0.0:13100:127.0.0.1:3100`。`Restart=always`、`RestartSec=10`」（実測コマンド: prod2 で `systemctl cat monitoring-tunnel.service`）
   - 根拠: `docs/handoff/gemini-egress-via-prod2/recon.md:48`「この unit はリポジトリに無い（`autossh`・`tunnel-key`・`ExitOnForwardFailure` で grep すると0件）」

3. `backend/app/services/gemini_extraction_svc.py` の docstring/コメントが古いモデル名を指していた。
   - 実際のモデル定数: `_GEMINI_MODEL = "gemini-3.1-flash-lite"`（同ファイル 282行目、変更なし）
   - 旧記述（変更前の実測）:
     - 5行目: `Gemini 3.6 Flash で LINE メッセージから商品明細を抽出する。`
     - 15行目: `  - モデル: gemini-3.6-flash / temperature=0`
     - 377行目: `    モデル: gemini-3.6-flash（GAS 側デフォルトと同一）`
   - カード指定の置換文言と一部フォーマットが異なっていた（15行目のみ完全一致、5・377行目は表記ゆれ）が、いずれも「gemini-3.6-flash」という誤ったモデル名を指す点は共通のため、カード指定どおりに置換した（詳細は design.md 参照）。

## 変更方針

- ADR-080 の決定文（本文）は変更しない。末尾に「実物との差分」を追記節として記録するのみ。
- `monitoring-tunnel.service` 自体（unit ファイルのリポジトリ管理）は対象外。
- 実行コードの変更なし（コメント・docstring・ドキュメントのみ）。
