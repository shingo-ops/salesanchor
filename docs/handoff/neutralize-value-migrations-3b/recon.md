# recon: 値を書く migration 7 本の無効化（段3 の PR-3b、2026-10-07）

基準: origin/main に、#4012（所有者・管理者の権限を check 時に計算する PR）と、その下の #3986（roles.system_key の列）を積んだ状態。値（件数・権限キー名）だけを記載する。元の調査は「社外秘のローカル作業メモ（リポジトリ外）」にある。

## 0. 既存 ADR の検索（STANDARD-WORKFLOW）
- 検索語: neutralize / ADR-155 / ADR-1007 / permissions。関係する ADR: ADR-155（マイグレーションは構造変更のみ。docs/adr/ADR-155-product-master-ssot-csv-app.md:26）。同じ形の前例は PR #3544（13 本の無効化、commit fd7423f99）。

## 1. 事実：対象と、外す範囲（カードの 3b の行どおり）
| migration | 登録 | 外す範囲 | 残すもの |
|---|---|---|---|
| migrations/080_phase_b_migration.sql | scripts/run_all_migrations.sh:175 | :36-40（既存 'A' を 'B' にする UPDATE） | :33-34 の DEFAULT 'B'（構造。バイト単位で同一） |
| migrations/023_fix_system_admin_is_system_flag.sql | :89 | :24-54（全テナントの is_system の UPDATE） | ヘッダ |
| migrations/075_create_goals.sql | :170 | :36-39（権限マスタへの goals.* の INSERT）、:121-146（役割ごとの goals.* の付与） | goals 表・索引・RLS・ポリシー・トリガー（:42-120）。:148 の NOTICE の文言から「権限割当」を外した |
| migrations/025_resync_owner_admin_all_permissions.sql | :91 | :24-79（オーナー/管理者への全権限の再付与） | ヘッダ |
| migrations/018_extend_permissions_with_menu_grain.sql | :88 | :41-68（menu.* 19 キーの INSERT） | :24-37（列の追加・索引・コメント） |
| migrations/024_add_staff_bots_permissions.sql | :90 | :17-26（staff.* / bots.* 8 キーの INSERT） | ヘッダ |
| migrations/20260604_180000_analytics_agent_a_tables.sql | :312 | :203-212（analytics.customer_priority.* 2 キーの INSERT と説明コメント） | :1-202（表・RLS の構造） |
- 無効化の形: 全体が値だけのもの（023・025・024）は #3544 の前例どおり（ヘッダ＋ NEUTRALIZED の印＋ NOTICE だけの DO ブロック）。構造と値が混ざったもの（080・075・018・20260604_180000）は、構造と存在確認を一字も変えず、値を書く文だけを NEUTRALIZED のコメントに置き換えた。印の文言は「NEUTRALIZED (ADR-1007 / ADR-155, 2026-10-07)」。
- 各ファイルの行数は、カードの範囲と一致している（080:40 行、023:54、075:165、025:79、018:68、024:26、20260604_180000:212）。

## 2. 事実：なぜ #4012 のデプロイ後か（マージの順）
- 080: 新テナントの phase は、#4012 より前のコードでは 'A'（backend/app/services/tenant.py の tenant_settings の INSERT）。#4012 は 'B' を直接書く。
- 023: #4012 より前の作成コードはシステム管理者を is_system=False で作る。#4012 は True にする。
- 075: #4012 より前の役割一覧に goals.* が無い。#4012 は goals.view / goals.edit を役割一覧に足す。
- 025: 後から増えた権限キーが所有者・管理者に届く経路が、再実行しかなかった。#4012 は backend/app/auth/dependencies.py の load_user_permissions で、system_key を持つロールの権限を権限マスタから計算する。その計算は、既存テナントに system_key の値が入って初めて働く（値の設定は docs/handoff/roles-system-key-data/ にある一度きりの手順。未実行）。
- したがって、この PR をマージするのは、#4012 がデプロイされ、かつ system_key の値の設定が済んだ後だけ。018・024・20260604_180000 は同じ順に並べる指定。

## 3. 事実：権限キーの INSERT を外しても、今ある経路は減らない
- .github/workflows/migration-guard.yml:416 の PROTECTED_TABLES に permissions が入り、Check 7 が 2026-09-18 から、新しい migration による public.permissions への書き込みを止めている（追加されたファイルだけが対象）。本番には 123 キーが既にある（5 テナントのオーナーの権限数）。新しいキーは、そもそも migration では足せない。
- 「今後、新しい権限キーをどう足すか」は別 ADR（権限の正本）に先送り済みで、この PR では決めない。

## 4. 事実：他の参照
- .github/workflows/schema-check.yml:171,173 が 018 と 024 を流す（|| true）。無効化後も構造（018 の列・索引）は残り、024 は NOTICE だけになる。scripts/migrate_phase1_redesign.py:52 が 018 のファイル名を一覧に持つ（過去の移行スクリプト。deploy では呼ばれない【未確認: 呼び出し元は調べていない】）。
- 試験: この 7 本のファイルを読む試験は無い（git grep: schema-check.yml と上記スクリプトのみ）。#4012 の PG 試験は、goals の権限キーを自分で入れるので、075 の INSERT が無くても動く。

## 5. 未確認・実施していないこと
- 手元で SQL を流しての確認はしていない（書き込みを防ぐフックが手元の DB 実行も止める）。CI の Migration SQL Test と、マイグレーション全件ドライランに任せる。
- 本番で値の書き込みが止まったこと（デプロイ後に updated_at が動かないこと）は、デプロイ後に読み取りで確かめる。
