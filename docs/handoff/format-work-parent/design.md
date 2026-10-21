# design: 細分類を中分類（作品）の子にする

> この文書は何か: 「ポケモン」などの中分類を親、「ブースターパック」などの細分類を子として、親に合わない子を商品に付けられなくする設計。
> 親: [商品マスタ 仕様書](../../specs/product-master/README.md)／登録の決め方: [registration-rules.md](../../specs/product-master/registration-rules.md)
> 基準: origin/main dddf785704ddee3d353220350a3c821ddf1433da（2026-10-22 取得）

- 起案: 2026-10-22 / Planner・Architect: Claude Opus（同一AIの自己審査。独立レビューは別途 Fable 評価と reviewer）
- 状態: 設計案（PO 承認前）。ADR 案: `docs/adr/ADR-1038-product-format-child-of-work.md`（Proposed）
- 現状: `docs/handoff/format-work-parent/recon.md`（以下 recon。§番号で引く）。生出力は同フォルダ `raw/`。

## 0. PO の願いと成功条件（KGI）

PO 原文（2026-10-21）「細分類は中分類と紐づけて中分類を親に親子関係にできる？」
前提（PO 2026-10-22）: 配線と DB の SSOT を守り、データを分散させない。フロントはデザイントークンと金型を守り、金型にないハードコードをしない。推測で進めない。

KGI（○×で判定できる形）:
- G1. どの登録・編集の入口でも、中分類を選ぶと、その中分類の子の細分類だけが選べる。中分類を選ぶ前は細分類を選べない。
- G2. 親子の組み合わせを記録する場所が DB に 1 か所（`product_format_game_links`）だけになる。旧い 2 か所目（`product_formats.type_master_id`）は無くなる。
- G3. 親に属さない細分類を持つ商品を、画面・CSV・SQL の直接書き込みのどれでも保存できない（DB が拒否する）。
- G4. 今ある商品 1453 件の中分類・細分類は 1 件も変わらない。

## 1. 先に結論

**できる。** 大きな作り替えは要らない。
- 親子の表（`product_format_game_links`。中分類＝親、細分類＝子）は既にあり、すべての入口がこの表で選択肢を絞り、保存時に照合している（recon §4）。
- 本番の 1283 件で、親子に合わない商品は 0 件（recon §3-3、§10.2）。
- 足りないのは次の 3 つ。
  1. DB での保証（G3）
  2. 二重の置き場の撤去（G2）
  3. 金型外の入力部品 1 か所（G1 の画面で、PO 前提の金型遵守）

**形の選び方は PO が決定済み（2026-10-22 チャット「1,」）。** 選んだのは「ブースターパック 1 つを、複数の中分類で一緒に使う」形。

「1 つの細分類は 1 つの中分類にだけ属する」厳密な木にはしない。
- ブースターパックなど 15 個の細分類は、複数の中分類で使われている（recon §3-1、§9-1）。
- 木にするには、同じ「ブースターパック」を中分類ごとに 16 行へ複製することになる。これは PO 前提の「データを分散させない」に反する。
- そこで「親（中分類）は子（細分類）を複数持ち、子は複数の親の下に並べる」形とし、親子の記録を 1 か所に置く。

### 1-2. 旧列の由来（reviewer 審査で判明。recon §2-3 の「記録無し」を訂正）
- `migrations/20260923_010000_product_formats_add_type_master_id.sql:1-2` に「細分類に中分類への直接リンクを追加。カードゲームごとの細分類フィルタリングを実現する」とある。
  - つまり過去に「細分類 1 つに親 1 つ」の案が入っていた。
- 同ファイル :42-52 に「初期値は super-admin 画面から手動設定」とあり、予定値が書かれている。
  - 予定値は、細分類 17〜22 → ポケモン、23 → 遊戯王、24・25 → ワンピース。今の値（recon §10.1）と一致する。
  - 細分類 1〜16 は「NULL 据置（PO判断待ち）」と書かれているが、今は全部に値が入っている。誰がいつ入れたかの記録は見つかっていない（【未確認】）。
- その後、ADR-1020 で links（1 つの細分類を複数の中分類で使える表）が選択肢の正になり、旧列は使われなくなった。
- PO に選んでもらう形は 2 つ。
  - A（推奨）: 今の links のまま。1 つの細分類を、複数の中分類の下で共有する。親子の記録は 1 か所。
  - B: 厳密な木。中分類ごとに別の細分類の行を持つ。ブースターパックだけで最大 16 行に分かれる。
  - B は旧列の考え方に近いが、同じ名前の行が増えて「データを分散させない」に反する。
