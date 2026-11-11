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
| ADR-120 | 状態 → 見た目の入口は statusPresentation.ts のまま。中身（名前・色の種類）を DB の行から作るように変える |
| ADR-109 | 見込み客の状態は対象外（§9 未決1）。今回は会社・連絡先だけ「名前も DB」とする新 ADR を立てる |
| ADR-027 | 画面の固定の文は t() のまま。状態の名前だけは DB の日英2列から言語で選ぶ（前例: チャネル名簿の display_name） |
| ADR-1007 決定1 | 表を作る migration に行は書かない。4行は1回だけのデータ変更で入れる |
| ADR-1008 | 会社ごとの表から public の表への外部キーの前例 |
| ADR-145 | public の表の守り（RLS の ENABLE と FORCE）の写し方 |
| ADR-1037 | 入れ替え時のロック待ち1秒 |
| docs/handoff/channel-master-shared/design.md | 作る便 → 行を入れる → 付け替え、の3段の型 |

## 1. 目的と成功条件

- 目的: 4つの状態の「記号・日本語名・英語名・並び順・色の種類」を DB の1つの表だけに置く。画面とサーバーと分析は、その表を読む。同じ値を別の場所に書かない。
- 利用者に見える変化:
  - 会社一覧の絞り込み・連絡先一覧の絞り込み・会社の連絡先タブで、選択肢が4つそろう（今は2か所が3つだけ）。
  - まとめる画面の文から「master」「pending_dedup_review」「active」「audit_logs」が消える。
  - 名前の見た目は今と同じ（有効／無効／アーカイブ／重複確認待ち）。

## 2. 変更前と変更後

| 項目 | 変更前 | 変更後 |
|---|---|---|
| 4つの値 | DB の CHECK 10表＋会社を作る処理2か所＋サーバー列挙2か所＋画面8か所 | DB の表 `public.customer_statuses` の4行（正本）。会社・連絡先の status 列はこの表への外部キー |
| 名前 | 辞書 11キー（ja/en） | 表の name_ja・name_en。辞書の重複キーは消す |
| 色の種類 | statusPresentation.ts に2組 | 表の bucket 列（success/warning/neutral など ADR-120 の5種から選ぶ） |
| 画面の選択肢 | 8か所で自前に並べる | 1つの読み口（hook）から並べる |
| 分析 | 名前を引けない | 会社・連絡先の status を表と結んで名前・並び順が引ける |

## 3. 新しい表 `public.customer_statuses`（便1・migration・形だけ）

