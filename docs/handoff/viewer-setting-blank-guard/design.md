<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。 -->
# Phase 3 設計 — viewer-setting-blank-guard（閲覧ページ停止の再発防止）

> この文書は何か（専門用語なしの1行）: 配信の設定が空で保存されてお客さんの在庫ページが止まった件を、二度と起こさず、起きても止まる前に気づくための設計。

**対象ADR**: ADR-1019（閲覧ページ）・ADR-1014（配信の行の正本）・ADR-1012（24 時間保守運用・経路の正本は Alertmanager）
**recon**: docs/handoff/viewer-setting-blank-guard/recon.md
**親**: [在庫の閲覧専用ページ](../../specs/inventory-management/inventory-viewer/README.md)（区分: 既存の延長）
**日付**: 2026-11-12 ／ **担当**: Claude Opus（Planner・Architect）
**状態**: 設計案作成済み・設計審査済み（§12）・KGI は PO 未承認・実装未着手

---

## 1. あるべき姿（PO の言葉）

- 「停止したということは意図していない」（2026-11-12）
- 「この仕組みを標準化して管理定着させて継続させるための機械的な仕組みも出来ているか…外れた原因と再発防止策、CI・CDによる機械的な防止も」（2026-11-12）
- 「再発を防ぐ仕組みの設計書を作る」（2026-11-12）

## 2. KGI（案・PO 未承認）

| # | 合格条件 | 測り方 | 合格ライン |
|---|---|---|---|
| K1 | 設定「何時間以内の投稿を出すか」に、空・文字・マイナスを保存しようとすると断られ、保存済みの値は変わらない | CI の試験で 4 種（空・空白だけ・`abc`・`-1`）を送る | 断られた数 4/4・値が変わった数 0 |
| K2 | 正しい値（`0` と `48`）は今までどおり保存できる | CI の試験 | 2/2 |
| K3 | 設定パネルを閉じているあいだ、ページの中に設定パネルの「保存」ボタンが無い | 画面の試験（Playwright）でページ全体の「保存」ボタンを数える | 閉じているとき 0 個 |
| K4 | 設定の読み込みに失敗したとき、保存ボタンが押せない | 画面の試験で読み込みを失敗させる | 押せない 1/1 |
| K5 | 在庫の作り置きが 6 時間書けないと、雑音と別の Discord の場所に「お客さんの画面が止まる前」の知らせが届く | 警報の規則の試験（promtool）と、本番での 1 回の試し鳴らし | 試験 合格・試し鳴らしが届いた 1/1 |
| K6 | AI がブラウザの中でプログラムからボタンを押そうとすると、見張りが止める | 見張りの試験で 3 つの書き方（`.click()`・`dispatchEvent(new MouseEvent`・`.requestSubmit()`）を当てる | 止めた数 3/3・読むだけの書き方を通した数 3/3 |
| K7（全体） | 同じ原因（設定の空保存）で閲覧ページが「準備中です」になった回数 | 本番の 503 `viewer_inventory_not_ready` と設定の PUT の記録を 90 日分数える | 0 回 |

## 3. KPI

- 達成 KGI 数 ◯/7（K1〜K6 は各便のマージ時、K7 は本番反映から 90 日後に数える）。

## 4. recon の要点（全文は recon.md）

- 空の保存を断る場所が 1 つも無い（recon §2 観点1・観点5）。
- 閉じた設定パネルの「保存」も DOM に残る（recon §2 観点2）。
- 警報は 14 件鳴ったが、対応の記録は 0 件。同じ場所に認証の警報が 86 件流れていた（recon §2 観点5）。
- AI のブラウザ操作に見張りが無い。今回は AI がプログラムで「保存」を押した（recon §3）。

## 5. design（技術 How）— 4 つの守り

### 5-1. API で断る（便1・backend）

