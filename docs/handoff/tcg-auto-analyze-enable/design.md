# IMP-20: TCG_AUTO_ANALYZE 有効化 — 設計書

作成日: 2026-09-05
ADR 参照: ADR-154-tcg-parity02-gas-python-migration
recon 参照: `docs/handoff/tcg-auto-analyze-enable/recon.md`

---

## KGI

**`TCG_AUTO_ANALYZE=1` がコンテナに渡り、`extraction_jobs` への書き込み後に `analyze_extraction_job()` が自動呼び出されること。**

受け入れ基準（PO が画面・ログで一義に判定できる粒度）:

| 基準 | 検証方法 |
|-----|---------|
| backend コンテナで `os.environ["TCG_AUTO_ANALYZE"]` が `"1"` を返す | `docker compose exec backend python -c "import os; print(os.getenv('TCG_AUTO_ANALYZE'))"` が `1` を出力 |
| celery-worker コンテナで同変数が `"1"` を返す | `docker compose exec celery-worker python -c "import os; print(os.getenv('TCG_AUTO_ANALYZE'))"` が `1` を出力 |
| `extraction_jobs.status='done'` の処理後にログに `解析はスキップ` が**出ない** | `docker compose logs backend --tail=50` で `解析はスキップ（フラグ未設定）` が消え、代わりに解析ログが出る |
| VPS の `.env` に `TCG_AUTO_ANALYZE` 行がなくてもデフォルト `1` で動く | `grep TCG_AUTO_ANALYZE /path/to/.env` が空でも上記3項目が成立 |

---

## 変更ファイル一覧

### 既存ファイルへの追記

| ファイル | 変更内容 | 触らない範囲 |
|---------|---------|-----------|
| `docker-compose.yml` | backend の environment `GEMINI_API_KEY` 直後に `- TCG_AUTO_ANALYZE=${TCG_AUTO_ANALYZE:-1}` を追記 | 他の全環境変数行・ネットワーク設定・volumes |
| `docker-compose.yml` | celery-worker の environment `GEMINI_API_KEY` 直後に同行を追記 | 同上 |

### 新規作成

| ファイル | 役割 |
|---------|------|
| `docs/handoff/tcg-auto-analyze-enable/recon.md` | 現在地把握 |
| `docs/handoff/tcg-auto-analyze-enable/design.md` | 本ファイル |

### 変更しないファイル

- `.github/workflows/deploy.yml`（TCG_AUTO_ANALYZE は Secrets 管理不要・compose デフォルト値で制御）
- `backend/app/tasks/tcg_extraction.py`（コードは #3291 マージ済み・変更なし）
- migration ファイル一切

---

## 設計詳細

### デフォルト値方式

```yaml
# docker-compose.yml — backend / celery-worker 共通パターン
- TCG_AUTO_ANALYZE=${TCG_AUTO_ANALYZE:-1}
```

`${VAR:-default}` の shell 展開: 環境変数 `TCG_AUTO_ANALYZE` が未設定または空の場合に `1` を使う。  
VPS の `.env` に明示行がなくても ON になる。OFF にしたい場合は `.env` に `TCG_AUTO_ANALYZE=0` を追記。

### deploy.yml との関係

`deploy.yml:206〜231` の `sed` ブロックに `TCG_AUTO_ANALYZE` は含まれていない。  
よって deploy 時も `.env` 内の既存値は保持される（sed が触らない）。  
デフォルト値 `1` は compose 起動時にコンテナへ渡されるため、`.env` への追記は不要。

### OFF に戻す方法

VPS 上で:

```bash
echo "TCG_AUTO_ANALYZE=0" >> .env
docker compose up -d backend celery-worker
```

または PR をリバート → deploy。

---

## 弊害・リスク

| リスク | 評価 | 対策 |
|-------|------|------|
| `analyze_extraction_job()` の呼び出しが増加してコンテナ負荷が上昇 | 低（TCG テナントの抽出頻度は限定的） | Celery worker の concurrency=2 上限が既存の制限として機能 |
| `.env` に `TCG_AUTO_ANALYZE=0` が残っていて意図せず OFF になる | 低（VPS 上に該当行が存在しないことを確認済み：未設定） | デプロイ後に `docker compose exec backend python -c "print(...)"` で即時確認可 |
| compose デフォルト `1` が他テナントの想定外解析を発火 | 排除済み（tcg_extraction.py は TCG テナント専用・他テナントのタスクは別ルート） | コードレビュー済み（Stage 2 #3291） |

---

## 戻し方

```bash
# PR をリバートするだけ。migration なし・DB 変更なし
git revert <merge-commit>
```

または VPS `.env` に `TCG_AUTO_ANALYZE=0` を追記して `docker compose up -d`（即時 OFF）。

---

## 外部・過去事例の参照と我々への応用

**GEMINI_API_KEY の同一パターン（ADR-110・2026-05-29 修正）:**
- `backend:95` と `celery-worker:202` の両方に `GEMINI_API_KEY=${GEMINI_API_KEY:-}` を追加した precedent あり
- 今回はその直後に同形式で追記（一貫性確保）

**compose passthrough 漏れ教訓（2026-05-29）:**
- `.env` に値があっても `docker-compose.yml` に passthrough 行がないと `os.getenv` が空になる
- 今回は逆方向（compose デフォルト `1` で常時 ON）だが、同じ「1行追加」が根拠

---

## 維持の仕組み + 守り手

守り手: `backend/tests/test_tcg_gemini_extraction.py`（CI で自動実行）

| 層 | 仕組み | 守り手 |
|----|--------|--------|
| フラグ OFF 既定テスト | `TCG_AUTO_ANALYZE` 未設定時に `analyze` を呼ばない | `test_auto_analyze_off_skips_analyze`（CI） |
| フラグ ON テスト | `TCG_AUTO_ANALYZE=1` 時に `analyze` を 1 回呼ぶ | `test_auto_analyze_on_calls_analyze`（CI） |
| compose 変数追加の記録 | 本 design.md + PR 本文 | PR レビュー |
