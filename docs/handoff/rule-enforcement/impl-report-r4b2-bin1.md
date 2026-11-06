本報告はカード card-r4b2-bin1.md の実行結果である。受領：§0〜§11 を読んだ

## 準備
- 起点：`origin/release/r4b2-push-gap-bin1` の先頭 `fc00ec7e6`（`git log -1 --oneline` の出力が `fc00ec7e6 docs(rule-enforcement): R4b-2 第1便の実装カード`）
- 台帳：`bash scripts/ledger-lookup.sh release/r4b2-push-gap-bin1` の出力
  `| release/r4b2-push-gap-bin1 | push 前の確認の記録（frontend/.husky/pre-push・scripts/dev/check-before-submit.sh・scripts/tests/test_check_before_submit.py）R4b-2 第1便 | 2026-11-06 15:41 | IN_PROGRESS | | | |`（rc=0）

## §7-1 構文
```
bash -n scripts/dev/check-before-submit.sh → rc=0
sh -n frontend/.husky/pre-push → rc=0
```

## §7-2 台本の中の個数
```
^trap _cbs_log EXIT: 1
^_cbs_now(): 1
^CBS_T0=: 1
```

## §7-3 `grep -c 'CBS_REASON='`
出力は 12（カードの期待は 13。カードの内訳の数え違いと思われる。記録して続けた）。`grep -n` の生出力：
```
34:CBS_REASON="-"
64:        CBS_REASON=bad-arg; echo "--only には検査の id（カンマ区切り）を渡してください。終了コード 2"; exit 2
68:    *) CBS_REASON=bad-arg; echo "不明な引数: $1" >&2; exit 2 ;;
73:cd "$(git rev-parse --show-toplevel)" || { CBS_REASON=cd-fail; exit 2; }
85:    CBS_REASON=unknown-id
102:  if printf '%s\n' "$CBS_PORC" | grep -qv '^??'; then CBS_REASON=dirty-tracked; else CBS_REASON=dirty-untracked; fi
111:  CBS_REASON=req-unreadable
116:  CBS_REASON=req-empty
120:MAIN_SHA=$(git rev-parse --verify -q origin/main) || { CBS_REASON=no-origin-main; echo "origin/main が見つかりません（fetch は自動では行いません）。終了コード 2"; exit 2; }
121:BASE_SHA=$(git merge-base origin/main HEAD) || { CBS_REASON=no-merge-base; echo "origin/main との分岐点が見つかりません。終了コード 2"; exit 2; }
160:  CBS_REASON=select-dir
413:  CBS_REASON=zero-checks
```

## §7-4 試験
このクラウドの `python3` には pytest が無かった（`/usr/local/bin/python3: No module named pytest`）。py312-guard に従い `python3.12 -m venv` で作った venv の python で同じ命令を流した：
`python -m pytest scripts/tests/test_check_before_submit.py -q 2>&1 | tail -n 15`
```
.................................                                        [100%]
33 passed in 233.26s (0:03:53)
```
落ちた試験なし（K3 の 5 秒も超えず）。

## §7-5・§7-6（commit 前の作業ツリー対 HEAD で測った生出力。commit 後の `origin/main...HEAD` は最後の返事に載せる）
```
git diff --stat HEAD
 frontend/.husky/pre-push                  | 31 ++++++++++++
 scripts/dev/check-before-submit.sh        | 70 +++++++++++++++++---------
 scripts/tests/test_check_before_submit.py | 83 ++++++++++++++++++++++++++++++-
 3 files changed, 159 insertions(+), 25 deletions(-)

git diff HEAD | grep -c '^-[^-]'
25

git diff --numstat HEAD
31	0	frontend/.husky/pre-push
47	23	scripts/dev/check-before-submit.sh
81	2	scripts/tests/test_check_before_submit.py
```
消した行は §2 の 3 ファイル（`check-before-submit.sh`・`test_check_before_submit.py`）の中だけ。`pre-push` は消した行 0。

## 備考
- `git diff --stat origin/main...HEAD`（commit 前）は、設計パートナーの commit 済みのカードと台帳（2 ファイル・248 行追加）だけだった。
- K8（CI）は設計パートナーが PR で確かめる。
