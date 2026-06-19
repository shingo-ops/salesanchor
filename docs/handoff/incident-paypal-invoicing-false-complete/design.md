# design: PayPal請求書発行 虚偽完了報告インシデント 再発防止

**仕事名**: incident-paypal-invoicing-false-complete
**作成**: Planner（Web Claude）
**実装**: Generator（Claude Code）
**参照 recon**: docs/handoff/incident-paypal-invoicing-false-complete/recon.md
**対象 ADR**: ADR-1000（本インシデントのADR）。関連既存ADR: ADR-051（claude-pipeline 自動化）/ ADR-121（process-artifacts gate）/ ADR-135（develop 常時出荷可能）/ ADR-136（危険変更0承認マージ防止・認可承認者の承認必須ロジック）/ ADR-112（設計起点フロー v2）/ ADR-012（ブランチ運用）/ ADR-124（sop-health-reporter）
**ステータス**: PO承認済み（KGI承認ゲート通過 2026-06-18）
**日付**: 2026-06-18
**正本**: docs/STANDARD-WORKFLOW.md。矛盾時は正本優先。

---

## 外部・過去事例の参照と我々への応用

- **過去事例1: ADR-136 / PR #2063（2026-06-12）** — 危険変更を含むのに承認ゼロでマージされた事故。check-process-artifacts.js:398 の !hasAuth ブランチが runFullCheck にフォールスルーし、書類が揃っていればgateを通過してしまう実装バグが原因。「書類の存在チェックは、動作・承認の実在を保証しない」という今回の穴3と同じ構造。**このADRで導入した「認可承認者の PR Approve が無ければ gate FAIL」のロジックを、本設計の人間確認必須化（PR-E）に流用する。**
- **過去事例2: ADR-135 / #1981（2026-06-12）** — develop に PR レビュー必須がなく、危険変更がセルフマージで本番手前まで到達。人間レビュー必須化を Ruleset（require_code_owner_review）で試みたが GitHub 仕様上不成立（required_approving_review_count=0 だと review 要求が生成されない）。→ **本設計でも「人間確認を必須にする」が、Ruleset 方式ではなく gate 方式で実現する（PR-E）。**
- **過去事例3: FedEx スモークテストの休止（今回 recon R6）** — test_fedex_sandbox.py は存在するが CI secrets 未登録で常時 SKIP（=緑扱い）。「テストを書いても起動・実行されなければ無いのと同じ」という、穴1・穴2と同じ教訓の先行例。→ 本設計では「secrets 未登録時は SKIP ではなく FAIL」を原則化（KGI-4）。
- **外部事例: 契約テスト/スモークテストのベストプラクティス** — 速度のため外部APIをモックするのは一般的だが、実APIの疎通を保証するには別途「実エンドポイントを最小限叩くスモーク」を用意するのが定石（モックは実APIの破壊を検知できない）。今回 R2 で「PayPal テスト6本すべてモックのみ」が確定したため、この定石に従い実Sandboxスモークを新設する。
- **外部事例: 多層防御（defense in depth）** — 単一の砦に依存せず、独立した複数の関門を直列に置く考え方。今回の核心（§設計思想）はこれに沿う。人間を唯一の砦にした結果が今回の事故であり、機械の関門を一次に、人間を最終に置く。

---

## 設計思想：二重防御と順序（PO採用 2026-06-18）

壊れたコードが本番に到達する経路を、**機械と人間の二重**で塞ぐ。**順序が決定的**：機械を一次防御（人間がサボっても効く）、人間を最終確認（機械が判定できない範囲）に置く。

今回の事故は人間（morimoto）を"唯一の砦"に置き、その人間が動作確認をサボった結果だった。機械を一次に置けば、人間がサボっても機械が壊れたコードを止める。その上で、機械が判定できない範囲（見た目・業務妥当性・本番固有の懸念）を人間が最終確認する。この順序だからこそ両方が意味を持つ。

**防御層（上から順に通過しないと先へ進めない）**：

