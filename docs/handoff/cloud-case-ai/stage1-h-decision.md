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
