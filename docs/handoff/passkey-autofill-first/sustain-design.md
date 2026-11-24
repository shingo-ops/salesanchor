# パスキーの自動の候補 — 続けるための仕組み（設計案）

状態: 設計案（Opus 作成・審査役3回目 REQUEST_CHANGES を受けて4版）。実装は PO の実装承認の後。
親: [design.md](design.md) ／ KGI: [../../specs/auth-login/kgi.md](../../specs/auth-login/kgi.md)「KGI 追加 — パスキーの自動の候補」 ／ 対象 ADR: ADR-1013・ADR-1063（毎日点検の形の前例）・ADR-1051（画面点検の通知）

## 1. 目的（PO の言葉）
PO 2026-11-24:「この仕組みを標準化して管理定着させて継続させるための機械的な仕組みも出来ているか事実ベースで…」「残っていることも不透明にせずに事実確認を実施すること」。
→ 人が覚えていなくても、(a) 壊す変更は合流できない、(b) 本番で壊れたら知らせが来る、(c) 効果の数が毎週自動で届く、の3つを機械で持つ。KGI の決まった日（12/8・12/24）の1回ずつの数えだけは週の区切りと合わないため、台帳に載せて Opus が手で数える（§5-1 末）。

## 2. 今ある仕組み（事実・2026-11-24 11:40 JST・origin/main 1ac87e46b）

| # | 仕組み | 事実 | 根拠 |
|---|---|---|---|
| A1 | 壊す変更を止める試験 | T1〜T12 が vitest にある。T7 はメール欄の `email webauthn` を確かめる | frontend/src/pages/login/LoginPage.test.tsx:451-453、frontend/src/lib/auth/passkey.test.ts:162-288 |
| A2 | 試験が合流の必須 | vitest（unit-run）は必須チェック「Lint & Dark Mode Check (ADR-067)」の集約に入る。画面を変えた PR で落ちれば赤 | .github/workflows/e2e.yml:89-121, 129-167。main の ruleset の必須一覧に同名あり（gh api rulesets 出力） |
| A3 | 決まりの置き場 | あるべき姿・KGI・設計が仕様書と索引から辿れる | docs/specs/README.md:82、docs/adr/FEATURE-INDEX.md:48、docs/specs/auth-login/kgi.md |
| A4 | 攻撃の見張り | ログインの入口6つ（パスワード・パスキーの確認ほか）の 401/429 の合計が5分に10件超・1時間に20件超で知らせる | monitoring/loki/rules/jarvis/alerts.yml:10-33 |
| A5 | 毎朝の画面点検 | 本番のログイン画面を開き(S1)、パスワードでログインする(S2)。失敗だけ Discord | tests/prod-check/prod-ui.spec.ts:28-42、.github/workflows/prod-ui-check.yml:134-172。直近5回すべて success（gh run list） |
| A6 | ログイン記録 | public.auth_events に道ごとの記録。90日残る | migrations/001_create_auth_events.sql:6-16、backend/app/tasks/maintenance.py:179-189 |

## 3. 足りない所（事実）

| # | 足りない所 | 事実 |
|---|---|---|
| G1 | 効果の数（P5・KPI）を数える仕組みが無い | 12/8・12/24 の数えはどこにも予約されていない。auth_events を数えて知らせる係は無い（backend/app/tasks に passkey の語 0件: `git grep -il passkey origin/main -- backend/app/tasks` 出力なし） |
| G2 | 本番で「候補が出る設定」が消えても気づけない | 画面点検 S1 は欄が見えるかだけを見る。`webauthn` の語は tests/prod-check に 0件 |
| G3 | パスキーの道が少ない件数で 5xx になっても知らせが無い | A4 は 401/429 だけ。全体の 5xx の見張り BackendHighErrorRate（monitoring/prometheus/alert_rules.yml:71-72）は 5件/秒 超が条件で、1日0〜14件のパスキーの道では鳴らない |

## 4. 残っている確かめ（事実・本番 auth_events、反映後 2026-11-24 03:27〜11:35 JST）
生の記録: 手元 scratchpad/sustain/passkey-after-deploy.tsv・pw-after-deploy.tsv（IP は読んでいない）

