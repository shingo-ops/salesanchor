---
mode: handoff
status: design-reviewed
scope: ui-governance-git-read-errors
---

# CI検査不能時の誤合格防止 — 後続CI便の設計

親: [design.md §N](design.md#n-ciによる金型ルールの強制設計2026-09-10構築仕様草案)

> 実施順序更新: PO指定により先行実装しない。画面統一の全体設計と実装の後、最後のCI補強便で扱う。設計の自己審査合格は先行着手の許可ではない。EV-20260910-FRONTEND-MOLD-13参照。

## 目的と合意の範囲

比較元やファイルを読めなかった検査が、変更なしとして合格することを防ぐ。
POの「合意進める」は、CI補強方針への合意・設計続行として記録。第一便の具体的実装開始承認は別。全体の金型化・画面外観の完成を本便の合格と混同しない。

## Why: 確認した根拠

基準コミット6e1335725bb8dfdf390125c4caf5a93f705f4821。取得済みmain 5386d664f40aa826e7e3d943b87bb65697d49165まで本便対象2ファイルの差分なし。

- `scripts/check-ui-governance.js:51`: git show失敗を空文字に置換。
- 同`:66`: git diff失敗を空配列に置換。
- 同`:311`: 対象数0ならexit0。
- 実行再現2件: 存在しないBASE=`0000000000000000000000000000000000000000`/HEAD=`HEAD`と、正常BASE/HEAD=`HEAD`の両方がexit0・対象0・skip出力。[再現ログ](../../handoff/design-system-recon/evidence-20260910/ci-invalid-ref-repro.json)。読み取りだけで再現し製品を改変していない。
- 既存22テストは検出関数中心で上記エラー経路の回帰を検出しない。[22件結果](../../handoff/design-system-recon/evidence-20260910/ui-governance-recheck.log)。
- 既存必須jobは`.github/workflows/ui-governance-gate.yml:32`で同テストを先に実行する。新しいworkflow・依存追加・Ruleset変更なしで回帰試験を運用に載せられる。

この再現はCI本番で常に比較が壊れているという意味ではない。壊れた入力を成功扱いする分岐の証拠。

## 変更対象・対象外

実装ファイルは2つに限定する。

1. `scripts/check-ui-governance.js`: git取得とエラー伝播、終了状態、テスト用の最小公開口。
2. `scripts/tests/test-ui-governance.js`: 既存22件を維持し取得・CLIの回帰試験を追加。

フロントエンドsrc、package/lock、workflow、Ruleset、既存違反一覧、ui-allowの扱い、検出対象と件数比較方式は本便では変更しない。これらは後続設計で扱う。本便は全体設計§NのCI-07を先行して成立させる。

## 契約

### Gitの入力と実行

- 既存環境変数`BASE_SHA`/`HEAD_SHA`を維持。空値は設定エラー。
- 各入力を`git rev-parse --verify --end-of-options <入力>^{commit}`でコミットへ解決する。成功しても返るOIDが1件の40桁または64桁hexでなければエラー。以後は解決済みOIDのみ使う。
- コマンドは`spawnSync('git', args, options)`を使用し、shellを有効にしない。既存リポジトリrootをcwdとする。利用者の入力をシェルコマンドへ埋め込まない。
- 全git呼出しで`result.error`あり、`signal`あり、`status !== 0`を失敗にする。既存Buffer上限超過もエラーになり、部分stdoutを結果に使わない。待ち時間上限は呼出しごと30秒とする（提案する運用上限、実測性能値ではない）。
- 一覧取得は`git diff --name-status -z -M <baseOID> <headOID> -- frontend/src/pages/`。NUL区切りでレコードを読み、パス内の空白・タブ・改行を改変しない。
- 対応する状態: A（basePath=null）、M（両側同path）、D（読み取り対象から除外）、Rと数値スコア（旧path/newpath）。コピーCが返った場合は元pathをBASEとして対応。未知状態・項目不足・空path・末尾切断はエラー。type変更Tは曖昧に通さず検査不能として扱う。
- 既存の`.tsx`とstories/design-system/design-preview除外条件を維持。列挙方法の修正を対象拡張へ読み替えない。
- `showFile(oid,path)`は常に成功した取得内容を返す。失敗ならエラー。BASEなしとして空内容にできるのは一覧でAと判明した場合だけ。既存ファイルが空文字なのは正常な取得結果として許容する。
- DだけのPRはコミット確認・一覧取得に成功してから対象0で成功できる。読めないHEADを削除扱いにしない。

### 終了値とログ

| 状態 | exit | 最終出力の識別子 |
|---|---:|---|
| 有効な比較で新違反なし | 0 | `UI_GOVERNANCE_RESULT status=pass` |
| 有効な比較で対象0 | 0 | `UI_GOVERNANCE_RESULT status=no-target` |
| 既存ルールで新違反あり | 1 | `UI_GOVERNANCE_RESULT status=violation` |
| 設定・取得・一覧解析が失敗 | 2 | `UI_GOVERNANCE_RESULT status=error` |

最終識別子は1実行1回。error時はpass/no-targetを出さない。失敗したstage（resolve-base/resolve-head/diff/read-base/read-head/parse-diff）、対象path、プロセス終了値またはerror.codeを出す。入力値とpathはJSONエスケープし、git stderrの先頭2000文字までを診断補助にする。ファイル全文や環境変数一覧は出さない。既存の違反説明は維持できるが、上記識別子は変えない。

処理関数は結果を返し、CLI入口で終了値へ変換する。テストのために`process.exit`を呼ぶグローバル関数を書き換えない。既存の検出関数exportsを維持し、runner/cwdを注入できる取得関数だけ追加公開する。通常CLIにはテスト専用の環境変数や成功強制オプションを設けない。

## 受入試験（実装後に実行する設計）

既存22ケースに加え、以下16 IDをそれぞれ独立した結果として報告する。各ケースはexitだけでなく内容・識別子・対象path・不要な後続呼出しがないことを検証する。最終件数は38 passed / 0 failedを最低条件とする。追加ケースは許容するがID欠落は不合格。

| ID | 入力・状態 | 期待 |
|---|---|---|
| G01 | BASE未設定 | exit2、resolve-base、git差分取得0回 |
| G02 | HEAD未設定 | exit2、resolve-head、git差分取得0回 |
| G03 | 実gitでゼロ40桁BASE | exit2、resolve-base、no-targetなし |
| G04 | 実gitでゼロ40桁HEAD | exit2、resolve-head、no-targetなし |
| G05 | 正常コミット同士・同一内容 | exit0、no-target、解決済OID表示 |
| G06 | diffがstatus128 | exit2、diff、read0回 |
| G07 | 起動失敗ENOENT | exit2、該当stage、passなし |
| G08 | タイムアウトまたはsignal終了 | exit2、該当stage、部分出力不使用 |
| G09 | Buffer上限エラーと部分stdout | exit2、部分出力不使用 |
| G10 | 新規Aファイルに生select追加 | BASEのshow0回、HEAD読取、exit1 |
| G11 | MのBASE読取失敗 | exit2、read-base、違反判定不実施 |
| G12 | MのHEAD読取失敗 | exit2、read-head、違反判定不実施 |
| G13 | Dのみ | 内容のshow0回、exit0 no-target |
| G14 | R100・空白/タブ/改行を含むpath | 旧/新pathがそのまま各showへ渡る |
| G15 | NULレコード切断・未知status・不正OID出力 | 各入力でexit2、空一覧として成功しない |
| G16 | 有効な空ファイルと許可済ui-allow | 既存の成功判定を維持 |

G03〜05はOSの一時ディレクトリに最小git fixtureを作り実gitとCLI子プロセスで確認し、ユーザーの作業treeをfixtureへ使わない。他は注入runnerで到達困難な失敗を再現する。fixtureはテスト作成した専用ディレクトリだけ管理し、既存リポジトリへの書き込み・ネットワーク・本番操作を伴わない。

検証コマンド: `node scripts/tests/test-ui-governance.js`。既存必須jobでも同じコマンドを通す。実装PRではG03が現行コードで失敗、新コードで成功する結果を添付する。差分に上記2実装ファイル以外の製品変更がないことと、既存22テストの削除0を確認する。

## 代替案と維持

- stderr表示だけ追加: 不採用。CIの成功終了が残る。
- git失敗時にexit1: 機械的には止まるが、違反修正と環境修復を区別できないためexit2とする。
- 先に巨大な検査器へ置換: 本便では不採用。実測済みの誤合格を2ファイルで修正でき、検出対象変更の影響を混ぜずに検証できる。

既存required jobを守り手にする。実装Reviewerはエラーが空結果へ変換されていないことと回帰テストを確認。失敗時は比較元や取得環境を直し、チェックを無効化して通さない。

## 外部仕様との照合

Context7 MCPは利用可能ツール一覧に存在しなかったため、POの代替許可に従い公式資料を2026-09-10に確認。
- [Node v22公式ソースのchild_process仕様](https://raw.githubusercontent.com/nodejs/node/v22.0.0/doc/api/child_process.md): spawnSyncのerror/status/signalとtimeout/maxBuffer。現在CIが使うNode22に合わせた確認。
- [Git rev-parse](https://git-scm.com/docs/git-rev-parse): verify、commitへの型確認、end-of-options。
- [Git diff](https://git-scm.com/docs/git-diff): name-status/-zとrenameの出力。

新ライブラリを導入しないため外部企業の導入事例は不要。一次再現と既存CI接続を根拠とし、障害削減率は推測しない。

## Architect整合検査（同一AIによる自己審査）

判定: **APPROVE（本便の設計のみ）**。

- ADR-144の既存検出対象・増加判定・例外を維持。比較失敗を合格とする規定はなく矛盾なし。
- 2ファイルと受入IDを明示、既存workflowでテストと本体が実行される実物を確認。
- 失敗実測と正常対照あり。新依存・バックエンド変更・保護設定変更への依存なし。
- 取得異常時にPRが止まるのは意図した結果。削除・新規・空ファイルは別に扱う。

未解決の製品仕様は本便にない。正式カードの発行チェック・POの具体的実装承認・実装・PR・CI実測は未実施。全体設計はREVISEを継続する。

## 外部・過去事例の参照と我々への応用

企業事例は不要。本文「外部仕様との照合」のNode22/Git公式仕様と一次再現を使用する。対象ADRはADR-144、reconは [既存調査記録](../../handoff/design-system-recon/recon.md)。

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 検査不能を合格にしない | G01〜G09/G11/G12/G15、exit2と結果識別子を照合 |
| 正常な追加・削除・名称変更を維持 | G05/G10/G13/G14/G16と既存22ケースを実行 |
| 変更範囲を守る | 対象2ファイルの差分、既存22ケースの削除0を確認 |

## 維持の仕組み

守り手: `.github/workflows/ui-governance-gate.yml`
既存jobが検査テストと本体を実行する。新しいテストが実際のPRで通るまで実装合格とはしない。

## 引き継ぎの状態

[実装前確認カード](../../handoff/design-system-recon/CARD-FRONTEND-MOLD-CI-RECON-01.txt)の読み取り確認を、POの明示的な委任合意に基づき別エージェントへ依頼し完了した。修正版83行・card-lint exit0。旧fetchは書込権限不足で停止したため、権限を広げずリモートSHAの読み取り照合へ修正した。

[担当の実行報告](../../handoff/design-system-recon/evidence-20260910/ci-executor-recon-report.json): 手順0〜9の出力とexit受領、既存22件成功、異常BASEの誤合格を再現、正常対照一致。リモートmain 7e3dd6565bc8b239ee09967961326fd096fb72feと対象3ファイル差分0。設計担当も設計worktreeで当該差分0を直接確認した。これは実装前の実測であり独立した設計レビューではない。

実装カードの確定と具体的な実装開始承認は未完了。製品・CI未変更、実装未着手。以前の「別AI未起動・結果未受領」は過去時点の記録であり、現在地は本節とEV-20260910-FRONTEND-MOLD-12を参照する。
