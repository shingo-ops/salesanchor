# design: 状態マスタ・商品カテゴリの権限キーを権限の一覧に足す

この文書は、所有者も開けなかった「状態マスタ」と「商品カテゴリ」の画面を、権限どおりに開けるようにする設計です。

- 親（仕様書）: [../../specs/auth-roles/README.md](../../specs/auth-roles/README.md)
- 調査: [docs/handoff/permission-keys-conditions-categories/recon.md](recon.md)
- データ変更の手順: [data-change-1/README.md](data-change-1/README.md)
- 設計審査の記録: [review-opus.md](review-opus.md)
- 状態: 設計案作成済み・設計審査済み（2026-11-04、クラウドの審査 3 回目で APPROVE）・PO 実装承認済み（2026-11-04 チャット「1」）。便1-コードは実装カード [card-impl-1.md](card-impl-1.md) でクラウドの Sonnet に渡す。便3（§11）は 2026-11-04 PO「1」で承認、実装カード [card-impl-3.md](card-impl-3.md)。データ変更の本実行は、その都度 PO の使い捨て許可が要る。

## 1. 目的と KGI

### 1-1. PO の言葉
- 2026-11-04 チャット「1」。選んだ選択肢は「2つの鍵を権限の一覧に足す設計を作る【おすすめ】」。
- 前の問い（点検用の役割に 3 画面の閲覧権限を足す）に「1」。
- 2026-11-04 チャット「1」。選んだ選択肢は「作る作業に進む【おすすめ】」（実装の承認）。
- 常設の条件: 推測禁止・事実確認・配線と DB の SSOT 遵守・データ分散禁止・テナント 001 を試しに使う。

### 1-2. 利用者に見える変化
- 変更前: どの会社の所有者が管理センターを開いても、「状態マスタ」と「商品カテゴリ」がメニューに出ない。URL を直接開いても一覧は 403 になる（recon.md §2・§3）。
- 変更後:
  - 所有者・管理者のメニューに 2 つが出て、一覧・登録・編集・削除・CSV 取り込みができる。
  - ほかの役割は、権限の画面で「状態マスタ」「商品カテゴリ」の欄にチェックを付けた分だけ使える。
  - 点検用（見るだけ）の役割は 2 画面を見るだけで、書き込みはできない。

### 1-3. KGI（○× で判定）
| # | 基準 | 検証方法 |
|---|---|---|
| K1 | 本番の権限の一覧が 130 件になり、§4-2 の 7 キーが category「状態マスタ」「商品カテゴリ」で入っている | data-change-1/02_verify_read.sql を読み取りの道で流す（K1_TOTAL=130・K1_NEW_COUNT=7） |
| K2 | テナント 001 の所有者で管理センターを開くと「状態マスタ」と「商品カテゴリ」がメニューに出る。両方の一覧が開け、通信が 200 になる（`/api/v1/conditions`・`/api/v1/conditions/catalog`・`/api/v1/product-categories`） | Chrome で画面を開き、画面の写しと通信の記録を取る（Opus） |
| K3 | 点検用（見るだけ）の役割は、状態マスタ・商品カテゴリの一覧を開ける。CSV 取り込みのボタンは出ず、取り込みの確定 API は 403 になる | 試験（§6 の T1〜T7）と、本線の画面点検（prod-ui-check）の速さの表で 2 画面が 403 なしで測れること |
| K4 | 状態マスタの CSV 取り込み（下見・確定）は、登録・編集・削除の 3 つ全部の権限を持つ人だけが使える | 試験 T1・T2・T5・T6・T7 |
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
- 1 件の編集（PATCH /conditions/{id}・conditions.update）で is_active を FALSE にできること。
  - 実物: 編集できる項目の集合 `_UPDATABLE`（conditions.py:120-124）に is_active が入っている。受け取りの型も is_active を持つ（backend/app/schemas/condition.py:35）。
  - つまり今も、編集の権限だけで 1 件ずつなら論理削除と同じことができる。取り込みだけの穴ではない。
  - 編集から is_active を外すと、今その操作をしている人の使い方が変わる。PO の判断が要るので、本設計では変えず、PO に別件として聞く。

