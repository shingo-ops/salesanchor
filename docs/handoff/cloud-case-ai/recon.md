# recon: クラウドの保守相談AI 設計の現在地

実測時の origin/main SHA: bcd6bd3571ca1101143e8f32e9aedd23574be1c3

目的: Discord の投稿で始まるクラウドの保守相談AIの設計の現在地。

## 既存 ADR の検索結果

コマンド: git grep -n -i -m1 "discord\|クラウド\|cloud\|routine\|相談係" -- docs/adr/（ファイルごとの最初の1件・生の結果）

```
docs/adr/ADR-009-discord-gateway.md:1:# ADR-009: Discord Gateway Worker
docs/adr/ADR-011.md:183:| docs/ADR-009_discord_gateway.md | docs/adr/ADR-009-discord-gateway.md | 中（次スプリント） |
docs/adr/ADR-012-what-how-separation.md:109:- **ADR-009**: Discord Gateway → 変更なし
docs/adr/ADR-013.md:20:- LP（salesanchor.jp）、Discord通知、メールテンプレートなど frontend アプリ以外のロゴ
docs/adr/ADR-014-inventory-management.md:1:# ADR-014: 在庫管理モジュール — Discord 自動収集 + AI 解析 + 自己改善ループ
docs/adr/ADR-015.md:35:- 問い合わせチャンネルが複数（Messenger / Instagram / Discord / Telegram）あり、同一人物の重複対応が発生している
docs/adr/ADR-021-order-management.md:209:6. **eLogi CSV 出力の実装方式**: バックエンドで生成 / フロントで生成 / Cloud Function 切り出し のどれが運用上良いか
docs/adr/ADR-024_meta_integration_structural_fix.md:6:- **関連 ADR**: ADR-009 (Discord Gateway / 認証基盤), ADR-022 (UI Meta Business Suite 風), ADR-023 (スタッフライフサイクル 3
docs/adr/ADR-025_meta_integration_operational_hardening.md:92:- 監視・アラート機構の本格整備（Sentry または Slack/Discord 通知）
docs/adr/ADR-026_meta_messages_message_id_text.md:69:- IG 受信時の通知文言の変更（Discord 通知メッセージは既存のまま）
docs/adr/ADR-027-ui-internationalization.md:86:- BOX・Discord・LINE などの固有名詞も、画面に出す言葉は t() を通す。ja の値は英字のままでよい。例外を作らず、検査の除外を増やさないため。
docs/adr/ADR-029-self-hosted-runner-fleet.md:32:| runs-on: ubuntu-latest | GitHub-hosted runner | feedback-issue-triage.yml, e2e.yml, deploy.yml, disco
docs/adr/ADR-035-external-state-verification.md:12:外部システム（Meta App / Firebase Auth / GitHub Secrets+Actions / Cloudflare DNS / Discord Webhook / GCP IAM）の状態が re
docs/adr/ADR-038-qa-smoke-suite.md:37:scripts/qa/reset-tenant.sh で flock 排他 → tenant_code assert → TRUNCATE → seed 投入 → 行数 assert を実行。実装は冪等。撮影との時間衝突は flock
docs/adr/ADR-042-guardrails-and-release-flow.md:63:- 失敗時 (conflict 等): Discord 通知 → 手動対応
docs/adr/ADR-049-lp-section-completion.md:84:  - Discord
docs/adr/ADR-051-claude-pipeline-full-automation.md:33:  → 両 APPROVE 完了通知 (Discord)
docs/adr/ADR-053-claude-pipeline-decision-parsing-fix.md:117:- Discord 通知フォーマットの全面刷新 (ADR-053 とは別論点、必要なら別 ADR)
docs/adr/ADR-056-human-in-the-loop-minimization.md:17:1. PR open 後、Discord 通知でしんごさんが diff 確認指示を受ける
docs/adr/ADR-068-platform-brand-asset-policy.md:13:同様に Discord・Telegram も独自のブランドガイドラインを持ち、公式アセットの使用を推奨（または義務化）している。
docs/adr/ADR-069-uptime-kuma-activation.md:37:1. Cloudflare DNS: monitor.salesanchor.jp A レコード → VPS IP を追加
docs/adr/ADR-075-github-secrets-only-policy.md:42:| DISCORD_BOT_TOKEN_* | Discord Bot トークン |
docs/adr/ADR-080-monitoring-vps-separation.md:88:- PO が GUI 操作する項目: VPS 契約、ファイアウォール設定、DNS 設定（Cloudflare）
docs/adr/ADR-081-monitoring-vps-final-operational-design.md:26:| PostgreSQL / Redis / Celery / Discord gateway | 既存同居を維持 |
docs/adr/ADR-082-generator-executor-codex-fallback.md:56:3. いずれのケースも GENERATOR_FALLBACK=true を $GITHUB_ENV に書き込み、後続の Discord 通知ステップが発動
docs/adr/ADR-089-deprecate-customers-unify-to-companies.md:15:| customers | 52件 | 請求先・配送先・Discord webhook・販売チャネルを持つ旧顧客マスタ | Phase 1 初期に作成。companies と二重管理 |
docs/adr/ADR-090-products-central-unification.md:1:# ADR-090: products アーキテクチャ統一（tenant別 → public 中央）と Discord取込→在庫表反映
docs/adr/ADR-091-discord-bot-scope-definition.md:1:# ADR-091: Discord Bot 担当業務スコープ定義・実装記録
docs/adr/ADR-092-deploy-concurrency-control.md:53:（backend / frontend / celery-worker / celery-beat / discord-gateway）**に拡張し、
docs/adr/ADR-093-inventory-table-product-master-redesign.md:17:在庫数は常に 0 で表示される。一方 Discord 受信の取り込み（承認）は
docs/adr/ADR-095-sa-ssot-two-backbone-architecture.md:101:2. **多チャネルの取り込み（webhook/API）** … 6チャネル（Messenger/Instagram/WhatsApp/Discord/Telegram/Email）の受信を会話ログへ取り
docs/adr/ADR-098-sa-multi-channel-identity-resolution.md:11:顧客は複数チャネル（Messenger/Instagram/WhatsApp/Discord/Telegram、将来Email）から来る。プラットフォーム間に「同一人物」を判定する共通キーは無い。
docs/adr/ADR-1003-go-delegation-to-opus.md:40:- 外部 GUI（Cloudflare・Firebase 等）の操作
docs/adr/ADR-1004-llm-usage-ledger.md:25:1. **新表 public.llm_usage_events**（1行 = Gemini の応答1回）を新設する。purpose（使いみち）・tenant_id・model・sdk・6種のトークン数列（prompt
docs/adr/ADR-1008-person-ssot-users-id.md:8:| 関連 | ADR-023（スタッフの3層同期・提案）、ADR-091（Discord 接続）、ADR-159（Discord 上のスタッフ識別）、ADR-1003（GO 委任）、ADR-1007（migration は構造だけ）
docs/adr/ADR-1009-discord-ops-intake.md:1:# ADR-1009: Discord の監視通知を Claude Code の常駐受付で受け、不具合ごとの担当が承認チャンネルで対応する
docs/adr/ADR-1012-ai-ops-247.md:1:# ADR-1012: 監視の通知から応急処置と AI（Claude Code routines）を起動し、障害記録で振り返る 24 時間保守運用
docs/adr/ADR-1019-inventory-viewer-separate-accounts.md:6:| 備考 | PO の決定済み：閲覧者はアプリのユーザーにしない（2026-10-15 Y）。列は今の本番の GAS と同じ14列（Q1 y・Q13 y、2026-10-15。発送日を含む）に、アプリと同
docs/adr/ADR-1025-analysis-error-report-autofix.md:1:# ADR-1025: 解析の誤り報告から自律修正まで — 報告は本番の表 1 か所、起動は agent-console が Discord の 1 チャンネルを読む
docs/adr/ADR-1039-discord-pdca-agent-console.md:1:# ADR-1039: Discord の不具合報告を agent-console で受け、件ごとに Opus が対応と効果測定を回す
docs/adr/ADR-1042-cloud-read-window.md:1:# ADR-1042: クラウドから本番を読むだけの HTTPS 窓口を、読む人の接続だけを持つ専用コンテナで作る
docs/adr/ADR-1043-accuracy-gold-in-db.md:1:# ADR-1043: 精度測定の正解表を本番 DB の専用表に置き、クラウドは読むだけの窓口から取り出す
docs/adr/ADR-1049-lead-merge-all-tables-and-fill-blanks.md:25:8. ADR-119 の「lead 新規作成時は同一トランザクション内で lead_channels にも INSERT する」は、「窓口の番号を持つ経路（Meta・Discord の受信）だ
docs/adr/ADR-1050-api-error-auto-retry.md:18:3. 3回とも失敗した分と、24時間を過ぎた分は「諦めた」として、次の見回りで管理者用の Discord に1回だけ知らせる。
docs/adr/ADR-1051-prod-ui-black-box-check.md:6:| 備考 | PO 決定 2026-10-30: D1「1」（作り直し・方式B）、D2「1」（旧 qa-smoke の自動実行を止める）、D3「1」（tenant_001）、D4「1」（不合格のときだけ Discord）、D5
docs/adr/ADR-107-sa-analytics-agent-a-customer-priority.md:32:| discord_notifier | backend/app/services/discord_notifier.py:1 | 208行 | ADR-025 監視通知の流用元（ADM
docs/adr/ADR-108-inbox-karte-panel-redesign.md:20:- 連絡先タブは手入力URL欄・旧式 DISCORD ID 形式で属人的。
docs/adr/ADR-109-leads-status-ssot-immutable-codes.md:44:| バックエンド直書き | backend/app/services/discord_gateway/dm_writer.py (100行) | 新規lead作成の初期値 |
docs/adr/ADR-110-sa-translation-subsystem.md:39:| 監視 | 失敗率・遅延・低確信度多発を Discord 通知（ADR-025 3点セット） |
docs/adr/ADR-114-worktree-auto-cleanup.md:95:- 各 Mac は **自分の部屋だけ** を掃除する（中央集計はしない＝クラウドからフォルダは見えないため構造的に不可）。
docs/adr/ADR-115-deploy-safety.md:24:- 結果（成功 or 失敗）を Discord 通知
docs/adr/ADR-119-lead-channels-and-lead-merge.md:43:| platform | VARCHAR(30) NOT NULL | 'messenger' / 'instagram' / 'discord' |
docs/adr/ADR-124-sop-health-reporter.md:14:3. ゼロ許容条件（宿題期限超過）を検知したら Discord #scheduled-report へ即通知する。
docs/adr/ADR-141-inbound-translation-entry.md:9:Discord ticket と Meta inbound は受信保存後の即時翻訳 enqueue を個別に持っていた。Meta はこれまで翻訳 enqueue の標準入口がなく、将来の新チャンネル追加時に実装差分が増えやす
docs/adr/ADR-150-agent-domain-windows.md:8:複数エージェント（設計パートナー／実装役／Codex）が同一リポジトリを触る体制で、担当領域が暗黙だと重複作業と抜けが生じる。recon 実測で、外部接続系ファイルが backend/app/services/ と backend/a
docs/adr/ADR-153-data-durability.md:19:- 失敗時の通知は DISCORD_WEBHOOK_OPS が設定されているときのみ動くが、prod1 の .env にも crontab にも当該変数は無く、約3か月の失敗は通知されなかった。
docs/adr/ADR-159-staff-identity-on-discord.md:1:# ADR-159: Discord 返信を担当者の名前・アイコンで送る
docs/adr/ADR-999-pipeline-test.md:22:- Discord通知が「実装開始」「成功（変更なし）」と流れること
docs/adr/ADR-SA-17-translation-bidirectional-glossary-two-layer.md:116:3. **監視/通知**：即時翻訳失敗・sweeper 拾い・昇格キュー滞留 を Discord 通知
docs/adr/FEATURE-INDEX.md:18:| 在庫 / inventory / 商品マスタ / 仕入元 / オファー | **ADR-099** ／ ADR-093 ／ ADR-014 | 在庫モデル・商品/在庫マスタ分離・Discord 収集 |
docs/adr/README.md:22:| [ADR-009](./ADR-009-discord-gateway.md) | ADR-009: Discord Gateway Worker | Accepted | — | — |
docs/adr/karte_reference.html:164:      '<div style="margin-bottom:10px;"><a class="dlink" href="#" onclick="return false;">Discordで開く '+EXT+'</a></div>'+
```

