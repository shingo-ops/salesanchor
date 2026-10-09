# デッキビルド系商品マスタの修正（SV3/SVF, SV7/SVK, SV9/SVN）

状態: 準備のみ（本番は未実行）。product code・商品名のみ記載。仕入元名・投稿本文は含まない。

## PO の決定（チーム長経由で受領した引用）
- 目標の表: 「はい」
- 品番＋デッキビルド の検索キーワード追加: 「はい」
- 実行者: 「変更も私ではなくあなたとsonnetが実行」
- ADR-155 の例外（直接 SQL）: 「はい」
- 「2」（質問番号への回答。質問文は未確認）
- 2026-10-05: 「あなたに任せる許可する」
- 許可の根拠: `~/.claude/settings.json` autoMode.allow「Deckbuild master fix by direct SQL」（2026-10-05 追加）

## 目標の状態（最終版。品番キーワード込み）
| id | code | name | mark | search_keywords（順） | exclude_keywords |
|---|---|---|---|---|---|
| 58 | SV9 | バトルパートナーズ（変更なし） | SV9 | バトルパートナーズ | デッキビルド |
| 60 | SVN | バトルパートナーズ デッキビルドBOX | SVN | バトルパートナーズ デッキビルド / SV9 デッキビルド | なし |
| 74 | SV7 | ステラミラクル（変更なし） | SV7 | ステラミラクル | デッキビルド |
| 75 | SVK | ステラミラクル デッキビルドBOX | SVK | ステラミラクル デッキビルド / SV7 デッキビルド | なし |
| 103 | SV3 | 黒炎の支配者（変更なし） | SV3 | 黒炎 / 黒炎の支配者 | デッキビルド |
| 105 | SVF | 黒炎の支配者 デッキビルドBOX | SVF | 黒炎の支配者 デッキビルド / 黒炎 デッキビルド / SV3 デッキビルド | なし |

現在値（2026-10-04 21:19 に本番で取得、`/tmp/CC報告ファイル/system-accuracy-v9/masters/current_values.csv`）:
60 は mark SV9・name「バトルパートナーズ」、75 は mark SV7・name「ステラミラクル」・keyword「デッキビルド ステラミラクル」、105 は mark SV3・name「黒炎の支配者」。
基底 58/74/103 の除外は「デッキビルド」と「デッキビルドBOX …」の 2 件 → 「デッキビルド」のみに縮める。

## シミュレーション結果（ローカル・実際の match_product、v9 T2 3,066 ブロック）
- ambiguous → matched: 56（SV3/SV7/SV9 の曖昧ブロックがすべて基底商品に確定。デッキビルド文言は 0 件なので基底が正）
- 変化なし: matched 2,336 / ambiguous 373 / unmatched 301
- 退行: 0（matched → 未確定 / 別商品 のブロックなし）
- matched 2,336 → 2,392、自動確定（needs_review=false）は 343 のまま、クラス1相当の正解ブロック 2,315 → 2,371 / 3,066
- 合成プローブ（短い文字列）: 「{基底名} デッキビルド{BOX/ボックス/box/ BOX/全角空白ボックス}」「ﾃﾞｯｷﾋﾞﾙﾄﾞBOX」「でっきびるど」「デッキ ビルド」はすべて変種に確定。「SV7/SV3/SV9 デッキビルドBOX」「[SV7] デッキビルド」も変種。「SV7 BOX」「SV3 BOX」「SV9 BOX」は基底に確定（現状は曖昧）。
- 既知の限界: 「ＤＥＣＫ ＢＵＩＬＤ」「Deck Build BOX」は変種のキーワードに当たらず基底に確定。「SV7a デッキビルド」は SV7a/SVK で曖昧のまま（現状と同じ。3文字の値は語境界を要求しない: extraction_judgement_svc.py:57-59）。
- 元データ: `/tmp/CC報告ファイル/system-accuracy-v9/product-check/sim2/deckbuild_sim2.md`、`sim3/deckbuild_sim3.md`

## 影響メモ
- 作業参照のダイジェスト: 全有効商品の name / mark / keywords が作業参照に入る（tcg_work_reference.py:86-94、ダイジェスト :30-31）。変更後は保存済み v5 以降ジョブの再解析が `Work reference changed; re-extraction required` で失敗する（tcg_analyzer_svc.py:1258-1259）。実行中の抽出は `REFERENCE_CHANGED`（tasks/tcg_extraction.py:428）。商品マスタを 1 件でも変えれば同じ結果になる既存の挙動。
- v6 の型番照合（Gate 1）: `rawcode_to_id` は mark → id を作った後に product_code → id で上書きする（tcg_analyzer_svc.py:1219-1224）。変更前も SV9/SV7/SV3 は基底（product_code 優先）、SVN/SVK/SVF は product_code で変種を指すため、既存キーの対応先は変わらない。照合は Gemini の raw_product_code の完全一致（:1431）。
- v6 のキーワード照合: 除外キーワードの短縮は、残す「デッキビルド」が削る語に含まれるため包含関係で同等（日本語混じりは token_and_match、tcg_analyzer_svc.py:279-296）。変種に足す 2 語キーワードは、両方の語が含まれるとき当たる。語順に依存しないかは token_and_match 本体を読んでおらず **未確認**。
- v6 の直近 30 日の実績（check_deckbuild_usage.sh の結果）: analysis_results の product_id 別件数 = 60 が 13、75 が 7、105 が 11。Gemini の選択（extraction_items.resolved_product_code）= 58:165、60:19、74:93、75:4、103:103、105:1。基底 58/74/103 は主に Gemini 経由で確定。
- Gemini が見る作業参照（name / mark / keywords）が変わるため、Gemini の選択が変わるかは **未確認**（モデルの挙動）。
- 更新経路との差: アプリ保存は audit_log 行を 1 件書く。apply.sql も同じ形の行を書く（record_id は新規 uuid、old/new は TEXT の JSON、changed_by は 'claude-opus (PO承認 2026-10-04)'）。JSON の空白・キー順はアプリと異なり得る（形は同じ）。updated_at はトリガ（migrations/062_create_inventory_movements_and_budget.sql:71-80）が更新する。

