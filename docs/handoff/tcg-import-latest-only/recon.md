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

## 文書PRと追加の読取確認

文書PR: https://github.com/shingo-ops/salesanchor/pull/3456 （OPENを直接確認）。初回HEAD 59aeb61e9bf80501b19581a488180cda11415faf。文書コミット時のpre-commitチェックも成功。最初のcommitコマンドはworkdirを本店mainと判定した事前ガードに拒否され、専用releaseブランチの実在を再確認してgit -Cで対象を明記した通常操作で成功した。ガード変更・mainコミットなし。

既存のtcg-product-master-growth/recon.mdが参照する /private/tmp/line-postdeploy-rows.json、line-loop-active-before.json、line-dictionary-audit-rows.json の3保存先を今回確認したが、3/3でファイル不在だった。過去の文書の集計値を現在在庫や実例の正解として流用しない。未確認の識別重複を埋めるには、別の認可済み保存先または本番の読み取り経路で原文と在庫を取得する必要がある。

## 10. 未確認と次の調査

1. 実メッセージの分類正解と対象商品/状態/単位。現在在庫のキー候補重複、投稿時刻の同値/欠損の件数。
2. 物理DBの所有者・適用済みDDL・初期在庫候補の行数/一致。本書のDDL引用を実DB確認に読み替えない。
3. 候補方式の費用・時間、再解析/遅延・並行処理時の反映契約、既存画面への具体接続。
設計自己審査はREVISE。次は実例と識別キーの読み取り調査で、設計草案の未確認を埋める。製品実装カードは未発行。

## 2026-09-13追加調査: PO提供LINE原文の語検索と除外条件の検算

原文提供は今回解決済み。以前参照した一時ファイル3件の不在は過去の確認事実として保持するが、現在の原文不足とは扱わない。
提供元名/送信者名/商品名・価格を含む実原文は公開文書へ転記しない。公開記録はA/Bの識別子、ファイルSHA256、集計、根拠行番号/行hash、匿名化して作り直した合成例に限定する。
原本はユーザー指定のDownloads配下の2ファイル。原本への書込み0、DB/APIアクセス0。

| source_id | SHA256 | bytes | 行数 | 20候補語の該当行（和集合） |
|---|---|---:|---:|---:|
| A | f88a6a7c193b6c178dad7ba8104ffffd9b7cd46b52b6afefef33a860fb4e61a3 | 2929746 | 120412 | 1582 |
| B | 8a765988fb5c7dc50374625293a3760c90236ce2ec57e565e1cc20e169e7ae07 | 25736286 | 985978 | 11523 |
| 合計 | ファイル間の投稿重複を除いていない | 28666032 | 1106390 | 13105 |

方法: UTF-8-SIGで全ファイルを読取、splitlines、各行をlowerへ変換し20語のliteral substring有無を数えた。Unicode正規化・時間窓フィルターは未適用。同じ行の語数を加算せず和集合を別計数。各語の行数は重なり、〆切は〆に含まれる。再投稿・別ファイルの重複はそのまま数える。
この13105行は検索候補であり、売り切れ通知件数・ユニーク投稿件数・分類正解率ではない。
全20語別集計と14根拠位置のhashは [probe-20260913.json](probe-20260913.json) のvocabulary_corpusへ保存。

### 文脈で確かめた境界（実原文を公開せず意味だけ記録）

| 根拠位置 | 観測した意味 | 設計への影響 |
|---|---|---|
| A:448 | 国外向けのラベルの時刻締切 | 〆だけで商品の欠品としない |
| A:84917 | 在庫有無に関係なく時刻で受付終了 | 「〆=売り切れ」は商品売切の文脈に限定 |
| A:2005,20098 | 問合せ時などに完売している可能性の注意書き | 断定ではなく一般的な可能性を区別 |
| A:31113,90252 | 現在は完売だが追加可能性あり、別発送分は残る | 「可能性」「予定」を丸ごと除外にすると真の完売を見逃す |
| B:49283 | 当日出荷分の完売と翌日以降の入荷予定が同居 | 発送枠と時間を分ける |
| B:165528 | 旧価格の在庫は完売、別価格なら提供可能 | 同じ商品でも価格別の販売枠を区別 |
| B:397088 | 開封条件等が異なる行と数量の矢印更新/在庫なしが同居 | 品目/状態/単位/販売条件の粒度を保つ |
| B:705265 | 梱包資材の在庫切れ | 販売商品を消す対象ではない |
| B:712492 | 特定の販売単位の品切れ | 別単位を巻き添えにしない |
| B:819695 | 売り切りセール | 売り切れの同義語ではない |
| B:264565 | 本日分は〆、前日分は残る | 時刻文字列だけでなく販売枠を特定 |
| A:39205 | 特定商品の〆切 | 〆切の語を一律除外にしない |