- 旧列を落とすと、人が画面で入れた 28 個の値が消える。便3b の前に CSV に退避し、PO に見せる。

## 2. 現在地（recon からの要約・根拠付き）

| 事実 | 根拠 |
|---|---|
| 中分類＝作品＝ `public.type_master`（18 行）。links の親も同じ表 | recon §2-2、raw/q07 |
| 親子は `product_format_game_links`（78 行、PK (format_id, type_master_id)） | recon §2-1、§10.5 raw/q24 |
| 全入口（詳細ドロワー・レビュー登録・登録ドロワー・CSV・往復 CSV）が links で絞り、保存時に照合 | recon §4-1、§4-2 |
| DB に親子の制約は無い（products の FK は product_formats だけ） | recon §2-1、§10.5 raw/q25 |
| 旧列 `product_formats.type_master_id` は二重の置き場で、どこの絞り込みにも使われていない。商品の作品と 706/1283 件で食い違う。読み書きは 14 か所 | recon §2-3、§5、§10.1 |
| 旧列の ADD が毎デプロイ走る（20260923_010000 Step 1） | recon §10.4、`migrations/20260923_010000_product_formats_add_type_master_id.sql:4-21` |
| 詳細保存は作品と細分類を別々の UPDATE 2 回で書く（1 トランザクション。commit は :326 の 1 回） | `backend/app/services/tcg_product_detail_svc.py:260-276,326` |
| 仕入元詳細の登録ドロワーの 5 欄は自作 SearchSelect（datalist）で、金型ではない | recon §6、§10.6、`frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:54-91,215-219` |
| PG16: 複合 FK は MATCH SIMPLE で NULL を検査しない。NOT VALID は走査しない。VALIDATE は products に SHARE UPDATE EXCLUSIVE | recon §10.3（公式文書＋使い捨て PG16.15 実験 raw/x02） |
| 実験: 即時の複合 FK では 2 回 UPDATE の 1 回目で失敗する。1 文の UPDATE なら成功する | recon §10.3、raw/x02 |

既存 ADR（recon §8）: ADR-1020 What 5（links が選択肢の正）、ADR-1026 What 3（旧列は「別の情報なので変えない」）。本設計は ADR-1026 What 3 を改める。ADR-156（分類の木の外に細分類）とは矛盾しない。木の中には入れず、木の段（中分類）に links でぶら下げる。

## 3. 変更前 → 変更後

| | 変更前 | 変更後 |
|---|---|---|
| 親子の記録 | links（正）＋ product_formats.type_master_id（二重・食い違いあり） | links だけ |
| DB の保証 | なし（アプリの照合だけ） | 複合 FK `fk_products_format_in_work`: products(product_format_id, work_id) → links(format_id, type_master_id)、MATCH SIMPLE、NO ACTION |
| 詳細保存 | UPDATE 2 回、照合は書いた後 | 照合を書く前に行い、UPDATE 1 回で作品と細分類を同時に書く |
| 細分類マスタ画面 | 「使えるゲーム」（links）と「type_master_id」単独欄の 2 つ | 「使えるゲーム」だけ |
| 仕入元詳細の登録ドロワー | 自作 SearchSelect 5 欄 | 金型 `Select` 5 欄 |

## 4. 便の分け方（1 便 1 目的・順番を守る）

順番の理由: FK を足す前に、FK に当たる書き方（2 回 UPDATE）を本番から無くす。列を落とす前に、列を読むコードを本番から無くす。

### 便1 詳細保存を 1 文にする（コードのみ・migration なし）
- 対象: `backend/app/services/tcg_product_detail_svc.py:260-284`。
- 変更:
  - 細分類の値を、`final_format_id`（来ていれば新値、無ければ現値）として先に決める。
  - 存在確認（`_validate_product_format`）と親子照合（`format_matches_game`。条件は今と同じ「細分類か作品が変わったときだけ」）は、UPDATE の前に行う。
  - :260 の UPDATE に `product_format_id=:product_format_id` を加え、:275 の 2 回目の UPDATE を消す。
  - 細分類が来なかったときは現値をそのまま書く（値は変わらない）。
