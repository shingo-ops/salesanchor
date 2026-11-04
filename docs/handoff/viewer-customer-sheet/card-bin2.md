---
mode: handoff
---
# 実装カード 便2: 請求先フォーム（本契約のお客さんが自分で請求先を書く）

親: [design.md](./design.md) §3-1・§3-2・§3-5「請求先」「請求先フォームを送る」・§3-6・§3-7・§7（便2の行）・§6 Q3a〜Q3c・Q4・Q4b・Q4c・Q5

- 状態: カード作成済み（2026-11-04 Opus）・PO 実装承認済み（2026-11-04 チャットで「1」＝「この内容で作る」を選んだ）。マージと本番への反映の GO は兼ねない。
- 担当: クラウドの Sonnet（実装）。Opus は審査・GO・マージ判断。
- 本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
- 区分: A（`migrations/` と `scripts/` と `frontend/api-contract/` を触るため。ADR-1015）。
- 着手の前提: 便1（PR「配信先のシートとお客さんをつなぐ」・枝 `release/viewer-sheet-link-bin1`）が main に入っていること。両方が `frontend/src/pages/super-admin/ViewerAccountsPage.tsx` を直すため。Opus が便1 の合流を確かめてから渡す。

## 0. カード発行前チェック（docs/ai-agents/design-partner.md §5.5 の照合結果）

| 番号 | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲む | ○ |
| 2 | PR は ready で作る（`--draft` を付けない）と明記 | ○（§6。PR は Opus が作る） |
| 3 | 報告の宛先（完了報告の本文に生出力を全文） | ○（§7） |
| 4 | 1便1目的（請求先フォームだけ。請求書は別テーマ） | ○ |
| 5 | 起点の明示（新しい枝を origin/main から） | ○（§5 手順1） |
| 6 | PR 欄の書式を良い例と禁止形で示す | ○（§6） |
| 7 | 合格基準を出力まで縛る（main との差分に削除が想定外に無いこと） | ○（§5 手順10） |
| 8 | 件数の停止には名前を出す手順を対で置く | ○（§5 手順10） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 報告様式3点（停止の3点・受領と終端の合図・冒頭の便名） | ○（§7） |
| 11 | 行番号を停止条件にしない（行番号は目印。前後の文で探す） | ○ |
| 12 | 停止は不可逆・本番影響のものだけ。数の食い違いは記録して続行 | ○（§4） |
| 13 | 委任文の定型4点（sleep 禁止・Write/Edit で書く・validate-pr-body.sh・フックに止められたら言い換えない） | ○（§4） |

読んだ節（docs/handoff/design-partner-card-ops/guards/）: 00-common.md・04-worktree.md・05-pr.md・07-migration.md（便1 と同じ）。

基準: 設計の基準 origin/main d948cf9c7。2026-11-04 に origin/main 89d3320ed と比べ、下の §2 の対象ファイルの差分は `scripts/run_all_migrations.sh` の末尾2行だけ（`20261105_100000_tenant_discord_config_purpose.sql` の登録）。行番号は d948cf9c7 時点の目印で、ずれていたら前後の文で探す。便1 の合流で `ViewerAccountsPage.tsx`・`ja.json`・`en.json`・`openapi.json` の行はずれる。

## 1. 目的（便2で利用者に見える変化）

- 閲覧者管理ページで、本契約のお客さんの詳細に「請求先」の区切りが出る（まだ無ければ空の案内）。
- 本契約のお客さんの詳細に「請求先フォームを送る」ボタンが出る。押すと、7日間使えるリンクが Discord の部屋とメールの両方に送られる。
- お客さんはリンクを開くと、ログインせずに請求先の7項目を書いて送れる。前に書いた値があれば、それが入った状態で開く。
- 請求先は AI の読み取りから見えない。プライバシーポリシーに書き足す。

## 2. 触るファイル（これ以外は触らない）

