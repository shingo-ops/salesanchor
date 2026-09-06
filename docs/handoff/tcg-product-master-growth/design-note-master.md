# design — 備考マスタ（tcg_note_master）拡張

この文書は何か（専門用語なしの1行）: 商品の補足メモ（発送日・仕入元・跡など）を、配信の Note_JA 欄に日本語と英語の決まった札で出せるように、備考の辞書を増やし、日付など変わる値も拾えるようにする設計。

親（設計仕様書）へのリンク: ../../specs/product-master/README.md
recon（照合ロジック側）: docs/handoff/tcg-product-master-growth/recon.md
対象ADR: ADR-154（docs/adr/ADR-154-tcg-parity02-gas-python-migration.md）

- 仕事名: tcg-product-master-growth（子テーマ: note-master）
- 日付: 2026-09-06
- 区分（STANDARD-WORKFLOW 1.8）: 既存の延長・修正
- 実測の出所: 実装役の読み取り専用カード CM-NOTE-RECON-01 / 02 / 03（2026-09-06、origin/main f156bccf7cfb06c46b54da3246a954edaba0340b、tenant_004 を transaction_read_only=on で SELECT のみ）。生出力は /tmp/CC報告ファイル/ に保管しリポジトリには入れない。

---

## 1. あるべき姿（PO自筆・2026-09-06）

まずマスタを充実させて取りこぼしのないように全て登録、登録後に検索ワードと除外ワードを適切に配置する。検索ワードは該当する可能性のある候補をキャッチするための網、除外ワードは誤った解析結果を出さないための壁として作成する。商品マスタの設計と同じ仕様を想定する。MM/DD発送のメモは常に日付が変わり続けるので日付が変化しても取得できるようにしたい。今後日本語と英語対応させたいので正規表現化させたい。

## 2. 現在地（recon・file:line）

- backend/app/services/tcg_analyzer_svc.py:730 load_note_master が tenant_004.tcg_note_master（enabled=TRUE、priority ASC, id ASC）を読む。
- backend/app/services/tcg_analyzer_svc.py:757 build_note_ja(raw_memo, note_entries) は match_keyword（同:277）で search_keywords / exclude_keywords を照合し、当たった label_ja をカンマ連結して返す。1札も当たらなければ None。
- backend/app/services/tcg_analyzer_svc.py:921 照合に渡るのは raw_memo を NOTE 正規化した norm_memo。raw_state は渡らない。
- backend/app/services/tcg_analyzer_svc.py:961-967 needs_review の理由は pid_unresolved / multi_candidate のみ。備考の未ヒットは理由に含まれない。
- backend/app/services/tcg_distribution_svc.py:218 配信は COALESCE(ar.note_ja, '') をそのまま Note_JA 列に出す。
- backend/app/services/tcg_analyzer_svc.py:766-800 付近の load_status_master は match_type（LITERAL / REGEX / DEFAULT）と search_pattern を持つ。正規表現の先例。
- tenant_004.tcg_note_master: 22行（NJ001〜NJ022）、8分類（検品／プロモ／版情報／ダメージ／分布／外装／バルク／付属品）。「発送」を含む検索語は0件。
- tenant_004 実測（2026-09-06）: raw_memo 非空の解析済み行 982、うち note_ja 空 761（77.5%）。raw_memo 異なり値 171、うち日付を含むもの 71行20種、「発送」を含むもの 427行。raw_state 異なり値 93。
- 過去の LINE ログ（2025-04〜2026-09、約106万行）の語頻度: 発売日前日発送 3,515行、N日前発送 1,091行、買取品 9,520行、問屋 8,785行、ラベル跡 5,274行、伝票跡 3,559行、未サーチ 1,580行、サーチ済 1,721行（DB の171種には無い語が多数）。

## 3. KGI（○×で測る）