```sql
CREATE TABLE IF NOT EXISTS public.customer_statuses (
    code        VARCHAR(20) PRIMARY KEY,          -- 会社・連絡先の status に入る記号（変えない）
    name_ja     VARCHAR(50) NOT NULL,             -- 画面の日本語名
    name_en     VARCHAR(50) NOT NULL,             -- 画面の英語名
    sort_order  SMALLINT    NOT NULL UNIQUE,      -- 選択肢・集計の並び順
    bucket      VARCHAR(10) NOT NULL CHECK (bucket IN ('success','danger','warning','info','neutral')),
    is_active   BOOLEAN     NOT NULL DEFAULT TRUE,  -- FALSE＝新しく選べない（過去の行は残る）
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

- 会社と連絡先で1つの表にする。理由: 今の4つの値と名前が両方で同じ（`backend/app/services/tenant.py:224`・`:255` の CHECK が同一、名前も同一）。片方だけに足す日が来たら、その時に別設計（§8 弊害4）。
- 会社ごとの独自の状態は持たない（tenant_id 列なし）。理由: サーバーの動きが記号に頼る（`backend/app/routers/companies.py:765`・`:978-985`）。会社が独自に足すと動きが決まらない。
- RLS: 読む＝誰でも。書く＝運営だけ（`current_setting('app.is_operator', true) = 'true'`）。ENABLE と FORCE。`migrations/20261106_190000_create_public_channel_masters.sql` の守りを写す。
- 消す操作は受けない（外部キーで止まる）。取り下げは is_active=FALSE。
- 行を入れる文は書かない（ADR-1007）。この便では作るだけで、どこからも読まれない。
- ロールバック: 表を残してプログラムが使わない。

## 4. 4行の投入（1回だけのデータ変更・ADR-1007 決定1）

| code | name_ja | name_en | sort_order | bucket |
|---|---|---|---|---|
| active | 有効 | Active | 10 | success |
| inactive | 無効 | Inactive | 20 | neutral |
| archived | アーカイブ | Archived | 30 | neutral |
| pending_dedup_review | 重複確認待ち | Pending duplicate check | 40 | warning |

- 日本語名は今の ja.json の値（`frontend/src/locales/ja.json:1133-1135`・`:1299`）をそのまま写す。英語名の3つは今の en.json（`frontend/src/locales/en.json:1133-1135`）と同じ。重複確認待ちだけ、今の英語「Pending Dedup Review」（`frontend/src/locales/en.json:1161`）は仕組みの略語（Dedup）を含むため「Pending duplicate check」に直す（英語画面だけ見た目が変わる）。
- bucket は今の `frontend/src/utils/statusPresentation.ts:164-176` と同じ。
- 手順: SQL ファイルを docs/handoff/status-ssot-contact-company/ に置く → DRY-RUN（ROLLBACK）で4行と出るのを確かめる → PO の `!` で COMMIT（`SET LOCAL app.is_operator='true'`）→ 読み取りの鍵で4行を確かめる。

## 5. 会社・連絡先の列を表に結ぶ（便2・migration）

- 全会社の領域（tenant_*）の companies・contacts で:
  1. `ADD CONSTRAINT ..._status_fkey FOREIGN KEY (status) REFERENCES public.customer_statuses(code) NOT VALID`
  2. `VALIDATE CONSTRAINT`（本番は合計105行・§recon 1）
  3. 旧 CHECK（companies_status_check / contacts_status_check）を DROP
- 便2 は「4行が本番に入っている」ことを冒頭で確かめ、無ければ止まる（RAISE EXCEPTION）。
- 会社を作る処理 `backend/app/services/tenant.py:224`・`:255` も CHECK → 外部キーに直す（同じ PR）。
- ロック待ち1秒（ADR-1037）。
- ロールバック: 外部キーを DROP し CHECK を付け直す SQL を design に添える（カードに書く）。

## 6. 読み書きの付け替え（便3・アプリのコード）

### 6-1. サーバーの読み口1か所

- 新しいファイル backend/app/services/customer_statuses.py に表名の定数と読む SQL を置く（チャネル名簿の `backend/app/services/channel_masters.py:1-13` と同じ型）。
- API: `GET /api/customer-statuses` → 4行（code・name_ja・name_en・sort_order・bucket・is_active）。ログインした人なら誰でも読める。
- サーバーの列挙（`backend/app/schemas/company.py:33-37`・`backend/app/schemas/contact.py:26-36`）は残す。理由: 動きが記号に頼るため、記号はコードでも名前を持つ。代わりに §6-4 の試験で「列挙＝表の行」を毎回確かめる。受け取り時の正しさは DB の外部キーが最後に守る。

### 6-2. 画面の付け替え

- 読み口: 新しい hook（useCustomerStatuses）で API を1回読み、言語で name_ja/name_en を選ぶ。
- statusPresentation.ts の contact・company の組は、表の bucket から作る形に変える（入口は ADR-120 のまま）。
- recon §3 の8か所を、この読み口から並べる形に直す。絞り込みの2か所（ContactsPage・CompanyContactsTab）は4つになる。
- 値の直書き（recon §3 の比較・初期値）: 動きに関わる比較（まとめる時の pending 判定など）は記号の定数1か所（新しいファイルに CUSTOMER_STATUS_CODES）にまとめ、各所はそれを使う。
- 色の CSS `frontend/src/components.css:271` は bucket の共通クラスを使う形にし、記号名のクラスは消す。`frontend/src/pages/design-system/DesignSystemPage.tsx:191` も合わせる。
- 辞書から消すキー: customers.status_active/inactive/archived/pending_dedup・contacts.statusPendingDedupOption・contacts.statusCode.*（ja/en 両方）。ただし他の画面が同じキーを使っていれば残す（カードで `git grep` して0件を確かめてから消す）。ja.json の 1475・1922・2114 行の status_active は別の画面のキーなので触らない。

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

### 6-4. 試験と見張り

- サーバーの試験: 試験 DB に4行を用意し、CompanyStatus・ContactStatus の値の集合＝表の code の集合を確かめる。§4 の SQL ファイルの値とも一致を確かめる。
- 画面の試験: statusPresentation.test.ts を表の行から作る形に直す。
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
| K4 画面の状態の選択肢が4つ（6か所すべて） | Chrome で会社一覧の絞り込み・会社の新規・会社の基本タブ・連絡先一覧の絞り込み・連絡先の編集・会社の連絡先タブを開いて数える |
| K5 4つの記号を画面のコードに直書きした所が定数ファイル以外0件 | `git grep -n -E "\"(inactive\|archived\|pending_dedup_review)\"" -- frontend/src ':!*locales*'` の結果が定数ファイルだけ |
| K6 状態の名前の辞書キーが0件 | `git grep -n -E "customers\.status_(active\|inactive\|archived\|pending_dedup)\|contacts\.statusCode\|statusPendingDedupOption" -- frontend/src` が0件 |
| K7 まとめる画面の文に master・pending_dedup_review・active・audit_logs が0件 | ja/en.json の mergeCompany・mergeContact を grep → 0件。Chrome で会社をまとめる画面を開き文を読む（実行はしない） |
| K8 分析で名前が引ける | 読み取りの鍵で companies と customer_statuses を結んだ件数の集計が名前付きで出る（tenant_004: 有効 51） |
| K9 試験 | CI 全部緑。列挙＝表の試験が緑 |

## 9. 未決（PO に1件ずつ）

1. 見込み客の状態（ADR-109・名前は辞書）も同じ形（名前も DB）に寄せるか。今回は対象外。別テーマとして後で聞く。
2. 他にも「名前が辞書にあり DB に無い」状態が13種ある（statusPresentation.ts の13ドメイン）。どこまで DB に移すかは別テーマ。

## 10. 弊害と対処

1. 画面が API を読むまで選択肢が空になる → hook が読み込み中を返し、選択肢は読み込み後に出す。失敗時は失敗の文（ADR-1071 の形）。
2. 試験 DB に4行が無いと会社・連絡先を作る試験が落ちる → 試験の準備で4行を入れる（ADR-1007 の「試験の側でデータを用意」）。
3. 新しい会社を作るとき、public の表に4行が無いと作れない → 本番は4行が入っている。開発の手元環境はデータ変更の SQL を流す手順を README に書く。
4. 会社だけ・連絡先だけの状態が必要になった時、1つの表では足りない → その時に applies_to 列を足す別設計。今は両方同じ（recon §1）。
5. 英語名を DB に置くと翻訳の置き場が2つになる → 状態の名前は DB だけ・固定の文は辞書だけ、と新 ADR で線を引く。

## 11. 新しい ADR（便1 の PR で起票）

- 題: 会社と連絡先の状態は public.customer_statuses を正本にする
- 決定: 記号・日英名・並び順・色の種類は表の行。会社・連絡先の status 列は外部キー。画面は API から読む。サーバーの列挙は試験で表と一致を確かめる。
- ADR-109 との関係: 見込み客は変えない（PO 判断待ち）。ADR-120 との関係: 入口は同じ・中身の出所が DB になる。

## 12. 外部・過去事例の参照と我々への応用

- 外部事例は使わない。理由: 同じリポジトリのチャネル名簿（docs/handoff/channel-master-shared/design.md）が、同じ形（public の名簿＋1回だけの投入＋付け替え）で本番反映まで済んでいる。数値の主張はしない。

## 13. 維持の仕組み

- DB の外部キーが、表に無い値を入れさせない（K3）。
- CI の試験が、サーバーの列挙と表の行のずれを止める（§6-4）。
- scripts/check-ui-governance.js が、画面への記号の直書きを止める（§6-4）。
- 状態を足すときの手順: データ変更で行を足す → 列挙に足す → 試験が緑、の順。この設計書に書き、ADR に残す。

## 14. 審査記録

- （未）
