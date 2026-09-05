# handoff recon — TCG LINEインポートパイプライン 2026-09-05

この文書は何か（専門用語なしの1行）: 2026年9月5日に本番で何が起きたかを実測のみで書き出した引き継ぎ記録。

- 日付: 2026-09-05
- 実測時の origin/main SHA: ffd50d98ab6645ec880809b5eb7823a8c9540d44
- 関連テーマ: docs/handoff/tcg-product-master-growth/recon.md

---

## 1. 本日マージしたPR一覧（28本・2026-09-05 JST 全件）

| # | PR | ブランチ | 内容 | マージSHA（7桁） | マージ時刻 |
|---|---|---|---|---|---|
| 1 | #3276 | tcg-pokemon-master-batch1 | feat: ポケモン商品25件をtenant_004商品マスタに登録 | 87614adc | 00:02 |
| 2 | #3277 | tcg-diagnostics-drawer | feat: 診断ドロワー実装（extraction_jobs・source_messages閲覧） | e6052c8d | 00:23 |
| 3 | #3278 | lessons-discord-reaction | docs: Discord反応仕様セッション（2026-09-04）レッスン記録 | a38f066c | 00:16 |
| 4 | #3279 | preamble-alt-means-ban | docs: executor-preamble に「代替手段で済ませる」禁止ルール追加 | de10899c | 07:27 |
| 5 | #3280 | tcg-ss-catalog | docs: スーパースターカタログ調査記録 | 82efee8b | 01:14 |
| 6 | #3281 | sop-pr-format | docs: executor-preamble にPR作成手順（標準ワークフロー形式）追記 | 48a8ca53 | 00:52 |
| 7 | #3282 | tcg-data-sources | docs: 商品マスタ整備のデータソース（GAS・LINEエクスポート）調査記録 | a9b30c53 | 01:21 |
| 8 | #3283 | tcg-fix-product-names | fix(tcg): 4商品名・1拡張版マークを修正（tenant_004実測） | 78db5b87 | 05:57 |
| 9 | #3284 | card-templates | docs: カードテンプレート（各種カードの正規フォーマット定義）をhandoffへ移動 | f21e16d6 | 06:50 |
| 10 | #3285 | tcg-line-import-stage1 | feat: MIG-04 Stage1 LINEエクスポート取り込みパイプライン + スキーマ修飾 + CI4件修正 | 7bbd6d59 | 07:45 |
| 11 | #3287 | fix-guard-hex-ratchet | fix(ratchet): `(# PR番号)` 形式を16進数誤検知から除外 | cf0372dd | 07:24 |
| 12 | #3288 | card-templates-guessing | docs: カードテンプレートに「推測禁止」ルール追加 | 1673717f | 07:42 |
| 13 | #3289 | tcg-onepiece-catalog | docs: ワンピースカタログ（63アイテム・プロモ/プレミアム版含む）調査記録 | ae737ceb | 07:59 |
| 14 | #3290 | tcg-line-import-router-schema-fix | fix(tcg-router): import_jobs SQLにtenant_004スキーマ修飾を追加（search_path不足） | a0b765fd | 08:18 |
| 15 | #3291 | tcg-gemini-extraction-stage2 | feat: MIG-04 Stage2 Gemini抽出移植（gemini_extraction_svc + tcg_extraction） | 2153b524 | 08:36 |
| 16 | #3292 | tcg-auto-analyze-enable | feat: TCG_AUTO_ANALYZEを本番cutoverスクリプト経由で有効化（docker run環境変数） | a68b284f | 09:02 |
| 17 | #3293 | tcg-import-latest-only | fix(tcg-import): 仕入元ごとに最新メッセージ1件のみ採用（SQR-05・全消え防止） | 8c0d0a57 | 09:23 |
| 18 | #3294 | nav-tcg-line-import | feat: サイドメニューに「インポート」追加（NAV-01） | d7c697d8 | 09:16 |
| 19 | #3296 | tcg-import-fk-order-fix | fix(tcg-import): INSERT source_messages → UPDATE の順序入れ替えでFK違反解消 | 1e57df8d | 10:22 |
| 20 | #3297 | sop02-pr-template-hint | docs: PRテンプレートの標準ワークフロー確認欄にHTMLコメントヒント追記 | a5315fd9 | 10:45 |
| 21 | #3298 | tcg-diagnostics-extraction-keys | feat(tcg-diagnostics): 抽出パイプライン監視用診断キー4つ追加 | e11bafd5 | 10:43 |
| 22 | #3299 | imp-35-is-active-filter | fix: source_messages の is_active=TRUE フィルタを3サービスに追加（IMP-35） | f734f2e5 | 10:58 |
| 23 | #3300 | tcg-sender-split | fix: parse_line_export 送信者名切り出しをGAS latest24SplitHeader_に合わせる | 154e93f6 | 11:06 |
| 24 | #3301 | sec-01-gemini-error-redact | fix: GeminiエラーメッセージからAPIキーを除去（SEC-01） | f8e3f1ff | 11:30 |
| 25 | #3302 | sup-register-15 | feat: 仕入元15件（SP0188〜SP0202）+ LINEチャンネル行をtenant_004に登録 | d6dc4e56 | 11:40 |
| 26 | #3303 | tcg-diagnostics-retry-extraction | feat: extraction_jobs再実行エンドポイント追加・診断ドロワーに再実行ボタン配置 | f1d3f24e | 12:07 |
| 27 | #3304 | fix-cutover-sa-key-mount | fix: cutover docker run にtcg-sheets-sa.json固定パスマウントを追加（2回目踏み） | def62568 | 12:26 |
| 28 | #3305 | fix-tcg-received-at-jst | fix: tcg_line_import_svc の received_at をUTC→JST として保存（DIST-R3） | ffd50d98 | 12:55 |

