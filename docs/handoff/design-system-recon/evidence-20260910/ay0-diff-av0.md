# ay-diff-av0: §AV(base 55d99a97e) と現在(origin/main f0f7ef8c7) の input 差 -12 の原因

## 方法
- 旧: `git archive 55d99a97e frontend/src` を展開し、ay-inventory.cjs と同じ AST 走査（タグ全文を空白正規化した src 付き）を実行。ページ側 460、omitted150/text97/number65 …と §AV の記載値に一致（旧基準を再現）。
- 新: f0f7ef8c7 を同じ走査。ページ側 448。
- 突合: (file, タグ全文) の多重集合で一致判定。旧のみ 13、新のみ 1、差し引き -12。
- 注: av0-input-audit.json にはタグ全文がないため、JSON は直接使わず上記の再走査で突合した。

## 旧のみ（13件）: すべて「要素ごと消えた」か「TextField に置換」

| 旧 file:line (55d99a97e) | type | 原因コミット | subject |
|---|---|---|---|
| frontend/src/pages/admin/DiscordConfigPage.tsx:261,396,414,432,469,487,512,526 (8件, text) | text | e95f856b2 (2026-10-03) | feat: redesign Discord config page, hide admin tab bar on PC, add admin entries to management center |
| frontend/src/pages/super-admin/ParseReviewPage.tsx:536 | checkbox | d010d6700 (2026-10-02) | feat: remove dormant Discord inventory-parse feature (code + UI only) |
| 同:659, 676 | number x2 | d010d6700 | 同上 |
| 同:778, 805 | text x2 | d010d6700 | 同上 |

根拠:
- DiscordConfigPage.tsx: `git show <c>^:file | grep -c '<input'` / `'<TextField'` は e95f856b2 で `<input` 8→0、`<TextField` 0→8。bc58a5dd5 は 8→8（無変更）、62be5841f は TextField 8→8（無変更）。現在 `<TextField` は :360, :467, :475, :483, :491, :499, :507, :515。
- ParseReviewPage.tsx: 旧に `<input` 5、現在ファイルが存在しない。d010d6700 で 917行削除（`git show --stat`）。5件 = checkbox1 + number2 + text2。
- d010d6700 は 55d99a97e の祖先ではない（`merge-base --is-ancestor` 偽）。コミット日は 10-02 だが 55d99a97e の後に main へ入った。
- 3コミットとも origin/main の祖先（e95f856b2, 62be5841f, bc58a5dd5 は確認済み）。

type 別の整合: text 8+2=10 → 97→87、number 2 → 65→63、checkbox 旧のみ1 と 新のみ1 が相殺。合計 -12 に一致。

## 新のみ（1件）
- frontend/src/pages/super-admin/components/UnitIgnorePhrasesPanel.tsx:169 `<input type="checkbox" checked={form.is_active} ...>`（checkbox）
- ファイルは 55d99a97e に存在しない。追加コミット 49c628361 (2026-10-08) feat: add line_unit_ignore_phrases master (table, super-admin API, panel)。ui-allow は 18514b21c (2026-10-08) fix: ui-allow for checkbox, declare openapi.json in design.md。コードに `ui-allow: ... (#4032)` あり(:168)。

## 結論（事実）
差 -12 = Discord設定画面のテキスト入力8件が TextField に置換(e95f856b2) + ParseReviewPage 削除で5件(d010d6700) − 新規パネルの checkbox 1件(49c628361)。他の差はなし。
