# 通常Icon公開契約の実装検収（2026-09-11）

[設計§AE](../../../specs/design-system/design.md) / [実装カード](../CARD-ICON-CONTRACT-01.txt)。基準main76c6dff98e3fa68f47c381d044e86fd0564d9509。

## 結果

製品4ファイルに限定。通常Iconの自由なstyle/color入口を閉鎖し、ARIA6属性を同SVGへ転送。未指定/undefinedのhidden=trueと明示falseを保持。唯一のIcon.styleを同じSVGの配置classへ移し、2宣言の値は変更していない。PlatformIcon/LeadChatIconの本体は基準と同一。className全閉鎖・全アイコン種別の統合・全画面配色変更は未完。

## 実行者と検証

Generator frontend_definition_auditが実装と以下試験を実行。rootは製品差分・ログ/JSON/検証スクリプトを直接読んで、4製品SHA256と前後対象の対応を独立照合した。rootが全テストを再実行したとは称しない。

| 検査 | 観測結果 | 根拠 |
|---|---|---|
| 既存lockで導入 | npm ci exit0、manifest/lock差分0 | /tmp/frontend-icon-contract-20260911/install.log |
| 単体 | 19ファイル162テスト成功（追加11） | [checks](icon-contract-checks.txt) |
| 既存静的検査 | check:all exit0、0errors/既存219warnings | 同上 |
| 製品/見本ビルド | build、build-storybook各exit0 | 同上 |
| 局所ブラウザー | 明暗×幅390/1280×接続/切断8条件すべて前後一致 | [JSON](icon-contract-browser.json) / [再現原稿](icon-contract-browser.mjs) |
| ARIA出力 | 変更前はhidden=true/他5属性なし、変更後は明示6属性を保持 | 同JSON |
| 診断 | document入口1、client React module入口0、console.error0/pageerror0 | 同JSON |
| 製品照合 | 4hashが限定第二レビュー対象と一致 | [manifest](icon-contract-manifest.json) |

ブラウザーは実際の前後Icon TSXを実Heroiconsで静的HTMLへ生成し、実tokens/indexと配置CSSをChromiumで測定したもの。クライアントReactのhydrate試験、本番ページ操作、認知的な理解速度の試験ではない。ref/re-renderはDOM unitで確認。CalendarStatusBarは現行ではstoriesからのみ参照され、本番の画面変更効果を主張しない。

## 利用監査の失敗と修正

最初の変更後監査は型の表示名IconPropsという文字列に依存し、型変更後にtotal=0となった。rootがこの出力を発見し不採用とした。[不採用出力](icon-contract-rejected-zero-audit.json)。0件を移行完了の根拠に使わず、製品を検査都合に変更しなかった。

修正版はpropsのweight宣言の出所がconstants/icons.tsxであることを追跡する。[修正版](icon-contract-after-audit.cjs) / [変更後全対象](icon-contract-after-targets.json)。固定SHAを読む前版と現在worktreeを読む後版を区別する。rootがJSONをfile/tag/出現順で突合し、変更前152→変更後163、元対象の欠落0、追加11は新規unitのJSXのみ、元対象の属性差分はCalendarStatusBarのstyle→class1件と確認。実運用分類118箇所39ファイルは維持、style/color/ref/spread各0、hidden86/weight17を保持。

この抽出法は本便の有限な実物照合であり、将来任意の型/構文を完全解析できるCIではない。新CIは全画面移行の最後に別途設置する。監査原稿は/tmpへコピーして使用し、正式根拠ファイルの横で再実行して既存結果を上書きしない。

## 審査と現在状態

限定コード第二レビューci_preflight_readonlyは4ファイルのコード/型/§AE整合にAPPROVE。レビュー担当も試験は再実行せずログ確認。全体設計の審査は同一AIによる自己審査である。根拠の範囲を混同しない。

