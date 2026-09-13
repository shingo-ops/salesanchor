# GO記録の自動転記（案X）

**この文書は何か（専門用語なしの1行）**: PO がチャットで出した `GO #PR番号` を、実装役が PR 本文の `### GO記録` に転記する案Xの親草案。

**状態**: セッション上の委任時点でGO発行権限が移る方式をPO承認（2026-09-11）。追加GitHub有効化操作は不要。全体設計は自己審査REVISE、検査実装未着手。現在の条件は [design.md](design.md)「セッション委任の成立」。以下の本人発行のみの記述は初期案であり、代理発行は最新節で区別する。


次の一便: 既存チャット画面に入力時の独立記録を接続できるかの限定検証設計。CLI 0.154.0のschemaと公式資料を照合し、履歴readだけでは取消到達性を証明できないことを整理。P2の受信/writer契約とI01〜I08を草案保存、自己審査REVISE。P1実機6/6維持、P2実装・代理GO0。根拠はrecon.md「2026-09-13 入力経路の仕様照合」。


## 2026-09-11 文書保存のマージ方針

PO原文「追従してPRマージを実行」を、直前に提示した設計PR #3418のmain追従・文書保存のマージ指示として受領。全体設計REVISEを維持して草案/根拠/カードを保存する。製品機能の実装合格や制度の本番有効化には読み替えない。番号付きGO原文を創作しない。

P1の限定実装はPO承認後に実行したが、手順3のGitHubアプリによるbranch作成で403 Resource not accessible by integrationとなり停止。再GETでbranch/PRとも0件を確認した。検証workflow未設置、実機試験0件。接続権限が解消した後に同じカードの手順3から再開する。

---

## 1. あるべき姿

- PO の作業は「チャットで `GO #<PR番号>` と言う」だけ。
- 実装役は、その発話を PR 本文の `### GO記録` に転記する。
- gate が見るのは、転記された文字列と PR 番号の一致。

## 2. KGI

| # | 合格条件 | 測り方 | 合格ライン |
|---|---|---|---|
| 1 | GO記録の転記が PO 発話と一致している | PR本文の GO原文と PO 発話を見比べる | 不一致 0 |
| 2 | GO記録4欄が空欄にならない | 4欄の記入有無 | 空欄 0 |
| 3 | 実装役が GO を作らない | GO発話の起点が PO かどうか | 代筆 0 |

## 3. recon

- [recon.md](recon.md)
- gate 本体は `scripts/check-process-artifacts.js`
- `GO発行者` は GitHub の本人承認ではなく、PR本文の文字列 allowlist で検証される

## 4. design

以下3項目は旧草案。PR作成前のGO取得を要求する意味には使わない。2026-09-10の正規ルート・設計範囲・未解決事項は [design.md](design.md) を参照する。

- `docs/ai-agents/design-partner.md` の §6 に合わせて、GO記録の 4 欄は「PO発話を実装役が転記する」運用にする
- 機械的歯止めは置かず、誤転記と偽造は人手確認と governance 監査で扱う
- `### GO記録` は空欄のまま PR を止め、PO が自分で `GO #<PR番号>` を書き込む発効手順を別運用で担保する

## 5. 弊害・トレードオフ

- 機械が本人性を証明しないので、誤転記やなりすましを完全には防げない
- その代わり、PO の実作業は軽くなり、GitHub を開かずに運用しやすい

## 6. 外部・過去事例

- 該当なし＋理由: このテーマは自社の運用設計であり、外部事例よりも `docs/handoff/go-record-transcription/recon.md` の実測と関所の実装を優先する

## 7. 受入基準

| 基準 | 検証方法 |
|---|---|
| 親草案から recon に辿れる | 相互リンク確認 |
| docs/specs/README.md に索引がある | 行追加の確認 |
| design-partner の §6 と矛盾しない | file:line 突合 |

## 8. 維持の仕組み

- 人手と governance 監査で守る
- 仕様の変更は本 README と recon の双方向リンクを保ったまま行う

## 9. 2026-09-10の設計範囲合意