備考: タスク起票時は「17本」と見込んでいたが実測は28本。

---

## 2. 本番で判明した構造上の落とし穴

### 2-1. docker run と docker-compose の環境変数・ボリューム分離

**事実**（#3292・#3304 で2回踏んだ）:

`backend` は `scripts/blue-green-cutover.sh` 内の `docker run` コマンドで起動する。
`docker-compose.yml` の `environment` セクションおよび `volumes` セクションは **backend コンテナに効かない**。

- `TCG_AUTO_ANALYZE=true` を docker-compose.yml に書いても無効（#3292 原因）
- `tcg-sheets-sa.json` のボリュームマウントを docker-compose.yml に書いても無効（#3304 原因）
- 対策: `scripts/blue-green-cutover.sh` の `docker run` 呼び出しに `-e` フラグ・`-v` フラグを直接追加すること

確認コマンド: `grep -n "docker run" scripts/blue-green-cutover.sh`

### 2-2. search_path と schema 修飾

**事実**（#3290 で修正）:

本番のsearch_pathは `{pg_catalog, public}`。`tenant_004` スキーマは自動で検索されない。
TCGパイプラインの全SQLで `tenant_004.テーブル名` の明示修飾が必須。

修飾漏れの検出コマンド:
```bash
backend/tests/test_tcg_schema_qualification.py
```
（静的検査で主要テーブルを網羅。ただしSQLを文字列で組み立てる場合は捕捉できない）

### 2-3. 24時間窓のUTC基準ずれ（#3306 で是正予定）

**事実**:

LINEエクスポートの取り込み対象期間を「24時間以内」と定義しているが、
UTC基準で計算されているため JST 換算で実質33時間になる。
`#3306`（取り込みの2段階化）でこの是正を予定。

### 2-4. received_at のUTC誤保存（#3305 で是正済み）

**事実**:

`tcg_line_import_svc` が received_at を UTC として保存していた。
`#3305` で修正済み（DIST-R3）。
ただし移行306件の received_at は元データに存在せず、永久に空欄のまま。

---

## 3. テストが捕まえない範囲

本日の障害3件はすべてテスト緑のまま本番で発覚した。

| 障害 | テストがグリーンのまま通った理由 |
|---|---|
| FK順序違反（#3296） | DB接続をモック → SQL実行順序が検査されない |
| commit前エンキュー（#3303前身） | DB接続をモック → commit/rollbackとキューの順序関係が検査されない |
| スキーマ修飾漏れ（#3290） | DB接続をモック → 実際にSQLが実行されないためsearch_path依存が表面化しない |

部分的な塞ぎ手: `backend/tests/test_tcg_schema_qualification.py`（静的文字列検査・#3303時点で追加）

**根本的な空白**: テスト層でDBをモックしている限り、SQL文字列の正しさと実行順序は本番まで検証されない。

---

## 4. 未解決の業務課題

### 4-1. 「〆」「売り切れ」投稿で在庫が全消えする（#3293 の副作用）

SQR-05（最新1件のみ採用）の実装後、仕入元が「〆」「売り切れ」だけを投稿した場合、
その投稿が最新1件として採用される。
結果: その仕入元の在庫がゼロ扱いになる。
**対策未実施**。設計が必要。

### 4-2. 仕入元名の重複の可能性（#3302 で登録した15件）

SP0188〜SP0202 と既存仕入元の名称が実質同一の可能性がある。

| 新規登録 | 既存の可能性 |
|---|---|
| funスタッフ | 株式会社fun labo |
| Kei | けい |
| 大知 | たいち |
| oyama | やまちゃん |

**確認未実施**。マスタ重複なら集計・分析がずれる。

### 4-3. 移行306件の received_at が永久に空欄

移行データ（2026-09-04以前）の received_at は元LINEエクスポートに存在しない。
フィールドは空欄のまま残る。表示・ソートの影響を確認していない。

### 4-4. 解析失敗が無音（extraction_jobs が done のまま）

解析パイプラインが失敗しても `extraction_jobs` のステータスが `done` のまま変わらない。
エラーは記録されない。リトライもされない。
`#3303` で手動再実行ボタンは追加したが、自動検知・自動リトライは未実装。

### 4-5. 昨日の pending 26件が未処理

2026-09-04T07:54 時点で pending 状態の extraction_jobs が26件あった。
本日（2026-09-05）時点での処理状態は未確認。

---

## 5. 未マージ・未着手

| 項目 | PR/場所 | 依存関係 |
|---|---|---|
| 取り込みの2段階化（24時間窓是正） | PR #3306 (backend) | マージ待ち |
| 配信プレビューの500エラー（ar.created_at） | PR #3258 | マージ待ち |
| ビューアの Series 列対応 + 24時間フィルタ | shingo-ops/tcg-client-viewer | PR #3306 マージ後 |
| 確認画面 | frontend | PR #3306 マージ後 |

---

## 実測の出所

- git log: SHA ffd50d98ab6645ec880809b5eb7823a8c9540d44 を基点に実行
- ファイル: worktree `release-handoff-2026-09-05-summary` で確認
- 書き込みは一切行っていない