区分は設計担当が確認した文脈上の境界。販売商品マスタID・提供者ID・現本番在庫行への対応は未確定。網羅的な正解ラベルは未作成。
探索用の広い正規表現は商品名中の文字も拾ったため、探索候補のカテゴリ数をそのまま意味分類の正解数に使わない。

### 既存の「除外パターン」列は判定に接続されていない

固定コード: backend/app/services/tcg_analyzer_svc.py:979-1060。
調査ブランチ基点5b21b3b8と更新されたorigin/main d66923e2edad1b6c22df4cba8adf74f23b968cfcを同ファイル/LINE取込/配信で比較し、差分0を確認した。

1. load_status_masterのSELECTはexclude_patternを取得する（:985）。
2. 戻り値の各dictはcanonical/search_pattern/priority/match_type/effectだけで、exclude_patternを落としている（:995-1004）。
3. resolve_status_v2はその除外条件を評価せず、EXCLUDEの肯定パターン一致でexcludedを返す（:1034-1046）。
4. raw_memoの完全一致経路も同様。数量0を永続在庫へ適用する仕組みと、解析結果のexclusionは別の契約である。

ASTでload_status_master/_match_status_pattern/resolve_status_v2のみを抽出し、DBの代わりに合成2行を返すFakeSessionを渡した。
肯定パターンは「売り切れ|完売」、除外パターンは「売り切れではない|完売となる場合」、DEFAULTはactiveという合成データ。実マスタの登録内容ではない。

| 合成raw_state | 実際の返り値 |
|---|---|
| 売り切れ | sold_out, excluded |
| 売り切れではない | sold_out, excluded |
| 予告なく完売となる場合があります | sold_out, excluded |

戻り値dictにexclude_patternが存在する件数0。意図した反例2/2が同じ除外扱いとなった。AIが実投稿からこのraw_stateを生成するかは未検証で、実データの誤判定率ではない。
初回の隔離試験は検証側TCG_SCHEMA定数の用意漏れで失敗。合成専用定数を与えて同じ関数を再実行して得た結果を記録した。製品コードの変更はない。
再現データと関数名/コードSHA/hashはprobe JSONのstatus_exclusion_probeに保存。

追加分の直接検証: 候補語集計の合計・20語・14根拠位置・合成状態3ケースのJSON整合、設計形式/引用/維持欄、ADR索引、台帳、差分空白、相対リンク、旧本文の保持を再確認して成功。原本ファイルへの書込み0、既存の判定コード変更0。

### 追加調査後の次の一手

- design.md §12に11候補群・8抑止条件・12回帰ケースを文書登録した。runtime登録/有効化は0。
- 実原文を材料に正解集合を作り、商品IDだけでなく価格/発送分/状態/単位の販売枠を特定する。曖昧な枠は人の確認へ回す。
- 既存exclude_patternを効かせる場合も適用範囲と正例/反例を先に確定する。文全体への単純な除外では別商品の正例を潰すため、除外列の配線だけで本件完了とはしない。
- 自己審査REVISE継続。実DBの識別キー・DDL/API/切替手順と、改善後の実原文/実PG検証は未完了。


## 2026-09-13追加確認: 締切の統一性と既存の発送枠処理

### 同じ仕入元で締切は一律か

A:84909の送信者表示名に完全一致する時刻付きヘッダーを2ファイルで抽出。日付行と次の時刻ヘッダーを区切りとして投稿を集計した（A28/B372、計400）。送信者名は非公開とし、DBの仕入元IDとの同一性や他の表示名は今回未照合。ファイル間の重複は除いていない。
「在庫の有無に関係なく17時30分で〆」の文は400投稿中1投稿、A:84917（2026-09-07 14:47の投稿）。その投稿にはA:84912に14時までの注文で当日発送という別の条件がある。
全投稿に17時30分の〆があるという前提は、この表示名の標本では成立しない。

