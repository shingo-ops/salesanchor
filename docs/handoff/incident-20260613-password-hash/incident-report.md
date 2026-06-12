# インシデント報告: 本番 password_hash 列削除による 500 エラー

**発生日時**: 2026-06-12 15:13:44 UTC（JST 2026-06-13 00:13）  
**復旧日時**: 2026-06-12 15:19:04 UTC（JST 2026-06-13 00:19）  
**継続時間**: 約 5 分 20 秒  
**作成者**: Hikky-dev  
**確認者**: Shingo

---

## 1. 時系列

| 時刻 (UTC) | JST | 事象 |
|---|---|---|
| 〜15:13 | 〜00:13 | Hikky-dev が「素振り確認」目的で SSH 経由で本番 DB に `ALTER TABLE public.users DROP COLUMN IF EXISTS password_hash` を手動実行 |
| **15:13:44** | **00:13** | `astro-webapp-backend-1` が `UndefinedColumnError: column users.password_hash does not exist` を起点に全認証エンドポイントで 500 を返し始める |
| 15:13〜15:18 | 00:13〜00:18 | `/api/v1/conversations/stream` `/api/v1/leads` `/api/v1/companies` が 500 継続（SQLAlchemy が旧モデル定義経由で `password_hash` を SELECT に含めていたため） |
| **15:18:47** | **00:18** | Hikky-dev が worktree（PR #2067）から 4 ファイルを `docker cp` して `docker restart` |
| **15:19:04** | **00:19** | 新コードで起動完了・500 解消 |
| 16:29:16 | 01:29 | PR #2070（develop→main）が CI デプロイを起動 |
| 16:33〜16:34 | 01:33〜01:34 | blue-green cutover 完了・`run_all_migrations.sh` 実行 |
| 16:34:11 | 01:34 | migration `20260612_150000_drop_password_hash.sql` 実行 → `NOTICE: column "password_hash" of relation "users" does not exist, skipping`（no-op 確認） |
| 16:34〜 | 01:34〜 | 本番コンテナが main 由来の正規ビルドに置換。暫定 `docker cp` ファイルが解消 |

---

## 2. 原因

### 直接原因

**本番 DB に migration を CI/CD を経由せず SSH で手動実行した**（VPS 直作業禁止ルール違反）。

具体的には、PR #2067（password_hash 廃止）の「素振り確認」として、Hikky-dev が本セッション内で以下を実行した:

```bash
ssh ubuntu@49.212.137.46 "docker exec astro-webapp-postgres-1 psql -U jarvis -d jarvis_db \
  -c 'ALTER TABLE public.users DROP COLUMN IF EXISTS password_hash;'"
```

この時点で本番バックエンドコンテナは旧コード（PR #2067 未デプロイ）が動いており、  
SQLAlchemy の ORM モデル（`models.py`）に `password_hash = Column(...)` が残っていたため、  
全ユーザー認証クエリが `SELECT ... password_hash ...` を生成し続け、列削除直後から 500 が発生した。

### 誘因（設計ミス）

PR #2067 の `design.md`「デプロイ順序」セクションに**誤記**があった:

> ❌（誤）migration 先行実行 → 新コード デプロイ  
> ✅（正）blue-green cutover（新コード先行）→ run_all_migrations.sh（deploy.yml:321-423）

この誤記を素振り手順と混同し、「migration を先に適用する」と判断した。  
（誤記は本インシデント後に修正済み: commit `a098e4d5`）

### 見落とし

「書き込みコードを削除した」だけでは不十分で、**ORM モデル定義が残っている限り全 SELECT クエリに `password_hash` が含まれる**という点を recon 段階で見落とした。  
（recon.md に学びとして追記済み）

---

## 3. 暫定処置（hot-deploy）

以下 4 ファイルを PR #2067 worktree から `scp` → `docker cp` で本番コンテナに直接注入し、`docker restart` で 500 を解消した:

```
/app/app/models.py
/app/app/auth/utils.py
/app/app/routers/auth.py
/app/app/schemas/auth.py
```

この状態は「main 未マージのコードが本番で動いている」異常状態であった。  
PR #2070 の CI デプロイ（16:34 UTC）により正規ビルドに置換され、暫定ファイルは解消。

---

## 4. 恒久対策（別途設計）

本インシデントの恒久対策は以下の 2 点。ADR 化・実装タスクは別 PR で行う。

### (A) 本番 VPS 直作業禁止の技術的強制

「手順書で禁止」では再発防止にならない。  
候補: VPS の `~/.bashrc` または `pre-exec` hook で `psql` + 本番 DB への直接接続を検知・警告する仕組み。  
または Claude Code Bash hook で `ssh ubuntu@49.212.137.46 ... psql` パターンを検出してブロック。

### (B) 「素振り」は本番相当環境（staging）で実施する

現状 staging が存在しないため、「本番」しか使えない。  
候補: Docker Compose で local に `staging` profile を定義し、migration の dry-run が local で完結する環境を用意する。  
または migration は CI の dry-run（`--dry-run` オプション相当）で検証し、本番への直打ちは一切行わない運用に統一する。

---

## 確認済み事項（復旧後）

| 項目 | 結果 |
|---|---|
| 本番コンテナの MD5 が main 由来と一致 | ✅（`models.py` f370afca 等、全 4 ファイル一致） |
| `password_hash` 列が存在しない（全スキーマ） | ✅（information_schema → 0 rows） |
| `GET /api/v1/leads` | ✅ 200 count=20 |
| `GET /api/v1/companies` | ✅ 200 count=11 |
| migration no-op ログ | ✅ `NOTICE: column "password_hash" does not exist, skipping` |
| Firebase ログイン（review@salesanchor.jp） | ✅ ID token 取得・認証通過 |