## 3. 代替案と選択理由
| 案 | 中身 | 採否 | 理由 |
|---|---|---|---|
| A | コードのキーに合わせて、権限の一覧に 7 行足す | 採用 | 画面・API・試験がすでにこのキーで書かれている（recon.md §3）。足すだけで所有者・管理者に届く（ADR-1007:48-51）。DB を正とする今の形を変えない |
| B | コードを既にあるキー（products.view など）へ付け替える | 不採用 | 状態マスタ・商品カテゴリの権限を商品の権限と分けて付けられなくなる。権限の画面に「状態マスタ」の欄が無いままになる |
| C | migration で足す | 不採用 | ADR-1007・ADR-155 で禁止。migration-guard の保護表に permissions が入っている（recon.md §1） |
| D | アプリに権限の一覧の書き込み画面を作る | 不採用 | 7 行のために新しい書き手を作ることになり、範囲が大きすぎる。運用者だけが一度だけ書く今の手順で足りる |

## 4. 便1（変更前後）

### 4-1. 便1-コード（クラウドの Sonnet が実装・1 PR）
変更するファイルは 4 つ、試験ファイルは 3 つ新しく作る（backend 2 つ・画面 1 つ。§6）。

(1) `backend/app/auth/dependencies.py` require_permission（:646-672）
- 変更前: checker は求めるキーを外から読めない。
- 変更後: `return checker` の前に `checker.required_permission_keys = frozenset(required)  # type: ignore[attr-defined]` を 1 行足す。判定の中身は変えない。
- 理由: 試験（§6）と便2 の見張りが、どの経路がどのキーを求めるかを、文字列を探さずに読むため。

(2) `backend/app/routers/conditions.py`
| 行 | 経路 | 変更前 | 変更後 |
|---|---|---|---|
| :163 | GET /conditions/catalog | `require_permission("work_items.view")` | `require_permission("conditions.view")` |
| :414 | POST /conditions/import/preview | `dependencies=[Depends(require_permission("conditions.view"))]` | `dependencies=[Depends(require_permission("conditions.create")), Depends(require_permission("conditions.update")), Depends(require_permission("conditions.delete"))]` |
| :452 | POST /conditions/import/commit | 同上 | 同上 |
- 取り込みは次の 3 つをする。そのため、登録・編集・削除の 3 つ全部を求める。dependencies に並べると、全部を満たさないと通らない。
  - 新しい行の登録（INSERT。conditions.py:492-502 付近）。
  - 既存の行の上書き（UPDATE。:481-490 付近）。
  - is_active を CSV の値で上書きする（取り込みの読み取り :85-101 が is_active を読み、UPDATE で書く）。is_active を FALSE にすることは、削除の経路 delete_condition（:324-361・conditions.delete）がしている論理削除と同じ結果になる。だから削除の権限も求める（クラウドの設計審査の指摘④）。
  - 出典: FastAPI 公式「Dependencies in path operation decorators」。`dependencies=[Depends(verify_token), Depends(verify_key)]` の例で、どちらの依存も失敗すると HTTPException で止まる（Context7 /websites/fastapi_tiangolo、2026-11-04 確認）。require_permission の checker も、キーが無ければ 403 の HTTPException を出す（dependencies.py:646-672）。
- 一覧（:130）・1 件（:186）・CSV 出力（:371）・別名の一覧（:522）は conditions.view のまま。
- catalog は、共用の状態の行（tenant_id IS NULL）を読むだけ（:160-180）。呼ぶのは状態マスタの画面だけ（ConditionsPage.tsx:150）。

(3) `frontend/src/pages/conditions/ConditionImportPage.tsx:130`
- 変更前: `const canImport = hasPermission("conditions.view");`
- 変更後: `const canImport = hasPermission("conditions.create") && hasPermission("conditions.update") && hasPermission("conditions.delete");`

(4) `frontend/src/pages/conditions/ConditionsPage.tsx:374-376`（取り込みボタン）
- 変更前: conditions.view の枝の中で、条件なしに出している。
- 変更後: `{hasPermission("conditions.create") && hasPermission("conditions.update") && hasPermission("conditions.delete") && ( ... )}` で包む。ボタンの部品・文言・data-testid は変えない。
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
3. 300 秒待つ（権限のキャッシュ。backend/app/cache.py:19）。そのあと K2 を見る。
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

(2) 新しいファイル backend/app/auth/permission_catalog.py（新規）
- `KNOWN_MISSING: dict[str, str]` を置く。キーと、残す理由・PO 判断待ちの印を並べる。
  - 最初の 3 件: companies.view・customers.edit・leads.edit。
- `async def count_missing_permission_keys(db) -> list[str]` を置く。
  - `SELECT key FROM public.permissions` を読む。
  - `sorted(REGISTERED_PERMISSION_KEYS - 一覧 - KNOWN_MISSING)` を返す。

