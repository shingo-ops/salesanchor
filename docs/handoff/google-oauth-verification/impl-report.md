# 実装報告: Google カレンダーの許可を狭める

BLOCKED: executor-preflight が失敗（GitHub API に到達不可・gh を shingo-cc に切り替えられない）。指示の `|| exit 1` に従い、実装に入らず止めた

## 経過

- 取得: `git fetch origin main release/google-oauth-verification-plan release/google-calendar-narrow-scope-review2` は成功。カードと審査2回目（APPROVE）は読んだ。
- 作業場所: `bash scripts/new-worktree.sh release/google-calendar-narrow-scope --claude` は作成できた（`/root/worktrees/salesanchor/release-google-calendar-narrow-scope`）。末尾の Claude 起動だけ `Input must be provided either through stdin or as a prompt argument when using --print` で失敗（作成自体は完了）。
- preflight（作業場所で実行）。出力の全文:

```
== executor preflight (identity=shingo-cc, mode=fix) ==
[1/3] network -> api.github.com
  [FAIL] GitHub API に到達不可。Mac回線ではなく実行役サンドボックスの通信OFFが濃厚。
       => Codexをネット有効で起動 (信頼repo内: codex --sandbox danger-full-access / または config の network_access=true)
[2/3] gh auth = shingo-cc
  [warn] gh の active account が shingo-cc でない。gh auth switch で切り替え試行...
  [FAIL] gh auth switch --hostname github.com --user shingo-cc に失敗。gh auth status --active で現状を確認。
[3/3] git config user.name = shingo-cc
  [OK]   git user.name を shingo-cc に設定
[4/4] long-lived branch -> origin/main
  [OK]   origin/main は存在
==============================================
PREFLIGHT FAIL — 上の対策を実施し再実行(深追いしない)
exit=1
```

## 止められた命令

- 見張りに止められた命令は無い。

## 未実施（事実）

- 変更1〜6・試験・確かめ（pytest・vitest・eslint・tsc）は一切実行していない。コードは変えていない。
- 実装用の枝 `release/google-calendar-narrow-scope` は作業場所だけ作成済み（commit・push なし）。

## 判断してほしいこと

- クラウドには gh の shingo-cc 認証が入らず、preflight は毎回落ちる見込み。クラウドで preflight を免除してよいか（git push は通る前提）、または手元で実行するかを PO に確認したい。

BLOCKED: executor-preflight 失敗（GitHub API 不達・gh が shingo-cc に切替不可）
