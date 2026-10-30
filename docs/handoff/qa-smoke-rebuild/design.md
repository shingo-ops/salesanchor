# 本番の自動点検（qa-smoke）を直すか作り直すかの設計案

- 作成日: 2026-10-30
- recon: docs/handoff/qa-smoke-rebuild/recon.md
- 作成: 設計担当（Claude）／読み取りと下書きのみ。リポジトリ編集・実行・本番接続はしていない
- 第2版（2026-10-30 Opus 審査 REVISE を反映）: 審査記録 docs/handoff/qa-smoke-rebuild/review.md（同じ内容を repo に写した版）。追加調査の生出力 `/tmp/CC報告ファイル/qa-smoke-review/sonnet/`
- 根拠の基準: `origin/main` = `f41b95411ca3f7b8aa4616c806275d42fa93c3de`（`/tmp/CC報告ファイル/qa-smoke-recon2/origin-main-sha.txt`）
- 調査の生出力: `/tmp/CC報告ファイル/qa-smoke-recon/`、`/tmp/CC報告ファイル/qa-smoke-recon2/`、`/tmp/CC報告ファイル/qa-smoke-design/raw/`、`/tmp/CC報告ファイル/auth-status-1030/`
- 形式: `docs/STANDARD-WORKFLOW.md`の design.md の型（KGI／現在地の引用／`|基準|検証方法|`／外部事例／維持の仕組み）

---

## 0. ねらい（普通の言葉で）

この点検は「お客さんが使う画面が壊れていないか」を、お客さんより先に機械が気づくためにあります。
いまの点検は 2026-06-21 から 30 回連続で失敗していて、失敗の理由は「画面が壊れている」ではなく「点検の機械の置き場所と道具が合っていない」ことです。つまり 4 か月間、この点検は何も見張れていません。

直す道は 3 つ以上ありますが、推奨は「作り直し」です。理由は、いまの形が
（１）本番のデータベースを直接消して書き直す（危ない入口が点検のために開いている）、
（２）置き場所（監視サーバー）からデータベースに届かない、
（３）ログインの自社化（ADR-1013）で丸ごと置き換える予定になっている、
の 3 つを同時に抱えていて、「直す」より「本番に触らず外から見る形」に作り直す方が、安全で、長持ちし、ねらい（壊れたら気づく）に近いからです。

---

## 1. 目的と、PO が ○× で判定できる成功基準（KGI）

### 1-1. 目的

本番アプリ `https://app.salesanchor.jp/` が「利用者から見て壊れている」状態を、利用者より先に自動で見つけ、PO に知らせる。

### 1-2. KGI（PO が画面・通知で判定できる粒度）

| # | 成功基準（○× で判定） | 判定方法 |
|---|---|---|
| K1 | 点検が毎日 1 回以上、自動で最後まで走り「合格」になっている日が、導入後 14 日のうち 13 日以上 | GitHub Actions の実行一覧（`gh run list --workflow <新WF>`）を 14 日分保存し数える |
| K2 | 点検が「不合格」のとき、15 分以内に Discord に 1 通届く（本番を壊さずに、わざと不合格にする試験で確認） | 試験時刻と Discord 受信時刻の差 |
| K3 | 点検は本番の業務データ（会社・リード・案件など）を作らない・変えない・消さない。点検が持つ SQL は 0 行。変わるのはログインの副作用（点検利用者 1 名の `last_login` 更新と refresh トークン 1 行。`backend/app/routers/auth.py:300-306,315`）だけ | 新WF と `tests/prod-check/` に SQL・DB 接続が 0 行（§6 の grep）。§5-1 の書き込み欄がすべて「無」 |
| K4 | 点検がログインに使う利用者は「super admin ではない・1 テナント限定・閲覧権限」である | `public.users` の該当 1 行を PO が確認（AI の読み取り専用の道 ADR-1024 で取得した出力を提示） |
| K5 | 点検が本番で見つけられる壊れ方の一覧（§5-1）を PO が読んで「これなら気づける」と言える | PO 判定 |

K1〜K4 は数で判定、K5 のみ PO 判定。

---

## 2. 現在地（事実。根拠つき）

### 2-1. いまの点検の形

