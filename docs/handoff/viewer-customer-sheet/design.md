# design（草案）: 閲覧者管理ページを在庫解析ツールの顧客管理にする — 要件定義と DB 設計

> この文書は何か（専門用語なしの1行）:
> 本契約のお客さんごとにシートへ配信し、請求先をフォームで集め、あとでツール用の請求書を作れるようにするための、決めごとと DB の置き方の下書き。

- 親（設計仕様書）: [docs/specs/inventory-management/inventory-viewer/README.md](../../specs/inventory-management/inventory-viewer/README.md)
- 現状の記録: [recon.md](./recon.md)
- 関係 ADR: [ADR-1019](../../adr/ADR-1019-inventory-viewer-separate-accounts.md)（改訂が要る。recon §2）、ADR-1014（在庫の行の定義は1か所）、ADR-144・ADR-067（金型とデザイントークン）、ADR-027（i18n）
- 状態: **草案・PO 未承認・設計審査1回目 REVISE（2026-11-04）の指摘9件・2回目 REVISE の指摘7件・3回目 REVISE の指摘6件を反映済み・4回目 APPROVE（LOW 1件＝分類表の件数 1068→1075 を反映済み）**。下の「§6 PO に決めてもらうこと」が全部決まるまで、設計合格にも実装にも進まない。

## 1. 目的（PO の言葉から）

- 閲覧者管理ページを、在庫解析ツールの顧客管理として使う（B2B トレカの顧客管理とは分ける）。
- 本契約のお客さんには、そのお客さんが共有したブックへ個別に在庫を配信する。
- 本契約のときに、請求書に使う情報をお客さんにフォームで書いてもらう。
- ツール用の請求書を作る機能は別に作る。今回は、そのための DB の決めごとを先に決める。

## 2. 対象と対象外

- 対象（この設計で決める）: 名簿・請求先・配信先・ツール用請求書の DB の置き方とつなぎ方、閲覧者管理ページで見せる範囲、フォームの項目、消す決まりとの関係。
- 対象外: ツール用請求書の画面・PDF・金額の計算（別テーマで設計する。ここでは表の要件だけ決める）。B2B トレカの請求書と顧客管理（触らない）。配信する在庫の行の中身（ADR-1014 のまま。お客さんごとに中身は変えない）。

## 3. 要件（案）

### 3-1. 正本の置き場所（1つの情報は1か所だけ）

| 情報 | 正本の置き場所 | 他の場所には |
|---|---|---|
| お客さん本人（メール・LINE 名・状態・期限） | public.viewer_accounts（今のまま） | 写さない。B2B の取引先（tenant_004.companies）にもつながない |
| 請求先（フォームで書いてもらう項目） | 新しい表 public.viewer_billing_profiles（お客さん1人に1行） | 名簿にも配信先にも写さない |
| シート（ブックの番号・タブ名・最後の配信） | public.tcg_distribution_targets（今のまま） | 名簿に写さない |
| どのシートが誰のものか | tcg_distribution_targets に足す1列 viewer_account_id（名簿の番号だけ） | 名簿側には持たない（向きは一方向） |
| 発行した請求書の宛先 | 将来の public.viewer_invoices の行に、発行した時点の宛先を写して残す | — （下の 3-4 の理由で、これは「分散」ではなく発行時点の記録） |

### 3-2. 請求先の表 viewer_billing_profiles（案）

- お客さん1人に1行。名簿の番号 viewer_account_id を主キーにする。
- 名簿の行が消えたら一緒に消える（ON DELETE CASCADE）。消す決まり（recon §3）と同じ扱いになる。
- 名簿に列を足さず別の表にする理由:
  1. お試しの人は請求先を持たない。名簿に空の列が並ばない。
  2. 本番の AI 読み取り（ai_ro）で、請求先だけを隠す設定にしやすい。
  3. フォームを出した時刻・直した時刻を、請求先の塊として持てる。
- 前提（Q3 決定 2026-11-04 PO 原文「2」＝お客さんは国内だけ／「登録済み」＝HIGH LIFE JPN はインボイス制度の登録済み）。円と消費税の国内向けの請求書にする。国の欄・通貨・海外の税番号（B2B の country・tax_id）は持たない。
- HIGH LIFE JPN の登録番号（T と13桁）は、こちらの設定として1か所に置き、請求書に印字する。お客さんのフォームでは聞かない。値の受け取りと置き場所は請求書の便で決める。
- 項目（Q3c 決定 2026-11-04 PO「1」＝下の7項目で決める）:

| 項目 | 必須か | 理由 |
|---|---|---|
| 宛名（会社名・屋号、または個人名） | 必須 | 国税庁 No.6625 の記載事項「交付を受ける者の氏名または名称」 |
| 会社か個人か | 必須 | 宛名の後ろを「御中」「様」のどちらにするか決める |
| 担当者名 | 会社のときだけ | 「〇〇株式会社 △△様」と書くため |
| 郵便番号 | 必須 | 請求書の宛先として一般的な記載（法律の必須ではない） |
| 住所 | 必須 | 同上 |
| 電話番号 | 必須 | 支払いの連絡用 |
| 請求書を送るメール | 任意 | 空なら名簿のメール（viewer_accounts.email）を使う。名簿のメールは写さない（正本は名簿） |

- 表の定義（名簿の migration migrations/20261016_150000_add_viewer_accounts.sql の書き方にそろえる。RLS なし＝テナントを持たない public の表のため、同ファイル冒頭と同じ）:

