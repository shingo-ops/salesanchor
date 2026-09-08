# recon — tcg-keyword-quality（検索語・除外語の品質検査）

**仕事名**: tcg-keyword-quality  
**日付**: 2026-09-06  
**対象ADR**: ADR-154  
**担当**: architect（設計パートナー）  
**親（設計仕様書）**: docs/specs/product-master/README.md  
**関連**: docs/specs/product-master/dev-plans/precision-benchmark.md

> この文書は何か（専門用語なしの1行）:
> 商品を見つけるための「検索語」と、紛らわしい商品を弾くための「除外語」が、いまどんな状態にあるかを本番DBの読み取りだけで数えた記録。

実測時の origin/main SHA: DB件数は f156bccf（2026-09-06）、R5 再測は a9847358（2026-09-06・代替SQL）、file:line は f70daf7f（2026-09-07・7関数の def 行を grep で実在確認。同ファイル 1132 行）  
出所: CARD-KW-RECON-01 / 02 / 03（読み取り専用。01/02 は transaction_read_only=on 実測。03 の DB 手順は旧版 a9847358 で同日 on を確認）  
書き込みは一切行っていない。

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/services/tcg_analyzer_svc.py:156` | `load_product_keywords`: is_active=TRUE の商品のみ・position 順で検索語/除外語を {商品コード: [語]} に読む |
| `backend/app/services/tcg_analyzer_svc.py:220` | `normalize_en`: 全角英数記号→半角、小文字化 |
| `backend/app/services/tcg_analyzer_svc.py:238` | `token_and_match`: 空白分割・全トークンが**部分一致**すれば当たる（順不同AND） |
| `backend/app/services/tcg_analyzer_svc.py:256` | `match_one_kw`: 英数字のみの語は単語境界 `(?<![a-z])語(?![a-z])`、それ以外は token_and_match |
| `backend/app/services/tcg_analyzer_svc.py:276` | `match_keyword`: **除外語が先**に評価され、1語でも当たれば候補から外す。検索語が空なら候補にならない |
| `backend/app/services/tcg_analyzer_svc.py:346` | `match_pid_name_first`: 候補2つ以上は最長語の商品を仮の答えにするが `resolved=False`（要確認）。解決はしない |
| `backend/app/services/tcg_analyzer_svc.py:850` | `analyze_extraction_job`: 判定に渡すのは raw_product_name（正規化後）のみ |

## 表の構造（DB実測）

| 表 | 列 | 制約 |
|---|---|---|
| `tenant_004.product_search_keywords` | id, product_id, keyword, position | UNIQUE(product_id, keyword)、FK → tcg_products(id) ON DELETE CASCADE |
| `tenant_004.product_exclude_keywords` | 同上 | 同上 |

## 件数（DB実測・2026-09-06）

| 項目 | 値 |
|---|---|
| 商品 | 296（is_active=FALSE 2件を含む） |
| 検索語 / 除外語 | 630 / 134 |
| 検索語を持つ商品 | 295 |
| 検索語1つだけの商品 | 140 |
| 除外語を持つ商品 | 63（有効商品294のうち231が除外語0件） |
| 空白を含む検索語 | 259（うち日本語混じり 163） |

語の長さ分布（検索語）: 1文字=1、2文字=15、3文字=7、4文字=63、5文字=67、以降減少、最長39。

## 規則候補ごとの該当（DB実測・値つき）

### R1 検索語0件の有効商品 — 1件
PM0146（is_active=t）

### R2 3文字以下の検索語 — 23件
- 1文字（日本語）: `枕`（PM0201）
- 2文字（日本語）12件: `仰天` `双璧` `白銀` `漆黒` `蒼空` `摩天` `切手` `白熱` `黒炎` `楽園` `超電` `熱風`
- 3文字（日本語・中国語）5件: `闘う虹` `ソード` `小火龙` `杰尼龟` `レトロ`
- 英数字 5件: `AR`×3（PM0007/0008/0009）、`151`（PM0104）、`OSK`（PM0230）

### R3 同じ語が複数の商品に登録 — 1語
`AR` → PM0007, PM0008, PM0009

### R4 除外語が自商品の検索語に当たる（自滅）— 8組・5商品
| 商品 | 除外語 | 殺される検索語 |
|---|---|---|
| PM0003 | `RR バルク` | `RRR バルク` |
| PM0063 | `イーブイヒーローズ` | `イーブイヒーローズ イーブイズセット` / `イーブイヒーローズイーブイズセット` |
| PM0072 | `25th Anniversary Collection` | `25th Anniversary Collection プロモ` / `〜 プロモパック` |
| PM0159 | `熱風のアリーナ` | `熱風のアリーナ プロモ` |
| PM0172 | `THE BEST` | `ONE PIECE CARD THE BEST vol.2` / `THE BEST vol.2  PRB-02` |

8組を上の照合規則（:256 / :276）で追跡した結果、**すべて実際に自滅する**（英数字の除外語も、後続が空白・カタカナのため単語境界を通過する）。

### R5 別商品の語に相乗りする語（除外語で守られていないもの）— 68組（コード準拠の近似・2026-09-06）
- 第1測（`position()` 部分一致のみ）: 152組。英数字語を単語境界で見ないため過大。
- 第2測（CARD-KW-RECON-03 旧版・SHA a9847358）: 英数字語は前後1文字が `[a-z]` でないことを `substring()` で検査（コードの `(?<![a-z])語(?![a-z])` と同値）、日本語混じりは部分一致 → **68組**。差の84組は単語境界で除かれた（`card` `rare` 等の内部の `ar`）。
- 内訳（Aの語 → 相乗りする商品数）: `ar`(PM0007/0008/0009・各4商品) `vmax`(PM0074・4) `vol.1`(PM0230・3) `クレイバースト`(PM0098・1) `シールド`(PM0048・1) `スノーハザード`(PM0097・1) `ソード`(PM0047・1) `ビクティニ`(PM0231・1) `双璧`(PM0059・1)
- 近似の限界: 空白を含む日本語語の AND 分解は部分一致で代用（過大側）。厳密値は design の検査コード（既存関数を呼ぶ）で出す。
- 測定上の記録: 先読み・後読み `(?<!` を含む SQL は、ローカルの psql-write-guard が `<` を書き込みと誤検知して止めた（既知の落とし穴）。`substring()` 版で回避した。

### R6 正規化後に同一商品内で重複 — 1組
PM0069: `切手Box` / `切手BOX`

### R7 空白を含む日本語混じりの語 — 163語
AND 分解される（:238）。個別の値は本 recon では出していない。

## 現行の検査機械
無い（docs/handoff/tcg-product-master-growth/recon.md §5 と一致）。R1〜R7 のいずれも、登録時に止める仕組みが存在しない。

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | R5 の英数字語を、コードと同じ単語境界で数えた件数 | CARD-KW-RECON-03（旧版）代替SQL で再測 → 68組 | ✅ 解消済み（近似の限界は上記 R5 に明記） |
| 2 | CI の「マイグレーションSQL 実行テスト（実DB）」が scripts/run_all_migrations.sh を全件流しているか | `.github/workflows/migration-test.yml` の実読（CARD-KW-RECON-03） | ✅ 解消済み: ジョブ `migration-full-dryrun`（同ファイル 687 行〜）が全件を run_all_migrations.sh の順で実行する。ただし **migrations に変更がある PR でのみ**起動し、変更が無い PR では skipping（集約ジョブは skipping を pass 扱い） |
| 3 | キーワード検査は GAS に無い新規機能。ADR の要否 | PO 判断 | 未解消（実装便の前に PO へ確認。本 recon/design の文書 PR には影響しない） |

**未解決ゼロ確認**: 不明点#1・#2 は解消。#3 は PO 判断待ち（実装は不明ゼロが条件。文書 PR は進める）。

## CI の migration ジョブ（実読・f70daf7f）

| ジョブ | 行 | 何をするか | 起動条件 |
|---|---|---|---|
| `detect-changes` | 30 | migrations 関連の変更有無を判定 | 常時 |
| `migration-registration-exists` | 51 | run_all_migrations.sh の登録先ファイルの実在を全件点検 | migrations 変更あり |
| `migration-test-run` | 86 | **PR で変更された SQL のみ**を1回＋冪等性で実行 | migrations 変更あり |
| `migration-full-dryrun` | 687 | **全件**を run_all_migrations.sh の順で実行 | migrations 変更あり |
| `migration-test` | 1368 | 集約（skipping を pass 扱い） | 常時 |

run_all_migrations.sh: `run_sql` 188本・最終登録 `20260906_120000_create_tcg_tables_t001.sql`。

---

## 補足

- 語の値は PO 承認（2026-09-06・A案）のもとで記載。商品名・仕入元名・原文は含めていない。
- 検索語・商品の件数は 2026-09-04 実測（593 / 268）から増えている。計画書 precision-benchmark.md §1 の値は古い。
