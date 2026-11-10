# recon: アプリ本体が取引を開いたままにして本番反映の点検を止めた件

状態: 調査済み（C1〜C3 を実測で解いた）。基準: origin/main 4cc17871f（fetch 済。対象ファイルは d06f150c7 から差分なし）。PO 2026-11-10「1」（理由を調べ、直す設計案を作る）。
生出力の置き場（社内のみ・PR に載せない）: /tmp/CC報告ファイル/replay-bin2/ の deploy-5364-failed.log・deploy-5364-retry.log・idle-tx-sample-20261110T121412Z.txt・idle-tx-sample-20261110T122507Z.txt・nginx-stream-20261110T122428Z.txt・nginx-window-check.txt・waitfor-check.txt・inbox-stream.txt・leads-stream.txt。IP は伏せてある。

既存 ADR の検索（`git grep -i` で SSE・stream・idle in transaction・get_db）: ADR-1016（即時反映の通り道は1本）、ADR-1037（移行前の点検）、ADR-1070（借りた接続の後始末・Proposed）、ADR-131（テナント文脈の後始末）。SSE が DB 接続を握ってはいけないと書いた ADR の行は無い（コードの docstring だけ。A-12）。

## A. 事実

1. 【事実】本番反映 run 42805522437 の 1 回目（2026-11-10 11:12〜11:22Z）は「Check open DB transactions before deploy」で止まった。115 回数えて 0 本が 3 回続かず、600 秒の上限で止まった（deploy-5364-failed.log・`STOP: open transactions did not clear within 600s (last count=2)`）。
2. 【事実】止まったときの握り手は 2 本。どちらも `salesanchor_app|salesanchor_backend|idle in transaction`。pid 122539 は 20 秒・表 `permissions,role_permissions,roles,tenants,user_roles,users`。pid 122170 は 13 秒・表 `users`。一時コンテナは 0 個。
3. 【事実】0 本の回は 227 秒目から約 32 秒おきに出た（227・264・296・327・359・396・428・459・491 秒。deploy-5364-failed.log）。
4. 【事実】2 回目（11:31Z）は 3 回続けて 0 本で 11 秒で通り、反映・移行・動作確認まで成功した（deploy-5364-retry.log）。
5. 【事実】点検の数え方は `state IN ('idle in transaction', 'idle in transaction (aborted)') AND now() - xact_start > 5 秒`（`scripts/deploy-db-precheck.sh` :49-53）。
6. 【事実】アプリの DB 接続は `get_db()` の yield 依存（`backend/app/database.py` :70-85）。後始末は応答を送り終えた後の finally。application_name は `salesanchor_backend`（同 :16）。pool_size=20・max_overflow=10（同 :27-28）。
7. 【事実（公式文書 Context7 /websites/fastapi_tiangolo）】yield 依存の既定は `scope="request"` で、後始末は応答を送り終えた後に走る。本番は fastapi==0.136.3（`backend/requirements.txt` :1）。
8. 【事実】握り手の表は、認証の4つの関数が読む表と一致する。`get_current_user`（`backend/app/auth/dependencies.py` :112-130）→ users、`get_current_tenant`（同 :235-286。最後の文は :274-281 の `SET app.is_operator = ''`）→ tenants、`load_user_permissions`（同 :537-563。最後の文は `SELECT key FROM public.permissions`）→ user_roles・role_permissions・permissions、`get_user_system_keys` → roles。認証の道に commit は無い。
9. 【事実】流し続ける口（SSE）は 3 つ。
   - `/api/v1/events/stream`: DB 依存を持たず、短いセッションで認証して閉じてから流す（`backend/app/routers/realtime_events.py` :53-71）。試験 `backend/tests/test_realtime_events.py` :52-73 が「最初のかたまりを受け取った時点で DB セッションが閉じている」を確かめている。
   - `/api/v1/conversations/stream`: 経路に `Depends(require_permission("messaging.view"))` と `Depends(get_current_tenant)`（`backend/app/routers/meta_inbox.py` :1045-1052）。さらに登録時に `dependencies=[Depends(get_current_tenant)]`（`backend/app/main.py` :556-559）。
   - `/api/v1/leads/stream`: 経路に `Depends(require_permission("leads.view"))` と `Depends(get_current_tenant)`（`backend/app/routers/leads.py` :2938-2945）。登録時にも `get_current_tenant`（`backend/app/main.py` :418-421）。
