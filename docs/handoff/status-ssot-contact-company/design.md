# 会社と連絡先の「状態」を1か所へ — 設計

> この文書は何か（専門用語なしの1行）:
> 会社と連絡先の「有効・無効・アーカイブ・重複確認待ち」を DB の1つの表にまとめ、画面の選択肢・札・まとめる画面の文・分析がすべてその表を読むようにする手順。

- 状態: **設計案作成済み（Opus）／設計審査 4回目 APPROVE・5〜7回目 REVISE の指摘を反映済み・8回目 APPROVE（§14）／2026-11-12 PO 判断（§9 未決4）を反映して §1・§2・§3・§4・§6-2-1・§6-3-4・K4・K14・K15 を変えた（5〜7回目の審査で確認・§14）／PO 承認 済（2026-11-11「SSOTしてほしい」・2026-11-12 冒頭の依頼「PRマージ、デプロイまで完走させてくれ」と §9 の「1」2件）／便1 実装済み（ADR-1076）・便2・便3 未着手**
- recon: docs/handoff/status-ssot-contact-company/recon.md
- 基準: origin/main a88194893（2026-11-11 取得）
- PO の言葉（2026-11-11）: 「DBがバラバラに成っていていろいろなところからデータ撮ってきているならSSOTしてほしい」「分析機能に影響するから値の直書きは禁止、基本的に値はDBにSSOTさせて、後から分析の材料として使用できる状態にする必要がある」。同日「1」で、状態の1か所化とまとめる画面の文を1つの設計にする。

## 0. 既存ADR・仕様書（recon §0 の再掲と、この設計で従うもの）

| 文書 | この設計での使い方 |
|---|---|
| ADR-120 | 状態 → 見た目の入口は statusPresentation.ts のまま。色の種類（bucket・badgeVariant）はコードに残す。名前だけ DB の行から出す（審査2回目の指摘4） |
| ADR-109 | 見込み客の状態は対象外（§9 未決1）。今回は会社・連絡先だけ「名前も DB」とする新 ADR を立てる |
| ADR-027 | 画面の固定の文は t() のまま。状態の名前だけは DB の日英2列から言語で選ぶ（前例: チャネル名簿の display_name） |
| ADR-1007 決定1 | 表を作る migration に行は書かない。4行は1回だけのデータ変更で入れる |
| ADR-1008 | 会社ごとの表から public の表への外部キーの前例 |
| ADR-145 | public の表の守り（RLS の ENABLE と FORCE）の写し方 |
| ADR-1037 | 入れ替え時のロック待ち1秒 |
| docs/handoff/channel-master-shared/design.md | 作る便 → 行を入れる → 付け替え、の3段の型 |

## 1. 目的と成功条件

- 目的: 4つの状態の「記号・日本語名・英語名・並び順」を DB の1つの表だけに置く。画面とサーバーと分析は、その表を読む。同じ値を別の場所に書かない。色の種類は見た目の決まり（ADR-120）なのでコードの1か所に残す（分析の材料ではない）。
- 利用者に見える変化:
  - 状態を選ぶフォームは7か所ある（recon §3。2026-11-12 に Opus が数え直した内訳は §6-2-1）。作るときだけの2か所・直すときだけの4か所・両方で使う1か所（会社の詳細の「担当者管理」タブの小窓 `frontend/src/pages/company-detail/CompanyContactsTab.tsx:151-154`）。
  - 変更後（PO 2026-11-12「1」= §9 未決4 の答え）: 作るときは、どこでも「重複確認待ち」を出さない（有効・無効・アーカイブの3つ）。直すときは、どこでも4つ出す。今と変わる所は2つ: 会社の「新規登録」から消える／担当者管理タブの小窓で直すときに出るようになる。
  - 出すか出さないかは画面に書かない。表の列 `selectable_on_create`（§3）を読んで決める。
  - 一覧の絞り込みの選択肢はもともと無い（審査2回目の指摘3で確認）。
  - まとめる画面の文から「master」「pending_dedup_review」「active」「audit_logs」が消える。
  - 名前の見た目は今と同じ（有効／無効／アーカイブ／重複確認待ち）。

## 2. 変更前と変更後

| 項目 | 変更前 | 変更後 |
|---|---|---|
| 4つの値 | DB の CHECK 10表＋会社を作る処理2か所＋サーバー列挙2か所＋画面8か所 | DB の表 `public.customer_statuses` の4行（正本）。会社・連絡先の status 列はこの表への外部キー |
| 名前 | 辞書 11キー（ja/en） | 表の name_ja・name_en。辞書の重複キーは消す |
| 色の種類 | statusPresentation.ts に2組 | 変えない（statusPresentation.ts の bucket・badgeVariant。名前の辞書キー labelKey だけ外す） |
| 画面の選択肢 | 7か所で自前に並べる（作るとき: 会社1か所は4つ・担当者2か所は3つ。直すとき: 4か所は4つ・担当者管理タブの小窓は3つ） | 1つの読み口（hook）から並べる。作るときは `selectable_on_create` が TRUE の行だけ（3つ）、直すときは全行（4つ） |
| 分析 | 名前を引けない | 会社・連絡先の status を表と結んで名前・並び順が引ける |

## 3. 新しい表 `public.customer_statuses`（便1・migration・形だけ）