(3) `backend/app/metrics.py`
- Gauge を足す: `salesanchor_permission_keys_missing`。説明は「コードが求めるのに権限の一覧に無いキーの数」。
- /metrics を読んだときに更新する。DB を読むのは最大 300 秒に 1 回。結果はプロセスの中に置く。
- 値の意味を 3 つに分ける。
  - -1: まだ数えていない、または数えられなかった。Gauge を作った直後に `.set(-1)` を入れる（作りたての値に頼らず、「欠け無し」の 0 と見分けるため。クラウドの設計審査の指摘⑥。作りたての値そのものは公式の説明に書かれておらず未確認だが、直後に -1 を入れるのでこの設計は作りたての値に依存しない。Context7 /prometheus/client_python 2026-11-04）。DB が読めないときも -1。
  - 0: 数えて、欠けが無かった。
  - 1 以上: 欠けの数。
- DB の接続は `backend/app/database.py:36` の AsyncSessionLocal を使う。
- 既存の _update_viewer_inventory_gauges（metrics.py:81-90）は Redis の値を読むだけで DB は読まない。この見張りは DB を読む点が違う。
  - そのため、DB の読みに時間の上限（2 秒）を付け、超えたら -1 にする。/metrics の応答を遅らせないため。
  - 読めなかったときも、次に数えるのは 300 秒後とする（すぐには数え直さない）。DB の具合が悪いときに負担を重ねないため。-1 が 30 分続けば警報になる。
  - 呼び出しの形（/metrics の中で await する）だけを既存に合わせる。

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
- 試験 backend/tests/test_permission_catalog.py（新規） で次を確かめる。
  - KNOWN_MISSING の各キーが REGISTERED_PERMISSION_KEYS に入っていること。使われなくなったら名前を消させるため。
  - KNOWN_MISSING の件数が 3 以下であること。増やすには、この試験の数字を変える PR が要る。
- PO が 3 キーの扱いを決めたら、付け替えまたは一覧への追加をする。その PR で KNOWN_MISSING から消し、上限の数字を下げる。

### 5-4. 見張れない範囲（正直に書く）
- 画面側の hasPermission("...") のキー。今回の 2 画面は API と同じキーを使っているので、API 側の見張りで捕まる。画面だけで使うキー（menu.* など）は見張らない。
- require_permission を通らず、キーの文字列を直接比べている場所。例: calendar.py・inventory_aggregated.py・inventory_search.py の load_user_permissions 呼び出し（migration-hygiene/recon.md §5.2）。
- この 2 つを見張るかどうかは、便2 のあとに件数を数えてから決める。

## 6. 試験（便1）
新しいファイル backend/tests/test_conditions_permission_keys.py（新規）。DB は使わない。

名前の試験（T1〜T4）:
- T1: アプリの経路から POST /api/v1/conditions/import/commit を探す。
  - その dependencies の checker の required_permission_keys が {conditions.create}・{conditions.update}・{conditions.delete} の 3 つであること。
- T2: /conditions/import/preview も同じであること。
- T3: GET /api/v1/conditions/catalog の求めるキーが {conditions.view} であること。
- T4: conditions・product-categories のすべての経路で、求めるキーが §4-2 の 7 キーのどれかであること。
  - 対象は、dependencies の checker が required_permission_keys を持つものだけ。持たない依存（get_current_tenant・require_super_admin など）は飛ばす（クラウドの設計審査 3 回目の注記）。
  - 将来、一覧に無いキーを書いたら試験で止める。便2 の前の簡易版。

実動の試験（T5〜T7。クラウドの設計審査の指摘⑦）:
- 置き場所は backend/tests/test_conditions_import_permission.py（新規）。client の試験の形にする。
- 前例: backend/tests/test_order_purchase_details.py:414-457。`patch("app.auth.dependencies.load_user_permissions", 差し替え)` で、持っている権限を絞って呼び、403 を確かめている。
  - 全試験で全権限を返す差し替え（backend/tests/conftest.py:1862-1879 の bypass_permissions）の上から、試験の中だけ差し替える。
