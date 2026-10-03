# 為替レート履歴（app_fx_rate_history）新設 — Design

**日付**: 2026-10-03
**ブランチ**: release/fx-rate-history-table（本PRは **PR-A**。PR-B は別PRで後続）
**Recon**: [recon.md](recon.md)
**PO承認**: 2026-10-03 — USD/JPY レート履歴を保持し、LLM使用量ダッシュボードを各使用時点のレートで換算する
**ADR参照**: ADR-148（為替レート SSOT、本PRで追記）、ADR-1004（LLM使用量台帳）、ADR-135／ADR-136（本番投入・危険PRのGO手順）

---

## 1. 目的

LLM 使用量ダッシュボード（`frontend/src/pages/super-admin/components/LlmUsageSection.tsx`）は現在、USD コストを**常に「現在の」`app_fx_rates.rate_jpy`** で JPY 換算している（recon.md §4）。`app_fx_rates` は `currency` を PRIMARY KEY に UPSERT するため過去のレートは残らない（recon.md §1-2）。1547件のLLM使用イベント（2026-09-27〜）を、各イベント発生時点の実際のレートで正しく換算するには、レートの履歴を保持する必要がある。

本PR（PR-A）は **テーブル新設のみ**。アプリケーションコードは変更しない。理由: `.github/workflows/deploy.yml` はバックエンドのコード切替をマイグレーション実行より先に行うため（`migrations/20260930_150000_create_llm_usage_events.sql` 冒頭コメントに同種の既知パターンの説明あり）、PR-Bのコード（新テーブルへの書き込み/読み取り）を先に出すと「テーブルが無い」エラーの窓ができる。PR-A → PR-B の順で安全にデプロイする。

**利用者に見える変化（本PR）**: なし。
**開発者に見える変化（本PR）**: `public.app_fx_rate_history` テーブルが追加される。既存の `app_fx_rates` の読み書き経路・LLM使用量ダッシュボードの表示は無変更。

---

## 2. 対象と対象外（本PR = PR-A）

### 対象
- 新規マイグレーション `migrations/20261003_100000_create_app_fx_rate_history.sql`: `public.app_fx_rate_history` テーブル・RLS・シードINSERTを新設。
- `scripts/run_all_migrations.sh`: 末尾に `run_sql migrations/20261003_100000_create_app_fx_rate_history.sql` を追記（SSoT登録）。
- `docs/adr/ADR-148-fx-rate-ssot.md`: 2026-10-03 追記セクション。
- `docs/adr/README.md`: `node scripts/generate-adr-index.js` 再生成分。

### 対象外（本PRでは変更しない。recon.md で確認済み）
- `backend/app/tasks/fx_rate_updater.py`、`backend/app/routers/fx_rate_admin.py`: 書き込み/読み取りロジックは PR-B で変更。本PRはテーブルのみ。
- `frontend/src/pages/super-admin/components/LlmUsageSection.tsx`: PR-B で `cost_jpy`/`fx` ブロック対応に変更。本PRは無変更。
- `public.app_fx_rates` テーブル自体: DROP しない。PR-B 移行後も当面残置し、DROP は別途 PO 自身の GO が必要（ADR-148 追記）。
- 請求書のライブ取得系統（`backend/app/routers/invoices.py` の `fetch_fx_rate`、`GET /api/v1/fx-rate/{currency}` 単数形）: 本PR・PR-Bいずれも対象外。独立系統のまま維持。
- 発注書等のスナップショット列（受発注時点のレートを個別カラムに保存する既存の仕組みがあればそれ）: 本PRは関与しない。履歴テーブルは「ダッシュボード用の参照系」であり、既存のスナップショット保存の仕組みを置き換えるものではない。

---

## 3. 変更内容（本PR = PR-A）

### 3-1. 新テーブル

```sql
CREATE TABLE IF NOT EXISTS public.app_fx_rate_history (
    currency   VARCHAR(3)    NOT NULL,
    rate_jpy   NUMERIC(12,4) NOT NULL CHECK (rate_jpy > 0),
    fetched_at TIMESTAMPTZ   NOT NULL,
    created_at TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    PRIMARY KEY (currency, fetched_at)
);
```

- `PRIMARY KEY (currency, fetched_at)`: 同一通貨・同一取得時刻の重複挿入を防ぎつつ、取得ごとに新しい行を追記できる（`app_fx_rates` の `currency` 単独PKとの違い）。
- `rate_jpy NUMERIC(12,4) CHECK (rate_jpy > 0)`: `app_fx_rates` にはCHECK制約がないため、履行テーブルでは不正値（0以下）を防ぐ制約を追加した（新設テーブルのため既存データ互換の制約はない）。
- RLS: `app_fx_rates`（`migrations/20260628_170000_add_app_fx_rates.sql:35-51`）と同方針。読み取り全許可・書き込み `app.is_operator='true'` のみ。ポリシー名は `app_fx_rate_history_read` / `app_fx_rate_history_write`（新テーブル用に別名）。
- シード: `app_fx_rates` の現在値（本番1行）を `ON CONFLICT DO NOTHING` で取り込む。これにより履歴テーブルは本番適用直後から「取得可能な最古の1点」を持つ。

