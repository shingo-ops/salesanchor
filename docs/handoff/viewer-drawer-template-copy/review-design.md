# Architect 審査 — 閲覧者管理の詳細欄に「送る文を選んでコピー」

対象: docs/handoff/viewer-drawer-template-copy/design.md（recon: 同じフォルダの recon.md）
基準: origin/main 67e5ea6b9 と PR #4581 の差分（head 5e8915b36、OPEN。/tmp/CC報告ファイル/template-copy-recon/pr4581.diff と `gh pr diff 4581` を突き合わせて一致を確認）
審査日: 2026-10-21

## 判定: REVISE

方針（サーバーで DB の本文に差し込み、1 件ずつ返す GET を足す）は既存の決めと合っており妥当。ただし受け入れ基準 2 件（K2・K10）が書いてあるとおりには検証できず、Generator に渡せない。手早く直せる範囲。

## 突合できた事実（合っている点）

- `_http_error` は main の backend/app/routers/super_admin_viewers.py:140 にある（引数 ViewerAdminError、戻りは HTTPException）。`_ERROR_STATUS["not_found"]` は 404 "viewer_not_found"（:39）。
- `_TEMPLATE_NOT_FOUND = "template_not_found"` は #4581 がモジュール直下に足す（pr4581.diff の router hunk @@ -33,6 +34,8 @@）。
- `viewer_admin._get_item(db, viewer_id)` は dict を返す（backend/app/services/viewer_admin.py:121-126）。無いときは `ViewerAdminError("not_found")`（:33-38 のクラス）。`item["email"]`・`item["trial_expires_at"]`（datetime または None。SQL :72 の列）で読める。
- `format_jst_date` は backend/app/discord_gateway/viewer_bot_texts.py:121 にあり「M月D日」（ゼロ埋めなし）。`SIGNUP_URL` は :68。#4581 は文面の定数と `*_text()` 関数を消すが、`SIGNUP_URL`・`format_jst_date`・`format_jst_datetime` は残す。
- #4581 の `render`（pr4581.diff:463-517 付近）: 6 鍵のうち signup_request は manual、他の 5 鍵（room_recreated・notice_extended・notice_activated・notice_suspended・interview_request）は台帳上 auto（backend/app/services/viewer_message_templates.py:39-49）。auto は差し込み後 2000 字を超えると None。
- Select 金型（frontend/src/components/Select.tsx）: `options[].disabled` を `<option disabled>` に渡す、`error` は下に role="alert" で出す、`size` は sm/md/lg、`data-testid` など残りの属性は `...rest` で `<select>` に渡る。placeholder の option は `required` が無いと選び直せるが、未選択のときはコピーが押せないので問題ない。
- i18n: superAdmin.viewerTemplates.names に 6 鍵の名前が ja/en 両方ある。superAdmin.viewers の新しいキー（templatePick など 4 つ）は main・#4581 のどちらとも重ならない。
- 画面テスト（frontend/src/pages/super-admin/ViewerAccountsPage.test.tsx）: `api.get` は path で分ける mock（:52-55）、`ApiError` は本物（:9-12）、clipboard の mock 例あり（:228）。K6〜K8 はこの形で書ける。
- ルート順: 同じ層には `/super-admin/viewers/{viewer_id}/logins` だけで、`{viewer_id}` だけの GET は無い。ぶつからない。
- 設計内のバッククォート付きパス 11 件は全部ある（scripts/check-process-artifacts.js の `validateFileCitations` を実行してエラー 0）。recon の 15 件も 0。受け入れ基準の表・recon への参照・ADR 参照・外部事例欄の検査（`validateDesignDoc`）もエラー 0。

## 指摘（番号つき）

### 1. 【要修正】K2 の検証方法が実在しない関数を指している
- 設計 §5 K2「面談側の生成結果（#4581 後の関数）と文字列一致」。#4581 のあと面談の文は `viewer_interview_notice.run_once` の中で `vmt.render("interview_request", body, expires_date=format_jst_date(expires_at))` をその場で呼ぶだけで、文だけを返す関数は無い（pr4581.diff の viewer_interview_notice.py hunk @@ -77,7 +88,12 @@）。
- 延長は `viewer_room_notice.prepare_notice(db, "extend", item)` が `(True, 文)` を返すので比べられる（同差分の viewer_room_notice.py）。
- 直し方（どちらかに決めて書く）:
  - 延長: 実 DB テストで、`send_room_notice` を偽物にして `/extend` を呼び、応答の `room_notice_text` と、そのあと呼んだ `template-text?key=notice_extended` の `text` を比べる（自動送信の本当の道を通る）。
  - 面談: `run_once` に実 DB のセッション作成関数・FakeRedis・偽の `send_room_notice` を渡し、送られた文と `template-text?key=interview_request` を比べる。重すぎるなら「同じ本文 DEFAULT_BODIES に同じ値を入れたものと一致（K1 と同じ）」へ基準を下げると明記する。

### 2. 【要修正】K10 の基準と検証方法が合っていない
- 基準は「本番で API が 200 で文を返す」だが、検証は「配信 JS に `template-text` が含まれる」で、200 は確かめていない。
- 直し方: 基準を「配信物に新しい画面が入り、本番 API に新しい道がある（認証なしで 401／403 が返り 404 ではない）」に変えるか、200 の確認を PO の画面操作（コピーして貼る）に回すと書く。

### 3. 【要修正・軽い】「維持の仕組み」の見出し名が検査に合っていない
- scripts/check-process-artifacts.js:529-560 は `^##.*維持の仕組み` の見出しを探す。設計の見出しは「## 10. 戻し方・維持」で、実行すると「設計docに「## 維持の仕組み」欄がありません」が出る。CI は今は警告扱い（:700-712、workflows に MAINTENANCE_ENFORCE の指定なし）だが、成果物の完了定義に合わせて「## 10. 戻し方・維持の仕組み」などに直す。