| KGI | 済み/残り | 事実 |
|---|---|---|
| P1 Mac の Chrome | 済み | 08:15 PO の id で passkey/login/verify 200（Mac・Chrome 157） |
| P1 Android の Chrome | 一部 | 11:20 verify 200 は「テスト管理者」の id。PO の id の成功は無い（PO 目視は「ログインまで出来た」） |
| P1 iPhone の Safari | 残り | 反映後 iPhone からの verify 0件（10:45 iPhone の Chrome で options だけ1件） |
| P2 すぐ確認が出る | 未判定 | 記録ではボタンからか候補からか区別できない。PO の目視が要る |
| P3 無いときの案内 | 残り | シークレット窓での目視はまだ |
| P4 Safari は今まで通り | 残り | P1 iPhone と同時に見られる |
| P5 パスワードも使える | 進行中 | 自動点検の係が 12回成功（最後 11:35）。14日分は 12/8 |
| P6・P7 | 済み | PR #5710 に migrations 無し・必須チェック緑 |

## 5. 変更の案（4つ・どれも本番の DB は読むだけ）

### 5-1. 週1回のパスキーの報告（G1 を埋める）
- 新しい係（新しく作るファイル: backend/app/tasks の passkey_weekly_report.py）。形は ADR-1063 便6 の毎日点検 backend/app/tasks/tenant_isolation_daily_check.py と同じ: DB を読むだけ（アプリの接続。前例 backend/app/routers/super_admin_meta_review.py:157-166 が public.auth_events を読む。auth_events に RLS は無い）・管理者用 Discord（環境変数 `ADMIN_NOTIFICATION_DISCORD_WEBHOOK`・tenant_isolation_daily_check.py:31・送り方 :98-109・動けなかったときも1通 :112-124 を写す）・毎回送る（届かない＝止まっている）。
- 登録: backend/app/celery_app.py の `include=[...]`（:21-50）に係を足し、beat の予定（:255-258 の隣）に crontab(day_of_week=1, hour=9, minute=10)。timezone は Asia/Tokyo（:58）。
- 区切り: 日本時間の暦日。月曜 09:10 の回は「前の週の月曜 00:00〜日曜 24:00（7日）」と「その日曜 24:00 までの30日」を数える。
- 数える人: 全社の管理者（public.users の is_super_admin が true）だけ。会社ごとの利用者は数えない。2026-11-24 の本番では id 1・3 の2人（reader 鍵で確かめた）。会社をまたぐ人の情報は出ない。
- 数えるもの（auth_events と users だけ。ログインの成功の数え方は前例 backend/app/routers/super_admin_meta_review.py:157-166 と同じ4つの道。道の文字は backend/app/routers/auth.py:377・:1119、prefix は backend/app/main.py:260）:
  1. 人ごとのパスキーでのログイン成功＝`/api/v1/auth/passkey/login/verify` の 200
  2. 人ごとのパスワードでのログイン成功を2つに分けて書く。(2a)＝`/api/v1/auth/login` の 200。(2b)＝`/api/v1/auth/login-requests/poll` の reason が approved_admin・approved_device ＋ `/api/v1/auth/login-requests/recovery` の 200（本番は知らない機械の確認が有効: .github/workflows/deploy.yml:442。login の 202 は数えない）
  3. 人ごとのパスキーの割合＝(1)÷((1)+(2a))。PO が承認した KPI の測り方（docs/specs/auth-login/kgi.md:47）のまま変えない。(2b) は割合に入れず、件数を横に添える。7日と30日の両方。分母が0なら「-」
- 12/24 の KPI の数えも同じ (1)÷((1)+(2a))。測り方を4つの道に広げるかは、(2b) の件数を見てから PO が決める（§11）。
- 通知に名前・メール・IP・端末は載せない。人は id と role だけで書く（前例 backend/app/tasks/viewer_share_flag_monitor.py:4「id だけ」）。PO の id は 3（docs/adr/ADR-1056 の21行目「id 3 の PO 1 人」・docs/handoff/secretary-chat/design.md:36）。Opus が月曜に読んで PO に伝える。
- 人の id は設定にもコードにも持たない（is_super_admin で選ぶ）。新しい設定・secrets は要らない。
- 文の長さ: 送り方の元は本文を1800字で切る（tenant_isolation_daily_check.py:103）。1人1行・約60字で、管理者が20人を超えるまで切れない。
- 自動点検の係（P5）はこの報告に入れない。毎朝 A5 の S2 がパスワードでログインし、失敗なら Discord に届く。
- 12/8（P5 の14日）と 12/24（KPI の30日）の決まった日の数えは、週の区切りと合わないためこの報告では代えない。tasks/todo.md の「進行中」に1行、この PR で載せる（担当 Opus・次の一手に2つの日付）。Opus がその日に reader 鍵（ai_ro.public__auth_events）で1回数え、kgi.md に書く。P5 は毎日 A5（S2 のパスワードログイン・失敗で Discord）が機械で見ているので、数えは結果の記録だけ。

