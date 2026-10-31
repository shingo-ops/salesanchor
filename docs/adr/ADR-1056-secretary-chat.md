# ADR-1056: アプリ内のチャット秘書は、AI に会社のデータも道具も渡さず「頼みの文を決まった形に直す」だけをさせ、作成は利用者が「作る」を押したときに今の口で行う

| 項目 | 内容 |
|---|---|
| ステータス | Accepted（2026-11-01・POの委任に基づくClaude Opus発行。方針の芯は PO 決定: 本番サーバーの中に置く・004 の AI は 004 以外、001 の AI は 001 以外に触れない・月額契約で動かし約束の調査はしない・下書きを見せて「作る」で作る（選択「1」）・PO だけで始める（選択「1」）・合格の基準 K1〜K6（選択「1」）・「PRマージ、デプロイまで完走させてくれ」） |
| 起案日 | 2026-11-01 |
| 方針の決定者 | Shingo（PO） |
| 関連 | ADR-1003（secrets の変更は PO 本人）、ADR-1004（LLM 使用量台帳。Gemini 用で本テーマは書かない）、ADR-1016（変わった合図）、ADR-1052（相談係 AI。保守用で別の道）、ADR-027（i18n）、ADR-067・ADR-144（金型とデザイントークン） |
| 設計 | docs/handoff/secretary-chat/design.md（現在地: docs/handoff/secretary-chat/recon.md・recon2.md、KGI: docs/specs/secretary-chat/kgi.md） |

---

## What（何を決めたか）

- 本番サーバーに専用の容器 `secretary-agent` を 1 つ置き、中で Claude Code を月額契約のログイン（`CLAUDE_CODE_OAUTH_TOKEN`）で `-p` 実行する。道具は全部切る（`--tools ""`・`--disallowedTools "mcp__*"`・`--strict-mcp-config`）。
- AI に渡すのは利用者が書いた文と日本時間の今の日時だけ。AI が返すのは決まった形の JSON（請求書・予定・わからない、のどれか）だけ。会社のデータは渡さない。
- 名前（会社・担当者）を会社のデータから探すのは backend。今のログインの会社の範囲だけを読み取りで探す。
- 作成は、利用者が下書きを確かめて「作る」を押したときに、画面が今の `POST /invoices`・`POST /calendar/events` を利用者本人のログインで呼ぶ。AI の側に書き込みの道は無い。請求書・予定の写しを持たない。
- 容器は backnet（データベースのいるネットワーク）に入れず、backend とだけつながる `secretarynet` に置く。read_only・cap_drop ALL・no-new-privileges・mem_limit 512m・同時 1 本・80 秒で打ち切り。
- 使える人は `tenant_features` の `secretary_chat`（テナント 1・4 の 2 行）と `is_super_admin` の両方がそろった人。2026-11-01 の本番では 2 人（テナント 1 の id 1、テナント 4 の id 3）。画面と backend の両方で同じ条件を見る。
- 第1段は `llm_usage_events` に書かず、1 回ごとにログへ 1 行（頼みの文は書かない）。

## Why（なぜ）

- AI が会社のデータを読まなければ、「ほかの会社の情報に触れない」（K4）は作りの上で成り立つ。会社の判定は今の `get_current_tenant` がそのまま効く（recon2 §D）。
- 書き込みを今の口に任せると、権限確認・監査ログ・変わった合図が今のまま効き、新しい書き込みの道を作らずに済む（recon §1・§2）。
- 頼みの文に紛れた命令に AI が従っても、道具もデータも無く、返す JSON は backend が型で検査する。
- `--bare` は月額契約のログインを読まない。`ANTHROPIC_API_KEY` があると `-p` ではそちらが優先される（recon2 §A）。だから `--bare` を使わず、API キーを容器に入れない。
- `llm_usage_events` は purpose・sdk を DB の CHECK で固定している（recon2 §B）。書くには制約を作り直す必要があり、第1段の目的に対して変更が大きい。

## リスク（記録）

- 月額契約の約束に反していて契約を止められるおそれがある（約束の調査は PO が禁止）。止められてもチャットが「準備ができていません」になるだけで、請求書・予定の機能は今のまま動く。使い方をごまかす作りはしない。
- 利用者が書いた文は AI 会社へ送られる。会社のデータは送らない。
- 予定の口に権限確認が無く、予定の表の RLS の記述が無い（recon §2・§3）。使う人を広げる前に確かめる。

## Scope

- Included: 右下の印とチャットの窓（金型 `FloatingActionButton`・`ChatBubble` の登録を含む）、`POST /api/v1/assistant/messages`、名前探しの service、容器 `secretary-agent`、compose・deploy.yml、`tenant_features` の 2 行を入れる migration、i18n、試験
- Excluded: 請求書・予定そのものの作りの変更、今あるデータを直す頼み（第2段）、Codex・Grok（第1段の合格後に 1 つずつ）、使う人を広げる権限キー、`llm_usage_events` の変更

## 戻し方

- `tenant_features` の 2 行を `enabled=false` にすると、印も口も止まる。容器は compose から外せば消える。請求書・予定の表には何も足していないので、データの戻しは無い。
