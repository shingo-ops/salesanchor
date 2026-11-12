# Phase 2 recon — viewer-setting-blank-guard（閲覧ページが「準備中です」になった件の再発防止）

> この文書は何か（専門用語なしの1行）: お客さんの在庫閲覧ページが止まった原因と、それを今は何も止められない理由を、実物で確かめた記録。

- 親（あるべき姿・KGI）: [在庫の閲覧専用ページ](../../specs/inventory-management/inventory-viewer/README.md)（既存の延長）
- 設計: [design.md](./design.md)
- 日付: 2026-11-12 ／ 土台: origin/main（6b086f13c） ／ 担当: Claude Opus（設計担当）

## 0. 既存 ADR の検索（STANDARD-WORKFLOW Phase 2）

- 実行: `git grep -l -i -e max_age_hours -e "viewer:inventory" -e ViewerInventoryStale -e distribution_settings origin/main -- docs/adr`
- 結果: ADR-1014（配信の行の正本）、ADR-1041、ADR-1066 の 3 本。設定値の入力チェックを決めた ADR は無い。
- `docs/adr/FEATURE-INDEX.md` の 51 行目: 24 時間保守運用は ADR-1012（Proposed）。経路の正本は Alertmanager、障害記録の正本はアプリ DB。
- 閲覧ページは ADR-1019（docs/specs/inventory-management/inventory-viewer/README.md の 15 行目）。
- 閉じたパネルの無効化は docs/handoff/drawer-inert-when-closed/design.md（2026-10-27）。
- 個人側の見張りの置き場は docs/specs/local-hooks-ssot/README.md（原本を repo に置き PR で変える。前例 ADR-1029・ADR-1045）。

## 1. 起きたこと（実測・時刻は日本時間）

| 時刻 | 出来事 | 根拠 |
|---|---|---|
| 11/10 18:35 | 配信の設定「何時間以内の投稿を出すか」が空で保存された | 本番 Loki の PUT /api/v1/tcg/distribution/settings/max_age_hours の記録（調査メモ loki-*.json） |
| 11/10 18:36〜 | 在庫の作り置きが毎分失敗（理由: 未設定のため配信しない） | worker のログ `[viewer-cache]` |
| 11/10 18:47〜 | 警報 ViewerInventoryStale が鳴る。11/12 まで 14 件 | `public.ops_incidents`（reader 鍵で集計） |
| 11/11 12:51 | 同じ空保存がもう一度起きた | 本番 Loki の PUT 記録 |
| 11/11 18:35 ごろ | 作り置きが 24 時間で消え、閲覧ページが「準備中です」（503）。時刻は最後の成功（11/10 18:35 ごろ）に寿命 24 時間を足した計算 | backend/app/routers/viewer.py:248、backend/app/tasks/viewer_inventory_cache.py:33 |
| 11/12 午前 | お客さんから「在庫を確認できない」と連絡 | PO 受信の画面写し |
| 11/12 11:21:00 | PO が設定画面で 48 を保存し直した | 本番 Loki の PUT 記録（section=dashboard の 1 件） |
| 11/12 11:22 | 作り置き 1356 行・失敗回数 0、配信先 5 件すべて成功 | Redis の読み取り、配信の記録 |

## 2. 観点ひな型 v1（docs/specs/recon-standard/kgi.md の 7 観点）

部品の定義（本 recon）: ①API の入口 ②設定パネルの画面部品 ③作り置きの定期タスク ④警報の規則と届け先 ⑤AI のブラウザ操作の道具。

### 観点1: 全体像（データの流れ）

- 画面: frontend/src/pages/super-admin/AnalysisRulesPage.tsx:149 が設定パネルを常に置く（開閉は `open` だけで切り替え）。
- パネル: frontend/src/pages/super-admin/components/DistributionSettingsDrawer.tsx:34 で入力の初期値は空文字。
- 読み込み: 同ファイル:40-53。開いたときだけ GET する。取得に失敗しても「空のまま編集可能」（:50 のコメント）。
- 保存: 同ファイル:55-68。中身を確かめずに PUT する。ボタンが押せなくなるのは保存中だけ（:110）。
- API: backend/app/routers/tcg_distribution.py:63-64 で受け取る形は `value: str` だけ。中身の確認は無い。
- 保存の処理: backend/app/services/tcg_distribution_svc.py:859-871 はそのまま UPDATE する。
- 読む側: backend/app/services/tcg_distribution_svc.py:202-213 は空・整数でない・負を None（配信しない）として読む。
- 作り置き: backend/app/services/tcg_distribution_svc.py:999-1001 で None なら kind="unset" を返す。
- 作り置きタスク: backend/app/tasks/viewer_inventory_cache.py:81-98 は unset を失敗として数え、前回の写しは残す。
- 写しの寿命: backend/app/tasks/viewer_inventory_cache.py:33 の 86400 秒（24 時間）。
- 閲覧 API: backend/app/routers/viewer.py:248 は写しが無いと 503 `viewer_inventory_not_ready` を返す。

### 観点2: 共用部品

