# 設計審査（便2: v6 の値の直し）— Architect

- 対象: `docs/handoff/review-edit-all-fields/design.md` §5（5-0〜5-5）
- 基準: worktree `/Users/tanizawashingo/worktrees/salesanchor/release-review-edit-v6`（HEAD 759cee4d5）
- 審査日: 2026-10-16

## 判定: REVISE

設計の骨格（同じ鍵を v6 解析でも取る、apply_value_overrides を v6 の8変数に重ねる、v6 では配信の予約を積む）は実装できる。
ただし、次の5点は直してから実装に渡す必要がある。
- そのまま書くと import が循環して起動できない（M1）。
- 鍵の守りが抜ける経路が2つある（M2・M3）。
- review-ack の挙動が変わる（M4）。
- 画面の文言が事実と合わない（M5）。

---

## 1. §5-0 の事実の照合（実物との突き合わせ）

| 記載 | 実物 | 判定 |
|---|---|---|
| 数量 A:1669、単価 A:1670、メモ A:1674、販売状況 A:1678 | `backend/app/services/tcg_analyzer_svc.py:1669,1670,1674,1678` | 一致 |
| 単位 A:1523-1524、A:107 で `str(uid)` | `tcg_analyzer_svc.py:1523-1524`、`:107` | 一致 |
| `"unit_id": unit_uuid` A:1794、`"exclusion": exclusion_val` A:1804、最初の commit A:1814 | `:1794`、`:1804`、`:1814` | 一致 |
| 途中 commit 1829・1840・1997 | `:1829`、`:1840`、`:1997`（`_merge_supplier_products` の中） | 一致 |
| 商品の直しがある件 A:1493-1507 | `:1493` で EXISTS を読み、`:1496-1506` で状態だけ UPDATE して continue | ほぼ一致 |
| 束縛ハッシュ `tcg_condition_review_svc.py:93-96` | `:93-96`（unit_id・unit_canonical・unit_resolved・quantity・price） | 一致 |
| exclusion を書くのは A:1804 だけ | `git grep` で書き込み元は `tcg_analyzer_svc.py:1779`（v6 の UPSERT）、`line_analysis_v102_svc.py:718`（v102）、`v102_human_decisions_svc.py:472`（保存）だけ。`routers/tcg_product_master.py:359` は docstring | 一致（v6 の経路として） |
| `resolve_status_v2` A:1273-1312、'active' は A:1243・1281・1312 | 定義は `:1273`。'active' を返すのは `:1283` と `:1309`。`:1243` は debug ログで、`:1244` が `[]` を返す | **ずれ（行番号のみ）** |
| `analyze_extraction_job` A:1317、呼び出し元は T:599 と `tcg_product_master_svc.py:753` の2つ | `:1317`。`git grep` の結果、app 内の呼び出し元はこの2つだけ（ほかはテスト） | 一致 |
| T:599 の直前に commit T:588 | `backend/app/tasks/tcg_extraction.py:588` → `:599` | 一致 |
| 753 の前は「analysis_runs の INSERT だけ」 | `tcg_product_master_svc.py:654-667` で INSERT して commit（:667 付近）、さらにスナップショットを INSERT して commit（:724 付近）。753 に入る時点で、開いている取引は無い | **ずれ（表現）**。結論（行ロックを持っていない）は同じ |
| 鍵 `v102_transcription_svc.py:166`、v102 解析 `line_analysis_v102_svc.py:1269`、H:581 は直書き | `:166-168`、`:1269`（直書きの文字列）、`v102_human_decisions_svc.py:581` | 一致 |
| `load_v102_decisions` H:231-279 は prompt_version を見ない | `:231-279` | 一致 |
| manual_values `tcg_analysis_review_svc.py:277,319` | `:277`、`:319` | 一致 |
| `item_rejection` H:446、呼ぶのは H:443・R:231・R:273。H:576 は 404 だけを自前で作る | `:446`、`:443`、`routers/item_corrections.py:231,273`。H:576 は `item_rejection(...) if found is not None else 404` で、**409 も item_rejection 経由で出る** | 一致（補足あり） |
| 配信 `tcg_distribution_svc.py:247,336,448` | `:247`（sold out を外す）、`:336`、`:448`（`exclusion IS DISTINCT FROM 'excluded'`） | 一致 |
| `schedule_distribution` T:670、呼ぶのは T:723 だけ | `:670`、`:723` | 一致 |
| `review_reason_codes_svc.py:17` で外せないのは condition_unknown だけ | `:17` | 一致 |
| R:261-284 value-override | `routers/item_corrections.py:261-284` | 一致 |
| `reviewFixRows.ts:37` | `frontend/src/features/tcg-analysis-review/reviewFixRows.ts:37` | 一致 |
| §5-2 の A:1694（empty_box の理由）と A:1696（reanalysis_condition） | 実物は `:1690`（empty_box の理由）と `:1691-1698`（`:1692` で reanalysis_condition を呼ぶ） | **ずれ（4行）** → O1 |
| 本番の件数（35672 / 1033 / 90 / 8、'active' 0 件） | 本番 DB は読んでいない | **未確認** |
| 'manual_review_pending' はコードにも git の全履歴にも無い | `git grep` で当たるのは design.md（未コミット）の2行だけ。`git log --all -S manual_review_pending` は0件 | 一致 |

