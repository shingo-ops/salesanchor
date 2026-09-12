# LINE在庫・〆・混在投稿の商品単位反映調査

この文書は、〆の投稿で他商品まで在庫出力から外れる経路を、現行コードと合成入力で確かめた記録です。
親: [提供元フィード翻訳](../../specs/inventory-management/feed-translation/README.md)。
設計: [design.md](design.md)。
ADR: [ADR-154](../../adr/ADR-154-tcg-parity02-gas-python-migration.md)、[ADR-113](../../adr/ADR-113-two-mode-dev-flow.md)。

調査日: 2026-09-13。固定SHA: `5b21b3b8f12d8c3c443da6cc4bb7c7d1c49ccc15`。
調査対象の「部品」はLINEパーサー・原文保存・商品照合・出力クエリ・非同期タスクと定義する。
現本番DBの件数/適用スキーマ/被害件数は未確認。実装者の報告を採用せず、ファイルと関数の直接実行で検算した。
保存区分は既存テーマの延長・修正。旧SQR-05の調査本文は末尾にそのまま残す。

## 1. 全体像

| 観測 | 固定SHAの根拠 |
|---|---|
| LINE投稿をパース・仕入元解決した後に最新1件を選ぶ | backend/app/services/tcg_line_import_svc.py:120,215,273,579 |
| 同じ仕入元の投稿を時刻順に並べ、末尾だけraw_textへ。先頭の時刻をreceived_atへ入れる | backend/app/services/tcg_line_import_svc.py:301-316 |
| チャネルをロックし、既存のactive原文を全件取得する | backend/app/services/tcg_line_import_svc.py:340-357,385-394 |
| 新しい原文を挿入し、古いactive原文すべてをsuperseded_byで繋ぎis_active=FALSEにする | backend/app/services/tcg_line_import_svc.py:405-437 |
| 抽出ジョブを作り、commit後にエンキューする | backend/app/services/tcg_line_import_svc.py:439-453,613-621 |
| 配信はactive原文の解析行だけを対象とする | backend/app/services/tcg_distribution_svc.py:223-242 |
| シート書込みはclear後にヘッダーとデータを全置換する | backend/app/services/tcg_distribution_svc.py:463 |
| 解析レビューもactive原文だけを結合する | backend/app/services/tcg_analysis_review_svc.py:31-39 |

結論の適用範囲: 「最新が〆なら古い投稿の商品が出力対象から外れる」というコード経路を確認した。実本番でA/B/Cが消えた特定事象を再現した報告ではない。
原文/商品マスタの物理削除を原因とはしていない。有効性と出力対象の切替で表示から外れる。

## 2. 共用部品

- 最新1件構築/原文保存は即時取込と仕入元解決後の確定が共有する。両経路が改訂対象:
  backend/app/services/tcg_line_import_svc.py:579,613 と backend/app/routers/tcg_line_import.py:621,624。
- 商品照合の既存入口: backend/app/services/tcg_analyzer_svc.py:495,1062。新分類のために商品辞書や作品判定を独自に複製しない。
- 原文は既に複数行の構造を持つ。is_activeとsuperseded_byで履歴を扱う:
  migrations/20260906_120000_create_tcg_tables_t001.sql:350-361（QA作成DDL）。
- 原文同一性はsupplier_channel_id/line_posted_at/raw_sha256のunique index。取込と原文は多対多リンクを持つ:
  migrations/20260910_010000_tcg_import_message_links.sql:14-31。
- 同一原文の再利用時は再活性化・再エンキューしない:
  backend/app/services/tcg_line_import_svc.py:367-383。

「複数保存できない」というユーザーに見える制約は、テーブルの1行上限ではなく最新1件選択/有効性/出力経路の組合せである。

## 3. 非共用部品

- 現在在庫の出力: backend/app/services/tcg_distribution_svc.py:183。
- 解析レビューの一覧: backend/app/services/tcg_analysis_review_svc.py:31。
- 取込の進捗: backend/app/services/tcg_import_progress.py:21,66。
それぞれ独立のSQLで原文/解析の状態を読むため、原文保存だけの変更では在庫出力と画面が一致しない。
- 抽出結果はitemsが空ならemptyであり、投稿種別ではない:
  backend/app/services/gemini_extraction_svc.py:303-324。
- 分配の未完了ガードはpending/running/extractedを止めるが、done/empty/errorは終端扱い:
  backend/app/services/tcg_distribution_svc.py:675-683。
以上から「emptyだから在庫全体を0」とする根拠は現契約にない。

## 4. ルールの所在

