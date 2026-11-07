# 設計 — S1 段階⑤（会社の行も足せる public の 6 表と別名の入口 2 つの RLS）

> この文書は何か：状態・単位・注記・在庫状況・商品区分・決済手数料の 6 つのマスタ表に、データベース自身が「他社の行を書かせない」守りを付け、別名の入口（ビュー）からもその守りを素通りできないようにする計画です。4 便に分けて 1 便ずつ本番に出します。

- 状態: KGI-7〜9 は **PO 承認済み**（2026-11-07 チャット「1」。問い「この目標で承認する【おすすめ】：設計を書き、確かめてから、1〜2表ずつ作って本番に出すところまで進めます。」への答え）。方向は PO 2026-11-07「ｃ1」（6 表を許可一覧に載せ、次の段で RLS を付ける）。本設計の 4 便の分け方は設計担当の判断で、PO の承認した目標の範囲内（「1〜2表ずつ」）。
- 根拠: [recon.md](recon.md)（以下 R と書く。R§4 は recon の 4 章）。決定の記録: [ADR-1069](../../adr/ADR-1069-shared-master-tables-rls.md)。前例: ADR-1067（段階④）・ADR-1018。
- 自己審査: 同じ AI（Claude Opus）が Planner と Architect を順に担った。独立した第二者の審査ではない。各便のカードの前にクラウドの設計審査を通す。審査の記録: review-opus.md（審査の後に足す）。

## 1. 目的と利用者に見える変化

- 目的: アプリのどこかで会社の絞り込み（`WHERE tenant_id`）を書き忘れても、他社のマスタの行や全社共用の行を、会社の画面から書き換え・削除できないようにする。今は SQL の 1 行だけが守り（R§4-1）。
- 目的 2: 別名の入口 public.conditions・public.units は、今は持ち主（superuser）の権限で元の表を読む（R§3）。元の表に RLS を付けても、ビュー経由の読み書きは素通りする。これを「読む人の権限で読む」に変える。
- 利用者に見える変化: 無い。運営画面・会社の画面の 6 つのマスタの一覧・保存、解析の結果は今と同じ。変わるのは、絞り込みを書き忘れた不具合が起きたときに DB が書込を止める点。
- 対象外: 別名の表（line_condition_aliases・line_unit_aliases とそのビュー）、残りの許可一覧 5 表（meta_page_routing・llm_usage_events・data_deletion_logs・tenant_deletion_audit・products_category_classification_backup）、読取の絞り込み（§8）。

## 2. 型（6 表すべて型C）

| 表 | 型 | 選んだ理由（R の根拠） |
|---|---|---|
| line_conditions・line_units・tcg_note_master・tcg_status_master・tcg_product_categories・payment_fee_settings | 型C: 読取は全行可。作成・変更・削除は自社か運営の文脈だけ | 全行が共用（R§2-1、会社の行 0）。解析は会社で絞らずに全行を読む（R§4-3、tenant_rls_allowlist.py:19-20）。読取を絞ると解析と会社の画面の一覧（共用＋自社を読む。例 note_master.py:152、payment_fee_settings.py:70）が止まる |

- ポリシーは段階④の型C（docs/handoff/s1-rls-stage4/design.md §2-2）をそのまま使う。3 点の決まり（`NULLIF(…, '')`・各 `CREATE POLICY` の前の `DROP POLICY IF EXISTS`・`BEGIN;`〜`COMMIT;`）も同じ。文面は書き写さず、カードに表の名を入れて書く。
- 結果: 共用の行（tenant_id 空）は、運営の文脈からだけ書ける。会社の文脈からは自社の行だけ書ける。

### 2-1. 別名の入口（ビュー）

