# 審査用アカウントの「期限つき確認なし」 — 設計

この文書は、決めた期限の間だけ、選んだ1人が知らない機械からパスワードだけで入れるようにする作り方です。期限が来たら自動で元に戻ります。

- 親（あるべき姿）: [docs/specs/auth-login/README.md](../../specs/auth-login/README.md)
- 現在地: [review-exempt-recon.md](review-exempt-recon.md)（以下 recon:記号）
- 決定: [ADR-1055](../../adr/ADR-1055-new-device-login-approval.md) の改訂（What 11 を足す。2026-11-21 提案中）
- 状態: 設計案作成済み（Opus 2026-11-21）・KGI は PO 承認待ち・実装未着手

## 1. 目的（PO の言葉）

PO 2026-11-21: 「meta用に用意した006だけはオンオフでログイン認証を切り替える…レビュー期間だけONに切り替えてログインできるようにして、レビューと審査が終わったらOFFにしてログインできないようにしたい」。その後「1」（期限つきで自動で戻る形）を選んだ。

奥の目的: Meta の審査を1回で通す。そのために、審査員が止まらずに入れるようにする。他の人の守りは弱めない。

## 2. KGI（合格の基準）— PO 承認待ち

| # | 基準（○×で判定） | 検証方法 |
|---|---|---|
| K1 | 期限の間、確認を外した人は、初めての機械からパスワードだけで入れ、受信箱の画面が開く | 本番: 私物でない新しいブラウザ（シークレット窓）で review@ に入る。試験 `test_review_exempt.py::test_exempt_login_gets_tokens` |
| K2 | 期限が過ぎたら、同じ操作で「許可を待っています」に戻る | 試験 `test_exempt_expired_returns_202`。本番: 期限を消した後に同じ手順で 202 を見る |
| K3 | 確認を外していない人は、今までどおり 202 で止まる | 試験 `test_not_exempt_still_202`・既存 `backend/tests/test_new_device_approval.py` が全部緑 |
| K4 | 外せるのは super admin だけ。他の人は 403。super admin 自身・止まっている人には外せない（422） | 試験 `test_exempt_set_forbidden_for_non_super_admin`・`test_exempt_set_rejects_super_admin_target` |
| K5 | 期限は1〜14日だけ。0日・15日は 422 | 試験 `test_exempt_days_range` |
| K6 | 外して入るたびに、記録に「review_exempt」が1行残り、本人に知らせメールが届く | 試験 `test_exempt_login_audited`。本番: auth_events を reader で1行確かめ、review@ の受信箱の Discord 知らせを見る |
| K7 | 期限が過ぎたら、ログイン中の画面も15分以内に入り直しを求められる | 試験 `test_exempt_refresh_after_expiry_401` |
| K8 | 管理画面に、外している人・期限・外した人が出る。部品は金型だけ・直書き0件・文字は全部 t() | フロントの試験＋ `ui-governance` と i18n の必須チェックが緑 |

## 3. 作り方（What／How）

### 3-1. データ（SSOT）

- 置き場は人の正本 `public.users` に列を1つ（ADR-1008。前例 recon:G）。
  - `device_approval_exempt_until TIMESTAMPTZ NULL`。NULL か過去なら「外していない」。
- 期限の値はこの1列だけ。機械の表や設定ファイルに写さない。オンオフの印を別に持たない（「期限が未来か」だけで決める）。
- 機械の表の登録の種類（recon:G の7種類）は増やさない。外して入った回は機械を登録しない。

### 3-2. 判定の関数（1か所）

`backend/app/auth/devices.py` に足す:

```python
EXEMPT_MAX_DAYS = 14

def is_exempt(exempt_until: datetime | None) -> bool:
    """期限つきの確認なし（ADR-1055 What 11）。期限が今より後のときだけ True。"""
    return exempt_until is not None and exempt_until > _now()
```

### 3-3. パスワードのログイン（recon:C の3の前に1段足す）

