---
mode: handoff
---
# 設計草案 — S1 段階③（会社・PayPal 設定・認証系 5 表）

> この文書は何か：段階③の方針を PO と決めるための草案です。**PO 未承認・実装不可**。ADR-1018 Decision 1 の「RLS を付けるか、付けずに代わりの守りにするかを PO と決めてから」に従い、ここでは決めていません。

**日付**: 2026-10-16　**作成**: Claude Opus（調査は Sonnet、読取のみ）
**生データ（リポジトリ外）**: `/tmp/CC報告ファイル/s1-stage3/`（db-*.txt・code-*.txt）

## 1. 現在地（2026-10-16 本番・読取のみ）

7 表とも RLS 無効・ポリシー 0（`/tmp/CC報告ファイル/s1-stage3/db-rls-flags.txt`、`/tmp/CC報告ファイル/s1-stage3/db-policies.txt`）。所有者 jarvis、salesanchor_app に読み書き権限あり（`/tmp/CC報告ファイル/s1-stage3/db-owners-grants.txt`）。

| 表 | 本番行数 | 会社との結び付き | 認証前（会社未確定）の読取 | 書込 | 既存の守り |
|---|---|---|---|---|---|
| tenants | 5 | 表そのもの | get_current_tenant 内 dependencies.py:296（文脈を張る前） | admin.py:57、super_admin_tenants.py:66/:167 | なし。Celery が全社を横断して読む（tasks/avatar.py:101 ほか約 8 ファイル） |
| tenant_paypal_config | 1 | tenant_id 列 | PayPal Webhook integrations.py:914/:983（署名で会社を特定する設計で全社横断） | paypal_payments.py:94/:119/:430（会社確定後） | 鍵は Fernet 暗号化 |
| users | 15 | tenant_id 列 | ログイン・トークン更新・パスワード再設定 auth.py:251/:328/:385/:445、dependencies.py:102/:160/:201/:246、self_tokens.py:224 | auth.py・staff.py（8 か所） | パスワードは argon2 ハッシュ |
| auth_refresh_tokens | 0 | user_id 経由 | self_tokens.py:207 | self_tokens.py 4 か所、auth.py:463 | token はハッシュで保存 |
| password_reset_tokens | 0 | user_id 経由 | なし（UPDATE…RETURNING のみ） | auth.py:393/:401/:432 | token はハッシュ |
| webauthn_credentials | 0 | user_id 経由 | なし（読み書きコード 0） | なし | 公開鍵のみ |
| registration_tokens | 5（全行 tenant 4） | tenant_id 列 | registration_token.py:125（招待リンクを開いた時点・文脈前） | registration_token.py:77/:157 | token は HMAC ハッシュ |

【事実】7 表のうち 6 表は「会社が決まる前に引く」か「全社を横断して引く」経路を持つ。会社別 RLS をそのまま付けると、ログイン・招待・PayPal 入金通知・Celery の全社処理が 0 行になって止まる。
【未確認】Celery 各タスクの文脈付与の有無（tasks/*.py の一部未読）。

## 2. 選択肢（表ごとに選ぶ）

| 案 | 中身 | 効く範囲 | 代償 |
|---|---|---|---|
| A. 付けない＋代わりの守り | RLS は付けず、試験（他社行を返さない）とコード審査で守る。トークン類はハッシュ保存を維持 | 現状維持 | DB 自身の拒否はない |
| B. 「認証用の窓口」を作って RLS | ログイン等の認証前処理だけが使う専用の DB 関数（SECURITY DEFINER）か専用の文脈（例 app.auth_phase）を通し、それ以外は会社別 RLS | 認証前の経路以外で他社行が出ない | 改修が大きい（users だけで 17 か所）。ログイン停止の危険が最も高い |
| C. 書込だけ RLS | 読取は全行可、書込は自社 or 運営文脈のみ（段階①・②b と同じ型） | 他社行の書き換え・削除を DB が拒否 | 読取の漏れは防げない |

【事実】0 行の表（auth_refresh_tokens・password_reset_tokens・webauthn_credentials）は今は守る中身がない。行が入り始めるのはログイン自社化（ADR-1013）の本格利用後。

## 3. Opus の推奨（PO 未承認）

- tenant_paypal_config・registration_tokens：C（書込だけ RLS）を先に。読取経路は 2〜3 か所で、書込は全部会社確定後のため改修が小さい。
- users・tenants：C を次に。ただし Celery の全社処理と super admin 画面の書込に運営文脈を張る改修が要る（件数は未確認、追加調査が必要）。
- 認証トークン 3 表：A（ハッシュ保存と試験で守り、RLS は付けない）。0 行で、認証前に引く経路しかないため。

## 4. PO に決めてほしいこと（1 回に 1 問ずつ聞く）

1. 段階③は「読取の漏れ」まで DB で止めますか（案 B・大改修）、それとも「書き換え・削除」だけ DB で止めますか（案 C）。
2. 認証トークン 3 表は RLS を付けない（案 A）でよいですか。
3. 着手順は PayPal 設定・招待リンク → 利用者・会社 の順でよいですか。

## 5. 外部・過去事例の参照と我々への応用

- PostgreSQL 公式 docs/16/ddl-rowsecurity: ポリシーに合わない行は読取 0 行・書込拒否になる。→ 認証前に引く表へ会社別ポリシーを付けると、ログインが「該当なし」で止まる（案 B の危険の根拠）。
- 社内前例: 段階①（permissions）・段階②b（suppliers）は「読取は広く、書込は運営文脈のみ」の型（案 C）で本番反映済み、反映後の拒否エラー 0 件（PR #4332・#4349 の本番確認コメント）。
- 数値の外部事例は、方針を PO と決める前の草案では成否を左右しないため用いない。

## 6. 次の一手

PO が 1 に答えたら、選んだ案で表ごとの recon（Celery 全タスクを含む）→ 設計 → 審査 → 実装カード。

## 維持の仕組み

- 方針決定前のため新設なし。決定後の設計で、表ごとの RLS 試験（CI の pytest）を守り手として定める。
- 状態は docs/specs/tenant-rls/README.md の段階③欄で管理する。