- `security_invoker = true` を public.conditions と public.units に付ける。元の表の権限と RLS が、ビューを使う人（アプリの接続役 salesanchor_app）に対して効く（PostgreSQL 16 公式文書「CREATE VIEW」、R§3）。
- 権限は足りている: salesanchor_app はビューにも元の表にも `arwd` を持つ（R§2-2）。ビューを使う役は jarvis（superuser）と salesanchor_app だけ。
- 毎回のデプロイで設定が消えない形にする: 古い移行 3 本（R§3 の :52・:42・:47）の `CREATE OR REPLACE VIEW` に `WITH (security_invoker = true)` を足し、さらに末尾の新しい移行で `ALTER VIEW … SET (security_invoker = true)` を流す。古い移行を直さないと、デプロイのたびに「古い移行が設定を消す → 末尾の移行が付け直す」の数秒の間、ビューが持ち主の権限に戻る（RLS が付いた後は、その間の書込が RLS を素通りする）。
  - 古い移行を直す前例: 684563698（20260925_020000 の参照先を直した）、ff63f0981。直すのは WITH を足す 1 か所ずつで、表の形は変えない。
  - 20260922_080000:32・:83 の `CREATE VIEW`（ビューが無いときだけ）は直さない。新しい DB では、その後の 20260925_020000:42（条件なし）が設定付きで作り直す。
- 新しい移行は「ビューのときだけ」流す（`pg_class.relkind = 'v'` で確かめる）。CI の変更 SQL のジョブでは public.units が表として作られているため（R§6）。

## 3. 便の分け方（1 便ずつ: 出す → 本番で確かめる → 次）

| 便 | 表・入口 | 変更 |
|---|---|---|
| ⑤-1 | ビュー 2 つ（RLS はまだ付けない） | ① 新しい移行 migrations/<日時>_set_conditions_units_security_invoker.sql（§2-1。DO の中で relkind='v' を確かめて `ALTER VIEW public.conditions SET (security_invoker = true)`・同 units）② 古い移行 3 本に `WITH (security_invoker = true)` ③ backend/app/ops/tenant_rls_allowlist.py に `INVOKER_VIEWS: dict[str, str]`（ビュー名 → 理由）を足す（正本はこの 1 か所） ④ scripts/check_public_tenant_rls.py に「INVOKER_VIEWS の各ビューが relkind='v' で reloptions に `security_invoker=true` を持つ。無い・設定が無いなら落とす」を足す ⑤ backend/tests/test_check_public_tenant_rls.py に試験を足す |
| ⑤-2 | line_conditions・line_units | ① RLS の移行（2 表・型C） ② `_operator_writes`（super_admin_suppliers.py:58）を backend/app/auth/dependencies.py に `operator_writes` の名で移し、super_admin_suppliers.py はそれを import する（中身は変えない） ③ super_admin_conditions.py の 4 本（:167・:239・:275・:377）と super_admin_units.py の 4 本（:146・:178・:213・:382）に `@operator_writes` ④ 状態の確定 backend/app/services/tcg_condition_review_svc.py:399 の直前に `await db.execute(text("SET LOCAL app.is_operator = 'true'"))`（§3-1） ⑤ 許可一覧から 2 行を消す ⑥ CI の変更 SQL のジョブの前提の表に tenant_id 列を足す（§3-2） ⑦ 試験 |
| ⑤-3 | tcg_note_master・tcg_status_master | ① RLS の移行（2 表） ② super_admin_note_master.py の 4 本（:164・:197・:232・:334）と super_admin_status_master.py の 4 本（:161・:206・:259・:360）に `@operator_writes` ③ 許可一覧から 2 行 ④ CI の前提の表に列 ⑤ 試験 |
| ⑤-4 | tcg_product_categories・payment_fee_settings | ① RLS の移行（2 表） ② super_admin_product_categories.py の 4 本（:135・:235・:293・:328）と super_admin_payment_fee_settings.py の 3 本（:88・:121・:156）に `@operator_writes` ③ 商品詳細の保存 backend/app/services/tcg_product_detail_svc.py:258 の `SET LOCAL app.is_operator = 'true'` を :156 の `try:` の直後（:158 の鍵の前）へ移す（§3-1） ④ 許可一覧から 2 行（残り 5） ⑤ CI の前提の表に列（tcg_product_categories だけ。payment_fee_settings は :864 にある） ⑥ 試験 |

