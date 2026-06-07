# ADR-116: 本番デプロイの自動ロールバック＋失敗理由の保全

| 項目 | 内容 |
|------|------|
| ステータス | Proposed |
| 作成日 | 2026-06-07 |
| 起案 | しんごさん（PO） |
| 関連 | ADR-115（デプロイ安全策 2026-06-06 事故記録）/ ADR-092（deploy 直列化）/ ADR-082（front-only skip）|

---

## ひとことで

本番デプロイを「**安全に失敗する**」形にする。デプロイ後の健康診断が NG なら、**失敗理由を保全してから**前の動く版へ自動で戻す。

---

## Context（なぜ・現状の穴）

- 現状 `deploy.yml` は、健康診断がタイムアウトしても **ログ一行で先に進む**（L202: `|| echo "timed out, proceeding"`）。
- デプロイ失敗時の **通知がない**（システム監査でも最優先課題）。失敗理由（backend ログ・DB 接続状況）を残す仕組みもない。
- 結果：2026-06-06 の SA-18 Phase2 デプロイ（`localhost` 誤指定＋`application_name` 誤りの二重バグ）で **本番 503 が継続し、手動で `jarvis` へ巻き戻す**ことになった（詳細: ADR-115）。
- この状態で切替を再挑戦すると、同じ「落ちたまま・理由も曖昧」を繰り返す。

---

## Decision（What）

デプロイの最後に **決定的な健康ゲート** を置き、NG 時は「保全 → 自動復帰 → 復旧確認」を機械的に行う。

### 1. 健康ゲート（待って先に進む、をやめる）

- Finalize ステップの `/api/health` チェック（現在 L254）を決定的に扱う。
  - **成功 → last-good SHA を記録して正常終了**
  - **失敗 → 保全 → ロールバック → 復旧確認 → 非 0 exit**（現在の "exit 1 のみ" を置き換え）
- Step 4 の container healthcheck timeout（L202）は「ロールバックの引き金」にせず、migration の先行条件として残す（コンテナが起動前なら migration 実行も止まる）。

### 2. 失敗理由の保全（復帰の前・非交渉）

コンテナ再生成で消える前に、**消えない場所**（VPS 上ファイル + Discord 通知）へ記録する。

保全内容:
- backend ログ（直近 200 行）
- `/api/health` の HTTP ステータス + 本文
- `docker compose ps` 出力
- **DB 接続診断**: `pg_stat_activity` でアプリ backend が「どの宛先・どのロール（`usename`）・どの `application_name`」で繋いだか（前回の二重バグがそのまま映る診断）
- 対象コミット（bad SHA）と直前の良版（good SHA）

保存先:
- VPS ファイル: `/home/ubuntu/salesanchor/deploy-failures/<timestamp>-<short-sha>.log`
- Discord: `ADMIN_NOTIFICATION_DISCORD_WEBHOOK`（`.env` に sync 済み）へ要約と保存先を inline curl で通知。`discord-owner-ping.sh` は `DISCORD_WEBHOOK_OWNER_PING` を要求するため、deploy ステップ内では inline curl を使用する（変数名不一致を避けるため）。

### 3. 自動復帰（前の動く版へ）

**準備（Deploy ステップ冒頭・`.env` 更新前）:**
- `PREV_SHA=$(git rev-parse HEAD)` を `.deploy_prev_sha` に保存
- `.env` のバックアップを `.deploy_prev_env` に保存（`cp .env .deploy_prev_env`）

**復帰手順（Finalize ステップ・健康ゲート失敗時）:**
1. `.deploy_prev_sha` から `PREV_SHA` を読み出す
2. `PREV_SHA` が空 / ファイルなし → "初回デプロイのためロールバック先不明" をログ + Discord 通知 → exit 1（ロールバックなし）
3. `git reset --hard $PREV_SHA`
4. `.deploy_prev_env` が存在すれば `cp .deploy_prev_env .env`（`.env` を元に戻す）
5. `docker compose build`（build-from-source 構成のため再ビルド必須）
6. `docker compose up -d`
7. 健康ゲートを再実行（最大 60s ポーリング）
8. 復旧成功 → "ROLLBACK 成功" を Discord 通知 → exit 1（本番に問題があったことは可視化）
9. 復旧失敗 → "ROLLBACK も失敗・要即時対応" を Discord 通知 → exit 1

### 4. 「良版」の記録

- 健康ゲートを通過したデプロイの SHA を VPS 上の `.deploy_last_good_sha` に記録。
- 次回のロールバック先はこのファイルから読む（`PREV_SHA` ではなく `LAST_GOOD_SHA` を優先）。
- 初回デプロイ（ファイルなし）: ロールバック不可。障害時は手動対応必須と明示。

---

## Scope

- 対象: `deploy.yml` の健康ゲート・失敗時保全・自動復帰・last-good 記録。**全デプロイに効く一般の安全網**（SA-18 Phase2 はその最初の利用者）。
- 対象外: デプロイ前 DB バックアップ（migration は冪等・additive のため別件）、専用ステージング（コスト見合いで保留）。

---

## 前回の二重バグとの対応（この安全網で何が変わるか）

| 前回の問題 | 今後 |
|------------|------|
| `localhost` 誤指定で接続できず 503 | 健康ゲートが落ちる → 自動復帰。DB 接続診断に「接続先・接続不可」が残る |
| `application_name` 誤りで app/admin 識別不能 | 診断で `application_name`/`usename` を記録 → 誰で繋いだか即判明 |
| 503 が継続（手動復旧） | good SHA へ自動復帰し、復旧を再確認 |

---

## architect recon 結果（2026-06-07 確認済み）

| # | 項目 | 確認 |
|---|------|------|
| 1 | 健康待ち箇所 | L196-202（Step4 container healthcheck → timeout で続行）+ L254（Finalize `/api/health` → exit 1 のみ）。挿入位置: L254 の `exit 1` 前に保全 + ロールバック処理を追加 |
| 2 | 復帰手段 | build-from-source 確定。`.env` は deploy step L127-160 で上書きされるため、L127 前に `.deploy_prev_env` バックアップが必須。`git reset --hard` + `docker compose build/up` の順が安全 |
| 3 | last-good SHA | 未実装 → `.deploy_last_good_sha` に実装。初回（ファイルなし）はロールバック不可・明示失敗 |
| 4 | Discord webhook | `discord-owner-ping.sh` は `DISCORD_WEBHOOK_OWNER_PING` を要求するが `.env` sync 変数名は `ADMIN_NOTIFICATION_DISCORD_WEBHOOK`。deploy ステップ内では inline curl を使用 |
| 5 | migration 安全性 | additive/冪等確認済み。Phase2 は config/code のみ。コードだけ戻す rollback は安全 ✅ |

---

## トリガー

本 ADR は What/Why + 設計契約の決定ログ。実装は Generator ハンドオフ（Terminal CC）で起動。

## 参照

- SA-18 Phase2 事故: ADR-115、PR #1696, deploy run #27040643295
- 緊急修正: PR #1704, #1705
- `discord-owner-ping.sh`: `scripts/notify/discord-owner-ping.sh`（`DISCORD_WEBHOOK_OWNER_PING` 要求 → deploy では inline curl を代用）
