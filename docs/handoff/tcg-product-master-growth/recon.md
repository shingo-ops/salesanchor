# recon — TCG商品マスタ育成

この文書は何か（専門用語なしの1行）: 商品の辞書を増やして自動判別の精度を上げる作業に入る前に、今どうなっているかを実測だけで書き出した現状報告。

親（設計仕様書）へのリンク: ../../specs/product-master/README.md

- 仕事名: tcg-product-master-growth
- 日付: 2026-09-04
- 実測時の origin/main SHA: 0d329d404471a80b39dd2144734c2e44426da8ca
- 対象ADR: ADR-154
- 担当: architect
- 区分（STANDARD-WORKFLOW 1.8）: 既存の延長・修正（索引 docs/specs/README.md に「商品マスタ … 公開」が在るため新規仕様書を作らない）

本reconで「部品」とは次の3種を指す。① 照合ロジックの関数 ② マスタテーブル ③ キーワードデータ。

---

## 0. 既存ADR検索の結果

実行コマンドと結果（SHA 0d329d40 で実測）。

- git grep -il "keyword" -- docs/adr/ → ADR-029 / ADR-093 / ADR-099 / FEATURE-INDEX.md
- git grep -il "tcg" -- docs/adr/ → ADR-014 / ADR-021 / ADR-046 / ADR-047 / ADR-049 / ADR-054 / ADR-057 / ADR-083 / ADR-084 / ADR-090 / ADR-093 / ADR-110 / ADR-143 / ADR-152 / ADR-154 / README.md
- git grep -il "product master" -- docs/adr/ → NO_MATCH

本テーマの直接の正本は ADR-154。docs/adr/ADR-154-tcg-parity02-gas-python-migration.md:23 に決定事項、同:30 に検証基準。

---

## 1. 全体像

照合の入口と流れ。

- backend/app/services/tcg_analyzer_svc.py:887 で extraction_items から raw_product_name と raw_memo を取得する。
- backend/app/services/tcg_analyzer_svc.py:922 で raw_memo を正規化し norm_memo を作る。
- backend/app/services/tcg_analyzer_svc.py:937 で商品照合を呼ぶ。渡す引数は norm_product_name / filtered_codes / search_kw / exclude_kw の4つ。
- backend/app/services/tcg_analyzer_svc.py:758 の build_note_ja が raw_memo を使う。用途はメモ文の生成であり、商品の判定ではない。
- backend/app/services/tcg_parallel_report_svc.py:235 が同じ照合関数を別経路（レポート用）で呼ぶ。

事実: 商品の判定に渡る文字列は商品名だけである。メモ欄は判定に渡らない。

---

## 2. 共用部品

- backend/app/services/tcg_analyzer_svc.py:277 match_keyword — 検索語と除外語の照合本体。
- backend/app/services/tcg_analyzer_svc.py:302 除外語チェック。1語でもヒットしたら候補から外す。
- backend/app/services/tcg_analyzer_svc.py:308 検索語が空の商品は候補にしない。
- backend/app/services/tcg_analyzer_svc.py:323 filter_product_codes_by_unit_kubun — 単位が箱系のとき候補を箱系商品に絞る。ゼロ件ならフォールバックで全件に戻す。
- backend/app/services/tcg_analyzer_svc.py:347 match_pid_name_first — 商品ID解決の本体。
- backend/app/services/tcg_analyzer_svc.py:380 候補0件で NONE を返す。
- backend/app/services/tcg_analyzer_svc.py:387 候補1件で SK:キーワード を返し解決済みとする。
- backend/app/services/tcg_analyzer_svc.py:394 候補2件以上で MULTI を返す。最長マッチの1件を product_id に入れるが解決済みとはしない。

マスタテーブル（tenant_004・読み取り専用セッションで実測）。

- tcg_products 268件。最新コード PM0268。english_title が空 17件。
- product_search_keywords 593件。
- tcg_series 11件 / tcg_manufacturers 5件 / tcg_product_categories 2件 / tcg_major_categories 3件。

---

## 3. 非共用部品