- 順番の理由: ⑤-1 を先に出すのは、ビューの読み方を変えても RLS が無いうちは結果が同じで（権限は足りている）、この便だけで安全に確かめられるため。RLS を先に付けると、ビュー経由の書込が素通りする期間ができる。⑤-2 は書込の入口が多く鍵の穴（状態の確定）がある 2 表なので、先に済ませて型を固める。⑤-4 は商品詳細の保存に触るので最後。
- 運営画面の入口 23 本（R§4-2）は、その表に RLS が付く便と同じ便で包む。包んだだけなら RLS が無くても動く（運営の文脈は今の RLS 付きの表では読める範囲を広げるだけ）。
- `@operator_writes` は関数の引数 `db` を名前で取る（super_admin_suppliers.py:58-）。23 本すべてに `db: AsyncSession = Depends(get_db)` があることを確かめた（関数の宣言を読んだ）。
- 各便は migration を含むので危険パス。GO は ADR-136 の手順、委任 GO は ADR-1003 の範囲で Opus が出す（段階④と同じ）。
- 移行の置き場所と登録: 1 便 1 ファイル。scripts/run_all_migrations.sh の末尾に `run_sql migrations/<ファイル>` を 1 行足す（段階④と同じ）。

### 3-1. 行に鍵を掛ける 2 か所（R§5）

- 型C の後、文脈の無い接続から共用の行に `FOR SHARE` を掛けると、エラーにならず鍵が 0 行になる（UPDATE のポリシーの USING が黙って絞る。PostgreSQL 16 公式文書「CREATE POLICY」）。2 か所とも運営専用の入口で、文脈を張っていない。
- 状態の確定（⑤-2）: :399 の直前に `SET LOCAL app.is_operator = 'true'` を置く。取引の終わりで自動的に元に戻る（商品詳細の保存 :258 と同じ書き方）。鍵の掛け方は今と同じ（行ごとの FOR SHARE）。
  - 同じ取引の後の文（:402 の商品の `FOR SHARE OF p`、:434 以降の書込）にも運営の文脈が効く。運営の文脈は見える・書ける範囲を広げるだけで、狭めることはない（各ポリシーは `… OR is_operator`）。:402 は今は共用の商品に鍵が掛かっていない穴（R§5 の既存の穴）で、この変更で注記どおり鍵が掛かるようになる。これは注記（:397-398「穴は認めない」）の意図どおりの動きで、運営専用の短い取引なので待ちの増え方は小さい。
  - 選ばなかった案: `LOCK TABLE public.line_conditions IN SHARE MODE`。文脈に頼らない点は良いが、鍵の強さが変わり（新しい行の追加も待たせる）、待ちの組み合わせが今と変わる。今と同じ鍵の掛け方を保つ案を選んだ。
- 商品詳細の保存（⑤-4）: :258 の `SET LOCAL` を :156 の `try:` の直後へ移す。:210 の区分の確かめ（`FOR SHARE`）が共用の区分を見つけられるようになる。:158 の商品の `FOR UPDATE` も共用の商品に実際に鍵が掛かるようになる（今は運営の文脈が後から張られるため掛かっていない）。入口は運営専用（tcg_product_import.py:330-331）なので、運営の文脈を先に張っても見える範囲は運営として正しい。

### 3-2. CI の変更 SQL のジョブの前提の表（R§6）

- `PUBLIC_SQL`（.github/workflows/migration-test.yml:480）の 5 表の定義に tenant_id 列が無い。RLS の移行が落ちるので、その便の表の定義に `tenant_id INTEGER`（本番で外部参照があるものは本番と同じ `REFERENCES public.tenants(id)`。根拠は R§7 の 20260920_0X0000 の各 ADD COLUMN の行）を 1 行足す。定義を足す場所は既存の定義の中で、新しい表は作らない。
- 前提の移行を先に流す step（段階④ ④-2・④-4 の型）は使わない。理由: このジョブでは units と line_units が別々の表として作られていて（:528・:543）、20260920_030000 は public.units にしか列を足さないため、line_units に列が付かない。
- 全件ドライラン（:1385）は実物の移行から 6 表とビューを作る（除外一覧に無い、R§6）。追加の準備は要らない。

## 4. 試験（実 PostgreSQL・アプリの接続役。前例: backend/tests/test_tenant_budget_settings_rls.py）

