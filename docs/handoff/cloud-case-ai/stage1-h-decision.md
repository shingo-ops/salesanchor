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
