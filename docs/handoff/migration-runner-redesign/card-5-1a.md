---
mode: handoff
---
# 調査カード：値を書く移行 52本の中身を1本ずつ読む（段5 5-1 の前・P11 の詳細・読むだけ・Sonnet）

## 発行前の照合（design-partner.md 5.5）
| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号をバッククォートで囲む | ○ |
| 2 | PR は作らせない（Opus が作る） | ○ |
| 3 | 報告の宛先と生出力の全文 | ○（下の「出すもの」） |
| 4 | 1便1目的（読むだけ。コード・移行・試験は変えない） | ○ |
| 5 | 既存ブランチの起点を明示（`origin/release/migration-p11-classify`） | ○ |
| 6 | 書式は実例で示す（下の表の列と例の1行） | ○ |
| 7 | 合格基準を出力まで縛る | ○（「合否の線」） |
| 8 | 件数と名前を対で出す | ○ |
| 9 | 出力量に上限のある命令だけ | ○ |
| 10 | 停止時の3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実測から（行番号は文の一致で探す） | ○ |
| 12 | 停止は不可逆なものだけ。数の食い違いは記録して続ける | ○ |
| 13 | sleep させない・Write で書く・PR を作らない・止められたら言い換えない | ○ |

## 前提
- 設計: `docs/handoff/migration-runner-redesign/design.md` §5-5（値を書く移行を「無効にする」か「固めてよい」に分ける）と §5-10。先に全部読む。
- 一覧の正本: `docs/handoff/migration-runner-redesign/recon-5-0a/p11.md` の表（52本）。この52本だけを読む。足りない・多いと思っても数は変えず、気づいたことを最後に書く。
- 依存する試験は `docs/handoff/migration-runner-redesign/recon-5-0a/p12.md` を使う（新しく探し直さない）。
- 今の本番反映は、登録された移行を毎回全部流している。だから「2回目に流すと何が起きるか」は、毎回の本番反映で起きていることと同じ。
- 分ける判断（無効にする／固めてよい）は書かない。Opus が決める。このカードは事実だけ。
- 本番のサーバーと DB には一切つながない。

## 手順
1. 受領確認: 報告の先頭に「本報告はカード 5-1a の実行結果である」と書く。
2. 作業フォルダ: `git fetch origin` のあと `bash scripts/new-worktree.sh release/migration-p11-classify`（`--claude` なし。既にあればそのフォルダ）。以後の Bash は `cd $HOME/worktrees/salesanchor/release-migration-p11-classify && ` で始める。`git merge --no-edit origin/release/migration-p11-classify`（ぶつかりが出たら **停止**）。`git log -1 --format=%H` を記録する。
3. `./scripts/dev/executor-preflight.sh` を流し、出力を記録する（`gh auth switch` で落ちるのは前と同じ。記録して続ける）。
4. 52本を表の順に1本ずつ Read し、下の表を `docs/handoff/migration-runner-redesign/recon-5-1a/p11-detail.md` に Write する。先頭に読んだ commit を書く。
5. 「アプリが書き換えるか」の列は、そのファイルが値を書く表の名前ごとに、`backend/app` を台本で探して決める。台本は Write で `/tmp/recon/apps.py` に書き、Bash は `python3 -I /tmp/recon/apps.py > /tmp/recon/apps.out` だけにする。台本の全文と出力の全文を `recon-5-1a/apps.md` に貼る。
6. `git add docs/handoff/migration-runner-redesign/recon-5-1a/` だけ。`git diff --cached --stat` を記録。
7. commit（文は Write で `/tmp/recon/commit-msg.txt` に書いて `git commit -F /tmp/recon/commit-msg.txt`。最後の行は `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）。文の例: `docs(migration-runner): record 5-1a P11 detail (read-only)`。
8. `git push -u origin release/migration-p11-classify`（force 禁止）。push の出力の全文を記録。PR は作らない。

## 出すもの（p11-detail.md の表。52行）
列:
- `#`（p11.md と同じ番号）／ファイル名
- 書く表: `スキーマ.表`（会社ごとに回す形なら `tenant_*.表` と書き、回し方の行番号を添える）
- 文の形: 次のどれか（複数可）と行番号。`INSERT ... ON CONFLICT DO NOTHING`／`INSERT ... ON CONFLICT DO UPDATE`（更新する列名も）／`INSERT`（ON CONFLICT なし。重複を止める `WHERE NOT EXISTS` などがあればその文）／`UPDATE`（`WHERE` の条件の文をそのまま）／`DELETE`／`TRUNCATE`
- 行の出どころ: `直書きの値`（行数）／`他の表から写す`（元の表名）／`条件で絞った既存行の書き換え`
- 2回目に流すと: 次のどれかと、そう言える本文の行番号。`何も変わらない`／`アプリやPOが消した行が戻る`／`アプリやPOが直した値が上書きされる`／`行が増える`／`エラーで止まる`／`本文だけでは決められない`（理由を1行）
- 包み: `DO $$` の中・`IF NOT EXISTS` の中・関数の本文の中・トリガの本文の中、のどれかに入っていれば書く（関数やトリガの本文の中なら、移行を流した時には値は書かれない。その旨を書く）
- アプリが書き換えるか: `backend/app` で表名が `INSERT`／`UPDATE`／`DELETE` と同じ文に出る場所の有無（○×と最初の1か所のファイル:行）
- 依存する試験: p12.md の当たり（無ければ「なし」）

例の1行（書式の見本。中身は実物で確かめて書き直す）:
| 17 | 20260903_120000_tcg_unit_evidence_rules_t004.sql | tenant_004.tcg_unit_evidence_rules | INSERT ... ON CONFLICT DO NOTHING :47 :67 :87 :107 | 直書きの値 4行 | アプリやPOが消した行が戻る（:47 の ON CONFLICT は同じ鍵の行が無いときだけ入る） | なし | ○ backend/app/xxx.py:NN | なし |

表のあとに数を書く: 「2回目に流すと」の6種それぞれの本数と番号の一覧。「包み」が関数・トリガの本文の本数と番号。

## 合否の線
- 52行そろっている。番号とファイル名が p11.md と全件一致（ずれ0）。
- どの行も「2回目に流すと」に本文の行番号がある（`本文だけでは決められない` は理由つき）。
- 6種の本数の合計が52。

## 停止
- 止めるのは手順2のぶつかり、push の拒否、フックや自動判定に止められたとき。言い換えて再試行しない。
- Bash に psql の語を書かない。移行の文の語（`DROP`・`TRUNCATE`・`DELETE`・`INSERT`・`UPDATE` など）を検索語に使うときは台本に書き、Bash は `python3 -I /tmp/recon/<名>.py > /tmp/recon/<名>.out` だけにする。git は1命令ずつ。sleep しない。rm を使わない。
- コード・移行・試験・workflow は1文字も変えない。書くのは `recon-5-1a/` の下だけ。
- 停止したら報告に「止まった手順の番号／最後に流した命令／止まった理由の原文」を書く。

## 報告
- 最後の行は `DONE` か `BLOCKED: <理由>`。
- commit の番号と、`recon-5-1a/` の各ファイルの行数を書く。中身の要約は書かない（Opus がファイルを読む）。
