# recon — TCG商品マスタ育成

> ローカル証跡の扱い: /private/tmp配下のline-*ファイルは開発端末で保管する外部証跡です。保管名・既存SHA256は保持し、リポジトリ内コードの引用とは区別して記載します。顧客原文を含む証跡はGitへ追加しません。CIがこれらの内容を再検証したという意味ではありません。


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

- /private/tmp/line-postdeploy-rows.json SHA256 `7cb48132a116e59acea286627c562ce3786d680775e342677d7a09bfff990b51`
- /private/tmp/line-postdeploy-master.json SHA256 `d63fc233af2f4275ea8a6acf96ed62f8298aab2c0a1920afb5cd998087bcac4c`
- /private/tmp/line-postdeploy-probes.json SHA256 `3f92474330a638a6e8db5fe272b98164035a9156002f0a12b933e97bb5d5d700`
- /private/tmp/line-postdeploy-final-status.json SHA256 `986b2181b13b50fe4fed38307264416451c511d73c337358cad397d62f3634b0`

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

- /private/tmp/line-dictionary-audit-context.json SHA256 `05808fe80c29f081facdd8787a4f71341de89618a209945b43f6ab8a4ea48dac`
- /private/tmp/line-dictionary-audit-rows.json SHA256 `4c6570e82a93060c264e98673b9d094e20eb36cc23796a642cbcc6c6619bd9d5`
- /private/tmp/line-dictionary-contrast.py SHA256 `a9387734448885323f89d520227fad3a55e7b0189cbca56059e5337f68188aaa`
- /private/tmp/line-dictionary-contrast.json SHA256 `d9ce9894aca1b28966807b130a2a6db5fae9692f1dabd26f436eb79051f6cc8a`
- /private/tmp/line-dictionary-safe-contrast.json SHA256 `238e212872cf61265f1f0ad35715b70ac791ef748f0b338ce6c8809c625e89c4`

## 2026-09-10 継続改善と再解析・配信の事前調査

POはPRマージ、本番反映後の再解析、完了後の接続3シートへの配信と改善ループを明示承認。さらに原文「商品名のご検出が完了したら状態のご検出も確認してくれ、同じループで進めてくれ」を受領。商品名の原文照合を先行し、状態の原文照合へ続ける。未知の新商品定義など事業判断は保留する。

- 接続先はDB実物で有効3件。各tabは在庫集計。最後の配信は3件とも674行・ok。新規接続作成や設定変更は不要。ID等はローカルline-loop-operations-preflight.json。既存run_distributionは全有効targetへ書き込む。再解析未完了、抽出pending/running/extracted、タブ不在、上限超過で停止し、この安全装置を維持する。既存タブ全置換なので、実行直前にタブ/出力を退避・比較し、3件の実値を検算する。まだ配信していない。
- 有効原文の全明細は1386（count1386/取得1386、LIMIT3000未到達）。engine内訳v3=745、v2=641。今回の再解析は既存reanalyze_extraction_job経路で辞書を反映し、analysis_runs/analysis_run_snapshotsを残す。Gemini再抽出と名称照合だけの再解析を区別する。旧GAS時点の退避テーブル実在は既往調査で確認済みだが、今回実行前の退避確認はまだ必要。
- 次周の商品名候補: トウホクPSA7/8とフクオカPSA6/7/9がBOX商品へ誤確定、各表記3行・計15行。原文のシングル/PSA見出しと枚数・鑑定表記を直接照合。全15行の保存状態はFLAG_SINGLEで、include_flag_single=falseの現在設定では配信対象外。PM0182/PM0189へPSA除外を加えるメモリ比較は15行→NONE、他1371行の比較結果不変。これは追加案の局所比較であり、正式名称・境界・更新競合の検証や正式設計は未了。初回3操作へ混載していない。
- 状態の確認済み問題: id d54d7243-8485-49fc-981a-c90b1ee4cf3d プレシャスコレクターボックスはraw_state=開封済み、raw_memo=(検品のため一度開封済み)、raw_unit=BOX、保存condition=Sealed box/R4単位既定。既存CN0006は「検品のため一度開封済み」「確認のため開封済み」を検索語に持つが、状態判定入力は商品名＋状態で、備考は渡されない。単純に開封済みを全区分へ登録するとシングルや外箱だけの開封もBOX扱いする可能性が未検証のため、未承認の語追加や即時修正はしない。
- 配信を止める残存job2件: 6da3ca68-651e-4ff6-8316-1c9135508ad2（source b1b58ee9-0d6a-4ed1-8034-f1d62a72b4b2、原文無効）とbfa07018-9b34-42b6-990a-017e3c1cf140（source afbc08d1-cf3b-43be-87e5-4b7200144b6c、原文有効）。両方created_at=2026-09-10T02:49:21.105805Z、running、items0、extracted_at/prompt_versionなし。Celery inspectのactive/reserved/scheduledはすべて空。現行workerログの指定ID/timeout検索は該当なしで、終了原因は未確認。単なる成功への状態書換えは禁止。既存diagnostics.retry_extractionはrunningを対象外とするため、正式な復旧設計が必要。旧stale終端化migrationと1行requeue migrationに前例があるが、古い固定IDのスクリプトを流用実行しない。

現在地: #3400技術検証・root読み取りレビュー済み、番号付きGOの機械要件でマージ停止。次は当該承認記録を満たして反映確認し、残存jobの復旧を別途設計・検証、再解析完了後に全3シートへ配信。商品名追加候補と状態の改善は、原文・正常例との対照検証を揃えた順に進める。

ローカル証拠（原文・接続情報をGitへ格納しない）:

- /private/tmp/line-keyword-guards-before.json SHA256 `b8539d0df63bd9e7502181c5499cbf3cde58bebf6c5e0b734e4f83393395e772`
- /private/tmp/line-loop-operations-preflight.json SHA256 `38c6b8fab85840e9a7e0451de949ac3f9256a4fddb4aba6e5392b8c933505dcd`
- /private/tmp/line-loop-active-before.json SHA256 `a52f558f55e71def1bedf3aecb4c87d832e1dc638773b0d515243b369130a336`
- /private/tmp/line-loop-psa-proposal.json SHA256 `855da1dbe3a39be650e435dceb03ca9033b2a6a02fb6ba918830b0aaec587fc3`
- /private/tmp/line-stale-running-jobs.json SHA256 `1ef480bd87dec0d05556acabc51f3df8c36fd14a2037bb72cceb1ee7cd661f54`
- /private/tmp/line-state-master.json SHA256 `10b38426d34d18ea3745bd2bf8a716c866408439ba3f55ddfa64756c76601ebb`

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

ローカル実行証拠（生原文・接続IDをGitに含めない）: /private/tmp/line-reanalysis-before.json、line-reanalysis-after.json、line-reanalysis-diff.json、`line-reanalyze-execution.jsonl`、line-reanalysis-verification.json、line-distribution-attempt.json、line-loop-worker-inspect.json。各ファイルは/private/tmp配下。今回の調査・実行はrootによる直接確認であり、独立した第二者レビューとは称さない。

文書検証: git diff --check、bash scripts/check-task-state.shは成功。次の復旧案は未承認・未実装のため、復旧機能の試験成功や設計合格は宣言しない。

## 2026-09-10 復旧実装中の並行確認

前節の復旧方針にPO原文「進める」、追加原文「› › 次に進む、また離席するのでPRマージとデプロイまで進めてくれ」を受領。07:38:28Zに2件の同一性・running・items0を再確認。無効sourceの後継ID、有効sourceの後継NULLも確認。workerのactive/reserved/scheduledは各0。設計§12を自己審査APPROVE、正式カード検査後に既存実装担当へ渡した。実装PRは https://github.com/shingo-ops/salesanchor/pull/3403 。本番直接更新・permit発行・追加エージェントはない。

### 配信前検証の準備

既存サービスの認証経路で全3接続を読み取り、ID・在庫集計タブを照合。3シートともデータ674行・12列（ヘッダ含む675行）で値は完全一致。SHA256は `1fa4605ca28c175759631271b1141640fbf20c4524afa55603b188a2453e8564`（JSON UTF-8・ensure_ascii=False・区切り空白なし）。式として取得したセルで先頭=は0件。退避先は /private/tmp/line-three-sheets-before.json。現時点の配信候補は432行だが未完了1原文の復旧前プレビューであり、最終配信件数ではない。既存674行との母集団・時点が異なるため、その差を今回修正による減少と断定しない。配信直前に再度対象・内容を確認して退避する。

