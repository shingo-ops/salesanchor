# SA 日次ハンドオフ — 2026-06-12

> **目的**: 本日の SA 作業の完了状態・残タスク・恒久対応を後続セッションに引き継ぐ。
> **正本**: `docs/plans/sa-progress/HANDOFF-SA-2026-06-12.md`

---

## §1. 作業日・参加者

| 項目 | 内容 |
|------|------|
| 日付 | 2026-06-12 |
| PO | Shingo |
| 実装担当 | Terminal CC（複数セッション） |

---

## §2. SA 進捗現況（EOD）

| SA | 進捗 | フェーズ | 残タスク |
|----|------|---------|---------|
| SA-03 | **90%** | ⑤ 本番反映済み | テスト発行検収（Shingo）→ 「検収OK」でCC が100%更新 |
| SA-04 | **90%** | ⑤ 本番反映済み | KGI G1〜G4 実測 + SA-01 横断チェック |
| SA-05〜12 | 0% | 未着手 | 順番待ち |

---

## §3. 本日完了事項

| PR | 内容 | マージ時刻 |
|----|------|-----------|
| #2031 | hotfix: nginx コンテナ再作成ステップ追加（design-site ボリューム反映） | 07:22 |
| #2032 | release: develop → main（ADR-136 company-stats-ssot 本番投入） | 10:46 |
| #2037 | docs(adr-134): design-site Basic認証欠落インシデント事後承認記録 | 12:28 |
| #2042 | fix(deploy): nginx inode ズレ対策 — 設定変更時に force-recreate (ADR-137) | 10:53 |
| #2045 | release: develop → main（OVERVIEW バッジ修正・SA-03/SA-04 90%反映） | 12:36 |
| #2053 | release: develop → main（ADR-137 Completed 含む） | 13:04 |

---

## §4. 決定事項（Shingo 2026-06-12）

| 決定 | 内容 |
|------|------|
| SA-03 完了条件確定 | テナント告知は対象外（社内用）。G4＝「社内運用が新フォームへ切替済み」で達成 |
| SA-03 マニュアル作成 | バックログ切り出し（UIボタン配置最終確定後・デザイン改善イニシアチブと連動） |
| ADR-136 GO確認 | PR #2032 の本番投入を別セッションで承認済みと確認（GO: Shingo 2026-06-12） |
| GO 記録軽量ルール | GO を出した時点で当該 PR に `GO: Shingo YYYY-MM-DD` コメントを残す（STANDARD-WORKFLOW §5） |

---

## §5. ペンディング・残作業

| 項目 | 状態 | 担当 |
|------|------|------|
| PR #2023（SA-04-plan.md ⑤更新） | CI 通過後 auto-merge 設定済み | CC |
| PR #2035（smoke④ FAIL 自動遮断） | OPEN・CI 待ち | CC |
| PR #2056（ADR-136 GO記録 + STANDARD-WORKFLOW） | OPEN・CI 待ち | CC |
| SA-03 テスト発行検収 | Shingo 実施待ち | Shingo |

---

## §6. 関所恒久対応 — nginx inode ズレ対策（ADR-137 PR-A）

**問題**: `git reset --hard` が `nginx.conf` を新 inode で置換するため、Docker bind mount が旧 inode を参照し続ける。2026-06-12 の ADR-134 デプロイで `/design/` 認証未反映（200 返却）として発現。

**実施した方式（別セッション・PR #2042）**:
- `.github/workflows/deploy.yml` に `nginx:` paths-filter を追加
- `nginx/**` または `docker-compose.yml` が変更されたデプロイでのみ `docker compose up -d --no-deps --force-recreate nginx` を実行
- blue-green cutover 完了後に実行するため backend 可用性に影響なし（nginx 再起動 ~2-3s 窓のみ）

| 項目 | 内容 |
|------|------|
| 対応 PR | **#2031**（hotfix・即日適用） → **#2042**（ADR-137 PR-A・恒久版） |
| ADR | `docs/adr/ADR-137-nginx-config-deploy-reliability.md` |
| ステータス | ✅ マージ済み（2026-06-12 10:53） |
| 検証 | deploy run #27401107031 smoke PASS |

---

## §7. インシデント記録（2026-06-12）

| 項目 | 内容 |
|------|------|
| 発生 | /design/ が約55分間 Basic認証なし 200 を返却 |
| 原因 | PR #2021 で htpasswd.d ボリューム追加、nginx 自動再作成されず未マウント |
| 対応 | PR #2031 hotfix（force-recreate 追加）→ smoke PASS で復旧 |
| 事後承認 | Shingo 承認済み（2026-06-12、緊急セキュリティ対応）|
| 記録場所 | `docs/handoff/design-site/design.md` §10 |

---

## §8. 関所恒久対応 — smoke④ FAIL 時の /design/ 自動遮断（ADR-134 D）

**問題**: smoke④ が FAIL した場合に `/design/` が無防備のまま残るリスク（§7 インシデントの再発防止）。

**実施した方式（別セッション・PR #2035）**:
- `.github/workflows/deploy.yml` に `Emergency block /design/ on smoke FAIL`（`if: failure()`）ステップを追加
- 動作: `Verify deployment` 失敗 → htpasswd 削除 → `--force-recreate nginx` → nginx が 500 を返す（fail-closed）
- 次回デプロイ成功時に `Setup design-site htpasswd (idempotent)` が自動復旧
- fail-open なし・`--no-deps` でアプリ本体に影響なし

| 項目 | 内容 |
|------|------|
| 対応 PR | **#2035**（ci(adr-134): smoke④ FAIL 時の /design/ 自動遮断） |
| ADR | `docs/adr/ADR-134-design-site-basic-auth.md` |
| ステータス | OPEN（CI 待ち・マージ待ち） |
| 設計書 | `docs/handoff/design-site-smoke-autoblock/design.md` |
