# AT フォームButton移管・実装検収

設計: docs/specs/design-system/design.md §AT。基準a1cd9ea379cc7d85b797cca6b1cc092192296bc3。Astra設計/自己審査、Sol調査・分離実装。POの条件付き続行・担当委任指示に基づく。代理GOは未有効。

## 変更と境界

9製品11ボタンを既存Buttonへ移管。変換はimport/タグ/className→variant/sizeのみ。root直接監査で9file全byte逆変換、対象11、対象外221、共有18不変、構文0を確認。AT単独で共通265→276、旧232→221。API/DB/権限/handler/配線/翻訳/CSS/共有部品/CI変更0、新データ保存先0。元からあるPO supplier複製とpublic master書込は変更せず、本番への実保存試験は実施しない。

## 検証

root直接実行: 関連既存4suite59試験成功。全体coverage46files631試験成功（statement26.79/branch23.01/function23.36/line27.83%）。check:all成功（既存warning140/error0）、Storybook成功。初回buildは新規Admin試験のHTMLElement.value型エラー5件で失敗、製品障害とは区別し原ログを保存。修正後の結果は追記する。

Sol担当実行原ログ: Commerce11試験、Account/Company/Admin14試験、strict ESLint成功。rootがrawと実試験内容を確認し、不足していた非空/数値変換/guard分岐/再取得/required/再試行の期待を補完。型検査・交差レビュー・最新main統合後の最終結果をもって検収確定する。

## 調査・検証中の訂正

- bare btn-smのsecondary推測を撤回し60件を対象外へ。
- Invoice submitは非JPY時外部FX APIを参照するため対象外。Roles権限保存も別便。
- Buttonはtype既定値なし。商品payloadは34キー。誤記を実ソースで訂正。
- Company/Profileの実hook/providerを利用。refreshをnoopにするmockは禁止。
- Sol2初回4fail/6passはAuth mock参照とselector曖昧さ。実物根拠で試験fixtureだけ補正しログを保持。
- rootレビューで「試験成功」だけでは計画受入を満たさない不足を発見し、送信全項目/変換/空値/再試行/pending/GET差分を補完。

## 状態と残件

設計案・設計自己審査済み、11件実装済み。最終検収/PR/番号付き本人GO/マージ/本番反映は未完了。画面・本番ログインフォーム・PO目視はPO指示で省略・未検証。残旧221、表、報酬3件、カレンダー色、最後のCI補強は別設計。営業効果や全KGI達成は主張しない。

初回buildの5型エラーは実input配列の型指定2箇所で解消し、root再build成功。Sol2→Sol1交差レビューAPPROVE。Sol1→Sol2の予備指摘（再試行payload/成功callback/再GETの不足）を試験だけ補完、14試験とstrict再成功。rootの追加25件再実行と逆変換、最新main統合後の最終品質を確認する。

root追加25件再実行成功、最終逆変換監査pass。Sol両方向交差レビューは最終hashでAPPROVE。最新main統合と全体最終品質のため保存へ進む。


## 最新main統合後の最終検収

origin/main 638cc6f91025c623a9ab47032b9466cdb03e3cffを正規merge。AT対象製品差分0、他便PR3831がLINE案内へButton1件/翻訳キーを追加している。今回の移管11件と別計数し、統合後は共通277/旧221。対象9逆変換・対象外221・共有18（翻訳2は統合mainのhash）一致、構文0。原監査はat-final-audit-result.json、統合監査はat-main-integration.json/at-integrated-audit.cjs/at-integrated-audit-result.jsonに区別。現在の再現コマンドはnode docs/handoff/design-system-recon/evidence-20260910/at-integrated-audit.cjs。

root最終: 47files634試験成功（coverage、maxWorkers=1、時間上限変更なし）。統合初回は631成功/3タイムアウト(5000ms)、失敗の既存RoleKnowledge試験と関連製品の差分0を直接確認。同時実行数だけ1へ変更した全体再実行で合格。初回失敗原ログを保持し性能問題の恒久解消とは主張しない。check:all error0/warning140、build/Storybook成功、許可12製品・試験ファイル以外の製品差分0、backend/API/DB/scripts/CI変更0。レビュー後追加25試験もroot直接成功。

Astra実装検収APPROVE。Sol両方向交差レビューAPPROVE（記録はat-sol1-review.md/at-sol2-review.md）。初回build型エラー、fixture4失敗、レビューで追加した期待、統合タイムアウトを隠さず保存。PO指示で本番画面/フォーム/目視は省略・未検証。設計・実装・ローカル検収・文書保存済み、PR最新CIと本人番号付きGO/マージ/配備は次段階。


## PR保存と再開点

PR #3839（https://github.com/shingo-ops/salesanchor/pull/3839）を公式create-safe経由で提出、.pr-numberとGitHub head branchの一致を直接確認。初回提出HEAD37f37475a47c1822ccf8a7905a5206ef6166766a。CIのprocess-artifacts gateは本人番号付きGO欄が無いことだけで停止（job108946092604、2026-09-28T13:19:54Z）。他の技術検査は提出後に順次実行。今回の番号付きGO原文は未受領、過去GO #3834を流用しない。広域の続行許可は受領済みだが、現行の番号照合を迂回/改変しない。

直前バックアップの読取確認: 2026-09-28T13:16:17.766798Z、/home/ubuntu/backups/postgres/salesanchor_db_20260928_214745.sql.gz、229641593bytes、gzip -t exit0。マージ直前には改めてHEAD/CI/バックアップを確認する。画面確認は省略・未検証。

再開手順: 本worktree release/frontend-form-button-batchでpreflight→.pr-number/GitHub PR head・state/未保存差分照合→最新CI確認。本人からGO #3839受領後のみ原文転記し、正式merge-safe --merge→Deployログ→本番HEAD/公開asset hash/HTTP/接続状態を確認、結果は別文書便で保存。権限・鍵の変更、代理GO発行はしない。
