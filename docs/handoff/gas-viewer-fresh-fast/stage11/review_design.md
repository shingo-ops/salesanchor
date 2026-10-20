# 審査: 段11 閲覧者向け文面のテンプレートページ（design_stage11.md）

- 審査者: Architect（読み取りのみ。ファイル編集は本書のみ）
- 基準: `git fetch -q origin main` 後の origin/main = 38613d7d7（設計の基準 386727908 からの差は #4576 段10 便3 の5ファイルのみ。recon2 §7 は便3 の行番号まで反映済みで、差は無い）
- 生の検索結果: /tmp/CC報告ファイル/viewer_templates/tpl_page/review_raw/grep_uses.txt（9定数・4関数・notify_status_change・send_room_notice の `git grep -n`、77行）

## 判定: REVISE

方向（正本を DB の1か所へ、migration は構造だけ、既存の金型だけ、便1/便2 分割）は妥当で、既存 ADR と食い違いはない。ただし、(1) 本番での初期値投入の実行経路が PO 決定 Q12=n と食い違っている、(2) 「テンプレートが読めないときは送らない」を後戻りできない処理の後で判定する箇所があり、パスワードや申込コードが失われる、(3) 作り直し案内の「さん、」を外す処理が本文の書き出しに依存していて編集で壊れる、(4) 便2 の後に空の環境を埋める手段が無い、(5) お知らせが送れなかったことが画面に出ない、の5点が未設計。Generator に渡すと判断を任せることになるため差し戻す。

## 観点ごとの結果

### ① 11-1 の file:line と実物の一致 — ○
実物で確かめた（全て origin/main）:
- backend/app/discord_gateway/viewer_bot_texts.py:30-42（ROOM_WELCOME/ROOM_RECREATED）、:68-98（SIGNUP_URL〜INTERVIEW_REQUEST）、:133-159（4関数）一致
- frontend/src/pages/inbox/InboxPage.tsx:81-91、frontend/src/App.tsx:281-289・:342 一致
- frontend/src/pages/super-admin/ViewerAccountsPage.tsx:90・:187-195・:272-284・:371-384・:410-416・:421-438・:453-462 一致
- frontend/src/components/PageLayout.tsx:8・:27、Drawer.tsx:22-32、Textarea.tsx:62-71、DataTable.tsx:100 一致。docs/CC_UI_GOVERNANCE.md:9-15 一致
- backend/app/main.py:650、backend/app/auth/dependencies.py:516-518、backend/app/models.py:25 一致
- migrations/20260608_080000_add_carrier_credentials.sql:21、migrations/20261018_100000_create_product_packagings.sql:52-60 一致
- viewer_trial.py:206・:381、viewer_interview_notice.py:80、viewer_discord_cli.py:114、super_admin_viewers.py:142-143・:258、services/viewer_room_notice.py:44-57、services/discord_notifier.py:37 一致
- docs/handoff/gas-viewer-fresh-fast/design.md:277-281（D6）・:838（10-3）一致

### ② SSOT・ADR との整合 — 概ね○（直す点あり）
- ADR-1007:31-36／ADR-155:25-32：migration は表だけ → ○。ただし ADR-1007:36「1回だけのデータの変更：PO の合意、DRY-RUN → COMMIT、docs/handoff/<topic>/ に記録」の DRY-RUN が seed CLI に無い（B-1）。
- ADR-027：画面の言葉は i18n、本文は i18n に入れない → ○（本文はデータなので妥当）。
- ADR-144/067：PageLayout・DataTable・Drawer・Textarea・Button だけ、新しい金型なし → ○。
- ADR-1019（docs/adr/ADR-1019-inventory-viewer-separate-accounts.md 全40行）に文面の置き場所の記述は無く、食い違いなし。食い違うのは段10 の設計 design.md:838「文面は全部 viewer_bot_texts.py に置く」で、段11 がこれを置き換えることを design.md 側に書く必要がある（N-7）。
- 便1〜便2 の間：DB は定数の写しで、画面からは変えられない → 食い違いは起きない（11-4 の説明は正しい）。ただしこの間に別の PR が定数を直すと DB の写しが古くなる。11-6「便2 の deploy 前に T3 を必ず○」で拾える → ○。
- **食い違い（Blocking）**：11-3「本番で1回だけ Opus が実行（PO 委任・GO 記録）」は、段10 までの PO 決定 Q12=n（design.md:606「委任しない。Claude の経路の操作は、今までどおり毎回 PO 本人の GO」）と、操作の GO の条件（design.md:561「無制限鍵の操作を Sonnet に頼むときは PO が permit-danger.sh を1回実行したチケットを証拠にする」）、CLAUDE.md「無制限鍵は人間の明示許可があるタスクでのみ」に反する。制限付き鍵では DB に書けない（design.md:559）→ B-1。

