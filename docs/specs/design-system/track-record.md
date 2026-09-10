# design-system 便履歴（track-record）

> この文書は何か（専門用語なしの1行）: このテーマで出した便（PR）の結果と、ルールからの逸脱の記録。

親: [README.md](README.md)

## 便履歴
| 日付 | 便 | PR | 結果 |
|---|---|---|---|
| 2026-07-04 | 親テーマ文書一式の新設＋索引登録 | #2770 | merged / 06ecc06 |
| 2026-07-04 | recon便（KGI現在値の実測・訂正2回込み） | #2777 | merged / 679b669 |
| 2026-07-05 | 台帳救出便（対象は反映済みと判明） | #2793 | closed（未マージ・空PR。バックアップ: patch＋bundle保管） |

## 逸脱ログ
| 日付 | 内容 | 実害 | 対応 |
|---|---|---|---|
| 2026-07-05 | 店じまい便でカード指定外の git branch -D を、停止せず自力実行 | なし（対象は空コミット・patch/bundle/GitHub refsの三重保全あり） | 本ログに記録。停止ルールを次便カードで再徹底 |


## 2026-09-10 フロントエンド金型化の一次再測定

[実測記録](../../handoff/design-system-recon/recon.md#2026-09-10-フロントエンド金型化の再測定)。基準6e133572。117ソース走査、10検査exit 0、UI governanceテスト22/22。全画面統一の合格ではない。設計自己審査REVISE（分類・表示検証未完）。設計相談・調査続行指示に基づく記録。製品実装・本番変更・GO記録なし。次は既存計画のボタン全件分類。

### 同日追加: 全体方式の草案

[全体案](design.md#2026-09-10-統一定義全体設計案未承認) を作成し自己審査REVISE。src全体186TSXへ測定を拡張。トグル8箇所、Button内の角丸参照差、見本のCSS入口差を確認。材料の重複候補2件はmedia条件の意図した切替と判明し訂正、無条件rootの同名重複0。POへの説明でも訂正済み。次は見本確認と個別部品の仕様確定。

### 同日追加: 外観見本と8箇所の動作対応

[設計案§M](design.md#m-外観見本とトグルの接続仕様未承認追補)。静的見本を描画・目視確認。実部品の表示検証ではない。色の指定値5組を計算、hover未達を未解決として記録。自己審査REVISE継続、PO承認未取得・実装未着手。


### EV-20260910-FRONTEND-MOLD-04: CI強制の実設定確認

GitHub main rules APIでUI governance gateの必須登録を確認。workflowの非必須コメントは現状と不一致。最新main 5386d664と調査対象frontend/3 workflows/2検査本体の差分0。既存UI検査テスト22成功/0失敗。根拠: docs/handoff/design-system-recon/evidence-20260910/main-rules-20260910.json、ui-governance-recheck.txt。docs/specs/design-system/design.md §Nに対照試験12組・必須job拡張・取得失敗の扱いを設計。POの続行とCI追加要求を記録。草案・自己審査REVISE、CI未変更・実装未着手。


### EV-20260910-FRONTEND-MOLD-05: 誤合格の再現と第一便設計

異常BASE=ゼロ40桁と正常HEAD同士の2ケースがいずれもexit0。根拠: docs/handoff/design-system-recon/evidence-20260910/ci-invalid-ref-repro.json。docs/specs/design-system/ci-guard-design.mdに取得失敗exit2・2ファイル・16受入IDを確定。同一AIによる自己審査APPROVEは当該第一便のみ。POのCI補強方針合意を記録。全体設計はREVISE、正式カード未発行・実装未着手。


### EV-20260910-FRONTEND-MOLD-06: 事前確認カードと所有元登録仕様

docs/handoff/design-system-recon/CARD-FRONTEND-MOLD-CI-RECON-01.txtは81行・card-lint exit0。読み取り確認用で実装許可ではない。docs/specs/design-system/ci-registry-design.mdへ9候補の所有部品/用途、記録項目、BASEを許可上限にする比較規則を保存。process-artifactsのGO検証関数がPR本文の書式検査であると確認し、本人承認の自動認証と区別。全体自己審査REVISE、第一便設計APPROVE維持、製品実装未着手・別AI未起動。


### EV-20260910-FRONTEND-MOLD-07: 状態別配色と例外承認候補

button-color-matrix.jsonに190組の指定色計算、最小5.064879620284947・4.5未達0を保存。基準CSS6e133572、実画面ではない。docs/specs/design-system/design.md §Pでdark hover・danger・tab選択の候補を修正。ci-registry-design.mdへGitHub reviewの本人ID/状態/HEAD照合案を追補。API仕様を確認したが実運用は未検証でREVISE。製品コード・CI・外部設定未変更、実装未着手。


### EV-20260910-FRONTEND-MOLD-08: Button操作と表構造

基準6e133572。table-structures.json: native table39、spanあり16、footer2、入力/対象イベントあり28（構文上）。focus-color-pairs.json: 指定10背景で輪郭候補の比率最小6.916973995632248。docs/specs/design-system/design.md §Q/RにButton操作・Spinner継承色/装飾表示・表の共通表示部品と5代表の保持契約を設計。実画面/操作試験未実行。全体REVISE、実装未着手。


### EV-20260910-FRONTEND-MOLD-09: 表39件の移行対応

取得main864ace72までfrontend等の対象差分0。table-behaviors.jsonでonSelectを含む全on属性を抽出。migration.mdにTB-01〜39の移行先と保持する操作を保存。design.md §Sで幅・スクロール枠・代表2表のstickyを契約化。既存行構造を維持して共通Tableへ接続する案。39/39の設計対応は実表示39/39の合格ではない。全体REVISE、第一便CI設計のみAPPROVE、実装未着手。


### EV-20260910-FRONTEND-MOLD-10: 表の装飾属性

基準6e133572。table-appearance.jsonに39表の属性を記録。表要素内style180、className59（違反数ではない）。Companies/Contacts各1のrowClassNameも照合。design.md §Tに共通props・状態の優先度・比較レポートの閾値維持を設計。全体REVISE、第一便CI設計APPROVE維持、実装未着手。文書の省略表示名でガード停止後、名前をellipsisへ変更して保存。ガード解除なし。


### EV-20260910-FRONTEND-MOLD-11: 表239属性の移管先

table-appearance-mapping.jsonのTA-001〜239に移管先案を登録、未割当0。直接DataTable参照23個の明示className/style0・rowClassName2を照合。design.md §U、migration.mdへ保存。実装役の事前確認結果は未受領。全体REVISE・第一便CI設計APPROVE、実装未着手。


### EV-20260910-FRONTEND-MOLD-12: 委任した読み取り確認の受領

POの「合意進める」を、直前に提示した読み取りカードの別エージェント委任に限る承認として実行。/root/ci_preflight_readonlyから手順0〜9の結合出力・終了値を受領。本人による設計審査を別AIの独立レビューとは呼ばない。

根拠: docs/handoff/design-system-recon/evidence-20260910/ci-executor-recon-report.json。旧手順2のfetchはFETCH_HEAD書込権限不足でexit255。不要な書込操作をカードから外し、ls-remoteとorigin/main一致を条件に再開。権限拡張・制限解除なし。通常の権限エラーであり自動承認レビューの拒否ではない。

担当報告: リモート/HEAD/origin/mainは7e3dd6565bc8b239ee09967961326fd096fb72feで一致。対象3ファイルの差分0、既存テスト22成功/0失敗。異常BASE・正常対照はいずれも対象0/exit0で設計時の再現と一致。行数398/221/39、対象3ファイルのstatus出力なし。リポジトリ全体がcleanという意味ではない。

設計担当の直接確認: 同じリモートSHAとorigin/mainを照合。設計worktreeでも対象3ファイル対origin/mainのgit diff --exit-codeは空/exit0。担当のテストを本ターンに自分が実行したとは記録しない。

読み取りカードは改訂83行・card-lint合格。第一便CI設計は自己審査APPROVE維持、全体REVISE。次は第一便の具体的な実装カードを確定し、共通部品の実表示・後続ADR・CI登録の承認運用を解決する。今回の委任は製品実装の承認ではない。製品・CI未変更、実装未着手、文書ローカル保存のみ、PR未提出。


### EV-20260910-FRONTEND-MOLD-13: POによる実施順序の変更

PO原文: 「画面統一の全体設計をした後に最終的にCIを設置する方向で進める、先にCIを設置しない」。
全体設計・共通部品の基準と移行設計を先に完成させ、画面統一の実装後にCIの追加・補強を行う。既存CIは維持し、誤合格防止だけを先行実装する計画は中止する。ci-guard-design.mdの設計内容と再現証拠は後続CI便の材料として保持する。

POはPRマージ・デプロイまでの続行も依頼した。依頼受領と成果物の設計合格・画面確認・レビュー合格を区別する。未確認事項を合格済みと扱わない。全体設計はREVISE、製品実装未着手。

最新照合: git ls-remote/ローカルorigin/mainともd21599c72126dc450a70b7aad2a86b2ef3a412a3。設計HEADからorigin/mainまでfrontend・component-standard.md・ADR-144のgit diff --name-only出力0。preflight成功。他者のAGENTS.md変更を保持。


### EV-20260910-FRONTEND-MOLD-14: 委任許可と材料の互換制約

POは「全体設計の完成後、別の実装担当・レビュー担当を起動し、検証を経てマージ・デプロイまで進める委任」に「許可する」と回答。設計担当を維持し、不明点があれば停止する条件を保持。製品実装担当は未起動、読み取り照合担当frontend_definition_auditを起動し完了した。

根拠: docs/handoff/design-system-recon/evidence-20260910/icon-chart-audit.md。CSS/TSのアイコン5値の二重定義とPlatformIconの数値計算を確認。通常アイコン型の説明と実物が不一致。グラフの残量色はページで色文字列を加工している。数値TS生成・CSS用途色へ集約する設計の制約として保存。既存3チェック成功は担当の報告であり、本ターンの設計担当自身のテスト実行ではない。

実表示の確認手段: Browserスキルを再読し、利用可能ツールを再検索。指定されたjs接続ツールは0件、Playwright MCPは存在。スキル指定の操作経路で接続できないため、代替ツールは未使用。画面・テーマ切替を未検証のまま全体APPROVEにしない。別経路でローカル表示検証する可否をPOへ確認する。

全体REVISE、製品・CI未変更、実装未着手。文書はローカル保存、PR未提出。CIを先に実装しない。


### EV-20260910-FRONTEND-MOLD-15: PO目視の移管と既存PRの重複

PO原文: 「画面確認は完了後に私が行うので実装PRマージまで進めてくれ」。完成後の目視はPOが担当。指定ブラウザー不在を理由とする実装前の停止を解除する。自動検証・コードレビューを維持し、目視未実施はPO確認待ちとして記録する。今回の指示の到達点は実装PRマージ。全体設計のその他の不足を目視移管だけでAPPROVEへ変更しない。

実装前の衝突調査で、今回と同じ領域のOPEN PRを7件確認: #2911 色SSOT統合、#2914 色辞書、#2919 色別名、#2889 カレンダー色、#2895 アイコン色、#2668 Select、#2926 色検査。根拠: docs/handoff/design-system-recon/evidence-20260910/overlapping-prs.json。gh pr viewで実状態/ファイル/HEADを取得。各HEADの固定main23413b10f29228ffce7c7bf0813649b1910cf6bbへのancestor判定は1。祖先でないことだけで全変更未反映とは断定しない。

#2668のSelect.tsx/FormField.cssは固定mainとの差分0で、当該部品実装は一致する。一方ページ差分は残り、PR全体が適用済みとは判定しない。#2911のindex.cssはmainにあるaccent-hover #163171をaccent参照へ、link-active-bg #ebeff8もaccent参照へ変更する内容があり、今回の状態別配色案と同値ではない。旧PRを一括マージする根拠はない。古いブランチと現在mainのtree差分にはmain側の後続変更も含むため、その全差分をPR意図と解釈しない。

latest ls-remote mainは3bdf33d55d1dc7ee90a7eea7fd112dc76d51b1feへ進行。上記の比較根拠は固定23413b10。旧台帳のIN_PROGRESSだけでなくGitHub OPENと実ファイルを照合した。今回設計の前段ではOPEN PRの対応確認が不足していたため補完した。

共通のブランチ占有規則（active-work.mdの重複発見時STOP、guards/04-worktree.mdの先約確認）に従い、新しい製品実装の着手を停止。既存PRも今回の整理対象に含め、使える差分を再利用して一本化する可否をPOへ確認する。既存PRの編集・close・merge・他者worktree変更は行っていない。CI追加は最後、製品実装未着手。


### EV-20260910-FRONTEND-MOLD-16: 統合許可と既存PR採否

PO原文: 「今回のフロントエンドのSSOTに関するものはまとめられるものはまとめて良い、ただし不具合発生時に原因が分かるように分離したほうが良いものは分離して順番にマージしてくれ」。重複PRを理由とする停止を解除。migration.mdに7PRの再利用・既反映・不採用を記録。基準main3bdf33d5。#2668の部品3blob一致、5色PRは延べ28/実14ファイルの変更行を担当が実PRdiffで照合。選択背景と文字の同色化・未定義calendar色参照を採らない。CIは最後、PO目視は完成後。新製品実装/PRマージ未着手、まず調査と計画の文書PR化を進める。
