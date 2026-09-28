---
mode: handoff
---

# PR作成とマージの審査分離（2026-09-28）

この文書は何か: 提出前に取得できない承認を要求する矛盾を解き、本番へ入れる直前の確認を確実にする設計。
親: [GO記録の手順](README.md)。既存テーマの限定子仕様であり、代理GO制度全体の設計とは区別する。
recon: docs/handoff/go-record-transcription/pr-lifecycle-recon.md
対象ADR: ADR-113、ADR-121、ADR-135、ADR-136。
PO提示: 「PR作成時は設計・検証を確認し、番号付きGOはマージ直前に必須確認する」修正方針。
PO応答原文: 「よい」。本セッションで受領。方針承認であり、未発行PRの番号付きGOや代理委任有効化を意味しない。

## 目的・境界

成功条件はGO未発行の適正なPRを提出でき、GOなし/対象違い/検証失敗時のmerge送信が0になること。
変更はPR作成wrapper、本文構造validator、merge wrapperと限定helper/テスト/設計台帳。
CI full gateのGO要件、Ruleset、認証、hooks/trust、GO発行権、製品機能、DB、deploy.ymlは変更しない。
既存のAI委任制度案全体はREVISEのまま。今回その本人性・期限・予約・本番障害復旧機構を実装しない。

## 観測とWhy

LINEガイド実装は単体17/E2E6+可視範囲2成功、87c4ad83aまでGitHub保存済みだが、PR作成hookがGO欠落で拒否した。
adapter.py:639-661は対象worktreeのvalidate-pr-body.shを無引数で呼ぶ。adapterや個人設定を編集せず、正本の本文審査を修正できる。
validate-pr-body.sh:283-324は番号未発行でも番号付きGOを要求し、実PR番号との一致は確認できない。
create wrapper:26-42はCI専用のfull checkerを入力無しで実行し、BASE_SHA/HEAD_SHAの不足も発生する構造。
merge wrapperは所有権を確認するが、送信直前のGO審査なし。main自動追従後も同じGOで再送する。
外部事例は不要。自社スクリプトと実拒否を根拠とする限定的な手順修正で、効果数値を創作しない。

## 採用設計

1. 本文validatorはPR作成/編集の準備検査に限定し、検査1〜9を保つ。検査10のGO必須判定をマージ前のfull gateへ移す。
   repo/diff取得不能は合格扱いせず失敗にする。本文検査中のnetwork fetchはやめ、存在するorigin/main...HEADの実diffを使う。
   提出wrapperが先にfetch/参照確認する。hookは読み取りで素早く判定できる。
2. create wrapperは必須bodyを実際に読み、準備validatorへstdinで渡す。body-file/inline body両方、値欠落/二重指定/stdin '-'は拒否。
   base=main/head=current releaseまたはhotfix、実HEAD/remote head一致、認証作者shingo-cc/Hikky-devを確認。
   GITHUB_ACTIONSの素通りを除く。任意repo overrideは禁止し、既存originを対象にする。PRはreadyで作り、成功後register-prを維持する。
   この入口からfull checkerを呼ばない。作成成功はGO取得やCI合格を意味しない。
3. merge wrapperは既存.pr-number/台帳の所有権照合を残す。merge commit方式のみを受け入れ、admin/auto/squash/rebase/別repo/別PR指定を拒否。
   既存の自動main追従・再送は停止へ変える。HEAD変更後は再検証とPO再GOが必要という既存ルールを守る。
4. 新helper scripts/dev/check-pr-merge-ready.py が実取得/厳格検査/送信/結果照合を1回だけ担当する。
   subprocess argvで実行し、shell文字列連結は使わない。外部書込は正常ケースのgh pr merge 1回だけ。
   GitHubから実PRのnumber/state/baseRefName/baseRefOid/headRefName/headRefOid/author/body/reviewDecision/mergeStateStatusを取得。
   PR番号一致、OPEN、非draft、base=main、head=currentbranch、許可作者、local HEAD=origin head=PR head、clean作業机を必須にする。
   BASE_SHA/HEAD_SHA/PR_NUMBER/REPO/HEAD_REF/BASE_REFを実値で固定して既存full checkerを --validation-only で実行する。
   MOCK_*、CHANGED_FILES等のchecker入力上書き値は継承せず、CIで使う同じGO判定を省略なしで実行する。
   必須checksは全成功を要求。reviewDecisionがCHANGES_REQUESTED/REVIEW_REQUIREDなら拒否。AIレビュー記録は別の人手ゲートとして維持。
   最後にPR/HEAD/base/bodyを再取得して検査した値と同一と確認し、gh pr merge --merge --match-head-commit 検査済SHAを1回送信。
   BEHIND/競合/取得失敗/値変化なら送信せず停止。送信結果不明なら再送せず照合結果を報告。
   成功後はMERGEDと対象head/mergeCommit/mergedAtを実取得し、確認できた場合だけwrapperの既存後片付けへ返す。
