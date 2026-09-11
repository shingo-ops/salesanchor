# 提供終了モデルによる翻訳・在庫解析の失敗 recon（2026-09-07）

対象: 本番（tenant_004 を含む全テナント共通の LLM 呼び出し）。調査は読み取りのみ。

## 1. 症状

Celery worker のログに、翻訳処理が 404 で失敗し続ける記録が多数ある。
エラー文は models/gemini-2.5-flash が新規利用者に提供終了であり
models/gemini-3.6-flash を使うよう促す内容。翻訳は成立していない。

## 2. 確定した事実

- 翻訳の既定モデルは環境変数で上書き可能だが、本番の celery worker と backend の
  どちらにも TRANSLATION_MODEL_RECEIVE / TRANSLATION_MODEL_SEND は設定されていない
  （2026-09-07 実測。printenv の出力が 0 件）。よってコードの既定値が使われている。
- 既定値は `backend/app/services/message_translator.py:40` が gemini-2.5-flash、
  `backend/app/services/message_translator.py:41` が gemini-2.5-flash-lite。
- 在庫解析も同じ系のモデルを直書きしている:
  `backend/app/services/inventory_parser_llm.py:89` と
  `backend/app/services/inventory_parser_llm.py:225`。
- 価格表は `backend/app/services/llm_budget.py:53` の LLM_PRICING に 2.5 系 3 件のみ。
  未知のモデル名を渡すと `backend/app/services/llm_budget.py:130` で ValueError を送出する。
  よってモデル名だけ変えるとコスト記録が落ちる。
- TCG 抽出は別系統で `backend/app/services/gemini_extraction_svc.py:126` が
  gemini-3.6-flash を指定しており、こちらは動作している。
- 本番の API キーで利用可能なモデル一覧を実測し、gemini-3.5-flash-lite が
  利用可能であることを確認した（2026-09-07）。
- 正本 `docs/adr/ADR-110-sa-translation-subsystem.md:139` の表も 2.5 系のまま。

## 3. 決定事項（PO 合意、2026-09-07）

- 翻訳・在庫解析とも gemini-3.5-flash-lite を使う。
- 対応は 2 段に分ける。第 1 段は本件（404 の止血）。
  第 2 段はモデル名の SSOT 化（用途とモデルと価格を 1 箇所に集約する）。

## 4. 未確認・要実測

- gemini-3.5-flash-lite の料金は公開情報の参照値であり、請求実績で裏を取っていない。
- 送信英訳に Flash-Lite を使うことによる訳質の変化。
- TCG 抽出（gemini-3.6-flash）を将来どう扱うか。


## 2026-09-11 在庫補助解析2.5 LiteへのPO変更依頼

基点eefa9143。既定モデルはinventory_parser_llm.py:91,227の3.5 Lite。呼出側inventory_parser.py:1034は結果modelを予算計算へ渡す。llm_budget.py:67に2.5 Liteの単価登録済み。翻訳とTCG抽出は別用途。POはレガシーで2.5 Liteの精度を確保できたと報告し、変更を明示依頼。モデル比較の実測や現行精度合格を創作しない。設計追補の限定契約を自己審査APPROVE。ローカルDocker不在のためpytestはCIで確認する。PR3422のGOを本便へ流用しない。

実装追補: 既定モデル2箇所を変更し、SDK指定と結果model・料金0.50USD/各100万tokenの既存試験を更新。実APIテストは結果modelで費用算出。対象ruff成功、既存テストimport指摘を整理して再検査。台帳/diff検査成功。Docker不在でローカルpytest未実行。生報告/tmp/reports/LITE25-VERIFY-02.txt。製品差分自己レビュー済み、独立レビューではない。実API・現行精度・本番反映未検証。

在庫補助解析2.5 Lite変更はcommit be42f18e、PR #3425へ提出済み（https://github.com/shingo-ops/salesanchor/pull/3425）。CI確認中・GO未受領・本番未反映。PR3422のUI変更とは別便。報告/tmp/reports/LITE25-PR-01.txt。


