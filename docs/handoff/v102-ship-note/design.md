# design: 試作版 v102 の発送日の文字を「備考」（note_ja）に入れる（便PO3）

参照: docs/handoff/v102-ship-note/recon.md、docs/handoff/v102-ship-note/card-PO3.md、docs/handoff/v102-preorder-context/design.md §7。

## 1. 目的（PO の言葉、2026-10-12）
- 「y,発送日の情報は発送日情報に記載する条件で」→ 保存先を問うと「備考に入れる」。
- 利用者に見える変化：在庫一覧と配信の「備考」に、「発送日要相談」「10/16発送」などの発送日の文字が出る（今は v102 の行で空）。

## 2. 変更
| 場所 | 変更前 | 変更後 |
|---|---|---|
| backend/app/services/line_analysis_v102_svc.py `ship_note`（新規） | 無し | 発送日の文字 → 備考。None・空白・"none"（v101 の _NONE を import）は None。" / " ごとに括弧を直す（開きの無い閉じは消す・閉じが足りない開きには末尾に閉じを足す。組は定数 _BRACKET_PAIRS） |
| 同 `_analysis_values` の note_ja | 常に None | `ship_note(item.get("ship"))`。ほかの列は変えない |
| v101・v10・旧 v6（build_note_ja）・配信・GAS | — | 変えない |
| データ | — | 変えない（次に解析された行から入る） |

## 3. 受入条件
| 基準 | 検証方法 |
|---|---|
| T1 備考が入るのは ship のある件だけ、"none" は入らない | 置き換え試験（2,693 件）：空でない 233 件＝ship のある件、ship が none なのに備考ありは 0（/tmp/CC報告ファイル/preorder-design/shipnote/test/compare.txt、手元・社外秘） |
| T2 note_ja 以外の列は変わらない | 同上：変化 0 件 |
| T3 括弧直しが仕様どおり | テスト backend/tests/test_line_analysis_v102_svc.py（ship_note 9ケース・_analysis_values 1件） |
| T4 本番反映後、反映時刻以降に解析された v102 の行で、備考が空でない行がある・"none" の行は 0 | 本番読み取り（analysis_results の note_ja） |

## 4. 代替案
- 専用の「発送日」の列を作る：表・配信・画面の作り変えが要る → PO が「備考に入れる」を選択。
- 旧系の tcg_note_master で注記ラベルにする：決まった語のラベルしか出ず、「10/16発送」の日付が消える → 拾った文字をそのまま入れる。

## 5. リスクと対処
- 備考の列は表示だけに使われる（recon）ため、判定・統合・配信の絞り込みは変わらない。
- 今後、備考に別の情報（括弧の注記など、統合ルールの設計で検討中）を入れるときは、" / " でつなぐ形で同じ欄に足す（その便で設計）。

## 6. 戻し方
- PR を revert。入った備考は、次の解析で None に戻る（データの手作業は不要）。

## 外部・過去事例の参照と我々への応用
- 外部事例：使わない（社内の解析結果を既存の表示欄へ渡すだけで、比べられる公開の実測が無いため）。
- 過去事例：#4158（予約の判定）の置き換え試験と同じ作法で、全件の前後を比べてから出す。

## 維持の仕組み
- テスト（ship_note の括弧直し・none の扱い・_analysis_values の note_ja）が CI で毎回走る。
- 守り手: CI（backend/tests/test_line_analysis_v102_svc.py）