5. check-process-artifacts.jsには --validation-only だけを追加し、緊急モード時のfollowup Issue起票を行わず検証だけ実施できるようにする。
   全検査条件と通常CIの振る舞いは維持。merge helperは必ずこの検証専用モードを使う。CI workflowは変更しない。GO待ちPRのCI赤は予定された状態。

## 非保証とリスク

既存full checkerはGO文字列と実PR番号の一致を確認するだけ。本人認証、GOとHEADの暗号的結合、委任期限検証を実装済みとはしない。
--match-head-commitは確認したhead以外のマージを防ぐ。GO原文が過去HEADに対するものかの判断は既存の再GO手順で維持。
repo側コードをPO判断無しで自分の認可根へ昇格しない。本便は明示承認された手順修正として検証・レビュー・PRを経る。
自動追従をやめるためBEHIND時は停止が増えるが、異なるHEADを同じ承認で送らないことを優先する。
外部API readとmerge送信の間に全状態を原子的に固定する保証はない。GitHub保護とSHA一致を併用し、専用代理承認基盤は対象外。

## 受入条件と守り手

既存node scripts/tests/test-process-artifacts.jsを全件成功させる。既存GO条件を弱めない。
既存bash scripts/tests/test-merge-safe-guard.shは鍵欠落/空を残し、BEHINDの期待を自動追従から停止へ改める。
新規scripts/tests/test-pr-lifecycle.pyは一時git repoと偽ghを使い、全外部要求を記録する。実ネットワーク/本番変更は0。
create: GOなし正しいbodyは提出1、body欠落/構造/diff/作者/remote不一致は提出0。
merge: GO欠落/番号違い/作者違い/API失敗/closed/draft/wrong base/head/dirty/local-remote不一致/checks失敗・pending/拒否レビュー/BEHINDは送信0。
環境のMOCK/CHANGED_FILES等で否定ケースが通らないこと。正常のみ--mergeと検査SHAを伴う送信1。
直前HEAD/body/base変化は送信0。応答不明時の再送0。MERGED確認失敗時のcleanup0。
維持: 上記3テストと変更shellのbash -n、helperのPython構文、card/doc/taskチェック。

## 実装構造の比較と審査追補

Sol調査はshell内完結を代替案として提示。AstraはJSONの多項目同一性検査、外部呼出の引数分離、応答不明時の状態を見通せるPython helperを採用する。
増分は1ファイルだが、GO判定そのものは既存Node checkerを呼び再実装しない。Shellの所有権検査と成功後の後片付けも維持する。
full checkerの緊急モードには未マージでもIssueを起票する副作用があるため、validation-onlyを明示追加する。判定の免除modeにはしない。
通常CIは従来どおり、validation-onlyで全検査合否が同一かつIssue write0になることをテストする。
Pythonは標準ライブラリだけで実装、依存追加なし。対象repo以外への送信やtest用overrideの利用を製品入口では許可しない。

## 実装前の確定補足

GO要否の分類は既存checkerのユーザー影響/危険変更に従う。書類のみ免除の既存条件を新たなGO制度で上書きしない。今回の修正とLINEガイドはいずれもGO必須分類。
merge helperのrepoはoriginから確認したshingo-ops/salesanchorに限定し、gh --repoを明示してGH_REPO等で別repoを選ばない。
checkerの既存mock入力を全て削除し、CHANGED_FILES/MAINTENANCE_ENFORCE/GITHUB_OUTPUT等も外部継承値を排除する。BASE/HEAD/PR/REPO/refは実取得値で上書き。
ネットワーク・状態・JSON不明時は失敗。cleanは追跡変更と未追跡の実ソースを対象に既存.gitignoreを尊重し、node_modules等の生成物を対象外とする。
Python helperのCLIは内部用の実PR番号と現在branchのみ。任意のbodyやSHAやスキップ引数を利用者が渡す形にはしない。
対応するNode parser/GO判定を別実装へ複製しない。設計記録とPR本文は既存様式を使い、GO原文を生成しない。

## 設計自己審査