| 列 | 型 | NULL | 決まり（CHECK は名前付き ck_viewer_billing_profiles_*） |
|---|---|---|---|
| viewer_account_id | BIGINT 主キー | 不可 | REFERENCES public.viewer_accounts(id) ON DELETE CASCADE |
| party_type | TEXT | 不可 | 'company' か 'individual' のどちらか |
| bill_to_name | TEXT | 不可 | 1〜100 字（char_length、前後の空白を除いて1字以上） |
| contact_name | TEXT | 可 | 1〜50 字。party_type='company' のときは必須（CHECK: party_type <> 'company' OR contact_name IS NOT NULL） |
| postal_code | TEXT | 不可 | 数字7桁だけ（'^[0-9]{7}$'。ハイフンは画面で外してから保存し、表示のときに付ける） |
| address | TEXT | 不可 | 1〜200 字 |
| phone | TEXT | 不可 | 数字10〜11桁だけ（'^[0-9]{10,11}$'。ハイフンは保存しない） |
| invoice_email | TEXT | 可 | 3〜254 字で '@' を含む（名簿の email の CHECK と同じ形） |
| created_at / updated_at | TIMESTAMPTZ | 不可 | DEFAULT now()。updated_at は保存のたびに now() |

  - 各列に COMMENT を付ける。§7 の「1か所だけ」の検査: information_schema.columns で、table_schema='public' のうち bill_to_name・contact_name・invoice_email・party_type の4列を持つ表が viewer_billing_profiles の1つだけであること、かつ viewer_accounts と tcg_distribution_targets に請求先の7列のどれも無いことを数える（postal_code・address・phone は B2B の tenant_* の表にもあるので、public と名簿・配信先に絞って見る）。
  - 請求先は個人情報なので、本番の AI 読み取りからは隠す。足す場所は2つとも「今ある migration の中の一覧」で、新しい migration には書かない（観測事実: どちらのファイルも配備のたびに流し直され、先頭で表を空にしてから一覧を入れ直す。新しい migration で足した行は次の配備で消える）。
    1. 拒否表 ops_case.deny_tables: migrations/20261031_210000_create_ops_case.sql:91〜:101 の一覧に ('viewer_billing_profiles', '請求先（宛名・住所・電話）') を足す（:90 で表を空にする。scripts/run_all_migrations.sh:1205 で毎回流す）。試験 backend/tests/ops/test_ops_case_db.py:656〜:664 の10件を11件にする。
    2. 列の分類 ai_cloud_meta.column_class: migrations/20261024_100300_create_ai_cloud_views.sql の、viewer_accounts の行（:298〜:299）の後ろに足す（:11 で表を空にする。run_all_migrations.sh:234・:253 で毎回流す）。足す行は ('public','viewer_billing_profiles',ARRAY['address','bill_to_name','contact_name','invoice_email','phone','postal_code'],'mask','') と ('public','viewer_billing_profiles',ARRAY['party_type'],'allow','値の決まり ck_viewer_billing_profiles_party_type で値が限られる')（:299 の status と同じ書き方）。分類表は配列を列ごとにほどいて1列1行で入る（同ファイル :13〜:16 と末尾の CROSS JOIN LATERAL unnest）ので、足す2行は7件になる（mask 6列＋allow 1列）。試験 backend/tests/ops/test_ai_cloud_views.py:484 の 1068 を 1075 にし、同じ migration の :3 のコメント「1068 行」も「1075 行」に直す。
    3. 配信先の新しい列 tcg_distribution_targets.viewer_account_id には分類の行を足さない。理由: 型が BIGINT（int8）で、そのまま出してよい型の一覧（test_ai_cloud_views.py:50〜:53 の _PASS_TYPES）に入り、列名も名前の見張り（同 :44〜:47 の _NAME_RE）に当たらないため、T10 の分類漏れ検査（同 :490〜:530）の対象外。viewer_billing_profiles の viewer_account_id・created_at・updated_at も同じ理由で行は要らない。


### 3-3. 配信先とお客さんのつなぎ（案）

