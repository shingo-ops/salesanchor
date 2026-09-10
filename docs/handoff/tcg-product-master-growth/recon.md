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

---

## 2026-09-09 取り込みから Gemini 抽出・解析までの経路

出所: CARD-PMG-FLOW-RECON-01 / -02 / -03 / -04（読み取りのみ・DB接続なし）。
実測時の origin/main SHA は便ごとに動いた: 060ac986 → 764c2167 → 038df9f9。
本節の file:line は 038df9f9 時点の値である。

### 1. ファイル単位の冪等化がある

- backend/app/services/tcg_line_import_svc.py:448 「ファイル全体の sha256 で冪等化チェック」
- 同:476 file_sha256 = sha256_text(export_text)
- 同:479 SELECT id, status FROM import_jobs WHERE raw_sha256 = :sha256
- 一致する行が在れば status="already_imported" を返し、source_messages も extraction_jobs も書かない。

### 2. メッセージ単位の重複判定は存在しない

- 窓フィルタは同:181 と :183 の timestamp 比較のみ。取り込み済みか否かは見ていない。
- 窓は同:176 の _compute_window(window_hours, window_start, window_end) で決まる。window_hours=0 で無効化。
- 同:37 JST = timezone(timedelta(hours=9))。同:17 に「旧実装は UTC 基準で実質 33h」との記載がある。

### 3. 仕入元ごとに1通だけ採用する（SQR-05）

- 同:271 build_provider_entries。sorted_msgs = sorted(msgs, key=lambda m: m["timestamp"]) の昇順、
  latest_msg = sorted_msgs[-1]、raw_text = latest_msg["body"]。採用されるのは最新の1件。
- skipped_message_count = len(sorted_msgs) - 1。残りは採用されない。
- received_at = sorted_msgs[0]["timestamp"]（最古）。canonical_name も sorted_msgs[0] から取る。
  事実: source_messages.received_at に入る時刻は、raw_text の投稿時刻ではなく窓内最古の投稿時刻である。
  本テーマでは是正しない。time-handling-ssot へ引き渡す。
- sha256 は採用した1件の本文に対して計算され、同:396 で source_messages.raw_sha256 に入る。重複判定には使われない。
- skipped_message_count は import_jobs の INSERT 列（同:211 から :214）に含まれない。DBに残らない。

### 4. 取り込みは世代交代を起こす

- 同:364 SELECT id FROM source_messages WHERE supplier_channel_id = :scid AND is_active = TRUE
  （時刻・本文の条件は無い）
- 新しい id を uuid4 で作り、同:384 で INSERT する（is_active = TRUE）。
- 同:406 で上記の従来行を superseded_by = 新id / is_active = FALSE に更新する。
- 同:418 で extraction_jobs に status='pending' を1件 INSERT する。
- 配信と確認画面は sm.is_active = TRUE で絞る
  （tcg_distribution_svc.py:229 / tcg_analysis_review_svc.py:35）。
  よって前回取り込み分は、analysis_results が残っていても画面と配信に出ない。

### 5. Gemini 抽出の対象は新着のみ

- backend/app/tasks/tcg_extraction.py の _run_extraction は
  WHERE ej.source_message_id = :smid AND ej.status = 'pending'
  ORDER BY ej.created_at DESC LIMIT 1 で1件だけ取る。
- status='done' のジョブを再び読む経路は無い。再抽出は
  backend/app/routers/tcg_diagnostics.py:14 の再エンキュー（status を pending に戻す）でのみ起きる。

### 6. システム解析の対象は当該ジョブのみ

- backend/app/services/tcg_analyzer_svc.py:850 analyze_extraction_job(session, extraction_job_id)。
- extraction_items を WHERE extraction_job_id = :ej_id で取得する。
- 同:974 analysis_results を UPSERT する（extraction_item_id に UNIQUE 制約）。
- 呼び出しは tcg_extraction.py:225。TCG_AUTO_ANALYZE=1 かつ final_status が done のときのみ。
- 全件を再解析する経路はコード内に無い。単一ジョブ再解析は
  tcg_product_master_svc.py:689 reanalyze_extraction_job。

### 7. 本節で確認していないこと

- 未解決の仕入元が在るときの保留と commit 経路の実装。
  router 側 tcg_line_import.py:621 が同じ _write_source_messages を呼ぶことのみ確認した。
- skipped_message_count が本番で何件発生しているかの実測値。
- 世代交代で is_active = FALSE になった source_messages の実測件数。
- parse_line_export の実装（同一投稿者の連続投稿をどう1件に区切るか）。

---

## 2026-09-10 LINE解析精度の読み取り調査（暫定・本番の正解率は未計測）

この追記は、LINE原文が別商品として解決済みになる可能性と、精度改善を妨げる処理を調べた記録である。

- 依頼: 「LINEメッセージの解析精度を向上させたい、現在の解析情報を確認してボトルネックを確認してくれ」。追加条件: 「解析されていても違う商品に誤って解析されている可能性もあるので確認すること」。
- 担当: Codex（設計担当の読み取り調査）。設計審査・PO承認・実装承認は行っていない。
- 固定コード: `8206ba2844921c1efb3ca4fd647230e76bb0c5c6`。`git ls-remote origin refs/heads/main` とローカル origin/main の一致を確認。以下のコード行番号はこのSHAを指す。
- 親仕様: [提供元フィード翻訳](../../specs/inventory-management/feed-translation/README.md)、[商品マスタ](../../specs/product-master/README.md)。既存の [精度の物差し計画](../../specs/product-master/dev-plans/precision-benchmark.md) を参照。独立テーマは新設しない。
- 本調査の「部品」: 取り込み、AI抽出、抽出応答の読解、辞書照合、数値変換、確認表示、人の訂正記録。

### 1. 全体像

| 工程 | 根拠（固定SHAの path:line） | 確認した点 |
|---|---|---|
| 原文取り込み | backend/app/services/tcg_line_import_svc.py:271 | 提供者内の最新投稿1件を採用する。取り込み漏れと抽出漏れは別に計測する必要がある |
| AI抽出 | backend/app/services/gemini_extraction_svc.py:31 | 共通プロンプトで7列を抽出。呼び出し引数は原文のみ |
| 抽出応答の読解 | backend/app/services/gemini_extraction_svc.py:177 | 全角パイプの7列形式と行番号を読む |
| 商品照合 | backend/app/services/tcg_analyzer_svc.py:993 | 正規化した商品名と単位による候補絞り込みを使用。原文全体・仕入元・訂正履歴は商品照合関数の引数にない |
| 確認画面 | backend/app/services/tcg_analysis_review_svc.py:81 | NORMAL_COMPLETEDは商品解決・単位解決・exclusion=NULL。原文との正解照合ではない |
| 出力 | backend/app/services/tcg_distribution_svc.py:238 | 商品解決・単位解決・価格存在・condition条件を使用。人による商品正解確認は本SQLの条件にない |

### 2. 共用部品と再現結果

固定SHAの純関数をASTで抽出してローカル実行した。DB/API/再解析タスクは呼んでいない。初回の再現スクリプトでは補助定数の読み込み漏れが発生し、定数を同じSHAから取得して再実行した。下表は修正後の出力である。

