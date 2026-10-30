# クラウドの決まり: SQL の手順ファイルを書くときの例外（設計）

- 状態: 設計案 第3版（Opus 作成）。1回目の審査 REVISE（MEDIUM 3・LOW 4）、2回目の審査 REVISE（MEDIUM 2・LOW 3）を反映。3回目の審査 APPROVE（2026-10-31、LOW 2 件を反映）。PO 許可待ち。審査役（新規 opus）の再審査 → PO 許可 → クラウド Sonnet が実装。
- 発端: 2026-10-31、PO「1」（安全確認に、本番に出す前の手順ファイルを作るときだけの狭い例外を設ける）。
- 関係: docs/handoff/cloud-parity/design.md の K1（クラウドで危険操作を Bash で「実行」しようとすると止まる）。docs/handoff/cloud-case-ai/stage1-card.md §4-B。

## 1. 目的（PO の言葉で）
クラウドの AI が、本番に出す前の手順ファイル（migrations/*.sql）を書けるようにする。危ない命令を「実行」することは今までどおり止める。

## 2. 現在地（事実）
- 見張りは Bash の命令の文字に危険語（scripts/agent-hooks/cloud/danger_ops.json）があると止める（scripts/agent-hooks/cloud/guard_pre_tool.py:386-409 check_danger。一覧の照合は :393-395、psql・ssh の止めは :399-408）。
- ファイルへ書くだけの heredoc の本文は調べない作り（同 :37-46 strip_heredoc_bodies）。本文を実行しうる命令（同 :26 EXEC_CMDS: bash・python3・psql など）に流す heredoc の本文は調べる。
- Bash 以外の道具（Write・Edit）は調べない（同 :667-669）。
- 試験の台本もこの作りを確かめている（scripts/agent-hooks/cloud/test.sh:106-110。「cat>file heredoc本文は通す」は exit 0）。
- 2026-10-30 16:54 UTC、段1の実装でクラウドの AI が migrations の SQL を `sed -i` と `python3 - <<'EOF'` で書こうとし、TRUNCATE の語で止められた（クラウドの実行記録）。AI は止まって報告した（正しい動き）。
- その後、Opus が「書くだけの道具で書け」とクラウドへ伝えようとしたところ、手元の自動判定が「見張りのすり抜け」として止めた（2026-10-31）。決まりとして明文化されていないため、止められた後に道具を替える形になるのが理由。
- クラウドの AI が読む決まり（scripts/agent-hooks/cloud/rules.md、12 行。session_start.py が毎回渡す）には、この扱いが書かれていない。

## 3. 変更（2 ファイルだけ）
### 3-1. scripts/agent-hooks/cloud/rules.md に 1 項目を足す
```
- 本番に出す前の手順ファイル（migrations/*.sql）の中身に SQL の危険語（DROP・DELETE・TRUNCATE など）が入るのは正当。書くのは Write・Edit の道具、または区切りを引用符で囲んだ書くだけの heredoc（`cat > migrations/<名前>.sql <<'EOF'`。引用符の無い <<EOF は使わない）で行う。sed・python・bash など実行する命令の引数や本文には、危険語を入れない（見張りが止める。止まらない書き方でも入れない）。見張りに止められたら、道具を替えず BLOCKED: で報告する。
- SQL を流して確かめるのは pytest の中だけ。接続先は、そのクラウドの中で自分が立てた使い捨ての PostgreSQL（localhost）だけにする。本番やほかの外部の接続先は設定しない・使わない。本番への適用は手元で PO の GO の後。
```
- 審査 M3 への注記: pytest の既定は SQLite（backend/tests/conftest.py:17）。段1の試験は PG が要るため、クラウド内に立てた使い捨ての PG（localhost）を使う（段1カード §4-E。カードは本線に無く、枝 origin/release/cloud-case-ai-stage1 の docs/handoff/cloud-case-ai/stage1-card.md にある。§4-E の本文は「試験 DB」とだけ書く。localhost の使い捨て PG にする点は本設計で決める）。「CI に任せる」にすると段1の試験がクラウドで流せないため、接続先を localhost に限る文にした。
### 3-2. scripts/agent-hooks/cloud/test.sh の K1 に 2 行を足す（見張りの作りは変えない。今の作りを例外の正本として固定する）
- 「cat>migrations/*.sql heredoc本文は通す」: `cat > migrations/x.sql <<'EOF'\n{TRUNCATE の語} t;\nEOF` → 0
- 「sed -i で SQL に危険語は止める」: `sed -i 's/a/{TRUNCATE の語} t/' migrations/x.sql` → 2
- 語は既存の行と同じく ops の一覧から取り出す（台本に危険語を直書きしない）。取り出し方は `next(o for o in ops if o.startswith("TRUNC"))` に固定する。

## 4. 触らない範囲
- guard_pre_tool.py・danger_ops.json・dispatch.sh・手元の agent-danger-hook（見張りの止める範囲は 1 文字も変えない）。
- psql への流し込みの止め・本番への接続の止め・マージの止め。

## 5. 代替案と選ばなかった理由
- 見張りのコードに migrations/*.sql 宛ての例外を足す: 止める範囲が広がる変更で、作りが複雑になる。今の作りで書けるので不要。
- 危険語の一覧から TRUNCATE などを外す: 実行も止まらなくなる。却下。
- 手元で Opus が SQL を書く: Opus はコードを書かない決まり。却下。

## 6. リスクと対処
- 書いた SQL を本番で流すのは、今までどおり ADR-136 の GO（migrations は危険パス）の後だけ。クラウドでは流せない（psql の止めは残る）。
- 引用符の無い heredoc の本文の `$( )` は bash が実行するが、見張りは本文を先に取り除くため検出しない（guard_pre_tool.py:333-334。元からある穴。審査 M2）。rules.md で引用符付きだけを使う決まりにする。見張りの直し（引用符付きの heredoc だけ本文を除く）は別の件として扱う（この設計では見張りを変えない）。
- `sed -n -i` は読み取り扱いで通る（同 :57-67。元からある穴。審査 L3）。rules.md で「止まらない書き方でも入れない」とする。見張りの直しは上と同じ別の件。
- 接続先を localhost に限る決まりは、見張りでは強制されない（pytest を外の接続先に向けても見張りは止めない）。決まりの文だけで守られる。審査役が実行記録で接続先を確かめる。クラウドから本番 DB に通信が届くかは【未確認】。
- AI が「書くだけ」の形に見せかけて実行する: `cat > x.sh <<EOF` の後に `bash x.sh` で流すことは今も起こりうる。これは今の作りから変わらない（この変更で広がらない）。rules.md の文で実行を禁じ、審査役が PR の差分と実行記録で確かめる。

## 7. 受入
| 基準 | 検証方法 |
|---|---|
| rules.md に 3-1 の 2 項目があり、ほかの行は変わらない | `git diff origin/main -- scripts/agent-hooks/cloud/rules.md` が 2 行の追加だけ |
| test.sh の新しい 2 行が OK、ほかの行の結果は変更前と同じ | 変更前と変更後に `bash scripts/agent-hooks/cloud/test.sh` を流し生出力を残す。新しい 2 行が OK。機械の速さで結果が変わる時間の項目（B8・K7・T1）を除き、全部の行の OK/NG が変更前と行ごとに一致（審査時の変更前の実測は 2 回で NG の行が B8・T1 と入れ替わった。どちらも時間の項目） |
| 変えたのは 2 ファイルと本設計書・作業中の登録だけ | `git diff --name-only origin/main...HEAD` が rules.md・test.sh・本設計書・.claude-pipeline/active-work.d/release-cloud-rule-sql-file.md の 4 つだけ |
| クラウドで段1の SQL を決まりどおり書ける | 段1の実装のやり直しで ①migrations の SQL が push されている ②その書き込みが Write・Edit・引用符付きの cat heredoc のどれかだと実行記録で確かめられる ③SQL の危険語による BLOCKED が 0 件。この行はこの PR のマージ後、段1の実装のやり直しが終わった時に Opus が判定し、段1の引き継ぎ文書に記録する |

## 8. 戻し方
この PR を revert する（2 ファイルの追加分だけ）。

## 9. 外部事例
不要。社内の見張りの決まりを明文化するだけで、作りは変えないため。