当日発送の明示型「※N時までの(ご)注文で当日発送」は121投稿で検出した。複数型が同じ投稿にあるため該当行数は141。時刻別行数は6時2、10時19、11時10、12時3、13時5、14時33、15時69。
この型が現れる日付115日のうち、異なる時刻の候補がある日付は12。ただし条件差・書き直し・矛盾を意味分類した件数ではない。
手動で確認した具体例:
- B:601762（2025-12-04 10:30投稿）は13時、B:604244（同日21:26投稿）は15時。原文だけから標準締切/変更/誤記のどれかは確定しない。
- B:856347と856350は同一投稿内に14時/11時の2条件がある。後者の前に国外向け配送/転送案内があるため、種類を区別せず1時刻へまとめない。
全仕入元が統一/非統一という一般化はしていない。この対象表示名の反例から、仕入元別の単一締切を自動仮定しない設計へ反映した。

### 発送日①②の解析は既存のままでできるか

- backend/app/services/gemini_extraction_svc.py:35-46は商品/数量/価格/単位/状態/備考/根拠行/作品の9列。発送枠ID専用列はこの出力契約にない。
- 同:190-290は応答の各行を別明細として保持し、raw_memoと根拠行も保持する。
- backend/app/tasks/tcg_extraction.py:165-191は各明細をextraction_itemsへ保存する。
- backend/app/services/tcg_analyzer_svc.py:1206-1222は数量/価格、注記、状態を解析する。:918-954のbuild_note_jaは注記マスタに一致したラベルだけを返すので、raw_memoに「追加可能性あり」があってもsystem.noteへの表示は自動保証されない。
- backend/app/routers/tcg_analysis_review.py:28-46とbackend/app/services/tcg_analysis_review_svc.py:238-256は抽出メモとシステムstatus/note/exclusionの出力枠を持つ。
- 同レビューサービス:72-84はexclusionがあればNEEDS_REVIEWへ入れ、NORMAL_COMPLETEDから外す。原文activeに依存する一覧条件も:35にある。完売の確定表示と判定失敗の分離・履歴保持には改訂が必要。

既存parse_extraction_responseをAST隔離し、同商品・発送日①完売/②在庫12BOXという2行の合成応答を渡すと、2行と異なる備考を保持することを確認した。AI APIは呼んでいない。入力の原文からAIがその応答を出すこと、適切な原文範囲/商品ID/販売枠に紐づくこと、実在庫へ安全に反映することはこの試験で保証しない。
結論: 複数明細と表示枠は再利用可能。既存システム全体が発送枠を自動判定・継続管理できるとは確認できず、専用の対象識別と後続通知対応の設計・検証が必要。

POの追加指定をdesign.md §13へ記録した。完売行は解析リストへ保持し、ステータス完売・備考追加可能性ありとする。製品/マスタの変更なし。

## 追加予定日部品テスト（2026-09-13）

固定コード: origin/main `99a008a74a8c9926871d1e9ad084433f0b3e8cd3`。対象2ファイルは設計ブランチHEADと差分0。コード/提供2ファイルのSHA256、日時、各入出力は [probe-20260913.json](probe-20260913.json) に記録。提供ファイルのハッシュは前回確認時と2/2一致。

実行: 一時領域のローカル検証ハーネス（保存対象外。再現する仮マスタと手順は下記、入出力はリンク先JSON）。実コードの関数ASTだけを読んで、`parse_extraction_response` → `build_note_ja` と `resolve_status_v2` を実行した。原文全体のAI抽出ではなく、原文から切り出した備考を手動で9列応答へ入れた。商品名は商品Aへ置換。状態も手動ラベル。実DBのマスタは未照会・未変更。

