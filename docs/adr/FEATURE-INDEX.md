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
| 共用商品の登録 / 必須項目 / 調べたが無い / product_blank_confirmations / 細分類 | **ADR-1020** ／ ADR-155 ／ ADR-156 | 9項目必須・4項目は印で空を認める・全入口で check_required_fields。値の決め方は docs/specs/product-master/registration-rules.md |
| 取り込み / 解析 / パイプライン / Discord 収集 | **ADR-100** ／ ADR-014 ／ ADR-1050 | 提供元メッセージ→生オファー。一時的に断られた解析の送り直しと、諦めた分の知らせ・月曜の数の知らせは ADR-1050 |
| まとめ売り / N枚セット / bundle_size / バルク / bulk_price_basis_unknown / bundle_unverified | **ADR-1027** ／ ADR-1021 ／ [`docs/specs/bundle-sale/README.md`](../specs/bundle-sale/README.md) | 値段を割らずまとめの数を保存・商品名の欄に「N単位セット」。バルク系だけ形 P1・P2 を足す（2026-10-21 追記）。新しい書き方の手順は [`docs/runbooks/bundle-sale-new-wording.md`](../runbooks/bundle-sale-new-wording.md) |
| 社外秘の原文 / 書き写し / confidential-quote-guard / 送る前の見張り | **ADR-1045** ／ ADR-1043 ／ ADR-1029 | 仕入元の投稿の原文を「」『』で書き写したまま push・PR 本文・コメントで公開の置き場へ送るのを Mac の PreToolUse で止める。表は社外秘フォルダ |

## 顧客・リード・テナント

| 機能キーワード | 正準 ADR | 補足 |
|---|---|---|
| 会社 / 顧客情報 / Client Profile / contact / 担当者 | **ADR-060** ／ ADR-058 | リネーム・担当者統合 |
| リード / lead / lead_channels / 名寄せ | **ADR-015** ／ ADR-119 ／ ADR-098 | リード管理・チャネル・名寄せ |
| テナント / RLS / schema prefix / tenant_context | **ADR-072** ／ ADR-034 ／ ADR-036 | 書込後 reset_tenant_context・新規テナント migration 自動化・整合性 |
| 権限 / role / 認証 / Firebase | ADR-023 ／ ADR-032 | 認証3層同期・カスタム認証ドメイン |
| password_hash / bcrypt / 認証情報 DB 保存 | **ADR-138** | password_hash 列廃止（Firebase 専一）。列削除 recon では ORM モデル定義確認必須 |
| ログイン / パスキー / WebAuthn / 生体認証 / パスワード再設定 / 自社認証 | **ADR-1013** | Firebase から自社サーバーへ移行・Argon2id・パスキー・再設定メール。ADR-138 を覆す |
| 管理者の2段階の確認 / 二段階認証 / MFA / TOTP / 認証アプリ / 新しい機器の承認 | **ADR-1048** | 管理者はパスキーかパスワード＋6桁が必須・初めての機器はいつもの機器で番号を選んで承認 |

## 横断・運用・プロセス

| 機能キーワード | 正準 ADR | 補足 |
|---|---|---|
| i18n / 国際化 / ja.json / en.json | **ADR-027** | 全 UI 文字列 `t()` 経由・キー同期必須 |
| リリース / release PR / develop→main / branch protection | **ADR-050** | merge commit のみ（squash 禁止＝back-merge 構造バグ防止）・Ruleset 15777895 |
| リリース相乗り防止 / 危険変更の develop 入口関所 / develop=出荷可能 | **ADR-135** | 危険変更(migrations/deploy.yml/scripts)は PO GO まで feature で待機・develop マージ＝本番投入可宣言。CODEOWNERS/PRテンプレ済、B（B-2 方式）・C（main 必須チェック追加）・D・E も実施済み（ADR-135:32-60） |
| 自動マージ / human-in-the-loop / develop 自動 merge | **ADR-056** | develop は AI 自動 merge・main は人間。通知集約 |
| 並行開発 / worktree / AEON / Evidence | **ADR-086** | 複数エージェント並行開発の標準化 |
| 標準ワークフロー / SOP / process-artifacts gate | **ADR-121** ／ ADR-112 ／ [`docs/STANDARD-WORKFLOW.md`](../STANDARD-WORKFLOW.md) | KGI→recon→設計の関所 |
| 設計仕様書 / あるべき姿 / 仕様書索引 | **ADR-121** ／ [`docs/specs/README.md`](../specs/README.md) | 領域→設計仕様書の地図。索引に載る領域に触れる開発は仕様書を先に読む |
| Claude Code 運用ガードレール / SessionStart hook | **ADR-042** | 運用ガードレール・hook 整備 |
| CLAUDE.md / AGENTS.md / 入口の行数 / 目次 / 指示文書の構成 | **ADR-1040**（Accepted） ／ ADR-076 | 入口→目次→章→末端。本文の正本は AGENTS.md・入口の上限90行（ADR-076 のルート上限と命名を一部改訂） |
| 担当者アイコン / 英語名必須 / Discord webhook 送信 / avatar | **ADR-159** ／ ADR-091 | Discord 返信を担当者の名（given_name_en）とアイコンで送る・Bot 名義では送らない（便A=アイコン+英語名必須 / 便B=webhook 送信） |
| 24時間保守運用 / 障害記録 / 応急処置 / routines / アラート札 page・auto・ticket | **ADR-1012**（Proposed） ／ ADR-1009 ／ ADR-115 | 経路の正本は Alertmanager・障害記録の正本はアプリ DB・AI は PR で修理（ADR-136 の GO）・C は予備 |
| Meta / Facebook / Instagram / Webhook | ADR-024 ／ ADR-025 ／ ADR-041 ／ ADR-026 | 連携整備・フォールバック・mid TEXT 化 |

## インフラ / デプロイ / nginx

| 機能キーワード | 正準 ADR | 補足 |
|---|---|---|
| nginx / inode / bind mount / force-recreate / deploy / git reset | **ADR-137** | git reset 後の inode ズレ対策。nginx/** 変更時のみ conditional force-recreate（git reset 後・bootstrap 前） |
| 502 / resolver / backend IP / proxy_pass | **ADR-137** ／ ADR-133 | PR-B 相当は ADR-133 で実装済み。ADR-137 では解消済みとして統合記録 |

> **使い方（recon）**: ①この表で領域の正準 ADR を引く → ②`git grep -i "<keyword>" docs/adr/` で取りこぼしを確認 → ③該当 ADR を read してから設計に入る。該当が無ければ「既存設計なし（grep 済み）」と recon.md に明記する。

## ADR 候補バックログ（未起案）

| 課題 | 概要 | 起案優先度 |
|---|---|---|
| ADD 系 migration の expand-contract 運用 | `ADD COLUMN NOT NULL` など新列追加 migration は blue-green cutover **前**に実行される（deploy.yml 構造）。旧コンテナが新列を知らない状態で列が追加されると、RLS/VIEW/trigger 依存によっては旧コンテナが壊れる可能性がある。対策候補: ①cutover 前後で migration を pre/post に分割、②ADD 系は nullable で追加して NOT NULL は後 PR で付与、③新列は ORM 側でオプショナル定義してから追加。構造保証として ADR 化する | 中 |
