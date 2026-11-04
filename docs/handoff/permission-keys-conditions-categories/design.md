# design: 状態マスタ・商品カテゴリの権限キーを権限の一覧に足す

この文書は、所有者も開けなかった「状態マスタ」と「商品カテゴリ」の画面を、権限どおりに開けるようにする設計です。

- 親（仕様書）: [../../specs/auth-roles/README.md](../../specs/auth-roles/README.md)
- 調査: [recon.md](recon.md)
- データ変更の手順: [data-change-1/README.md](data-change-1/README.md)
- 状態: 設計案作成済み（2026-11-04）。設計審査・PO 承認・実装はまだ。

## 1. 目的と KGI

### 1-1. PO の言葉
- 2026-11-04 チャット「1」。選んだ選択肢は「2つの鍵を権限の一覧に足す設計を作る【おすすめ】」。
- 前の問い（点検用の役割に 3 画面の閲覧権限を足す）に「1」。
- 常設の条件: 推測禁止・事実確認・配線と DB の SSOT 遵守・データ分散禁止・テナント 001 を試しに使う。

### 1-2. 利用者に見える変化
- 変更前: どの会社の所有者が管理センターを開いても、「状態マスタ」と「商品カテゴリ」がメニューに出ない。URL を直接開いても一覧は 403 になる（recon.md §2・§3）。
- 変更後:
  - 所有者・管理者のメニューに 2 つが出て、一覧・登録・編集・削除・CSV 取り込みができる。
  - ほかの役割は、権限の画面で「状態マスタ」「商品カテゴリ」の欄にチェックを付けた分だけ使える。
  - 点検用（見るだけ）の役割は 2 画面を見るだけで、書き込みはできない。

### 1-3. KGI（○× で判定）
| # | 条件 | 検証方法 |
|---|---|---|
| K1 | 本番の権限の一覧が 130 件になり、§4-2 の 7 キーが category「状態マスタ」「商品カテゴリ」で入っている | data-change-1/02_verify_read.sql を読み取りの道で流す（K1_TOTAL=130・K1_NEW_COUNT=7） |
| K2 | テナント 001 の所有者で管理センターを開くと「状態マスタ」と「商品カテゴリ」がメニューに出る。両方の一覧が開け、通信が 200 になる（`/api/v1/conditions`・`/api/v1/conditions/catalog`・`/api/v1/product-categories`） | Chrome で画面を開き、画面の写しと通信の記録を取る（Opus） |
| K3 | 点検用（見るだけ）の役割は、状態マスタ・商品カテゴリの一覧を開ける。CSV 取り込みのボタンは出ず、取り込みの確定 API は 403 になる | 試験（§6 の T1〜T4）と、本線の画面点検（prod-ui-check）の速さの表で 2 画面が 403 なしで測れること |
| K4 | 状態マスタの CSV 取り込み（下見・確定）は、登録と編集の両方の権限を持つ人だけが使える | 試験 T1・T2 |
| K5 | 権限の一覧に無いキーをコードが求めたら、30 分以内に Discord の運用の通知に出る（便2） | 警報の試験（promtool）と、本番の /metrics の値が 0 であること |

KGI の数値と ○× は、PO の承認前の草案です。

## 2. 対象と対象外

### 対象
- 便1-コード: 状態マスタの CSV 取り込みの穴を塞ぐ（recon.md §4）。共用の状態一覧（catalog）の鍵を conditions.view に付け替える。
- 便1-データ: 権限の一覧に 7 キーを足す（ADR-1007:36 の 1 回だけのデータ変更）。
- 便1-画面操作: テナント 001 の点検用の役割に conditions.view・product_categories.view を付ける（アプリの権限の画面から。ADR-1007 のアプリの画面の道）。
- 便2: 権限の一覧に無いキーをコードが求めていたら知らせる見張り。

