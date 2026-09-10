---
mode: handoff
---

# 設計 — ガード変更の評価ゲート（限定版v1）

**対象ADR**: ADR-113、ADR-121、ADR-135
**recon**: docs/handoff/design-partner-card-ops/guard-authoring-recon.md
**日付**: 2026-09-10
**区分**: 既存カード運用の延長。設置フェーズと必須化フェーズを分ける。

## 目的・対象と対象外

ガード変更の前に、正常な作業への弊害、代替案、解除と維持方法を評価する。画面・商品機能の変更は0件。
POの6件の自律整備指示に基づく実装案。適用範囲の個別選択や番号付きGOを代筆しない。
今回のguards/card-lintから始め、全CIや全運用スクリプトを評価対象にする案は採らない。
対象外: 本番・DB・secrets変更、既存process-artifactsの変更、既存GO運用変更、攻撃者としてのrepo書込権限者への完全防御。

## 外部・過去事例の参照と我々への応用

外部導入事例は不要。自社の成功終了5箇所（recon引用）と公式API仕様、実Gitを使う試験が直接の根拠。
試作の最終67検査が成功、失敗0・skip0、25.98秒。これは手元の試作でありGitHub実行ではない。
成功証跡: /tmp/reports/GUARD-EVAL-PROTOTYPE-04.log。初回56/57は試験側の存在しない角かっこ付きpathの判定誤りで、git rev-parse --verifyへ直して再検証した。
Context7は利用不可。POが許可した公式資料の直接参照で代替した（reconに出典・日付）。

## 変更前後と代替案

前: guards変更は通常文書として既存CIからスキップされ得る。評価・読んだ版の記録を確認する専用結果はない。
後: 専用結果guard-authoring/evaluationが、変更blob・読書blob・評価・検証記録を照合する。
既存process-artifacts全体をmain必須にすると、本件以外の既存検査まで新しく強制されるため不採用。
既存スクリプトの途中へ追加する案は、早期終了の経路を取りこぼすため不採用。
PR側の変更済みvalidatorを権限付きで実行する案は、自分の検査を外せるため不採用。

## 固定対象

- docs/handoff/design-partner-card-ops/guards.md と guards/ 以下。
- scripts/card-lint.sh、scripts/tests/card-lint/ 以下。
- scripts/check-guard-evaluations.js、scripts/run-guard-evaluation.js、scripts/tests/test-guard-evaluations.js。
- .github/workflows/guard-authoring-gate.yml。
- 本書とguard-authoring-recon.md。

追加・変更・削除をすべて検査。rename検出を無効にしたgit差分で移動を削除＋追加として扱う。
判定する対象範囲はmain版のコードに固定する。範囲を増減するPRも、変更前の規則で評価する。
評価JSONと試験ログは対象変更の証跡であり、更なる評価を要求する再帰対象にしない。
対象が0件なら追加評価なしでpass。評価履歴だけの編集は、このv1の強制対象外。

## JSON契約

保存先はguard-evaluations/直下、英数字・ハイフン・アンダースコアの名前のJSON。一つのPR差分に変更JSONは一つ。

| 項目 | 必須条件 |
|---|---|
| version | 1 |
| base_commit | 評価対象のmain完全SHAと一致 |
| changes | 全対象pathを過不足なく一度ずつ。old_blob/new_blobは実blobと一致、不存在側はnull |
| reads | guards.md・00-common・11-lint・12-authoringと変更するguards文書。path/ref/blobが実物と一致 |
| assessment | purpose、impact、false_positives、future_costs、alternatives、decision、rollback、owner、normal_example、violation_exampleが非空 |
| verification.kind | 文書のみはdocumentation、コード/workflow/試験変更はlogic |
| documentation | 機械試験不要のreasonが非空 |
| logic | normal/negative各々にcommand、expected_exit、actual_exit、report_path、report_blob |
| 試験ログ | guard-evaluations/内のGit管理された非空txt/log/md。終了値は0〜255の整数で期待と実際が一致 |

読む版はbaseがあるときbase、新設文書のみhead。headの完全SHAをJSONへ自己参照させず、変更ファイルのblobを照合する。
ロジック試験の否定例は、拒否をassertする試験プログラムの成功（終了0）として記録してよい。正常/否定を一度の試験で実行した場合、同じ実ログを両欄から参照できる。
機械はコマンドを再実行せず、読了・評価・報告内容の真実性を証明しない。内容確認はレビュー担当の責務。
評価入力1ファイルは1MiB以下、git出力は16MiB以下。不正JSON・symlinkへの変更・解釈不能は停止する。極端に大きい変更は分割する。

### 入力ミスを減らすmanifest

base版のcheck-guard-evaluations.jsを一時ファイルへ取り出し、--manifest base完全SHA head完全SHAで測定値を生成する。
変更したhead版の規則でmanifestを作ると、対象範囲変更時にmain側の判定とずれるため使わない。
生成物のassessmentと試験理由/結果は空であり、採否やGOを自動生成しない。変更者が実測を記入する。
初回設置はbaseに検査器がないため新規版を用い、人手レビュー・試験で照合する。

## GitHub実行契約と全経路