POが指定した正規ルート: PR作成 → PR番号確定 → POがGO発行 → 実装役がPR本文のGO記録4欄に転記 → マージ前にGO確認。

提案した範囲: 「『GOなしを必ず拒否』を満たすため、GitHub画面からの直接マージの制限まで設計対象に含めてよいですか？ 推奨しますが、POのマージ操作にも影響します。これは設計範囲の確認で、設定変更の承認ではありません。」

PO返答原文: 「合意」。2026-09-10、本設計セッションで受領。

これは設計範囲への合意であり、特定方式の承認・実装開始・Rulesetやsecrets変更・PRマージのGOではない。

- 現在地と証拠: [recon.md](recon.md#2026-09-10の再実測)
- 設計候補と自己審査: [design.md](design.md)
- L1 time-handlingの実装とは別ブランチで管理する。

### 文書公開の承認

2026-09-10、「未承認の設計草案を含む文書7ファイルを、公開リポジトリ shingo-ops/salesanchor へpushし、PR提出してよいですか？」という確認に、POが「GO」と返答した。公開・PR提出への承認であり、設計方式の採択・実装・設定変更・マージのGOではない。PR番号付きのGO記録として転用しない。

### 文書PRのマージ承認

2026-09-10、PO発話原文「GO #3388」を受領。対象は文書PR #3388のマージ。PR本文のGO記録4欄へ転記した。方式の設計合格・製品実装・Rulesetやsecrets変更の承認ではない。

### 改訂2の設計継続

PR #3388は2026-09-10 10:09:40 JSTにマージ済み（5316315fa1356d637a54d23ac2ad7ffe270260fd）。続くPO発話「進める」を設計継続として受領。design.md改訂2に専用経路とGO取消期限の選択肢を記録した。この設計継続時点では方式採択・実装承認は未受領。その後の取消期限への合意は次節に記録。自己審査REVISE、実装カード未発行。

### GO取消期限への合意

2026-09-10、以下の提案説明・確認に対し、PO返答原文「合意」を受領。

> そのため、**最後に確認したGOを、その1回のマージ用に確定する方式**を推奨します。ただし、確定後の本文編集では進行中のマージを取り消せません。
>
> この取消期限を採用して設計を進めてよいですか？

合意の対象はこの取消期限。PR作成→番号確定→POのGO→4欄転記→マージ前確認は維持する。専用Appの採用・運用担当・再GO条件・製品実装・保護設定やsecrets変更・今回文書PRのマージまで承認されたとは扱わない。design.mdの成功条件と比較表に反映し、全体の自己審査はREVISEを維持した。

### 改訂2の文書公開・提出承認

2026-09-10、「改訂文書7件を公開リポジトリへpushし、文書PRを提出してよいですか？」という確認に対し、PO返答原文「続ける」を受領。未承認草案を含む改訂2の文書7件の公開・PR提出を進める承認として記録する。方式全体の採択・実装・設定変更・PRマージの承認ではない。

### 改訂3の設計継続

PR #3394マージ後のPO発話「次を進める」を設計継続として受領。保存・送信・再GOの草案をdesign.md改訂3へ記録。取消期限の合意は維持し、再GOの推奨候補を新しい合意とは扱わない。例外一覧のPO読取結果待ち。自己審査REVISE、実装未着手。

### PO認証の一時読取り承認と結果

「この環境に登録済みのPO認証を今回の読み取りにだけ使い、既定認証や保護設定を変更しない」という提案に対し、PO原文「GO」を受領。main Rulesetの例外0件と旧Branch Protectionなしを実測した。通常認証はshingo-ccのまま。詳細はdesign.md改訂3追補とrecon.md。設定変更・実装・文書公開やマージのGOとして扱わない。

### コミット追加時の再GOへの合意

2026-09-10、直前の提案「GO後にコミットが追加されたら、main取り込みだけでも再GOを必要にする方針でよいですか？」および「推奨します。承認対象を明確にできますが、GOの回数は増えます。」に対し、PO返答原文「進める」を受領。この再GO条件で設計を進める合意として記録する。取消期限とは別の合意。App採用・全PR適用・運用担当・実装開始・外部設定変更・文書公開/マージの承認に広げない。

### PO管理の専用GitHub App方式への合意

2026-09-10、直前の確認「PO管理の専用GitHub Appにマージを集約する方式を採用してよいですか？」と、日常のチャットGOは維持・POが鍵や停止/再開を管理・App障害時はマージ停止・今回は方式採用までで作成/設定変更は別途承認、という説明に対し、PO返答原文「GO」を受領。方式採用とPOの管理責任への合意として記録する。

App作成・鍵発行・Environment/Ruleset変更・実装開始・文書公開/PRマージの承認ではない。保管方式、復旧条件、鍵更新周期、必要権限の検証は設計残件。

### 検証環境の準備案（未承認）

2026-09-10、設計継続の依頼に基づき、design.md「専用環境の検証計画」に検証repo/App・権限上限・費用条件・担当・13試験群・終了条件を保存。外部対象は新設候補で、作成していない。方式採用のGOを鍵/設定変更に転用しない。計画と全体設計の自己審査はREVISE。検証コード仕様と正式カードは未完了、実装未着手、改訂3は未コミット・未push。

### 検証手順と初期作成準備（2026-09-10）

検証処理の入出力・8つの失敗注入位置・10本の試験PR割当（成功merge上限7本）をdesign.mdに具体化。repo1件だけのPO側初期作成手順と読取カードは同一AI自己審査APPROVE。正式card-lint exit 0、構文検査PASS、読取4記録の出力を実測。repo/mainはshingo-cc認証で404、名称の空きは断定しない。全体設計REVISE、製品実装未着手。外部作成への個別承認は未受領。

### 検証repo1件の公開作成承認

2026-09-10、直前の確認「次は **`shingo-ops/salesanchor-go-gate-sandbox` の公開作成1件（初期READMEのみ）を承認しますか？** PO本人の画面操作を想定し、App・鍵・本番設定の変更は含みません。作成後は通常認証で照合します。」に対し、PO原文「進める」を受領した。対象repo1件を初期READMEのみで公開作成する承認として記録する。App・鍵・設定変更・製品実装・PRのGO・文書公開の承認へ広げない。

本セッションのBrowserスキルで必須の操作ツールが利用可能一覧になく、POの画面からの作成は未実施。PO認証をCLI書込みに転用せず、PO画面での作成手順を案内する。追加の作成承認は不要。作成後に既存読取カードで所有者/公開範囲/mainを照合する。

### ブラウザ接続後の状態（2026-09-10）

POの「ブラウザ操作ツールが未接続のため→接続して作成してくれ」を受け、利用可能な別のブラウザ接続でGitHubの新規repo画面へ移動した。ログイン画面への遷移を実測。ブラウザ接続は成功、shingo-ops認証は未確認。POへ画面でのログインだけを依頼し、パスワード・認証コードの提供は求めていない。repo作成承認は維持し、作成自体は未実施。証拠 /tmp/reports/TH-GO-BROWSER-CONNECT-RESULT.json。

### 検証repo作成・照合完了（2026-09-10）

POがshingo-opsとしてブラウザにログインした後、作成画面のOwner/名前/Public/READMEあり/追加ファイルなしを照合し、承認済みの1件を作成した。POの後続指示「不明点は推測で進めることを禁止するので停止して質問してくれ」も受領。以後も不明を補完して外部操作を進めない。

- URL: https://github.com/shingo-ops/salesanchor-go-gate-sandbox
- repo_id: 1363676622、created_at: 2026-09-10T07:26:07Z
- visibility: public、default_branch: main、初期HEAD: a815d94c535f59fae6415b881296d64ef17bf6c7
- ファイル: README.md 1件のみ。通常CLIのshingo-cc認証でGET照合済み。shingo-ccはpull=true/push=false/admin=false。
- App・鍵・Environment・Ruleset・workflow・共同作業者は本便で作成/変更していない。main protected=falseは初期repoの観測値であり、検証環境全体の準備完了ではない。
- 根拠: /tmp/reports/TH-GO-SANDBOX-CREATED-VERIFY.json。全体設計REVISE、製品実装未着手。次工程のApp作成/鍵/設定変更は本便のrepo作成承認に含めない。

### App登録の読取調査・適用対象の確認（2026-09-10）

GitHubの実フォームで登録項目と権限欄を照合。秘密鍵生成時の端末ダウンロードと「端末保存なし」案の不整合を明記し、鍵管理は未確定として停止。App/鍵は未作成。POのマージ・デプロイまでの依頼を受領し、対象がGOフロー修正かL1時刻統一か確認中。両既存head branchのPR検索は0件。回答までマージ・デプロイを実行しない。設計全体REVISE、製品実装未着手。

## 2026-09-10 L1 PR #3404のGO受領とmain追従

POは対象を確認する質問へ「両方とも許可する」と回答。GOフロー修正とL1時刻統一のマージ・デプロイまでを対象として確定した。GOフロー設計全体のREVISE、App鍵受渡し未確定は維持する。

L1は既存実装を確認しPR https://github.com/shingo-ops/salesanchor/pull/3404 を作成。対象はFedEx/SA-02のJST定数参照2ファイル（5行追加・4行削除）。PO原文「GO #3404」をHEAD e4f88d5b7bf2583c43fb3782294a6b61229e9112への承認として受領し、4欄へ転記。必須CI12件とGO転記後process-artifacts gate成功をAPIで確認した。ローカルruff/構文解析/diffチェックは成功。引継ぎのpytest20件成功は他者報告であり、今回のローカル再実行ではない。ローカルBanditはPython3.14の内部エラーがあり全静的検査成功とは扱わない。GitHub上のbackend lint/pytestは成功。

マージ直前にmainがPR #3403で前進しBEHINDとなったため、マージwrapperは実行せず停止。mainを通常取り込み、de9d474aa60886a5c0563a80bd772e89de200517をpushした。差分は同じ2ファイル、5行追加・4行削除。旧GOはPR本文の過去HEAD記録へ移し、現HEADに適用しないと明記した。合意済みの再GO条件に従い、最新CI確認と再GOが必要。L1は実装済み・PR提出済み・旧HEADのみPO承認済み・マージ/本番反映未実施。設計文書はローカル草案であり改訂3のPR未提出。

根拠: /tmp/reports/TH-L1-3404-AFTER-GO.json、TH-L1-3404-MAIN-RULES.json、TH-L1-3404-PRE-MERGE.json、TH-L1-3404-MAIN-ADVANCE.txt、TH-L1-3404-MAIN-SYNC-2.txt、TH-L1-3404-SYNCED.json、TH-L1-3404-PUSH-2.txt、TH-L1-3404-REGO-PENDING-EDIT.txt。マージカードはcard-lintのL31に従い追記出力へ修正後、違反0件（L24警告のみ）。

## 2026-09-10 予約制の既定化依頼

POから既定の予約制とガード追加の依頼を受領。design.md末尾へ契約・ガード文案・10項目の受入条件・自己審査を追記。REVISE、実装未着手。次予約の解放時点はPO判断待ち。L1 #3404の再GO待ちは継続。

## 2026-09-10 予約解放条件のPO合意

「本番デプロイ成功後に次予約へ進む。失敗時は後続停止」の提示にPO原文「OK」を受領。design.md末尾へ状態・照合契約と試験6件を保存。解放条件は合意済み、全体自己審査REVISE。ガード/CI未反映、L1 #3404の再GO未受領。

## 現行の予約方針（2026-09-10）

マージ前に予約し、処理中も後続受付可能。通常は本番デプロイ成功後に次へ渡す。マージ前の確定失敗は順番を返し、修正後に最後尾へ再受付。PO承認した緊急PRは待機列先頭へ移動し、実行中は中断しない。詳細・PO原文・検証条件・残件はdesign.md「現行の予約契約（失敗・緊急優先）」へ集約。全体REVISE、ガード未実装。L1はGO転記済みだがmain前進でBEHIND、未マージ。

## 2026-09-10 cxastrago同条件の委任依頼

POの委任依頼を受領。実物モードはLINE限定・代理GO未有効で、GO制度自身は対象外。正式委任記録/対応済み承認経路がないため代理GOは発行しない。詳細はdesign.md末尾。既存の読取・設計権限は継続。

## 2026-09-10 委任範囲の追加確認

GO制度そのものを含む委任の意図をPOが確認。対象確認を再要求しない。正式有効化/代理GO経路は未整備。design.md冒頭に現在の合意・実物・残件と実装前の順序を集約。deploy.ymlが実行時origin/mainへ更新する実測制約を追記。全体REVISE、文書草案提出の準備中。

## 設計改訂3の提出（2026-09-10）

https://github.com/shingo-ops/salesanchor/pull/3418 を作成し、.pr-numberとhead指定検索で一致確認。初回HEAD0546b8b86358a2d5d182dab9b39de829d01dd7a9。差分は設計・調査・台帳6ファイルのみ。card-lintのDraft禁止に従い通常PRとして提出したが、内容は設計草案、同一AI自己審査REVISE。制度実装・代理GO有効化・マージの承認を兼ねない。main由来の台帳追記は双方保持、同由来の他テーマログの末尾空白は変更せず本PR差分をmain基準で検査。検査ログは /tmp/reports/TH-GO-REV3-PR-CARD-LINT.txt、TH-GO-REV3-PUBLISH-DESIGN-CHECK.json、TH-GO-REV3-FINAL-TASK-CHECK.txt。

## L1 PR #3404の本番反映完了（2026-09-10）

PO原文「GO #3404」をHEAD45b9ae3677153002952bceee77a63972484d47c4へ受領。受領確認21:40 JST、GO4欄へ転記。最新の必須13件とprocess-artifacts gate成功、CLEANを確認して既存gh-pr-merge-safe.shへ --merge --match-head-commit を渡した。GitHub実測: mergedAt2026-09-10T12:42:19Z、mergeCommit df3c2a47ed8a89de86246af834b89329133f86d6。親に承認HEADを含み、差分はFedEx/SA-02の2ファイル+5/-4だけ。

Deploy to VPS run34478228420/job102874182347はsuccess。事前DBバックアップ、既存マイグレーション、SA-19 smoke、FedEx Rates smoke、Finalize、Verify deploymentの成功をActions APIで確認。新しいDB変更を本PRへ追加したわけではない。

今回直接実行した本番読取: prod1の /home/ubuntu/salesanchor のHEADがmergeCommitと一致。稼働astro-webapp-backend-1内の /app/app/services/fedex_rates.py と /app/app/tasks/sa02_recon_monitor.py のSHA256が承認HEAD由来の2値と一致。コンテナState.Statusはrunning。https://api.salesanchor.jp/api/health はstatus ok、database/redis/celery connected。DockerのHealthフィールドが存在せず最初のinspectはexit1となったため、成功扱いせずState.Statusのみの再読取とAPI healthを分離した。本文やログへsecretを出力していない。

承認ファイルhash: fedex_rates.py=1d6c6fc464e553318c15324122aced896d5212ff645caa26d03f795ed6ae7812、sa02_recon_monitor.py=2767f444270a938e53a5ad3496e9454fd7880b2e24b9543919c59429302b4876。

証拠: /tmp/reports/TH-L1-3404-MERGED.json、TH-L1-3404-MERGE-PROOF.json、TH-L1-3404-GO3-CHECK.json、TH-L1-3404-GO3-MERGE.txt、TH-L1-3404-DEPLOY-FINAL-RUN.json、TH-L1-3404-DEPLOY-JOBS.json、TH-L1-3404-PROD-VERIFY.txt、TH-L1-3404-PROD-STATE.txt、TH-L1-3404-API-HEALTH.json、TH-L1-3404-RESULT.json。

L1状態はPO承認済み・マージ済み・本番反映照合済み。wrapperでL1worktree/ローカルbranchを整理、公式ledger-lookupでDONEを確認。GOフロー設計PR #3418は別テーマとして未マージ、全体設計REVISE、ガード/委任経路は未実装のまま。
