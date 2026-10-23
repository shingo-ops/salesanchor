# K12 練習問題10題（測定前に固定。根拠: pairs.md）

共通の末尾文（全題に付ける）: 「計画だけを日本語で答えてください。ファイルの変更・commit・push はしないでください。」
「開いた」の定義: その実行の stream-json に記録された tool_use の input（文字列化したもの）に、正解の集合のどれかのパスが含まれていれば 1。Read・Bash（cat/sed/git show 等）・Grep を区別せず数える。
K10 は同じ実行で docs/INDEX.md を含む tool_use の有無を数える（変更前は存在しないので 0 の見込みだが、実測する）。

| 題 | 依頼文 | 正解の集合 | 根拠（pairs.md） |
|---|---|---|---|
| T1 | 在庫表の画面に、仕入元を選ぶ欄を1つ足したい。どう作るか計画してください。 | docs/CC_UI_GOVERNANCE.md | A 一意（7-15行目） |
| T2 | 新しい作業を始めたい。作業する場所とブランチをどう用意するか計画してください。 | docs/specs/branch-operations/README.md, docs/PARALLEL_TERMINAL_GUIDE.md | B 複数（手順の所在が分かれているため両方を正解） |
| T3 | 実装が終わった。commit する前と PR を作る前に確かめることを計画してください。 | docs/ai-agents/executor-checklist.md | C 一意（3-5行目） |
| T4 | 「売上の月別グラフを見たい」という新しい依頼が来た。手を動かす前に何をどの順に作るか計画してください。 | docs/STANDARD-WORKFLOW.md | D 一意（3行目・21-28行目） |
| T5 | GitHub Actions で使っている秘密の値の1つを新しいものに入れ替えたい。手順を計画してください。 | docs/runbooks/secret-rotation.md | E（対象を GitHub Actions に絞ると同書が対象8件を持つ） |
| T6 | 監視から「バックエンドが落ちている」という通知が来た。対応を計画してください。 | docs/runbooks/alerts.md | F 一意 |
| T7 | 毎週の「止まっている作業」の通知が今週届かなかった。原因の調べ方を計画してください。 | docs/runbooks/weekly-stale-tasks.md | G（依頼を通知の失敗に直すと一意。10-11行目） |
| T8 | 仕入元が、まとめて売るときにこれまでと違う書き方を使い始めた。対応を計画してください。 | docs/runbooks/bundle-sale-new-wording.md | H 一意（26-60行目） |
| T9 | PO から新しい相談が来た。設計の担当として、相談を設計にまとめる進め方を計画してください。 | docs/ai-agents/design-partner.md | J 一意（3-4行目） |
| T10 | 画面にボタンの文字を1つ足したい。文字の足し方を計画してください。 | frontend/CLAUDE.md, frontend/AGENTS.md | L（手順に最も近いのは frontend/CLAUDE.md:21,27-35。frontend 配下の案内2本を正解） |

除外: I（recon。正本が3か所に分かれ、D と重なる）、K（作業カード。task-template.md は「カード」の語が無く、書き方は design-partner.md 等に分散し J と重なる）。

## 実行条件
- 場所: origin/main の detached 写し（作業ブランチを持たない）。題ごとに同じ写しを使う。
- `claude -p "<依頼文><末尾文>" --model sonnet --permission-mode plan --output-format stream-json --verbose --max-budget-usd 1 --no-session-persistence --permission-prompts none`
- 各題2回（計20回）。ばらつきを見るため。
- 値: K12 = 開いた実行の数 / 20。K10 = docs/INDEX.md を開いた実行の数 / 20。費用は各実行の result 行の total_cost_usd の合計。

## 注意（未確認）
- frontend/CLAUDE.md は frontend 配下のファイルを読むと自動で読み込まれる場合があり、tool_use に出ない可能性がある（T10）。stream-json にその読み込みが出るかは未確認。出なければ T10 は「tool_use で開いた」だけを数え、その旨を記録する。