| ケース | 根拠/種別 | 確認内容 | 備考結果 |
|---|---|---|---|
| R1 | A:31113 | 完売＋追加可能性 | 統一表示一致 |
| R2 | B:109822 | 後日追加入荷予定 | 日付未定付き統一表示一致 |
| R3 | B:95980 | 後日追加予定 | 日付未定付き統一表示一致 |
| R4 | B:325164 | 8月30日再入荷予定 | 月日保持一致 |
| R5 | A:1957 | 12月下旬〜1月中旬入荷予定 | 期間表記保持一致。初回予約入荷であり補充の実例とはしない |
| S1 | 合成、投稿2026-09-13 JST | 明日追加入荷予定 | 不一致: 9月14日へ変換されず日付未定 |
| S2 | 合成 | 9月20日発送予定＋追加入荷予定 | 一致: 発送日を入荷日へ流用しない |
| S3 | 合成 | 再入荷予定なし | 不一致: 追加予定ありへ誤変換 |
| S4 | 合成 | 2月30日再入荷予定 | 不一致: 不正日付をそのまま表示 |

部品の原文備考保持9/9、仮ルールの備考一致6/9、不一致3/9。空マスタ対照では9/9がnote=None。これは本番マスタが空であるという観測ではない。ステータスは手動完売ラベル7件がsold_out/excluded、空状態2件はactiveとなった。数量、別商品不変、販売枠照合、日付経過、画面保持は未試験。

再現する仮マスタ: JSONの `candidate_date_pattern` に `(?:追加|再)?入荷予定` を連結し、REGEXの `label_template` を `追加予定あり（$1入荷予定）` とする。これに一致しなければ `candidate_restock_pattern` とテンプレート `追加予定あり（日付未定）` を使用。exclude_keywordsは空。これは欠点を含む比較用候補で、登録してよいルールではない。既存のbuild_note_jaを順に2回呼ぶ比較ハーネスであり、新規の製品コードではない。

根拠: `backend/app/services/tcg_analyzer_svc.py:905` 捕捉表示、同:918 備考生成には投稿日引数なし、同:1022 状態判定。`backend/app/services/gemini_extraction_svc.py:190` 応答形式パース。試験でAI API送信0、DB操作0、製品コード変更0、再解析/配信0。自己審査REVISE。

## 再入荷予定なしの追加部品試験（2026-09-13）

PO合意に従い合成3件N1〜N3を追加。固定SHAは `99a008a74a8c9926871d1e9ad084433f0b3e8cd3`。前節と同じ未変更関数・仮マスタ・手動9列応答を使用し、数量だけを8/0/空欄、raw_stateを空欄/完売/空欄にした。全件raw_memoは「再入荷予定なし」。

結果: 数量文字列表現保持3/3、状態判定active/sold_out/activeは期待一致3/3。仮備考ルールは全3件で「追加予定あり（日付未定）」となり期待の備考なしと不一致。これは前回S3と同じ否定処理不足の再現であり、別の3種類の障害ではない。実DBマスタ・AI抽出・数量更新・画面表示・既存在庫保持はテストしていない。

証跡: [probe-20260913.json](probe-20260913.json) の `restock_negative_stock_probe`。N3のactiveはこの関数の既定値であり、既存完売をactiveへ戻す許可ではない。数量/状態の記載がないときは反映イベントを発生させない設計が別途必要。設計の行別受入契約を更新、自己審査REVISE。

## main追従・互換性再確認（2026-09-13）

origin/main `ee455fb1ba4c7ad407ed6506ee4fe515fce371a8` を設計ブランチへ取り込み。競合はADR-154/evidence-registry/tasksの末尾追記3件。双方の追記を保持し、main比の削除は3ファイルすべて0行。製品コードはmainの既存更新を取り込んだもので、本件独自の製品実装ではない。

`backend/app/services/gemini_extraction_svc.py:225` のパーサーはv2/v3/v4を受け、v4の10列目は作品ID。前の9列固定前提を修正。最新SHAでも前回の9件＋否定3件を再実行し、備考一致6/9、数量表現保持3/3・状態3/3・備考一致0/3を再現。これらはv3の手動応答でありv4/AI全文評価ではない。JSONのmain追従再試験に旧結果と区別して保存した。

現在在庫の本番集計は未実行。CLAUDE.mdのVPS鍵規則と `docs/handoff/rehearsal-env/design-b-ssh-isolation.md:58` の監視専用制限を確認した。既存カードの無制限鍵例から本タスクの許可を推定しない。

## 日付の正解値確認（2026-09-13）

