# recon 追補: Mac の空き容量の見張り（2026-10-15・origin/main a0a09cb00 基準）

## 既存 ADR 検索
- `git grep -n -i -E 'disk|ディスク' -- docs/adr/`: ADR-114（:83, :161 で scripts/disk-janitor.sh に言及）、ADR-153:41（ダンプの容量消費）。mac-jobs-watch を直接扱う ADR は無い。
- docs/adr/FEATURE-INDEX.md: mac / janitor / 片付け / 見張り / ディスク の該当行なし。
- 通知先 webhook は ADR-1009（docs/adr/ADR-1009-discord-ops-intake.md）の番人と共有（scripts/mac-jobs-watch.sh:5）。

## 見張り役の作り（scripts/mac-jobs-watch.sh）
- scripts/mac-jobs-watch.sh:20-43 mjw_config。MJW_ 環境変数で既定値を上書き（試験用）。:40 MJW_REPEAT_SECONDS=86400。
- scripts/mac-jobs-watch.sh:153-165 list_has / list_add / prob_names / prob_time / prob_del / prob_set。
- scripts/mac-jobs-watch.sh:168-176 mjw_judged（名前ごとに「判定する回か」）。
- scripts/mac-jobs-watch.sh:179-191 mjw_text（名前 → 固定文）。
- scripts/mac-jobs-watch.sh:218-236 mjw_read_state。:226 で PROB（知らせ済みの問題）を読む。
- scripts/mac-jobs-watch.sh:295-333 mjw_detect_states（状態型点検。list_add DETECTED <名前>）。
- scripts/mac-jobs-watch.sh:444-448 mjw_read_state → mjw_detect_states の順で呼ぶ。
- scripts/mac-jobs-watch.sh:374-390 mjw_classify（新規 / 24h 再通知 / 復旧の振り分け）。
- scripts/mac-jobs-watch.sh:474-505 通知 3 種（異常 / まだ続いています / 直りました）。送信成功時だけ prob_set / prob_del。
- ops/launchd/jp.salesanchor.mac-jobs-watch.plist:46-47 StartInterval 1800。実機の plist は ~/.salesanchor-tools（origin/main の祖先であることを確認してから）を動かす。

## 試験
- scripts/tests/test-mac-jobs-watch.sh（素の bash、ok/ng/eq ヘルパー :20-25、setup :80-106、偽 launchctl / curl）。既存は ①〜㉔（:2）。

## 空き容量の現状
- scripts/disk-janitor.sh:42 DJ_DF_PATH=/System/Volumes/Data。:502, :532 で df -h をログに出すだけ。しきい値判定は無い。
- 実機 2026-10-15: `df -k /System/Volumes/Data` Available 47717140（≒45.5GiB）、Capacity 78%。
- 棚卸し（大きい順）: /tmp/CC報告ファイル/disk-20261015/inventory.md（リポジトリ外）。
- 経緯: 10/13 空き 143MB で npm ci ENOSPC → 片付け設置で 17GiB。10/14 午後に空き 117Mi で全停止。
