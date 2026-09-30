# recon: LINE取り込みパーサ統合（段階1）

- デプロイ済みSHA: `a5547fb7b1a5af7c0bb10d0dcf5d37dc2238c401`（`gh run list --workflow deploy.yml --status success --limit 1 --json headSha`）
- 調査日時: 2026-09-30（JST）
- 既存ADR検索結果: `git grep -il "line" docs/adr/` はほぼ誤検出（pipeline/online等の部分一致）。`docs/adr/FEATURE-INDEX.md` にも該当なし。LINE取り込みパーサへの直接言及は以下2件のみ:
  - `docs/adr/ADR-1001-deprecate-tcg-products-unify-to-public.md:105` — `backend/app/routers/tcg_line_import.py` のスキーマ参照変更（表内の一行）
  - `docs/adr/ADR-158-product-level-supersession.md:62,69` — `backend/app/services/tcg_line_import_svc.py` の is_active/旧メッセージ無効化ロジックへの言及
  - パーサ統合そのものを扱うADRは**未確認**（存在しない）
- worktreeは作成していません（上限到達のため）。読み取りのみ、コードはすべて `git show <SHA>:<path>` で取得。Q4のパース実験は scratchpad 内に一時的にソースを書き出して実行（作業後もscratchpad配下に残置＝リポジトリ外）。

---

## Q1. 2つのパーサの全体像

### PC用: `backend/app/services/tcg_line_import_svc.py`

- **`parse_line_export(export_text, supplier_names=None)`** （122-209行目）
  - 戻り値: `list[dict]` 各要素 `{"timestamp": "YYYY-MM-DD HH:MM:00", "display_name": str, "body": str, "is_system_event": bool}`
  - 日付行判定: `_DATE_RE = re.compile(r"^(\d{4})\.(\d{2})\.(\d{2})\s+.+$")`（42行目）— ドット区切り `2026.08.01 金曜日` 形式
  - 時刻行判定: `_TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})\s+(.+)$")`（44行目）— 半角スペース区切り
  - 区切り: 送信者名の切り出しは `_split_sender`（64-92行目）。`supplier_names`（公式サプライヤー名を長さ降順ソートしたリスト）に対して前方一致を試み、一致すれば `(name, rest)`、一致しなければ最初のスペースで分割
  - 続き行: 時刻行・日付行・空行のいずれでもない行は `current_msg["body"]` に `_MSG_SEPARATOR = "\n\n"`（51行目）で連結（196-203行目）。連結の度にシステムイベント判定を再実行
  - システム行判定: `_SYSTEM_EVENT_RE`（46-49行目）。固定サフィックスパターンのみ:
    ```
    (?:がグループに参加しました。?|をグループに招待しました。?|招待をキャンセルしました。?|がメッセージの送信を取り消しました。?)$
    ```
    `display_name + " " + body` の連結文字列に対して `.search()`（185-186行目、200-202行目）
  - 送信取り消しの扱い: 上記正規表現の4パターン目「がメッセージの送信を取り消しました」のみ対応。他の取り消し表現（例: 「メッセージの送信を取り消しました」単独、時制違い等）は**カバーされていない**（未確認: 実データでの表現ゆれの全パターン）
  - トーク名（ヘッダ行）を読んでいるか: **読んでいない**。日付行にマッチしない行は `current_msg is None` の間は単に無視される（157-165行目の日付行分岐、196-198行目の続き行分岐は `current_msg is not None` が条件）。ヘッダ行があってもエラーにならず黙って捨てられる
  - 未認識行のエラー処理: **なし**。日付未検出状態で任意の行が来ても例外を投げない（Android版とは対照的）

- **`_SYSTEM_EVENT_RE`**: 上記の通り、46-49行目

- **`import_line_export(db, filename, export_text, uploaded_by, window_start=None, window_end=None, window_hours=24, source_format="pc")`**（501-706行目）
  - `source_format` は `Literal["pc", "android"]`。`"pc"` の場合 `parse_line_export(export_text, supplier_names)` を呼ぶ（580行目）。`"android"` の場合は `parse_android_export(export_text)` を先に呼び、`parse_line_export` は呼ばれない（543行目、580行目の三項演算子）
  - ファイルsha256は `source_format` で分岐（546-548行目）: android は `"line-android-v1\0" + export_text` にプレフィックスを付けてPCと別IDになるよう設計（コメント545行目「Android file previously misread as PC (zero messages) can be retried」）
  - 未解決サプライヤーは自動登録される（598-647行目のコメントで「4b」）。resolve_suppliers の結果 unresolved があっても、display_name をそのまま `public.suppliers.name/line_name` として INSERT し、`resolved_msgs` に追加。**この自動登録ロジックがQ4/Q5で確認する実害の直接原因**

### スマホ(Android)用: `backend/app/services/tcg_line_android_parser.py`（52行目、全文）

