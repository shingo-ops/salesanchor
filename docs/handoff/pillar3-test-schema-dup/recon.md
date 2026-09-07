# 柱3 recon — テストスキーマ複製（柱3-a/b 中心）

> この文書は何か（専門用語なしの1行）:
> テスト用ファイルが本番と同じテーブル定義を勝手にコピーしている実態を、証拠つきで棚卸ししたもの。

親KGI: docs/specs/process-hardening/kgi.md（柱3節）
recon日: 2026-07-24
基準SHA: refs/remotes/origin/main（採取時点）

## 1. 問題（KGI前提の実測確認）
テストファイルが本番テーブルの定義を各自コピーして持つ。本番に列を足すとコピー側も直す必要が生じる（KGI記載: #2956で179件連鎖）。

## 2. 複製を持つファイル数（実測）
- backend/tests 配下で CREATE TABLE を含むファイル: 32件
- うち共通定義 backend/tests/conftest.py（集約先・CREATE TABLE 64件）を除いた独自複製: 31ファイル
- KGIの「31ファイル」と一致。

## 3. 書き方の変種（柱3-b の検出対象・実測）
- IF NOT EXISTS の有無: `CREATE TABLE leads (` と `CREATE TABLE IF NOT EXISTS leads (` が併存
- スキーマ接頭辞: `{schema}.leads`, `public.tenants`, `{WORK_SCHEMA}.leads` 等のプレースホルダ付き
- AS 構文: `CREATE TABLE public.tenants AS`
- 本物の複製の書かれ方: `await conn.execute(text("""` に続く複数行DDL（例: backend/tests/conftest.py:141-142）

## 4. 誤検出の罠（検出時に除外すべき・実測で範囲確定）
本物の複製ではないのに CREATE TABLE 文字列を含む箇所:
- backend/tests/test_tenant_service.py:17 — sql文字列（CREATE TABLE foo / bar）
- backend/tests/test_tenant_service.py:25 — sql文字列（CREATE TABLE foo）
- backend/tests/test_tenant_service.py:40,41 — assert 内の文字列（CREATE TABLE a / b）
- backend/tests/test_inventory_parser_real_samples.py:60 — docstring内の説明文
これらを複製とみなすと誤検出（foo/bar/a/b が偽のテーブル名になる）。単純な行一致の正規表現は IF NOT EXISTS の IF も誤って拾う。

## 5. 複製されているテーブル（柱3-c の材料・実測の複製回数）
leads=9, staff=9, tenant_meta_config=8, meta_messages=7, audit_logs=4, tenants=3, tenant_discord_config=3, public.tenants=3, lead_channels=2, data_access_events=2, conversation_logs=2（foo/a/b/IF は誤検出のため除外対象）

## 6. 検出を足せる場所（実測 file:line）
- 既存の最重要関所 scripts/check-process-artifacts.js は CI の .github/workflows/process-artifacts-gate.yml:44 で実行される。
- 同関所の既存基盤: getAddedFiles()（151行, 新規追加ファイルを git diff --name-status --diff-filter=A で取得）／削除照合の git diff --numstat（792行）。
- 制約: 既存関所には「既存ファイルへの追加行」を抽出する処理が無い。柱3-a の新規CREATE TABLE増加検出には追加行のdiff処理が新規に必要。
- 独立スクリプトの手本: scripts/check-dangling-routes.js 他（scripts/check-*.js/sh が11本）。ペアテストの手本: scripts/tests/test-migration-registration-exists.js。

## 7. 採用方針（設計の前提）
柱3-a/b の検出は、最重要関所 check-process-artifacts.js には足さず、独立スクリプト（例: scripts/check-test-schema-dup.js）＋専用CIジョブとして実装する。理由: 全PRの生命線である関所に新種のdiff処理を足す危険を避け、単体テスト可能にするため。CIジョブ追加（.github/workflows/）は危険変更でありPO自筆GOを要する。

## 8. 未確定・次段で詰めること
- 新規増加の判定を、追加行diff（git diff の + 行のCREATE TABLE）で行うか、ファイル単位で行うかは設計で決定する。
- 誤検出除外の具体ルール（文字列・アサーション・docstring の除外方法）は設計で確定する。推測で実装しない。
