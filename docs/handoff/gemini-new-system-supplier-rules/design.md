# design: 新しい仕組みだけが読む仕入元ルールの欄を2つ足す

- 作成：2026-10-06 Opus（設計）
- PO の指示と承認（2026-10-06）
  - 「本番ではなく新しいシステムを書き換えてほしい」
  - 「この案（新しい仕組み専用の欄を2つ足す）で設計を始めてよいですか？」→「y」
- recon：docs/handoff/gemini-new-system-supplier-rules/recon.md（元資料：/tmp/CC報告ファイル/v102/newcols/recon_raw.md）
- 関係する ADR：ADR-027（i18n）、ADR-135・ADR-136（危険パスと GO）、ADR-144（UI ガバナンス）、ADR-100、ADR-1004
- 前の版：docs/handoff/gemini-supplier-rules-file/design.md、docs/handoff/gemini-prompt-e/design.md

## 1. 目的（KGI）
- 新しい仕組み（v8 以降の書き写し。指示書 e）だけが読むルールの置き場所を、データベースの suppliers 表に作る。中身は「指示書の手順への当てはめ」と「間違えやすい形の原文例と出力例」。
- 本番の仕組み（v7：gemini_extraction_svc の call_gemini_raw_copy と extract_message、shadow、shadow_backfill）の指示書は、1文字も変えない。
- 判定（○×）
  1. 本番 v7 の指示書（_build_supplier_context_note の出力）が、新しい2列に値があっても変わらない。テストで確かめる。
  2. 新しい仕組みの指示書（build_supplier_note_v8 の出力）には、新しい2列の値が決まった見出しで入る。テストで確かめる。
  3. 管理画面の仕入元ルールのページで、2列を見ること・直すことができる。部品は既存の Textarea（金型）を使い、文言は ja/en の両方に置く。
  4. CI がすべて緑。

## 2. 現在地（事実。行番号は recon.md）
- 仕入元ルールは public.suppliers の extraction_* の8列にある。本番 v7 も新しい仕組みも、tcg_extraction.py:230-296 の同じ SELECT（位置で読む。supplier_id は row[10]）から作られた supplier_context を読む。
- 本番 v7 の指示書を作る _build_supplier_context_note（gemini_extraction_svc.py:313-343）が読むのは7つの鍵だけ。dict に新しい鍵を足しても、そこに書き足さない限り v7 の指示書には入らない。ship_format で同じ性質をテストしている（test_tcg_gemini_extraction.py:819-879）。
- tcg_extraction.py:273-274 は、「どれかの欄に値があれば supplier_context を作る」。新しい列をこの判定に含めると、新しい列だけを持つ仕入元の supplier_context が None から非 None に変わる。
- 新しい仕組みの指示書は build_supplier_note_v8・build_prompt_v8（gemini_raw_copy_v8.py:94-117）で作られる。呼び出しは prompt_ab.py だけで、本番からは呼ばれない。
- suppliers に ORM のモデルは無い（生の SQL）。migration は `scripts/run_all_migrations.sh` に登録する（deploy.yml:205）。
- 8列を並べている箇所が API に5か所ある（central_masters.py:393-416、super_admin_suppliers.py:604-608, 610-619, 716-727, 767-777）。openapi.json は `python -m tools.export_openapi` で作り直し、api-contract-check.yml が差分を確かめる。
- 画面は SupplierExtractionRulesPage.tsx（欄の並びは :37-48, 77-97, 99-110, 421-430、描画は :774-805 の Textarea）。文言は supplierExtractionRules 名前空間にある。
- 試しの結果（手元：/tmp/CC報告ファイル/v102/rules/）
  - 指示書 e＋佐々木さんの新しい形のルールで、試験A は 2/25 から 0/25 になった。
  - 中村さんの分は、e だけで 30/30 だった。
  - 新しい形で精度が下がった例は無い。

## 3. 変更
### 3-1. migration（危険パス）
- `migrations/20261006_170200_add_supplier_new_system_rules.sql`
  - `ALTER TABLE public.suppliers ADD COLUMN IF NOT EXISTS extraction_layout_rules TEXT;`
  - `ALTER TABLE public.suppliers ADD COLUMN IF NOT EXISTS extraction_hard_cases TEXT;`
  - 既存の行の値は書かない（NULL のまま）。
  - 戻すとき：`ALTER TABLE public.suppliers DROP COLUMN IF EXISTS ...` を別の migration で行う。DROP は PO の確認が要る。
- `scripts/run_all_migrations.sh` に run_sql の1行を足す。