### 5-2. 毎朝の画面点検に1行足す（G2 を埋める）
- tests/prod-check/prod-ui.spec.ts の S1 に、ログイン画面のメール欄の autocomplete が `email webauthn` であることを足す。
- 落ちれば今ある仕組み（prod-ui-check.yml:134-172）で Discord に届く。新しい通知の道は作らない。

### 5-4. パスキーの道の 5xx の見張り（G3 を埋める）
- 記録の限界（事実）: auth_events は backend/app/middleware/audit.py が `call_next` の後に書く。処理の途中で落ちた 500 と、入口（nginx）が返す 502/504 は auth_events に残らない（審査役の指摘。Starlette の例外の順は Context7 kludex/starlette docs/exceptions.md）。だから 5xx は auth_events では数えない。
- 入口（nginx）の行で数える。入口の行は `"POST /api/v1/auth/passkey/login/options HTTP/2.0" 499 0` の形（状態の後に数字）で、落ちた 500 も 502/504 も残る。
- monitoring/loki/rules/jarvis/alerts.yml の auth_anomaly に1本足す。見張りの名前は `PasskeyServerError`。式は `sum(count_over_time({job="containerlogs"} |~ "\"POST /api/v1/auth/passkey/login/(options|verify) HTTP/[0-9.]+\" 5[0-9][0-9] [0-9]+" [10m])) > 0`（エスケープは alerts.yml:12 と同じ）・for 0m・severity warning・tier ticket・runbook_url は docs/runbooks/alerts.md の #passkeyservererror。届け先は今の Alertmanager（Discord）。
- docs/runbooks/alerts.md に見出し `## PasskeyServerError` を、SustainedAuthFailure の節（:147）の後に同じ形（札・何が起きているか・最初に見るもの・直し方・止め方）で足す。monitoring/scripts/check_alert_rules.py がこのつながりを確かめる。
- 本番（prod2）への置き方: 合流しても prod2 には自動で届かない。前例 docs/handoff/ai-ops-247/card-login-alert-bin8.md:227 の手順4と同じに Opus が置く（今の alerts.yml を控える → main の版を置く → sha256 が main と一致）。毎日 09:23 の設定のずれの点検で誤って鳴らさないため、合流した日のうちに置く（同じ前例の手順3）。ずれは毎日 monitoring/scripts/check_config_drift.sh が数える。
- 本番での試し（2026-11-24 13時台 JST・Loki）: 同じ式の 5xx を外した版はパスキーの道で直近7日 14件に当たり、5xx 版は 0件。誤報の元は今は無い。

### 5-3. 残りの確かめを KGI の表に書く（§4）
- docs/specs/auth-login/kgi.md の「KGI 追加」に、P1〜P7 の済み/残りを日付つきで書く。

## 6. 選ばなかった案
- 毎日送る: パスキーの回数は1日0〜2回で、毎日では変化が見えない。週1にした。
- 手元の Mac の定期で数える: Mac を閉じていると動かない。本番の中の係なら止まらない（ADR-1063 便6 は 11/19〜11/24 で毎日届いた: k9 の記録）。
- 外部の監視の会社を使う: 費用が増え、データが外へ出る。

## 7. 弊害と対処
| 弊害 | 対処 |
|---|---|
| Discord の通知が週1通増える | 管理者用の部屋だけ。月曜の1通 |
| 人が分かる情報が Discord に出る | id と role だけ。名前・メール・IP・端末は出さない（viewer_share_flag_monitor.py:4 の前例） |
| 5-4 が1件で鳴る（うるさい） | パスキーの道は1日0〜14件。1件の 5xx でも人が見る価値がある。鳴りすぎたら [10m] と > 0 を見直す |
| DB の負荷 | auth_events の (event_type, created_at) の索引あり（001:19-20）。7日分の数えだけ |