### 4. 【要修正・軽い】Stack の前提が実物と違う
- frontend/src/components/Stack.tsx:16-24 の props は direction・gap・children・className だけで `align` が無い（設計 §3-3 の `align="end"` は型エラー）。設計は「無ければ付けない」と逃げ道を書いているので、最初から付けないと書き直す。
- §8「Stack の折り返しは金型の既定に任せる」は誤り。row は `flex-wrap: nowrap; align-items: center`（frontend/src/components/Stack.css:11-15、Stack.tsx:5「折り返さない」）。ラベル付きの Select（上にラベル、下にエラー）とボタンが縦の中央で揃うので、エラーが出るとボタンの位置がずれる。スマホでは Drawer が全幅（Drawer.css:109-112）。並べ方を決めておく（例: footer を縦の Stack にし、1 段目に Select とコピー、2 段目に保存。または今の横 1 列でずれを許すと書く）。

### 5. 【要修正・軽い】契約ファイルの作り直し手順は分かっているので書く
- .github/workflows/api-contract-check.yml の手順は `cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json`（エラーメッセージにも同じ文）。型ファイル（src/api/generated）はコミット対象外。「git log で探す・無ければ停止」ではなく、この 1 行を書く（Generator は単純作業だけという決めのため）。

### 6. 【推奨】選択の初期化は `detail` ではなく `detailId` で
- `load()` は操作のたびに `setDetail` で別のオブジェクトに入れ替え（ViewerAccountsPage.tsx:123）、保存でも `setDetail(res)`（:163）。`detail` を見て初期化すると、保存しただけで選択が消える。既存の書き方（:138-146、`detailId` を見る useEffect）に合わせる。

### 7. 【推奨】2000 字を超えたときも「テンプレートが見つかりません」になる
- 5 鍵は auto なので、本文 1800 字近くに長いメールが入ると `render` が None → 503 → 画面は「テンプレートが見つかりません」。自動送信もこの場合は送らないので「同じ文」の約束とは合う。起きにくいが、§8 に「この場合も 503」と 1 行書いておく。

### 8. 【推奨】テストの書き方の細部
- K1・K4: 本文は #4581 の `_prepare(..., seed_templates=True)` が backend/tests/viewer_template_fixtures.py の DEFAULT_BODIES を入れる。503 は `_prepare(..., skip_templates=("notice_extended",))` で作れる（同差分）。期待値も DEFAULT_BODIES を使うと書く。
- K5: ROUTES に足す path は `?key=signup_request` 付きにする（キーなしでも 403 は先に出るが、意図を明確にするため）。
- router の書き方は既存に合わせ `status.HTTP_422_UNPROCESSABLE_ENTITY` などの定数と `raise _http_error(exc) from None` を使う（:181・:205 と同じ）。

### 9. 【確認のみ】前提の #4581 は 2026-10-20 15:27Z 以降更新が無く OPEN のまま
- 設計 §1 の「マージを確かめてから着手・形が違えば停止」で足りる。

## 戻ってきたら見る点
- 指摘 1・2 の直し（検証方法が実在の関数・観測で書けているか）。
- 指摘 3〜5 の文言修正。

---

# 2回目の審査（2026-10-21）

## 判定: APPROVE

## 指摘 1〜8 の反映確認
1. K2 の直しは反映済み。延長は「同じ人に `/extend` した応答の `room_notice_text` と GET（key=notice_extended）が一致」。延長で期限が変わったあとの GET も同じ DB の値を読むので、比べる意味がある。面談は「K1 と同じ基準で代える」と明記された（§5 K2）。
2. K10 の直しは反映済み。「未ログインで呼ぶと 401／403 になり 404 にならない」＋配信 JS の確認。backend/app/middleware/session_guard.py:149-151 は Authorization ヘッダーが無いとそのまま通すので、無いルートは 404、あるルートは認証の段階で 401 になり、ルートがあるかどうかを見分けられる。
3. 見出しは「## 10. 維持の仕組み」に直った。`validateMaintenanceSection` を実行してエラー 0。
4. footer は縦 2 段（1 段目に Select を fullWidth、2 段目にコピーと保存の横並び）になり、`align` は使っていない。Stack の実物（direction・gap だけ）と合う。
5. 契約ファイルの手順が 1 行で書かれた（api-contract-check.yml と同じ）。差分が想定外なら停止、という条件も付いた。
6. 初期化は `detail?.id` を見ると明記された（既存 :138-146 の書き方に揃える）。
7. 2000 字を超えたときの 503 が §8 に書かれた。
8. テストの細部（`_prepare(seed_templates)`・DEFAULT_BODIES、ROUTES は `?key=` 付き、`status.HTTP_*` と `from None`）が明記された。

## process-artifacts の検査（scripts/check-process-artifacts.js の関数を直接実行）
- validateDesignDoc（受け入れ基準の表・recon への参照・ADR-144/027/1019 の参照・外部事例欄）: エラー 0
- validateMaintenanceSection: エラー 0
- validateFileCitations（design.md・recon.md）: どちらもエラー 0

## 残っている細かい点（直さなくても通す。実装役への申し送り）
- §3-1 のコード例は `status_code=422` などの数字のままだが、その下の箇条書きが「定数と `from None` を使う」と決めているので、実装は箇条書きに従う。
- K10 の curl は `?key=signup_request` を付けて呼ぶ。付けないと、認証より先に引数の検査で 422 になる可能性が残る（ルートがあることの証明にはなるが、基準の「401／403」と食い違って見える）。

VERDICT: APPROVE
