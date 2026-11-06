# 段F 実装報告: 知らせメールの言葉をボタンに揃える

## 0. 注意点
- executor-preflight.sh は FAIL（GitHub API 不達・gh 未導入のクラウド環境。git fetch/push は通る。PR は作らないので続行）。
- §4-4 の前の `git grep -nE "watcher\.title"` は locales 以外の docs・台帳の文章 4 件に当たった。コード・試験からの参照は 0 件（下に生出力）。カードの趣旨（コード参照 0 件）と判断して消した。
- ja/en の葉の数は 5316 / 5316（カード記載の 5272 と数え方が違う。ja と en が同数であることが要点）。
- tsc は api/generated/schema が gitignore のため、初回は TS2307 で落ちた。`npm run generate:api-types` 後に通った（下に両方）。

## 1. HEAD の確認
```
着手時 HEAD = e63e895232a6ece76110918b3aa607ff0544f567 (origin/release/new-device-mail-wording と一致。e63e89523 で始まる)
```

## 2. git diff origin/main --stat（直しの commit 時点）
```
 .../release-new-device-mail-wording.md             |  5 ++
 backend/app/services/auth_mail.py                  |  4 +-
 backend/tests/test_new_device_approval.py          | 14 ++++
 .../stageF-mail-wording-card.md                    | 98 ++++++++++++++++++++++
 frontend/src/locales/en.json                       |  1 -
 frontend/src/locales/ja.json                       |  1 -
 6 files changed, 119 insertions(+), 4 deletions(-)
```

## 3. 変えた行の git diff（直しの commit）
```diff
diff --git a/backend/app/services/auth_mail.py b/backend/app/services/auth_mail.py
index 69b14b9d8..ed610bc69 100644
--- a/backend/app/services/auth_mail.py
+++ b/backend/app/services/auth_mail.py
@@ -170,3 +170,3 @@ _NEW_DEVICE_BODY = """Sales Anchor に、新しい機械からのログインが
 {note}
-心当たりがなければ、いつもの機械でアプリを開いて「私ではない」を押し、パスワードを変えてください。
+心当たりがなければ、いつもの機械でアプリを開いて「私ではありません」を押し、パスワードを変えてください。
 このメールにリンクはありません。
@@ -180,3 +180,3 @@ Approximate location: {location}
 
-If this was not you, open the app on a device you usually use, press "This is not me", and change your password.
+If this was not you, open the app on a device you usually use, press "This wasn't me", and change your password.
 This email contains no links.
diff --git a/backend/tests/test_new_device_approval.py b/backend/tests/test_new_device_approval.py
index 6ed1a3a8a..24e8c72e9 100644
--- a/backend/tests/test_new_device_approval.py
+++ b/backend/tests/test_new_device_approval.py
@@ -421,2 +421,16 @@ def test_k2_mail_has_no_link_and_includes_time_device_location():
 
+def test_k2_mail_button_name_matches_screen_button():
+    """メールに書く押すボタンの名前は、画面のボタンの言葉（ja.json / en.json の notMe）と同じ（段F）。"""
+    import json
+    from pathlib import Path
+
+    from app.services import auth_mail
+
+    locales = Path(__file__).resolve().parents[2] / "frontend" / "src" / "locales"
+    ja = json.loads((locales / "ja.json").read_text("utf-8"))["login"]["deviceApproval"]["watcher"]["notMe"]
+    en = json.loads((locales / "en.json").read_text("utf-8"))["login"]["deviceApproval"]["watcher"]["notMe"]
+    assert f"「{ja}」" in auth_mail._NEW_DEVICE_BODY
+    assert f'"{en}"' in auth_mail._NEW_DEVICE_BODY
+
+
 # ── K3: 許可して入る ─────────────────────────────────────────────
diff --git a/frontend/src/locales/en.json b/frontend/src/locales/en.json
index 5f76f2558..cbecedf75 100644
--- a/frontend/src/locales/en.json
+++ b/frontend/src/locales/en.json
@@ -706,3 +706,2 @@
       "watcher": {
-        "title": "Sign-in request from a new device",
         "body": "Someone is trying to sign in to your account from an unknown device.",
diff --git a/frontend/src/locales/ja.json b/frontend/src/locales/ja.json
index 53c62a9c1..d8acf1a6f 100644
--- a/frontend/src/locales/ja.json
+++ b/frontend/src/locales/ja.json
@@ -706,3 +706,2 @@
       "watcher": {
-        "title": "新しい機械からのログイン依頼",
         "body": "あなたのアカウントに、知らない機械からログインしようとしています。",
```

