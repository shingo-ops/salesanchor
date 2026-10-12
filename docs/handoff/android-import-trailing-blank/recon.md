# recon: Android 取込で本文末尾の空行により同じ投稿の2通目ができる（便TB）

基準 origin/main（2026-10-12、9f71e3cb9）。本番は読み取りのみ。生出力（手元・社外秘）: /tmp/CC報告ファイル/v102-unit-state-set/prod/dup/（ingest/ を含む）、/tmp/CC報告ファイル/android-trailing-nl/。

## 既存 ADR
- `git grep -il -E "line.?import|source_messages|android" docs/adr/` → docs/adr/ADR-158-product-level-supersession.md、docs/adr/ADR-1001-deprecate-tcg-products-unify-to-public.md。docs/adr/FEATURE-INDEX.md に該当行なし。
- docs/adr/ADR-158-product-level-supersession.md:15-17 は source_messages.is_active の責務（最新性と配信可視性）を述べる。再利用判定・raw_text の定義を決める ADR は無し。本変更は is_active・superseded_by の意味を変えない。

## 取込の経路（origin/main）
- source_messages への INSERT は backend/app/services/tcg_line_import_svc.py:326 `_write_source_messages` の1箇所（本番で動く唯一の経路）。呼び出しは backend/app/services/tcg_line_import_svc.py:700（通常取込）と backend/app/routers/tcg_line_import.py:622（保留ジョブ確定。:619 で build_provider_entries を作り直す）。移行用の一括コピー backend/tcg_migration/scripts/ingest_to_prod.py:216・scripts/migrate-pipeline-data-to-public.sh:76 は本番の取込では動かない。
- entry の raw_text・sha256 は backend/app/services/tcg_line_import_svc.py:272 build_provider_entries（仕入元ごとの最新1通の body）。_write_source_messages より前に entry を使うのは :668 の skipped_message_count の合算だけ（本文に依存しない）。
- 再利用判定 backend/app/services/tcg_line_import_svc.py:391-404: 同じ channel・同じ line_posted_at で raw_sha256 と raw_text が完全一致なら reused（新規なし）。違えば新規 INSERT（:431-447）し、その channel の有効な行をすべて superseded（:449-460）。
- PC 用パーサ backend/app/services/tcg_line_import_svc.py:149-154 は行末 rstrip・空行を飛ばす（末尾に改行は付かない）。
- Android 用パーサ backend/app/services/tcg_line_android_parser.py:46-47 は空行も `'\n' + line` で本文に足す。投稿がファイルの最後なら後ろに空行が無く、後続の投稿があると直後の空行が本文末尾の "\n" になる。

## 観測（本番、2026-10-12 読み取り）
- 同じ channel・同じ line_posted_at で、後の行が前の行の末尾に "\n" を1つ足しただけの組: 全期間 24組（初出 2026-09-20 15:54 UTC）、直近14日 18組。24組すべてで前の行は superseded_by が後の行。
- 4組（job 08c195f3→5cf9ace3、c48b0a03→3edda361、0f792341→5a0c8391、d3d35405→439aaecb）は filename android-talk.txt の別々の import_job（ファイル sha256 が異なる）。24組すべてで前の取込ではその投稿がファイル内の最新、23組で後の取込にはより新しい投稿が入っていた。
- source_messages 2,534件の末尾: "\n" 87（うち "\n\n" 3）、半角空白・タブ・全角空白 70（全角 4）。
- 影響: 同じ投稿の2行が同じ時刻で並び、現行行（is_current）の選び方が解析順で入れ替わる（便SU の再解析で 18組中 10組がこの形）。数量・価格は同じ。

## 未確認
- LINE の Android 書き出しが、どの条件で投稿の直後に空行を入れるか（後続があっても付かない投稿があり、24組中1組は後続なしで付いた）。元の書き出しファイルは保存されていない。
