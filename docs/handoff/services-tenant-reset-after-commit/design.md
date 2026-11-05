<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# Phase 3 設計 — commit の後の会社付け直し漏れを見張りで止める（Rule C）

**対象ADR**: ADR-072（改訂 v3）  
**recon**: docs/handoff/services-tenant-reset-after-commit/recon.md  
**日付**: 2026-11-05  
**担当**: Planner（Opus）

---

## 0. 目的（PO の言葉と読み）

- PO（2026-11-05）:「1」＝前回の予定の不具合（commit の後に会社の付け直しを忘れ、Google に送られなかった）と同じ種類のミスを、今後は機械が自動で止める。見かけだけの当たり（誤検知）を出さない。マージと本番反映まで進める。
- 同じ種類のミスは二度と通さない（PO 恒久ルール 10/31）。

## 1. 外部・過去事例の参照と我々への応用

- 事例1（社内・直近）: 予定の作成・削除で commit の後に会社の付け直しが無く、設定表の RLS で行が見えず Google に送られなかった（docs/handoff/calendar-sync-tenant-reset/design.md・実 DB 試験で再現→直して緑・本番 K5 合格 2026-11-05）。→ 応用: 今回の規則 C は、この直す前のコード（d344d12ea^1 の calendar_service.py）を2か所とも当てることを合格条件に入れる（recon「試し2回目」で実測済み: 2件）。
- 事例2（社内・起源）: Issue #563 tenant_profile の commit 後の再 SELECT が "relation does not exist"（ADR-072 コンテキスト）。→ 応用: 会社名付きの表名（tenant_table_ref）は search_path の問題しか解かない。RLS のある表では付け直しが要る（recon「5〜9 を本物とした根拠」）。
- 外部資料: SQLAlchemy 2.0 公式 Session Basics（commit の後の次のトランザクションは新しい接続の払い出しで始まる）・Connection Pooling（use_lifo の既定は False）。→ 応用: 「commit の後は別の接続になりうる」を前提に、commit の直後に付け直す規則を全関数に課す。数値の外部事例は使わない（今回の効果は社内の実測で測れるため）。

## 2. 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| K1 直す前の予定のコードを規則 C が2か所とも当てる（create_event・delete_event） | `scripts/test_lint_tenant_schema.py` に直す前の形の試験を足し、CI の rule-registry の pytest が緑。加えて実装役が `git show d344d12ea^1:backend/app/services/calendar_service.py` を一時ファイルに出して lint を当て、`[Rule C]` が2行出る生出力を impl-report に貼る |
| K2 直した後の backend/app/ 全体で違反0件 | CI の必須チェック「ADR-072 tenant schema lint (strict mode)」が緑（対象が backend/app/ 全体になっていることを workflow の差分で確認） |
| K3 見かけだけの当たりが0件（別名で呼ぶ・URL の tenant_id・commit が最後）、決めた形どおりに当たる | 試験（合格の形）: 別名 `_reset_ctx`・URL の tenant_id の endpoint・commit が最後の文・try の中の commit の後に return だけ・if の中の commit の後に if の外で直後に reset・同期の def、の各形で `[Rule C]` が出ない。試験（違反の形）: commit の次が `if x: await reset_tenant_context(db, tenant_id)`・commit の次が db を使う with 文・router 以外の飾り付きで db と tenant_id を持つ関数、の各形で `[Rule C]` が出る。すべて pytest で確かめる。加えて直す前の main（32b39bd59）を backend/app/ に当てた `[Rule C]` が recon の6件と完全一致（行番号まで）することを impl-report に生出力で貼る |
| K4 Rule A・B の結果が変わらない | 実装役が直す前の main で `--mode warning backend/app/routers/` と、変更後の lint で `--mode warning backend/app/` を流し、`[Rule A]`・`[Rule B]` の行が同じ（どちらも0件）ことを生出力で impl-report に貼る |
| K5 6か所の付け直しが入る | `git diff origin/main` で6か所に `await reset_tenant_context(db, tenant_id)` が commit の直後の行として入っている。Reviewer が差分で確認 |
| K6 見張りが services など routers の外の変更でも走る | workflow の changes の正規表現が `^(backend/app/|scripts/lint_tenant_schema\.py|\.github/workflows/lint-tenant-schema\.yml)` になっている。本 PR の CI で必須チェックが skip でなく実行されたこと（ログに "ADR-072 lint: OK" が出る）を Opus が `gh run view --log` の生出力で確認 |
| K7 既存の試験・見本を壊さない | CI の必須チェックがすべて緑（rule-registry の pytest・run_rule_fixtures を含む） |
| K8 本番反映後も動く（付け直しは SET を3つ打つだけ） | 本番反映後、Opus が deploy の成功と /health を確認。手数料の割当・会社情報の保存は PO 目視なし（害が無い変更のため。下の「未確認」を参照） |

