# コード審査 — 閲覧者管理の詳細欄に「送る文を選んでコピー」

- 対象: ブランチ `release/viewer-drawer-template-copy`、HEAD `edab32d8f`（実装コミット。`bb8676c6c` は origin/main の取り込み）
- 差分: `git diff origin/main...HEAD`（merge-base 5bf64c911）
- 正本: `docs/handoff/viewer-drawer-template-copy/design.md`（§3・§4・§5）、`docs/handoff/viewer-drawer-template-copy/review-design.md`（2回目 APPROVE）
- 審査日: 2026-10-21
- 審査役: Opus（読み取りと検査の実行のみ。製品コードは変更していない）

## 判定: APPROVE

重大・要修正の指摘はない。下の Low / Info は直さずに通してよい。

## 実行した検査（観測値）

| 検査 | 結果 |
|---|---|
| `npx vitest run src/pages/super-admin/ViewerAccountsPage.test.tsx` | 34 passed（K6〜K9 の新規 6 件を含む） |
| `npx tsc --noEmit -p .`（frontend） | exit 0 |
| `npx eslint` 変更 2 ファイル | exit 0 |
| `node scripts/check-ui-governance.js`（BASE=merge-base） | 新規ハードコードなし |
| `node frontend/scripts/check-i18n-missing-keys.js` | PASSED |
| `pytest tests/test_super_admin_viewers.py`（python3.12 + requirements.txt の venv、PG なし） | 16 passed, 40 skipped（PG 試験 K1〜K4 は skip。CI で走る） |
| openapi 再生成（python3.12 venv に `backend/requirements.txt` をそのまま入れ、`ENVIRONMENT=test python -m tools.export_openapi`） | コミット済み `frontend/api-contract/openapi.json` と `diff` 差分 0 行 |

## 観点別の確認

### 1. 設計どおりか
- ルート `GET /super-admin/viewers/{viewer_id}/template-text`、`response_model=ViewerTemplateTextResponse`、`dependencies=[Depends(require_super_admin)]`: `backend/app/routers/super_admin_viewers.py:193-199`。設計 §3-1 と一致。
- `COPYABLE_KEYS` 6 種・順序: `backend/app/routers/super_admin_viewers.py:39-47`。設計 §2 と一致。
- エラー: 422 `template_not_copyable`（:202）、404 は `_http_error(exc) from None`（:206、`_ERROR_STATUS["not_found"]` :52）、409 `no_trial_expiry`（:215）、503 `_TEMPLATE_NOT_FOUND`（:220）。いずれも `status.HTTP_*` 定数（review-design 申し送りどおり）。
- 差し込み値は自動送信と同じ関数・同じ値:
  - 延長: `backend/app/services/viewer_room_notice.py:54-60` が `format_jst_date(item["trial_expires_at"])` を `until_date` に入れる。新ルート :212-217 も同じ。
  - 面談: `backend/app/discord_gateway/viewer_interview_notice.py:92` が `expires_date=format_jst_date(expires_at)`。新ルートも `expires_date`。
  - 作り直し: `backend/app/discord_gateway/viewer_trial.py:200` が `email=email`。新ルートは `item["email"]`。
  - 申込: 既存 `signup_request_endpoint`（:186）と同じ `SIGNUP_URL`。
- `load_rendered` は #4581 の `backend/app/services/viewer_message_templates.py:160-165`（None を返す条件: 行なし・検査不合格・差し込み不可）をそのまま使用。

### 2. 正しさ
- DB セッション: `Depends(get_db)` で既存 `signup_request_endpoint`（:184）と同じ。読み取りのみで commit なし。
- テナント/RLS: 本ルーターは既存全ルートとも `get_db` のみで tenant context を設定していない（`grep tenant` 該当なし）。新ルートも同じ扱い。対象表は `public.viewer_accounts`・テンプレート表で、既存ルートと差はない。
- None の扱い: `trial_expires_at is None` は延長・面談だけ 409。`load_rendered` の None は 503。`activate`/`suspend` は値なしで呼び、既存 `prepare_notice`（:62-65）と同じ。
- 422 検査を `_get_item` の前に置くため、対象外の鍵は存在しない人でも 422（設計 §3-1 のコード例と同じ順）。
- 既存の `test_404_for_missing_viewer`（`backend/tests/test_super_admin_viewers.py:456-463`）は ROUTES の `/1/` を含む口を 424242 に置き換えて 404 を期待する。新しい ROUTES 行は `key=signup_request`（対象の鍵）なので 422 にならず 404 になり、既存試験とも整合。

