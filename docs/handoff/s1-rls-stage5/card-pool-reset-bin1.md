---
mode: handoff
---
# 実装カード 便1: commit・rollback の後に会社の文脈を張り直す（6 起点・8 か所）

親: [design-pool-reset.md](./design-pool-reset.md) §3（便1 の行）・§4-1・§5（便1 の行）・§6・§7 R5。ADR: [ADR-1070](../../adr/ADR-1070-pool-reset-on-return.md) What 3。

- 状態: カード作成済み（2026-11-07 Opus）。1 回目のクラウド実行（2026-11-07 10:05Z）は手順4で止まった。クラウドの環境に sqlalchemy と pytest が無かったため。依存を入れる手順 2-2 を入れ忘れたのが原因で、2-2 を足した。手順9に各箇所の前後3行の diff を足した。2 回目（10:09Z）は手順2-2 で止まった。素の pip install をリポジトリの見張り py312-guard が止めたため。3.12 の venv を作る手順を書き忘れたのが原因で、2-2 を venv `/tmp/v312` を作って使う形に直し、手順4・6・7 もその python で流す形にした（直した命令は見張りに通ることを手元で確かめた）。
- 実装承認: PO 2026-11-07「1」（S1 段階⑤の前に、接続の返却時に文脈を消す仕組みを 2 便で先に出す選択）と、同日の PO の指示「PRマージ、デプロイまで完走させてくれ」。設計は 3 回目の審査で APPROVE（review-design-pool-reset-r3.md）。マージと本番への反映の GO は兼ねない（Opus が委任に基づき別に出す）。
- 担当: クラウドの Sonnet（実装）。Opus は審査・PR 作成・GO・マージ判断。
- 区分: A（`backend/app/routers/`・`backend/app/services/`・`backend/app/discord_gateway/` を触る。ADR-1015）。migrations・deploy.yml・scripts・.github は触らない。
- 作業する枝: `release/s1-rls-pool-reset-bin1`（Opus が origin/main から作り、このカードだけを載せて push 済み）。新しい枝は作らない。

## 0. カード発行前チェック（docs/ai-agents/design-partner.md §5.5 の照合結果）

| 番号 | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲む | ○ |
| 2 | PR は Opus が ready で作る（担当は PR を作らない） | ○（§6） |
| 3 | 報告の宛先（完了報告の本文に生出力を全文） | ○（§7） |
| 4 | 1便1目的（reset を足すだけ。Bx 本体は便2） | ○ |
| 5 | 既存の枝の起点を明示（origin/release/s1-rls-pool-reset-bin1） | ○（§5 手順1） |
| 6 | 書式は実例で示す（足す1行の良い例と禁止形） | ○（§3） |
| 7 | 合格基準を出力まで縛る（main との差分に削除が 0・触るファイル以外 0） | ○（§5 手順9・10） |
| 8 | 件数の判定には名前を出す手順を対で置く | ○（§5 手順9・10） |
| 9 | 出力量に上限のないコマンドを使わない | ○（`| tail -N`・`--name-only`） |
| 10 | 報告様式3点（停止の3点・受領と終端の合図・冒頭の便名） | ○（§7） |
| 11 | 行番号を停止条件にしない（前後の文で探す） | ○（§3） |
| 12 | 停止は不可逆・本番影響のものだけ。数の食い違いは記録して続行 | ○（§4） |
| 13 | 委任文の定型4点（sleep 禁止・Write/Edit で書く・PR は作らない・フックに止められたら言い換えない） | ○（§4） |

読んだ節（docs/handoff/design-partner-card-ops/guards/）: 00-common.md・04-worktree.md・05-pr.md。

基準: 設計の基準 origin/main 170ff9612。2026-11-07 に origin/main ce2815fd6 と比べ、§2 の 7 ファイルの差分は 0 行（`git diff --stat 170ff9612 origin/main -- <7 ファイル>` が空）。設計文書の合流後の origin/main 37fa04f7b でも backend/ の差分は 0 行（`git diff --stat ce2815fd6 37fa04f7b -- backend/` が空）。行番号は目印で、ずれていたら前後の文で探す。

## 1. 目的（便1 で起きること）

- 利用者に見える変化は無い。今は commit の後も前の要求の会社の文脈が接続に残っていて、同じ会社の値で偶然動いている。便1 はその偶然に頼らず、commit・rollback の直後に同じ会社の文脈を張り直す。
- 便2（接続を返すたびに文脈を消す）を入れたとき、ここの 8 か所が 0 行や例外にならないようにするための先行の直し。

