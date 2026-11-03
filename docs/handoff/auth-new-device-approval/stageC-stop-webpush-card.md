# ADR-1055 段C 直し: パソコン・スマホへの通知（web push）を止め、知らせはメールと画面にする（実装カード v1）

- 状態: 設計案作成済み・Opus 自己審査 APPROVE（同一AIの審査で、独立した第二者の審査ではない）・PO 方向承認済み（2026-11-03 PO「3」＝パソコンの通知は止めてメールだけにする）
- 担当: 実装はクラウドの Sonnet。マージ前に手元の審査役（reviewer・opus）の審査を受ける。GO・マージは PO の委任に基づき Claude Opus（deploy.yml を含む危険 PR・ADR-136）

## 1. 目的（PO に見える変化）
- 知らない機械からログインの依頼が来たとき、パソコンやスマホへの通知（web push）は送らない。知らせはメール（と、開いているアプリの画面）だけになる
- アカウント設定の「この機械に通知を出す」の切り替えが出なくなる
- 壊れたまま「通知を出す」がオンに見える状態（実際は届かない）を無くす

## 2. 観測した事実（2026-11-03・根拠つき）
- 本番で PO のパソコンに通知が出なかった原因: 名乗り（`WEBPUSH_VAPID_SUBJECT`）が https で終わりに「/」が付いている。送る部品（py_vapid 1.9.6）の `_check_sub` がこれを拒み、VapidException で送れなかった（PO が `stagec-k2push-diag2.sh` を実行: 終わりの「/」True・https の終わり「/」の見本が FAIL）
- 失敗の数が0に見えた理由: 06:32:42 UTC に送信失敗 → 06:32:55 に画面が購読を出し直し、`backend/app/routers/auth.py` の push-subscriptions POST の ON CONFLICT が failed_count を0に戻した（PO 実行の `stagec-k2push-diag.sh` の記録と時刻）
- メールは届いている: Gmail の受信記録で、ログイン 15:32:42 JST に対し Google の受信 15:33:08 JST（約26秒）。中身に時刻・機械（Android・Chrome）・場所「不明」
- 通知を送るかどうかは鍵3つの有無だけで決まる: `backend/app/services/web_push.py:47-51` `is_configured()` は3つとも空でないときだけ True。`:54-58` `public_key()` は未設定なら None。`backend/app/routers/auth.py:340-366` `_notify_new_request` は SSE・メールを送り、web push は is_configured() のときだけ
- 画面の切り替えは公開の鍵が文字列のときだけ描く: `frontend/src/pages/account-settings/PushNotifySection.tsx:63` と `:85`（null なら何も描かない）
- 鍵3つが本体に届く道は1本だけ:
  - `.github/workflows/deploy.yml:329-331` が .env から WEBPUSH の3行を消す（sed）
  - `.github/workflows/deploy.yml:389-391` が secrets の値で3行を書き戻す（heredoc）
  - `scripts/blue-green-cutover.sh:84` は .env にある名前だけを `--env` で渡す
  - `docker-compose.yml:155-157` は `${WEBPUSH_*:-}`（無ければ空）
- 他の確かめは3行に頼っていない: `git grep -n -i webpush -- scripts .github` の結果は deploy.yml の 329-331・389-391 の6行だけ。`.github/workflows/deploy.yml:396` の行の形の確かめ（`^[A-Z0-9_]+='[^']*'$`）は行が減っても通る
- 試験は環境を自分で作る: `backend/tests/test_web_push.py`（W-t8 `:486` など）は deploy.yml に頼らない
- 設計の取り決め: K2 全体の ○ は画面とメールで判定し、web push は「判定待ち」と分けてある（`docs/handoff/auth-new-device-approval/design.md:193`）