- tcg_distribution_targets に viewer_account_id（BIGINT・NULL 可・public.viewer_accounts(id) を指す）を足す。
- NULL は「特定の人用ではないシート」（無料トライアルシート・配信テスト）。
- 配信するかの決まり（Q1 決定 2026-11-04 PO 原文「停止したら自動で止める。停止を外したら自動で再開する【おすすめ】」・Q1b 決定 2026-11-04 PO 原文「本契約の人にだけ配信する。お試しの人は、登録してあっても配信しない【おすすめ】」）:
  - 配信するかどうかの判定は、今 is_active だけを見ている（backend/app/services/tcg_distribution_svc.py:990〜:994）。ここに「viewer_account_id がある行は、その人の状態が active（本契約）のときだけ配信する」を足す。pending・verified・trial（期限切れを含む）・suspended はどれも配信しない。viewer_account_id が NULL の行は今までどおり is_active だけで決める。
  - 判定の置き場所は1つ: list_targets・get_target（同ファイル :701〜:724）の SELECT で名簿を LEFT JOIN し、各行に「配信するか（deliverable）」と「しない理由（manual_off／not_contracted／suspended）」を SQL で出す。理由が重なるときは1つだけ出し、順番は manual_off → suspended → not_contracted（手で止めたことを最優先で見せる。停止中の人は not_contracted より先に suspended と出す）。SQL は CASE WHEN NOT is_active THEN 'manual_off' WHEN status='suspended' THEN 'suspended' WHEN viewer_account_id IS NOT NULL AND status<>'active' THEN 'not_contracted' END の1か所。:990〜:994 は is_active ではなく deliverable を見る。is_active を別に見ている所も、この2つの値を読むように直す（判定を書き写さない）:
    - backend/app/line_import_admin.py:139（配信前の点検で返す active。:134 の targets も同じ）
    - backend/app/services/tcg_analysis_dashboard_svc.py:665〜:687（解析ダッシュボードの配信の数。自前の SELECT を list_targets の呼び出しに替える）
    - 配信先の画面（frontend/src/pages/super-admin/TcgDistributionPage.tsx）と閲覧者管理ページの表示（下の §3-5）
  - is_active は書き換えない。理由: 停止で is_active を false にすると、「手で止めた」と「停止で止まった」が同じ値になり、停止を外したときにどちらへ戻すか分からなくなる。状態は名簿の status の1か所から読む。
  - 停止を外すと、名簿は停止の前の状態に戻る（backend/app/services/viewer_admin.py:239〜:253 が状態の記録 viewer_status_changes の直前の from_status を読んで戻す）。戻った状態が active なら次の配信から自動で書き込みが戻る。trial に戻った人は配信しないまま。is_active を手で false にしたシートは、停止を外しても止まったまま。
  - お試しの人を本契約にすると（trial → active。backend/app/services/viewer_admin.py:231〜:233）、シートが登録済みなら次の配信から自動で書き込みが始まる。
  - 配信先の画面と閲覧者管理ページには、配信していない理由（停止中／本契約でない）が分かる表示を出す（文言は t() の新しいキー）。
- 名簿の行が消えたとき（停止の90日後の自動削除。recon §3）: 配信先の行も一緒に消す（ON DELETE CASCADE）。
  - SET NULL にしない理由: 目印が空になると「特定の人用でないシート」と同じ扱いになり、停止の判定から外れて配信が再開してしまう。
  - RESTRICT にしない理由: 毎日の自動削除（backend/app/tasks/maintenance.py:220）が失敗し、ポリシーに書いた90日を守れなくなる。
- 1人が持てるシートは1つまで（Q2 決定 2026-11-04 PO「1」）。DB で強制する: viewer_account_id に「NULL でない値は1回だけ」の一意の索引（部分一意索引 WHERE viewer_account_id IS NOT NULL）。NULL（特定の人用でないシート）は何件でもよい。2件目の登録は API が 409 を返し、画面は t() の文言で知らせる。
- viewer_account_id を書く入口は1つ: 今の create_target・update_target（tcg_distribution_svc.py:727〜:775）に viewer_account_id を足す（:731 の INSERT 列、:753 の allowed）。2つの画面はどちらも今の API（backend/app/routers/tcg_distribution.py:99〜:132 の POST・PUT /tcg/distribution/targets）を呼ぶ。閲覧者管理ページ用の別の書き込み API は作らない。
  - 入出力の型にも足す: 入力の型 DistributionTargetCreate・DistributionTargetUpdate（routers/tcg_distribution.py:44・:52）に viewer_account_id（int | None）。解析ダッシュボードの応答の型 DistributionTargetItem（backend/app/routers/tcg_analysis_dashboard.py:184）に viewer_account_id・deliverable・理由（reason）。型に無い値は応答から落ちるため。
  - 配信先の削除（soft_delete_target。tcg_distribution_svc.py:778〜:789）は、今は行を消さず is_active を false にするだけ。このままだと消したシートに viewer_account_id が残り、上の一意の索引で同じ人の新しいシートが 409 になる。削除のときに viewer_account_id も NULL にする（同じ UPDATE の1文で）。索引の条件に is_active を入れる案は採らない。理由: 手で止めた（is_active=false の）シートが残っている人に2枚目を登録できてしまい、「1人1つ」（Q2）が崩れる。手で止めることと削除は、今は同じ is_active=false で区別できない。区別は「つなぎが残っているか」で付く（止めた＝残る、削除＝外れる）。
  - 一意の索引の名前は uq_tcg_distribution_targets_viewer_account_id。IntegrityError は SQLSTATE で分ける: 23505（一意違反）かつ索引名が上の名前なら 409、23503（外部キー違反＝名簿に無い番号）なら 422。どちらも svc が専用の例外に直し、router が返す（同ファイル :163 の 409 と同じ形）。それ以外の IntegrityError はそのまま上げる。
  - 今の create_target・update_target は RETURNING で行を返す（svc :734・:767）が、この形では名簿を JOIN できず deliverable と理由が入らない。書いたあとは get_target で読み直して返す（判定を書き写さないため）。
  - つなぎを外す（NULL に戻す）ことができるようにする: 今の PUT は model_dump(exclude_none=True)（:129）なので、null を送っても捨てられる。viewer_account_id だけは「送られたか」（model_fields_set）で判断し、null が送られたら NULL にする。
  - 名簿に無い番号は外部キーで止まる。上のとおり 422 にする（理由の文言を t() で出す）。
- シートを自動で作らない決まり（tcg_distribution_svc.py:15 の #2）は変えない。お客さんが共有したブックの番号を登録する。

### 3-4. ツール用請求書の表（要件だけ・作るのは別テーマ）

