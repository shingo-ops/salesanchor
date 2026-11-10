# 設計審査 — 受信箱の通知の流れが DB の取引を開いたままにする件

同じ AI（Claude Opus）による審査であり、独立した第二者の審査ではない。審査役はクラウドの一回実行（読み取りのみ・model claude-opus-5-5）。

## 1 回目（2026-11-10 12:40〜12:44Z・対象 commit 1acef2048・基準 origin/main 4cc17871）

判定: **REVISE**（中心の §5-3 は効く。表の抜け 1 件と見張りの詰め 3 件）

### 審査役が確かめた事実
- recon・design の file:line の引用は origin/main 4cc17871 の実物と全部一致した。
- FastAPI 0.136.3・starlette 1.3.1・Python 3.12.3 で §5 を写した小さなアプリを /tmp に作り、pytest 8 件が緑。
  - 変更前: 最初のかたまりを送った時点で DB セッションは開いたまま。
  - 変更後: 同じ時点で open→auth→tenant→perm→closed の順に閉じていた。
  - 登録時だけの依存も `route.dependant` に入る（`['tenant','get_db']`）。§5-3 の後、受信箱の流れの依存の木に get_db は無い。
- 認証の結果は変更前後で同じ（トークン無し 401、閲覧者 401、会社が無効 403、権限なし 403、正常 200）。
- recon U2: Python 3.12.3 でも wait_for の時間切れの次の呼び出しは StopAsyncIteration。

### 指摘と対応（Planner が実物で確かめてから直した）
| # | 重さ | 指摘 | Planner の確かめ | 直したところ |
|---|---|---|---|---|
| 1 | 中 | docstring を変えると OpenAPI の説明文が変わり `api-contract-check` が赤になる。表に openapi.json が無い | `frontend/api-contract/openapi.json` :46877-46902 の description は今の docstring。tags は main.py :556-559 の `meta-inbox` | design §5-3: docstring は変えず `#` の行に理由を書く。tags は同じ。openapi.json は触らない。K7 を追加 |
| 2 | 中 | 戻り型の判定方法が無い。`from __future__ import annotations` で戻り型が文字列になり、0 本になる | 流し口は `git grep` で 3 本（leads.py :2945・meta_inbox.py :1052・realtime_events.py :62） | design §5-5: `typing.get_type_hints` と `text/event-stream` の補助で集め、3 本と完全一致を確かめる |
| 3 | 低 | 禁止の依存が get_db だけ。get_admin_db も同じ yield 依存 | `backend/app/database.py` :112 で確認 | design §5-5: 禁止を `{get_db, get_admin_db}` に |
| 4 | 低 | recon A-10 に受信箱の画面のもう 1 本が抜け | `frontend/src/hooks/useInboxSSE.ts` :14・`frontend/src/pages/inbox/useInboxState.ts` :594 で確認 | recon A-10 に追記。直す範囲は変わらない |

## 2 回目
（審査待ち）