| 項目 | 事実 | 根拠 |
|---|---|---|
| 実行場所 | self-hosted runner `salesanchor-vps` | `.github/workflows/qa-smoke.yml:46` `runs-on: [self-hosted, salesanchor-vps]` |
| runner の実体 | 監視サーバー prod2 で `/home/ubuntu/actions-runner` が service 稼働 | `qa-smoke-recon/host/`（prod2 の調査記録）3-4 行目 |
| 頻度 | 毎週月曜 03:00 JST の 1 回＋手動＋`tests/qa-smoke/**`・`scripts/qa/**` を触る PR | 止血前の版（origin/main）の .github/workflows/qa-smoke.yml の 12,39-41 行目（調査記録 qa-smoke-recon の wf.yml） |
| 手順 | checkout → node 22 → `npm ci` → Playwright ブラウザ導入（`--with-deps`）→ `scripts/qa/reset-tenant.sh`（DB 初期化）→ Playwright 30 本 → `scripts/qa/cleanup-smoke-data.sh` → 成果物保存 | `.github/workflows/qa-smoke.yml:86-140` |
| DB 接続先 | `DATABASE_URL: ${{ secrets.QA_TENANT006_DATABASE_URL }}`（値は見ていない） | `.github/workflows/qa-smoke.yml:52` |
| 不合格時の通知 | **Discord 通知の step は無い**。`QA_DISCORD_WEBHOOK_URL` は reset 開始/完了用で任意 | `.github/workflows/qa-smoke.yml:33,100`（調査記録 qa-smoke-recon の wf.yml 128-160 行目に通知 step なし） |
| 試験の中身 | scene-01〜09、`test(` 30 本。scene-01 は email+password で UI ログイン（Firebase）。`psqlCount`／`tests/qa-smoke/utils/db-assert.ts` で DB を直接数える試験が 12 か所 | `qa-smoke-recon2/test-titles.txt`、`scenes-head.txt`（`grep -c "psqlCount\|db-assert"` = 12） |

### 2-2. 失敗の事実（4 か月間なにも見張れていない）

| 事実 | 根拠 |
|---|---|
| 直近 30 回すべて `failure`（2026-06-21 〜 2026-10-29） | 調査記録 qa-smoke-recon の runs.json（30 件、conclusion は failure のみ） |
| 直接の原因①: ブラウザ導入で `sudo: a password is required` | `qa-smoke-recon/log-40925191476.txt:11-15` |
| 直接の原因②（①を越えても）: prod2 に `psql` が無い | `qa-smoke-recon/log.txt`（以前の run）、`host/prod2-detail.txt` |
| 直接の原因③（②を越えても）: prod2 から prod1 の 5432 に届かない。トンネルは 19100/19187/19113/19121/13100 のみで 5432 は無い。compose の postgres は `ports` 無し（「ホストには公開しない」） | `host/prod2-dbpath.txt:30-34`（`prod1-5432-closed`／`local-5432-closed`）、`qa-smoke-recon2/grep-tunnel.txt`、`compose.txt:407` |
| 同じ runner の `.github/workflows/external-state-snapshot.yml` も直近 8 回の schedule がすべて failure | 調査記録 qa-smoke-recon の runs.json と同条件で取得した一覧（recon 記録） |
| 最後に成功した日は 2026-06-19 14:24 JST（手動実行）。直近 200 件で成功 2・失敗 150・取消 48 | `qa-smoke-review/sonnet/`（Q6） |

### 2-3. なぜ前提がずれたか

| 事実 | 根拠 |
|---|---|
| ADR-078 は「runner はアプリサーバー prod1 に置く（同じ箱なので DB に届く）」前提 | `docs/adr/ADR-078-vps-runner-registration.md:38` |
| ADR-080 で監視スタックと runner を prod2 へ移した。2026-09-30 の追記で「トンネルは ADR の記載と異なる」 | `docs/adr/ADR-080-monitoring-vps-separation.md:170-173` |
| qa-smoke.yml は ADR-078 前提のまま（`runs-on` と DB 直結の手順が残っている） | `.github/workflows/qa-smoke.yml:46,52,86-118` |

【事実】runner の引っ越し（ADR-080）のとき、qa-smoke の前提（DB 直結）を一緒に見直さなかった。これは設計の入れ忘れ。

### 2-4. 本番データへの入口（いまの形が持っている危なさ）

| 事実 | 根拠 |
|---|---|
| `scripts/qa/seed-tenant.sql` は `tenant_006` の 7 表を `TRUNCATE ... RESTART IDENTITY CASCADE` | `qa-smoke-recon2/seed.txt`（`scripts/qa/seed-tenant.sql:76-94`） |
| `public.meta_page_routing` から tenant_id=6 を DELETE、`public.users` から `email LIKE 'qa-%@salesanchor.jp'` を **テナント条件なしで** DELETE | 同上 seed-tenant.sql:76-94、`cleanup.txt`（cleanup-smoke-data.sh:107） |
| `public.tenants` の id=6 の settings を UPDATE で置き換え | seed-tenant.sql:301-307 |
| `set_config('app.is_operator','true')` で RLS を越える操作者として実行 | `seed.txt` |
| PR #2332 の説明は「public 非接触」と書いているが、上の通り public の 3 表に触れている | `qa-smoke-recon2/pr2332.txt` と seed.txt の突合 |
| secrets に `QA_*_PASSWORD_HASH`・`QA_*_FIREBASE_UID`・`QA_TENANT006_DATABASE_URL` が存在（値は見ていない） | `.github/workflows/qa-smoke.yml:25-33,94-100`、調査記録 qa-smoke-recon の ess.json（名前のみ） |
| `docs/STANDARD-WORKFLOW.md` は「tenant_006 は Meta App Review 撮影専用テナント（QA 用途禁止）」 | `docs/STANDARD-WORKFLOW.md:98` |
| ADR-038 は tenant_006 を QA ゲートとして使う決定 | `docs/adr/ADR-038-qa-smoke-suite.md` |