- **`parse_android_export(text)`**（17-52行目）
  - 戻り値: `list[dict]` 各要素 `{"timestamp": ..., "display_name": str, "body": str, "is_system_event": bool}`（PCと同じキー構成）
  - 日付行判定: `DATE = re.compile(r"^(\d{4})/(\d{1,2})/(\d{1,2})\s*\([^\r\n)]*\)$")`（9行目）— スラッシュ区切り `2026/9/12(土)` 形式（PCとは別形式）
  - 時刻行判定: `TIME = re.compile(r"^(\d{1,2}):(\d{2})\t(.*)$")`（10行目）— **タブ区切り**（PCは半角スペース区切り）
  - 区切り: タブで `sender, body = fields` に2分割（35-37行目）。タブが1個だけならシステムイベント扱い（`sender, body, system = '', fields[0], True`、42行目）— つまりAndroid側は「タブが1個あるかどうか」でシステム行を判定しており、PC側の正規表現サフィックス一致とは全く異なるロジック
  - 続き行: 日付・時刻行にマッチせず `current is not None` なら `current['body'] += '\n' + line`（46-47行目、区切りは `\n` のみでPCの `\n\n` と異なる）
  - 送信取り消しの扱い: 明示的な正規表現なし。タブが1個の行はすべて `is_system_event=True` になる仕組みで包括的に扱う（PCの固定パターン方式より広い）
  - トーク名（ヘッダ行）: **読んでいない**。日付行にマッチせず `current is None` かつ `day` が未設定なら黙ってスキップ（48行目の `elif day and line: raise` は `day` が設定済みのときだけ発火）
  - 未認識行のエラー処理: `day` が設定済み（＝最初の日付行より後）で、時刻行にもマッチせず継続行でもない行が来ると `AndroidExportError` を送出（49行目）。**PC版と違いここは例外を投げる**
  - 空データ検出: 全メッセージが `is_system_event=True` の場合 `AndroidExportError('No Android LINE messages found')`（50-51行目）。**PC版にはこの相当ロジックがない**

### 戻り値の型・フィールドの一致点/相違点まとめ

| 項目 | PC (`parse_line_export`) | Android (`parse_android_export`) |
|---|---|---|
| 戻り値キー | timestamp/display_name/body/is_system_event | 同じ |
| 日付行形式 | `YYYY.MM.DD 曜日` | `YYYY/M/D(曜日)` |
| 時刻行区切り | 半角スペース | タブ |
| 送信者名の切り出し | サプライヤーマスタ前方一致 or 最初のスペース分割 | タブで単純2分割 |
| 続き行の連結記号 | `\n\n` | `\n` |
| システム判定方式 | 固定サフィックス正規表現（4パターン） | タブの有無（包括的） |
| 未認識行 | 無視（エラーなし） | `AndroidExportError` |
| 空メッセージ検出 | なし | あり |
| ヘッダ行（トーク名） | 読まない | 読まない |

---

## Q2. 呼び出し元の全走査

コードを呼ぶ箇所は3つのHTTPエンドポイントとテストのみ。Celeryタスク・scriptsディレクトリからの直接呼び出しは**なし**（`git grep -ln "import_line_export\|parse_line_export\|parse_android_export" $SHA -- backend/app/tasks` / `-- scripts` いずれも0件）。

1. **`POST /tcg/line-import`**（`backend/app/routers/tcg_line_import.py:127-134` デコレータ〜関数定義、呼び出しは182行目）
   - `upload_line_export()` から `import_line_export(..., )` を呼ぶ。`source_format` を明示的に渡していない＝デフォルト値 `"pc"` が使われる
   - フロントエンド呼び出し元: `frontend/src/pages/super-admin/TcgLineImportPage.tsx:230`、`frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:652`（`api.postForm("/tcg/line-import", formData)`）

2. **`POST /tcg/line-import/android`**（`backend/app/routers/tcg_line_import.py:678-685`、呼び出しは714行目）
   - `upload_android_line_export()` から `import_line_export(..., source_format="android")` を呼ぶ（722行目で明示指定）
   - super_admin認証（`require_super_admin`）。フロントエンドからの直接呼び出しは**未確認**（grep範囲では見つからず）

3. **`POST /tcg/line-devices/import`**（`backend/app/routers/line_import_devices.py:69-82`）
   - デバイストークン認証（`device_user`）。**Python関数として `upload_android_line_export()` を直接呼ぶ**（HTTPを経由しない、78-81行目）。この関数内のコメント（72-77行目）に「新しい引数が増えたときは、ここにも必ず明示的に渡すこと」という警告があり、2026-09-24に `window_start`/`window_end` 追加漏れで本番障害が起きた実績がある
   - 実際の呼び出し元（Termuxクライアント）: `tools/termux-line-import/client.py:22` の `ENDPOINT = 'https://api.salesanchor.jp/api/v1/tcg/line-devices/import'`、435行目 `post()` 関数でこのURLにmultipartでPOST
   - `tools/termux-line-import/client.py` は先にローカルで `parse_android_export`（19行目でimport、158行目で呼び出し）を使って解析＆検証してからサーバーに送信（サーバー側の`parse_android_export`と**重複したロジック**が `tools/termux-line-import/android_parser.py` に存在）

### `source_format` の決定箇所

- デフォルトは `"pc"`（`backend/app/services/tcg_line_import_svc.py:509`）
- `"android"` になるのは `upload_android_line_export()` から呼ばれた場合のみ（722行目でハードコード）。ユーザー入力やリクエストパラメータでは変わらない＝エンドポイントのルーティングで固定的に決まる

### 関連する追加の呼び出し経路（Q7で言及）

- `backend/app/line_import_admin.py`（メンテナンス専用モジュール、FastAPIルーターではなくCLI的呼び出し）は `commit_pending_job` / `resolve_supplier`（`backend/app/routers/tcg_line_import.py` からimport）と `line_source_names.resolve_android` / `is_android` を使う。**`resolve_android`/`is_android` は `import_line_export` の本流フローでは呼ばれておらず**、`backend/app/services/line_source_names.py` 内の `link_pending` 相当の別経路でのみ使用（`git grep` で `resolve_android(` の呼び出し元は`backend/app/services/line_source_names.py:119`のみ）。この関数群がAndroid専用の別解決ロジックとして存在すること自体、現状「2系統に分かれている」実例

---

## Q3. テストの全走査