| 観測 | 結果 | 根拠 |
|---|---|---|
| 候補が1商品なら解決済み | 商品の意味的な正誤・作品・版の独立照合はない | backend/app/services/tcg_analyzer_svc.py:384 |
| 版違いの単独誤一致の再現 | 第2弾を示す末尾数字2付きの表記が第1弾に解決済みとなる条件を再現 | backend/app/services/tcg_analyzer_svc.py:256、:384。ローカル監査JSONのprobes |
| 商品マスタ自身の日本語名を入力 | 手元の有効293商品: 正しい単独238、別商品単独1、複数32、未一致22 | ローカル監査JSON export-before-v4。現本番の精度ではない |
| 同じ書き出しに9/8変更SQLの値だけをメモリ上で適用 | 正しい単独255、別商品単独0、複数29、未一致9。末尾数字2の誤一致条件は残る | ローカル監査JSON export-plus-v4-file-SIMULATION。SQL実行・本番適用確認はしていない |
| AI応答で有効1行＋列数不正1行 | 不正行を捨て、status=done、error_message=null | backend/app/services/gemini_extraction_svc.py:210、:283 |
| AI応答でヘッダーなし | status=empty、error_message=null | backend/app/services/gemini_extraction_svc.py:204、:283 |
| 商品Bの出典行番号が不正 | 先頭1行目に置き換え、status=done | backend/app/services/gemini_extraction_svc.py:234 |
| 数値表記の変換（合成入力） | 1.5万円→1.5、1〜3→13.0、10,000円→10000.0、〆→null | backend/app/services/tcg_analyzer_svc.py:637 |

版違いの再現の限界: 9/10朝のLINE書き出し98,904行を読み、対象の末尾数字2表記15行を確認したが、15行とも型番が併記されていた。型番が抽出後の商品名に残れば除外語が効き得るため、この再現を「本番15件が誤判定」と解釈してはならない。正規化ルールと単位区分マスタのスナップショットも未取得であり、再現は商品名照合層だけである。

### 3. 非共用部品・訂正の扱い

- 仕入元別の抽出プロンプトは、このTCG経路には渡されない（backend/app/tasks/tcg_extraction.py:149、backend/app/services/gemini_extraction_svc.py:147）。他の在庫解析経路にある機能と混同しない。これが何件の誤りを生むかは未計測。
- 再解析のUPSERTは商品ID・解決状態・根拠を無条件更新する（backend/app/services/tcg_analyzer_svc.py:1080）。人の判定を守るPR #3248は、`gh pr view 3248 --json number,state,headRefOid,title,url` でOPEN、head=`d074db1ae6d9120f669177810d2ecca153b66879` を実測した。本番で実際に上書きされた件数は未確認。
- 抽出サービスはraw_responseを返すが、タスクの保存処理は使用していない（backend/app/services/gemini_extraction_svc.py:288、backend/app/tasks/tcg_extraction.py:151）。列数不正で捨てた行をDBの抽出明細だけから数え直すことはできない。

### 4. ルールの所在

- ADR-154はGASとの処理互換を規定する。旧システムとの一致は人間の正解との一致を証明しない。
- docs/specs/inventory-management/feed-translation/kgi.md:8 は、人間の正解5項目（商品名・単位・状態・価格・在庫数）との一致を要求する。
- docs/specs/product-master/dev-plans/precision-benchmark.md の「弊害・限界」は、基準が現状の答えであり既存誤判定を固定すること、AI抽出は測定対象外であることを明記している。
- 外部事例は使っていない。今回は当該コードと手元データの診断であり、外部の改善率を本システムの証明として用いる必要はない。ライブラリ/API仕様の断定も行っていない。

### 5. 維持の仕組みと測定上の空白

- キーワード品質検査は既に存在する（backend/app/services/tcg_keyword_lint.py:35）。過去reconの「存在しない」は現状として採用しない。ただし原文の正解商品を判定する検査ではない。
- 既存抽出テストはAI呼び出しを差し替える（backend/tests/test_tcg_gemini_extraction.py:183）。今回の応答形式の再現も合成入力であり、モデルの実精度測定ではない。
- 仕入元品質サマリーの件数は、商品未解決・単位未解決・除外の状態を集計する（backend/app/services/tcg_supplier_quality_svc.py:31）。誤って単独商品に解決した行はこの条件だけでは検出できない。
- 最新コードのnote_unmatchedはneeds_reviewに入る（backend/app/services/tcg_analyzer_svc.py:822）が、確認画面の正常/要確認タブはar.needs_reviewを参照していない（backend/app/services/tcg_analysis_review_svc.py:69）。注記未解決の見落とし条件もある。

### 6. 設計図との対照（今回の診断対象）

| あるべき姿 | 現状 | 判定 |
|---|---|---|
| 原文を保持し解析結果を追える | source_messagesとextraction_itemsの参照がある。ただし不正SPANは先頭に補正する | 一致する部分あり・出典の厳密性は不足 |
| 別商品を区別し、不明は人に伝える | 複数候補は要確認になる。単独誤一致は解決済みになる | 不足 |
| 人間の正解5項目と一致する | 単独一致率と正解率を分ける現本番の実測値がない | 不足・率は未確認 |
| 仕入元固有表記を扱う | 本TCG抽出経路は共通プロンプトのみ | 不足 |
| 人の修正を財産にし一度教えたことを忘れない | 訂正テーブルと確認表示はあるが、再解析の保護PRはOPEN | 一致する部分あり・保護は不足 |

これは親仕様全体の完了審査ではない。未調査の仕様を合格としない。

### 7. ノイズ・境界・未確認事項

- 8/20の抽出バックアップを別に検査: 180メッセージ、1,475商品行、単位空欄332行、数量に〆が入り状態空欄4行。旧データであり、現在の誤り件数・単位復旧後の件数ではない。
- 過去報告の1,294/1,626の解決や12,023種の改善数を、今日の正解率として引用しない。
- 本番DB・管理画面の保存済み判定・最新マスタ値・実配布SHAは今回直接読めていない。無制限SSH鍵・ブラウザの認証情報は使用していない。
- 現在提供されているツールにはBrowserスキルが必要とするNode REPL jsがなく、ブラウザ接続は実施していない。認証済み診断APIの利用情報も未提供。
- 現在の原文→抽出名→判定商品→判定理由→人の正解を同じ行IDで比較する必要がある。「正常完了」を必ず含め、無作為標本と、版違い・短い略語等の高リスク標本を分離する。標本数と不一致数を併記し、未解決率とは別に誤商品率を測る。
- 提案優先順（未承認）: 正常完了の正解照合→単独誤一致と出典・数値の検証→人の訂正保護→辞書・抽出プロンプトの改善。影響件数が未計測なので頻度順位とは称さない。

### 再現物・状態

- ローカル再現スクリプト: /private/tmp/line-accuracy-audit-20260910.py。
- 再現結果: /private/tmp/line-accuracy-audit-20260910.json、/private/tmp/line-accuracy-parser-probes-20260910.json。個別原文・マスタ書き出しはリポジトリへ複製していない。
- 自分で実行した検証: 固定SHAコードの読み取り、商品名照合のローカル再現、応答形式・数値変換の合成入力再現、旧抽出バックアップ集計、PR #3248のOPEN確認。
- 調査は暫定。本番正解率未計測／設計案未作成／設計審査未実施／実装未着手。利用者から解析済みデータの読み取り先を確認中。

---

## 2026-09-10 追加調査: 保存済み判定の誤商品20行

**対象は2026-08-26 09:20:10 UTCの保存済みバックアップです。現在の本番で残っている件数ではありません。**

解析1,086行と出力1,086行をdataRowで照合し、商品ID・抽出名の不一致は0行。商品解決YESは882行。原文に戻って少なくとも20行の別商品判定を確認しました。残り862行を正しいと判定したわけではなく、この20/882は正解率・誤り率の推定には使えません。

20行のうち15行はFLAG_SINGLE、5行はそれ以外です。商品IDの取り違えと配信可否は別です。顧客に送られたことは確認していません。