## 3. 変更（`.github/workflows/deploy.yml` の3行を消すだけ）
変更前（`:389-391`）:
```
            WEBPUSH_VAPID_PRIVATE_KEY='${{ secrets.WEBPUSH_VAPID_PRIVATE_KEY }}'
            WEBPUSH_VAPID_PUBLIC_KEY='${{ secrets.WEBPUSH_VAPID_PUBLIC_KEY }}'
            WEBPUSH_VAPID_SUBJECT='${{ secrets.WEBPUSH_VAPID_SUBJECT }}'
```
変更後: この3行が無い（前の `CASE_ADMIN_TOKEN=...` の次が `COMPOSE_FILE=...`）。

- 残す: `:329-331` の sed の消す行（残すことで、次の反映で本番の .env から3行が消える）
- 触らない: deploy.yml の他の行・GitHub の secrets（値は消さない）・backend・frontend・sw.js・tests・DB（購読の表と行はそのまま）・docker-compose.yml・その他すべて
- 実装前に実物の `:389-391` が上と同じ文字か読む。違えば止める

## 4. 選んだ理由と退けた案
- 採用: 本体に鍵を渡さない。コードは「鍵が無ければ送らない・切り替えを出さない」を既に持っている（§2）。1ファイル3行・データを変えない・戻しは revert だけ
- 退けた案1: GitHub の secrets を消す → 秘密の変更で PO の確認が要る操作。戻すときに値を作り直す必要が出る
- 退けた案2: 名乗りの「/」を直して通知を続ける → PO が「3」（止める）を選んだ
- 退けた案3: 画面の切り替えだけ隠す → 本体は送り続けて失敗するまま。設定の正本（鍵の有無）が2か所に分かれる

## 5. 守りへの影響
- ログインを止める仕組み（許可・拒否・番号）は変わらない
- 知らせはメール（リンクなし）と、開いているアプリの画面（SSE）で続く
- 購読の行（本番の1件）は残るが、鍵が無いので送られない

## 6. 受入条件
| 基準 | 検証方法 |
|---|---|
| S-a 変更は3行の削除だけ | PR の diff が `.github/workflows/deploy.yml` の3行削除のみ（追加0行）。`git grep -c "secrets.WEBPUSH" -- .github` が0 |
| S-b CI が緑 | PR の必須の確かめがすべて緑 |
| S-c 本番の本体に鍵が無い | 反映後、PO の `!` 読み取りで backend コンテナの環境に WEBPUSH の名前が0個（値は出さない・数だけ） |
| S-d 公開の鍵が出ない | 反映後、`GET /api/v1/auth/push-public-key` の応答の public_key が null（同じ読み取りで） |
| S-e 切り替えが消えた | PO がアカウント設定を開き「この機械に通知を出す」が無い（PO の目視） |
| S-f メールが1分以内 | 知らない機械でログイン → メールの受信時刻とログインの時刻の差が60秒以内（Gmail の受信記録） |

## 7. 戻し方
この PR を revert する PR を main に入れる（次の反映で鍵3つが .env に戻る）。通知を再び使う前に §9 の直しが要る。

## 8. 止まる条件
- 実物の `:389-391` が §3 と違う → 止めて報告
- CI が赤 → 直さず報告
- deploy.yml 以外を変えたくなった → 止めて報告

## 9. 再び通知を使う前に要る直し（今回はしない・記録のみ）
- 名乗りの終わりの「/」を受け付ける（または secrets の値を直す。秘密の変更なので PO 確認）
- 送れなかったときの記録に例外の種類を出す（今は `web push: 送れなかった id=…` だけ）
- 購読の出し直しで failed_count を0に戻さない

## 10. 別に記録する残り（今回はしない）
- メールの場所が「不明」になる理由（場所の表が本番で読めているか）はまだ確かめていない
- 英語のメール本文で「Approximate location」の前に空行が1つ多い

## 11. 外部事例
不要。止めるのは自社の鍵を渡さないことだけで、外部の仕組みの判断を含まない。py_vapid の名乗りの確かめは本番で PO が実行した結果（§2）を根拠にした。

## 12. 維持の仕組み
- 本番の鍵の有無は deploy.yml の1か所が正本。再開は revert の PR 1本で、ADR-1055 の改訂に条件（§9）を残す