コマンド: grep -n -i "discord\|クラウド\|cloud\|routine\|相談係" docs/adr/FEATURE-INDEX.md（生の結果）

```
docs/adr/FEATURE-INDEX.md:18:| 在庫 / inventory / 商品マスタ / 仕入元 / オファー | **ADR-099** ／ ADR-093 ／ ADR-014 | 在庫モデル・商品/在庫マスタ分離・Discord 収集 |
docs/adr/FEATURE-INDEX.md:20:| 取り込み / 解析 / パイプライン / Discord 収集 | **ADR-100** ／ ADR-014 ／ ADR-1050 | 提供元メッセージ→生オファー。一時的に断られた解析の送り直しと、諦めた分の知らせ・月曜の数の知らせは ADR-1050 |
docs/adr/FEATURE-INDEX.md:49:| 担当者アイコン / 英語名必須 / Discord webhook 送信 / avatar | **ADR-159** ／ ADR-091 | Discord 返信を担当者の名（given_name_en）とアイコンで送る・Bot 名義では送らない（便A=アイコン+英語名必須 / 便B=webhook 送信） |
docs/adr/FEATURE-INDEX.md:50:| 24時間保守運用 / 障害記録 / 応急処置 / routines / アラート札 page・auto・ticket | **ADR-1012**（Proposed） ／ ADR-1009 ／ ADR-115 | 経路の正本は Alertmanager・障害記録の正本はアプリ DB・AI は PR で修理（ADR-136 の GO）・C は予備 |
```

## 非公開の記録について

詳しい調査記録（今の姿・クラウドの仕組み・段0の試し）は非公開の記録に置いた。公開リポジトリには置かない（PO 2026-10-30 決定）。
