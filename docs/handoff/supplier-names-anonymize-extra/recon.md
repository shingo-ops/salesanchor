# recon: 一覧外の仕入元名と先方担当者名を仮名に置き換える（社外秘）

基準: origin/main cc20266c3（作業開始時点）。スキャンは `git grep -n -F -f`（名前一覧は repo 外）。実名・対応表は repo 外の `/tmp/CC報告ファイル/supplier-names-scan/extra/` にのみ置く。PO 承認 2026-10-13（対象は「一覧にない仕入元の名前」と「仕入元の担当者（先方の人）の個人名」。自社の人は対象外）。

## 既存 ADR の検索

- `git grep -i -l 仮名 docs/adr/` ／ `docs/adr/FEATURE-INDEX.md` を確認 → 仕入元名の仮名化を定める ADR なし。前回便（10社）は docs/handoff/supplier-names-anonymize-docs/recon.md。関連 ADR-099（在庫モデル）は前回便で置換済み。
- 方針の根拠は PO 判断（2026-10-01 仕入元データは社外秘）。

## 前回調査の結果（候補の件数）

| 区分 | 件数（仮名の数） |
|---|---|
| 仕入元 | 29（文字列 33） |
| 個人 | 36（文字列 39） |
| 不明 | 32（文字列 33）→ 今回は置換しない |
| 対象外（1〜2文字・かな3文字以下・英字4文字以下・一般語・略称ほか） | 65 文字列 |

## 絞り込み（置換の前）

- 仕入元 29 件: 全件を置換対象にした。外したのは部分一致・一般語の誤検出 1 行（一般語「重なり」の意味で使われているカタカナ語。docs/handoff/line-import-incremental-send/design.md:124）。英字を含む名前は、英数字の隣接を許さない単語境界で照合した。
- 個人 36 件: 1 件ずつ根拠を確認（repo 外 person-judge.tsv）。
  - 先方（仕入元側）: 36 件。根拠は、`SP-` 番号付きの仕入元アカウント名として出ている／仕入元ごとの見出しの括弧付き名として出ている／migration の name 列・recon の仕入元一覧に姓名として入っている、のいずれか。
  - 自社（PO・社内スタッフ・開発担当・作成者・GO 発行者）: 0 件（社内の役割の文脈にある名前は無かった）。
  - 判定不能: 0 件。
  - このうち 3 件は migrations/ にしか無く、対象外ゆえ今回の置換は 0 行（置換された個人は 33 件）。
  - 部分一致で外した行: 英字のみの名前（担当者18）は、住所の英字地名・配送会社の URL に部分一致していた 5 行（backend/app/routers/shipping.py:645 と docs/research/external-integrations-research-2026-06-05.html の 4 行）を、単語境界で外した。
- 不明 32 件: 置換しない（件数のみ。backend/app・backend/tests に当たる行は不明のみ）。

## 現在地（置換した行）

対象範囲は docs/ のみ（tasks/・コメント・docstring・テストには、仕入元・先方担当者の置換対象は 0 行。テスト・コードで当たったのは不明と部分一致のみ）。migrations/・frontend/src/locales/・提供者G の行は触らない。

置換した行数 103（15 ファイル）。ファイル別:

| ファイル | 置換した行数 |
|---|---|
| docs/handoff/gemini-extract-role-split/supplier-block-evidence.md | 65 |
| docs/handoff/line-parser-unify/recon.md | 13 |
| docs/handoff/fix-received-at-latest/recon.md | 5 |
| docs/handoff/supplier-name-dedup/recon.md | 4 |
| docs/handoff/gemini-extract-role-split/supplier-rules-design.md | 3 |
| docs/handoff/fix-received-at-latest/design.md | 2 |
| docs/handoff/sup-register-15/recon.md | 2 |
| docs/handoff/tcg-2026-09-05-summary/recon.md | 2 |
| docs/handoff/dashboard-ux-improvement/recon.md | 1 |
| docs/handoff/pmg-import-delivery-ssot/recon.md | 1 |
| docs/handoff/sup-register-15/design.md | 1 |
| docs/handoff/tcg-direct-sql-record/design.md | 1 |
| docs/handoff/tcg-direct-sql-record/recon.md | 1 |
| docs/handoff/tcg-import-latest-only/sold-out-rules-handoff.md | 1 |
| docs/handoff/v102-shime-inventory-ref/recon.md | 1 |

## 置換後に残る部分（同一行内の掃除）

- 見出しの姓・略称が同じ行に重複していた 3 行は、同じ仮名に揃えた（会社の略称 1 行、担当者の姓 2 行）。
- 姓だけ・名前の一部だけの別表記（例: 見出しの姓のみ、一覧中の姓のみ）は、前回の「2文字以下は対象外」判断に従い今回は触らない。行数は repo 外 `residual-fragments.txt` に記録。

## 触らない範囲

migrations/、frontend/src/locales/、提供者G の行、backend/app・backend/tests（置換 0 行）、不明 32 件。
