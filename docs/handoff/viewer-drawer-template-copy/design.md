<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# Phase 3 設計 — 閲覧者管理の詳細欄に「送る文を選んでコピー」を置く

**対象ADR**: ADR-144, ADR-027, ADR-1019（文面の正本は `docs/handoff/gas-viewer-fresh-fast/design.md` 段10・段11）
**recon**: `docs/handoff/viewer-drawer-template-copy/recon.md`
**日付**: 2026-10-21
**担当**: Planner（Opus）

---

## 0. 目的と PO 承認
- PO「データブロックの行をクリックしたときの下部の余白にテンプレートをコピーするボタンを設置してその人専用のメッセージを送れるように出来る？」→ 提示した 3 案に PO「1」（2026-10-21）。
- 利用者に見える変化: 閲覧者管理（super admin だけの画面）で行を押して開く詳細欄の一番下に、「送る文」の選択欄と「コピー」ボタンが出る。選んでコピーすると、その人のメールアドレスや期限が入った文がクリップボードに入る。

## 1. 前提（着手条件）
- **PR #4581（段11 便2）が main にマージされていること。** 本機能は #4581 が足す `viewer_message_templates.load_rendered(db, key, **values)` を使う。#4581 は同じ service・router・画面・locales・tests を触るため、並行して作ると衝突し、差し込み関数が二重になる。
- 実装役は着手前に `git fetch origin && git merge-base --is-ancestor <#4581 の merge commit> origin/main` で確かめ、本ブランチを origin/main へ追従させる（`git merge origin/main`）。#4581 が未マージなら着手しない。
- #4581 のマージ後に `load_rendered` の形（引数・None を返す条件）が recon と違っていたら停止して Opus へ。

## 2. 対象と対象外
- 対象の文（6つ、`COPYABLE_KEYS` の順で表示）: signup_request（申込のお願い）、room_recreated（部屋の作り直しの案内）、notice_extended（延長のお知らせ）、interview_request（面談のお願い）、notice_activated（本登録のお知らせ）、notice_suspended（停止のお知らせ）。
- 対象外: reissue_notice・reissue_notice_no_invite（申込コードは sha256 のみ、招待は保存しない→作り直さないと埋まらない。今の「コードと招待を作り直す」のまま）、room_welcome（初期パスワードは argon2 のみ）。スマホ用の別画面は作らない（Drawer はそのまま）。文面の編集・自動送信の変更はしない（#4581 の範囲）。

## 3. 変更前後

### 3-1. バックエンド `backend/app/routers/super_admin_viewers.py`
新しい GET を 1 つ足す（他のエンドポイントは触らない）。

```python
# 詳細欄からコピーできる文（その人のデータだけで埋まるもの）。表示順もこの順。
COPYABLE_KEYS = (
    "signup_request", "room_recreated", "notice_extended",
    "interview_request", "notice_activated", "notice_suspended",
)

class ViewerTemplateTextResponse(BaseModel):
    text: str

@router.get(
    "/super-admin/viewers/{viewer_id}/template-text",
    response_model=ViewerTemplateTextResponse,
    dependencies=[Depends(require_super_admin)],
)
async def viewer_template_text_endpoint(
    viewer_id: int, key: str, db: AsyncSession = Depends(get_db)
):
    if key not in COPYABLE_KEYS:
        raise HTTPException(status_code=422, detail="template_not_copyable")
    try:
        item = await viewer_admin._get_item(db, viewer_id)
    except viewer_admin.ViewerAdminError as exc:
        raise _http_error(exc)            # not_found → 404 viewer_not_found（既存の対応表）
    values: dict[str, object] = {}
    if key == "signup_request":
        values["signup_url"] = viewer_bot_texts.SIGNUP_URL
    elif key == "room_recreated":
        values["email"] = item["email"]
    elif key in ("notice_extended", "interview_request"):
        expires = item["trial_expires_at"]
        if expires is None:
            raise HTTPException(status_code=409, detail="no_trial_expiry")
        name = "until_date" if key == "notice_extended" else "expires_date"
        values[name] = viewer_bot_texts.format_jst_date(expires)
    text = await viewer_message_templates.load_rendered(db, key, **values)
    if text is None:
        raise HTTPException(status_code=503, detail=_TEMPLATE_NOT_FOUND)  # #4581 の定数を使う
    return {"text": text}
```
- `_get_item` は dict を返す（`backend/app/services/viewer_admin.py:121-126`）。`_http_error` は `backend/app/routers/super_admin_viewers.py:140`、`_TEMPLATE_NOT_FOUND` は #4581 が足す定数。書き方は既存に揃え、`status.HTTP_422_UNPROCESSABLE_ENTITY`・`status.HTTP_409_CONFLICT`・`status.HTTP_503_SERVICE_UNAVAILABLE` の定数と `raise _http_error(exc) from None` を使う。名前が #4581 マージ後に違っていたら停止して Opus へ。
- 値の作り方は自動送信と同じ（recon「自動送信が入れる値」）。同じ本文・同じ値なので、コピーの文は自動で送られる文と一字一句同じになる。
- ルート順: `/super-admin/viewers/{viewer_id}/template-text` は既存の `{viewer_id}` 系と衝突しない（パスの末尾が違う）。