## 3. 技術 How・KPI

- KPI: (1) 直す前の予定のコードに対する当たり 2/2。(2) 今の backend/app/ に対する当たりが recon の6件と一致（見かけだけ0件）。(3) 直した後 0件。(4) 見張りの対象のフォルダ: routers だけ → backend/app/ 全体。
- 技術選択: 既存の `scripts/lint_tenant_schema.py`（ast・必須チェック配線済み）に Rule C を足す。新しい見張りの仕組みは作らない（理由: 配線・必須チェック・見本・規則台帳がすでにある。分散させない）。

### 3-1. 規則 C の定義（recon の試し2回目と同じ。実測で6件・2件を確認済み）

対象の関数（`ast.AsyncFunctionDef` だけ。入れ子も含む。同期の `def` は対象外）:
- (a) 既存の `_is_router_endpoint(func)`（`scripts/lint_tenant_schema.py:102-116`、`@router.get|post|put|patch|delete(...)` だけを endpoint と見る）の1つ目が True のもの: 既存の `_has_tenant_id_dep(func)` が True のときだけ（tenant_id が `Depends(get_current_tenant)`）。
- (b) (a) に入らないもの（他の飾りの有無は問わない。`@router.websocket` なども含む）: 引数（args と kwonlyargs）の名前に `db` と `tenant_id` の両方があるとき。

判定:
1. 関数の中の、式文 `await db.commit()`（`ast.Expr(ast.Await(ast.Call(func=ast.Attribute(value=ast.Name('db'), attr='commit'))))`）ごとに、その後に実行されうる文を順にたどる。たどり方: 同じブロックの後ろ → 尽きたら親へ。try の本体なら orelse → finalbody → try の後ろ。except・else の中なら finalbody → try の後ろ。if・for・while・with・async with の中ならその文の後ろ。関数の本体の終わりで止める。入れ子の関数・クラスの中にはもぐらない。
2. 複合文（if・for・while・with・async with・try・match）は、たどる途中では**中にもぐらず文全体を1つの文**として見る。「`db` を含む」は、その文の ast の木のどこかに名前 `db`（`ast.Name(id='db')`）があること。
3. 名前 `db` を含む最初の文が「`await <名前>(db, ...)` だけの式文」で、<名前> が `reset_tenant_context`・`set_tenant_context`、またはそのファイルの `from app.auth.dependencies import reset_tenant_context as X`（set_tenant_context も同じ）の X なら合格。
4. `db` を含む別の文に先に着いたら違反。2 により、commit の次が `if x: await reset_tenant_context(db, tenant_id)` のような**条件付きの付け直しは違反**（付け直しは条件なしで直後に置く。ADR-072 §4 の「直後」）。`db` を含む文に着かずに終わる、または `db` を含まない return・raise で止まったら合格。
5. 件数が recon の6件・2件と1件でも違えば、実装役は直さずに止めて Opus に生出力を返す（試し2回目の判定器の原本は手元に無く、この定義が正本）。
6. 出力: `Violation(file, commit の行, 関数名, "C", "await db.commit() の後、db を使う前に reset_tenant_context(db, tenant_id) がない（:<違反の文の行>で db を使用）")`。

### 3-2. 対象のフォルダの分け方

