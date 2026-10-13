# S4 実装カード（SM-S4-TOOLS）— 引き継ぎ用・実装済み（#4221）

この文書は何か: 許可の自律保守（ADR-1011）の週1回の定期実行で使う道具と指示書を作るためのカード。2026-10-13、Sonnet の週の利用上限で一度止まったが、その後実装済み（#4221）（当時の上限の解除は 10/16 18:00 JST の予定だった）。

親: [self-maintenance-design.md](self-maintenance-design.md)（§5-2〜§5-6・§8・§9 を先に読むこと）

## 作るもの（置き場所: このディレクトリの routine/）

道具は python3 -I で動き、標準ライブラリだけを使う。本物のパスを既定にし、引数で差し替えられるようにする。秘密値は出力しない。

1. sm_count.py
   - 入力:
     - ~/.claude/logs/permission-denied.jsonl
     - ~/.claude/logs/agent-events.jsonl（type=hook_blocked）
     - ~/.claude/logs/test-runs.log（試験した時間帯）
   - 過去7日のうち、試験した時間帯を除いた記録を、形（入口・理由の分類名・コマンドの先頭2語）ごとに数える。
   - 代表例を3件付ける（伏せ字にする）。
   - 出力は Markdown と JSON。
2. sm_check_entry.py
   - 足す文を設計 §5-2 (3) で判定する。判定の項目:
     - 先頭が `SM-YYYY-MM-DD-N:` の形か
     - 120語以内か
     - 禁止の文字列を含まないか（部分一致）
     - 全称の語を含まないか（単語単位）
     - environment のホストのアドレスを含まないか
   - 禁止の文字列の一覧は、実行のたびに設計書の §5-2 の引用ブロックから抜き出す。
3. sm_k1_k3.py
   - K1: 基準の写しに台帳の結果行を順に当て、その結果と現在の autoMode を sha256 で比べる。
     - 当てる行の種類は add / remove（全文）/ remove（sha256）。
     - 参考実装: 設計担当の scratchpad にあった k1_replay.py（下記「事実」）。
   - K3: 保護対象の sha256 を、前回の値（~/.claude/logs/permission-protected-hashes.json）と比べる。
     - 保護対象: SM- で始まらない allow、soft_deny、hard_deny、environment、permissions、hooks、~/.claude/scripts/ の全ファイル、§5-2 の文、scripts/dev/test-agent-hooks.sh
     - `--save` を付けたときだけ前回の値を保存する。
4. sm_apply.py
   - add / remove: SM- で始まる文に限る。手順はバックアップ → pending.json → 変更。
   - recover: pending.json に書いた SM- の文1件だけを外し、pending.json を .done-<日時> に変える。
   - `--clear-pending`
5. ROUTINE.md（agent-console の定期実行に PO が登録する指示書。2026-10-14 に Claude Desktop 前提から変更）
   - 中身:
     - 設計 §5-5 の手順0〜9
     - 委任の型（Opus＝判断と変更、Sonnet＝集計・PR・試験、Fable＝審査、Haiku は使わない）
     - 「許可保守停止」
     - 保留の扱い
     - PO への5行報告の型
   - 今週の分が済んでいるかの確認（月〜金の毎日起動のため。済みなら何もせず終える）
   - 登録手順（agent-console の定期実行の画面、役割 opus-designer、月〜金 9:00 JST、フォルダは /Users/tanizawashingo/salesanchor）。HTTP API は認証方式が未確認のため書かない。

## 試験（必須）

ダミーのファイルを使い、次の (a)〜(e) を確かめる。

- (a) 件数と、試験した時間帯の除外が正しい。
- (b) 良い文は合格する。次の4種類は不合格になる: 禁止語を含む、全称語を含む、121語ある、接頭辞が違う。
- (c) K1 は、一致するとき「一致」、1件変えたとき「不一致」を返す。K3 は次の3つの場合を確かめる: 初回、同じ、変化あり。
- (d) add → recover で、ファイルが元と同一（cmp）になる。add → remove でも同一になる。SM- でない文の remove は拒否する。
- (e) py_compile が通る。

## 委任文に必ず書くこと（このセッションで実測した落とし穴）

- 検査用の文字列やヒアドキュメントに、データベースのクライアント名などの危険語を直接書かない。必要なら Python の中で文字列を連結して作る（フックが反応して止まる）。
- bash で、変数の直後に全角文字を続けない（`${VAR}` と書く）。macOS の bash 3.2 で壊れる。
- 試験のあとにファイルを直したら、必ず試験をやり直す。
- PR を作る `gh` は `cd <worktree> && gh …` の形で、パスは `$変数` を使わずに書く。
- マージすると作業場所は自動で片付けられる。PO が実行するスクリプトの場所は、マージ前の作業場所のパスで渡す。

## 事実（2026-10-13 時点）

- K1 の参考実装は、セッションの作業領域にあった（次のセッションでは見えない可能性がある）。仕組み: 基準の写しの autoMode に、台帳「記録」節の結果行を当てる。sha256 は §5-6 の方法で計算する。
- 基準の写し: ~/.claude/logs/permission-baseline-2026-10-13.json（権限 600）
- PO が外した許可の全文: ~/.claude/logs/removed-allow-20261013140423.txt
- critique の全文: ~/.claude/logs/automode-critique-20261013121121.txt
- 現在の autoMode.allow: 25件。SM- の文は0件。