### 3-2. 契約ファイル
- `frontend/api-contract/openapi.json` を `cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json` で作り直す（`.github/workflows/api-contract-check.yml` と同じ手順）。差分が新ルートと ViewerTemplateTextResponse 以外に出たら停止して Opus へ。

### 3-3. 画面 `frontend/src/pages/super-admin/ViewerAccountsPage.tsx`
- import に `Select`（`frontend/src/components/Select.tsx`）を足す。生 select は使わない。
- state: `templateKey: string`（初期 ""）、`templateError: string | null`。開いている人の id（`detail?.id`）が変わったとき（別の行を開いた・閉じた）だけ両方を初期化する。`detail` オブジェクトは load()・保存のたびに入れ替わる（`frontend/src/pages/super-admin/ViewerAccountsPage.tsx:123,163`）ので、`detail` そのものを依存にしない。既存の LINE 名の初期化（同ファイル :138-146）の書き方に揃える。
- 定数（ファイル内、文言ではないので i18n 対象外）:
  `const COPYABLE_TEMPLATE_KEYS = ["signup_request","room_recreated","notice_extended","interview_request","notice_activated","notice_suspended"] as const;`
  `const NEEDS_EXPIRY = new Set(["notice_extended","interview_request"]);`
- options: `COPYABLE_TEMPLATE_KEYS.map(k => ({ value: k, label: t(\`superAdmin.viewerTemplates.names.${k}\`), disabled: NEEDS_EXPIRY.has(k) && !detail.trial_expires_at }))`
- footer（変更後。保存ボタンは今のまま先頭に残す）:

```tsx
footer={
  detail && (
    <Stack direction="column" gap="2">
      <Select
        size="sm"
        fullWidth
        label={t(`${f}.templatePick`)}
        placeholder={t(`${f}.templatePlaceholder`)}
        options={templateOptions}
        value={templateKey}
        onChange={(e) => { setTemplateKey(e.target.value); setTemplateError(null); }}
        error={templateError ?? undefined}
        data-testid="viewers-detail-template"
      />
      <Stack direction="row" gap="2">
        <Button
          variant="secondary"
          disabled={!templateKey}
          onClick={() => { void copyTemplate(); }}
          data-testid="viewers-detail-template-copy"
        >
          {copiedKey === "template" ? t(`${f}.copied`) : t(`${f}.copy`)}
        </Button>
        <Button variant="primary" ... data-testid="viewers-detail-save">{t("common.save")}</Button>
      </Stack>
    </Stack>
  )
}
```
- 並べ方: 1 段目に選択欄（幅いっぱい・エラー文はその下）、2 段目に「コピー」と今の「保存」を横並び（Stack 金型は align を持たず横並びは折り返さない＝ `frontend/src/components/Stack.tsx:16-24`。縦 2 段にしてエラー表示やスマホの全幅でもボタンがずれないようにする）。保存ボタンの中身（onClick・disabled）は今のまま。インライン style・色直値は禁止。
- copyTemplate:
```ts
const copyTemplate = async () => {
  if (!detail || !templateKey) return;
  try {
    const res = await api.get<{ text: string }>(
      `/super-admin/viewers/${detail.id}/template-text?key=${encodeURIComponent(templateKey)}`,
    );
    copyText("template", res.text);
  } catch (e) {
    setTemplateError(templateErrorMessage(e));
  }
};
```
- templateErrorMessage: ApiError の status 409 → `${f}.templateNoExpiry`、503 → `superAdmin.viewerTemplates.unregistered` ではなく `${f}.templateNotFound`、404 → 既存 `${f}.notFoundError`、その他 → 既存 `${f}.genericError`。クリップボード失敗は既存 copyText の扱い（genericError）のまま。

### 3-4. 文言 `frontend/src/locales/ja.json`・`frontend/src/locales/en.json`（superAdmin.viewers に追加、両ファイル同じキー）
| キー | ja | en |
|---|---|---|
| templatePick | 送る文 | Message |
| templatePlaceholder | 送る文を選ぶ | Choose a message |
| templateNoExpiry | お試しの期限が無いので、この文は作れません | This message needs a trial end date |
| templateNotFound | テンプレートが見つかりません | Template not found |

文の名前は既存の superAdmin.viewerTemplates.names.<鍵> を使う（新設しない）。

## 4. 触らない範囲
- 文面の本文・台帳・validate/render・自動送信・再発行の処理・テンプレート画面（#4581 の範囲）。
- 一覧の列、Drawer 本文（LINE名〜目印）、保存の動き、ヘッダーのボタン。
- DB・migration・deploy.yml。