## 2. 実装可能性の審査

### 2-1. 鍵（D2）: デッドロックと長い待ち

**取る順番（デッドロック）**
- 保存（H:562-616）: 鍵（H:581）→ マスタを読む → `analysis_results` を FOR UPDATE（H:589）→ item_corrections に INSERT（ei・sm への FK の key-share）→ UPDATE。
- 解析（案）: 鍵 → `FOR SHARE OF ei, ej, sm`（A:1456）→ 件ごとに ar を FOR UPDATE（A:1490-1491）→ UPSERT。
- 呼び出し元は、どちらも直前に commit していて、行ロックを持たない（T:588、`tcg_product_master_svc.py:724` 付近）。
- 両方とも鍵を最初に取るので、待つ向きは一方向になり、デッドロックはしない。
- FOR SHARE と FK の key-share はぶつからない。
- `save_condition_review`（`tcg_condition_review_svc.py:320-332`）は鍵を取らないが、FOR SHARE → ar の FOR UPDATE の順で、今と変わらない。

**途中 commit で鍵が外れる点**
- 人の値を読む（ループ前の `load_v102_decisions`）、件ごとに重ねる、UPSERT する。この3つはすべて A:1814 の最初の commit より前、つまり鍵の内側にある。「鍵が外れた後に人の値を読む」順にはなっていない。
- ただし、外れた後に走る E3a/E4 が単位の列を書き換えるので、保存と競合しうる → **M3**。
- 1997 の commit は `_merge_supplier_products` の中で、is_current だけを書く。8列には触らない（`tcg_analyzer_svc.py:1981-1990`）。

**鍵の位置**
- 「v102 の分岐（A:1331-1338）の直後」に取ると、その後のマスタ読み込みで `session.rollback()` が呼ばれたときに、鍵が黙って外れる。以後のループは鍵なしで走る → **M2**。
- rollback する箇所: `load_condition_entries` の `:682`、`load_normalization_rules` の `:969`、`load_note_master` の `:1037`、`load_status_master` の `:1242`。

**長い待ち**
- 保存は、同じ投稿の v6 ループ全体（＋鍵の位置によってはマスタ全件の読み込み）が終わるまで待つ。
- 5-5 は「解析が保存1回分を待つ」向きしか書いていない。
- v6 ループ1投稿の所要時間は **未確認** → O6。

### 2-2. 8変数への重ね方（v102 との一致）

- v102（`line_analysis_v102_svc.py:952-954`）は `apply_value_overrides(values, d.values, unit_ids, status_entries)` を呼ぶ。
  - unit_ids は `load_v102_masters` が `analyzer.load_lookup_maps` の `unit_canonical_to_uuid` を返したもの（`:198,206`）。
  - status_entries は `masters["status_entries"]`。
- v6 の `unit_canonical_to_uuid`（A:1341-1348）・`status_entries`（A:1381）も同じ関数から来る。同じ型・同じ中身なので一致する。
- 戻り値の `unit_id` は int（H:530）。v6 の UPSERT は str を渡しているので、設計どおり `str(v)` に戻せば今の型と揃う。
  - v102 側でも、非上書きの値は str、上書きの値は int で混在している。v6 だけ別の扱いにはならない。
- 数量・単価は、v6 では float（`_parse_numeric`、A:924）、上書き値は Decimal。
  - UPSERT のパラメータは、どちらでも書ける。
  - `reanalysis_condition` は `json.dumps(candidate, default=str)`（`tcg_condition_review_svc.py:293`）で Decimal を文字列にする。束縛ハッシュは `trim_scale(...::numeric)` で比べる（`:96`）。型の違いで例外やハッシュのずれは起きない。