| ファイル | test関数数 | 対象 |
|---|---|---|
| `backend/tests/test_tcg_line_import.py` | 44 | `parse_line_export` / `import_line_export`（PC側中心） |
| `backend/tests/test_tcg_line_android_parser.py` | 6 | `parse_android_export`（サーバー側） |
| `backend/tests/test_tcg_line_android_api.py` | 5 | `upload_android_line_export` エンドポイント |
| `backend/tests/test_line_source_names.py` | 7 | `backend/app/services/line_source_names.py`（`is_android`/`resolve_android`含む）+ `import_line_export(source_format='android')` |
| `backend/tests/test_line_import_devices.py` | 6 | `/tcg/line-devices/*` エンドポイント |
| `backend/tests/test_line_import_devices_pg.py` | 5 | DB統合（`source_format`カラム含む） |
| `backend/tests/test_tcg_import_progress_pg.py` | 18 | 進捗API（`import_line_export`呼び出しあり、106行目） |
| `backend/tests/test_line_import_admin.py` | 20 | `backend/app/line_import_admin.py`（メンテナンスCLI） |
| `tools/termux-line-import/test_android_import.py` | 38 | `tools/termux-line-import/android_parser.py`（tools側の重複実装）+ `tools/termux-line-import/client.py`全体 |
| `tools/termux-line-import/test_device_session.py` | 7 | デバイス認証（パーサ非対象） |

- カウント方法: `git show $SHA:<file> | grep -c "def test_"`
- **フィクスチャファイル（サンプル書き出し.txt等）は見つからず**。`git ls-tree -r --name-only $SHA` 全体で `.txt` かつ line/talk/sample/export を含むファイルは `backend/tests/fixtures/inventory_parser_samples/sample_04_yasu_kishi.txt`（在庫パーサ用、無関係）のみ。LINE用サンプルはすべてテストファイル内の文字列リテラル（`SAMPLE = '...'` 等）として埋め込まれている

---

## Q4. PCパーサの穴の実害（実パース実験）

対象ファイル: `/Users/tanizawashingo/Downloads/[LINE]WeGo売ります掲示板グループ.txt`（2026-09-29更新、193,975行、UTF-8）

実行方法: デプロイ済みSHAの `backend/app/services/tcg_line_import_svc.py` と `backend/app/services/tcg_line_android_parser.py` を scratchpad にコピー（`app/services/` 相当のダミーパッケージを作成してimport解決）、`parse_line_export()` をそのまま呼び出し。`supplier_names` は渡さず（＝本番のマスタ一致は再現していない点に注意、名前の切り出しは「最初のスペースで分割」フォールバックのみで検証）。

```
total messages: 3997
is_system_event=True (correctly excluded): 908
is_system_event=False (kept as normal messages): 3089
suspect non-system messages containing system-like keywords (通話/ノート/退出/アルバム等): 14
keyword breakdown: Counter({'通話': 6, 'ノートを作成': 5, 'ノート': 3})
```

### 実例3件ずつ（`_SYSTEM_EVENT_RE` がカバーしない＝システム行なのに「メッセージ」扱いされたもの）

**「通話」系（グループ通話開始/終了）**
```
timestamp: 2026-08-28 12:04:00
display_name: 'N.Fukuda'
body: 'グループ通話が開始されました'

timestamp: 2026-08-28 12:04:00
display_name: 'N.Fukuda'
body: 'グループ通話が終了しました。'

timestamp: 2026-09-02 20:17:00
display_name: '伊藤晴彦'
body: 'グループ通話が開始されました'
```

**「ノート」系（ノート作成）**
```
timestamp: 2026-08-30 22:48:00
display_name: '一真'
body: '新しいノートを作成しました。'

timestamp: 2026-09-09 11:35:00
display_name: 'RAITO'
body: '新しいノートを作成しました。'

timestamp: 2026-09-09 11:37:00
display_name: 'ぱ'
body: '新しいノートを作成しました。'
```

**その他（LINE WORKS参加通知＝別種のシステムメッセージ）**
```
timestamp: 2026-09-04 12:48:00
display_name: 'GL'
body: 'スタッフ ビジネス版LINE 「LINE WORKS」からトークに参加しました。\n\n(グループ機能のノート/アルバム/イベント/投票には対応していません。)'
```

これらの `display_name`（例: `N.Fukuda`, `伊藤晴彦`, `一真`, `RAITO`, `ぱ`, `GL`）は、supplier マスタに一致しなければ `import_line_export` の「4b. 未解決仕入元の自動登録」ロジック（`backend/app/services/tcg_line_import_svc.py:598-647`）により**そのまま新規サプライヤーとして自動登録される**。Q5でこれが実際に本番DBで発生していることを確認。

「招待」「退出」に該当する明確な実例は今回のサンプル抽出キーワードでは0件だった（**未確認**: このファイル内に存在するか自体は全数走査していない。抽出は代表的キーワードのみ）。

---

## Q5. 同じ実害が本番に入ったか（本番DB照会・読み取り専用）

- 接続確認: `SET default_transaction_read_only=on; SHOW transaction_read_only;` → `on`（実行済み、SELECTのみ実施）
- 実行クエリ1:
  ```sql
  SELECT count(*) FROM public.source_messages
  WHERE raw_text ~ '(通話|ノートを作成|新しいノート|グループを退出|タイムラインに投稿|アルバムを作成)';
  ```
  結果: **3件**