キーワードを扱う個別実装（git grep -l product_search_keywords で列挙・SHA 0d329d40）。

- backend/app/tasks/tcg_mirror.py
- backend/tcg_migration/scripts/ingest_to_prod.py
- backend/tcg_migration/scripts/write_mirror_once.py
- backend/tcg_migration/scripts/verify_acceptance.py

いずれも移行・同期用の個別スクリプト。本reconでは中身を読んでいない。共用化の要否は未判定。

---

## 4. ルールの所在

- docs/adr/ADR-154-tcg-parity02-gas-python-migration.md:27 ENGINE_VERSION を name-first-v2 に統一する。
- docs/adr/ADR-154-tcg-parity02-gas-python-migration.md:28 GAS Phase 3 の実行順序を Python で完全再現する。
- backend/tcg_migration/MIGRATION_LOG.md:17 2026-09-03 の match_keyword 修正で MULTI 1340件から46件、pid_resolved 286件から1294件へ変化した記録。
- backend/tcg_migration/MIGRATION_LOG.md:138 MULTI 1340件は Phase E 測定で初めて発見・修正されたとの記録。
- docs/specs/product-master/README.md 商品マスタの理想形（親の正本）。

事実: 現行ロジックは GAS の移植であり、GAS の挙動を正とする制約下にある。

---

## 5. 維持の仕組み

守り手の実物。

- backend/tests/test_tcg_keyword_matching.py:130 AR が CARD にヒットしないことを検査する。
- backend/tests/test_tcg_keyword_matching.py:135 AR が単独語としてはヒットすることを検査する。
- backend/tests/test_tcg_keyword_matching.py:211 検索語が空の商品は候補にならないことを検査する。
- backend/tests/test_tcg_keyword_matching.py:217 検索語が空の商品はいかなる商品名でも候補にならないことを検査する。
- backend/tests/test_tcg_keyword_matching.py:287 候補2件以上で MULTI になることを検査する。

守り手が無い箇所（名指し）。

- キーワードデータそのものの品質を検査する機械は存在しない。2商品以上にヒットするキーワードの登録、3文字以下のキーワードの登録、キーワードが1件も無い商品の存在を止める仕組みが、リポジトリ内に見当たらない。
- 実測: product_search_keywords に AR が在り、3商品にヒットしている。1文字から3文字のキーワードが21種・23行在る。キーワードが1件も無い商品が1件（PM0146）在る。
- 現状の守り手は人手のみ。

---

## 6. 設計図との対照（一致／不足／余剰）

親 docs/specs/product-master/README.md の記述と、tenant_004 の実物の対照表。

| 設計図の項目 | 現状値（実測） | 判定 |
|---|---|---|
| 日本語名を直接持つ | japanese_title が NOT NULL で存在 | 一致 |
| 英語名を直接持つ | english_title が存在（NULL許容・空17件） | 一致 |
| 型番（Mark）を直接持つ | mark が存在 | 一致 |
| 発売日を直接持つ | release_date が存在 | 一致 |
| 検索キーワードを直接持つ | 別表 product_search_keywords で保持（593件） | 一致（保持形式は別表） |
| 除外キーワードを直接持つ | 別表 product_exclude_keywords が存在 | 一致（保持形式は別表） |
| 判定の正解値を直接持つ | required_output_value が存在 | 一致 |
| 1ケースの箱数を直接持つ | tcg_products に該当列なし | 不足 |
| 1箱のパック数を直接持つ | tcg_products に該当列なし | 不足 |
| 容積を直接持つ | tcg_products に該当列なし | 不足 |
| 箱の重さを直接持つ | tcg_products に該当列なし | 不足 |
| ケースの重さを直接持つ | tcg_products に該当列なし | 不足 |
| 最小発注数を直接持つ | tcg_products に該当列なし | 不足 |
| 関連シリーズを直接持つ | tcg_products に該当列なし | 不足 |
| 種類分けをマスタから選ぶ | product_category_id が tcg_product_categories を参照（2件） | 不足（名称・粒度が設計図と不一致） |
| 品目をマスタから選ぶ | 該当FKなし | 不足 |
| HTSコードをマスタから選ぶ | 該当FKなし | 不足 |
| 素材をマスタから選ぶ | 該当FKなし | 不足 |
| 設計図に記載なし | division_id が tcg_major_categories を参照（3件） | 余剰・要判定 |
| 設計図に記載なし | work_id が tcg_series を参照（11件） | 余剰・要判定 |
| 設計図に記載なし | manufacturer_id が tcg_manufacturers を参照（5件） | 余剰・要判定 |
| 設計図に記載なし | category_class が NOT NULL で存在 | 余剰・要判定 |
| 設計図に記載なし | products_logistics が tcg_products を参照 | 余剰・要判定 |