| ファイル | 何をする |
|---|---|
| `migrations/2026110x_xxxxxx_create_viewer_billing_profiles.sql`（新規。時刻は作成時。`migrations/` の直近より後） | 請求先の表、鍵の用途の CHECK の付け替えと COMMENT の書き直し。冪等 |
| `scripts/run_all_migrations.sh` | 末尾の `run_sql` の並びの最後に1行足す |
| `migrations/20261031_210000_create_ops_case.sql` | 拒否表の一覧に1行足す |
| `migrations/20261024_100300_create_ai_cloud_views.sql` | 列の分類に2行足す・:3 のコメントの数 |
| `migrations/20261020_120000_create_viewer_message_templates.sql` | :11 の COMMENT「台帳の9件」→「台帳の10件」 |
| `.github/workflows/migration-guard.yml` | :224 の `PUBLIC_TABLES` に `viewer_billing_profiles` を足す（`viewer_status_changes` の後ろ） |
| `backend/app/services/viewer_message_templates.py` | LEDGER に `billing_form_request` |
| `backend/app/services/viewer_billing_form.py`（新規） | 鍵を作る唯一の入口・開く・送信の処理 |
| `backend/app/services/auth_mail.py` | 新しい送信部 `send_viewer_billing_form_email` を足す（今の関数は変えない） |
| `backend/app/routers/super_admin_viewers.py` | 送る API・請求先を読む API・応答の型 |
| `backend/app/routers/viewer.py` | フォームの2本の API |
| `backend/app/realtime/topics.py` | `NO_SIGNAL_ROUTES` に書き込みの口3本を足す（§3-3 の最後の項目） |
| `backend/tests/test_viewer_isolation.py` | `_PUBLIC_NO_AUTH_ROUTES` にフォームの2本を足す（§3-3 の最後の項目） |
| `frontend/api-contract/openapi.json` と生成される型 | §5 手順7 の命令で作り直す（手で書かない） |
| `frontend/src/pages/super-admin/ViewerAccountsPage.tsx` | 詳細に「請求先」の区切りと送るボタン |
| `frontend/src/pages/viewer/ViewerApp.tsx` | `#billing=` の入口 |
| `frontend/src/pages/viewer/BillingFormView.tsx`（新規） | 請求先フォームの画面 |
| `frontend/src/pages/viewer/api.ts`・`frontend/src/pages/viewer/types.ts` | フォームの2本の呼び出しと型 |
| `frontend/src/locales/ja.json`・`frontend/src/locales/en.json` | 管理画面の新しいキー・テンプレートの名前・使う場面・差し込み項目の説明（両方に同じキー） |
| `frontend/src/locales/viewer/ja.json`・`frontend/src/locales/viewer/en.json` | フォームの文言（両方に同じキー） |
| `lp/src/pages/privacy.astro` | §3-5 の文を足す |
| 試験（下の §3-6） | 受入条件を確かめる試験 |

触らないもの: 配信先の表と配信の判定（便1）・請求書の表（別テーマ）・`_send_reset_mail`・パスワード再設定の処理・`backend/app/auth/viewer_allowlist.py`・B2B の `registration_tokens` と登録画面・`deploy.yml`・ADR と仕様書の文書（Opus が別に直す）・本番のテンプレートの中身（本番へ出した後に PO か管理者が画面で1回保存する）。

## 3. 作るものの決まり（design.md が正。食い違えば design.md に従い、報告する）

### 3-1. migration（新しい1本）

- `public.viewer_billing_profiles` を design §3-2 の表の定義どおりに作る（`CREATE TABLE IF NOT EXISTS`）。主キー `viewer_account_id BIGINT REFERENCES public.viewer_accounts(id) ON DELETE CASCADE`。RLS なし（名簿と同じ public の全体共通の表）。
- CHECK は名前付き `ck_viewer_billing_profiles_*`。design §3-2 の各行どおり:
  - `party_type IN ('company','individual')`
  - `bill_to_name`: `char_length(bill_to_name) BETWEEN 1 AND 100 AND char_length(btrim(bill_to_name)) >= 1`
  - `contact_name`: NULL か 1〜50 字。かつ `party_type <> 'company' OR contact_name IS NOT NULL`
  - `postal_code ~ '^[0-9]{7}$'`、`phone ~ '^[0-9]{10,11}$'`
  - `address`: 1〜200 字（前後の空白を除いて1字以上）
  - `invoice_email`: `invoice_email IS NULL OR (char_length(invoice_email) BETWEEN 3 AND 254 AND position('@' in invoice_email) > 0)`（名簿の email には CHECK が無いので、見本にしない）
  - CHECK は冪等に足す（既存の migration の書き方に合わせる。`DO $$ ... IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = ...)` の形か、CREATE TABLE の中に書く）
