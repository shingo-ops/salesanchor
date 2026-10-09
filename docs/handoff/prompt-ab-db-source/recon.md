# recon: 比較試験の道具が、指示書を DB から名前で読めるようにする

この文書は何か：試験の道具（prompt_ab）が指示書をどこから読んでいるかの、現状の事実の一覧。
親（仕様書）：[../../specs/line-analysis-tuning/README.md](../../specs/line-analysis-tuning/README.md)
設計：[design.md](./design.md)

調査日：2026-10-07。基準：origin/main 5bc79ef97。調査は Sonnet、Opus が行番号を再確認した。
社外秘：指示書の本文・仕入元の名前は、この文書に書かない。

## 1. 指示書の置き場所と読み込み

### 1-1. 試験の道具は、リポジトリのファイルからしか読めない
- `backend/app/tools/prompt_ab.py:86` `_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"`
- `backend/app/tools/prompt_ab.py:272-282` `resolve_prompt_path()`：名前の形を `_PROMPT_NAME_RES`（`:80-84`）で検査し、`_PROMPTS_DIR / f"{prompt_name}.txt"` を返す。
- `backend/app/tools/prompt_ab.py:285-299` `_load_prompt_text()`：`--prompt-name` があればそのファイル、無ければ v101・v102 の既定（`backend/app/services/gemini_raw_copy_v101.py:25-26`、v102 の既定は `raw_copy_v101_e`）。
- `backend/app/tools/prompt_ab.py:448` `run_ab()` の中で、Gemini を呼ぶ前に `_load_prompt_text(config, prompt_name)` を読む。
- `backend/app/tools/prompt_ab.py:449-452`・`:476` 結果の行に `prompt_name` を記録する。
- `backend/app/tools/prompt_ab.py:553` 引数 `--prompt-name`。`:585-589` 引数の検査で `resolve_prompt_path()` を呼ぶ。
- `backend/app/tools/prompt_ab.py:616` DB の接続は `_get_sync_session()`（`backend/app/tasks/tcg_extraction.py:88-92`）。`:626-627` で閉じる。

### 1-2. 本番の解析は、もともと DB の表から読む
- 表の定義：`migrations/20260926_080000_create_extraction_prompt_config.sql:11-20`（`prompt_key` UNIQUE、`prompt_text`、`is_active`、`version`、`updated_by`、`created_at`、`updated_at`）。RLS・CHECK は無い。
- `backend/app/services/gemini_extraction_svc.py:141-173` `_load_db_raw_copy_prompt()`：`prompt_key = 'raw_copy_extraction' AND is_active = TRUE` の1行だけを読む。
- `backend/app/services/gemini_extraction_svc.py:109-110`・`:125-126` `_load_db_prompts()`：有効な全行を読み、`base_extraction` と `work_id_extraction` だけを `.get()` で選ぶ。ほかの名前の行が増えても、選ばれない。
- `backend/app/routers/super_admin_suppliers.py:1015-1083` 管理画面の API（一覧・1件・書き込み）。`require_super_admin`。
- `frontend/src/pages/super-admin/ExtractionPromptConfigTab.tsx:65` 画面は `base_extraction`・`work_id_extraction` の2つだけを表示する。
- 試作の指示書ファイルの注記：`backend/app/services/gemini_raw_copy_v8.py:22`「採用が決まったら DB（extraction_prompt_config）へ移す」（v9 `:17`、v10 `:18` も同じ）。

### 1-3. 本番への届け方
- `.github/workflows/deploy.yml:235-236` VPS で `git fetch` / `git reset --hard origin/main`。`backend/Dockerfile:24` `COPY . .` で `backend/` 全体（`app/prompts/` を含む）をイメージに入れる。

## 2. 公開の状態
- `gh repo view shingo-ops/salesanchor`：`"visibility":"PUBLIC"`（2026-10-07 実行）。`backend/app/prompts/*.txt`（9ファイル）は、だれでも読める。

## 3. 試験
- `backend/tests/test_prompt_ab.py:374-381` `named_prompts`：一時フォルダに指示書を作り、`_PROMPTS_DIR` を差し替える。
- `backend/tests/test_prompt_ab.py:37-56` `fakes`：Gemini・台帳・DB の関数を差し替える（本物の DB は使わない）。
- 本物の Postgres を使うのは `:305` の1件だけ。fixture `pg`（`backend/tests/test_tcg_work_matching_integration.py:315-346`）は CI 専用。

## 4. ADR 検索
- 検索：`docs/adr/FEATURE-INDEX.md`（該当なし）と `docs/adr/` の本文（prompt・指示書・extraction_prompt_config・Gemini・書き写し・秘匿）。
- `docs/adr/ADR-014-inventory-management.md:23`・`:29`：解析のロジック・プロンプト・仕入元の情報を、外から構造的に見えなくする（秘匿の方針）。
- `docs/adr/ADR-085-supplier-prompts.md:1`：仕入先別の Gemini プロンプトの管理（別の表 `supplier_prompts`）。
- `docs/adr/ADR-1004-llm-usage-ledger.md:25`：費用の台帳（prompt_ab が書く唯一の表）。
- `extraction_prompt_config`・書き写しを直接扱う ADR：該当なし。