- T5: {conditions.view} だけで import/preview と import/commit を呼ぶと、どちらも 403。
- T6: 3 つのうち 1 つだけ欠けた組（view＋create＋update、view＋create＋delete、view＋update＋delete）で、どちらも 403。
- T7: view＋create＋update＋delete の 4 つで呼ぶ。
  - import/preview に見出しだけの CSV（中身 `code,canonical\n`、名前は .csv で終わる）を送ると、200 で total が 0。
  - import/commit に同じ CSV と、食い違う digest（例: 文字列 `mismatch`）を送ると、409（CONDITION_IMPORT_DIGEST_MISMATCH）。
  - 「403 でない」ではなく、ちょうどの番号を確かめる。500 で合格しないようにするため（クラウドの設計審査 2 回目の指摘）。
- T5・T6 の commit も、同じ CSV と食い違う digest で呼ぶ。権限の確かめ（dependencies）が先に走るので 403 になる。権限が足りていれば 409 になる。
- 表を読まずに済む理由（2026-11-04 origin/main 48eab3eaf で確認。conditions.py・conftest.py・dependencies.py は cb9525b9d と差分 0 件）:
  - client の試験は SQLite で動き、public.conditions の表が無い（conftest.py:1883 以降）。行のある CSV だと表を読んで 500 になる。
  - preview の表の読みは、行ごとの繰り返しの中だけ（backend/app/routers/conditions.py:429-437）。見出しだけなら行が 0 件で、表を読まない。必須の列 code・canonical（:43）がそろっていれば誤りも出ない（:73-75）。
  - commit の digest の照合（:463-465）は、表を読む前に 409 を返す。
  - 中身の正しさ（書き込み）は、この試験では見ない。
- 画面側: 既存の vitest の書き方に合わせる。ConditionImportPage で、conditions.view だけを持つ利用者に取り込みパネルが出ないことを確かめる。
  - 試験ファイルの置き場所は、実装のときに既存の画面試験ファイル（拡張子 .test.tsx）の並びに合わせる。

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

## 8. 外部・過去事例の参照と我々への応用
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
  - 1 件の編集で is_active を FALSE にできる今の形（§2 対象外）。

### 10-1. クラウドの設計審査 1 回目（2026-11-04・判定 REVISE）と直したこと
| 指摘 | 直したこと |
|---|---|
| ① 照合（行番号付きの主張・鍵の数 97 種類） | 合っていた。直すこと無し |
| ② 行番号のずれ（取り込みの書き込み・cache.py・RolesPage） | :476-503／:481-490／:492-502、cache.py:19、RolesPage.tsx:416 に直した |
| ③ dependencies を 2 つ並べると両方必要 | 合っている。出典を §4-1 に足した |
| ④ 取り込みが is_active を書くので、削除の権限なしで消せる | 取り込みに conditions.delete も求める（§4-1）。編集の is_active は §2 対象外として PO に聞く |
| ⑤ 戻しの件数確認がコメントだけ | 09_rollback_dryrun.sql・09_rollback_apply.sql を足し、件数ガードを付けた |
| ⑥ 見張りの作りたての値と「欠け無し」の区別・DB を読む点 | -1 の初期化と時間の上限 2 秒を §5-2 に書いた |
| ⑦ 名前だけの試験 | 実動の試験 T5〜T7 を §6 に足した |

### 10-2. クラウドの設計審査 2 回目（2026-11-04・先頭 f3b89a8c7・判定 REVISE）と直したこと
| 指摘 | 直したこと |
|---|---|
| T7 が書けない。client の試験は SQLite で動き、public.conditions の表が無い。行のある CSV では 500 になり、「403 でない」だけを見ると 500 でも合格してしまう | T7 を「見出しだけの CSV で preview が 200」「digest を食い違わせた commit が 409」に変えた（§6）。どちらも表を読まない（conditions.py:429 の行ごとの読みは行が 0 件なら回らない。:464-465 の 409 は表を読む前） |
| delete_condition の行番号（実物は :324-361） | §4-1 を :324-361 に直した |
| §10-1 に③が無い | 1 回目の報告の原文の番号（①〜⑦）に合わせて表を直した |
| DB が読めなかったとき、300 秒待たずに数え直すか | 待つ。次に数えるのは 300 秒後とする（§5-2）。DB に負担をかけ続けないため。-1 が 30 分続けば警報になる |
| 件数の数え方が 01_apply（category）と 00・09（resource）で違う | 害は無い（事前の値はどちらも 0）。01_apply の件数ガードは category で数え、全体 130 件の照合と合わせて確かめる。09 は DELETE で category と resource の両方の条件を使う（マージ前の審査の注記で書き直し） |