`backend/app/routers/auth.py:404-405` の SELECT に `device_approval_exempt_until` を足す。
`backend/app/routers/auth.py:452` の `else:` の前に足す:

```python
        elif devices.is_exempt(user_row.device_approval_exempt_until):
            # ADR-1055 What 11: 期限つきの確認なし。機械は登録しない（期限後に残らない）
            audit_reason, audit_new_device = "review_exempt", True
            background_tasks.add_task(
                send_new_device_mail,
                user_row.email,
                when=devices.jst_text(),
                device=devices.describe_user_agent(request.headers.get("user-agent")),
                location=geo.lookup(ip),
                note="期限つきの確認なしの設定でログインしました。 / Signed in with the time-limited exemption.",
            )
```

- `trusted_device_id` は None のまま。トークンの組に機械は付かない。

### 3-4. トークンの更新（recon:D の2か所目）

`backend/app/routers/auth.py:552-570` を次の形にする（変更前は `elif devices.is_enforced():` の直下が `cutoff = ...` と `if cutoff ...: 登録 / else: 401`）:

```python
    elif devices.is_enforced():
        exempt_until = (
            await db.execute(
                text("SELECT device_approval_exempt_until FROM public.users WHERE id = :id"), {"id": user_id}
            )
        ).scalar_one()
        cutoff = devices.bootstrap_cutoff()
        if devices.is_exempt(exempt_until):
            # ADR-1055 What 11: 期限の間だけ、機械の無い組の更新を通す
            audit_reason = "review_exempt"
        elif cutoff is not None and rotated.family_created_at is not None and rotated.family_created_at < cutoff:
            ...（今の bootstrap の登録。中身は1字も変えない）
        else:
            ...（今の 401。中身は1字も変えない）
```

- 期限が過ぎると、次の更新（アクセストークンは最長900秒）で今までどおり 401 になる＝K7。

### 3-5. 触らない場所

- パスワードの変更（`backend/app/routers/auth.py:769-779`）: 外した人も今までどおり 403。審査員にパスワードを変えさせない。
- パスキーのログイン（`backend/app/routers/auth.py:1188-1200`）: 変えない。
- `AUTH_DEVICE_APPROVAL`・deploy.yml・締切: 変えない。

### 3-6. 管理の口（super admin だけ）

`backend/app/routers/super_admin_login_requests.py` に足す（同じ `require_super_admin`・`require_app_origin`）:

| 口 | 中身 | 断る場合 |
|---|---|---|
| `GET /super-admin/login-exemptions` | 期限が未来の人の一覧（user_id・email・会社名・期限） | — |
| `PUT /super-admin/login-exemptions` 本文 `{email, days}` | 期限＝今＋days 日 | 人がいない 404／super admin・止まっている人 422／days が1〜14の外 422 |
| `DELETE /super-admin/login-exemptions/{user_id}` | 期限を NULL | 人がいない 404 |

- 書き込みの `db.commit()` の直後に `reset_tenant_context(db)` を呼ぶ（ADR-072。既存の許可の口と同じ並び）。
- 操作の記録は既存の `_record_auth_audit`（会社別の audit_logs。`backend/app/routers/auth.py:282`）に `event: login_exemption_set|cleared`・`days`・`until` を残す。誰が操作したかは `user_id=current_user.id`。

### 3-7. 画面

`frontend/src/pages/super-admin/LoginRequestsPage.tsx:46` の `AdminLoginRequestList` の下に、新しい部品 `features/auth/LoginExemptionSection.tsx` を置く。

- 使う金型だけ: `SectionCard`・`TextField`（メールアドレス）・`Select`（1・3・7・14日）・`Button`・`DataTable`・`ConfirmModal`（外すとき・戻すとき）。
- 文字は全部 `t()`。キーは `superAdmin.loginExemption.*` を ja.json と en.json に同じ数で足す。色・大きさの直書きはしない（ADR-067・ADR-144）。
- 期限は日本時間で出す。

### 3-8. 移行（危ない変更）

