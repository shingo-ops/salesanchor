<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ。このPRに含まれない新しいファイルにはバッククォートを付けない。 -->
# 実装カード 便1 — 受信箱の通知の流れを短い DB セッションで認証する

**設計の正本**: `docs/handoff/app-idle-tx/design.md` §5（変更前→変更後）・§6（弊害）・§2 KPI。このカードは手順と点検だけを足す。設計と食い違ったら設計が正。  
**PO 承認**: 2026-11-11「1」（案 A を実装）。区分 A（ADR-1015）。GO 不要（危険パスを含まない）。  
**基準の main**: 8d2c7e1b4（設計の頼る行が d9a5938f から変わっていないことを `git diff --stat d9a5938f 8d2c7e1b4` で確かめ済み。差分 0 行）。  
**実装担当**: クラウドの Sonnet。**ブランチ**: release/app-idle-tx-bin1（このカードと同じブランチに積む）。

## 1. 触るファイル（これ以外は触らない）
設計 §5 の表の 7 つと、このカードを含む書類（設計の状態行・§11 守り手の行・作業台帳）だけ。

- backend/app/realtime/stream_db.py（新規）— 設計 §5-1 のコードをそのまま
- `backend/app/routers/realtime_events.py` — 設計 §5-2
- `backend/tests/test_realtime_events.py` — 設計 §5-2（:34 の1行と import 1行。import は `from __future__` の後ろ）
- `backend/app/routers/meta_inbox.py` — 設計 §5-3
- `backend/app/main.py` — 設計 §5-3（:556 の直前に 2 行）
- backend/tests/test_sse_no_db_hold.py（新規）— 設計 §5-4・§5-5
- `docs/adr/ADR-1016-realtime-change-signal-standard.md` — 設計 §5-6 の文を追記。その後 `node scripts/generate-adr-index.js`
- `docs/handoff/app-idle-tx/design.md` — §11「守り手:」を backend/tests/test_sse_no_db_hold.py に書き換える（ファイルができた後）

触らない: `backend/app/auth/`、`backend/app/database.py`、leads/stream（`backend/app/routers/leads.py`）、nginx、`frontend/`（`frontend/api-contract/openapi.json` を含む）、`migrations/`、deploy、`.github/`。

## 2. 手順
1. `./scripts/dev/executor-preflight.sh || exit 1`。ブランチ release/app-idle-tx-bin1 を取り、そこに積む（new-worktree.sh の手順に従う）。
2. 設計 §5-1 → §5-2 → §5-3 の順に書く。meta_inbox.py の流れの関数は、docstring とその後ろ（接続数の確かめ・event_generator・StreamingResponse）を 1 文字も変えない。
3. 設計 §5-4・§5-5 の試験を書く。
4. 赤の確かめ（K2）: 新しい試験ファイルだけを、変更前の main（8d2c7e1b4）のアプリに当てて走らせ、見張りが conversations/stream を名指しして `get_db` で赤になる生出力を残す（例: 試験ファイルを一時的に main の写しへ置いて走らせる。写しは commit しない）。
5. 緑の確かめ: `backend/tests/test_sse_no_db_hold.py`・`backend/tests/test_realtime_events.py`・`backend/tests/test_viewer_isolation.py`・`backend/tests/test_permission_catalog.py` を走らせる。
6. ADR 追記 → `node scripts/generate-adr-index.js` → `docs/adr/README.md` を一緒に commit。
7. design.md §11 の守り手を書き換える。
8. push して止まる。PR は作らない（Opus が作る）。

## 3. 想定される分岐（迷ったらここを見る。ここに無い分岐は止まって報告）
| 起きたこと | すること |
|---|---|
| 設計の行番号が実物とずれる | 中身で同じ場所を探す。中身も違えば止まる |
| `security` が `backend/app/auth/dependencies.py` に無い・名前が違う | 止まる（auth は触らない） |
| `get_current_user`・`get_current_tenant` の引数が (request, cred, db)・(request, user, db) でない | 止まる。引数の並びを推測して合わせない |
| `require_permission` の checker の引数名が current_user・tenant_id・db でない | 止まる |
| 見張りの集め方で 3 本と一致しない（増える・減る） | 集まった全部を生で出して止まる |
| 変更後に leads/stream 以外が赤 | 名前を生で出して止まる |
| openapi.json に差分が出る（`backend/tools/export_openapi.py` で書き出して比べる） | 止まる。openapi.json を書き換えない |
| `test_viewer_isolation` が 401 以外を返す経路を出す | 止まる |
| 試験の都合で auth や database.py を直したくなる | 止まる |

## 4. 報告の形
生出力をそのまま。①preflight の結果 ②`git diff --stat origin/main...HEAD` ③K2 の赤（旧 main）④緑の試験の出力 ⑤openapi の比較結果 ⑥HEAD の sha と push の結果。最後の行は DONE / BLOCKED: <理由> / NEEDS_DECISION: <問い> のどれか。

## 5. 受け入れ（Opus が確かめる）
| 基準 | 検証方法 |
|---|---|
| 設計 §5 の表のファイルだけが変わる | `git diff --name-only origin/main...HEAD` |
| K2: 見張りが緑、旧 main で conversations/stream を名指しして赤 | 報告③④の生出力 |
| K3・K6・K7 | CI の backend 試験・api-contract-check が緑 |
| K4: DB を閉じてから最初のかたまり | T1 の記録 |
| docstring と流れの後半が不変 | diff を Opus が読む |
