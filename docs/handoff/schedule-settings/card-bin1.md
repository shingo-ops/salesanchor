# 実装カード schedule-settings 便1 — 設定ページに Google 連携の区画を作り、解除で許可を取り消す

> この文書は何か：スケジュール設定ページ整備の便1（DB 変更なし）の作業指示書です。

- 設計: `docs/handoff/schedule-settings/design.md` §2〜§5
- 状態: 要件は PO 承認済み（2026-11-25「1」）。実装・マージ・本番反映までの委任も同日。本カードは設計の範囲を変えない
- 危険便: いいえ（`migrations/`・`deploy.yml`・`scripts/` を触らない）
- 担当: 実装 Sonnet（クラウド）は push まで／PR 作成・審査・マージ Opus
- 枝: `origin/main` から `release/schedule-settings-google`（`bash scripts/new-worktree.sh release/schedule-settings-google --claude` で場所を作る。clone のまま commit しない）
- 触るファイル（これ以外は触らない）:
  1. `backend/app/services/google_calendar.py`
  2. `backend/app/routers/google_calendar.py`
  3. `backend/tests/test_google_calendar.py`
  4. `frontend/src/pages/schedule/SchedulePageImpl.tsx`
  5. `frontend/src/pages/schedule/SchedulePageImpl.test.tsx`
  6. `frontend/src/pages/schedule/ScheduleSettingsPage.tsx`
  7. `frontend/src/pages/schedule/ScheduleSettingsPage.test.tsx`（新規）
  8. `frontend/src/pages/schedule.css`（`.schedule-settings__nav*` を消すときだけ）
  9. `frontend/src/components/ToggleMigration.test.tsx`（設定ページの行を外す）
  10. `frontend/src/locales/ja.json`・`frontend/src/locales/en.json`
  11. `.claude-pipeline/active-work.d/release-schedule-settings-google.md`（台帳）

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md・03-file.md・04-worktree.md・05-pr.md・10-executor.md。照合: 場所は new-worktree.sh で作る（04）・PR は担当が作らない（05）・プレースホルダなし（00）・push は `git push -u origin HEAD`（04）・各段で `git log` を確かめる（00）。

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード schedule-settings 便1 の実行結果である」と書くこと。
## 変更1 取り消しの関数
design §3-1 のとおり `revoke_tenant_token`・`GoogleRevokeError`・`_REVOKE_URL`・`_error_code` を足す。合鍵の値はログに出さない。

## 変更2 解除の受け口
design §3-2 のとおり `disconnect` を「通知の窓口を止める → 取り消す → 行を消す」に変える。失敗は 502 `google_revoke_failed` で行を残す。`calendar_events` には触れない。

## 変更3 戻り先
design §3-3 のとおり `connect_callback` の戻り先を `/schedule/settings` にする（5 か所）。

## 変更4 予定ページ
design §4-1 のとおり。見出しのつなぐボタンと `?connected=` の処理を消し、歯車の条件を `canManageOwners || isTenantAdmin` にする。`gcalStatusQ` と `banner` は残す。

## 変更5 設定ページ
design §4-2 の 1〜6 のとおり。特に §4-2 の 1 の「読み込み中の扱い（審査 R1）」を守る: 読み込みの丸は持ち主の 2 区画だけに出し、Google 区画と左の並びは包まない。管理者で staff.view が無い人でも Google 区画が出ること。金型は `SubMenu`・`SectionCard`・`ConfirmModal`・`Button` だけ。新しい色の直書き・生の button/select/input を足さない（ADR-144・ADR-067）。

## 変更6 文字
design §4-3 の表のキーを ja/en の `schedule` に足す。`connectBtn`・`connectBtnConnected`・`connectBtnError` を両方から消す（消す前に `grep -rn "connectBtn" frontend/src` で使う所が触るファイルの中だけか確かめる）。

## 試験
design §5 の表のとおり。外への通信（httpx）は差し替える。

## 確かめ
- `cd backend && python -m pytest tests/test_google_calendar.py -q` の生の出力をファイルに残す。
- `cd frontend && npx vitest run src/pages/schedule src/components/ToggleMigration.test.tsx src/lib/query/batch3bPages.test.tsx` の生の出力を残す。
- `cd frontend && npx tsc --noEmit` と `npx eslint src/pages/schedule`。
- i18n の自己点検（`frontend/CLAUDE.md`）。
- 提出前: `bash scripts/dev/check-before-submit.sh`。
- commit（`--no-verify` は使わない）→ `git log -1 --oneline`。
- `git push -u origin HEAD` → `git log origin/release/schedule-settings-google -1 --oneline`。
- PR は作らない（Opus が作る）。`migrations/`・`deploy.yml` は触らない。

## 停止する条件（BLOCKED: で返す）
- 触るファイル以外を変える必要が出た。
- `stop_webhook` が設定行を消した後に呼ばれる形でしか書けない。
- 既存の試験が、この変更と関係なく落ちる。
- 金型に無い部品が要る。

## 報告

- 冒頭に受領文。1 行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか
- 本文に: 試験・型・lint の生の出力のファイルの場所と末尾・push した commit・判断を要した点（事実のみ）
- 停止したときは: 停止した手順／最後に実行したコマンド／停止した理由の原文

## 委任の定型

- sleep は使わない。CI は待たない
- PR は作らない。main にマージしない。本番と倉庫の設定に触れない
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える

END OF CARD