### 対象外（理由）
- companies.view・customers.edit・leads.edit の 3 キー
  - 既にある別のキー（customers.view・customers.update・leads.update）へ付け替えると、誰が使えるようになるかが変わる。PO の判断が要る。
  - 便2 の見張りでは「既知の欠け」として名前を残し、件数は増やさない（§5-3）。
  - work_items.view は §4-1 で付け替えるので、残りはこの 3 キー。
- 点検用の役割が持つ書き込みの権限 20 件（recon.md §6）。これは別件として PO に聞く。
- 権限の一覧の正本を DB とコードのどちらに置くか（ADR-1007:73 の別の ADR）。本設計は今どおり DB を正とし、コードの写しを作らない。
- 権限の画面の category 見出しの翻訳。今の 26 の category はすべて DB の日本語をそのまま出している（RolesPage.tsx:384）。今回の 2 つも同じ扱いにする。
- 画面の見た目・部品は変えない（ボタンを出す条件だけを変える）。

## 3. 代替案と選択理由
| 案 | 中身 | 採否 | 理由 |
|---|---|---|---|
| A | コードのキーに合わせて、権限の一覧に 7 行足す | 採用 | 画面・API・試験がすでにこのキーで書かれている（recon.md §3）。足すだけで所有者・管理者に届く（ADR-1007:48-51）。DB を正とする今の形を変えない |
| B | コードを既にあるキー（products.view など）へ付け替える | 不採用 | 状態マスタ・商品カテゴリの権限を商品の権限と分けて付けられなくなる。権限の画面に「状態マスタ」の欄が無いままになる |
| C | migration で足す | 不採用 | ADR-1007・ADR-155 で禁止。migration-guard の保護表に permissions が入っている（recon.md §1） |
| D | アプリに権限の一覧の書き込み画面を作る | 不採用 | 7 行のために新しい書き手を作ることになり、範囲が大きすぎる。運用者だけが一度だけ書く今の手順で足りる |

## 4. 便1（変更前後）

### 4-1. 便1-コード（クラウドの Sonnet が実装・1 PR）
変更するファイルは 4 つ、試験ファイルは 1 つ新しく作る。

(1) `backend/app/auth/dependencies.py` require_permission（:646-672）
- 変更前: checker は求めるキーを外から読めない。
- 変更後: `return checker` の前に `checker.required_permission_keys = frozenset(required)  # type: ignore[attr-defined]` を 1 行足す。判定の中身は変えない。
- 理由: 試験（§6）と便2 の見張りが、どの経路がどのキーを求めるかを、文字列を探さずに読むため。

(2) `backend/app/routers/conditions.py`
| 行 | 経路 | 変更前 | 変更後 |
|---|---|---|---|
| :163 | GET /conditions/catalog | `require_permission("work_items.view")` | `require_permission("conditions.view")` |
| :414 | POST /conditions/import/preview | `dependencies=[Depends(require_permission("conditions.view"))]` | `dependencies=[Depends(require_permission("conditions.create")), Depends(require_permission("conditions.update"))]` |
| :452 | POST /conditions/import/commit | 同上 | 同上 |
- 取り込みは新しい行の登録と既存の行の上書きをする（:487-511 付近）。そのため、登録と編集の両方を求める。dependencies に 2 つ並べると、両方を満たさないと通らない。
- 一覧（:130）・1 件（:186）・CSV 出力（:371）・別名の一覧（:522）は conditions.view のまま。
- catalog は、共用の状態の行（tenant_id IS NULL）を読むだけ（:160-180）。呼ぶのは状態マスタの画面だけ（ConditionsPage.tsx:150）。

(3) `frontend/src/pages/conditions/ConditionImportPage.tsx:130`
- 変更前: `const canImport = hasPermission("conditions.view");`
- 変更後: `const canImport = hasPermission("conditions.create") && hasPermission("conditions.update");`

(4) `frontend/src/pages/conditions/ConditionsPage.tsx:374-376`（取り込みボタン）
- 変更前: conditions.view の枝の中で、条件なしに出している。
- 変更後: `{hasPermission("conditions.create") && hasPermission("conditions.update") && ( ... )}` で包む。ボタンの部品・文言・data-testid は変えない。
- CSV 出力ボタン（:371-373）は conditions.view のまま出す。