【事実】会社の決まり（tenant_006 は QA 禁止）と ADR-038（tenant_006 を QA で初期化する）は食い違っている。どちらが正か **未確認**（PO 判断の対象。§11 D3）。

### 2-5. すでにある本番の見張り（重複を作らないために）

| 見張り | 何を見るか | 根拠 |
|---|---|---|
| Uptime Kuma（prod2） | `https://app.salesanchor.jp/`、`https://api.salesanchor.jp/api/health`、LP などの HTTP 応答。30〜60 秒間隔。失敗 2 分で `KumaMonitorDown`（critical, page） | `docs/adr/ADR-069-uptime-kuma-activation.md`（監視対象表）、`monitoring/prometheus/alert_rules.yml:141-153` |
| deploy.yml 配備後スモーク（prod1 内で docker exec） | RLS の有効・方針・アプリ役の接続・`/api/health` | `scripts/smoke_test_post_deploy.sh`（195 行、docker exec psql）、`.github/workflows/deploy.yml:611-622` |
| deploy.yml Step 6 健康確認＋自動ロールバック | 配備直後の `/api/health` | `.github/workflows/deploy.yml:677-788` |
| FedEx live smoke（スイッチ `FEDEX_SMOKE_ENABLED`、失敗で Discord） | FedEx 連携 | `.github/workflows/deploy.yml:627-672`、ADR-124 |
| smoke 専用トークン経路（ADR-1017） | `SMOKE_SERVICE_TOKEN` 一致時に `SMOKE_SERVICE_EMAIL` の利用者として API に入れる。super admin なら拒否（fail-closed）。本番 .env には `FEDEX_SMOKE_API_TOKEN`／`FEDEX_SMOKE_USER_EMAIL` が流し込まれている | `backend/app/auth/dependencies.py:43-46,149-171`、`.github/workflows/deploy.yml:345-346` |

【事実】「サイトが落ちた」「API が死んだ」「配備で壊れた」はすでに見張られている。**見張られていないのは「ログインして画面を操作したときに壊れていないか」（ログイン→一覧→検索→詳細が動くか）** で、qa-smoke だけがそこを担っていた。

### 2-6. ログイン自社化（ADR-1013）との関係

| 事実 | 根拠 |
|---|---|
| ADR-1013 Consequences: qa-smoke／rotate-qa-firebase／snapshot／smoke は便6で置き換える | `docs/adr/ADR-1013-self-hosted-auth-and-passkey.md:43` |
| 便4a（#4858）は合流済み。`AUTH_PROVIDER` 既定は firebase。便4b（切替）は PO の日付待ち | 調査記録 auth-status-1030 の handoff.md と prs-recent.txt |
| ADR-1048（管理者 2FA）の設計は「7 日前に qa-admin と SMOKE_SERVICE_EMAIL の利用者が管理者でないことを確認」 | `docs/handoff/admin-2fa/design.md:172` |
| scene-01 のログインは Firebase の email+password 前提（「Firebase auth が生きていることの確認」の試験あり） | `test-titles.txt`（scene-01 行 41） |

【事実】いまの点検は Firebase 前提で、ログイン切替後にそのままでは動かない。切替の前後で「ログインのやり方」だけ差し替えられる作りにしておく必要がある。

### 2-7. GitHub 提供 runner で Playwright を動かしている前例（社内）

| 事実 | 根拠 |
|---|---|
| `.github/workflows/e2e.yml` の「画面検査」job は `ubuntu-24.04`（GitHub 提供）で `npx playwright install --with-deps chromium` を実行し成果物を保存 | `.github/workflows/e2e.yml:152-220` |
| `.github/workflows/sandbox-test.yml` が存在（一時 VM は GitHub 上で） | `git ls-tree origin/main .github/workflows/`（出力に sandbox-test.yml）、メモリ #4403 |

---

## 3. 選択肢の比較（3 つ以上）

