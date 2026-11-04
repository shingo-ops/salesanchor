# recon: 閲覧者管理ページを在庫解析ツールの顧客管理にする（お客さんごとのシート配信・請求先フォーム）

> この文書は何か（専門用語なしの1行）:
> 閲覧者の名簿・配信先のシート・請求書について、今どうなっているかを、コードと本番の読み取りで確かめた記録。

- 親（設計仕様書）: [docs/specs/inventory-management/inventory-viewer/README.md](../../specs/inventory-management/inventory-viewer/README.md)
- 設計: [design.md](./design.md)
- 状態: 草案（2026-11-04 作成）。PO 未承認。
- 基準: origin/main d948cf9c7（worktree `release/viewer-customer-sheet-design` を origin/main から作成）

## 1. PO の発言（原文・2026-11-04）

- 「シートと顧客を整備したいのだが出来る？…閲覧者管理ページで管理できるようにしてほしい。本契約をした人には個別にスプレッドシートに配信をするようにしたい」
- シートの作り方: 「3、相手にシートを共有してもらってそのブックに書き込みをしている」
- 「顧客管理ページはB2Bトレカの管理ページなので閲覧者ページを在庫解析ツールの顧客管理として使いたい、DBはどうするべき？」
- 名簿に項目を足すか: 「2」（項目を足す）
- 「本契約時に請求書に使うための情報を取りたいのでフォームで書いてもらう方式にする」
- 「今の請求書はトレカの請求書の作成に使っているのでツール用の請求書作成機能を別途作りたいと考えている、DBについてはどう要件定義しておくべき？先に要件定義と設計だけ決めてから進める」
- 共通の条件: 推測禁止・事実確認・配線と DB の SSOT 遵守（データの分散禁止）・デザイントークンとデザインシステム遵守（金型登録のないハードコード禁止）・分からないことは聞く。

## 2. 既存 ADR・仕様書の検索

- 実行: `git grep -l -i -E "viewer_accounts" origin/main -- docs/adr` → ADR-1019 のみ。`git grep -l -i "tcg_distribution_targets" origin/main -- docs/adr` → 該当なし。
- ADR-1019 `docs/adr/ADR-1019-inventory-viewer-separate-accounts.md:9` は「ADR-1008（取引先・顧客の正本。申込の email は取引先に写さず、本契約の便で参照列でつなぐ）」と書く。
- 【食い違い・観測事実】ADR-1008 の題は `docs/adr/ADR-1008-person-ssot-users-id.md:1`「「人」の正本は public.users.id 一本にする」で、取引先の正本の ADR ではない。ADR-1019:9 の ADR-1008 の説明は ADR-1008 の中身と合っていない。
- 既存の決定: `docs/handoff/gas-viewer-fresh-fast/design.md:70`「本契約のときに取引先とつなぐ方法は、本契約フォームの便で設計する。そのときは viewer_accounts から取引先を指す列（参照）で結び…」。`docs/specs/inventory-management/inventory-viewer/README.md:22` も同じ。
- → 今回の PO 発言「閲覧者ページを在庫解析ツールの顧客管理として使いたい」は、この既存の決定（取引先につなぐ）を置き換える。ADR-1019 と README の境界の改訂が要る。

## 3. 名簿（閲覧者）の表

- `migrations/20261016_150000_add_viewer_accounts.sql:6` public.viewer_accounts。列は email・line_name・inventory_issue・status・パスワード関係・discord_user_id・discord_channel_id・trial_expires_at・created_at・updated_at。
- `migrations/20261016_150000_add_viewer_accounts.sql:21` 状態は pending／verified／trial／active／suspended の5つ。本契約＝active（`docs/handoff/gas-viewer-fresh-fast/recon.md:238`）。
- 関連の表は名簿の行が消えると一緒に消える: `migrations/20261016_150000_add_viewer_accounts.sql:41`・`:60`・`:81`（ON DELETE CASCADE）。
- 名簿の行は自動で消える（本番で動く仕組み）:
  - `backend/app/tasks/maintenance.py:33` VIEWER_RETENTION_DAYS = 90
  - `backend/app/tasks/maintenance.py:214` 期限切れ trial を90日後に DELETE
  - `backend/app/tasks/maintenance.py:220` 停止 suspended を停止の90日後に DELETE
  - `backend/app/celery_app.py:110` 毎日の定期実行に登録済み
- お客さんに見せているポリシー: `lp/src/pages/privacy.astro:76` 預かる情報は「Name, Email Address」。`lp/src/pages/privacy.astro:213` 閲覧者の行は停止の90日後に消すと書いてある。

