# ADR-115: デプロイ安全策（自動ロールバック・環境差バグ対策）

## ステータス
採用

## コンテキスト

SA-18 Phase2 デプロイで本番が 503 で放置された（2026-06-06）。原因は2つ重なった環境差バグ：
1. `asyncpg` の `connect_args` に `application_name` を直接渡すと TypeError（CI では localhost で postgres を動かすため素通り）
2. bootstrap ステップが `DATABASE_URL` を `salesanchor_app@localhost:5432` に書き換えたが、コンテナ内から `localhost:5432` は不到達（CI では localhost でも通る）

いずれも **「CI は通るが本番の Docker ネットワーク構成で初めて出る」クラスのバグ**で、単体テストや結合テストでは構造的に検出できない。デプロイ後の smoke テストが唯一の網だったが、その smoke も「アプリが接続できない場合に偽陽性 PASS する」設計だったため検出が遅れた。

## 決定

### ① ヘルスチェック失敗時の自動ロールバック（実装済み）

`deploy.yml` Finalize ステップのヘルスチェックが失敗した場合、自動的に直前の動く版（`PREV_SHA`）へ戻す。

**仕組み**:
- `git pull` 前に `PREV_SHA=$(git rev-parse HEAD)` を `.deploy_prev_sha` に保存
- health `/api/health` 失敗 → `git reset --hard $PREV_SHA` → `docker compose build` → `docker compose up -d`
- 復旧健全性を再確認（最大 60s ポーリング）
- 結果（成功 or 失敗）を Discord 通知
- deploy job は常に非0 exit（本番が UP でも問題を可視化）

**不変条件**: マイグレーションは後方互換（追加型・冪等）を保つ。これにより「コードだけ戻す」ロールバックが常に安全になる。破壊的マイグレーション（カラム削除・型変更）は原則禁止とし、削除は deprecated 化 → 古いコードが消えた後に別 PR で実施する。

### ② 本番相当 docker-compose での事前素振り（手動、再挑戦系デプロイ直前）

CI は postgres を localhost で動かすため、コンテナ間通信や接続構成バグを構造的に検出できない。Phase2 のような「接続先切替」「ロール変更」を伴うデプロイを再挑戦する際は、本番相当の docker-compose 環境で事前に動作確認（素振り）を行う。

自動化は将来課題。手動実施のタイミング：本番相当の接続構成変更を伴う PR のマージ直前。

### ③ 専用ステージング環境（保留）

コストと運用負荷を考慮し、事業規模が拡大したタイミングで検討する。現時点では ② の手動素振りで代替する。

## 背景・根拠

- smoke[7] を「アプリが salesanchor_app として実接続しているか」の陽性確認込みに強化済み（PR #1704）
- 自動ロールバックにより Phase2 再挑戦は「失敗しても自動で戻る」安全網の上で実施できる
- ADR-082（デプロイ並行性制御）・ADR-092（コンカレンシー）と連携する

## 参照

- SA-18 Phase2 事故: PR #1696, deploy run #27040643295
- 緊急修正: PR #1704, #1705
- smoke[7] 強化: scripts/smoke_test_post_deploy.sh