| 観点 | A. いまの形を直す | B. 作り直し：本番に触らない外側点検（推奨） | C. 配備時だけ動かす（deploy.yml に組み込む） | D. 止めて既存の見張りに畳む |
|---|---|---|---|---|
| 何をするか | prod2 に sudo なし依存を入れ、psql を入れ、prod1 の DB へ届く道を新設し、今の seed/TRUNCATE を続ける | GitHub 提供 runner から HTTPS だけで本番にログインし「閲覧系の画面操作」を点検。DB に触らない。毎日 | B と同じ中身を、配備後だけ実行 | qa-smoke を無効化し、Uptime Kuma と配備スモークに任せる。ADR-1013 便6を待つ |
| 得られる価値（壊れたら気づく） | 高（書き込み系も試せる）。ただし週 1 回 | 中〜高（閲覧・検索・詳細・ログイン）。毎日〜数時間ごと | 中（配備時のみ。配備なしで壊れた時＝外部要因・証明書・Firebase 側の変更は気づけない） | 低（画面操作の壊れは気づけない） |
| 本番データの安全（入口） | **悪い**。TRUNCATE/DELETE/UPDATE と RLS 越え（`is_operator`）を点検が持ち続ける。public.users の DELETE にテナント条件なし。さらに prod2→prod1 の DB 入口を新設する必要 | **良い**。SQL を 0 行にする。ログイン利用者は閲覧権限 1 名。新しい DB 入口を作らない | B と同じ | 最良（点検が無い） |
| SSOT（同じ事実を 2 か所に持たない） | 悪い。試験用の利用者・テナント設定を seed.sql と secrets（hash・UID）の 2 か所で持つ | 良い。試験用利用者は `public.users` の 1 行のみ。期待値は画面の「存在」で判定し、件数の写しを持たない | B と同じ | 該当なし |
| 費用・手間 | 大。prod2 の sudo 権限設計、psql 導入、DB 経路（トンネル追加＝ADR-080/081 の入口設計変更）、PO の危険操作承認が複数 | 中。WF 1 本＋試験 5〜8 本の書き直し。サーバー変更なし。secrets 追加 2 件（email/password） | 中（B の中身＋deploy.yml 変更＝危険パス、ADR-136 GO 必要） | 小（WF 無効化のみ） |
| ログイン切替（ADR-1013）との関係 | 便6で捨てる前提のものを直すことになる | ログイン手順を 1 ファイルに閉じ込めれば、切替後はその 1 ファイルだけ差し替え。便6の受け皿になる | B と同じ | 便6まで画面点検が無い |
| 戻し方 | 新設した DB 経路・sudo を閉じる作業が要る（戻しも危険操作） | WF を 1 本消すだけ。本番に変更がないので戻す対象がない | deploy.yml を戻す（危険パス） | WF を戻すだけ |
| 既存ルールとの整合 | tenant_006「QA 禁止」と衝突したまま | tenant_006 の初期化をやめるので衝突が消える（読むだけならどのテナントでも PO 判断で可） | B と同じ | 衝突が消える |

【推測】A は「今あるものを活かす」ように見えるが、3 つの障害（sudo・psql・経路）をすべて新しい入口で解決することになり、点検のために本番の守りを弱める。B は守りを弱めずに価値の大半（画面が動くか）を取り戻す。

---

## 4. 推奨と理由

**推奨: B（作り直し。本番に触らない外側点検を GitHub 提供 runner で毎日動かす）**。合わせて、いまの qa-smoke.yml の schedule を止める（D の一部を先に実施）。

理由（事実に基づく）
1. いまの点検は 4 か月間なにも見張れていない（§2-2）。まず「見張れている状態」に戻すのが最優先で、B はサーバーを触らずに最短で達成できる。
2. いまの形は本番 DB への TRUNCATE/DELETE/UPDATE と RLS 越えを含み（§2-4）、会社の決まり「新しい本番データへの入口を安易に増やさない」に反している。A はさらに入口を増やす。
3. ADR-1013 便6で置き換える予定（§2-6）。A に投資しても捨てる。B はログイン手順を 1 ファイルに閉じるので便6の受け皿になる。
4. 社内に GitHub 提供 runner で Playwright を動かす前例がある（§2-7）ので、道具の問題（sudo・ブラウザ依存）は起きない。

B で失うもの（正直に）
- 書き込み系（会社の登録・案件の更新など）の点検。これは本番でやると本番データを汚すので、**staging か便6の試験環境**で行う（§5-7）。
- 「seed 済 5 件が出ている」のような件数一致の点検。件数は本番で変わるので、B では「一覧が 1 件以上描画される・エラー 0 件」に置き換える。

---

## 5. 推奨案（B）の詳細

### 5-1. 何を点検するか（利用者から見た壊れ方）