### 3. 画面
- `Select` 金型を import（`frontend/src/pages/super-admin/ViewerAccountsPage.tsx:26`）、使用は :480-497。生 select・インライン style・色直値なし（UI governance 検査も合格）。
- 文言はすべて `t()`。新キー 4 つは ja/en 同じ位置・同じキー（`frontend/src/locales/ja.json:2781-2784`、`frontend/src/locales/en.json:2781-2784`）。文の名前は既存 `superAdmin.viewerTemplates.names.<鍵>` を使用。
- 選択のリセット: `useEffect(..., [detailId])`（:159-164、`detailId = detail?.id ?? null` :154）。`detail` オブジェクトそのものは依存にしていない。
- 期限なしの人: `disabled: NEEDS_EXPIRY.has(k) && !detail.trial_expires_at`（:488）。
- コピー未選択時は `disabled={!templateKey}`（:501）。エラー表示は 409→templateNoExpiry、503→templateNotFound、404→既存 notFoundError、他→genericError（:226-233）。設計 §3-3 と一致。
- footer は縦 2 段（Select / [コピー, 保存]）。保存ボタンの onClick・disabled は変更前のまま。

### 4. テストが受け入れ基準を検査しているか
- K1 `test_template_text_returns_each_key_with_viewer_values`: 6 鍵すべてで DEFAULT_BODIES に同じ値を format した文と完全一致を確認。期限値は DB から読み直した `trial_expires_at` を `format_jst_date` に通しており、JST「M月D日」を自動送信と同じ関数で検査している。
- K2 `test_template_text_matches_auto_sent_extend_text`: `/extend` 応答の `room_notice_text` が空でないことを確認したうえで、その後の GET と文字列一致。面談は設計どおり K1 で代替。
- K3: 4 鍵（reissue_notice・reissue_notice_no_invite・room_welcome・unknown_key）で 422 と detail を確認。
- K4: 409（pending・期限なし、2 鍵）、404（viewer_not_found）、503（`skip_templates=("notice_activated",)`）を status と detail の両方で確認。
- K5: ROUTES に `?key=signup_request` 付きで追加 → 既存 `test_non_super_admin_gets_403_on_all_routes`（:134）がローカルで合格。
- K6: 未選択で disabled、選択後 enabled、押すと API の text が `writeText` に渡り「コピーしました」表示。
- K7: 期限なし（Sato）で延長・面談が disabled、他は enabled。期限あり（Taro）で enabled。
- K8: 409・503 でそれぞれの文言が表示される。
- K9（設計では CI 検査）: i18n・UI governance・lint をローカルで実行し合格。画面テストの「K9」は別の行を開いたときのリセット確認で、設計 §3-3 のリセット仕様を検査している。

### 5. openapi.json
- 実装担当は新ルートと `ViewerTemplateTextResponse` の 2 か所（70 行）を手で取り込んだ。
- 審査役が python3.12 venv に `backend/requirements.txt`（pydantic 2.10.6・fastapi 0.136.3）を入れて CI と同じコマンドで再生成した結果、コミット済みファイルとの差分は 0 行。CI の api-contract-check は一致する見込み（同じ依存・同じコマンドでの観測値）。
- 位置も `sort_keys=True` の順（`ViewerTemplateListResponse` < `ViewerTemplateTextResponse` < `ViewerTemplateUpdate`、`.../{viewer_id}/suspend` < `.../template-text` < `.../unsuspend`）に合っている。

### 6. 触らない範囲
- `git diff origin/main...HEAD --name-only` に migrations・deploy.yml・`viewer_message_templates.py`・`viewer_bot_texts.py`・`viewer_room_notice.py`・テンプレート画面は含まれない。変更は router（追加のみ）・tests・locales・ViewerAccountsPage（footer と state・関数の追加）・openapi・handoff 文書・active-work の 11 ファイル。
- 既存エンドポイントの本体変更なし（router の差分は定数・モデル・新関数の追加のみ）。

## 指摘

1. 【Low】`.claude-pipeline/active-work.d/release-viewer-drawer-template-copy.md:5` の状態が「WIP（設計 APPROVE・#4581 マージ待ち）」のまま。#4581 はマージ済みで実装も入っているので、PR 起票時に状態を更新すると台帳と実態が合う。
2. 【Info】`copyTemplate`（`frontend/src/pages/super-admin/ViewerAccountsPage.tsx:235-246`）は API 応答を待ってから `navigator.clipboard.writeText` を呼ぶ。ブラウザによってはクリック直後でないと書き込みを拒む場合があるが、既存の `copySignupRequest`（:215-223）と同じ作りで、失敗時は既存どおり genericError が出る。本 PR 固有の問題ではない。PO の画面目視（K10）で実機確認する。
3. 【Info】設計 §3-3 本文は「保存ボタンは今のまま先頭に残す」と書くが、同じ節のコード例は「コピー、保存」の順。実装はコード例に従った（:499-515）。設計内の食い違いで、実装の誤りではない。
4. 【Info】K10（本番の curl とログイン後の画面目視）はデプロイ後の確認でこの審査の対象外。curl は review-design の申し送りどおり `?key=signup_request` を付けて呼ぶ。

VERDICT: APPROVE
