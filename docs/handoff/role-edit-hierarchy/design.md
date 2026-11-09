# design: ロール画面の編集の決まり

状態: 設計案。PO 回答「2」（2026-11-09）＝マネージャーにもロールの作成・削除・人への割当を渡す。スモーク専用は画面から外す（選択肢2は1の2点目を変えていない）。実装の承認はまだ。recon: `docs/handoff/role-edit-hierarchy/recon.md`。

## 1. 目的（PO の言葉から）

- 今は「マネージャー」等の権限が保存できない／オーナー・システム管理者は押せない（recon「本番画面」）。
- あるべき姿:
  - オーナー・システム管理者・マネージャーの3つだけがロール画面を開いて権限を直せる。
  - ロール画面にはオーナー・システム管理者・点検用（＋スモーク専用・PO確認）を出さない。
  - それ以外のロールの人はロール画面を開けない（メニューにも出ない）。

## 2. KGI（○×で判定）

| # | 基準 | 検証方法 |
|---|---|---|
| K1 | オーナーの人がロール画面でマネージャーの切替を1つ変えて保存→再読込で残る | 本番で PO が操作（済んだら元に戻す） |
| K2 | ロール画面の左の一覧にオーナー・システム管理者・点検用（見るだけ）・スモーク専用が0件 | 本番画面の目視＋ GET /roles?scope=role_page の件数 |
| K3 | マネージャーの人でロール画面が開け、仕入れ等を保存できる。オーナー・システム管理者の権限は API で 403 | backend 試験（role 別の HTTP 試験） |
| K4 | 営業・CS・仕入れ・発送・点検用の人はメニューに「ロール」が無く、GET /roles が 403 | backend 試験＋本番の点検用で /roles が 403 |
| K5 | スタッフ編集画面でオーナー・システム管理者を今までどおり付けられる（一覧の件数が変わらない） | backend 試験（scope 無しの GET /roles の結果が今と同じ） |
| K6 | 判定のある毎日の自動点検（prod-ui）が緑のまま | 反映翌日の実行結果 |
| K7 | マネージャーの人はロールを作れる（順位はマネージャー未満だけ）・消せる（隠すロールとマネージャーは不可）・人に付けられる（オーナー・システム管理者・マネージャー・点検用・スモーク専用は不可） | backend 試験（操作×対象の表） |

## 3. 対象と対象外

対象:
- `backend/app/auth/system_roles.py` 見分けの鍵と計算を足す。
- `backend/app/auth/dependencies.py:569-572` 計算を owner/admin 以外にも通す。
- `backend/app/routers/roles.py` 一覧の scope、権限保存の可否の決まり。
- `backend/app/services/tenant.py:69-90` 新しい会社のマネージャーに system_key='manager'。
- `frontend/src/pages/roles/RolesPage.tsx`・`frontend/src/constants/menuPermissions.ts`・`frontend/src/locales/ja.json`/`frontend/src/locales/en.json`。
- 本番データ: 一度きりの SQL で system_key を入れる（ADR-155、前例 `docs/handoff/roles-system-key-data/`）。

対象外（触らない）:
- 作成の順位の決まり `backend/app/routers/roles.py:220-224`、割当の「相手が自分より下」の決まり（`backend/app/routers/roles.py:579` ensure_target_below_me）は今のまま。
- スタッフ画面 `frontend/src/pages/staff/StaffEditPage.tsx:107`・`frontend/src/pages/staff/StaffPage.tsx:118` と `_visible_role_sql`（`backend/app/routers/roles.py:54-64`、`backend/app/routers/staff.py:96`）は今のまま。
- 点検用・スモーク専用が持つ roles.* 以外の権限。

## 4. 変更前後

### 4-1 見分けの鍵（system_roles.py）

前: `owner` / `admin` の2つ。`TENANT_HIDDEN_SYSTEM_KEYS={admin}`（super admin 以外の全画面から隠す）。

後（足すだけ。既存の定数は変えない）:

```python
ROLE_KEY_MANAGER = "manager"
ROLE_KEY_INSPECTOR = "inspector"   # 点検用（見るだけ）ADR-1051
ROLE_KEY_SMOKE = "smoke"           # スモーク専用 ADR-1017
ROLE_PAGE_HIDDEN_KEYS = frozenset({ROLE_KEY_OWNER, ROLE_KEY_ADMIN, ROLE_KEY_INSPECTOR, ROLE_KEY_SMOKE})
ROLE_EDITOR_KEYS = frozenset({ROLE_KEY_OWNER, ROLE_KEY_ADMIN, ROLE_KEY_MANAGER})
ALL_ROLE_KEYS = frozenset({"roles.view", "roles.create", "roles.update", "roles.delete", "roles.assign"})
ROLE_PAGE_KEYS = ALL_ROLE_KEYS  # PO「2」: マネージャーにも作成・削除・割当
# 編集できるのが owner/admin だけのロール（マネージャーは触れない）
OWNER_ADMIN_ONLY_KEYS = ROLE_PAGE_HIDDEN_KEYS | {ROLE_KEY_MANAGER}
```