- exclusion は `apply_value_overrides` が status と組で決める（H:533-538）。D1 のとおり。
- 注意: dict のキーは H の列名（`unit_id`・`status`・`exclusion`）にする必要がある。変数名（`unit_uuid`・`status_val`・`exclusion_val`）のままでは重ならない → O4。

### 2-3. 循環 import（実験で確認）

worktree の `backend/app` を scratchpad に複写し、import 文だけを足して `python3 -c "import ..."` を実行した。

| 変更 | 結果 |
|---|---|
| H の先頭に `from app.services.v102_transcription_svc import v102_analysis_lock_key` | **ImportError**（`cannot import name 'FIELD_V102_PRICE' from partially initialized module ...v102_human_decisions_svc`） |
| A の先頭に H と transcription の import | **ImportError**（`tcg_analyzer_svc` / `line_analysis_v102_svc` / `tasks.tcg_extraction` / `routers.item_corrections` の4つすべて） |
| A の先頭に H の import だけ | 4つ＋transcription とも import できる |
| 変更なし（基準） | import できる |

設計は「H を A から遅延 import」とだけ書いている。`v102_analysis_lock_key` の取り込み方（H・A の両方）を書いていないため、素直に先頭へ書くと起動できない → **M1**。

### 2-4. item_basic_rejection 分割と review-ack

- 今の `item_rejection` は 404 → 409（v6）→ 422（source 不一致）の順（H:446-457）。
- 設計の「basic で断れればそれ、v6 なら 409」は 404 → 422 → 409 の順になる。v6 で source も違う件の応答が 409 から 422 に変わる。
- 影響: review-ack の確定（`review_ack_rejection` H:443 → R:199）、取り消し（R:231）、CSV（`tcg_review_csv_svc.py:177` の文言）。
- 「review-ack の挙動は変えない」と矛盾する → **M4**。

### 2-5. router からの schedule_distribution 呼び出し

- `schedule_distribution()`（T:670-692）は同期関数。中で Redis（接続・送受信とも timeout 2秒、T:641-648）と `apply_async` を呼ぶ。引数は無く、戻り値は bool。
- 今の router は同期の `enqueue_v102_reanalyze` を async 関数の中からそのまま呼んでいる（R:206,240,283）。同じ書き方で実装はできる。ただし、Redis が遅いと event loop を最大数秒止める → O3。
- import: `routers/item_corrections.py:45` に `schedule_distribution` を足すだけ。tasks モジュールはもう import 済みなので、新しい循環は無い。
- `TCG_AUTO_DISTRIBUTE` の既定値は backend コンテナでも `0`（`docker-compose.yml:104`）。本番での値は **未確認**。0 なら D3 は何もしない（関数が False を返す）。

### 2-6. frontend の変更範囲（is_v102 の全走査）

`git grep is_v102 frontend/src`（テスト以外）の結果:

| 箇所 | 中身 | 設計 |
|---|---|---|
| `reviewFixRows.ts:37` | 値の5行を v102 だけにする | 外す（5-3 に記載） |
| `ReviewFixWizard.tsx:39` | `availableFixChoices` の "value" | 外す（5-3 は「あれば」と書いている。実在する） |
| `ReviewFixWizard.tsx:27` | `ackableReasonCodes`（v6 の ack は 409） | 残す。正しい |
| `ConditionReviewPanel.tsx:25` | 状態の行（D4） | 残す。正しい |
| `ReviewItemDrawer.tsx:25`、`ItemComparison.tsx:22`、`NeedsReviewTabsPanel.tsx:44` | 型の定義だけ | 変更不要 |

範囲はこの2か所で足りる。ただし次の2点がある。
- 保存後の文言 `reviewItem.valueFix.saved`「直しました。解析をやり直しています」（`ReviewValueFixForm.tsx:87`）は、v6 では事実と違う（v6 は再解析しない、D3） → **M5**。
- 既存のテストのうち、v6 で値の行が押せないことを前提にしているもの → O2。

### 2-7. §5-4 の受け入れ基準

- V1・V2・V3・V5・V7・V8 は検証できる。
  - V3 は `TCG_AUTO_DISTRIBUTE` に左右されないよう、router で `schedule_distribution` を monkeypatch して呼び出し回数を数える必要がある。
  - V7 は既存テストの期待値を更新したうえでの緑になる（O2）。
