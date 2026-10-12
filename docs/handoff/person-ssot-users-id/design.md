# design: 「人」の正本を public.users.id 一本にする（段階3）

| 項目 | 内容 |
|---|---|
| 状態 | 設計審査済み（Opus 自己審査・APPROVE 条件付き §9）。PO 承認済み 2026-10-13（問い「段階3を、先ほどお見せした順番と操作一覧で進めてよいですか？（y/n）y の場合：名簿のつなぎ直しから始めて、スタッフ追加の画面の変更まで、本番反映を1つずつ順に進めます。重複している古い欄の削除だけは、その前にあらためて GO をいただきます。」に PO「y」）。P4 は PO 本人の GO が別途必要 |
| 起案 | Claude Opus（設計担当） 2026-10-12 |
| 依頼 | PO 2026-10-12「SSOTの定義に基づき正本は1箇所で管理したい」 |
| ADR | docs/adr/ADR-1008-person-ssot-users-id.md（本 PR で新設） |
| recon | docs/handoff/person-ssot-users-id/recon.md |
| 前段 | 段階1 #4162（会社作成・利用者登録を super admin 専用）、段階2 #4163（ロール判定を user_roles に一本化）。根拠 docs/handoff/admin-api-super-admin-only/design.md、docs/handoff/role-ssot-user-roles/design.md |

## 1. KGI（○×で判定できる形）

| # | 基準 | 検証方法 |
|---|---|---|
| K1 | 全テナントの名簿（tenant.staff）で user_id が空の行が 0 | 本番読み取り `SELECT count(*) FROM tenant_NNN.staff WHERE user_id IS NULL` を5テナント合計 |
| K2 | 「人」を指す列がすべて public.users(id) を参照する（staff.id を参照する外部キーは、名簿の付属表 staff_emails・staff_ui_preferences の2種類だけ） | 本番読み取り `pg_constraint` で confrelid が staff の FK を列挙 |
| K3 | t4 の会社42件の担当者が、しんごさん（users 3）として集計される | 本番読み取り: tenant_004.companies の sales_rep_id 値別件数が 3→42、1→0 |
| K4 | 名簿の重複列（staff.role_id・staff.primary_email・staff.firebase_uid・users.role）が無い | information_schema.columns に 0 件（段階 P4。PO 本人の GO 後） |
| K5 | 画面の担当者・作成者の表示が、変更前と同じ人名で出る（t4 の会社担当は「谷澤 伸吾」） | 本番 API の応答か画面で目視 |

## 2. 現状（事実の要約。全文と行番号は recon.md）

- 人の番号が2種類ある。public.users.id（ログイン）と tenant.staff.id（名簿）。名簿 7 行のうち users に紐付くのは 1 行（t6 staff 1→users 10）。
- staff.id を参照する外部キーが 43 本（9 列×テナント）。users.id を参照する外部キーが 32 本。
- companies.sales_rep_id は staff.id を参照する外部キーだが、analytics.py は users.id として結合している。t4 の 42 件は staff 1（しんごさん）の意味なのに、別テナントの users 1 の名前で集計される。
- 名簿の行を追加する POST /staff は users・user_roles を作らない。users を作るのは super admin 専用の POST /auth/register だけ。
- 名簿の行を引く処理の多くが「users.email と staff.primary_email の一致」で、primary_email に一意制約が無い。

## 3. あるべき姿（ADR-1008）

- 人の正本は public.users（1人1行）。is_active=false は「ログイン不可」を表す（dependencies.py のログイン判定が is_active=TRUE を条件にしている）。
- tenant.staff は、その会社の中の詳細（氏名・かな・英字・Discord・電話・在籍状態）。staff.user_id は NOT NULL かつ UNIQUE で users(id) を参照する。
- 人を指す列（担当者・作成者・接続した人・送信者・既読者・Bot の持ち主・歩合の対象・カレンダーの持ち主）は users.id を持つ。
- 名簿の付属表（staff_emails・staff_ui_preferences）は staff.id のままにする。名簿の行そのものの付属情報で、人を指す列ではないため。
- ロールは user_roles だけ。メールは users.email だけ。Firebase の識別は users の email で引く（今のログイン判定と同じ）。