- 試験の変更:
  - `backend/tests/test_product_format_game_links_pg.py:142-143`（`test_detail_update_keeps_unchanged_old_pair`）は、便2 の後は DB が古い不一致の組を作らせないため、前提が成り立たない。
  - 便1 では残し、便2 で「DB が不一致の組を拒否する」試験に置き換える。
  - 便1 に足す試験は 3 つ。①作品と細分類を同時に変えて成功すること、②不一致なら 422 で行が変わらないこと、③細分類を送らず作品だけ変えた場合に今と同じ判定になること。
- 触らない: API の形、エラー符号（`PRODUCT_DETAIL_FORMAT_GAME_MISMATCH`・`PRODUCT_DETAIL_INVALID_CLASSIFICATION`）、ほかの入口。
- 現値の書き直しは、ほかの人の更新を消さない。詳細保存は `FOR UPDATE` と版の照合（`tcg_product_detail_svc.py:158,161`）で守られている（reviewer r01）。
- GO: backend のみで、危険なパスは含まない。委任 GO（Opus）。

### 便2 複合 FK を足す（migration・危険 PR・GO 要）
- 新しい migration: `migrations/2026xxxx_xxxxxx_products_format_in_work_fk.sql`。`scripts/run_all_migrations.sh` に登録する。
- 中身（前例 `migrations/20260919_030000_master_ssot_fk_work_id.sql` の冪等 DO ブロック）:
  1. 事前点検: 不一致の行数を数える。条件は「products で product_format_id と work_id がともに入っていて、links に組が無い」こと。1 件以上なら `RAISE EXCEPTION` で止める。値は書かない（ADR-1007）。
  2. pg_constraint に `fk_products_format_in_work` が無ければ、`ALTER TABLE public.products ADD CONSTRAINT fk_products_format_in_work FOREIGN KEY (product_format_id, work_id) REFERENCES public.product_format_game_links (format_id, type_master_id) NOT VALID` を実行する。
  3. convalidated が false なら `ALTER TABLE public.products VALIDATE CONSTRAINT fk_products_format_in_work` を実行する。
- migration-guard チェック 8 への対処（`scripts/check-migration-value-writes.py:35-42` の許可語に `ADD CONSTRAINT`・`VALIDATE CONSTRAINT`・`pg_constraint`・`RAISE EXCEPTION` は含まれない）:
  - 前例 `migrations/20260919_030000_master_ssot_fk_work_id.sql:13-37` の技法に従う。
  - 表名は `'pro' || 'ducts'` のように連結した変数に入れ、`EXECUTE format('... %I ...')` で組み立てる。
  - 事前点検の SELECT も、存在確認（pg_constraint）も、同じ技法で書く。
  - 完了条件: 実装後に手元で `python3 scripts/check-migration-value-writes.py diff origin/main HEAD` を流して 0 件であること。
  - チェック 4 は PUBLIC_TABLES に links があるので通る。制約名 `fk_products_format_in_work` は `\bproducts\b` に当たらない（Fable 審査 10_guard_wf_219_392.txt）。
- ロック:
  - ADD は products と links に SHARE ROW EXCLUSIVE を取る。NOT VALID なので走査はしない。
  - ADR-1037 の 1 秒の lock_timeout と流し直し（全体 40 回まで）の中で取る。
  - VALIDATE は products に SHARE UPDATE EXCLUSIVE を取り、読み書きを止めない。1453 行なので短時間で終わる。
- 試験（pytest・PG）:
  - (1) 不一致の組を直接 UPDATE すると IntegrityError になる（旧 :142 の試験の置き換え）。
  - (2) 片方が NULL なら通る。
  - (3) 使用中の links の行を消すと DB が拒否する。API は今と同じ 409。
  - (4) 細分類を物理削除したとき（links が CASCADE で消え、products の細分類は SET NULL）に、文が通るかを確かめる。recon §10.3(c) の【未確認】をここで確定させる。
- 試験の土台に FK を足す: 試験の土台は migration ファイルを名前で直接流している。新しい migration を次の 2 か所に足す。
  - `backend/tests/test_product_format_game_links_pg.py:26-28`
  - `backend/tests/test_tcg_work_matching_integration.py:374` の後
  - 既存の後始末の順（:42-45。products の細分類を NULL にしてから product_formats を消す）は FK と合うので、変えない。