## 手順（この順。各ステップを実行し、結果を確認してから次へ）
実行ラッパー: `/tmp/CC報告ファイル/system-accuracy-v9/masters/run_deckbuild_sql.sh <mode>`（rollback は含まない）
1. precheck: `precheck.sql`（読み取り専用）。6 商品が現在値と一致しなければ RAISE して止まる。
2. dryrun: `dryrun.sql`（apply と同一処理 → 最終状態を SELECT → ROLLBACK）。エラーなく終わり、各 UPDATE/DELETE/INSERT の件数が想定どおりであること。
3. apply: `apply.sql`（1 トランザクション、末尾 COMMIT。各 UPDATE は 1 行、最終状態＝目標でなければ RAISE して全体が戻る）。
4. postcheck: `postcheck.sql`（読み取り専用）。目標と一致しなければ RAISE。audit_log の書き込み行も表示。
- 戻し: `rollback.sql`（2026-10-04 の状態に戻す。実行には新たな PO 判断が必要）。
- SQL は `gen_sql.py` で生成した（1つの仕様表から 5 本）。手で直さず、仕様表を直して再生成する。

## 実行前の確認事項
- 実行前の状態: これらの SQL は本番 DB で未実行。ローカルの使い捨て DB での動作確認は、フックにより `rm -rf` が止められたため行っていない（未確認）。dryrun が最初の実行だった（最後は ROLLBACK）。

## 実行記録（2026-10-04、PO 承認済みの本番データ変更・ADR-155 の例外）
許可: PO が「psql write」チケットを 2 回発行（各 1 回限り）。1 回目 2026-10-04T23:03:02Z（dryrun 用）、2 回目 2026-10-04T23:10:55Z（apply 用）。

| 順 | 内容 | 実行時刻 (UTC) | ファイル sha256 | 結果 |
|---|---|---|---|---|
| 1 | dryrun（最後は ROLLBACK） | 2026-10-04 23:03:19 頃 | bff2759dcf2b102a8094b32b7b5f7aecbe0bfd632fd076c3db95b223c096de28 | 成功。何も保持されない。ログ: logs/dryrun.log |
| 2 | apply（COMMIT） | 2026-10-04 23:11:34 | 3ce3657e6132af2f86c83646b30d167cf7960f310aa77d9e04434bc62ec231f4 | 成功。COMMIT。ログ: logs/apply.log |
| 3 | 実行後の確認（読み取り専用の SELECT 2 本） | 2026-10-04 23:12 頃 | （ファイルは使わず、クエリ文をログ先頭に記載） | 目標と一致。logs/postcheck_products.log、logs/postcheck_audit.log |

- 差分: dryrun.sql と apply.sql の違いは、先頭 2 行のコメントと最終行（ROLLBACK → COMMIT）のみ（diff で確認）。
- 件数（apply）:
  - products の UPDATE: 6 件（各 1 行）
  - product_exclude_keywords: 削除 6 行・挿入 3 行（id 58, 74, 103 が各 2 行 → 1 行）
  - product_search_keywords: 削除 3 行・挿入 7 行（id 60 が 1 → 2、id 75 が 1 → 2、id 105 が 1 → 3）
  - audit_log: 6 行（id 20〜25、changed_by = 'claude-opus (PO承認 2026-10-04)'、changed_at = 2026-10-04 23:11:34.417695+00）
- 実行後の確認: 6 商品はすべて目標の表と一致（mark SVN / SVK / SVF、名称、keyword の順、除外は基底が「デッキビルド」のみ・変種はなし、is_active はすべて t）。updated_at は 6 件とも 2026-10-04 23:11:34 に更新された。
- precheck.sql と postcheck.sql はファイルとしては実行していない（dryrun の中の確認で現在値の一致を確認し、実行後は上記の SELECT で確認した）。
- 位置番号: 変更しなかった keyword の一覧は位置が 0 始まり、書き直した一覧は 1 始まり（アプリの保存と同じ）。順序のみ使うため影響はないと見ているが、混在している事実を記録する。
- rollback.sql は実行していない。実行するには新たな PO の判断が必要。
- 未確認: Gemini の選択が変わるか、v6 の語順非依存。保存済みジョブの再解析は、作業参照のダイジェスト変更により再抽出が必要になる（影響メモのとおり）。
