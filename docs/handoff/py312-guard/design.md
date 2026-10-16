# 設計: 手元の Python 部品入れを 3.12 に揃える見張り（py312-guard）

状態: 設計案（Opus 作成・自己審査済み）。PO 方針「手元でも 3.12 を使う決まりを見張りで守らせる設計に進める」（2026-10-16 チャット「y」）。実装承認 2026-10-16 チャット「y」。根拠 [recon.md](recon.md)。関連 ADR: ADR-040（Claude Code 運用ガードレール。本件はその見張りの 1 本を足す）。

## 0. 目的
Sales Anchor の作業で、本番（3.12、recon P4）と違う版の Python で venv を作ったり部品を入れたりする命令を、打った時点で止める。今日のような「3.14 で部品を手作りして Mac が重くなる」（P1）と「手元と本番で結果が違う」（P5）をなくす。水準は A（うっかり防止）。

## 1. 変更前と変更後
| 命令（Sales Anchor の作業場所で） | 変更前 | 変更後 |
|---|---|---|
| `python3 -m venv /tmp/x`（python3 は 3.14） | 通る | 拒否。正しい形を返す |
| `/tmp/x/bin/pip install …`（x が 3.14 の venv） | 通る | 拒否 |
| `pip install …` / `pip3 install …`（素の pip） | 通る | 拒否 |
| `/usr/local/bin/python3.12 -m venv /tmp/x` | 通る | 通る |
| `/tmp/x/bin/pip install …`（x が 3.12 の venv） | 通る | 通る |
| `docker compose exec backend pip install …` | 通る | 通る（中は 3.12） |
| Sales Anchor 以外の場所での同じ命令 | 通る | 通る（対象外） |

## 2. 成功条件
| # | 基準 | 検証方法 |
|---|---|---|
| K1 | 次を拒否（終了 2・標準エラー 1 行）: `python3 -m venv /tmp/a`、`python3.14 -m venv /tmp/a`、`python3.13 -m pip install x`、`/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -m venv /tmp/a`、`pip install -r requirements.txt`、`pip3 install x`、`python3 -m pip install x`、`<3.14 の venv>/bin/pip install x`、`<3.14 の venv>/bin/python -m pip install x`、`uv venv /tmp/a`（`--python 3.12` なし）、`virtualenv /tmp/a`、recon P2 の命令そのもの | 単体試験（venv は試験の中で pyvenv.cfg だけ作る） |
| K2 | 次を通す（終了 0・無出力）: `/usr/local/bin/python3.12 -m venv /tmp/a`、`python3.12 -m venv /tmp/a`、`<3.12 の venv>/bin/pip install x`、`<pyvenv.cfg の無い場所>/bin/pip install x`、`uv venv --python 3.12 /tmp/a`、`docker compose exec -T backend pip install x`、`python3 --version`、`python3 script.py`、`grep -n "pip install" docs/x.md`、`git log` | 単体試験 |
| K3 | 対象は Sales Anchor の作業場所だけ: 入力の `cwd` が `/Users/tanizawashingo/salesanchor` か `/Users/tanizawashingo/worktrees/salesanchor/` の下、または命令に `cd <その下>` を含むとき。それ以外の場所では K1 の形も通す | 単体試験（cwd を変えて 2 本） |
| K4 | 入力が読めない・pyvenv.cfg が読めないときは通す（fail-open） | 単体試験 |
| K5 | 拒否文言は 1 行・120 字以内で、正しい形 `/usr/local/bin/python3.12 -m venv <場所>` を含む。拒否は `~/.claude/logs/agent-events.jsonl` に hook_blocked で 1 行残る（既存の型 recon P8） | 単体試験＋実機で 1 行を確認 |
| K6 | 実機: 導入後、Opus 本体から Sales Anchor の作業場所で `python3 -m venv /tmp/py312-guard-probe` を打つと拒否され、venv が作られない。`/usr/local/bin/python3.12 -m venv /tmp/py312-guard-probe312` は通る | 実機 1 回 |
| K7 | 実機の効果: 3.12 の venv に `pip install -r requirements.txt -r requirements-dev.txt` を入れる間、rustc の数を 5 秒ごとに数え、最大値を記録する（0 を期待。0 でなければ記録して PO に報告し、順番待ちの案へ進むかを判断する） | 実機 1 回（Sonnet。生出力保存） |

## 3. 方式
新しい PreToolUse hook `~/.claude/scripts/python-version-guard.py`（matcher `Bash`、同期、timeout 5）。`~/.claude/settings.json` の PreToolUse に 1 本足す（既存 26 件はそのまま）。

