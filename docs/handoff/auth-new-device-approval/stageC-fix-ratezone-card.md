# ADR-1055 段C 直し: 設定画面の読むだけの4つの道を入口の login 枠から外す（実装カード v1）

- 状態: 設計案作成済み・Opus 自己審査 APPROVE（同一AIの審査で、独立した第二者の審査ではない）・PO 方向承認済み（2026-11-03 PO「1」＝「この直し方で進める。設計・審査・直し・本番まで Opus が進める」）
- 担当: 実装はクラウドの Sonnet。マージ前に手元の審査役（reviewer・opus）の審査を受ける。GO・マージは PO の委任に基づき Claude Opus

## 1. 目的（PO に見える変化）
アカウント設定の SecuritySection（機械の一覧が並ぶ欄）を開くと、ログインしている機械の一覧・予備の合言葉の残り・顔/指紋の一覧・「この機械に通知を出す」が、「試行回数が多すぎます」で欠けずに出る。

## 2. 観測した事実（2026-11-03・根拠つき）
- 本番の入口（nginx）の記録（PO が `stagec-429check.sh` を2回実行。数だけ・接続元は置き換え文字）:
  - 429 は 03:22 2件・03:29 9件・03:30 4件・04:20 4件 = 19件。同じ分・同じ道で nginx の「limiting requests ... zone="login"」が19件。本体（backend）が返した429は0件
  - 04:20（JST 13:20）は直前41分呼び出しが無い（枠は満タン）状態で、/api/v1/auth/ 11本のうち4本が429。devices は2本とも429 → 通知の切替は出ない
  - 断られた道は devices・passkeys・recovery-codes/status・push-public-key の4つだけ
- 入口の枠: `nginx/nginx.conf:6` login 10回/分・`:156-158` と `:420-422` の `location /api/v1/auth/` に `burst=5 nodelay`（同時6本まで・6秒に1本回復）。本番の設定も同じ（同スクリプトのC行）
- 画面を1回開くと /api/v1/auth/ に最低7本出る（origin/main のコード）:
  - refresh 1: `frontend/src/contexts/AuthContext.tsx:112`
  - recovery-codes/status 1: `frontend/src/features/auth/RecoveryCodePrompt.tsx:78`（残り>0なら毎回）
  - push-public-key・devices: `frontend/src/pages/account-settings/PushNotifySection.tsx:59-60`
  - devices: `frontend/src/pages/account-settings/SecuritySection.tsx:46`
  - recovery-codes/status: `frontend/src/pages/account-settings/SecuritySection.tsx:155`
  - passkeys: `frontend/src/pages/account-settings/PasskeySection.tsx:35`
- 失敗時の表示: 一覧は空のまま空表示（「機械はありません」等）と失敗の文を出す（`SecuritySection.tsx:121-127`・`PasskeySection.tsx:127-133`）。通知の切替は push-public-key と devices の両方が成功しないと描かない（`PushNotifySection.tsx:58-63,85`）
- 4つの道は読むだけ（GET のみ）: `backend/app/routers/auth.py:1226` passkeys / `:1636` devices / `:1782` push-public-key / `:1788` recovery-codes/status。消す・作るは別の道（`/devices/{id}` DELETE `:1668`・`/passkeys/{id}` DELETE `:1251`・`/recovery-codes` POST `:1797`・`/push-subscriptions` POST/DELETE `:1701,:1754`）で、今回は触らない
- 4つとも本体側でログイン済みの確認がある（`Depends(get_current_user)` 系。審査で実物確認すること）。本体の回数制限 `backend/app/middleware/rate_limit.py`（ログイン済み 300回/分/人・未ログイン 60回/分/IP）は全 /api/ に掛かる
- 前例: 許可待ちの一覧は同じ理由で /api/v1/auth/ の外に置き、login 枠を使わないと決めた（`docs/handoff/auth-new-device-approval/design.md:126-129`）。そのとき「機械の一覧と取り消し・合言葉の作り直し」は login 枠に残すとしたが、設定画面が開くたびに5本・全体で7本出ることを数えていなかった（設計の入れ忘れ）

## 3. 変更（nginx/nginx.conf の1ファイルだけ）
app.salesanchor.jp の server（`location /api/v1/auth/` `:156` の直前）と api.salesanchor.jp の server（`:420` の直前）の2か所に、同じ4つの完全一致の location を足す。中身は各 server の `location /api/`（`:231-244`・`:541-554`）と同じ api 枠・同じ中継の設定。