## 2. 触るファイル（これ以外は触らない）

| ファイル | 何をする |
|---|---|
| `backend/app/discord_gateway/ticket_channel_writer.py` | 起点1: import に1語足す・reset を1行足す |
| `backend/app/services/message_translator.py` | 起点2: 関数の中の import と reset を足す |
| `backend/app/services/priority_scoring.py` | 起点3a・3b・3c: 関数の中の import と reset を足す（3 か所） |
| `backend/app/routers/tenant_commission_settings.py` | 起点4: reset を1行足す |
| `backend/app/routers/products.py` | 起点5: reset を1行足す |
| `backend/app/routers/webhook.py` | 起点7: reset を1行足す |
| `backend/tests/` の既存の試験 | §5 手順6 で赤になったものだけ、期待値を「commit・rollback の直後に reset が1回増える」に直す |

触らないもの: `backend/app/database.py`（Bx は便2）・`backend/app/auth/dependencies.py`・admin_engine・同期 engine・Celery の設定・設計 §4-2 と §4-3 の箇所（calendar_service.py・refresh_meta_tokens.py・verify_meta_subscriptions.py・data_deletion.py・notifications.py・tcg_distribution_svc.py・discord_role_sync.py・tcg_product_import.py・product_packagings.py・customer_priority.py）・ADR と設計の文書・migrations・deploy.yml・scripts・.github。

## 3. 直す 8 か所（design §4-1 が正。食い違えば design に従い、報告に書く）

足す行はどれも `await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2.5`。字下げは直前の `await db.commit()`／`await db.rollback()` と同じ。

- 良い例（直前の行と同じ字下げで、直後に1行）:
  ```
          await db.commit()
          await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2.5
  ```
- 禁止形: commit より前に置く／`set_tenant_context` を使う／`try:` で囲む／`if` の外に出す（起点3b）／別の引数名を作る。

| 起点 | ファイルと関数 | 目印（前後の文） | 足すもの |
|---|---|---|---|
| 1 | `backend/app/discord_gateway/ticket_channel_writer.py` の `process_ticket_channel_message` | `inserted_row = result.first()` の次の `await db.commit()` の直後、`if inserted_row is None:` の前 | reset の1行。先頭の `from app.auth.dependencies import set_tenant_context` を `from app.auth.dependencies import reset_tenant_context, set_tenant_context` に替える |
| 2 | `backend/app/services/message_translator.py` の `translate_inbound` | `await _save_translation(` の後の `await db.commit()` の直後、`logger.info(` と `"[translator] inbound done:` の前 | commit の直前に `from app.auth.dependencies import reset_tenant_context  # noqa: PLC0415`（関数の中。ファイル先頭には足さない）、commit の直後に reset の1行 |
| 3a | `backend/app/services/priority_scoring.py` の `calibrate_tenant_weights` | `"cold": is_cold_start,` を含む execute の後の `await db.commit()` の直後、`return weights` の前 | 起点2 と同じ形（関数の中の import・commit の直後に reset） |
| 3b | 同 `label_lead_messages` | `if saved > 0:` の中の `await db.commit()` の直後（`if` の中・同じ字下げ）、`return saved` の前 | 起点2 と同じ形。import も `if` の中の commit の直前に置く |
| 3c | 同 `_compute_and_persist` | `"now": now,` を含む execute の後の `await db.commit()` の直後、`return CustomerScoreResponse(` の前 | 起点2 と同じ形 |
| 4 | `backend/app/routers/tenant_commission_settings.py` の `_create_default` | `except Exception:` の直後の `await db.rollback()` の直後、`# 競合時は既存レコードを取得して返す` の前 | reset の1行（import は既にある） |
| 5 | `backend/app/routers/products.py` の `delete_product` | `except IntegrityError as exc:` の直後の `await db.rollback()` の直後、`logger.warning(` と `"delete_product IntegrityError fallback:` の前 | reset の1行（import は既にある） |
| 7 | `backend/app/routers/webhook.py` の `_create_outbound_lead_for_echo` | `"UPDATE leads SET lead_code = :code WHERE id = :id"` の execute の後の `await db.commit()` の直後、`return lead_id` の前 | reset の1行（import は既にある） |

