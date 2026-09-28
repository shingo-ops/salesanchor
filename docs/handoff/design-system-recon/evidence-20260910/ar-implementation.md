# AR 28ボタン一括移管の実装・検収

親: [design-system](../../../specs/design-system/README.md)。設計: [design.md §AR](../../../specs/design-system/design.md)。調査: [recon](../recon.md)。対象ADR: ADR-113/067/027/073/122。

## 状態

2026-09-28、POの広い一括移管とAstra設計/Sol調査実装の明示依頼に基づく。14製品ファイル28件の機械移管済み。操作試験の交差レビューAPPROVE、対象92試験成功。ローカル検収済み。PR・CI・マージ・本番反映は未完。画面/実ログイン/本番フォーム/PO目視はPO指示で省略・未検証。

## 実物の分類と範囲

10 native forms（9 Modal、1 inline）20ボタン、Roles割当の非form Modal操作2ボタン、検索submit6（API GET5/local filter1）。調査初期の「11フォーム」をSol第二照合で訂正し、設計/監査/契約/正式カードを修正後に審査合格。詳細: ar-button-audit.json / ar-contracts.md。初期/tmp草案は正本ではなく、正式カードを指定して発行した。

## 直接確認と担当報告の区別

Astra直接実行: ar-final-audit.cjs（2026-09-28 06:54 UTC以前の検収時点）。14ページ逆変換byte一致、28変換原文、対象外53原文、共有15hash一致、共通231/旧266、pass=true。再実行可能な監査スクリプトと基準JSONを保存。

Sol実装担当も同監査を実行して一致。別Solは14製品diff全件をread-only審査しAPPROVE（所見0）。未導入12ファイルだけnamed import追加、既存importのLeads/Suppliersは維持。diffは14files/+48/-36で、指定タグ/属性置換以外のAPI/DB/権限/処理本文/SSOT/CSS/トークン/翻訳/依存変更0。これは製品差分の静的審査であり、未完成の操作試験の合格ではない。

## 試験の先行レビュー

初稿FormAction試験は、X/Escape/焦点、pending取消後結果、取消後入力保持が不足し、権限拒否試験に旧mock履歴で偽陽性となる可能性があるためREVISE。実装担当へ既存受入条件内の補強を指示。最終結果は原ログで確定し、ここへ追記する。

## PR作成経路の依存

release/pr-lifecycle-gatesで同じ承認手順が変更中と実物確認し、台帳の重複時STOP規則に基づいて自分の手順編集を停止。別担当はPR #3824を提出済み（読取確認）。現時点の同PRはOPEN、番号付きGO未受領と本文に記載。main反映済みとは扱わない。こちらが作成したrelease/pr-create-phase-separationは作業場所だけでコード変更0、担当確認待ち。ARからガード/Ruleset/GO制度/本番設定を変更しない。


### 試験の分担追加

初稿4suiteの静的レビューで、検索は契約充足、フォーム側にedit/failure/pending/modal-close等の不足を確認。初稿の成功件数だけで完了とせず補強する。作業効率のため既存Sol2名の所有を分割。sol_staff_report_generatorは製品14固定とFormAction/MasterSearch/OrderLead試験、sol_button_inventoryはRoleKnowledge試験1件へ役割変更。移管前担当の編集停止・実行中コマンドなしを確認後、正式補強カードlint exit0で発行。後者は自分の試験を独立レビューせず、担当を交差して最終レビューする。新エージェント起動なし。

### 現行mainと起票経路の追加照合

origin/mainは6a156401へ進んだが、固定4bad43a4との差は別テーマのbackend1/docs2だけでfrontend・依存差分0。まだUIブランチへ統合していない。別SolによるPR3824呼出実物照合では、新wrapperは実行cwdのvalidatorを使うため他worktreeの絶対パス実行は版混成になる。正式main反映→UIブランチへ通常統合→同worktree内の公式wrapperが必要で、未マージ版の孤立コピーや借用はしない。


### 補強中の実物照合と失敗分類

受注/Roleのcancelは閉鎖だけだが、次のnew/edit openerが初期値/選択レコードを再設定する（OrdersPage:47-55、useOrdersState.ts:289-301、RolesPage:253-268）。再openでも下書き保持とする試験の初期仮定を実ソース照合で訂正し、正式契約に明記。製品は変更しない。Role側では既定色・testid複数形・未登録focus matcherも実物に補正した。初回失敗ログは保持する。

個別72試験とRoleKnowledge15試験の成功ログをrootが読取確認。ただし交差レビューではselector guardに到達しない試験（native requiredが先に遮断）、権限拒否不足、edit PATCH側async分岐不足、duplicate実回数assert不足などを検出。個別成功件数だけで最終合格とせず、両担当へ補強を戻した。

## 最終交差レビュー

Sol担当を分けて互いの試験をread-only再審査し、双方APPROVE。FormAction/MasterSearch/OrderLead側のselector guard・権限拒否・初回focus、RoleKnowledge側のcreate/edit両モードfailure/retry・pending重複回数・取消後resolve/reject・割当retry exact PUTを補強済み。自作試験を独立審査と呼ばない。RoleKnowledge最終SHA256はa1e862d537688abae391b35ccca3171fb0ece948300f75a666c91a8548005c07。