| 層 | 担い手 | タイミング | 内容 |
|---|---|---|---|
| 1 | 機械 | マージ前 | 実Sandboxスモーク必須。実際に叩いて緑でないとマージ不可 ← **壊れたコードをマージさせない主役** |
| 2 | 人間 | マージ前 | 認可承認者（Shingo/Suttan）の承認必須。承認なしはマージ不可（gate方式・ADR-136流用） |
| 3 | 機械 | デプロイ前 | 本番相当環境（docker-compose）での素振り。環境差バグを事前検出 |
| 4 | 人間 | デプロイ時 | 本番での実操作による最終確認（実発行・業務妥当性判断）。証拠を残す |
| 5 | 機械 | デプロイ後 | 自動ヘルスチェック ＋ 異常時の自動ロールバック |

> 人間の確認（層2・層4）は**「証拠を残す」**（実行結果・スクリーンショットをPR/記録に添付）。単なる自己申告チェックは今回の再来になるため不可。
> **正直な限界**：「承認者・確認者が本当に確認したか」は機械で強制できない（空判子リスク）。だから機械の層（1・3・5）を主防御に置き、人間の層（2・4）はその上の最終確認とする。

---

## KGI（成功条件・PO承認済み 2026-06-18）

**狙い（PO 2026-06-18 確定）**：人間の動作確認漏れ・うっかりに起因する「未確認のまま通過」を仕組みで最小化する。Sandboxであっても実際にAPIを起動・呼び出して正常応答を確認できない限りマージを通さない。さらに本番でも、機械の素振り・ヘルス・自動ロールバックと、人間の証拠付き最終確認の二重で壊れたコードの稼働を防ぐ。目標は「人間起因ミスのリスク最小化」であり「あらゆる不具合流出のゼロ化」ではない。

