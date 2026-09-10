---
mode: handoff
status: draft
---

# 金型利用検査 — 所有元と移行残件の管理案

親: [全体設計§N](design.md#n-ciによる金型ルールの強制設計2026-09-10構築仕様草案)
対象ADR: ADR-144（検出範囲・例外方式の改訂案が必要）、ADR-067。
recon: [調査記録](../../handoff/design-system-recon/recon.md)。

## 決めた設計上の分担

- 所有元一覧: native要素を共通部品自身が使う許可。部品名・ファイル・用途・許可要素を登録する。
- 移行残件一覧: ページ等に残る個別実装。許可された正しい金型と混ぜない。
- 見本: 所有元一覧の部品を参照する。色や寸法を一覧へ重複登録しない。

機械可読の保存先候補は既存frontendの検査領域に frontend/scripts/ui-governance/owners.json と baseline.json。
これらは未作成の実装対象候補であり、現在実在する正本とは呼ばない。docs側は理由と審査を記録し、同じ一覧を手編集しない。

## 所有元の初期候補を実物と照合

基準6e133572のfrontend/src以下。行番号は初期照合の証拠で、検査の永続IDにはしない。

| 部品 | ファイルとnative要素 | 用途・分類 |
|---|---|---|
| Button | components/Button.tsx:73 button | 通常の操作ボタンの所有元 |
| SelectControl | components/Select.tsx:53 select | Selectと同じファイル内の入力本体。SelectControl.tsxという別ファイルは存在しない |
| TextField | components/TextField.tsx:64 input | 入力本体。型の制約も照合対象 |
| Textarea | components/Textarea.tsx:63 textarea | 複数行入力本体 |
| DataTable | components/DataTable.tsx:168 table | 表本体 |
| DataTable | 同:173/261 input | 表の選択操作。ページの任意input許可へ拡張しない |
| DataTable | 同:197 button | 並べ替え操作。通常Buttonへの自動置換対象としない |
| DataTable | 同:286/298 button | ページ送り。最終的にButtonを使うかは部品仕様の判断が必要 |
| Tabs | components/Tabs.tsx:74 button | タブ操作。通常の保存ボタンと同一の外観にしない |

これは初期候補9行であり、全native要素の免除一覧完成ではない。DataTable/Tabsの内部ボタンも、外観を決める所有部品を必ず持つ。同じ所有元ファイルへ別コンポーネントを追加しても自動免除しない。

## 記録契約案

所有元レコードの必須項目:
- componentId: 永続的な部品名。キー重複不可。
- module: リポジトリ相対の完全パス。basename/globによる免除不可。
- exportName: 実際の公開名。import側の別名ではなく解決後の名前を使う。
- nativeUses: tag、入力ならtype、用途role、対象構文の識別子。
- story: 実在する見本と必須状態名。見本ファイルの存在だけで全状態確認としない。
- decision: 採用理由と承認された設計への参照。明暗・寸法値は保持しない。

移行レコードの必須項目:
- ruleId、module、owner、syntax、occurrences、targetComponent、evidence。
- syntaxは対象開始タグ全体の構文トークン列。コメントと空白を除外するが文字列値・JSX属性・属性順序・spreadを保存する。children本文をIDへ含めない。属性変更は要確認として新規扱いになる。
- occurrencesは同じ識別子の出現数。行番号は診断用の派生値。空行挿入でIDが変わらないことと、同じ違反の複製が許容数超過になることを試験する。
- ownerは構文上の包含関数/変数の名前と親の列。同名・匿名で一意に識別できない箇所は自動で免除せず、初回登録前に表現を確定する。
- targetComponent未確定のものは「移行設計待ち」と明記し、実装可能な一覧へ混ぜない。初期件数の分母には残す。

JSONのschemaVersion=1、未知キー・重複キー・絶対パス・親ディレクトリ参照・空理由・0以下のoccurrencesは登録エラー。JSON parserが重複キーを後勝ちにする挙動をそのまま承認判定に使わない。

## PR比較の規則

BASEの一覧を許可上限に使う。HEAD側への追記だけでは新違反を免除しない。

| 変更 | 判定 |
|---|---|
| 空行・コメント追加だけ | 同じ構文で照合できれば合格 |
| 生button1個を別属性の生button1個へ変更 | 件数が同じでも新規として不合格 |
| 生buttonをButtonへ移行し、該当残件も削除 | 合格 |
| 生buttonを移行したが残件だけ残す | 不合格。再導入の抜け道を残さない |
| HEADにui-allowを書いて新規違反を隠す | 本案では不合格。ADR-144改訂承認・切替後に適用 |
| 共通部品内の登録済み内部操作 | 登録した用途に一致する場合に限り合格 |
| 全componentsフォルダを除外する変更 | 許可方針に反する。Reviewerも差分確認 |

初回登録/新部品/正当な例外の追加は、一般移行PRの自己免除と別経路にする。BASEにはない所有元を追加する正当な経路と、悪意ある免除を区別する承認の機械的接続は未確定。この点が解決するまで本案を実装合格にしない。既存process-artifactsのGO検証を候補として調査し、単なるラベルや自称のapproved文字列を根拠にしない。

## 解析器と保証範囲

frontend/package-lock.json実物: TypeScript5.9.3、PostCSS8.5.15。TypeScriptは直接devDependency、PostCSSは現在直接宣言なし。依存名と実物を混同しない。
TypeScriptの公開Compiler APIで構文木を取得・走査する案。直接依存の範囲で始める。構文エラーは診断結果で扱う。
CSSの条件・selector・変数参照は別の検査責務に分け、native要素の識別と一つの巨大な正規表現にしない。

任意のJavaScript実行結果やCSS読み込み順を静的解析だけで保証しない。動的class/style/spreadを解決できない場合の専用入口登録と、実部品の表示比較を併用する。完全保証のためと称して正常な既存動的コードを初回から全件赤にする設計は採らない。未分類件数を調査残件として先に出す。

## 外部・過去事例の参照と我々への応用

Context7なしのため許可済み代替として[TypeScript公式Compiler API資料](https://github.com/microsoft/TypeScript/wiki/Using-the-Compiler-API)を2026-09-10に確認。createSourceFile/forEachChild等の構文走査を参照。ローカルtypescript.d.tsの公開APIも照合した。採用済み5.9系を対象とし将来版へ無条件に拡張しない。企業事例は本検査の検出力の直接根拠にならないため使用しない。

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 所有元と利用先を区別 | Button本体合格・同ファイル別関数のbutton追加不合格 |
| 名前の付け替えで回避できない | import別名と再exportの解決結果を照合 |
| 件数を据え置いた違反も検出 | 同数置換の不合格と空行追加の合格を対照 |
| 解消した違反が復活しない | 移行→BASE更新→再導入の連続2PR相当fixture |
| 読めない登録表が通らない | 重複キー・未知version・壊れた構文の不合格 |
| 分母を減らして完成を装えない | 初期スナップショットと移行・残件・例外件数の突合 |

## 維持の仕組み

守り手: `.github/workflows/ui-governance-gate.yml`
登録表と検査自身の変更はReviewerが理由・試験・承認を確認する。自分のプログラムで自分の削除を完全防止できるとは記載しない。

## 自己審査

REVISE。所有元候補と記録項目・比較規則は具体化済み。新規登録の承認接続、全所有元の照合、匿名構文の識別、動的CSSの扱い、ADR-144改訂案が未完。未確定をGenerator裁量として渡さない。第一便の取得エラー修正は独立して進められる。

### 承認接続の追加確認

scripts/check-process-artifacts.js:265のparseGORecordはPR本文を読む。:293のvalidateGORecordは本文に書かれたissuer/date/GO番号等の形式を検査する。この関数はGitHub上の承認者本人を認証する処理ではない。したがってこの戻り値だけで新しい金型例外を自動許可する案は採らない。既存の正式GO運用を否定するものではなく、機械判定の保証範囲を区別する。新例外の自動認証の設計が整うまではReviewerによる実際のPO承認記録の確認が必要。

## 例外・所有元の追加を承認につなぐ案

前節で未確定だった自動認証について、GitHub本人のPRレビューを読む方式を候補とする。PR本文の自称「承認済み」は使わない。通常の部品利用・残件削除ではこの追加承認を要求しない。所有元の追加/変更・例外増加など、ルールを緩めるPRだけが対象。初回登録も同じ扱い。

観測事実:
- 既存UI gateのpermissionsにはpull-requests: readがある。
- GitHub `GET users/shingo-ops`でlogin=shingo-ops、id=246949427、type=Userを取得。これは本人のレビューを取得した証拠ではない。
- 公式[レビュー一覧API](https://docs.github.com/en/rest/pulls/reviews)にはuser.id/state/commit_id/submitted_atがあり、時系列順・ページ送りに対応。read権限で取得できる。
- 公式[レビューイベント](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#pull_request_review)はsubmitted/edited/dismissedで起動できる。GITHUB_SHAはmerge側なので承認対象のhead SHAと混同しない。
- Context7 MCPは未提供。PO許可済みの公式資料代替で確認した。

契約候補:
1. PR番号から現在のHEADを取得し、検査開始時のHEADと一致するか確認。取得失敗・ページ取得途中の失敗・HEAD更新は検査不能として非ゼロ。
2. 全レビューをページ末尾まで取得する。POのuser.idが上記IDに一致する投稿を選び、時系列の最後の有効な意思決定レビューを確認する。COMMENTED/PENDINGを承認にせず、後のCHANGES_REQUESTED/DISMISSEDを見逃さない。
3. 最新の意思決定がAPPROVEDで、commit_idが現在HEADと一致する場合だけ、HEAD側の登録変更を使用する。それ以外は「登録変更の承認待ち」で非ゼロ。同じ件数への置換・baseline増加を自動承認しない。
4. 承認後のpushは旧承認を流用しない。検査末尾でもHEADと承認状態を再取得し、途中変更を検出したらやり直す。
5. 再実行はPR更新とreview submitted/edited/dismissedを契機にする案。必須job名は維持し、承認されたイベントだけでjobをskipするifを置かない。
6. 検査ロジック・承認者ID・workflowそのものを書き換える変更まで自己防御できるとは主張しない。これらは既存の設計審査とReviewerが確認する。

必要な対照試験: 本人の現在HEAD承認=可、他者=不可、古いHEAD=不可、取消=不可、変更要求=不可、PR本文だけの承認=不可、2ページ目に取消=不可、API失敗=検査不能、承認対象外の通常移行=追加承認不要。

未解決: review取消直後とマージの競合、複数イベントの同名必須jobの再評価、レビュー権限の実運用確認が必要。公式APIが存在するだけで運用成功とは判定しない。POにGitHub上の追加操作を求める仕組みなので採用前に操作手順と負担を提示する。現在のチャット合意をGitHubレビューへ代筆しない。本案は草案であり、今回workflow/外部設定は変更しない。


## 実施順序変更による設計見直し（草案）

PO指定で画面統一を先行しCI追加を最後にするため、移行途中のbaselineをCIへ導入する必要性を再評価する。推奨案は、最終対象の未移行0を確認してから全件検査を有効化し、一時的な違反許可一覧を導入しないこと。これは完了対象を縮小する提案ではない。共通部品内部のnative要素の所有元定義は引き続き必要であり、その全件照合は未完。

上記は設計案。既存ADR-144の増加検査/例外を独断で削除しない。追加の本人レビュー認証機構もまだ採用しない。ルール自体の変更を人のレビューで扱う範囲と、自動判定する範囲をADR改訂案へ明記してから設計合格を判定する。取得エラー修正を含め、CIの先行実装は行わない。


## 最新の限定検査契約（過去草案の置換案）

[最終CI契約](../../handoff/design-system-recon/evidence-20260910/final-ci-contract-audit.md)を最新案とする。baseline、GitHub本人認証API、全動的計算のadapter化は採用しない。旧節の対応する候補は履歴。全対象の未移行0を実装台帳で照合後、所有するexportとnative/所有CSSを登録する。27受入IDを正常・不正・取得不能の対照とする。禁止styleは共通部品の外観上書きで、一般の動的配置を一律禁止しない。CI自身の変更は既存の人のPRレビューで確認する。