足す塊（各 server に1回ずつ・字下げは周りに合わせ4空白）:
```
    # ADR-1055 段C 直し: 設定画面の読むだけの4つの道（GET のみ）は login 枠の外（api 枠）に置く。
    # 画面を1回開くと /api/v1/auth/ に最低7本出て、login 枠（同時6本）を超えるため（stageC-fix-ratezone-card.md）。
    # 完全一致（=）は前置きの location /api/v1/auth/ より先に選ばれる。消す・作る道（/devices/{id} など）は login 枠のまま。
    location = /api/v1/auth/devices {
        limit_req zone=api burst=50;
        limit_req_status 429;

        proxy_pass http://$backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Request-ID $request_id;
        proxy_connect_timeout 10s;
        proxy_send_timeout    60s;
        proxy_read_timeout    120s;
    }
```
同じ形で `location = /api/v1/auth/passkeys`・`location = /api/v1/auth/push-public-key`・`location = /api/v1/auth/recovery-codes/status` を続ける（4塊）。コメント3行は各 server の最初の塊の上に1回だけ。

- 中継先は各 server の既存の `/api/v1/auth/` と同じ書き方（`proxy_pass http://$backend:8000;`）。実装前に、各 server の `location /api/v1/auth/` の proxy_pass の行を実物で読み、同じ文字列にする（server ごとに違えば各 server の物に合わせる）
- 触らない: 上の2か所以外の nginx.conf・limit_req_zone の定義（`:6-12`）・frontend・backend・tests・deploy.yml・その他すべて

## 4. 選んだ理由と退けた案
- 採用: 入口で4つの読む道だけを api 枠へ。1ファイル・本体と画面は不変・戻しはこの PR の revert だけ
- 退けた案1: 画面の呼び出しを減らす（devices の2本を1本に等）→ 最少でも6本ちょうどで、つなぎ直しや別タブと重なると断られる。根本が残る
- 退けた案2: 4つを /api/v1/auth/ の外の新しい道へ移す（許可待ち一覧の前例の形）→ 本体・画面・API の形の検査・試験の差し替えが要り、変更が大きい。入口の完全一致で同じ効果が出る
- 退けた案3: login 枠そのものを広げる → パスワード・合言葉の総当たりの守りが弱くなる

## 5. 守りへの影響
- パスワード（login）・合言葉（login-requests/recovery）・許可/拒否・poll・refresh・取り消し・作り直しは login 枠のまま（守りは変わらない）
- 外す4つはログイン済みでないと中身を返さない読む道。総当たりの対象（推測される鍵）を受け取らない。本体の 300回/分/人 の上限は残る

## 6. 受入条件
| 基準 | 検証方法 |
|---|---|
| K-a 入口の設定の文法が通る | CI「nginx config check」の nginx -t が緑 |
| K-b 4つの道だけが api 枠に入り、他の /api/v1/auth/ は login 枠のまま | PR の diff が nginx/nginx.conf の追加だけ（削除0行）・`location = /api/v1/auth/` が8個・`grep -c "limit_req zone=login" nginx/nginx.conf` が変更前と同じ8 |
| K-c 本番に入った | deploy.yml の nginx 作り直しの手順が成功・本番の default.conf に `location = /api/v1/auth/devices` が2行（PO の `!` 読み取り） |
| K-d 設定画面を開いても断られない | PO がアカウント設定の SecuritySection を1回開く → 機械の一覧・予備の合言葉の残り・顔/指紋の一覧に「試行回数が多すぎます」が0件、「この機械に通知を出す」が出る（PO の目視）。本番の入口の記録で、その分の4つの道の429が0件（`stagec-429check.sh` の A・B 行） |
| K-e 守りが残る | 本番の記録で、反映後も login・refresh 等は zone=login の扱い（429が出たときの B 行の zone 名）。新たな試験は作らない（観測のみ） |

## 7. 戻し方
この PR を revert する PR を main に入れる（deploy.yml が nginx を作り直す）。deploy.yml の nginx 手順は作り直し前に nginx -t を通し、失敗したら前の設定に自動で戻す（`.github/workflows/deploy.yml:499-518`）。

## 8. 止まる条件
- 実物の proxy_pass や location の並びが本カードの行番号と食い違う → 止めて報告
- nginx -t が通らない・CI の nginx config check が赤 → 直さず報告
- nginx.conf 以外を変えたくなった → 止めて報告

## 9. 外部事例
不要。nginx の location の選ばれ方（完全一致が最優先）と limit_req の挙動は公式の仕様の範囲で、事例で裏付ける判断がない。仕様は Context7（/websites/nginx_en・2026-11-03 取得）で nginx 公式 ngx_http_core_module の location を確かめた: 「using the "=" modifier it is possible to define an exact match of URI and location. If an exact match is found, the search terminates.」。照合は正規化した URI（問い合わせ文字列を含まない）に対して行う。

## 10. 維持の仕組み
- 次に /api/v1/auth/ に読む道を足すときに同じ入れ忘れをしない見張りは、本件では作らない（未決: 別件で、画面1回あたりの login 枠の本数を数える試験を足すかを決める）
- 翌朝の本番の自動点検（prod-ui-check）が 429 0件で緑であることを段C の C-g と一緒に見る