- 分岐の想定:
  - (4) が落ちる場合は、細分類の物理削除の経路がアプリに無い（論理削除のみ。`backend/app/routers/super_admin_product_formats.py:227-231`）。そのため試験の後始末を「products の細分類を NULL → links → formats の順に消す」に直し、「物理削除の前に使用中の商品を外す」ことを ADR に書く。ON DELETE の動作は変えない。
  - 事前点検が 1 件以上で止まった場合は、その行を PO に見せて直し方を決める（推測で直さない）。
- 索引は足さない。products(product_format_id, work_id) の索引は、links の行を消すときの照合を速くするためのもの。products は 1453 行で、links の行を消すのは細分類マスタ画面からの手作業だけ（`super_admin_product_formats.py:184`）。
- 仕様書: 同じ PR で `docs/specs/product-master/README.md` §3-2 と `registration-rules.md` §2 の細分類の行に、「細分類は中分類の子。親子の正本は product_format_game_links。DB の FK で守る」と追記する。
- GO: migrations/ を含むため危険 PR（ADR-135/136）。DROP は含まない。そのため ADR-1003 の委任 GO（Opus）の対象とする。STANDARD-WORKFLOW:140 の PO 本人 GO は DROP のときだけ。

### 便3a 旧列を読むコードを外す（コードのみ）
- 外す所は、recon §10.1 の 14 か所のうちコードと文言のぶん。
  - `backend/app/routers/super_admin_product_formats.py:30,31,93-94,130` の type_master_id
  - `backend/app/schemas/product_format.py:19,33`
  - `frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.tsx:44,57,68,134,159,222,328-341`（単独欄と一覧の列）とそのテスト :39
  - `frontend/api-contract/openapi.json` の 3 か所（再生成の手順に従う）
  - `ja.json`/`en.json` のキー typeMasterId（両方同時に外す）
- API は type_master_id を受けたら、ほかの未知の項目と同じ扱い（スキーマの既存の扱い）にする。どの扱いになるかは、カード作成時に schemas の model_config を確かめて書く。
- 列は残す（便3b まで値はそのまま）。
- 作成・更新のスキーマ（`backend/app/schemas/product_format.py:12-33`）に model_config は無い。既定では知らない項目は無視される（pydantic v2 の extra="ignore"）。これはまだ実際に送って確かめていない（【未確認】）。便3a の試験で、type_master_id を付けて送っても 200 で保存できることを確かめる。
- GO: `frontend/api-contract/` を触るため、ADR-1015:17 の危険なパスに当たる。委任 GO（Opus）。DROP は含まない。

### 便3b 旧列を落とす（migration・DROP COLUMN・PO 本人の GO 要）
- 事前: 本番の `product_formats` から `id, code, type_master_id` の 28 行を CSV に退避し、`docs/handoff/format-work-parent/data/` に置く（ADR-1026 What 4 の前例）。値は recon §10.1 の一覧と照合する。
- `migrations/20260923_010000_product_formats_add_type_master_id.sql` の Step 1（:4-21）を消し、「ここに ADD を戻さないこと（ADR-1038）」と書く。Step 2（kind_id）は残す。前例は ADR-1026 の commit 03d770375。
- 新しい migration: `DROP COLUMN IF EXISTS type_master_id`。FK 制約 `product_formats_type_master_id_fkey` は列と一緒に消える。値は書かない。`run_all_migrations.sh` の末尾に登録する。
- チェック 10（column churn）とチェック 6（PR 本文に ADR-1038）を満たす。
  - 【未確認】`scripts/check-migration-column-churn.js` の allowlist に product_formats.type_master_id を足す必要があるか。便3b のカードで、ADR-1026 の commit 03d770375 と照らして確かめる。
- GO: STANDARD-WORKFLOW:140 により **PO 本人の「GO #PR番号」** が要る。

### 便4 登録ドロワーの 5 欄を金型 Select にする（画面のみ）
- 対象: `frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:54-91`（SearchSelect を消す）と `:215-219`。
- 変更: 5 欄（大分類・中分類・製造元・商品分類・細分類）を金型 `SelectControl`（`frontend/src/components/Select.tsx:64`）にする。
  - 周りの欄と同じく `<label className="pmd-field">{label}<SelectControl .../></label>` の形にする（:220-235 の TextFieldControl と同じ形）。ラベル付きの `Select` は使わない。こうするとラベルが二重にならない。前例は `ProductFormatsMasterPanel.tsx:332`。
  - props: `size="sm" fullWidth placeholder options value onChange`。
  - options は金型の形 `{value,label}`（Select.tsx:106-108）に変換する。例: `formatOptionsFor(formats, values.work_id).map(o => ({ value: String(o.id), label: o.name }))`。value の型は Select.tsx の実物に合わせる。
  - 細分類には `disabled={!values.work_id}` を付ける。
  - 中分類の onChange は、今の `formatAfterWorkChange`（:125）をそのまま通す。