| # | 点検 | 壊れたら何が起きるか（PO 視点） | 書き込み |
|---|---|---|---|
| S1 | `https://app.salesanchor.jp/` が 200 で表示され、ログイン画面が出る | 誰もアプリに入れない | 無 |
| S2 | 点検専用の利用者で email+password ログインできる | 全員ログイン不能（Firebase／自社ログインの壊れ） | 無（ログイン記録は残る） |
| S3 | ログイン後のダッシュボードが描画され、`console.error` が 0 件 | 最初の画面が真っ白 | 無 |
| S4 | 会社一覧・リード一覧・案件一覧が「1 件以上」または「0 件表示」のどちらかで正常描画（エラー表示なし） | 一覧が開かない（API 500 など） | 無 |
| S5 | 一覧の検索欄に文字を入れて結果が返る（結果 0 件でも可） | 検索が止まっている | 無 |
| S6 | 一覧の 1 行目を開いて詳細が描画される（1 件以上ある場合のみ） | 詳細が開かない | 無 |
| S7 | 間違ったパスワードでログイン失敗になる | ログインの守りが壊れている | 無 |
| S8 | ログアウトできる | セッションが壊れている | 無 |

除外する（本番ではやらない）: 会社の新規登録、案件の更新、メッセージ送信、Meta 連携の書き込み。これらは §5-7 の staging で扱う。

### 5-2. どこで動かすか

- GitHub 提供 runner `ubuntu-24.04`（`.github/workflows/e2e.yml:157` と同じ）。
- self-hosted runner（prod2）は使わない。理由: sudo 不可・psql 無し・prod1 DB に届かない（§2-2）。B は DB を使わないので self-hosted の利点が無い。
- 本番への経路は HTTPS（`app.salesanchor.jp`・`api.salesanchor.jp`）のみ。
- 【未確認】Cloudflare が GitHub の送信元 IP を bot として弾くか。→ §10 U1。

### 5-3. 誰でログインするか

- 点検専用の利用者 1 名（メールアドレスは PO 判断。文書には書かず GitHub secrets にだけ置く）。
- 条件: `is_super_admin = false`、1 テナント限定（`users.tenant_id` は 1 つだけ。`backend/app/models.py:24-26`）、役割は「見る権限（`*.view`）だけ」。
  - 【事実】既定の 7 役割（`backend/app/services/tenant.py:50-`）に閲覧だけの役割は無い。`backend/app/auth/viewer_*` は閲覧ページ用の別物で、ここでは使わない。
  - そのため点検先の会社の役割画面で「点検用（見るだけ）」の役割を 1 つ作り、`*.view` だけを付ける（通常の画面操作。手動 INSERT はしない・ADR-025）。権限が無い書き込み API は 403（`backend/app/auth/dependencies.py:623-648`）。
  - owner／admin にはしない。理由: ADR-1048 で管理者は二段階が必須になり（ADR-1048:16）点検がログインできなくなる。管理者でない人は今のまま（ADR-1048:23）。
- どのテナントか: **PO 判断（§11 D3）**。候補は tenant_001（STANDARD-WORKFLOW で QA 用）。tenant_004（HIGH LIFE JPN 実データ）は使わない。tenant_006 は「撮影専用・QA 禁止」の決まりがあるため既定では使わない。
- 作り方: 既存の管理画面から通常の手順で 1 名作る（手動 INSERT をしない。ADR-025）。Firebase 側にも同じ email の利用者が要る（便4b 前）。
- 秘密情報: GitHub secrets に `SMOKE_E2E_EMAIL`／`SMOKE_E2E_PASSWORD` の 2 件。既存の `QA_*` 9 件は B の稼働確認後に削除候補（§7-2）。
- ADR-1017 の `SMOKE_SERVICE_TOKEN` 経路は使わない。理由: その経路は Firebase と MFA を飛ばすので、「ログインが壊れていないか」を見る S2・S7 の点検ができない。API 単体点検には将来使える（§10 U4）。

### 5-4. 本番データを汚さない方法

- 点検は SQL を 1 行も持たない（K3）。seed／cleanup／reset を廃止。
- 点検がデータを作らないので、後片付けも不要。
- ログイン記録・アクセスログは残る。これは「点検専用利用者の記録」と一目で分かる email にして、集計から除外できるようにする（【未確認】ダッシュボード KPI に点検ログインが混ざるか。→ §10 U3）。
- 書き込み系は本番でやらない（§5-1 除外）。

### 5-5. 頻度と、誤報を減らす仕組み

- 頻度: 毎日 1 回（JST 07:00 ごろ）＋手動。将来 6 時間ごとに増やす（K1 の 14 日を見てから）。
- 誤報対策:
  （１）各点検は失敗時 1 回だけ自動で再試行（Playwright `retries: 1`）。2 回連続失敗で不合格。
  （２）不合格でも「ログインできない」と「一覧が開かない」を分けて通知文に書く。
  （３）配備（deploy.yml）の最中は走らせない。【事実】配備は push のたびに走り、固定時刻ではない。10/20〜10/30 の 300 件で 7 時台 3 件・6 時台 0 件（Q7）。時刻をずらすだけでは防げないので、最初の段で GitHub の実行一覧から「配備が走っているか」を確かめ、走っていれば 10 分待って 1 回だけ確かめ直す。それでも走っていれば「配備中のため見送り」と記録し、不合格にしない。
  （４）Uptime Kuma が既に「落ちている」と言っている時間帯の不合格は、通知文に「サイト全体が落ちている可能性」と添える（実装は 2 段階目）。

