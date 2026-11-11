# 実装カード 3c: 移行の確かめの試験DBに選択肢の表を前もって登録する（ADR-1058 段3）

## 受領確認
- 作業場所: release/secretary-codex-stage3。着手時の先頭は 0. の確かめのとおり。
- 触るファイルは `.github/workflows/migration-test.yml` の1つだけ。

## なぜ
PR の確かめ「マイグレーションSQL 実行テスト（実DB）」が次で落ちた（2026-11-11 06:29 UTC・job 130364667484）:
`psql:migrations/20261111_120000_add_codex_secretary_choices.sql:15: ERROR:  relation "public.ai_job_choices" does not exist`
この確かめは変わった SQL だけを流す。前の migration で作られた表は、`.github/workflows/migration-test.yml` の `<<'PUBLIC_SQL'` の塊に最小定義を前もって登録する決まり（同じ塊の ops_incidents・ai_cloud_meta などと同じ）。段3a/3b のカードに入れ忘れた。

## 禁止
- 下の 1. の差し込み以外は変えない（並び・空白・ほかの塊も）。`.github/workflows/workflow-lint.yml` は触らない。
- 2 か所目の `PUBLIC_SQL`（1849 行目付近の別のジョブ）には足さない。

## 0. 着手前の確かめ
- 0-1 `git log -1 --format=%H` を記録する。
- 0-2 `grep -n '^          PUBLIC_SQL$' .github/workflows/migration-test.yml` が2行（1044 行目と 1926 行目付近）。違えば停止して NEEDS_DECISION。
- 0-3 `grep -c 'ai_job_choices' .github/workflows/migration-test.yml` が 0。違えば停止して NEEDS_DECISION。

## 1. 差し込み
1 つ目の `          PUBLIC_SQL` の行（0-2 の1行目）の直前に、次の 14 行をそのまま差し込む（先頭の空白は 10 個。表の定義は migrations/20261103_120000_create_ai_job_assignments.sql の 1-1 と同じ）:

```
          -- public.ai_job_choices: migrations/20261103_120000_create_ai_job_assignments.sql（ADR-1058 段1a）で本番作成済み。
          --   20261111_120000_add_codex_secretary_choices.sql が INSERT ... ON CONFLICT DO NOTHING するため前提として登録する（定義は本物と同じ）。
          CREATE TABLE IF NOT EXISTS public.ai_job_choices (
              id SERIAL PRIMARY KEY,
              job_key TEXT NOT NULL,
              provider TEXT NOT NULL,
              model TEXT NOT NULL,
              created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
              CONSTRAINT ai_job_choices_job_key_check CHECK (job_key IN ('line_extraction', 'translation_inbound', 'translation_inbound_escalation', 'translation_outbound', 'secretary_intent')),
              CONSTRAINT ai_job_choices_provider_check CHECK (provider IN ('gemini', 'codex', 'claude')),
              CONSTRAINT ai_job_choices_job_provider_model_key UNIQUE (job_key, provider, model),
              CONSTRAINT ai_job_choices_id_job_key_key UNIQUE (id, job_key)
          );

```

（最後の 1 行は空行。差し込んだ後、空行の次が `          PUBLIC_SQL` になる。）

## 2. 確かめ方
- 2-1 `git diff --stat` が `.github/workflows/migration-test.yml | 14 +` の 1 ファイルだけ（消した行 0）。
- 2-2 `python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/migration-test.yml')); print('yaml ok')"` が `yaml ok`。
- 2-3 `grep -c 'ai_job_choices' .github/workflows/migration-test.yml` が 6。

## 分岐
- 2-1〜2-3 のどれかが違う → 停止して NEEDS_DECISION（生の出力を添える）。直そうとして別の書き方にしない。
- push が見張りに止められた → 言い換えず停止して BLOCKED:。

## 合格の基準
2-1〜2-3 がすべて書いたとおり。push 後の `git log origin/release/secretary-codex-stage3 -1` が自分の commit。

## 報告の型
commit id・`git diff HEAD~1` の全文・2-1〜2-3 の生出力・最後に DONE / BLOCKED: / NEEDS_DECISION: のどれか。

commit 文: `ci: register ai_job_choices as a migration-test prerequisite (ADR-1058 stage 3)`、空行、`Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`。

END OF CARD
