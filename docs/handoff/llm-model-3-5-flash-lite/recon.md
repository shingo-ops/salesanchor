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