### ③ 送る側9件の切り替えの漏れ — 呼び出し元は漏れなし、テストと順序に不足
`git grep -n` の結果（review_raw/grep_uses.txt）で、本番コードの呼び出し元は設計 11-1 の7か所＋ notify_status_change の呼び元2か所（super_admin_viewers.py:181、viewer_admin_cli.py:30）で全部。漏れは無い。
直す必要があるテスト（設計に列挙が無い。N-5）:
- backend/tests/test_super_admin_viewers.py:89・:531・:561・:567・:571・:596
- backend/tests/test_viewer_discord_trial.py:294-296・:302・:312・:319・:897
- backend/tests/test_viewer_room_notice.py:42-44・:47-52・:64-68
- backend/tests/test_viewer_interview_notice.py:80・:132-133
- 注意：test_viewer_discord_trial.py は `_db_factory(lambda ...: next(rows))`（:247）のように DB の結果を順番で返すモックを使う。テンプレートの読み出しが1回増えると順番がずれる。PG のテスト（test_super_admin_viewers.py:4・:26-27）は migration を個別に流す形なので、新しい migration をテストの準備に足す必要がある。
- frontend/api-contract/openapi.json：GET/PUT の追加で .github/workflows/api-contract-check.yml:50-53 が落ちる。再生成が要る（N-5）。

### ④ sync→async 化の影響 — 呼び出し元ごとの扱いが未設計（Blocking）
| 箇所 | DB セッション | 今の順番 | 問題 |
|---|---|---|---|
| viewer_trial.py:381 ROOM_WELCOME | db_factory あり。:368 で commit 済み | 申込コードの照合・パスワードのハッシュ保存・commit の後に送る | commit 後に「テンプレートが無いので送らない」とすると、パスワードの平文は手元から消え、本人に届かない。申込コードも使用済み。**読み出しは照合の前（:232 以降の早い段階）にし、無ければ TRY_LATER で何も変えずに返す**必要 |
| viewer_trial.py:206 ROOM_RECREATED | db_factory あり | 部屋を作る（:186）→ 保存 commit（:199）→ 送る | 送れないなら部屋だけ作られる。**:186 の前に読み、無ければ TRY_LATER** |
| super_admin_viewers.py:258 reissue | db あり | 申込コードを作り直して commit（:250）→ 招待作成 → 文面 | commit 後の 503 は、作り直した申込コードを画面に出さずに古いコードを無効にする。**reissue_signup_code（:246）の前に読み、無ければ 503 で何も変えない** |
| super_admin_viewers.py:142 signup_request | db 引数なし | — | `db: AsyncSession = Depends(get_db)` を足す。副作用なし |
| services/viewer_room_notice.py:44-70（④） | db 引数なし。呼び元 _change（:158 db あり、:176 commit）と viewer_admin_cli.py:24-28（with の外で呼ぶ） | commit の後に送る（10-3 の決まり「DB を開けたまま Discord を待たない」design.md:840） | commit 後に同じ session で読むと、Discord を待つ間トランザクションが開いたままになる。**読み出しは commit の前（同じトランザクション内）に行い、文を作ってから commit → 送る**、CLI も with の中で読む。状態の変更そのものは止めない（10-3「送れなくても操作は成功」） |
| viewer_interview_notice.py:80 | `_load_trials(db_factory)`（:49-61）で開いて閉じる | — | `run_once` の最初に1回読む。無ければ警告ログを1回出して 0 を返す（Redis キーは作らないので次の1時間で再試行）|