### 3-2. 登録

`scripts/run_all_migrations.sh` 末尾に以下を追記（既存の直近エントリと同じ書式）:
```
# ADR-148 追補 PR-A: public.app_fx_rate_history 新設（為替レート履歴・追記専用・表のみ。書込/読取切替はPR-Bで実施）
run_sql migrations/20261003_100000_create_app_fx_rate_history.sql
```

### 3-3. ADR追記

`docs/adr/ADR-148-fx-rate-ssot.md` に「追記（2026-10-03）」セクションを追加（なぜ／決定／関連）。移行順序（PR-A→PR-B→`app_fx_rates`は当面残置・DROPはPO本人のGO必須）を明記。

---

## 4. ローカル検証の制約（事実）

ローカルDocker（`salesanchor-postgres-1`）に対して `docker exec -i ... psql < migrations/20260628_170000_add_app_fx_rates.sql`（前提となる既存テーブルを先に作る目的）を実行しようとしたところ、ローカルのPreToolUseフック（リポジトリ外 ~/.claude/scripts/agent-danger-hook.sh の `psql-write-guard`）が `docker+psql < file` パターンを検知し以下を返して **BLOCKED** した（verbatim）:

```
🚫 BLOCKED [psql-write-guard]: 本番DBへの直接書き込みは禁止されています。
   検知パターン: docker+psql < file
   読み取り（-c "SELECT ..."）は許可されています。
   書き込みが必要な場合: bash scripts/permit-danger.sh "psql write"
   （1回限り有効・30分で自動失効）
```

本カードの許可範囲に `scripts/permit-danger.sh` の実行は含まれておらず、フックに止められた場合は「言い換えて回避しない・止まって報告する」運用のため、ローカルでの実行検証はここで停止した。SQL自体は `app_fx_rates`（`migrations/20260628_170000_add_app_fx_rates.sql`）の既存パターンを1行単位で忠実に複製しており、構文上の新規リスクは低いと判断するが、**未確認**の部分（ローカルでの実際のCREATE/INSERT成功・2回目実行での冪等性）は、本PR作成後に `.github/workflows/migration-test.yml`（recon.md §5、既存行と新規行の両方を実DBに2回適用して冪等性を検証する設計）で検証される。

本番のマイグレーション実行ロールが RLS を自動バイパスするか（`BYPASSRLS` 権限・テーブル所有者特権等）は未確認のため、§3-3のシードINSERTはそれに依存せず、INSERT直前に `SELECT set_config('app.is_operator', 'true', false);` を発行して明示的に operator コンテキストを与える（`migrations/20261003_100000_create_app_fx_rate_history.sql`）。`scripts/run_all_migrations.sh:61-65` の `run_sql()` は `docker exec -i "${POSTGRES}" ${PSQL} < "${REPO_DIR}/${file}"` でファイル1本につき新規 `psql` 接続（セッション）を1つ起動するため、この設定は当該ファイルの1セッションに限定され他マイグレーションへ漏れない。既存マイグレーションで同パターンを使った例はなく（migrations/ 配下に `set_config('app.is_operator'` の前例なし）、`backend/tests/rls_bootstrap.py:278` 等のテストコードでのみ同種の設定（空文字へのリセット）が使われている。

| 基準 | 検証方法 |
|------|---------|
| 1) SQL構文が正しい | `.github/workflows/migration-test.yml` の `migration-test-run` job が実PostgreSQLに本マイグレーションを適用（CI、PR作成後） |
| 2) 冪等（2回実行してエラーなし） | 同CI jobが2回目の適用も行う設計（recon.md §5）。PRのCIログで確認 |
| 3) `scripts/run_all_migrations.sh` への登録漏れがない | `migration-registration-exists` job（`.github/workflows/migration-test.yml`）が `migrations/**` 配下の全ファイルの登録有無を点検 |
| 4) RLSポリシーが `app_fx_rates` と同方針 | 本design §3-1の記述とマイグレーションファイルの該当行を目視比較（本ドキュメント作成時点で実施済み） |
| 5) ADR追記・索引再生成 | `node scripts/generate-adr-index.js` 実行後 `git diff docs/adr/README.md` に変更が出ることを確認（本PRのコミットに含む） |

### 外部・過去事例

該当なし。理由: 本変更は既存の自社パターン（`app_fx_rates` の UPSERT 型 SSOT テーブルと同じRLS/コメント規約に沿った「履歴テーブルの追加」）であり、一般的なRDBMS設計パターン（追記専用の履行テーブル、複合PK）の範囲内。外部ベンダー固有の実装ではないため個別の外部事例調査は不要と判断。

---

## 5. 維持の仕組み