[probe-20260913.json](probe-20260913.json) の `date_calendar_oracle` にPython実行版と9件の入力・期待値・実測値を保存。原投稿日をJSTへ変換して翌日を計算する6件（月末・年末・閏年・UTC/JST境界含む）と暦の妥当性3件、計9/9が一致。式は `datetime.fromisoformat(posted_at).astimezone(JST).date() + timedelta(days=1)`、暦検査は `date(year, month, day)` のValueError。実行版はローカルPython 3.14.3であり、本番Python 3.12上の製品試験とは区別する。

これは受入テストの正解値の計算であり、製品の日時解決処理は未実装。手動ラベルの既存部品試験の不一致3件を解消した証拠にはしない。設計§17に意味契約と未実行の受入例14件を保存。今回の製品コード/DB/外部API変更は0。

GitHub読取: #3465はPR/Issueとも取得不可。#3456はHEAD 3c17a83ce61ba154c53ad664883df7e9d1d2a9e0、OPEN/CLEANを確認。承認対象の番号を推定していない。

## 保存・画面・配信の再照合（2026-09-13）

読取基点は設計ブランチ7cfcd94c33092067bb76890bceecd8a8609a6587。製品ファイルは変更していない。

- `migrations/20260906_120000_create_tcg_tables_t001.sql:350` 原文、同:388 抽出、同:410 analysis_resultsは抽出明細単位UNIQUE。販売枠の現在在庫を独立保持する構造ではない。
- `backend/app/services/tcg_line_import_svc.py:345` チャネルロック、同:370 原文重複照合、同:426 過去active全件無効化。商品単位の更新先を変えずに〆語句だけを増やす方法では目的を満たさない。
- `backend/app/routers/tcg_analysis_review.py:28` 原文抽出とsystemのレスポンス。`backend/app/services/tcg_analysis_review_svc.py:35` active原文限定、同:72 exclusion有無を要確認に使う。完売を正常な結果として保持するため接続改訂が必要。
- `frontend/src/features/tcg-analysis-review/ItemComparison.tsx:17` FinalSystemValueは数量をgemini.quantityから、stateをsystem.conditionから表示。商品状態と販売状態、抽出数量と反映数量は分離が必要。
- `backend/app/services/tcg_distribution_svc.py:183` 現行12列出力、同:229 active原文JOIN、同:239以降 品質条件。現在在庫への参照変更時も品質条件を維持する。単純なquantity条件の追加だけでは他商品消失を直せない。
- `backend/app/services/tcg_distribution_svc.py:464` clear→write。複数接続先で不変データを配ることと、各シートの途中失敗時の表示維持は別問題。外部APIの安全な公開方式は未調査として残す。

design §18に追加4テーブルの列/制約案、更新順序、stock_effectsの配列レスポンス、12列配信との境界、未実行の受入条件8項目を保存。設計案の生成は実装検証ではない。自己審査REVISE。次は抽出/手動解決/履歴互換/配信公開・初期化の未確定契約を実物と照合する。

## 配信失敗の模擬実行と公式仕様確認（2026-09-13）

基点c10f26f505b588140048000752b384a70bff4e05。`backend/app/services/tcg_distribution_svc.py:412` の_write_to_target_syncだけをAST抽出し、認証/worksheetを模擬化して実行。成功とappend失敗の2件ともclear→appendの順。後者はstatus=error、残存0行。実Google/DB操作0。コードhashと結果は [probe-20260913.json](probe-20260913.json) sheet_write_failure_probe。これは現行の呼出順の反例で、新公開方式の試験合格ではない。