## 4. 配信先（シート）の表

- 作成: `migrations/20260903_200000_tcg_distribution_targets_t004.sql:20`（当時は tenant_004）。のちに public へ移った（`backend/app/services/tcg_distribution_svc.py` の TCG_SCHEMA = "public"、本番 ai_ro に public__tcg_distribution_targets がある）。
- 列: id（UUID）・name・spreadsheet_id（`:23`）・sheet_name・is_active（`:25`）・sa_key_secret_name・last_distributed_at・last_distributed_count・last_result・created_at・updated_at、ほかに review_sheet_name（`migrations/20261012_210000_add_tcg_distribution_targets_review_sheet_name.sql:2`）。
- 名簿の人を指す列は無い（上の列が全部）。
- 安全の決まり: `backend/app/services/tcg_distribution_svc.py:15`「#2 シート自動作成禁止」。書く前に所有者を記録: `backend/app/services/tcg_distribution_svc.py:131`。
- 読む場所: `backend/app/services/tcg_distribution_svc.py:706`・`:718`（配信）、`backend/app/services/tcg_analysis_dashboard_svc.py:669`（ダッシュボード）。
- 画面: `frontend/src/App.tsx:325` /super-admin/tcg-distribution（配信先の管理）、`frontend/src/App.tsx:366` /super-admin/viewers（閲覧者管理）。2つは別の画面。

## 5. 本番の読み取り（reader 鍵・ai_ro。2026-11-04 13:42〜14:03 JST）

生出力: /tmp/CC報告ファイル/haishin-prod.txt・haishin-prod2.txt・haishin-prod3.txt（個人名を含むためリポジトリに載せない）

- 配信先は3件。3件とも有効で、2026-11-04 13:32 JST に結果 ok。要確認タブの名前があるのは1件（配信テスト）。
- 3件のうち2件は特定の人用ではない名前（無料トライアルシート・配信テスト）。1件はお客さんの個人名。
- 名簿の状態: active 3人・trial 20人。
- active 3人の LINE 名と同じ名前の配信先は0件（どのシートが誰のものか、DB からは分からない）。
- tenant_001 の tcg_distribution_targets は0行（古い置き場所。使われていない）。
- HIGH LIFE JPN は tenant id 4。tenant_004 の取引先（companies）は51件（すべて status=active）。

## 6. 既存の請求書（B2B トレカ用）

- 請求書の表は会社ごとの置き場所（tenant_NNN.invoices）にある: `migrations/20260604_160000_add_invoice_snapshot_columns.sql:31` bill_to_snapshot（JSONB）。
- `migrations/20260604_160000_add_invoice_snapshot_columns.sql:46` 「発行時点の請求先住所スナップショット（company_addresses から複写）」。発行した時点の宛先を請求書の行に写して残す方式。
- 宛先の項目: `backend/app/services/invoice_renderer.py:115`〜`:122` company_name・contact_name・address・country・tax_id・phone・email の7つ。
- PO 方針: この請求書はトレカ用のまま。ツール用は別に作る（2026-11-04）。

## 7. 外部の決まり（請求書の保存）

- 国税庁 タックスアンサー No.6625（「令和8年4月1日現在法令等」）: 請求書等は「課税期間の末日の翌日から2か月を経過した日から7年間…保存しなければなりません」。「6年目および7年目は、帳簿または請求書等のいずれか一方を保存すればよい」。https://www.nta.go.jp/taxes/shiraberu/taxanswer/shohi/6625.htm
- 同ページの適格請求書の記載事項は、作成者の名称と登録番号・取引年月日・取引内容・税率ごとの合計と税率・税率ごとの消費税額・交付を受ける者の氏名または名称。
- 【未確認】交付した請求書の写しの保存期間について、No.6625 のページには個別の記載が無い。Q&A（https://www.nta.go.jp/taxes/shiraberu/zeimokubetsu/shohi/keigenzeiritsu/pdf/qa/01-10.pdf）の本文はまだ読んでいない。
- 【確認済み 2026-11-04 18:50 JST 取得・ファイルの更新日 2026-03-31】上の Q&A（PDF の 122 ページ目）問79【令和5年10月改訂】:「この適格請求書の写しや電磁的記録については、交付した日又は提供した日の属する課税期間の末日の翌日から２月を経過した日から７年間…保存しなければなりません（消令70の13①）」。問78:「交付した適格請求書の写し」は「その適格請求書の記載事項が確認できる程度の記載がされているものもこれに含まれます」。文字にした全文: /tmp/CC報告ファイル/nta-qa-01-10.txt
- 【未確認】HIGH LIFE JPN が適格請求書発行事業者か。お客さんが国内か海外か。どちらも PO に聞く。