`compute_permission_keys` の後ろ2行を変える:

```python
    if ROLE_KEY_OWNER in system_keys: return stored_keys | all_keys          # 前と同じ
    if ROLE_KEY_ADMIN in system_keys: return stored_keys | (all_keys - {SYSTEM_MANAGE_KEY})  # 前と同じ
    if ROLE_KEY_MANAGER in system_keys:
        return (set(stored_keys) - ALL_ROLE_KEYS) | (ROLE_PAGE_KEYS & all_keys)
    return set(stored_keys) - ALL_ROLE_KEYS
```

### 4-2 計算をいつも通す（dependencies.py:569-572）

前: `if is_tenant_admin(system_keys):` のときだけ全権限の表を読んで計算。
後: 条件を外し、毎回 `compute_permission_keys` を通す（全権限の表は今と同じ読み方）。キャッシュの仕組みは変えない。
- 影響: roles.* を保存行に持っている非編集ロールの人は roles.* を失う。本番では t001 点検用の roles.view だけ（recon）。

### 4-3 一覧の scope（roles.py:178-203）

- `GET /roles?scope=role_page` のときだけ、`system_key IN ROLE_PAGE_HIDDEN_KEYS` を super admin でも除く。
- scope 無しは今と1文字も変えない（K5）。scope の値は `role_page` 以外を 422。

### 4-4 権限の保存の可否（roles.py:431-442 PUT /roles/{id}/permissions）

前: is_system なら 403 ／ 対象 priority ≥ 自分の最大なら 403。
後（上から順に判定）:
1. 自分の system_keys が ROLE_EDITOR_KEYS と重ならない → 403（念のため。roles.update を計算で失っているので通常はここまで来ない）。
2. 対象の system_key が ROLE_PAGE_HIDDEN_KEYS → 403「このロールの権限はここでは変更できません」（i18n はサーバー文言の既存の形に合わせる）。
3. 自分がマネージャーだけ（owner/admin を持たない）で、対象が owner/admin → 2 で既に止まる。対象がマネージャー自身は通す（PO の言葉「オーナーとシステム管理者以外」）。
4. 送られた鍵に roles.* が入っている → 422（ロール画面の鍵は計算で決まる。保存行に持たせない）。
5. 既存のエスカレーション防止 `backend/app/routers/roles.py:459-468` はそのまま。
- `GET /roles/{id}/permissions` も対象が ROLE_PAGE_HIDDEN_KEYS なら 404（画面に出さないものは開けない）。ただし scope 無しの一覧を使うスタッフ画面は権限の詳細を読まないので影響なし（実装時に grep で確かめる）。

### 4-4b 作成・削除・名前の変更・割当（PO「2」で足す止め）

- POST /roles（`backend/app/routers/roles.py:206-259`）: 今のまま（順位はマネージャー 500 未満だけ・system_key は付けられない＝INSERT に列が無い）。
- DELETE /roles（`backend/app/routers/roles.py:335-383`）: 今の2つの止めに足す。対象に system_key があれば誰でも 403「このロールは削除できません」。これで点検用（300）・スモーク専用（100）をマネージャーが消せない。マネージャーのロールも消せない（編集役が消えるのを防ぐ）。
- PATCH /roles（`backend/app/routers/roles.py:262-332`）: 今の止めに足す。対象が ROLE_PAGE_HIDDEN_KEYS なら 403。
- PUT /users/{id}/roles（`backend/app/routers/roles.py:533-611`）: 付けるロールに system_key が OWNER_ADMIN_ONLY_KEYS のものがあり、自分が owner/admin でなければ 403。オーナー・システム管理者はマネージャー（500）も点検用も今どおり付けられる。
  - 今の順位の止め（`backend/app/routers/roles.py:572-576`）でマネージャーはオーナー・システム管理者・マネージャーを付けられない。足す止めは点検用・スモーク専用（順位が低い）のため。
- 画面の作成・削除ボタンは既に `hasPermission("roles.create")`・`hasPermission("roles.delete")`（`frontend/src/pages/roles/RolesPage.tsx:311,363`）で出し分け済み。変更なし。

### 4-5 新しい会社（tenant.py）

- DEFAULT_ROLES のマネージャーに `"system_key": ROLE_KEY_MANAGER` を足す。権限の配列から `"roles.view"` を外す（計算で付く）。
- upsert は `COALESCE(既存, 新)`（`backend/app/services/tenant.py:1625`）なので、既存会社の値を壊さない。
- `backend/tests/test_system_roles.py:65-69` の「他は system_key 無し」を「マネージャーは manager、他は無し」に直す。

### 4-6 画面（frontend）

