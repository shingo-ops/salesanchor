# 会社と連絡先の「状態」を1か所へ — 設計

> この文書は何か（専門用語なしの1行）:
> 会社と連絡先の「有効・無効・アーカイブ・重複確認待ち」を DB の1つの表にまとめ、画面の選択肢・札・まとめる画面の文・分析がすべてその表を読むようにする手順。

- 状態: **設計案作成済み（Opus）／設計審査 未／PO 承認 未／実装未着手**
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
  - 状態を選ぶフォームは7か所ある（recon §3）。そのうち連絡先を新しく作るフォーム2か所（連絡先一覧の「新規」・会社の連絡先タブの「追加」）だけ選択肢が3つで「重複確認待ち」が無い。残り5か所（会社の新規・会社の基本タブ・連絡先の編集など）は4つ。変更後は7か所すべて4つにそろう（審査2回目の指摘3。手で「重複確認待ち」を選べる所が2か所増える）。
  - 一覧の絞り込みの選択肢はもともと無い（審査2回目の指摘3で確認）。
  - まとめる画面の文から「master」「pending_dedup_review」「active」「audit_logs」が消える。
  - 名前の見た目は今と同じ（有効／無効／アーカイブ／重複確認待ち）。

## 2. 変更前と変更後

| 項目 | 変更前 | 変更後 |
|---|---|---|
| 4つの値 | DB の CHECK 10表＋会社を作る処理2か所＋サーバー列挙2か所＋画面8か所 | DB の表 `public.customer_statuses` の4行（正本）。会社・連絡先の status 列はこの表への外部キー |
| 名前 | 辞書 11キー（ja/en） | 表の name_ja・name_en。辞書の重複キーは消す |
| 色の種類 | statusPresentation.ts に2組 | 変えない（statusPresentation.ts の bucket・badgeVariant。名前の辞書キー labelKey だけ外す） |
| 画面の選択肢 | 7か所で自前に並べる（2か所は3つ） | 1つの読み口（hook）から4つ並べる |
| 分析 | 名前を引けない | 会社・連絡先の status を表と結んで名前・並び順が引ける |

## 3. 新しい表 `public.customer_statuses`（便1・migration・形だけ）