| 保存行番号 | 原文が示す商品 | 保存された別商品 | 判定根拠 | 原文の記録番号:実際の行番号 |
|---|---|---|---|---|
| 200 | スタートデッキ100 コロちゃお版 | PM0200 MEGA スタートデッキ100 バトルコレクション | SK:スタートデッキ100 | 2:144 |
| 392 | ガンダム Eternal Nexus [EB01] | PM0123 メモリアルコレクション | SK:EB01 | 4:149 |
| 449 | 一番くじ ルフィ プロモ OP13-001 | PM0181 受け継がれる意思 | SK:OP13 | 6:43 |
| 453 | プレミアムカードコレクション 6 assort vol.1 | PM0230 トライアルデッキ 【推しの子】 | SK:vol.1 | 6:47 |
| 639 | 151のマスターボールミラーカード | PM0104 ポケモンカード151 | SK:151 | 11:109 |
| 785 | ヴァイスシュヴァルツ 勝利の女神：NIKKE Vol.2 | PM0225 UNION ARENA 勝利の女神NIKKE【PC02BT】 | SK:NIKKE | 17:12 |
| 792 | ガンダム EB01 | PM0123 メモリアルコレクション | SK:EB01 | 17:33 |
| 818 | OP-17プロモパック | PM0266 世界最強の戦士 | SK:OP-17 | 19:7 |
| 854 | ロケット団のミュウツーSAR（単品カード） | PM0161 ロケット団の栄光 | SK:ロケット団 | 20:13 |
| 861 | メガゲンガーex SAR（単品カード） | PM0184 スターターセットMEGA メガゲンガーex | SK:メガゲンガー | 20:20 |
| 865 | リザードンex SAR #134（単品カード） | PM0131 バトルマスターデッキ テラスタル リザードンex | SK:リザードンex | 20:24 |
| 868 | リザードンex SR #185（単品カード） | PM0131 バトルマスターデッキ テラスタル リザードンex | SK:リザードンex | 20:27 |
| 876 | ニンフィアex SAR（単品カード） | PM0139 スターターセット テラスタイプ：ステラ ニンフィアex | SK:ニンフィアex | 20:36 |
| 878 | メガゲンガーMA（単品カード） | PM0184 スターターセットMEGA メガゲンガーex | SK:メガゲンガー | 20:38 |
| 881 | ピカチュウVMAX #265（単品カード） | PM0074 VMAXクライマックス | SK:VMAX | 20:41 |
| 914 | スタートデッキ100 コロちゃお版 | PM0200 MEGA スタートデッキ100 バトルコレクション | SK:スタートデッキ100 | 22:30 |
| 997 | ピカチュウV S8a-G 001/015（単品カード） | PM0073 25th Aniniversary Golden Box | SK:ゴールデンボックス | 28:50 |
| 1030 | BASE SHOP vol.1のコレクション商品 | PM0230 トライアルデッキ 【推しの子】 | SK:vol.1 | 31:22 |
| 1041 | ブラホワ／テラスタルフェスのマスターボールミラーカード | PM0147 テラスタルフェスex | SK:テラスタルフェス | 32:20 |
| 1042 | テラスタルフェスのブイズRRコンプリートセット | PM0147 テラスタルフェスex | SK:テラスタルフェス | 32:23 |

元ファイル: /Users/tanizawashingo/Documents/tcg-inventory-parser-lineage-backup-2026-08-27

analysis-v2.jsonl / output-v2.jsonl / extraction-v2.json を使用。原文の記録番号はextraction-v2.jsonのrows配列の1始まり。行番号は当該記録の原文をsplitlinesした1始まりです。

原文の記録と解析行は提供者名・抽出名を照合し、対象20行すべてで対応記録1件、対象商品記述1箇所を確認しました。提供者名や原文全文は本一覧へ転載していません。

出典位置にも不一致があり、対象20行中7行は保存されたSPANの外に商品名がありました。上表は実際に探して確認した行番号です。

現行コード8206ba28と手元の旧マスタ＋9/8変更値のメモリ再現では、18行で同じ誤商品への単独一致条件が残り、コロちゃお版2行はPM0285に変わりました。これは最新本番マスタ・前処理を取得した再解析ではありません。

別枠の要確認: 保存行797のUA18BT→PC02BTは型番の不一致。商品マスタの表記誤りと商品そのものの取り違えをまだ区別できないため20行には含めていません。

商品区別の補強資料（公式）:

- ガンダム Eternal Nexus [EB01]: https://www.gundam-gcg.com/jp/products/eb01.html
- ヴァイスシュヴァルツ NIKKE Vol.2: https://ws-tcg.com/products/nik_bp2/
- コロちゃお版と通常版の区別: https://www.pokemon-card.com/info/005270.html
- BASE SHOPのコレクション商品: https://baseshop.onepiece-base.com/en/item/7qkdoa2wz3jj

本一覧は調査結果であり、正しい商品コードへの更新指示・本番変更承認ではありません。

再現スクリプト: /private/tmp/line-saved-misclassification-audit-20260910.py。個票・入力ファイルSHA256: /private/tmp/line-confirmed-misclassifications-20260910.json。

今回の状態: 過去の保存済み誤商品20行を確認・文書保存済み。現本番残存件数は未確認。設計審査未実施・製品実装未着手。


## 2026-09-10 要因分析とBOX系共通フィルターの相談（未承認案）

POからの提案は、検索ワードを網、除外ワードをフィルターとし、商品区分によってBOX系へ単品特有語の共通除外を適用し、状態・備考も除外対象にすること。実装承認として扱わない。

### 観測事実と原因

固定SHA `8206ba2844921c1efb3ca4fd647230e76bb0c5c6` の `backend/app/services/tcg_analyzer_svc.py` を確認した。

- 商品区分は実在する。135–152行で `tcg_products.product_category_id` と `tcg_product_categories.id` を結び `kubun_type` を取得する。現在の本番の全商品への設定状況は未確認。
- 322–343行の絞り込みは入力単位が箱系なら箱系商品へ限定するもの。それ以外は全候補のまま、箱系候補が空でも全候補へ戻る。単品の証拠によって箱系商品を拒否する共通フィルターではない。
- 276–317行は検索語のいずれかが一致し、除外語のいずれにも一致しない商品を通す。網とフィルターという考え方は既存処理に合う。
- 994–996行の商品照合入力は商品名だけ。状態・備考は取得されるが商品除外には届かない。
- 256–273行の英字境界判定では `SAR` は `exSAR` に一致しない。単純な部分一致への全面変更も、他の英単語の一部をARとして拾う可能性があるため未採用。
- 手元マスタ＋9/8変更値のメモリ再現で同じ誤商品になった18行は、13行が当該商品の除外語なし、5行が除外語ありだが該当しない。別ゲームで共通のEB01、汎用的なvol.1、キャラクター名だけ等の網が、商品を区別する条件なしで単独候補になっていた。

### PO提案の局所検算（本番変更なし）

保存済み20誤判定のうち、単品・単品セットからBOX／デッキ等へ誤一致した11行について、誤候補側に `SAR`, `AR`, `PSA10` を追加する場合を検算した。

| 条件 | 誤候補を止める行数 |
|---|---|
| 現行どおり商品名だけを除外照合 | 1/11 |
| 仮に同一商品の商品名＋状態を除外照合 | 7/11 |