- public.viewer_invoices（仮の名前）。B2B の tenant_004.invoices とは別の表にする（PO 方針）。
- 発行した時点の宛先（請求先の項目）を、請求書の行に写して残す。B2B の請求書と同じ方式（recon §6）。
  - 理由1: 発行したあとで請求先が直されても、出した請求書の中身は変わってはいけない。
  - 理由2: 名簿の行は停止の90日後に自動で消える（recon §3）。請求書は7年残す決まりがある（recon §7）。請求書が名簿に頼ると、宛先が消える。
- 名簿の番号 viewer_account_id は持つが、名簿の行が消えたら NULL にする（ON DELETE SET NULL）。請求書の行は消さない。
- 【確認済み 2026-11-04】交付した請求書の写し（電子で渡したものはそのデータ）も、交付した日の属する課税期間の末日の翌日から2か月を過ぎた日から7年間の保存が要る（国税庁 インボイス制度Q&A 問79【令和5年10月改訂】、消法57の4⑥・消令70の13①。recon §7）。写しは記載事項が確かめられる一覧や明細でもよい（同 問78）。発行時点の宛先の写しを請求書の行に持つ方式（§3-4）で足りる。

### 3-5. 閲覧者管理ページ（画面の要件・案）

- 今の詳細スライドに、「配信するシート」と「請求先」の2つの区切りを足す。
- 配信先の画面（/super-admin/tcg-distribution）は残す。両方の画面が同じ表を読み書きする（写しを作らない）。
- 部品は既存の金型だけを使う（ADR-144）。新しい部品が要る場合は、先に金型として登録してから使う。文字はすべて t() を通す（ADR-027）。色・余白はデザイントークンだけ（ADR-067）。
- 部品の当てはめ（観測事実: 閲覧者管理ページ frontend/src/pages/super-admin/ViewerAccountsPage.tsx:15〜:28 が既に金型の PageLayout・Button・Badge・DataTable・EmptyState・Drawer・Stack・Modal・TextField・Radio・Select を読み込んでいる）:
  - 「配信するシート」: Drawer の中に Stack で、シートの名前・最後の配信時刻・結果を文字で、配信していない理由を Badge で出す。登録・変更は Modal＋TextField（ブックの番号・タブ名）＋Button。
  - 「請求先」: 7項目を文字で出すだけ（直すのはお客さんのフォーム）。まだ無いときは EmptyState。
  - 「請求先フォームを送る」: Button。結果（部屋へ送れた／送れなかった／部屋なし、メールの手配）は今の発行の操作と同じ出し方にする。
  - 新しい部品は要らない。

### 3-6. フォーム（要件・案）

- 本契約のときに、お客さんが自分で請求先を書く。
- 入口（Q4 決定 2026-11-04 PO「2」＝フォーム用の専用リンクをお客さんに送る。ログインは要らない）。
- 専用リンクの仕組み（今ある使い捨ての鍵を使い回す。新しい鍵の表は作らない）:
  - 観測事実: public.viewer_login_tokens（migrations/20261016_150000_add_viewer_accounts.sql:39〜:49）が、鍵のハッシュだけを保存し（:42・:46・:47）、期限（:44）と用途（:43・:48 の CHECK は 'signup_code'／'password_reset' の2つ）を持つ。パスワード再設定は、鍵を1回だけ・期限内だけ使える（backend/app/routers/viewer.py:331〜:342 で古い鍵を消してから作る、:369〜:378 で DELETE…RETURNING して使い切る）。
  - 用途に 'billing_form' を足す（CHECK を変える移行が1本要る）。鍵の作り方・使い切り方はパスワード再設定と同じにする。
  - 名簿の行が消えると鍵も一緒に消える（:41 ON DELETE CASCADE）。
  - 鍵を作る入口は1か所に置く。backend/app/services/viewer_signup.py:19 の「唯一の入口」と同じ形で、請求先フォーム用の関数を services に1つ作る。閲覧者管理ページの発行 API とメール送信は、その関数だけを呼ぶ。
  - 期限は password_reset の30分（backend/app/routers/auth.py:577 を viewer.py:49 で読み込み）を使わない。7日にする（Q4b で決定）。
  - 送る道は2つある（観測事実）。メールは backend/app/services/auth_mail.py:130 send_viewer_password_reset_email。Discord の部屋は backend/app/services/viewer_room_notice.py:25 send_room_notice（状態を変えた直後に、DB のテンプレートから文を作って送る。:1〜:6）。
  - 本番（reader 鍵・2026-11-04 16:57 JST、生出力 /tmp/CC報告ファイル/viewer-room-prod.txt）: 本契約3人のうち、メールあり3人・Discord の部屋あり2人。