```sql
CREATE TABLE IF NOT EXISTS public.customer_statuses (
    code        VARCHAR(20) PRIMARY KEY,          -- 会社・連絡先の status に入る記号（変えない）
    name_ja     VARCHAR(50) NOT NULL,             -- 画面の日本語名
    name_en     VARCHAR(50) NOT NULL,             -- 画面の英語名
    sort_order  SMALLINT    NOT NULL UNIQUE,      -- 選択肢・集計の並び順
    is_active   BOOLEAN     NOT NULL DEFAULT TRUE,  -- FALSE＝新しく選べない（過去の行は残る）
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
- 同じ PR で `scripts/migration-guard/protected-tables.txt` に customer_statuses を足す。以後、migration がこの表に値を書くと `scripts/check-migration-value-writes.py` が止める（ADR-1007 決定5 を機械で守る）。
- ロールバック: 表を残してプログラムが使わない。

## 4. 4行の投入（1回だけのデータ変更・ADR-1007 決定1）

| code | name_ja | name_en | sort_order |
|---|---|---|---|
| active | 有効 | Active | 10 |
| inactive | 無効 | Inactive | 20 |
| archived | アーカイブ | Archived | 30 |
| pending_dedup_review | 重複確認待ち | Pending duplicate check | 40 |

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
- 止める条件は「どこかの会社の領域の companies・contacts に行が1つでもあり、かつ public.customer_statuses の行が4に足りない」に絞る（RAISE EXCEPTION）。行が0の空の DB（CI の全件ドライラン `.github/workflows/migration-test.yml:2118`）では止まらない。本番は105行あるので、4行の投入前に流すと止まる。
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
- API: `GET /api/customer-statuses` → 4行（code・name_ja・name_en・sort_order・is_active）。ログインした人なら誰でも読める。
- 会社をまとめる処理の `backend/app/routers/companies.py:982`（`SET status='active'`）と `:1019`（記録）も記号の定数を使う（審査2回目の指摘5）。
- `frontend/api-contract/openapi.json:5904`・`:7712` は、サーバーの列挙を残すので変わらない。新しい API の分だけ契約の書き出しを更新する。
- サーバーの列挙（`backend/app/schemas/company.py:33-37`・`backend/app/schemas/contact.py:26-36`）は残す。理由: 動きが記号に頼るため、記号はコードでも名前を持つ。代わりに §6-4 の試験で「列挙＝表の行」を毎回確かめる。受け取り時の正しさは DB の外部キーが最後に守る。

### 6-2. 画面の付け替え

- 読み口: 新しい hook（useCustomerStatuses）で API を1回読み、言語で name_ja/name_en を選ぶ。
- statusPresentation.ts の contact・company の組は bucket・badgeVariant を残し、labelKey（辞書キー）だけ外す。名前は hook から出す。`frontend/src/pages/design-preview/sections/StatusSection.tsx:40-85` は、この2組だけ hook の名前を使う（他の11組は今のまま）。
- recon §3 のフォーム7か所とまとめる画面1か所を、この読み口から並べる形に直す。連絡先を新しく作る2か所（`frontend/src/pages/contacts/ContactsPage.tsx:337` の createForm・`frontend/src/pages/company-detail/CompanyContactsTab.tsx:198` の contactForm）は、§9 未決4 の PO の答えに従う。
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
| K4 状態を選ぶフォーム7か所の選択肢が §9 未決4 の答えどおり | Chrome で 会社一覧の「新規」・会社の詳細の基本タブ・会社の連絡先タブの「追加」・連絡先一覧の「新規」・連絡先の編集・会社の新規フォーム（CompanyFormFields）・連絡先のフォーム（ContactFormFields）を開いて数える。名前と並びが §4 のとおり |
| K5 会社・連絡先の画面のコードに4つの記号の直書きが0件（定数ファイルを除く） | `git grep -n -E '"(active\|inactive\|archived\|pending_dedup_review)"' -- frontend/src/pages/contacts frontend/src/pages/companies frontend/src/pages/company-detail frontend/src/components/MergeCompanyModal.tsx frontend/src/components/MergeContactModal.tsx \| grep -v className` が0件。基準値（a88194893 で実測）: 10ファイル53件のうち tab の className の3件を除く50件 |
| K6 状態の名前の辞書キーが0件 | `git grep -n -E 'customers\.status_(active\|inactive\|archived\|pending_dedup)\|contacts\.statusCode\|statusPendingDedupOption' -- frontend/src` が0件。基準値（a88194893 で実測）: 41件（辞書を除くと39件） |
| K7 まとめる画面の文に master・pending_dedup_review・active・audit_logs が0件 | ja/en.json の mergeCompany・mergeContact を grep → 0件。Chrome で会社をまとめる画面を開き文を読む（実行はしない） |
| K8 分析で名前が引ける | 読み取りの鍵で companies と customer_statuses を結んだ件数の集計が名前付きで出る（tenant_004: 有効 51） |
| K9 試験 | CI 全部緑。列挙＝表の試験が緑 |
| K10 RLS の下で外部キーが働く | backend/tests/test_customer_statuses_pg.py が緑（会社の領域の利用者で会社を作れる・表に無い値は断られる） |
| K11 まとめる先がアーカイブのときの文に仕組みの言葉が0件 | `frontend/src/lib/apiErrorReason.test.ts` で merge_target_archived → 文に master・archived・active・merge_target が無い。`backend/tests/test_api_error_reason_sync.py` が緑 |
| K12 migration が新しい表に値を書くと止まる | `scripts/migration-guard/protected-tables.txt` に customer_statuses がある。`python3 scripts/check-migration-value-writes.py repo` が緑 |
| K13 便2 が CI の migration 検査を通る | 便2 の PR の Migration SQL Test が緑（変更 SQL・全件ドライラン・2周目の冪等） |

## 9. 未決（PO に1件ずつ）

1. 見込み客の状態（ADR-109・名前は辞書）も同じ形（名前も DB）に寄せるか。今回は対象外。別テーマとして後で聞く。
2. 他にも「名前が辞書にあり DB に無い」状態が13種ある（statusPresentation.ts の13ドメイン）。どこまで DB に移すかは別テーマ。
3. 会社の書き出し（CSV）の状態の列を、記号のままにするか名前にするか。今回は記号のまま（§6-3-3）。
4. 【実装前に PO に聞く】連絡先を新しく作る2か所（連絡先一覧の「新規」・会社の連絡先タブの「追加」）にも「重複確認待ち」を出すか。今は7か所中5か所で選べ、この2か所だけ選べない。決めた記録は無い（recon §3）。答えで §6-2 の並べ方が決まる（全部出す／作るときだけ出さない＝表に列を1つ足す／人の手では選べない）。

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

- 外部事例は使わない。理由: 同じリポジトリのチャネル名簿（docs/handoff/channel-master-shared/design.md）が、同じ形（public の名簿＋1回だけの投入＋付け替え）で本番反映まで済んでいる。数値の主張はしない。

## 13. 維持の仕組み

- DB の外部キーが、表に無い値を入れさせない（K3）。
- CI の試験が、サーバーの列挙と表の行のずれを止める（§6-4）。
- scripts/check-ui-governance.js が、画面への記号の直書きを止める（§6-4）。
- `scripts/check-migration-value-writes.py` と protected-tables.txt が、migration による表への値の書き込みを止める（K12）。
- 便2 の外部キーが、新しい会社の領域にも付く（`backend/app/services/tenant.py:224`・`:255` を外部キーに直す）。
- 状態を足すときの手順: データ変更で行を足す → 列挙に足す → 試験が緑、の順。この設計書に書き、ADR に残す。

## 14. 審査記録

- 1回目（2026-11-11 13:58 JST・クラウド Opus）: 判定なしで停止。原因は依頼文の確かめ方に見張りの止める語が入っていたこと（Opus の依頼の書き方の誤り）。途中の指摘6件（試験 DB が SQLite・recon の漏れ5か所・409 の文）は実物で確かめて recon §2・§3 と §5-2・§6-2・§6-3-2・§6-3-3・§8 K10/K11・§9-3 に反映した。
- 2回目（2026-11-11 14:14 JST・クラウド Opus・da68ab5af）: **REVISE**。指摘8件と直した所: (1) 便2 が CI で止まる → §5 の止める条件を絞り、§5-2 に前提の移行の step（K13） (2) VALIDATE は FORCE の下で読む決まりに絞られる（PG16 で実測）→ §3 に `USING (true)` (3) 「絞り込み」は実は作る・直すフォーム → §1・§6-2・K4 を直し、§9 未決4 で PO に聞く (4) statusPresentation.ts は同期の固定表 → 色は表に置かずコードに残す（§2・§3・§4・§11） (5) recon の漏れ → recon §2・§3 と §6-1・§6-2 (6) K5・K6 の grep の書き方の誤り → 書き直して基準値を実測（K5 50件・K6 41件） (7) 理由コードの形 → 共通の表 apiErrorReason.ts（§6-3-2） (8) ADR-1007 と値の書き込みの検査 → protected-tables.txt に足す（§3・K12）。8 の文の後半は記録の切れで読めず、検査の道具と一覧を Opus が実物で読んで補った（`scripts/check-migration-value-writes.py`・`scripts/migration-guard/protected-tables.txt`。customer_statuses は今は一覧に無い）。
