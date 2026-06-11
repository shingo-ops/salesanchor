# ADR-130: nginx reload ポリシー（案B）+ migration TOTAL 自動カウント

## Status
Accepted

## Context

2026-06-11、CI/CD 外の backend コンテナ手動再起動により nginx が旧 Docker IP をキャッシュし続け、全 API が約10時間 502 を返す障害が発生した。

調査により以下が判明:
- CI/CD デプロイ経由の backend 再起動はすべて `scripts/blue-green-cutover.sh` 内の `nginx -s reload` でカバー済み
- Bootstrap SA-18 path（SA18_PHASE2_ENABLED=1）も同 blue-green を使用
- **未カバーの残存ギャップ**: 手動 `docker compose restart backend` などの CI/CD 外操作

あわせて `scripts/run_all_migrations.sh` の `TOTAL=130` ハードコードが migration 追加のたびに手動更新を要することも確認。

## Decision

### ① nginx 安全 reload（案B）

`deploy.yml` の Bootstrap step 末尾に `nginx -s reload` を追加する（belt-and-suspenders）。

- blue-green cutover で既にカバーされているが、将来の Bootstrap 変更でも確実に reload されるよう明示的に追加する
- **案A（resolver + 変数化）は別ADRで後日実施**。9箇所の proxy_pass 書き換えと SSE 動作確認が必要なため今回は見送る

### ② TOTAL 自動カウント

`run_all_migrations.sh:47` の `TOTAL=130` を下記に変更:

```bash
TOTAL=$(grep -cE '^run_(sql|py)[[:space:]]' "$0" 2>/dev/null || echo 0)
```

自動カウントにより migration 追加時の手動更新を不要にする。

## Consequences

- deploy.yml 変更 → 危険変更枠 → **本番デプロイ前に Shingo GO 必須**
- 案A（恒久解）は今後の別ADRで実施。手動再起動時の 502 は現運用ルール（手動再起動後は `nginx -s reload` を実行する）で対処
- TOTAL=0 フォールバック（grep 失敗時）は機能的影響なし（進捗表示のみ）

## References

- recon: `docs/handoff/nginx-reload-total-autocount/recon.md`
- design: `docs/handoff/nginx-reload-total-autocount/design.md`
- 障害ログ: Issue #1951
