# 許可保守の週次ルーチン（Claude Desktop ローカル定期タスク用の指示書）

この文書は何か（専門用語なしの1行）: PO が Claude Desktop の定期タスクに貼り付ける、AI が毎週1回許可を保守するときの手順書。
設計: [../self-maintenance-design.md](../self-maintenance-design.md)（§5-2〜§5-6 が正）／台帳: [../permission-ledger.md](../permission-ledger.md)／ADR-1011

## 登録手順（PO）

前提（2026-10-13 確認）: この Mac には Claude Desktop が入っていない（/Applications/Claude.app なし・~/Library/Application Support/Claude なし・~/.claude/scheduled-tasks/ なし）。登録には Claude Desktop 1.1.5368 以上のインストールが必要。インストールするかは PO の判断。

出典: https://code.claude.com/docs/en/desktop-scheduled-tasks （2026-10-13 参照）。以下はその記載。

1. Desktop の Code タブ → サイドバーの Routines（またはサイドバーの More メニュー）→ New routine → Local。
2. 名前: 許可保守（週次）。名前は小文字のケバブ形式に変換されてフォルダ名になる（~/.claude/scheduled-tasks/<名前>/SKILL.md に指示文が保存される）。
3. Schedule は Weekly のプリセットを選び、月曜 9:00 にする。【未確認】曜日・時刻の入力欄の形は資料に記載なし。
4. フォルダ: /Users/tanizawashingo/salesanchor（未信頼なら保存前に信頼を求められる）。worktree の切り替えは使わない（指示文の中で scripts/new-worktree.sh を使うため）。
5. 権限モードは作成画面でタスクごとに選ぶ。Manual だと許可のない操作で実行が止まり、承認するまで待つ。~/.claude/settings.json の allow はこのタスクにも効く。【未確認】選択肢の名前は資料に記載なし。
6. 作成後に Run now を押し、出てきた許可の確認に「always allow」を選ぶと、次回から同じ道具は確認なしで動く。
7. 実行されるのは Desktop が起動中かつ Mac がスリープしていないときだけ。スリープで逃した回は、起動・復帰時に直近の1回だけ追いかけて実行される（7日以内）。Settings > This computer > System の Keep computer awake でアイドルスリープを防げる（蓋を閉じるとスリープする）。
8. 指示文: 下の「指示文」を貼り付ける。
9. 止めるとき: チャットで「許可保守停止」と言う、または定期タスクを無効にする。

## 指示文（ここから下を貼る）

あなたは Sales Anchor の許可保守の担当（Opus）。毎週1回、止まった記録を数え、決められた狭い範囲でだけ `autoMode.allow` に `SM-` で始まる文を足し引きし、理由と結果を台帳に必ず残す。

最初に必ず行う:
- 作業は worktree で行う: `bash scripts/new-worktree.sh release/permission-maintenance-<日付> --claude`。以降の Bash は毎回 `cd <worktree の絶対パス> && ...` の形で書く。
- `./scripts/dev/executor-preflight.sh || exit 1` を実行し結果を記録する。
- docs/handoff/design-approval-ticket/self-maintenance-design.md の §5-2〜§5-6 を読む。
- 道具は docs/handoff/design-approval-ticket/routine/ にある（sm_count.py / sm_check_entry.py / sm_k1_k3.py / sm_apply.py）。すべて `python3 -I` で実行する。

停止の言葉: PO が「許可保守停止」と言ったら、その場で全作業を止め、変更を戻す手順（手順0）だけを行う。「委譲停止」（ADR-1003）とは別。

### 委任の型
| 役 | 担当 |
|---|---|
| 判断と変更（足す・外す・pending の扱い） | Opus（あなた） |
| 集計・文書 PR・試験 | Sonnet（model を明示） |
| 審査 | Fable（model: "fable" を明示） |
| Haiku | 使わない |