- 本物の移行を当てて試す（表の定義を試験に書き写さない。test-schema-dup の見張り）。使い捨て DB に backend/tests/rls_bootstrap.py の `_ensure_public_users`（tenants）・`bootstrap_public_products`（20260919_020000 が public.products を参照するため）を流してから、run_all_migrations.sh の順で R§7 の移行（表を作る → tenant_id を足す → 名前の付け替えとビュー → 列の追加とビューの作り直し）を当て、最後にその便の移行を当てる。当てる一覧はカードを書くときに `git grep -l <表> -- migrations` と run_all の行番号で作り直す。通らない移行があれば、理由（足りない前提）を記録して止まり、Opus に戻す（推測で定義を書き足さない）。
- 会社番号は他の試験と重ならない番号（カードで決める。例 986・987）。
- 型C の項目（段階④ §4 と同じ）: ①文脈なし・他社文脈で SELECT が全行 ②他社の tenant_id で INSERT が 42501 ③他社の行の UPDATE・DELETE が 0 行 ④運営文脈（`app.is_operator='true'`・`app.tenant_id=''`）で他社の行の UPDATE が 1 行 ⑤同じ移行を 2 回当ててもエラーにならない ⑥自社文脈で自社の行の tenant_id を他社へ付け替える UPDATE が 42501。⑦共用の行（tenant_id 空）を会社の文脈から UPDATE すると 0 行・運営の文脈からは 1 行。
- ビュー経由（⑤-2）: ⑤-1 の移行を当てた後、public.conditions・public.units を通して ②③⑦ を同じように確かめる（ビュー経由でも 42501・0 行）。
- ⑤-1: ①ビュー 2 つの reloptions に `security_invoker=true` がある ②古い移行 3 本と新しい移行を 2 回流しても設定が残る ③ check_public_tenant_rls.py の新しい確かめが、設定の無いビュー・ビューが無いときに落とし、設定があるときに通る（backend/tests/test_check_public_tenant_rls.py）。
- 運営画面: 便ごとに、その便の表の運営画面の作る・変える・消すを、`SET app.tenant_id=''` の済んだアプリの接続役の接続で呼んで通る。終わった後に `app.is_operator` が空に戻る（段階④ ④-5 の試験の型）。
- 鍵（⑤-2・⑤-4）: アプリの接続役で、状態の確定・商品詳細の保存の取引を鍵の後で止めた状態で、別の接続から共用の行に `SELECT … FOR UPDATE NOWAIT` を掛けると「鍵が取れない」（55P03）になる。試験の書き方はカードで決める。
- 既にある試験への影響: 6 表に触るファイルは backend/tests に 40 本（R§6）。カードには、その便の表に触るファイルを列挙し、CI の Backend Tests が全部緑であることを合格の条件にする。RLS のせいで落ちた試験は、試験の側で文脈を張って直す（ポリシーを緩めない）。test_tcg_condition_review.py の文の確かめ（:414 付近）が新しい `SET LOCAL` の文で崩れるなら、確かめの対象を足す。

## 5. 受入条件（KGI は docs/specs/tenant-rls/kgi.md の KGI-7〜9）

