# design: LLM 月次予算リセットの反映漏れ修正

## 問題

`public.tenant_llm_budgets.current_month_usd`（月次 LLM 利用額の累積）は `reset_monthly_if_needed()`
（`backend/app/services/llm_budget.py:363-398`）が呼ばれたときだけ月初に 0 リセットされる。この関数の
本番唯一の呼び出し元は `inventory_parser.py:961`（在庫解析フロー）のみで、`message_translator.py`
（翻訳フロー、ADR-110-sa-translation-subsystem）は `check_budget()` のみを呼び、`reset_monthly_if_needed()`
を一度も呼んでいなかった（`docs/handoff/llm-budget-monthly-reset/recon.md` §3）。

結果、翻訳のみを使う／在庫解析をほぼ使わないテナントでは月次リセットが実質的に発生せず、
`current_month_usd` が月をまたいで累積し続ける。本番確認（2026-10-02, recon.md §4）で
tenant 4 / tenant 6 とも `last_reset_at = 2026-05-22` のまま 5 ヶ月間更新されていないことを確認した
（根拠: recon.md に生出力あり）。`hard_stop=true` のテナントでは、本来当月分のみで判定すべき予算超過が
過去分の累積によって早期に誤トリガーされるリスクがある。

## 変更

`backend/app/services/message_translator.py` の2つのエントリポイントで、既存の `check_budget()` 呼び出しの
直前に `reset_monthly_if_needed()` を追加した。`inventory_parser.py:959-966` の「reset → check、同一トランザクションでまとめてコミット」の順序をそのまま踏襲している。

- `backend/app/services/message_translator.py:38` — import に `reset_monthly_if_needed` を追加
- `backend/app/services/message_translator.py:528` — `translate_inbound()` 冒頭、初回 `check_budget()`（`:529`）の直前
- `backend/app/services/message_translator.py:680` — `generate_outbound_draft()` 冒頭、`check_budget()`（`:681`）の直前

### 触らない範囲（スコープ外）

- `backend/app/services/llm_budget.py` のロジック（`reset_monthly_if_needed` / `check_budget` 本体）は無変更
- `backend/app/services/inventory_parser.py` は無変更（既存の呼び出しをそのまま参照パターンとして使用）
- DB スキーマ・マイグレーション変更なし
- `translate_inbound()` のエスカレーション時の 2 回目の `check_budget()`（`:552`）には `reset_monthly_if_needed()` を追加しない —
  同一リクエスト内で直前に実行済みのため二重呼び出しは不要（`reset_monthly_if_needed` 自体は冪等だが、1リクエスト1回で十分という inventory_parser の設計と揃える）
- `reset_monthly_if_needed()` 呼び出しを `try/except` で包むかどうか: `inventory_parser.py` は
  例外を握りつぶして解析を止めない設計（`:959-963` のコメント「budget エラーで解析を止めない」）だが、
  本変更ではラップしていない。`message_translator.py` は元々 `check_budget()` やその他の DB 呼び出しを
  個別に `try/except` していないスタイルであり、例外発生時に処理が止まる挙動は既存の `check_budget()` /
  `record_cost()` と同じ扱いになる。挙動差分として明記する（下記リスク参照）。
- コミット追加なし: `reset_monthly_if_needed()` 自体は `db.execute()` のみで commit しない。
  `translate_inbound()` 末尾 `:573`、`generate_outbound_draft()` 末尾 `:711` の既存 `await db.commit()` に
  同一トランザクションとして乗る（recon.md §3 の判断）。

## テスト

`backend/tests/test_message_translator.py` を拡張（既存の mock スタイルを踏襲）:

- `test_cache_miss_calls_gemini_and_saves` / `test_outbound_uses_send_model`: `reset_monthly_if_needed` と
  `check_budget` を共有の `call_order: list[str]` に `side_effect` で記録させ、`call_order[0] == "reset"`,
  `call_order[1] == "check"` で呼び出し順序を assert
- `test_budget_exceeded_raises_error` / `test_no_budget_row_raises_error` / `test_translate_inbound_override_persists_to_save` /
  `test_outbound_budget_exceeded_raises`: 新たに `reset_monthly_if_needed` を `AsyncMock` で patch し、
  `mock_reset.assert_awaited_once_with(db, 1)` を追加（既存テストが実関数を叩いて `AsyncMock` の DB と
  比較して壊れるのを防ぐ目的も兼ねる）