- 実行クエリ2（supplier情報とJOIN）:
  ```sql
  SELECT sm.id, sm.line_posted_at, sm.raw_text, s.name, s.line_name, s.supplier_code
  FROM public.source_messages sm
  JOIN public.supplier_channels sc ON sc.id = sm.supplier_channel_id
  JOIN public.suppliers s ON s.id = sc.supplier_id
  WHERE sm.raw_text ~ '(通話|ノートを作成|新しいノート|グループを退出|タイムラインに投稿|アルバムを作成)';
  ```
  結果（生出力）:
  ```
                    id                  |     line_posted_at     |           raw_text           |    name    | line_name  | supplier_code 
  --------------------------------------+------------------------+------------------------------+------------+------------+---------------
   d98ef146-2115-4e04-9ef1-4c33ad4430dd | 2026-09-02 11:17:00+00 | グループ通話が終了しました。 | 伊藤晴彦   | 伊藤晴彦   | SP-00302
   cc885f49-8ad1-41bb-81ae-a3c0f566629a | 2026-09-24 03:36:00+00 | 新しいノートを作成しました。 | いとう　あ | いとう　あ | SP-00255
   2f502e0d-c5f7-4108-9e0d-5943315ed518 | 2026-09-15 06:05:00+00 | 新しいノートを作成しました。 | いとう　あ | いとう　あ | SP-00255
  (3 rows)
  ```

**事実**: 本番で実際に「システムイベント（通話終了・ノート作成）」が `source_messages.raw_text` としてそのまま登録され、その送信者名（`伊藤晴彦`、`いとう　あ`）が `public.suppliers.name`/`line_name` になっている。これはQ1で確認した「4b. 未解決仕入元の自動登録」ロジックが実際にシステム行に対しても発動した証拠。これらの `source_messages` が現在 `is_active=TRUE` かどうか、後続の抽出ジョブ（`extraction_jobs`）でどう処理されたかは**未確認**（今回のクエリでは確認していない）。

**このクエリはPC経路由来か明示的に判定していない点に注意**: `supplier_channels.channel='line'` のみで絞っており、PC取り込み経由かAndroid取り込み経由かは区別していない（`source_messages` テーブル自体に取り込み元フォーマットを示すカラムは確認していない＝**未確認**）。ただし「通話」「ノート」はいずれもPC/Android問わずLINEの標準システムイベント文言であり、`_SYSTEM_EVENT_RE`（PC側）がカバーしない一方、Android側は「タブの有無」で包括的に弾く設計のため、**PC経路由来である可能性が高いが未確定**。

---

## Q6. スマホ書き出し形式・PC書き出し形式の実物

### Android（テストのSAMPLE定数、`backend/tests/test_tcg_line_android_parser.py:4`）
```
[LINE] test\r\n保存日時: test\r\n\r\n2026/9/12(土)\r\n12:00\t姓 名\t商品A\r\n\r\n商品B\t注記\r\n12:01\t別の人\t末尾\r\n
```
- 1行目「`[LINE] test`」＝トーク名ヘッダ行、2行目「`保存日時: test`」も付随情報。**いずれもパーサは読まず無視**（日付行にマッチしないため）
- 日付行: `2026/9/12(土)`
- メッセージ行: `12:00\t姓 名\t商品A`（タブ区切り、時刻・送信者・本文）
- 続き行: 空行を挟んだ後の `商品B\t注記` も継続行として扱われる（タブを含んでいても時刻行の正規表現にマッチしないため継続行扱い）
- システム行の例（同ファイル20行目のテスト）: `12:02\t参加しました\n` — タブは1個のみなので `is_system_event=True`

### PC（実ファイル `/Users/tanizawashingo/Downloads/[LINE]WeGo売ります掲示板グループ.txt` 先頭3行、個人情報は構造把握のためそのまま引用）
```
2026.08.24 月曜日
14:30 Shingo Shingoがグループに参加しました。
14:38 ㍿NGA 株式会社NGAです。
```
- **ヘッダ行（トーク名）自体が存在しない**。ファイル冒頭がいきなり日付行から始まっている（Android版のテストSAMPLEにあるような `[LINE] test` 相当の行はPC実ファイルには無い）
- 日付行: `2026.08.24 月曜日`（ドット区切り）
- メッセージ行: `14:30 Shingo Shingoがグループに参加しました。`（半角スペース区切り、システム行の例でもある）
- 続き行の実例は先の `head -30` 出力（商品情報の複数行）で確認済み（マスク済みログのため本文は伏せているが、空行を挟んで複数行が1メッセージに連結される構造は`_MSG_SEPARATOR`と整合）

---

## Q7. 「1つにまとめる」際の境界案（材料のみ、判断はしない）

事実から見える共通点・相違点の一覧:

**戻り値の型は完全に共通**（`timestamp`/`display_name`/`body`/`is_system_event`の4キー、Q1参照）。

**形式ごとに異なる要素**（すべて実装差異として確認済み）:
- 日付行の正規表現（`.`区切り vs `/`区切り+曜日括弧）
- 時刻行の区切り文字（半角スペース vs タブ）
- 送信者名切り出しロジック（マスタ前方一致フォールバック vs タブ単純分割）
- 続き行の連結記号（`\n\n` vs `\n`）
- システムイベント判定方式（固定サフィックス正規表現 vs タブ有無の構造的判定）
- 未認識行時の挙動（無視 vs 例外送出）
- 空メッセージ検出（なし vs あり）

**呼び出し経路の非対称性**（Q2参照）:
- PCは1系統（`POST /tcg/line-import` → `import_line_export(source_format="pc")` がデフォルト）
- Androidは2系統が同じ `import_line_export(source_format="android")` に収束するが、手前に「サーバー側 `upload_android_line_export`」と「クライアント側 `tools/termux-line-import/client.py` が独自に `parse_android_export` を呼んでローカル検証」という**パーサ実装の二重化**がある（`backend/app/services/tcg_line_android_parser.py` と `tools/termux-line-import/android_parser.py` は別ファイルで内容比較は**未確認**、Q2参照）
- Android専用の別解決ロジック（`line_source_names.resolve_android`/`is_android`）が`import_line_export`の本流とは別に存在し、`backend/app/line_import_admin.py`経由でのみ使われる（Q2参照）。これが現状「1本化されていない」実例のひとつ