## 8. 分かったこと（設計に効く事実）

1. 名簿の行は停止の90日後に自動で消える。請求書を名簿の行に頼ると、請求書の宛先も一緒に消える。
2. 配信先とお客さんをつなぐ情報は DB のどこにも無い。
3. 名簿と配信先は同じ public にある。片方からもう片方を指す列を作れる。
4. 既存の決まり（本契約で取引先につなぐ）は、今回の PO 方針で書き換えが要る。

## 9. 既存の「お客さんごとのフォームを発行する仕組み」（B2B 登録フォーム。2026-11-04 PO「顧客別のフォームを発行する機能はすでに使ってるので共用で使い回せる？」を受けて確認）

基準: origin/main（2026-11-04 fetch 後）。生出力: /tmp/CC報告ファイル/adr127.md・regtok-mig.txt・regtok-router.py・regtok-svc.py・regtok-prod.txt・register-pages.txt

- 決まり: ADR-097（登録フォーム・署名トークン）と ADR-127（`docs/adr/ADR-127-registration-post-forms.md`、Status Proposed）。
- 鍵の表 public.registration_tokens（`migrations/20260604_080000_create_registration_tokens.sql:6`〜`:16`）:
  - `:8` tenant_id INTEGER NOT NULL（会社の置き場所）、`:9` lead_id INTEGER NOT NULL（B2B のリード）。名簿（viewer_accounts）を指す列は無い。
  - `:10` token_hash（HMAC-SHA256）、`:12` expires_at、`:13` used_at（1回だけ）。
  - 種類は register／add_address／change_billing の3つ（`migrations/20260612_090000_extend_registration_tokens_change_billing.sql:7`〜`:9`）。
  - 書き込みは tenant_id が今の会社と一致するときだけ（`migrations/20261016_160000_add_paypal_regtoken_write_rls.sql:35`〜`:46`。`:29` で FORCE ROW LEVEL SECURITY）。tenant_id を持たない行は書けない。
- 鍵の作り方と確かめ方: `backend/app/services/registration_token.py:48`〜`:56`（作る）、`:99`〜`:150`（署名・期限・使用済みの3点を確かめる）、`:153`〜`:163`（使用済みにする）。期限は既定7日（`:36`）。関数は tenant_id・lead_id を必ず受け取る（`:59`〜`:67`）。
- 書き込む先: 送信されると、会社の置き場所の companies・company_addresses・contacts に書く（`backend/app/routers/registration_tokens.py:240`〜`:346`・`:405`・`:502`〜`:557`）。会社はリードから決める（`:241`・`:393`・`:488`）。
- 画面: `frontend/src/pages/register/` に RegisterPage・RegisterAddressPage・RegisterChangeBillingPage・CountryCombobox。RegisterPage は金型の Button・TextFieldControl・Radio・LoadingBlock を使う（`frontend/src/pages/register/RegisterPage.tsx:17`〜`:20`）。
- 本番の使用状況（reader 鍵・2026-11-04 16:32 JST）: register 4件（うち使用済み1件）・add_address 1件（使用済み0件）。最後に発行されたのは 2026-06-19。change_billing は0件。
- 閲覧者側には別の使い捨ての鍵の表 public.viewer_login_tokens が既にある（§3 の表のほかに。`migrations/20261016_150000_add_viewer_accounts.sql:39`〜`:49`。名簿を指す列 `:41` を持つ）。

### 分かったこと

1. B2B の登録フォームの鍵は「会社の置き場所」と「リード」に必ずつながる作り（NOT NULL）。閲覧者は会社の置き場所にもリードにもいない（public の名簿）。そのままでは閲覧者のための鍵を作れない。
2. 共用にするには、B2B の鍵の表の決まり（NOT NULL・書き込みの制限）を変える必要がある。B2B の登録フォームにも影響が出る。
3. 使い回せるのは、鍵の考え方（署名・期限・1回だけ）と、画面の金型の部品。

### 行番号の訂正（2026-11-04）

§9 の初版の行番号の一部は、3本の移行ファイルをつないだ生出力の行番号でした。そのため、ファイルの実際の行番号とずれていました。Fable の評価で指摘を受け、実物の行番号に直しました（grep で確認）。