「stale `last_reset_at` → リセット実行」自体の単体テストは既に `backend/tests/test_llm_budget.py:166-218`
（`TestResetMonthlyIfNeeded`、`test_previous_month_triggers_reset` 等）に存在し、`reset_monthly_if_needed()`
本体は無変更のため新規追加不要と判断した。

## 外部事例・過去事例

該当なし。理由: 本変更は社内の2つの類似関数（`inventory_parser.py` の既存パターン）を
もう一方のモジュールに揃えるだけの社内整合性修正であり、外部ライブラリ・外部サービスの仕様に
依存しない。Context7 / GitHub 検索の対象となる新規ライブラリ導入・API 仕様確認は発生しない。

## 検証方法

| 基準 | 検証方法 |
|---|---|
| `reset_monthly_if_needed()` が `check_budget()` より前に呼ばれる（`translate_inbound` / `generate_outbound_draft` 両方） | `backend/tests/test_message_translator.py` の `call_order` assert（`test_cache_miss_calls_gemini_and_saves`, `test_outbound_uses_send_model`）。pytest green |
| 既存の budget 超過・NO_BUDGET_ROW 時の例外挙動に変更がない | `test_budget_exceeded_raises_error` / `test_no_budget_row_raises_error` / `test_outbound_budget_exceeded_raises` が green のまま |
| `llm_budget.py` 本体の reset ロジックは無変更 | `git diff origin/main -- backend/app/services/llm_budget.py` が空 |
| 反映後に翻訳が1回呼ばれたテナントの `last_reset_at` が当月初以降・`current_month_usd` が当月分のみ | デプロイ後、該当テナントで翻訳実行 → 本番 read-only SELECT で `last_reset_at >= 当月1日UTC` かつ `current_month_usd` が今回分と整合することを確認（本タスクでは未実施・デプロイ後の確認項目として記録） |
| ruff / pytest に新規違反がない | `ruff check backend/app/services/message_translator.py`（クリーン）。`backend/tests/test_message_translator.py` の3件の I001/F401 は `origin/main` 時点から存在する既存違反で本変更による新規発生ではないことを `/tmp` 保存の `origin/main` 版との diff で確認済み |
| condition-vocab gate に影響しない | `scripts/check-condition-vocab.js` の `CODE_FILES` は `inventory_parser.py` / `inventory_parser_llm.py` / `ParseReviewPage.tsx` のみで `message_translator.py` を含まない（目視確認） |

## リスク

初回デプロイ後、最初に翻訳機能（`translate_inbound` または `generate_outbound_draft`）が呼ばれたテナントで
`reset_monthly_if_needed()` が実行され、`last_reset_at < 当月1日` であれば即座にリセットされる。これは
tenant 6 のように 5月以降蓄積していた `current_month_usd`（recon.md §4: `0.0145`）がその時点で 0 に戻ることを意味する。
これは意図した挙動（本来あるべき状態への是正）であり、予算超過判定が緩む方向の変化のみでユーザー影響はない
（`hard_stop` 誤トリガーのリスクを下げる方向）。

## 維持の仕組み

`inventory_parser.py` と `message_translator.py` の双方が `reset_monthly_if_needed()` を呼ぶようになったことで、
今後 LLM を呼ぶ新しいエントリポイントを追加する開発者は既存の2箇所をパターンとして参照しやすくなる。
ただし「新しい LLM 呼び出し箇所で `reset_monthly_if_needed()` の呼び忘れ」を機械的に防ぐ CI チェックは存在しない。

守り手: `backend/app/services/llm_budget.py`（`reset_monthly_if_needed` / `check_budget` の定義）、
`backend/app/services/inventory_parser.py`（Step 1/Step 2 のコメントで手順を明文化）、
`backend/app/services/message_translator.py`（本変更で2箇所に追加）、
`backend/tests/test_llm_budget.py`（`TestResetMonthlyIfNeeded`）、
`backend/tests/test_message_translator.py`（本変更で追加した呼び出し順序 assert）。

## ADR 参照

- `docs/adr/ADR-110-sa-translation-subsystem.md` — 翻訳サブシステムの設計（`message_translator.py` の対象範囲）
- `docs/adr/ADR-072-tenant-schema-prefix-enforcement.md` — `reset_tenant_context()` 必須ルール。本変更は
  `public.tenant_llm_budgets`（テナント非分離の共有テーブル）への `UPDATE` のみで対象外（recon.md §「判断」参照）
- `docs/adr/ADR-1004-llm-usage-ledger.md` — LLM 利用量台帳。本変更は `current_month_usd` の集計元である
  usage ledger のロジックには触れていない（予算リセットのみ）