- 表と各列に COMMENT。
- 鍵の用途: `public.viewer_login_tokens` の `ck_viewer_login_tokens_purpose` を `('signup_code','password_reset','billing_form')` に付け替える（`DROP CONSTRAINT IF EXISTS` → `ADD CONSTRAINT`。1 トランザクション）。`purpose` の COMMENT に `billing_form＝請求先フォーム` を足す。
- 書き方は `migrations/20261016_150000_add_viewer_accounts.sql` にそろえる。
- 着手前に確かめること: `git grep -n "password_reset'" origin/main -- backend migrations` で、用途の値を並べている所（CHECK 以外）を全部探し、報告に書く。並べている所が CHECK だけでなければ、そこも `billing_form` を足すかを design どおりに判断し、判断の理由を報告に書く。

### 3-2. 今ある migration の一覧に足す（新しい migration には書かない。design §3-2 の「足す場所は2つ」）

- `migrations/20261031_210000_create_ops_case.sql` の拒否表の一覧（:91〜:101 付近）に `('viewer_billing_profiles', '請求先（宛名・住所・電話）')`。
- `migrations/20261024_100300_create_ai_cloud_views.sql` の `viewer_accounts` の2行（:298〜:299 付近）の後ろに:
  - `('public','viewer_billing_profiles',ARRAY['address','bill_to_name','contact_name','invoice_email','phone','postal_code'],'mask','')`
  - `('public','viewer_billing_profiles',ARRAY['party_type'],'allow','値の決まり ck_viewer_billing_profiles_party_type で値が限られる')`
  - :3 のコメントの「1068 行」→「1075 行」。
- `migrations/20261020_120000_create_viewer_message_templates.sql` :11 の「台帳の9件」→「台帳の10件」。

### 3-3. backend

- 文面: `viewer_message_templates.py` の LEDGER（:43〜:53 付近）に鍵 `billing_form_request` を1件。送り方は auto。差し込み項目は `form_url` と `form_expires`（`expires_date` は使わない）。
- 鍵を作る入口は1つ: 新しい `backend/app/services/viewer_billing_form.py` に関数を1つ置き、送る API はそれだけを呼ぶ（`viewer_signup.py:19` の「唯一の入口」と同じ形）。中身: 名簿の状態が active でなければ例外（router で 409 `viewer_status_conflict`）、無い人は 404（`super_admin_viewers.py` :51〜:57 の `_ERROR_STATUS` を使う）。同じ人の `billing_form` の鍵を消してから1本作る。期限は7日。鍵の作り方（乱数・sha256・保存）はパスワード再設定（`viewer.py` :331〜:342 付近）と同じ。
- 送る API: `POST /api/v1/super-admin/viewers/{viewer_id}/send-billing-form`（`require_super_admin`。本文なし）。置き場所と並びは今の `reissue-signup-code`（`super_admin_viewers.py` :358〜:399 付近）にそろえる。順番は design §3-6 の①〜⑥どおり:
  ①テンプレートの本文を読む。無ければ 503（`_TEMPLATE_NOT_FOUND`）・何も変えない
  ②入口の関数で古い鍵を消し新しい鍵を作る
  ③差し込み後の文が作れなければ（render が None。2000 字超え）rollback して 503
  ④commit
  ⑤commit の後で部屋へ送る（`viewer_room_notice.py` :69 の `notify_prepared` に `(True, 文)` と名簿の行を渡す。中で :25 の `send_room_notice` が送る。部屋が無ければ `no_room`）
  ⑥メールを裏で送る手配（宛先は `invoice_email` ではなく名簿の `email`。請求先がまだ無い人にも送るため）
