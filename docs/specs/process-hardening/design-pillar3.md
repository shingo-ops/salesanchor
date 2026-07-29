# 柱3-a/b design — テストスキーマ複製の検出

> この文書は何か（専門用語なしの1行）:
> テスト用ファイルが本番テーブル定義を新しくコピーしたら機械が気づいて止める、その作り方を決めた設計。

親: docs/specs/process-hardening/kgi.md（柱3節）
recon: docs/handoff/pillar3-test-schema-dup/recon.md
対象ADR: ADR-121

## 1. あるべき姿（親から）
テストが本番テーブル定義を各自コピーする状態を止め、コピーはこれ以上増やさない。既存の複製は段階的に減らす。本便は「増やさない検出（柱3-a/b）」を設計する。

## 2. 対象KGI（本便が満たすもの）
- 柱3-a: テストの独自CREATE TABLEの新規増加を機械が検出して止める。
- 柱3-b: 検出パターンが変種（IF NOT EXISTS有無・引用符違い・スキーマ接頭辞・記述形式4種）を取りこぼさない。
- 柱3-e: 欠落版・充足版のペアテストで実測（柱3-a/bの検証方法）。
（柱3-c 一覧固定・柱3-d 同伴警告は別便）

## 3. recon根拠（実測・固定SHA）
実測SHA: 2771fba288b30d2535f64bc2b5a1504e33e375ca / 186b6db0f90c9a32f25a9a1569f3e9160262ab61 / d62a3af18c008ca29a9d577bbac630bf127841b8（3点で同値）