- `migrations/20261122_100000_add_users_device_approval_exempt_until.sql`（`ADD COLUMN IF NOT EXISTS`・COMMENT 付き・追加だけ）。
- `scripts/run_all_migrations.sh` の末尾の並びに1行足す（前例 `scripts/run_all_migrations.sh:1468`）。
- 列を足すだけで、既存の行は NULL＝今と同じ動き。ADR-136 の GO が要る。

## 4. 便の分け方（一度に1つ）

| 便 | 中身 | GO |
|---|---|---|
| 便1 | 3-1〜3-6・3-8（裏側と移行と試験） | 要（移行を含む） |
| 便2 | 3-7（画面） | 画面だけ（CI 緑で可） |

便1 の後は、画面が無いので本番では誰も外せない（列はすべて NULL＝今と同じ動き）。K1・K2・K6・K7 の本番確認は便2 の後に、Opus が画面で review@ に7日を入れて行う。

## 5. 代わりの案と選ばなかった理由

| 案 | 選ばなかった理由 |
|---|---|
| A. 本番の設定を全員 off にする | 全員の守りが外れる。PO の目的に反する |
| B. review@ の last_login を手で空にして D5 を使う | 最初の1台しか通らない。審査員は複数の機械を使う。本番の手書き修正になる |
| C. 印（Cookie）を命令で発行（What 9） | 外の審査員の機械に入れられない（recon:A） |
| D. 会社（tenant）ごとの設定にする | 会社の中の全員に効き、範囲が広い。人の正本に置く方が狭く済む |
| E. 機械を登録して通す | 期限の後も180日残る。消す仕組みが別に要る |

## 6. 弊害と対処

| 弊害 | 対処 |
|---|---|
| パスワードが漏れると期限の間は機械の確認なしで入れる | 期限は最長14日。super admin には外せない。入るたびに記録と知らせメール（K6）。審査が終わったら PO の画面で戻す |
| 期限の消し忘れ | 期限が来れば何もしなくても戻る（K2）。戻す操作は早めたいときだけ |
| 期限の直後もアクセストークンが最長15分残る | 15分で切れる（K7）。これより短くするには全員の仕組みを変える要があり、範囲外 |

## 7. 外部・過去事例の参照と我々への応用

- Meta の申請の手引きは、審査員がアプリに入れるテスト用のログイン情報を求める（[submission guide](https://developers.facebook.com/documentation/resp-plat-initiatives/individual-processes/app-review/submission-guide)・2026-11-21 閲覧）。入れないと対応依頼になる。→ 審査員の入口は必須と判断した。
- 2段階の確認がある口座で審査員が入れず、確認なしの口座で出し直した開発者の報告がある（[Meta 開発者コミュニティ](https://developers.secure.facebook.com/community/threads/442251551600133)）。個人の報告で数値は無い。成功の証明には使わず、「確認が入ると止まる」危険の裏付けにだけ使う。
- 過去の自社の事例: ADR-1055 の締切と D5 は、全員に効かせる時の例外を「期限と条件で自動で閉じる」形で作った。今回も同じ考え方で、人の手で閉じ忘れても閉じる形にした。

## 8. 実装カードに渡す試験の一覧

`backend/tests/test_review_exempt.py`（新規）に、K1〜K7 の試験名どおりの関数を作る。既存の `backend/tests/test_new_device_approval.py` の準備（enforce の setenv・人の作り方）をそのまま使う。

## 維持の仕組み

- 守り手: .github/workflows/test.yml（`pytest-run-internal` が `backend/tests/test_review_exempt.py` と `backend/tests/test_new_device_approval.py` を毎回流す）
- 守り手: .github/workflows/migration-test.yml（移行の SQL を毎回流す）
- 対象: 期限が過ぎたら必ず戻ること（K2・K7）、外していない人が止まること（K3）、super admin だけが外せること（K4）、14日の上限（K5）
- 期限の消し忘れは、人の手でなく時刻の比べで閉じる（3-2）。オンオフの印を別に持たないので、印の消し忘れは起きない