- 変更: backend/app/services/tcg_distribution_svc.py の `update_setting`（:859）の先頭で、key が `max_age_hours` のとき値を確かめる。
- 確かめ方: 読む側と同じ関数 `_max_age_hours`（:202）を使う。`_max_age_hours({"max_age_hours": value})` が None なら `InvalidSettingValue` を送出する。読む規則と書く規則が 1 か所になる。
- backend/app/routers/tcg_distribution.py:216-228 は `InvalidSettingValue` を受けて 422（detail `invalid_setting_value`）を返す。UPDATE は走らせない。
- 変更前: 何でも保存する。変更後: 空・空白・整数でない・負は 422。`0`（無制限）と正の整数は今までどおり。
- 試験: backend/tests/ に `test_distribution_settings_validation.py` を新設。K1 の 4 種で 422 と値が変わらないこと、K2 の 2 種で 200。
- 触らない: 読む側の `_max_age_hours` と `build_distribution_rows`。key が他の設定の扱い。

### 5-2. 画面で押させない（便2・frontend）

- 変更: frontend/src/pages/super-admin/components/DistributionSettingsDrawer.tsx だけ。
- (1) 中身（入力欄と保存ボタン）は `open` のときだけ描く。枠は共用の Drawer のまま（金型は変えない。開閉の動きは枠が持つ）。
- (2) 読み込み済みの印 `loaded` を足す。GET が成功するまで保存ボタンは押せない。
- (3) GET に失敗したら、入力欄を空のまま編集させる今の動き（:50）をやめ、エラー文を出して保存ボタンを押せないままにする。
- (4) 値が「空でない 0 以上の整数」でないとき、保存ボタンを押せない。入力欄の下に理由を出す。
- (5) 保存で 422 が返ったら、その理由を出す。
- 文言: `distributionSettings.errors.loadFailed` と `distributionSettings.errors.invalidValue` を ja.json・en.json に同じキーで足す（ADR-027）。色・余白は既存のトークンのみ（ADR-067・ADR-144）。
- 試験: Playwright の画面試験で K3（閉じているとき「保存」0 個）と K4（読み込み失敗で押せない）。
- 触らない: frontend/src/components/Drawer.tsx（金型）と AnalysisRulesPage.tsx。

### 5-3. 止まる前に人が気づく（便3・監視）

- 新しい警報 `ViewerInventoryExpiring` を monitoring/prometheus/alert_rules.yml の 245 行目の群に足す。
  - 条件: `(time() - viewer_inventory_updated_timestamp_seconds{job="backend"}) > 21600`（6 時間）。保留かどうかは問わない。`for: 5m`。
  - 札: `tier: page`、`severity: critical`。
  - 6 時間の理由: 写しの寿命は 24 時間（viewer_inventory_cache.py:33）。夜中に鳴っても、朝に直す時間が 12 時間以上残る。
- 届け先: monitoring/alertmanager/alertmanager.yml の routes に `tier="page"` の受け先を足す。今の受け先（認証の警報も来る場所）とは別の Discord の場所へ送る。`continue: true` で ops-api にも今までどおり送る。
- 新しい Discord の場所と webhook の鍵は PO が作る（secrets の変更は PO）。鍵は prod2 の `/etc/alertmanager/secrets/` に置く。
- 試験: monitoring/prometheus/tests/alert_rules_test.yml に「6 時間で鳴る」「5 時間 59 分では鳴らない」の 2 件。monitoring/scripts/check_alert_rules.py の検査を通す。
- 手順書: docs/runbooks/alerts.md に `ViewerInventoryExpiring` の節を足す。最初に見るものは設定の値と `[viewer-cache]` のログ。
- 除く: backend/app/tasks/viewer_inventory_cache.py:62-70 のテナント 4 宛ての Discord 通知。届け先が 0 件で 1 度も届いていない。届け先の正本は Alertmanager（ADR-1012）。失敗の記録（ログと回数）は残す。
- 対象外: AI の自動対応（ADR-1012 の routines）。ADR-1012 は Proposed で、まだ動いていない。動き出したら page の札で呼ばれる。

### 5-4. AI がブラウザでプログラムから押さない（便4・個人側の見張り）