## 維持の仕組み
- 守り手:
  - 便1 は backend/tests/test_conditions_permission_keys.py（新規）と backend/tests/test_conditions_import_permission.py（新規）（CI の pytest）。
  - 便2 は `monitoring/prometheus/alert_rules.yml` の PermissionKeyMissing と backend/tests/test_permission_catalog.py（新規）。
  - いずれも実装の PR で作る。この設計の PR の時点では、まだ無い。
- 対象: 状態マスタの CSV 取り込みが閲覧だけで通らないこと。コードが求める権限キーが、権限の一覧にそろっていること。
- 関所ができるまで: 人手で守る。理由は、守り手のファイルが便1・便2 の実装で初めてできるため。

### 10-3. クラウドの設計審査 3 回目（2026-11-04・先頭 e9318f7d8・判定 APPROVE）
| 注記（直さなくても止まらない） | 直したこと |
|---|---|
| T4 で、鍵を持たない依存（require_super_admin など）をどう扱うか書かれていない | required_permission_keys を持たない依存は飛ばす、と §6 に書いた |
| 確認元の版が §10 は cb9525b9d、§6 は origin/main と揺れている | §6 に origin/main 48eab3eaf と書き、3 ファイルが cb9525b9d と差分 0 件であることを添えた |

## 11. 便3（既知の欠け 3 キーを、一覧にある鍵へ付け替える）

### 11-1. PO の判断
- 2026-11-04 チャットで PO「1」（3 つとも案のとおり付け替える）。条件は §1-1 と同じ（推測禁止・事実確認・SSOT 遵守・分からないことは聞く）。
- 一覧に新しい鍵を足す案（DB 変更）は採らない。同じ役目の鍵が一覧に既にあるため。

### 11-2. 今の困りごと（実測。2026-11-04 origin/main d948cf9c7）
3 つの鍵は一覧（public.permissions）に無い。どの役割にも付けられない。所有者・管理者も持たない（`backend/app/auth/dependencies.py:618-623` の計算は一覧から作るため）。よって次の 4 つの道は、誰が呼んでも 403 になる。

| 道 | 鍵 | 場所 | 画面の呼び出し | 失敗の見え方 |
|---|---|---|---|---|
| POST /api/v1/contacts/{id}/channel-acknowledge-duplicate | customers.edit | `backend/app/routers/contacts.py:659` | `frontend/src/components/ContactChannelForm.tsx:161`（`PATCH /contacts/{id}` の成功の後） | 黙って失敗（:166-169 で握りつぶす）。監査の記録が残らない |
| POST /api/v1/discord/channel-invite/{lead_id} | leads.edit | `backend/app/routers/discord_channel_invite.py:63` | `frontend/src/pages/inbox/InboxKartePanel.tsx:846`（:534 で無条件に出す） | 赤字のエラー表示 |
| POST /api/v1/discord/sync-role/{lead_id} | leads.edit | `backend/app/routers/discord_role_resync.py:43` | `frontend/src/pages/inbox/InboxKartePanel.tsx:888`（:542 で無条件に出す） | 赤字のエラー表示 |
| GET /api/v1/companies/duplicates | companies.view | `backend/app/routers/duplicates.py:69` | 無し（docs/handoff/s6-get-access-audit/recon.md §3） | — |

- 本番の記録（Loki、job=containerlogs、2026-10-28〜11-04 の 7 日）で 4 つの道の呼び出しは 0 回（Opus が自分で流した検索 1 行のみ）。30 日の検索は Grafana が 502 を返し、読めていない（未確認）。

### 11-3. 付け替え先と選んだ理由
| 今 | 後 | 理由（実物） |
|---|---|---|
| customers.edit | customers.update（一覧 id 10） | 同じファイルの更新の道 `PATCH /contacts/{id}`（contacts.py:518-521）が customers.update。画面はこの PATCH の成功の後にだけ記録の道を呼ぶ。よって押せる人は増えない |
| leads.edit | leads.update（一覧 id 14） | リードを直す既存の鍵。コード中の leads.update は 3 か所、leads.edit は この 2 か所だけ |
| companies.view | customers.view（一覧 id 8） | 会社の道（`backend/app/routers/companies.py:294`・`:339`）の閲覧が customers.view |

