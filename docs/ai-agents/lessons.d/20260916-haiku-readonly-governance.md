分類: 6-3
出所: （2026-09-16 PR #3524）

# Haikuサブエージェントの読み取り専用ガバナンス

## 1. Haikuに書き込み操作を委任してはならない（分類 6-3）

PR #3524 の作業中、Haikuサブエージェントに調査を委任したところ、
指示に含めていない git add / git commit / git push を独断で実行した。
その結果、design.md が diff に未宣言ファイルとして追加され、
process-artifacts gate が赤になった。赤の原因調査と修正で
CI赤が5回連鎖した。

Haikuは読み取り専用として委任する。git add / git commit / git push /
ファイル編集（Write/Edit）を指示に含めてはならない。
委任時は「出力を全文貼れ。分析・行動をするな」と明示する。

## 2. migration-test.yml のテーブルスタブは既存Pythonマイグレーションと競合する（分類 6-1）

migrate_inventory_sprint1.py は public.products テーブルの存在を確認し、
存在しなければ全カラム付きで CREATE TABLE する。CI用に最小カラムの
スタブ（7カラム）を事前登録すると、Python側が「テーブルは既にある」と
判断してCREATEをスキップし、存在しないカラム（jan_code等）への
インデックス作成で失敗する。

対策: products を参照する SQL migration は IF EXISTS ガードで
テーブル不在時をスキップする設計にする。CI用スタブで
Pythonマイグレーションの前提を壊さない。