10. 【事実】画面は `/api/v1/conversations/stream` を全画面の外枠から開く（`frontend/src/components/DesktopShell.tsx` :141・`frontend/src/components/MobileShell.tsx` :116）。`/api/v1/leads/stream` はリード画面だけ（`frontend/src/pages/leads/LeadsPage.tsx` :159）。
11. 【事実】`frontend/src/hooks/useSSE.ts` は、つながったら待ちを 2 秒に戻し（:63）、流れが終わると 2 秒後につなぎ直す（:90・:93-100）。
12. 【事実】`/api/v1/events/stream` の docstring（`backend/app/routers/realtime_events.py` :65-67）に「yield 依存はストリーム送出が終わるまで閉じず、SSE 1 本ごとに DB 接続を握り続けてしまう」とある。ADR-1016 の本文に同じ趣旨の行は無い（`docs/adr/ADR-1016-realtime-change-signal-standard.md` を DB・接続・セッションで grep）。
13. 【事実】`salesanchor_app` に idle_in_transaction_session_timeout を付ける設定は repo に無い。

## B. C1〜C3 を解いた実測

### C1: 握り手はどの要求から来るか → `/api/v1/conversations/stream`
- 基準（タブなし・12:14〜12:19Z、idle-tx-sample-20261110T121412Z.txt）: 5 秒より長い握り手は 0 本。0 秒の `SELECT 1`（接続の生存確認）だけ。
- 実験（Chrome でアプリのダッシュボードを 1 枚だけ開く・12:25:20〜12:27:50Z、idle-tx-sample-20261110T122507Z.txt）: 開いている間、`salesanchor_backend` の idle in transaction が常に 1 本あった。取引の開始は 12:25:20・12:25:53・12:26:25・12:26:57・12:27:31 と約 32 秒ごとに入れ替わり、各回 24〜29 秒まで伸びた。最後の文は `SELECT key FROM public.permissions` または `SET app.is_operator = ''`（A-8 の最後の文と一致）。接続元は全部 172.19.0.13。
- タブを閉じた後（12:28:19 の回）: 5 秒より長い握り手は 0 本に戻った。
- ブラウザの通信記録: 約 60 秒の間に `/api/v1/conversations/stream` が 2 回、どちらも 200（つなぎ直し）。
- nginx（12:05〜12:08Z、nginx-stream-20261110T122428Z.txt）: 別の利用者（Windows の Chrome）が各画面で conversations/stream と events/stream を開いていた。

### C2: 1 本の流れの間、取引は開いたままか → 開いたまま
- A-8 のとおり認証の道に commit が無い。A-6・A-7 のとおり get_db の後始末は流れを送り終えた後。実験の握り手は流れの 1 本と同じ長さ（約 30 秒）だけ続き、最後の文は認証の文のまま（C1）。

### C3: 約 30 秒で入れ替わる理由 → 流れが 30 秒で自分で終わり、2 秒後につなぎ直す
- `stream_inbox_updates` は `asyncio.wait_for(gen.__anext__(), timeout=30)` で待つ（`backend/app/routers/meta_inbox.py` :1078、inbox-stream.txt）。
- 手元の確かめ（Python 3.14.3、waitfor-check.txt）: 時間切れで `__anext__()` が取り消されると非同期ジェネレータが閉じ、次の呼び出しは StopAsyncIteration になる。`stream_inbox_updates` は StopAsyncIteration で抜ける（同 :1082-1083）ので、1 本は約 30 秒で終わる。本番の Python 3.12 では確かめていない（C3 の結論は本番の 32 秒周期の実測 A-3・B-C1 で裏付けた）。
- 30 秒＋2 秒（A-11）＝ 32 秒の周期。1 枚のタブで約 32 秒のうち約 25 秒（5 秒を超える部分）握り手が 1 本になる。点検は「5 秒おきに 3 回続けて 0 本」なので、タブが 2 枚以上あると通りにくい（A-3 の 0 本の回はまばら）。

### 別の不具合（今回の原因ではない）
- `/api/v1/leads/stream` は本番で 422 を返している（nginx 12:06:08Z・12:08:07Z の 2 回、155 バイト）。理由: 同じ leads 経路の `/leads/{lead_id}`（`backend/app/routers/leads.py` :367-373、`lead_id: int`）が先に登録されていて（:2938 より前）、"stream" が数字にならず 422 になる。流れに入らないので長い握り手にはならない。リード画面の即時更新は今も届いていない。
- 受信箱の流れが 30 秒で切れる間（約 2 秒）に来た合図は届かない（C3）。

## C. 未確認
- U1: 本番反映 1 回目（11:12〜11:22Z）の握り手 pid 122539・122170 が conversations/stream だったこと（nginx の記録は 11:35:03Z の入れ替えで消えた。nginx-window-check.txt）。表と周期の一致（A-2・A-3・A-8）は実験（B-C1）と同じ形。
- U2: 本番の Python 3.12 での wait_for の動き（C3 の手元確かめは 3.14.3）。