- 既存仕様索引: docs/specs/README.md。在庫の入口: docs/specs/inventory-management/README.md。
- 原文と人の確認を求める親の願い: docs/specs/inventory-management/feed-translation/ideal-state.md:7-15。
- 旧最新1件契約: 本テーマdesign.mdの旧設計原文。PR #3293はGitHubでMERGED、mergedAt=2026-09-05T00:23:21Zを直接確認。
- 最新1件を正解としているテスト: backend/tests/test_tcg_line_import.py:328,399,424。supersede順序テスト: 同:509。
- ADR検索: ADR-154はGAS移植と既存解析順序の決定。SQR-05/〆/混在の今回の意味は同ADRに既存決定なし。ADR-113は設計持ち込みと整合検査。旧調査のADR説明は履歴として保持し、今回の事実は実ファイルから記録。
- 追加専用のDB規約: backend/AGENTS.md。手順の正本: docs/STANDARD-WORKFLOW.md。今回の起動指示に従い設計担当として文書のみ扱う。

## 5. 維持の仕組み

- backend/tests/test_tcg_line_import.py:328,399は古い最新1件契約の再発防止を担っている。新KGIの保証ではない。
- .github/workflows/test.yml:206-241は実PostgreSQLを含むpytestの実行経路。
- .github/workflows/process-artifacts-gate.ymlは設計/根拠等の検査。
- .github/workflows/adr-index-check.ymlはADR索引、.github/workflows/task-state-check.ymlは台帳形式。
- 本調査で、新しい混在/商品単位の保持を保証する試験は未確立。後続カードに入れる必要がある。
- 配信の未完了ガードと現在在庫の保持は異なる。不成立の抽出が終端化しても古い原文を無効化済みなら出力対象は戻らない。

## 6. 設計図との対照

| 合意/親の要件 | 現状 | 判定 |
|---|---|---|
| A〆はAだけ0・ほか維持 | 原文全体をsupersedeする | 不足 |
| 在庫・〆が混在しても明細別 | 現行抽出に明細はあるが、原文全体の有効性で出力を切替 | 不足 |
| 無関係投稿は在庫不変 | 最新なら内容にかかわらず選ばれる | 不足 |
| 複数原文と根拠を保持 | DBに履歴構造/リンクはあるが取込内の最新以外を棄却 | 一部一致・不足あり |
| 不明を人に報告 | 既存解析needs_review等はあるが、〆対象と反映履歴の専用契約なし | 不足 |
| 対象外の商品マスタを保持 | 調査したsupersedeはsource_messagesのみ | 一致 |
| 優れた既存を残す | 同一原文再利用・チャネルロック・取込リンク・配信安全検査 | 維持。廃棄する余剰として扱わない |

## 7. ノイズと境界

- 「〆」に関係しないFedEx集荷締切、インポート親ジョブを「締める」関数説明は対象外。
- 旧GAS移植の一致率や以前の解析行数は、本件の〆精度や現本番の欠落件数に使わない。
- 対象はLINE系TCG取込。Discord/CRM自社在庫の書換えは調査・設計対象外。
- 実DB・AI API・シート・本番には今回アクセスしない。既存ローカルの他者変更も編集しない。
- ライブラリ/外部APIの仕様照会は未実施。本調査の観測はリポジトリのコード/DDL/純粋関数に限定。

## 8. 実行した現行関数の合成検証

[probe-20260913.json](probe-20260913.json) に入力・出力・source SHAを保存。
固定SHAのファイルをgit showで読み、ASTからsha256_text/build_provider_entriesだけを抽出して実行した。アプリのimport/DB接続/API呼び出しなし。sha256_textには標準hashlibを与えた。
3ケースの共通先行投稿は「商品A 10個 1000円／商品B 20個 2000円／商品C 30個 3000円」。次投稿は各ケースの11:00、先行投稿は10:00。

| 次投稿 | 実際に選ばれた本文 | skipped_message_count |
|---|---|---|
| 商品A〆 | 商品A〆 | 1 |
| ありがとうございます | ありがとうございます | 1 |
| 商品A 5個 1000円 | 商品A 5個 1000円 | 1 |

直接観測: 3/3で先行在庫一覧はraw_textに含まれない。
静的コードからの帰結: この1件を保存すると古いactive原文が無効化され、配信クエリが古い商品行を対象外にする。
未観測: この合成入力のAI抽出結果、本番DBの反映、実シートの変化。検証を本番再現や改善後のテスト合格とは呼ばない。

再現コード:

```python
import ast, hashlib, subprocess
sha = "5b21b3b8f12d8c3c443da6cc4bb7c7d1c49ccc15"
src = subprocess.check_output(
    ["git", "show", sha + ":backend/app/services/tcg_line_import_svc.py"], text=True)
nodes = [n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef)
         and n.name in ("sha256_text", "build_provider_entries")]
ns = {"hashlib": hashlib}
exec(compile(ast.Module(body=nodes, type_ignores=[]), "<fixed-source>", "exec"), ns)
base = {"sp_code": "TEST-A", "canonical_name": "Synthetic Supplier"}
for body in ("商品A〆", "ありがとうございます", "商品A 5個 1000円"):
    messages = [
        {**base, "timestamp": "2026-09-13 10:00:00",
         "body": "商品A 10個 1000円\n商品B 20個 2000円\n商品C 30個 3000円"},
        {**base, "timestamp": "2026-09-13 11:00:00", "body": body}]
    print(ns["build_provider_entries"](messages))
```