**実害の非対称性**（Q4/Q5参照）:
- PC側の `_SYSTEM_EVENT_RE` は4パターンの固定サフィックスのみをカバーし、「通話」「ノート」「LINE WORKS参加」等はすり抜けて通常メッセージ扱いになり、送信者名がそのまま新規サプライヤーとして自動登録される（本番で3件確認済み）
- Android側は「タブの有無」で構造的にシステム行を判定するため、上記のようなキーワード漏れは原理上起きにくい（ただし今回の調査ではAndroid側実データでの検証はしていない＝**未確認**）

**トーク名ヘッダ行**: PC・Android双方とも現状は読んでいない（無視）。ヘッダ行から「トーク名」自体を取得する要件があるかどうかは今回のrecon範囲外＝**未確認**。

---

## 追補（Q8〜Q12）

- 生出力全文: `q8_output_final.txt`（scratchpad同ディレクトリ、218行）
- 実行スクリプト: q8_analysis.py（scratchpad調査用スクリプト。リポジトリ外）（PC実ファイルを対象に `parse_line_export` の全出力を再集計）

### Q8. 網羅性チェック（PC実ファイル、`is_system_event=False` 3089件 / `=True` 908件の全数走査）

前回の別調査記録「招待しました系37件が0/37しか_SYSTEM_EVENT_REに一致しなかった」との整合確認: **今回の実ファイルでも「招待」を含む is_system_event=False メッセージは38件、_SYSTEM_EVENT_REによる正しい除外は0件**（全て正規表現の`$`アンカーが「招待中の友だちが参加するまでしばらくお待ちください。」という末尾テキストのせいでマッチしない）。件数（38 vs 37）はファイル差分によるものだが、**「0/37」という不一致パターンは整合する**。

語別の件数（`is_system_event=False` 3089件中、display_name+bodyに該当語を含むもの。件数は延べ、複数語にまたがる重複あり）:

| 語 | 件数 | 実態 |
|---|---|---|
| 招待 | 38 | 全て「AがBをグループに招待しました。招待中の友だちが参加するまでしばらくお待ちください。」＝本物のシステムイベントだが末尾テキストのため`_SYSTEM_EVENT_RE`が一致しない |
| 参加 | 43 | 上記38件＋LINE WORKS参加通知3件＋業務メッセージ内の「参加」誤爆2件（Whatnotウェビナー案内等） |
| 退出 | 0 | 該当なし（今回のファイルには「退出」表現の該当メッセージが存在しない） |
| 取り消 | 0 | is_system_event=False側には存在しない（取り消しは全てis_system_event=True側で正しく検出されている、下記参照） |
| 通話 | 6 | 「グループ通話が開始/終了されました」＝本物のシステムイベントだが`_SYSTEM_EVENT_RE`に該当パターン自体が存在しない |
| ノート | 8 | 「新しいノートを作成しました。」5件（本物のシステムイベント）＋LINE WORKS参加通知の説明文に含まれる「ノート」3件（誤爆・上記「参加」と重複） |
| アルバム | 3 | 全てLINE WORKS参加通知の説明文中の誤爆（「参加」「ノート」と重複） |
| イベント | 4 | LINE WORKS参加通知3件（誤爆・重複）＋業務メッセージ1件（在庫案内、キーワード誤爆） |
| 投票 | 3 | 全てLINE WORKS参加通知の説明文中の誤爆（重複） |
| アナウンス | 10 | 「Aが\<u\>アナウンスしました\</u\>」＝本物のシステムイベント（HTMLタグ付き、`_SYSTEM_EVENT_RE`に該当パターンなし） |
| 削除 | 19 | 「AがBをグループから削除しました。」12件（本物のシステムイベント、`_SYSTEM_EVENT_RE`に該当パターンなし）＋業務メッセージ2件の誤爆（「削除」を含む長文案内） |
| 変更 | 2 | 「グループ名を『...』に変更しました。」1件（本物のシステムイベント）＋業務メッセージ1件（価格変更案内、誤爆） |
| LINE WORKS | 3 | 上記と同一のLINE WORKS参加通知3件（重複） |
| 退会 | 5 | 「Aがグループを退会しました。」＝本物のシステムイベント（`_SYSTEM_EVENT_RE`に該当パターンなし） |

**重複除去後（is_system_event=False のうち上記いずれか1語以上を含むメッセージの実件数）: 91件**（3089件中）。このうち大半（招待38＋削除12＋退会5＋アナウンス10＋通話6＋ノート作成5＋LINE WORKS参加3＋グループ名変更1 ＝ 概算80件前後）が本物のLINEシステムイベントであり、`_SYSTEM_EVENT_RE`の4パターンでは全くカバーされていない。残りは業務メッセージへのキーワード誤爆（本レコンのgrep手法自体の限界であり、パーサのバグではない）。

`is_system_event=True`（908件）の本文パターンの異なり: **70種類**（全件、q8_output_final.txt 146-215行目に列挙）。うち786件は`body=''`（display_name側に「Aがグループに参加しました。」等の全文が収まったケース＝supplier_namesを渡していない今回の実験条件でのフォールバック分割の結果、正しくシステム判定されている）。残り122件（19種類×複数）は「Xがメッセージの送信を取り消しました」（19+8+8+5+3+3+2+1×8種＝多数）と「Xがグループに参加しました。」（多数）、「Xがグループへの招待をキャンセルしました。」（2件）＝いずれも`_SYSTEM_EVENT_RE`の想定通り正しく捕捉されている。

### Q9. Android実データの保存有無