### 3-2. 読み込み（tcg_extraction.py）
- SELECT の**最後**（supplier_id の後ろ）に2列を足す。row[11]、row[12] で読み、supplier_id の row[10] は変えない。
- dict（extraction_rules）に extraction_layout_rules と extraction_hard_cases の鍵を足す。
- 「supplier_context を作るかどうか」（:273-274）の判定には、新しい2列を**含めない**。今までどおり8列だけで決める。これで本番 v7 の supplier_context が None になる条件は変わらない。
  - 新しい列にだけ値がある仕入元では、supplier_context は None のままになり、新しい仕組みにもルールが渡らない。
  - そこで、新しい仕組みには別の鍵で渡す。ExtractionContext に `new_system_rules: dict | None` を足し（既定は None）、2列のどちらかに値があれば入れる。
  - supplier_context には新しい鍵を入れない。本番 v7 に渡る dict は1文字も変わらない。

### 3-3. 新しい仕組みの指示書（gemini_raw_copy_v8.py）
- build_prompt_v8 と call_gemini_raw_copy_v8 に、引数 `new_system_rules: dict | None = None` を足す。
- 値があるとき、仕入元ルールの部分（note）の後ろ、「原文:」の前に、次の形で入れる。空の欄の見出しは出さない。
```
# この仕入元の書き方（指示書の手順への当てはめ）
{extraction_layout_rules}

# この仕入元で間違えやすい形
{extraction_hard_cases}
```
- 値が無いときは、今と1文字も違わない指示書にする。

### 3-4. prompt_ab.py
- ctx.new_system_rules を build_prompt_v8・call_gemini_raw_copy_v8 に渡す（v8 系の config だけ。v7 には渡さない）。
- `--supplier-rules-file` で extraction_layout_rules と extraction_hard_cases を指定したときは、new_system_rules 側を上書きする。null は外す。ほかの欄は今までどおり supplier_context を上書きする。
- JSONL の supplier_rules_override の fields に、上書きした欄の名前を今までどおり記録する。
- `--omit-supplier-field` で新しい2列の名前を指定したときは、new_system_rules からも外す（効かせないと、指定しても何も起きないため。設計者承認 2026-10-06）。

### 3-5. API とスキーマ
- central_masters.py の読み書きのスキーマに、2列を Optional[str]・max_length 50000 で足す。
- super_admin_suppliers.py の4か所（SELECT・dict・UPDATE・返り値）に2列を足す。
- overview の has_extraction_rules（:639-646）は変えない。本番の8列の有無を表すため。
- openapi.json を `python -m tools.export_openapi` で作り直す。

### 3-6. 画面
- SupplierExtractionRulesPage.tsx の4か所に2欄を足す。
- 部品は既存の Textarea（:774-805 と同じ作り）だけを使う。新しい部品や生の要素、色の直値は使わない（ADR-144）。
- 文言のキーを supplierExtractionRules に足す（ja.json と en.json に同じキー。ADR-027）。
  - layoutRules：「書き方の当てはめ（新しい仕組み専用）」／"Layout rules (new pipeline only)"
  - layoutRulesHelper：「指示書の手順番号を指して、この仕入元での判断を書きます。本番の解析には使われません。」／"Describe how each instruction step applies to this supplier. Not used by the current production extraction."
  - hardCases：「間違えやすい形（新しい仕組み専用）」／"Hard cases (new pipeline only)"
  - hardCasesHelper：「実際に誤りが出た形の原文例と出力例を書きます。本番の解析には使われません。」／"Original text and expected output for cases that were actually misread. Not used by the current production extraction."

### 3-7. テスト
- conftest.py の _PUBLIC_SUPPLIERS_DDL に2列を足す。
- test_tcg_gemini_extraction.py：新しい2列に値があっても、本番 v7 の note と supplier_context が変わらないこと。ship_format のテスト（:819-879）と同じ形で書く。
- test_gemini_raw_copy_v8.py
  - new_system_rules があるとき、見出しと値が「原文:」の前に入ること。
  - 無いときは、今の出力と同じであること。
  - 片方だけのときは、その見出しだけが出ること。
- test_prompt_ab.py：ctx.new_system_rules が v8 系に渡ること。--supplier-rules-file で上書きできること。v7 には渡らないこと。
- test_shadow_backfill.py:190-201：タプルを13要素にする（SELECT に合わせる）。
- tcg_extraction の _build_extraction_context の単体テスト
  - 2列が row[11]・row[12] から読まれること。
  - supplier_id は row[10] のままであること。
  - 新しい列だけに値がある仕入元では、supplier_context が None で、new_system_rules が入ること。
