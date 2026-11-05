# 段F 実装カード: 知らせメールの言葉をボタンに揃える・使っていない言葉を消す（ADR-1055 後片付け）

状態: 設計案作成済み・Opus 自己審査済み（§10）。PO 承認: 2026-11-05 PO「1」（メールの言葉と使っていない言葉を直す）＋「確立したなら進める」。

## 1. 目的（PO の言葉）
- PO が選んだ「1. メールの言葉と使っていない言葉を直す」。
- 利用者に見える変化: 新しい機械の知らせメールに書かれた押すボタンの名前が、画面のボタンの名前と1字も違わなくなる（日本語・英語の両方）。

## 2. 根拠（実物。基準 origin/main 9b96f0764）
- メールの日本語: `backend/app/services/auth_mail.py:171` 「…アプリを開いて「私ではない」を押し、パスワードを変えてください。」
- メールの英語: `backend/app/services/auth_mail.py:181` `press "This is not me"`
- 画面のボタンの日本語（正本）: `frontend/src/locales/ja.json:714` `"notMe": "私ではありません"`
- 画面のボタンの英語（正本）: `frontend/src/locales/en.json:714` `"notMe": "This wasn't me"`
- ボタンを出す場所: `frontend/src/features/auth/LoginRequestDecision.tsx:123` `t("login.deviceApproval.watcher.notMe")`
- 使っていない言葉: `frontend/src/locales/ja.json:707` `"title": "新しい機械からのログイン依頼"`、`frontend/src/locales/en.json:707` `"title": "Sign-in request from a new device"`。
  - `git grep -nE "watcher\.title"` は locales 以外 0 件（frontend・tests・scripts・backend）。
  - `git grep` で `watcher[` や `` `login.deviceApproval.watcher `` などの組み立てて読む書き方も 0 件。
  - 使っていた `LoginApprovalWatcher.tsx` は段D で消した。
- watcher の他の言葉（body・device・location・time・unknown・pickNumber・notMe・rejectedTitle・rejectedBody・changePassword）はすべて使われている（`LoginRequestDecision.tsx:99-131`・`NoticeBell.tsx:170`）。消すのは title だけ。
- メールの今の試験: `backend/tests/test_new_device_approval.py:398-419` `test_k2_mail_has_no_link_and_includes_time_device_location`。ボタンの名前は確かめていない。だから食い違いが CI で見つからなかった。
- backend の試験が frontend の正本を読む前例: `backend/tests/seed_data.py:22`（`Path(__file__).resolve().parents[2] / "frontend" / ...`）、`backend/tests/test_realtime_topics.py:133`。

## 3. 決めたこと（選んだ理由）
- 正本は画面の言葉（ja.json / en.json の notMe）。メールの文はその写し。
- 写しが正本とずれたら CI で落ちる試験を足す（同じ種類のミスを二度と通さない）。
- 選ばなかった案: backend が実行時に ja.json を読む。本番の backend の入れ物に frontend の言葉のファイルがあるかは確かめていない。仕組みも増える。だから試験で揃いを守る。
- `backend/app/routers/auth.py:1608` の説明文と `frontend/api-contract/openapi.json:41918` の「私ではない」は、利用者に見えない内部の説明なので触らない（触ると API の約束ファイルの作り直しが要る）。

## 4. 触る範囲（変更前→変更後）

### 4-1. `backend/app/services/auth_mail.py:171`
- 前: `心当たりがなければ、いつもの機械でアプリを開いて「私ではない」を押し、パスワードを変えてください。`
- 後: `心当たりがなければ、いつもの機械でアプリを開いて「私ではありません」を押し、パスワードを変えてください。`

### 4-2. `backend/app/services/auth_mail.py:181`
- 前: `If this was not you, open the app on a device you usually use, press "This is not me", and change your password.`
- 後: `If this was not you, open the app on a device you usually use, press "This wasn't me", and change your password.`
- `_NEW_DEVICE_BODY` は `"""` の文字列で `.format()` に渡す。`'` は `{` `}` を含まないのでそのまま書いてよい。

### 4-3. `backend/tests/test_new_device_approval.py`：試験を1つ足す
- 置き場所: `test_k2_mail_has_no_link_and_includes_time_device_location` の直後（今の :419 の後・:422 の `# ── K3` の前）。
- 中身（このとおり書く）:
```python
def test_k2_mail_button_name_matches_screen_button():
    """メールに書く押すボタンの名前は、画面のボタンの言葉（ja.json / en.json の notMe）と同じ（段F）。"""
    import json
    from pathlib import Path

    from app.services import auth_mail

    locales = Path(__file__).resolve().parents[2] / "frontend" / "src" / "locales"
    ja = json.loads((locales / "ja.json").read_text("utf-8"))["login"]["deviceApproval"]["watcher"]["notMe"]
    en = json.loads((locales / "en.json").read_text("utf-8"))["login"]["deviceApproval"]["watcher"]["notMe"]
    assert f"「{ja}」" in auth_mail._NEW_DEVICE_BODY
    assert f'"{en}"' in auth_mail._NEW_DEVICE_BODY
```
- 先に確かめること: ja.json の最上位に `login` があり、その下に `deviceApproval.watcher.notMe` があること（`python3 -c` で読んで値を出す）。無ければ止まる。

### 4-4. `frontend/src/locales/ja.json:707` と `frontend/src/locales/en.json:707`
- `"title": ...,` の1行を消す（watcher の中の1行だけ。`detail.title` や他の title は消さない）。
- 消した後もキーの数が ja と en で同じこと（今 5272 / 5272 → 5271 / 5271）。

### 4-5. 台帳 `.claude-pipeline/active-work.d/release-new-device-mail-wording.md`
- Opus が作成済み。実装役は触らない。

## 5. 触らない範囲
- `backend/app/routers/auth.py`・`frontend/api-contract/openapi.json`・ADR-1055・design.md の「私ではない」（内部の説明・過去の設計記録）
- 画面の部品・CSS・トークン（見た目は変えない）
- DB・migrations・deploy.yml・secrets・workflow・scripts
- メールの件名・他のメール（パスワード再設定など）

## 6. 想定される分岐（迷ったら止まる）
- `git grep -n "watcher.title"` などで locales 以外に1件でも当たった → 消さずに止まり、当たった場所を報告。
- ja.json / en.json の watcher の中身が §2 と違う（行がずれている・title が無い）→ 止まる。
- 足した試験が、直す前の文（4-1・4-2 の前）で落ちることを確かめる。直す前に通ってしまったら試験の書き方が違うので止まる。
- i18n のキー検査（`check-i18n` 等）が落ちた → 止まって生出力を報告。

## 7. 受入条件

| # | 基準 | 検証方法 |
|---|---|---|
| K1 | メールの日本語に「私ではありません」、英語に "This wasn't me" がある。「私ではない」「This is not me」は auth_mail.py に 0 件 | `grep -n` |
| K2 | 足した試験が、直す前の文では落ち、直した後は通る | 実装役が順に流した pytest の生出力（落ちた→通った） |
| K3 | ja.json / en.json の watcher.title が無い。キー数が ja と en で同じ | `node -e` で葉の数を数える |
| K4 | `test_new_device_approval.py` 全件・frontend の vitest（LoginRequestDecision・NoticeBell）・tsc・lint が通る・必須 CI 緑 | 実装報告の生出力と CI |

## 8. 戻し方
- PR を revert する。DB の変更が無いので、revert とデプロイだけで元に戻る。

## 9. 外部事例
- 該当なし。理由: 社内の言葉の揃えであり、外部の事例で判断することがない。

## 10. Opus 自己審査（同じAIによる審査。独立した第三者の審査ではない）
- 根拠はすべて origin/main 9b96f0764 の実物の行番号で確かめた（`/tmp/CC報告ファイル/cleanup/recon1.txt`〜`recon3.txt`）。
- 正本は locales に1つ。メールは写しで、ずれは試験で止まる。データを分散させていない。
- 画面の見た目は変えない（トークン・金型に触れない）。
- 未解決の前提: なし。
- 判定: APPROVE
