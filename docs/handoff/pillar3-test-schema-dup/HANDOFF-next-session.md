# 引き継ぎ — 柱3 検出ロジック作り直し（IF混入の真因が未解明）

作成: 2026-07-24 セッション終了時
状態: 柱3-a/b の検出スクリプトに取りこぼしバグが判明。作り直しが必要。数の最終確定が未完（IF混入バグ残存・真因未確定）。

---

## このセッションで本番反映した成果（全て state=MERGED 確認済み）
- 柱1完結: #3069/#3074/#3080/#3087/#3091/#3104/#3113
  - #3091 柱1-a: PR作成時に .pr-number 自動生成
  - #3104 柱1-c-1: RULE_WAIT中 BEHIND 検出で待機せず追従へ戻る（本番 gh-pr-merge-safe.sh 反映済）
  - #3113 柱1-c-2: checks待ちを gh pr checks --watch --required に（本番反映済）
- 柱3-a/b: #3117(recon 46行)/#3120(design 68行)/#3121(本体+テスト)/#3122(CIジョブ non-mandatory)
  - ※ #3121 の本体 scripts/check-test-schema-dup.js は取りこぼしバグあり（下記）

## 【最優先・要対応】柱3本体スクリプトの取りこぼしバグ（実測確定）
- 現状: scripts/check-test-schema-dup.js は execute(text 三連引用符 の1形式のみ検出（本番36行目相当）。
- 問題: 実際のテストの本物DDLは4形式ある。大半を取りこぼす。
  - 見逃す本物形式（実測）: (1)変数代入 _X_DDL = 三連引用符CREATE TABLE...（最多。test_message_send/test_outbound_draft_send/test_discord_inbox 等）(2)execute と text が別行の多段 (3)exec_driver_sql (4)dbapi_conn.execute
- 影響: 柱3-a/b の「新規複製を止める」が、変数代入形式で新複製を足すと素通り。KGI 柱3-b「変種を取りこぼさない」を実は未達。
- 原因: ペアテストを自分が実装した1形式だけで作り実データの多様性を検証しなかった。実ファイルで数え直す検算を実装後にやった（本来は実装前）。

## 検出方式の結論（作り直しの設計）
- AST 方式に切り替える（正規表現の行走査は書き方の多様さに追随できない）。
- Python の ast で文字列リテラル内の CREATE TABLE を拾う → execute の形に関係なく本物を捕捉。
- 罠の除外: docstring と assert内 は AST で除外可能（実測確認済）。
- 罠2ファイルはファイル名で除外（自動分類の泥沼回避・実測で妥当性確認）:
  - backend/tests/test_tenant_service.py（CREATE TABLE 7個は全て foo/bar/a/b の SQL分割関数テスト入力・DB非作成）
  - backend/tests/test_inventory_parser_real_samples.py（CREATE TABLE 3個は docstring/コメント内の説明）

## 【未解決バグ】IF がテーブル名として混入する（真因未確定）
- 症状: CREATE TABLE IF NOT EXISTS <name> から IF をテーブル名として13件拾う。約9ファイル（test_adr119_backfill_source_guard, test_analytics_conversion_by_attribute_rls, test_countries_master, test_priority_prospects_pg_rls, test_products_cross_tenant_fk, test_rls_carrier_credentials, test_rls_invariants, test_rls_translation_glossary, test_rls_tenant_meta_config）。
- 試して外れた修正（繰り返すな）:
  1. 正規表現に IF NOT EXISTS の optional 群を付けた → 効かず IF 残存
  2. 「CREATE TABLE位置から70文字で切り出したのが原因」と特定 → 文字列全体にかけても IF 残存。この原因特定は誤り。
- 実物の行は正しい: 例 test_countries_master.py:205 CREATE TABLE IF NOT EXISTS {schema}.country_probe ( 。名前は取れるはず。
- 未確定の仮説（要実測・推測で実装するな）: 名前部の文字クラスが IF の I にマッチし optional の IF NOT EXISTS 群が消費されない可能性。ただし全体にかけても残る理由が未説明。
- 次の手順: IF が出る1文字列を repr で切り出さず全体表示 → その生文字列に正規表現を1件だけ適用し group('name') が何を取るか、なぜ IF NOT EXISTS を読み飛ばさないかを文字レベルで確定してから直す。推測で正規表現をいじらない。

## 数（SHA固定で3回安定・並行開発は無関係と確定）
- IF混入込みの暫定値: 複製ファイル数=29・総数=72（うち IF が偽名で13件混入）。
- 正しい数は IF バグ修正後に確定。parse失敗=0。
- 「並行開発でブレたのでは」の仮説は否定（SHA固定で3回同一を実測）。

## 作り直しの手順（次セッション）
1. IF の真因を上記手順で実測確定 → 名前抽出を直す。
2. 直した確定版で全件集計し、偽名ゼロの最終数と一覧（ファイル→テーブル名）を固定。
3. その確定一覧を基準に本体 scripts/check-test-schema-dup.js を AST 版に作り直す。
4. ペアテストは実28ファイル前後の全件で本物が正しく数えられ罠2ファイルが除外されるを検算（自作問題禁止＝本セッションの再発防止）。
5. docs/specs/process-hardening/design-pillar3.md を AST 方式に更新。
6. 柱3-c の基準数を確定数にする。
7. 1〜5は論理的に一体。1PRで（危険変更・PO自筆GO）。

## 本セッションの教訓（再発防止・design-partner.md 反映を検討）
- 数える道具を新設したら、既存の数え方と突き合わせ一致するまで実装に進まない（recon の grep 数と新道具の数を照合していれば早期に気づけた）。
- テストは実データ全件で検算する。自作の練習問題で代替しない。
- 数字が出ても確定と即断せず、再実行の安定と内訳の妥当性を確認してから確定と呼ぶ。
- 原因特定も「これで直る」と言う前に実測で潰す（本セッションで原因特定を2回誤った）。

## 環境メモ
- 本店作業場 /Users/tanizawashingo/salesanchor は origin/main より大きく遅れる。参照は必ず git show refs/remotes/origin/main:。
- 実行環境は rm 系コマンド拒否。元に戻すは git restore/checkout。
- mac に timeout・cat -A なし。node/python スクリプトは一時ファイルに書いて実行（コマンド行に正規表現直書きすると二重エスケープで壊れる）。
- worktreeフォルダはハイフン区切り、ブランチはスラッシュ。cd失敗時は後続を止める。
- マージは bash scripts/gh-pr-merge-safe.sh --merge のみ。BEHIND/BLOCKED はラッパーに委ねる。報告が途切れても実際はマージ成功＋机自動片付け済みのことが多い（state=MERGED と本番反映で判定）。