- 送り方（Q4b 決定 2026-11-04 PO 原文「2、フォームを送るボタンを作ってボタンを押したらフォームを送る作りにしたい」＝ボタンで、メールと Discord の部屋の両方に送る。期限は7日）:
  - 閲覧者管理ページの、本契約の人の行に「請求先フォームを送る」ボタンを置く（文言は t() の新しいキー。部品は金型の Button）。本契約でない人には出さない。API も active 以外は 409 で断る。
  - 押すと、鍵を1本作り（古い鍵は消える）、同じリンクをメールと部屋の両方に送る。期限は7日。
  - 文の正本は1か所: Discord の文面テンプレートの台帳（backend/app/services/viewer_message_templates.py:43〜:53 の LEDGER。本文は public.viewer_message_templates、migrations/20261020_120000_create_viewer_message_templates.sql:3）に、鍵 billing_form_request（送り方は auto＝仕組みが部屋へ送る。差し込み項目は form_url と form_expires）を1件足す。expires_date は使わない（今は「お試し期限の日付」の意味で interview_request が使い、管理画面の差し込み項目の説明 frontend/src/locales/ja.json:2827 もその意味。frontend/src/pages/super-admin/ViewerTemplatesPage.tsx:275 が placeholders の名前ごとに説明を出すので、同じ名前を別の意味で使うと説明が食い違う）。auto の文は差し込み後 2000 字を超えると送らない（viewer_message_templates.py:22・:154）。手で写して送る manual（例 signup_request、backend/app/routers/super_admin_viewers.py:184〜:186）とは違う。メールの本文も同じテンプレートから作る。メールの件名だけは、ほかの閲覧者メールと同じくコードの定数に置く（backend/app/services/auth_mail.py:130 の並び）。
  - メールの送信部は新しく1つ作る（例 send_viewer_billing_form_email(to_addr, subject, body)）。今の _send_reset_mail（auth_mail.py:97〜:117）は :108 で本文に format(reset_url=…) をかけ直すので、テンプレートから作った文（{ や } を含み得る）を渡すと壊れるか例外になる。新しい関数は format をかけず、受け取った文をそのまま送る。SMTP の設定の読み方・宛先の伏せ方・失敗をログにだけ残す形（:99〜:102・:114〜:117）は同じにする。_send_reset_mail は変えない。
  - テンプレートが無いとき（load_body が None。viewer_message_templates.py:111）: 鍵を作らず、メールも部屋も送らず、API は 503（今の管理 API と同じ _TEMPLATE_NOT_FOUND。backend/app/routers/super_admin_viewers.py:189・:220・:367〜:368）を返して画面で知らせる。差し込み後に 2000 字を超えて render が None を返したとき（:135・:154）も同じ。どちらも鍵を作る前か、作った同じトランザクションを rollback して、鍵は残さない。
  - テンプレートの初期値の入れ方（観測事実: migrations/20261020_120000_create_viewer_message_templates.sql:2 は「専用 CLI（viewer_template_cli）で入れる」と書くが、その CLI は origin/main に無い）: 管理画面の文面テンプレートのページから入れる。行が無い鍵は保存で INSERT される（viewer_message_templates.py:185〜:192、backend/app/routers/super_admin_viewers.py:237〜:259）。本番へ出したあと、ボタンを使う前に PO か管理者が文を1回保存する。これを本番の確かめの手順に入れる。
  - 部屋へは今ある送り方を使う（backend/app/services/viewer_room_notice.py:25 send_room_notice）。部屋が無い人は送らず、結果を no_room として画面に出す（同ファイル :80〜:83 と同じ扱い）。
  - 管理 API（置き場所は backend/app/routers/super_admin_viewers.py。今の reissue-signup-code（:358〜:399）と同じ並び）:
    - POST /api/v1/super-admin/viewers/{viewer_id}/send-billing-form（require_super_admin）。本文なし。
    - 順番: ①テンプレートの本文を読む（無ければ 503・何も変えない。:363〜:367 と同じ）②services の1つの関数で古い鍵を消して新しい鍵を作る（active 以外は 409 viewer_status_conflict、無い人は 404。:51〜:57 の _ERROR_STATUS をそのまま使う）③差し込み後の文が作れなければ rollback して 503 ④commit ⑤commit の後で部屋へ送る（viewer_room_notice の notify_prepared の形。DB を開けたまま Discord を待たない）⑥メールを裏で送る手配をする。
    - 応答（新しい型 ViewerBillingFormSendResponse）: room_notice（"sent"／"failed"／"no_room"。viewer_room_notice.py:80 と同じ値。テンプレートは①で確かめ済みなので no_template は出ない）、room_notice_text（部屋へ送ろうとした文。リンクを含む）、mail_queued（メールを送る手配をしたか）、expires_at（リンクの期限）。
    - 部屋が無い・送れなかったときは room_notice_text を返し、画面でコピーできるようにする（今の状態変更の応答 :84〜:86 と同じ扱い）。文にはリンク（鍵）が入る。今の reissue-signup-code も申込コードと文を画面へ返している（:394〜:399）ので、同じ扱いにする。見られるのは super admin だけ。ログには文も鍵も出さない。
  - 画面には、部屋へ送れたか（送れた／送れなかった／部屋なし）と、メールを送る手配をしたことを出す。メールは裏で送るので、届いたかは画面に出せない（auth_mail.py:97〜:117 は失敗をログにだけ残す）。
  - 送り直すと前のリンクは使えなくなる。同じ用途の古い鍵を消してから作るため（viewer.py:331〜:334 と同じ形）。
  - 鍵は、フォームを開いただけでは使い切らない。送信が viewer_billing_profiles への書き込みと同じトランザクションで成功したときだけ使い切る（viewer.py:364〜:378 と同じ順番）。
  - 発行するときと使うときの両方で、名簿の状態が active の人に限る（password_reset は viewer.py:327・:389 の両方で状態を確かめている）。
  - 鍵の表には、使った時刻は残らない（行を消すため）。いつ書いたかは viewer_billing_profiles の作成・更新の時刻で持つ。
  - 用途は 'billing_form' の1つにして、初めての記入とあとからの変更の両方に使う（請求先は1人1行を上書き）。
  - リンクの決まり（期限・何回使えるか・いつ送るか）は §6 の Q4b で決定済み（上の「送り方」）。