7行には状態欄にPSA10がある。残る4行はマスターボールミラー151、ピカチュウV（Golden Box収録）、テラスタルフェスマスボ、ブイズRRコンプで、この3語では止まらない。AR表記の実例はこの11行にないため、ARへの効果は未実測。備考追加の増分効果も未計測。この検算は除外文字列だけの実験で、商品区分IDを含むDB統合試験ではない。現本番の改善率とも称さない。

商品ごとの診断用除外語を追加する別実験では再現18行すべてが候補なしとなった。293商品の正式名称の判定結果に変化はなかったが、実際の正しい売り文句での取りこぼしは未検証。この辞書は本番投入用ではない。

### 新規登録の要否

- 誤ったBOXへの結び付けを止めるだけなら、単品商品の新規登録は必須ではない。正解候補がなければ未解決として保持する。
- BASE SHOP商品は手元マスタにPM0199として既存。短縮名の網だけを追加すると誤候補PM0230と複数一致、PM0230の除外だけなら候補なし、両方でPM0199へ単独一致した。既存商品の網とフィルターの組合せで改善する例。
- コロちゃお版もPM0285として存在し、手元再現では2行とも正しい候補に変わった。本番修正済みとは未確認。
- 別ゲームのNIKKE等、正しい商品が手元マスタで見つからないものは、自動的に正しい商品IDを付けたい場合に登録確認が必要。仮の新規NIKKE登録だけでは既存の別ゲームNIKKEと複数候補になり、既存側の除外も必要だった。

### 推奨する設計方向と未解決事項

1. 検索は商品名を入口とし、候補商品の区分IDを参照して箱系だけに共通の単品除外規則を適用する。各商品の除外語も併用する。登録画面で選択した箱系区分が解析時の適用条件となる方向で検討する。
2. 除外は同じ抽出商品行の商品名・状態・備考をそれぞれ確認し、理由に一致語と元の欄を残す。LINEメッセージ全体は対象にしない。他商品のPSA10でBOXを落とす混入を避ける。複数語規則を欄またぎで成立させるかは未決。
3. `exSAR`、`exSR`、PSAの空白表記等を扱える規則を定める。短いARを全文部分一致にはしない。単品表記の網羅範囲（MA、マスボ、RRコンプ、カード番号等）は追加調査が必要。
4. 備考の「SAR封入」「PSA10ではない」等は、単語の存在だけで単品を断定できない合成反例。肯定的な単品状態と、封入説明・否定・他商品の記述を区別し、曖昧な場合は要確認へ送る条件を決める。これら反例の実際の発生頻度は未計測。
5. 共通除外で落とした候補を、候補ゼロ時のフォールバックで復活させない。区分未設定、単位と区分の矛盾時の扱いも受入条件に含める。

次の検証は、最新マスタの区分設定を読み取り、上記11行と正常なBOXの実例を対にして、誤一致防止件数・正しいBOXの取りこぼし件数・要確認件数を別々に測ること。状態／備考へ広げることによる正味の精度改善は、その検証前には確定しない。

実行証跡: /private/tmp/line-factor-analysis-20260910.py / 同名のJSON結果ファイル、/private/tmp/line-single-filters-20260910.json。外部事例は不要: 今回は自システムの保存済み誤判定と照合処理を直接検算する原因調査である。

状態: 要因調査・設計方向の草案を保存。正式設計審査未実施、PO設計承認未記録、PR未提出、製品実装未着手。


### 追加相談: Geminiの作品抽出と作品IDによる候補制限

技術的には実現可能。ただし実測精度・現行モデルでの新形式の動作は未検証で、設計合格ではない。

- 現行 `gemini_extraction_svc.py:31–43` は事実のみの7列抽出で、分類・ID付与を明示的に禁止する。作品欄を足すには抽出契約・保存・解析・テストと関連仕様の設計変更が必要。プロンプト1文追加だけで完成とはしない。
- `backend/app/services/tcg_product_master_svc.py:85` で作品IDは `work_id`、参照先は `tcg_series` と確認。既存の商品照合はこれを候補制限に使っていない。
- 推奨方向はGeminiに同一商品行または対応する見出しの作品表記と根拠位置を抽出させ、システムが管理済み名称・別名から作品IDへ変換すること。Geminiに実DBのIDを創作させない。見出しの適用範囲、複数作品混在、不明を扱う。
- `ガンダム EB01` は作品ガンダムを根拠としてワンピース候補を排除できる。正しいガンダム商品が未登録なら未解決で止める。`EB01` のみで作品根拠がない場合は推測でワンピースへ確定しない。
- 作品分類だけでは同じNIKKEのヴァイスシュヴァルツ／UNION ARENAを区別できない。ゲームブランド等の追加軸は既存マスタの意味・収容先を確認して設計する。
- Google公式資料はGeminiの構造化出力で定義済みカテゴリへの分類とenumを説明している。これは形式の実現可能性の根拠であり、作品認識の正確さの証明ではない。Context7 MCPは利用可能ツールに存在しないため、PO起動指示の代替許可により公式資料を直接確認した（2026-09-10）: https://ai.google.dev/gemini-api/docs/structured-output

受入検証案: ガンダム誤判定2行、作品見出し付き型番、型番のみ、複数作品混在、同一作品の別ゲームを用い、誤作品の確定0件と正常商品維持・不明率を別計測する。API実験は未実施。正式設計・実装承認は未取得。


## 2026-09-10 本番DB読み取り調査（先行の接続未確認を更新）

POの「全てDBにある進める」を受領し、既存の接続定型で本番 `tenant_004` を読み取った。SSH認証情報の内容は出力せず、psqlは `-X` / `ON_ERROR_STOP=1` / `default_transaction_read_only=on` / `statement_timeout=10000` を使用。初回の `SHOW transaction_read_only` はon。SELECTのみで、DB更新・再解析・配信なし。

マスタ取得日時: 2026-09-10T00:25:43.417463+00:00（DB時刻）。商品296件（有効293件）、作品11件、商品区分2件。上限2000件に対して296件なので取得上限による欠落なし。有効293商品のwork_idはNULL 0件。これ以前の「最新マスタ未取得」「読み取り先未提供」はこの取得によって解消した。

| 対象 | 本番DBでの事実 |
|---|---|
| 作品 | IP001 Pokemon/ポケモン、IP002 One Piece/ワンピース、IP006 GUNDAM/ガンダム。いずれも有効 |
| 区分 | PC_BOX＝Box／箱系、PC_SINGLE＝Single／シングル系 |
| 通常バトルコレクション | PM0200。検索7語、除外5語（Generations、ex、コロコロ、コロちゃお、コロチャオ）。「コロ」そのものは未登録 |
| コロちゃお版 | PM0285として登録済み。検索「コロちゃお」「コロチャオ」、除外なし。新規登録は不要 |
| コロコロコミックver. | 全296商品の名称に登録なし。和英名・検索キーワードも全296商品で確認し、コロコロ版の登録なし。既存PM0285と同一視しない |
| ガンダムEternal Nexus | 名称に登録なし。作品制限後に正しい商品へ解決できるとは称さない |
| メモリアルコレクション | PM0123、作品IP002。検索EB-01／EB01／メモリアルコレクション、除外なし |
| Weiss Schwarz | IP007の別名はWeiss Shwarzのみ。日本語ヴァイスシュヴァルツの別名が入っていない。作品マスタの存在だけで日本語認識までできるとはしない |

最新DBの保存済み判定を対象語で検索し、60グループ・304行を取得（LIMIT150グループ未到達）。2026-09-10T00:27:43.173196+00:00の別クエリで原文のis_active別に検算した。

