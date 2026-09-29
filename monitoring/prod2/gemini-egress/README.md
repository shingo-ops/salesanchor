# gemini-egress（prod2）

## 目的

Gemini（`generativelanguage.googleapis.com`）向けの通信だけを prod2 経由にする。
本番（prod1）が Google に「日本以外」と誤判定され、Gemini API が
`400 User location is not supported for the API use.` を返す問題への対処。
prod2 の IP から中継することで、Gemini への通信だけを迂回させる。
Gemini 以外の通信（Meta・Discord・FedEx・Drive 等）の経路は変えない。

設計の正本: [`docs/handoff/gemini-egress-via-prod2/design.md`](../../../docs/handoff/gemini-egress-via-prod2/design.md) §5-1

## 正本はここ

**このディレクトリ（`monitoring/prod2/gemini-egress/`）がリポジトリ上の正本。**
prod2 には scp で写す（コピー先が正本になるわけではない）。

```
scp -r monitoring/prod2/gemini-egress ubuntu@49.212.160.98:/opt/salesanchor-gemini-egress
```

`/opt` 直下に `ubuntu` が書き込めない場合は、代わりに
`/opt/salesanchor-monitoring/gemini-egress` に写す。

**変えるときは、必ずこのディレクトリを直してから、prod2 に写し直すこと。**
prod2 上のファイルを直接編集しない（次に写し直したときに消える）。

## 起動・停止

写し先のディレクトリで、`ubuntu` ユーザーのまま（sudo は使わない）実行する。

起動:

```
docker compose -p gemini-egress up -d --build
```

停止（元に戻す）:

```
docker compose -p gemini-egress down
```

既存の監視スタック（`monitoring-tunnel.service` 等）には一切触れない。
プロジェクト名を `gemini-egress` にすることで、監視スタックの compose とは
完全に分離している。

## 構成

- `tinyproxy`：`generativelanguage.googleapis.com:443` 宛だけを中継する HTTP CONNECT プロキシ（127.0.0.1:8888 で待受）
- `tunnel`：`autossh` で prod1 の `172.17.0.1:18888` へ逆転送（`-R`）し、prod1 側から prod2 の tinyproxy（127.0.0.1:8888）を使えるようにする

両サービスとも `network_mode: host` で動作する。