- 守り手: `.github/workflows/migration-test.yml` の `migration-registration-exists` job が、`migrations/**` に追加したファイルが `scripts/run_all_migrations.sh` に登録されているかを**PRごとに**強制点検する。登録漏れがあればCIが赤くなる。
- 守り手: `migration-test-run` job が、新規マイグレーションを含むPRで**毎回**実PostgreSQLに2回適用し冪等性を検証する。これにより本テーブルが将来誤って非冪等な変更をされた場合に検知できる。
- `app_fx_rates` の残置期間（PR-B適用後〜DROP）は、ADR-148追記に明記した通り「DROPは別途PO本人のGOが必要」というルールで管理される。DROPし忘れを恒常化させるリスクはあるが、残置自体は実害がない（読み書きされないだけの不使用テーブル）ため、積極的な期限管理は本PRの範囲外とする。

---

## 6. リスクと戻し方

### リスク
- 本PRはテーブル追加のみで既存動作に影響しないため、本番投入リスクは低い。
- シードINSERTが対象とする `public.app_fx_rates` に本番で複数通貨・複数行が将来追加された場合でも、`ON CONFLICT (currency, fetched_at) DO NOTHING` のため重複挿入エラーは起きない。
- ローカルでのSQL実行確認ができなかった（§4）ため、未知の構文エラーがCI初回実行で初めて判明するリスクが通常よりやや高い。緩和: `app_fx_rates` の既存マイグレーションの行をそのまま複製する形で記述しており、差分は列定義・PK・テーブル名・ポリシー名のみ。

### 戻し方
- `git revert <本PRのマージコミット>` でマイグレーションファイル・`scripts/run_all_migrations.sh` 登録・ADR追記を元に戻せる。
- DBに対しては、本番適用後であればマイグレーションのコメントに記載したロールバックSQL（`DROP TABLE IF EXISTS public.app_fx_rate_history CASCADE;`）を別途実行する必要がある（revertだけではテーブルは消えない。コードのrevertとDBの変更は別物）。本PRの範囲ではDROPは実行しない。

---

## 7. ロールアウト

- 本PRはマイグレーション追加のみで、アプリケーションコードの挙動は変わらない（ADR-135の「migrations/ を含む実装はPO GOが出るまでreleaseブランチで待機」に該当するため、mainへのマージにはPO GOが必要）。
- マージ条件: 必須CI通過（`.github/workflows/migration-test.yml` 含む）＋ Reviewer APPROVE ＋ PO の「GO #PR番号」。
- PR-B（書き込み/読み取り切替＋ダッシュボードのJPY換算対応）は本PRのマージ・本番デプロイ完了後に別PRとして着手する。

---

## 8. PR-B 概要（別PR・本PRでは実装しない）

設計の継続性のため、次PRの方針をここに記録する（実装は別PRで行う）。

- **書き込み**: `backend/app/tasks/fx_rate_updater.py`・`backend/app/routers/fx_rate_admin.py` の `refresh_fx_rate` が、`app_fx_rates` へのUPSERTに加えて（または代えて）`app_fx_rate_history` へ `INSERT ... ON CONFLICT (currency, fetched_at) DO NOTHING` で追記する。
- **読み取り**: `GET /api/v1/fx-rates/{currency}`（`backend/app/routers/fx_rate_admin.py:44-72`）は `app_fx_rate_history` から `ORDER BY fetched_at DESC LIMIT 1` で最新行を取得する実装に切替える。レスポンス形状（`FxRateResponse`: `currency`/`rate_jpy`/`fetched_at`/`updated_at`）は維持する（`updated_at` は履行テーブルの `created_at` を転用、またはレスポンスから `updated_at` を除くかは実装時に設計）。
- **ダッシュボードAPI**: `GET /api/v1/tcg/analysis-dashboard/llm-usage`（`backend/app/routers/tcg_analysis_dashboard.py:680`）に `cost_jpy` を各集計行（total/by_purpose/by_model/daily等）に追加する。各 `public.llm_usage_events` 行に対し、`LATERAL` で「`fetched_at <= occurred_at` を満たす最新の `app_fx_rate_history` 行」を引き、無ければ（`occurred_at` が履歴の最古行より古い場合）最古行にフォールバックする。レスポンスに `fx` ブロック（最新レート・`fetched_at`・履行開始時点・フォールバック適用件数）を追加する。
- **フロントエンド**: `frontend/src/pages/super-admin/components/LlmUsageSection.tsx` は `cost_jpy` と `fx` ブロックをAPIレスポンスから直接使うようにし、自前の `/fx-rates/USD` 呼び出しと `toJpy()` 変換（同ファイルの394行目・311行目付近）を削除する。フォールバック適用件数がある場合はUIにその旨を表示する。
- **i18n**: `frontend/src/locales/ja.json` / `frontend/src/locales/en.json` に、フォールバック表示用の新規キー（例: `llmUsage.fxFallbackNotice`）を両言語同時に追加する（ADR-027）。
