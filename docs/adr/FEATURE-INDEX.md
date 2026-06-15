# 機能 → ADR 索引（着手前に必ず確認）

> **目的**: 機能に着手する前に「その領域の設計がすでに ADR で決まっていないか」を即座に引けるようにする索引。
> ADR は CLAUDE.md と違い自動ロードされない＝**指さないと参照されない**。見落とし防止のため、recon 段階で
> 必ずこの索引と `git grep -i "<機能キーワード>" docs/adr/` の両方で既存設計を拾うこと（[[docs/STANDARD-WORKFLOW.md]] Phase 2）。
>
> 網羅一覧は自動生成の [`README.md`](./README.md)。本ファイルは**主要ドメインの正準 ADR**だけを人手でキュレートする。
> 新しい主要機能の ADR を起案したら、ここにも 1 行追記する。

## 受発注・請求まわり（Sales Anchor コア業務）

| 機能キーワード | 正準 ADR | 補足 |
|---|---|---|
| 見積 / 請求 / invoice / quote / PDF / 発行モード | **ADR-101** | 正規化2テーブル・テンプレSSOT・発行モード。PayPal は Invoicing 方式（2026-06-12 改訂） |
| 決済 / 入金確認 / payment / PayPal / Wise / 売上 / P&L | **ADR-104** ／ ADR-101 §6 | 入金確認→受注ステータス遷移・売上計算。ADR-021 も受注報酬計算 |
| 受注 / order / フルフィルメント / 引当 / 発注 | **ADR-102** ／ ADR-021 ／ ADR-071 | 受注管理・発注最適化・ナビ導線 |
| 発送 / 出荷 / shipping / 同梱 / 配送キャリア / FedEx / DHL | **ADR-103** ／ ADR-123 ／ ADR-128 | 出荷タイミング・キャリア連携・Integrator 認定 |
| 在庫 / inventory / 商品マスタ / 仕入元 / オファー | **ADR-099** ／ ADR-093 ／ ADR-014 | 在庫モデル・商品/在庫マスタ分離・Discord 収集 |
| 取り込み / 解析 / パイプライン / Discord 収集 | **ADR-100** ／ ADR-014 | 提供元メッセージ→生オファー |

## 顧客・リード・テナント

| 機能キーワード | 正準 ADR | 補足 |
|---|---|---|
| 会社 / 顧客情報 / Client Profile / contact / 担当者 | **ADR-060** ／ ADR-058 | リネーム・担当者統合 |
| リード / lead / lead_channels / 名寄せ | **ADR-015** ／ ADR-119 ／ ADR-098 | リード管理・チャネル・名寄せ |
| テナント / RLS / schema prefix / tenant_context | **ADR-072** ／ ADR-034 ／ ADR-036 | 書込後 reset_tenant_context・新規テナント migration 自動化・整合性 |
| 権限 / role / 認証 / Firebase | ADR-023 ／ ADR-032 | 認証3層同期・カスタム認証ドメイン |
| password_hash / bcrypt / 認証情報 DB 保存 | **ADR-138** | password_hash 列廃止（Firebase 専一）。列削除 recon では ORM モデル定義確認必須 |

## 横断・運用・プロセス

| 機能キーワード | 正準 ADR | 補足 |
|---|---|---|
| i18n / 国際化 / ja.json / en.json | **ADR-027** | 全 UI 文字列 `t()` 経由・キー同期必須 |
| リリース / release PR / develop→main / branch protection | **ADR-050** | merge commit のみ（squash 禁止＝back-merge 構造バグ防止）・Ruleset 15777895 |
| リリース相乗り防止 / 危険変更の develop 入口関所 / develop=出荷可能 | **ADR-135** | 危険変更(migrations/deploy.yml/scripts)は PO GO まで feature で待機・develop マージ＝本番投入可宣言。CODEOWNERS/PRテンプレ済、Ruleset B/C は PO GO 待ち |
| 自動マージ / human-in-the-loop / develop 自動 merge | **ADR-056** | develop は AI 自動 merge・main は人間。通知集約 |
| 並行開発 / worktree / AEON / Evidence | **ADR-086** | 複数エージェント並行開発の標準化 |
| 標準ワークフロー / SOP / process-artifacts gate | **ADR-121** ／ ADR-112 ／ [`docs/STANDARD-WORKFLOW.md`](../STANDARD-WORKFLOW.md) | KGI→recon→設計の関所 |
| セキュリティ / security / hardening / SEC-MASTER | **ADR-140** | Sales Anchor 全体のセキュリティKGI・10領域定義・実施順序。運用SSOTは `docs/security/SEC-MASTER.md` |
| Claude Code 運用ガードレール / SessionStart hook | **ADR-042** | 運用ガードレール・hook 整備 |
| Meta / Facebook / Instagram / Webhook | ADR-024 ／ ADR-025 ／ ADR-041 ／ ADR-026 | 連携整備・フォールバック・mid TEXT 化 |

> **使い方（recon）**: ①この表で領域の正準 ADR を引く → ②`git grep -i "<keyword>" docs/adr/` で取りこぼしを確認 → ③該当 ADR を read してから設計に入る。該当が無ければ「既存設計なし（grep 済み）」と recon.md に明記する。

## ADR 候補バックログ（未起案）

| 課題 | 概要 | 起案優先度 |
|---|---|---|
| ADD 系 migration の expand-contract 運用 | `ADD COLUMN NOT NULL` など新列追加 migration は blue-green cutover **前**に実行される（deploy.yml 構造）。旧コンテナが新列を知らない状態で列が追加されると、RLS/VIEW/trigger 依存によっては旧コンテナが壊れる可能性がある。対策候補: ①cutover 前後で migration を pre/post に分割、②ADD 系は nullable で追加して NOT NULL は後 PR で付与、③新列は ORM 側でオプショナル定義してから追加。構造保証として ADR 化する | 中 |