| # | 合格条件 | 測り方 | 合格ライン |
|---|---|---|---|
| ① | 拡張後の tcg_note_master 行数 | SELECT count(*) | 56/56（NJ001〜NJ056） |
| ② | raw_memo 非空かつ note_ja 空の行の割合 | 再解析後の SELECT | 20% 以下（実測 77.5% → 20% 以下） |
| ③ | 日付入りメモ（71行）で日付を含む札が付く行 | 再解析後の SELECT | 60/71 以上 |
| ④ | 全札に label_en が在る | SELECT count(*) WHERE label_en 空 | 0 |
| ⑤ | 反対語の同時付与（例: 未サーチ と サーチ済の可能性）が同一行に出ない | 再解析後の SELECT | 0行 |

## 4. 設計（技術How）

### 4-1. 二段構成
- B1（先行）: build_note_ja の末尾に norm_memo を「札,札 | 原文」の形で併記する。札が0件でも原文は出す。既存の札利用者は「|」より前だけを読む。
- B2（第2段）: tcg_note_master に match_type（LITERAL / REGEX、既定 LITERAL）と label_template_ja / label_template_en を追加し、REGEX 行は search_keywords を正規表現として評価、捕捉グループを {1}{2}… でテンプレートに埋めて札を生成する。exclude_keywords は従来どおり含有一致で壁として先に評価する。
- 実行順序は GAS Phase 3 の順序（正規化→照合→E3a→E5→E3b→E4）を変えない。C-7（注記生成）の内部でのみ処理を足す（ADR-154:28 の制約下）。

### 4-2. 固定札の追加（B1で有効・NJ023〜NJ056）

| id | label_ja | label_en | search_keywords（網） | exclude_keywords（壁） | category |
|---|---|---|---|---|---|
| NJ023 | 発売日発送 | Ships on release day | 発売日発送,発売日当日発送,当日発送,発売日出荷 | 前日,翌日 | 発送時期系 |
| NJ024 | 発売日前日発送 | Ships day before release | 発売日前日,前日発送 | | 発送時期系 |
| NJ025 | 発売日翌日発送 | Ships day after release | 発売日翌日,翌日発送 | 受注の翌日 | 発送時期系 |
| NJ026 | 即日発送可 | Same-day shipping | 即日発送,即日出荷,当日出荷,受注の翌日 | | 発送時期系 |
| NJ027 | 入荷次第発送 | Ships upon arrival | 入荷次第,届き次第,到着次第,入荷後発送 | | 発送時期系 |
| NJ028 | 発送日要相談 | Ship date negotiable | 発送日要相談,発送日相談,発送日（要相談）,発送日(要相談),発送日要相,発送日確認 | | 発送時期系 |
| NJ029 | 国内発送のみ | Domestic shipping only | 国内発送のみ,国内のみ,国内限定 | | 発送時期系 |
| NJ030 | （正規表現・4-3 P1） | | | までに | 発送日付系 |
| NJ031 | （正規表現・4-3 P2） | | | | 発送日付系 |
| NJ032 | （正規表現・4-3 P3） | | | | 発送日付系 |
| NJ033 | （正規表現・4-3 P4） | | | | 発送日付系 |
| NJ034 | （正規表現・4-3 P5） | | | | 発送日付系 |
| NJ035 | 買取品 | Buyback stock | 買取品,買取含,自社買取,買取(当グループ含) | | 仕入元系 |
| NJ036 | 問屋品 | Wholesale stock | 問屋 | | 仕入元系 |
| NJ037 | 店舗品 | Retail-sourced | 店舗仕入,店舗購入,ポケセン,カドショ | | 仕入元系 |
| NJ038 | 正規流通品 | Official distribution | 正規流通,正規品 | | 仕入元系 |
| NJ039 | サーチ済の可能性 | Possibly searched | サーチ済,サーチの可能性,サーチ痕,サーチ跡 | サーチ痕無,サーチ痕なし,サーチ跡無,未サーチ | サーチ系 |
| NJ040 | 未サーチ | Unsearched | 未サーチ,サーチ痕無,サーチ痕なし,サーチ跡無,サーチなし | | サーチ系 |
| NJ041 | 伝票跡 | Shipping label marks | 伝票跡,伝票痕,伝票剥がし跡 | | 跡痕系 |
| NJ042 | テープ跡 | Tape marks | テープ跡,テープ痕,連結跡,連結痕,テープ連結 | テープカット | 跡痕系 |
| NJ043 | ラベル跡 | Label marks | ラベル跡,ラベル痕 | | 跡痕系 |
| NJ044 | シリアル切り取り | Serial cut out | シリアル切り取り,シリアルナンバー切り取り,シリアル切取 | シリアルのみ | 跡痕系 |
| NJ045 | カートン数字記載 | Numbers written on carton | 数字の記載,数字記載 | | 跡痕系 |
| NJ046 | 段ボール傷 | Outer carton damage | 段ボール傷,段ボールダメージ,段ボール凹 | | ダメージ系 |
| NJ047 | B品 | B-grade | B品,Ｂ品 | | ダメージ系 |
| NJ048 | 上部切り取り | Top panel cut | 上部切り取り,切り取り部分 | | ダメージ系 |
| NJ049 | 美品 | Mint condition | 美品 | | 外装系 |
| NJ050 | カートン発送可 | Carton shipping available | カートン可,カートン発送可,マスターカートン発送可,カートン発送可能 | | 荷姿系 |
| NJ051 | （正規表現・4-3 P6） | | | | 荷姿系 |
| NJ052 | （正規表現・4-3 P7） | | | | 荷姿系 |
| NJ053 | （正規表現・4-3 P8） | | | | 荷姿系 |
| NJ054 | 大口割引可 | Bulk discount available | 大口,値引,値下げ,お値段交渉,交渉可 | | 取引条件系 |
| NJ055 | 写真掲載可 | Photos may be posted | 写真掲載可,画像掲載可,写真掲載可能 | | 取引条件系 |
| NJ056 | SNS投稿不可 | No social media posting | SNSへの投稿不可,SNS投稿不可 | | 取引条件系 |