**取れない**。根拠:
1. `public.import_jobs`（`migrations/20260921_110000_pipeline_tables_public.sql:40-56`）のカラムは `id/filename/raw_sha256/message_count/provider_count/unresolved_count/uploaded_by/status/created_at/pending_messages/window_start/window_end/unresolved_names/review_status/messages_linked_at` のみで、**アップロード原文（export_text全体）を保存する列が存在しない**
2. `public.source_messages.raw_text`（同migrations:20-30行目）も、`build_provider_entries`（`backend/app/services/tcg_line_import_svc.py:275-321`）により「サプライヤーごとの最新メッセージ1件のみ」に絞り込まれた後の断片であり、アップロードファイル全体の原文ではない
3. Termux端末側 (`tools/termux-line-import/client.py:63,167`) は `self.base/originals/<sha256>.txt` にファイルを保存するが、`supersede_and_cleanup`→`remove_old_files`（201-221行目）により**最新1件（keep_digest）を除いて古いoriginalsを削除する設計**。かつ端末自体への接続手段は今回のrecon環境に与えられていない（本指示で許可されているのは本番DBへのSELECT専用SSHアクセスのみ）

よってQ9のパース実験・システム判定パターン集計は実施不可。

### Q10. `tools/termux-line-import/android_parser.py` diff

```
diff <(git show a5547fb7...:backend/app/services/tcg_line_android_parser.py) \
     <(git show a5547fb7...:tools/termux-line-import/android_parser.py)
```
**出力なし（完全に同一内容、diff 0件）**。デプロイ済みSHA時点でサーバー側とTermuxクライアント側の`tools/termux-line-import/android_parser.py`はバイト単位で一致している。ただし同期の仕組み（CI等での自動同期か手動コピーか）は今回未確認。

### Q11. 本番・SELECT のみ（Q5の3件の追跡）

```sql
SELECT sm.id, sm.is_active FROM public.source_messages sm WHERE sm.id IN (...);
```
```
                  id                  | is_active 
--------------------------------------+-----------
 d98ef146-2115-4e04-9ef1-4c33ad4430dd | t   -- 伊藤晴彦(SP-00302) 通話終了
 cc885f49-8ad1-41bb-81ae-a3c0f566629a | t   -- いとうあ(SP-00255) ノート作成
 2f502e0d-c5f7-4108-9e0d-5943315ed518 | f   -- いとうあ(SP-00255) ノート作成（supersededで非アクティブ化済み）
```

```sql
SELECT sm.id, ej.status, count(*) FROM public.source_messages sm
JOIN public.extraction_jobs ej ON ej.source_message_id = sm.id
WHERE sm.id IN (...) GROUP BY sm.id, ej.status;
```
```
                  id                  | status | count 
--------------------------------------+--------+-------
 2f502e0d-c5f7-4108-9e0d-5943315ed518 | done   |     1
 cc885f49-8ad1-41bb-81ae-a3c0f566629a | empty  |     1
 d98ef146-2115-4e04-9ef1-4c33ad4430dd | empty  |     1
```
（`status='empty'` は抽出ジョブが「商品情報なし」と判定した結果と推測されるが、statusの意味の正式定義は今回未確認）

```sql
SELECT s.supplier_code, count(*) AS total,
  count(*) FILTER (WHERE sm.raw_text !~ '(通話|ノートを作成|新しいノート|グループを退出|タイムラインに投稿|アルバムを作成)') AS normal_count
FROM public.source_messages sm
JOIN public.supplier_channels sc ON sc.id = sm.supplier_channel_id
JOIN public.suppliers s ON s.id = sc.supplier_id
WHERE s.supplier_code IN ('SP-00302','SP-00255') GROUP BY s.supplier_code;
```
```
 supplier_code | total | normal_count 
---------------+-------+--------------
 SP-00255      |     9 |            7
 SP-00302      |     1 |            0
```
**事実**: SP-00302（伊藤晴彦）は`source_messages`が総1件のみで、それがまさにシステムイベント誤登録（「グループ通話が終了しました。」）そのもの＝**このサプライヤーは実在の仕入元ではなく、システム行の誤認識だけから生まれた「幽霊サプライヤー」**。SP-00255（いとうあ）は9件中7件が通常投稿の実在サプライヤーだが、2件がノイズとして混入している。

### Q12. 「どのトークか」の追跡可否

```sql
SELECT filename, created_at FROM public.import_jobs ORDER BY created_at DESC LIMIT 5;
```
```
     filename     |          created_at           
------------------+-------------------------------
 android-talk.txt | 2026-09-29 20:35:52.751785+00
 android-talk.txt | 2026-09-29 20:15:38.801636+00
 android-talk.txt | 2026-09-29 20:01:02.116065+00
 android-talk.txt | 2026-09-29 19:41:09.024497+00
 android-talk.txt | 2026-09-29 19:32:41.935106+00
```
```sql
SELECT filename, created_at FROM public.import_jobs WHERE filename != 'android-talk.txt' ORDER BY created_at DESC LIMIT 5;
```
```
               filename               |          created_at           
--------------------------------------+-------------------------------
 [LINE]WeGo売ります掲示板グループ.txt | 2026-09-25 00:19:24.569544+00
 [LINE]WeGo売ります掲示板グループ.txt | 2026-09-24 02:13:13.675435+00
 [LINE]WeGo売ります掲示板グループ.txt | 2026-09-23 12:12:53.929644+00
 [LINE]WeGo売ります掲示板グループ.txt | 2026-09-18 00:11:45.225211+00
 [LINE]WeGo売ります掲示板グループ.txt | 2026-09-17 07:13:06.800816+00
```
- カラム名: `public.import_jobs.filename`（TEXT）
- **事実**: PC経由のアップロードはブラウザで選択した元ファイル名がそのまま保存され、トーク名（グループ名）が含まれる（例上記）。**Android経由は `tools/termux-line-import/client.py:432` で `filename="android-talk.txt"` に固定でハードコードされており、どのトーク（グループ）から書き出されたファイルかを`filename`列からは一切判別できない**
- Android書き出しヘッダ `[LINE] <名前>` の実物: Q9で原文取得不可のため本番実データでは確認できず。テストのSAMPLE定数（`backend/tests/test_tcg_line_android_parser.py:4`）の `[LINE] test\r\n保存日時: test\r\n` がQ6既出の唯一の参照可能な実例（**パーサ自体がこの行を読んでいないため、たとえ実データにあってもトーク名として抽出できる設計にはなっていない**）