- 各関数の中で、会社の番号を持つ変数の名前が `tenant_id` であることを目で確かめる（design: 起点2 は引数 :425、3a は :160、3b は :257、3c は :386、7 は :540）。名前が違えば、その関数の中の名前を使い、報告に書く。
- 関数の中の import の理由（design R6）: message_translator.py の先頭で app.auth.dependencies を読むと、読むだけで app.database も読まれる。scripts/lead_regression/generate.py からも読まれるので避ける。

## 4. 担当の決まり（定型）

1. sleep で待たない。CI の結果は待たずに報告して終える（Opus が見る）。
2. ファイルの編集は Edit／Write のツールで行う。ヒアドキュメントや sed で書き換えない。
3. PR は作らない（Opus が作る）。push までで終える。
4. フックや自動判定に止められたら、言い換えて再試行しない。止まった手順・最後のコマンド・理由の原文を報告に書いて終える。
5. 止まるのは次だけ: 削除・`--force` が要る push・main への push・本番への接続が要る場面・§2 以外のファイルを直さないと進めない場面。それ以外の数や行の食い違いは記録して続ける。
6. 秘密の値を画面にもファイルにも出さない。

## 5. 手順（1手順1コマンド。`<repo>` は担当の作業場所の絶対パス）

1. `cd <repo> && git fetch origin release/s1-rls-pool-reset-bin1 main` → `cd <repo> && git checkout -B release/s1-rls-pool-reset-bin1 origin/release/s1-rls-pool-reset-bin1`。`cd <repo> && git log --oneline -3` の出力を記録する。
2. `cd <repo> && git merge-base --is-ancestor origin/main HEAD; echo rc=$?` が `rc=0` であることを記録する（0 でなければ記録して続け、報告に書く）。
2-2. Python 3.12 の venv `/tmp/v312` を作り、依存を入れる（CI の .github/workflows/test.yml:166 と同じ組。リポジトリの見張り py312-guard は 3.12 以外の venv 作成と venv の外の pip install を止める）。次の 4 つを順に、1 つずつ流して出力を報告に書く。
   - (a) `python3.12 --version; echo rc=$?`。rc=0 なら (b1)、0 でなければ (b2) へ。
   - (b1) `python3.12 -m venv /tmp/v312; echo rc=$?`
   - (b2) `uv venv --python 3.12 /tmp/v312; echo rc=$?`。これも 0 でなければ、出力を報告に書いて BLOCKED で終える（まだ何も直していないので失うものは無い）。
   - (c) `/tmp/v312/bin/python --version` が `Python 3.12.` で始まること。違えば BLOCKED で終える。
   - (d) `cd <repo>/backend && /tmp/v312/bin/python -m pip install -q -r requirements.txt -r requirements-dev.txt > /tmp/v312-pip.txt 2>&1; echo rc=$?` と `tail -30 /tmp/v312-pip.txt`。rc=0 でなければ BLOCKED で終える。(b2) の uv で venv を作ったときだけ、(d) の代わりに `cd <repo>/backend && uv pip install --python /tmp/v312/bin/python -q -r requirements.txt -r requirements-dev.txt > /tmp/v312-pip.txt 2>&1; echo rc=$?` と `tail -30 /tmp/v312-pip.txt` を流す（uv の venv は版を `version_info` と書くため、見張りが 3.12 と読めず (d) を止める。CI も uv pip install で入れている）。
   - (e) `/tmp/v312/bin/python -m pip check 2>&1 | tail -20`（uv で作ったときは `uv pip check --python /tmp/v312/bin/python 2>&1 | tail -20`）。壊れの報告は記録して続ける。
   - 以後の手順の `python` はすべて `/tmp/v312/bin/python` で流す（手順4・6・7）。素の `python`・`pip`・`python3` は使わない。