既存札への追記: NJ004 再販品 の search_keywords に 第二版,2版,２版 を追加。NJ014 箱痛み の search_keywords に 箱傷み を追加。見送り: 「通常版」は初版と同義でないため NJ005 に追記しない。

### 4-3. 正規表現テンプレート札（B2で有効）

search_keywords に正規表現を1本だけ置き、label_template_ja / label_template_en の {1}{2}{3}{4} に捕捉を埋める。数字は全角を半角に正規化してから照合する。

```
P1 NJ030  ([0-9０-９]{1,2})[/／]([0-9０-９]{1,2})(\([月火水木金土日]\)|（[月火水木金土日]）)?発送
          ja: {1}/{2}発送            en: Ships {1}/{2}
P2 NJ031  ([0-9０-９]{1,2})[/／月]([0-9０-９]{1,2})日?までに発送
          ja: {1}/{2}までに発送      en: Ships by {1}/{2}
P3 NJ032  ([0-9０-９]{1,2})[/／]([0-9０-９]{1,2})[〜~-]([0-9０-９]{1,2})[/／]([0-9０-９]{1,2})発送
          ja: {1}/{2}〜{3}/{4}発送   en: Ships {1}/{2}-{3}/{4}
P4 NJ033  発売日([0-9０-９]+)日前
          ja: 発売日{1}日前発送      en: Ships {1} days before release
P5 NJ034  到着後([0-9０-９]+)日以内
          ja: 到着後{1}日以内発送    en: Ships within {1} days of arrival
P6 NJ051  1?カートン([0-9０-９]+)(個|BOX|箱)入
          ja: 1カートン{1}{2}入      en: {1} per carton
P7 NJ052  ([0-9０-９]+)(個|BOX|箱|パック|P|ｐ)単位
          ja: {1}{2}単位             en: Units of {1}
P8 NJ053  ([0-9０-９]+)で括り
          ja: {1}で括り              en: Bundled by {1}
```

### 4-4. 触らない範囲
- 商品照合（match_pid_name_first）、単位・状態の解決（E3a/E5/E3b/E4）、配信の列構成、needs_review の判定条件（別決定・§7）。
- raw_state は本設計では備考照合に渡さない（別決定・§7）。