| 条件 | 保存行全体 | 有効な原文 | 無効な原文 |
|---|---:|---:|---:|
| ガンダム／Eternal Nexus→PM0123 | 29 | 4 | 25 |
| コロちゃお表記を含む商品名または備考→PM0200 | 4 | 0 | 4 |
| コロコロ表記の商品名・pid_resolved=false | 21 | 1 | 20 |

保存行は投稿・解析明細の数であり、固有商品数や顧客配信件数ではない。無効原文の判定を現時点の配信対象として数えない。最新原文の全文再照合による正解ラベル付けは別の検証である。

コロちゃお誤判定4行のうち、商品名に限定版表記を持つ3行は最新マスタ＋固定SHAコードの再現でPM0285へ一致した。残り1行は商品名「MEGA スタートデッキ100」、備考「コロちゃおバージョン」で、最新マスタでもPM0200へ誤一致した。この1行は2026-09-09T00:13:39.670492+00:00の保存で、原文は取得時点では無効。同一商品行の備考を除外に使うというPO提案の直接の根拠となる。

局所検算: 最新マスタと固定SHA `8206ba2844921c1efb3ca4fd647230e76bb0c5c6` の照合関数を使用。ガンダム作品が既知と仮定して候補をIP006に制限すると29保存行相当はすべてNONEとなり、PM0123誤一致を止める。これはGeminiが29行の作品を正解した実測ではない。PM0200に対する同一明細のコロ除外は備考のみ1行をNONEに変え、既にPM0285へ一致する商品名3行を維持する。

再現物（原文全文・提供者情報をリポジトリへ複製しない）:
- /private/tmp/line-current-master-20260910.json SHA256 `a30231ed06faca89d076b9667c6f773872dbce0649a7a76c76cb51144c8b7c5f`
- /private/tmp/line-current-targeted-analysis-20260910.json
- /private/tmp/line-current-counts-20260910.json
- /private/tmp/line-current-candidate-probes-20260910.json

初回のAST局所再現は `_FULLWIDTH_OFFSET` 定数の取り込み漏れで失敗し、定数を含めた再実行が成功。製品コードは変更していない。

## 2026-09-10 新方式の本番保存結果・初回監査（11:55 JST標本）

これは何か: 作品による商品絞り込みを反映した後、実際の保存結果で誤商品が残る条件を確認した記録。

### 対象と検証方法

- PO依頼「進める」に基づく読み取り調査。製品実装、辞書変更、再解析の起動、配信は行っていない。
- #3398先行DB反映成功後に #3393 をmerge SHA `864ace729fe45a1b254fa2c3b8f66baa547d57fa` で反映。deploy run34430833637成功。実装・本番反映の完了と、解析精度の合格を区別する。
- 既存card-templates.md §2-3のSSH接続定型でtenant_004を取得。`default_transaction_read_only=on`、`statement_timeout=10000`、`-X`、`ON_ERROR_STOP=1`。最初のSHOWと集計中のread_onlyはいずれもon。SELECTのみ。
- 標本はextraction_items.created_atが2026-09-10T02:47:43Z〜02:55:15.472122Z、prompt_version=`raw-extraction-v3-work-p1`。取得上限2000に対し398明細、19原文・19job。全398行のengine_version=`name-first-v3-work`、原文is_active=true。商品確定266、未確定132。確定数は正答数ではない。
- 元メッセージのreceived_atは2026-09-09T02:52Z〜2026-09-10T02:48Z。過去受信分の新方式処理も含み、「反映後に新着LINE19件」とは数えない。raw_work_nameは334/398行が空欄、64行は非空欄。空欄が全て抽出ミスという意味ではない。作品不明のまま商品確定は229行。
- 11:57:13 JSTの別時点で、対象時刻以降作成jobはdone24、empty2、running4、pending11、error0。処理中の母集団を混ぜないため、以下は固定398行に限定。
- 最新マスタは296商品・有効293、作品11、区分BOX/SINGLEの2件を取得。2追加列の実在とPM0200の除外「コロ」もDB実物で確認。

### 原文と保存結果で確認した取り違え（少なくとも5明細）

| 原文の商品 | 保存された商品 | 件数 | 保存された一致根拠 | 要確認 |
|---|---|---:|---|---|
| BASE SHOP vol.1／リミテッドカードコレクション Vol.1 | PM0230 トライアルデッキ【推しの子】 | 3 | WORK:UNKNOWN / SK:vol.1 | 2行true、1行false |
| マスターボールミラー151のみ（原文見出し「シングルカード」、300枚） | PM0104 ポケモンカード151（PC_BOX） | 1 | WORK:UNKNOWN / SK:151 | false |
| スペシャルデッキセットMEGA メガオーダイル・メガカイリュー・メガゲンガー | PM0184 スターターセットMEGA メガゲンガーex | 1 | WORK:UNKNOWN / SK:メガゲンガー | false |

照合ID（extraction_items.id）: BASE SHOP系 `05158657-3a10-4426-9a38-7268eff23961` / `19eae84d-6754-4c34-b33c-f96817be8ea9` / `451c2bff-609e-420e-b4d0-0ddbf8e04e89`、151 `0d5ee233-2ba0-4c1f-ae5a-422e2a3b043b`、デッキセット `0b4291b7-083f-401c-a0ba-c6fab3b4497e`。全5行pid_resolved=true。この5件は全398件への完全な正解ラベル付けではなく、誤判定率の確定値として使わない。

### 要因と改善候補（未承認案）

1. **網が広すぎる＋正しい商品の網が不足**: PM0230は検索語にvol.1、除外なし。正しい既存PM0199は「リミテッドカードコレクション VOL1」で、原文のVol.1（点あり）とは一致しない。BASE SHOP単独略称も検索語にない。新規商品登録は不要。PM0230からvol.1単独を外し、PM0199へ点あり表記／BASE SHOP表記を追加する案。
2. **フィルタ不足**: PM0104の除外9語にマスターボールミラーなし。PM0184の除外はMEGディアンシーだけでスペシャルデッキセットなし。作品が同じ商品同士なので作品制限だけでは解消しない。BOX/SINGLE共通フィルタは今回実装の対象外。SAR/AR/PSA10だけでは今回の151の「マスターボールミラー」を防げない。
3. **作品不明時に残る広い語**: 実装SHAのtcg_analyzer_svc.py:463–469は英字と数字を含み、所定のハイフン／スラッシュ形に合う語だけを型番と判定。vol.1（点あり）と151（数字のみ）は型番だけの確定禁止に該当しない。:478–497は作品不明でも名称検索一致を許す。これは今回の設計どおりの動作であり、型番禁止を強める際は正常な「151」等の取りこぼしも検証する。
4. **作品見出しの認識範囲**: BASE SHOP系1行の原文は1行目「⚫︎ ONE PIECE BASE SHOP」、3–9行目に商品。gemini_extraction_svc.py:43–46は作品名単独の見出しのみ許すため、この装飾と店名を含む行は対象外。別の未確定OP-09原文には「🟡ONE PIECE在庫🟡」見出しがあるが同様に対象外。作品が空欄だから直ちにGeminiの能力不足とはしない。見出しの許容範囲拡大は別設計と混在作品の検証が必要。

### 変更せず行った局所再現

反映済みSHAの純粋な商品照合関数のみASTで抽出し、今回の最新マスタと同じ5明細を入力。現状は5/5で保存済みの誤商品へ一致。メモリ上だけでPM0230のvol.1削除、PM0199へ「BASE SHOP vol.1」「リミテッドカードコレクション vol.1」追加、PM0104へ「マスターボールミラー」除外、PM0184へ「スペシャルデッキセット」除外を適用すると、3行はPM0199へ正しく一致、2行はNONEへ変わる。誤商品確定は5→0。これは5例の商品照合だけの再現で、全処理の回帰・全商品への影響確認・正式設計審査は未実施。製品／DBへは適用していない。

