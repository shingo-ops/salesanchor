# Recon: 素振り環境の構造化（再発防止）

**調査日**: 2026-06-13  
**調査者**: Hikky-dev  
**目的**: 2026-06-12 本番 500 インシデント（password_hash 列削除）の再発防止のため、「素振りを本番で実行してしまう」構造的原因と対策案を調査・整理する。  
**スコープ**: 調査のみ。コード・設定変更なし。

---

## 1. 現状の素振り環境インベントリ

### docker-compose ファイル一覧

| ファイル | 最終更新 | 用途 | 本番相当か |
|---|---|---|---|
| `docker-compose.yml` | 2026-06-12 | 本番スタック（VPS 上で稼働） | **本番そのもの** |
| `docker-compose.test.yml` | 2026-05-24 | `postgres-test` サービスのみ（CI 用） | CI 専用・バックエンドなし |
| `docker-compose.monitoring.yml` | - | 監視スタック（Grafana / Prometheus） | 監視専用 |
| `docker-compose.exporters.yml` | - | Prometheus Exporter 群 | 監視専用 |

**結論**: 本番相当の docker-compose でバックエンド+DB を同時起動するローカル素振り環境は**存在しない**。

### 既存の素振りスクリプト

`backend/scripts/rehearsal_phase2.sh`（394行、SA-18 Phase2 専用）:
- `/tmp/phase2-rehearsal-XXXXXX` に一時ディレクトリを作成
- 接続対象: **本番コンテナ**（`astro-webapp-postgres-1`, `astro-webapp-backend-1`）
- 用途: SA-18 Phase2 のデプロイ直前確認専用スクリプト
- 汎用性: なし（特定 PR 専用）

### ADR 上のステータス

**ADR-115** `docs/adr/ADR-115-deploy-safety.md:29-37`:
```
② 本番相当 docker-compose での事前素振り（手動、再挑戦系デプロイ直前）
③ 専用ステージング環境（保留）
  コストと運用負荷を考慮し、事業規模が拡大したタイミングで検討する。
  現時点では ② の手動素振りで代替する。
```
- 専用ステージング環境は **「保留」** — コスト・運用負荷が理由
- ADR-115 は「本番相当 docker-compose での手動素振り」を定義しているが、その「本番相当環境」の具体的な compose ファイルは未作成

---

## 2. 本番 SSH アクセスパス（事実確認）

### ローカル SSH 鍵一覧（`~/.ssh/`）

| 鍵ファイル | コメント | ubuntu へのアクセス | 制限 |
|---|---|---|---|
| `id_ed25519` | `hitoshi@Hs-MacBook-Pro.local` | **可（制限なし）** | なし |
| `salesanchor_vps` | - | 不可（permission denied） | - |
| `salesanchor-claude` | Claude Code 専用 | 可（ForceCommand 制限） | 4コマンドのみ |

### VPS `~/.ssh/authorized_keys`（ubuntu）

```
1: ssh-ed25519 ... hitoshi@Hs-MacBook-Pro.local       ← 制限なし
2: ssh-ed25519 ... github-actions-deploy               ← CI/CD 鍵
3: ssh-ed25519 ... shingo-macbook-primary              ← Shingo の鍵
4: command="docker stats --no-stream; free -h; df -h; uptime",
   no-port-forwarding,no-X11-forwarding,no-agent-forwarding,
   no-pty ... salesanchor-claude                       ← ForceCommand 制限
5: ssh-ed25519 ... mgmt-vps-tunnel
```

**`salesanchor-claude` の ForceCommand 制限（ADR-079 準拠）**:
- 許可コマンド: `docker stats --no-stream; free -h; df -h; uptime` のみ
- `psql` / `docker exec` / `docker cp` はすべてブロック

---

## 3. インシデントの構造的原因（なぜ本番で素振りしたか）

### 3-1. 技術的障壁が存在しなかった

| アクセス経路 | 状態 |
|---|---|
| `id_ed25519` → ubuntu → `docker exec ... psql` | **無制限で実行可能** |
| `salesanchor-claude` → `docker exec ... psql` | ForceCommand でブロック（ADR-079） |
| ローカル staging 環境 | **存在しない**（docker-compose.staging.yml 未作成） |