## 4. 進め方（1つずつ: 反映 → 本番測定 → 次）

| 段 | 種類 | 内容 | GO |
|---|---|---|---|
| D1 | 本番データ | 名簿の紐付け（§5） | PO 合意（本設計の承認）→ Opus 実行 |
| P1 | PR（migration＋コード） | companies.sales_rep_id の参照先を users(id) に変更。書き込み時に同じテナントの users か確かめる | 委任 GO（ADR-1003） |
| D2 | 本番データ | t4 companies.sales_rep_id 1→3（42件） | PO 合意（本設計の承認）→ Opus 実行 |
| P2 | PR（migration＋コード＋画面） | 残りの人を指す列（bots.owner_staff_id、order_commissions.staff_id、calendar_owner_settings.staff_id、tenant_meta_config.connected_by_staff_id、meta_messages.sent_by_staff_id・seen_by_staff_id）を users(id) 参照に移す。列名は *_user_id に改める（RENAME。列の削除はしない）。書き込み側は current_user.id を直接使い、メールから staff を引く処理を撤去 | 委任 GO |
| D3 | 本番データ | P2 で移した列の値を staff.id→users.id に付け替え（t1 meta_messages 2件、t4 meta_messages 25件・tenant_meta_config 11件、t6 tenant_meta_config 1件） | PO 合意（本設計の承認）→ Opus 実行 |
| P3 | PR（migration＋コード） | staff.user_id を NOT NULL に。名簿の行の引き方を user_id に統一。スタッフ追加（POST /staff）で users・staff・user_roles を1トランザクションで作る（ログインする人は is_active=true、しない人は false） | 委任 GO |
| P4 | PR（migration） | 重複列の削除（staff.role_id・primary_email・firebase_uid、users.role） | **PO 本人の GO**（ADR-1003 の例外） |

P2・P3 の実装カードは、P1 の本番測定の後に、その時点の origin/main で書き直す（行番号がずれるため）。

## 5. D1 の操作一覧（本番データ・1トランザクション・件数ガード付き）

SQL: docs/handoff/person-ssot-users-id/d1_link_roster.sql。戻し: d1_rollback.sql。

| # | 操作 | 想定件数 |
|---|---|---|
| 1 | t1 staff 1（谷澤 伸吾）→ users 1 に紐付け（メール一致） | 1 |
| 2 | t4 staff 1（谷澤 伸吾）→ users 3 に紐付け（メール一致） | 1 |
| 3 | t6 staff 8・9・10（田中 誠一・鈴木 花子・山本 大輔。ログインしない人）に users 行を作る（is_active=false、email は名簿のもの）。紐付け | 3＋3 |
| 4 | その3人のロール（名簿の role_id: 4・4・3）を user_roles に写す | 3 |
| 5 | t4 tenant_meta_config id 2・3（無効化済みの古い接続記録）の「接続した人」を空にする | 2 |
| 6 | t4 staff 7（レビュー アカウント）を名簿から削除（付属表の行は 0） | 1 |
| 確認 | 全テナントで user_id の無い名簿行 0 | 0 |

手順: 事前読み取り → staff 7 の行を VPS 上のファイルに控える → DRY-RUN（COMMIT を ROLLBACK に置換）→ NOTICE 'D1 ok' を確認 → 本実行 → 事後読み取り。

## 6. P1 の範囲（実装カードは別ファイル card-p1.md）