- 応答の型 `ViewerBillingFormSendResponse`: `room_notice`（`"sent"`／`"failed"`／`"no_room"`）・`room_notice_text`（部屋へ送ろうとした文。`notify_prepared` の戻り値どおり、sent のときも返る。リンクを含む）・`mail_queued`・`expires_at`。
- リンク: `{rp_origin}/viewer/#billing={鍵}`（`viewer.py` :347 付近の再設定のリンクと同じ作り方）。`form_expires` は期限の日付（日本時間）。
- メールの送信部: `auth_mail.py` に `send_viewer_billing_form_email(to_addr, subject, body)` を足す。`format` をかけず、受け取った文をそのまま送る。SMTP の設定の読み方・宛先の伏せ方・失敗をログにだけ残す形は `_send_reset_mail`（:97〜:117 付近）と同じ。件名はコードの定数（:130 付近の並び）。本文は部屋と同じテンプレートから作った文。
- 請求先を読む API（管理画面の表示用）: `GET /api/v1/super-admin/viewers/{viewer_id}/billing-profile`（`require_super_admin`）。行が無ければ 200 で `null`。名簿の一覧・詳細の応答には請求先を足さない（正本は表1つ・読む口も1つ）。
- フォームの API（`viewer.py`。design §3-6「フォームの置き場所と受け口」どおり）:
  - `POST /api/v1/viewer/billing-form/open {token}`: 鍵を使い切らずに確かめ、今の請求先（無ければ空）を返す。鍵が無い・期限切れ・用途違い・本契約でない人は、どれも同じ 400（理由を分けない）。
  - `POST /api/v1/viewer/billing-form/submit {token, 7項目}`: 項目の検査 → `DELETE … RETURNING` で鍵を使い切る → 名簿が active でなければ鍵を消したまま commit して 400 → active なら `INSERT … ON CONFLICT (viewer_account_id) DO UPDATE`（`updated_at = now()`）→ commit。保存に失敗したら rollback（鍵は残る）。
  - 2本とも最初に `_require_app_origin`、次に `check_auth_rate_limit`（超えたら 429）。鍵が無効のときは `record_auth_failure`。
  - 2本は閲覧者のトークンを見ない公開の入口（鍵は本文の1回きりの鍵だけで確かめる。get_current_viewer を使わない）。このため `backend/tests/test_viewer_isolation.py` の `_PUBLIC_NO_AUTH_ROUTES`（:27〜:62）に2本を足し、足した理由をコメントで1行書く（同じ形の B2B の請求先フォーム `POST /api/v1/public/register/change-billing` が既にここにある）。`backend/app/auth/viewer_allowlist.py` の `VIEWER_ROUTE_ALLOWLIST` には足さない（ADR-1019 決定5 の「閲覧者のトークンで呼べる7本」は変えない）。
- 即時反映の対応表（ADR-1016）: `backend/app/realtime/topics.py` の `NO_SIGNAL_ROUTES`（:123〜:135 付近の閲覧者の行の並び）に、書き込みの口3本（`POST /api/v1/super-admin/viewers/{viewer_id}/send-billing-form`・`POST /api/v1/viewer/billing-form/open`・`POST /api/v1/viewer/billing-form/submit`）を足す。理由の文は既にある閲覧者の行と同じ形（例「閲覧ページ ADR-1019: 閲覧者の請求先フォームは画面更新の通知対象外」）。足さないと `backend/tests/test_realtime_topics.py` が赤になる（topics.py:5）。`WRITE_ROUTE_TOPICS` には足さない。
  - 入力の検査は DB の CHECK と同じ決まりを pydantic にも書く（郵便番号・電話はハイフンと空白を外してから数字だけにする。外した後の値で検査する）。
- ログ・応答に鍵・宛名・住所・電話を出さない（ログは名簿の番号と結果だけ）。送る API の応答の `room_notice_text` は例外（design §3-6。super admin だけが見る）。

### 3-4. 画面