- 画面：既存の画面のテストがあれば、2欄が表示されることを足す。無ければ i18n のキーの検査（check:i18n-missing-keys）で代える。

## 4. 触らない
- _build_supplier_context_note（本番 v7 の指示書）
- gemini_extraction_svc.py の call_gemini_raw_copy・call_gemini_extraction
- extraction_shadow_svc.py
- 既存の8列の値
- 指示書のファイル
- deploy.yml
- 本番のデータ（2列への値の書き込みは、別に PO の許可を受けて行う）

## 5. 受入条件
| 基準 | 検証方法 |
|---|---|
| 本番 v7 の指示書と supplier_context が、新しい2列の値があっても変わらない | test_tcg_gemini_extraction.py に足すテスト |
| 新しい仕組みの指示書に、2列が決まった見出しで入り、無いときは今と同じ | test_gemini_raw_copy_v8.py |
| prompt_ab が new_system_rules を v8 系に渡し、ファイルで上書きでき、v7 には渡さない | test_prompt_ab.py |
| SELECT の位置がずれない（supplier_id は row[10]） | tcg_extraction の単体テスト、test_shadow_backfill.py |
| API で2列を読み書きできる | super_admin_suppliers の既存または新規のテスト。無ければ追加 |
| 画面に2欄が出て、文言は ja/en の同じキー | check:i18n-missing-keys、画面のテスト |
| migration の名前と登録 | migration-guard.yml のチェック2、登録ファイル存在点検 |
| API の契約が最新 | api-contract-check.yml |
| CI が緑 | gh pr checks |
| 危険パスの GO | ADR-136 の手順（対象・3行の要約・バックアップの確認を PO に示し、「GO #番号」を受けて PR 本文の GO記録に書く） |

## 6. 外部・過去事例の参照と我々への応用
- 社内の過去事例
  - extraction_ship_format の追加（migrations/20260928_110000_create_extraction_shadow_tables.sql:9）。v7 の指示書には入れず、v8 の末尾にだけ足した。その性質をテスト（test_tcg_gemini_extraction.py:819-879）で固定している。今回も同じ型を使う。
  - extraction_example_text の追加（migrations/20260924_030000_add_extraction_example_text.sql）。ADD COLUMN IF NOT EXISTS の作法を同じにする。
- Google の公式資料（Context7、2026-10-06）
  - Gemini 3 では指示に明確な決まりを書く（https://ai.google.dev/gemini-api/docs/gemini-3）。
  - 例は正しくできた姿を見せる（https://ai.google.dev/gemini-api/docs/prompting-strategies）。
- 我々への応用：決まりと例の置き場所を、新しい仕組み専用の欄として分ける。

## 7. リスクと戻し方
- リスク1：本番 v7 の指示書が変わる。
  - 対策：supplier_context に新しい鍵を入れず、別の new_system_rules で渡す。テストで固定する。
- リスク2：SELECT の位置がずれる。
  - 対策：列は最後に足す。位置のテストを置く。
- リスク3：migration の失敗。
  - 対策：ADD COLUMN IF NOT EXISTS だけを使い、既存の値は触らない。マージ前にバックアップを確かめる（ADR-136）。
- 戻し方：コードは PR を revert する。列は残っても害が無い（どこからも読まれなくなる）。列を消すときは、別の migration で PO の確認を受けて行う。

## 維持の仕組み
- 記録：新しい仕組みの試しの JSONL（supplier_rules_override）。
- 守り手: backend/tests/test_tcg_gemini_extraction.py と backend/tests/test_gemini_raw_copy_v8.py が CI で毎回通ること（本番 v7 の指示書が変わらないことと、新しい仕組みの組み立て）。
- 担当：2列への値の書き込み（17社分）は、別に PO の許可を受けて行う。本番を新しい仕組みに入れ替えるときに、ここを読むようにする。

## 8. 審査（Architect・同一 AI による自己審査）
- 判定：APPROVE（設計合格）
- 根拠
  - 本番 v7 への影響を、別の鍵（new_system_rules）で断っている。行番号の根拠は recon_raw.md にある。
  - SELECT の位置ずれを、列を最後に足すことで避けている。
  - 部品・文言・API 契約・migration の検査が、それぞれ CI で確かめられる。
- 未解決の点：無し。has_extraction_rules を変えないことは、意図した判断（§3-5）。

- 2026-10-07 試作版 v102 の既定を採用確定の形に変更（指示書 e・元からある7欄を既定で外す・`--keep-legacy-supplier-fields` で戻せる）。PO 指示。PR #TBD