- 新しい見張り `browser-click-guard` の原本を scripts/agent-hooks/browser-click-guard/ に置く（guard.py・install.sh・rollback.sh・試験）。置き方は docs/specs/local-hooks-ssot/README.md と ADR-1045 の前例に合わせる。
- 対象の道具（PreToolUse の matcher）: `mcp__claude-in-chrome__javascript_tool`・`mcp__playwright__browser_evaluate`・`mcp__playwright__browser_run_code_unsafe`。MCP の道具は `mcp__<server>__<tool>` の名前で照らせる（Context7: anthropics/claude-code の CHANGELOG と PreToolUse の型定義で確認）。
- 止める書き方: `.click(`・`dispatchEvent(`（MouseEvent・PointerEvent・SubmitEvent を作るもの）・`.requestSubmit(`・`.submit(`。止めたら `permissionDecision: "deny"` と、日本語で「押すときは画面の座標で押す道具を使い、押す前に画面写しで開いているパネルを確かめる」を返す。
- 通すもの: DOM を読むだけのプログラム（値・文字・数を取る）。
- 押すときの決まり: 画面の座標で押す道具（`computer` の left_click）だけを使う。これは本物のマウス操作なので、閉じたパネル（inert・画面外）には届かない。
- 試験: K6 の 3 つの書き方を止め、読むだけの 3 つを通すこと。
- 決まりの文: docs/ai-agents/executor-checklist.md に 1 行（「ブラウザで押すのは座標の道具だけ。プログラムから押すのは見張りが止める」）。

## 6. 弊害・トレードオフ

- 5-1: 今まで空にして「配信を止める」使い方があったなら、できなくなる。→ 実測で、空の保存は 11/10・11/11 の 2 回だけで、どちらも意図しない操作だった（recon §1）。閲覧ページだけを止める正規の手段は今は無い（`TCG_AUTO_DISTRIBUTE` はシートへの自動配信の切り替えで、閲覧の作り置きには効かない。backend/app/tasks/tcg_extraction.py:703）。必要になったら別の設計で足す。
- 5-2: 読み込みに失敗すると設定を直せない。→ エラー文で知らせる。空のまま保存されるよりは安全。
- 5-3: 新しい Discord の場所が増える。→ page の札は年に数回の想定。鳴りすぎたら KGI の測定（ADR-1012 の月次成績表）で見直す。
- 5-4: AI のブラウザ作業が遅くなる（1 回ずつ座標で押す）。→ 商品マスタの一括登録のような作業は、画面でなく API の正規の道で行う設計にする（別テーマ）。プログラムで押す必要がある正当な場面が出たら、PO の 1 回限りの許可（permit-danger.sh）で通す。

## 7. 外部・過去事例の参照と我々への応用

- 事例1: OWASP Input Validation Cheat Sheet（https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html 、2026-11-12 参照）は「入力の確かめはサーバー側で必ず行う。画面側の確かめは使い勝手のためで、守りにはならない」とする。→ 応用: 5-1 を守りの本体とし、5-2 は補助にする。今回、画面以外（AI のプログラム）から空が送られたので、この考え方が当てはまる。
- 事例2: Google SRE book 第 6 章（https://sre.google/sre-book/monitoring-distributed-systems/ 、2026-11-12 参照）「お客さんに見える症状で知らせる」「すべての page は動ける内容にする」。→ 応用: 5-3 は「写しが消える＝お客さんの画面が止まる」前の症状で 1 回だけ page にし、雑音と分ける。
- 過去事例: 本件（2026-11-10〜12・recon §1）。鳴った 14 件が雑音と同じ場所に流れ、対応 0 件だった。数値は recon §2 観点5。
- 数値の効果を示す外部の実測は見つけていない。効果は K7 の 90 日の数で測る。

## 8. 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| K1: 空・空白・`abc`・`-1` が 422 で値が変わらない | CI pytest `backend/tests/test_distribution_settings_validation.py`（便1で新設） |
| K2: `0` と `48` が保存できる | CI pytest 同上 |
| K3: 閉じているとき「保存」0 個 | Evaluator（Playwright の画面試験・便2で新設） |
| K4: 読み込み失敗で保存を押せない | Evaluator（Playwright の画面試験・便2で新設） |
| K5: 6 時間で鳴り 5 時間 59 分で鳴らない・本番で 1 回届く | CI promtool（`monitoring/prometheus/tests/alert_rules_test.yml`）＋本番の試し鳴らし（amtool で 1 回送る） |
| K6: プログラムの押下 3/3 を止め、読むだけ 3/3 を通す | 見張りの試験（scripts/agent-hooks/browser-click-guard/ の試験・便4で新設） |
| K7: 同じ原因の停止 0 回（90 日） | 本番 Loki と ops_incidents を reader 鍵で数える |