- 金型だけを使う（ADR-144）。色・余白はデザイントークンだけ（ADR-067）。文字はすべて `t()`（ADR-027）。新しい部品は作らない。金型にない部品が要ると分かったら、そこで止まって報告する。
- 閲覧者管理ページの詳細スライド（Drawer）:
  - 「請求先」の区切り: 7項目を文字で出すだけ（郵便番号は表示のときに `123-4567` の形）。まだ無いときは EmptyState。直す欄は作らない（直すのはお客さんのフォーム）。
  - 「請求先フォームを送る」ボタン（Button）: 本契約（active）の人のときだけ出す。押した結果（部屋へ送れた／送れなかった／部屋なし、メールの手配をした、期限）は、今の申込コードの再発行と同じ出し方。送れなかった・部屋なしのときは `room_notice_text` をコピーできるようにする（再発行と同じ部品）。409・503 は文言を `t()` で出す。
- 閲覧ページ（`frontend/src/pages/viewer/`）:
  - `ViewerApp.tsx`: `RESET_HASH_PREFIX` と並べて `"#billing="` を足す。鍵の読み方・URL から消す処理・画面の種類・画面の出し分けは、再設定と同じ形（design §3-6）。
  - `BillingFormView.tsx`: 見本は `PasswordResetView.tsx`・`SignupView.tsx`。使う部品は TextField・Radio（会社か個人か）・Button・EmptyState。会社のときだけ担当者名の欄を出す。開いたら open を呼び、前の値を入れる。無効の鍵なら無効の案内（EmptyState）だけ出す。送れたら完了の案内。
  - 文言は閲覧ページ専用の辞書 `frontend/src/locales/viewer/` に入れる。キーの葉の名前に `searchNameCode`・`distributionOff`・`expiryWarning`・`windowUnlimited`・`resetSort` を使わない（`frontend/scripts/check-viewer-bundle.js` の MARKERS）。
  - 閲覧ページの JS の合計は300KB以内（`check-viewer-bundle.js` の LIMIT_KB）。超えたら止まって報告する。
- 管理画面の辞書（`frontend/src/locales/ja.json`・`en.json`）: テンプレートの名前（:2797〜:2805 付近）・使う場面（:2808〜:2816 付近）に `billing_form_request`、差し込み項目の説明（:2818〜:2828 付近）に `form_url`（ja「請求先フォームのURL（自動で入ります）」）と `form_expires`（ja「請求先フォームのリンクの期限の日付」）。en は同じ意味の英語。

### 3-5. プライバシーポリシー（`lp/src/pages/privacy.astro`。英語のページ。文はこのとおり入れる）

- 3.1 の表（:76 付近の `Account Information` の行の後ろ）に1行:
  `<tr><td>Inventory Viewer Billing Information</td><td>Billing name (company or individual), contact person, postal code, address, phone number, invoice email address</td><td>Billing form sent to contracted Inventory Viewer customers</td></tr>`
- 5.1 の箇条（:170〜:176 付近）の最後に1行:
  `<li>Issuing invoices to contracted Inventory Viewer customers</li>`
- 6.3 の表（:213 付近の `Inventory Viewer Account` の行の後ろ）に1行:
  `<tr><td>Inventory Viewer Billing Information</td><td>Deleted together with the Inventory Viewer Account</td></tr>`

### 3-6. 試験に足すもの（design §7 の便2の行。どの試験で確かめたかを報告の表に書く）