## 4. (a) 直す前に落ちた（生出力。長い行は pytest の表示のまま）
```
$ python -m pytest --no-cov -p no:cacheprovider tests/test_new_device_approval.py -k button_name_matches -x -q
>       assert f"「{ja}」" in auth_mail._NEW_DEVICE_BODY
E       AssertionError: assert '「私ではありません」' in 'Sales Anchor に、新しい機械からのログインがありました。\n\n日時（日本時間）: {when}\n機械: {device}\n場所の目安: {location}\n{note}\n心当たりがなければ、いつもの機械でアプリ...assword.\nThis email contains no links.\n---------------------------------------------\n\n{geo_credit}\nSales Anchor\n'
tests/test_new_device_approval.py:432: AssertionError
FAILED tests/test_new_device_approval.py::test_k2_mail_button_name_matches_screen_button
1 failed in 2.77s
```

## 5. (b) 直した後に通った（生出力）
```
$ python -m pytest --no-cov -p no:cacheprovider tests/test_new_device_approval.py -k button_name_matches -q
.                                                                        [100%]
1 passed in 2.12s
```

## 6. 確かめ
### (1) test_new_device_approval.py 全件（backend。venv は uv で requirements.txt + requirements-dev.txt を入れた。DB 不要で全件動いた）
```
$ python -m pytest --no-cov -p no:cacheprovider tests/test_new_device_approval.py -q
............................................................             [100%]
60 passed, 483 warnings in 19.94s
```
### (2) grep
```
$ grep -n "私ではない\|This is not me" backend/app/services/auth_mail.py; echo "grep exit=$?"
grep exit=1      （0 件）
```
### (3) 葉の数
```
$ node -e '(葉を数える)'
ja 5316
en 5316
```
### §4-4 の前の git grep（生出力）
```
.claude-pipeline/active-work.d/release-new-device-mail-wording.md:5:| ...（台帳の文章）
docs/handoff/auth-new-device-approval/stageD-notice-detail-impl-report.md:50:- 使わなくなったキー `login.deviceApproval.watcher.title` は…消していない
docs/handoff/auth-new-device-approval/stageE-badge-modal-card.md:206:- 使わないキー `watcher.title` の掃除（別件）
docs/handoff/auth-new-device-approval/stageF-mail-wording-card.md:73 / :84（カード自身の文章）
```
コード（frontend/src・tests）で `watcher.title` を読む行は 0 件（`git grep` で除外 docs/.claude-pipeline/locales 後、title は出ない）。

### (4) frontend
```
$ npm ci          → 完了
$ npx tsc --noEmit（1回目。生成物なし）
src/features/tcg-sold-out/soldOutApi.ts(3,45): error TS2307: Cannot find module '../../api/generated/schema' ...
src/pages/inventory/OwnInventoryPage.tsx(11,33): error TS2307: ...
src/pages/super-admin/components/SoldOutResultsPanel.tsx(34,27): error TS7006 ...
tsc exit=2
$ npm run generate:api-types
🚀 api-contract/openapi.json → src/api/generated/schema.d.ts [1.2s]
$ npx tsc --noEmit
tsc exit=0
$ npm run lint
✖ 59 problems (0 errors, 59 warnings)      lint exit=0
$ npx vitest run --project unit src/features/auth/LoginRequestDecision.test.tsx src/components/NoticeBell.test.tsx
 Test Files  2 passed (2)
      Tests  10 passed (10)
```
（lint の警告 59 件は error 0。今回触ったのは json・py のみで、警告が tsx 側のものであることまでは確認したが、変更前との件数比較はしていない＝未確認。）

### (5) check-before-submit.sh
```
合計 10.3 秒 / 必須 16 件を表示 / 流した検査 18 件 / 落ちた検査 0 件
結果: ○ 流した検査は全部通りました（終了コード 0）
```
（版の違い: 手元 Python 3.11 / CI 3.12。最後の判定は CI。）