最終検証（2026-09-11）: PR #3425 head e60f555e、backend job103106398328は2543成功/94skip。ただし実API試験がrequested model unavailableとしてskipしたことをwarning生ログで直接確認（404または提供不可文字列の既存判定）。2.5 Liteが現在のCIキーで利用できたとは扱わない。ログ/tmp/reports/LITE25-PYTEST-SKIP-EVIDENCE.log、結果LITE25-FINAL-02.json。実装・理由記録は完了、本番未反映。運用採用はREVISE: 対象プロジェクトでの提供可否解決が必要。旧環境の利用実績は現在のキーでの提供を保証しない。GO未受領。停止記録の文書commitは再CIを避けローカル保存、PR本文にも同内容を保存する。


## 2026-09-11 現在のCI接続の拒否理由を直接確認

PR #3425 head 5fa171b86638e59e433d5c4e6e08a501aaab031f、Backend Tests run34550427274/job103112026495を直接取得。固定ラベル診断は new_users=True / no_longer_available=True / http_404=True / not_found=False / unsupported_method=False / api_v1beta=False。Google呼出しの例外に新規ユーザー向け提供終了の文言が含まれることを確認。従来の一括skip表示からの推測とは区別する。全文は秘密値漏洩防止のため出力していない。

実行結果2543passed・94skipped・303warnings、92.62秒。対象実API試験はskipであり、2.5 Liteによる解析成功や精度合格ではない。本番キーの利用可否・CIキーと本番キーの一致・Googleが新規利用者を判定する具体単位/解除条件は未確認。APIバージョン変更やSDK移行で解決すると断定しない。

Google公式 https://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash-lite は安定版IDとStructured outputs対応を掲載。https://ai.google.dev/gemini-api/docs/deprecations は安定版の終了日未発表、preview-09-2025の終了2026-03-31を掲載。確認日2026-09-11。Context7ツールは利用不可、PO起動指示の代替許可により公式資料を直接参照。これらの公開資料は個別キーの利用を保証しない。

診断追加commit2be4c372。CI開始前にmain5de8afa1との根拠台帳追記競合を双方保持して5fa171b8へ統合。本文に残る「停止記録commitはローカル保存」は前時点の記録であり、今回4cf66482もpush済み。製品コード・CI設定・secrets・本番は今回変更なし。診断は実API試験の固定警告のみ、判定と呼出回数は不変。PR未マージ、GO #3425未受領、運用採用REVISE継続。

生ログ /tmp/reports/LITE25-ERROR-DIAGNOSTIC-CI.log、SHA256 0a1c1a6223e8c09f929ada43c8c407a02983974073dfce2e77d48061169b4891。GitHub https://github.com/shingo-ops/salesanchor/actions/runs/34550427274/job/103112026495 。次の確認は本番接続の提供可否と対象プロジェクトの利用条件。レガシー調査は旧利用権の比較材料であり、現接続の診断に必須ではない。キー交換・Google再認証・追加課金は実施していない。


## 2026-09-11 3.1 Flash-Liteとレガシーキーへの変更契約

PO原文「じゃあ3.1に変更して、キーもレガシーに差し替え」。直前の2.5採用契約は本追補で置き換える。2.5はCIキーとPO提供レガシーキーで404・新規ユーザー向け提供終了の文言を実測。3.1 LiteはレガシーキーでHTTP200、JSON期待値一致、入力8/出力9tokenを実測。共有キー利用の3.5 Lite（翻訳）と3.6 Flash（TCG抽出）も各1回HTTP200・非空応答。単純な接続検証であり在庫解析や翻訳精度の合格ではない。報告: /tmp/reports/LITE25-LEGACY-KEY-PROBE-02.json、LITE31-LEGACY-KEY-PROBE-01.json、LITE31-SHARED-KEY-CHECK-01.json。

Why: 利用不可の2.5に代えて利用できた3.1を選ぶ。通常のテキスト入力/出力単価は100万token当たり0.25/1.50USD（Google公式 https://ai.google.dev/gemini-api/docs/pricing 、2026-09-11確認、Context7利用不可のため許可済み公式代替）。3.5の0.30/2.50より同token数なら入力約16.7%・出力40%低い。実請求額・無料/有料契約状態・実在庫精度は未確認。外部導入事例は本選択の証明に不要。