- Rule A・B は今と同じく `@router` の endpoint だけ（中身は変えない）。
- Rule C は渡されたフォルダのすべての .py。
- 配線の引数を `backend/app/routers/` → `backend/app/` に変える（3か所: workflow の run、`scripts/dev/check-before-submit.sh:211`、見本2件の argv）。main() の既定値と help の文も `backend/app` にする。
- workflow の changes の正規表現（`.github/workflows/lint-tenant-schema.yml:53`）の `backend/app/routers/` を `backend/app/` にする。
- 説明文も今の事実に合わせる: `scripts/lint_tenant_schema.py:2-18`（検出ルールに Rule C を足す・Usage の例を `backend/app/` に）、`.github/workflows/lint-tenant-schema.yml:5-10`（検出ルールに Rule C を足す）、`Violation.rule` の注釈（"A" / "B" / "C" / "SYNTAX"）。
- `scripts/test_lint_tenant_schema.py:137-146` の試験の説明文は「endpoint と認識しない（Rule A・B）。Rule C の対象だが commit が最後なので違反なし」に直す（中身・assert は変えない）。
- 変えないもの: `.github/PULL_REQUEST_TEMPLATE.md:57-59`（routers の write endpoint 向けの点検項目で、今も正しい。Rule C の範囲は機械が見るので人の点検項目は増やさない）。`.github/workflows/workflow-lint.yml` は触らない。
- 順番の条件: argv を `backend/app/` に変えると、見本の pass 側（`scripts/tests/run_rule_fixtures.py:169` は HEAD の写しで argv を流す）が backend/app/ 全体を見る。よって **6か所の直しと argv・既定値の変更は同じ commit に入れる**（途中の commit で pass の見本が落ちる形を作らない）。

### 3-3. 6か所の直し（すべて commit の直後に1行）

| 場所（origin/main 32b39bd59） | 変更前 | 変更後 |
|---|---|---|
| `backend/app/routers/leads.py:712` | `await db.commit()` の次が `await invalidate_dashboard_cache(tenant_id)` | 間に `await reset_tenant_context(db, tenant_id)` を足す（import 済み :28-34） |
| `backend/app/routers/order_commissions.py:322` | `await db.commit()` の後 :324 で読み直し | 直後に1行足す |
| `backend/app/routers/order_commissions.py:385` | 同上 :387 | 直後に1行足す |
| `backend/app/routers/order_commissions.py:472` | 同上 :474 | 直後に1行足す |
| `backend/app/routers/orders.py:440` | 次の行 :441 が return の中で読む | 間に1行足す（import 済み :29-34） |
| `backend/app/routers/tenant_profile.py:141` | :143 で読み直し | 直後に1行足す |

- import の追加: `backend/app/routers/order_commissions.py:36-41` と `backend/app/routers/tenant_profile.py:34-39` の `from app.auth.dependencies import (...)` に `reset_tenant_context,` を足す（並びは今の書き方に合わせて英字順）。
- 直し方の案内文の誤りも直す: `scripts/lint_tenant_schema.py` の「[Rule B 修正方法]」の `from app.database import reset_tenant_context` は誤り（定義は `backend/app/auth/dependencies.py:339`）。`from app.auth.dependencies import reset_tenant_context` にし、Rule C の違反にも同じ案内を出す。

### 3-4. 見本と台帳

- 見本を2件足す: `scripts/tests/rule-fixtures/tenant-schema/fail-service-commit-without-reset/`（routers の外 `backend/app/services/zz_fixture_service.py.fixture` に飾りの無い関数・commit の後に db を使う → `expect: fail`・`expect_output: "[Rule C]"`・`rules: ["K01"]`）と `pass-service-commit-with-reset/`（同じ形で直後に reset → `expect: pass`）。既存2件の argv を `backend/app/` にする。
- 規則台帳 `docs/specs/rule-enforcement/rules.yml` の K01 の reason を今の事実に書き換える（kind は review のまま。理由: for 文の中で commit し次の回の頭で db を使う形は見ない＝止まらない部分が残る）。新しい reason の要点: 見張りは backend/app/ 全体の commit の後を Rule C で見る／止まらない部分は「ループの次の回」「db 以外の名前の session」／検査は backend/app/ を変えた PR で走る。
- 改訂の記録: `docs/adr/ADR-072-tenant-schema-prefix-enforcement.md` に v3 を足す（§4 に「3. 案 C 違反（Rule C）: 会社名付きの表名を使っていても、RLS のある表では commit の後の付け直しが要る。routers の外も対象」、変更履歴に v3 の行）。足した後 `node scripts/generate-adr-index.js` を流し `docs/adr/README.md` を一緒に commit する。
- 決まりの文 `backend/AGENTS.md:10` は見出しの `**ADR-072 write endpoint**` だけを `**ADR-072 commit の後に db を使う関数（routers の外も）**` に直す。後ろの「`db.commit()` 直後に `reset_tenant_context()` 必須」は rules.yml K01 の anchor なので1字も変えない。

