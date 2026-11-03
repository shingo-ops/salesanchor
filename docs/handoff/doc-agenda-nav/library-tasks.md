# 図書館化の練習問題（本の分。測定前に固定）

作成: 2026-11-03 Opus（設計担当）。根拠: [library-design.md](./library-design.md) §7・§9 受入条件「本は場面で開かれる」。数え方の元: [k12-tasks.md](./k12-tasks.md) 2026-10-25 の改定。
このリポジトリは公開されている。決まりの本文は書かない。依頼文・正解の本のパス・必ず含む語だけを書く。

## 題（本1冊につき2題・各題2回・計8実行）

| 題 | 依頼文 | 正解の本（読む道具の input に含まれれば「開いた」） | 必ず含む語（開いた実行の答えに無ければ「読み違えた」） |
|---|---|---|---|
| B1 | 実装が終わった。commit の文の書き方を答えて | .claude/books/git-workflow.md | feat |
| B2 | PR を作る手順を答えて | .claude/books/git-workflow.md | git diff |
| B3 | 新規ファイル3つを作る作業。最初に呼ぶ担当は | .claude/books/agents.md | planner |
| B4 | コードを直した。マージ前に要る審査は | .claude/books/agents.md | reviewer |

- 依頼文は設計 §7 の文のまま。末尾に k12 と同じ文（[k12/suffix-open.txt](./k12/suffix-open.txt)）を付ける。
- 必ず含む語は、本の中の語から Opus が測る前に決めた（設計 §7 で「未確認」としていたもの）。大文字・小文字は区別しない。

## 実行条件

- 場所: origin/main の detached 写し。ユーザー設定（`~/.claude`）のある手元で測る。クラウドには `~/.claude` が無く比べられない（設計 §7）。
- 引数は k12 と同じ: `claude -p "<依頼文><末尾文>" --model sonnet --permission-mode plan --output-format stream-json --verbose --max-budget-usd 1 --no-session-persistence --permission-prompts none`
- 実行は PO が `!` で台本を1回流す（手元で別の AI を立てる命令は、Opus からは見張りで止まるため）。

## 数え方

- 開いた: 読む道具（Read・Bash・Grep・Glob）の tool_use の input に正解の本のパスがある実行。
- 開かれなかった ＝ 8 − 開いた − 拒まれた。
- 拒まれた: 正解の本を読む道具が許可で断られた実行（tool_result が is_error で、その input に正解の本のパスがある）。
- 読み違えた: 開いた実行のうち、result の答えに必ず含む語が無い実行。
- 合否には使わない。記録だけ（設計 §7）。開かれなかったが 8回中4回以上なら、目録の行の「いつ開くか」の文言を直すか、スキル化を PO に見せる。拒まれたが1回でもあれば PO に知らせる。
- 記録先: [library-errors.md](./library-errors.md)（列: 日付｜題｜分類｜直し｜PR）。