### ⑤ 編集の検査（string.Formatter） — 方向は○、書き方を確定させる必要（Non-blocking）
- `{{` `}}`：parse では文字として扱われ、項目にならない → 問題なし（送ると `{` になる）。ただし `{{email}}` と書くと項目が消えるので①の集合検査で 422 になる → 期待どおり。
- `{a.b}` `{a[0]}`：parse の field_name は "a.b"／"a[0]" の文字列。**field_name を `.` や `[` で切らずに文字列のまま台帳の集合と比べる**と書けば 422 になる。切って比べると通ってしまい、送るときに属性参照が起きる。
- `{}` `{0}`：field_name は "" ／ "0" → 集合に無いので 422。これも文字列のまま比べることが条件。
- `{email:>10}` `{email!r}` `{email:{x}}`：format_spec／conversion が空でなければ 422（設計どおり）。入れ子は format_spec に入るのでこれで止まる。
- `abc}` `{abc`：parse は遅延評価で、回したときに ValueError が出る。**`list(Formatter().parse(body))` を try の中で回し切る**ことを明記。
- 送るときの差し込みも、DB を直接直された場合に備えて同じ検査を通し、失敗は「行が無い」と同じ扱いにする（例外を外へ出さない）。
- 長さ：本文 1800 以下でも、差し込み後は email（最大254）・invite_url などで 2000 を超え得る（例：1800−7+254＝2047）。Discord は 2000 超を拒否する。**送る直前に差し込み後の長さを数え、2000 を超えたら送らない（自動は警告ログ、コピーは 422 か文をそのまま返すかを決める）**か、本文の上限を下げる（N-3）。

### ⑥ seed CLI と本番実行の安全さ — 経路が未確定（Blocking）
- CLI の形（stdin JSON だけ、SQL を受けない、無い行だけ INSERT＝`ON CONFLICT (key) DO NOTHING`、本文を出さない）は viewer_discord_cli.py の前例どおりで○。
- 足りない：DRY-RUN（ADR-1007:36）、実行の経路（どの鍵・誰の GO）、記録の置き場所（docs/handoff/<topic>/）。
- 便2 で seed と定数を消すと、テスト環境・リハーサル環境・作り直した DB では9行を入れる手段が無くなる。PUT は「画面で開いた時の updated_at と違えば 409」なので、行が無いと保存もできない（B-4）。

### ⑦ 受け入れ基準の○×判定 — 概ね○、足りない基準あり
- T1〜T6 は pytest/vitest で○×が出る。T3 は CLI の鍵ごとの一致で○×が出る。
- T7 は検索式が無い。T8 は本番の実際のお客様向け文を直すので、どれを直してどう戻すかが無い（N-8）。
- ④の B-2 の順番（テンプレートが無いとき申込コード・パスワード・部屋・申込コードの作り直しが変わらない）を確かめる基準が無い（N-8）。

### ⑧ ルートと API パスの衝突 — ○
- 画面 `/super-admin/viewer-templates`：App.tsx の Route は平置きで、`/super-admin/viewers`（:342）とは別の文字列。`viewer-templates` を含む Route・API は origin/main に0件（`git grep -n -E "viewer-templates|viewer_templates|viewer_message_templates|ViewerTemplates|superAdminViewerTemplates" origin/main` → docs/handoff/gas-viewer-fresh-fast/design.md:807 の /tmp パスの1件だけ）。
- API `GET /api/v1/super-admin/viewer-templates`・`PUT .../{key}`：既存の `/super-admin/viewers/{viewer_id}`（super_admin_viewers.py:186）とは最初の区切りが違うので衝突しない。

## 直すべき点（具体的な文案）

### Blocking
**B-1 本番での初期値投入の経路（11-3「初期値の入れ方」を置き換え）**
> 初期値の入れ方：migration は表だけ。専用 CLI `python -m app.viewer_template_cli` は stdin の JSON `{"action":"seed","dry_run":true|false}` と `{"action":"verify"}` だけを受ける。seed は viewer_bot_texts.py の今の9つの定数を読み、無い行だけ `INSERT ... ON CONFLICT (key) DO NOTHING` で入れる。dry_run=true は入れる予定の鍵だけを返して書かない。verify は鍵ごとに「行がある／本文が定数と一字一句同じ」を ○× で返す（本文は出さない）。本番では DB に書くので無制限鍵が要る。Q12=n と操作の GO の条件（design.md:561）のとおり、実行の前に PO へ3行で報告し、PO 本人の GO と、Sonnet が実行する場合は PO が `bash scripts/permit-danger.sh "<操作>"` を1回実行したチケットを受けてから、dry_run → seed → verify の順で行う。結果と GO 原文は docs/handoff/gas-viewer-fresh-fast/ に残す。