設計案作成済み・設計自己審査済み・限定製品実装/ローカル検証済み。新PR/リモートCI/番号付きGO/マージ/デプロイは未完。完成後のPO画面確認と理解しやすさ評価は未実施。


## PR提出時の停止（当時の記録）

CARD-ICON-CONTRACT-PR-01手順2のgit commitがpre-commitで拒否、exit1。GoogleCalendarStatusBar.tsx:82:6にonSyncStatusChangeの依存不足というreact-hooks/exhaustive-deps警告が1件あるため。check:allでは警告許容、保存前eslintはmax-warnings=0である。実行役は依存配列を変更せず停止した。

rootが基準76c6dff9の同ファイル本文をgit showで取得し、同じインストール済みeslintへstdin入力してmax-warnings=0で再現。基準でも:81:6の同警告1件・exit1。今回のCSS移管による新警告ではない。[提出停止と基準再現ログ](icon-contract-commit-block.txt)。HEADは基準のまま、commit/push/PRなし。製品4ファイル・検証結果は保持、hook迂回なし。

限定コードレビューAPPROVEとローカル試験成功は維持するが、便の提出可能性はREVISE（既存コミット検査との実行条件未解決）。設計§AEの業務処理非変更とmigration.mdのuseEffect依存修正分離を優先し、別件修正を混載しない。

POへ戻す1判断（未承認案）: この既存依存不足を別PRで先に修正する。具体案はcheckStatusのuseCallback依存に既存onSyncStatusChangeを含める。通知関数が差し替わった場合に最新関数を参照し、effectの状態再取得と30秒タイマー再登録が起きる点が外観移管との動作差。現在の呼出はstoriesのみで本番コード利用0（root rg全src確認）。

承認後の別便では通知関数差替え、旧タイマー解除、新タイマー1本、アンマウント後追加通知なし、既存再接続動作を回帰試験して独立レビュー/PRとする。番号付きGOを受けて先行マージ後、本Icon便を最新mainへ追従し、4ファイル検収/既存全検査/保存前検査を再確認する。既存警告を抑止したり検査を弱めたりする案は採らない。現時点では修正実装・承認・新GOを記録しない。


2026-09-11続行受領: 上記別PR修正案へのPO原文「次を進める」を受領。依存不足を別PRで先に修正する作業を開始する。番号付きGO/マージ承認としては記録しない。元Icon便のstage/未保存変更は保持し、先行修正へ持ち込まない。


## 2026-09-11 最新mainで再開

PR3426をmerge5de8afa1でマージ済みとroot直接確認。保留分を保存後にmain追従/復元、製品競合0・文書4競合を双方保持で解消。StatusBarは前Icon版へ既反映callback依存1行を加えた内容と一致。rootがこれを文字列全体で比較した。旧検収は旧基準の結果として保持し、最新基準の検収は以下に別記する。


### 最新基準の検収結果

基準5de8afa1。Generatorが再実行し、厳格eslint（max-warnings=0）、unit20ファイル179試験、check:all（0errors/218warnings）、製品build、Storybookの5コマンドすべてexit0。[今回ログ](icon-contract-resume-checks.txt)。旧162試験の結果を最新として流用していない。

[今回の対象一覧・表示結果・4製品manifest](icon-contract-resume-evidence.json)。before152→after163、既存欠落0、追加11は新規テストJSX。実運用分類118箇所39ファイル、style/colorとも0。rootが別のPythonでfile/tag/出現順を突合し、既存属性差分がStatusBarのstyle→class1件だけと確認した。明暗×幅390/1280×接続/切断の8条件は全測定属性が前後一致、ARIA6属性は意図どおり出力、document入口1/client入口0/errors0。rootはJSON・ログ・現物hashを直接照合し、全試験を再実行したとは称しない。