- V4 は v6 の PG fixture（`test_tcg_work_matching_integration.py` 系）を使えば検証できる。
- V6 の「別の接続で鍵を持つ間は待つ」は、スレッドと待ち時間に頼ると不安定になる → O5 に決まった形を書いた。

---

## 3. 指摘

### 必須（M）

**M1 `v102_analysis_lock_key` の取り込みが循環 import になる**
- 箇所: design §5-2-1（H:581 を `v102_analysis_lock_key` に置き換える）、§5-2-3（A で同じ関数を使う）。
- 事実: §2-3 の実験で、H または A の先頭で `app.services.v102_transcription_svc` を import すると ImportError になった。原因は、transcription が先頭で H と line_analysis_v102_svc を import していること（`v102_transcription_svc.py:18-20`）。
- 直し方（どちらかを design に明記する）:
  - (a) H と A の両方で、関数の中で import する（`# noqa: PLC0415  循環 import を避ける`。H:165・H:313・H:452 と同じ書き方）。
  - (b) 鍵の関数の正本を H（依存の一番下）に移す。`v102_transcription_svc.v102_analysis_lock_key` は H の関数を返すだけにする。A は H を先頭で import してよい（実験で import できることを確認済み）。
- (b) の方が「正本1つ」に合う。

**M2 鍵を v102 分岐の直後に取ると、マスタ読み込みの rollback で黙って外れる**
- 箇所: design §5-2-3 の1つ目（A:1331-1338 の直後）。
- 事実: 鍵の後に呼ぶ読み込み関数が、例外時に `session.rollback()` する（`tcg_analyzer_svc.py:682,969,1037,1242`）。xact lock はそこで外れ、ループは鍵なしで走る。マスタ全件の読み込み時間も、保存を待たせる時間に加わる。
- 直し方: 鍵は extraction_items の SELECT の直前（A:1440、全マスタを読み終えた後、FOR SHARE の前）で取る。`load_v102_decisions` はその SELECT の後、ループの前で読む。鍵から A:1814 の commit までの間に rollback・commit が無いことを design に書く（今のコードでは無い。`reanalysis_condition` は commit しない）。

**M3 A:1814 の commit 後の E3a/E4 が、その間に保存された人の単位を上書きしうる**
- 箇所: A:1817-1842 から呼ぶ `backend/app/services/tcg_unit_recovery_svc.py`。
  - E3a: `:784-805` で `unit_resolved` を読む（ロックなし）→ `:873-880` で `UPDATE ... WHERE id = :ar_id`。
  - E4: `:1141-1155` → `:1175-1182`、同じ形。
- 事実: 1814 で鍵が外れた後に保存（unit_resolved=TRUE）が commit されると、E3a/E4 の UPDATE の WHERE は id しか見ない。READ COMMITTED で行が更新されていても、その UPDATE は通る。結果、人の単位が解析の推定単位で上書きされる。
  - item_corrections の記録は残るので、次の v6 解析で戻る。ただし v6 では再解析を積まない（D3）。
  - 起きるのは、同じ投稿を再解析している数十〜数百ミリ秒の間に保存が来たときだけ（間隔は **未確認**）。
- 直し方（design で選んで明記する）:
  - (a) E3a・E4 の UPDATE の WHERE に `AND unit_resolved = FALSE` を足す。再評価で人の値の行を飛ばせる。触るファイルに `tcg_unit_recovery_svc.py` が加わる。
  - (b) 5-5 に「残る危険」として、起きる条件・頻度・戻し方（もう一度保存する）を明記して受け入れる。
- 推奨は (a)。2行で済み、v102 側には影響しない（v102 は E3a/E4 を呼ばない。【推測】`run_v102_analysis` から tcg_unit_recovery_svc を呼んでいるかは grep していない。実装担当が確認する）。

**M4 `item_rejection` を「basic → 409」の順に組み直すと、review-ack の応答が変わる**
- 箇所: design §5-2-1 の2つ目。H:446-457。
- 事実: 今は 404 → 409 → 422。設計の順では、v6 かつ source 不一致の件が 409 から 422 になる。影響は R:199・R:231・`tcg_review_csv_svc.py:177`。
- 直し方: `item_rejection` は `found is None → 404`、`v102 でない → 409`、`return item_basic_rejection(found, source_message_id)` の順にする。`item_basic_rejection` は 404 → 422 にする。docstring の順番（H:432-433）も合わせる。