- backend/tests 配下で CREATE TABLE を含むファイル: 32。
- 集約先 backend/tests/conftest.py を除いた独自複製: 31ファイル・89行。
- 誤検出の罠2ファイル（backend/tests/test_tenant_service.py=7行・backend/tests/test_inventory_parser_real_samples.py=3行）を除く: 29ファイル・79行。docs/handoff/pillar3-test-schema-dup/recon.md §4。
- AS構文（backend/tests/test_webhook_instagram.py の1件のみ・実測）を除く: 29ファイル・78行。
- 上記78行のうち7件はコメント行およびdocstring内の説明文である。本物のDDLは29ファイル・71件（AST実装の初回実測で確定・差7件は全件を内訳で説明済み）。
- 注: conftest.py の件数は 186b6db 時点64、d62a3af1 時点63。集約先のため基準に含めない。
- 旧版 scripts/check-test-schema-dup.js は execute(text( の1形式のみ検出し、他3形式を取りこぼす（同スクリプトの inExecuteBlock 判定）。

## 4. design（技術How）

### 4-1 置き場と実装言語
- 本体を Python で新設: scripts/check_test_schema_dup.py。旧 scripts/check-test-schema-dup.js は削除する。
- ペアテストも Python で新設: scripts/tests/test_check_test_schema_dup.py。旧 scripts/tests/test-check-test-schema-dup.js は削除する。
- CI: .github/workflows/test-schema-dup-gate.yml に actions/setup-python@v5 を追加し、実行を python3 に変更する。setup-node は本ジョブでは不要となるため削除する。
- 言語選定の根拠: 対象は Python ファイルであり、Python の文法を最も正確に読めるのは Python 自身の ast である。同リポジトリで actions/setup-python@v5 は10箇所の実績がある（実測）。

### 4-2 検出アルゴリズム（AST方式）
- 対象ファイルを Python の ast で構文木として読む。
- 文字列リテラル（ast.Constant の str）のみを走査対象とし、その中の CREATE TABLE を検出する。
- docstring（各スコープ先頭の文字列）と、ast.Assert の配下にある文字列リテラルは走査対象から除外する。
- f-string（ast.JoinedStr）は、定数部を連結し置換部を {expr} に置き換えて1本の文字列に再構成してから走査する。断片のまま走査するとテーブル名が切れる。
- 行単位の正規表現走査は用いない。旧方式が書き方の多様さに追随できないことは実測済み。
- 判定: 変更されたファイルごとに BASE と HEAD の検出数を比べ、HEAD > BASE なら赤。同数・減少は緑。

### 4-3 除外規則（確定・実装時の裁量を残さない）
- 集約先 backend/tests/conftest.py は対象外。
- 罠2ファイルはファイル名で除外する: backend/tests/test_tenant_service.py、backend/tests/test_inventory_parser_real_samples.py。
- 列定義を伴わない AS 構文（CREATE TABLE ... AS）は対象外とする。理由: 列を書き写していないため、本番の列追加が連鎖しない。実測1件は SQLite 上で同名の代用を張る用途であり、定義の書き写しではない。

### 4-4 検出すべき記述形式（4種・柱3-b）
1. 変数代入: 識別子 = 三連引用符の中に CREATE TABLE
2. execute と text が別行に分かれた多段記述
3. exec_driver_sql 経由
4. dbapi_conn.execute 経由
いずれも 4-2 の文字列リテラル走査で捕捉される。execute の書き方に依存しない。

## 5. 弊害・トレードオフ（空欄不可）
- CIワークフローとスクリプトの変更を伴うため危険変更に当たり、PO自筆GOを要する。
- 既存のペアテスト（63行・JavaScript）は言語が変わるため作り直しとなる。旧テストの資産は引き継がない。
- AS構文を対象外とするため、将来 AS 構文で本物の複製が増えても本ゲートは検出しない。列の書き写しではないため柱3の主目的（列追加の連鎖）には該当しないが、穴が残ることを明記する。
- テーブル名が変数で書かれている箇所は、名前が {expr} として記録される。実測2件（backend/tests/test_rls_invariants.py、backend/tests/test_rls_translation_glossary.py）。件数の計上には影響しないため柱3-a/b は成立するが、柱3-c の一覧では2件が名前不明となる。
- IF がテーブル名として混入した旧不具合の真因は未解明である。当該実装はリポジトリ・全履歴・一時領域のいずれにも存在せず、追跡不能と実測確定した。本設計はASTにより名前抽出の経路自体を変え、加えてペアテストで IF 混入ゼロを常時検査することで再発を防ぐ。

## 6. 外部・過去事例の参照と我々への応用
- scripts/check-dangling-routes.js（同リポジトリ）: BASE/HEADの集合差分で検出し、専用CIジョブと専用テストを同workflowで走らせる方式。本設計のジョブ構成はこれを踏襲する。
- 過去事例（本リポジトリ・2026-07-24）: 旧実装は自作の合成ケースのみで検証し実データの多様性を検証しなかったため、4形式中3形式を取りこぼした。本設計はこれを受け、受入基準に実データ全件検算を必須として組み込む。

## 7. 受入基準

| 基準 | 検証方法 |
|---|---|
| 基準値を再現する | 実データ全件走査で 29ファイル・71件 を出力し、grep基準78行との差7件を内訳で説明できる |
| テーブル名に IF が混入しない | ペアテストの real-if-zero が PASS（実データ全件でIF検出0件） |
| 4形式すべてを検出する | ペアテストの form1-assign / form2-multiline / form3-exec-driver / form4-dbapi が全て PASS |
| 罠で誤検出しない | ペアテストの trap-docstring / trap-assert / trap-comment が全て PASS |
| 罠2ファイルが走査対象外である | ペアテストの real-excluded 3件が全て PASS |
| 実データ全件で検算する | ペアテストの real-parse-failed が空（読めないファイル0件） |
| 新規複製を仕込んだPRで赤になる | ペアテストの pair-violation-exit1 が PASS（exit 1） |
| 既存の緑PRが赤化しない | ペアテストの pair-clean-exit0 が PASS（exit 0） |

## 8. 維持の仕組み
- 守り手: .github/workflows/test-schema-dup-gate.yml
- 対象: テストへの新規スキーマ複製が増えること
- 守り手（本設計docの改変防止）: .github/workflows/process-artifacts-gate.yml
- 補足: 本ゲートは現時点で必須チェックではない。必須化は安定確認後に別途PO GOで判断する。

## 9. 接触面分析（6面）
- 人: 実装役がテストにCREATE TABLEを足すとき赤で気づく。
- エージェント: 本設計docと docs/handoff/pillar3-test-schema-dup/recon.md が案内書。実装便のカードが従う。
- 機械: .github/workflows/test-schema-dup-gate.yml を書き換える。process-artifacts gate も通る。
- データ: 非接触（テストのスキーマ定義の話。本番DB tenant_004 非接触）。
- 本番: 非接触（CIのみ。deploy.yml に触れない）。
- 外部: 非接触。