- フォームの置き場所と受け口（ログインは要らない＝Q4。パスワード再設定と同じ形にする）:
  - 置き場所は閲覧ページ。リンクは `{rp_origin}/viewer/#billing={鍵}`。再設定のリンク `{rp_origin}/viewer/#reset={鍵}`（backend/app/routers/viewer.py:347）と同じ形。
  - 閲覧ページの入口（frontend/src/pages/viewer/ViewerApp.tsx）に、:27 の RESET_HASH_PREFIX と並べて "#billing=" を足す。:31〜:35 と同じ形で鍵を読み、:63〜:65 と同じ形で読んだ鍵を URL から消す。画面の種類（:21〜:25）に billing{token} を足し、:149〜:150 と同じ形で請求先フォームの画面を出す。
  - API は2本。どちらも POST で、鍵は本文で受け取る（URL に載せない）。置き場所は backend/app/routers/viewer.py（/api/v1/viewer。backend/app/main.py:255）。
    1. POST /api/v1/viewer/billing-form/open {token}: 鍵を使い切らずに確かめ、今の請求先（無ければ空）を返す。初めての記入とあとからの変更の両方に使う決定（上の「用途は1つ」）のため、今の値を見せて直せるようにする。鍵が無い・期限切れ・用途違い・本契約でない人は、どれも同じ 400 を返し、理由を分けない（推し量られないため）。
    2. POST /api/v1/viewer/billing-form/submit {token, 7項目}: 先に項目を検査する（鍵はまだ使わない。viewer.py:364〜:366 と同じ順）。次に DELETE…RETURNING で鍵を使い切る（:369〜:378 と同じ）。名簿の状態が active でなければ、鍵を消したまま commit して 400（:383〜:391 と同じ。使えない鍵を残さない）。active なら viewer_billing_profiles に INSERT … ON CONFLICT (viewer_account_id) DO UPDATE で書き、同じトランザクションで commit する。保存に失敗したら rollback し、鍵は残る（同じリンクで送り直せる）。
  - 2本とも、最初に出どころの検査（_require_app_origin。backend/app/auth/origin.py の require_app_origin、viewer.py:359 と同じ）をし、回数制限（check_auth_rate_limit。backend/app/cache.py:311、viewer.py:361〜:362 と同じ。超えたら 429）をかける。鍵が無効のときは record_auth_failure（cache.py:328。viewer.py:380 と同じ）を数える。
  - 返す値と記録に、鍵・宛名・住所・電話を出さない（ログは名簿の番号と結果だけ）。
- B2B の登録フォーム（public.registration_tokens）を共用するかの比較（recon §9。PO 2026-11-04「顧客別のフォームを発行する機能はすでに使ってるので共用で使い回せる？」）:

| 案 | 中身 | B2B への影響 | 正本 |
|---|---|---|---|
| 甲 閲覧者の鍵の表を使う（採用） | viewer_login_tokens に用途 billing_form を足す。画面は B2B と同じ金型の部品で作る | なし | 鍵は名簿を指す（:41）。請求先は viewer_billing_profiles |
| 乙 B2B の鍵の表を共用 | registration_tokens の tenant_id・lead_id を空でもよくし、名簿を指す列と種類を足す。書き込みの制限（RLS）も変える | B2B の鍵の決まり（NOT NULL・RLS）と、鍵を作る関数の引数が変わる。B2B の登録フォームの試験のやり直しが要る | 鍵の表に B2B 用と閲覧者用が混ざる |

  - 甲でも、鍵の考え方（期限・1回だけ・ハッシュだけ保存）は B2B と同じにする。
  - Fable による評価（2026-11-04。生出力 /tmp/CC報告ファイル/fable-eval-token/）の判定は甲。乙で B2B 側が変わる所: NOT NULL の3列、RLS のポリシー4本、ADR-1018 の前提、鍵を作る関数の引数、公開 API の4経路、リード統合（backend/app/routers/leads.py:3028）、試験5本以上、表の写し4か所。
- 画面の部品: B2B の登録画面は写さない。直値（frontend/src/pages/register/RegisterPage.tsx:249・:322）と、金型にない自作の候補リスト（CountryCombobox.tsx:62〜:80）があるため。閲覧ページで金型だけを使って組まれている画面を見本にする（PasswordResetView.tsx:6〜:8、SignupView.tsx:6〜:9）。使うのは TextField（components/TextField.tsx:60）・Radio（components/Radio.tsx:27）・Button・EmptyState。金型にない部品は要らない。
  - 閲覧ページの JS の合計は300KB以内に収める（frontend/scripts/check-viewer-bundle.js:21 が CI で止める）。文言は閲覧ページ専用の辞書（frontend/src/locales/viewer/）に入れる。
  - 【未確認】今の閲覧ページの JS の大きさと、フォームを足したあとの大きさ。実装でビルドして測り、PR に数を書く。300KB を超えるなら実装を止めて設計に戻す（フォームの画面だけ別に読み込む等）。
- 預かる情報が増えるので、プライバシーポリシー（lp/src/pages/privacy.astro:76・:213）に書き足す。

### 3-7. 一緒に直す所（漏れると CI か本番で止まる。すべて origin/main で確認）

