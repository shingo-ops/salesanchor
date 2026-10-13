# 許可保守の週次ルーチン（agent-console の定期実行用の指示書）

この文書は何か（専門用語なしの1行）: PO が自作アプリ agent-console の定期実行に登録する、AI が毎週1回許可を保守するときの手順書。月〜金の朝9時に毎日起動し、その週の分が済んでいれば何もせず終える。
設計: [../self-maintenance-design.md](../self-maintenance-design.md)（§5-2〜§5-6 が正）／台帳: [../permission-ledger.md](../permission-ledger.md)／ADR-1011／実行基盤の変更記録: [../../permission-routine-on-agent-console/design.md](../../permission-routine-on-agent-console/design.md)

## 登録手順（PO）

前提:
- agent-console v0.18.0 以上が導入済みであること（2026-10-14 時点の導入済みは 0.17.0。v0.19.0 への更新は手空き待ち。0.17.0 は旧仕様で、毎回新しいセッションを開く動作にならない）。
- agent-console リポジトリの docs/handoff/routines-new-session/design.md の K15（導入後の実機確認: 2〜3分後の時刻で1件登録し、新しいセッションが開き、確認画面ではなく入力欄に指示が入り、履歴が「送信済み」になること）が合格済みであること。

登録内容（アプリ画面の「定期実行」から登録する。HTTP API は認証方式が未確認のため、この文書では使わない）:

| 項目 | 値 |
|---|---|
| 名前 | 許可保守（週次）（1〜40字） |
| 役割 | opus-designer |
| 作業フォルダ | /Users/tanizawashingo/salesanchor（本店。worktree の切り替えは使わない。指示文の中で scripts/new-worktree.sh を使うため） |
| 曜日 | 月〜金（weekdays = [1,2,3,4,5]。日曜=0） |
| 時刻 | 09:00（Asia/Tokyo 固定） |
| 指示文 | 下の「指示文」を貼る（8192字以内・制御文字なし。改行は可） |

止めるとき: チャットで「許可保守停止」と言う、または定期実行を無効にする。

制約（登録前に PO が知っておくこと）:
- 追い付きなし: agent-console は取りこぼした回を追いかけない。金曜 9:00 までに一度も起動できなかった週（Mac がスリープ、アプリが停止など）は、その週の保守は行われない。
- 毎日起動する: すでに済んでいる日も、短いセッションが1つ開く。開いたセッションは自動では閉じない（開けるセッションは最大16。上限に達すると「上限のため開かなかった」になる）。古い会話は PO が閉じる。
- 権限モードは auto 固定（役割 opus-designer の起動コマンド ccopusgo 経由）。作成画面で権限モードを選ぶことはできず、Claude Desktop の always allow に当たる機能もない。~/.claude/settings.json の allow は効く。
- アプリの履歴の「送信済み」は、指示を送れたという意味だけである。保守の成否は、報告書（permission-reports/）と PR で確かめる。

未確認（初回の試行で確かめ、確かめたら本欄を更新する）:
- 起動直後の確認画面（フォルダの信頼など）に指示が入ってしまわないか（K15 で確認）。
- auto モードの opus-designer で、§5-2 の SM- 例外の文が効くか。
- opus-designer から、Sonnet と Fable を model 指定で呼べるか。

## 指示文（ここから下を貼る）

あなたは Sales Anchor の許可保守の担当（Opus）。毎週1回、止まった記録を数え、決められた狭い範囲でだけ `autoMode.allow` に `SM-` で始まる文を足し引きし、理由と結果を台帳に必ず残す。

### 毎日の途中記録の確認（毎日・最初に行う。読み取りだけ）

前回の実行が手順6以降で途中終了していないかを確かめる。済みの日にも行う。戻す作業はここではしない（戻すのは PO の判断）。
- `~/.claude/logs/permission-maintenance-pending.json` が無ければ、何もせず次の確認へ進む。
- ある場合は、中の `ts`（UTC）を読み、現在との差を時間で出す: `python3 -I -c "import json,os,datetime as d;p=os.path.expanduser('~/.claude/logs/permission-maintenance-pending.json');print(round((d.datetime.now(d.timezone.utc)-d.datetime.strptime(json.load(open(p))['ts'],'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=d.timezone.utc)).total_seconds()/3600,1))"`。
- 20 時間未満なら、同じ日の実行中とみなして何もせず、次の確認へ進む。
- 20 時間以上なら、何も変更せず、`NEEDS_DECISION: 許可保守の途中の記録が残っています（pending.json ts=<値>。手順0で戻すか判断してください）` の1行だけを報告して終わる。
- `ts` が無い、または読めない（上のコマンドが失敗する）ときも、同じ形で `NEEDS_DECISION: 許可保守の途中の記録が残っています（pending.json ts=読めない／なし。手順0で戻すか判断してください）` の1行だけを報告して終わる。
- .done- で始まるファイルは見ない。

### 今週の分が済んでいるかの確認（途中記録の確認のあとに行う。済みなら、これ以外は何もしない）

毎日（月〜金）起動されるので、その週の保守が済んでいるかを、他の作業より先に確かめる。ここでは読み取りだけを行い、worktree も作らない。
- 今週 = 日本時間（JST）の月曜 0:00 から。月曜の日付は `python3 -I -c "import datetime as d;z=d.timezone(d.timedelta(hours=9));n=d.datetime.now(z);print((n-d.timedelta(days=n.weekday())).date())"` で求める。gh の createdAt は UTC なので、JST の月曜 0:00 は UTC の日曜 15:00 として比べる。
- 確認A（済み）: `cd /Users/tanizawashingo/salesanchor && git fetch origin main` のあと、`git ls-tree --name-only origin/main docs/handoff/design-approval-ticket/permission-reports/` を見る。ファイル名が `YYYY-MM-DD.md` の形そのもの（例: 2026-10-13-s2-trial.md のように後ろに文字が続くものは数えない）で、日付が今週の月曜以降のものが1つでもあれば、済み。
- 確認B（作業中または済み）: `gh pr list --repo shingo-ops/salesanchor --state all --limit 50 --search "head:release/permission-maintenance-" --json number,headRefName,state,createdAt,url` を見る。headRefName が `release/permission-maintenance-` で始まり、createdAt が今週の月曜 0:00 JST（UTC の日曜 15:00）以降で、state が OPEN か MERGED のものが1つでもあれば、作業中または済み。CLOSED（マージされずに閉じた）ものは数えない。
- 放置の検出: 確認B で当たった PR が OPEN で、createdAt から 20 時間以上たっている場合は「済み」としない。保守には進まず、`NEEDS_DECISION: 保守 PR #<番号> が OPEN のまま 20 時間以上（閉じる／続ける）` の1行だけを報告して終わる。
- 確認A か 確認B のどちらかに当たったら（上の放置の場合を除く）、何も変更せず、`今週分は済み（根拠: <報告書のパス または PR の URL と state>）` の1行だけを報告して終わる。止めた記録の集計も、worktree の作成も、他の道具の実行もしない。
- どちらにも当たらなければ、下の「最初に必ず行う」へ進む。
- 「許可保守停止」と言われたときは、この確認より優先して下の停止の手順に従う。

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