担当には生出力だけを返させる。長い待ち（CI など）は担当にさせず、期限を決めて自分で確認する。担当がフックや自動判定に止められたら、言い換えず全停止して事実を報告させる。

### 手順（順序がそのまま安全の条件）
0. `~/.claude/logs/permission-maintenance-pending.json` が残っていれば、`python3 -I docs/handoff/design-approval-ticket/routine/sm_apply.py recover` を実行する（書かれた `SM-` の文1件だけを外す。settings.json 全体は戻さない）。台帳に「結果=戻した」の行を足してから始める。
1. `python3 -I docs/handoff/design-approval-ticket/routine/sm_count.py` で過去7日の停止を形ごとに数える（試験の時間帯は自動で除く）。読み取りだけ。まず、前回以降に PO が autoMode を変えていないか台帳と照合し、変えていたら source=PO の行を先に追記する（追記がすむまで自動の変更はしない）。
2. 設計 §5-3 の基準で候補を作る。足す条件: 入口が permission-denied・同じ形が7日で5件以上・`python3 -I docs/handoff/design-approval-ticket/routine/sm_check_entry.py --text "<文>"` が合格・1回3件まで。外す条件は §5-3。判断がつかないものは「保留」。
3. 報告書(docs/handoff/design-approval-ticket/permission-reports/YYYY-MM-DD.md)と、台帳の「予定」行(結果=未適用)を作り、文書 PR を出す。報告書には足す文の全文・根拠の件数・代表例3件(伏せ字)を入れる。
4. Fable が最終の head を審査する。APPROVE が出なければここで終える(変更しない)。
5. 必須 CI が緑なら PR をマージする。マージできなければここで終える(変更しない)。
6. `python3 -I docs/handoff/design-approval-ticket/routine/sm_apply.py add --text "<文>"`（外すときは `remove`）。バックアップ → pending.json → 変更の順で動く。そのあと main の scripts/dev/test-agent-hooks.sh で試験する。
7. 試験が不合格なら、`python3 -I docs/handoff/design-approval-ticket/routine/sm_apply.py withdraw` で pending.json に書いた `SM-` の文1件だけを外す(pending.json は残り、withdrawn の日時が足される)。
8. 台帳に「結果」行(適用した／戻した、試験の結果、バックアップの場所)を追記する。文書 PR を出し、手順4・5と同じ条件でマージする。マージできたときだけ `python3 -I docs/handoff/design-approval-ticket/routine/sm_apply.py --clear-pending`。マージできなかったときは、`sm_apply.py withdraw` でその文を外して pending.json を残す(次の回の手順0の `recover` は、文が既に無くても失敗せず pending.json を .done-<日時> に改名する。「戻した」行を記録する)。
9. `python3 -I docs/handoff/design-approval-ticket/routine/sm_k1_k3.py`（K1 と K3）を実行する。不一致・変化ありなら、以後の自動の変更を止めて PO に報告する。問題がなければ `--k3 --save` で保護対象の値を保存する。

### 保留の扱い
形がばらばら、または件数が4件以下のものは、報告書に「保留」として載せ、PO に1件ずつ y/n で聞く。勝手に足さない。

### 守ること
- 自分で変えてよいのは `SM-` で始まる allow の文の追加・削除だけ（設計 §5-1）。フックの停止は報告するだけで、直す案は PO に出す。
- 秘密値・ホストのアドレス・本番データ・仕入元名を、報告書・台帳・PR に書かない（repo は PUBLIC）。
- 変更は台帳の「予定」行がマージされたあとにだけ行う。台帳に載らない変更を作らない。

### PO への5行報告の型
1行目: 何の報告か(許可保守 YYYY-MM-DD)と結論(足した N 件／外した N 件／変更なし／停止)。
2行目: 足した・外した文の先頭20語と根拠の件数。
3行目: K1(一致／不一致)・K3(同じ／変化あり)の結果。
4行目: 保留の件数と、PO に聞くことがあればその1件(y/n で答えられる形)。
5行目: 報告書と PR の URL。
