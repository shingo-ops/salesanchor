# recon: 発送日欄「ー」で日付が読めない件（ship-drop-category 便C）

実測基準: origin/main f61be2c687f8471f5c8b14ce83c93986d1dd9204（本 PR の土台。下の file:line はこの SHA で行番号と該当行の一致を確認済み）。調査の元は 2026-10-14 の ship_dash_recon.txt（/tmp/CC報告ファイル/、repo 外）で、その時点の origin/main の行番号。事実のみ。評価・提案なし。
社外秘：仕入元の原文は書かない。入力例は一般化した形のみ。設計は同フォルダ design-dash.md。

## 現在地（file:line）
- `backend/app/services/tcg_analyzer_svc.py:244` normalize_en（全角英数記号→半角・小文字化。「ー」U+30FC と「〜」U+301C は変換しない。全角「－」「～」は - ~ に変わる）
- `backend/app/services/tcg_analyzer_svc.py:262` token_and_match（空白で分けた全語が部分文字列として含まれれば当たり）
- `backend/app/services/tcg_analyzer_svc.py:280` match_one_kw（純 ASCII の語は前後が英小文字でないことで判定、日本語混じりの語は token_and_match）
- `backend/app/services/tcg_analyzer_svc.py:1063` _note_matches（判定本体）
- `backend/app/services/tcg_analyzer_svc.py:1084` REGEX 行の exclude を部分の文字列全体に対して判定。1語でも当たれば行ごと不採用
- `backend/app/services/tcg_analyzer_svc.py:1090` `re.search(pattern, norm_memo)`（fullmatch ではない・flags なし）
- `backend/app/services/tcg_analyzer_svc.py:1173` build_ship_labels
- `backend/app/services/tcg_analyzer_svc.py:1186` 部分を `" / "` で分ける
- `backend/app/services/tcg_analyzer_svc.py:1187` 部分ごとに _note_matches
- `backend/app/services/tcg_analyzer_svc.py:1194` 1部分に複数行が当たると label を「,」でつなぐ（勝者を 1 つに絞る処理は無い）
- `backend/app/services/line_analysis_v102_svc.py` が build_ship_labels を呼ぶ（呼び出し元はこの 1 か所。note_ja は常に None）

## 本番マスタ（repo 外の取得物 note_master_prod.txt、2026-10-13 23:53 JST 取得）
- id 126 指定日発送 priority 2 REGEX `(\d{1,2})[/月](\d{1,2})日?.{0,4}?(発送|出荷)`、exclude `完売,前後,までに,〜,~,ー,-`、tenant_id NULL
- id 129 日数指定発送 priority 3 REGEX `(\d{1,2})日(発送|出荷)`、exclude `発売日,到着後,以内,完売,前後,までに,〜,~,ー,-`、tenant_id NULL
- 期間を担当する行：id 122（M/D〜M/D）・190（M/D〜D）・192（M月D日〜D日）・215（D日〜D日）・219〜224（旬〜旬）
- 事実：126 の exclude の ー と - を外し、pattern を替えないと、期間の文に 126 と期間の行が同時に当たり label が「,」でつながる（1194 の動き）。今は 126・129 の exclude が二重ラベルを防ぐ壁になっている。
- 事実：126 を変えると、発送日欄（v102）と旧経路 note_ja の両方の判定が変わる（_note_matches は両方の共通部品で、category で分けていない）。旧経路が今も本番で動くかは【未確認】。

## テスト（`backend/tests/test_tcg_keyword_matching.py`）
- `backend/tests/test_tcg_keyword_matching.py:435` 126 相当の pattern を持つ行（備考側）
- `backend/tests/test_tcg_keyword_matching.py:467` 126 相当の行（exclude に 〜,~,ー,- を持つ）
- `backend/tests/test_tcg_keyword_matching.py:575` test_build_ship_labels_without_drop_entries_is_unchanged
- `backend/tests/test_tcg_keyword_matching.py:582` test_build_ship_labels_generalized_cases_with_drop_entries（「カートン 11/20発送」→ 11/20発送 を含む）
- 事実：このテストの 126 相当（S6）は exclude が空で、本番の id 126（exclude に ー を持つ）とは別物。本番の形を検証するテストは無い。129 相当のテストも無い。

## 実測（使い捨て環境・DB 不使用。生資料は repo 外）
- 案 A・B・C・D1・D2 の比較：入力 78 件＋dry_parts 181 件（planB.txt・planC.txt・planD.txt）。案 C は 27 件が今と違い、期間に単独日付が二重に付く穴あり。D2 は 12 件が違う。
- 再審査で D2 を D2' に直した版は、78 入力と dry_parts で D2 と差 0（ship_dash_design_review2.txt）。
- 現行データ：dry_parts の入力 181 件（重複を除くと 52）に「ー/- ＋日付」の形は 0 件。正しさの根拠にはならないため、正しさは設計の A〜D 表で確かめる。
- snap_after.json（便B 反映後の 2,722 行）：ship_ja に ー か - を含む行 0 件。原文列は無い（変換後の ship_ja・ship_en のみ）。
- 【未確認】dry_parts が本番の現行データと同じ範囲かは未確認（dryrun の入力であり、本番へ直接問い合わせていない）。

## 共用マスタの書き込み制約
- `scripts/migration-guard/protected-tables.txt:29` に tcg_note_master。マスタのデータは migration で触らない（CI migration-guard チェック7）。

## 既存 ADR 検索（`git grep -il` で `docs/adr/`、`docs/adr/FEATURE-INDEX.md` 確認済み）
- tcg_note_master／note_master: `docs/adr/ADR-154-tcg-parity02-gas-python-migration.md`（マスタ不在時の fallback の記述。発送欄の判定の記述は無し）
- ship_ja: `docs/adr/ADR-1014-inventory-view-shows-distribution-rows.md`（在庫表の列に ship_ja を足す記述。判定の記述は無し）
- マスタの更新手段: `docs/adr/ADR-155-product-master-ssot-csv-app.md`（マスタは CSV 取り込みとアプリ画面に一本化。migration でデータを触らない根拠）
- FEATURE-INDEX.md：「備考マスタ」「発送日欄」の項目は無し（発送の項目は ADR-103 ほか出荷タイミング・キャリア系）。
