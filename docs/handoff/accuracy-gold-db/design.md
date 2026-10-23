# 答え合わせ表（正解表）を本番 DB に置き、クラウドは窓口から読む: 設計

状態: 設計案作成済み・自己審査済み（Opus、2026-10-23）。方針は PO 決定、方式は Opus（PO の委任に基づく）。
方針の根拠（PO 2026-10-23 チャット「1」）: 選択肢1「本番のデータの中に答え合わせ表を新しく作り、クラウドは『読むだけの窓口』から読む…作業は私が設計して進めます」。
関連: ADR-1043（この設計の決定）、`docs/handoff/accuracy-gold-db/recon.md`、ADR-1042、ADR-1024、ADR-1007、ADR-1037。

## 1. 目的
クラウドの AI が、手元の Mac にしかない正解表（`gold_v1.tsv`）を使って正答率を測れるようにする。正解表の正本は 1 か所（本番 DB）にし、社外秘の値を公開リポジトリ・PR に載せない。

利用者に見える変化: クラウドの AI が `python3 scripts/accuracy/fetch_gold.py --version gold_v1 --out <ファイル>` を実行すると、手元のファイルと同じ正解表が手に入り、`score_v102.py --gold` にそのまま渡せる。

## 2. 対象と対象外
- 対象: 表 2 つの migration、TSV→投入 SQL の作成道具、窓口から取り出す道具、その試験、手順書、本番への投入（gold_v1 の 1 版）。
- 対象外: score_v102.py の変更（変えない）、システム結果の写し（スナップショット）をクラウドで作る話、正解表の作り方（判定・裁定）の変更、窓口（ADR-1042）の変更。

## 3. 方式
### 3-1. 表（migration `migrations/20261023_180000_create_accuracy_gold.sql`）
- `public.accuracy_gold_versions`: 1 行 = 正解表の 1 版。
  - `id SERIAL PRIMARY KEY`、`gold_version TEXT NOT NULL UNIQUE`（`^[a-z0-9_]+$`）、`file_sha256 TEXT NOT NULL`（`^[0-9a-f]{64}$`）、`row_count INTEGER NOT NULL`、`post_count INTEGER NOT NULL`、`note TEXT NOT NULL DEFAULT ''`、`created_at TIMESTAMPTZ NOT NULL DEFAULT now()`。
  - 列名に hash を使わない（ai_ro の拒否語。recon §3）。
- `public.accuracy_gold_rows`: 1 行 = 正解表の 1 行。
  - `id SERIAL PRIMARY KEY`、`gold_version TEXT NOT NULL REFERENCES public.accuracy_gold_versions(gold_version) ON DELETE CASCADE`、`row_no INTEGER NOT NULL CHECK (row_no > 0)`（ファイルの何行目のデータか。1 始まり）、`post_id UUID NOT NULL`、
    以下すべて `TEXT NOT NULL DEFAULT ''`: `price_line`・`lines`・`allowed_lines`（許容する行）・`e2_price`・`e3_quantity`・`a1_product_id`・`a2_condition`・`a3_unit`・`a4_status`・`a5_ship`・`a4_basis`（A4根拠）・`hesitation`（迷い）・`exclusion`（除外）・`ruling_basis`（裁定根拠）・`po_check`（PO確認）、`created_at`。
  - `UNIQUE (gold_version, row_no)`。`(投稿id, price_line)` は一意でないので鍵にしない（recon §1）。索引 `(gold_version, post_id)`。
  - source_messages・products へは FK を張らない。既存表にロックを取らないため（ADR-1037）と、投稿や商品が消えても正解表は当時の記録として残すため。存在の確認は投入時の点検で行う（3-3）。
- 16 列すべてを入れる。採点が使うのは 12 列だが、一部だけ入れると残り 4 列の正本が Mac に残り、2 か所に分かれるため。DB にはもともと仕入元の投稿本文（社外秘）があり、置き場として格が変わらない。
- RLS: 両表とも ENABLE＋FORCE。方針は読みも書きも `current_setting('app.is_operator', true) = 'true'` のときだけ。アプリの通常の接続からは 0 行。ai_ro のビューは持ち主が superuser なので読める（recon §3）。
- 値は migration に書かない（ADR-1007）。冪等（IF NOT EXISTS・DROP POLICY IF EXISTS）。先頭にロールバックのコメント。
- `scripts/run_all_migrations.sh` の :1132 の後に 1 行登録。ai_ro は次のデプロイで自動的に 2 つのビューを作る（追加作業なし）。

