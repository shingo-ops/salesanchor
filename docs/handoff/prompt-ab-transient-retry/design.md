# prompt_ab: Gemini の一時的な失敗（503/429 等）を待ってやり直す — 設計・実装カード

対象ADR: ADR-1004（費用の台帳。変更しない）

状態: 設計案（Opus 作成 2026-10-27）。PO 承認: 2026-10-27 PO「1」（=「先に、混雑の返事が来たら少し待ってやり直す仕組みを試験の道具に足してから、最初から流し直す」）。

## 1. 目的（KGI）
比較試験の道具 `backend/app/tools/prompt_ab.py` が、Gemini の一時的な失敗 1 回で試験全体を止めないようにする。
- K1: 503 が 1 回返った後に成功する場合、その回は成功として JSONL に 1 行だけ書かれ、試験は続く（単体試験で○×）
- K2: 指定回数を超えて失敗し続けたら、今まで通り `stop_reason=job_failed` で止まる（単体試験で○×）
- K3: 一時的でない失敗（400 等・型の違う例外）は今まで通り 1 回で止まる（単体試験で○×）
- K4: オプションを付けないときの動きは今と同じ（既定 0 回＝やり直しなし。既存の単体試験が全部通る）
- K5: 費用の台帳は成功した 1 回分だけ（失敗した試みは台帳行を作らない＝今と同じ）

## 2. 現状（事実・origin/main）
- `backend/app/tools/prompt_ab.py:514-547` Gemini 呼び出しを try で包み、`except Exception` で failed+=1・stop_reason="job_failed"・JSONL に error 行・return。やり直しなし。
- `backend/app/services/gemini_raw_copy_v8.py:219-229` `client.models.generate_content` を 1 回呼び、例外は `RuntimeError(...) from exc` に包む（元の例外は `__cause__`）。
- 試験ログ（2026-10-27 01:40 JST）: 元の例外は `google.genai.errors.ServerError: 503 UNAVAILABLE`。
- 本番の解析経路（`backend/app/tasks/tcg_extraction.py:817-838` Celery max_retries=2, delay 30s）は今回触らない。
- `backend/app/services/gemini_extraction_svc.py:248-276` のクライアント生成も触らない（本番の解析経路に影響するため）。

## 3. 変更（prompt_ab.py と test_prompt_ab.py のみ）
1. 引数を 2 つ足す（`parse_args`、prompt_ab.py:584-604 付近）:
   - `--retry-transient N`（int、既定 0、0 以上。負なら argparse エラー）: 一時的な失敗のときのやり直し回数（初回を含まない）
   - `--retry-wait-sec S`（float、既定 30.0、0 より大きい）: 1 回目のやり直しまでの待ち。2 回目以降は前回の 2 倍（30→60→120）
   - `run_ab(...)` に同名の keyword 引数 `retry_transient: int = 0, retry_wait_sec: float = 30.0` を足し、`main` から渡す。docstring の「起動:」行にも足す。
2. 一時的な失敗の判定関数 `_is_transient_gemini_error(exc) -> bool` を足す:
   - `exc` から `__cause__` / `__context__` を最大 5 段たどり、`google.genai.errors.APIError` の実例で `getattr(e, "code", None)` が {408, 429, 500, 502, 503, 504} のどれかなら True。
   - それ以外（RuntimeError("job not found")、ValueError、400 等）は False。
   - import は `from google.genai import errors as genai_errors`（既に v8 が使う SDK。版は本番 requirements `google-genai>=1.0.0`）。
3. `run_ab` のループ（prompt_ab.py:514-547）で、**Gemini 呼び出し部分だけ**を内側でやり直す:
   - `load_extraction_context` と `_effective_supplier_context` は今まで通り 1 回（やり直しの外）。
   - 呼び出しが例外 → `_is_transient_gemini_error(exc)` が True かつ残り回数あり → `logger.warning("[prompt_ab] transient error, retry %d/%d in %.0fs: run=%s repeat=%d: %s", ...)` → `time.sleep(wait)` → wait*=2 → もう一度呼ぶ。
   - やり直し中は `summary.calls` を増やさない（1 回＝run×repeat の 1 組のまま）。JSONL は最終結果の 1 行だけ。
   - 成功した行に `"transient_retries": k`（k≥1 のときだけ）を足す。失敗で止まる行にも k≥1 なら同じ欄を足す。
   - 最後まで失敗 / 一時的でない失敗 → 今と同じ処理（rollback・failed+=1・job_failed・error 行・return）。
   - `elapsed_sec` は待ち時間を含めた初回開始からの経過（今の `started` のまま）。
4. 台帳（prompt_ab.py:557-569）は変えない。成功した 1 回分だけ書かれる。

## 4. 触らない範囲
- `backend/app/services/gemini_raw_copy_v8.py` / `backend/app/services/gemini_extraction_svc.py` / `backend/app/tasks/tcg_extraction.py` / 本番の解析経路すべて
- migrations / deploy.yml / scripts / frontend
- prompt_ab の他の動き（費用上限・ledger_missing・dry-run）