## 9. 計画票

| 便 | 内容 | 担当 | PO の操作 |
|---|---|---|---|
| 1 | API で断る（5-1）＋試験 | クラウドの Sonnet | 実装承認 |
| 2 | 画面で押させない（5-2）＋画面試験＋文言 | クラウドの Sonnet | 実装承認 |
| 3 | 6 時間の警報と別の届け先（5-3）＋テナント 4 宛て通知を除く | クラウドの Sonnet | Discord の場所と webhook の鍵を作る（secrets） |
| 4 | ブラウザの見張り（5-4） | クラウドの Sonnet（原本）・Opus（Mac に入れる） | 見張りを Mac に入れる許可 |

- 便1 を最初に出す。これだけで今回の原因（どこから送られても空は保存されない）が止まる。
- 1 便ずつ反映して測ってから次へ（変更は一度に 1 つ）。

## 10. 維持の仕組み

- 守り手: `.github/workflows/process-artifacts-gate.yml`（この設計の recon・design の相互参照）
- 守り手: CI の pytest（便1の試験。空の保存が通るように戻すと赤になる）
- 守り手: CI の promtool（`monitoring/prometheus/tests/alert_rules_test.yml`。6 時間の警報を消すと赤になる）
- 守り手: Playwright の画面試験（便2）
- 守り手: 個人側の見張り browser-click-guard（便4。原本は repo、変更は PR のみ）
- 守り手: ADR-1012 の月次成績表（page の札の鳴った数と対応の数）
- 対象: 設定の書き口・設定パネル・閲覧の作り置きの警報・AI のブラウザ操作

## 11. 接触面分析（6 面）

- 逆参照: `max_age_hours`・`DistributionSettingsDrawer`・`ViewerInventoryStale`・`_record_failure` を拡張子を問わず grep（.md 含む）。recon §0・§2 に記載。
- ①人: PO は便3で Discord の場所と鍵を作る。設定画面で空を保存できなくなる（今まで空にする必要は無かった）。
- ②エージェント: ブラウザでプログラムから押せなくなる（便4）。executor-checklist に 1 行足して周知する。並行セッションには見張りの文で伝わる。
- ③機械: CI の pytest・promtool・Playwright に試験が増える。Alertmanager の routes が 1 本増える。
- ④データ: 設定表 `tcg_distribution_settings` の値の形は変えない（列・表は増やさない）。tenant_004 のデータには触らない。
- ⑤本番: 便1・便2 は通常の配備。便3 は prod2 の Alertmanager の設定と鍵（PO）。migrations は無い。
- ⑥外部: お客さん（閲覧者）への見え方は変わらない。止まりにくくなるだけ。Discord に場所が 1 つ増える。

## 12. 設計審査（同一 AI による自己審査・独立した第二者レビューではない）

- 判定: **APPROVE（設計合格）**。ただし KGI は PO 未承認のため、実装カードは出さない。
- 根拠:
  - 既存の正本との整合: 設定の読み口 `_max_age_hours` を書き口でも使い、規則を 1 か所にする（SSOT）。警報の経路は ADR-1012 の Alertmanager に寄せ、独自の Discord の道を除く。金型 Drawer は変えない。
  - 受入条件は全部、CI か実測で ○× が決まる（§8）。
  - 便ごとに触るファイルと触らないファイルを書いた（§5）。
- 未解決（PO の判断が要る）:
  - KGI 7 件の承認（特に K5 の「6 時間」）。
  - 便3 の新しい Discord の場所を作るか（作らない場合は、今の場所に @ 付きで送る案になる）。
- 未確認（実装前に確かめる）:
  - inert のボタンにプログラムの `.click()` が届くか（recon §3）。設計はこれに頼らないので、合否には影響しない。
