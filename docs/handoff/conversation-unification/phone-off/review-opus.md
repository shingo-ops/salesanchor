# 審査記録: 名簿から「電話」「対面」を外す

## 1. 設計とカードの審査（クラウドの Opus・1 回目）

- 日時: 2026-11-08 01:09〜01:11 UTC（対象 HEAD a3e9ba602）
- 判定: APPROVE（高の指摘 0）
- 指摘と直し（eb56efd0f で反映）:
  1. 中 precheck で id 10・11 の conversion_item が空かを確かめていない → precheck に `ids_10_11_no_conversion_item` を足した。本番観測 2026-11-08 10:13 JST で 2 行とも空（/tmp/CC報告ファイル/conv/pi-q4.txt）
  2. 中 K4・K5 の測り方が 2 通りに読める → K3・K4 は reader 鍵で 1 社 1 文の読み取り、K4 は実施時刻より前に作られた行に限って比べる形に、K5 は rollback.sql の restored 検査の形に書き直した
  3. 低 run.sh の変える行の数の書き方 → 「2〜4 行目を変え、5 行目以降はそのまま」に直した
  4. 低 diff のパスが相対 → docs/ から始まるパスに直した
  5. 低 get_channel_by_id は is_active を見ない → 設計 §4 に例外として書いた
  6. 低 会社が phone を足し直した後に rollback すると 2 行並ぶ → 設計 §8 のリスクに書いた
- 未確認として挙がった「Opus が manual-only 鍵で本番に書くことの扱い」: PO 2026-11-08 の依頼文で「SSH への無制限鍵へのアクセス等、必要な権限は全て必要な場合は使用して良い」「PRマージ、デプロイまで完走させてくれ」と明示されている

## 2. 実装の照合（Opus・手元）

- 実装: クラウドの Sonnet（05551e4ef）
- 照合の結果:
  - 変更ファイルは phone-off/ の 8 本だけ（git diff --name-status origin/main...HEAD）
  - run.sh の 5 行目以降は data-store/run.sh と同じ（diff rc=0）・bash -n rc=0・実行権あり・15 行
  - SQL 5 本はカード §1-3〜§1-7 の文と一字ずつ同じ

## 3. マージ前の審査役（reviewer・opus）

- PR に記録する（VERDICT 行）
