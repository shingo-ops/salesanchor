# recon — tcg-diagnostics-readonly（TCG診断API・固定クエリ方式）

**仕事名**: GET /api/v1/tcg/diagnostics/{key} — 読み取り専用固定SQL診断エンドポイント  
**日付**: 2026-09-04  
**対象ADR**: ADR-154  
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `docs/handoff/rehearsal-env/design-b-ssh-isolation.md:58` | ForceCommand 許可コマンド: docker stats --no-stream; free -h; df -h; uptime（任意コマンド実行不可） |
| `docker-compose.yml:343` | postgres サービス定義（ports: なし → 外部からポートアクセス不可） |
| `backend/app/routers/tcg_diagnostics.py:40` | @router.get エンドポイント定義 |
| `backend/app/routers/tcg_diagnostics.py:48` | require_super_admin 認可ガード |
| `backend/app/routers/tcg_diagnostics.py:51` | 許可リスト完全一致チェック（key not in allowed → 400） |
| `backend/app/services/tcg_diagnostics_svc.py:13` | TCG_SCHEMA = "tenant_004"（スキーマ固定） |
| `backend/app/services/tcg_diagnostics_svc.py:19` | _ALLOWED_KEYS frozenset（4キーのみ受理） |
| `backend/app/services/tcg_diagnostics_svc.py:32` | _QUERIES dict（固定SQL4件） |
| `backend/app/services/tcg_diagnostics_svc.py:65` | run_diagnostic — _QUERIES[key] ルックアップのみ（動的SQL生成なし） |
| `backend/tests/test_tcg_diagnostics.py:72` | test_diagnostics_requires_auth（認証なし → 401/403） |
| `backend/app/main.py:582` | tcg_diagnostics.router の include_router 登録 |
| `backend/app/routers/tcg_supplier_quality.py:64` | 既存の TCG 系 super_admin API（診断クエリ機能なし） |

---

## DB-A1 調査内容（本番DB接続経路の実測）

### 1. SSH ForceCommand 制限

`docs/handoff/rehearsal-env/design-b-ssh-isolation.md:58` に明記:

> ForceCommand 許可コマンド: docker stats --no-stream; free -h; df -h; uptime（監視のみ）

`salesanchor-claude` 鍵で SSH 接続した場合、引数に関わらず上記コマンドの出力のみが返る。任意の psql / pg_dump 等は実行不可。

### 2. postgres の外部非公開

`docker-compose.yml:343` の postgres サービス定義に `ports:` キーが存在しない。外部ホストからポート 5432 へのアクセス経路なし。Docker network 内の backend コンテナからのみアクセス可能。

### 3. SELECT専用ロールの未定義

backend/init.sql・backend/migrations/ を確認。`CREATE ROLE` / `GRANT SELECT` の記述なし。SELECT専用の postgres ロールは定義されていない。

### 4. 既存の読み取り管理API（診断クエリ機能なし）

`backend/app/routers/tcg_supplier_quality.py:64` — TCG 品質サマリー API（tenant_004 対象）が存在するが、tcg_suppliers 等のマスタデータを一覧表示する診断目的の汎用 API は存在しなかった。

`backend/app/routers/super_admin_tcg.py` — public.tcg_series_master の CRUD のみ。tenant_004 スキーマへの直接参照なし。

### 5. 実装方針の決定（DB-A1 → DB-A2）

上記4点から:
- SSH 経由の直接 DB 接続は不可
- psycopg2 / sqlalchemy を使った直接ポート接続も外部非公開のため不可
- SELECT専用ロールの作成には migration が必要
- **→ 既存バックエンド API に新エンドポイントを追加する方式を採用**

---

## DB-A2 実装内容

### 6. 固定クエリ方式の実装

`backend/app/services/tcg_diagnostics_svc.py:19`:
- 許可キー4件を frozenset で定義。key は完全一致のみ受理
- `backend/app/services/tcg_diagnostics_svc.py:32` の _QUERIES dict に固定SQLを格納
- `backend/app/services/tcg_diagnostics_svc.py:65` の run_diagnostic は `_QUERIES[key]` でルックアップするのみ。外部入力からSQLを組み立てない

### 7. 認可ガード

`backend/app/routers/tcg_diagnostics.py:48` — require_super_admin が全リクエストをガード。is_super_admin=true のユーザーのみ到達可能。

### 8. テスト 6件

`backend/tests/test_tcg_diagnostics.py:72` に以下をカバー:
- 認証なし → 401/403
- 未知キー → 400（許可キー一覧をエラーメッセージに含む）
- 4キーそれぞれ → 200 + 形状検証（code/name/is_active 等のフィールド確認）

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | SSH で任意コマンドが実行できるか | design-b-ssh-isolation.md:58 を確認 | ✅ 解消済み（ForceCommand制限） |
| 2 | postgres に外部からポートアクセスできるか | docker-compose.yml:343 を確認（ports:なし） | ✅ 解消済み |
| 3 | SELECT専用ロールが存在するか | init.sql・migrations を確認（存在しない） | ✅ 解消済み |
| 4 | tenant_004 スキーマへの既存診断APIがあるか | routers/ を全走査（存在しない） | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