| 基準 | 検証方法 |
|---|---|
| K7-1 6 表すべてが本番で RLS 有効（ENABLE と FORCE）でポリシー 4 本 | 各便の反映後、reader 鍵の道で `pg_class.relrowsecurity / relforcerowsecurity` と `pg_policies` の件数を読む（反映前は 6 表とも False/False・0 本、R§2-2） |
| K7-2 ビュー 2 つが `security_invoker=true` | ⑤-1 の反映後と、以後の各便の反映後に reader 鍵の道で `pg_class.reloptions` を読む（反映前は空、R§2-2） |
| K7-3 反映の前後で 6 表の行数が変わらない（計 171） | reader 鍵の道で R§2-1 と同じ集計を反映の前後に流し、表ごとに一致 |
| K8-1 各便の反映後 24 時間、backend・worker・beat のログに 42501・`row-level security`・`invalid input syntax` が 0 件 | 反映時刻以降の `docker logs` を数える（段階④ K5-1 と同じ数え方） |
| K8-2 その便の表の保存が本番で動く | 運営画面でその便のマスタを 1 件、同じ値のまま保存して 200（⑤-2 は状態・単位、⑤-3 は注記・在庫状況、⑤-4 は商品区分・決済手数料と商品詳細の保存）。会社の画面の保存は本番に会社の行が 0（R§2-1）のため、反映後の backend のログで会社の画面の保存の道に 4xx・5xx が 0 件であることで見る（使われた回数も書く。0 回なら「使われず未観測」と書く） |
| K8-3 解析の結果件数が減らない | reader 鍵の道で、反映前の同じ長さの時間帯と反映後の解析の結果件数を数えて並べる（投稿の数の差も一緒に書く） |
| K9-1 他社の文脈からの書込を DB が拒否する（6 表・ビュー経由） | CI の Backend Tests が緑で、PostgreSQL のログに 6 表それぞれ `violates row-level security policy` が 1 件以上 |
| K9-2 全移行の後もビューの設定が残ることを CI が確かめる | 全件ドライランの後の check_public_tenant_rls.py が緑で、ログにビュー 2 つの確かめの行が出る |
| K9-3 許可一覧が 11 → 5 | ⑤-4 の後の backend/app/ops/tenant_rls_allowlist.py の件数 |

## 6. リスクと対処

| リスク | 対処 |
|---|---|
| 運営画面の書込に運営の文脈が無いと、INSERT は 42501、UPDATE・DELETE は静かに 0 行（段階②b の教訓） | 23 本を全部数えた（R§4-2）。RLS を付ける便と同じ便で包む。試験で運営画面の作る・変える・消すを確かめる。反映後に K8-1・K8-2 |
| 行の鍵が静かに外れる | 41 か所を全部読み、6 表に触る 2 か所を直す（§3-1）。試験で鍵が掛かることを確かめる |
| デプロイのたびに古い移行がビューの設定を消す | 古い移行 3 本も直す（§2-1）。CI の全件ドライラン（2 周）の後に設定が残ることを確かめる（K9-2） |
| 古い移行を直すと、変更 SQL のジョブでその古い移行が流れ、今の前提の表で落ちるかもしれない（まだ確かめていない） | ⑤-1 の CI で確かめる。落ちたら理由を記録して止まり、Opus に戻す（推測で前提を書き足さない） |
| ビューを「読む人の権限」に変えて権限不足になる | salesanchor_app はビューと元の表に arwd を持つ（R§2-2）。⑤-1 は RLS を付けずに出し、反映後のログで 42501・permission denied を数える |
| 会社の行を足す会社が現れたときに読めなくなる | 型C の読取は全行。読み方は今と同じ |
| 運営の文脈がつなぎの使い回しで残る | `operator_writes` は finally で reset。`get_db` の終わりの clear_tenant_context（database.py）が二重の守り。`SET LOCAL` は取引の終わりで消える |
| デプロイ中の約 70 秒、reader 鍵の道が使えない | 数分おいて流し直す（ADR-1024 の運用） |

## 7. 戻し方