## 5. 弊害・トレードオフ
- B1 で Note_JA が長くなり、原文がそのまま出るため表記ゆれが並ぶ。B2 が入るまでの暫定。
- NJ036「問屋」は1語の広い網。メモ欄限定のため許容するが、商品名に「問屋」を含む商品が出たら壁を足す。
- 既存 NJ010 の網「破損」は投稿末尾の定型文（補償に関する文）に当たる。Gemini が定型文を raw_memo に入れた事例は未確認。入れば壁を足す。
- NJ026 に「受注の翌日」を網として置き、NJ025 の壁にも置く。同じ語が網と壁に跨る唯一の箇所。
- 投稿全体の条件（適格請求書・着払い・送料無料・海外発送代行・発送元地域）は商品の備考ではないため本マスタの対象外。供給者条件として別テーマで持つ。
- 「完売」「〆」「在庫500」「商品名の断片」がメモ欄に混入している（DB実測）。これらは Status／数量／抽出プロンプトの課題であり、備考マスタで拾わない。

## 6. 外部・過去事例
- 同リポジトリ内の先例: tcg_status_master の match_type=REGEX/LITERAL（backend/app/services/tcg_analyzer_svc.py load_status_master）。B2 の列設計はこれに揃える。
- GAS 側の buildNoteJA_ / _NOTE_MASTER_ROWS_ の実挙動は未観測（PO判断で見ずに進めた・2026-09-06）。

## 7. 未決定（次の決定として諮る・現場で決めない）
1. raw_memo 非空かつ札0件を needs_review の理由に加えるか（加えると実測 761 行が一斉に人待ちになるため、マスタ投入後に判断）。
2. raw_state を備考照合にも渡すか。
3. B1 の区切り文字「 | 」を採用するか。

## 8. 受入基準

| 基準 | 検証方法 |
|---|---|
| tcg_note_master が 56 行 | SELECT count(*) FROM tenant_004.tcg_note_master → 56 |
| NJ023〜NJ056 の label_en が全行非空 | SELECT count(*) WHERE id BETWEEN 'NJ023' AND 'NJ056' AND length(label_en) BETWEEN 1 AND 200 → 34 |
| 「発売日前日発送」を含む raw_memo に NJ024 が付き NJ023 が付かない | backend/tests に固定文字列ケースを追加し pytest 緑 |
| 「9/18(金)発送」に P1 が当たり「9/18発送」が生成される | 同上 |
| 「9月27までに発送」に P2 が当たり P1 が当たらない | 同上 |
| 「未サーチ」に NJ040 が付き NJ039 が付かない | 同上 |
| 既存22札の既存テストが緑のまま | pytest backend/tests/test_tcg_keyword_matching.py 緑 |

## 9. 維持の仕組み
- 守り手: backend/tests/test_tcg_keyword_matching.py（備考照合のケースを同ファイルに追加する）
- 対象: 網と壁の組（NJ023/NJ024、NJ039/NJ040、P1/P2）が崩れないこと、正規表現テンプレートの捕捉が壊れないこと
- 関所なしの箇所（人手で守る）: マスタの行追加そのものの品質（2札以上に当たる語・3文字以下の語）を止める機械は無い。理由: 商品マスタ側（recon.md §5）と同じ状態で、機械化は別テーマ。

## 10. 接触面分析
- ①人: 配信シートを読む担当（Note_JA が長くなる）。
- ②エージェント: 実装役はマスタ投入を migration で行う（本番直INSERT禁止）。設計パートナーは本文書を正とする。
- ③機械: pytest（守り手）、process-artifacts gate（本文書の書式）。CI は DB を持たないため migration の実行は本番が初回になる（GUARD-02/03 未完のまま）。
- ④データ: tenant_004.tcg_note_master に 34 行追加＋2行更新（migration）。analysis_results は再解析で全行 note_ja が書き換わる（書き込みは別セッションの担当）。
- ⑤本番: 再解析の実行タイミングを配信の直前に置かない。
- ⑥外部: 配信先スプレッドシートの Note_JA 列の見た目が変わる。