### 失敗したコマンド（全文）

1件: 本番SELECTクエリで `<>`（不等号）を使ったところ、psql-write-guardフックが誤検知でブロック（書き込みではない）。
```
PreToolUse:Bash hook error: [/Users/tanizawashingo/.claude/scripts/agent-danger-hook.sh]: 🚫 BLOCKED [psql-write-guard]: 本番DBへの直接書き込みは禁止されています。
   検知パターン: ssh+psql < file
   読み取り（-c "SELECT ..."）は許可されています。
   書き込みが必要な場合: bash scripts/permit-danger.sh "psql write"
   （1回限り有効・30分で自動失効）
```
迂回・permit-danger.shの使用はせず、同じSELECT文を `<>` → `!=` に書き換えて再実行し成功（Q12参照、書き込みは一切発生していない）。

---

## 追補2（Q13、本番・SELECTのみ）

**注**: Q13着手時、複数行CASE文のクエリでpsql-write-guardフックに再度ブロックされた（検知パターン名「ssh+psql < file」）。設計担当の指示により、1パターン1クエリに分割し、かつコマンド文字列に `<` を含めない形（「アナウンスしました」はHTMLタグ`<u>`を外して照合、タグの有無は結果のraw_textを目視確認）で続行。permit-danger.shは使用していない。書き込み・ファイル入力・heredocなし。

### Q13(a) 種類別件数・is_active別件数（`public.source_messages.raw_text` 正規表現一致）

使用した正規表現（1パターン=1クエリ、`SELECT is_active, count(*) FROM public.source_messages WHERE raw_text ~ '<パターン>' GROUP BY is_active;`）:

| # | パターン（正規表現） | is_active=f | is_active=t | 合計 |
|---|---|---|---|---|
| 1 | `招待中の友だちが参加するまでしばらくお待ちください。` | 11 | 2 | 13 |
| 2 | `をグループから削除しました。` | 4 | 1 | 5 |
| 3 | `がグループを退会しました。` | 1 | 3 | 4 |
| 4 | `アナウンスしました`（タグなし照合） | 3 | 2 | 5 |
| 5 | `グループ通話が開始されました` | 0 | 0 | **0（該当なし）** |
| 6 | `グループ通話が終了しました` | 0 | 1 | 1 |
| 7 | `新しいノートを作成しました。` | 1 | 1 | 2 |
| 8 | `からトークに参加しました。` | 2 | 2 | 4 |
| 9 | `グループ名を` （`.*に変更しました。`まで含む形、および単純部分一致`グループ名を`単体でも再確認） | 0 | 0 | **0（該当なし）** |

**事実**: 「アナウンスしました」5件は全件、raw_textが`<u>アナウンスしました</u>`とHTMLタグ付きで格納されていた（目視確認、実例5件全て `<u>...</u>` 形式）。「グループ通話が開始されました」「グループ名を...に変更しました」の2パターンは**本番に0件**（Q4のローカルパース実験では「開始」1件・「名称変更」1件が検出されていたが、これらは本番には取り込まれていない＝おそらく実験対象ファイルの窓（window_hours）や供給元マスタ一致の違いにより取り込み対象から外れたため。**未確認**：具体的な理由）。

### Q13(b) システム行を含む仕入元ごとの内訳

上記9パターンのいずれかにraw_textが一致した`source_messages`を持つ仕入元は**21件**（重複除去後）。各仕入元の`source_messages`総件数と、システム行以外（通常投稿）の件数、`suppliers.is_active`列（列名確認済み: `is_active`, BOOLEAN）、`created_at`:

```
 supplier_code |               name               | is_active |          created_at           | total | non_system 
---------------+----------------------------------+-----------+-------------------------------+-------+------------
 SP-00020      | 矢ヶ嵜裕史                       | t         | 2026-08-30 11:13:22.005976+00 |    25 |         24
 SP-00139      | 井上武範                         | t         | 2026-08-30 11:13:22.005976+00 |     6 |          5
 SP-00192      | 徳武俊太郎                       | t         | 2026-09-05 02:44:02.344604+00 |     4 |          3
 SP-00215      | なかひら                         | t         | 2026-09-07 03:37:21.349403+00 |     6 |          5
 SP-00217      | SIG                              | t         | 2026-09-07 03:37:23.508385+00 |     7 |          6
 SP-00228      | 小菅圭輔                         | t         | 2026-09-07 14:05:13.166122+00 |     2 |          1
 SP-00234      | RAITO                            | t         | 2026-09-09 00:06:01.845315+00 |    19 |         16
 SP-00244      | 板谷よしみつ                     | t         | 2026-09-10 14:39:14.179732+00 |     4 |          1
 SP-00245      | 鈴木（板谷STAFFアカウント）      | t         | 2026-09-10 14:39:14.189848+00 |     3 |          0
 SP-00246      | Wevee                            | t         | 2026-09-10 22:05:54.274826+00 |     3 |          2
 SP-00247      | Evedat板谷                       | t         | 2026-09-10 22:05:56.723373+00 |     1 |          0
 SP-00248      | 竹内                             | t         | 2026-09-10 22:05:57.489894+00 |     6 |          2
 SP-00254      | イベダットースタッフアカウント） | t         | 2026-09-12 20:10:38.120759+00 |     1 |          0
 SP-00255      | いとう　あ                       | t         | 2026-09-12 20:10:39.514077+00 |     9 |          4
 SP-00260      | LF                               | t         | 2026-09-13 07:05:20.81969+00  |     1 |          0
 SP-00276      | maarii☆                          | t         | 2026-09-16 14:46:44.856917+00 |     1 |          0
 SP-00278      | kaishi                           | t         | 2026-09-16 14:46:46.034169+00 |    20 |         19
 SP-00285      | ｍ                                | t         | 2026-09-18 00:11:49.823239+00 |     1 |          0
 SP-00302      | 伊藤晴彦                         | t         | 2026-09-18 00:12:11.635431+00 |     1 |          0
 SP-00310      | GL スタッフ                      | t         | 2026-09-18 00:12:16.223831+00 |     1 |          0
 SP-00317      | Mie (*´ω`*)                      | t         | 2026-09-18 00:12:20.087563+00 |     2 |          1