| 何を足すと | 直す所 |
|---|---|
| 新しい migration（請求先の表・配信先の列・鍵の用途） | scripts/run_all_migrations.sh の並び（名簿は :1153、テンプレートは :1191） |
| 新しい表 viewer_billing_profiles | .github/workflows/migration-guard.yml:224 の PUBLIC_TABLES（viewer_accounts 等と並べる）。ops_case.deny_tables と backend/tests/ops/test_ops_case_db.py:656〜:664（10件→11件）。ai_cloud_meta.column_class と backend/tests/ops/test_ai_cloud_views.py:484（1068→1075。:3 のコメントも）と T10 の分類漏れ検査 |
| 名簿を消すと消える表（請求先・配信先） | backend/tests/test_viewer_purge.py:143〜:149 の「消えた表」の並びに viewer_billing_profiles と tcg_distribution_targets を足す |
| 鍵の用途 billing_form | migrations/20261016_150000_add_viewer_accounts.sql:48 の CHECK を変える新しい migration と、:54 の COMMENT の書き直し |
| 文面テンプレートの鍵 billing_form_request | viewer_message_templates.py の LEDGER（:43〜:53）。migrations/20261020_120000_create_viewer_message_templates.sql:11 の「台帳の9件」の COMMENT を10件に。backend/tests/test_viewer_message_templates.py:22〜:25 の KEYS。frontend/src/pages/super-admin/ViewerTemplatesPage.test.tsx の KEYS（:15〜:18）と PLACEHOLDERS（:19〜:29）。backend/tests/viewer_template_fixtures.py の DEFAULT_BODIES。i18n の名前と使う場面（frontend/src/locales/ja.json:2805・:2816。:2797〜:2805 が名前、:2808〜:2816 が使う場面 と en.json の同じ位置の並び）。差し込み項目の説明 placeholders（ja.json:2818〜:2828 と en.json の同じ並び）に form_url（請求先フォームのURL・自動で入ります）と form_expires（請求先フォームのリンクの期限の日付）の2行 |
| 配信先の判定の値（deliverable と理由） | §3-3 に挙げた3か所と2画面 |
| 公開の決めごと | ADR-1019:9、docs/specs/inventory-management/inventory-viewer/README.md:22、gas-viewer-fresh-fast/design.md:70 の改訂（recon §2）。プライバシーポリシー |

## 4. 代替案と選んだ理由

| 案 | 内容 | 採否 | 理由 |
|---|---|---|---|
| A | 名簿を正本にし、請求先は1対1の別表、配信先から名簿を指す（本案） | 採用（案） | 1つの情報が1か所。B2B に触れない |
| B | B2B の取引先（companies）につなぐ（前の決定） | 不採用 | PO「顧客管理ページはB2Bトレカの管理ページ」。tenant_004 の中にあり、名簿（public）と置き場所が違う |
| C | 名簿に請求先の列を直接足す | 不採用（案） | お試しの人に空の列が並ぶ。請求先だけを隠す設定がしにくい |
| D | 名簿にシートの番号を持たせる | 不採用 | シートの情報が名簿と配信先の2か所になる（分散） |

## 5. リスクと対処

- 名簿の自動削除で請求書の宛先が消える → 3-4 のとおり、請求書は発行時点の写しを持ち、名簿が消えても残す。
- 停止したお客さんのシートに書き続ける → Q1 で決定済み（停止したら自動で止め、停止を外したら自動で再開する）。§3-3 の判定1か所で守り、§7 の試験で確かめる。
- 個人情報が増える → ポリシーの書き足し、ai_ro での隠し設定、PR に個人名を載せない。
- 既存の決定との食い違い（ADR-1019:9・README:22・gas-viewer-fresh-fast/design.md:70）→ 同じ PR で改訂する。

## 6. PO に決めてもらうこと（全部決まるまで先へ進まない）

- Q1.【決定 2026-11-04 PO】停止したら自動で止める。停止を外したら自動で再開する（中身は §3-3）。
- Q1b.【決定 2026-11-04 PO】本契約の人にだけ配信する。お試しの人は、登録してあっても配信しない（中身は §3-3）。
- Q2.【決定 2026-11-04 PO「1」】1人1つまで（中身は §3-3）。
- Q3a.【決定 2026-11-04 PO「2」】お客さんは国内だけ。
- Q3b.【決定 2026-11-04 PO「登録済み」】HIGH LIFE JPN はインボイス制度の登録済み。
- Q3c.【決定 2026-11-04 PO「1」】フォームの項目は §3-2 の7項目。
- Q4.【決定 2026-11-04 PO「2」】フォーム用の専用リンクをお客さんに送る（中身は §3-6）。
- Q4c.【決定 2026-11-04 PO「1」】閲覧者の鍵の表（viewer_login_tokens）で作る。考え方と画面の部品は B2B と同じにする（§3-6 の甲）。
- Q4b.【決定 2026-11-04 PO「2」】ボタンを押したときに、メールと Discord の部屋の両方へ送る。期限は7日（中身は §3-6）。
- Q5.【決定 2026-11-04 PO「1」】便1 シートとお客さんをつなぐ → 便2 請求先フォーム → 別テーマ ツール用請求書。1便ずつ作り、本番で確かめてから次へ進む。

## 7. 受入条件（Q1〜Q5 決定済み。便1・便2 の行を実装カードで便ごとに分ける）

