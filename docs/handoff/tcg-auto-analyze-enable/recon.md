# IMP-20: TCG_AUTO_ANALYZE 有効化 — Recon

作成日: 2026-09-05
ブランチ: `release/tcg-auto-analyze-enable`
担当: Hikky-dev

---

## 前提調査

### フラグ読み取り箇所

`backend/app/tasks/tcg_extraction.py:219`（origin/main 時点・#3291 マージ済み）:

```python
auto_analyze = os.environ.get("TCG_AUTO_ANALYZE", "").strip() == "1"
```

- デフォルト: `""` → `False`（解析スキップ）
- ON にする値: `"1"` のみ（`"true"` / `"on"` 等は `False` 扱い）

### docker-compose.yml 現状確認

**backend（`docker-compose.yml:95`）** — `GEMINI_API_KEY` の直後:

```yaml
- GEMINI_API_KEY=${GEMINI_API_KEY:-}
# ← ここに追加
```

**celery-worker（`docker-compose.yml:203`）** — `GEMINI_API_KEY` の直後:

```yaml
- GEMINI_API_KEY=${GEMINI_API_KEY:-}
# ← ここに追加
```

`celery-beat`（`:243〜`）は `DATABASE_URL` / `REDIS_URL` のみ。TCG 抽出タスクは `celery-worker` 経由のため beat への追加は不要。

### deploy.yml の passthrough 経路

`deploy.yml:205〜264` の「sed 削除 → append」パターン確認:

- `TCG_AUTO_ANALYZE` は deploy.yml の対象外（GitHub Secrets 未登録）
- `docker-compose.yml` の `${TCG_AUTO_ANALYZE:-1}` デフォルト値で ON になる設計のため、deploy.yml の変更は不要

### 関連 ADR

```
docs/adr/ADR-154-tcg-parity02-gas-python-migration.md
```
（`ls docs/adr/ | grep 154` で実在確認済み）

### 変更スコープ確認

| ファイル | 変更内容 | 触らない範囲 |
|---------|---------|-----------|
| `docker-compose.yml` | backend・celery-worker の environment に `TCG_AUTO_ANALYZE=${TCG_AUTO_ANALYZE:-1}` を各1行追加 | 他の全環境変数行、`deploy.yml`、Python コード一切 |

migration: なし（コード変更なし）  
新規ファイル: `docs/handoff/tcg-auto-analyze-enable/recon.md`（本ファイル）・`docs/handoff/tcg-auto-analyze-enable/design.md`