Astra直接再実行したar-final-audit.cjsはpass=true（14逆変換一致、対象外53/共有15維持、共通231/旧266）。Sol実行の21-targeted-final.logをAstraが読み、5ファイル92試験成功を確認。全体coverageの初回には時間切れが発生し、未合格として原因照合中。初回を隠さず最終結果と併記する。

## 起票依存の解消（最新確認）

GitHub直接照会でPR #3824は2026-09-28T07:16:22ZにMERGED。取得したorigin/mainはfdf3b45a4。旧記載のOPEN/担当確認待ちは過去の観測である。こちらの承認手順編集は0のまま、正式mainを通常統合した後に同worktreeの公式wrapperでPRを作成する。今回の番号付きGO・マージ・本番反映の完了を意味しない。

### 全体試験の初回失敗

22-coverage-final.log: 40ファイル581試験、558成功/23失敗、271.55秒。Astraが全失敗理由を原ログで確認し、いずれも5000ms時間切れ（新規OrderLead/RoleKnowledgeに加え既存BotForm/StaffForm等も含む）。設定・製品・試験を変えず、`npm run test:coverage -- --maxWorkers=2`で全件再実行する。並行実行の影響は仮説であり、初回の原因を確定したとは主張しない。試験skip・全体timeout延長・既存期待値の緩和は行わない。

### 全件coverage再検証

23-coverage-maxworkers2.logをAstraが直接読取。40ファイル581試験すべて成功、275.70秒。statements20.24% (3619/17876)、branches16.53% (2122/12831)、functions17.89% (992/5542)、lines20.87% (3203/15346)。初回と同一の全581試験を並行数2で実行し、試験/製品/config変更0。初回失敗を消しておらず、正式CIの既定コマンド成功は別途確認する。

### 静的検査での試験データ修正

check:all初回24はFormAction試験の絵文字リテラル4件を検出して失敗。製品/guard/allowlistは変更せず、既存U+1F3C6と同値のString.fromCodePoint定数に4参照をまとめた。別Sol読取レビューAPPROVE、最終hash7aef08a64ab23d3c16916227eb1f8ba1e73da205bfb95c910e97cea2a976bc06。変更後25ログは1ファイル28試験成功。実行担当の初報40件は原ログで訂正・撤回し28を正とする。全体581成功は同値fixture修正前、修正後の影響28成功を区別する。26-check-all-rerun.logは成功、lint0 errors/140 warnings。既存警告を今回解消済みとはしない。

## 最終ローカル検収

APPROVE（画面省略の限界付き）。製品14静的レビュー、4試験の交差レビューとfixture修正の再レビューが合格。Astra直接監査とSol実行原ログの読取を区別して確認した。

- 最終fixture修正後29-targeted-post-fixture.log: 5ファイル92試験成功。
- 全体40ファイル581試験成功は23ログ（並行数2、fixture同値表現変更前）。修正後の影響試験を含む92件も成功。CIの既定全件実行は別確認。
- strict ESLint: 製品14と新規試験4成功。check:all最終26成功、0 errors/140 warnings。
- 本番build27・Storybook28成功。chunk size/dynamic import等の警告を保持し、解消済みとはしない。
- 製品/共有/配線/API/DB/依存/CI設定は契約どおり維持。AQ日報製品と試験にもAR差分0。
- 初回失敗/途中出力/最終原ログをar-validation-logs.tar.gzへ格納、ar-validation-manifest.jsonに各SHA256を保存して再照合一致。生成coverageは削除せず/tmp/ar-final-coverage-20260928へ退避、commitには含めない。

次: 実装と文書保存、正式main統合、公式wrapperでAQ+AR計30件のPR、最新HEADのCI、番号付きGO、merge/deploy確認。画面/実ログイン/本番フォーム/PO目視は省略・未検証。旧266件・表・報酬3・カレンダー色は残タスク、新CI追加は最後。

### 保存・main統合後の検証状況

AR実装を1557eb821へ保存、origin/main fdf3b45a4をddd470746fe6001b3b83525b4ef057012a7ca537へ通常統合（競合0）。統合前後frontend全体diff0をAstraが直接確認。正式のPR起票経路を取り込み済み。

同値fixture修正後の全件30ログは580成功/1失敗（OrderLead edit成功試験の5000ms timeout、233.04秒）。これを記録し、23の全件成功だけで最終安定性を断定しない。製品/試験/configを変えず並行数1で全件を再検証中。原因の資源競合は未確定で、マージ/配備の完了宣言はしない。

## 最終HEAD相当の全件検証確定

31-coverage-maxworkers1-final.log（Sol実行exit0、Astra原ログ直接確認）は40ファイル581試験成功/失敗0、171.87秒。statements20.23% (3618/17876)、branches16.53% (2122/12831)、functions17.88% (991/5542)、lines20.86% (3202/15346)。試験・製品・config変更なし、並行数1の実行。新たな除外/skip/期待緩和0。途中23のcoverage値と区別し、最終値はこちらを採用する。

32最終機械監査pass=true、33diff-check成功、34試験hash保存。コミットhookも最終18製品/試験をstrict ESLint・絵文字・CSS var検査して成功。ローカル検収APPROVE確定。archiveを全実行終了後に再生成してmanifest全件SHA256一致。最終coverage生成物も/tmpへ保管し、製品commitへ混入しない。PR/正式CI/番号付きGO/merge/deployは次段階。