| 基準 | 検証方法 |
|---|---|
| 閲覧者管理ページで本契約の人を開くと、その人のシートの名前・最後の配信時刻・結果が出る | 画面テスト＋PO 目視 |
| 閲覧者管理ページでシートを登録すると、配信先の画面にも同じ1件が出る（表は1つ） | API テスト（同じ行を読む）＋PO 目視 |
| 特定の人用でないシート2件は、今までどおり配信される（3件とも ok のまま） | 本番の配信結果の読み取り（ai_ro） |
| 本契約の人を停止すると、次の配信でその人のシートだけ書き込まれず、他の2件は ok。停止を外すと次の配信で書き込みが戻る | PG テスト（停止・解除の前後で配信の結果を比べる）＋PO 目視 |
| 手で止めた（is_active=false）シートは、停止を外しても止まったまま | PG テスト |
| お試し（trial・期限切れを含む）・pending・verified の人のシートは、登録してあっても書き込まれない。その人を本契約にすると、次の配信で書き込まれる | PG テスト（状態を変える前後で配信の結果を比べる） |
| 同じ人に2つ目のシートを登録すると止まり（API 409）、DB にも入らない。特定の人用でないシートは何件でも登録できる | PG テスト（一意の索引）＋API テスト |
| 名簿の行が自動削除されると、その人の配信先の行も消える | PG テスト（maintenance の削除を流す） |
| 配信先を削除すると、そのシートのつなぎが外れ（viewer_account_id が NULL）、同じ人に新しいシートを登録できる。手で止めただけのシートが残っている人には2枚目を登録できない（409） | API テスト＋PG テスト |
| 管理画面の文面テンプレートのページで、billing_form_request の差し込み項目 form_url・form_expires に日本語と英語の説明が出る | 画面テスト（ViewerTemplatesPage.test.tsx） |
| 請求先の項目は viewer_billing_profiles の1か所だけにある | DB の列の検査（information_schema）＋レビュー |
| 名簿の行が消えても、発行済みの請求書の行は残る | PG テスト（別テーマの便で） |
| 「請求先フォームを送る」ボタンは本契約の人の行にだけ出る。本契約でない人に API で送ろうとすると 409 で、鍵は作られない | 画面テスト＋API テスト＋PG テスト（鍵の件数 0） |
| ボタンを押すと、鍵が1本だけ残り（前の鍵は使えなくなる）、期限は押した時刻から7日 | PG テスト（2回押して件数1・前のリンクで開くと無効） |
| ボタンを押すと、部屋がある人は部屋に1通（結果 sent）、部屋が無い人は no_room と画面に出る。メールは名簿のメールあてに送る手配がされる | API テスト（送信部を差し替えて回数と宛先を数える）＋PO 目視 |
| 部屋とメールの文は、文面テンプレートの台帳の billing_form_request 1件から作られ、閲覧者管理ページで直すと次の送信から変わる | API テスト＋PO 目視 |
| フォームを送信して保存できたときだけ鍵が使い切られる。保存に失敗したら同じリンクで送り直せる。期限切れ・使用済み・本契約でなくなった人のリンクは無効の画面になる | PG テスト＋API テスト |
| 配信しないシートは、配信先の画面・閲覧者管理ページ・解析ダッシュボードの配信の数・配信前の点検の4か所で同じ理由（手で止めた／本契約でない／停止中）になる | API テスト（同じ行を4つの入口から読んで値を比べる） |
| つなぎを外す（null を送る）と viewer_account_id が NULL に戻る。名簿に無い番号は 422 | API テスト |
| 請求先の表の決まり: 会社なのに担当者が空・郵便番号が7桁でない・電話が10〜11桁でない・宛名が空の行は DB が入れない | PG テスト（CHECK ごとに1件ずつ） |
| テンプレートが無い状態でボタンを押すと 503 で、鍵は0件・メールも部屋も送られない | API テスト＋PG テスト |
| フォームの2本の API は、出どころが違うと止まり、回数を超えると 429 | API テスト |
| 開くだけでは鍵が残り、今の請求先が返る。送信が成功すると鍵が0件になる | PG テスト＋API テスト |
| 請求先は本番の AI 読み取りから見えない（deny_tables に入り、列の分類が個人情報） | PG テスト（test_ops_case_db・test_ai_cloud_views） |
| プライバシーポリシーに請求先の項目と使い道が書かれている | レビュー＋PO 目視 |
| 閲覧ページの JS の合計が300KB以内 | 既存の CI（check-viewer-bundle.js）＋PR に数を書く |
| 画面に直書きの文字・色が無い | 既存の CI（i18n・デザイントークンの検査） |

## 8. 外部・過去事例の参照と我々への応用

- 過去事例（社内）: B2B 請求書の bill_to_snapshot（migrations/20260604_160000_add_invoice_snapshot_columns.sql:31・:46）。発行時点の宛先を写して残す方式を、ツール用請求書にも使う。
- 外部の決まり: 国税庁 No.6625（令和8年4月1日現在法令等）の保存期間7年（recon §7）。名簿の90日削除と請求書の保存を分ける理由にした。
- 他社の導入事例: 該当なし。理由: 今回は表の置き方の決めごとで、社内の既存の方式（上の2つ）で根拠が足りるため。

## 9. 維持の仕組み

- 守り手: .github/workflows/process-artifacts-gate.yml（2026-11-04 に実在を確認）
- 対象: 1つの情報を1か所に置く決めごと（§3-1）と、請求書を名簿の削除から切り離す決めごと（§3-4）。
- 補足: 3-1 の表は、実装の PR で migration と照らしてレビューで確かめる。
