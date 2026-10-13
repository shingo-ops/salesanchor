---
mode: handoff
status: draft（PO 決定 2026-10-14 に基づく文書変更）
---

# recon: 許可保守の定期実行を agent-console に移すときの現在地

この文書は何か（専門用語なしの1行）: 許可の週次保守（ADR-1011）を Claude Desktop ではなく自作アプリ agent-console の定期実行で回すために、いま何がどう書かれていて、アプリに何ができて何ができないかを、実物の場所つきで調べた記録。
親: [../design-approval-ticket/self-maintenance-design.md](../design-approval-ticket/self-maintenance-design.md)／子: [design.md](design.md)／設計仕様書（あるべき姿）: 対象外（純粋な書類の変更のため）

- 基準: salesanchor は origin/main（4803be067）、agent-console は origin/main（f255892。v0.19.0 は cf34d4a で origin/main の祖先、server/ の差分なし）。導入済みアプリの healthz は version 0.17.0（commit df660d0）。
- 調査: 読み取りのみ。生の調査メモ: /tmp/CC報告ファイル/routine-on-ac/recon.md（repo の外）。
- 行番号は変更前（origin/main）のもの。

## 0. 既存 ADR の検索結果

- `docs/adr/ADR-1011-permission-self-maintenance.md:15` — 「週1回の定期実行」とだけ書く。`:60` — 「定期実行の手順9」。Desktop 固定の記述なし（grep "desktop|Routines|定期タスク|scheduled-tasks" で該当なし）。よって ADR-1011 は変更しない。
- `docs/handoff/design-approval-ticket/design.md`、`docs/handoff/design-approval-ticket/permission-ledger.md` も同じ grep で該当なし。
- 実行基盤を決める別の ADR: 見つからなかった（`git grep -i` で docs/adr/ を検索し、`docs/adr/FEATURE-INDEX.md` も確認。Desktop 採用の根拠は `docs/handoff/design-approval-ticket/self-maintenance-design.md:54` の「PO 採用 2026-10-11」の1行だけ）。

## A. 週次保守の要件（salesanchor 側）

### A1. ROUTINE.md（`docs/handoff/design-approval-ticket/routine/ROUTINE.md`）

- `docs/handoff/design-approval-ticket/routine/ROUTINE.md:14` — 頻度は週1・月曜 9:00。作業フォルダ /Users/tanizawashingo/salesanchor、worktree の切り替えは使わず、指示文の中で scripts/new-worktree.sh を使う（同 `:15`）。
- `docs/handoff/design-approval-ticket/routine/ROUTINE.md:24-69` — 指示文。役は Opus。最初に new-worktree.sh（`:27`）、executor-preflight.sh（`:28`）、self-maintenance-design.md §5-2〜§5-6 を読む（`:29`）。委任は Sonnet（集計・文書 PR・試験、model 明示）と Fable（審査、model:"fable" 明示）、Haiku は使わない（`:34-40`）。手順0〜9（`:44-54`）。
- `docs/handoff/design-approval-ticket/routine/ROUTINE.md:16-17` — 権限モードは作成画面でタスクごとに選ぶ。Manual は許可のない操作で止まる。~/.claude/settings.json の allow は効く。Run now で always allow を選ぶ。
- `docs/handoff/design-approval-ticket/routine/ROUTINE.md:6-21` — Desktop 固有の登録手順の全体。`:8` — この Mac に Claude Desktop は無い（2026-10-13 確認）。`:18` — 取りこぼした回は復帰時に直近の1回を追い付く（7日以内）。
- `docs/handoff/design-approval-ticket/routine/ROUTINE.md:9,32` — 停止の言葉は「許可保守停止」。

### A2. 「Desktop」固定の記述（書き換え対象）

- `docs/handoff/design-approval-ticket/self-maintenance-design.md:54` — 定期実行は Desktop のローカル定期タスク（PO 採用 2026-10-11）。
- `docs/handoff/design-approval-ticket/self-maintenance-design.md:179` — 「定期タスクを Desktop の画面で登録する」。`:181` — 「Desktop の定期タスク」。`:194` — S4「Desktop の画面で登録」。
- `docs/handoff/design-approval-ticket/s4-card.md:38` — ROUTINE.md は Desktop のローカル定期タスク用。`:45` — 登録手順 Desktop → Code → Routines → New routine → Local。
- `docs/handoff/design-approval-ticket/routine/ROUTINE.md:1` — 題。`:6-21` — 登録手順全体。`:8` — 前提。
- 証拠: /tmp/CC報告ファイル/routine-on-ac/desktop-grep.txt（6行）。

