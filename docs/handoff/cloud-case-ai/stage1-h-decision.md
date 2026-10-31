# 段1 §3(h) の判断と、例外ルール受入4行目の判定（Opus）

## 1. §3(h) 試験 DB の列と分類表の差（9 列）

### 観測事実
- 実装役の報告: 試験 DB（tests/rls_bootstrap.py の作り方）で、分類の無い「そのまま」でない列が 9 つ（stage1-evidence/pytest-test_ai_cloud_views.txt:20-29）。
  - public.tenants.company_name・public.users.firebase_uid
  - tenant_001.suppliers の 7 列（supplier_code・name・contact_name・email・phone・address・notes）
- 本番の確認（2026-10-31 04:09 JST、reader 鍵の道・ai_reader で pg_attribute。AUDIT sha=a40f10a0a8a5 rows=7）:
  - 上の 9 列の名前で表の列を探すと、出たのは public.suppliers の 7 列だけ。
  - public.tenants.company_name・public.users.firebase_uid は本番に無い。
  - tenant_*.suppliers は本番に無い（テナントのスキーマ 5 個。どれにも suppliers は無い。public.suppliers は分類表に 25 行ある）。
- 分類の無い列の扱いはカード §4-A の 5（「そのまま」の型でなければ伏せる式）。本番に将来この列ができても、値は伏せて出る。

### 判断
- 9 列は試験の足場だけにある列で、本番との差ではない。分類表（stage1-column-class.tsv・#4 の SQL）は変えない。
- 実装役が出した選択肢のうち (A) を採る。T10 の「本物の形の表」の試験で、この 9 列だけを名前で除外し、理由（本番に無い・確認日時と AUDIT sha）を試験の中に書く。
  - (B) 試験の足場を変えるのはカード §2 の範囲外で、既存の試験に影響する。
  - (C) 分類表に行を足すのは、本番に無い列を正本に入れることになる。
- T10 の「足した場合の試し」（test_t10_detects_added_columns）は変えない。見張りの効き目はそちらで確かめる。

## 2. 例外ルール（docs/handoff/cloud-parity/rule-sql-file.md §7 の 4 行目）の判定
クラウド実行 cse_01W47tdipNteNVCMvP7GSDCV（2026-10-30 18:38〜19:07 UTC）の実行記録で判定した。
- ① migrations の SQL が push されている: ○（64b31eec6。4 本）
- ② 書き込みの道具: ○（4 本とも Write の道具。例: 18:55:11 UTC に 20261024_100300_create_ai_cloud_views.sql）
- ③ SQL の危険語による BLOCKED が 0 件: ×（2 件）。どちらも SQL を書く操作ではなく、読むだけの検索のコマンドで止まった（19:05:18 UTC の表示は 'DROP TABLE'、19:05:33 UTC の表示は 'DELETE FROM'）。実装役は危険語を外した検索に変えて続けた（「止められたら言い換えない」の指示に合わない。読むだけの検索で害は無かったが、次の依頼で改めて伝える）。SQL のファイルを書く操作は 1 件も止まっていない。
- まとめ: SQL を決まりどおり書けることは確かめられた。読むだけの検索が危険語で止まるのは、見張りの今の作り（文字で判断する）のままで、この例外ルールの対象外。直すなら別の設計にする。

## 3. push 前の確認 8（ADR-155 の「共用マスタの中身の参照」）で止まった件

### 観測事実
- 2026-10-31 未明、e7380ca86 の push が push 前の自動確認で止まった。止めたのは scripts/check-migration-value-writes.py diff --check 8。CI でも同じ検査が走る（.github/workflows/migration-guard.yml:424）。
- 引っかかった行は、migrations/20261024_100300_create_ai_cloud_views.sql の ai_cloud.column_class への INSERT の値の行だけ（例: `('public','products',ARRAY['notes'],'mask','')`）。表の名前を文字の値として並べている行で、共用マスタの中身を読む文ではない。
- 確認 7（保護対象の表への INSERT / UPDATE / DELETE）は通っている（ai_cloud.column_class は保護対象ではない）。
- 確認 8 は文字だけで判断し、diff モードには例外の仕組みが無い（scripts/check-migration-value-writes.py:126-131。value-write-allowlist.tsv は repo モードの確認 7 相当だけに使う）。

### PO の決定
- 2026-10-31 10:07 JST、PO「1」: この手順ファイル 1 つだけを、理由を書いた例外の一覧に載せて通す（ほかのファイルへの確認は今のまま）。