pull_request側のunit jobは対象path変更時のみ、contents:readでPRコードを試験する。
pull_request_target側はmain向けopened/reopened/synchronize/ready_for_reviewを常時受け、path filterを置かない。
mainのgithub.shaをcheckoutし、Node24のmain版runnerだけを実行する。PRのheadはgit objectとしてfetchするだけでcheckout・import・buildしない。
権限はcontents:read、pull-requests:read、statuses:write。追加secret不要。cacheは無効、外部actionsは確認したcommitへ固定。
同PR・同イベント種別を直列化し、実行中cancelはしない。

1. APIから現在のopen/main PRのhead/baseを取得。番号は正の整数、SHAは40桁hex。
2. checkoutがAPI baseと違う古い実行は採用しない。
3. 検査対象headへpendingを送る。baseがhead祖先でなければerror（既存strict条件と一致）。
4. 対象0件はsuccess。対象ありは評価を照合しsuccess/failure。fetch等の実行障害はerror。
5. 再取得したPRのhead/base/stateが変わっていたら古い最終判定を送らない。
6. 検査後のhead更新には旧SHAのsuccessが使えない。base更新は既存strict保護で追従を要求する。

対象外PR、閉鎖PR、古いbase、検証失敗、API失敗、head/base更新を試験する。
API送信後の通信障害では、状態が届いたかを推測しない。GitHubの対象SHAを再確認する。

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 通常のdocs/frontend/backend変更を評価なしで通す | 対象外3正常例 |
| guard追加・変更・削除・移動で評価欠落を拒否 | 実Git差分を作る否定試験 |
| 旧/新blob、読み取り版、baseの不一致を拒否 | 各フィールドを変える試験 |
| 正常/否定の実行記録欠落・終了値不一致を拒否 | ロジック変更の証跡試験 |
| 検査自身を削除して素通りしない | validator/runner/test/workflowの削除試験 |
| PR内容を権限付きで実行しない | headの副作用コードが未実行、shallow cloneのHEAD不変 |
| 更新前の成功を別headへ送らない | APIスタブのhead/base変更と送信先SHA照合 |
| 評価の採否やGOを生成しない | manifestの空欄と未記入拒否試験 |
| 設置後の実イベントで同じ結果になる | 試行PRで正常/欠落/自己変更/HEAD更新を確認（未実施） |
| mainで欠落・失敗を必ず待機させる | 管理者による限定context追加後の試行PR（未実施） |

## 弊害・トレードオフと導入順

ガードの表記修正にも評価が必要になる。文書のみは実行試験不要の理由を記し、入力値の機械生成で記録の負担を抑える。
main前進時に評価を再確認する手間は増えるが、古い読み取り・採否を使い回さないため必要。
新しい必須結果は、障害時に通常PRも待たせ得る。先に未必須で試行し、動作確認と管理者判断の後に追加する。
既存12必須チェックを保持し、process-artifacts全体を追加しない。新contextだけを対象にする。

設置フェーズ: 本PRの単体試験・書類確認・既存CIと正式GOを満たしてmainへ入れる。この時点は設置済み・必須化未完了。
検証フェーズ: 試行PRの正常/拒否・SHA更新・状態の発行Appを実測する。検証用PRを製品変更へ混ぜず、終了時に閉じる。
必須化フェーズ: PO/管理者が現在設定と例外を確認し、既存必須を保ったまま当該contextのみ追加。正常/拒否を再検証して完了とする。
現接続はadmin=false・maintain=false、rulesetのbypass_actorsは返却されていない。完全な設定や例外なしを推測せず、設定変更は行わない。

同じGitHub Actions主体を使う別workflowからの状態偽装まで防ぐ専用App運用は、本v1の保証外。専用主体は別のGOフロー設計と混同しない。
解除時も評価とPO判断が必要。誤検知なら評価/実装を修正し、廃止なら限定contextの解除を先に管理者が行い、その後に評価付きでコードを撤去する。

## 維持の仕組み

- 守り手: scripts/check-guard-evaluations.js、scripts/tests/test-guard-evaluations.js。
- 維持担当: guards/検査の変更者。レビュー担当は採否と証跡の内容を確認。PO/管理者が強制設定と解除を判断する。
- 監視: guard-authoring/evaluationの対象SHAと実ログ。失敗・未報告を緑と扱わない。
- 仕様を変える場合はbase版の評価規則と正常/否定試験を通す。

## 自己審査と状態

設置フェーズはAPPROVE（2026-09-10、同一AIによるPlanner→Architectの自己審査）。独立した第二者レビューではない。
根拠: 実物の早期終了5箇所、公式API契約、67件の試作試験、PRコード非実行とSHA比較を含む実Git試験。
この合格はPO個別GO・マージ・必須化承認を兼ねない。必須化フェーズはREVISE: 実イベント/App/例外設定/管理者変更/強制試行が未了。
設置PRと証跡をレビュー可能にした後、正式GOを確認する。未実施を完了へ読み替えない。

### 設置実装の手元検証（2026-09-10）

実ファイル配置後も67成功・失敗0・skip0、24.77秒。試験ログはguard-evaluations/20260910-install-tests.txt。YAML構文・権限・main checkout・action固定SHA・cache無効を確認。設計形式・引用先・維持欄と台帳構造検査は成功。CI実行と実イベントは未実施。
Node24はこの専用workflow内だけで指定し、既存process-artifactsのNode22は変更しない。手元のNode24.12.0と新workflowの同一majorで検証する。