触らない範囲:
- product_categories.py と商品カテゴリの画面。取り込みは既に edit で守られている。
- ManagementCenterPage.tsx（メニューは view キーで出し分け済み）。
- 権限の判定の中身（load_user_permissions・compute_permission_keys）。
- 翻訳ファイル・CSS・部品。

### 4-2. 便1-データ（Opus が流す・PO の使い捨て許可のもと）
足す 7 行（data-change-1/01_apply.sql）:
| key | resource | action | description | category |
|---|---|---|---|---|
| conditions.view | conditions | view | 状態マスタの閲覧 | 状態マスタ |
| conditions.create | conditions | create | 状態マスタの登録 | 状態マスタ |
| conditions.update | conditions | update | 状態マスタの編集 | 状態マスタ |
| conditions.delete | conditions | delete | 状態マスタの削除 | 状態マスタ |
| product_categories.view | product_categories | view | 商品カテゴリの閲覧 | 商品カテゴリ |
| product_categories.edit | product_categories | edit | 商品カテゴリの登録・編集・CSV取り込み | 商品カテゴリ |
| product_categories.delete | product_categories | delete | 商品カテゴリの削除 | 商品カテゴリ |
- category の名前は、メニューの名前（ja.json:300「状態マスタ」、:301「商品カテゴリ」）に合わせた。
- description の書き方は既存の行に合わせた（products.view「商品一覧の閲覧」）。
- display_name_jp・permission_group・display_order は空にする。menu.* 以外の 104 行と同じ扱い。
- 手順・想定件数・戻し方は data-change-1/README.md。DRY-RUN（ROLLBACK）→ 本実行 → 事後確認の順。

### 4-3. 便1-画面操作（Opus が Chrome で行う）
- テナント 001 の役割「点検用（見るだけ）」に、権限の画面から 2 つのチェックを付ける。
  - 状態マスタの欄: 「状態マスタの閲覧」
  - 商品カテゴリの欄: 「商品カテゴリの閲覧」
- 前例: D2（2026-10-31）で同じ役割に products.view などを画面から足した。
- 付けたあと、読み取りの道で `tenant_001__role_permissions` を数え、45 → 47 になったことを確かめる。

### 4-4. 順番（1 つずつ、測ってから次へ）
1. 便1-コードをマージし、本番に反映する。
   - 反映の確認: 本番で `/api/v1/conditions/import/commit` の求めるキーが変わったこと。キーがまだ無いので、所有者でも今と同じく 403 になる。今の見え方は変わらない。
2. 便1-データの DRY-RUN → 本実行 → 事後確認（K1）。
3. 300 秒待つ（権限のキャッシュ。backend/app/cache.py:18）。そのあと K2 を見る。
4. 便1-画面操作 → K3 の確認。翌朝の本線の画面点検で、2 画面が 403 なしで測れたかを見る。
5. 便2。

コードより先にデータを入れると、点検用の役割に閲覧を付けた時点で CSV 取り込みが通ってしまう。だから 1 と 2 の順番は逆にしない。

## 5. 便2（見張り）

### 5-1. 何を見張るか
コードが require_permission で求めるキーのうち、権限の一覧に無いもの。今回の不具合は、キーを使うコードが入ってから 6 週間、誰も気づかなかった（recon.md §3、2026-09-20 → 2026-11-03）。

### 5-2. 仕組み
DB を正とし、コードに一覧の写しを作らない。

(1) `backend/app/auth/dependencies.py`
- 新しい集合を置く: `REGISTERED_PERMISSION_KEYS: set[str] = set()`。
- require_permission が呼ばれるたびに `REGISTERED_PERMISSION_KEYS.update(required)` を足す。
- 経路はアプリの起動で全部読み込まれる。そのため、起動のあとは全部の経路のキーがそろう。

