# AQ 日報フォーム2ボタン実装・検証

設計: [design.md §AQ](../../../specs/design-system/design.md)。調査: [recon](../recon.md)。対象ADR: ADR-113/067/027/073/122。

## 範囲と状態

基点 main: 4bad43a4dca6368ffa7370792a3c912e90bba521。Astraが設計・自己審査、POの明示委任に基づきSolが調査・実装。設計合格とPOの番号付きGOは別であり、新規GOの原文は作成していない。

StaffReportsPageの取消・追加2件だけを既存Buttonへ移管し、実ページの回帰試験1ファイルを追加。製品はページ1＋試験1の計2ファイル。DB・API・共有CSS・デザイントークン・翻訳・依存・CIの変更なし。画面表示・実ログイン・本番フォーム操作・PO目視はPO指示により省略であり、合格としない。

## 検証根拠

- root直接確認: 2置換とimportの逆変換で旧ページ全文byte一致。対象外の追加ボタン原文維持、共有14ファイルhash一致。AST再計数は共通201→203、旧296→294。
- Sol実行、rootが原ログを読取確認: 対象unit 2ファイル29試験（新規17＋既存Button12）、全体36ファイル501試験成功。coverage statements15.02%、branches13.65%、functions13.69%、lines15.22%。strict ESLint、check:all、本番build、Storybook buildを実行。最終終了値はすべて0と担当報告・原ログを照合。REVISE後は試験のみ変更のためstrict ESLint/unit/coverageを再実行し、check:all/build/Storybookは製品ページhash不変に対応する前回結果を使用。
- 試験は日/週/月の5キー送信、必須入力、改行、取消・再開、X/Esc・焦点、失敗後再試行、待機中2送信、待機中取消後の成功/失敗、権限、GET絞込を確認。APIはmock、実DBへの書込なし。
- 全体lintは0 errors/140 warnings。依存導入は24 vulnerabilities（low1/moderate7/high9/critical7）を報告。今回修正済みとはせず、依存/lock変更もしていない。

## 初回失敗

初回unitはsandboxのEPERM。権限付き再実行後、新規試験のlabelのhtmlFor仮定、Modal外のerrorの探索位置、未登録matcherが不一致。担当が既存DOMを照合し新規試験のみ補正して再実行。初回・再実行・最終ログをすべてaq-validation-logs.tar.gzに保存し、aq-validation-manifest.jsonでhashを固定。製品仕様変更、試験skip、既存試験の期待値変更なし。

## 次の一手

Sol第二レビューAPPROVEと全品質結果確定後、文書と実装を保存しPR作成・CIへ進む。本番投入前は正式なGO記録と対象HEADの検証が必要。今回のマージ・本番反映は未実施。残り旧294件と表・報酬3件・カレンダー色は別便。新規CI追加は移管の最後。

## 第二レビュー・検収確定

Sol read-only第二レビューは初回REVISE。空白原値、pending両ボタンの有効/aria-busyなし、filter下POST後GETの3点を新規試験へ補強し再レビューAPPROVE。レビュー担当自身のunit実行はsandbox EPERMで未実行、コード静的審査と担当ログ読取を行った。Astraは逆変換byte一致・共有14hash・対象外原文を直接再検証し、改訂後29/501成功の原ログを読取確認した。自己審査とSol第二レビューを区別する。

実装担当の初回報告にはcoverage件数488/1892という誤記があり、rootの原ログ照合で訂正・撤回した。正確な初回は36ファイル500件、改訂後は36ファイル501件。ログの数値を正とし、誤報を根拠には採用していない。画面省略という検証限界を残して実装検収APPROVE。

## 2026-09-28 保存とPR前検査の停止

実装/設計/検証13ファイルをf1935c24f1c6f4d0e40a5267cb75853ceac498a2でcommit/push済み。git ls-remoteでremote一致。gh pr list --head release/frontend-next-button-batch --state all --json number,url,state は []、PR未発行。未追跡frontend/coverageはローカル検証生成物でcommit対象外。製品2hashは保存前後一致。

公式 scripts/dev/validate-pr-body.sh に実差分13ファイルを列挙した本文をstdin入力したところexit1:

> ❌ ユーザー影響変更があります。PR本文に「### GO記録」セクションがありません
> → frontend/src / backend/app/routers / backend/app/services の変更は Shingo の GO 記録が必要です

実物の検査10（283行以降、309–321行）はGO節/発行者/原文/番号形式を要求する。新PR番号が未発行の段階で番号が必要な循環がある。またgh-pr-create-safe.shはPR生成前にcheck-process-artifacts.jsを実行するが、同checkerはBASE_SHA/HEAD_SHAとPR_NUMBER/REPOから既存PR本文を取得する構成（665–746行）。包括許可を番号付き原文へ代筆できず、別コマンド/skip環境変数でチェックを回避していない。PR/CI/マージ/本番配備は未実施。

次の一手（草案・未承認）: PR起票時の書式/範囲検査と、マージ直前の番号付きGO検査を分ける。GOなしでもPR番号を取得できるが、GOなしのmainマージは従来どおり拒否する設計を正式審査する。承認/CIを弱める変更はしない。対象は承認経路でありAQカード外のため、scripts/CI/ガード本体は変更していない。仕様・テスト・運用の正式な設計とPO判断後に別便で扱う。本番への投入再開は承認経路の解決、今回番号付きGO、最終HEADのCI成功が条件。
