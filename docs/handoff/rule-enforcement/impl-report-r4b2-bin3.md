本報告はカード card-r4b2-bin3.md の実行結果である。受領：§0〜§11 を読んだ

# R4b-2 第3便 実装報告

## §7-1 構文
```
$ bash -n scripts/dev/check-before-submit.sh; echo "rc=$?"
rc=0
```

## §7-2 数
```
CBS_COPY_KIND  : 2（期待 2）
cbs_kind       : 4（期待 4）
tracked-copy   : 2（期待 2）
```

## §7-3 bash の版
```
GNU bash, version 5.2.21(1)-release (x86_64-pc-linux-gnu)
```

## §7-4 試験（末尾 25 行）
```
test_prepush_skips_check_when_stamp_matches_head ... ok
test_prepush_skips_when_pushed_content_differs_from_head ... ok
test_prepush_stops_on_violation_and_writes_no_stamp ... ok
test_prepush_stops_when_copy_fails_check ... ok
test_prepush_stops_when_head_fails_with_dirty_tracked ... ok
test_prepush_unexpected_exit_code_passes ... ok
test_prepush_works_when_git_passes_git_dir_env ... ok
test_tenant_schema_violation_fails ... ok
test_untracked_copy_kind_not_taken_from_outside ... ok
test_untracked_file_is_not_in_copy ... ok
test_untracked_only_runs_in_copy ... ok
test_validate_pr_body_otherhead ... ok
test_validate_pr_body_same_or_unset_head_ref ... ok
test_validate_pr_body_warns_without_stamp ... ok
test_zero_checks_ran_exits_2 ... ok
test_hooks_path_value_is_the_same_in_three_places ... ok
test_prepare_does_not_touch_outer_repo ... ok
test_prepare_without_git_dir_exits_0 ... ok
test_prepare_without_git_on_path_exits_0 ... ok
test_prepare_writes_common_config ... ok

Ran 44 tests in 439.658s

OK
```
（各行の `(__main__.…)` の部分は省略して貼った）

## §7-5 写しの残り
```
$ git worktree list | grep -c cbs-copy
0
```

## §7-6・§7-7 差分（origin/main との比較。作業場所の台帳 2 件はブランチ取り込みで入ったもので commit に含めない）
```
 scripts/dev/check-before-submit.sh                 | 21 +++++---
 scripts/tests/test_check_before_submit.py          | 63 +++++++++++++++++++---
 （台帳 .claude-pipeline/active-work.d の 2 件は取り込み済みの既存差分）
 消した行（'^-[^-]'）: 14（台帳 1 行を含む）
 numstat: 15 6 scripts/dev/check-before-submit.sh / 56 7 scripts/tests/test_check_before_submit.py
```

## 記録
- 新規 2 本（M2・M5）は置き場所を `test_untracked_file_is_not_in_copy` の次ではなく `test_prepush_stops_when_copy_fails_check` の直前にした（試験の中身はカードどおり）。