### 3-2. 投入 SQL を作る道具 `scripts/accuracy/gold_to_sql.py`（中身を含まない）
- 入力 `--gold <tsv> --version gold_v1 --note <文> --out-dir <リポジトリ外のフォルダ>`。標準ライブラリのみ。
- 点検（どれか外れたら何も書かずに止まる）: 見出しが 16 列で順番どおり／全行 16 列／値に タブ・LF・CR・`\`・`"` が無い／投稿id が小文字 uuid（`str(uuid.UUID(v)) == v`）／`--version` が `^[a-z0-9_]+$`／`--out-dir` がリポジトリの中でない。
- 出力 3 本（前例 bin2 の型）。戻し用のファイルは道具では作らない（2026-10-23 Opus 変更: 消す文を道具のソースに持たせると、不可逆操作の見張りがそのソースを扱う全コマンドを止めるため。戻し方の正本は §7 の 1 か所）:
  - 01_precheck.sql: 表 2 つがあること、その版がまだ無いこと、投稿id 100 種が source_messages に全部あること（無い数を表示。0 でなければ止める）、a1_product_id の数字が products に全部あること（同）。
  - 02_apply.sql: `\set ON_ERROR_STOP on`、`-v end` の指定がなければ止める、`BEGIN`、`SET LOCAL app.is_operator = 'true'`、versions に 1 行、rows に 1494 行（文字列は `'` を `''` にするだけ。base64 などの符号化はしない）、件数が row_count と違えば `SELECT 1 / 0`、`:end`。
  - 03_verify.sql: 版の行数・投稿数・row_no が 1〜N の連番であること。
- 置き場: `~/CC報告ファイル-keep/accuracy-gold-20261020/db-load/gold_v1/`（社外秘の正本の隣。リポジトリに入れない）。

### 3-3. 本番への投入（Opus）
- 順: PR マージ → デプロイで migration 適用 → K1 → 01 → 02（ROLLBACK で試す）→ 02（COMMIT）→ 03 → K2〜K4。
- 道: 前例と同じく manual-only 鍵で psql に `-f` 相当（標準入力）で流す。担当（Sonnet）は流さない。

### 3-4. 取り出す道具 `scripts/accuracy/fetch_gold.py`
- 入力 `--version gold_v1 --out <ファイル> [--url <窓口>]`。既定の窓口は `https://api.salesanchor.jp/api/v1/ops/read-window/query`。標準ライブラリ（urllib）のみ。
- 鍵: クラウドでは network secret が自動でヘッダを付けるので、道具は鍵を扱わない。手元で試すときだけ、環境変数 `READ_WINDOW_TOKEN` があればヘッダ `X-Read-Window-Token` に付ける。鍵の値は表示しない。
- 1 回目の問い合わせ: `ai_ro.public__accuracy_gold_versions` から file_sha256・row_count。
- 2 回目: 先頭行 `-- limit=5000`、`select post_id::text as "投稿id", price_line as "price_line", … , po_check as "PO確認" from ai_ro.public__accuracy_gold_rows where gold_version = '<版>' order by row_no`。
- 応答が HTTP 200 かつ `X-Read-Window-Rc: 0` でなければ止まる。本文の sha256 と行数が 1 回目と一致しなければ、ファイルを書かずに止まる（終了コード 1）。一致したら書いて、sha256 と行数を表示する。
- 文の中に窓口の拒否語（insert 等）が入らないことを試験で確かめる。

### 3-5. 手順書
- `scripts/accuracy/README.md` に「クラウドで測る」節: fetch_gold → score_v102 の 2 行と、止まったときの読み方。

## 4. 変更前後
| | 変更前 | 変更後 |
|---|---|---|
| 正解表の正本 | Mac の gold_v1.tsv | 本番 DB の 2 表（Mac のファイルは投入元の記録として残す。新しい版は DB に入れてから使う） |
| クラウドで採点 | できない（正解表が無い） | fetch_gold → score_v102 |
| 手元で採点 | ファイルを --gold に渡す | 同じ（変わらない） |

## 5. 代替案
- Google Drive に置いてコネクタで読む: Mac と Drive の 2 か所に分かれる。読むたびに 0.29MB が AI の文脈を通る。不採用（PO 2026-10-23「1」で A を選択）。
- 非公開の別リポジトリ: クラウドではリポジトリが 2 つになると見張り（hooks）が読まれなくなる（stage34 調査記録）。不採用。
- 採点の 12 列だけ入れる: 正本が 2 か所に分かれる。不採用（3-1）。
- score_v102.py に DB 読みを足す: 採点が DB と窓口に依存し、手元のファイル採点と道が分かれる。道具を分け、採点は変えない。