## 8. 受け入れ条件

| 基準 | 検証方法 |
|---|---|
| 反映後の最初の月曜 09:10 JST に管理者用 Discord に報告が1通届く | celery-worker のログに係の `succeeded` と `"HTTP/1.1 204 No Content"` の2行（K9 と同じ読み方。2026-11-24 の毎日点検のログで同じ2行が読めると確かめた） |
| 報告の人ごとの (1)(2) の数が、同じ区切りの reader 鍵の数えと一致 | ai_ro.public__auth_events と ai_ro.public__users を同じ条件で数えて全行照合 |
| 区切りが日本時間の暦日 | backend の試験: 日曜 23:59 JST と月曜 00:00 JST の記録を入れ、前者だけが数えられる。CI の pytest 必須で緑 |
| パスキーもパスワードも0回の人は割合を「-」と書く（0で割らない） | 同じ試験に1件 |
| 画面点検 S1 が本番で緑 | 反映後の prod-ui-check の実行結果が success |
| `email webauthn` が無いと S1 が赤 | GitHub の prod-ui-check を、S1 の期待を `email webauthn-x` に変えた見本の枝で手動実行し failure を見る（見本の枝は確かめた後に消す） |
| 5-4 の見張りが prod2 で読み込まれている | prod2 の alerts.yml の sha256 が main と一致。Loki の `:3100/metrics` の `loki_ruler_` で始まり `jarvis` を含む行で、ルールの数が反映前より1本多い（前例 docs/handoff/ai-ops-247/card-stage1-bin1.md:109 の 8-4） |
| 通知に名前・メール・IP が無い | backend の試験: 送る本文に users.full_name・email の値が入らない。CI の pytest 必須で緑 |
| パスワードの成功の数え分け | backend の試験: login 200 を1件・poll approved_admin・poll approved_device・recovery 200 を1件ずつ入れて (2a) が1・(2b) が3、login 202 は数えない。割合は (1)÷((1)+(2a)) |
| 12/8・12/24 の数えが台帳にある | この PR の差分に tasks/todo.md の1行がある |
| 新しい表・列・設定なし | PR の差分に migrations と .env の変更が無い |

## 9. 維持の仕組み（だれが・何で）
守り手: .github/workflows/e2e.yml（必須チェック「Lint & Dark Mode Check (ADR-067)」が vitest を流す）・.github/workflows/prod-ui-check.yml（毎朝の本番点検）・実装後は backend/app/celery_app.py の週1の係・実装後は monitoring/loki/rules/jarvis/alerts.yml の見張り

- 壊す変更: A1・A2（必須チェック）が止める。
- 本番で壊れた: 5-2（毎朝・候補の設定）・A5（毎朝・パスワード）・5-4（10分以内・パスキーの道の 5xx）・A4（すぐ・失敗の急増）が知らせる。
- 効果: 5-1 が毎週数を届ける。読むのは Opus（毎週月曜の報告を読む）と PO。
- 決まった日の1回の数え（12/8・12/24）: 人手で守る。理由: 週の区切りと合わない1回きりの数えで、係を作るほどではない。tasks/todo.md の行を Opus がセッション開始時に読む（todo.md:3 の決まり）。
- 報告そのものが止まった: 月曜に届かないことで分かる（ADR-1063 便6 と同じ考え方）。

## 10. 外部・過去事例の参照と我々への応用
- 同じ考え方（壊れたら知らせ・緑でも定期に送る）は、この会社の ADR-1063 便6 が前例。11/19〜11/24 で毎日届き、日数を数えられた（scratchpad k9 の記録）。
- パスキーの普及の事例は design.md・evidence.md に記載済み（Microsoft・Yahoo! JAPAN・adidas ほか）。この設計は普及策ではなく見張りのため、新しい外部事例は使わない。

## 11. 未解決（PO に戻すこと）
- 実装（5-1・5-2・5-4）に進むかは PO の実装承認が要る。
- KPI の測り方に (2b)（知らない機械の確認を通ったログイン）を入れるか。今は入れない（kgi.md:47 のまま）。週報で件数が見えてから PO が決める。
- 残りの確かめ（§4 の iPhone・シークレット窓・PO の id での Android）は PO の手元の機械が要る。