- 設定パネルの枠は共用の金型 frontend/src/components/Drawer.tsx。中身は常に DOM に置かれる（同ファイル:131 のコメント「DOM は常にマウント」）。
- 閉じている間は `useInertWhenClosed` で無効化する（frontend/src/components/Drawer.tsx:116）。人の操作・Tab・読み上げは止まる。
- 設定値の読み口は 1 か所（backend/app/services/tcg_distribution_svc.py:202 `_max_age_hours`）。書き口に同じ確認は無い。

### 観点3: 非共用部品

- 失敗 3 回目の Discord 通知は backend/app/tasks/viewer_inventory_cache.py:48-73 の独自の道。宛先はテナント 4（:66）。
- テナント 4 の通知の届け先は 0 件（reader 鍵で `notification_channels` を数えた結果）。この道は 1 度も届いていない。

### 観点4: ルールの所在

- 設定値の範囲を決めた正本: 読む側の docstring（backend/app/services/tcg_distribution_svc.py:203-205「0 は無制限」）だけ。ADR には無い。
- 警報の規則: monitoring/prometheus/alert_rules.yml:245-254（10 分古い・保留でない・2 分続く・札 ticket）。
- 警報の届け先: monitoring/alertmanager/alertmanager.yml:1-34。全部の警報が同じ Discord の 1 か所と ops-api に行く。札で分けていない。
- 手順書: docs/runbooks/alerts.md:206-213。「24 時間で消えるので、それまでに直らないと 503」と書いてあるが、誰が見るかは決まっていない。

### 観点5: 維持の仕組み（今、何が守っているか）

| 守るべきこと | 今の守り手 | 判定 |
|---|---|---|
| 空の設定で配信しない | 試験 backend/tests/test_distribution_rows_builder.py:56-57・:91（unset を返すこと） | 有り |
| 空の設定を保存させない | 無し（API・画面・試験のどれにも無い） | **不足** |
| 閉じたパネルのボタンを押させない | inert（人の操作だけ） | **不足**（プログラムからの押下は未確認） |
| 写しが消える前に人か AI が気づく | 警報は鳴った（14 件）。対応した記録は 0 件 | **不足** |
| AI がブラウザで画面外のボタンを押さない | 無し（ブラウザ操作の道具に見張りが無い） | **不足** |

- 警報の届き方（実測。調査メモ ops-incidents.txt・am-logs.txt）:
  - Alertmanager から Discord への送信は 10/23 以降 1085 回で失敗 0 回。
  - ops-api への送信は 1516 回中 438 回失敗。
  - 11/1 以降の障害記録の出来事は、送り手が alertmanager だけ（通知 346・解決 327）。人や AI が対応した記録は 0 件。
  - 同じ時期に BruteForceAttempt 69 件・SustainedAuthFailure 17 件が同じ Discord に流れていた（11/9 以降）。
- ブラウザ操作の見張り: ~/.claude/settings.json の PreToolUse の対象に、ブラウザの道具の名前は 1 つも無い（matcher の一覧を実測）。repo の .claude/settings.json にも無い。

### 観点6: 設計図との対照（一致／不足／余剰）

| あるべき姿の項目（ADR-1019・inventory-viewer） | 現状 | 判定 |
|---|---|---|
| お客さんは在庫表をいつでも見られる | 11/11 18 時台〜11/12 11:21 は見られなかった | 不足 |
| 配信が保留のあいだは前回の在庫を出し続ける（設計 Q11） | 24 時間までは出し続けた | 一致 |
| 止まったら知らせる | 鳴ったが誰も動いていない | 不足 |
| テナント 4 宛ての Discord 通知（viewer_inventory_cache.py:62-70） | 届け先 0 件で届かない | 余剰 → 除く（届け先の正本は Alertmanager。FEATURE-INDEX 51 行） |

### 観点7: ノイズと境界

- 見ない範囲: 配信シート（Google シート）への書き出しの道。今回は 11/12 11:22 に 5 件成功しており、原因に関係しない。
- 見ない範囲: 解析の保留（ViewerInventoryStaleOnHold）。今回の 14 件は保留でない側。

## 3. 誰の操作だったか（実測と未確認）

- 【事実】11/10 18:35 と 11/11 12:51 の前後に、商品マスタの画面で AI（本セッション）がブラウザ操作をしていた。会話の記録から、ブラウザの道具の呼び出しを時刻で抜き出して確かめた（調査メモ scan-out.txt）。
- 【事実】その時間帯の操作は、ページの中でプログラムを動かす道具（javascript_tool）だった。ボタンを「表示されている文字」でページ全体から探し、プログラムで押す補助関数を使っていた（例: `__btn('閉じる')` を探して `.click()`）。
- 【事実】設定パネルの保存ボタンの文字は「保存」。商品の編集パネルの保存ボタンも「保存」。
- 【未確認】どの補助関数が設定パネルの「保存」を押したか。会話の記録を全文で読み直す操作は見張り（consent-guard）に止められたため、言い換えはしていない。
- 【未確認】inert の付いたボタンに対するプログラムからの `.click()` が止まるか。設計では、これに頼らない形にする（design.md §5-2）。

## 4. 調査で止められた操作

- 会話の記録を Bash で読む操作が見張り（consent-guard）に止められた。迂回はしていない。
