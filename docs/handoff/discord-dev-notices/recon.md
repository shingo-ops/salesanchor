# recon: 開発の知らせ 4 種の届け先（2026-11-22）

根拠は `git fetch` 後の origin/main（214e88d20）と、本番サーバーからの Discord Bot の読み取り。

## 1. 既存の ADR・設計
- `docs/adr/ADR-1039-discord-pdca-agent-console.md`（Discord の受付と agent-console）
- `docs/adr/ADR-035-external-state-verification.md`（毎週の外部の状態の写し。送り口の id の変化を差分として出す）
- `docs/adr/ADR-1012-ai-ops-247.md`（AI 保守運用）
- 前の作業 `docs/handoff/discord-channel-consolidation/design.md` §2 の対象外に「別のサーバーに届く PR・CI・PLAN_REVIEW・レビューのメール」とある。本件はその続き。

## 2. 送り口ごとの使い手（file:line）
| 鍵（GitHub secret） | 使う場所 |
|---|---|
| `DISCORD_WEBHOOK_PR` | `.github/workflows/discord-pr-notify.yml:21` `:61` `:92` `:160` `:198`、`.github/workflows/external-state-snapshot.yml:100`、`scripts/snapshot/discord.sh:81`、`scripts/smoke/external-discord.sh:59` |
| `DISCORD_WEBHOOK_CI` | `.github/workflows/discord-ci-notify.yml:100`（PR の点検のまとまりが終わるたび） |
| `DISCORD_WEBHOOK_PLAN_REVIEW` | `.github/workflows/hook-permission-check.yml:43`（失敗時だけ）、`.github/workflows/external-state-snapshot.yml:101`、`scripts/snapshot/discord.sh:81`、`scripts/smoke/external-discord.sh:60` |
| `REVIEW_MAIL_DISCORD_WEBHOOK` | `backend/app/services/review_mail_notifier.py:42`（起動時に環境変数を読む）、`docker-compose.yml:262`、`.github/workflows/deploy.yml:367`（古い行を消す）・`:429`（secret から書く） |

- `REVIEW_MAIL_DISCORD_WEBHOOK` は本番の `.env` に書かれる。GitHub の鍵を替えても、次の本番反映（`.github/workflows/deploy.yml` は main への push で動く）までは前の値のまま。
- 外部の状態の写しは 11/7・11/14 とも failure（別の原因・本件の対象外）。

## 3. 変更前の届け先（観測）
- 4 つとも guild 1288437029213835356（PO によると HIGH LIFE JPN のサーバー）のチャンネルへ届く。Bot はこのサーバーに入っていないので、中は読めない。
- 本番の `REVIEW_MAIL_DISCORD_WEBHOOK` の送り口 id は 1515524826645922025（値は控えに保存。画面に出していない）。
- Sales Anchor の「アラート」分類（1527986884624519208）の中に、開発の知らせのチャンネルは無い。