### 5-6. 通知

- 不合格のとき、既存の `DISCORD_WEBHOOK_OWNER_PING`（`.github/workflows/deploy.yml:670,683` で使用中）へ 1 通。新しい webhook は作らない（入口を増やさない）。
- 通知文: 「本番の画面点検が不合格。壊れていたのは: ログイン／一覧／検索／詳細 のどれか。実行ページへのリンク」。
- 合格時は通知しない（通知の慣れを防ぐ）。週 1 回、月曜に「先週 7/7 合格」の 1 行を送るかは PO 判断（§11 D4）。
- 成果物（trace／screenshot）は GitHub Actions の artifact に 14 日保存（現行と同じ `.github/workflows/qa-smoke.yml:125-140`）。

### 5-7. ログイン切替（ADR-1013）の前後と staging

- ログイン手順は tests/prod-check/login.ts のような **1 ファイル** に閉じ込める。切替前は Firebase の email+password、切替後は自社ログイン。試験本体は触らない。
- 切替の当日: 便4b の実施直後に手動実行して合格を確認する（K2 の試験も兼ねる）。
- 便6（ADR-1013 の置き換え便）では、本設計の点検を「便6の受け皿」とし、便6側で新しい点検を別に作らない（SSOT）。
- staging: 【未確認】本番と同じ構成の staging の有無 → §10 U2。無い場合、書き込み系の点検は便6で用意する試験環境に送り、本設計の範囲外とする。

### 5-8. 触るファイル（予定。実装は別便）

| 種別 | パス | 内容 |
|---|---|---|
| 新規 | .github/workflows/prod-ui-check.yml | B の WF（ubuntu-24.04、毎日、Discord） |
| 新規 | tests/prod-check/playwright.config.ts、tests/prod-check/login.ts、tests/prod-check/ 配下の spec ファイル | S1〜S8 |
| 変更 | `.github/workflows/qa-smoke.yml` | schedule と pull_request を外し `workflow_dispatch` のみ残す（即日の止血）。B の K1 達成後に削除便 |
| 変更 | docs/adr/ の ADR-038 ファイル | Superseded by 新 ADR |
| 変更 | docs/adr/ の ADR-080 ファイル | 追記: runner は prod2 で DB 不達。qa-smoke は B へ |
| 変更 | docs/adr/ の ADR-1013 ファイル | 便6の「置き換え」先を本設計に紐付け |
| 新規 | 新規 docs/adr/ADR-1051-prod-ui-black-box-check.md（番号は仮。ADR-1050 まで存在を確認済み） | 本設計の決定 |
| 変更 | `docs/STANDARD-WORKFLOW.md` | tenant_006 の扱いを PO 判断に合わせて整合 |
| 触らない | `scripts/qa/*`、`tests/qa-smoke/*` | 削除便まで残置（戻し用） |

---

## 6. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 新 WF が `ubuntu-24.04` で最後まで走り合格する | `gh run view <id>` の conclusion が success。出力を `/tmp/CC報告ファイル/` に保存 |
| 新 WF と `tests/prod-check/` に SQL・psql が 0 件 | `grep -rn "TRUNCATE\|DELETE\|UPDATE\|INSERT\|psql\|DATABASE_URL" .github/workflows/prod-ui-check.yml tests/prod-check/` が 0 行 |
| 点検利用者が super admin でなく 1 テナント限定 | ADR-1024 の読み取り専用の道で `public.users` の該当行を取得し PO に提示 |
| 不合格→Discord 15 分以内 | 手動実行の入力「わざと不合格にする」を付けて走らせ（本番に無い文字を探す点検を 1 本だけ足す）、通知時刻を記録。secrets は変えない |
| 14 日で 13 日以上合格（K1） | `gh run list --workflow prod-ui-check.yml --limit 20` を保存し数える |
| 旧 qa-smoke が自動で走らない | `gh run list --workflow qa-smoke.yml` に schedule／pull_request の新規 run が無い |
| ログイン切替後も合格 | 便4b 当日に手動実行 |
| ADR index が最新 | CI「ADR index is up to date」緑 |

---

## 7. リスクと対策、戻し方

### 7-1. リスク