再現原稿: [before監査](icon-contract-resume-before-audit.cjs) / [after監査](icon-contract-resume-after-audit.cjs) / [ブラウザー](icon-contract-resume-browser.mjs)。監査は/tmpの別ディレクトリへコピーしSALESANCHOR_AUDIT_REPOを対象worktreeへ設定して実行する。browser原稿には実行時のworktreeと/tmp出力先を保持。正式保存先の横で再実行して過去根拠を上書きしない。SSR局所比較であり、本番全画面/hydrate/理解速度の試験ではない。

限定第二レビュー担当は最新コードと検証内容をAPPROVE。root確認の4SHA256は今回manifestと一致し、StatusBarだけが旧Icon版から先行callback修正1行分更新、他3ファイルは旧レビュー時と同一。前提修正/並行進捗表示/翻訳/依存/CIに対する追加差分0。通常Iconの便は設計自己審査済み・実装検収済み・文書保存済み。PR/リモートCI/新番号付きGO/マージは後続で実状態を記録する。全画面統一とPO画面確認は未完。


PR #3427 提出確認: https://github.com/shingo-ops/salesanchor/pull/3427、ready OPEN、提出HEAD cfb3068b49429672d63dbb84d41be483f40b4bfc、公式.pr-number登録をroot直接確認。製品4/文書24ファイル、保存前検査を迂回せずcommit成功。最新179試験/8表示同値の検収と4hashを維持。番号付きGOは未受領、リモートCI確認が次の一手。マージ/デプロイは未実施。


PR3427提出後のmain追従: 並行PR3425のmerge4774d774を取り込む。追加main差分はbackend4/文書4、frontend差分0。根拠台帳1件の追補競合を双方の全文を保持して解消。既検収frontendツリーは同一、backendは最新mainと同一。今回のフロントエンド変更へbackend差分を追加したものではない。最新HEADのCIを再確認する。


PR3427最終確認（GO前）: head2031cfa30241bee576f34b540a3b4d0e6fa2af63、GitHub checksは37成功/8対象外/1失敗。唯一の失敗process-artifacts gateはjob103121703805のログでGO記録セクション欠落と直接確認。新番号付きGOは未受領、技術検査は成功、未マージ。根拠: /tmp/frontend-icon-resume-20260911/pr-checks-list.json と process-artifacts.log、https://github.com/shingo-ops/salesanchor/actions/runs/34553691458/job/103121703805 。製品frontendはcfb3068bと同一、backendは最新main4774d774と同一をroot git diff exit0で確認。台帳は公式ledger-updateでREVIEW。送信の初回自動審査拒否は送信先/WRITE/既承認範囲の追加確認後に同じ正規審査で承認され解消済み。

この最終CI追記とtasks現在状態はローカル保存し、不要な再CIを避けGO受領後の記録commitに含める。リモート検証対象2031cfa3と未commit文書2件を区別する。PO画面確認/全画面移行は未実施、新CI設置は最後。


PR #3427 GO受領: PO原文「GO #3427」。2026-09-11 12:23 JSTは受領後記録時刻。head2031cfa3のCI37成功/8対象外/残1失敗はGO記録欠落と確認済み。rootが製品4SHA256と検収manifestの一致を再確認。本人原文をPR本文へ転記し、最新CI確認後に公式マージする。DB変更なし、バックアップ該当なし。


GO後main追従: PR3422 merge dd9d3abf の商品画面追加を保持し、根拠台帳の末尾競合1件は両方を保持して解消。root自身が統合状態でunit22ファイル189試験・check:all・buildを実行し全exit0。ログ: /tmp/frontend-icon-resume-20260911/final-main-unit.log、final-main-check.log、final-main-build.log。Icon4製品SHA256は元manifestと一致、main追加差分にIcon利用追加0、backendはmainと同一。局所表示8比較は4製品不変の先行検収結果、追加商品ページの全画面目視を行ったとは称しない。受領済みGO #3427の対象製品差分4ファイルを維持、最終CI後に公式マージする。