**M5 v6 で保存した後の文言「直しました。解析をやり直しています」が事実と違う**
- 箇所: `frontend/src/features/tcg-analysis-review/ReviewValueFixForm.tsx:87`、`ja.json` / `en.json` の `reviewItem.valueFix.saved`。design §5-3 の「文言は便1のキーをそのまま使う（追加なし）」。
- 事実: v6 は再解析しない（D3。`reanalyze_v102_job` も v6 は skipped、T:701-704）。
- 直し方（ja/en 同一キー、ADR-027）: 次のどちらかを design に書く。
  - (a) 新しいキー（例 `reviewItem.valueFix.savedNoReanalyze`「直しました」）を足し、`item.is_v102` で出し分ける。
  - (b) 共通の文言を事実に合う表現に変える。

### 任意（O）

- **O1 行番号の修正**: §5-2-3 の「A:1694 と A:1696 の間」は「A:1690（empty_box の理由）の後、A:1691 のコメント・A:1692 の `reanalysis_condition` の前」にする。§5-0 の 'active' は A:1283・1309（1243 はログ、1244 で `[]`）。753 の前は2回 commit している（analysis_runs と snapshots）。
- **O2 既存テストの期待値の更新を明記**: 次の3つは v6 の値が押せないことを前提にしていて、そのままでは赤になる。V7 に「これらを更新したうえで緑」と書く。
  - `backend/tests/test_v102_value_overrides.py:266`（v6 → 409 の case）
  - `frontend/src/features/tcg-analysis-review/ReviewFixWizard.test.tsx:49-53`（`is_v102` 既定 false の case に "value" が無い）
  - `ReviewItemDrawer.test.tsx:182-191`（v6 の Quantity を「押せない行」の例にしている。別の押せない行に替える）
- **O3 schedule_distribution の呼び方**: 同期の Redis I/O なので、`await starlette.concurrency.run_in_threadpool(schedule_distribution)` を推奨する（既存の `enqueue_v102_reanalyze` と同じ直呼びでも動く）。
  - 本番の `TCG_AUTO_DISTRIBUTE` が 1 かどうかは **未確認**。0 なら D3 は効かず、次の定期配信まで Sold out の件が出続ける。PO の測り方（5-5）に、この確認を足す。
- **O4 dict のキーを明記**: `{"quantity_normalized": quantity_normalized, "price_normalized": price_normalized, "unit_id": unit_uuid, "unit_canonical": unit_canonical, "unit_resolved": unit_resolved, "note_ja": note_ja, "status": status_val, "exclusion": exclusion_val}` から通して戻す。
  - `stats["unit_resolved"]`（A:1526-1527）は重ねる前の値で数える。これを変えない旨も一言書く。
  - 人の単位は商品照合の kubun フィルタ（A:1530-1533）には効かない（v102 と同じ）。これも書く。
- **O5 V6 の検証方法**: 別の接続で `pg_advisory_xact_lock(hashtextextended('v102_analysis:<job>',0))` を保持する。解析側の接続で `SET lock_timeout='200ms'` にして analyze_extraction_job を呼び、LockNotAvailable（55P03）になることを確かめる。スレッドも待ち時間も要らない。
- **O6 5-5 の待ちの向き**: 保存が、同じ投稿の v6 ループ全体を待つ向きも書く。v6 ループ1投稿の所要時間は未測定（**未確認**）。
  - 便1の保存側も、鍵の後の `load_status_master`（H:584）で rollback すると鍵が外れる。本番には表があるので実害は無い。同じ型の穴として記録だけ残す。
- **O7 参考（今回の範囲外・既存の挙動）**: v6 の解析は束縛ハッシュの候補に `unit_id` を str で渡す（A:1693 → jsonb の文字列）。DB の行は数値（jsonb の数値）。v6 で単位がある件の状態の確定がやり直しで外れるかどうかは **未確認**。本設計は今の型に揃えるだけなので、悪化はしない。

---

## 4. 戻し方・測り方の確認

- 戻し方（PR を revert）は成り立つ。override_* の行は残っても、古いコードの v6 解析はそれを読まない。M3 で (a) を選んだ場合も、revert で一緒に戻る。
- 測り方: 5-5 に次の2点を足すと、反映の観測が4点（デプロイ・実行・結果・指標）にそろう。
  - 本番の `TCG_AUTO_DISTRIBUTE` の値。
  - v6 の件で保存した後、配信の予約が積まれたこと（worker のログ `scheduled_distribution result`）。

