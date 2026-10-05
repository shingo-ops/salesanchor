# MEGAドリームex の mark 修正（PM0198、id 440559、M3 → M2a）

状態: 本番に適用済み（2026-10-05 00:33:42Z）。実行記録は末尾。product code・商品名のみ記載（仕入元名・投稿本文は含まない）。

## PO の決定（チーム長経由で受領した引用）
- 「修正してくれ」（MEGAドリームex の mark を M3 から M2a に直す件）
- 本番での実行は、PO が「psql write」の許可チケットを 2 回発行（各 1 回限り）した後に行った。詳細は末尾の実行記録。

## 変更内容
| id | code | name | mark（前 → 後） | search_keywords | exclude_keywords |
|---|---|---|---|---|---|
| 440559 | PM0198 | MEGAドリームex（変更なし） | M3 → M2a | MEGAドリームex / MEGA Dream / メガドリーム（変更なし） | AR / PSA / PSA10 / PSA9 / SAR / SR / パラレル / マスターボールミラー（変更なし） |

- mark のみ変更。キーワードは変更しない。PM0198 のキーワードにも ムニキスゼロ（id 12、code M3・mark M3）のキーワードにも "M3" や "M2a" は含まれない（2026-10-05 の本番値）。
- 現在値の取得元: 本番の読み取り（2026-10-05）。created_at 2026-09-14T20:35:02Z、updated_at 2026-10-03T17:49:56Z、release_date 2025-11-28、is_active = t。

## 公式の根拠（公式サイトのみ。引用は取得ツールが返した文面）
- MEGAドリームex の発売日と種別: https://www.pokemon-card.com/ex/m2a/index.html
  - 「ハイクラスパック「MEGAドリームex」」 / 「11月28日（金）発売！」（税込550円、10枚入り）。このページの本文には "M2a" の文字はなく、URL の /m2a/ にのみ現れる。
- MEGAドリームex の公式コード M2a: https://www.pokemon-card.com/card-search/details.php/card/48585（公式カードデータベース、カード「ロケット団のミュウツーex」）
  - Set Code "M2a"、弾名 「ハイクラスパック 「MEGAドリームex」」、カード番号 "063 / 193"（M2a のロゴ）。
- ムニキスゼロ: https://www.pokemon-card.com/ex/m3/
  - 「ムニキスゼロ」 / 「発売日：2026年1月23日（金）」 / 「ポケモンカードゲーム MEGA 拡張パック」。コード M3 は URL（/ex/m3/）とカード画像名（m3-xxx）に現れる。ページ本文中の文字としての "M3" は 未確認。
- 本番の値との比較: PM0198 の release_date 2025-11-28 は公式と一致。mark M3 は公式コード M2a と不一致。ムニキスゼロ（id 12）は release_date 2026-01-23・mark M3 で公式と一致。
- 既存の記録: docs/adr/ADR-155-product-master-ssot-csv-app.md:21 「型番（mark）の誤登録も発生した（PM0198 MEGAドリームex: M3 → 正しくは M2a）」。

## シミュレーション（ローカル、v9 T2 3,066 ブロック、実際の match_product）
基準は現在の本番マスタ（デッキビルド修正後）。変更は id 440559 の mark のみ。

| 遷移 | ブロック数 |
|---|---|
| matched → matched | 2,392 |
| ambiguous → ambiguous | 357 |
| unmatched → unmatched | 301 |
| ambiguous → matched | 16 |

- 退行: 0（matched → 非 matched / 別商品 のブロックなし）。matched 2,392 → 2,408、自動確定 343 のまま。
- 変化した 16 ブロックはすべて、M3 と PM0198 の曖昧だったもの。原文はすべてムニキスゼロの記載（「ムニキスゼロ [M3]」「■拡張パック「ムニキスゼロ」(M3)」など）で、変更後は ムニキスゼロ（id 12、code M3）に RAWCODE で確定する。正しい確定。
- S4（短い記号での確定）の件数が 88 → 104。上記 16 ブロックが 2 文字の mark M3 で確定するため（既存の定義どおりで、新たな誤りではない）。

合成プローブ（短い文字列、match_product）:

| 文字列 | 現在 | 変更後 |
|---|---|---|
| MEGAドリームex | matched: PM0198（SK） | matched: PM0198（SK） |
| M2a | unmatched | matched: PM0198（RAWCODE） |
| [M2a] | unmatched | matched: PM0198（RAWCODE） |
| M3 | ambiguous: M3/PM0198 | matched: M3（RAWCODE） |
| ムニキスゼロ [M3] | ambiguous: M3/PM0198 | matched: M3（RAWCODE） |
| メガドリーム M2a | matched: PM0198（SK:メガドリーム） | matched: PM0198（RAWCODE） |
| M2a BOX | unmatched | matched: PM0198（RAWCODE） |
| M3 BOX | ambiguous: M3/PM0198 | matched: M3（RAWCODE） |
| MEGAドリームex M3 | ambiguous: M3/PM0198 | ambiguous: M3/PM0198 |
| M2 a | matched: M2 | ambiguous: M2/PM0198 |
| M2ab | unmatched | matched: PM0198 |