- migration（新規 1 本、構造のみ）: 全テナントの companies.sales_rep_id の外部キーを staff(id) から public.users(id) に張り替える（ON DELETE SET NULL）。外部キーの名前がテナントで2種類ある（tenant.py:650-661 の fk_companies_sales_rep と、migrations/028_create_companies.sql:80 の自動名 companies_sales_rep_id_fkey）ので、名前に頼らず pg_get_constraintdef で staff を参照する sales_rep_id の外部キーを探して外す。型は migrations/20260602_010000_repoint_downstream_fk_to_public_products.sql:18-60 に倣う（recon.md §3-d）。冪等（2回流しても同じ結果）にする。
- backend/app/services/tenant.py: 新規テナントの companies 定義の外部キーを同じく users(id) に。
- backend/app/routers/companies.py: POST・PATCH で sales_rep_id が指定されたら、同じテナントの users に存在するか確かめ、無ければ 422。
- 触らない: analytics.py（すでに users.id として読んでいる）、フロント（sales_rep_id を送る画面は 0 件）。
- 移行の間の状態: P1 反映後〜D2 まで、t4 の 42 件は users 1 を指したまま（今と同じ誤り）。D2 で直る。新しく悪化する点は無い。

## 7. 代替案と選んだ理由

| 案 | 内容 | 採否 |
|---|---|---|
| A（採用） | users を人の正本、staff を会社内の詳細にする | ログインの正本がすでに users。外部キー 32 本が users を指している。分析・目標・カレンダーは users.id で動いている |
| B | staff を人の正本にして、users をログイン専用にする | 却下。users を指す 32 本と、ログイン・権限（user_roles）の全経路を作り直すことになる |
| C | staff と users を1つの表に統合する | 却下。users は public（全テナント共通）、staff はテナントごと。RLS とテナント分離の作りを壊す |

## 8. リスクと対処

| リスク | 対処 |
|---|---|
| D1 で作る3人の users 行がログインできてしまう | is_active=false。ログイン判定は dependencies.py で is_active=TRUE を条件にしている（recon.md 参照） |
| D1 の削除（staff 7）が戻せない | 削除前に行を VPS 上のファイルに控える。戻し SQL はそのファイルから戻す |
| P1〜D2 の間、担当者の表示が今のまま誤っている | 現状から悪化しない。D2 を P1 の本番確認の直後に行う |
| P2 で画面の値（Bot の持ち主・歩合の対象）の番号の種類が変わる | P2 で画面と API を同じ PR で直し、E2E のモックも更新する。D3 を P2 デプロイ直後に行う |
| 新規テナントのひな形（tenant.py）と migration のずれ | 各 PR で tenant.py も同時に直す（ADR-1007 決定3） |

## 9. 設計審査（Opus 自己審査。独立した第二者レビューではない）

判定: APPROVE（D1・P1・D2）。P2〜P4 は方向のみ承認し、実装カードは P1 の本番測定後に作って再審査する。

- 既存 ADR との整合: ADR-1007（migration は構造だけ・値はデータ変更で）に合う。ADR-155 の値書き込み検査の対象外になるよう、値の変更は D1〜D3 に分けた。ADR-023（スタッフの3層同期・提案）は P3 で users・staff・user_roles の同時作成として取り込む。ADR-091:242 の「public.staff」記述と実装の食い違い（tenant_discord_config）は P2 で扱う。
- 根拠: 本番の値と件数は読み取りで確認済み（recon.md §本番）。推測で埋めた値は無い。
- 未解決: P2 の画面（BotsPage・CommissionPanel・ScheduleSettingsPage・SchedulePageImpl）の詳細は、P2 カード作成時に再調査する。

## 10. 維持の仕組み

- 守り手: backend/tests/test_companies_sales_rep_users.py（P1）と、各段の外部キー制約（DB が別の番号を拒む）。

- P3 の NOT NULL 制約で、紐付かない名簿行は DB が拒む。
- P2 以降、人を指す新しい列は users(id) を参照することを ADR-1008 に定める。

## 外部・過去事例の参照と我々への応用

- 外部事例: 該当なし。理由: 自社スキーマ内の参照先の統一で、数値の根拠を外部事例に頼る判断が無い。1つの実体を1つの表で持つ正規化の原則にのみ依拠する。
- 過去事例: #4163（ロール判定を user_roles に一本化）で、二重の正本が「片方だけ更新されて判定が食い違う」問題を起こしていた。本件も同じ構造（人の番号が2種類）で、t4 の42件で誤結合が実際に起きている。応用: 正本を1つに決め、参照する列を外部キーで縛り、DB が誤りを拒む形にする。