（別案として、ADR-1007 ①「アプリ画面」の経路で、super admin のページに「初期の文を入れる」ボタン〔行が無い鍵だけ定数から入れる。便2 で消す〕を置けば無制限鍵が要らない。どちらにするかを設計で決める。）

**B-2 「送らない」を判定する順番（11-3「送る側」に追記）**
> テンプレートは、後戻りできない処理より前に読む。無い・検査に通らないときは何も変えずに止める。
> - 部屋のはじめの案内（viewer_trial.py on_code_submit）：申込コードの照合より前に読む。無ければ TRY_LATER を返し、申込コードは使用済みにせず、部屋も作らない。
> - 部屋の作り直しの案内（viewer_trial.py on_open）：部屋を作る（:186）前に読む。無ければ TRY_LATER。
> - 申込コードの作り直し（super_admin_viewers.py reissue）：reissue_signup_code（:246）の前に読む。無ければ 503、申込コードは変えない。
> - 延長・本登録・停止のお知らせ（_change、viewer_admin_cli）：状態の変更と同じトランザクションの中で commit の前に読み、文を作る。無くても状態の変更は行い、お知らせは送らない（B-5）。commit の後に DB を読まない（Discord を待つ間トランザクションを開けない、design.md:840）。
> - 面談のお願い（viewer_interview_notice.run_once）：最初に1回読む。無ければ警告ログを1回出し、誰にも送らず 0 を返す（Redis キーは作らない）。
> - 申込のお願い（signup-request）：`db` を受け取り、無ければ 503。

**B-3 作り直し案内の名前が空のとき（11-3「編集の検査」に追記）**
> 今の reissue_notice_text は LINE 名が空のとき `removeprefix("さん、")`（viewer_bot_texts.py:152-153）で頭を外しており、本文が `{line_name}さん、` で始まることに頼っている。reissue_notice と reissue_notice_no_invite は、本文が `{line_name}さん、` で始まらなければ 422 にする（画面に理由を出す i18n キーを足す）。差し込みの後、名前が空なら今と同じく頭の「さん、」を外す。

（別案：名前が空のときの代わりの言葉を台帳に持つ。どちらにするかを決める。）

**B-4 行が無い環境の埋め方（11-3 PUT・11-4 便2 に追記）**
> PUT は、画面から `expected_updated_at: null` が来て行が無いときは INSERT する（ある場合は 409）。行があるときは `UPDATE ... SET body=:b, updated_by_user_id=:u, updated_at=now() WHERE key=:k AND updated_at=:expected` の更新件数が0なら 409。一覧 GET は台帳の9件を必ず返し、行が無い鍵は body=null・「未登録」と表示し、スライドで本文を入れて保存できる（便2）。これで、seed と定数を消した後の新しい環境やテストでも画面から9行を入れられる。

**B-5 お知らせが送れなかったことを画面に出す（11-3「送る側」・11-5 に追記）**
> 延長・本登録・停止でテンプレートが無い・検査に通らないときは、応答を `room_notice: "no_template"`、`room_notice_text: null` にする（ViewerStatusChangeResponse の Literal に足す。openapi.json を再生成）。閲覧者管理（ViewerAccountsPage.tsx:259-261）は no_template のとき「テンプレートが見つからないため、部屋に送れませんでした。テンプレートの画面で文を確かめてください」（新しい i18n キー superAdmin.viewers.roomNoticeNoTemplate、ja/en）を出す。今のままでは room_notice_text が null だと何も出ず、PO が気づけない。