Context7ツールなしを確認し、ユーザー指定の公式資料代替を使用。確認日2026-09-13。Google Sheets [batchUpdate](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/batchUpdate)は同じspreadsheets内の更新を原子的に適用するが共同編集結果の一致を保証しない。[UpdateCellsRequest](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/request#UpdateCellsRequest)のrange/fieldsにより新データ未被覆の旧セル値を除去可能。[利用上限](https://developers.google.com/workspace/sheets/api/limits)は推奨2MBと処理180秒、指数backoffを記載。これらはAPIの仕様根拠であり外部企業の成功率・性能実測ではない。

`backend/app/routers/tcg_analysis_review.py:94` はrequire_super_admin。手動解決API案も同じ権限に限定。`backend/app/services/tcg_distribution_svc.py:39` の5000行と同:448のタブ作成禁止を設計に維持。影響範囲は設計§19〜21、公開/手動解決/初期化の契約案。製品コード変更0、外部送信0。

## 抽出版・原文表示・テナント設定の照合（2026-09-13）

固定基点9858b29c4210b653aec22d85d5eda32cdc826b40。
`backend/app/services/gemini_extraction_svc.py:35` と同ファイルのWORK_ID_PROMPT_TEXTの既存v3/v4は原文欄と作品IDを分離。parse_extraction_responseはv2/v3/v4の7/9/10列に対応し、新しい根拠位置JSONは未対応。`backend/app/tasks/tcg_extraction.py:165` 以降は外部呼出し後の作品参照変更を検査してから原文欄を保存する。この制約をv5でも維持する。

`frontend/src/features/tcg-analysis-review/SupplierDetailView.tsx:60` 付近はsupplier/sourceから原文1件、同:67はstrip_raw_text=trueの明細一覧を取得。履歴を増やすだけでは過去行が最新原文を参照するため、メッセージID別取得が必要。`backend/app/routers/tcg_supplier_quality.py:78` は仕入元ID単位のsourceエンドポイント。`backend/app/services/tcg_analysis_review_svc.py:216` の並び順はreceived_atとline_start。履歴版選択と同一日時の安定順を別途定義した。

`backend/app/tcg_config.py:19` 以降はTCG_SCHEMAを環境設定から検証して読む（既定tenant_004）。説明コメントだけで固定スキーマと断定しない。`migrations/20260912_020000_tcg_resolved_work_id.sql:6` は既存TCGテーブルを持つtenant_*を列挙。新migrationの対象manifestと前提検査が必要。

設計§22〜24でv5/履歴/API既定値/制約を具体化。v5は提案であり、製品テスト実行0・精度測定0。FK保持による既存削除経路への影響、原文チャネル変更とイベント整合が未照合のためREVISE。

## 解析再実行と既存テストの追加照合（2026-09-13）

`backend/tests/test_tcg_is_active_filter.py:75` の対象3サービスと同:86の全SQL active強制は履歴scopeと衝突する。テスト撤去ではなく結果集合と重複防止に置換する設計対象へ追加。`backend/app/services/tcg_supplier_quality_svc.py:35` 付近のexclusion要確認集計と同:70付近のsupplier_id=SPコードも確認した。新API案のUUID絞込をsupplier_codeへ修正した。

`backend/app/services/tcg_analyzer_svc.py:1307` はanalysis_resultsをextraction_item_idでUPSERT。`backend/app/services/tcg_product_master_svc.py:638` 付近の再解析は同じjobへanalyze_extraction_jobを再実行するため、抽出IDのみではマスタ変更後の版を識別できない。適用時の不変結果、analysis_input_digest、差分保留を設計に追加した。

読み取り検索のコマンドに削除SQLの文字列が含まれたためPreToolUseが拒否。削除実行0、ガード変更0。テーブル参照ファイルの読み取りを継続した。backend/app、tools、ops、scripts内の参照を調査し、常設の抽出処理はINSERT/job状態更新、原文取込はactive更新、再解析はUPSERTであることを確認。任意の過去運用や外部の削除まで不存在とは断定しない。migrationのFK影響と履歴保持試験は残件。

## 発送枠13件の手動参照ラベルと数量部品試験（2026-09-13）

固定コードcf1e35946f0fb25f5efbded6fefedc7587bb9549。原文Aのhashはf88a6a7c193b6c178dad7ba8104ffffd9b7cd46b52b6afefef33a860fb4e61a3で従前と一致。A31111〜31127、A90251〜90253、A90254〜90269の3投稿から13枠を手動ラベル化。区間hash・行番号・数量/単位/完売/予定ラベルはprobe JSONのshipping_slot_reference_labels。完売4、正数量9、正数量で単位なし6、追加可能性2。商品ID/現在在庫との結合は未確認であり推定しない。

`backend/app/services/tcg_analyzer_svc.py:787` の数値変換関数をASTで隔離実行。入力5件中期待一致2、不一致3。「10→残3」を103.0へ変換し、「①」「残①カートン」をNoneとした。5件の詳細とコードhashはprobe JSONのnumeric_boundary_probe。既存関数は同:1232の数量解析で使用される。実際のGemini出力や本番の誤り率は測定していない。

全backend/appのSQLを集計する読み取りハーネスはPreToolUseに拒否され、実行していない。拒否理由は不可逆SQL語句、解除/許可スクリプト実行0。限定した常設コードの読取結果と、広範な監査未完了を区別する。

## 追加実例と参照文字列の全ファイル読取（2026-09-13）

基点4879b9039fbbb067861b6c4db868708fec095b58。backend/app Python245ファイルのASTから対象テーブル名を含む文字列73件を収集、構文エラー0。SQL実行なし。内訳はSELECT35/UPDATE9/INSERT5/FROM1、残り説明文等。対象と範囲の限界はprobe JSON runtime_table_reference_audit。全ての動的SQL/外部運用を監査したとはしない。

`backend/app/services/item_corrections_svc.py:63` は商品IDをanalysis_resultsへ直接更新。`backend/app/services/tcg_unit_recovery_svc.py:868`、同:986、同:1056、同:1170は後段で単位/状態等を更新。`backend/app/services/tcg_diagnostics_svc.py:212` はerror jobをpendingへ戻す。`backend/app/services/tcg_line_import_svc.py:430` は原文active更新。再解析の入力版に加えて最終解析結果の版が必要と判断し、design §26へ接続補正を記録。

原文Bの3投稿8枠を追加参照例として保存。行範囲B529960〜529970/B533930〜533941/B543172〜543180。従来参照17投稿の全文hashと新3投稿の一致0。類似文/送信者分離は未検証。商品単位の完売が他単位へ伝播してはいけない実例と、セット数量を構成商品へ複製してはいけない実例を含む。手動ラベルでありモデル評価0。

## snapshot読取と列定義の統合（2026-09-13）

Context7利用不可のため、許可された公式資料代替で [PostgreSQL 16の分離レベル](https://www.postgresql.org/docs/16/transaction-iso.html) と [制約](https://www.postgresql.org/docs/16/ddl-constraints.html) を直接確認。複数SELECTを同じ読取版へ固定する必要、NULLを含むCHECKとNOT NULLの区別を設計§27へ反映。外部・過去導入事例の成功率ではなく仕様根拠。DB接続・SQL実行0。

4新表と2既存表の追加列、配信予約、共通入口6経路を統合。各サービスの個別トランザクションの後に接続し、解析書込から逆順ロックへ入らない契約とした。状態遷移とsnapshotの厳密項目は最終設計残件、実装後試験と分けて記録した。

## 最終査定の最新main照合（2026-09-13）

fetch後のorigin/mainはaf269ae20ed2f52e6cd49ba0403ad7799e3a3870。専用設計作業台の基準644bf9a4から差分を読取確認。通常fetchはFETCH_HEADの書込権限で失敗し、許可済みGit参照更新の範囲で昇格実行が成功した。製品ファイルは変更していない。

- backend/app/services/tcg_work_reference.py:12のWORK_ID_PROMPT_VERSIONSはv4-work-id-p1/p2を保持。backend/app/services/tcg_analyzer_svc.pyとbackend/app/tasks/tcg_extraction.pyは集合所属で判定する。将来v5接続時も両既存版を保持する。
- backend/app/services/tcg_line_import_svc.py:571とbackend/app/routers/tcg_line_import.py:610にAndroid固有のline_source_names照合が追加された。複数原文保存の接続時に旧resolve_suppliersだけへ巻き戻さない。
- backend/app/services/gemini_extraction_svc.pyの最新差分はv4根拠範囲の書式指示と、原文を含めないエラー情報。本便は当該既存関数を編集せず新規の検証部品を作る計画。
- backend/app/__init__.pyはpackageコメントだけ、services/__init__.pyは空。第1便は標準ライブラリだけの新規モジュールとし、unittestによる部品試験でDB接続を要求しない。全pytestは別のDocker必須検証。

全体の正式査定で現在在庫/切替/意味変更時の解決操作の記述不足を残した。第1便の純粋部品はこの未解決に依存せず、変更ファイル4件と6試験群をdesign §15へ固定した。実装/モデル呼出/DB操作0。

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