ADR-079 が Claude Code 用鍵を制限したが、**個人鍵 `id_ed25519` には制限が適用されなかった**。VPS 直作業禁止は手順書上のルール（ADR-109:60「VPS直接作業禁止」）にとどまり、技術的強制がなかった。

### 3-2. 素振りタスクに「対象環境」指定がなかった

- 「素振り確認」指示に「本番相当 docker-compose ローカル環境で実施」が明示されなかった
- ローカルに本番相当環境がないため、選択肢が「本番 VPS」のみだった
- ADR-115 が定義する「本番相当 docker-compose」も compose ファイルが未作成

### 3-3. design.md の誤記が認知を歪めた

`design.md` のデプロイ順序セクションに「migration 先行実行 → 新コードデプロイ」と誤記されており、  
「migration を先に適用する」という誤判断を補強した（誤記は commit `a098e4d5` で修正済み）。

---

## 4. 対策案の比較

| 案 | 内容 | 効果 | コスト | 即時性 |
|---|---|---|---|---|
| **A: ローカル staging compose 作成** | `docker-compose.staging.yml`（backend + postgres）を作成し、素振りはローカルで完結させる | 高（本番 VPS に触れずに動作確認可能） | 中（初期構築 1-2 日、秘密管理が課題） | 中 |
| **B: `id_ed25519` の ForceCommand 制限** | VPS `authorized_keys` の `hitoshi@Hs-MacBook-Pro.local` 鍵にも ForceCommand を追加、または鍵を削除して `salesanchor-claude` 経由に統一 | 高（技術的に psql 実行不可） | 低（authorized_keys 1 行変更） | 高 |
| **C: Claude Code Bash hook で SSH+psql パターン検出** | `~/.claude/settings.json` の PreToolUse hook で `ssh ubuntu@49.212.137.46 ... psql` パターンをブロック | 中（Claude Code 経由のコマンドのみ） | 低（hook 追加のみ） | 高 |
| **D: migration dry-run CI ジョブ** | CI に `psql --dry-run`（`BEGIN`…`ROLLBACK` ラップ）ジョブを追加し、本番相当 DB の状態検証は CI で完結させる | 中（列の存在確認は CI で可能） | 中（CI ジョブ追加） | 中 |

### 推奨順序

1. **即時**: B（authorized_keys ForceCommand 制限）— 最低コスト・最高効果。VPS 直作業の技術的封鎖。
2. **短期**: A（ローカル staging compose）— migration の事前検証環境。ADR-115 ③ の実現。
3. **中期**: D（migration dry-run CI）— 自動化による構造的保証。

案 C（Bash hook）は案 B の代替として有効だが、Claude Code 外（zsh 直接実行等）には効かないため、B の補完として位置付ける。

---

## 5. 関連 ADR・ドキュメント

| ドキュメント | 関連箇所 |
|---|---|
| `docs/adr/ADR-115-deploy-safety.md:29-37` | 本番相当素振りの定義・staging 保留の根拠 |
| `docs/adr/ADR-079-salesanchor-claude-key.md` | `salesanchor-claude` 鍵の ForceCommand 制限（id_ed25519 は対象外） |
| `docs/adr/ADR-109-*.md` | VPS 直接作業禁止（手順書ルール、技術的強制なし） |
| `docs/adr/ADR-135-release-stowaway-prevention.md:29-37` | develop=出荷可能・関所は develop 入口 |
| `docs/handoff/incident-20260613-password-hash/incident-report.md` | 今回インシデントの詳細タイムライン・恒久対策案 |

---

## 6. 未調査項目（設計フェーズに持ち越し）

- ローカル staging compose の `.env` 管理方針（本番 secrets をローカルに持つリスク）
- `authorized_keys` 変更後の Shingo 鍵（`shingo-macbook-primary`）への影響範囲
- CI dry-run 用 migration テスト DB の初期化・teardown 手順
- ADR-115 ③「専用ステージング環境」の Go/No-go 判断基準の明文化