## 6. リスクと対処
| リスク | 対処 |
|---|---|
| 社外秘の値がリポジトリ・PR に入る | 道具は値を含まない。投入 SQL はリポジトリ外。gold_to_sql は出力先がリポジトリ内なら止まる。K6 で差分を点検 |
| アプリの通常の接続から読める | RLS FORCE＋is_operator のみ。K5 で 0 行を実測（アプリの役割が superuser でないことは実装前点検で確かめる。recon §6） |
| 取り出した表が元と違う（切り捨て・置き換え） | 値に特殊文字が無いことを投入前に点検。取り出し時に sha256 と行数を照合し、違えば書かない |
| migration が既存表を止める | 新しい表だけ。既存表への FK なし（ADR-1037） |
| ai_ro に出ない（拒否語） | 列名に hash 等を使わない。K1 で実測 |

## 7. 戻し方
- データだけ: Opus が psql で、versions からその版の 1 行を消す（rows は ON DELETE CASCADE で一緒に消える）。消す前に 03_verify で件数を控え、消した後に rows・versions とも その版 0 行を確かめる。
- 表ごと: migration 先頭のコメント `DROP TABLE IF EXISTS public.accuracy_gold_rows; DROP TABLE IF EXISTS public.accuracy_gold_versions;`（不可逆。PO 確認のうえ）。ai_ro は次のデプロイで自動的に消える。

## 8. 受入条件（確かめ方）
| 基準 | 検証方法 |
|---|---|
| K1 デプロイ後、ai_ro に 2 表が見える | 窓口で `select count(*) from ai_ro.public__accuracy_gold_rows` と versions が rc0・0 行の件数 0 |
| K2 投入後の件数 | 窓口と SSH の道の両方で rows 1494・投稿 100 種・versions 1 行（gold_v1） |
| K3 クラウドで取り出した表が元と同じ | クラウドの routine で fetch_gold を実行し、表示された sha256 が `b77fa105…8d`（元ファイル）と一致、行数 1494 |
| K4 採点が同じ | 手元で、同じスナップショットに対し元ファイルと取り出したファイルで score_v102 を走らせ、出力フォルダの差分 0 |
| K5 アプリの接続からは見えない | アプリの役割で `select count(*) from public.accuracy_gold_rows` → 0 |
| K6 社外秘がリポジトリに無い | PR の差分に、正解表の投稿id 100 種のどれも 0 件（手元で照合）。リポジトリに .tsv・投入 SQL の追加 0 |
| K7 既存に影響が無い | デプロイの migration が全部成功、ai_ro の作り直し成功、窓口の既存の件数照会（在庫・解析結果・商品）が rc0 |
| K8 道具の試験 | gold_to_sql と fetch_gold の試験（作った値だけ。社外秘なし）が全件通る。止まる条件それぞれに 1 件以上 |

## 9. 実装の分け方
- 便1（この設計の全部）: migration・2 道具・試験・手順書。migrations を含むので危険 PR。GO は Opus（ADR-1003 の委任）。カード `docs/handoff/accuracy-gold-db/card-1.md`。
- 投入と K1〜K7 は Opus（マージ後）。

## 10. 外部・過去事例の参照と我々への応用
- 該当事例を使わない。理由: 判断の中身は「既存の正本（本番 DB）と既存の読み道（ai_ro・窓口）に、1 つの小さな表を足す」で、このリポジトリの前例（product_packagings の RLS、bin2 の投入型、ADR-1042 の窓口）で根拠が足りる。外部の数値で成否が変わる論点が無い。

## 11. 維持の仕組み
- 新しい版（gold_v2 等）を作ったら、同じ gold_to_sql で投入する（版を列に持つので同居できる）。手順は scripts/accuracy/README.md。
- 表の形は ai_ro が毎デプロイで写す。列を足すときは拒否語を避ける（3-1）。
- 守り手: Opus（設計統括）。正解表の版を決めるのは PO、投入は Opus。

## 12. 審査（Opus 自己審査。同一 AI のため独立した第二者レビューではない）
- 判定: APPROVE（設計合格）。
- 根拠: 既存の仕様（ADR-1007 値は書かない・ADR-1037 ロック・ADR-1042 窓口・ADR-1024 ai_ro）と矛盾なし。窓口の上限（5000 行・値 10240 字）に対し 1494 行・最長 200 字で収まる。キー重複を実測で見つけ row_no 鍵にした。受入条件は全部、数か一致で判定できる。
- 未解決: アプリの役割が superuser でないこと（K5 の前提）と、scripts/accuracy の試験の走らせ方。どちらも実装前点検で事実を取る。superuser だった場合は K5 を満たせないので停止して設計に戻す。