- `frontend/src/pages/roles/RolesPage.tsx:117` → `/roles?scope=role_page`。
- `frontend/src/pages/roles/RolesPage.tsx:169` → `canEditPerms = hasPermission("roles.update")`（隠すロールは一覧に出ないので is_system の条件は要らない）。
- `frontend/src/constants/menuPermissions.ts:125,218` の fixed に `"roleEditors"` を足し、`frontend/src/constants/menuPermissions.ts:169-172` の「ロール」行を `fixed: "roleEditors"` にする（切替を出さず文だけ）。
- `frontend/src/locales/ja.json` / `frontend/src/locales/en.json` に `roles.fixedRoleEditors` = 「オーナー・システム管理者・マネージャーだけに出ます」／ "Shown only to Owner, System admin and Manager"。既存の fixedOwner の並びに置く。
- 新しい部品・色は作らない（既存の固定表示の金型をそのまま使う、ADR-144）。

## 5. 本番データ（ADR-155 の一度きり SQL）

前例 `docs/handoff/roles-system-key-data/` の形をそのまま写す（precheck / dryrun / apply / postcheck / rollback）。

| 会社 | ロール名 | id（recon） | 入れる値 |
|---|---|---|---|
| t001 / t003 | マネージャー | 2536 | manager |
| t004 / t005 | マネージャー | 2514 | manager |
| t006 | マネージャー | 3 | manager |
| t001 | 点検用（見るだけ） | 2611 | inspector |
| t004 | スモーク専用 | 2589 | smoke |

- 名前と id の両方で1件だけ当たることを確かめ、`system_key IS NULL` のときだけ入れる。1トランザクション・lock_timeout 10s・audit_log 記録。
- 同じ SQL で、編集できないロールの保存行から roles.* を消す（t001 点検用 roles.view の1行・マネージャーの roles.view 5行。2026-11-09 本番の読み直しで t005・t006 にも1行ずつあると分かり 3→5 に直した）。消した行は rollback.sql で戻せるよう、apply 前に行を書き出す。
- 順番: コードの反映 → データ SQL。コードが先でも、値が入るまでマネージャーは「その他」扱いでロール画面を失うだけ（数分）。値が先だと古いコードには影響しない。→ **データ SQL を先に入れ、その後コードを反映**（どの時点でも誰もロール画面を失わない）。

## 6. 代替案

- A（不採用）: 優先度の数（priority）で決める。マネージャー 500 と点検用 300 の差で書けるが、PO の言葉は「役割の名前」で決めており、順位を変えると壊れる。recon の通り今の保存不可の原因もこの数の比べ方。
- B（不採用）: 隠すロールを名前で見分ける。名前は会社ごとに変えられるので壊れる。既存の決め方（ADR-147 の system_key）に合わせる。
- C（採用）: system_key で見分け、ロール画面の鍵は計算で決める。オーナー・システム管理者と同じ仕組みを1段広げるだけ（SSOT は roles.system_key のまま）。

## 7. PO の決定

- 2026-11-09 PO「2」: マネージャーにも作る・消す・人に付けるを渡す。自分より上を作れない止めを足す（§4-4b）。
- スモーク専用は画面に出さない（選択肢1・2共通）。

## 8. リスクと対処

- 点検用の毎日の速さの記録（ADR-1053）で /roles 2本が 403 になる。判定の無い記録なので点検は落ちない（recon）。記録の読み手向けに design に残すだけ。
- 計算を全員に通すので、権限の読込が1回増える（全権限の表を読む）。今もオーナー・管理者は毎回読んでいて、キャッシュ付き。
- 誤って manager を2行に入れる → テナント内一意の索引（`migrations/20261005_150000_add_roles_system_key.sql:43`）で SQL ごと失敗する。

## 9. 外部・過去事例の参照と我々への応用

- 外部事例: 使わない。理由: 中身は既存 ADR-147 の仕組み（system_key で役割を見分け、権限を計算で足す）を1段広げるだけで、新しい方式を入れないため。直接の根拠がない事例を成功の証明に使わない。
- 過去事例（社内）: `docs/handoff/roles-system-key-data/` で owner/admin の system_key を一度きり SQL で入れた前例。名前で1件ずつ確かめ、audit_log に記録した。応用: 今回の data/ の precheck / dryrun / apply / postcheck / rollback も同じ形にした。

## 10. 維持の仕組み

- backend 試験: 4つの役割（owner/admin/manager/営業）× 3操作（一覧 scope・保存・隠すロールの保存）の表で固定。
- `backend/tests/test_system_roles.py` で DEFAULT_ROLES のマネージャーの system_key を固定。
- 守り手: CI の backend 試験（`backend/tests/test_roles_edit_hierarchy.py`・`backend/tests/test_system_roles.py`）と画面の試験（`frontend/src/constants/menuPermissions.test.ts`）。落ちたら合流できない。
- ADR-147 の Why に「ロール画面を直せるのは3役割。見分けは system_key」を追記（Amendment）。

## 11. 審査（Opus 自己審査・独立審査ではない）

判定: **APPROVE**
- 既存 ADR-147 / ADR-155 と矛盾しない。スタッフ画面の見え方（K5）を変えない設計になっている。
- 受入条件は全部 ○× で測れる。
- マネージャーが上の役割に届く道（作成の順位・削除・名前変更・割当・権限の付与）を5つとも止めた（§4-4・§4-4b）。
- 未解決: なし。実装の開始は PO の明示承認が要る。