### 改善を確認できた点と未確認

- Eternal Nexus [EB01] 1行（`05a99ae9-f7db-4fb4-8776-6c6087db7cbb`）はNONE。ワンピースPM0123へ誤確定していない。ただし作品抽出は空欄であり、「ガンダム作品の抽出に成功」とは扱わない。マスタにEternal Nexus名称の登録はなく、正しい商品への確定は別課題。
- スタートデッキ100コロコロコミック1行はNONE、通常バトルコレクション1行はPM0200に確定。今回標本にコロちゃお版の実例はなく、コロちゃお版の本番正答検証は未了。
- 「MEGA 30th CELEBRATION カードセット (9種セット)」1行がPM0263へ確定。既存9個別カードセットとの販売単位の扱いを含め、正しい集約商品の定義が未確認のため、上記確定誤判定5件には含めない。
- 新規登録が必要かは、151のシングル・複数デッキのセット・9種カードセットの販売単位と既存マスタ適用範囲を先に確定する。名称検索だけで新規登録を決定しない。
- 本調査は運用実測。外部事例・ライブラリ仕様確認は今回不要（既存本番データと反映コードの照合で判定）。

### 次の一手・状態

優先案は確認済み5件の検索語／除外語を修正する設計。正常な商品・曖昧な略称・作品見出し・BOX/SINGLEを含む対照標本で副作用を測ってから正式審査・実装カードへ進む。調査済み／修正案の局所再現済み／正式設計・設計審査・PO修正承認は未了／追加実装・本番修正は未着手。

ローカル証拠（原文を含むためGitには格納しない）:

- `/private/tmp/line-postdeploy-rows.json` SHA256 `7cb48132a116e59acea286627c562ce3786d680775e342677d7a09bfff990b51`
- `/private/tmp/line-postdeploy-master.json` SHA256 `d63fc233af2f4275ea8a6acf96ed62f8298aab2c0a1920afb5cd998087bcac4c`
- `/private/tmp/line-postdeploy-probes.json` SHA256 `3f92474330a638a6e8db5fe272b98164035a9156002f0a12b933e97bb5d5d700`
- `/private/tmp/line-postdeploy-final-status.json` SHA256 `986b2181b13b50fe4fed38307264416451c511d73c337358cad397d62f3634b0`

## 2026-09-10 辞書修正案の対照検証（12:03 JST標本）

PO「進める」に基づき、初回5件だけの局所試験から拡張。read_only=onで最新マスタ・正規化・単位・区分とv3全745明細を取得（DB count745、LIMIT3000未到達、取得03:03:04.045857Z）。反映SHA864ace72の純関数をAST抽出し、商品名/状態/備考の正規化、単位区分による候補制限、作品根拠検証、商品照合までを実行。保存済みproduct_id相当コード・pid_resolvedとの不一致は0/745。DB更新、Gemini呼び出し、後処理込みの全体再解析は未実施。

初案（PM0230のvol.1削除＋PM0199への点あり検索語2語＋除外2語）では10明細が変化。しかし合成境界例「BASE SHOP vol.10」「BASE SHOP vol.11」「リミテッドカードコレクション vol.10」がPM0199へ誤確定した。初回5例のみの試験ではこの副作用を検出できていなかった。現行ASCII境界は前後の英字のみを見る（tcg_analyzer_svc.py:215–277）、日本語混在語は部分文字列ANDなので数字の後続を拒否しない。この初案はREVISE、検索語追加を撤回する。

修正案は3操作だけ: PM0230の検索vol.1単独削除、PM0104に除外マスターボールミラー追加、PM0184に除外スペシャルデッキセット追加。最新745明細中10行が誤商品からNONEへ変化、残り735行の商品コード・確定可否・候補集合は不変。全有効293商品の正式名称を当該作品IDで照合した際の結果も293/293不変（全293商品が正解したという意味ではない）。正常例・状態/備考除外・Vol.10/11等の境界合成例16/16が期待どおり。全体正答率や未観測入力への完全性を保証しない。

変化10行の内訳: BASE SHOP/リミテッドカードコレクション4、LIMIT OVER SPECIAL PACK1、プレミアムカードコレクション3、151シングル1、複数デッキセット1。追加5行も原文の商品行を確認。現行PM0230「推しの子トライアルデッキ」と異なる商品である。商品コードと確定可否の不変735行には、他の未検出誤判定が含まれ得るため「735件正答」とは呼ばない。

トレードオフ: 安全案はBASE SHOP4行も正しい商品へ自動確定せず、要確認へ送る。特定できない商品の正しい新規登録、Vol番号の境界判定、装飾作品見出し、BOX共通フィルタは別課題。過去の保存結果は辞書だけでは自動修正されない。

変化行IDと確認した入力:

- `05158657-3a10-4426-9a38-7268eff23961`: リミテッドカードコレクション Vol.1 → NONE
- `0b4291b7-083f-401c-a0ba-c6fab3b4497e`: ■スペシャルデッキセットMEGA メガオーダイル・メガカイリュー・メガゲンガー → NONE
- `0d5ee233-2ba0-4c1f-ae5a-422e2a3b043b`: マスターボールミラー151のみ → NONE
- `19eae84d-6754-4c34-b33c-f96817be8ea9`: リミテッドカードコレクションvol.1 → NONE
- `3e6bbbc1-6cc9-4194-9eb0-babab18d5cdc`: LIMIT OVER SPECIAL PACK Vol.1 → NONE
- `40667fc5-5bd8-4ed1-bd0f-119b68682a6c`: BASE SHOP リミテッドカードコレクションvol.1 → NONE
- `451c2bff-609e-420e-b4d0-0ddbf8e04e89`: BASE SHOP vol.1 → NONE
- `a1a65e52-bc61-4e7d-a165-a428e9580420`: プレミアムカードコレクション  – 6 assort vol.1 - → NONE
- `abf5866d-01c3-4d58-8d81-400e2e2439e2`: プレミアムカードコレクション- ベストセレクションvol.1 - → NONE
- `dd252d27-e2d5-40dd-9a99-119275bc6e90`: プレミアムカードコレクション 6 assort vol.1 → NONE

ローカル検証証拠（生原文をGitへ格納しない）:

- `/private/tmp/line-dictionary-audit-context.json` SHA256 `05808fe80c29f081facdd8787a4f71341de89618a209945b43f6ab8a4ea48dac`
- `/private/tmp/line-dictionary-audit-rows.json` SHA256 `4c6570e82a93060c264e98673b9d094e20eb36cc23796a642cbcc6c6619bd9d5`
- `/private/tmp/line-dictionary-contrast.py` SHA256 `a9387734448885323f89d520227fad3a55e7b0189cbca56059e5337f68188aaa`
- `/private/tmp/line-dictionary-contrast.json` SHA256 `d9ce9894aca1b28966807b130a2a6db5fae9692f1dabd26f436eb79051f6cc8a`
- `/private/tmp/line-dictionary-safe-contrast.json` SHA256 `238e212872cf61265f1f0ad35715b70ac791ef748f0b338ce6c8809c625e89c4`

## 2026-09-10 継続改善と再解析・配信の事前調査

POはPRマージ、本番反映後の再解析、完了後の接続3シートへの配信と改善ループを明示承認。さらに原文「商品名のご検出が完了したら状態のご検出も確認してくれ、同じループで進めてくれ」を受領。商品名の原文照合を先行し、状態の原文照合へ続ける。未知の新商品定義など事業判断は保留する。