AstraがPlanner/Architectを順に担当し、APPROVE（限定設計合格）。独立した第二者審査とは称さない。
根拠はSolのread-only調査、実拒否、現行validator/merge/checker契約、Context7のGitHub CLI公式仕様とローカルhelpの一致。
確認した仕様: --match-head-commitは指定head一致を要求、gh pr checksはpending時exit8。出典 https://cli.github.com/manual/gh_pr_merge と https://cli.github.com/manual/gh_pr_checks。
未解決の実装前提なし。作業枠確保は別の実行前条件であり、空ける際に他者変更を消さない。
実装結果・否定試験・CI・PO番号付きGO・本番反映はこの設計合格に含めない。

維持の限界: 現在GitHub Actionsには既存2テストの呼出がない（Solの限定rg exit1）。今回workflowは変更せず、カードとレビューで3テストの実行結果を必須確認する。自動CI試験を追加済みとは記さない。CI上の既存full gateは継続する。

## 外部・過去事例の参照と我々への応用

該当なし。自社の実拒否と実装を修正するため、外部企業の数値ではなく以下の否定試験を根拠にする。

## 受入基準

| 基準 | 検証方法 |
|---|---|
| 適正な本文のPRをGO前に作成できる | 一時repoの偽ghでcreate 1回、GO記録なしをassert |
| 不適正な本文・対象・作者で提出しない | 否定fixtureでcreate呼出0 |
| GO必須変更でGO欠落/番号不一致ならmergeしない | full checker実行と偽gh記録でmerge呼出0 |
| 検査後にHEAD/body/baseが変わるとmergeしない | 前後2回のGET fixtureを変化させmerge呼出0 |
| CI失敗・未完了・レビュー拒否・BEHINDならmergeしない | 否定fixtureでmerge呼出0 |
| 正常ケースだけ検査済みHEADを送る | --merge/--match-head-commitとHEAD一致、送信1回をassert |
| 検証だけでIssueを作らない | validation-onlyでissue create0、通常checkerの判定維持 |
| 不明な応答で再送/cleanupしない | merge応答失敗・確認GET失敗のfixtureで再送0/cleanup0 |

## 維持の仕組み

守り手: scripts/tests/test-process-artifacts.js、scripts/tests/test-merge-safe-guard.sh、scripts/tests/test-pr-lifecycle.py。
対象: 提出と承認の順序、GOの必須条件、実HEAD/PRの一致、失敗時に外部変更をしないこと。
既存CIのfull gateは継続。上記テストのCI自動接続は未整備のため、カードとAstraレビューで実行記録を人手確認する。

## 呼出契約の確定追補（Astra、2026-09-28）

Solの技術照合で既存caller/CLI入力の具体化が必要と判明。以下を最終契約とする。限定設計の審査はこの追補を含めAPPROVE。

- 既存caller scripts/aeon-release.sh:97 の --merge --delete-branch は --merge に変更する。wrapperは--delete-branchを拒否する。既存成功後cleanupへ片付けを集約し、gh側と二重に削除しない。remote branchの新規削除を追加しない。
- wrapper→helperは正のPR番号とcurrent branchの2 positional引数だけ。helperはgh JSONを自ら取得する。body/SHA/repo/skipを引数で受け付けない。
- helper exit0はmergeコマンド成功かつ実GETでMERGED/対象head/mergeCommit/mergedAtを確認した場合だけ。exit1は送信前拒否、exit2は送信後異常または結果確認不能。非0はcleanup禁止。
- mergeコマンド非0でも確認GETは1回実行し観測結果を報告する。GETがMERGEDでも送信異常としてexit2、再送/自動cleanupはしない。MERGED観測を未マージと誤報告しない。
- --validation-onlyは唯一の追加CLI引数。引数なしは現行CIの処理、未知引数/余分な引数は失敗。typoで通常モードへ落ちてIssueを作らない。
- required checksはgh pr checks番号 --repo 正規repo --required --json name,bucket。非0、非配列、0件、pass/skipping以外は拒否。skippingはGitHubの正規の省略であり、試験実行成功とは区別して出力する。
- reviewDecisionはAPPROVEDまたは空文字だけ許可。空文字はGitHub側レビュー要求なしの場合で、Astra/POのレビューを不要とする意味ではない。
- 本文は--body 値/--body=値/--body-file パス/--body-file=パスを受理。二重指定/空/stdin '-'、非regular file、読取不能、非UTF-8、NUL入りは拒否。
- Shell所有権テストは鍵欠落/空とhelper非0時cleanup0を確認する。実際のBEHIND/GO/checks/送信回数は新lifecycleテストで実helperを一時repoへ置いて確認する。製品コードにtest用差替え入口を追加しない。
- MAINTENANCE_ENFORCE/GITHUB_OUTPUT/CHANGED_FILESと全MOCK_入力はhelper境界で削除、実6値は上書き。認証環境は保持し、--repoの明示でGH_REPOによる別repo選択を防ぐ。