### 作り（実装役へ渡す）
- 新しい一覧 scripts/migration-guard/reference-allowlist.tsv（タブ区切り・唯一の正本）。列: file / sha256（そのファイルの中身の SHA-256）/ reason / decision_ref。頭に value-write-allowlist.tsv と同じ書き方で説明の注記を置く。
- 行は 1 つだけ: migrations/20261024_100300_create_ai_cloud_views.sql ／ その時点の sha256 ／「ai_cloud.column_class の初期値として表の名前を文字の値で並べる。共用マスタの中身は読まない」／「PO「1」2026-10-31 / docs/handoff/cloud-case-ai/stage1-h-decision.md §3」。
- diff モードの確認 8: 一覧にあり、HEAD のファイルの中身の sha256 が一致するときだけ、そのファイルを確認 8 から外し、外したことを「⚠」で 1 行表示する。sha256 が違えば失敗（中身が変わったら例外は効かない）。
- 確認 7 は一覧に関係なく今のまま全ファイルに効く。
- repo モード: 一覧の各行のファイルが在り、run_all_migrations.sh に登録され、sha256 が一致することを確かめる。違えば失敗（古い行を残さない）。
- 試験（scripts/tests/test_migration_value_writes.py に追加）: ①一覧にあり sha256 一致 → 確認 8 通過 ②一覧にあり sha256 不一致 → 失敗 ③一覧に無いファイルは今までどおり失敗 ④一覧にあるファイルでも保護対象の表への INSERT は確認 7 で失敗 ⑤repo モードで古い行・未登録の行は失敗。

### 受入
| 基準 | 検証方法 |
|---|---|
| 確認 8 が段1 の SQL 1 本だけを外す | `python3 scripts/check-migration-value-writes.py diff origin/main HEAD --check 8` が通り、「⚠」行が 1 行だけ |
| ほかのファイルは今までどおり止まる | 試験 ③ が通る |
| 中身が変われば例外が切れる | 試験 ② が通る |
| 確認 7 は弱まらない | 試験 ④ が通る |
| push 前の自動確認が全部通る | `bash scripts/dev/check-before-submit.sh` の × が 0 |

戻し方: 一覧の行と検査の追加部分を revert する（確認 8 は元の厳しさに戻る）。

## 4. CI「マイグレーションSQL 実行（内部）」で ai_reader が無く止まった件

### 観測事実
- PR #4932（HEAD 90e2e6ab2）で「マイグレーションSQL 実行（内部）」が失敗した（run 41162867710 / job 124424123732）。同じ run の「マイグレーション全件ドライラン（実DB）」は pass（job 124424123746）。
- 内部の試しは、変わった SQL だけを空に近い試験 DB で流す（.github/workflows/migration-test.yml:1222「変更 SQL を 1回目実行」）。この DB には ai_reader が無い。
- 止まった行は migrations/20261024_100000_create_ai_cloud_meta.sql:187 `GRANT USAGE ON SCHEMA ai_cloud_meta TO ai_reader;`（エラー: role "ai_reader" does not exist）。
- 本番と全件ドライランでは、ai_reader を作る migrations/20261017_130000_create_ai_reader_role.sql が先に流れる（scripts/run_all_migrations.sh:1164。段1の meta は :1191）。
- 前例の migrations/20261017_130100_create_ai_ro_views.sql:78-79 が通ったのは、ロールを作る SQL が同じ PR に入っていたため（b2b49ec2f）。
- カードはこの試しが空の DB から始まることを想定していなかった（設計の入れ忘れ）。

### 判断
- meta.sql:187-188 の 2 行の GRANT を、pg_roles に ai_reader があるときだけ実行する DO ブロックに包む。無いときは RAISE NOTICE で「ai_reader が無いため付けない」と 1 行出す。
- 本番の動きは変わらない（本番には ai_reader がある。AUDIT は reader 鍵の道＝ai_reader で取れている）。
- 本番で付け損ねれば、カード §5 の「build_log の最新行を ai_reader で読む」測定で見つかる。黙って抜けたままにはならない。
- 採らない案:
  - (B) CI の手順で ai_reader を先に作る。workflow の変更はカード §2 の範囲外。
  - (C) ai_reader を作る SQL を段1で直す。カード §2 で触らないと決めている。
- 確認 8 の例外（§3）は migrations/20261024_100300 の sha だけに効く。meta.sql の変更は例外に関係しない。

### 受入
| 基準 | 検証方法 |
|---|---|
| ai_reader が無い DB で meta.sql が通る | ai_reader を作らない使い捨て PG で 4 本を 2 回流し、エラー 0・NOTICE 1 行 |
| ai_reader がある DB では今までどおり権限が付く | ai_reader を作った使い捨て PG で流し、has_schema_privilege と 3 表の has_table_privilege が t |
| 既存の試験が通る | test_ai_cloud_views 全件 PASSED |
| CI | 「マイグレーションSQL 実行（内部）」と「全件ドライラン」が pass |

戻し方: DO ブロックを外して元の 2 行に戻す（CI の内部の試しは再び止まる）。