| # | KGI | 検証方法 |
|---|------|---------|
| KGI-1 | 外部APIを叩くコードを変更したPRは、**実Sandboxで実際にAPIを起動・呼び出し正常応答を確認するスモークが成功しない限りマージできない** | 故意に実装を壊すとスモークが FAIL し、マージ不可になることを確認（負のテスト） |
| KGI-2 | 上記スモークの起動がブランチ名に依存しない（feature/morimoto/*（CLAUDE.md:70）でも起動） | 当該ブランチのPRでスモークjob起動をCIログ確認。起動率 0%→100% |
| KGI-3 | 「外部APIを叩くコード変更」の検出が**人間の手動登録に依存しない**。スモーク未用意・未実行のPRは gate が FAIL | スモーク未用意PRで gate FAIL を確認（負のテスト） |
| KGI-4 | スモークの認証情報（secrets）が未登録のとき SKIP（緑）ではなく FAIL | secrets を外した状態でCI赤を確認 |
| KGI-5 | 外部API連携PRは、**認可承認者（Shingo/Suttan）の承認が無ければマージできない**（人間確認・マージ前） | 承認なしPRで gate FAIL を確認 |
| KGI-6 | 本番デプロイは、**本番相当環境での素振り（機械）＋ 人間の証拠付き最終動作確認**なしに完了としない | デプロイ手順に両者が必須ステップとして組み込まれていることを確認 |
| KGI-7 | 本番デプロイ後、ヘルス異常時に**自動ロールバック**する | 異常を注入してロールバック発火を確認 |
| KGI-8 | 完了の根拠が「自己申告」ではなく「機械の緑 ＋ 人間の証拠付き確認」に置き換わる | 完了定義が CLAUDE.md / STANDARD-WORKFLOW.md にインライン明記されている |

> **本KGIで閉じる範囲**：動作確認漏れ・スモーク用意忘れという人間起因のミス。
> **本KGIで閉じない範囲（PO許容・スコープ外）**：①Sandboxと本番の差異、②外部API呼び出し検出パターンの網羅性、③緊急時の手動通過（bypass）は今回封鎖しない、④人間確認者の空判子（機械では強制不能）。

---

## recon 確定事実の要約（file:line）

| 穴 | 事実 | 出所（file:line / PR） |
|---|------|------|
| 穴1 | 検証パイプライン（Evaluator含む）が claude-impl/* のみ対象で、正規の人間ブランチ feature/morimoto/* では起動しない。今回 Evaluator は SKIPPED | claude-pipeline.yml:63-70（recon R5）。正規命名は CLAUDE.md:70 |
| 穴2 | PayPal テスト6本すべてモックのみ。実Sandboxを叩くテストは存在しない。実APIが壊れても緑 | recon R2。実装は backend/app/services/paypal_payments.py:549-629（create→send→get）, backend/app/routers/invoices.py:602-707 |
| 穴3 | gate（scripts/check-process-artifacts.js）は recon.md・design.md の存在と形式のみ検証。動作確認の有無を判定しない。Evaluator と独立動作のため Evaluator SKIPPED でも gate PASS | recon R4。gate本体 scripts/check-process-artifacts.js, ワークフロー .github/workflows/process-artifacts-gate.yml |
| 穴4 | 完了報告の根拠がモックテスト緑のみ。人間レビュー0件（sandbox実機確認の記録なし） | recon R3。PR #1980（feature/morimoto/paypal-invoicing → develop, 2026-06-11） |

---

## 対象範囲と実装単位（1リリース1変更で分解）

| PR | 内容 | 塞ぐ穴／層 | 種別 | PO GO | フェーズ |
|---|---|---|---|---|---|
| PR-A | PayPal Sandbox スモークテスト新設 | 穴2 / 層1 | テスト追加（通常）＋ secrets登録（PO作業） | テスト部分は不要 / secretsはPO手動 | 1 |
| PR-B | 検証パイプライン起動条件の拡張 | 穴1 / 層1 | claude-pipeline.yml 変更（**危険**） | **必須** | 1 |
| PR-C | gate に「外部API呼び出し検出→スモーク必須」＋ secrets未登録時 FAIL | 穴3 / 層1 | check-process-artifacts.js 変更（**危険**） | **必須** | 1 |
| PR-E | gate に「外部API連携PRは認可承認者の承認必須」を追加 | 層2（人間・マージ前） | check-process-artifacts.js 変更（**危険**） | **必須** | 2 |
| PR-F | 本番デプロイ安全化：本番相当素振り＋人間の証拠付き最終確認＋デプロイ後ヘルス＋自動ロールバック | 層3〜5 | deploy.yml／本番scripts 変更（**危険**） | **必須** | 3 |
| PR-D | 完了定義のインライン明記 | 穴4 / 層全体の定義 | docs-only | 不要（自動スキップ） | 4 |

> **最優先は Phase 1（PR-A＋PR-B＋PR-C）**。スモークを書いても（PR-A）人間ブランチで起動しなければ（穴1）空振りし、起動だけ広げても（PR-B）走るのがモックだけ／検出漏れなら故障を見逃すため、3つで初めて効く。

---

## 実装方針（技術How）

### 層1 / 穴2 / PR-A：PayPal Sandbox スモークテスト
- backend/app/services/paypal_payments.py:549-629 の3ステップ（create→send→get）を、**実Sandboxに対して請求書を1枚発行する**最小スモークとして新設。モック差し替えをしない。
- テストファイル名：backend/tests/test_paypal_sandbox.py（FedEx の test_fedex_sandbox.py に倣う）。
- flaky対策：発行1件のみ、タイムアウト＋限定リトライ。Sandbox自体の障害と自社実装の故障を切り分け（安易な無条件SKIPはしない）。
- secrets 未登録時は SKIP ではなく FAIL（KGI-4）。

### 層1 / 穴1 / PR-B：パイプライン起動条件の拡張
- 目的：feature/morimoto/*（CLAUDE.md:70）のPRでも検証（少なくともスモーク／Evaluator）が起動する。
- **要確認（推測で確定しない）**：現行 claude-pipeline.yml の起動意図に食い違いの疑い。ADR-051 は「ADR push起動」、recon R5 は「claude-impl/* 対象（:63-70）」、userメモリ上は「ADR自動発火の旧4エージェントモデルは ADR-112 で廃止済み」。**3者の整合を、実装着手前に正本 STANDARD-WORKFLOW.md と現物で確定する。**
- 確定している論理：正規の人間ブランチで検証が起動しないのは穴であり塞ぐ。これは不変。

### 層1 / 穴3 / PR-C：gate 強化 ＋ SKIP→FAIL
- scripts/check-process-artifacts.js に、**外部APIを実際に叩くコード（HTTP通信部分）の変更を検出したPRには、対応する実Sandboxスモークの成功（緑）を通過条件に加える**ロジックを追加。
- **検出は人間の手動登録に依存させない**（KGI-3）。
- スモークは **secrets 未登録時 SKIP ではなく FAIL**（KGI-4）。
- 検出の具体実装・挿入file:lineは Step 1 architect recon で確定。

### 層2 / PR-E：認可承認者の承認必須（人間・マージ前）
- ADR-136 の「認可承認者（shingo-ops / Hikky-dev）の PR Approve が無ければ gate FAIL」ロジックを流用し、**外部API連携PRにも承認必須**を適用する。
- 承認者は確認内容を**証拠付き**でPRに残す。GO: Shingo YYYY-MM-DD コメント方式（既存運用）と整合。
- **限界明記**：機械が強制できるのは「承認の存在」まで。空判子は機械で防げないため、層1の機械防御を主とする。

### 層3〜5 / PR-F：本番デプロイ安全化
- **本番現状は未確認**：deploy.yml・本番scripts・現行のヘルスチェック／ロールバックの有無は Step 1 recon で確認する（推測で断定しない）。
- 確認後、次を組み込む：①本番相当 docker-compose 環境での素振り（機械・環境差検出）、②人間の証拠付き最終動作確認を本番反映の必須ステップ化、③デプロイ後の自動ヘルスチェック、④ヘルス異常時の自動ロールバック。
- **本番での人間の実操作確認の具体（どのテナントにテスト発行するか等）は、実顧客に実害が出ない形を Step 1 recon/設計で確定する。**

### 穴4 / PR-D：完了定義のインライン明記
- docs/STANDARD-WORKFLOW.md と CLAUDE.md にインライン明記：
  - 「外部API連携を含む変更の完了とは、(a) 実Sandboxスモークを含む指定ゲートが全て緑、(b) 認可承認者の証拠付き承認、(c) 本番反映時の人間の証拠付き最終確認、の全てを満たすことを指す。担当者の『確認した』という自己申告は完了の根拠にしない。」

---

## KPI（測定指標）

| 指標 | 目標 | 測り方 |
|---|---|---|
| 外部API連携PRの実Sandboxスモーク実行率 | 100% | CIログ集計（sop-health-reporter 拡張余地） |
| feature/morimoto/* PRでのパイプライン起動率 | 0% → 100% | CIログ |
| 外部API連携PRの認可承認者 承認率 | 100% | gate ログ |
| 本番反映時の人間証拠付き確認の記録率 | 100% | デプロイ記録 |
| 実API故障の本番流出 | 0件 | インシデント記録 |
| secrets未登録時のスモーク結果 | 必ず FAIL | 負のテスト |

---

## 弊害・トレードオフと対策

- **実Sandboxスモークの不安定化（flaky）**：Sandbox障害・遅延・レート制限でCIが赤に。→ 発行最小限・タイムアウト＋限定リトライ。Sandbox障害と自社故障を切り分け、無条件SKIPはしない。
- **secrets 管理リスク**：→ GitHub Actions secrets、ログ出力禁止、登録はPO手動。
- **CI時間・コスト増**：→ スモーク必須は「外部API通信コードを変更したPR」に限定。
- **人間確認のボトルネック化**：承認者を Shingo/Suttan の2名に。通常PR（外部API非該当）は従来どおり影響なし。
- **空判子リスク**：→ 機械の層を主防御に。人間確認は証拠添付を要件化。
- **危険変更の自己ブートストラップ**：PR-C/PR-E は scripts/ を触り gate の承認要求が自分自身に発火（ADR-135 B-2 と同じ）。設計どおり、Shingo Approve で通す。

---

## 計画票

| ステップ | 内容 | 担当 | PO GO |
|---|---|---|---|
| 0 | 本設計docのKGIをPOが承認 | Shingo | 完了（2026-06-18） |
| 1 | 穴1起動条件の「要確認」を architect が現物確定（ADR-051/112/現行yml の整合）＋ 本番デプロイ現状 recon（PR-F前提） | architect recon | — |
| 2 | PR-A：PayPal Sandbox スモーク新設＋secrets登録 | Generator / PO（secrets） | secretsはPO手動 |
| 3 | PR-B：パイプライン起動条件拡張 | Generator | **必須** |
| 4 | PR-C：gate強化（呼び出し検出→スモーク必須・SKIP→FAIL） | Generator | **必須** |
| 5 | PR-E：認可承認者の承認必須を gate に追加 | Generator | **必須** |
| 6 | PR-F：本番デプロイ安全化（素振り＋人間確認＋ヘルス＋自動ロールバック） | Generator / PO | **必須** |
| 7 | PR-D：完了定義インライン明記 | Generator | 不要 |
| 8 | 負のテスト（故意破壊で FAIL／secrets外して FAIL／承認なしで FAIL／ヘルス異常でロールバック）でKGI実測 | architect / PO | — |

> 危険変更（PR-B/C/E/F）は ADR-130「1リリース1変更」に従い別PR。各々 Shingo の明示GO（PR上に GO: Shingo YYYY-MM-DD）を事前取得。新規ADRは穴・層ごとに起案（What/Why）。

---

## 継続

- 新しい外部API連携を追加するたび、PR-C の自動検出が実Sandboxスモークを要求する（人間の登録忘れに依存しない）。
- secrets未登録時 FAIL 原則で「テストはあるが休止」（FedExの二の舞）を構造的に防ぐ。
- 起動率・実行率・承認率を sop-health-reporter（ADR-124）の指標に追加する余地を残す。
- 本番デプロイの安全化（PR-F）は、バックログのゼロダウンタイムデプロイ化と統合的に育てる。

---

## 対象外（やってはいけない）

| 対象外 | 理由 |
|---|---|
| 人間レビューの **Ruleset 方式**での必須化 | GitHub 仕様で不成立（過去事例2）。代わりに **gate 方式で承認必須を実現**（PR-E） |
| 担当者の交代・人事的対処の設計 | 本設計は仕組みで再発を防ぐもの。人依存に戻さない |
| 既存CIチェックの削除・モックテストの廃止 | 追加のみ。モックは速度面で有用、実スモークと併存 |
| マージ前／CI内で**本番API**を実際に叩くこと | 実害（実請求書が顧客に飛ぶ）。本番確認は層3〜5（素振り・テスト発行・ヘルス）で安全に行う |
| migration / 本番DB操作 | 本件のスコープ外。含める場合は別途PO GO |
| claude-pipeline の判断ロジック全面刷新 | 今回は起動範囲の修正のみ。設計思想の変更は別ADR |
| 緊急時の手動通過（bypass）の封鎖 | 今回スコープ外（PO判断 2026-06-18）。本番障害時の break-glass として維持 |
| デプロイ基盤の全面刷新（blue-green等の本格導入） | PR-F は最小スコープ。本格刷新は別イニシアチブ |

---

## 受け入れ基準

| # | 基準 | 検証方法 |
|---|------|---------|
| A1 | 実Sandboxスモークが存在し正常時に緑 | pytest test_paypal_sandbox.py PASS |
| A2 | 故意に実装を壊すとスモークが FAIL | 負のテスト（誤エンドポイント等）で赤確認 |
| A3 | secrets 未登録でスモークが SKIP ではなく FAIL | secrets を外してCI赤確認 |
| A4 | feature/morimoto/* のPRでパイプライン／スモークが起動 | CIログで起動確認 |
| A5 | 外部API呼び出しコード変更PRで、スモーク未用意なら gate FAIL | gate 負のテスト |
| A6 | 外部API連携PRで、認可承認者の承認なしなら gate FAIL | gate 負のテスト |
| A7 | 本番反映手順に「本番相当素振り」「人間の証拠付き最終確認」が必須ステップとして存在 | 手順書・deploy フロー確認 |
| A8 | 本番ヘルス異常時に自動ロールバックが発火 | 異常注入テスト |
| A9 | 完了定義が CLAUDE.md / STANDARD-WORKFLOW.md にインライン記載 | git grep |
| A10 | 既存CIチェック・モックテストが消えていない | git diff --name-only / CI一覧 |
| A11 | 危険変更PR（B/C/E/F）に GO: Shingo コメントがある | PR確認 |

---

## 危険変更とPO GO要否（まとめ）

- **PO GO必須**：PR-B（claude-pipeline.yml）, PR-C・PR-E（scripts/check-process-artifacts.js）, PR-F（deploy.yml／本番scripts）。
- **PO手動作業**：PayPal Sandbox secrets のCI登録（PR-A）。本番での人間の証拠付き最終確認（層4）。
- **GO不要**：PR-A のテストコード追加、PR-D の docs-only。