Context7はツール一覧で利用不可。PO許可済み代替として[gspread公式Worksheet資料](https://docs.gspread.org/en/latest/api/models/worksheet.html#worksheet.get_all_values)で読取メソッドを確認。表示資料は6.1.2、本番実物は6.2.1のため本番inspect.signatureでもvalue_render_option/pad_values等の対応を照合した。UNFORMATTED_VALUEで値、FORMULAで式を退避した。書き込みは行っていない。既存配信は全targetへ同じ12列をRAWで渡すため、配信後は3シート間の一致と、配信対象行の多重集合を照合する（同順位行の順序だけで誤判定しない）。

### 次周の商品名15件・状態候補5件

- 再解析後の全1425明細に対し、確定BOX商品かつ名称/状態/備考にSAR/AR/PSA/BGS/CGC/ARSの表記を含む行を再検出。該当15行は全て前節のトウホク/フクオカPSA6〜9、raw_unit=枚、condition=FLAG_SINGLE。既存配信設定では対象外。
- 実コードtcg_analyzer_svc.py:323〜344は「箱系」単位のときだけBOX商品に絞り、それ以外は全候補を返す。DBの「枚」aliasはPiece/単品系。単位が枚でもBOX候補が残ることを確認。単位フィルタの全区分への変更は今回の復旧範囲外。
- 辞書案はPM0182/PM0189へPSA除外各1件。現在DBの判定再現は1425/1425不一致0。対照では対象15件のみNONE、他1410件不変、正式名称293件の判定変化0、名称/状態/備考×PSA/PSA6/PSA10/psa9/非該当部分文字列の36対照が全成功。line-psa-expanded-contrast.jsonへ保存。これは読み取りの対照結果であり、新たな本番辞書変更ではない。
- 状態の全量候補抽出では、Sealed box/Caseなのに名称/状態/備考に開封・損傷等の表記がある5行を検出。3行は既存状態辞書の語が備考にあるが、状態判定へ備考が渡されず通常BOXになる。既存関数の局所比較で、OP-17の凹み/破れ2行はDamaged sealed box、プレシャスコレクターボックスの検品開封1行はOpened boxとなる。現在保存の判定と局所再現は5/5一致。対象ID・根拠は line-state-memo-contrast.json。
- 残る2行は「箱にテープ剥がし跡」（商品未確定）と「伝票貼り付けあり」（商品確定）。現在状態マスタに該当語がなく、備考追加だけでも状態は変わらない。これらを損傷扱いにする事業上の定義は未確認。PO判断なしの語追加をしない。
- 備考を状態判定へ一般適用した場合の正常例・否定文・送料/免責文・区分間の影響は未検証。局所3件の改善だけで全体設計合格を出さない。状態の本番修正は未実施。

補足: 上記の全量は07:30:24Zの固定1425明細。後続の新着や復旧で増える明細は別の母集団として比較する。原文を含むJSONは/private/tmpに保持しGitへ複製しない。

状態の追加対照: 語を列挙する候補抽出だけでは「ダメージ(大)/(小)」を拾えなかったため、全1425件を状態判定関数で比較した。保存済みの最終単位を固定した局所再現は1425件不一致0。備考を加えると17件（Damaged caseへ14件、Damaged sealed boxへ2件、Opened boxへ1件）が変化し、他1408件の状態は不変。各17件の原文行範囲も直接読み、損傷/開封表記を確認した。これは全解析パイプラインの再現ではないため、単位再計算・否定文・別商品の備考混入などの回帰検証は残る。17件を次の設計用候補として /private/tmp/line-state-memo-all-function-contrast.json に保存。前記3件を含む拡張結果であり、3+17件とは数えない。伝票/テープ跡の2件の定義は引き続き未確認。


## 2026-09-10 #3403復旧後の抽出完了と配信前確認

- PR #3403: GitHubでMERGED、2026-09-10 17:43:53 JST、merge SHA 3bdf33d55d1dc7ee90a7eea7fd112dc76d51b1feを直接確認。Deploy to VPS 34456746721 success。後続の本番HEAD d715d998（#3407）はdocs-only差分、deploy34459619587 success。/api/healthはstatus ok、database/redis/celery connected。誤って/healthを照会した404は正規の健康確認結果には使わない。
- 本番2jobはmigration所定のerror・復旧マーカー。原本active/superseded、items0を再照合し、既存retry_extractionへ有効job bfa07018-9b34-42b6-990a-017e3c1cf140だけを渡した。応答enqueued1/skipped0。無効旧job6da3ca68-651e-4ff6-8316-1c9135508ad2はerrorのまま再実行していない。
- workerのTCG_AUTO_ANALYZE=1を直接確認。対象jobは2026-09-10 18:28:22 JSTにdone、prompt raw-extraction-v3-work-p1。18明細・18解析、全件name-first-v3-work、error_message NULL。後続確認で未完了jobs0/analysis_runs0。
- 原文と18明細を照合。商品名・価格・数量の抽出を確認し、2件の状態/備考問題を検出した。これを全体精度100%としない。PSA数量600と括弧内40×16の不一致は原文自体の記載であり、AIが推測で補正しない。該当行はFLAG_SINGLEかつ単位未確定で配信対象外。
- 2026-09-10 18:28:49 JST、3接続（山崎涼太郎・無料トライアルシート・配信テスト）の在庫集計の値/数式を退避。接続ID・spreadsheet ID・tabが先行退避と全件一致、各674行＋12列ヘッダー、3接続の値一致、数式0。include_flag_single=falseを確認。新たな配信予定445行。旧674との差は異なる時点/対象のため精度改善率に換算しない。

### 配信前に見つかった2件

| 商品 | 原文/抽出 | 現在の配信値 | 訂正候補・状態 |
|---|---|---|---|
| PM0268 4周年!四皇トレジャーゲット キャンペーンパック | raw_memo=※未サーチ品 | condition=Searched pack、note=未サーチ | CN0007 Unsearched packが実マスタに存在。備考を状態入力とした純関数対照でSearched→Unsearchedを確認。実DB値は未変更 |
| PM0141 新たなる皇帝 | raw_state=伝票剥がし跡あり | condition=Case、note=NULL | 「通常カートン＋備考へ原文記載」か「傷ありカートン＋備考へ原文記載」かをPOへ1問提示、回答待ち。定義を推測しない |

明細ID: PM0268=43da051f-e482-4e85-8ced-7f09154b7a0a、PM0141=d9d46717-6cd6-4fa4-9159-084ac342d799。いずれも有効source afbc08d1-cf3b-43be-87e5-4b7200144b6c配下。個別の訂正を行うなら対象ID、原値、原文、条件UUID、変更行数、訂正履歴、再解析時の保持/再発まで明記した設計と正規カードが必要。

原因実物: tcg_analyzer_svc.py:678の状態入力はstate+nameだけ、:719のパック既定はSearched pack、:1145の注記入力はmemoだけ。tcg_distribution_svc.py:215,218は解析結果の状態/注記を直接配信する。item_corrections_svc.py:54以降で配信元へ反映するのはproduct_idだけ。条件訂正を保存しても配信元を直したことにはならない。

検証の区別: rootが本番ジョブ/原文/18解析/3シート退避/条件マスタと純関数対照を直接実行。既存実装担当はコード読取だけで、別の状態/注記訂正経路がないことを回答。新しい実装・本番訂正・配信を実行した報告ではない。調査途中の誤ったテーブル名とSyncSessionLocal importは失敗し、本番変更なし。実在するconditionsと_get_sync_sessionをコードで確認して読取を完了。

ローカル証拠（原文/シート実体は公開gitに入れない）: /private/tmp/line-recovery-retry-preflight.json、line-recovery-retry-receipt.json、line-recovery-raw-and-state.json、line-recovery-condition-master.json、line-three-sheets-pre-distribution.json、line-recovery-pre-distribution-verification.json、line-recovery-final-job-check.json。

現在地: マージ/本番反映/有効1件再解析完了、3接続退避完了、配信未実施。次の一手: POに提示した状態分類1件の回答を受け、原文に沿う状態/備考の訂正経路を設計・検証してから3接続へ配信。安全装置#8/#8bの解除・DB直書きによる迂回・不明な分類の創作は行わない。以前の「GO #3403待ち」は当時の記録であり現在の停止理由ではない。


### 配信前2件のPO決定と限定設計（2026-09-10）

PO原文「通常カートンだがNOTE_JAに記載」を受領。伝票剥がし跡ありはCase維持・NOTE_JAへ記載と確定。状態/備考の全件参照案204変更に対し、限定案は1443明細中2変更/1441不変、既存再現不一致0、否定を含む11対照成功。実マスタ73行のNJ041伝票跡を保持し新NJ079にSTATE_LITERALを設定する案、CN0007の否定除外追加を設計§13へ記録。自己審査APPROVEは限定設計だけで、実装試験/配信完了を意味しない。証拠 /private/tmp/line-condition-note-focused-contrast.json。純関数対照の範囲・今後の実DBパイプライン試験を区別した。


## 2026-09-11 商品登録から解析・配信までの接続確認

基点7606ca9a。tcg_product_master_svc.pyのcreate_productはcategory_classに作品名を保存する。tcg_analyzer_svc.pyの旧BOX共通除外は同欄のBox/Caseを参照し、新規PC_BOX登録→PSA10付き抽出済み明細の解析を架空PostgreSQLで通すと商品確定1（期待0）を再現。商品区分IDで取得するkubun_typeを優先する修正後に同試験が成功。既存有効商品29件の参照元が変わるが、固定1630明細で商品判定変更0。

末尾単位の候補選択前に商品名中の長い語を選ぶため、末尾カートンを取りこぼす。候補選択時に末尾条件を満たすものだけを見る試作で、対象55のうち4単位を回復。単位未確定33→29（商品名整合52内）。冊2件、未記載単位を自動的に箱等とみなす根拠はない。

resolve_status_v2はraw_stateだけを参照し、備考単独の完売を見ない。fetch_output_rowsはexclusion条件がない。単独備考のEXCLUDEと配信SQLを接続し、架空DBで完売行が取得結果に出ないことを確認。原文・抽出値は変更せず、解析値の再実行一致と手動product_id訂正保持も検証。

登録候補59行のうち26行はコード参照の静的検査blocking0。他33行は版・形態・メーカー・書籍分類等を継続確認。全商品登録完了ではない。顧客原文・登録用実データはPR対象外。Gemini実呼出し0、本番書込0。設計と試験の詳細はdesign-keyword.md §15およびEV-20260911-ONEPIECE-COMPLETION。


## 人の確認完了と配信を接続するための検証記録（2026-09-12）

この追補は、未解決明細を人が確認するまで配信から外すために、既存のどこが不足しているかを実コードで確認した記録。**設計合格・製品変更ではない。**

### 依頼と権限

PO原文: 「システムが解析できなかったものは全て人間が確認するので要確認に回す、要確認のものは人間の確認後に配信をするので配信リストからは外しておく、人間の確認が完了した時点で配信する」。後続依頼「離席するので推測は禁止して事実確認を怠らずに確実性を重視して最も効果があり、現状把握の粒度が細く、精度が高いエビデンスを確立して安全に進めてくれ、確立したならPRマージまで進めて良い」。

後続依頼は根拠・審査・必要チェックが揃ったPRの条件付きマージ許可として扱う。今回は設計担当による**検証記録の文書PRのみ**。本番変更・製品実装・代理GO有効化・追加Gemini呼出しの許可に読み替えない。実装役への自動切替なし、サブエージェント起動なし。

### 正本と検証範囲

- 親: [商品マスタ仕様](../../specs/product-master/README.md)。在庫の状態・単位を商品の分類と混同しない。
- [ADR-154](../../adr/ADR-154-tcg-parity02-gas-python-migration.md)を参照。移植履歴のAcceptedと追加提案を区別する。
- [既存商品割当設計](../parity03-product-assign-drawer/design.md)は商品IDの変更/確認だけの契約。これを行全体の確認完了と誤認しない。
- [既存統合設計](../pmg-import-delivery-ssot/design.md) §§3–5には配信run/target/row保存、排他、unknownを含む提案が既にある。本追補は別の配信基盤を新設しない。
- 調査コードadc8bc4d67a94e8ede45a1e9c0ee9f28d28bb70bと起点main4afb81c398d26f4c9b1321a4c70f21c50e8211fbのGitHub compareは4文書差分のみ。対象サービス3ファイルのSHA256も同一。証跡JSONに記録。
- preflight成功。最新main起点の専用release/sig-review-delivery-evidenceを公式worktree手順で作成。他の未保存調査・実装差分は取り込まない。
- 本番画面/本番設定/実DB書込み/外部シート送信は未実施。Docker統合試験なし。人工データの件数は本番障害件数ではない。

### コードの観測事実

| 箇所 | 事実 | 希望との差 |
|---|---|---|
| `backend/app/services/tcg_analysis_review_svc.py:46` | 要確認タブは商品未確定・単位未確定・exclusion非NULL。正常タブはその逆 | 状態FLAG、価格欠落、needs_reviewと共通判定ではない |
| `backend/app/services/tcg_analyzer_svc.py:957` | needs_review理由はpid_unresolved / multi_candidate / note_unmatched | 単位・状態・価格の全体確認状態ではない |
| `backend/app/services/tcg_distribution_svc.py:183` | 商品/単位確定、価格非NULL、非excluded、非FLAGが基本。needs_review未参照 | 人確認待ちの全件除外を保証しない |
| 同`:203` | include_flag_single=trueでFLAG_SINGLEを許す | 本番設定値は未確認。新しい共通ゲートをこの例外で抜けない設計が必要 |
| `backend/app/services/item_corrections_svc.py:15` | 修正履歴は全フィールド保存。解析結果更新は商品IDの変更だけ | 状態/単位/価格/数量/備考の履歴保存は配信値反映と同義でない |
| 同`:54` | 同じ商品IDを確認したときは解析UPDATEしない | 商品確認履歴≠行全体の配信承認 |
| `backend/app/routers/item_corrections.py:54` | super_adminのみ。field_nameは文字列、旧値/原文IDをリクエストで受ける | 完了時の版一致・対象関連・必須値をサーバーで検証する契約が必要 |
| `frontend/src/features/tcg-analysis-review/SupplierDetailView.tsx:97` | 比較欄はreadOnly=true | 全項目修正/完了の画面としては未接続 |
| `frontend/src/features/tcg-analysis-review/ItemComparison.tsx:23` | 汎用修正保存ボタンdisabled=true | ボタン有効化だけではサーバー契約の不足を解消しない |
| `frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:420` | 商品修正/確認はcorrections API→表示更新 | その後の配信起動ではない |
| `backend/app/services/tcg_analyzer_svc.py:1116` | 商品修正履歴のある行を再解析対象から保護 | 確認対象版と原文更新後の扱いを明確化する必要 |
| `backend/app/services/tcg_distribution_svc.py:411` | シートをclearしてappendする全置換 | 明細追記方式ではない。途中失敗・並行実行の確認が必要 |
| 同`:628` | 全配信先への実行、未完了run/jobガードあり | 確認待ち1件で他の正常行を止めることと、処理中ガードは別 |

### 直接実行した検証

[機械可読結果](review-delivery-evidence.json)は匿名人工データのみ。顧客原文・認証情報なし。

1. 実関数`_build_where`で要確認条件を生成し、`fetch_output_rows`の実WHEREを抽出。商品確定2×単位確定2×exclusion3×価格2×状態2×needs_review2×数量2=**192組**をSQLiteメモリ表で照合した。
2. 要確認176組、通常配信8組。そのうち**要確認タブと配信の両方に入る4組**（exclusionがexcluded以外の非NULLという人工条件）。**needs_review=trueで配信される4組**、**数量NULLで配信される4組**。これらは重複し得るため合算しない。**配信から外れるが要確認タブにも出ない12組**を確認。SQLiteはこのWHEREの論理確認にだけ使用し、PostgreSQL/結合/権限/実運用全体の試験とは称しない。
3. 実`save_corrections`関数へSQL記録用の偽セッションを渡して**7ケース**確認。商品変更1件だけ解析UPDATE=1、同一商品確認/単位/状態/価格/数量/備考の6件はUPDATE=0。全7件で履歴INSERT=1、commit=1。実DBの制約・保存成功を確認した試験ではない。
4. 192組と7ケースは成功率を算出する正解データではなく、現在の条件の不一致と更新責務を確定する対照試験。固定ソースのハッシュと再現コードを下に残す。

### 効果が直接見込める順序と設計の境界

**第1優先候補: 要確認と配信の共通判定。** 上記の不一致を1か所の条件へ収束させる。モデルや商品辞書の精度を上げる前に、検出済みの未解決が配信される経路と、確認一覧から漏れる経路を塞げる。ただし本番の削減件数や最終正答率は未測定であり「最も効果がある」と数値比較で断定しない。

**第2候補: 全項目の確定値と確認完了。** 原文/機械値/人の修正を区別し、必須値・マスタ有効性・版一致をサーバーで検証する。修正保存と配信許可を分離。既存のsuper_admin権限を維持し、権限拡張を推測で決めない。

**第3候補: 確認完了→配信待ち→接続先別結果。** 既存統合設計の配信履歴・排他に接続。確認のcommit後に起動を落としても配信待ちを失わないこと、同時確認で旧一覧が新一覧を上書きしないこと、結果不明を成功扱い/自動再送しないことを先に実証する。全体置換なので「確認した1行を追記」しない。

正式設計へ進むための未解決項目: 商品・単位・状態・数量・価格・備考の確定条件と例外、手動確認の対象版/有効期間、保存先の既存schema適合、確認commitと配信待ちの原子性、接続先での結果照合とunknownの復帰手順。外部APIの原子性/冪等性は未確認のため保証しない。

将来の受入検査: (a)未解決の各理由が要確認に表示され配信0、(b)同投稿の正常行は配信対象、(c)未解決のまま確認完了不可、(d)全項目修正が出力値に反映、(e)原文/修正者/時刻/対象版保存、(f)競合確認/再解析で古い値を承認しない、(g)3接続先の一部失敗を全体成功と表示しない、(h)確認保存直後の停止でも配信待ち消失0、(i)結果unknown時の二重送信防止。これらは未実行。

### 同一AIの自己審査と保存判断

- **検証記録のレビュー: APPROVE**。主張を実コード/192条件/7捕捉試験に限定し、数値の意味・未確認・再現手順を明示。独立した第二者レビューではない。
- **製品設計: REVISE**。未解決の契約を残して実装カードを発行しない。文書PRが通っても実装・配信の合格とはしない。
- 外部導入事例は今回不要。既存システムの判定差を確定するための直接証拠が対象であり、他社の成功数値はこの挙動の証明にならない。
- 維持: 現在は人手のコードレビューと文書チェック。今回の局所検査を製品の恒久CIと呼ばない。実装時には判定共通化と確認/配信の障害試験を既存backendテストへ接続する設計が必要。
- 文書PRのみSTANDARD-WORKFLOW §5の書類区分。マージ条件は文書差分のレビュー完了とGitHub必須チェック通過。製品の二者検証・POによる本番確認を代行したとは扱わない。

### 再現用コード（リポジトリルートでPython標準ライブラリのみ、出力先は一時ディレクトリ）

```python
from pathlib import Path
import json,ast,asyncio,hashlib,itertools,sqlite3
W=Path.cwd()
s=(W/'backend/app/services/tcg_analysis_review_svc.py').read_text();f=next(x for x in ast.parse(s).body if isinstance(x,ast.FunctionDef) and x.name=='_build_where');ns={};exec(compile(ast.Module(body=[f],type_ignores=[]),'source-filter','exec'),ns)
w,_=ns['_build_where'](query=None,provider=None,status_tab='NEEDS_REVIEW',review_only=False,unregistered_only=False,unresolved_unit_only=False)
ds=(W/'backend/app/services/tcg_distribution_svc.py').read_text();pred='WHERE ar.pid_resolved = TRUE'+ds.split('WHERE ar.pid_resolved = TRUE',1)[1].split('ORDER BY',1)[0];pred=pred.replace('{cond_filter}',"ar.condition_canonical NOT LIKE 'FLAG_%'")
con=sqlite3.connect(':memory:');con.execute('CREATE TABLE a(id INT,pid_resolved INT,unit_resolved INT,exclusion TEXT,price_normalized REAL,condition_canonical TEXT,needs_review INT,quantity_normalized REAL)');rows=[]
for n,(pid,unit,ex,price,cond,needs,qty) in enumerate(itertools.product([0,1],[0,1],[None,'excluded','other'],[None,100],['FLAG_SINGLE','Sealed box'],[0,1],[None,10])):rows.append((n,pid,unit,ex,price,cond,needs,qty))
con.executemany('INSERT INTO a VALUES(?,?,?,?,?,?,?,?)',rows)
rv={x[0] for x in con.execute('SELECT id FROM a ar '+w)};dist={x[0] for x in con.execute('SELECT id FROM a ar '+pred)}
cases={r[0]:r for r in rows};summary={'synthetic_combinations':len(rows),'review_tab':len(rv),'distribution_default':len(dist),'both_review_and_distributed':len(rv&dist),'needs_review_true_but_distributed':sum(cases[i][6]==1 for i in dist),'quantity_null_but_distributed':sum(cases[i][7] is None for i in dist),'excluded_from_distribution_but_absent_review':len(set(cases)-rv-dist)}
source=(W/'backend/app/services/item_corrections_svc.py').read_text();func=next(x for x in ast.parse(source).body if isinstance(x,ast.AsyncFunctionDef) and x.name=='save_corrections');env={'text':lambda x:x,'_SCHEMA':'tenant_004'};exec(compile(ast.Module(body=ast.parse('from __future__ import annotations').body+[func],type_ignores=[]),'actual-save-correction','exec'),env)
class Capture:
 def __init__(self):self.statements=[];self.commits=0
 async def execute(self,s,p):self.statements.append({'sql':s,'parameters':p})
 async def commit(self):self.commits+=1
async def trial():
 out=[]
 for field,old,new in [('product_id','a','b'),('product_id','a','a'),('unit','Case','Box'),('condition','FLAG_SINGLE','Sealed box'),('price','1','2'),('quantity','1','2'),('memo','','memo')]:
  db=Capture();await env['save_corrections'](db,extraction_item_id='fixture',source_message_id='fixture-source',fields=[{'field_name':field,'system_value':old,'human_value':new}],corrected_by='fixture-user')
  out.append({'field':field,'changed':old!=new,'inserts':sum(x['sql'].startswith('INSERT') for x in db.statements),'analysis_updates':sum(x['sql'].startswith('UPDATE') for x in db.statements),'commits':db.commits})
 return out
c=asyncio.run(trial());assert c[0]['analysis_updates']==1;assert all(x['analysis_updates']==0 for x in c[1:]);assert all(x['inserts']==1 and x['commits']==1 for x in c)
report={'method':'Actual Python functions with SQL captured; WHERE predicates on synthetic SQLite table. No Postgres, network, product writes, or model calls. Counts are combinations, not production incidents.','source_commit':'adc8bc4d67a94e8ede45a1e9c0ee9f28d28bb70b','matrix':summary,'corrections':c,'files':{str(p.relative_to(W)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [W/'backend/app/services/tcg_analysis_review_svc.py',W/'backend/app/services/tcg_distribution_svc.py',W/'backend/app/services/item_corrections_svc.py']}}
print(json.dumps(report,ensure_ascii=False,indent=2))
```


## 2026-09-12 商品マスタ参照による作品ID判断

起点: 66b41766（origin/mainから専用worktree）。先行本番調査時4afb81cとの製品3ファイル差分0。
直接確認: backend/app/services/gemini_extraction_svc.py:32（推測・ID禁止）、:45（型番のみ空欄）、:153（表示名と別名だけ参照）、backend/app/tasks/tcg_extraction.py:148（作品一覧を渡す）、backend/app/services/tcg_analyzer_svc.py:400（tcg_series）、:408（原文根拠）、:516（作品不明の型番禁止）、:1160（◆等の正規化）、:1181（作品検証）。
本番celery-workerの対象ファイルもssh経由で読み取り、同じ契約を確認。TCG_SCHEMA=tenant_004。

本番SELECT実測（2026-09-12 JST、本セッション実行）:
- NR0022 PRODUCT_NAME REMOVE ◆ enabled=true。CONDITION/NOTE/UNIT/STATUSの対応4ルールもenabled=true。
- 有効原文に紐づく解析1557明細: 要確認なし1041、pid_unresolved444、pid_unresolved/multi_candidate32、pid_unresolved/note_unmatched22、note_unmatched14、3理由複合4。
- latest群をcreated_at >= 2026-09-11T23:00:00Zで切った観測:320明細、要確認120、商品未解決114。この時点の時刻フィルターであり、正式なimport_job識別の代替ではない。実行前に正式な取込IDとリンクで固定する。
- 原文UUID 29f19cc0-07be-43ef-a4ff-5bc668320fae:19明細、商品確定0、要確認19。created_at=2026-09-11T08:11:50.491655Z。直近320件の母集団とは別。「◆OP-01」作品原文欄空、line59–61、engine=name-first-v6-master-safety。投稿は型番を列記し、作品見出しなし。19件全ての正解作品をモデルの推測で確定したわけではない。
- OP-13抽出名「受け継がれる意志【OP-13】」の引用見出しは「【在庫品】 ワンピースカード」（最新投稿の2明細）または「【ワンピースカード】」（前日）。作品マスタはOne Piece／ワンピースの単一別名。完全一致検証では採用されない。
- 有効商品293、work_id NULL0、作品8。code/title/english_title/mark/work_id/search/excludeを集約したJSON相当68143文字。実トークン数・料金・Gemini正解率は未計測。
- PR #3417はOPEN、HEAD1186384cf6f743cc50035c380aec188012eb5e19。発送条件等の原文保持変更があるが本番未採用。

### PM0181正式名の明示依頼による訂正

PO原文:「受け継がれる意志→マスタの名前を修正してくれ」。
公式根拠: [バンダイ商品情報](https://www.bandai.co.jp/catalog/item.php?jan_cd=4582769864865000)。「受け継がれる意志【OP-13】」。
対象tenant_004.tcg_products、UUID26b15871-7ab6-4bbe-89f5-66280166e822、code PM0181、mark OP-13。
変更前JSONを /tmp/salesanchor-pm0181-before.json に退避。ローカル一時保存であり永続バックアップとは称さない。
所定permit-danger.shの書込みが最初PermissionErrorで停止。権限審査で同じ所定手順を実行し成功。ガード解除／別経路への迂回なし。
id/code/変更前名称の全一致を条件にjapanese_titleのみ「受け継がれる意思」→「受け継がれる意志」。UPDATE 1。別SELECTでPM0181／受け継がれる意志／OP-13を確認。検索キーワード2件の「意思」は未変更、再解析・配信未実行。行全体の変更前値は公開PRへ含めず、今回訂正した3値だけを記録。

### 調査の限界・再現手順

SQLはPGOPTIONS=-c default_transaction_read_only=onを使用（上記名称1件の明示修正を除く）。初回の標準入力形式はpsql-write-guardに拒否されたため、ガードに明記された-c SELECT形式で読み取りを実施。生の顧客投稿は公開文書へ載せない。
現在の解析値を正解ラベルとみなさず、未解決減少と誤確定増加を別々に比較する。プロンプト内のモデル名からSDKの仕様やトークン上限を推測しない。


### PR #3441 検証・退避記録

[PR #3441](https://github.com/shingo-ops/salesanchor/pull/3441)をready提出。初回CIの並列収集はランダムUUIDパラメータの不一致で失敗し固定UUIDへ訂正。run34663710924（6c47fe18）は2604成功/95skip/1失敗、coverage62.38%。唯一の失敗は旧状態/注記fixtureで新schema未準備・作品参照欠落。実migrationと架空作品参照を追加（8d245eac）。直近検証結果はPRのHEAD付きチェックを参照し、旧HEADの結果を新HEADの合格とみなさない。
承認gate job103471510004（run34663790634）を含む各回は番号付きGO記録が無いため失敗。POの一般的な条件付き実行依頼を「GO #3441」と代筆しない。マージ/機能配備/再抽出/再解析/配信は未実施。
本番9表（extraction_jobs/extraction_items/analysis_results/item_corrections/source_messages/tcg_products/tcg_series/product_search_keywords/product_exclude_keywords）をpg_dumpで読取退避。ローカル/private/tmp/salesanchor-line-work-before-3441.sql、17837898 bytes、SHA256 399c9e9a6df673ef888143214ab612ca7a6d8b975d38f537cdd83ef6aa284e3b。公開PRにデータ本体を含めない。一時保存であり永続退避の保証は無い。本番実行前に対象の鮮度と退避の読取可能性を再確認する。


## 2026-09-13 PR #3441再開・main追従

PO原文「進めてくれ」を受領。gh pr viewでOPEN、HEAD e25b09a9887cde20b0c2a561e681b50baf850c28、mergedAt null、mergeStateStatus DIRTYを確認。前回Backend CI34663978933は2606 passed/95 skipped、失敗0、coverage62.53%。番号付きGOの承認経路は未充足。

origin/main 5b21b3b8の追従でevidence-registry、商品マスタREADME、tasks/todoの3ファイルに追記位置の競合を確認。両方のテーマを保持して解消。製品コードの競合なし。runnerは双方のmigration登録を自動統合。追従後HEADのCIで再検証し、結果はPR #3441本文に記録する。Gemini実呼出し・本番再解析・配信は未実施。


## 2026-09-13 PR #3441本番反映・再抽出停止記録

POから番号付きGO #3441を受領（実メッセージ先頭に鉤括弧あり、PR本文に原文保持）。最終HEAD5c96611fのBackend CI34729142077は2698 passed/95 skipped、失敗0、coverage62.94%。全必須チェック成功を確認後、gh-pr-merge-safe.sh --mergeで09:58 JSTにマージ。merge SHA ee455fb1ba4c7ad407ed6506ee4fe515fce371a8。Deploy34729320369はsuccess。本番git HEAD一致、backend ENGINE_VERSION=name-first-v7-gemini-work-id、prompt=raw-extraction-v4-work-id-p1、追加列参照成功を直接確認。正式/api/healthはDB/Redis/Celery connected。最初に誤った/healthへ確認し404、その後正規パスをスクリプトから確認して成功した。

変更前: 最新import_job536422ed-79c7-4a87-a887-09a02b97968f（09:31 JST）は44有効投稿、done37/empty6/error1、762解析/要確認166。error1はSoftTimeLimitExceeded。3配信接続を確認。9表の追加退避18558933 bytes、SHA256 cfb28a14f61a09841d190712b7b8c21df1bdfba7c30a002a93893f48127f5fa4。取込リンク・原文・3接続設定もローカル非公開で退避。退避SQLとレポートは/tmp保存であり長期保管とは称さない。

本番反映後10:02:55 JST: 最新取込内でOP型番・要確認を含む投稿を明細数・ID昇順で選択。source8eff4338-34a8-4ea1-9d89-b6a99edd8350、旧1明細/要確認1。SELECT限定・READ ONLY接続で旧抽出/解析と現マスタを読み、transaction終了後にGemini実呼出し1回。呼出し前後マスタSHA一致。戻り値error/items0、error_message=`v3 extraction has an invalid product source span`。v4も共通パーサーのこの文言を使うため旧prompt動作とは判断しない。

観測事実: パーサーはL0001またはL0001-L0005形式を要求。新promptはLine ID範囲と入力の[L0001]を指示するが、厳密な出力形式の例がない。既存extract_messageは例外時raw_responseを空にするため、今回の応答表記そのものは未確認。特定の括弧/区切り記号が原因とは断定しない。抽出エラーによりRAW一致比較と作品IDの正誤判定は成立していない。

結果: 本番コード反映済み。新結果DB保存0、旧明細/訂正/解析更新0、配信0。精度向上未確認・結果採用保留。追加Gemini呼出しと再解析を停止。保留を解く設計は、行番号出力契約の明確化と非公開の診断記録、模擬応答の否定試験。POの検証失敗時停止指示により、本便では追加修正/再反映しない。同一AIの実装/自己確認であり独立レビューではない。

一次根拠: PR https://github.com/shingo-ops/salesanchor/pull/3441 （GO原文・最終結果記録）、CI34729142077、Deploy34729320369、ローカル比較JSON SHA256 48b573dcc561e37db160c225afd5305c55524cdeac5ab06ab866165cdc9fd715。比較JSONは顧客情報を含むためリポジトリへ入れない。本番稼働と今回のデータ採用/配信を区別して保存した。


## 2026-09-13 行番号修正の着手・ローカル検査

POが前述の停止報告と修正質問へ「進めてくれ」と回答。設計§16.12の自己審査APPROVE、CARD-LINE-WORK-SPAN-02を既存カード末尾へ発行。card-lint終了0、長行9警告。p2プロンプト・p1互換・形状のみ診断を実装。make lint-ci終了0、ruff/Bandit成功。mypyは依存不足を含む既存警告のため完全な型検査成功とは扱わない。Docker不在でローカルpytest未実施、実PGはCIへ。追加Gemini実呼出し0、追加本番更新/配信0。後続PRへGO3441を流用しない。


## 2026-09-13 GO #3458受領

PO原文「GO #3458」を11:04 JSTに受領確認。HEAD44fac147のCI34731045931は2710 passed/95 skipped、失敗0、coverage62.95%。最新main d9f8629cへ追従、台帳競合は本件とAndroid側の各最新行を保持。本番9表を再退避18652912 bytes、SHA256 5ea522ebb075c0b8a1dd6c7cab981b502b7eed66da95c29edb9194b3a6fa8c35。最終CI/マージ/本番反映/比較結果はPR3458本文へ実測で追記する。受領時点の追加Gemini呼出し・配信0。


## 2026-09-11 抽出2投稿中断の原因調査（実装未着手）

結論: 抽出API呼出し後・抽出結果保存前に、デプロイが担当workerを強制削除した。検索語/除外語の照合段階には到達していない。今回のPR3434マージ・配備を進めた本セッションは抽出終了前に配備を進めていた。配備と抽出の競合を防ぐ確認が不足した。

### 観測事実と時系列（JST）

| 時刻 | 証拠で確認した事実 |
|---|---|
| 17:20:02.147 | 投稿A（66商品行）のworker子プロセス2がAPI呼出し開始、入力1980文字 |
| 17:20:17.333 | 投稿B（1商品行）の子プロセス1がAPI呼出し開始、入力224文字 |
| 17:20:22.441 | deploy run34578529308が非backendサービス切替を開始 |
| 17:20:31.957 | 同runで旧workerコンテナacf087854064のforce-rmが完了 |
| 17:20:36.461 | 新worker起動 |
| 配信前確認 | 2jobsともrunning、抽出items0、extracted_at/error_message null、Celery active空 |

Lokiの旧workerログのfilename内コンテナIDは、deployのforce-rm出力IDと一致。17:19:50〜17:20:40の46ログを取得し、対象両プロセスはAPI開始以降応答受領/分析開始/完了ログなし。対象job/task/source識別子を17:10〜18:20で照会して得られた4ログも受信2・抽出開始2のみ（照会終了時点より未来部分を含むため、将来の再実行不存在を主張しない）。API事業者側で計算が完了したか、課金されたかは未確認。入力を読めない・商品語不足・API制限/タイムアウトを原因とする証拠はない。開始から削除までは約30秒/15秒で、当該taskに設定されたsoft100秒/hard120秒より短い。

### コードと再現根拠

事故前7606ca9aと配備2ac5e81aのbackend/app/tasks/tcg_extraction.pyはSHA256同一=f2f1c5cf56537a294dcf1efe64480970f9ded6379968b93c07cd60fd30472b90。
- `.github/workflows/deploy.yml:332-335`: celery-workerを含むコンテナをdocker rm -fしてから起動。実行中抽出の終了待ち・受付停止の確認はこの手順にない。
- `backend/app/tasks/tcg_extraction.py:104-142`: pendingだけ取得し、API開始前にrunningをcommit。
- 同`:145-219`: APIから戻った後にitemsを書き、done/empty/errorをcommit。今回この保存へ到達せず。
- 同`:119-130`: runningはno_pending_jobとしてreturn。単純な再投入では中断状態を回収できない。
- 同`:84-96`: 通常例外も戻り値errorに変換するだけでDB状態をerrorに戻さない。今回この例外経路を通った証拠ではなく、追加で確認した欠陥。
- `backend/app/celery_app.py:52-53`: acks_late/reject_on_worker_lostは設定済み。ただしDB側のrunning限定回収を実装した証拠ではない。

実関数ASTを実行し、DBと外部APIだけを偽物にした局所試験3件成功: ①running commit後の中断でrunning/結果0残留、②同ジョブ再実行はno_pending_job、③通常例外も戻り値error/DBrunning。実Celery強制終了の統合試験ではない。外部API実呼出し0。

### 必要な対策案（未承認・未実装）

1. 配備時は新規抽出の受付を止め、実行中が0になるまで終了を待つ。待てない場合は配備を止め、強制削除へ進まない。確認後の新規開始との競合も防ぐ。
2. jobに開始時刻/試行ID/実行者/生存確認を残す。実行者消失を確認した中断だけを失敗/再実行候補へ移し、現役ジョブを横取りしない。再試行上限・二重抽出/二重保存防止が必要。
3. API応答を受け取ったら、解析前に再利用できる形で保存する。中断前に受領していなければ復元できないことも明示する。
4. エラー時は戻り値とDB状態を一致させ、段階/原因を記録する。配信の未完了停止は維持する。
5. 模擬APIで処理途中のworker停止、配備との競合、保存直後停止、再実行・重複0、未完了の配信拒否を実DB/Celeryで検証してから設計合格・実装判断を行う。

今回の2投稿復旧: 抽出結果が0件のため、システム解析だけの再実行では商品行は生成されない。Gemini禁止を維持する場合、保存原文から抽出データを別途作成し、数量/価格/単位/状態/発送条件を照合してから正式な入力経路で登録する工程が必要。66行を単位未記載のまま全てBOXと推定してはならない。本調査では再抽出・商品投入・製品修正なし。

### 現在の運用状態・保存先

PO明示承認により2jobsはerror、原文保持。既存手修正が再解析で消えた別1商品は値を復元しexcluded。18:06JSTに584行×3シート配信、再読全セル一致。成功扱いに変更して配信したのではない。原因修正・2投稿復旧は未実施。

非公開証拠: /private/tmp/onepiece-research/stopped-loki.json, stopped-worker-final.json, stopped-followup-loki.json, deploy3434.log, incident-source/, reproduce-interruption.py, reproduce-interruption-result.json, finalize-stopped-two-receipt.json, delivery-receipt-private.jsonl。顧客原文とログ実体はGitへ含めない。 これらは調査時のローカル保存名であり、リポジトリ内ファイルの引用ではない。

ログ照会の仕様だけ[Grafana Loki公式API](https://grafana.com/docs/loki/latest/reference/loki-http-api/)で確認（2026-09-11）。Context7はツール一覧に存在せず、PO許可済み代替を使用。外部導入事例は、本番ログ・当該コード・局所再現が直接証拠のため不要。


### PO限定許可後の再抽出（2026-09-11 18:36JST）

PO原文「失敗したもののみ再抽出を許可する」。既知の2jobだけerror/items0と配備完了を再確認し、既存retry_extraction(job_ids=2ID,scope=None)を実行、enqueued2/skipped0。workerログのAPI呼出し2回・HTTP200応答2回・done2を確認。他投稿は再抽出なし。

結果: 66行投稿=66items、1行投稿=1item、合計67itemsが保存され、既存システム解析も自動完了。66行の原文商品名包含・数量・価格を順序と対応づけて照合し不一致0（状態/共通発送条件まで全正解を意味しない）。もう1行も原文op-17/30box/15500円と抽出値一致。

配信可能な新規行0。66行側は商品確定59/未確定7、単位確定1(Set)/未確定65、状態FLAG_SINGLE66。単位回復1件でも既存状態FLAGが維持される点は追加調査対象。もう1行はBox・30・15500確定だがpid未確定。原文未記載の単位をBOXと補完せず、商品確定を作為的に通さない。

配信データは584行で前回と全セル同一。接続3シートを再読し各584行+ヘッダの全セル一致を確認したため、同一内容の再書込は行わず既存配信を維持。抽出失敗は解消、解析の未確定事項は残存、対策コードは未実装。

証拠: /private/tmp/onepiece-research/retry-authorized-two-receipt.json、retry-two-worker.log、retry-two-results.json、retry-two-audit.json、retry-two-sheet-verification.jsonl。Gemini許可は今回の失敗2投稿だけで継続許可と扱わない。


### 再抽出67明細の4項目集計（2026-09-11 19:03JST 本番再読）

対象は今回再抽出した2投稿の67明細。ファイル全体/配信584明細の集計ではない。システム上の未確定件数と原文上の誤り件数を区別する。

| 項目 | 実測 | 判定の意味 |
|---|---:|---|
| 商品未確定 | 8/67 | pid_resolved=false。確定59件を全件正解と認定した数値ではない |
| 単位未確定 | 65/67 | unit_resolved=false。確定2件はBox1/Set1。SIG商品行66件のraw_unitは全て空 |
| 状態が単位不明由来のFLAG | 63/67 | condition_basis=R4:単位既定:単位不明。うち1件は後処理でSet回復後も状態FLAGが残る |
| 状態がプロモ判定由来のFLAG | 3/67 | condition_basis=R1:プロモ。前項と別で合計FLAG_SINGLE66。真のSingle商品66件/状態誤り66件という意味ではない |
| NOTE未照合 | 1/67 | raw_memo=業者、note_ja空、note_unmatched。業者を顧客向けNOTEへ出すべきかの正解判断は別 |
| NOTE生成 | 2/67 | サーチ済み可能性/買取品のメモと、雑誌プロモ付きのメモ。語句変換2件の存在確認で、情報全ての網羅認定ではない |
| NOTE空欄・うち抽出メモも空 | 65/67・64/67 | 空欄65件全てを漏れとは数えない。共通配送条件は個別商品NOTEの未照合1件と混ぜない |

上記の未確定/FLAG/NOTE未照合のいずれかに該当する実明細は重複除去67件。配信追加可能0。needs_reviewは8件のみで、単位未確定なのにneeds_review=falseが58件ある。画面の要確認件数だけでは未確定数を把握できない。最大の詰まりは単位65件と、それに関連する状態判定。

商品未確定8件: op-17 / 25thアニバーサリー / 最強ジャンプ 頂上の強者 プロモ / ナツコミ2026メタキラカード ワンピース ルフィ / 肉ルフィカード モンキー・D・ルフィ P-159 プロモ / ONE PIECE × ROUND1 プロモパック / ONE PIECE CHOPPER’s / プレミアムカードコレクション ONE PIECE DAY’24。未登録商品8件と断定しない。

原文で全明細に具体的な状態・販売単位があるわけではないため、真の誤判定数は上表から算出しない。具体的商品行の未開封1件はraw_stateに存在してもプロモFLAG、買取品1件はBox既定Sealed boxとなっている。仕様適否/修正要否の追加調査対象とし、独断で正解状態を作成しない。

証拠: /private/tmp/onepiece-research/four-field-current.json（2026-09-11T10:03:02.728608Z）/four-field-audit.json。Gemini使用0、再解析・DB変更・シート変更なし。


### 旧Knowledgeを使う単位・状態補完案（2026-09-11、草案）

指定ブック1or39_glwYtF9OfOxXizN8ZjcUKL0hNIeW3qP3nCx3AIのgid1382951829/API解析を認可済みサービスアカウントでread-only取得。7行目は仕入元別Knowledge33セルが非空。I7（原屋敷 悠）/AA7（ヒロト）に状態表記なし→Box/Sealed box。AE7（村上 宝聡）には単位なし→Sealed boxも存在。一部仕入元の単位省略ルールを全仕入元へ広げる根拠はない。I7の数量+単位+価格構文と今回SIGの数量@価格構文は異なり、旧列と現行supplier/channelの同一性・対象書式を検証する必要がある。

本番の実条件マスタをREAD ONLYで読み、現行resolve_condition_v2へ架空名で入力した5ケース: 状態なし+箱系=Sealed box、状態なし+箱系大=Case、両方なし=FLAG_SINGLE、箱系+シュリンク無し=No shrink box、箱系+ダメージ=Damaged sealed box。従って「状態未記載だから判定できない」は誤りで、単位の根拠不足が今回の中心。

草案の順序:
1. 商品を一意に特定する。作品、形態、版の衝突と商品除外語を先に確認する。箱系商品区分だけで販売単位をBoxと決めない（Case/Pack等での販売を区別する）。
2. 販売単位は明細の明示→その明細に属する見出し/ブロック→仕入元ID×対象商品群/形態×投稿書式で承認された省略ルールの順。矛盾時は保留。生の単位は空のまま保持し、採用ルールID/範囲/版/根拠行を別に保存する。
3. 状態は明細/商品名/備考と適用範囲が確認できる共有条件から明示損傷・開封・シュリンク無し等を優先。否定語/可能性/他商品の注記を区別。その上で状態無記載+確定BoxならSealed box、CaseならCaseという既存既定値を使用。既定値は実物検品済みという証明ではない。
4. 最終的に単位が確定した後に状態/理由/要確認を再計算し、古い単位不明FLAGを残さない。未解決と真のSingleを同じFLAGで表さない案を検討。状態既定値と単位の逆引きで互いを根拠にする循環を防ぐ。

今回のSIG66件はBOX以外のカード/書籍/プロモ/セットを含むため、一括Box補完は禁止。仕入元別ルールの適用条件が未確立のため回復件数は未測定。原文側に単位/状態が省略される運用をルールとして合意し、67実データとBox/Case/Pack/Single/書籍/セット混在・損傷/否定・範囲境界の対照で誤補完0を確認してから設計合格を判断する。

旧指示から再利用するのは書式/見出し範囲/単位辞書/条件付き既定値/検索と除外の順。ダメージ合算・最高価格採用・NOTE全消去、入荷を発送へ置換、未登録商品をそのまま配信するSoft Failは別の業務判断であり今回へ自動移植しない。日本語/中国語版も商品同一性へ影響するためNOTE付加だけで混同を解決したとしない。

証拠: /private/tmp/onepiece-research/legacy-knowledge-private.jsonl（顧客原文を含むため公開送信しない）、default-condition-proof.jsonl（本番の純関数5ケース）、deployed-review/tcg_analyzer_svc.py:687-765。Gemini0、製品/DB/シート変更0。提案段階でPO承認・設計審査・実装は未実施。


### 旧ナレッジの定量的な適用範囲（2026-09-11 19:23JST）

精度改善率・有効に働く確率は未算定。過去Knowledgeの存在件数、現データとの名称一致、既に実装済みの処理を分離する。根拠なしに50%等の改善見込みを提示しない。

- 旧7行目Knowledge非空33セル。「状態表記なし」という明示記載は22セル。「単位なし/単位無し」の明示記載は1セル（村上 宝聡）。これは指定文字列を使った棚卸しで、33指示の全意味を形式化した完全評価ではない。
- 2026-09-11T10:23:08.94728Zの本番有効analysis_resultsは1524明細。旧列の仕入元名と現supplier名の完全一致は19仕入元/472明細=31.0%。名称一致はID対応の承認でも精度上昇でもない。別名を推測で結合していない。
- 状態省略明示22セルの名前と一致する現データは207明細。既定Box/Case状態は現行機能のため、これら207件全てが新規に改善するとは言えない。
- 単位省略明示1セルの仕入元名と一致する現データは0明細。SIGにこの別仕入元のルールを流用する根拠なし。
- 今回の67明細: 商品確定59/67=88.1%、単位確定2/67=3.0%、追加配信可能0/67。これは確定率であり正答率ではない。
- 旧ナレッジの追加導入による正答改善は未検証（実証された追加改善件数は現時点0だが、有効性0%という評価ではない）。2投稿の正解単位は原文だけで全件確定できず、比較用の正解表も未完成。

次の実測: 19仕入元472件を名称対応候補としてID/別名を確定→旧指示を適用範囲付きルールへ翻訳→原文と仕入元の確認により正解表作成→現行と候補を同じ凍結入力に適用→商品/単位/状態/NOTEごとに「正しく回復」「新たな誤り」「保留」を比較する。改善率=(候補正解数-現行正解数)/同一評価対象数。原文にない内容を旧ルールで仮定した結果をそのまま正解表にして循環評価しない。高リスクの混在形態/否定/損傷/見出し境界は別対照が必要。

証拠: /private/tmp/onepiece-research/knowledge-all-active.json、knowledge-quantitative-evidence.json、legacy-knowledge-private.jsonl。今回Gemini0・本番更新0。数値は上記スナップショット限定で、将来データ/他仕入元への成功保証ではない。


### SIG66明細の省略ルール試験（2026-09-11、ローカル仮説検証）

PO依頼「SIGでテストしてみて」。再抽出済み66itemsと本番からread-only取得した商品区分/条件マスタを使用し、現行resolve_condition_v2等の実関数をASTでローカル実行。商品ID/数量/価格/NOTEは変更しない。新規Gemini呼出し0、製品コード変更0、本番DB/シート変更0。

試作仮説: SIGの対象書式（商品名 数量@価格）で単位未記載・商品確定・商品区分箱系の明細のうち、カード/プロモ/書籍/デッキ/セット/特殊商品/競合単位/サーチ表記を除いてBoxを補完し、状態を再計算する。既存確定単位や明示単位は上書きしない。これはSIGの実際の販売単位がBoxだと確立したルールではなく、承認前の条件付き試作である。

| 指標 | 現行 | 試作 |
|---|---:|---:|
| 対象商品行 | 66 | 66 |
| 商品確定 | 59 | 59（変更なし） |
| 単位確定 | 1 | 51 |
| 単位未確定 | 65 | 15 |
| FLAG_SINGLE | 66 | 16 |
| 既存配信行条件を満たす候補 | 0 | 50 |

50/66=75.8%は条件付き候補化率であり、正答率/実証済み精度向上率ではない。抽出・原文の商品情報が真にBox販売か、共通状態/発送条件の適用が正しいかはこのテストで確定できない。実DB/Celery/配信全体の結合試験でもない。

保留16: 商品未確定7、特殊形態等7（イーブイex、MEGAスタートデッキ100、フクオカ/トウホク/ヒロシマのスペシャルBOX、Classic、横浜記念デッキ）、既存Set1、シングル区分1。既存Set1の状態FLAG回復は別途検証対象として本試作に含めない。

安全対照は通常省略、明示Case/Pack、SAR/AR/PSA10、セット、備考の雑誌、サーチ可能性、ダメージ、備考ダメージ、シュリンク無しの12件。初回は備考の雑誌を見逃して11/12。試作内の特殊語チェックを商品名だけでなく状態/備考へ広げた後12/12成功。実データ50候補/16保留は前後不変。これは全否定表現・複雑条件の安全保証ではない。

本番適用前に必要な業務確認: 50候補として記録した通常商品の数量@価格を、SIGがBox販売の意味で使用するという確認。価格の高さや商品名だけからその意味を正解と創作しない。確認後に凍結正解表と範囲/否定/共有条件/再解析の結合試験を行う。現時点は試験完了・仮説未承認・設計合格なし・実装未着手。

証拠: /private/tmp/onepiece-research/sig-test-master.json、test-sig-defaults.py、sig-default-test-first-private.json、sig-default-test-private.json、sig-default-test-final.log。原文・対象詳細は非公開のまま保持。


### 過去SIG投稿への固定試作検証と統計限界（2026-09-11）

PO依頼: 過去SIGメッセージで誤解析リスクを統計化。Gemini0、本番DB/シート/製品コード変更0。前節の試作ルールを固定し、過去データをローカル評価した。

#### 母集団と重複

Downloads直下のLINE WeGo/WEGO .txt 16ファイルを調査。送信者名がSIGの出現153件を日時+本文のNFKC/空行除去正規化で重複除去し、33投稿（2026-08-02 12:47〜2026-09-11 12:28）。今回の9/11投稿は開発用データとして除外し、過去32投稿を評価。うち商品案内29、配送連絡/取消/招待通知3。価格数量構文のある商品行1044。

DB単独ではSIG8source records/489itemsがあるが、9/7同文5記録、9/10案内1・通知1、9/11案内1であり独立な8投稿ではない。履歴ファイルに本文SIG署名・送信者りょうの42出現もあったが、別名対応が未確定のため今回に合算しない。

境界解析は既存parse_line_exportの日時/送信者処理を使用。長文に対するsystem-event末尾照合が遅いため読み取り実験だけその分類呼出しを無効化し、通知3件は本文で別分類。実装変更ではない。商品行の抽出は数量[単位]@価格の明示構文に限定した決定的なローカル処理。@を含む未処理行0（全ての可能な販売構文の完全抽出証明ではない）。既存抽出結果がない履歴をGemini再抽出していない。

#### 固定ルールの結果

| 指標 | 件数 |
|---|---:|
| 過去の検証商品行 | 1044 |
| Box補完候補 | 729（69.83%） |
| 特殊形態・競合語で保留 | 160 |
| 商品未確定で保留 | 142 |
| 商品区分が箱系以外 | 9 |
| 明示単位を維持 | 4（Box1/Case3） |

729は候補化数であって正答数ではない。候補は66商品ID・473種類の名称/数量/価格/状態組合せからなり、729独立試行でもない。商品候補は現行商品検索/除外の実関数と今回取得した現マスタによる照合。過去当時マスタではなく現在マスタの再生であり、過去時点の性能を主張しない。作品見出し推定/正規化全件/配信全体の統合試験ではない。

#### 原文で答え合わせできた範囲

数量に単位が付く4行は2CT@278000、100box@16500、10CT@245000、OP-17世界最強の戦士5CT@245000。試作は4/4を上書きせず、CT→Box誤変換0。

補完候補の1行は8/2「【シュリンク無しBOX】ストームエメラルダ 100@17000」で、Box/No shrink boxとなり明示原文と一致。この行は真の単位省略ではなく、商品名側に明示単位があるケース。残り候補728行は正解単位の直接根拠が未確立。「誤判定0/729」「誤判定率0%」「95%保証」は禁止。明示確認できた5ケースの不一致0という限定事実に留まる。

新しい範囲確認対象はMEGAプレミアムトレーナーBOX6行/プレシャスコレクターボックス5行の計11行。現試作の特殊語フィルタでは通るが、通常商品のルール適用範囲として未検証。11/729=1.51%は対象範囲確認率であり誤解析率ではない。この履歴検証では11行を都合よく後から候補から削って成功率を再計算せず、固定試作の結果として残す。

結論: 試作の候補化率は69.83%、将来の誤解析確率は算出不能。確認済み成功5件のうち4件は明示値の保持、1件も商品名側の明示値であり、真の単位省略補完の正解ラベルは0件。省略された単位の正解をSIGの運用確認/注文実績等で確立することが先。通常品・特殊BOX・Case/Pack・否定/損傷・共有条件を分け、投稿単位の時系列holdoutで誤補完率/保留率を比較する。既存価格から単位を逆算して正解ラベルとする循環評価はしない。

証拠（非公開）: /private/tmp/onepiece-research/sig-history-db.json、sig-history-exports-private.json、scan-sig-history.py、sig-history-match-master.json、test-sig-history.py、sig-history-test-private.json、sig-history-statistics.json。読み取り中のテーブル名誤り1件は正しいproduct_search_keywords/product_exclude_keywordsへ修正、DB変更なし。長時間のローカル走査/照合は中断後、同一入力の結果をキャッシュするなど計算だけを軽量化して再実行した。


### 再起動用引き継ぎ（2026-09-11、SIG省略単位調査）

- 再開場所: `/Users/tanizawashingo/worktrees/salesanchor/release-line-interruption-investigation`、branch `release/line-interruption-investigation`、今回確認HEAD `adc8bc4d67a94e8ede45a1e9c0ee9f28d28bb70b`。recon.md / tasks/todo.md / evidence-registry.md の3文書はローカル未コミット。今回の調査PR/製品実装/配備はなし。本店mainには他者の未保存27件があり触らない。再開時にpreflightと現行差分・台帳を再確認する。
- 完了: 過去SIG29商品案内1044行の固定試作検証。729候補（69.83%）は精度ではない。候補1行のみ商品名にBOX明示、728行は単位正解未確認。明示単位4行は保持。特殊BOX11行は要確認で、誤判定確定ではない。将来誤判定率は未算定。
- 直近説明した案（未承認/未実装）: 明細の単位→適用範囲を確認した商品名・見出し→確認済みSIG限定省略規則の順。マスタの箱系区分だけで販売単位Boxを確定しない。特殊商品・矛盾は保留。状態は明示損傷/開封/シュリンク無しを優先し、確定単位と仕入元実態に合う場合のみ既存既定値を使う。補完の根拠行/ルールを記録する。
- 次の一手: SIGの省略単位を確認できる既存のナレッジ/注文実績を読み取り照合し、確認不能ならPOへ1問で確認する。SIGと旧Knowledge列/別名の同一性を創作しない。正解表を試作結果から作らず、独立した原文・運用確認で作る。その後、同一データで正しく回復/新たな誤り/保留を比較し、設計→自己審査→PO承認へ進む。現時点で設計合格なし。
- 制限: 本調査でGemini0、製品/本番DB/シート変更0。2件限定再抽出の過去許可を新たなAPI呼出しの許可に広げない。顧客原文・実データ・秘密は外部送信しない。
- 再起動に備え、選択した原文/マスタ/結果/試作/依存コードを `/Users/tanizawashingo/.local/share/salesanchor/private-research/sig-20260911` に非公開ローカル保存（directory700/files600）。SHA256-MANIFEST.jsonで内容照合。従来の /private/tmp は消える可能性があるため永続コピーを優先する。試作スクリプトには旧一時パス/作業台パスの固定参照があるため、そのまま自動実行せず参照先を確認する。保存した結果は再計算なしで閲覧可能。
- 今回は研究結果と草案の保存であり、新しいPO設計合意/GOを記録していない。共通ルールへの新規教訓追記なし。


### SIG解析精度を上げる対策の優先順位（2026-09-11、再開調査・未承認案）

依頼原文: 「進める、解析精度を上げられる方法が知りたい」。本便は設計担当の読み取り・提案・文書化。GO委任未有効、実装・本番変更・Gemini呼出しなし。先の回答はLINE全体の記録を参照していたが、再開対象のSIG固有の未コミット引き継ぎを確認し訂正した。

#### 今回直接確認した根拠

- 基準コード: adc8bc4d67a94e8ede45a1e9c0ee9f28d28bb70b。既存release/line-interruption-investigationの未保存3文書を保持し、同テーマの継続調査として追記する。
- 非公開永続保存sig-20260911のSHA256-MANIFEST.jsonにある21資料をPython hashlibで照合、21一致・不一致0。旧一時ディレクトリの欠落は永続資料の欠落を意味しない。
- sig-history-test-private.jsonを集計し直し1044行、729候補、特殊形態等160、商品未確定142、箱系以外9、明示単位保持4を再確認。照合試作自体の再実行ではない。
- 商品未確定142行は名称文字列21種類、特殊形態等160行は27種類。これは同一商品の数でも未登録商品数でもない。同一表記を束ねて根拠確認する作業単位には使える。
- 729候補の試作状態はSealed box728、No shrink box1。候補のunit_ground_truth列は729件すべて空で、前節の明示BOX1件は原文別照合の証拠。728件について単位・状態の正解を実証していない。
- 旧Knowledge保存本文のSIG完全一致文字列は0。既存の別仕入元の省略規則をSIGへ適用できる根拠は取得できていない。注文実績との突合は未実施。
- 過去29商品案内すべてにシール/伝票跡を含む可能性の共通注意書きを確認。個々の商品に傷や跡が存在する断定ではない。顧客原文は本文へ複製しない。
- 基準コードbackend/app/services/tcg_analyzer_svc.py:708は状態+商品名を通常状態入力とする。:750以降の備考利用はパック未サーチの限定経路。:1167以降に単位解決、:1184以降に商品照合、:1199以降に状態判定。単位省略と損傷の備考欠落は別に検証する必要がある。

#### 推奨する順序と効果の限界

| 順序 | 対策案 | 根拠・狙い | 検証と停止条件 |
|---|---|---|---|
| 1 | SIGの通常拡張パック・対象書式に限る省略単位の業務確認 | 過去729候補のうち728に正解根拠がないことが主な障害。確認済み取引・POの運用知識を正解根拠とする | 例外・適用期間・仕入元同一性を確認。商品分類や価格からBoxという正解を逆算しない |
| 2 | 明細の明示単位→適用範囲が確かな商品名/見出し→確認済みSIG限定規則の順で補完 | 現在の66行では50回復候補。過去1044行では729候補だが正解数ではない | 明示Case/Pack/Set等を保持。特殊BOX11行と商品群の境界を確認するまで適用保留。元raw_unitを上書きしない |
| 3 | 確定した単位で状態を再判定し、明示損傷・開封等を優先 | 単位不明に由来するFLAGを解消できる可能性。Sealed boxは既定判定であり検品済みの保証ではない | 否定、可能性、発送免責、別商品への注記、見出し境界を独立した対照で確認。備考全文の無条件連結は採らない |
| 4 | 商品未確定21表記と特殊形態27表記を束ねて照合 | 表記ゆれ/作品根拠不足/未登録/形態違いを分類し、件数の多い原因から対処できる | 正式商品・版・セット内容を確認して検索語と除外語を対で検証。142行を一括新規登録しない |
| 5 | 同じ固定入力で現行と候補を比較し、未使用の後続投稿で再検証 | 自動確定を増やすだけの改悪を検出する | 商品・単位・状態・注記ごとに正解/誤り/保留を集計。既知正常例の新規誤り0、明示値の上書き0を受入案とする |

29過去投稿と9/11の66行は既に試作の評価・調整で閲覧済みなので、新たな独立評価用データとは呼ばない。次の未使用投稿を確保してから、規則を固定し正解表と比較する。重複行を独立試行と数えず、投稿数・商品群数も併記する。精度の分母は正解が確立した対象、保留率の分母は評価対象全件とし、正解未確認件数も別記する。改善量は同じ正解表での正解数の差で示す。

#### Planner整理とArchitect自己審査

調査結果と優先順位案を作成済み。正式実装設計はREVISE（同一AIの自己審査、独立レビューではない）。SIG省略単位の業務上の正解、特殊商品の適用範囲、状態既定値の適否、実パイプラインの試験が未確立だからである。設計合格・PO承認・カード発行を行わない。

外部成功事例は不要: 今回の可否はSIG原文と販売実態・現行実関数に依存し、外部の精度数値で立証できない。ライブラリ/API仕様の変更提案はなく、モデル変更の費用対効果も未測定。現段階ではモデル変更を優先策とする根拠はない。

POへ提示した1問: SIGの通常拡張パック商品で数量@価格のみの場合、数量は原則Box数という運用か（特殊BOX/セット/書籍/プロモ/明示単位は別）。回答未受領として記録し、原文を創作しない。次の一手はこの業務確認を根拠として対象を固定し、正解表と比較試験の設計を具体化すること。担当は設計パートナー、実装は正式な設計審査・PO実装承認後に別担当へ渡す。


### SIG単位・価格・状態の比較試験（2026-09-11、今回直接実行）

PO依頼: 「テストをして懐石率が上がる方法をエビデンス付きで報告してくれ」。追加案: 「価格でcaseとboxを判別する」「シュリンク無しやダメージ品は状態表記が必ずあるはず」。いずれも検証する仮説として受け取り、業務上の事実・承認済み規則には変更しない。

#### 試験条件・再現性

- 非公開保存21資料のSHA256を再照合、不一致0。過去SIG29商品案内1044行を使用。9/11の66明細は別集計。
- 基準コードadc8bc4d67a94e8ede45a1e9c0ee9f28d28bb70bのunit_recovery_norm/build_unit_recovery_terms/find_term/find_terminal_unitをASTで読み込み、ネットワーク・DB依存を起動せず実行。状態判定は保存した実関数/実条件マスタを利用。以前の省略試作を1044行へ再適用し、候補/保留理由の再現不一致0、729候補を再現した。商品IDの正解を再検証した試験ではない。
- 歴史データは数量[単位]@価格の固定パーサ結果。Gemini抽出、正規化全件、実DBのE3/E5/E3b/E4、配信全体の試験ではない。実本番の回復件数・全体正答率を以下の局所値から断定しない。
- 初回は集計式がNoneを加算して失敗し、真偽値化だけを修正。次に矛盾単位の対照1件が失敗したため、候補側に数量+異なる単位の検出を追加。最初の失敗結果をfirst-summary.jsonに保持。期待値は変更せず、修正後に同じ全量と全対照を再実行した。

#### A: 明示単位を商品名先頭から回収する案

原文の同一行を照合し、数量欄のCT/box4行、先頭【カートン】44行、先頭【シュリンク無しBOX】1行、計49行を明示単位の答え合わせ対象にした。Box2/Case47。価格・商品カテゴリ・試作の出力から正解を作っていない。ただし、これらは閲覧済みの開発用原文で、未知投稿の独立試験ではない。

| 指標 | 末尾単位関数を用いた局所比較 | 先頭の明示タグも参照する案 |
|---|---:|---:|
| 原文明示49行で単位一致 | 4/49 | 49/49 |
| 正しく回収した単位の増分 | — | 45行（Case44/Box1） |
| 明示単位との不一致 | 0（未回収45） | 0 |
| 増分45行のうち既存商品照合が確定済み | — | 41行。残4は商品未確定 |

ベースライン4は「数量の明示保持＋実末尾単位関数＋既存商品制約」に限定した値。49/49を本番解析全体の100%と報告しない。状態関数まで追加照合すると44行はFLAG_SINGLE、1行はNo shrink boxで、そのマスタのapp_kubunは空。E4は実unitテーブルの衝突状況にも依存するため、DB再生なしに完全な本番ベースラインとはしない。Geminiが原文のタグをraw_unitへ既に抽出する場合は、本番の追加改善が小さくなる可能性がある。

案は商品行先頭の限定タグだけを採用。一般の商品名中のBOX、書籍、プロモ、否定タグ、共通注意書きは単位根拠にしない。数量付きの別単位と競合した場合は保留。架空対照11件は初回10成功/1失敗、修正後11/11成功。NGの例はカートン先頭タグと末尾2BOXの矛盾だった。これは実データの誤判定率ではない。

判断: 具体的な改善候補として最優先。実装案を作る前に、原文→抽出→解析を通す固定テストで45行のどこが既存機能で回復済みかを計測し、差分だけを対策対象にする。

#### B: 価格によるBox/Case判別

同一商品OP-17の明記例はBox16500、Case245000（同日）とCase278000。Case/Box比は同日14.85倍。商品をまたぐ単一価格閾値では判定しない。

固定した研究条件: 同じ商品ID、評価投稿より厳密に前の14日以内、Box/Case双方の明示価格あり、両中央値の比4以上、入力価格が片方の中央値から30%以内の場合だけ分類。同時刻投稿・未来の価格は参照しない。価格閾値は未承認の仮説で、正解ラベルとして再利用しない。

- 原文明示49行のうち過去価格が揃って判別できたのは2行。8/27 Case245000、8/31 Case240000の2/2一致、誤り0、他47は保留。
- 両方とも同一商品のCaseで、Boxの後日正解検証0。全てCaseとするだけでも同じ2/2になるため、価格方式の優位性や一般精度はまだ立証できない。49行全体でもCase47/49という偏りがある。
- 単位未明示の4行をBox候補にできたが、独立した単位正解なし。正しく4件改善したとは数えない。

判断: 補助候補・矛盾検出として調査継続。本番での自動確定は設計合格にしない。商品/版/状態/入数/時期が揃う確認済み取引価格を追加し、Box/Case双方の未使用投稿で比較する必要がある。

#### C: 状態表記が必ずあるという仮説

過去1044商品行の原文側でシュリンク無し1行、未開封30行、サーチ済みの可能性15行を確認。損傷候補語（ダメージ/凹み/破れ/箱潰/傷あり）は商品行で0。これは限定語の探索で、全表現を網羅した正解表ではない。29投稿すべての共通注意書きにはシール/伝票跡を含む可能性があり、個々の商品が損傷品という証拠ではない。

9/11のSIG66明細では未開封1行がraw_state、サーチ済みの可能性1行がraw_memoに保存されていることを確認。両方の解析conditionはFLAG_SINGLE。この未開封はプロモであり、通常BOXへ変更する根拠ではない。2例の保持を全状態の抽出漏れ0とはしない。

以前のBox省略＋備考を状態へ連結する仮説に対する追加対照13件は6成功/7不合格。ダメージなし・ダメージはありませんをDamaged sealed boxとする2件の反例を再現。損傷の可能性、配送免責、別商品の損傷、開封可能性、特殊BOXの適用にも不合格が出た。反例は架空入力でありSIGに同じ誤りが何件あるかの測定ではない。対照の特殊BOXは通常商品のfixtureへ名称だけ変更した適用範囲テストで、別の実商品登録試験ではない。

判断: 明示された状態を拾う方針は有用だが、「書かれていなければ通常品」「備考に語があれば損傷」の無条件ルールは未立証/不採用。否定・可能性・別商品・発送免責を分けてから、確定単位と既存の条件付き既定値を接続する。実際の損傷品なのに記載がない頻度は、原文だけでは観測できず、受入検品/注文実績との照合が必要。

#### 結論と審査状態

推奨順はAの明示単位回収→Cの否定/適用範囲の保護→Bの価格による補助照合。価格・省略規則だけで候補を増やして正解とみなす案は採らない。全工程の率を測るときは商品/単位/状態/注記の正解・誤り・保留を同じ対象で数え、各項目の分母と全属性一致件数を併記する。

Plannerの比較試験と案整理は完了。Architect自己審査はREVISE（同一AI、独立レビューなし）。Aは局所改善の証拠ありだが本番全工程未検証、Bは2件/1商品/Caseのみ、Cは反例あり。正式カード・実装・本番反映・再解析・配信は未着手。POの今回の発話をSIG省略ルールの承認やGOとして記録していない。

永続証跡（非公開）: /Users/tanizawashingo/.local/share/salesanchor/private-research/sig-20260911/accuracy-followup/ の evaluate.py、summary.json、result-private.json、first-summary.json、基準コード2ファイル、run.log、SHA256-MANIFEST.json。原文・価格等の顧客資料を外部へ送っていない。今回Gemini0、本番読書き0、製品コード変更0。外部事例の数値は自社SIGの正解を証明しないため使用しない。


### 5つの未解決点の追加試験（2026-09-12、今回直接実行）

PO依頼原文: 「離席するのでそれぞれを試してテスト結果を教えてくれ」。5領域をオフライン比較。設計担当の範囲を維持し、製品/本番/CI/secrets変更0、Gemini呼出し0、サブエージェント0。本番の現在値を再照会した試験ではない。

#### 今回の基準と前回説明の補正

preflight成功。git ls-remote origin refs/heads/mainはadc8bc4d67a94e8ede45a1e9c0ee9f28d28bb70b。既存の調査worktreeも同HEAD、文書3件の未コミット差分を保持。過去1044商品行/29案内と、保存済み実抽出489明細を別の母集団として使用。後者は同文5投稿を重複除去すると3商品案内205明細と1通知0明細。そのうち保存時点activeな最新投稿は66明細。現在の本番active件数とは呼ばない。

**前回の「明示単位＋45行」は、原文から作った簡易入力を使う局所比較である。今回、実際の保存済み抽出/解析結果を調べると、比較可能なカートン明示11行はすべて既存処理でraw_unit=カートン、unit=Case、unit_resolved=trueとなっていた。11行の追加改善は0。前回の45を本番改善見込みとして使わず、タグ回収を最優先とした前節の優先順位を更新する。** 残りの原文明示行はこの保存抽出標本に含まれず、全45行について本番改善0と断定することもしない。

#### 1. 省略単位・価格判別

前回の価格判別規則について、参照期間7/14/30日×中央値からの許容差10/20/30%の9組を固定比較。同じ商品、評価時刻より厳密に過去、Box/Case双方の明示価格、中央値比4以上という条件は維持。

- 全9組とも原文明示49行のうち分類可能2件、Case2/2一致、誤り0、47保留。9組×2件を18独立成功と数えない。同一OP-17・同一2投稿の繰返し評価である。
- 正解未確認のBox候補は期間7日で3行、14日で4行、30日で5行。許容差を広げても正解を確認できる件数は増えなかった。
- 同じCase2件なら常にCaseとする方式も2/2となるため、価格方式が優れる証拠にはならない。Boxの未知投稿正解と、他商品の双方単位の取引実績が必要。省略単位の自動確定は未採用。

#### 2. 商品未確定: 検索語修正と適用範囲の比較

固定した現行商品照合関数・検索/除外マスタを1044行に再適用し、前回の商品候補/確定フラグとの不一致0。誤記/表記不足に対する5群の仮の検索語追加をローカルで比較した。

| 修正候補の商品 | 過去の追加確定行 | 事実確認と限界 |
|---|---:|---|
| 25th ANNIVERSARY GOLDEN BOX | 9 | マスタにはAniniversary、検索語にはGoleenという綴りがある。正式綴りは公式資料で確認 |
| 受け継がれる意志 OP-13 | 2 | マスタの意思と公式の意志が異なる。型番も一致 |
| メガエルレイドのスペシャルカードセット | 9 | 公式の製品名は確認。SIG略称との対応・形態の正解は暫定候補 |
| ニャオハ＆マスカーニャのスターターセット | 3 | 公式の製品名は確認。SIGの短い表記だけで商品の単品カード/セットを常に区別できる証明ではない |
| ONE PIECE CARD THE BEST vol.2 / PRB-02 | 2 | 型番と正式名を公式資料で確認。表記THE BEST2を局所照合 |

追加確定計25、既存確定商品が別商品に変わった行0。既存商品未確定142→117。ただし商品名の対応根拠に強弱があるため、25を正答改善25と認定しない。現行の確定件数自体が正解ラベルではない。

安全対照は各5群×6ケース=30（正例5、PSA/単品カード/空箱/英語版/カードのみの否定側25）。単純に検索語を足す案は10/30成功。新しい照合を確認済みの完全表記・条件欄が空の行だけに限定し、既存確定は維持する試作では30/30成功。過去の追加確定25は維持。これは限定した30対照への合格であり、全表現への誤判定0保証ではない。既存誤確定の修正はこの試作の対象外。

保存された実抽出205明細では、この5群による追加確定0。保存時点activeの最新66明細でも0。過去原文の簡易入力での25件を、最新投稿へ適用すれば25件増えると報告しない。

参照した一次資料（閲覧2026-09-12、顧客原文や価格は検索に含めない）:
- [ポケモン公式: GOLDEN BOX](https://www.pokemon-card.com/info/003290.html)
- [バンダイ公式: OP-13](https://www.bandai.co.jp/catalog/item.php?jan_cd=4582769864865000)
- [ポケモン公式: MEGAスターターセットex](https://www.pokemon-card.com/ex/me/)
- [ポケモンセンター公式: メガエルレイドex](https://www.pokemoncenter-online.com/4521329462011.html)
- [ONE PIECE公式: PRB-02](https://one-piece.com/news/73794/index.html)

公式資料は商品名/型番/形態の確認に使い、SIGの販売単位や納品状態の証明には使わない。外部導入成功率を内部精度へ転用していない。

#### 3. 特殊商品の範囲を分ける試験

以前の「特殊形態・競合語160行」を分解すると、本来の特殊形態等120行と、明示カートン40行だった。160行全部を特殊商品と呼んだ以前の説明を訂正する。明示単位を先に拾い、その後に商品形態を確認する順序が必要。

また、以前のBox補完729候補には、通常扱いの省略717、商品名にBox明示1、MEGAプレミアムトレーナーBOX/プレシャスコレクターボックス11が含まれた。特殊商品の語を追加した保守的な試作で、この11行を自動Box補完から保留へ戻す。これは誤補完を防ぐための範囲縮小であり、11件の誤りを実証した結果や解析率の上昇ではない。

特殊商品/通常商品の架空対照7件は7/7成功。新しい商品形態の単位や商品マスタを追加登録していない。セット/書籍/プロモの販売単位は仕入先取引根拠の確認を残す。

#### 4. 状態の否定・可能性・範囲の試験

単位を明示Box/Caseとして固定し、12ケースずつ計24対照。未記載、損傷明示、備考の損傷、否定2種、開封、シュリンク無し、可能性、配送免責、他商品、肯否競合、開封予定を分けた。

- 以前の「状態+備考を連結して現行状態関数へ渡す」案は期待どおり7/24。これは以前の試作の判定で、本番全体に17誤りがあるという結果ではない。
- 限定表現の意味を分ける新試作は24/24。内訳は13件を判定、11件を保留。保留を正しく選んだケースを解析確定の成功件数へ混ぜない。
- 新試作は単位未確定なら状態も保留。単位の根拠を状態既定値から逆算する循環を防ぐ。状態の既定値は検品済みの保証にはしない。
- 24ケースは事前に期待値を固定した架空対照。実際の損傷/開封の無記載率は未測定で、「状態が必ず書かれる」という仮説は未確立。保存済みSIG原文の真の状態は注文/検品記録と照合する必要がある。

#### 5. 原文→抽出→解析のつながり

- 保存済み489明細の重複を除いた205明細すべてで、元原文の該当範囲にある数量@価格と保存抽出値が一致（205/205、数値不一致0）。原文側の商品の網羅性や、記載された数量/価格が業務上正しいかは別問題。
- 保存抽出値から9列応答を組み立て直して、現行parse_extraction_responseへ通した205件は205/205でフィールド/行番号一致。これは応答形式の再生であり、実Gemini応答の再生成・精度試験ではない。
- 原文のカートンタグと保存抽出/保存解析を行番号で結んだ11行は11/11が既にCase確定。前回の局所比較を本番改善と取り違えないための証拠。
- 実DB結合試験を実行する前提を確認したが、docker info/docker psは /var/run/docker.sock 不在で失敗。Dockerなし環境でpytestを走らせず、SQLiteへの置換や共有DBへの接続で代用しない。実DB・Celery・実Gemini・配信SQL実行・シートへの全工程試験は未実施。既存のtest_tcg_completion_safety.py/test_tcg_work_matching_integration.pyは読むだけで、今回合格とは宣言しない。

#### 判定・次の一手・維持

調査5項目の比較結果作成済み。正式実装設計は同一AIの自己審査REVISE。商品照合の限定改善と状態の保留判定は具体的な候補だが、最新66明細の正答改善は未実証。明示タグ改修を先に実装する方針はいったん採らず、保存結果で既存回収済みかを先に確認する。

次の一手: ①最新66明細について注文/納品・SIGの省略単位の独立した正解を整備、②25商品候補の略称と版/形態の対応を確定、③Dockerが使用可能な隔離環境で既存の実DB試験方式に従って再解析・配信行取得まで照合。数値のために保留を強制確定しない。POが離席中のため未解決の業務判断を代筆せず、実装開始/マージ/本番の追加承認は作成していない。

継続担当は設計パートナー。新たな試験結果はこの節へ追記し、固定コード/入力/期待値/結果を保持する。守り手候補は上記既存の結合試験と新たな否定/版違い対照で、試作の限定表現リストをそのまま本番ルールとみなさない。

非公開永続証跡: /Users/tanizawashingo/.local/share/salesanchor/private-research/sig-20260911/five-tests-20260912/。product-probe.py、full-probes.py、chain-audit.py、gemini_extraction_baseline.py、比較結果JSON、run.log、SHA256-MANIFEST.json。入力は元の21資料と前回accuracy-followup結果を参照。スクリプトは再実行時に同じディレクトリへ結果を書くため、原本を保全して複製先で実行する。全て本番接続・Gemini呼出しを含まない研究用スクリプト。


### Gemini 1回比較の準備・認証停止（2026-09-12）

PO原文: 「geminiは1回だけ仕様を許可するので調査してくれ」。本セッションは使用許可1回と解釈し、生成HTTPリクエスト最大1回、失敗・タイムアウト時も再送0とした。API呼出しは現時点0。代理GO有効化・製品実装の許可とは扱わない。

- 観測: ローカルGEMINI_API_KEY未設定、main/backendの.envなし。worktreeの.env候補にも設定なし。通常の制限付き鍵によるSSH読取接続はPermission denied (publickey)。人間専用鍵や認証情報の変更は行っていない。
- 用意した試験: 人工66ケース（商品30、状態24、単位12）。商品3明瞭表記の正例、人物名だけの曖昧2例、各候補のPSA/単品/空箱/英語版/カードのみを区別。状態未記載の既定値は人工試験内の明示規則であり、SIGの取引慣行として認定しない。価格判別も明示の仮定付き3例を分離し、実取引の正解に数えない。
- 送信入力と正解を分離し、送信前hash固定。入力SHA256=4ead17406501e397ff78fa26aa9a28040742cbb3110a18b1686ebc5efd47535c、正解SHA256=9c7e267b7f24cc4d9c749e275fbd11be854801492be3be2f10c5e1ae746a28fc。今回の商品30例は前回の曖昧な短縮名を含む30例とは異なり、前回30/30を今回の比較値に転記しない。
- 研究用の1回実行スクリプトを隔離保存。現行指定モデルgemini-3.6-flash、temperature=0、JSON形式指定。開始記録を排他的に作成し、再実行/自動再送/HTTPリダイレクトなし。認証未設定なら送信前に停止。製品サービスは呼ばず、DB/シート書込みなし。
- 採点器のローカル確認4/4: 全正解、欠落ID、重複ID、誤確定。これはGemini性能試験ではない。Geminiの実応答・正答率・優劣は未確認。
- Context7 MCPは利用不可。代替としてGoogle公式generateContent APIとStructured outputsを2026-09-12に直接確認。JSON形式への準拠だけで意味の正しさを保証しないため、固定正解で別採点する。
- 保存: `$HOME/.local/share/salesanchor/private-research/sig-20260911/gemini-one-shot-20260912/`（入力、正解、準備/実行スクリプト、readiness、SHA256-MANIFEST）。顧客原文や秘密値は送信入力に含めない。
- 自己審査: **REVISE / 認証待ち**。1回の人工試験で本番全件精度を認定しない。実行結果取得後に候補方式と比較し、実データ正解付き評価を別途設計する。次の一手は既存の承認済みGemini認証を研究プロセスから利用可能にすること。許可1回は未消費、再許可は求めない。設計合格なし、実装/マージ/本番反映/再解析/3シート配信なし。

公式資料: https://ai.google.dev/api/generate-content / https://ai.google.dev/gemini-api/docs/structured-output


### Gemini 1回比較の実結果（2026-09-12、前節の認証待ちを解消）

POの追加発言「1度だけ許可する」を、直前に説明した既存認証の今回1回利用への許可として受領。既存SSH接続先とbackendコンテナの環境変数を利用し、鍵の表示/ローカル持出し/変更なし。コンテナ内の隔離Pythonプロセスで直接RESTを1リクエストだけ実行。製品ファイル、DB、CI、シートは無変更。サブエージェント0。GO委任の有効化・実装開始ではない。

#### 実測結果と試験仕様の欠陥

事前固定の同一66ケースを1回で送信。modelVersion=gemini-3.6-flash、temperature=0、応答36.344秒。usage: prompt4047、出力1428、thinking6606、total12081 tokens。HTTP生成リクエスト1、再送0。許可枠1回は消費済み。

| 項目 | 事前固定の文字列完全一致 | 事後の意味対応を確認した結果 |
|---|---:|---:|
| 商品 | 30/30 | 30/30 |
| 状態 | 11/24 | 24/24 |
| 単位 | 6/12 | 12/12 |
| 合計 | 47/66（71.2%） | 66/66（探索的な自己確認） |

**試験設計側の欠陥**: プロンプト/JSON schemaでstate/unitの正式な出力値を列挙していなかった。実応答はcase/box、normal/damaged/opened/unshrunkenを使い、正解ファイルはCase/Box、Sealed box等を要求していた。19不一致はこの表記契約の不足。生の47/66を保存し、意味確認による66/66へ上書きしていない。意味確認は回答後に作った対応表と根拠文の同一AI確認であり、事前規定の独立試験合格と呼ばない。将来の試験仕様では許容値をenumで固定し、正式状態への変換と保留理由を別項目にする。今回追加API呼出しはしない。

#### 同じ入力による現行比較と意味

保存済みの現行商品照合関数とマスタを、今回の商品30ケースに読み取り適用して27/30一致。Geminiは同じ30ケースで30/30一致（90→100%、+3/30）。差分はGOLDEN BOX、OP-13受け継がれる意志、PRB-02 THE BEST2の3明瞭表記。これは照合ルール/旧マスタ対、正規化した候補一覧を与えたGeminiの比較であり、モデル単体の優位性の分離実験ではない。マスタ修正との公平比較や実際の未解決行の正解確認が必要。

意味確認の内訳は22判定・44保留。今回の人工ケースでは「ダメージなし」を損傷扱いせず、曖昧な商品名や単位のない価格を保留できた。通常の10000円/120000円だけでは単位を確定せず、人工的な確認済み取引規則を添えたときだけBox/Caseを選択。SIG実取引で価格から単位を判別できる正答率の証明ではない。状態未記載の既定値も人工試験の明示条件であり、SIGで『記載なし=正常』を保証しない。

過去のシステム側の状態限定ルール試作も24/24（合成対照）だった。今回の結果だけでGeminiがその方式より優れるとは判定しない。最新保存66明細の解析率改善、本番全件正答率、再現性、費用対効果は未測定。1回・人工66ケースで『すべて解析可能』とは結論しない。

#### Planner提案 / Architect自己審査

提案は、正式名/誤字のマスタ是正を先行候補とし、曖昧な表現を候補一覧と対象範囲付きでGeminiに照合させ、システムで商品コード・状態・単位と矛盾を検証する併用方式。価格のみの自動確定は採用せず、独立した取引正解の取得を優先する。

自己審査 **REVISE**: 商品の3対照改善は直接確認したが、出力値契約の欠陥、正規化候補を与えた比較条件の差、実データの独立正解不足、1回で再現性未確認が残る。実装カード発行条件は未充足。設計研究と文書保存済み、POの1回API利用許可のみ消費済み、設計合格/実装承認/PR提出/実装/マージ/本番反映/再解析/3シート配信なし。

証跡は前節の非公開保存先: ATTEMPT-STARTED.json、request.json、cases-with-gold.json、response.json、transport-result.json、result.json（事前採点）、semantic-review.json（事後意味確認）、current-product-baseline.json、各実行スクリプト、SHA256-MANIFEST.json。開始記録の排他作成により同じ許可で再送不可。採点器自己確認4/4、git diff --checkと台帳チェックの結果も分離して扱う。


### SIG 商品マスタ箱系によるBox補完の隔離試験（2026-09-12）

PO依頼「今の条件でシステムに解析させてみて」。製品変更ではなく、保存済み抽出/解析205明細（原文重複除去）へ隔離スクリプトを適用。保存時点の最新active投稿66明細を別集計。現本番への再照会/再解析ではない。

試験条件: SIG、既存の商品特定成功、商品マスタcategory=箱系、raw_unit空、既存確定単位なし、単位タグ・数量単位や単品競合記載なし→Box補完。セット/デッキ/アタッシュケースという商品名だけでは除外しない。既存確定Set等も保持。商品ID・価格・数量は固定し、商品検索語は変えていない。

| 標本 | 商品特定 | 単位確定の前→後 | Box追加 | 商品未確定 |
|---|---:|---:|---:|---:|
| 最新保存66 | 59/66 | 1→58（1.5→87.9%） | 57 | 7 |
| 重複除去205 | 184/205 | 15→181（7.3→88.3%） | 166 | 21 |

最新の単位保留8=商品未確定7+商品特定済みシングル系1（プレミアムカードコレクション ONE PIECE DAY’25）。別の1件は既存Set確定を保持。商品未確定7件: 25thアニバーサリー、最強ジャンプ 頂上の強者 プロモ、ナツコミ2026 メタキラカード ルフィ、肉ルフィP-159プロモ、ONE PIECE × ROUND1 プロモパック、ONE PIECE CHOPPER’s、プレミアムカードコレクション ONE PIECE DAY’24。原文の商品名抽出とマスタID特定は別工程。

状態は2通りに分離: (A)単位のみを変更し状態結果を保持→最新の状態FLAG_SINGLEは66のまま、配信候補条件を満たす件数0のまま。(B)Boxを渡して保存済み実状態関数resolve_condition_v2も再評価→57件がSealed box、9件FLAG_SINGLE。既存条件上の候補数0→57（86.4%）。これは機械的な状態既定値適用の結果で、状態の正解を独立に検証した57件ではない。

特にMEGA スタートデッキ100には備考「サーチ済みの可能性有」があり、既存Box状態処理では備考が評価対象にならずSealed boxへ既定化した。単位Boxの判定と、サーチ/開封/シュリンク状態は別であり、この備考をどう扱うかを設計で解決する必要がある。重複除去205件では同備考を含む補完3件がある。既存状態再評価後の候補12→178も、そのまま正答数/安全な配信件数とは呼ばない。

対照12/12成功（通常・セット・アタッシュケース名、シングル系、商品未確定、明示Case/Pack、カートンタグ、単品、PSA、傷、シュリンク無し）。全行で商品ID/価格/単位のみ適用時の状態保持、および既存確定単位の非変更を検証。Gemini追加0、製品/DB/シート変更0、Dockerを用いた統合試験なし。証跡: private-research/sig-20260911/master-box-trial-20260912/ のevaluate.py、results-private.json、summary.json、SHA256-MANIFEST.json。

自己審査REVISE: 単位補完による処理上の改善は実測済み。状態備考の扱いと商品未確定の解消は残る。実装カード発行/実装/マージ/本番反映/配信は未着手。


### Box補完試験の原文照合・備考保持確認（2026-09-12）

PO依頼「サーチ済みの可能性ありの商品は何？今の検査結果が適切化原文も確認してミスがないか見てくれ」。保存済み最新66明細を原文行範囲と照合。

- 該当商品: MEGA スタートデッキ100 バトルコレクション。原文L109は「MEGA スタートデッキ100 バトルコレクション※買取品のためサーチ済みの可能性有 100@1400」。数量100・税込単価1400。原文L145は1つあたり税込単価と明記。
- 原文L107はイーブイex、L111はスペシャルBOX フクオカ。注意書きはL109の同一商品行内にあり、前後商品への誤帰属なし。
- 抽出raw_memoは「※買取品のためサーチ済みの可能性有」、保存解析note_jaは「サーチ済の可能性,買取品」。試験後にもnote_jaは保持されていた。注意書きが消えたわけではない。Box向け状態判定はこのmemoを状態分岐に使わずSealed boxへ既定化する、という限定した観測である。
- 全66価格行に抽出66明細が対応。数量/価格一致66/66、商品名の原文内存在66/66、状態・備考の原文内存在66/66（空欄は不一致なしとして集計、非空状態1・非空備考2）、試験前後のnote_ja保持66/66。対象検査の不一致0。商品IDの意味的な正解59件を独立確認した試験ではない。
- 「サーチ済みの可能性」はサーチ確定・開封済み・シュリンク無し・損傷を証明しない。Sealed boxが事実として誤りだと断定する証拠もない。状態の確定根拠が足りないため、備考を残したまま要確認とする設計候補を維持。57件の機械的な候補を57件正答として報告しない。
- 元の試験集計（単位1→58、商品59/66、状態既定57）は再解釈によって書換えない。保存先master-box-trial-20260912/source-audit.jsonに66行別の照合結果と集計を保存。Gemini追加0、製品/本番変更0、自己審査REVISEを継続。


### 人間確認後の配信経路・調査と設計候補（2026-09-12）

PO原文: 「システムが解析できなかったものは全て人間が確認するので要確認に回す、要確認のものは人間の確認後に配信をするので配信リストからは外しておく、人間の確認が完了した時点で配信する」「進めてくれ調査して結果を報告」。調査・設計を実施。製品実装承認とは扱わない。

#### 実物の確認

preflight成功。調査HEAD=adc8bc4d67a94e8ede45a1e9c0ee9f28d28bb70b。調査中にremote main=4afb81c398d26f4c9b1321a4c70f21c50e8211fbを確認。GitHub compareで差分はdocs/ai-agents/evidence-registry.md、docs/handoff/go-record-transcription/line-delegation.md、docs/specs/README.md、tasks/todo.mdの4文書のみ。以下の製品コードに差分なし。既存worktreeの未コミット文書を保持。

| 既存部品 | 確認できた事実 | 足りない点 |
|---|---|---|
| 解析結果一覧 | tcg_analysis_review_svc.py:46-103、107-132。要確認タブは商品未確定/単位未確定/exclusionで抽出 | 状態FLAG・価格欠落・needs_reviewと判定が共通ではない |
| 解析の要確認理由 | tcg_analyzer_svc.py:957-973。商品未確定、多候補、備考未解釈を記録 | 単位/状態/価格等と統一した配信可否ではない |
| 配信行の選別 | tcg_distribution_svc.py:183-252。商品・単位確定、価格非NULL、非excluded、状態非FLAGを要求 | needs_reviewや人の確認完了を参照しない。include_flag_single設定でFLAG_SINGLEを通せる。現本番設定値は今回未照会 |
| 人の修正 | item_corrections_svc.py:15-73。修正履歴・確認者を記録、商品ID変更のみ解析結果へ反映 | 単位/状態/価格/数量/備考の修正は同サービスでは履歴のみ。全項目を確定して配信する完了処理がない |
| 画面 | SupplierDetailView.tsx:97でItemComparisonをreadOnly=true。ItemComparison.tsx:23の汎用修正保存ボタンもdisabled=true | 商品選択/確認はProductMasterDrawer.tsx:420-445にあるが、汎用の行全体確認完了UIではない |
| 権限 | backend/app/routers/item_corrections.py:54-75でsuper_admin必須 | 一般運用者への権限拡大は別判断。設計候補は既存権限を維持 |
| 再解析 | tcg_analyzer_svc.py:1116、1150-1152で商品修正履歴がある行をスキップ | 原文/版が変わっても過去の確認を無条件に引き継がない仕組みの検討が必要 |
| 配信 | tcg_distribution_svc.py:411-474はclear→append_rowsの全置換、628以降に全配信先処理と未完了ガード | 修正保存後の自動起動なし。確認完了≠配信成功。多接続先の一部失敗/再試行/同時配信を扱う必要 |

#### 直接行った判定照合

実ソースから要確認タブWHEREと配信WHEREを取り出し、SQLiteメモリDBの人工6行へ適用。PostgreSQL統合試験ではない。正常、備考未解釈needs_review=true、状態FLAG_SINGLE、価格NULL、単位未確定、商品未確定を比較。

- 要確認タブに現れるのは単位未確定/商品未確定の2行のみ。
- 通常配信条件を通るのは正常と備考未解釈の2行。要確認理由があるのに配信できる構造を確認。
- include_flag_single=trueでは状態FLAG_SINGLEも通り3行。
- 状態FLAG/価格NULLは通常配信から外れるが、要確認タブにも出ない。
- 検査scriptとresultはprivate-research/sig-20260911/review-gate-recon-20260912/に保存。実画面操作・修正API・配信API・外部API・本番書込みは実行していない。

#### Planner: 既存部品を使う設計候補（草案）

目的は、機械で確定できた行を配信し、未解決行は人の確認まで外すこと。Geminiによる追加商品補完は対象外。原文は保存し、人の修正は別の確定値と履歴として残す。

1. 商品/単位/状態/価格/数量/解釈できない備考・矛盾等の必要条件を共通の判定関数へ集約する。画面、プレビュー、配信直前で同じ理由と可否を使う。既存FLAG_SINGLE例外も未解決行を人確認前に通せないよう整合させる。
2. 確定値の保存と「確認完了」を分離する。確認完了APIは原文・抽出・解析の版、対象明細/仕入先の一致、マスタIDの有効性、必要項目、権限をサーバーで再確認し、未解決があれば完了不可。UIだけで止めない。
3. 既存修正履歴を再利用し、全項目の有効値、確認者/日時/対象版、完了状態を一貫して保存する。システムの旧値をクライアント申告だけに頼らない。原文更新・再抽出時は変更した項目と確認の有効性を再判定する。
4. 確認完了の保存が成功したら配信待ちを確実に記録する（保存成功後の起動失敗で消失しない方式を正式設計）。人確認済み行と機械確定行の対象一覧を再生成し、既存全置換経路で配信する。最新有効投稿の判定と抽出/再解析中ガードを維持する。
5. 同時要求は直列化/集約し、古い一覧が新しい一覧を上書きしないようにする。行を単純追記しない。各接続先の成功/失敗/対象版を記録し、一部失敗時は未達を表示して再試行できるようにする。現在のclear→appendの途中失敗で空になる可能性も設計対象。確認済みと配信済みは別表示。

受入条件の草案: (A)未解決各種が全て要確認に出て配信0件、(B)同じ投稿の正常行は配信対象、(C)必要項目不足では確認完了不可、(D)全項目修正後に確定値で配信、(E)原文/履歴保持、(F)同時確認や再送で重複/旧値上書きなし、(G)原文更新で古い確認を流用しない、(H)3接続先中1つ失敗しても配信完了と表示しない、(I)確認保存直後のワーカー停止でも配信待ちが消えない。確認完了後の即時配信はガード/外部障害で遅延し得るため、受付成功と反映完了を区別する。

#### Architect自己審査

判定REVISE（方向は実現可能、実装可能な正式仕様には未到達）。観測により単なるボタン追加では要件を満たさないことを確認した。次の設計では共通判定の必須値/正規値、確認版の保存先と既存履歴の使い方、原子性/配信待ち、接続先再試行・排他、既存FLAG_SINGLEルール/ADRとの整合を確定する必要がある。既存branch/runbookを継続し新規文書体系は作らない。外部事例はこの差分把握に不要（既存コード・局所照合が直接根拠）。外部API仕様変更の設計にはまだ進んでおらずContext7照会なし。

状態: 調査結果・設計候補・自己審査を文書保存。PO発言の目的は上記原文で保持、正式設計の承認/カード発行/製品実装/PR提出/マージ/配信は未実施。必要な正式カードチェックは設計合格後、カード発行前に実施する。


### 人確認後配信の検証記録の正式保存（2026-09-12）

文書PR https://github.com/shingo-ops/salesanchor/pull/3439 を2026-09-12T00:32:54Zにマージ確認。merge SHA=66b417665c013fdb354d5bda63226d07a1b2182c。専用main起点worktreeで確認済み事実だけを選別して提出し、必須13/13を含む成功35・対象外10、失敗0で条件付きPO許可に基づきマージ。初回process-artifacts gateはPR本文のADR/設計相互参照不足で失敗し、参照を是正後に成功。追加実証は人工192条件と実修正関数7ケース。公開再現コードと結果JSONの一致を直接確認。PostgreSQL統合試験・本番再解析・配信は未実施。検証記録は自己レビューAPPROVE、製品設計REVISE。元の本worktreeの未コミット調査全体をマージしたわけではない。


### 最新保存66明細の正答根拠監査（2026-09-12）

PO依頼「測定してくれ」。既存の確定フラグを正解ラベルに流用せず、原文とマスタ正式名・公式商品資料から名称の対応根拠を別に構成し、保存済み出力と比較した。最終結果は総合正答率ではなく、名称対応の証拠充足度と不足項目である。

- 数量/価格の原文一致66/66。商品特定フラグ59/66に対し、名称対応根拠55/66（83.3%）=文字の全半角/空白/大小文字の正規化後にマスタ正式名と一意一致48+公式名称の表記対応7。これは現物の同一性、言語、販売単位、状態まで正解と認定した55件ではない。正答率83.3%とは呼ばない。
- 公式対応7: メガドリームex→MEGAドリームex、ポケモンGO→Pokemon GO、フクオカ/トウホク/ヒロシマのスペシャルBOX3、Classic、OP-17。原文の名前を起点とし、pid_resolvedフラグから正解を生成していない。同一AIの資料照合であり独立した人間の正解付けではない。
- 確定59件の中の追加確認4: イーブイex→スターターセット、ワールドチャンピオンシップス2023横浜→記念デッキ、25th ANNIVERSARY COLLECTION スペシャルセット→25th Anniversary Collection、プレミアムカードコレクション ONE PIECE DAY’25→ONE PIECE DAY’25 プロモ。これらを誤り4件とは断定しない。略称と商品形態の対応・マスタの意図が未確認で、正答側へも数えない。
- 25th公式は拡張パックとスペシャルセットを別掲載。一方、保存解析では商品PM0071+unit=Set（NAME_RECOVERY:セット）を保持している。内部モデルがこの組を同商品の表現として意図するかは未確認。「別の公式商品だから誤ID」と早計に断定しない。
- DAY’25公式は専用台紙付きのカード2種セット。マスタ名「プロモ」・シングル系だけで、そのセット全体を表す登録か単品かを断定しない。
- 既存の商品未確定7件も維持。名称対応の証拠が不足する行は合計11。これをシステム上の要確認件数11に書き換えたわけではない。
- 最新66明細のraw_unitは全て空。1件Setは商品名からの回復、57件Boxは仮説ルールの補完。現物/取引による独立単位正解0件。未開封の明示は1件あるが、全項目を満たす状態正解表は存在せず、状態が未記載の通常扱いを正解とはしない。商品×販売単位×状態の組の独立正解が揃う行0件なので総合正答率は**算出不可（0%ではない）**。
- 66行別のevidence-labels-private.json、measured-private.json、summary.json、measure.pyをprivate-research/sig-20260911/accuracy-audit-20260912/へ保存しhash照合。まず正解の根拠を構成してから出力を比較。外部資料のURLを各表記対応に付与。
- 製品/DB/配信/Gemini追加0。今回の観測は保存済みsnapshotに限定し、現本番の現在精度と呼ばない。次は追加4商品の意図確認と、単位/状態の取引上の正解確認が必要。正式設計はREVISE継続。

公式確認日2026-09-12（数値はSIG実測と混同しない）:
- https://www.pokemon-card.com/ex/25th/products/ （拡張パックとスペシャルセットの区別）
- https://p-bandai.jp/press/2025/09/1000016346/ （2025-09-26公表、DAY’25カード2種セット）
- https://www.pokemon-card.com/ex/m2a/index.html
- https://www.pokemon-card.com/ex/s10b/index.html
- https://www.pokemon-card.com/info/005053.html
- https://www.pokemon-card.com/ex/classic/
- https://www.bandai.co.jp/catalog/item.php?jan_cd=4582770058390000

### WEGO指定2ファイルの全行調査と商品検索語試験（2026-09-12）

PO依頼: 「商品判定の改善っを進めてくれ、まず商品名を取り違えないように過去の投稿履歴を全て調査、検索語で網にかからない現象を0件を達成してくれ」。対象は今回指定の2ファイルに限定。全行走査と局所試験を実施したが、全商品明細の正解付き網羅評価・検索漏れ0件・誤商品確定0件は**未達/未証明**。製品変更・本番再解析は未実施。

#### 入力と比較条件

| 入力 | 期間（ファイル内日付） | bytes | 物理行数 | メッセージ開始行 |
|---|---|---:|---:|---:|
| A: [LINE]WEGOメンバーさん向け内部での商品内部個人間取引情報&外注委託受託共有.txt | 2025-04-10〜2026-08-04 | 25,736,286 | 985,978 | 33,802 |
| B: [LINE]WeGo売ります・BOXカートンパック20260912_16.15.txt | 2026-08-24〜2026-09-12 | 2,890,188 | 118,672 | 2,040 |
| 合計 | 8/5〜8/23は提供ファイルに含まれない | 28,626,474 | 1,104,650 | 35,842 |

- A SHA256: `8a765988fb5c7dc50374625293a3760c90236ce2ec57e565e1cc20e169e7ae07`、B: `e93c5839f2c749c9c04b6d0be8bf3d3b4b4387723f30e6db7a30662531e29ee3`。原本パスはprivate inventory.jsonに保持。
- 日付/時刻/空行/継続行への分割合計を原本総行数と照合。既存 `backend/app/services/tcg_line_import_svc.py:118` のparse_line_export本体をASTで取り出し、全2ファイルへ実行したメッセージ数も33,802/2,040で一致。うちシステムイベント判定9,632/422を含むため、35,842件を販売投稿数と呼ばない。supplier_names=Noneによる件数照合であり、送信者境界の正答確認ではない。
- 比較は保存マスタ293商品（箱系262/シングル系31）、検索657登録中非空653、除外156登録。最新本番マスタの再取得は未実施。saved analyzer/guardsと依存scriptのSHA256をmanifestに固定した。現本番精度とは呼ばない。
- 原文の半角カナ等を失わないよう生文字列を保持。非空/非日付822,733行を138,686種類にまとめて全種類を検索。日付と本文の全順序はmessages-private.json、同一行の件数と最大4参照はunique-lines-private.jsonに保存。全出現位置はハッシュ固定原本から再現可能。
- `backend/app/services/tcg_analyzer_svc.py:223` は全角英数/大小文字だけを正規化、`:259` のASCII検索は内部空白を文字どおり扱う。`:481` は数字末尾境界、`:495` は作品・除外・シングル制約を扱う。正規化と商品照合関数は保存実ソースを実行。検索前絞り込みと全検索語総当たりの一致を固定seed500行+変更153行の計653行で検査し差異0。これは全行の総当たり二重検査ではない。

#### 全行の検索候補分類（商品解析率ではない）

| 分類 | 重複除去した行 | 延べ行 |
|---|---:|---:|
| 検索語に一致なし | 118,192 | 590,376 |
| 候補1商品 | 18,863 | 224,022 |
| 複数候補 | 1,062 | 6,025 |
| 検索には一致するが除外/シングル制約で候補なし | 569 | 2,310 |

商品見出し・数量価格だけの明細・送料・挨拶・時刻行も含む。590,376行を商品検索漏れ件数とは数えない。行単位の候補検索には作品見出しや状態の行またぎ解釈がなく、AI抽出後の本番入出力とも異なる。

#### 原文で確認した漏れと取り違え

- A:185012「25thゴールデンBOX」の次行に2BOX@114,800円。対応候補PM0073の既存検索では漏れる表記。英語表記も含むGOLDEN系323出現中、検索語一致なし248出現/19種類。
- A:262413「受け継がれる意志」、前行OP-13 OP13、次行に価格と在庫。マスタPM0181は「意思」と記載。名前だけで漏れる14出現/5種類のほか、同一行コードは検索に当たるがwork_id=Noneではコードだけで確定しない例がある。作品を抽出できた本番なら結果が変わり得る。
- A:734458「メガエルレイドスペシャルカードセット」、次行54000円×3ct。関連表記20出現中一致なし18出現/9種類。略称「メガエルレイドセット」の対応を一律には確定していない。
- ナンジャモジムセット469出現/5種類は全て既存検索語に一致なし。ただしマスタにはPM0099「スノーハザード&クレイバースト ポケモンセンター・ジムセット」が存在する。PM0149「ナンジャモ プロモ」とは別。初期調査で登録不足候補として扱った点を訂正し、PM0099の略称候補として試験。公式は同セットのナンジャモの周辺グッズを説明するが、各取引の内容物まで保証しない。
- コンゴウ団セット系255出現/7種類、シンジュ団セット系175出現/9種類は既存検索語に一致なし。保存マスタの商品名に該当団名なし。別登録との同一性・現マスタの登録状況・正式商品対応を確認するまで既存の似た商品へ割り当てない。
- **実在する反例** A:206279は「25thゴールデンBOX サプライのみ(プロモ、デッキ無し)」。A:857845は「25thピカチュウゴールデンBOXビニール入りプロモ」、次行に98,000@2。後者は同一文面5出現。広い検索語を加えるだけではPM0073セット本体へ確定する。これは単なる英大小文字の問題ではない。商品形態の取り違えを防ぐ確認が必要。

#### 実行したオフライン比較

1. 正式名の誤字/略称/空白に対応する**11商品・検索語15個**をメモリ上で仮追加。既存商品判定関数へ全履歴行の該当表記を通した。商品未確定→確定は153種類/延べ2,108行。内訳はもともと検索語一致なし757行、コード等の候補があった1,351行。既に確定した行の商品ID変更/確定解除は今回の差分0。出力増2,108行は正答数ではない。
2. 増加の主な内訳: PM0181=1,365、PM0099=468、PM0073=233、PM0203=16、PM0263=13、ほか13。最初の14語試験の1,640行からジムセット略称追加で468行増えた。これらは同文面の反復を含み、独立した正解事例ではない。
3. 単純追加の人工試験では通常表記4/4確定。危険語付与32ケース中24ケースも商品ID確定した。空箱・海外版・開封済み等が同一シリーズIDで妥当な可能性はあるため、24件全てを誤商品とは呼ばない。これだけでは安全な配信を保証しないという証拠。
4. 同じ行のプロモ/サプライのみ/空箱/言語/開封/未確定/終了表記を要確認へ止める保守的な追加判定を研究scriptで試した。実履歴の差分153種類から3種類/延べ7行を保留、残る候補2,101行。止めたのはサプライのみ1・プロモのみ5・取引終了〆1。人工40ケース（通常/危険語/ジムセット）40/40期待どおり。ただし観測例から作った同一AIの局所試験であり、独立の評価セットではない。`プロモ`一律保留は正規のプロモ商品も止め得るため製品仕様には採用していない。
5. 単語をつなげたマスタ名探索では、検索語に一致しないが正式名の空白/大小文字正規化で部分一致する例が9商品・21組/33出現あった。一般SARカード・OP-17BOX〆等も含むので全てを安全な追加対象とはしていない。

#### Plannerの整理とArchitect自己審査

当面の改善候補は、(a)正式名の誤字と実在略称の検索語整備、(b)空白表記の正規化、(c)セット本体/封入プロモ/サプライ/言語/複数商品を別に検証すること。検索候補に上がったことを、自動確定・配信許可と同一視しない。価格だけで商品IDを推定しない。単位のSIG既定ルールは今回変更しない。

**自己審査REVISE。独立レビューではない。** 正式設計合格・実装カード発行には、最新マスタ照合、原文の商品ブロックと明細の全件対応付け、正解付き名称一覧、行またぎの付属品/状態と複数商品検査、売買/完売/予約の区別、未登録商品の対応、未使用評価例での誤確定/漏れ検査が残る。全行走査で全商品を確認済みとすること、未確定行を既存商品へ強制的に割り当てて0件に見せることは不可。

| 基準 | 検証方法 |
|---|---|
| 指定ファイルの読み飛ばし0 | 原本SHA/全行分割/既存パーサの開始行数一致（今回達成） |
| 商品明細の検索候補漏れ0 | 全商品明細に原文位置と確認済み候補IDを付け、候補集合への包含を測定（未達） |
| 商品の取り違え0 | セット/カード単品/付属品/言語等の正解と比較し、自動確定の誤り0を確認（未達） |
| 未解決を配信しない | 人確認後配信の既存設計/PR #3439の不足事項と合わせて統合検証（未実施） |

保存: `~/.local/share/salesanchor/private-research/wego-full-history-20260912/` の22ファイル+manifest。原文を含むものは非公開、directory700/files600、全保存ファイルのSHA一致を直接確認。inventory/match-lines/alias-trial/guard-trial/coverage-checkと結果を保持。商品DB・製品コード・CI・本番・配信変更0、追加Gemini呼出0。外部導入事例は不要（手元の原文と実ソースが直接の根拠）。正式製品名確認だけ公式資料を使用し、事業成果や精度数値の根拠にはしていない。

公式資料の確認日2026-09-12:
- https://www.pokemon-card.com/ex/25th/products/ （GOLDEN BOXと他の25th商品の区別）
- https://www.pokemon-card.com/ex/m3/ （スペシャルカードセット メガエルレイドexの内容物）
- https://www.pokemon-card.com/products/sv/sv2-set.html （ナンジャモをモチーフにしたジムセットの正式名/内容物）
- https://www.bandai.co.jp/catalog/item.php?jan_cd=4582769864865000 （受け継がれる意志 OP-13の正式表記）

状態: 全行走査・局所比較試験・調査保存済み、全商品明細の精度測定未完了、検索漏れ0未達、設計自己審査REVISE、製品実装未着手、本タスクのPR未提出。GO委任の有効化は確認できておらず代理GO発行なし。

保存後検証: 当該worktreeで `git diff --check` exit0、`bash scripts/check-task-state.sh` exit0を直接確認。未コミット差分は既存のrecon/evidence-registry/tasksの3ファイルに限定。前便からの未コミット調査を含むため全差分を今回変更とは数えない。

### WEGO全履歴の継続調査: 表記・商品コード矛盾・登録不足（2026-09-13）

PO「進めてくれ」に基づく継続。preflight成功。mainはorigin/mainより95コミット遅れ・台帳外の既存未保存28件、継続worktreeは26コミット遅れで既存調査3ファイルに変更あり、保持した。比較したorigin/mainの固定SHAは `5b21b3b8`。`adc8bc4d`との差分は商品判定/商品ガード0、取込サービス17行。さらにGitHub APIで最新main `d66923e2edad1b6c22df4cba8adf74f23b968cfc` を確認し、商品判定・商品ガードの2ファイルをそのSHAで取得した。保存実ソースと両方の全文SHA256が一致。商品マスタの現在値はコード差分では確認できない。正式GO委任文書はdraft・REVISE・開始終了未設定。代理GO発行なし。

#### 追加測定

| 調査/試験 | 結果 | 解釈の限界 |
|---|---|---|
| 全35,842メッセージの数値取引構文と直前行の対応 | 数値構文243,043行、その直前が検索一致なし17,851種類/93,631出現 | 送料・状態・数値の続きも含む。商品明細数/検索漏れ数ではない |
| 空白/半角カナ/全角英数/ASCII型番ハイフン前後の正規化 | 新たに確定21種類/68出現、既確定のID変更/解除は今回差分0 | 同じ行の照合試験、正答数ではない。別名追加なし、検索と除外の両方を同じ正規化 |
| 作品制約・番号境界・名前コード矛盾など人工15例 | 正規化だけでは13/15、2失敗 | 失敗2は元の照合でも同じ。変更前からある問題 |
| 明示型番/vol値の矛盾を保留する試作 | 同じ人工15例で15/15 | 発見に使った例の再試験であり、独立評価ではない |
| 試作で全文の追加保留候補を探索 | 37種類/215出現 | 正しい複数商品列挙、既存のvol.1表記、中国版の版番号も含む。215誤りとは呼ばない |
| 公式照合した名称とコードの矛盾だけを選別し原本を再走査 | 7種類/122出現、原本全122か所の件数一致。現行関数では全122確定、試作では全122保留 | 正しい現物の商品IDは不明。誤った商品ID122件とは断定しない |

使用した原本2ファイルのSHAは前節と同一を再確認。今回も保存293商品マスタとの比較。研究スクリプトは製品コードに適用していない。DB更新/本番再解析/配信/Gemini追加は全て0。

#### 公式の名前・コードと矛盾する実例

| 原文（商品部分） | 出現数 | 公式で商品名に対応するコード | 原本参照例 |
|---|---:|---|---|
| OP-08 新たなる皇帝 | 91 | OP-09 | A:360766 |
| OP-10 新たなる皇帝 | 19 | OP-09 | A:52990 |
| OP-03謀略の王国 | 3 | OP-04 | A:783367 |
| OP-02 謀略の王国 | 1 | OP-04 | A:808383 |
| OP-04双璧の覇者 | 3 | OP-06 | A:783370 |
| OP-04 二つの伝説 | 2 | OP-08 | A:957955 |
| THE BEST Vol.2 PRB-01 | 3 | PRB-02 | B:84675、90220、101492 |

A/Bは前節指定ファイル。最後の例は次行に「美品」、その次に数量価格。単なる研究用の矛盾文字列ではなく原文中に存在する。現行の `backend/app/services/tcg_analyzer_svc.py:495` では除外で候補を絞った後に名前優先で確定し、別商品の型番が原文に残ることを独立の矛盾として保留しない。研究試作は、確定候補と別の商品へ対応する明示型番を発見した場合、候補を保持して自動確定を止める。

人工失敗例もう1件は `THE BEST vol.20` がPM0137（THE BEST）に確定。vol.2を数字境界で拒否しても、短いTHE BESTへのフォールバックが残るため。原文全走査ではこのvol.20例は見つからず、人工反例としてのみ扱う。版番号があるのに確定候補の検索語でその版を裏付けられない場合を保留する試作を追加した。ただしTHE BEST vol.1を正しく許容する正式な版情報も必要なので、そのまま製品化しない。

公式確認2026-09-13（一次資料、同一AIの照合）:
- https://www.onepiece-cardgame.com/products/boosters/op09/ （新たなる皇帝 OP-09）
- https://www.onepiece-cardgame.com/products/boosters/op04.php （謀略の王国 OP-04）
- https://www.onepiece-cardgame.com/products/boosters/op06.php （双璧の覇者 OP-06）
- https://www.onepiece-cardgame.com/products/boosters/op08.php （二つの伝説 OP-08）
- https://www.onepiece-cardgame.com/products/boosters/prb02.php （THE BEST vol.2 PRB-02）

#### 保存マスタに該当正式名がない5商品の確認

| 公式商品名 | 原文出現数 | うち直後に取引数値 | 保存マスタで検索語ヒット |
|---|---:|---:|---:|
| エリートスパーク | 521 | 476 | 0 |
| ブルーミングレディアンス | 357 | 340 | 0 |
| Summer Pockets REFLECTION BLUE Re:Edit | 340 | 340 | 0 |
| Toy Story 30YEARS＆BEYOND | 308 | 306 | 0 |
| Re:ゼロから始める異世界生活 Vol.3 | 355 | 355 | 0 |
| 合計 | 1,881 | 1,817 | 0 |

5商品33種類の行。原文の完全な商品名を対象にした列挙で、関連略称全てを含む保証はない。保存マスタ293行の正式名の該当一致も0。現在の本番未登録と同一視しない。公式の存在確認から登録候補を作れるが、未確認の商品へ既存PMコードを流用しない。

公式資料（2026-09-13確認、正規商品の存在/内容を確認するために利用。原文取引の現物の正答根拠ではない）:
- https://hololive-official-cardgame.com/products/post/elite-spark/
- https://hololive-official-cardgame.com/products/post/blooming-radiance/
- https://ws-tcg.com/products/smp_bp3/
- https://ws-tcg.com/products/pxr_bp2/
- https://bushiroad.com/media/f557ee4e1133faf0 （メーカー発売案内。ws-tcgのrz_bp3直読はエラー、公式メーカー資料で確認）

#### 行またぎを一律継承できない証拠

- A:212627「ブラック&ホワイト」、212628「ボックスセット」、212629「¥18,000×100」。ボックスセット単独では商品名に足りないが、2商品を組み合わせたセットかマスタの別商品かは単なる直前行補完では確定できない。
- A:273424「白熱のアルカナ」の数量行の後、273427「PRB -02」、273428に数量価格。近くのポケモン作品名をPRB-02へ継承してはいけない。正規化した型番を既知のワンピース作品で検査すればPM0172、作品不明/ポケモン指定では未確定という人工制約試験を実施。
- A:6824「ロケット団の栄光」の数量行等の後、6829「アタッシュケース」、6830に数量価格。この距離だけでセットの具体的な商品IDを断定しない。
- A:94609「25thアニバーサリーコレクション」、94610に数量価格。全履歴の当該文字列は420出現（プロモパック28、スペシャルset等11も含む）。短縮語や表記揺れの一括登録では商品形態の検証が残る。

#### 設計への反映候補と自己審査

優先順は(1)明示された名前・型番・商品形態の矛盾を要確認へ、(2)比較用の表記正規化、(3)根拠付きの別名整備と不足商品の登録、(4)商品ブロック/数量行の全件対応付け。原文はそのまま保持し、比較用文字列・候補・保留理由を別に残す。マスタに無い商品や矛盾する原文を強制確定して「検索漏れ0」に含めない。

自己審査REVISE継続。局所試験で改善候補を確立したが、全履歴の未使用正解セット/最新マスタ/複数商品の分割/正式な版情報と形態情報/配信ガードの統合が未確認。37種類の保留候補をそのまま誤りラベルに使わない。外部導入事例は不要（原文・実関数・公式名称が直接根拠）。正式実装カードは未発行。

#### 最新マスタ読取の準備と停止範囲

`docs/handoff/rehearsal-env/design-b-ssh-isolation.md:107` は「エージェントが無制限鍵を使えるのは、人間の明示許可（都度・タスク単位）がある場合のみ」。実物の `~/.ssh/config` はエージェント鍵を監視専用、prod1/prod2を人間の緊急対話用として区別している。既存 `docs/handoff/tcg-product-master-growth/card-templates.md:73` の本番DB読取定型は人間用鍵を使用するため、本タスクでその接続を開始していない。以前のGemini1回の認証許可を今回へ広げない。

- 具体的な読取候補: tenant_004の有効商品・商品区分・検索語・除外語・作品名を1回の読み取り専用接続で取得。新規外部AI呼出なし。read-latest-master.sqlにSELECT1文を準備済み、未実行。
- 実行条件: 人間用SSH鍵を当該読取タスクに限り利用する許可。接続時PGOPTIONSでdefault_transaction_read_only=onとstatement_timeout=10000、`-X`/ON_ERROR_STOPを固定、取得時刻/read_only値を記録しon以外は成果物として採用しない。
- 読取SQLの列は `backend/app/services/tcg_product_master_svc.py:126`、`:366`、`:82`、`backend/app/services/tcg_analyzer_svc.py:149`、`:171`、`:189` の実物で確認。現在DBのスキーマが異なればエラーを報告し変更しない。
- 最新マスタ取得だけを保留。ローカル全行検査・公式照合・文書保存は進めた。今回、文書のrg検索に対してlocal psql-write-guardがパイプを誤検知して拒否した1回がある。解除せず、DB操作を含まない単純な文書検索で確認した。SSH接続/DBクエリの拒否実績とは混同しない。

証拠保存先: `~/.local/share/salesanchor/private-research/wego-followup-20260913/`（18ファイル+manifest、前回証拠を依存として明記）。全出現位置・原文前後・試作結果を非公開保存。現在は調査/試験/文書保存、製品設計REVISE、最新本番マスタ読取未実施、検索漏れ0未達、製品実装/本番変更なし。

### 実際のGemini抽出済みデータによる整形比較（2026-09-13）

PO依頼: 「実際のgeminiが抽出したデータを使ってテストしてみてくれ」。LINE原文の各行ではなく、保存済みextraction_itemsのraw_product_name/raw_state/raw_memoを使用した。新規Gemini呼出し0。結論は**今回の実抽出データでは、追加整形による商品特定の改善0件**。

#### 対象・条件

- 主評価: retry-two-results.jsonの2ジョブ・2投稿・67明細。SIG66明細と別投稿1明細。ジョブのprompt_versionはraw-extraction-v3-work-p1、保存解析はname-first-v6-master-safety。過去にGeminiを実行して保存した結果であり、今回再抽出した結果ではない。
- 補足: sig-history-db.jsonの7ジョブ・489明細。旧v2/v3/v4/v6解析が混在。主評価と66item_idが重複、両方の和集合は490item_id。67+489を独立556明細として数えない。同文面の再抽出もあるため独立した商品数でもない。
- Gemini返答の列をstripしてraw_product_name等へ保持する既存処理は `backend/app/services/gemini_extraction_svc.py:245`、`:280`。今回の入力はこの保存済み抽出フィールドであり、Geminiの通信レスポンスのバイト列そのものではない。
- 前回の試験と同じNFKC・casefold・連続空白統一・ASCII型番のハイフン前後空白統一を、比較用の名前/状態/備考と検索語/除外語に適用。検索語の新規追加はしない。原本、保存済み抽出、DB、商品マスタを更新しない。
- 保存済み293商品マスタと実商品判定関数を利用。作品の有効IDは保存解析pid_basisのWORK:UUIDを再利用して前後で固定。作品証拠を原文から新しく推定していない。
- DB正規化ルール・単位による商品候補絞り込み・後段の単位/状態解決・配信は全体再実行していない。商品照合段の比較である。まず主評価の整形前結果が保存済み商品ID/pid_resolvedと一致することを確認し、67/67一致を達成。不一致0のためこの標本の商品判定差分を測定できるが、全工程の再現試験とは呼ばない。

| 測定 | 主評価67明細 | 補足489明細 |
|---|---:|---:|
| 整形前の商品確定 | 59 | 436 |
| 整形後の商品確定 | 59 | 436 |
| 新たな確定 | 0 | 0 |
| 確定商品のID変更 | 0 | 0 |
| 確定から未確定へ | 0 | 0 |
| 候補集合も含む判定変化 | 0 | 0 |
| 保存解析との整形前一致 | 67 | 485 |
| 既存normalize_enを超える商品名文字列変化 | 2 | 14 |

主評価は確定59/未確定8のまま。ここでいう確定はシステムの特定結果であり、独立正解と照合した正答59件ではない。総合正答率は測定していない。補足の保存解析との差4件は旧name-first-v2のTHE BEST2等で、今回の整形前後は同じ。過去解析との違いを追加整形の効果に数えない。

主評価で文字が追加変換された2件は「ナツコミ 2026 メタキラカード　ワンピース ルフィ」「肉ルフィカード　モンキー・D・ルフィ P-159 プロモ」の全角空白→半角空白。どちらも商品未確定のまま。半角カナ等による見逃しが主評価で解消した例は0。

残る8件: op-17、25thアニバーサリー、最強ジャンプ 頂上の強者 プロモ、ナツコミ 2026 メタキラカード ワンピース ルフィ、肉ルフィカード モンキー・D・ルフィ P-159 プロモ、ONE PIECE × ROUND1 プロモパック、ONE PIECE CHOPPER’s、プレミアムカードコレクション ONE PIECE DAY’24。追加整形だけでは解消しないという観測であり、8件の原因を全てマスタ未登録と断定していない。

#### 設計判断

前節のLINE原文138,686種類を使った「68出現の確定増」は、Gemini抽出後のデータによる効果ではない。本実験により、少なくとも主評価67明細ではその改善は再現しなかった。追加整形を本番に入れる効果の根拠として原文68出現を流用しない。Geminiが常に必要な正規化を行う、整形処理に将来も効果がない、とは一般化しない。

商品判定改善全体の自己審査はREVISE継続。本試験は現状の追加整形の効果を測定する調査であり、製品実装承認ではない。最新DBマスタの取得、未解決商品の根拠付き対応、別の実抽出標本での評価が残る。既存の名前/型番矛盾122出現の原文検査とも母集団が異なる。

保存: private-research/gemini-extracted-normalization-20260913/（test-extracted.py、results-private.json、summary.json、audit.json、manifest.json）。入力2ファイルのSHA256を記録し、実行後に同一であることを直接確認。再現scriptは前回の保存実関数・整形関数を依存として利用。保存用manifestには依存ファイルのhashも記録する。

状態: 実抽出67明細の商品判定比較完了（保存判定67/67再現、改善0）、過去489明細補足比較完了。新規Gemini呼出/製品変更/DB書込み/本番反映/配信0。本タスクのPR起票なし。全履歴の検索漏れ0未達は継続。外部API仕様の変更・参照不要、外部事例は直接のデータ比較に不要。

### SIG未特定7明細の原因切り分けと整形実装方針（2026-09-13）

PO発話「まずこの整形の実装は確定で進める、sigが解析できない要因はマスタの検索語と除外ワードの不足が原因か？」、続く依頼「調査してくれ」を受領。

**決定記録**: 整形の実装方針はPO承認済み。配置はGemini抽出後・商品マスタ照合直前、原文/抽出結果は保持して比較用文字を整える。先の実抽出67明細で改善0だった事実は維持する。これは正式設計の自己審査合格・実装カード発行・本番反映の完了を意味しない。本セッションは設計担当を継続し製品コードは変更していない。方針承認を再要求しない。

#### 実測した直接原因

- 対象は保存ジョブ902f53c1のSIG66明細中、pid_resolved=falseの7明細。別投稿のop-17未確定1明細を含めない。
- 原文のL89、125、127、129、131、133、137を確認。7件すべてraw_product_nameの文字列が該当原文に存在する。CHOPPER’sの「チョッパーズ雑誌プロモ付き」はraw_memoにも保持。商品名脱落が原因である証拠なし。ただし全抽出項目の正答認定ではない。
- 保存293商品・検索657登録（非空653）について、作品/単位/シングル制約/除外を適用する**前**の検索一致を全商品で検査: 7/7が検索候補0。
- 除外語をメモリ上で全て外す比較も実行: 特定0/7。検索候補が最初から無いため、除外語が直接の遮断原因である件数0。DBの除外語は変更していない。
- 結論: 1件は登録済み商品群への略称不足と同一性の確認、6件は対応商品登録が保存マスタで見当たらない。検索語追加と商品登録は別の作業。除外語不足の対策は取り違え防止には必要だが、この7件の未特定を解消する直接の修正ではない。

| SIGの商品名 | 保存マスタで確認したこと | 次に必要な対応 |
|---|---|---|
| 25thアニバーサリー | PM0071 Collection、PM0072プロモパック、PM0073 Golden Box等は存在。原文の略称は検索一致0 | SIGの略称がどの商品・形態を指すかを確かめて検索語登録。周囲にブースター名が並ぶが、それだけで同一性を確定しない |
| 最強ジャンプ 頂上の強者 プロモ | 頂上の強者に対応する商品名・検索/除外語なし。PM0085「頂上決戦」とは別 | 正式な商品登録と検索語を用意。公式は「頂上の強者パック」特製カード3枚セットで、雑誌そのものの付録ではないと記載。原文販売物がセットか個別カードかも区別 |
| ナツコミ2026 メタキラカード ワンピース ルフィ | ナツコミ/メタキラの対応登録なし | キャンペーン特典として登録。別のルフィのTCGカードへまとめない |
| 肉ルフィカード モンキー・D・ルフィ P-159 プロモ | P-159/肉ルフィの対応登録なし | P-159の正式なカード・版を確認して登録。今回の検索ではメーカー/出版社によるP-159の一次資料を確保できず、通常版/豪華版等の同定は未確認 |
| ONE PIECE × ROUND1 プロモパック | ROUND1/ラウンドワンの対応登録なし。原文は未開封を明記 | 公式のROUND1プロモーションパックとして登録候補を整理。封入カード単品とは別に扱う |
| ONE PIECE CHOPPER’s | CHOPPER/チョッパーズの対応登録なし。原文/メモは本+プロモを記載 | 書籍+同梱カードの販売物として登録候補を整理。既存ONE PIECE magazine各号の付録プロモへ流用しない |
| プレミアムカードコレクション ONE PIECE DAY’24 | DAY24/2024の対応登録なし。PM0179 DAY’25は存在 | 2024年版を別商品として登録候補化。2025年版の検索語に追加してはいけない |

「対応登録なし」は**保存マスタの正式名・検索語・除外語を照合した結果**。現本番の最新マスタは今回も取得していないため、現在DBに絶対存在しないとは断定しない。名称が似た既存商品へ検索語だけ足し、無理に7件確定させる試験は実施していない。

#### 原文と公式資料の確認

公式確認日2026-09-13。名称/商品形態の根拠であり、仕入先の現物を確認した証拠ではない。

- https://www.pokemon-card.com/ex/25th/products/ : 拡張パック・スペシャルセット・プロモパック・GOLDEN BOX等が存在。短い「25thアニバーサリー」だけでは形態が一意と証明できない。
- https://www.saikyojump.com/zs_opcg2026/ : 最強ジャンプ2026年5月号「頂上の強者パック」、特製カード3枚セット。今号の付録ではない旨を確認。
- https://natsucomi.shueisha.co.jp/novelty/ : ナツコミ2026の描き下ろしメタキラカードにONE PIECEを掲載。原文「ルフィ」の個体/絵柄まで画像照合したわけではない。
- https://one-piece.com/news/80977/index.html : 2026-07-18開始のROUND1キャンペーンのプロモーションパックを確認。
- https://one-piece.com/news/78041/index.html : CHOPPER’s1巻、同梱EB02-003トニートニー・チョッパー、発売日2026-04-23。以前の告知03-04から変更されているため旧記事の日付を採用しない。
- https://www.onepiece-cardgame.com/pdf/don-cardlist.pdf : プレミアムカードコレクション ONE PIECE DAY’24の記載を確認。通常商品ページの直接取得はエラー。今回この資料だけでセット構成の全てを確定していない。
- P-159は原文に記載されたコードを保持。二次販売サイトの通常版/豪華版の説明を正式マスタ確定根拠として採用しない。公式カード検索の直接取得もエラーであり未確認を維持。

#### 保存・審査状態

private-research/sig-seven-causes-20260913/ にaudit.py、audit-private.json、summary.json、manifest.jsonを保存。実検索語一致と除外全解除比較、原文前後、登録探索パターン/結果、出典を保持。原本/マスタ/依存スクリプトのSHAを記録。

観測の切り分けは完了。整形実装方針はPO承認済み、製品設計の自己審査REVISE継続、製品実装未着手。7件全解決・検索漏れ0は未達。外部Gemini追加0、DB/本番/配信変更0。次は商品登録候補の正式形態と最新マスタを照合し、整形は承認済み方針として実装役へ渡せる仕様へまとめる。

### PO確定: 25thアニバーサリーの追加先（2026-09-13）

PO発話「25thアニバーサリー は検索ワードに追加」。確認「追加先は、通常の拡張パック『25th Anniversary Collection』で合っていますか？」に対しPO「イェス」。よって検索別名 `25thアニバーサリー` の対応先はPM0071（UUID797f6adb-87f5-4316-99be-6227bda5c431、保存正式名25th Anniversary Collection）としてPO承認済み。対象の再承認は不要。実装する整形方針も引き続きPO承認済み。

保存SIG実抽出66明細へ、メモリ上で当該検索語1個だけを仮追加した比較では、商品確定59→60、変更は当該1明細だけ。残る未特定6明細は変化なし。現物の総合正答率を測定した試験ではなく、POが指定した商品対応の局所確認である。新規Gemini呼出/DB書込み0。

境界試験7例: 指定別名はPM0071、明示プロモパックは既存PM0072へ特定。一方、別名の後ろに「プロモ」「ゴールデンBOX」「スペシャルセット」「空箱」「サプライのみ」を付けた人工5例も現行の部分一致ではPM0071に特定する。スペシャルセットの表現方法（商品ID+単位の組）の既存仕様は別途確認が必要だが、PO承認が本体以外まで包括するとは扱わない。**現行DBに別名だけ追加する案の自己審査はREVISE**。

実装設計では当該別名による補完と既存照合を区別し、商品名の完全一致条件・状態/備考の形態制約、または対象商品に限定した適切な除外条件を検証する。プロモパックの既存PM0072判定を維持する。部分一致に追加するだけで安全との承認は出さない。全商品に効く除外語を独断で追加しない。

証拠: private-research/sig-25th-alias-approved-20260913/check.py、result-private.json、decision.md、manifest.json。役割は設計担当を維持、方針/対応先PO承認済み、仮追加試験済み、決定文書保存、正式実装設計REVISE、製品DBへの追加は未実施。


### 25thの商品別除外語: プロモ・ゴールデン・golden（2026-09-13）

PO提案「除外ワードをフィルタとして機能させるためにプロモとゴールデンを除外ワードに追加すればいいのでは？」、続く指示「goldenも」を受領。対象は通常拡張パックPM0071（25th Anniversary Collection）の商品別除外語。追加候補は `プロモ`、`ゴールデン`、`golden`。プロモ商品のPM0072など他の商品へ同じ除外語を追加しない。

実関数/保存マスタのメモリ上で試験。検索別名25thアニバーサリーを追加したSIG66明細の商品確定60は、上記除外語追加後も60で維持。通常の別名はPM0071、プロモパック明記はPM0072を維持。別名+プロモ、別名+ゴールデンBOX、別名+GOLDEN BOXはPM0071に確定しない。goldenは既存の大小文字正規化によりGOLDENにも効く。最初の日本語2語だけの試験ではGOLDEN BOXを防げず、3語の試験で防げたことを直接確認。状態/備考に日本語2語を置く4例もPM0071へ確定しない。

局所結果はこの除外案の有効性を支持する。ただし人工の別名+スペシャルセット/空箱/サプライのみの3例は、この3語だけではPM0071への確定が残る。ASCII語のgoldenは単語境界付きであり、すべての綴り・連結表記に対応すると一般化しない。残る形態の扱いと最新マスタ確認を含む製品設計REVISEは継続。

証拠: private-research/25th-exclude-trial-20260913/ の日本語2語/英語追加版のscript・result・log・manifest。POの追加語を設計記録へ反映済み、DBへの登録・製品実装・本番反映は未実施。追加Gemini呼出0。


### Gemini実抽出データで除外語追加を再検証（2026-09-13）

PO依頼「現在のgeminiが抽出したデータを使ってテスト」。保存retry-two-results.json全67明細を入力とし、保存実関数で現状・別名追加のみ・別名+PM0071限定除外3語の3条件を再実行。SIG66明細は59→60→60、全67明細も59→60→60。変更は25thアニバーサリーのNONE→PM0071のみで、除外語追加による判定変更0件。残るSIG未特定6件は前記と同じ。商品特定率89.4%→90.9%であり、全項目の総合正答率ではない。

実データの商品名/状態/備考にプロモ含有4件、ゴールデン/golden含有0件。従って英語/日本語Golden除外の実データ上の効果は今回測定できない。前回の人工境界例と混同しない。入力ファイルmtimeは2026-09-11 11:10:29 UTC（取得日時そのものの証明ではない）。本番から最新データを取得した試験ではない。

証拠: private-research/sig-actual-excludes-retest-20260913/test.py、result.json、manifest.json。実行2026-09-13 00:48:31 UTC。Gemini呼出0、DB/本番変更0。追加3語による既存判定の変化がないことを確認、正式設計REVISEと実装未着手は継続。


### PO合意・登録依頼受領（2026-09-13）

PO原文「これで合意、登録してくれ」。直前に提示した保存Gemini抽出66件の比較（59→60、除外追加で変化0）を受けた登録依頼として記録する。承認対象はPM0071（25th Anniversary Collection）への検索語「25thアニバーサリー」1語と商品別除外語「プロモ」「ゴールデン」「golden」3語の追加。既存語の削除・他商品の除外変更・再解析・配信の許可へ拡張しない。登録内容について再承認を要求しない。

状態: PO合意・登録依頼受領済み、文書記録済み。本セッションは起動指示の設計担当を維持し、DB変更・実装役への自動切替は行わない。正式設計の自己審査REVISEは継続。最新対象マスタ未確認と、別名+スペシャルセット/空箱/サプライのみの人工3例でPM0071へ確定する既知の残件を合意によって合格へ読み替えない。実行可能な正式カードは未発行、DB登録は未実施。

引き継ぎ対象: PM0071 UUID797f6adb-87f5-4316-99be-6227bda5c431（保存マスタ）。実装担当は最新のテナント・商品ID・既存語を照合し、重複を避けて上記追加分のみ扱う。登録前後の語一覧差分、SIG66件の比較、プロモパックPM0072保持の証拠を残す。正式カード発行前に残る誤一致の対処を設計・検証し、承認済み追加語を独断で拡張しない。


### スペシャルセットの別商品登録依頼とサプライの未確定（2026-09-13）

POは25th ANNIVERSARY COLLECTION スペシャルセットと「25thアニバーサリー サプライのみ」を商品マスタへ登録し、検索語・除外語で判別するよう依頼。スペシャルセットの別商品登録方針を承認済みとして記録。公式 https://www.pokemon-card.com/ex/25th/products/ の商品一覧を再確認済み: 2021-10-22発売、拡張4パック・プロモ1パック・コイン1枚。既存登録の有無は最新マスタで未確認であり、新規IDを創作せず重複確認が必要。

設計案: スペシャルセットの商品別検索語へ「25thアニバーサリー スペシャルセット」「25th ANNIVERSARY COLLECTION スペシャルセット」を設定し、通常PM0071側では該当セット表記を除外する。確定語・商品別除外と競合候補は全マスタ再試験後に決める。これは設計案でありDB反映・設計合格ではない。

「25thアニバーサリー サプライのみ」はAIが境界試験に作成した文字列で、SIG実投稿の確認済み商品名ではない。サプライは個別のスリーブ・ケース・コイン等のどれかを特定していない。ユーザーへ対象の具体的な中身を1問で確認する。意味不明の汎用商品として自動登録せず、未確定の間は通常BOXと同一視しない設計とする。新たな商品登録方針は受領済み、商品同定・検索除外設計・試験は未完了。実装担当への自動切替なし、DB変更なし。


### PO合意: サプライのみの除外登録（2026-09-13）

PO原文「合意、除外ワードに登録して」。直前提示の通常BOX一致除外・商品未特定として要確認/配信対象外・人間確認後に具体的商品へ紐付けて配信する方針への合意として記録。対象は通常25th Anniversary Collection（保存PM0071）の商品別除外語「サプライのみ」。全商品共通除外や単独語「サプライ」への拡張、新規の汎用サプライ商品登録は含めない。

登録予定の合意済み差分は検索語「25thアニバーサリー」、商品別除外語「プロモ」「ゴールデン」「golden」「サプライのみ」。既存語は保持。他商品への一致可能性と要確認/配信抑止経路は別途検証が必要で、除外語追加のみで全経路の配信抑止が保証されたとはしない。「空箱」除外は今回の承認に含めず未決を維持。

PO承認・文書記録済み、DB登録未実施。設計担当の権限範囲は継続し、正式設計・カードの審査完了前に実装担当へ自動切替しない。登録内容の再承認は不要。


### 25th登録準備の追加実測（2026-09-13）

preflight成功。本店mainはorigin/mainより145コミット遅れ、台帳以外の未保存28件を保持。専用調査ブランチHEADはorigin/mainより76コミット遅れ、既存未保存3文書を保持。mainの最新SHAをGitHub APIでee455fb1ba4c7ad407ed6506ee4fe515fce371a8と確認し、その版の解析/配信コードを読み取り比較。

証拠private-research/25th-design-review-20260913/。5照合関数AST一致、保存実抽出67件59→60、変更は25th1件。4除外追加後のサプライ3欄3例はNONE+pid_unresolved、プロモパック維持。配信SQLはpid_resolved/needs_review/exclusion条件を持つ（main版tcg_distribution_svc.py:238–240）。実DB配信試験は未実施。スペシャルセット/空箱2例はPM0071確定のまま。

既存design-keyword.md §17へ目的/登録差分/Why/受入/自己審査を保存。PO登録方針合意済み、設計草案・自己審査REVISE、正式カード未発行、DB未登録。旧§5と保存マスタのPM0071記載不一致を確認したため最新のID+正式名照合が必須。全有効/無効商品を含む単一SELECTを証拠先に準備したが未実行。監視専用SSHではDBを読めず、人間用鍵の都度許可未確認が現時点の取得上の制約。GO委任のmain文書はdraft・有効化未整備であり代理GOを出していない。


### 最新マスタ読み取り1回と再試験（2026-09-13 10:32 JST）

POへの直前確認「今回のマスタ読み取り接続1回に限り、人間用SSH鍵の使用を許可しますか？ DB更新は行いません。」にPO「進める」。このタスクの読取1回の許可として人間用SSHのprod1経路を使用。接続1回・単一SELECT、psql -X/ON_ERROR_STOP/default_transaction_read_only=on/statement_timeout=10000。返却transaction_read_only=on、captured_at=2026-09-13T01:32:27.885752+00:00。許可は消費済みであり次回接続へ流用しない。DB更新0・Gemini呼出0。

商品296（有効293）、検索657、除外156、作品11。PM0071 UUID797f6adb-87f5-4316-99be-6227bda5c431は現DBでも通常25th Anniversary Collection、S8a、箱系。PM0072はプロモパック、PM0073はGolden Box。旧設計§5のPM0071 Golden記載を現在の更新先根拠にしない。今回合意の検索1語と除外4語は当該商品に全て未登録。

有効/無効全商品名・英名・検索/除外語で25th/25周年/アニバーサリーおよびスペシャルセット/special set/specialsetを照合。25thスペシャルセット対応登録は見当たらない。別商品PM0100 exスペシャルセットの存在は確認し、25thの代用にしない。

最新有効293商品・辞書へ置き換えて保存Gemini67明細を再試験。特定59→60（SIG66件内も59→60）、変更25th1件のみ。サプライの商品名/状態/備考の人工3例すべてNONE+pid_unresolved。プロモパック判定保持。空箱・スペシャルセットはまだ通常へ確定するため、残件は維持。最新のDB辞書での試験であるが、Gemini抽出自体は既存保存値であり最新投稿全量の再取得ではない。

根拠private-research/25th-design-review-20260913/latest-master.json（SHA256 9373400c7036275dcd32bbbf63ff92d14bb1d5cf35c205b0fec921ec46a1ed63）/live-summary.json/test-latest.py/result-latest.json/manifest.json。人間確認後の配信経路の実DB試験は未実施。今回の規則検索1回はlocal psql-write-guardがrgの正規表現をpipeと誤検知して拒否したが、DB操作はその時点で行っておらず、解除せず単純な文書読取で確認。SSH/SELECTは成功。


### 訂正と追加実測: スペシャルセットはSIG実データにも存在（2026-09-13）

先行チャットの「実際のSIG抽出データでこの誤判定が見つかったわけではない」「人工例だけ」という説明は、スペシャルセットに関して誤りだった。人工の短縮名テストとは別に、保存SIG原文L121に「25th ANNIVERSARY COLLECTION スペシャルセット 30@40000」が存在する。抽出item cc81d3d1-6e0e-423e-b83e-5fb064dbc886、job902f53c1のraw_product_nameも同じ商品名。保存analysisはPM0071/通常25th Anniversary Collection、pid_resolved=true、needs_review=false、unit=Set、condition=FLAG_SINGLE。商品特定数の59件に、この通常商品への紐付けが含まれていた。59/66は正答率ではない。配信実績は今回確認しておらず、FLAG_SINGLEは配信オプションで扱いが変わるため配信済み/未配信を推測しない。

latest-master（10:32JST）のメモリコピーに新規セットの仮IDTEST_ONLY_25TH_SPECIAL_SETを追加。通常PM0071の追加検索1語、除外は合意4語+スペシャルセット+空箱。新セット検索2語・除外サプライのみ/空箱。空箱はPO未承認の提案として区別。PM0072/PM0073の辞書不変。実67行は59→60、変更は略称NONE→PM0071と、実スペシャルセットPM0071→仮セットの2行。SIG内の商品特定数は同じ60/66だが紐付け訂正1件を別に計上する。

人工対照21/21成功: 通常/プロモ/Golden正式通称維持、GOLDEN BOXの通常不一致、セットの英字名/日本語略称/空白なし3例、新セットの商品名を保ち備考に同梱プロモを記載する1例、セット+プロモパックの曖昧名は複数候補で未確定、通常/セット双方の空箱/サプライのみを商品名/状態/備考に記載する12例は未確定。21は商品ID判定の局所対照であり全解析/配信試験ではない。

最新マスタの既存exスペシャルセットPM0100とGolden PM0073は通常PM0071と同じ箱系category UUIDを持つ。新セットの箱系分類はこの既存運用に合わせる設計案。単位SetをBoxに変換しない。登録サービスはmark/english_title/release_dateを任意、4分類参照+日本語名を必須とする。新規ID/PM番号は実装時の安全な採番としテスト仮IDを本番へ入れない。

証拠private-research/25th-design-review-20260913/test-set.py/result-set.json/actual-special-set-proof.json。公式商品の構成は既出メーカー資料。製品コード/DB変更0、追加SSH0、Gemini0。設計改訂とカード草案を保存、空箱のPO判断が未決のため発行しない。


カード草案検査記録: `bash scripts/card-lint.sh docs/handoff/tcg-product-master-growth/card-25th-product-disambiguation.md` 終了0、L24の200字超警告2件（非停止）。`git diff --check` と `bash scripts/check-task-state.sh` も終了0。人手の発行前確認では空箱のPO判断と正式文書保存が未了のため、書式合格のみ・未発行を維持する。今回の実測は実装後のCI/DB試験合格ではない。


### 空箱の履歴全行検索（2026-09-13）

PO「空箱が出てくることはないと考えているがどうか？」を受け、提供2履歴の全1,104,650行（985,978+118,672）を再検索。内部取引履歴に「空箱」10行、後半の売ります履歴には0行。全10行とも「ポケモンカートンの空箱」で、前後原文に「6個セット」と価格がある販売投稿。2025-07-29〜2025-08-04、同じ投稿者の反復であり独立した10種類の商品ではない。最初の5000円、4000円、3800円の値を確認。25thの商品を特定した空箱表記はこの10行にはない。SIG抽出66件の空箱出現事実とも混同しない。

「サプライのみ」は内部取引履歴5行、売ります履歴0行。そのうち原文L206279に「25thゴールデンBOX サプライのみ(プロモ、デッキ無し) 7000円 15BOX」が存在（原文空白はprivate証拠に保持）。空き箱/空BOX/empty box/emptybox/外箱のみは0。「箱のみ」3行は残り8箱のみとコロちゃお箱のみ本無しを含むため空箱として数えない。字面検索結果を空箱件数へ無条件集約しない。

根拠private-research/25th-emptybox-history-20260913/result.json/contexts.json/manifest.json、入力SHAは先行履歴照合と一致。日付はYYYY.MM.DD見出しで確認。中間抽出で数字/boxを日付誤検出した結果は訂正し保存値は正しい見出しに置換済み。

結論: 一般に空箱販売が出ないという前提は履歴と一致しない。ただし今回の25thに限った出現は未確認なので、PM0071への除外追加を実績ある25th誤判定の解消とは説明しない。空箱方針のPO判断は本確認を踏まえて継続待ち。直前の進めるを最新の疑問を無視して確定承認へ読み替えない。製品/DB変更なし。


### 空箱の状態マスタ化: 現状と試作（2026-09-13）

POの状態分類提案と「進めてくれ」を受領。design-keyword.md §18へ方針変更を記録。商品別の空箱除外案は実装前に撤回。商品分離は空箱を除いた15対照で全成功、実67明細59→60・変更2を維持。

main9e0406eeの実関数と9/11保存条件10件で試験。マスタだけ仮追加は12中8件で空箱判定、8件とも空箱を理由とする要確認なし。備考4件は空箱状態へならない。局所試作は12/12+既存7/7、曖昧4例は判定層の検出のみ。状態保存/確認画面/配信SQLを通した試験ではない。初回2回の実験失敗は抽出した関数の正規表現定数不足によるNameErrorで、実ソースの定数を含めて修正後に測定。製品不具合やCI失敗に数えない。

証拠private-research/emptybox-condition-design-20260913/に参照ソース、test.py/result.json、prototype.py/prototype-v2.pyと結果、SHAを保存。空箱10履歴の同一商品名を状態関数へ渡す照合も保存済みだが、実際にGeminiを再実行した入力ではない。商品判定の最新再試験は25th-design-review-20260913/test-set-no-empty.py/result-set-no-empty.json。

最終状態: 方針PO合意・草案/試作保存、自己審査REVISE、製品実装/DB登録なし、追加SSH/Geminiなし。次は最新状態マスタの確認と人間確認後の状態/理由解除を既存設計へ接続する。旧カードの空箱商品別除外を実行させない。


### 空箱の確認後経路を実物照合（2026-09-13）

最新参照main cacc889eで、ItemComparisonはreadOnly表示、商品確認のAPI入力はproduct_idのみ。実save_correctionsへSQL記録代役を与えた4対照でcondition/needs_review更新0を観測。_build_where実関数のNEEDS_REVIEW/NORMAL_COMPLETEDはneeds_reviewを参照しない。従って状態マスタ+解析フラグだけでは確認画面への到達/状態確認後の解除は完成しない。初回試験のkeyword-only関数に位置引数を渡したTypeErrorは試験呼び出しを修正して再実行成功。DB結合試験とは区別する。

design-keyword.md §18.6へ画面・版照合・履歴/状態の同時保存・空箱のまま確認・他理由保持・再解析時の保護・既存配信候補への復帰を設計。最新のconditions/units/列定義を1SELECTで読むSQLを準備、未実行。根拠private-research/emptybox-confirmation-design-20260913/。新SSH/Gemini/製品/DB変更0。自己審査REVISE、正式カード未発行。


### 状態マスタ・確認列の最新読取（2026-09-13 11:35 JST）

直前の人間用SSHによる状態マスタ・保存項目の読み取り1回確認にPO「進める」。許可範囲でprod1へ1回、単一SELECTを実行し成功。default_transaction_read_only=on、statement_timeout=10000、psql -X/ON_ERROR_STOP、返却read_only=on。DB更新なし。conditions10/units8/対象3表列42、CN0011およびEmpty boxは未登録。状態全10行は9/11保存と一致し、関連5関数ASTも参照main cacc889eと前回試験で一致。

条件追加案のID/codeと優先順位衝突の未確認は解消。確認履歴の全必要欄があり、新たな履歴表を直ちに増やす根拠はない。ただし現行商品修正はupdated_atを更新しないので、日時だけの版照合では足りない。design-keyword.md §18.7に指紋・明示状態確認・予約履歴キー・同時保存・重複送信・再解析時の失効を具体化した。状態マスタ最新確認を設計完成や実DB検証合格と同一視せずREVISE継続。

根拠private-research/emptybox-confirmation-design-20260913/live-condition-context.json、live-summary.json、manifest.json。入力SHA d80ac2fe09e973342ca8b8c4503c5f4498bd55e9179213f6c912bb09877d4660。今回SSH許可は消費済み、新規Gemini0・本番更新0。


### 空箱の確認保護・最終設計（2026-09-13）

全サービスの解析行書込をgit grepで照合しanalyzer1、item_corrections1、unit_recovery4箇所を確認。E5はR4:単位既定:単位不明だけを上書きし、状態専用basisは対象外。更新日時の変化に頼らないbindingと、読取時の共通保留判定をdesign-keyword.md §19へ固定した。

private-research/emptybox-final-contract-20260913/check.py/result.jsonで表現26例/確認有効性15例を期待と照合、全一致。これは実行可能な設計モデルであり製品試験ではない。PG16のsha256/convert_to/encode/jsonb_build_object/trim_scale/IS JSON OBJECTを公式確認。Context7はツール一覧に存在せず代替許可に従った。

同一AI自己審査は§19の限定実装設計APPROVE。実DB/画面/CI/競合試験は実装後の必須受入。実装担当未起動、DB/製品変更なし。通常25thの辞書カードは空箱保護の完成と合わせて扱い、条件マスタ1行を先に投入しない。POのGOや独立レビューを創作しない。


2026-09-13 カード整備: `docs/handoff/tcg-product-master-growth/card-empty-box-condition-review.md`（CARD-LINE-EMPTY-BOX-REVIEW-01）を引継ぎ案として保存。所有23ファイル、設計§19の受入、禁止範囲、正式保存/実装依頼の開始条件を明記。`bash scripts/card-lint.sh docs/handoff/tcg-product-master-growth/card-empty-box-condition-review.md` exit 0（警告なし）、`git diff --check` exit 0、`bash scripts/check-task-state.sh` exit 0。製品実装・実DB/画面試験・PR提出・本番変更は未実施。旧25th商品カードは未発行のまま。


2026-09-13 正式保存準備: release/line-empty-box-design-handoffをorigin/main af269ae2起点に公式手順で作成。既存文書を保持して追記差分を統合。重複を避け今回の設計節は17〜19へ更新。参照サービス5件/レビュー画面のcacc889e→af269ae2差分0を確認。設計モデルの26+15固定対照を設計§19.7に掲載。カードは実行未許可の引継ぎ案、製品実装未着手。


2026-09-13 文書PR提出: https://github.com/shingo-ops/salesanchor/pull/3464 。初回HEAD ba68076c9b49ff96abeae104efe6b3a26afccab0、OPEN、文書6ファイルのみをGitHub APIで確認。ローカルdiff/task-state/両card-lint終了0、旧25thカードの長文警告3件。提出時CI進行中。未マージ、製品実装/本番変更なし。設計の正本参照は本PRの§19、旧作業台の§18は履歴として保持。

2026-09-13 PR3464検査修正: CIの参照実在検査で省略パスと非公開証拠名の混同を検出。リポジトリ内引用はルート相対フルパスへ修正、非公開ファイルは調査時のローカル保存名と明記。証拠内容や検査ロジックは変更しない。


2026-09-13 実装委任: POへ「空箱対応に限定して、別の実装担当へ実装・テスト・PR提出までを委任してよいか。マージ・本番反映は含めない」と明示確認し、PO原文「進める」を受領。CARD-LINE-EMPTY-BOX-REVIEW-01を発行。担当は委任先1名、製品所有23ファイル、追加委任禁止。停止条件はカード範囲外/設計矛盾/承認ゲート拒否、完了は実装・必要試験・PR提出まで。設計担当は製品を変更せず差分/検証を読み取り確認する。GO委任の有効化やPOの番号付きGOではない。設計参照は文書PR3464のHEAD54469a74 §19。


2026-09-13 空箱限定実装PR提出: https://github.com/shingo-ops/salesanchor/pull/3470 / HEAD3301b4f682ee8b56716e70929c1e2ae1f9e73c93 / OPEN / 所有22ファイルを親がGitHub API確認。画面6/6・Python3.12静的検査は担当報告、PG受入CIは進行中。親の読取指摘4件とカード本文例不足の補正を設計§19.8へ保存。実装中・未マージ・本番未変更。


## 2026-09-13 作品ID読取比較の実装検証

比較専用設計は未マージPR #3462、HEAD 2fc9e64755ebc69be31781d1b1a6332ccf9068f0 の design-keyword.md §17 / CARD-LINE-WORK-COMPARE-03 を参照。後続のPO「進める」を受け、origin/main dd1df11c 起点の専用机 release/line-work-id-comparison に新サービスと試験2ファイルを追加。既存製品コード変更0。本記録は設計PRのマージやGO委任有効化を意味しない。

実装は保存RAW・明細IDを固定し、2列の作品判断だけを受け付ける。保存商品結果と旧作品判断の対照不一致時はモデル呼出し0。READ ONLYの専用トランザクションを毎回閉じ、モデル前後の全入力/マスタSHA不一致で停止。訂正済みを除外し、候補は常にadoptable=false・正誤未検証。

ローカル make lint-ci 終了0、ruff成功、Bandit高重大度0。mypyは既存エラーを警告扱いにするMakefileのため完全な型検査成功とは称さない。Docker未稼働につきpytest未実行、合成データ・模擬モデル・隔離PostgreSQL試験はGitHub CIで検証する。実Gemini呼出し0、本番更新0、候補採用0、配信0。実装自己確認であり独立レビューではない。CI結果は実装PRで記録する。


### PR #3465 比較実装のCI結果

製品HEAD d8ff688f5f57d0ada396f0fa0fd76de1717d1399。Backend CI34735091935 / job103664991919: 2759 passed、95 skipped、失敗0、coverage63.26%、95.38秒。全表不変、READ ONLYによるDML拒否、API中transactionなし、RAW/マスタ/訂正/解析/リンク変更時停止、実analyzer内の候補集合との一致を合成データで検証。初回CI34734918033は2753成功/6失敗、共通原因は試験DBの正規化表未構築。既存migrationで試験環境を補完して解消、製品側の厳格な表存在検査は維持。

追加のローカル単独mypyは2.3.1内部エラーで終了2。型検査の完全成功とは称さない。実装自己レビューは比較カードの範囲で合格、独立レビューなし。gh pr checks実測で番号付きGO未受領のprocess-artifacts gateだけ失敗、他に失敗/実行中なし。PR #3465提出済み・未マージ、比較用の本番モデル実行/再解析/採用/配信は未実施。比較結果の正誤判定・安全な採用保存・配信設計はこの試験の合格対象外。


### 空箱限定実装・最終検証（2026-09-13）

実装PR https://github.com/shingo-ops/salesanchor/pull/3470 、HEAD8684707cdf7fe347cd14ec48b4d94c978dcc111f。親がGitHub APIでOPEN/所有22ファイル/最終HEADを確認。GitHubの実PG16を含む全pytestログ（run34736840990/job103669691099）を親が直接読み、2813 passed / 95 skipped / 失敗0、114.85秒、coverage64%を確認。空箱必須PG試験にはskip経路がなく、26分類SQL/Python一致・15確認状態・旧備考・競合/再送・不正JSON/JSONB・原文変更・商品/単位変更・E5非上書き・件数/配信・保存小数精度を検証。95skipを成功に数えない。

画面単体6/6とPython3.12静的検査は実装担当が実行し、親は画面ログの6 passedを読取確認。親自身が行ったのはPython判定26例の直接実行、製品差分の読取照合、GitHub検査/ログの直接確認であり、実PG/画面試験を親がローカル実行したとはしない。ブラウザ実機操作や本番実データ再解析は未実施。設計モデルの一致を総合解析正答率へ置き換えない。

初回CIは2803成功/2失敗/95skip。既存配信の解消済みunit_unresolved残存とactive表記検査を修正。中間928962a9は2812成功/失敗0/95skip。最後に実列NUMERIC(14,2)とbindingを揃え、数量2.345→2.35・価格10.125→10.13でも同内容再解析で確認保持となる1試験を追加し、最終2813成功を確認した。親指摘4件は修正と対応試験を確認済み。

設計担当の読取適合判定: APPROVE（委任範囲の実装/技術検証/PR提出まで）。独立した第二者レビューとは称しない。gh pr checks集約は42成功/2skip/1失敗、残るprocess-artifactsはrun34736874594/job103669756096で番号付きGO記録セクション不足を直接確認。これは技術試験失敗と区別するが、CI全緑・マージ可能な承認取得済みとはしない。一般の「進める」をGO #3470として代筆しない。

空箱カードの委任範囲は完了。実装PRは未マージ、本番反映・本番DB変更・再解析・3シート配信は未実施。GO委任有効化は本作業に含まない。25th商品辞書の別カードは未発行のまま。本記録はマージや本番操作の承認を求めたり代行したりするものではない。


2026-09-13 13:45 JST記録: PO原文「GO #3470」を受領。直前の説明に沿い、既存実装担当へ本番安全確認後のPR3470マージ・自動本番反映の結果確認を委任。CARD-LINE-EMPTY-BOX-RELEASE-01発行。現HEAD8684707c、技術CI42成功/2skip、GOゲートのみ不足。安全確認/バックアップは現時点未実施で、完了後にのみGO記録のバックアップ欄へ実測を転記する。再解析/配信/PR3464マージは対象外。GO委任モードの自己有効化ではなく、PO本人の個別番号付きGO。


### 空箱限定リリース完了（2026-09-13 14:03 JST確認）

PO原文「GO #3470」に基づき、既存の委任実装担当がCARD-LINE-EMPTY-BOX-RELEASE-01を実行。PR https://github.com/shingo-ops/salesanchor/pull/3470 は13:57:35 JSTにMERGED、merge SHA56a1661d03a583be53fc74507c7d428faa2f0b18。直前HEAD8684707c、所有22ファイル、最新検査43成功/2skip/失敗0、GOゲート成功。DB未完抽出/解析0、Celery active/reserved/scheduled各空を確認して公式merge wrapperを実行（exit0）。

13:55:10 JSTにconditions/analysis_results/item_correctionsの3表を読取pg_dumpでバックアップ。2096257 bytes、SHA256 d0a2cd3b4b395882dc11bac40429e9bacf684a284b317b9b62d0567876446592、pg_restore --list終了0/TABLE DATA3件。初回のSSH読取とローカルheredoc併記はフックがSQL実行前に拒否。カードを同一権限のSELECT単独コマンドへ補正し成功、ガード解除や回避はしていない。

自動配備 https://github.com/shingo-ops/salesanchor/actions/runs/34739114060 は上記merge SHAでsuccess。14:02:22 JSTに空箱migration（230/230）適用。14:03:19 JSTの本番SELECTはread_only=on、CN0011/Empty boxが設計どおり有効1件、既存10状態の全列一致。解析結果28994件/訂正17件で前後件数同一。API healthとappはHTTP200、DB/Redis/Celery connected、実配備HEADもmerge SHAと一致。

親はGitHub APIからMERGED/配備成功を直接確認し、担当の保存した前後DB JSONをPythonで直接対照して既存10行一致/追加CN0011のみを確認。HTTP/配備版/バックアップの保存ログも読取確認。SSH・本番照会・バックアップ・マージを実行したのは委任担当であり、親自身の本番操作や独立第二者レビューとはしない。証跡/バックアップは非公開ローカル保存先 private-research/emptybox-release-3470-20260913 に保管（Gitへ生データを含めない）。

設計合格・個別PO GO受領・実装・マージ・本番反映・読取確認は完了。人の確認保存の本番実機操作、再解析、3シート配信は未実施。総合解析正答率の再測定ではない。25th商品辞書カードは未発行、文書PR #3464は未マージ、GO委任モードは有効化していない。


### 25thカード再審査（2026-09-13 14:17 JST以降）

origin/main56a1661d・設計PR #3464 OPEN/e9fb8b6d・製品PR #3470 MERGEDを直接確認。preflight成功、本店は185遅れ/台帳以外の未保存30件を保持し専用文書作業台を使用。該当25th runbookは検索で見当たらず既存todo行を更新。

保存マスタ10:32 JST/有効293商品とGemini67明細（SIG66）を最新照合8関数で再測定。旧関数AST8/8一致、商品特定59→60、変更2（略称回復1/セット訂正1）、固定15例15/15。work_id=Noneの局所比較であり現在本番全経路や総合正答率を表さない。

追加人工入力のセット否定がセットへ誤確定。設計提案の否定4語を新セットの除外へ仮追加すると12/12未特定、既存15/15と実67行に追加差分0。設計§17改訂3と未発行カードを更新し、商品1/検索3/除外10の案へ訂正。否定4語はPO合意済みとしない。PM0073のサプライ表記は本便未対処として記載。新しい商品/辞書版では旧v4再解析が拒否される現行契約も実物で確認し受入へ追加。

自己審査REVISE（同一AI）。最新マスタ再照合と否定4語案の方針確認が残る。製品実装/本番接続/DB更新/追加Gemini/再解析/配信0、追加実装委任0。証拠は非公開ローカル保存名 private-research/25th-recheck-20260913 のcheck.py/result-private.json/check-negation-draft.py/negation-draft-result.jsonとmanifest.json。入力SHA5e165443af0812b5f2c45c8b82e2c7682514bfd1cffdbcbbd005821174961693、マスタSHA9373400c7036275dcd32bbbf63ff92d14bb1d5cf35c205b0fec921ec46a1ed63。