(2) 新しいファイル `backend/app/auth/permission_catalog.py`
- `KNOWN_MISSING: dict[str, str]` を置く。キーと、残す理由・PO 判断待ちの印を並べる。
  - 最初の 3 件: companies.view・customers.edit・leads.edit。
- `async def count_missing_permission_keys(db) -> list[str]` を置く。
  - `SELECT key FROM public.permissions` を読む。
  - `sorted(REGISTERED_PERMISSION_KEYS - 一覧 - KNOWN_MISSING)` を返す。

(3) `backend/app/metrics.py`
- Gauge を足す: `salesanchor_permission_keys_missing`。説明は「コードが求めるのに権限の一覧に無いキーの数」。
- /metrics を読んだときに更新する。DB を読むのは最大 300 秒に 1 回。結果はプロセスの中に置く。
- DB が読めないときは -1 を入れる。0 にはしない（「欠け無し」と取り違えないため）。
- DB の接続は `backend/app/database.py:36` の AsyncSessionLocal を使う。
- 既存の _update_viewer_inventory_gauges と同じ形にする。

(4) `monitoring/prometheus/alert_rules.yml`
- 規則を足す: `PermissionKeyMissing`。式は `salesanchor_permission_keys_missing{job="backend"} > 0`、for 10m、severity warning、tier ticket。
- 規則を足す: `PermissionKeyCheckFailed`。式は `== -1`、for 30m。
- runbook の書き先は `docs/runbooks/alerts.md` に 2 節を足す。中身は「欠けたキーをログで確かめ、data-change の手順で足すか、コードを直す」。
- 通知は alertmanager の既定の宛先（Discord）に届く。

(5) `monitoring/prometheus/tests/alert_rules_test.yml`
- 試験を足す: 値が 1 のとき 10 分で発火すること。0 のときは発火しないこと。-1 のとき 30 分で別の警報になること。

(6) ログ
- 欠けがあるとき、更新のたびに 1 回 warning を出す。中身は欠けたキーの名前の一覧（秘密は含まない）。

### 5-3. 既知の欠けの扱い（ラチェット）
- 試験 `backend/tests/test_permission_catalog.py` で次を確かめる。
  - KNOWN_MISSING の各キーが REGISTERED_PERMISSION_KEYS に入っていること。使われなくなったら名前を消させるため。
  - KNOWN_MISSING の件数が 3 以下であること。増やすには、この試験の数字を変える PR が要る。
- PO が 3 キーの扱いを決めたら、付け替えまたは一覧への追加をする。その PR で KNOWN_MISSING から消し、上限の数字を下げる。

### 5-4. 見張れない範囲（正直に書く）
- 画面側の hasPermission("...") のキー。今回の 2 画面は API と同じキーを使っているので、API 側の見張りで捕まる。画面だけで使うキー（menu.* など）は見張らない。
- require_permission を通らず、キーの文字列を直接比べている場所。例: calendar.py・inventory_aggregated.py・inventory_search.py の load_user_permissions 呼び出し（migration-hygiene/recon.md §5.2）。
- この 2 つを見張るかどうかは、便2 のあとに件数を数えてから決める。

## 6. 試験（便1）
新しいファイル `backend/tests/test_conditions_permission_keys.py`。DB は使わない。

- T1: アプリの経路から POST /api/v1/conditions/import/commit を探す。
  - その dependencies の checker の required_permission_keys が {conditions.create} と {conditions.update} の 2 つであること。
- T2: /conditions/import/preview も同じであること。
- T3: GET /api/v1/conditions/catalog の求めるキーが {conditions.view} であること。
- T4: conditions・product-categories のすべての経路で、求めるキーが §4-2 の 7 キーのどれかであること。
  - 将来、一覧に無いキーを書いたら試験で止める。便2 の前の簡易版。
- 画面側: 既存の vitest の書き方に合わせる。ConditionImportPage で、conditions.view だけを持つ利用者に取り込みパネルが出ないことを確かめる。
  - 試験ファイルの置き場所は、実装のときに既存の `*.test.tsx` の並びに合わせる。