- 段階④ §7 と同じ順番と道で戻す（戻しの PR を作り GO を受ける → 走っているデプロイ 0 件を確かめる → 戻しの SQL を無制限鍵で `docker exec -e PGOPTIONS="-c lock_timeout=1s" -i astro-webapp-postgres-1 psql -U jarvis -d jarvis_db -v ON_ERROR_STOP=1` で流す → reader 鍵の道で確かめる → すぐに戻しの PR を main に入れる → デプロイ → もう一度確かめる）。
- ⑤-2〜⑤-4 の戻しの SQL: `BEGIN;` → 表ごとに `DROP POLICY IF EXISTS <表>_select/_insert/_update/_delete` → `ALTER TABLE … NO FORCE ROW LEVEL SECURITY` → `ALTER TABLE … DISABLE ROW LEVEL SECURITY` → `COMMIT;`。データは変えないので行は失われない。コードと RLS は 1 つの戻しの PR でまとめて戻す（運営の文脈を張るコードは RLS が無くても動くので、コードを残して RLS だけ戻してもよい。その場合は移行のファイルと run_sql の行だけを消す PR にする）。
- ⑤-1 の戻しの SQL: `ALTER VIEW public.conditions RESET (security_invoker); ALTER VIEW public.units RESET (security_invoker);`。⑤-2 以降が出た後に ⑤-1 だけを戻すと、ビュー経由の書込が RLS を素通りする。⑤-1 を戻すのは ⑤-2〜⑤-4 をすべて戻した後だけにする。
- 移行は、migrations/**・scripts/**・backend/** などを含むデプロイのたびにすべて流れ直す（段階④ §7 の根拠: .github/workflows/deploy.yml:38-43・:765・:73-78）。戻しの SQL だけでは次のそういうデプロイでまた付くので、戻しの PR と同じ便で行う。

## 8. 触らない範囲・後続

- 触らない: 別名の表 2 つとそのビュー、許可一覧に残る 5 表、会社スキーマの表、画面（frontend）、読取の絞り込み。
- 後続（本段階の対象外。必要になったら PO に聞く）:
  - 別名の表（line_condition_aliases・line_unit_aliases）の tenant_id の有無と型の調べ。
  - CI の確かめに「FORCE の有無とポリシーの中身」を足す（今の確かめは RLS の有無だけ）。
  - public の他のビューで、RLS の付いた表を持ち主の権限で読むものが無いかの全数の確かめ。
  - tcg_condition_review_svc.py:402 は §3-1 で鍵が掛かるようになるが、他の入口の `FOR SHARE OF p` の全数は調べていない。

## 9. 外部・過去事例の参照と我々への応用

- 社内の前例（直接の根拠）: 段階④（ADR-1067）で 8 表に型A／型C を付け、各便の反映後に 42501・row-level security を数えた（docs/specs/tenant-rls/kgi.md KGI-5）。段階②b で「書込の入口に運営の文脈が無いと UPDATE が静かに 0 行」を見つけ、入口を全部数えてから出す手順にした。本設計 R§4・R§5 はその手順に従った。
- 外部の仕様: PostgreSQL 16 公式文書（2026-11-07 取得）。
  - 「CREATE VIEW」: `security_invoker` を true にすると、元の表の権限と RLS が「ビューを使う人」に対して確かめられる。既定では持ち主の権限で読む。`CREATE OR REPLACE VIEW` は WITH の設定を置き換える（ソース src/backend/commands/view.c:191-200 でも確かめた）。適用: ビュー 2 つに設定を付け、作り直す古い移行にも同じ設定を書く。
  - 「CREATE POLICY」: `SELECT … FOR UPDATE / FOR SHARE` には UPDATE のポリシーの USING も当たり、条件に合わない行は黙って外れる。適用: 鍵を掛ける 2 か所の前に運営の文脈を張る。
  - 「LOCK」: 表に UPDATE・DELETE・TRUNCATE の権限があればどの強さの鍵も掛けられ、RLS は効かない。適用: 選ばなかった案（§3-1）の判断材料。
  - 「5.8. Row Security Policies」: superuser・BYPASSRLS の役には効かない。表の持ち主には FORCE を付けたときだけ効く。適用: FORCE を付ける。reader 鍵の窓口（BYPASSRLS の役）の数え方は変わらない。
  - Context7 は月の上限に達して使えなかったため、起動指示の許可に従い公式文書とソースを直接読んだ。
- 外部の導入事例の数値は使わない。理由: 本段階は社内の前例（段階④）と同じ型の繰り返しで、判断の根拠は社内の実測と公式の仕様で足りる。

## 10. PO に決めてもらうこと

- 決めることはありません（KGI-7〜9 は承認済み。4 便の分け方は承認された「1〜2表ずつ」の範囲内）。

## 維持の仕組み

- 守り手: CI。新しく会社の列を持つ表を public に作って RLS を付け忘れると、全件ドライランの後の scripts/check_public_tenant_rls.py が落とす（許可一覧に理由を書かない限り）。⑤-1 からは、許可一覧の INVOKER_VIEWS に載せたビューの設定が消えても同じ確かめが落とす。
- 正本は backend/app/ops/tenant_rls_allowlist.py の 1 か所（表とビューの両方）。ほかに写さない。
- 型の選び方（型A／型C／付けない）は ADR-1067・ADR-1069 に残し、次の表もこの表で判断する。