```sql
CREATE TABLE IF NOT EXISTS public.customer_statuses (
    code        VARCHAR(20) PRIMARY KEY,          -- 会社・連絡先の status に入る記号（変えない）
    name_ja     VARCHAR(50) NOT NULL,             -- 画面の日本語名
    name_en     VARCHAR(50) NOT NULL,             -- 画面の英語名
    sort_order  SMALLINT    NOT NULL UNIQUE,      -- 選択肢・集計の並び順
    is_active   BOOLEAN     NOT NULL DEFAULT TRUE,  -- FALSE＝新しく選べない（過去の行は残る）
    selectable_on_create BOOLEAN NOT NULL DEFAULT TRUE,  -- FALSE＝作る画面の選択肢に出さない（直す画面には出す）。PO 2026-11-12「1」
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

- 会社と連絡先で1つの表にする。理由: 今の4つの値と名前が両方で同じ（`backend/app/services/tenant.py:224`・`:255` の CHECK が同一、名前も同一）。片方だけに足す日が来たら、その時に別設計（§8 弊害4）。
- 会社ごとの独自の状態は持たない（tenant_id 列なし）。理由: サーバーの動きが記号に頼る（`backend/app/routers/companies.py:765`・`:978-985`）。会社が独自に足すと動きが決まらない。
- RLS: 書く＝運営だけ（`current_setting('app.is_operator', true) = 'true'`）。ENABLE と FORCE。`migrations/20261106_190000_create_public_channel_masters.sql` の守りを写す。
- 読む決まりは必ず `USING (true)`（誰でも全行）。審査2回目が PostgreSQL 16 を使い捨てで立てて実測した: 行ごとの外部キーの検査は RLS を飛ばして通るが、`VALIDATE CONSTRAINT` は FORCE の下では表の持ち主でも読む決まりで行が絞られ、読む決まりが狭いと違反で失敗した。`USING (true)` では通った。
- 消す操作は受けない（外部キーで止まる）。取り下げは is_active=FALSE。
- 行を入れる文は書かない（ADR-1007）。この便では作るだけで、どこからも読まれない。
- `scripts/migration-guard/protected-tables.txt` に customer_statuses を足すのは便1 ではなく便3（審査3回目の指摘 M1）。理由: 確認8（`scripts/check-migration-value-writes.py:70-72`・`:181-186`）は、変えた migration の追加行で守る表の名前を含み、許す語（`:39-45`）を含まない行を止める。便1 の migration は前例どおり `GRANT SELECT ... ON public.customer_statuses` を持つので、同じ PR で一覧に足すと便1 自身が止まる。全件走査（`:260` の run_repo）は確認8 を全ファイルには当てないので、便1・便2 が合流した後の便3 で足せば、以後に新しく足す migration だけが止まる（ADR-1007 決定5 を機械で守る）。注意（審査4回目 N3）: 便3 の後で便1・便2 の migration ファイルを直すと、customer_statuses を含む追加行（GRANT など）が確認8 に止められる。そのときは `scripts/migration-guard/reference-allowlist.tsv` にそのファイルを足して外す（`scripts/check-migration-value-writes.py:11`）。
- ロールバック: 表を残してプログラムが使わない。

## 4. 4行の投入（1回だけのデータ変更・ADR-1007 決定1）

| code | name_ja | name_en | sort_order | selectable_on_create |
|---|---|---|---|---|
| active | 有効 | Active | 10 | TRUE |
| inactive | 無効 | Inactive | 20 | TRUE |
| archived | アーカイブ | Archived | 30 | TRUE |
| pending_dedup_review | 重複確認待ち | Pending duplicate check | 40 | FALSE |

- selectable_on_create の根拠（2026-11-12 origin/main・生は同じフォルダの evidence-hide-on-create.md）: この状態を自動で付ける道は今のコードに無い。新規作成の道5本（`backend/app/routers/companies.py:404`・`backend/app/routers/contacts.py:439` は画面の値で既定 active＝`backend/app/schemas/company.py:134`・`backend/app/schemas/contact.py:109`／`backend/app/routers/registration_tokens.py:322` は 'active' 固定／`backend/app/routers/integrations.py:653`・`:671` は列を書かず DB 既定 'active'＝`migrations/028_create_companies.sql:78`）。付けたのは4月の移行の使い捨て `scripts/_archive/data_migration/migrate_customers_from_sheet.py:72`・`:198` だけ。状態の意図は「移行で二重の疑いがある記録を仮に入れ、人が別か同じかを決めるまでの保留」（PR #163 本文・`migrations/015_replace_customers_schema.sql:130`）。解消の操作は直す画面だけ（`frontend/src/pages/company-detail/CompanyBasicTab.tsx:124-125`・`frontend/src/pages/contacts/ContactEditPage.tsx:196`・`frontend/src/pages/contacts/ContactsPage.tsx:395`）。
- サーバーは作るときに pending_dedup_review を受けても断らない（列挙は残す・§6-1）。画面で出さないだけにする。理由: 断る形にすると記号の判断がサーバーに増え、表の列と二重になる。必要になれば別設計。

- 日本語名は今の ja.json の値（`frontend/src/locales/ja.json:1133-1135`・`:1299`）をそのまま写す。英語名の3つは今の en.json（`frontend/src/locales/en.json:1133-1135`）と同じ。重複確認待ちだけ、今の英語「Pending Dedup Review」（`frontend/src/locales/en.json:1161`）は仕組みの略語（Dedup）を含むため「Pending duplicate check」に直す（英語画面だけ見た目が変わる）。
- 色の種類は表に置かない。今の `frontend/src/utils/statusPresentation.ts:164-176` の bucket・badgeVariant をそのまま使う（審査2回目の指摘4: statusPresentation.ts は同期の固定表で `:62`・`:190`、`frontend/src/pages/design-preview/sections/StatusSection.tsx:40-85` が回している。DB から作る形はつなぎ方が無い）。
- 4行の値を書くのは1ファイルだけ: docs/handoff/status-ssot-contact-company/insert-customer-statuses.sql（便1 の PR で作る。今は無い）。本番への投入も、試験の準備（§5-2）も、このファイルを読む。
- 手順: そのファイルを DRY-RUN（ROLLBACK）で4行と出るのを確かめる → PO の `!` で COMMIT（`SET LOCAL app.is_operator='true'`）→ 読み取りの鍵で4行を確かめる。

## 5. 会社・連絡先の列を表に結ぶ（便2・migration）

- 全会社の領域（tenant_*）の companies・contacts で:
  1. `ADD CONSTRAINT ..._status_fkey FOREIGN KEY (status) REFERENCES public.customer_statuses(code) NOT VALID`
  2. `VALIDATE CONSTRAINT`（本番は合計105行・§recon 1）
  3. 旧 CHECK（companies_status_check / contacts_status_check）を DROP
- 会社の領域ごとに、表（companies・contacts）や status 列が無ければ飛ばす（CI の土台の tenant_001.companies には status 列が無く、contacts の表も無い: `.github/workflows/migration-test.yml:312-319`）。
- 件数を数える SELECT と RAISE EXCEPTION は置かない（審査3回目の指摘 M1: 表の名前を含む SELECT は、便3 で一覧に足した後に確認8 が止める形になるため）。代わりに `VALIDATE CONSTRAINT` そのものが止め役になる: 会社・連絡先に行があり4行が足りなければ外部キー違反で失敗し、移行全体が止まる。行が0の空の DB（CI の全件ドライラン `.github/workflows/migration-test.yml:2118`）では通る。本番は105行あるので、4行の投入前に流すと止まる。理由の説明は RAISE NOTICE（許す語 `:39-45`）で書く。外部キーの行は REFERENCES を含むので許される。
- 済んでいる会社の領域は飛ばす（審査4回目 N1）: 入れ替えのたびに全 migration を流し直す（ADR-1037）ので、`pg_constraint` で「`..._status_fkey` が有り、かつ旧 CHECK が無い」なら ALTER を1つも出さない。2周目で鍵を取りに行かない。
- 取引の単位（審査4回目 N1）: `scripts/run_all_migrations.sh:118` はファイルを1つずつ流し、まとめて1つの取引にする指定は無い（`:25` は失敗で止める指定だけ）。会社の領域を回す DO ブロックは1つの取引になるので、その中の NOT VALID・VALIDATE・DROP は同じ取引で、ADD が取った鍵は VALIDATE の終わりまで続く。つまり NOT VALID に分けても鍵を軽くする効果は無い。それでもよい理由: 本番は合計105行で VALIDATE はすぐ終わる。鍵待ちは ADR-1037 の1秒で諦めて流し直す。参照先は便3 まで誰も読まない（§12-4）。NOT VALID を残すのは、書き方を GitLab の決まりにそろえるためだけ。
- 会社を作る処理 `backend/app/services/tenant.py:224`・`:255` も CHECK → 外部キーに直す（同じ PR）。
- ロック待ち1秒（ADR-1037）。
- ロールバック: 外部キーを DROP し CHECK を付け直す SQL を design に添える（カードに書く）。

### 5-2. 試験の準備（審査1回目の指摘）

- 単体試験（SQLite）: 会社・連絡先の表は `backend/tests/conftest.py` が自前で作り、外部キーが無い。ここは変えない（外部キーの確かめは PostgreSQL の試験で行う）。
- PostgreSQL の試験: `backend/tests/rls_bootstrap.py` の `_PG_BOOTSTRAP_MIGRATIONS` に便1の migration を足す。`backend/tests/seed_data.py` に customer_statuses_seed_sql() を足し、§4 の SQL ファイルを読んで4行を入れる（値をもう1回書かない）。前例 `backend/tests/test_channel_masters_shared_pg.py`。
- 新しい PostgreSQL の試験 backend/tests/test_customer_statuses_pg.py で K3（表に無い値は断られる）と K10（RLS の下で、会社の領域の書き込みが外部キーの検査に通る）を確かめる。
- migration の試し流し（.github/workflows/migration-test.yml）: CI は PR で変えたファイルだけを流す（`:1233-1235`）ので、便2 の PR では便1 の表が無い。前例（`:1305` の「変更 SQL の前提の移行を先に実行」）と同じ形で、便2 のファイルが入ったときに便1 の migration を先に流す step を足す（便2 の PR で）。この step は workflow-lint.yml ではないので PO の permit 対象外だが、CI の設定の変更として PR 本文に明記する。
- それでも全件ドライランで落ちたときは、実測の ERROR 文を `scripts/migration-guard/dryrun-exclusions.tsv` の reason に書く（見込みで書かない。同ファイル冒頭の規則）。

## 6. 読み書きの付け替え（便3・アプリのコード）

### 6-1. サーバーの読み口1か所

- 新しいファイル backend/app/services/customer_statuses.py に表名の定数と読む SQL を置く（チャネル名簿の `backend/app/services/channel_masters.py:1-13` と同じ型）。
- API: `GET /api/customer-statuses` → 4行（code・name_ja・name_en・sort_order・is_active・selectable_on_create）。ログインした人なら誰でも読める。
- 会社をまとめる処理の `backend/app/routers/companies.py:982`（`SET status='active'`）と `:1019`（記録）も記号の定数を使う（審査2回目の指摘5）。
- `frontend/api-contract/openapi.json:5904`・`:7712` は、サーバーの列挙を残すので変わらない。新しい API の分だけ契約の書き出しを更新する。
- サーバーの列挙（`backend/app/schemas/company.py:33-37`・`backend/app/schemas/contact.py:26-36`）は残す。理由: 動きが記号に頼るため、記号はコードでも名前を持つ。代わりに §6-4 の試験で「列挙＝表の行」を毎回確かめる。受け取り時の正しさは DB の外部キーが最後に守る。

### 6-2. 画面の付け替え

- 読み口: 新しい hook（useCustomerStatuses）で API を1回読み、言語で name_ja/name_en を選ぶ。
- statusPresentation.ts の contact・company の組は bucket・badgeVariant を残し、labelKey（辞書キー）だけ外す。名前は hook から出す。`frontend/src/pages/design-preview/sections/StatusSection.tsx:40-85` は、この2組だけ hook の名前を使う（他の11組は今のまま）。
- recon §3 のフォーム7か所とまとめる画面1か所を、この読み口から並べる形に直す。hook は `options(mode: "create" | "edit")` を出し、create は `selectable_on_create` が TRUE の行だけ、edit は全行を sort_order 順に返す。記号で行を選び分ける書き方（`code !== "pending_dedup_review"` など）は画面に書かない。is_active が FALSE の行は create・edit とも出さない。ただし edit で今の値がその行のときは、その1行だけ残す（今の値が空に見えるのを防ぐ。§3 の「過去の行は残す」と同じ考え）。

#### 6-2-1. 7か所とそれぞれの mode（2026-11-12 Opus が origin/main で数え直し）

| # | 場所（画面の名前は ja.json） | 実物 | 使う場面 | 今 | 変更後の mode |
|---|---|---|---|---|---|
| 1 | 顧客情報の一覧 →「新規登録」の小窓 | `frontend/src/pages/companies/CompaniesPage.tsx:436-439`・選択肢 `:510-515` | 作るだけ | 4つ | create（3つ） |
| 2 | 担当者の一覧 →「新規登録」の小窓 | `frontend/src/pages/contacts/ContactsPage.tsx:289-292`・選択肢 `:337-341` | 作るだけ | 3つ | create（3つ） |
| 3 | 顧客情報の一覧 → 行の「顧客情報編集」の引き出し | `frontend/src/pages/companies/CompaniesPage.tsx:566-576` → `frontend/src/pages/companies/CompanyFormFields.tsx:32` | 直すだけ | 4つ | edit（4つ） |
| 4 | 顧客情報の詳細 →「基本情報」タブ | `frontend/src/pages/company-detail/CompanyBasicTab.tsx:92` | 直すだけ | 4つ | edit（4つ） |
| 5 | 担当者の一覧 → 行の「担当者編集」の引き出し | `frontend/src/pages/contacts/ContactsPage.tsx:360` → `frontend/src/pages/contacts/ContactFormFields.tsx:43` | 直すだけ | 4つ | edit（4つ） |
| 6 | 担当者の編集画面 | `frontend/src/pages/contacts/ContactEditPage.tsx:189` | 直すだけ | 4つ | edit（4つ） |
| 7 | 顧客情報の詳細 →「担当者管理」タブの小窓 | `frontend/src/pages/company-detail/CompanyContactsTab.tsx:151-154`（題 = `contactForm.id === null ? newContact : editContact`）・選択肢 `:196-204` | 両方 | 3つ | `contactForm.id === null` なら create、そうでなければ edit |

- 7 は直すときに4つになる。直すときに今の値が pending_dedup_review の担当者を開くと、今は選択肢に無い値になっている（`:196-204` に無い）。変更後は選択肢にあるので正しく出る。
- 記号から CSS の組み名を作る4か所（`frontend/src/pages/companies/CompaniesPage.tsx:408`・`frontend/src/pages/contacts/ContactsPage.tsx:386`・`frontend/src/pages/company-detail/CompanyContactsTab.tsx:124`・`frontend/src/pages/company-detail/CompanyDetailPage.tsx:98`）は statusPresentation の badgeVariant の共通の組に直す（審査2回目の指摘5）。
- サーバーの比較 `backend/app/routers/duplicates.py:93`・`backend/app/routers/companies.py:767`・`:980` は記号の定数（サーバー側1か所: backend/app/services/customer_statuses.py）を使う。
- 値の直書き（recon §3 の比較・初期値・`frontend/src/components/MergeCompanyModal.tsx:96`、審査2回目のあとに Opus が見つけた初期値と「有効に戻す」操作 `frontend/src/pages/company-detail/company-detail.types.ts:125`・`:138`・`:222`、`frontend/src/pages/company-detail/useCompanyDetail.ts:115`・`:236`・`:274`、`frontend/src/pages/contacts/ContactEditPage.tsx:62`・`:125`・`:126`、`frontend/src/pages/contacts/ContactsPage.tsx:86`・`:91`・`:171`・`:225`、`frontend/src/pages/companies/CompaniesPage.tsx:151`・`:159`・`:294`）: 動きに関わる比較（まとめる時の pending 判定など）は記号の定数1か所（新しいファイルに CUSTOMER_STATUS_CODES）にまとめ、各所はそれを使う。
- 色の CSS `frontend/src/components.css:268-271`（status-active・status-inactive・status-archived・status-pending_dedup_review）は、上の4か所を直したあと使う所が0件になるのを `git grep` で確かめてから消す。`frontend/src/pages/design-system/DesignSystemPage.tsx:191` も合わせる。
- 辞書から消すキー: customers.status_active/inactive/archived/pending_dedup・contacts.statusPendingDedupOption・contacts.statusCode.*（ja/en 両方）。ただし他の画面が同じキーを使っていれば残す（カードで `git grep` して0件を確かめてから消す）。ja.json の 1475・1922・2114 行の status_active は別の画面のキーなので触らない。同じ名前の別の画面のキー channels.status_*・products.status_* も触らない（審査2回目で確認）。

### 6-3. まとめる画面の文（6キー）

| キー | 変更後（ja） |
|---|---|
| mergeCompany.selectMaster | 残す方の顧客情報を選択 |
| mergeCompany.reasonLabel | マージ理由（任意・記録に残ります） |
| mergeCompany.confirmDesc3 | 残す方が{{pending}}のときは、自動で{{active}}になります。 |
| mergeCompany.confirmDesc4 | 操作の内容は記録に残ります。 |
| mergeContact.reasonLabel | 統合理由（任意・記録に残ります） |
| mergeContact.confirmDesc3 | 操作の内容は記録に残ります。 |

- {{pending}}・{{active}} には §6-2 の読み口から状態の名前を入れる（名前を文に直書きしない）。
- en も同じ意味に直す。裏付け: `backend/app/routers/companies.py:978-985`（上げる動き）、`backend/app/routers/contacts.py:869`・`:875`（記録）。

### 6-3-2. まとめる先がアーカイブのときの失敗の文（ADR-1071）

- `backend/app/routers/companies.py:768` の文をやめ、detail に小文字の理由コード merge_target_archived を返す。
- 画面は共通の対応表 `frontend/src/lib/apiErrorReason.ts` に1行足す（審査2回目の指摘7: 新しい共通の前例。`i18n.t(key)` は差し込みの値を渡さないので、文に状態の名前は入れない）。文（ja）:「残す方の顧客は今の状態ではまとめられません。先に残す方の状態を変えてから、やり直してください。」。状態の名前を文に直書きしない（名前の正本は DB）。ja/en の apiError に足す。
- 突き合わせの試験 `frontend/src/lib/apiErrorReason.test.ts`・`backend/tests/test_api_error_reason_sync.py` に足す。`backend/tests/error_detail_baseline.json` の数を1下げる。
- 文の出る場所: `frontend/src/components/MergeCompanyModal.tsx:141`（e.message。`frontend/src/lib/api.ts` が表のコードのとき文に変える）。

### 6-3-4. 重複の解消ボタンの文（2026-11-12 Opus が見つけた・PO に「設計書に載せる」と伝え済み）

- この節の ja.json の行番号は origin/main cee9633b9 のもの（他の節の a88194893 とは3行ずれる。画面ファイルの行は両方で同じ）。

| キー | 今（ja・`frontend/src/locales/ja.json`） | 変更後（ja） |
|---|---|---|
| companies.dedupConfirmAsDistinct（`:1235`・使う所 `frontend/src/pages/company-detail/CompanyBasicTab.tsx:137`） | 別顧客情報として確定（active 化） | 別顧客情報として確定（{{active}}にする） |
| contacts.confirmAsDistinctFull（`:1284`・使う所 `frontend/src/pages/contacts/ContactEditPage.tsx:202`） | 別人として確定（active 化） | 別人として確定（{{active}}にする） |
| contacts.mergeAsDuplicate（`:1285`） | 重複としてマージ（担当者単位は未実装） | 重複としてマージ（en: Merge as duplicate）。キーは分けず文だけ直す |

- {{active}} には §6-2 の読み口から「有効」の名前を入れる（名前を文に直書きしない）。en も同じ意味に直す（今は `(activate)`）。
- `frontend/src/pages/company-detail/CompanyContactsTab.tsx:136` は `t("contacts.mergeAsDuplicate").replace("（担当者単位は未実装）", "")` と日本語の文字を書いて消している（ADR-027 違反・英語画面では消えない）。文を直したので replace を消し `t("contacts.mergeAsDuplicate")` だけにする（新しいキーは作らない）。
- `frontend/src/pages/contacts/ContactEditPage.tsx:204-206` は金型の Button でない生の `<button>` と直の style（ADR-144 違反）で、押せないまま。担当者をまとめる処理は既にある（`backend/app/routers/contacts.py:706` ADR-098 SA-04 J3・画面 `frontend/src/components/MergeContactModal.tsx:128`・`frontend/src/pages/company-detail/CompanyContactsTab.tsx:136` から開ける）。つなぐか消すかは §9 未決5。
- 試験 `frontend/src/components/FullPageFormButtonMigration.test.tsx:176-177`・`:198` はキー名で探す。§6-3-4 の文言の直しだけなら、キーを分けないので試験は変えずに通る（審査6回目で確認）。ただし §9 未決5 を実行するときは、同じ試験の統合ボタンの行を直す（手順は未決5 の選択肢に書いた）。

### 6-3-3. 変えない所

- 会社の書き出し（`backend/app/tasks/reports.py:51`）は記号のまま出す。記号は分析で結ぶための鍵で、名前は表から引ける（K8）。書き出しの形を変えるかは別に PO に聞く（§9 未決3）。

### 6-4. 試験と見張り

- サーバーの試験: 試験 DB に4行を用意し、CompanyStatus・ContactStatus の値の集合＝表の code の集合を確かめる。§4 の SQL ファイルの値とも一致を確かめる。
- 画面の試験: statusPresentation.test.ts を表の行から作る形に直す。記号を書いた試験（`backend/tests/test_companies.py`・`backend/tests/test_contacts.py`・`frontend/src/components/FullPageFormButtonMigration.test.tsx`）は、選択肢の数え方が変わる所だけ直す。
- 見張り: 便3 の後、会社・連絡先の4つの記号を画面のコードに直書きしたら止める検査を scripts/check-ui-governance.js に足す（定数ファイル1か所だけ許す）。

## 7. 出す順番（前が本番で確かめ終わってから次へ）

1. 便1: 表を作る（migration・危険パス＝GO要）
2. データ変更: 4行を入れる（PO の `!`）
3. 便2: 外部キーに付け替え（migration＋tenant.py・GO要）
4. 便3: API・画面・辞書・まとめる画面の文・試験・見張り（アプリのみ）

## 8. 受入条件と確かめ方

| 基準 | 検証方法 |
|---|---|
| K1 表に4行・名前と並びが §4 のとおり | 読み取りの鍵で `SELECT * FROM ai_ro.public__customer_statuses ORDER BY sort_order`（見る名前は実装時の ai_ro の名前に合わせる）→ 4行 |
| K2 本番10表の status 列が表に結ばれ、CHECK が無い | 読み取りの鍵で制約一覧 → 外部キー10本・status の CHECK 0本 |
| K3 表に無い値を入れると DB が断る | CI の試験で `UPDATE companies SET status='xxx'` が外部キー違反 |
| K4 状態を選ぶフォーム7か所の選択肢が §6-2-1 の表のとおり | Chrome で §6-2-1 の 1〜7 を開いて数える（保存はしない）。作るとき（1・2・7の新規）は「有効・無効・アーカイブ」の3つ、直すとき（3〜6・7の編集）は「有効・無効・アーカイブ・重複確認待ち」の4つ。名前と並びが §4 のとおり。加えて画面のコードに `pending_dedup_review` で選択肢を選び分ける書き方が0件（K5 の grep に含まれる） |
| K14 作る画面に出すかを表だけで変えられる | 2本とも緑: (a) サーバーの試験（PostgreSQL・backend/tests）で `GET /api/customer-statuses` の各行に selectable_on_create があり、表の値と同じ (b) 画面の試験（vitest・useCustomerStatuses の隣）で、API の返事を作り替えて1行の selectable_on_create を FALSE にすると、options("create") から消え options("edit") には残る。件数は create 3・edit 4（§4 の値のとき） |
| K15 解消ボタンの文に「active」「未実装」が0件 | `git grep -n -E 'active 化|\(activate\)|未実装|not implemented' -- frontend/src/locales/ja.json frontend/src/locales/en.json` の行のうち companies.dedupConfirmAsDistinct・contacts.confirmAsDistinctFull・contacts.mergeAsDuplicate が0件（変更後の文の {{active}} は当たらない）。`git grep -n 'replace("（' -- frontend/src/pages/company-detail/CompanyContactsTab.tsx` が0件 |
| K5 会社・連絡先の画面のコードに4つの記号の直書きが0件（定数ファイルを除く） | `git grep -n -E '"(active\|inactive\|archived\|pending_dedup_review)"' -- frontend/src/pages/contacts frontend/src/pages/companies frontend/src/pages/company-detail frontend/src/components/MergeCompanyModal.tsx frontend/src/components/MergeContactModal.tsx \| grep -v className` が0件。基準値（a88194893 で実測）: 10ファイル53件のうち tab の className の3件を除く50件 |
| K6 状態の名前の辞書キーが0件 | `git grep -n -E 'customers\.status_(active\|inactive\|archived\|pending_dedup)\|contacts\.statusCode\|statusPendingDedupOption' -- frontend/src` が0件。基準値（a88194893 で実測）: 41件（辞書を除くと39件） |
| K7 まとめる画面の文に master・pending_dedup_review・active・audit_logs が0件 | ja/en.json それぞれで `jq -r '.mergeCompany[], .mergeContact[]' frontend/src/locales/<ja\|en>.json \| sed -E 's/\{\{[A-Za-z_]+\}\}//g' \| grep -c -E 'master\|pending_dedup_review\|active\|audit_logs'` が両方0（大小文字を区別。`{{active}}` は sed で除くので数えない）。基準値（origin/main cee9633b9 で Opus が同じ命令で実測）: ja 6・en 6 で ×。Chrome で会社をまとめる画面を開き文を読む（実行はしない） |
| K8 分析で名前が引ける | 読み取りの鍵で companies と customer_statuses を結んだ件数の集計が名前付きで出る（tenant_004: 有効 51） |
| K9 試験 | CI 全部緑。列挙＝表の試験が緑 |
| K10 RLS の下で外部キーが働く | backend/tests/test_customer_statuses_pg.py が緑（会社の領域の利用者で会社を作れる・表に無い値は断られる） |
| K11 まとめる先がアーカイブのときの文に仕組みの言葉が0件 | `frontend/src/lib/apiErrorReason.test.ts` で merge_target_archived → 文に master・archived・active・merge_target が無い。`backend/tests/test_api_error_reason_sync.py` が緑 |
| K12 migration が新しい表に値を書くと止まる | 便3 の後、`scripts/migration-guard/protected-tables.txt` に customer_statuses がある。`python3 scripts/check-migration-value-writes.py repo` が緑。便1・便2 の PR の Migration guard が緑（一覧に足すのが便3 なので確認8 に当たらない） |
| K13 便2 が CI の migration 検査を通る | 便2 の PR の Migration SQL Test が緑（変更 SQL・全件ドライラン・2周目の冪等）。加えて、2周目の記録に便2 の ALTER が1つも出ない（§5 の飛ばす条件）。後半は CI では確かめられず（tenant_001 に contacts が無い）、本番で不合格だった → §15 便4 で直し、デプロイの記録で確かめる |

## 9. 未決（PO に1件ずつ）

1. 見込み客の状態（ADR-109・名前は辞書）も同じ形（名前も DB）に寄せるか。今回は対象外。別テーマとして後で聞く。
2. 他にも「名前が辞書にあり DB に無い」状態が13種ある（statusPresentation.ts の13ドメイン）。どこまで DB に移すかは別テーマ。
3. 会社の書き出し（CSV）の状態の列を、記号のままにするか名前にするか。今回は記号のまま（§6-3-3）。
4. 【決定 PO 2026-11-12「1」】「重複確認待ち」は作るときはどこにも出さず、直すときはどこでも出す。表に列 selectable_on_create を足して決める（§3・§4・§6-2-1）。PO の言葉:「新規で作成するときは必要ないステータスなら表示しなくていいと考える」「直すときだけ表示させるのが良い？」。
5. 【決定 PO 2026-11-12「1」＝選択肢1 つなぐ】担当者の編集画面の押せない「重複としてマージ」ボタン（§6-3-4）を、既にある担当者をまとめる画面につなぐ。便3 で下の「1 つなぐ」のとおり作る。PO に示した選択肢: 1 ボタンが使えるようにする／2 ボタンを消す／3 今のまま残す。
   - 事実（origin/main aec493c7f・cee9633b9 から対象パスの差分なし。生は同じフォルダの evidence-merge-button.md）:
     - まとめる画面 `frontend/src/components/MergeContactModal.tsx:37-45` が要るのは open・companyId・source（id・contact_code・display_name・surname・given_name）・onMerged・onCancel。編集画面の `frontend/src/pages/contacts/ContactEditPage.tsx:29-43` の Contact にすべてある（company_id を companyId に渡す）。新しい API は要らない。
     - 会社の担当者タブ `frontend/src/pages/company-detail/CompanyContactsTab.tsx:134-137`・`:241-256` が同じ窓を同じ形で開いている（手本）。
     - まとめると、今開いている担当者が消える（`backend/app/routers/contacts.py:706-720`・`frontend/src/components/MergeContactModal.tsx:128-132`）。取り消せない。商談・注文・見積・請求がある担当者は 400 で止まる（`backend/app/routers/contacts.py:765-789`）。
     - 消えるので、つなぐ場合は onMerged で残した側の編集画面 `/contacts/{masterId}/edit`（`frontend/src/pages/contacts/ContactEditPage.tsx:2` の道）へ移る必要がある。
   - 既存の試験 `frontend/src/components/FullPageFormButtonMigration.test.tsx:171-205`（Opus が origin/main で行を確かめた）は「統合ボタンがあって押せない」ことを確かめている: `:177` ボタンを名前で探す、`:181` disabled が true、`:182-183` 押しても何も送らない、`:203` 失敗のあとも disabled が true。どちらの選択肢でもこの試験が落ちるので、同じ便で直す（審査7回目の指摘）。
   - 1 つなぐ: `frontend/src/pages/contacts/ContactEditPage.tsx:204-206` の生 button を金型 `Button`（variant="secondary" size="md" type="button"）に替え、押すと MergeContactModal を開く（companyId=contact.company_id、source は Contact の5項目）。onMerged(masterId) で `/contacts/{masterId}/edit` へ移る（道は `frontend/src/App.tsx:213`・Opus が origin/main で確認）。試験は `:181`・`:203` を「disabled が false」に、`:182-183` を「押すと窓の題 `mergeContact.title` が出て、patch は呼ばれない」に変える。`:177` はそのまま。窓は開くと `/companies/41/contacts?per_page=100` を読むので、試験の偽の GET（`:78-83`。知らない道は例外を投げる）にこの道の答え（例: 空の一覧 `[]`）を1行足す（審査8回目の指摘）。
   - 2 消す: `frontend/src/pages/contacts/ContactEditPage.tsx:204-206` を消す。辞書キー contacts.mergeAsDuplicate は会社の担当者タブ（`frontend/src/pages/company-detail/CompanyContactsTab.tsx:136`）が使うので残す。試験は `:177`・`:181-183`・`:203` を消し、代わりに「`queryByRole('button', { name: 'contacts.mergeAsDuplicate' })` が null」を1行足す。
6. 【別テーマ・PO 2026-11-12 依頼】作る画面で、すでに登録されている項目を赤枠で知らせる（名前・メール・電話番号＝PO「1」、加えて会社コード・担当者コード・FedEx口座番号・ウェブサイト＝PO「1」）。この設計とは別の設計 docs/handoff/create-duplicate-warning/ で扱う（1リリース1テーマ）。この設計の §6-2 の hook とは別の部品。

## 10. 弊害と対処

1. 画面が API を読むまで選択肢が空になる → hook が読み込み中を返し、選択肢は読み込み後に出す。失敗時は失敗の文（ADR-1071 の形）。
2. PostgreSQL の試験で4行が無いと会社・連絡先を作る試験が落ちる → §5-2 の seed で入れる（ADR-1007 の「試験の側でデータを用意」）。SQLite の単体試験は外部キーが無いので影響なし。
3. 新しい会社を作るとき、public の表に4行が無いと作れない → 本番は4行が入っている。開発の手元環境はデータ変更の SQL を流す手順を README に書く。
4. 会社だけ・連絡先だけの状態が必要になった時、1つの表では足りない → その時に applies_to 列を足す別設計。今は両方同じ（recon §1）。
5. 英語名を DB に置くと翻訳の置き場が2つになる → 状態の名前は DB だけ・固定の文は辞書だけ、と新 ADR で線を引く。

## 11. 新しい ADR（便1 の PR で起票）

- 題: 会社と連絡先の状態は public.customer_statuses を正本にする
- 決定: 記号・日英名・並び順は表の行。色の種類は statusPresentation.ts（ADR-120）に残す。会社・連絡先の status 列は外部キー。画面は API から読む。サーバーの列挙は試験で表と一致を確かめる。
- ADR-109 との関係: 見込み客は変えない（PO 判断待ち）。ADR-120 との関係: 入口と色は同じ・名前の出所だけ DB になる。

## 12. 外部・過去事例の参照と我々への応用

調べた日: 2026-11-11（Opus が原文を直接読んだ。生の本文は /tmp/CC報告ファイル/ext/）。数は原文にあるものだけ書く。クラウドの調べ役は外のサイトに届かず BLOCKED だったため、Opus が手元で読んだ。

### 12-1. 仕様（事例ではない・PostgreSQL 16 公式文書 sql-altertable.html、Context7 で確認）

- ADD FOREIGN KEY は、付ける表と参照先の表の両方に SHARE ROW EXCLUSIVE の鍵を取る（読み取りは止めない・書き込みは止める）。
- NOT VALID なら既存の行を調べず、すぐ終わる。VALIDATE CONSTRAINT は SHARE UPDATE EXCLUSIVE（読み書きを止めない）と、参照先に ROW SHARE。

### 12-2. 失敗事例

| | 失敗事例1: GoCardless（決済会社） | 失敗事例2: 当社 Sales Anchor（ADR-1037） | 失敗事例3: 公開リポジトリの事故報告 |
|---|---|---|---|
| いつ | 1月下旬（年は記事に無い。記事の最終更新 2024年6月） | 2026-10-19 の入れ替え。直近300回で4件 | 日付は記事に無い |
| どこで | 本番の API と PostgreSQL | 本番 prod1（在庫表） | GitHub FEMZYKENTLTD/Resume-Screening-Classifier PR #6 |
| 誰が | GoCardless の開発チーム（筆者 Chris Sinjakli） | 当社の入れ替え作業 | 同リポジトリの開発者 |
| 何を | 空の表に外部キーを付け直す（NOT VALID でも起きる、と記事は書く） | 全 migration の流し直しで、外部キー先の表に強い鍵を取りに行った | 状態の値の綴りがプログラムと DB でずれた（大文字の COMPLETED を DB が断った） |
| なぜ | 参照先の表に長い読み取りが走っていて、鍵待ちの列ができ、後から来た読み書きが全部止まった | 鍵待ちに上限が無く、後から来た在庫表の読み取りが全部止まった | 値の正本が2か所（プログラムの列挙と DB の型）にあった |
| どうやって分かった | API の時間切れの警報。前日の写しで流し直すと数百ミリ秒で通った | 在庫表の平均が最大 13.5 秒・deadlock で 500。試験 DB の再現で読み取りが 8912ms 待った | 状態を書くたびに invalid input value for enum の失敗 |
| どれだけ | API 停止 約15秒 | 平均最大 13.5 秒・失敗4件/300回 | 状態の書き込みが毎回失敗（件数は記事に無い） |
| 失敗の要因 | 鍵待ちの上限（lock_timeout）が無かった | 同じ（上限が無かった） | 値の置き場が2つで、ずれを止める試験が無かった |

- 適用の限界: 事例1 の記事は年も PostgreSQL の版も書いていない（脚注で「9.4 は VALIDATE の鍵を軽くした」と触れるだけ）。今の版 16 の鍵は記事の説明（AccessExclusive）より軽い（12-1）。ただし「鍵待ちの列で後ろが全部止まる」仕組みは今も同じ。事例3 は小さな個人の作品で、規模は当社より小さい。

### 12-3. 成功事例

| | 成功事例1: GitLab（社内の決まりと道具） | 成功事例2: 当社 ADR-1037 の後 | 成功事例3: 当社 チャネル名簿（同じ型の前例） |
|---|---|---|---|
| いつ | 今の開発文書（2026-11-11 時点の docs.gitlab.com） | 2026-10-21 便1.1 以降 | 2026-11-06（表を作る PR #5206 本番反映 22:22 JST・6行投入） |
| どこで | GitLab.com とセルフホスト全部 | 本番 prod1 | 本番 prod1 |
| 誰が | GitLab の開発者全員 | 当社の入れ替え | PO の `!` 実行・Opus が確認 |
| 何を | 外部キーは NOT VALID で付け、確かめ（VALIDATE）は別の回に分ける。鍵が取れなければ短い待ちで諦めて流し直す（with_lock_retries） | ロック待ち1秒で諦め、3秒あけて流し直す | public の名簿の表＋1回だけの投入＋付け替え（この設計の型） |
| なぜ | 高い利用の表で鍵待ちの列を作らないため | 事例2 の失敗の再発を止めるため | 会社ごとの写しをやめて値の正本を1つにするため |
| どうやって | 道具（add_concurrent_foreign_key・with_lock_retries）と RuboCop の機械点検。確かめは週末にまとめて流す | `scripts/run_all_migrations.sh` の4つの値と、使い捨て DB の試験 | DRY-RUN → COMMIT → 読み取りの鍵で確認 |
| どれだけ | 鍵の取り直しは最大50回・最悪40分で打ち切り。「止めてよい」印の仕組みは4年間1度も使われず廃止（＝止めずに作れた） | 便1.1 の入れ替え: 移行77秒・流し直し1回・上限到達0回・成功。2回目: 流し直し0回・成功 | 共用6行が表のとおり・会社行0（23:38 JST 確認） |
| 成功の要因 | 人の注意でなく道具と機械点検に決まりを入れた | 上限と流し直しを道具の中の値1か所にした | 投入を migration に書かず台本で1回だけ（ADR-1007） |

- 適用の限界: GitLab は当社よりはるかに大きい（表もアクセスも）。当社の対象は会社105行で、VALIDATE は短い。成功事例2・3 は当社の記録で、外部の第三者の確かめではない。
- 調べたが見つからなかったもの: 「状態の値を名簿の表に移して分析が良くなった」ことを数で示した公開の事例。案内記事（どちらを選ぶかの考え方）はあるが、効果の数は無かった。この設計の成功は事例ではなく §8 の K1〜K13 で確かめる。

### 12-4. この設計への応用

1. 便2 の外部キーは NOT VALID → VALIDATE の書き方にする（§5）。ただし1つの取引の中なので、GitLab のように鍵を軽くする効果は無い。当社は105行と小さく、鍵待ちは1秒で諦める（2）ことで守る。
2. 鍵待ちは1秒で諦めて流し直す（ADR-1037 が既に機械で入っている。事例1 の要因を消している）。
3. 便2 の時点で、参照先の public.customer_statuses は誰も読んでいない（便3 まで使われない）。事例1 の「参照先に長い読み取り」が起きない。
4. 値の正本を DB の表1つにし、サーバーの列挙とのずれは試験で止める（§6-4。事例3 の要因を消す）。
5. 決まりは人の注意でなく機械（外部キー・試験・見張り）に入れる（成功事例1 の要因。§13）。

## 13. 維持の仕組み

- 守り手: CI の必須チェック（外部キー・試験・画面の直書きの見張り・値の書き込みの見張り）と、状態の行を足すときの PO（運営の手作業・ADR-1007）。
- DB の外部キーが、表に無い値を入れさせない（K3）。
- CI の試験が、サーバーの列挙と表の行のずれを止める（§6-4）。
- scripts/check-ui-governance.js が、画面への記号の直書きを止める（§6-4）。
- `scripts/check-migration-value-writes.py` と protected-tables.txt が、便3 以降に足す migration による表への値の書き込みを止める（K12）。
- 入れ替えのロック待ちは1秒で諦め、3秒あけて最大40回流し直す（ADR-1037・`scripts/run_all_migrations.sh`）。便2 の外部キーの付け替えもこの道を通る（§12 失敗事例1 の対策が既に機械で入っている）。
- 便2 の外部キーが、新しい会社の領域にも付く（`backend/app/services/tenant.py:224`・`:255` を外部キーに直す）。
- 状態を足すときの手順: データ変更で行を足す → 列挙に足す → 試験が緑、の順。この設計書に書き、ADR に残す。

## 14. 審査記録

- 1回目（2026-11-11 13:58 JST・クラウド Opus）: 判定なしで停止。原因は依頼文の確かめ方に見張りの止める語が入っていたこと（Opus の依頼の書き方の誤り）。途中の指摘6件（試験 DB が SQLite・recon の漏れ5か所・409 の文）は実物で確かめて recon §2・§3 と §5-2・§6-2・§6-3-2・§6-3-3・§8 K10/K11・§9-3 に反映した。
- 2回目（2026-11-11 14:14 JST・クラウド Opus・da68ab5af）: **REVISE**。指摘8件と直した所: (1) 便2 が CI で止まる → §5 の止める条件を絞り、§5-2 に前提の移行の step（K13） (2) VALIDATE は FORCE の下で読む決まりに絞られる（PG16 で実測）→ §3 に `USING (true)` (3) 「絞り込み」は実は作る・直すフォーム → §1・§6-2・K4 を直し、§9 未決4 で PO に聞く (4) statusPresentation.ts は同期の固定表 → 色は表に置かずコードに残す（§2・§3・§4・§11） (5) recon の漏れ → recon §2・§3 と §6-1・§6-2 (6) K5・K6 の grep の書き方の誤り → 書き直して基準値を実測（K5 50件・K6 41件） (7) 理由コードの形 → 共通の表 apiErrorReason.ts（§6-3-2） (8) ADR-1007 と値の書き込みの検査 → protected-tables.txt に足す（§3・K12）。8 の文の後半は記録の切れで読めず、検査の道具と一覧を Opus が実物で読んで補った（`scripts/check-migration-value-writes.py`・`scripts/migration-guard/protected-tables.txt`。customer_statuses は今は一覧に無い）。
- 3回目（2026-11-11 17:11 JST・クラウド Opus・0cde60fe6）: **REVISE**。2回目の8件はすべて直っていると確認（design の行で照合）。recon の行番号11か所も実物と一致。必須1件 M1: 便1 で protected-tables.txt に足すと、確認8 が便2 の件数の SELECT（と便1 自身の GRANT の行）を止める。Opus が `scripts/check-migration-value-writes.py` の確認8・許す語・全件走査（`:260`）を読んで確かめ、(1) 一覧に足すのを便3 へ移す（§3・K12・§13）、(2) 便2 の件数の SELECT をやめて VALIDATE を止め役にする（§5）、と直した。指摘の文の後半は記録の切れで読めなかった。同時に §12 を外部事例に書き換えた。
- 4回目（2026-11-11 17:17 JST・クラウド Opus・6fcfbacd8）: **APPROVE**（必須0件）。M1 が直っていることを確認した。確認8 は変えた migration の追加行だけを見る（`scripts/check-migration-value-writes.py:153-157`・`:175-180`）。全件走査（`:260-286`）は値の書き込みだけを当てる。便2 の外部キーの外し方は本人 GO の対象外で、委任の GO で足りる（`scripts/check-process-artifacts.js:569`・`:493`。ADR-1003 の例外は表と列を消す migration）。§12 の当社の数は、ADR-1037 と channel-master-shared/design.md の行とすべて一致した。外部の原文は審査役は開いていない（原文は Opus が取得して /tmp/CC報告ファイル/ext/ に置いた）。推奨3件を反映した: N1 済んだ領域は飛ばす・取引の単位の説明（§5・K13・§12-4）、N2 原文に無い「2015年ごろ」を消す（§12-2）、N3 便3 の後に便1・便2 を直すときの外し方（§3）。審査の途中で、見張りが DB の道具名を含む検索を止めた。取引の単位は Opus が `scripts/run_all_migrations.sh:25`・`:118` を読んで補った。
- 5回目の前の変更（2026-11-12・Opus）: PO の答え「直すときだけ表示させるのが良い？」→「1」を反映した。表に列 selectable_on_create を足し（§3・§4）、7か所を作る2・直す4・両方1に分け直した（§6-2-1。前の「作る3・直す4」は数え違いで、会社の連絡先タブの窓は作ると直すの両方に使う `frontend/src/pages/company-detail/CompanyContactsTab.tsx:151-154`）。解消ボタンの文の「active 化」「担当者単位は未実装」と日本語の replace を §6-3-4 に足した。K4 を書き直し、K14・K15 を足した。押せない「重複としてマージ」ボタンを §9 未決5 に、作る画面の重複の警告を別テーマとして §9-6 に置いた。5回目の審査はまだ。
- 5回目（2026-11-12 04:53 JST・クラウド Opus・48068620c）: **REVISE**。7か所の分類と行番号は実物と一致。直した3件: (1) §6-1 の API の列に selectable_on_create が無い→足した (2) K15 の grep が変更後の文 {{active}} に当たる→探す語を「active 化・(activate)・未実装・not implemented」に絞った (3) K14 の試験の種類が決まっていない→サーバーの試験と画面の試験の2本に分けた。
  - 5回目の推奨も反映した: K7 も {{active}} を数えない形に直した。is_active が FALSE の行の扱いを §6-2 に書いた。contacts.mergeAsDuplicate はキーを分けず文だけ直す（§6-3-4）。根拠の生ファイルをリポジトリの evidence-hide-on-create.md に置いた。ja.json の行番号の基準を §6-3-4 に書いた。
- 6回目（2026-11-12 05:01 JST・クラウド Opus・d0d93a95d）: **REVISE**。K15 は流して○×が付くと確認した（今は6行で×、設計どおりの文の写しなら0行で○）。§6-3-4 の行番号・K4・K14 は実物と一致し、未決5・6 は実装役が迷わないと確認した。直した2件: (1) K7 にどの文を取り出すかが書かれておらず、ファイル全体を grep すると60行当たった。値だけを取り出す jq の命令を書き足した。基準値は Opus が同じ命令で origin/main に流して ja 6・en 6 と実測した。審査役の「14行」は別の取り出し方での数なので採らない。 (2) §6-3-4 の試験の項（design.md:177）に残っていた古い文「キーを分けたら合わせる」を、キーを分けない今の方針に合わせて直した。
- 7回目（2026-11-12 05:19 JST・クラウド Opus・f0ee07d6e）: **REVISE**。K7 は ja 6・en 6 で基準値と一致し○×が付くと確認した。未決5 の事実（受け取る値・消える側・400 で止まる・編集画面の道）は実物と一致した。直した3件: (1) 重大: 未決5 のどちらの選択肢でも既存の試験 FullPageFormButtonMigration.test.tsx が落ちるのに手当てが無かった。Opus が行を確かめ（審査役の「:180」は実物では `:181`。ほかに `:182-183`・`:203` も当たる）、選択肢ごとの直し方を書いた。 (2) 6回目の記録の節番号を §6-3-2 から §6-3-4 に直した。 (3) 冒頭の状態の行の「5回目の審査が要る」を直した。
- 8回目（2026-11-12 05:29 JST・クラウド Opus・ee66d38c7）: **APPROVE**。未決5 の試験の行（`:177`・`:181-183`・`:203`）と道（`frontend/src/App.tsx:213`）が実物と合うと確認した。小さな書き足し2件を反映した: (1) 選択肢1 で窓が読む道の答えを試験の偽の GET に足す（Opus が `frontend/src/components/FullPageFormButtonMigration.test.tsx:78-83` で、知らない道は例外を投げると確かめた） (2) 冒頭の状態の行に7回目の反映を書いた。

## 15. 便4: 古い移行 037 が CHECK を足し直す件の直し（2026-11-12 追加）

### 15-1. 目的と成功条件（KGI）

- PO の言葉（2026-11-12）: 「11」＝「古い移行の直しを、設計から始める」。目的: 移行を流すデプロイのたびに、担当者（contacts）の表に鍵を取りに行く処理を0回にする。
- 成功条件（○×）: この便を入れたデプロイの記録で (a) `migration 037: … CHECK 制約に pending_dedup_review を追加` が0行・037 の完了の行が「新規追加 0 テナント」 (b) `customer_status_fk: … を外部キーに付け替えた` が0行 (c) 読み取りの鍵で K2（外部キー10本・convalidated・status の CHECK 0本）が変わらず ○。

### 15-2. 現在地（事実）

- デプロイ 43149812899（2026-11-12 12:48 JST）の記録 `/tmp/CC報告ファイル/bin3/deploy-43149812899.log`:
  - `:3468` `[21/398] psql < migrations/037_add_pending_dedup_review_to_contacts_check.sql`、`:3470-3474` tenant_001/003/004/005/006 の5行「CHECK 制約に pending_dedup_review を追加」、`:3475`「新規追加 5 テナント」。
  - `:7529` `[397/398] … 20261112_140000_customer_status_fk.sql`、`:7531-7535` 同じ5領域の contacts を「外部キーに付け替えた」。companies の行は0（028 は CREATE TABLE の中の CHECK で、足し直さない）。
- 原因: `migrations/037_add_pending_dedup_review_to_contacts_check.sql:118-133` は「pending_dedup_review を含む status の CHECK があれば飛ばす」だけ。便2 が CHECK を外したので、CHECK が無い → `:136-140` で `ADD CONSTRAINT contacts_status_check` に進む。続いて `migrations/20261112_140000_customer_status_fk.sql:41-46` の飛ばす条件（外部キーが有効・かつ CHECK が無い）が崩れ、`:56` で DROP する。2つで毎回足して外すを繰り返す。
- 順番: `scripts/run_all_migrations.sh:311`（037）→ `:1263`（便2）。全件を毎回流す（ADR-1037）。
- CI が見逃した理由（2026-11-12 CI run 43164959836 の記録で直した。前の版の「tenant_001 に contacts が無い」は誤り）: 1周目・2周目を流す段（127本）は tenant_001・tenant_002 に contacts があり、037 は「新規追加 2 テナント」を出す。ただしこの段は便2 の migration（20261112_140000）を流さないので、往復は起きない。便2 まで流す全件ドライラン（372本）は ✅ の行だけを出し、NOTICE を出さないので、往復が起きても見えない。§8 K13 の後半（2周目に便2 の ALTER が出ない）を CI で確かめる手段が無かったのに、K13 を CI の項目にした（Opus の設計漏れ）。
- 既存 migration を直す前例: ADR-1002（`docs/adr/ADR-1002-unify-product-id-and-fix-migration-compat.md:39`・`:132`）は、既存 migration に先頭のガードを足して冪等を保つ。テーブルがある場合の動きは変えない、という形。CI に「既存 migration の編集を止める」検査は無い（`git grep -n -i -E "immutable|diff-filter=M" origin/main -- .github/workflows scripts` の当たりは workflow-lint.yml の注釈1件だけ）。
- 新しい会社の領域: `backend/app/services/tenant.py:224`・`:254` は status 列に名前なしの `REFERENCES public.customer_statuses(code)` を付ける。PostgreSQL は名前なしの列の外部キーに `<表>_<列>_fkey` と名前を付ける（公式 tutorial-fk.html の例 `weather_city_fkey`、Context7 /websites/postgresql で確認）。便2 の migration も同じ名前 `contacts_status_fkey` を使う（`:24`）。

### 15-3. 変更（案と選んだ理由）

- 選ぶ案: 037 の会社の領域ごとのループで、contacts の表の有無を見た直後（`:64-71` の後）に、「contacts に名前 `contacts_status_fkey` の外部キー（contype='f'）があれば、何もせず次へ」を足す。数えて完了の行に「外部キー済 % テナント」を足す。
  - 外部キーがあるなら値の決まりは表 public.customer_statuses が持つ（ADR-1076）。CHECK を足す理由が無い。
  - 外部キーが無い領域（空の DB で 029→037 と流すとき・CI）は今までと同じ動き。
  - 足すのは pg_constraint を読むだけ。contacts の表に鍵を取らない。
  - 表の名前 customer_statuses を足す行に書かない（`scripts/migration-guard/protected-tables.txt` に載っているため、`scripts/check-migration-value-writes.py` の確認8 が足した行に表の名前を見ると止める。§14 3回目 M1 と同じ理由）。名前と contype で見分ける。
- 採らない案:
  - 便2 の migration 側で CHECK を見逃す: 037 は毎回 CHECK を足すので、contacts の鍵は1回は取る。目的に届かない。
  - 037 を run_all_migrations.sh から外す: 空の DB から作る道（CI の全件ドライラン）で、029 の3つの値の CHECK のまま便2 まで進む。便2 で外れるので結果は同じだが、登録の一覧を変えるのは影響が広い（全件ドライランと登録先の点検 `.github/workflows/migration-test.yml:56`）。ガード1つの方が小さい。
  - 新しい migration で 037 の後始末をする: 037 が足す → 新しいものが外す、の往復が残る。
- 便2 の migration は変えない（037 が足さなければ `:41-46` で飛ぶ）。

### 15-4. 機械の見張り（同じ種類を二度と通さない）

- PostgreSQL の試験 `backend/tests/test_customer_statuses_pg.py` に1つ足す: tenant.py の表の形の使い捨て DB（`_fresh()`）で、管理役で 037 → 便2 の migration をこの順に2回流す（`tests.rls_bootstrap._apply_migration`）。037 を流した直後に (1) その領域の companies・contacts に status の CHECK が0本、便2 を流した直後に (2) `contacts_status_fkey` と `companies_status_fkey` の oid が流す前と同じ（外して付け直していない）を確かめる。
  - 037 のガードを消すと (1) が落ちる（便2 のあとでは CHECK は外れているので、037 の直後に見る）。便2 が外部キーを付け直す形に壊れると (2) が落ちる。
  - CI の全件ドライランで見えない理由（§15-2: 便2 まで流す372本の段は NOTICE を出さない）を、本番と同じ表の形の試験で埋める。
- 残る隙（この便では作らない・次の候補）: 372本の全件ドライランは NOTICE を出さないので、別の表で同じ往復が起きても CI は気づかない。NOTICE を出す・往復を数える件は別テーマとして台帳に置く。

### 15-5. 受入条件と確かめ方

| 基準 | 検証方法 |
|---|---|
| K16 037 は外部キーのある領域で何もしない | 15-4 の試験が CI（PostgreSQL の試験）で緑。ガードの行を消すと落ちることを、実装役がクラウドで1回確かめて報告に書く（消したまま commit しない） |
| K17 外部キーの無い空の DB では今までと同じ | PR の Migration SQL Test（変更 SQL の1回目・2回目・全件ドライラン1周目・2周目）が緑 |
| K13 後半（直し） | この便のデプロイの記録で `/usr/bin/grep -a -c "CHECK 制約に pending_dedup_review を追加"` が0、`/usr/bin/grep -a -c "外部キーに付け替えた"` が0、037 の完了の行で「新規追加 0 テナント」、かつ「外部キー済」の数が contacts のある領域の数と同じ（今の本番は5。領域が増えたらその数） |
| K2 変わらない | 読み取りの鍵で、5領域の companies・contacts に `*_status_fkey` 10本（convalidated）・status の CHECK 0本 |

### 15-6. 弊害・戻し方・GO

- 弊害: 名前が `contacts_status_fkey` でない外部キーには効かない。いまの作り方は2つ（便2・tenant.py）とも同じ名前になる（15-2）。名前を変えるときは K16 の試験が落ちて気づく。
- 戻し方: この便の commit を戻す PR（037 の動きが元に戻るだけ。DB の形は変わらない）。
- GO: migrations を含むので危険 PR（ADR-136）。委任の GO（ADR-1003）で Opus が出す。DB の形は変えない（この便のデプロイで流れても ALTER は0のはず）が、デプロイ前の自動バックアップを確かめて GO 記録に書く。
- 外部事例: 使わない。理由: 当社の移行の流し方（毎回全件）と当社の記録で原因が決まり、効果は K13 の記録の行数で直接測れる。§12 の GitLab・GoCardless は「鍵を取る移行は短く・少なく」の根拠として引き続き当てはまる。
- 審査: 1回目（2026-11-12 14:17 JST・クラウド Opus・a886aa22b）**APPROVE**（必須0件）。ガードの名前が便2 と tenant.py の外部キーの名前と合う・CI の tenant_001 は contacts が無く動きが変わらない・確認8 に当たらない・試験はガードを消すと落ちる・037 の行番号は実物と合う・companies を含めほかの往復は無い、を確認。推奨2件を反映: K13 後半の「外部キー済」を領域の数で書く／カード手順4 の diff に台帳の札も出ると書く。

## 16. 便5: まとめる画面の後始末3件（2026-11-13 追加）

### 16-1. 目的と成功条件（KGI）

- PO の言葉（2026-11-13）: 「1」＝「残りの候補4つの設計に入る」。候補は便3 の審査役の注意（PR #5442 のコメント「マージを止めない注意」4件）。
- 目的: 会社・担当者を「まとめる」画面で、(1) 状態を表の名前で出す（ADR-1076 の SSOT を最後の1か所まで通す）、(2) まとめる権限の無い人に、押すと失敗するボタンを押させない、(3) まとめたあとの動きを機械で確かめ、壊れたら CI で気づく。
- 成功条件（○×）:
  - K18 会社をまとめる窓の候補の一覧で、状態の欄に記号（`active` 等）でなく表の名前（日本語の画面なら「有効」）が出る。
  - K19 顧客を消す権限（customers.delete）が無い人には、担当者の編集画面の「重複としてまとめる」ボタンが押せず、理由が出る。会社の担当者タブの行のボタンと、連絡手段の重複の知らせの「まとめる」ボタンは出ない。権限がある人には今までどおり出て押せる。
  - K20 担当者の編集画面でまとめて成功すると、窓が閉じ、残した担当者の編集画面に移る（試験で確かめる）。

### 16-2. 現在地（事実・origin/main cee15756b）

- 候補1（K18）: `frontend/src/components/MergeCompanyModal.tsx:238-240` は札の色は `getStatusPresentation("company", c.status)` で決め、文字は `{c.status}`（記号のまま）。同じ窓の `:301-302` と担当者の窓 `frontend/src/components/MergeContactModal.tsx:235` はすでに `customerStatuses.nameOf(...)` を使う。`customerStatuses` は `frontend/src/components/MergeCompanyModal.tsx:55` で取り済み。
- 候補2（K19）: サーバーは止めている。`backend/app/routers/contacts.py:694-699` と `backend/app/routers/companies.py:703-708` はどちらも `require_permission("customers.delete")`。画面は3か所で確かめていない。
  - `frontend/src/pages/contacts/ContactEditPage.tsx:205-207` のボタンは、状態が重複確認待ちなら誰にでも出て押せる。このファイルは権限を読んでいない（import に usePermissions が無い）。
  - `frontend/src/pages/company-detail/CompanyContactsTab.tsx:131-142` の行のボタンは canEdit（`frontend/src/pages/company-detail/CompanyDetailPage.tsx:39` の customers.update）だけで出る。
  - `frontend/src/pages/company-detail/CompanyContactsTab.tsx:234` は連絡手段の窓に `onRequestMerge` をいつも渡す。`frontend/src/components/ContactChannelForm.tsx:253-260` は渡されたときだけ「まとめる」ボタンを出す。
  - 手本: 会社の側は確かめている。`frontend/src/pages/company-detail/CompanyDetailPage.tsx:40-41` の `canMerge = hasPermission("customers.delete")`、`frontend/src/pages/company-detail/CompanyBasicTab.tsx:146-152` は重複確認待ちの欄のボタンを `disabled={!canMerge …}` にし、`title` に `companies.dedupMergeNoPermission` を出す。一覧の行の消すボタンは権限が無ければ出さない（`frontend/src/pages/companies/CompaniesPage.tsx:420`・`frontend/src/pages/contacts/ContactsPage.tsx:404`）。
- 候補3（openapi の tags が2回出る）: `frontend/api-contract/openapi.json` で tags が2回並ぶ道は74本ある（暦・翻訳・買取価格など多くの機能。生は `/tmp/CC報告ファイル/m037/recon-next/openapi-dup.txt`）。原因は `backend/app/main.py:361` の include_router の tags と、各道の `tags=[...]`（例 `backend/app/routers/contacts.py:349`・`:661`・`:697`）の両方に書く形。この機能だけの話ではない。
- 候補4（K20）: 会社・担当者をまとめる処理の試験は、サーバー・画面とも1本も無い（`git grep -l "/merge" origin/main -- backend/tests frontend/src` は見込み客の `backend/tests/test_lead_merge_pg.py` と窓の本体3つだけ）。画面の試験 `frontend/src/components/FullPageFormButtonMigration.test.tsx:172-205` は、担当者の編集画面で窓が開いて閉じられるところまでで、まとめる処理を流していない。

### 16-3. 変更（案と選んだ理由）

- 対象: 候補1・2・4。画面のコードと画面の試験だけ。サーバー・DB・辞書のキーは変えない。
- 対象外: 候補3（openapi の tags）。74本・十数の機能にまたがり、この機能のテーマから外れる（1リリース1テーマ）。画面にも数値にも影響しない（説明書の並びの重なりだけ）。台帳に別テーマとして置く。便4 の残りの隙（372本の全件ドライランが NOTICE を出さない・§15-4）も同じく別テーマ。
- (1) K18: `frontend/src/components/MergeCompanyModal.tsx:239` の `{c.status}` を `{customerStatuses.nameOf(c.status)}` にする。担当者の窓 `frontend/src/components/MergeContactModal.tsx:235` と同じ形。
- (2) K19: 権限の確かめ方は、場所ごとに既にある手本に合わせる（新しい見せ方を作らない）。
  - 重複確認待ちの欄のボタン（担当者の編集画面）: 会社の同じ欄 `frontend/src/pages/company-detail/CompanyBasicTab.tsx:142-152` に合わせ、押せなくして理由を `title` に出す。理由の文は既にある `companies.dedupMergeNoPermission` を使う（同じ文を2か所に持たない）。
  - 行のボタン・連絡手段の知らせのボタン: 一覧の消すボタンに合わせ、権限が無ければ出さない。
  - 権限の名前は会社と同じ customers.delete（サーバーの決まりと同じ）。
- (3) K20: 新しい画面の試験に、まとめる処理を最後まで流す1本と、権限の無い人の1本を書く（16-4 の理由で既存のファイルとは分ける）。会社の窓の名前の試験を1本足す。サーバーの試験は今回は足さない（サーバーの決まりは変えないため。足すなら別の便）。
- 採らない案:
  - 担当者の編集画面のボタンも出さない: 会社の同じ欄が「押せなくして理由を出す」なので、同じ種類の欄で見せ方が割れる。
  - 理由の文を contacts の下に新しく作る: 同じ文が2か所になる。

### 16-4. 機械の見張り

- K18: 新しい試験 `frontend/src/components/MergeCompanyModal.test.tsx` が、候補の状態の欄に「有効」が出て、`active` だけの欄が無いことを確かめる。`{c.status}` に戻すと落ちる。
- K19・K20: 新しい試験 `frontend/src/pages/contacts/ContactEditPageMerge.test.tsx` の2本（権限なし・まとめる流れ）と、新しい試験 `frontend/src/pages/company-detail/CompanyContactsTab.test.tsx` の2本。権限の確かめを消すと落ちる。まとめたあと移る先を変えると落ちる。まとめる2本を既存の `frontend/src/components/FullPageFormButtonMigration.test.tsx` に足さない理由: その `afterEach`（`:91-99`）が「POST が1回も呼ばれない」ことを確かめているため。既存のファイルには偽の GET に `/me/permissions` の1行だけ足す（足さないと知らない道で例外になり、`:172-205` のボタンが押せる試験が落ちる）。
- 同じ種類（状態の記号をそのまま画面の文字に出す）を探す grep は、§8 に無かった（K5 は記号の直書き、K7 は辞書の文を数える）ので見逃した。K18 の受入に grep を足す: `git grep -n -E '^[[:space:]]*\{[A-Za-z_]+\.status\}[[:space:]]*$|>\{[A-Za-z_]+\.status\}<' -- frontend/src/pages/contacts frontend/src/pages/companies frontend/src/pages/company-detail frontend/src/components/MergeCompanyModal.tsx frontend/src/components/MergeContactModal.tsx`。基準値（cee15756b で Opus が実測）: 1件（`frontend/src/components/MergeCompanyModal.tsx:239`）。変更後は0件。選ぶ欄の `value={form.status}` は当たらない。

### 16-5. 受入条件と確かめ方

| 基準 | 検証方法 |
|---|---|
| K18 会社の窓で状態が名前で出る | `frontend/src/components/MergeCompanyModal.test.tsx` が CI の画面の試験で緑。16-4 の grep が0件。デプロイ後、Chrome で会社の詳細→重複確認待ちの会社→まとめる窓で、状態の欄が「有効」等の名前（保存・まとめるはしない） |
| K19 権限の無い人にはボタンを押させない | `frontend/src/pages/contacts/ContactEditPageMerge.test.tsx` の権限なしの1本（ボタンが押せず title が `companies.dedupMergeNoPermission`）と、`frontend/src/pages/company-detail/CompanyContactsTab.test.tsx` の2本（canMerge が false なら行のボタンが無い・true ならある）が緑 |
| K20 まとめたあと窓が閉じて残した側の画面に移る | `frontend/src/pages/contacts/ContactEditPageMerge.test.tsx` のまとめる1本（`POST /contacts/53/merge` に `{loser_id: 52, reason: null}` を1回送る・窓が消える・場所が `/contacts/53/edit`）が緑 |
| 既存が壊れない | 画面の試験全体・型の確かめ・ESLint・UI governance gate・i18n のキー数（変わらない）が CI で緑 |

### 16-6. 弊害・戻し方・GO

- 弊害: customers.update はあるが customers.delete が無い人は、今まで押せた（押すとサーバーで失敗した）ボタンが押せない・見えなくなる。結果は変わらない（今も失敗する）。
- 戻し方: この便の commit を戻す PR。DB は変えない。
- GO: migrations・deploy.yml・本番 scripts を含まないので危険 PR ではない（ADR-136 の対象外）。画面の変更なので、CI 緑・審査役 APPROVE で Opus がマージする（ADR-1003 の委任）。
- 守る決まり: ADR-067（デザイントークン）・ADR-144（UI 金型）は、新しい色・大きさ・部品を足さず、既にある金型の Button と既にある文言キーだけを使うことで守る。ADR-135（main にマージ＝本番に出してよいという宣言）は、migrations・deploy.yml・本番 scripts を含まない画面だけの変更なので、CI 緑と審査役 APPROVE のあとで main にマージしてよい。
- 外部事例: 使わない。理由: 既にある当社の手本（会社の側の権限の確かめ方・担当者の窓の名前の出し方）に合わせるだけで、新しいやり方を選ばない。
- 実装カード: [card-bin5.md](card-bin5.md)。
- 審査: 1回目（2026-11-13 08:16 JST・クラウド Opus・46d234e09）**APPROVE**（必須0件）。§16-2 の行・カードの変更前の文字列が実物（origin/main 4892f2c6a、対象ファイルは cee15756b から差分0）と合う・CompanyContactsTab を使うのは CompanyDetailPage.tsx:158 だけ・試験の流れ（POST の形・ボタン名・ラジオ・Provider なし）が成り立つ・辞書の新しいキーは要らない・§16-4 の grep は1件、を確認。推奨3件を反映: (中) ボタンが押せるかは権限の取得を待ってから確かめる（カード手順6・7）／(低) カード手順6 の行を `:184`・`:209` に直した／(低) contacts.py の行を `:694-699` に直した。