判定（`tool_input.command` に対して）:
1. 対象の場所か（K3）。違えば通す
2. 命令を `;` `&&` `||` `|` 改行で部分に分け、各部分の先頭語（`sudo` `env` `NAME=値` `time` を飛ばす）を見る。先頭語が `docker` `ssh` `git` `grep` `rg` `cat` `echo` `printf` の部分は見ない
3. 拒否する部分:
   - 先頭語が `python3` `python`、または `python3.N`（N≠12）、または `/…/Versions/3.N/bin/python3`（N≠12）で、その後に `-m venv` か `-m pip install` がある
   - 先頭語が `pip` `pip3` `pip3.N`（N≠12）で次の語が `install`
   - 先頭語が `<dir>/bin/pip*` か `<dir>/bin/python*`（`-m pip install`）で、`<dir>/pyvenv.cfg` の `version` が 3.12 で始まらない（ファイルが無い・読めないなら通す）
   - 先頭語が `virtualenv`
   - 先頭語が `uv` で次が `venv`、かつ `--python 3.12` / `-p 3.12` / `--python=3.12` が無い
4. `python3.12`・`/usr/local/bin/python3.12`・`…/Versions/3.12/bin/python3` は通す
5. 拒否時: `_hook_blocked_log` と同じ形式の 1 行を agent-events.jsonl に足し、標準エラーに `本番は Python 3.12 です。/usr/local/bin/python3.12 -m venv <場所> で作り、その venv の pip を使ってください（py312-guard）` を出して終了 2

試験: `~/.claude/scripts/tests/test_python_version_guard.py`（判定関数を import して K1〜K5）。

## 4. 影響範囲
- 新規: `~/.claude/scripts/python-version-guard.py`、その試験
- 変更: `~/.claude/settings.json`（PreToolUse に 1 本。変更前に控え `settings.json.bak-py312-guard-<日時>` を作る）
- 文書: `AGENTS.md` の Python 3.12 の行に「手元の venv は `/usr/local/bin/python3.12 -m venv`。違う版は見張りが止める」を 1 行（AGENTS.md 自動更新ルールの「新規必須チェック追加」に該当）
- 触らない: Mac の PATH（ほかの仕事が 3.14 を使う可能性があるため）、本番、CI、既存の hook

## 5. 代替案
| 案 | 選ばなかった理由 |
|---|---|
| PATH を並べ替えて python3 を 3.12 にする | Mac 全体に効き、Sales Anchor 以外の仕事を変える。戻し忘れの危険 |
| 文書（AGENTS.md）に書くだけ | 今回の担当も版を表示しながら続けた（P2）。文書だけでは止まらない |
| 重い作業の順番待ち（同時 2 本まで） | 重さの元（手作りの組み立て）を断つ方が先。K7 で効果を測ってから判断（1 回に 1 変更） |
| `backend/.python-version` を置く | pyenv・uv を使う命令にしか効かず、素の `python3 -m venv` は止まらない |

## 6. リスクと対処
- R1 迂回できる（変数経由・スクリプトに書いて実行）。水準 A のため README 相当（AGENTS.md）に限界を書く
- R2 誤拒否（Sales Anchor で 3.12 以外を意図して使う仕事、例: 将来の版上げの試し）。そのときは版上げの仕事として本 hook の許可を設計で変える（期限の件は別の PO 判断）
- R3 hook の起動の重さ: 全 Bash で起動する。判定は文字列処理と pyvenv.cfg 1 回読みだけ。起動は `/usr/local/bin/python3`（既存の launch_guard_for_sim.py と同じ）

## 7. 維持
- 単体試験は `~/.claude/scripts/tests/` で手元実行（リポジトリ外のため CI には乗らない。recon P8 の既存 hook と同じ扱い）
- 拒否の記録は agent-events.jsonl に残り、件数を後から数えられる
- 担当: Sales Anchor 開発基盤（Opus 設計・Sonnet 実装）

## 8. 戻し方
`~/.claude/settings.json` から本 hook の 1 本を外す（控えから戻すこともできる）。ファイルは残してよい。

## 9. 外部事例
不要。手元の道具の決まりを機械で守らせる種類で、既存の見張り（recon P8）と同じ型。版の事実は公式の予定表（devguide.python.org/versions、2026-10-16 取得: 3.12 security・2028-10 終了）。

## 10. 自己審査（同一 AI）
APPROVE（設計合格。PO の実装承認とは別）。
- 整合: 本番 3.12（P4）に手元を寄せる向きで、CLAUDE.md の「ADR と実装の優先順位」と同じ向き
- 検証: K1〜K5 単体、K6・K7 実機で○×が出る
- 未解決: なし（K7 が 0 にならない場合の次の手は PO 判断として残す）