余剰5項目は、POが「残す（あるべき姿に採用）」か「除く」かを判定する対象。本reconでは判定しない。

---

## 7. ノイズと境界

本reconで見ないと決めた範囲。

- analysis_results への書き込み（別セッションの担当）。
- 移行スクリプト4本の中身（backend/tcg_migration/scripts/ 配下・存在のみ確認）。
- 配信対象の抽出条件。status の内訳は In Stock 1585件 / Sold out 41件であり、引き継ぎ資料の「配信対象707行」に対応する条件は特定できていない。
- 商品マスタの重複登録の有無。ONE PIECE magazine Vol.21 が PM0267 と PM0190 の2商品にヒットしている事実のみ確認。

数え上げの単位。

- 「行」は analysis_results の1行を指す（全1626行）。
- 「種」は extraction_items.raw_product_name の異なり数を指す。
- pid_basis が NONE の286行は184種。判定軸は pid_resolved であり product_id の空・非空ではない。MULTI の46行にも product_id は入っている。

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|---|---|---|
| 1 | 未解決184種をどの商品として登録するか | POの判断とキーワード設計 | 未解消 |
| 2 | 配信対象707行の抽出条件 | 配信側コードの実測 | 未解消 |
| 3 | PM0267 と PM0190 が重複登録か | 両商品の内容比較 | 未解消 |
| 4 | 移行スクリプト4本が現役か廃止済みか | 中身の実測 | 未解消 |
| 5 | 余剰5項目を残すか除くか | POの判定（design-partner.md 4.5 の3） | 未解消 |
| 6 | MULTI 46行のうち商品名に判別情報が無い30行をどう扱うか | 設計局面で検討 | 未解消 |

未解決ゼロ確認: 未解決6件あり。いずれも本reconの範囲外であり、設計局面またはPO判断で解消する。

---

## 現在地更新（2026-09-05）

2026-09-05 に28本のPRがマージされ、LINEエクスポート取り込みパイプライン（MIG-04）が本番稼働した。
本テーマ（商品マスタ育成）の現在地は以下を参照。

- 実測記録: docs/handoff/tcg-2026-09-05-summary/recon.md
- 本日の主な進展: ポケモン商品25件・仕入元15件の登録、解析パイプライン自動化有効化、複数の本番障害修正
- 未解決: キーワード品質検査の機械化、仕入元名重複確認、「〆」投稿による在庫全消え対策

---

## 実測の出所

- DB実測: ssh 経由で docker exec -e PGOPTIONS="-c default_transaction_read_only=on" psql を使用。全クエリで transaction_read_only=on を事前確認済み。書き込みは一切行っていない。
- ファイル実測: git show および git ls-tree を SHA 0d329d404471a80b39dd2144734c2e44426da8ca 指定で実行。ローカル作業ツリーは読んでいない。

---

## 2026-09-08 キーワード整備 v4

### 実測の出所

実メッセージ2ファイル（LINE エクスポート、延べ約98万行）から商品名の候補行
37,865種を抽出し、3回以上出現する12,023種を対象に照合を再現して検証した。

- `_LINE_WeGo売ります_BOXカートンパック.txt`（92,163行）
- `_LINE_WEGOメンバーさん向け内部での商品/個人間取引情報_外注委託受託共有.txt`（985,955行）

### 照合エンジンの実測（backend/app/services/tcg_analyzer_svc.py）