| リスク | 対策 |
|---|---|
| Cloudflare が GitHub runner を弾く（U1） | 先に手動実行 1 回で確認。弾かれたら Cloudflare 側の許可（PO の外部 GUI 操作＝PO 確認必須）か、User-Agent の明示。それでも不可なら self-hosted に戻すが、その場合も DB には触らない |
| 点検のログインが KPI や監査ログを汚す（U3） | 専用 email で除外可能にする。混ざるなら集計側で除外（別便） |
| 点検用パスワードの漏えい | 閲覧権限のみ・1 テナント限定・super admin 不可。定期的な変更は便6で自社ログインに移ってから仕組み化 |
| 本番で一覧が 0 件のテナントだと S6 が常に skip。【事実】tenant_001 は「空テスト」との記載がある（`docs/handoff/data-durability-design/design.md:79`）。件数は未確認 | 「0 件なら skip」を仕様に書き、通知文に skip 数を出す。段階 2 で件数を読み取り専用の道で数え、0 件なら PO に見本データを画面から数件入れてよいか聞く |
| Cloudflare の有無の記載が食い違う（無い: `docs/handoff/gas-viewer-fresh-fast/design.md:455` ほか 2 件／有る: `docs/handoff/outage-recovery-watch/design.md:88`） | 段階 3 の手動実行 1 回で実際に届くかを確かめる（U1） |
| 配備と重なって誤報 | 時刻をずらす。2 段階目で deploy.yml の実行中は skip |
| 旧 secrets（`QA_*` 9 件）が残り続ける | K1 達成後に削除便（secrets 変更は PO 確認必須） |

### 7-2. 戻し方

- 新 WF を削除（1 ファイル）。本番サーバー・DB に変更は無いので戻す対象なし。
- 旧 qa-smoke.yml は `workflow_dispatch` を残して残置するので、必要なら手動で呼べる（ただし §2-2 の理由で成功しない）。
- 点検利用者は管理画面から無効化（is_active=false）。

---

## 維持の仕組み

守り手: 人手で守る（作り直しの仕組みはまだ無いため。新しい点検を入れる PR で、毎週の定期点検に『直近7日の成功数』を足して関所にする）

| 何を | 誰が／何が | どう |
|---|---|---|
| 毎日の実行と不合格通知 | GitHub Actions（schedule）→ Discord | 人の手なしで回る。合格は無通知 |
| 「走っていない」こと自体の検知 | 週次の定期点検（agent-console 定期実行、ADR-1011／#4247）に「prod-ui-check の直近 7 日の成功数」を 1 行追加 | 0〜6 なら Discord。今回の「4 か月間 failure に気づかなかった」の再発防止 |
| ログイン切替への追随 | tests/prod-check/login.ts（新規）の 1 ファイル | 便4b の作業手順書に「login.ts を差し替え → 手動実行」を 1 行入れる |
| 点検の中身の見直し | 画面を大きく変える PR（`frontend/src/pages/**`）に CLAUDE.md 経由で「prod-check が壊れないか」の確認項目 | 既存の `docs/ai-agents/executor-checklist.md` に 1 項目追加 |
| 旧資産の始末 | K1 達成後の削除便（qa-smoke.yml／scripts/qa／tests/qa-smoke／QA_* secrets） | ADR-1051 の Consequences に期限を書く |

---

## 8. 外部・過去事例の参照と我々への応用

| 事例 | 出典 | 何が使えるか | 使えない範囲 |
|---|---|---|---|
| GitHub 提供 runner で Playwright を定期実行する社内前例 | `.github/workflows/e2e.yml:152-220`（画面検査 job） | ブラウザ導入手順・cache・成果物保存をそのまま流用できる | e2e.yml はモック相手。本番相手の認証・通知は本設計で追加 |
| Playwright 公式ドキュメント「CI」「GitHub Actions」 | playwright.dev の Continuous Integration ページ（本設計の作成時に外部取得はしていないため **版・日付は未確認**。実装便で Context7 で確認する） | `npx playwright install --with-deps` を ubuntu runner で使う形は公式の推奨 | 数値（所要時間など）は本設計では引用しない |
| 「synthetic monitoring（合成監視）」の考え方 | 一般的な監視の分類（出典を本設計では取得していない。**実装便で出典を添える**） | 「本番に対して利用者と同じ操作を定期的に行い、壊れを先に見つける」＝本設計の B の考え方 | 具体的な製品の数値は引用しない |

【事実】本設計の作成では外部サイトを取得していない（指示: 読み取りと下書きのみ、ネット取得の指示なし）。外部事例の数値は書いていない。実装便で Context7／公式ドキュメントの出典を添える。

---

## 9. 触る ADR と、段階ごとの PO 承認点