試験は GitHub の CI で回す。Mac では重い試験を回さない（PO 2026-11-02）。

## 7. リスクと対処
| リスク | 対処 |
|---|---|
| 5 社の所有者・管理者に、新しいメニューが突然出る（HIGH LIFE JPN を含む） | もともとこの 2 画面は、所有者が使う前提で作られている（2026-09-20 の追加）。PO への説明で「出るようになる会社」を明記して承認を取る |
| データを先に入れると、閲覧だけで CSV 取り込みが通る | 順番を §4-4 で固定する。DRY-RUN の前提にコードの反映を書いた（data-change-1/README.md） |
| 権限の画面で category の見出しが日本語のまま出る（英語の画面でも） | 既存の 26 の category と同じ。翻訳は対象外とした（§2） |
| DRY-RUN で id の連番が進む | 害は無い。前例（product-packaging）と同じ |
| 便2 の見張りが DB を読みすぎる | 最大 300 秒に 1 回、130 行だけ読む |
| 便2 の見張りで、すぐ 3 件が警報になる | KNOWN_MISSING で除く（§5-3） |

## 8. 外部事例
- 一般的な RBAC の実装（例: Django の権限、Spring Security の authority）は、コードが参照する権限名と、保存された権限の定義がずれると、黙って拒否になる。
- 起動時またはテストで突き合わせるのが通例である。ただし本件に当てはまる数値の事例は、まだ確かめていない。
- 本設計の見張りは、この「突き合わせ」を本番の DB に向けて行う形にした。
- 事例の数値は設計の成功の根拠にしない。根拠は recon.md の実測（11 件の欠け・6 週間気づかなかった）。

## 9. 計画票
| 便 | 中身 | 担当 | 前提 | 完了の印 |
|---|---|---|---|---|
| 便1-コード | §4-1・§6 | クラウドの Sonnet | 設計審査 APPROVE・PO の実装承認・実装カード | CI 緑・審査役 APPROVE・本番反映 |
| 便1-データ | §4-2 | Opus | 便1-コードの本番反映・PO の本実行の合意・使い捨て許可 2 回 | K1 |
| 便1-画面操作 | §4-3 | Opus（Chrome） | 便1-データ・300 秒待ち | K2・K3 |
| 便2 | §5 | クラウドの Sonnet | 便1 の完了・PO の実装承認 | K5 |

## 10. 設計審査（自己審査・2026-11-04）
同じ AI による自己審査で、独立した第二者のレビューではない。クラウドの審査は別に回す。

- 判定: REVISE 無し・APPROVE（設計合格）。ただし PO 承認と実装承認はまだ。
- 確かめたこと:
  - ADR-1007 の値の変更の道（:36）に合っている。migration を使っていない。
  - DB を正とし、コードに一覧の写しを作らない。便2 の KNOWN_MISSING は「欠けの許可」であって、一覧の写しではない。
  - 変更前後の行番号は cb9525b9d の実物で確かめた。
  - 本番の基準値（123・0・0・17859）は読み取りの道で実測した。
  - 受入の K1〜K5 は、それぞれ検証方法と紐づいている。
- 未解決（PO に戻すもの）:
  - 5 社の所有者・管理者に 2 つのメニューが出ること。
  - 3 キー（companies.view・customers.edit・leads.edit）の扱い。

## 維持の仕組み
- 守り手:
  - 便1 は `backend/tests/test_conditions_permission_keys.py`（CI の pytest）。
  - 便2 は `monitoring/prometheus/alert_rules.yml` の PermissionKeyMissing と `backend/tests/test_permission_catalog.py`。
  - いずれも実装の PR で作る。この設計の PR の時点では、まだ無い。
- 対象: 状態マスタの CSV 取り込みが閲覧だけで通らないこと。コードが求める権限キーが、権限の一覧にそろっていること。
- 関所ができるまで: 人手で守る。理由は、守り手のファイルが便1・便2 の実装で初めてできるため。