### 11-4. 誰が使えるようになるか（本番の読み取り。2026-11-04 16:22 JST・読み取り専用の鍵・ai_ro）
- 5 社とも、所有者・システム管理者・営業・マネージャーの役割が customers.update・customers.view・leads.update を持つ。CS は customers.update・customers.view だけ（leads.update は無い）。仕入れ・発送は 3 つとも無い。
- よって付け替えの後、Discord の 2 つのボタンは CS・仕入れ・発送の人には今までどおり 403 になる。画面はボタンを無条件に出す（:534・:542）。この出し分けは対象外とする（§11-6）。
- 001（開発用）の「点検用（見るだけ）」の役割は customers.update と leads.update を持つ。見るだけの役割が書ける鍵を持つ件は、別に PO へ聞く（本便では変えない）。
- 生の出力: Opus の手元の作業ファイル（km-q3a.out・km-q3c.out）。PR には役割の人数だけを書き、人の名前は書かない。

### 11-5. 変更（4 本の道の鍵の文字列と、見張りの例外を空にする）
1. `backend/app/routers/contacts.py:659` の `"customers.edit"` → `"customers.update"`
2. `backend/app/routers/discord_channel_invite.py:63` の `"leads.edit"` → `"leads.update"`
3. `backend/app/routers/discord_role_resync.py:43` の `"leads.edit"` → `"leads.update"`
4. `backend/app/routers/duplicates.py:69` の `"companies.view"` → `"customers.view"`
5. `backend/app/auth/permission_catalog.py:13-17` の KNOWN_MISSING を空の dict にする。注記は「今は空。足すには PO の判断と試験の上限の変更が要る」。
6. `backend/tests/test_permission_catalog.py`
   - C2（:24）の上限を `<= 3` から `== 0` にする。
   - C4（:56）は KNOWN_MISSING を試験の中で `{"companies.view": "試験"}` に差し替える。今の形のままだと、空にした後 `["b.view", "companies.view"]` が返り落ちるため。
7. 新しい試験 C5（同じファイル）: 4 本の道の checker の `required_permission_keys` が、それぞれ §11-3 の後の鍵 1 つだけであること。経路は `app.main.app` の routes から path と method で探す（§6 T1 と同じ探し方）。
- DB・画面・migration は変えない。

### 11-6. 対象外
- 画面のボタンの出し分け（CS などに Discord の 2 ボタンを隠す）。見た目が変わるため、別に PO に聞く。
- 001 の点検用の役割の書ける鍵（§11-4）。
- §5-4 の見張れない範囲。

### 11-7. 受入（○×）
| 基準 | 検証方法 |
|---|---|
| K6 4 本の道が §11-3 の後の鍵を求める | 試験 C5（CI の pytest） |
| K7 見張りの例外が 0 件 | 試験 C2（CI）・`backend/app/auth/permission_catalog.py` の KNOWN_MISSING が空 |
| K8 本番の見張りの値が反映後も 0 | Grafana 経由で `salesanchor_permission_keys_missing{job="backend"}` を、反映から 300 秒あと以降に読む。値 0 |
| K9 所有者で Discord の案内ボタンが 403 にならない | 001 で、反映後に Opus が Chrome で押すか、API を読む形で確かめる。ただし 001 のリードに Discord の設定が無いと 409 や 404 になる。403 でないことだけを見る（送信の成否は見ない） |

### 11-8. リスクと対処
| リスク | 対処 |
|---|---|
| 営業・マネージャーが Discord のボタンを押せるようになり、顧客のチケットに案内が届く | 元々そのために作られたボタン（ADR-091 KPI5・KPI7）。PO が 2026-11-04 に承認 |
| 会社の重複探しが顧客を見られる人に開く | 中身は会社の名前・メール・電話で、会社の一覧（customers.view）と同じ範囲 |
| 試験が付け替え前の鍵を参照していて赤になる | 実物で探した: 4 本の道の鍵を名前で参照する試験は無い（`git grep` で test_permission_catalog.py:56 のみ） |

### 11-9. 戻し方
PR を revert する。DB は変えないので、DB の戻しは要らない。

### 11-10. 設計審査（自己審査・2026-11-04・同一 AI）
- 判定: APPROVE（設計合格）。
- 確かめたこと: 4 か所の行と前後の道を d948cf9c7 の実物で読んだ。付け替え先の 3 鍵が一覧にあることを本番の読み取りで確かめた（id 8・10・14）。役割ごとの保有を 5 社分読んだ。KNOWN_MISSING を空にしたとき C4 が落ちることを、試験の中身から確かめた。DB の写しを作らない（鍵の文字列は一覧の既存の鍵を指すだけ）。
- 未解決（PO に戻すもの）: §11-6 の 2 件。
