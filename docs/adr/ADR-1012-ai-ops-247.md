# ADR-1012: 監視の通知から応急処置と AI（Claude Code routines）を起動し、障害記録で振り返る 24 時間保守運用

| 項目 | 内容 |
|------|------|
| ステータス | Proposed |
| 経緯 | KGI 6 件は PO が 2026-10-13 に「Cも予備で構築して動作確認まで完結させる、その条件付きでy」と回答。全体設計は審査中。段階ごとに実装カードと PO の実装承認を取る |
| 作成日 | 2026-10-13 |
| 起案 | Claude Opus（設計担当） + しんごさん（PO あるべき姿・KGI） |
| 関連 | ADR-1009（予備 C：Mac 上の Discord 受付）、ADR-115（デプロイ自動ロールバック）、ADR-079（監視の読み取り専用アクセス）、ADR-080/081（監視 VPS）、ADR-136（危険 PR の GO・ADR-136-cc-bot-github-identity.md）、ADR-1004（LLM 使用量台帳） |
| 根拠 | docs/specs/ai-ops-247/、docs/handoff/ai-ops-247/recon.md、docs/handoff/ai-ops-247/design.md |

---

## Context

- 一次記録のある過去の障害 4 件のうち、報知器が人より先に鳴ったのは 0 件（recon §4）。計器の無いアラートルールが 4 本あり、BackendHighLatency は直近 14 日で 320 回に分かれて鳴っている（recon §1・§2）。
- unhealthy のコンテナを自動で再起動する仕組みが無い。定義済みの応急処置は抽出ジョブの回収とデプロイ時の自動ロールバックだけ（recon §3）。
- 障害の記録・振り返り・成績表が無く、改善が測れない（recon §5）。
- ADR-1009 の受付は PO の Mac が起きている間しか動かない（recon §6）。
- Claude Code routines（研究プレビュー）は API の /fire で起動でき、公式の使い道に監視ツールからの起動（Alert triage）が載っている。利用はサブスクの枠から引かれる（公式・recon §6）。
- リポジトリは PUBLIC のため、障害記録を repo や Issue に置けない。

## Decision

1. 経路の正本は Alertmanager 1 本。全アラートルールに札（page / auto / ticket）と手順書リンクを付ける。
2. 障害記録・処置・AI の調べ・振り返りの正本はアプリ DB の障害記録の表 1 か所。書き込みは保守 API（backend）からだけ。Discord と成績表画面は表示だけ。
3. 応急処置は prod1 ホストの定期実行が repo の「症状→処置」一覧に載った処置だけを行う。回数の上限と全停止スイッチを持つ。
4. AI の本命は Claude Code routines（B・クラウド）。保守 API が障害 1 件に 1 回 /fire を呼ぶ。AI は本番へ直接書かず、止血は一覧の処置の依頼、修理は PR として既存の審査・CI・GO（ADR-136）を通す。
5. ADR-1009 の受付（C）は予備として構築と動作確認まで完了させ、B が着手しなかった障害だけを扱う。B と C は repo の共用担当定義 1 ファイルを読む。
6. 不可逆操作（データ削除・secrets・お金）は AI が止まって PO に承認を求める。

## Why

- 自動化の暴走は自動では止まらない（AWS DynamoDB 2025-10）→ 全停止スイッチと回数の上限。
- 指示（プロンプト）は防壁にならない（Replit 2025-07）→ 権限で塞ぐ（DB 直結なし・SSH なし・鍵は VM の外の network secrets）。
- AI の自動解決率は SRE 課題で 11.4%（ITBench 2025）→ AI の修理は人と同じ審査を通す。
- 「対応が要らない通知はページにしない」（Google SRE book 第 6 章）→ 札で振り分け、精度を KGI 2 で測る。
- 記録の正本を 1 か所にすると、KGI 1〜6 を同じデータから計算できる（PO 条件「データを分散させない」）。

## Consequences

- 監視からの常時起動がサブスクの「ordinary, individual usage」の範囲に入るかは公式文書に明言が無い（recon 不明点 7）。段階4 の前に PO 判断を仰ぐ。
- routines は研究プレビューで、サブスクの枠を B と C で共有する。枠切れ・仕様変更時は Discord 通知で人に戻る。代替候補は GitHub Actions の claude-code-action（design.md §8 案 D）。
- 障害記録の表の追加は migration（危険 PR）になり、ADR-136 の GO が要る。
- 段階4 で PO が Web で routine を作り、トークンを本番の secrets に登録する作業が要る。
- AI の修理 PR のマージ権限は広げない。広げるかは月次成績表の実績を見て PO が判断する。

## 追記（2026-10-22・ADR-1039 から。決定は変えない）

- Decision 5 の「repo の共用担当定義 1 ファイル」は `docs/ai-agents/ops-incident-agent.md` とする。ADR-1039（Discord の不具合報告を agent-console で受ける件）の便2 で先に作る。段階4 の B の節は段階4 の設計で足す。
- Decision 5 の予備 C（ADR-1009 の受付）は、ADR-1039 で全部置き換える（PO 2026-10-21「1」）。ADR-1039 が Accepted になったときに効く。