## 5. 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| K1 6つの鍵それぞれで、その人の値を入れた文が返る（延長・面談は JST「M月D日」、作り直しはメール、申込は SIGNUP_URL 入り） | `backend/tests/test_super_admin_viewers.py` に実 DB テスト追加。本文は #4581 の `_prepare(seed_templates=...)` と DEFAULT_BODIES で用意。期待値は同じ本文に同じ値を format したもの |
| K2 コピーの文が自動送信の文と同じ（延長） | 同テストで、同じ人に `/extend` を実行した応答の `room_notice_text` と、その後の GET（key=notice_extended）の text が文字列一致。面談は自動送信が `run_once` 内で直接 render するため、K1 の「DEFAULT_BODIES に同じ値（format_jst_date(trial_expires_at)）を入れたものと一致」で代える |
| K3 対象外の鍵（reissue_notice・reissue_notice_no_invite・room_welcome・未知）は 422 | 同テスト（パラメータ化） |
| K4 期限なしの人に延長・面談は 409、存在しない人は 404、本文の行なしは 503 | 同テスト |
| K5 super admin 以外は 403 | ROUTES 表に新ルート（`/super-admin/viewers/1/template-text?key=signup_request`）を追加（既存の 403 検査） |
| K6 詳細欄の一番下に選択欄とコピーが出る。未選択ではコピー不可。選んで押すと API の text がクリップボードに入り「Copied」表示 | `frontend/src/pages/super-admin/ViewerAccountsPage.test.tsx` に追加（api.get の path 分岐と clipboard mock） |
| K7 期限なしの人では延長・面談の選択肢が選べない（disabled） | 同テスト |
| K8 409/503 で選択欄の下にエラー文が出る | 同テスト |
| K9 i18n キーが ja/en 同一、ハードコード日本語なし、UI 金型のみ | CI（i18n チェック・lint・`scripts/check-ui-governance.js`） |
| K10 本番に新しい API と画面が載っている（未ログインの呼び出しは 401／403 で、404 にならない＝ルートがある。配信 JS に `template-text` と `viewers-detail-template` がある） | デプロイ後に Opus が curl で確認。ログインしての 200 とコピーの中身は PO の画面目視 |

## 6. 外部・過去事例の参照と我々への応用
- 該当なし：既存画面に、既存の API の作法（再発行の応答で出来上がりの文を返す `reissue-signup-code`）と同じ形の GET を 1 つ足すだけで、新しい技術選択が無いため外部事例は不要と判断。過去事例としては、段10 の「フロントに文面を持たず API の出来上がりの文をコピーする」（`docs/handoff/gas-viewer-fresh-fast/design.md:838`）をそのまま踏襲する。

## 7. 技術 How・代替案
- 採用: サーバーで DB 本文に差し込んで返す。理由: 文面の正本が DB 1 か所のまま（フロントに本文・差し込みを持たない＝データの分散なし）、自動送信と同じ関数・同じ値で一字一句同じ文になる。
- 不採用: (a) テンプレート一覧 API の copy_text をフロントで置換 → 差し込みと日付整形がフロントに二重化する。(b) 6 つ分を一度に返す API → 押していない文まで毎回作る。1 件ずつで十分。

## 8. 弊害・トレードオフ
- #4581 待ちで着手が遅れる → 対策: 設計と審査を先に済ませ、マージ直後に着手する。
- Drawer の footer が高くなる（選択欄の段が増える）→ 縦 2 段で固定し、横に並べて崩れることを避ける。
- 差し込み後 2000 字を超える本文も 503「テンプレートが見つかりません」になる → 自動送信も同じ条件で送らないので約束と矛盾しない。本文は 1800 字上限（validate）なので、差し込みで 200 字超増えるのはメールアドレスが極端に長い場合だけ。
- 期限が後から変わった人（延長直後）は、詳細欄の trial_expires_at が古いと選択肢の可否がずれる → API 側で毎回 DB から読むので、出る文は常に最新。選択肢の可否のずれは一覧の再読込で直る（許容）。

## 9. 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | #4581 マージ確認・origin/main 追従 | Sonnet |
| 2 | バックエンド GET＋テスト（K1〜K5） | Sonnet |
| 3 | 契約ファイル更新 | Sonnet |
| 4 | 画面＋文言＋テスト（K6〜K9） | Sonnet |
| 5 | コード審査 | Opus（reviewer） |
| 6 | PR・CI・マージ・デプロイ確認（K10） | Opus |

## 10. 維持の仕組み
- 戻し方: 本 PR を Revert（DB 変更なし）。
- 維持: 台帳に鍵を足すときは COPYABLE_KEYS に入れるかを決める（入れない＝詳細欄に出ない）。守り手: 人手で守る（K3 のテストが対象外の鍵を固定する）。