### A3. 道具の実行時要件（routine/*.py。すべて標準ライブラリ、`python3 -I`）

- `docs/handoff/design-approval-ticket/routine/sm_count.py:21-23` — ~/.claude/logs/permission-denied.jsonl、agent-events.jsonl を読むだけ。
- `docs/handoff/design-approval-ticket/routine/sm_check_entry.py:20` — ~/.claude/settings.json を読む。
- `docs/handoff/design-approval-ticket/routine/sm_k1_k3.py:24-29,173` — ~/.claude/logs、settings.json、~/.claude/scripts を読み、`--k3 --save` で保存値を書く（権限 0o600）。
- `docs/handoff/design-approval-ticket/routine/sm_apply.py:27-28` — ~/.claude/settings.json を書き、バックアップと ~/.claude/logs/permission-maintenance-pending.json を書く。対話の承認コードは無い（`input()` 該当なし）。
- ネットワーク: 道具自体は `urlopen` 無し。手順（PR 作成・マージ・CI 確認・Fable 審査）は gh / git で外部通信が必要。
- 承認: `docs/handoff/design-approval-ticket/self-maintenance-design.md:71-73` の「例外の文」を PO が `!` で1回 autoMode.allow に書く前提（`:49,:63,:179`）。効かない場合は「AI が案 → PO が `!` で反映」に戻す（`:149`）。S2 での効果は `docs/handoff/design-approval-ticket/permission-reports/2026-10-13-s2-trial.md`（本書では精読していない）。

### A4. 「今週の分が済んでいるか」の判定に使える記録（既存の文書が定めるもの）

- 報告書: `docs/handoff/design-approval-ticket/routine/ROUTINE.md:48`（手順3「報告書(docs/handoff/design-approval-ticket/permission-reports/YYYY-MM-DD.md)…を作り、文書 PR を出す」）。ファイル名の規則は `docs/handoff/design-approval-ticket/permission-reports/README.md:5`（YYYY-MM-DD.md、その週の実行日）。K4 は「permission-reports/ にできる報告書の数」で数える（`docs/handoff/design-approval-ticket/self-maintenance-design.md:24`）。
- 作業ブランチ: `docs/handoff/design-approval-ticket/routine/ROUTINE.md:27`（`release/permission-maintenance-<日付>`）。そこから出る文書 PR（手順3・手順8）。
- 注意: 同じディレクトリに 2026-10-13-s2-trial.md がある（`docs/handoff/design-approval-ticket/permission-reports/2026-10-13-s2-trial.md`）。日付だけで前方一致すると週次報告と誤認するため、判定は YYYY-MM-DD.md の形そのものに限る。
- 台帳（`docs/handoff/design-approval-ticket/permission-ledger.md`）の行は、候補が無い週に行が作られるか文書から特定できないため、判定材料にしない。

## B. agent-console

- B1 時刻: weekdays:number[]（0-6、重複不可）＋ timeHHmm（"HH:mm"）＋固定の Asia/Tokyo。`/Users/tanizawashingo/agent-console/server/routines.ts:14-15`（TZ と TIME）、`:52`（Sun=0 の曜日表）。cron 式は無い。時刻一致は 1 秒ごとの tick で、現在の分との一致だけを見る（`:72,:95`）。月〜金の 9:00 は weekdays=[1,2,3,4,5]、timeHHmm="09:00"。
- B2 セッション: 登録項目は roleId / cwd / branch? / promptText / name（`/Users/tanizawashingo/agent-console/server/routines.ts:30-32`、検査は `:78-:87`）。promptText は 8192 字以内・制御文字なし（`:17,:23,:80`。制御文字の定義は U+0000-0008 と U+000B-001F と U+007F で、改行 U+000A と タブ U+0009 は可）。cwd は本店か git worktree のみ（`:83-:84`、resume-targets.ts:43-50）。
  - 役: `/Users/tanizawashingo/agent-console/agent-console.config.json` の opus-designer は needsWorktree=false、command=['/bin/zsh','-ic','ccopusgo']。needsWorktree=true の役は branch 必須（server/routines.ts:85）。よって salesanchor 本店で opus-designer を開ける。
  - モデルと effort は役の起動コマンド（ccopusgo）で決まり、定期実行側では指定できない。実プロセスで `claude --model opus --effort medium --permission-mode auto --append-system-prompt …` を確認。
  - 送信: 入力待ちになったら 3 秒間隔・最大 120 秒待ち、括弧付き貼り付けのあと "\r"（`server/routines.ts:19-20,:122-125`）。