- `normalize_en` は全角英数記号（U+FF01–FF60）→半角と小文字化のみを行う。
  装飾記号の除去は別処理で、`tenant_004.tcg_normalization_rules` の
  `PRODUCT_NAME` ルール（`REMOVE`）が担う。`apply_field_normalization` の
  結果が `match_pid_name_first` に渡ることを実行経路で確認した。
- `match_one_kw` は2つのモードを持つ。
  - 純ASCII語（`^[\x20-\x7e]+$`）: 単語境界照合 `(?<![a-z])kw(?![a-z])`。
    スペースを含む語はその並びのまま探す。数字は境界とみなされない。
  - 日本語混じり: `token_and_match`。空白で分割し全トークンが部分文字列として
    含まれれば当たる（単語境界なし・順不同）。
- `match_keyword` は除外語を検索語より先に評価し、1語でも当たれば候補から外す。
- 大文字小文字は区別しない（原文・キーワードとも小文字化される）。

### 変更の要点

1. 「商品名 型番」で1本にまとめられた網を分解し、商品名単体を追加した（18商品）。
   例: PM0143「二つの伝説 OP-08」は両方揃わないと当たらず、
   原文「二つの伝説」を取り逃していた。
2. 実メッセージに現れた別名・略記を追加した。
   例: PM0224 に「遊戯王 RIVALS」。純ASCII語は並びのまま照合されるため、
   原文「LIMIT OVER COLLECTION -THE RIVALS」は既存の網では当たらなかった。
3. バルク系（PM0002〜PM0011）の壁を単語に分解した。
   「SAR バルク」は日本語混じりで両トークンが必要だったが、「SAR」単体にして
   壁として機能させた。PM0004 にあった連結事故「RR バルクSARバルク」も解消した。
4. PM0097 の壁を4本に分解した（PM0098 と対称にした）。
5. PM0137 の網を「THE BEST」に広げ、壁（`OF XY` `ストレージ` `vol.2` `PRB-02`）で
   別商品を弾く形にした。

### 検証結果（12,023種で照合を再現）

| 変化 | 延べ件数 |
|---|---|
| MULTI から単独へ | 1,356 |
| NONE から単独へ | 1,224 |
| MULTI4 から MULTI2/3 へ（候補が絞れた） | 214 |
| 単独から NONE へ（悪化） | 5 |

悪化5件は「クレイバースト＆スノーハザード ジムセット」（語順が逆）。
PM0099 の網が「スノーハザード&クレイバースト…」の順のため当たらない。
件数が小さいため、網を増やさず受け入れる。

### 保留した判断

- **型番の自動照合**: `tcg_products.mark` を照合エンジンが直接参照する案を検討したが、
  仕入元が型番を1つズラして書く誤記が267件あることを実測した。
  例: 原文「■強化拡張パック「ナイトユニゾン」(SM9a)」— マスタでは SM9a はダブルブレイズ。
  自動参照にすると、現在は商品名で正しく解決できている267件が MULTI に落ちる。
  ポケモンを除外すれば回避できる見込み（`work_id` で判定可能）。別便で設計する。
- **AR/CHR のダブり指定なし原文（約2,000件）**: PM0007/0008/0009 の網から「AR」を
  外すと守り手①違反は解消するが、これらが MULTI から NONE に落ちる。
  MULTI のほうが「この3つのどれか」と分かるぶん情報量が多いため、網は現状維持とした。
  解決には「ダブり指定なしの AR/CHR」という商品をマスタに追加する必要がある。別便。

### 参考: 作品マスタ

`tcg_products.work_id` は `tcg_series` を指す。有効293件の内訳。

| コード | 作品 | 商品数 |
|---|---|---|
| IP001 | ポケモン | 202 |
| IP002 | ワンピース | 33 |
| IP004 | 遊戯王 | 19 |
| IP010 | ロルカナ | 12 |
| IP003 | ドラゴンボール | 11 |
| IP007 | Weiss Schwarz | 10 |
| IP005 / IP006 | ユニオンアリーナ / ガンダム | 3 / 3 |
| IP008 / IP009 / IP011 | デジモン / ホロライブ / クロススターズ | 0 |
