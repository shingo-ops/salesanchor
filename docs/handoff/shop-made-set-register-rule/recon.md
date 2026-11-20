# recon: 公式に無い組の登録（手順書の例外）

## 既存 ADR 検索
- `git grep -il "セット" docs/adr/` と docs/adr/FEATURE-INDEX.md を確認。共用商品の登録規則は ADR-1020（Accepted）が親で、正本は docs/specs/product-master/registration-rules.md。
- 「公式に無い組」を扱う ADR は無い。

## 現在地（行番号は変更前の origin/main 基準）
- docs/specs/product-master/registration-rules.md:14 C4 の次に、公式に無い組についての規則は無い。
- docs/specs/product-master/registration-rules.md:27 商品区分 決め方は「公式のセット内容（商品の形）で決める。Set は別々の物 A と B が1つの商品になっているときだけ」。公式に無い組の扱いは書いていない。
- docs/specs/product-master/registration-rules.md:20 日本語名は「外部サイトから公式情報を採用する」。
- PO 2026-10-30 の判断（公式に無い組は登録せず要確認に回す・件数が増えたら考え直す）は手順書に未転記だった。

## 今回の材料
- 過去60日の投稿 3551 品の試算で、メガブレイブ・メガシンフォニアの組は 51 件。登録前は 43 件が単品メガブレイブとして数えられていた。登録後の単品の悪化は 0 件（社外秘の記録ファイルに保存。PR には載せない）。
