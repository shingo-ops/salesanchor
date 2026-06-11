# recon — deploy-timeout-fix

**仕事名**: deploy-timeout-fix  
**日付**: 2026-06-12  
**対象ADR**: ADR-115  
**担当**: Morimoto

---

## 背景

連続2回のデプロイ（PR #1966 CSS修正・PR #1969 PayPal webhook）が「Finalize (health check + cleanup)」で失敗し、自動ロールバックが発動した。
ロールバック後も API は 200 を返しており、本番ダウンは実質的に発生していなかった。

調査の結果、**backend 実際の起動時間（~120s）とロールバック health check の待機上限（60s）の不一致** が根本原因と判明した。

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `.github/workflows/deploy.yml:456` | Step 6 ヘルスチェック開始点（auto-rollback 付き） |
| `.github/workflows/deploy.yml:462` | 修正後: 36×5s=180s のリトライループ（修正前は単発1回のみ） |
| `.github/workflows/deploy.yml:511` | rollback stabilize メッセージ（修正後 "max 180s"） |
| `.github/workflows/deploy.yml:512` | rollback health check リトライ（修正後: seq 1 36 = 180s） |
| `docs/adr/ADR-115-deploy-safety.md:23` | 旧仕様: 「復旧健全性を再確認（最大 60s ポーリング）」← この値が起動時間と不一致だった根本 |

---

## 問題の仕組み（調査結果）

### 実測起動時間

VPS ログで確認した起動タイムライン（障害発生時の実測値）:

- `docker compose up -d` 完了後コンテナ作成: `08:13:15 UTC`
- FastAPI startup complete ログ出力: `08:15:xx UTC`
- **実測: 約 120s**（Python 依存パッケージ import + SQLAlchemy 初期化 + Celery worker 起動）

### なぜ Step 6 が誤判定していたか

修正前の Step 6 (`.github/workflows/deploy.yml:462` の前身) は**単発1回のチェック**だった。
ロールバック health check (`.github/workflows/deploy.yml:512` の前身) は `seq 1 12` × 5s = **60s** で待機していたが、
backend の実際の起動時間は **120s** のため、60s 到達時点でまだ起動中 → health check 失敗 → `_rollback_result="failed"` のまま exit 1。

ADR-115 (`.github/workflows/deploy.yml:511` の設計元) は 60s を仕様として定めていたが、
実環境の起動時間とのギャップが調査まで可視化されていなかった。

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | backend 起動が毎回 120s かかるか（一過性か恒常か） | VPS ログ 2回の失敗デプロイで同じ ~120s を確認 | ✅ 解消済み |
| 2 | ロールバック後に DB と code が不整合にならないか | 全マイグレーションが `ADD COLUMN IF NOT EXISTS` の追加型・冪等性を保証 | ✅ 解消済み |
| 3 | Step 4 の `timeout 120` が存在するか（develop vs main の差異） | develop ブランチは blue-green cutover 採用済みで Step 4 は廃止 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
