# ADR-134: SA設計図書サイトの配信方式（アプリVPS静的配信＋Basic認証）

| 項目 | 内容 |
|------|------|
| ステータス | Proposed |
| 作成日 | 2026-06-12 |
| 起案 | Hikky-dev（Terminal CC） |
| PO承認 | Shingo 2026-06-12（J1〜J4・KGI G1〜G4） |
| 関連 | ADR-095〜106（SA設計シリーズ）／ADR-121（process-artifacts gate）|

## What

ADR-095〜106（SAシリーズ）の設計意図を非技術者向けに図解したHTML静的サイトを
アプリVPS（app.salesanchor.jp）で配信する。

詳細設計は `docs/handoff/design-site/design.md`（v2）、調査根拠は同 `recon.md` に収録。
本ADRはWhat/Whyのみを記録し、繰り返し内容はそちらへ委譲する。

## Why

- ADRは技術者向けで非技術者（PO・社外関係者）には読みにくい
- GitHub Pagesはプライベートリポジトリでも公開URLが誰でも閲覧可能なため不採用（Shingo 2026-06-12）
- アプリVPSの既存nginxがすでにMGMT VPSへのリバースプロキシ実績を持ち（nginx.conf:162/179）、
  同パターンで静的配信を追加するのが最小工事
- 既存deploy.ymlに包含することで、初日から完全自動更新が成立する

## 決定済み事項（J1〜J4）

| # | 決定 |
|---|------|
| J1 | APP VPS nginx で `/design/` を静的配信（`/home/ubuntu/salesanchor/www/design-site/`） |
| J2 | URL = `https://app.salesanchor.jp/design/` |
| J3 | htpasswdはVPS上 `nginx/htpasswd.d/design-site` に手動作成・git追跡禁止（B-11準拠） |
| J4 | HTMLはリポジトリに静的コミット。`progress.json` のみデプロイ時に `00-SA-OVERVIEW.md` §1から自動生成（派生値原則）。変換失敗＝デプロイ失敗 |

## Scope IN

- `docs/design-site/` 新設（HTML + CSS + JS）
- nginx `/design/` location ブロック追加（追加のみ・既存ブロック変更なし）
- docker-compose.yml nginx volumes 追加（`www/design-site` と `nginx/htpasswd.d`）
- deploy.yml 工程追加（進捗JSON変換 + 設計図書同期）
- 毎デプロイ smoke: 認証なし=401 / 認証あり=200 / progress.json存在確認 / 既存経路疎通確認

## Scope OUT

- ビルドツール・フレームワーク（素のHTML+CSSのみ）
- 新サブドメイン・新TLS証明書（既存 `app.salesanchor.jp` 証明書を流用）
- MGMT VPSへの変更（J1変更に伴い不要）
- ADR→HTML自動生成・ページ内検索・英語版（v2候補）
- PR実績のサイト内表示（v2候補）

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 認証なしアクセス＝401 が100% | smoke①（毎デプロイ自動） |
| 認証ありアクセス＝200 | smoke② |
| progress.json が有効JSON＋generated_at フィールドあり | smoke③ |
| /api/health, /grafana/api/health が200のまま | smoke④ |
| --force-recreateを含むデプロイでhtpasswd・コンテンツが消えない | デプロイ後確認 |

## リスクと対策

| リスク | 対策 |
|--------|------|
| 公開事故（認証設定漏れ） | デフォルトdeny構成 + smoke①で毎回確認 |
| パスワード平文流出 | HTTPS必須（既存TLS流用）。htpasswdはgit外管理（B-11） |
| 本番nginx変更でアプリ経路を壊す | location追加のみに限定 + smoke④で既存経路を毎回確認 |
| 進捗の陳腐化 | progress.json をデプロイ時に毎回生成。手書きコピーを持たない |
| ADRと図書の乖離 | 全ページに正本ADRリンク+「矛盾時はADR優先」を明記 |

## 関連ドキュメント

- 設計doc（v2）: `docs/handoff/design-site/design.md`
- recon: `docs/handoff/design-site/recon.md`
- 進捗正本: `docs/plans/sa-progress/00-SA-OVERVIEW.md`
- 変換スクリプト: `scripts/design-site/generate-progress-json.py`
- smoke: `scripts/smoke/design-site-smoke.sh`

---

## 事故記録

### INC-001 — migration 013 失敗→fail-closed→/design/ 自動遮断（2026-06-12）

**発生**: 2026-06-12T17:28 UTC（deploy run #27431943512）  
**影響**: `/design/` が 403 Forbidden となり、設計図書サイトに接続不可。本番アプリへの機能影響なし（health check 通過）。

**経過**:  
PR #2068（ファネルダッシュボード PR1、merged 2026-06-12T15:00 UTC）に含まれる `migrations/20260613_030000_funnel_leads_initiative_channel.sql`（`scripts/run_all_migrations.sh:387行目`）が ADR-138 §D1-3 クリーンスレート方針に基づき全テナントの `leads.source` 列を `DROP COLUMN IF EXISTS` した。  
同日 16:44 UTC のデプロイ（run #27429644941）で当該 migration が初めて本番実行され、`leads.source` が全テナントから消滅。  
続く 17:28 UTC のデプロイで `migrations/013_add_meta_webhook_idempotency.sql`（`run_all_migrations.sh:74行目`、step [2/145]）が `SELECT source FROM tenant_001.leads` を実行し `ERROR: column "source" does not exist` で終了。`set -e` により migration ステップ全体が即停止。smoke tests がスキップされ、ADR-134 §D（`Emergency block /design/ on smoke FAIL`）が htpasswd ファイルを削除・nginx を再起動、`/design/` を fail-closed（403）に遮断した。

**根本原因**: `run_all_migrations.sh` は毎デプロイ全 migration を最初から再実行するが、migration 状態テーブルを持たない。migration 013（step 2）は `leads.source` の存在を前提としていたが、後続の migration 20260613_030000（step ~100相当）が同列を DROP した結果、次のデプロイから 013 が常に失敗する構造になった。migration 順序の後ろ方向依存（early migration → column 存在前提、late migration → column 廃止）が顕在化したケース。

**修正**: PR #2084 — `migrations/013_add_meta_webhook_idempotency.sql` の C1 セクション（`source` 列依存）に `information_schema` 存在チェックを追加し、列が無い場合はスキップ（NOTICE を出力のみ）するよう変更（`migrations/013_add_meta_webhook_idempotency.sql:65-103`）。ADR-138 §D1-3 クリーンスレート方針に則り列の再追加は行わない。あわせて C2 セクション（`meta_messages` 依存）にもテーブル存在ガードを追加し、CI テスト環境での実行可否チェックも通過させた。

**自己修復の動作確認**: 次の成功デプロイで htpasswd が `Setup design-site htpasswd (idempotent)` ステップにより再生成、nginx 再起動後に `/design/` が 401 → 200 に復旧することで、fail-closed ブロックが自動解除される。