## 入力・送信対象の審査追補（CARD-03）

CARD-02実装はSol試験106/4/10成功だが、追加のread-onlyレビューでREVISE。試験成功を実装合格としない。
以下を先行節より優先する設計契約としてAstraが自己審査APPROVE。実装修正と再検証は未了。

- create/helper/checker/registerのGitHub送信先をgithub.com/shingo-ops/salesanchorへ固定する。ghのPRコマンドにはhost付き--repo、apiには--hostname github.comを指定し、子プロセスGH_HOST/GH_REPOも正規対象へ固定する。既存トークンや認証設定を書き換えない。
- gh help environmentのGH_REPO/GH_HOST仕様と、create/helper/registerの呼出実物が根拠。任意環境で別repoに作成・登録しない否定試験を追加する。
- createは許可した非対話引数だけを解析し、検証済みtitle/body/base/headで送信引数を再構成する。title/body/base/headの長形式、body-file長形式だけを許可し、未知/重複/欠落/明示空値は拒否。省略baseはmain、省略headはcurrent branch。body-file内容は検証した文字列を--bodyで送信する。
- draft/web/editor/fill/template/recover等の本文変更・対話経路は拒否。既存callerが許可外引数を使う場合は変更せず報告する。
- 実repoのSHA形式を確認し、full checkerへ渡すbase/headと比較用local/origin SHAが40桁hexでなければ拒否。文字列を既存Node shellへ流す前に止める。
- merge wrapperのGITHUB_ACTIONS成功skipを除去する。環境名だけで成功にはならない。registerのCI skipもcallerでGITHUB_ACTIONSを継承せず、正常な登録処理を必ず行う。
- required checksはfull checker終了後にも再取得して同条件で確認し、その後最後のPR同一性確認とmergeを行う。passからpending/failへ変化した試験は送信0。全状態の原子的固定を保証するものではない。

根拠追補: https://cli.github.com/manual/gh_help_environment 。確認手段はContext7公式manualとローカルgh help environment。レビュー指摘のdraft拒否はCARD-02最終版では修正済みであり、残る対話経路と再構成を対象にする。

実設定確認追補: 2026-09-28T06:28:31Z、Solがmain適用Rulesetをread-only取得。13必須checks/strict=true/review必須人数0/mergeのみを確認。
process-artifacts gateはサーバ側required一覧に無い。本設計のGO必須検査はsafe wrapper経路の保証であり、UI/直接CLIまで物理強制する保証ではない。
根拠はpr-lifecycle-recon.md末尾。本便ではRulesetを変更しない。reviewDecision空の扱いは実設定と一致する。

## 実装審査結果（2026-09-28）

Solによる追加read-onlyコード/試験審査はAPPROVE、blocking finding=0。
Astraは設計契約、実差分、body保持処理、否定試験コードと実ログを確認し、限定実装をAPPROVEとする。
Planner/Architectの設計審査は同一Astraの自己審査であり、独立した設計審査とは称さない。
実行担当Solの最終実測: Node107 PASS/0 FAIL、wrapper5 PASS/0 FAIL、lifecycle11 methods/OK。
shell/Python構文、task-state、diff-checkはSol実行exit0。Astra直接実行の設計/引用検査はerrors=[]。
初回lifecycleの5失敗は本文末尾改行とfixture経路の不具合。修正後の11成功だけを最終結果とする。
ガード拒否は複合読み取り1回。停止後、Astraが実ログを確認し単独の検査可能な読み取りへ限定。設定変更0、再開後拒否0。
コード根拠SHA256: create=83c14d22ccff1f41e143b4f07894396976abd9418fec0f6ed3951adb98116a08、helper=67b045a0595023650dde0dd0eecefa22cb2f9d4a91f67dd4d6186b899c61066e。
試験証跡: /private/tmp/pr-lifecycle-card03-sol-resume.log の最終出力Node107、wrapper5、lifecycle11。実GitHubへのcreate/merge/issue書込0。
状態: 設計方針PO承認済み、設計審査済み、限定実装/ローカル検証済み。PR番号付きGO・マージ・本番反映は未了。