## 9. 保存・並行作業の証跡

- 必須preflight成功。本店mainはorigin/mainより95コミット遅れ、既存変更あり。git ls-remote originのmainと固定SHA一致。
- 専用ブランチrelease/line-stock-message-designをorigin/mainから作成。事前に提示した既存作業場所を削除しない方法で、設計継続指示を受けて実施した。新しいAIセッションは起動しない。
- 作成コマンド: git worktree add -b release/line-stock-message-design /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-message-design origin/main。成功、HEAD 5b21b3b8。
- 自ブランチの識別情報と分割台帳を登録。既存の台帳ファイル/作業場所/製品コードを変更しない。
- PR #3441（作品ID）、#3417（原文保持）はOPENを直接確認。今回その差分に実装を重ねない。実装設計の確定時に最新HEADを再照合する。
- 関連runbookを検索したが本テーマ専用のものは特定できず、既存の本handoffとtasks/todo.mdへ記録する。
- 前ターンの削除文字列検索はPreToolUseの不可逆操作ガードに拒否された。削除操作は要求/実行していない。検索以外の独立した読取作業を継続し、ガードを変更しない。

## 文書の直接検証（2026-09-13）

3件の合成入力を保存時に再実行し期待する現行選択結果と一致。git diff --check、ADR索引--check、check-task-state.sh、設計形式・引用パス・維持欄の検証関数が成功。相対リンク（コードブロックを除く）と旧設計/調査原文の末尾一致も確認。最初の簡易リンク検査はコード内の関数呼出しをリンクと誤検知し、検査対象をMarkdown本文へ修正して再検証した。製品テスト・AI分類精度・本番検証の成功を意味しない。

## 10. 未確認と次の調査

1. 実メッセージの分類正解と対象商品/状態/単位。現在在庫のキー候補重複、投稿時刻の同値/欠損の件数。
2. 物理DBの所有者・適用済みDDL・初期在庫候補の行数/一致。本書のDDL引用を実DB確認に読み替えない。
3. 候補方式の費用・時間、再解析/遅延・並行処理時の反映契約、既存画面への具体接続。
設計自己審査はREVISE。次は実例と識別キーの読み取り調査で、設計草案の未確認を埋める。製品実装カードは未発行。

---

## 旧調査原文（SQR-05移植時点・履歴）

# recon — tcg-import-latest-only (SQR-05 移植)

## 調査対象

GAS SQR-05（tcg-inventory-parser PR #279）で変更された「仕入元別・最新1件採用」ロジックが、
Python 版 `backend/app/services/tcg_line_import_svc.py` に移植されていないことを確認し、修正する。

## 根本原因の特定

### GAS 側 変更（SQR-05 / PR #279、2026-08-30）

tcg-inventory-parser の `buildLatest24Dataset` (line 88):

```diff
- var raw = rows.map(function(m) { return m.body; }).join(LATEST24_SEPARATOR_);
+ var latestMsg = rows[rows.length - 1];
+ var raw = latestMsg.body;
```

`applyLatest24Extraction` (line 215) にも同等変更。

### Python 側 現状（SQR-05 未適用）

`backend/app/services/tcg_line_import_svc.py:221`（修正前）:

```python
raw_text = _MSG_SEPARATOR.join(m["body"] for m in sorted_msgs)  # 全件結合
```

→ GAS（最新1件のみ）と不一致。

## 影響範囲

- 修正ファイル: `backend/app/services/tcg_line_import_svc.py`
- 修正関数: `build_provider_entries`（line 194）
- 変更行数: 本体 2行変更 + 1フィールド追加
- `import_line_export` の戻り値: `skipped_message_count` 追加
- `backend/app/routers/tcg_line_import.py`: `ImportResultResponse` に `skipped_message_count: int` 追加
- テスト: `backend/tests/test_tcg_line_import.py`（既存2件更新 + 新規2件追加）

他に `build_provider_entries` を呼ぶ箇所は `import_line_export` のみ（grep 確認済み）。

## 既存 ADR 調査

- `docs/adr/ADR-154`（TCG LINE インポートパイプライン設計）— MIG-04 全体設計。SQR-05 相当の記述なし。
- `docs/adr/ADR-072`（テナントスキーマ）— write 系: db.commit() 後 reset_tenant_context() 必須。本PR 変更外。

## supersede の挙動（確認済み・変更なし）

`import_line_export` step5（`backend/app/services/tcg_line_import_svc.py:336〜`）:
- `build_provider_entries` が仕入元ごとに1エントリを返す
- 既存 `is_active=TRUE` レコードを `superseded_by` でリンクして無効化
- 新規1件を INSERT
- 同一アップロード内の複数メッセージは `build_provider_entries` で集約済みのため、supersede は機能しない（INSERT は1件のみ）