## 5. 試験（backend/tests/test_prompt_ab.py に追加）
既存の試験の作り（`call_gemini_raw_copy_v8` の差し替え方）に合わせる。`time.sleep` は monkeypatch で記録だけ。
| 基準 | 検証方法 |
|---|---|
| K1 | 1 回目に `RuntimeError from ServerError(503)`、2 回目に成功を返す偽物。`retry_transient=3` で succeeded==1・failed==0・JSONL 1 行・`transient_retries==1`・sleep が [30.0] |
| K2 | 4 回連続 503・`retry_transient=3` → stop_reason=="job_failed"・sleep が [30,60,120]・JSONL の error 行 1 行 |
| K3 | 400 の ClientError（`__cause__`）と、包まれていない ValueError → やり直しなし（sleep 呼ばれない）・job_failed |
| K4 | `retry_transient` 既定のまま 503 → sleep 呼ばれず job_failed。既存の試験は全部合格 |
| K5 | K1 で台帳書込（record_usage_event_sync の偽物）が 1 回だけ |
| 判定関数 | 429/500/502/503/504/408 → True、400/404 → False、`__cause__` 2 段の入れ子 → True |
ServerError/ClientError の作り方は、本番で入る google-genai の版で通る形にする（`errors.APIError(code, response_json)` の引数の形を、試験を書く前に CI と同じ環境で確かめ、確かめた方法を recon.md に書く）。

## 6. 反映と使い方
- PR は `release/prompt-ab-transient-retry`（origin/main 起点・worktree）。危険パスは含まない（ADR-135/136 の対象外）。
- 試験道具はコンテナのイメージの中で動くため、main へのマージ後の通常の反映でイメージに入るのを確認してから試験を流す（反映の確認方法: コンテナ内で `python -m app.tools.prompt_ab --help` に `--retry-transient` が出ること）。
- 試験の起動台本（PR 外・手元の試験フォルダ。リポジトリ外）に `--retry-transient 3 --retry-wait-sec 30` を足すのは Opus の別作業。

## 7. リスクと対処
- 待ちが長くなる: 最大 30+60+120=210 秒/組。20 分の見張りより短い。
- 失敗した試みに Google が課金するか: 【未確認】。台帳は成功分だけなので台帳上の二重計上はない。
- SDK の版で `APIError.code` が無い: `getattr(..., None)` で False（＝今と同じく止まる）側に倒れる。

## 8. 戻し方
PR を revert。既定 0 なので、オプションを付けなければ戻さなくても今と同じ動き。

## 外部・過去事例の参照と我々への応用
不要。理由: 既に使っている SDK 自身が 408/429/5xx を指数的な待ちでやり直す仕組みを持っている（google-genai 2.33.0 `types.HttpRetryOptions` の既定 attempts=5・initial_delay=1.0・exp_base=2.0、Sonnet 調査 retry_recon/sdk_HttpRetryOptions.txt）。本件はその考え方を、本番経路に触れずに試験道具の側だけで取るもの。

## 維持の仕組み
- 守り手: `backend/tests/test_prompt_ab.py`
- 既定 0 のため、オプションを付けない呼び出しは今と同じ動き。やり直しの判定と回数・待ちは backend/tests/test_prompt_ab.py の K1〜K5 試験で CI が毎回確かめる。
- 試験の起動台本でどの値を使ったかは、各試験の記録（Opus）に残す。

## 9. 審査（REVISE 1回目）の反映 — 以下が §3・§5・§6・§7 より優先する
- 置き場所: `docs/handoff/prompt-ab-transient-retry/design.md`（本カード全文）と `docs/handoff/prompt-ab-transient-retry/recon.md`（実装役が file:line で作る）。
- R1: やり直しの対象は prompt_ab.py:524-539 の `if config == "v7": ... else: call_gemini_raw_copy_v8(...)` の **if/else 全体**（v7 も `RuntimeError from exc` で包むので同じ判定が効く）。
- R2: `transient_retries` = 実際にやり直した回数 k（k≥1 のときだけ欄を書く）。K2 では error 行に `transient_retries == 3`。
- R3: parse_args の検査は既存の `if args.repeat < 1: p.error(...)` と同じ形で、`args.retry_transient < 0 or args.retry_transient > 5` → `p.error("--retry-transient は 0〜5")`、`args.retry_wait_sec <= 0` → `p.error("--retry-wait-sec は 0 より大きく")`。試験: 既定値 0 / 30.0、`-1`・`6`・`0`（wait）で SystemExit。
- R4: main → run_ab の配線試験を 1 つ足す（`pab.run_ab` を偽物に差し替えて kwargs に `retry_transient=3, retry_wait_sec=30.0` が渡ることを確認）。
- R5: N の上限は 5（最大の待ち合計 30+60+120+240+480=930 秒 < 20 分の見張り 1200 秒）。試験の運用は N=3（合計 210 秒）。
- R6: K1 は `_run` の前に `fakes.v8.side_effect` を「1 回目は例外を投げ、2 回目は `_v8_result()` を返す」**関数**にする（リスト・iterator は不可。`_run` が `count_v8` で包むため）。`run_ids=("r1",)` を渡して JSONL 1 行を確かめる。K2 は `v8_error=` に `__cause__` 付きの例外を渡す。
- R7: 例外の作り方の例: `e = RuntimeError("x"); e.__cause__ = genai_errors.ServerError(503, {"error": {"code": 503, "message": "m", "status": "UNAVAILABLE"}})`。`APIError.__init__(code, response_json, response=None)` の形が CI の google-genai 版で通ることを試験を書く前に確かめ、版と方法を recon.md に書く。
- R8: sleep は `monkeypatch.setattr(pab.time, "sleep", calls.append)`。K5 は `fakes.record.call_count == 1`（偽の台帳 rows は v8 の呼び出し回数なので ledger_missing の回帰はこの偽物では見られない、と試験に注記）。
- R9: 反映の確認は、deploy.yml の main 実行が success になったあと、`/home/ubuntu/salesanchor` で `docker compose run --rm --no-deps -T celery-worker python -m app.tools.prompt_ab --help | grep -- --retry-transient`（DB・Gemini に触る前に終わる）。無制限鍵が要るので Opus が PO の付与範囲で実行（Sonnet は実行しない）。
- §7 追記: 判定は google.genai の APIError だけ。httpx の接続エラー・タイムアウトは今まで通り 1 回で止まる。