- 副作用: 正規化が空白を除く（backend/app/services/extraction_judgement_svc.py:38-39）うえ、3 文字の値は語境界を要求しない（同 :57-59）ため、「M2 a」「M2ab」のような文字列が新しい mark "M2a" に当たる。「M2 a」は M2（インフェルノX）と PM0198 の曖昧になる。T2 には該当ブロックなし。
- 矛盾する入力（「MEGAドリームex M3」）は変更後も曖昧のまま。

## v6 への影響（コードで確認）
- backend/app/services/tcg_analyzer_svc.py:1219-1221: 有効な全商品の mark → id を読む。
- backend/app/services/tcg_analyzer_svc.py:1223-1224: `rawcode_to_id` を mark → id で作り、product_code → id で上書き（product_code 優先）。
- backend/app/services/tcg_analyzer_svc.py:1431: Gemini v6 の raw_product_code を `rawcode_to_id` で完全一致引き。
- "M2a": 現在は code・mark とも M2a の有効商品なし → 対応なし。変更後は id 440559（PM0198）に対応。
- "M3": 変更前後とも id 12 に対応（id 12 の product_code が M3 で、:1224 の上書きが優先される。変更後は mark M3 を持つのも id 12 のみ）。
- 作業参照のダイジェスト: 全有効商品の mark が作業参照に入る（backend/app/services/tcg_work_reference.py:86-94、ダイジェスト :30-31）。変更後は保存済み v5 以降ジョブの再解析が `Work reference changed; re-extraction required` になる（backend/app/services/tcg_analyzer_svc.py:1258-1259）。商品マスタを 1 件変えれば同じ結果になる既存の挙動。
- 未確認: Gemini の選択が変わるか（作業参照の mark が変わるため）。

## 手順（この順。各ステップを実行し、結果を確認してから次へ）
1. precheck: `precheck.sql`（読み取り専用）。id 440559 が現在値（mark M3、キーワード不変）と一致しなければ RAISE して止まる。
2. dryrun: `dryrun.sql`（apply と同一処理 → 最終状態を SELECT → ROLLBACK）。
3. apply: `apply.sql`（1 トランザクション、末尾 COMMIT。UPDATE は 1 行、最終状態＝目標でなければ RAISE して全体が戻る。audit_log を 1 行書く）。
4. postcheck: `postcheck.sql`（読み取り専用）。mark M2a・キーワード不変を確認し、audit_log の行を表示。
- 戻し: `rollback.sql`（mark を M3 に戻す。実行には新たな PO の判断が必要）。
- SQL は `gen_sql.py` で生成した（仕様表から 5 本）。手で直さず、仕様表を直して再生成する。
- 各ステップの実行結果とログは、実行後にこの README の「実行記録」に追記する。

## ファイル
README.md / recon.md / gen_sql.py / precheck.sql / dryrun.sql / apply.sql / rollback.sql / postcheck.sql / logs/（dryrun.log, apply.log, postcheck.log）

## 実行記録（2026-10-05、PO 承認済みの本番データ変更）
許可: PO が「psql write」チケットを 2 回発行（各 1 回限り）。1 回目 2026-10-05T00:32:41Z（dryrun 用）、2 回目 2026-10-05T00:33:29Z（apply 用）。

| 順 | 内容 | 実行時刻 (UTC) | ファイル sha256 | 結果 |
|---|---|---|---|---|
| 1 | dryrun（最後は ROLLBACK） | 2026-10-05 00:32:52 | 58e005db4b7c5ea8d46e5ab45bde2bda36cbb1fbb0a0205f3101978ec67e090c | 成功。何も保持されない。ログ: logs/dryrun.log |
| 2 | apply（COMMIT） | 2026-10-05 00:33:42 | 4222f235265913cde25a3da3d177759d91432ff0ca2119a669ffb0d389656c7e | 成功。COMMIT。ログ: logs/apply.log |
| 3 | 実行後の確認（読み取り専用の SELECT） | 2026-10-05 00:34 頃 | （ファイルは使わず、クエリ文をログ先頭に記載） | 目標と一致。ログ: logs/postcheck.log |

- 差分: dryrun.sql と apply.sql の違いは、先頭 2 行のコメントと最終行（ROLLBACK → COMMIT）のみ（diff で確認）。
- 件数（apply）: products の UPDATE 1 件（1 行）。キーワードの削除・挿入は 0 行（キーワードは変更していない）。audit_log 1 行（id 27、changed_by = 'claude-opus (PO承認 2026-10-05)'、changed_at = 2026-10-05 00:33:42.916535+00）。
- 実行後の確認:
  - id 440559（PM0198）は mark M2a、name MEGAドリームex、updated_at 2026-10-05 00:33:42.916535+00。
  - id 12（ムニキスゼロ）は変化なし（code M3、mark M3、updated_at 2026-10-02 11:34:44.457428+00）。
  - 有効な商品のうち、mark または product_code が M3 のもの: 1 件（id 12。mark と code の両方が M3）。mark または product_code が M2a のもの: 1 件（id 440559。mark のみ）。
  - audit_log の changed_by = 'claude-opus (PO承認 2026-10-05)' の行: 1 件（id 27）。
- rollback.sql は実行していない。実行するには新たな PO の判断が必要。
- 位置番号や他商品への変更はない（UPDATE は id 440559 の mark のみ）。
- 未確認: 保存済みジョブの再解析は、作業参照のダイジェスト変更により再抽出が必要（影響の節のとおり）。Gemini の選択が変わるかは未確認。