- 文言: 今の「名称で検索・選択」（ja.json:4923）は、文字を打って絞れない Select の動きと合わない。新しいキー `tcgAnalysisReview.productMasterDrawer.selectPlaceholder`（ja「選択してください」、en「Select」）を ja/en 同時に足す。使わなくなる `searchSelectPlaceholder` は、ほかで使っていなければ消す。
- GO: 画面だけの変更。委任 GO（Opus）。
- 試験: `ProductMasterDrawer.test.tsx` の `input[list]`（:63）と `#lookup-product_format_id option`（:132 付近）を、Select の選択の試験に書き直す。
- 動きの違い（PO に伝える）:
  - 文字を打って絞る動きが、一覧から選ぶ形に変わる。候補は最大 18 件。
  - 中分類の子だけが出ることと、中分類を変えると細分類が空に戻ることは変わらない。

### 対象外（この設計では扱わない）
- 中分類 9043（鳴潮）・9044（マジック）に子の細分類が 0 件であること（recon §2-2）。
  - 親子の形の問題ではなく、マスタの値の問題。
  - 細分類マスタ画面で links を足せば直る。どの細分類を子にするかは、値の決定なので PO に候補を見せて決める（registration-rules C3）。
- links の `alias`（9 行。読み書きするコード無し。recon §3-1）。
- 中分類ごとに子の細分類を一覧する新しい画面。PO が望めば別便。

## 5. 影響範囲（呼び出し元の全走査の結果）

- products の work_id・product_format_id を書く所は 3 か所（recon §10.2、raw/g07）。新規 INSERT と往復 CSV は 1 文なので FK に当たらない。当たるのは詳細保存だけで、便1 で直す。
- links を消す所: `super_admin_product_formats.py:184`。今も使用中なら 409（:172-180）。競合時は IntegrityError を 409 にする分岐が既にある（:196-199）。
- type_master を消す所: `super_admin_tcg.py:270`。既に `fk_products_work_id` で止まるので、新しい失敗の形は無い。
- 旧列の読み手: 14 か所（recon §10.1）。gas/、監視、ai_ro（動的に作り直す）は影響なし。
- テナント商品: 0 行（recon §3-4）。

## 6. 代替案と選ばなかった理由

| 案 | 選ばなかった理由 |
|---|---|
| 細分類 1 行に親 1 つ（product_formats.type_master_id を正にする） | 15 個の細分類を中分類ごとに複製することになり、SSOT に反する。旧列の値は商品と 706 件食い違い、正にできない（recon §2-3） |
| products に親子の列を足す | products は列番号 1600 の上限に到達済み（recon §10.1、raw/q27b） |
| トリガーで照合 | 複合 FK で同じことが宣言でき、コードの保守が要らない。PG 公式の仕組みで、実験で確認済み |
| DEFERRABLE INITIALLY DEFERRED の FK | 2 回 UPDATE を残せるが、ずれがコミットまで見えない。1 文にまとめれば即時 FK で足りる（recon §10.3 実験） |
| アプリの照合だけで済ませる（今のまま） | SQL の直接書き込み・台本からの書き込みを止められず、G3 を満たさない |

## 7. 危ないことと対処

| 危ないこと | 対処 |
|---|---|
| 便2 の実行前に不一致が生まれ、VALIDATE が失敗する | migration の事前点検で止め、行を PO に見せる。GO の直前に本番で不一致 0 件を測り直す |
| 便2 の ADD がロックを取れない | ADR-1037 の 1 秒と流し直しの中で取る。NOT VALID で走査しない |
| 便1 より先に便2 が入り、詳細保存が 500 になる | 便の順番を守る。便2 の GO の条件に「便1 が本番反映済み」を入れる |
| (c) 細分類の物理削除が FK に止められる | 便2 の試験 (4) で確定させる。アプリに物理削除の経路は無い |
| 旧列の値が要るようになる | 便3b の前に CSV を退避する。product_formats は再追加できる（列数は便3b のカードで測る） |

## 8. 受入条件と検証方法

