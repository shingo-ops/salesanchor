# 実装カード schedule-settings 便1 直し1 — 自動の確認3件を通す

> この文書は何か：PR #5753 のマージ前審査（2026-11-25・REQUEST_CHANGES）で見つかった、CI の落ち3件を直す作業指示書です。設計（design.md §2〜§5）の中身は変えません。

- 元のカード: `docs/handoff/schedule-settings/card-bin1.md`
- 枝: 既存の `release/schedule-settings-google`（HEAD d2588cbe0 の上に足す）
- 担当: 実装 Sonnet（クラウド）は push まで／審査・マージ Opus
- 範囲を広げる理由（Opus 判断・設計からのずれなし）: 下の2ファイルは、便1の変更に機械的についてくる付属物です。1つ目は裏側の説明文から自動で作る「受け口の一覧」です。2つ目は、消した文字キーの数え台帳です。どちらも機能の中身は変えません。

## 触るファイル（これ以外は触らない）

1. `frontend/api-contract/openapi.json`（自動生成。手で書かない）
2. `frontend/scripts/error-text-next-action-baseline.json`（`schedule.connectBtnError` の1行を消すだけ）
3. `frontend/src/pages/schedule/ScheduleSettingsPage.test.tsx`（試験の色の値だけ）

## 直し1 受け口の一覧を作り直す（CI「API contract is up to date」）

- `cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json`
- 差分が `DELETE /google-calendar/connect` の説明文の変化だけであることを `git diff --stat` と `git diff frontend/api-contract/openapi.json` で確かめ、生の出力を残す。他の場所も変わったら止まる（BLOCKED）。

## 直し2 数え台帳から消したキーを外す（CI「Frontend lint & custom checks」の check:error-text-next-action）

- `frontend/scripts/error-text-next-action-baseline.json` の `"schedule.connectBtnError"` の行だけを消す（前後のカンマを JSON として正しく保つ）。
- `cd frontend && npm run check:error-text-next-action` が通ることを確かめる。

## 直し3 試験の色を hex で書かない（CI「guard-hex-increase」）

- `ScheduleSettingsPage.test.tsx` の 44・45・202 行目の `"#112233"`・`"#445566"` を、hex ではない色の文字列（例: `"rgb(17, 34, 51)"`・`"rgb(68, 85, 102)"`）に変える。202 行目の期待値は 44 行目と同じ値にそろえる。
- 禁止: `"#" + "112233"` のように文字をつないで見張りを避ける書き方。見張りの例外リストを触ること。
- `grep -cE '#[0-9a-fA-F]{3,8}\b' frontend/src/pages/schedule/ScheduleSettingsPage.test.tsx` が 0 になることを確かめる。

## ついでに直してよい小さな点（同じ試験ファイルの中だけ）

- 209 行目で `Element.prototype.scrollIntoView` を差し替えたまま戻していない。元の値を取っておき、試験の終わりで戻す。

## 確かめ

- `cd frontend && npx vitest run src/pages/schedule src/components/ToggleMigration.test.tsx src/lib/query/batch3bPages.test.tsx` の生の出力を残す。
- `cd frontend && npx eslint src/pages/schedule`
- `cd backend && python -m pytest tests/test_google_calendar.py -q`
- `BASE_SHA=$(git merge-base origin/main HEAD) HEAD_SHA=HEAD bash scripts/check-design-token-ratchet.sh`
- 提出前: `bash scripts/dev/check-before-submit.sh`
- commit（`--no-verify` は使わない。末尾に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）→ `git log -1 --oneline`
- `git push -u origin HEAD` → `git log origin/release/schedule-settings-google -1 --oneline`

## 停止する条件（BLOCKED: で返す）

- 触るファイル以外を変える必要が出た。
- openapi.json の差分が disconnect の説明文以外にも出た。
- 試験が、この直しと関係なく落ちる。

## 報告

- 冒頭に「本報告はカード schedule-settings 便1 直し1 の実行結果である」。1 行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容
- 本文に: 各確かめの生の出力の場所と末尾・push した commit

## 委任の定型

- sleep は使わない。CI は待たない
- PR は作らない。main にマージしない。本番と倉庫の設定に触れない
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える

END OF CARD