### Non-blocking
- **N-1 migration**：`REFERENCES public.users(id) ON DELETE SET NULL` と書く（migration-guard.yml:219 の参照先検査に合わせる）。GRANT は `GRANT SELECT, INSERT, UPDATE ON public.viewer_message_templates TO salesanchor_app;` で、SEQUENCE の GRANT は書かない（key が TEXT で sequence が無い。add_viewer_accounts.sql:111 をそのまま写すと失敗する）。updated_at は PUT の SQL で `now()` を入れるか、product_packagings と同じ trigger を付けるか、どちらか一方に決めて書く。
- **N-2 409 の比べ方**：B-4 のとおり SQL の WHERE で比べる（文字列にして Python で比べない。マイクロ秒の丸めで誤判定するため）。
- **N-3 長さ**：送る直前に差し込み後の長さを数え、2000 を超えたら送らない（自動は警告ログ、コピーの API は文を返す。LINE は 2000 の制限と無関係のため）。画面は Textarea の helperText に「n / 1800」を出す（Array.from で数える。ViewerAccountsPage.tsx:147-151 の前例）。
- **N-4 検査の書き方**：⑤の4点（field_name を文字列のまま比べる、`list(Formatter().parse())` を try の中で回し切る、送るときも同じ検査を通し失敗は行が無いのと同じ扱い、`{{` `}}` は文字として許す）を 11-3 に明記。
- **N-5 Generator が触るテストと生成物**：③のテスト4ファイルの行、PG テストの準備への新 migration の追加、MagicMock の db_factory の順番、frontend/api-contract/openapi.json の再生成、新ページの vitest、ja.json/en.json の追加キー一覧（nav.superAdminViewerTemplates、superAdmin.viewerTemplates.*、B-3/B-5 のエラー文）を設計に列挙する。
- **N-6 更新者の表示名**：public.users の `full_name`、空なら `username`（models.py:27-29）と決める。
- **N-7 記録**：段11 を docs/handoff/gas-viewer-fresh-fast/design.md に追記してコミットし（recon.md・recon2.md も docs 側へ）、10-3 の「文面は全部 viewer_bot_texts.py に置く」（:838）を「段11 便2 で DB へ移した」と注記する。便2 で viewer_bot_texts.py:1 の「SSOT」と冒頭の利用箇所の説明を直す。便2 で残すもの（SIGNUP_URL、format_jst_date、format_jst_datetime、external_browser_url、RECEPTION_MESSAGE ほか対象外の定数）を明記する。
- **N-8 受け入れ基準の足し**：
  - T7 の検索式：`git grep -n -E "^(SIGNUP_REQUEST|REISSUE_NOTICE|REISSUE_NOTICE_NO_INVITE|ROOM_WELCOME|ROOM_RECREATED|NOTICE_EXTENDED|NOTICE_ACTIVATED|NOTICE_SUSPENDED|INTERVIEW_REQUEST) =" origin/main -- backend/app` が0件。
  - T9（新規）：テンプレートの行が無いとき、①申込コードを入れても申込コードは使用済みにならず部屋も作られない、②作り直しで申込コードが変わらない、③延長の応答が room_notice="no_template" で状態は変わる — pytest。
  - T8：直すのは手で送る「申込のお願い」1件に限り、確かめた後に元の文へ戻す（自動で送る文では試さない）。
- **N-9 基準のコミット**：11-1 の「origin/main 386727908 以降」を 38613d7d7 に更新（差は #4576 のみで内容は反映済み）。

## 未解決事項（Planner/PO が決めること）
1. 初期値を本番に入れる経路：CLI（PO 本人の GO＋permit-danger）か、画面のボタン（無制限鍵不要）か（B-1）。
2. 作り直し案内の名前が空のとき：書き出しを `{line_name}さん、` に固定するか、代わりの言葉を持つか（B-3）。
3. 差し込み後に 2000 文字を超えたときの扱い（N-3）。
4. 【未確認】便2 の deploy で discord-gateway コンテナも新しいコードで起動し直されるか（docker-compose.yml:350-352 の同じイメージであることは recon で確認済み、deploy.yml での再起動は本審査では見ていない）。便2 の後に gateway だけ古いコードのまま定数を使い続けると T5 が本番で成り立たないため、便2 の計画に「gateway の起動時刻が deploy 後であること」を観測項目として入れること。

VERDICT: REVISE