実装: inventory_parser_llm.pyの既定2箇所と関連テストをgemini-3.1-flash-liteへ変更。llm_budget.pyへ3.1のテキスト単価を追加し、入力100万=0.25・出力100万=1.50・合計1.75を既存parser試験で検証する。共有DEFAULT_MODEL、翻訳/TCGのモデル名、prompt、JSON schema、予算上限、DB、CI設定は維持。

キー: ADR-075に従い既存GitHub Actions repository secret GEMINI_API_KEYのみをPO提供値へ更新する。キーは標準入力で渡し値をログ・引数・文書に出さない。更新時刻を読み取り、後続CIの実API試験がskipでなく成功することを確認。deploy.yml:245が同Secretを本番へ展開するため、本番適用は正規デプロイ時に起きる。現キーはGitHubから読み戻せず、旧値への復元材料は本調査では確保していない。旧Googleキー自体を削除・失効させない。更新承認は上記PO原文、PRマージのGO #3425を創作しない。

| 基準 | 検証方法 |
|---|---|
| 在庫既定呼出・返却modelが3.1 Lite | 既存モックとCI実APIテスト |
| 入出力別の費用と合計が正しい | 既存費用連携assert3件 |
| 共有キー利用機能が接続可能 | 3.5 Lite/3.6 Flashへの固定入力各1回HTTP200実測済み |
| 新キーで既存解析経路が成立 | CI実APIテスト、skipを成功に数えない |
| 本番反映の状態を区別 | Secret更新とPRマージとdeploy成功を別記録 |

代替: 3.5継続より単価が低く、2.5は今回拒否されたため不採用。リスクは共有キーの利用量・課金先が変わること、実データ精度/上限が未検証なこと。失敗時に既存ルール解析へ戻る挙動は維持。モデルのロールバックは別PR、キー復元には旧値を安全に再取得する必要がある。新規の秘密管理やCIを追加しない。守り手は既存parser/budget試験と本recon。

同一AIによる自己審査APPROVE（この限定実装契約）。正確な既定値2箇所・料金追加・既存試験・正規Secret更新経路を確認済み。独立レビュー、現行在庫精度の合格、GO #3425、本番反映完了を意味しない。


実装追補: 3.1既定2箇所・単価追加・費用assert3件を反映、対象4Pythonのruffとdiff検査成功。GitHub GEMINI_API_KEY更新操作exit0、updatedAt=2026-09-11T01:45:14Zを直接確認。生報告/tmp/reports/LITE31-KEY-SWAP-01.txt。次回以降のdeployで本番へ展開される経路であり、本番反映は未確認。CIは新キーで検証予定、GO #3425未受領。


## 2026-09-11 3.1変更・新キーのCI検証結果

PR #3425の製品head e606ce4fad444331677d34852b7a61cca06d95f0を検証。Backend Tests run34552094629/job103116973038は2544passed・93skipped・302warnings（91.84秒）。従前2543passed/94skippedに対して成功1増・skip1減で、既存実API試験のモデル不可/認証不可等の固定skip警告は0。モデル/費用・既存全試験のCI成功と、実データ精度の未検証を区別する。生ログ/tmp/reports/LITE31-PYTEST-01.log、SHA256 837725e72484fe4eb4e17bb1123f465a83fce6b98471f3f0669424fc461702ee。

PR全チェック34success/8skipped/1failure。唯一の失敗process-artifacts gate job103116955933はGO記録セクション欠落を明示。コード品質の検査失敗ではない。新たなGO #3425は未受領。GitHub Secret更新完了、製品コードはPR提出済み、本番モデル変更と本番キー反映は未確認。PRマージ・本番デプロイは本便未実施。差分の自己レビュー済み、独立レビューではない。次の一手はPOのGO #3425受領後に正式な記録・最新チェック・マージ/デプロイ確認。

この検証後追記は不要な再API実行を避け文書だけのローカルcommitで保持し、同内容をPR本文にも保存する。GO受領後の次便で文書commitもpushする。現行PR検証結果と未push文書を混同しない。
