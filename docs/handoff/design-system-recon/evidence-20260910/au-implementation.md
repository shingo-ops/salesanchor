# AU 旧ボタン221件の共通部品移管

> 個別ボタンを登録済み部品へ置き換え、元の操作を維持したことと未検証部分を記録する。

親: [design-system](../../../specs/design-system/README.md)。設計: docs/specs/design-system/design.md §AU。基準303c3cfe756b1d82c042cba342c3a3150fc5ab8c。

## 実装と成果

対象221件/71fileを移管（native213、Router Link1、anchor7）。root直接AST監査で旧221→0、共通Button494/共通ButtonLink8、全221の非外観属性/children/handlerを維持。共有HeaderButton内部のButton1件は利用側213とは別計数。対象外179native原文は不変。ButtonLinkは既存§Z設計に従い登録/実装、型でhref/to排他、anchor/Routerと外部target/rel/download/refを保持。Button.cssとbuttonAppearance.tsを単一の外観正本として共有する。

HeaderButtonの間接旧CSS依存を削除前に発見し停止、追補設計後にtext3variantだけButtonへ委譲、icon-btnは維持。3storyの旧6件も移管して旧CSSを撤去。71file逆変換はGoalSettingの審査済みi18n2コード差分を明示的に戻したうえで全byte一致。ja/en追加はgoals.advisorRecommended1keyずつ、その他キー完全一致。DB/API/配線/認可/業務handler/依存/CI変更0、データ保存先追加0。全旧CSS利用0はHeaderButton/Storybookを含む検索を実施して判定した。

## 根拠

- au-inventory.json/md: 全221原文・file:line・対象外native。
- au-transform-plan.json、au-page-changes.json: 全221変換とimportの固定記録。
- au-audit.cjs、au-audit-result.json: root直接実行でpass=true、errors=[]、71file/221/179/locale2確認。実行: node docs/handoff/design-system-recon/evidence-20260910/au-audit.cjs。
- au-overlap-evidence.json: OPEN PR6件の実diffを照合。#2656の4opening整形と将来text競合し得るがボタン操作仕様の競合0。他PR/worktreeは変更しない。
- au-pages-review.md / au-shared-review.md: Sol相互read-onlyレビューAPPROVE。Astra設計審査は自己審査であり独立レビューとは称しない。
- au-validation.tar.gz / au-validation-manifest.json: 初回失敗を含む原ログとSHA256。報告中/tmpパスの原ログはこのarchiveで永続化。

## 検証（root自身が実行）

全体coverage52files/661tests成功、78.40秒、maxWorkers=1。statement27.9%、branch23.99%、function24.44%、line29.06%。build/check:all/Storybook成功。静的検査139warnings/0errors、今回変更TSXはstrict警告0（Sol原ログを確認）。doc設計/維持欄errors=[]、task-state/diff/card検査成功。

担当実行原ログ確認: shared4files36tests、実ページ2files11tests、関連6files47tests。Login実引数・pending二重クリック抑止・成功遷移・reset失敗表示/成功再試行、Carrier削除取消0write/確認sandbox対象DELETE1回、InvoicePDFのwindow.open引数とwrite0。動的6条件は実Inventory/InvoiceCreate/Products/Quotes/ProductMastersで確認。これは全221業務フローを本番実行したという意味ではない。

## 訂正と失敗履歴

- 初回棚卸し226はsuffix-btn5件の過大検出。境界修正し221、曖昧な数を実装母数にしなかった。
- Carrier削除計画のghost誤記を設計どおりdangerへ訂正。Login fullWidthの計画漏れを原設計と照合して修正。root外観監査も追加。
- 旧CSS撤去前にHeaderButton/3story依存を発見、破壊的削除を保留して設計/カード追補後に処理。
- 初回Dynamic試験は合成Buttonの反復で実ページ未被覆、root REVISEで5実ページ6条件へ差し替えた。
- 初回実ページCarrier試験1失敗は環境カード読込待機前のselector。実際のDOMで補正、失敗ログ保持。
- GoalSetting既存日本語警告1件をi18nへ限定補正。lint無効化なし。
- 最終build初回は新規試験mockResolvedValueの引数欠落TS2554。undefinedを明示してtsc/最終build成功。製品不具合とは区別する。
- JSDOMの外部document navigation未実装メッセージはLink修飾クリック検証に伴う環境制限。実ブラウザーや実外部遷移の成功としない。

## 状態・残件・限界

設計/審査/実装/相互レビュー/ローカル全検証/文書保存済み。PR提出・最新CI・マージ・本番反映は未実施。POは全数移管とPR/配備までを依頼済み、特定PR番号のGOは未受領。AstraはOpus向け常時委譲を自分へ読み替えない。正式承認経路を改変/迂回しない。
画面・本番ログインフォーム・PO目視は既存PO指示で省略・未検証。旧smの色/枠/寸法を含め共通外観へ変わるがpixel同一とはしない。表の狭幅表示/報酬欄の見た目も未検証。本便は指定された旧221の移管であり、別のnative179（タブ等）や表/カレンダー/最後のCI強化の全完了を意味しない。

2026-09-29 PR #3855提出済み（https://github.com/shingo-ops/salesanchor/pull/3855）。実装HEAD91fdf21be5bbf28277377eb535f5ac675af40b02。公式create-safe/.pr-number/占有台帳照合済み。process-artifacts gateは番号付きGO未受領のみで失敗（run36521962033/job109256570175、au-process-gate.log）。包括的実施許可からPO原文を創作しない。残る技術CI確認後、GO #3855受領・最新HEAD/CI/バックアップ照合を経て正式経路でマージ/配備。現在未マージ・未配備。

## 2026-09-29 AU 本番反映完了

PO本人の「GO #3855」を本チャットで受領し、そのままPR本文へ転記。最新HEAD523ca39d9、CI40成功/8skip、必須13/13成功と直前バックアップgzip -t成功を確認後、公式merge-safeでPR3855をmerge。merge SHA85af04d5e51ab0cfc75ce11bb8792bb8542abae5、2026-09-29T04:44:47Z。

Deploy36522989354 success。rootは2026-09-29T04:48:08.291083+00:00に本番HEAD一致、App/API/JS HTTP200、DB/Redis/Celery接続正常、公開index/JSと本番コンテナの各SHA256一致をread-onlyで直接確認。証跡au-go-merge-record.json、au-approved-checks.json、au-merge-final.log、au-deploy-result.json、au-production-verification.json。au-verify-production.pyは読取検証の再現資料。

設計・審査・実装・相互レビュー・本人GO・マージ・本番反映・公開配信照合済み。旧方式221→0、共有Button494/ButtonLink8。DB/API/配線/データ保存先変更0。画面・本番ログインフォーム・PO目視は指示どおり省略・未検証、復元試験も未実施。別native179、表/報酬3/カレンダー色、最後のCI補強は別便。本記録PRは実施済み結果の文書保存のみ。