- `backend/tests/ops/test_ops_case_db.py` :656〜:664 付近: 関数名と集合を11件にする（`viewer_billing_profiles` を足す）。
- `backend/tests/ops/test_ai_cloud_views.py` :484 付近: 1068 → 1075。
- `backend/tests/test_viewer_purge.py` :143〜:149 付近の「消えた表」の並びに `viewer_billing_profiles` を足す。
- `backend/tests/test_viewer_message_templates.py` :22〜:25 付近の KEYS、`backend/tests/viewer_template_fixtures.py` の DEFAULT_BODIES、`frontend/src/pages/super-admin/ViewerTemplatesPage.test.tsx` の KEYS（:15〜:18 付近）と PLACEHOLDERS（:19〜:29 付近）に `billing_form_request`。
- 新しい PG 試験 `backend/tests/test_viewer_billing_form_pg.py`: CHECK ごとに1件ずつ拒否（会社で担当者が空・郵便番号が7桁でない・電話が10〜11桁でない・宛名が空）／名簿を消すと請求先も消える／2回送ると鍵は1本・前の鍵で開くと 400／送信成功で鍵0件・失敗で鍵が残る／本契約でない人の送る API は 409 で鍵0件／テンプレートが無いと 503 で鍵0件・送信部の呼び出し0回／期限は押した時刻から7日／「1か所だけ」の検査（design §3-2 の information_schema の数え方）。
- API 試験（同じファイルか、`backend/tests/test_super_admin_viewers.py` の並び）: 送信部（部屋とメール）を差し替えて回数と宛先を数える／部屋なしで `no_room` と `room_notice_text`／出どころ違いで止まる・回数超えで 429／open で鍵が残り今の値が返る。
- `backend/tests/test_viewer_isolation.py`: フォームの2本を `_PUBLIC_NO_AUTH_ROUTES` に足した後、この試験が passed（足さないと、2本が Origin なしで 403 を返して失敗する）。
- `backend/tests/test_realtime_topics.py`: 3本を `NO_SIGNAL_ROUTES` に足した後、この試験が passed。`backend/tests/test_origin_check_not_on_get.py`: GET billing-profile は Origin を確かめないので passed のまま。
- 画面試験: 閲覧者管理ページ（ボタンは active だけ・請求先の表示・空の案内）、閲覧ページ（`#billing=` で開く・会社のときだけ担当者欄・無効の鍵の案内）。

## 4. 守ること

