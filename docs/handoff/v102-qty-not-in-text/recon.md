# recon: v102 の数量の写しが原文に無い件を要確認にする

- 基準: origin/main 656817ddd37e7c30896ac41db00a183a058668c1（#4075 マージ）。読み取りのみ（Sonnet 調査、Opus 確認）。
- 既存 ADR 検索: 要確認の SSOT は docs/adr/ADR-154（配信は needs_review が偽の件だけ）。v102 の本番組み込みは docs/handoff/v102-prod-switch/design.md（便B）。本件は新しい判断を足さず、既存の理由の形に1種類足すだけなので ADR 新設なし。

## 1. PO の条件（2026-10-08、指示書 f_c 合格の条件）
「写した価格・数量がその件の行の原文に無ければ要確認→理由を添える→人が直す→すぐ本線に戻す」

## 2. 価格（満たしている）
- backend/app/services/gemini_raw_copy_v101.py:124-144 `_first_line_containing` / `_priced_line`：件の lines の行だけを NFKC＋空白除去で部分一致で探す。
- backend/app/services/gemini_raw_copy_v101.py:213-226：見つからなければ rejected（kind=price_not_in_lines）。v102 は keep_rejected=True（backend/app/services/line_analysis_v102_svc.py:239）で件を残し、backend/app/services/gemini_raw_copy_v101.py:1059-1072 `_rejected_row` が review=[{kind:"price_not_in_lines", field:"price", copied}] を付ける。
- backend/app/services/line_analysis_v102_svc.py:507-518：review と gemini_review の kind を review_reasons に結合し needs_review=True。
- 既知の限界（本件の対象外）：部分一致なので写し「1100」が原文「11000」の行で通る。

## 3. 数量（満たしていない）
- backend/app/services/gemini_raw_copy_v101.py:781-792 `_quantity_not_in_text`：写しの数字の塊ごとに、件の行（:818 block＝件の lines の行を連結）に独立した数として在るかを見る。
- backend/app/services/gemini_raw_copy_v101.py:860：結果は件の bool 欄 `quantity_not_in_text` に入るだけ。
- `git grep -n quantity_not_in_text origin/main -- backend frontend/src` の該当は gemini_raw_copy_v101.py:781,860,1071 とテストのみ。review の kind にならず、line_analysis_v102_svc.py の review_reasons にも流れない＝True でも配信から外れない。
- 似た既存の理由：quantity_no_number（gemini_raw_copy_v101.py:1047,1088）＝写しに数字が無い件。別物。

## 4. 手元の測定（社外秘データ・手元のみ、~/CC報告ファイル-keep/session-20261007b/after24/）
- 2026-10-09 06:25Z 時点の再計算 r1 3,697 件・r2 3,698 件で quantity_not_in_text が True の件は 0／0。
- よって本変更で要確認が増える件数の見込みは、この 147 投稿では 0（実装後に同じデータで再計算して確認する）。
- 見逃し（止められない誤り）：原文どおりの写しで意味が違う数（入り数など）。本件では止められない（指示書 f_c で対処済み）。

## 5. 本番への影響
- 本番の既定は v6（docker-compose の LINE_ANALYSIS_ENGINE、便B）。v102 で解析された投稿だけが対象。