| 基準 | 検証方法 |
|---|---|
| K1 便1 後、詳細保存で中分類と細分類を同時に変えて保存できる。不一致は 422 で、行は変わらない | pytest（便1 で足す 3 試験）と、本番反映後に PO が商品詳細画面で 1 件、中分類と細分類を変えて保存できること（○×） |
| K2 便2 後、本番の pg_constraint に `fk_products_format_in_work` があり、convalidated=t | reader の道で `SELECT conname, convalidated FROM pg_constraint WHERE conname='fk_products_format_in_work'` |
| K3 便2 後、不一致の組を書き込もうとすると DB が拒否する | pytest (1)(3)。本番では試さない |
| K4 便1・便2・便3b のそれぞれ前後で、商品 1453 件の (work_id, product_format_id) が 1 件も変わらない（G4） | 各便の GO 前と反映後に、組ごとの件数表（raw/q22 と同じ SQL）を取って比べる。差分 0 |
| K5 便3b 後、product_formats に type_master_id 列が無い。旧列の読み手 0 | 列の有無: reader の道で information_schema.columns を見る。<br>読み手: 同じ 3 ファイルに対する `git grep -n "type_master_id"` の残りが、links 由来の行（router :40 の array_agg、:185 の DELETE、:192-193 の INSERT など、`l.type_master_id` か `product_format_game_links` の文脈）だけであること。PR で 1 行ずつ確かめる。<br>加えて `git grep -n "typeMasterId" frontend/src` が何も出さないこと（locales・試験も含む）。`frontend/api-contract/openapi.json` の ProductFormat 系スキーマに type_master_id が無いこと |
| K6 便3b 後、細分類マスタ画面に type_master_id の欄が無く、「使えるゲーム」で親子を編集できる | PO 目視（○×） |
| K7 便4 後、仕入元詳細の登録ドロワーの 5 欄が金型 Select で、中分類を選ぶまで細分類を選べない。選んだ中分類の子だけが出る | vitest と、PO 目視（○×） |
| K8 便4 後、ProductMasterDrawer.tsx に datalist が 0 件 | `git grep -n datalist frontend/src` が何も出さず、exit 1 で終わる。CI の check-ui-governance は datalist を見ないため、Reviewer が確かめる |
| K9 全便で CI（migration-guard・UI ガバナンス・i18n・ADR 索引）が緑 | PR の CI |

## 維持の仕組み

- 守り手: backend/tests/test_product_format_game_links_pg.py（便2 で FK の試験を足す）
- 守り手: scripts/check-migration-column-churn.js（旧列の ADD を戻さない）
- 対象: 親に合わない細分類が商品に付くこと。親子の置き場が 2 か所に戻ること。
- 親子の保証は DB の FK が持つ（人の注意に頼らない）。
- 便2 の pytest が、FK と細分類削除の動きを CI で毎回確かめる。
- 旧列の ADD を戻さないことを、migration のコメントとチェック 10（column churn）で守る。
- ADR-1038 に「親子の正本は links だけ」と書き、FEATURE-INDEX の「細分類」に足す。

## 10. 外部事例

なし。数値つきの導入事例は見つからなかった（recon §10.9、WebSearch 2026-10-22）。理由は、中間表と複合 FK は一般的な DB の仕組みで、事例として公開される種類の話ではないため。設計の根拠には、次のものを使う。
- PG16 公式文書（sql-createtable の MATCH SIMPLE、sql-altertable のロック）
- 使い捨て PG16.15 での実験（raw/x02）
- 本番の実測（不一致 0 件）

## 11. 未解決（実装カードで確かめるもの）

- (c) 細分類の物理削除の動き → 便2 の試験 (4)
- 便3b の column churn の allowlist → 便3b カード
- （解決済み・Fable 審査）試験の土台: §便2 のとおり。schemas に model_config は無く、既定の extra=ignore なので、古いクライアントが type_master_id を送っても 422 にならない（20_consumers.txt）。
- product_formats の列数の余裕 → 便3b カード
- pmd-field と Select ラベルの重なり → 便4 カード
- （解決済み・reviewer r05/r06/r22）ADR-1038 の番号は空いている
- ADR-1026 側の「Amended by ADR-1038」の追記 → ADR-1038 を Accepted にする PR で行う
- recon §10.3 の実験見出し（raw/x01 :27-28 は組があるので成功）の訂正 → 本 PR で recon を直す