- 担当は sleep しない（待ちは設計者が期限付きで行う）。
- ファイルの作成と編集は Write／Edit ツールで行い、ヒアドキュメントで書かない。
- PR を作る前に `scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し、exit 0 を確かめる（PR は Opus が作る）。
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える。
- 止まるのは次のときだけ: 本番への接続・DB への書き込み・マージ・`main` への push・`--force`・ファイルの削除が要るとき／金型にない部品が要るとき／design.md と食い違うのに design.md どおりに作れないとき／閲覧ページの JS が300KBを超えたとき／§2 の表に無いファイルを直さないと CI が通らないとき。
- 行番号のずれ・件数の食い違いは記録して続行し、報告に書く（判定は設計者がする）。
- 本番 DB・本番サーバーに接続しない。GO 記録・evidence-registry に書かない。マージしない。
- 試験の値・画面の見本に、実在の人の名前・住所・電話を使わない（`株式会社テスト`・`1000001`・`0300000000` のような作った値）。

## 5. 手順

クラウドで行う。手順1 で `new-worktree.sh` が作った作業場所のパス（以下「作業場所」）を報告に書き、手順1 の `cd 取り出した場所` はクラウドがこのリポジトリを取り出した最上位の場所に読み替え、手順2 以降の命令は毎回その作業場所へ cd してから流す。1手順1命令。

手順1 枝を作る（起点は origin/main）
    cd 取り出した場所 && git fetch origin
    cd 取り出した場所 && bash scripts/new-worktree.sh release/viewer-billing-form-bin2
    cd 作業場所 && git log -1 --format=%H
    cd 作業場所 && git rev-parse origin/main
    期待する出力: 作業場所のパスと、2つの番号が同じこと。報告に書く。違えば NEEDS_DECISION: で止まる。

手順2 便1 が入っているか確かめる
    cd 作業場所 && git grep -c "viewer_account_id" origin/main -- backend/app/services/tcg_distribution_svc.py
    期待する出力: 「origin/main:ファイル名:数」の1行で、数が1以上。何も出ずに終わったとき（一致0件。exit 1）は NEEDS_DECISION: 便1 が main に無い、で止まる。

手順3 対象ファイルが設計の基準から変わっていないか確かめる
    cd 作業場所 && git diff --stat d948cf9c7 origin/main -- migrations/20261016_150000_add_viewer_accounts.sql migrations/20261031_210000_create_ops_case.sql migrations/20261024_100300_create_ai_cloud_views.sql migrations/20261020_120000_create_viewer_message_templates.sql .github/workflows/migration-guard.yml backend/app/routers/viewer.py backend/app/routers/super_admin_viewers.py backend/app/services/viewer_signup.py backend/app/services/auth_mail.py backend/app/services/viewer_room_notice.py backend/app/services/viewer_message_templates.py backend/tests/ops/test_ops_case_db.py backend/tests/ops/test_ai_cloud_views.py backend/tests/test_viewer_message_templates.py backend/tests/viewer_template_fixtures.py frontend/src/pages/viewer frontend/src/locales/viewer frontend/src/pages/super-admin/ViewerTemplatesPage.test.tsx frontend/scripts/check-viewer-bundle.js lp/src/pages/privacy.astro
    期待する出力: 空。差分があれば記録して続行し、報告に書く。

手順4 §3-1 の着手前の確かめ（用途の値を並べている所）を流し、結果を報告に書く。
    cd 作業場所 && git grep -n "password_reset'" origin/main -- backend migrations

手順5 §3-1・§3-2 の migration を作り・直し、`scripts/run_all_migrations.sh` の並びの最後の `run_sql` の次の行に登録する（コメント行を1行添える。並びの書き方に合わせる）。`migration-guard.yml` の `PUBLIC_TABLES` に足す。

手順6 §3-3 の backend、§3-4・§3-5 の画面とポリシーを直し、§3-6 の試験を書く。

手順7 API の形を作り直す（手で書かない）
    cd 作業場所/backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json
    cd 作業場所/frontend && npm ci
    cd 作業場所/frontend && npm run generate:api-types

手順8 試験とビルドを流す
    cd 作業場所/backend && python -m pytest tests/test_viewer_billing_form_pg.py tests/test_viewer_purge.py tests/test_viewer_message_templates.py tests/test_super_admin_viewers.py tests/test_viewer_isolation.py tests/test_realtime_topics.py tests/test_origin_check_not_on_get.py tests/ops/test_ops_case_db.py tests/ops/test_ai_cloud_views.py -q
    期待する出力: 全部 passed。PostgreSQL が無くて skipped になったら、その数と理由を報告に書いて続行する（CI で確かめる）。
    cd 作業場所/frontend && npx vitest run src/pages/super-admin src/pages/viewer
    期待する出力: 全部 passed。
    cd 作業場所/frontend && npx tsc --noEmit
    期待する出力: exit 0。
    cd 作業場所/frontend && npm run build
    cd 作業場所/frontend && node scripts/check-viewer-bundle.js
    期待する出力: 閲覧ページの JS の合計（KB）と合格。数を報告に書く。300KB を超えたら止まる。

手順9 commit
    cd 作業場所 && git add -A
    commit 文は Write でファイルに書き（1行目 `feat: billing form for contracted viewer customers (bin2)`、末尾に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）、`git commit -F` で流す。active-work.d と `frontend/dist` は commit しない。
    cd 作業場所 && git log -1 --stat
    期待する出力: commit の番号と、§2 の表のファイルだけ。

手順10 差分の点検
    cd 作業場所 && git diff origin/main --numstat
    期待する出力: §2 の表のファイルだけ。削除の数（2列目）が 0 でないファイルは、名前と消えた行の中身を報告に書く（既存の行の書き換えはあってよい）。表に無いファイルがあれば、その名前を報告に書いて止まる。

手順11 push（PR は作らない。PR は Opus が手元で作る）
    cd 作業場所 && git push -u origin HEAD
    cd 作業場所 && git ls-remote origin release/viewer-billing-form-bin2
    期待する出力: 手順9 の commit と同じ番号。

## 6. 受入条件（design.md §7 の便2の行）

| 基準 | 検証方法 |
|---|---|
| 管理画面の文面テンプレートのページで、billing_form_request の差し込み項目 form_url・form_expires に日本語と英語の説明が出る | 画面テスト（ViewerTemplatesPage.test.tsx） |
| 請求先の項目は viewer_billing_profiles の1か所だけにある | DB の列の検査（information_schema）＋レビュー |
| 「請求先フォームを送る」ボタンは本契約の人の行にだけ出る。本契約でない人に API で送ろうとすると 409 で、鍵は作られない | 画面テスト＋API テスト＋PG テスト（鍵の件数 0） |
| ボタンを押すと、鍵が1本だけ残り（前の鍵は使えなくなる）、期限は押した時刻から7日 | PG テスト（2回押して件数1・前のリンクで開くと無効） |
| ボタンを押すと、部屋がある人は部屋に1通（結果 sent）、部屋が無い人は no_room と画面に出る。メールは名簿のメールあてに送る手配がされる | API テスト（送信部を差し替えて回数と宛先を数える）＋PO 目視 |
| 部屋とメールの文は、文面テンプレートの台帳の billing_form_request 1件から作られ、閲覧者管理ページで直すと次の送信から変わる | API テスト＋PO 目視 |
| フォームを送信して保存できたときだけ鍵が使い切られる。保存に失敗したら同じリンクで送り直せる。期限切れ・使用済み・本契約でなくなった人のリンクは無効の画面になる | PG テスト＋API テスト |
| 請求先の表の決まり: 会社なのに担当者が空・郵便番号が7桁でない・電話が10〜11桁でない・宛名が空の行は DB が入れない | PG テスト（CHECK ごとに1件ずつ） |
| テンプレートが無い状態でボタンを押すと 503 で、鍵は0件・メールも部屋も送られない | API テスト＋PG テスト |
| フォームの2本の API は、出どころが違うと止まり、回数を超えると 429 | API テスト |
| 開くだけでは鍵が残り、今の請求先が返る。送信が成功すると鍵が0件になる | PG テスト＋API テスト |
| 請求先は本番の AI 読み取りから見えない（deny_tables に入り、列の分類が個人情報） | PG テスト（test_ops_case_db・test_ai_cloud_views） |
| 名簿の行が消えると、その人の請求先も消える | PG テスト（test_viewer_purge） |
| プライバシーポリシーに請求先の項目と使い道が書かれている | レビュー＋PO 目視 |
| 閲覧ページの JS の合計が300KB以内 | 既存の CI（check-viewer-bundle.js）＋PR に数を書く |
| 画面に直書きの文字・色が無い | 既存の CI（i18n・デザイントークン・UI governance） |

PR について（Opus が作る。実装役は作らない）:

- Opus が手元で `scripts/gh-pr-create-safe.sh` を使い、ready（Draft にしない）で作る。本文は `.github/PULL_REQUEST_TEMPLATE.md` を起点にし、`scripts/dev/validate-pr-body.sh` に標準入力で渡して exit 0 を確かめてから出す。
- 欄の良い例: `触るファイル: scripts/run_all_migrations.sh, backend/app/routers/viewer.py`（1行・カンマ区切り・実際のファイル名）。禁止形: 箇条書き／ファイル名の後ろの注記／テンプレの仮の値を残す。
- `区分: A`、`PO承認:` に PO の実装承認の言葉と日時、`Opus 審査記録: docs/handoff/viewer-customer-sheet/review-opus.md`、`対象ADR: ADR-1019`、`設計仕様書（あるべき姿）: docs/specs/inventory-management/inventory-viewer/README.md`。
- migration と `.github/` を含むので、マージは GO（ADR-136 の形）まで待つ。
- 本番へ出した後、ボタンを使う前に、管理画面の文面テンプレートのページで billing_form_request の文を1回保存する（PO か管理者。Opus が PO に頼む）。

## 7. 報告

- 報告の冒頭に「本報告はカード 便2（請求先フォーム）の実行結果である」と書く。
- 受領確認: 受け取ったら最初に「カード 便2 を受領」と1行書く。
- 完了報告の本文に、手順1・2・3・4・8・9・10・11 の生出力を全文含める。枝の名前と push した commit の番号を書く。§6 の各行をどの試験で確かめたかの表を書く。
- 止まったときは「止まった手順の番号／最後に実行したコマンド／止まった理由」と生出力を書いて終える。
- 最後の行に `DONE`、止まったら `BLOCKED: 理由`、判断が要るなら `NEEDS_DECISION: 内容` と書く。

END OF CARD