- B3 登録: 画面（`/Users/tanizawashingo/agent-console/src/components/Routines/`）と HTTP API（server/http.ts:170-175）。API は認証付きの前提で、認証方式は未確認。保存先は <dataDir>/routines.json（既定 ~/Library/Application Support/agent-console、server/config.ts:32）。稼働中のファイル直編集の反映は未確認（起動時の `start()` で読むだけ、server/routines.ts:72）。
- B4 取りこぼし: 追い付かない（/Users/tanizawashingo/agent-console/docs/handoff/routines-new-session/design.md:14「対象外: …取りこぼした回の追い付き」、`:39`「取りこぼした回は追い付かない」）。tick は現在の分の一致だけ（server/routines.ts:95）。二重起動は lastSlot を先に保存して防ぐ（`:98-99`）。
- B5 記録: routine ごとに最大 100 件 {at, slot, outcome, sessionName?}（`server/routines.ts:18,:30`）。outcome は sent / not_ready / full / cwd_invalid / failed。開いたセッションは通常のセッションとして残り、自動では閉じない（上限 16）。保守の成否は routines.json には残らない。
- B6 実機確認 K15: /Users/tanizawashingo/agent-console/docs/handoff/routines-new-session/design.md:84（導入後。2〜3 分後の時刻で 1 件登録 → 新しいセッションが開き、確認画面ではなく入力欄に指示が入り、履歴が「送信済み」）。`:60` に【未確認】（フォルダの信頼などの確認画面で指示が入るか）。
- B7 版: healthz は version 0.17.0。「毎回新しいセッションを開く」動作（lastSlot、version 2 の保存形式）は v0.18.0 の変更（`git diff v0.17.0 v0.18.0 -- server`、routines.ts が +101 行）。導入済みの 0.17.0 は旧仕様（専用セッションへ送る）。本件には v0.18.0 以上の導入が要る。K15 は未実施。

## C. Desktop 前提で agent-console では満たせない・要確認の要件

1. 取りこぼしの追い付き（`docs/handoff/design-approval-ticket/routine/ROUTINE.md:18`）: 無い。Mac のスリープやアプリ停止の回は飛ぶ。
2. 権限モードの選択（`docs/handoff/design-approval-ticket/routine/ROUTINE.md:16`）: 無い。ccopusgo 経由で auto 固定。Desktop の always allow 相当も無い。
3. モデル指定: ROUTINE.md の Sonnet・Fable の model 明示（`docs/handoff/design-approval-ticket/routine/ROUTINE.md:34-40`）が opus-designer の中で可能かは未確認。
4. 手順の worktree 作成（`docs/handoff/design-approval-ticket/routine/ROUTINE.md:27`）: 本店で opus-designer が実行する形で可。セッションは通常の Claude。
5. 指示文の長さの上限 8192 字（`/Users/tanizawashingo/agent-console/server/routines.ts:17`）。変更前の指示文 L24-L69 の長さは未計測だった。変更後の長さは design.md に記す。
6. 実行結果の自動集約が無い。sent は指示を送っただけで成功ではない。結果は報告書・PR で確かめる。
7. 開いたセッションが上限 16 を消費する。毎日起動にすると、済んでいる日も短いセッションが 1 つ増える。
8. 導入済みの 0.17.0 は旧仕様。v0.18.0 以上の導入が先に要る。

## D. 未確認一覧

- API の認証方式と、稼働中の routines.json 直編集の反映（本変更では API を使わない）。
- 既定 dataDir の実在と routines.json の有無。
- 起動直後の確認画面（信頼など）に指示が入るか（K15 で確認）。
- auto モードの opus-designer で、SM- 例外の文が効くか（S2 の記録は未精読）。
- opus-designer から Sonnet と Fable を model 指定で呼べるか。
- メモリ scheduled_assistant_decision（repo の外）の更新要否。
- 候補が無い週に台帳の行・報告書が作られるか（ROUTINE.md:48 の手順3は条件分岐を書いていないため、報告書は作られる前提で判定材料にした。台帳は判定に使わない）。