## 4. 弊害・トレードオフ

- 見張りの対象が backend/app/ 全体になり、routers の外の変更でも必須チェックが走る → 対策: 走る時間は ast の解析だけ（試しで backend/app/ 全体を数秒で処理）。workflow の timeout 5分は変えない。
- これから services に commit の後で db を使う関数を書くと止まる → 意図どおり。案内文に直し方1行を出す。
- 止まりすぎる形（誤検知になりうる形）: 付け直しを別の自作の関数に包んで呼ぶ・条件付きで付け直す・会社の設定を入れない管理用の関数が db と tenant_id の名前の引数を持つ。→ 今の backend/app/ では該当0件（K3 の6件一致で確かめる）。将来出たら、付け直しを直後に条件なしで置く形に直す（例外の印は作らない）。
- 止まらない部分が残る（ループの次の回・`db` 以外の名前の session・同期の def・引数に tenant_id が無い関数・commit を `await db.commit()` 以外の書き方で呼ぶ形）→ 対策: 台帳 K01 を kind: review のまま残し、reason に書く。直す前の予定の不具合の形（直線の流れ）は止まる。
- 6か所の付け直しは SET を3つ打つだけ。SQLite の試験では何もしない（`backend/app/auth/dependencies.py:293-294`）→ 既存の試験の挙動は変わらない。
- 5か所（leads・手数料3・注文明細）が本番で実際に空の応答や 500 を出したかは未確認。実 DB で再現する試験は今回作らない（理由: 同じ形の予定の不具合は実 DB 試験で再現済みで、本番の表の RLS が有効なことも確認済み。直しは害が無い1行）。

## 5. 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | 本書と recon をクラウドの設計審査役に審査させ APPROVE まで直す | Opus（審査はクラウド） |
| 2 | 実装カード（本書 3 章）で実装・push（`release/services-tenant-reset-after-commit`）。試験は Mac で回さない。CI で見る | クラウド Sonnet |
| 3 | Draft PR（shingo-cc）→ CI 緑 → K1〜K7 を生出力で確認 | Opus |
| 4 | マージ前の審査役（reviewer・opus・新規起動）APPROVE → 委任 GO 記録 → 確認済みコメント → 別の応答でマージ | Opus |

- GO 記録が要る理由（`scripts/check-process-artifacts.js` の実物）: `^scripts/` を含む（:1026）・`docs/specs/rule-enforcement/rules.yml` を含む（:1037）・`backend/app/routers` を含む（:1055・:1858-1865）。`.github/workflows/lint-tenant-schema.yml` は危険扱いではない（:1049）。PO 本人の GO が要るのは `.github/workflows/workflow-lint.yml` だけ（:51-53）で、本件は触らないため委任 GO（名義「POの委任に基づくClaude Opus発行」・:43）で足りる。
| 5 | deploy の成功・/health を確認（K8）。台帳・覚え書きを更新 | Opus |

## 6. 継続

- 完了後の監視: 必須チェック「ADR-072 tenant schema lint (strict mode)」が backend/app/ の変更で毎回走る（K6）。push 前の自動確認 `scripts/dev/check-before-submit.sh` でも同じ命令が走る。見本4件が規則の効き目を毎回確かめる（rule-registry の pytest と run_rule_fixtures）。
- 維持する担当・仕組み: 規則台帳 K01（reason に止まらない部分を記録）・ADR-072 v3。
- 次フェーズへの引き継ぎ: ループの次の回の形を止めるかは、同じ形の不具合が出たときに判断する（今は該当0件）。

## 7. 未確認

- 5か所が本番で実際に失敗した回数（本番の記録は見ていない）。
- 公式資料は commit の後に必ず別の接続になるとは書いていない（なりうる、まで）。