---

## 再審査（r2）

- 審査日: 2026-10-16
- 対象: design.md §5 の直したもの（5-0〜5-5、D5・D6 を追加）
- 使った資料: worktree の実物から抜き出した `/tmp/CC報告ファイル/review-edit-fields/r2_check.txt`（340行）

### 判定: APPROVE

必須の指摘 M1〜M5 は、すべて設計に反映されていて、実物と矛盾しない。新しい必須の指摘は無い。

### M1〜M5 の確認

| 指摘 | 設計の該当箇所 | 実物で確かめたこと | 結果 |
|---|---|---|---|
| M1 循環 import | D5、§5-2 の1・2・3 | H の先頭の import は `tcg_condition_review_svc` だけ（H:23）。transcription は先頭で H を import 済み（`v102_transcription_svc.py:66`）。line_analysis_v102_svc も H を import 済み（`:62`）。鍵の関数を H に置けば、どこからも新しい循環は生まれない。A→H の先頭 import は、r1 の実験で import できることを確認済み | 解消 |
| M2 鍵の位置 | §5-2 の5 | 行を読む SELECT（`FOR SHARE OF ei, ej, sm`）は、マスタと商品の判断を読み終えた後にある。ここで鍵を取れば、rollback する読み込み関数（A:682/969/1037/1242）はすべて鍵より前になる。鍵から A:1814 の commit までの間に rollback・commit が無いことを、実装担当が報告する条項もある | 解消 |
| M3 単位の補完が人の単位を上書きする | D6、§5-2 の6、V6c | 単位の補完を呼ぶのは A:1819-1826 の遅延 import だけ。v102 は呼ばない（grep 結果）。E4 の SELECT は、もともと `ar.unit_resolved = FALSE` の行だけを読む。E3a は全行を読み、Python 側で `unit_resolved` が真の行を飛ばす。どちらも WHERE を足しても、競合が無いときの結果は変わらない | 解消 |
| M4 判定の順 | §5-2 の1、V2 | 404→409→422 を保ち、value-override だけを basic（404→422）にする | 解消 |
| M5 文言 | §5-3、V6d | v6 用のキー `savedNoReanalyze` を ja/en の両方に足し、`is_v102` で出し分ける | 解消 |

O1〜O6 も反映されている。
- O1: 行番号を直した。
- O2: 既存の試験の期待値を直すことを §5-3・V2 に書いた。
- O3: `run_in_threadpool` を使う。本番の `TCG_AUTO_DISTRIBUTE=1` は、呼び出し元が読み取りで確認した（私は値を見ていない。確認したファイルのパスが 5-0 にある）。
- O4: dict のキーと stats の扱いを書いた。
- O5: V6 を lock_timeout で確かめる。
- O6: 5-5 に、待ちが2方向あることと H:584 の件を書いた。

### 任意の指摘（r2 で新しく見つけたもの）

- **P1 E3a の数え方と E5**: E3a は `e3a_updates` を作った後に UPDATE する（`tcg_unit_recovery_svc.py:873-880`）。WHERE で飛ばされた行も `e3a_recovered` に数えられ、後に続く E5（condition_basis='R4:単位既定:単位不明' の行の状態の再計算）の対象にも残る。
  - 起きるのは、競合したまれなときだけ。そのとき、人が単位を直した行の状態が、補完した単位で計算し直されうる。【推測】E5 の対象の選び方は r2_check.txt の範囲では読んでいない。
  - 直し方: UPDATE の rowcount が 0 の行は、数にも E5 の対象にも入れない。または、E5 の UPDATE にも `AND unit_resolved` の守りを入れるか確かめる。実装担当の報告事項に足せば十分。
- **P2 鍵の正本を移す件の試験**: transcription の名前を残すとき、`monkeypatch.setattr(v102_transcription_svc, "v102_analysis_lock_key", ...)` のような既存の試験があると、効く先が変わる。実装の前に `git grep v102_analysis_lock_key backend/tests` で確かめる。私は grep していないので **未確認**。
- **P3 鍵より前に読む商品の判断**: A の商品の判断（resolved_product_code/work_id）は、鍵より前に読む。これは人の値（override_*）ではなく、今回の守りの範囲外。悪化はしない（参考）。