3. §3 の 8 か所を Edit で直す。
4. `cd <repo>/backend && /tmp/v312/bin/python -c "import app.services.message_translator, app.services.priority_scoring, app.discord_gateway.ticket_channel_writer, app.routers.tenant_commission_settings, app.routers.products, app.routers.webhook; print('import ok')"` が `import ok` を出すこと（R5）。失敗したら出力の最後 40 行を報告に書く。
5. `cd <repo> && grep -n "reset_tenant_context" backend/app/discord_gateway/ticket_channel_writer.py backend/app/services/message_translator.py backend/app/services/priority_scoring.py backend/app/routers/tenant_commission_settings.py backend/app/routers/products.py backend/app/routers/webhook.py | tail -60` の全文を報告に書く。
6. 試験を流す。`cd <repo>/backend && timeout 300 /tmp/v312/bin/python -m pytest -q --no-cov -p no:cacheprovider tests/test_message_translator.py tests/test_message_translator_usage_ledger.py tests/test_ticket_channel_translation.py tests/test_customer_reply_notifier.py tests/test_lead_regression_generate.py tests/test_priority_scoring.py tests/test_priority_scoring_check.py tests/test_products.py tests/test_products_cross_tenant_fk.py tests/test_products_required_fields_pg.py tests/test_webhook_instagram.py 2>&1 | tail -40`。名前に `customer_priority`・`tenant_commission_settings` を含む試験があれば（`cd <repo> && ls backend/tests | grep -E "customer_priority|tenant_commission" | head -20`）それも足す。PostgreSQL が無くて skip になるものは skip のまま記録する。`timeout 300` で時間切れ（rc=124）になったら、同じ形で 1 ファイルずつ `timeout 150` で流し、止まったファイル名を報告に書いて続ける。背景に回さない。
   - db を MagicMock にした試験で、execute の回数・順番が変わって赤になったら、試験の期待値を「commit・rollback の直後に reset が1回増える」に直す。製品コードの直しを減らさない。直した試験はファイル名・試験名・直す前と後の期待値を報告に全部書く。
   - それ以外の理由の赤は直さずに記録し、出力の最後 80 行を報告に書いて続ける。
7. `cd <repo> && /tmp/v312/bin/python scripts/lint_tenant_schema.py --mode strict backend/app/ > /tmp/lint_tenant.txt 2>&1; echo rc=$?` と `tail -20 /tmp/lint_tenant.txt`（CI の .github/workflows/lint-tenant-schema.yml:71 と同じ呼び方） の出力を報告に書く（Rule C: commit の後の最初の文が reset か）。
8. `cd <repo> && git add backend/app/discord_gateway/ticket_channel_writer.py backend/app/services/message_translator.py backend/app/services/priority_scoring.py backend/app/routers/tenant_commission_settings.py backend/app/routers/products.py backend/app/routers/webhook.py`（手順6 で試験を直したら、そのファイルも名前で足す）。
9. `cd <repo> && git diff --cached --stat | tail -20` と `cd <repo> && git diff --cached -U3 | head -300` を報告に書く（後者は §7 の 3 の「前後3行」に使う）。合格: 変えたファイルが §2 の表のものだけ、各製品ファイルの deletions は起点1 の import 行の 1 だけ（ticket_channel_writer.py）で他は 0。違えば、違うファイル名と行を報告に書く。
10. commit: `cd <repo> && git commit -m "fix(s1-rls): reset tenant context after commit/rollback at 8 sites (ADR-1070 bin1)" -m "Co-Authored-By: Claude Sonnet <noreply@anthropic.com>"`。続けて `cd <repo> && git diff origin/main...HEAD --name-only | tail -30` を報告に書く。合格: `docs/handoff/s1-rls-stage5/card-pool-reset-bin1.md` と §2 のファイルだけ。
11. push: `cd <repo> && git push -u origin HEAD`。出力の全文を報告に書く。続けて `cd <repo> && git ls-remote origin release/s1-rls-pool-reset-bin1` と `cd <repo> && git rev-parse HEAD` を報告に書き、一致を確かめる。

## 6. PR

担当は作らない。Opus が push を確かめてから、`### 標準ワークフロー確認` と `### GO記録` を入れて作る。

## 7. 報告（完了報告の本文に、次をこの順で全部含める）

1. 冒頭の1行: 「本報告はカード 便1（card-pool-reset-bin1）の実行結果である」。続けて「受領: カード末尾の合図 END-OF-CARD-BIN1 まで読んだ」。
2. 手順1〜11 の各コマンドの生出力（省略しない。`tail` で切った範囲はそのまま）。
3. 直した 8 か所のそれぞれについて、ファイル・関数・足した行の前後3行（`git diff` の該当部分）。
4. 手順6 で直した試験があれば、その全部。
5. 止まった場合は「止まった手順の番号／最後に実行したコマンド／止まった理由の原文」。
6. 最後の行は `DONE`、`BLOCKED: <理由>`、`NEEDS_DECISION: <問い>` のどれか1つ。

END-OF-CARD-BIN1