(21 rows)
```
（`non_system`は上記9パターンいずれにも一致しないraw_textの件数。全件`is_active='t'`＝いずれも現時点で無効化されていない）

**「システム行以外が0件」＝システム行だけから生まれた仕入元（8件）**:

| supplier_code | id | name | total | 由来パターン |
|---|---|---|---|---|
| SP-00245 | 25593 | 鈴木（板谷STAFFアカウント） | 3 | 退会・LINE WORKS参加 |
| SP-00247 | 25595 | Evedat板谷 | 1 | 退会 |
| SP-00254 | 25602 | イベダットースタッフアカウント） | 1 | 退会 |
| SP-00260 | 25608 | LF | 1 | 退会 |
| SP-00276 | 25624 | maarii☆ | 1 | アナウンス |
| SP-00285 | 25633 | ｍ | 1 | アナウンス |
| SP-00302 | 25650 | 伊藤晴彦 | 1 | 通話終了（Q5既出） |
| SP-00310 | 25658 | GL スタッフ | 1 | LINE WORKS参加 |

### Q13(c) 「システム行だけ」の仕入元への他テーブルからの参照

FK定義の洗い出し（本番DB `information_schema` をSELECTして取得、`ccu.table_name='suppliers'`）:
```
 table_schema |        table_name        |     column_name     |              constraint_name
--------------+--------------------------+---------------------+-------------------------------------------
 public       | discord_inbound_messages | supplier_id         | discord_inbound_messages_supplier_id_fkey
 public       | ingestion_jobs           | supplier_id         | ingestion_jobs_supplier_id_fkey
 public       | inventory                | supplier_id         | inventory_supplier_id_fkey
 public       | inventory_movements      | supplier_id         | inventory_movements_supplier_id_fkey
 public       | parse_logs               | supplier_id         | parse_logs_supplier_id_fkey
 public       | products                 | supplier_default_id | products_supplier_default_id_fkey  （重複表示5行、原因未確認だが実体は1つのFK）
 public       | supplier_aliases         | supplier_id         | supplier_aliases_supplier_id_fkey
 public       | supplier_channels        | supplier_id         | supplier_channels_supplier_id_fkey
 public       | supplier_discord_routing | supplier_id         | supplier_discord_routing_supplier_id_fkey
 public       | supplier_knowledge_links | supplier_id         | supplier_knowledge_links_supplier_id_fkey
 public       | supplier_prompts         | supplier_id         | supplier_prompts_supplier_id_fkey
(15 rows、うちproducts行が重複)
```

上記8仕入元のid（25593,25595,25602,25608,25624,25633,25650,25658）で各テーブルをSELECTした結果:

```
discord_inbound_messages: 0件
ingestion_jobs: 0件
inventory: 0件
inventory_movements: 0件
parse_logs: 0件
supplier_aliases: 0件
supplier_discord_routing: 0件
supplier_prompts: 0件
products.supplier_default_id: 0件
supplier_knowledge_links: 1件（supplier_id=25624 = SP-00276 maarii☆）
```

`supplier_knowledge_links`の該当行詳細:
```sql
SELECT skl.id, skl.supplier_id, skl.knowledge_rule_id, skl.is_active FROM public.supplier_knowledge_links skl WHERE skl.supplier_id = 25624;
```
```
 id  | supplier_id | knowledge_rule_id | is_active 
-----+-------------+-------------------+-----------
 290 |       25624 |                39 | t
```

**事実**: 8件の「システム行だけの仕入元」のうち、**7件はどのテーブルからも参照されていない**（完全な孤立レコード）。**1件（SP-00276 maarii☆）のみ、`supplier_knowledge_links`（仕入元別ルール紐付けテーブル、`knowledge_rule_id=39`を参照）から1件参照されている**。この参照がいつ・誰によって設定されたか（自動生成か手動設定か）は今回の調査範囲外＝**未確認**。

### 未確認事項（Q13）
- Q13(a)5番・9番が0件だった理由（Q4のローカル実験結果との差異の原因）
- products行がFK一覧に5回重複表示された理由（information_schemaのJOINによる技術的重複と推測されるが未検証）
- SP-00276の`supplier_knowledge_links`参照（`knowledge_rule_id=39`）がいつ・どのように設定されたか
- 「システム行だけの仕入元」が抽出対象（extraction_jobs等）としてLINE解析結果や在庫データに影響を与えているかどうか（今回は参照有無の確認のみで、実際の業務影響までは追跡していない）