- 接続先はDB実物で有効3件。各tabは在庫集計。最後の配信は3件とも674行・ok。新規接続作成や設定変更は不要。ID等はローカルline-loop-operations-preflight.json。既存run_distributionは全有効targetへ書き込む。再解析未完了、抽出pending/running/extracted、タブ不在、上限超過で停止し、この安全装置を維持する。既存タブ全置換なので、実行直前にタブ/出力を退避・比較し、3件の実値を検算する。まだ配信していない。
- 有効原文の全明細は1386（count1386/取得1386、LIMIT3000未到達）。engine内訳v3=745、v2=641。今回の再解析は既存reanalyze_extraction_job経路で辞書を反映し、analysis_runs/analysis_run_snapshotsを残す。Gemini再抽出と名称照合だけの再解析を区別する。旧GAS時点の退避テーブル実在は既往調査で確認済みだが、今回実行前の退避確認はまだ必要。
- 次周の商品名候補: トウホクPSA7/8とフクオカPSA6/7/9がBOX商品へ誤確定、各表記3行・計15行。原文のシングル/PSA見出しと枚数・鑑定表記を直接照合。全15行の保存状態はFLAG_SINGLEで、include_flag_single=falseの現在設定では配信対象外。PM0182/PM0189へPSA除外を加えるメモリ比較は15行→NONE、他1371行の比較結果不変。これは追加案の局所比較であり、正式名称・境界・更新競合の検証や正式設計は未了。初回3操作へ混載していない。
- 状態の確認済み問題: id d54d7243-8485-49fc-981a-c90b1ee4cf3d プレシャスコレクターボックスはraw_state=開封済み、raw_memo=(検品のため一度開封済み)、raw_unit=BOX、保存condition=Sealed box/R4単位既定。既存CN0006は「検品のため一度開封済み」「確認のため開封済み」を検索語に持つが、状態判定入力は商品名＋状態で、備考は渡されない。単純に開封済みを全区分へ登録するとシングルや外箱だけの開封もBOX扱いする可能性が未検証のため、未承認の語追加や即時修正はしない。
- 配信を止める残存job2件: 6da3ca68-651e-4ff6-8316-1c9135508ad2（source b1b58ee9-0d6a-4ed1-8034-f1d62a72b4b2、原文無効）とbfa07018-9b34-42b6-990a-017e3c1cf140（source afbc08d1-cf3b-43be-87e5-4b7200144b6c、原文有効）。両方created_at=2026-09-10T02:49:21.105805Z、running、items0、extracted_at/prompt_versionなし。Celery inspectのactive/reserved/scheduledはすべて空。現行workerログの指定ID/timeout検索は該当なしで、終了原因は未確認。単なる成功への状態書換えは禁止。既存diagnostics.retry_extractionはrunningを対象外とするため、正式な復旧設計が必要。旧stale終端化migrationと1行requeue migrationに前例があるが、古い固定IDのスクリプトを流用実行しない。

現在地: #3400技術検証・root読み取りレビュー済み、番号付きGOの機械要件でマージ停止。次は当該承認記録を満たして反映確認し、残存jobの復旧を別途設計・検証、再解析完了後に全3シートへ配信。商品名追加候補と状態の改善は、原文・正常例との対照検証を揃えた順に進める。

ローカル証拠（原文・接続情報をGitへ格納しない）:

- `/private/tmp/line-keyword-guards-before.json` SHA256 `b8539d0df63bd9e7502181c5499cbf3cde58bebf6c5e0b734e4f83393395e772`
- `/private/tmp/line-loop-operations-preflight.json` SHA256 `38c6b8fab85840e9a7e0451de949ac3f9256a4fddb4aba6e5392b8c933505dcd`
- `/private/tmp/line-loop-active-before.json` SHA256 `a52f558f55e71def1bedf3aecb4c87d832e1dc638773b0d515243b369130a336`
- `/private/tmp/line-loop-psa-proposal.json` SHA256 `855da1dbe3a39be650e435dceb03ca9033b2a6a02fb6ba918830b0aaec587fc3`
- `/private/tmp/line-stale-running-jobs.json` SHA256 `1ef480bd87dec0d05556acabc51f3df8c36fd14a2037bb72cceb1ee7cd661f54`
- `/private/tmp/line-state-master.json` SHA256 `10b38426d34d18ea3745bd2bf8a716c866408439ba3f55ddfa64756c76601ebb`

## 2026-09-10 #3400本番反映・再解析の実行結果

PO原文「GO #3400」を受領しPR本文へ転記。追加原文「› 次に進む、また離席するのでPRマージとデプロイまで進めてくれ」「↳ 不明点は推測で進めることを禁止するので停止して質問してくれ」も受領。時分は原文から取得していない。未確認の扱いを推測で決めず停止する。

### 実行・直接検証

- PR https://github.com/shingo-ops/salesanchor/pull/3400 は2026-09-10T07:24:27Zにマージ済み。merge SHA `d21599c72126dc450a70b7aad2a86b2ef3a412a3`。公式gh-pr-merge-safe.sh、merge commit、対象HEAD指定で実行。承認チェックはrun34449729764でsuccess。旧失敗run34433392699は履歴として残る。
- Deploy to VPS run34449800503/job102782709121はsuccess。07:25:11Zのログで反映前バックアップ `salesanchor_db_20260910_162509.sql.gz`（4.7M）生成、07:27:50Zに224/224番の今回SQL実行、SA-19 smoke成功、07:28:12ZにDeployment completed successfullyを直接確認。VPSのgit HEADは上記merge SHA、backend `/api/health` はHTTP200。
- 本番辞書の内容・並び順比較は検索658→657（PM0230のvol.1を1件削除）、除外154→156（PM0104のマスターボールミラー、PM0184のスペシャルデッキセットを各1件追加）。他の語・並び順の差分0。既存の別migration `20260908_170000_tcg_keyword_v4_t004.sql:124` は12商品の除外を入れ直すため、デプロイ全体では既存除外49行のUUIDが再発行された。今回SQL単体のUUID保持試験と、全migration実行結果を混同しない。根拠はline-keyword-guards-current/after/deploy-diff.jsonと既存SQL。
- 同じmerge SHAに付く失敗run34449804461は別PR #2649（event=pull_request、head=main）のCI設定検査。#3400のマージ差分8ファイルにworkflow-lint.yml/design-partner.mdはない。今回のpush側CI設定検査run34449800302はsuccess。別PRの失敗を今回の変更へ帰属させない。
- 再解析直前、有効原文のdone79ジョブ・1425明細を退避。analysis_runs未完了0、item_corrections0、GAS旧退避テーブル実在。今回の復元根拠は反映前DBバックアップと下記の処理別スナップショットであり、古いGAS退避だけでは代用しない。
- 既存 `_run_reanalyze_sync` を固定79ジョブへ順次実行。事前に各ジョブのdone・原文有効・明細ID集合・エンジン版を照合し、対象ずれなら停止する呼び出し。exit0。DBで79/79 run完了・1425 snapshotを確認。対象明細の追加/欠落0、全1425件がname-first-v3-work。Gemini再抽出はしていない。

### 再解析差分の意味と限界