| 段階 | 内容 | ADR | PO 承認点 |
|---|---|---|---|
| 0 | 止血: qa-smoke.yml の schedule／pull_request を外す（手動のみ残す） | ADR-038 に「停止中」追記 | 通常 PR（危険パスでない）。審査役 APPROVE |
| 1 | 新 ADR-1051（仮）起案: 本番 UI 外側点検。ADR-038 を Superseded、ADR-080 追記、ADR-1013 便6の受け皿を紐付け | ADR-1051 新規／038・080・1013 改訂 | **PO 承認（ADR）** |
| 2 | 点検利用者 1 名を管理画面で作成（Firebase にも）、secrets 2 件追加 | — | **PO 確認（secrets 変更は不可逆操作の一覧に該当）** |
| 3 | 新 WF＋試験 S1〜S8 を PR。手動実行 1 回で合格・不合格通知を確認 | — | 通常 PR。危険パス（deploy.yml・`migrations/`・本番 `scripts/`）を含まないので GO 記録は不要 |
| 4 | 14 日観測（K1）。定期点検に「走っているか」を追加 | — | 結果報告のみ |
| 5 | 旧資産の削除便（WF・scripts/qa・tests/qa-smoke・QA_* secrets 9 件） | ADR-1051 Consequences | **PO 確認（secrets 削除）** |
| 便4b 当日 | login.ts 差し替え＋手動実行 | ADR-1013 | 便4b の GO に含める |

---

## 10. 未確認の点と、確かめ方

| # | 未確認 | 確かめ方 | 依存する選択 |
|---|---|---|---|
| U1 | Cloudflare が GitHub 提供 runner からの本番アクセスを弾くか | 段階 3 の手動実行 1 回（読み取りだけ） | B の実行場所。弾かれたら §7-1 の代替 |
| U2 | （解消）staging は無い。ADR-115:35-37「保留」、ADR-1000:25「ステージング環境がなく」、STANDARD-WORKFLOW.md:98「当面の確認環境は本番のみ」 | — | 書き込み系の点検は本設計の範囲外 |
| U3 | （解消）混ざらない。成功ログインは監査記録を書かない（監査は auth.py:114,488,575 のみ）。`last_login` を読む集計は backend・frontend に無い | — | 除外の仕組みは不要 |
| U4 | （解消）コードでは FedEx だけ。この経路には二段階より前に通す穴があり、管理者の二段階の設計で扱う（`docs/handoff/admin-2fa/design.md:172`）。本設計は使わない | — | — |
| U5 | （解消）§5-5（３）。配備中なら見送る | — | — |
| U6 | （解消）2026-06-19 14:24 JST | — | — |
| U7 | tenant_006 の扱い（「撮影専用・QA 禁止」と ADR-038 の食い違い） | PO 判断 | 点検利用者のテナント（D3） |
| U8 | 2026-10-29 に tenant 6 へ入った利用者 id=86（is_active=false）の email が `qa-` 始まりか | ADR-1024 の読み取り専用の道で 1 行確認 | 旧 cleanup が消す対象になるか（止血で schedule を外せば影響なし） |
| U9 | playwright.dev の CI ページの版・日付 | 実装便で Context7 取得 | 外部事例の出典 |

---

## 11. PO に決めてほしいこと（1 件ずつ・推奨つき）

### D1. 方針（最初に 1 件）
- **PO 決定 2026-10-30: 「1」（B 作り直し）**
1. B（作り直し。本番に触らない外側点検を毎日）【おすすめ】→ 2〜3 週間で「壊れたら Discord に届く」状態になる。本番サーバー・DB は触らない
2. A（いまの形を直す）→ 監視サーバーに sudo・psql・DB への道を新設する。危険操作の承認が複数回必要で、ログイン切替後に捨てる
3. D（止めて既存の見張りに畳む）→ 今すぐ失敗通知は止まるが、「ログインして画面が動くか」は便6まで誰も見ない

### D2. 止血（D1 と独立。先にやってよい）
- **PO 決定 2026-10-30: 「1」（自動実行を止め、手動だけ残す）。実装承認を兼ねる**
1. qa-smoke.yml の自動実行（毎週＋PR）を今すぐ止め、手動だけ残す【おすすめ】→ 失敗の山が止まる。本番に影響なし
2. そのまま残す → 毎週月曜に失敗が積み上がり続ける

### D3. 点検でログインする利用者のテナント
1. tenant_001（決まりで QA 用）【おすすめ】→ 実データを触らず、決まりとも一致
2. tenant_006（ADR-038 のまま）→ 「撮影専用・QA 禁止」の決まりと食い違うので、決まりを直す必要がある
3. 新しい点検専用テナントを作る → 最も隔離されるが、作る手間と「空のテナントで一覧 0 件」になりがち

### D4. 合格の知らせ
1. 不合格のときだけ Discord【おすすめ】→ 通知に慣れて見なくなるのを防ぐ
2. 毎週月曜に「先週 7/7 合格」の 1 行も送る → 「走っている」安心が毎週得られる（維持の仕組みの定期点検と重複）

### D5. 旧資産（QA_* secrets 9 件・scripts/qa・tests/qa-smoke）の削除
1. B が 14 日合格（K1）してから削除便【おすすめ】→ 戻し用に残しつつ、期限付きで片付く
2. すぐ削除 → 片付くが、B が動かなかったときの戻し先が無い