- 商品コードが変わったのは87行。旧v3からの10行は設計の固定10IDと完全一致し、全件NONEになった。誤った商品への自動確定を止めた結果で、正しい商品の新規特定ではない。
- 旧v2からの77行は別集計。71行は作品情報NULLかつ従来SK根拠が型番語、1行はBASE SHOPのvol.1誤一致で、合計72行がNONE。前者は既存v3契約（作品根拠なしの型番単独確定を禁止、design-keyword §10）の適用であり、71件全部を誤商品だったと断定しない。
- 残る5行は候補コード変更。PSA10 AR/CHRセット2行は変更前後ともMULTI（未確定）の代表候補変化。ARバルク/AR,CHRの3行は備考「被りあり」を含みPM0007→PM0008へ変更。原文・商品の適合性の最終判断を全件完了としない。5行ともシングル状態の配信除外条件は維持。
- pid_resolvedは1011→937。これは自動確定件数であり正答率ではない。状態変更0/1425。既知の開封済み→Sealed box1件とPSA→BOX15件は残件。

### 配信の停止・確認する判断

- 既存run_distributionをtarget指定なし（全有効3接続）で実行したが、2026-09-10T07:32:05Zに安全装置#8bがrunning2件を検知し、書き込み前に停止。results=[]。実シートへは書いていない。DBでも3接続とも前回配信674行の記録を維持。安全装置・接続設定を変更していない。
- 未完了2件は前節の固定IDと同じ。既存retry_extractionはrunningを対象外とする。成功扱いへの書換え・無断リセット・再抽出のための既存明細削除はしない。停止原因は未確認。
- 反映後のCelery inspectでもworker `celery@16887600ee27` のactive/reserved/scheduledは全て空。これは観測時の実行・予約がない証拠であり、過去の中断原因の証明ではない。
- POへ確認する復旧案（未承認・未実装）: 2件を成功扱いにせず中断として記録したうえで、有効な原文1件だけを再実行する。無効な旧原文1件は再配信しない。実行前にworkerの実行/予約がないこと、対象ID・作成時刻・items0・原文有効性・退避を再確認し、対象を限定した復旧設計・検証を行う。停止原因をこの案の説明で創作しない。
- 作品未取得の旧データを補う方法と、商品/状態の次の修正は設計未了。今回は#3400反映・再解析済み、配信未完了。改善ループ全体の完了とはしない。

ローカル実行証拠（生原文・接続IDをGitに含めない）: `/private/tmp/line-reanalysis-before.json`、`line-reanalysis-after.json`、`line-reanalysis-diff.json`、`line-reanalyze-execution.jsonl`、`line-reanalysis-verification.json`、`line-distribution-attempt.json`、`line-loop-worker-inspect.json`。各ファイルは/private/tmp配下。今回の調査・実行はrootによる直接確認であり、独立した第二者レビューとは称さない。

文書検証: git diff --check、bash scripts/check-task-state.shは成功。次の復旧案は未承認・未実装のため、復旧機能の試験成功や設計合格は宣言しない。

## 2026-09-10 復旧実装中の並行確認

前節の復旧方針にPO原文「進める」、追加原文「› › 次に進む、また離席するのでPRマージとデプロイまで進めてくれ」を受領。07:38:28Zに2件の同一性・running・items0を再確認。無効sourceの後継ID、有効sourceの後継NULLも確認。workerのactive/reserved/scheduledは各0。設計§12を自己審査APPROVE、正式カード検査後に既存実装担当へ渡した。実装PRは https://github.com/shingo-ops/salesanchor/pull/3403 。本番直接更新・permit発行・追加エージェントはない。

### 配信前検証の準備

既存サービスの認証経路で全3接続を読み取り、ID・在庫集計タブを照合。3シートともデータ674行・12列（ヘッダ含む675行）で値は完全一致。SHA256は `1fa4605ca28c175759631271b1141640fbf20c4524afa55603b188a2453e8564`（JSON UTF-8・ensure_ascii=False・区切り空白なし）。式として取得したセルで先頭=は0件。退避先は `/private/tmp/line-three-sheets-before.json`。現時点の配信候補は432行だが未完了1原文の復旧前プレビューであり、最終配信件数ではない。既存674行との母集団・時点が異なるため、その差を今回修正による減少と断定しない。配信直前に再度対象・内容を確認して退避する。

Context7はツール一覧で利用不可。PO許可済み代替として[gspread公式Worksheet資料](https://docs.gspread.org/en/latest/api/models/worksheet.html#worksheet.get_all_values)で読取メソッドを確認。表示資料は6.1.2、本番実物は6.2.1のため本番inspect.signatureでもvalue_render_option/pad_values等の対応を照合した。UNFORMATTED_VALUEで値、FORMULAで式を退避した。書き込みは行っていない。既存配信は全targetへ同じ12列をRAWで渡すため、配信後は3シート間の一致と、配信対象行の多重集合を照合する（同順位行の順序だけで誤判定しない）。

### 次周の商品名15件・状態候補5件

- 再解析後の全1425明細に対し、確定BOX商品かつ名称/状態/備考にSAR/AR/PSA/BGS/CGC/ARSの表記を含む行を再検出。該当15行は全て前節のトウホク/フクオカPSA6〜9、raw_unit=枚、condition=FLAG_SINGLE。既存配信設定では対象外。
- 実コードtcg_analyzer_svc.py:323〜344は「箱系」単位のときだけBOX商品に絞り、それ以外は全候補を返す。DBの「枚」aliasはPiece/単品系。単位が枚でもBOX候補が残ることを確認。単位フィルタの全区分への変更は今回の復旧範囲外。
- 辞書案はPM0182/PM0189へPSA除外各1件。現在DBの判定再現は1425/1425不一致0。対照では対象15件のみNONE、他1410件不変、正式名称293件の判定変化0、名称/状態/備考×PSA/PSA6/PSA10/psa9/非該当部分文字列の36対照が全成功。`line-psa-expanded-contrast.json`へ保存。これは読み取りの対照結果であり、新たな本番辞書変更ではない。
- 状態の全量候補抽出では、Sealed box/Caseなのに名称/状態/備考に開封・損傷等の表記がある5行を検出。3行は既存状態辞書の語が備考にあるが、状態判定へ備考が渡されず通常BOXになる。既存関数の局所比較で、OP-17の凹み/破れ2行はDamaged sealed box、プレシャスコレクターボックスの検品開封1行はOpened boxとなる。現在保存の判定と局所再現は5/5一致。対象ID・根拠は `line-state-memo-contrast.json`。
- 残る2行は「箱にテープ剥がし跡」（商品未確定）と「伝票貼り付けあり」（商品確定）。現在状態マスタに該当語がなく、備考追加だけでも状態は変わらない。これらを損傷扱いにする事業上の定義は未確認。PO判断なしの語追加をしない。
- 備考を状態判定へ一般適用した場合の正常例・否定文・送料/免責文・区分間の影響は未検証。局所3件の改善だけで全体設計合格を出さない。状態の本番修正は未実施。

補足: 上記の全量は07:30:24Zの固定1425明細。後続の新着や復旧で増える明細は別の母集団として比較する。原文を含むJSONは/private/tmpに保持しGitへ複製しない。

状態の追加対照: 語を列挙する候補抽出だけでは「ダメージ(大)/(小)」を拾えなかったため、全1425件を状態判定関数で比較した。保存済みの最終単位を固定した局所再現は1425件不一致0。備考を加えると17件（Damaged caseへ14件、Damaged sealed boxへ2件、Opened boxへ1件）が変化し、他1408件の状態は不変。各17件の原文行範囲も直接読み、損傷/開封表記を確認した。これは全解析パイプラインの再現ではないため、単位再計算・否定文・別商品の備考混入などの回帰検証は残る。17件を次の設計用候補として `/private/tmp/line-state-memo-all-function-contrast.json` に保存。前記3件を含む拡張結果であり、3+17件とは数えない。伝票/テープ跡の2件の定義は引き続き未確認。
