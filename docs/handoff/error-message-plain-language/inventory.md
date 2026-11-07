# エラーメッセージ棚卸し（調査のみ・製品コード変更なし）

- 調査対象: origin/main `67d7bbf87`（Merge pull request #5263）
- 作業場所: release/error-message-inventory
- 実施: 調査役（読むだけ）。推測で埋めず、分からない所は「未確認」と書く

## 件数サマリ（表の先頭）

| 項目 | 内容 | 件数 |
|---|---|---|
| A | ja.json で値に「失敗」「エラー」「できません」「できませんでした」を含むキー | 267 件（次の行動の語あり ○ 52 / なし × 215） |
| B | frontend の ts/tsx でエラーの message/detail を参照する行（テスト・stories・viewer 除く） | 342 行 |
| C | backend/app の HTTPException 周辺で detail に日本語を直接書いた行 | 646 行（95 ファイル） |
| D | リダイレクトで reason= / status=error を付ける箇所 | discord_oauth.py 12 行（11 行が error） / 読む側 get("reason") 2 行 |
| E | 理由コード→文言キー対応の既存ファイル | 下の E 節（9 件） |
| F | エラー表示用の部品 | 下の F 節（Toast / Callout / EmptyState / AppUpdateNotice ほか） |

### 未確認・注意（正直に書く）
- A の○×は「もう一度」「お試し」「連絡」「確認して」「してください」の語を含むかだけの機械判定。文として次の行動になっているかの人の判断はしていない（例: 「確認してください」は ○ だが何を確認するか不明の場合がある）。
- A はキー階層を `.` でつないだ名前。値が配列の要素も含む。en.json は対象外。
- B は grep の機械抽出。`err/error/e/ex/exc/caught/reason` の `.message` `.detail`、`response.data.detail` などの行を拾った。画面に実際に出るか（表示先）は行の中身と周辺から読んだ範囲で、全件の表示先は未確認。`console.warn` 向けの行や、コードで分岐するだけの行（例 `err.message === "429"`）も混ざる。
- B の背景: `frontend/src/lib/api.ts:164-171` は、サーバーの detail が文字列ならそのまま ApiError の message にする（文字列でなければ common.httpError）。そのため `e.message` を出す箇所は、実質サーバーの detail 原文を画面に出すことになる（C の日本語文もそのまま出る）。
- C は grep -A4 で `detail="…日本語…"`（f 文字列含む）の行を取っただけ。複数行にまたがる detail、変数経由の detail、日本語以外（英語・識別子）の detail は拾っていない（未確認）。HTTPException 以外（JSONResponse など）の detail が混ざる可能性あり。
- D: `backend/app/routers/meta_inbox.py:119` の `_frontend_callback_url` は定義のみで呼び出し箇所が無い（grep 結果）。Meta 側の `status=error&reason=` は frontend の `OAuthCallbackPage.tsx` が自分で作る。
- 実行役の事前確認 `./scripts/dev/executor-preflight.sh` は gh の認証と GitHub API 到達で FAIL した（クラウド環境のため）。調査は読むだけなので続行した。
- 手順の逸脱の自己申告: 抽出用の小さな Python を引用符つきヒアドキュメントで一度書いた（指示は「ヒアドキュメントはしない」）。それ以降は Write で書いた。製品コードは触っていない。

## A. ja.json（frontend/src/locales/ja.json）エラー系キー 全 267 件

抽出命令: `python3 -I a.py`（ja.json を再帰的に走査し、値が「失敗」「エラー」「できません」「できませんでした」のいずれかを含むものを出力）。次の行動語＝「もう一度」「お試し」「連絡」「確認して」「してください」。

| キー | ja の文 | 次の行動の語 |
|---|---|---|
| `productCsv.loadError` | 商品を取得できませんでした。再度お試しください。 | ○ |
| `productCsv.previewFailed` | ファイルを検査できませんでした。商品は登録していません。 | × |
| `productCsv.uncertain` | 登録結果を確認できませんでした。一部の商品が登録済みの可能性があります。再取り込みせず、管理者に履歴の確認を依頼してください。 | ○ |
| `productCsv.messages.requiredFieldCleared` | {{value}} を空にはできません。値を入れるか、調べて存在しなかった場合は blank_confirmed にこの列名を入れてください（english_title・mark・release_date・exclude_keywords だけ）。 | × |
| `productCsv.messages.unknown` | 検査を完了できませんでした。管理者に確認を依頼してください。 | ○ |
| `productCsv.exportError` | 出力できませんでした。再度お試しください。容量が大きい場合は検索条件を絞ってください。 | ○ |
| `common.error` | エラー | × |
| `common.fetchError` | 取得に失敗しました | × |
| `common.saveError` | 保存に失敗しました | × |
| `common.deleteError` | 削除に失敗しました | × |
| `common.operationError` | 操作に失敗しました | × |
| `common.requestFailed` | リクエストに失敗しました | × |
| `common.httpError` | リクエストに失敗しました（{{status}}） | × |
| `common.unknownError` | 不明なエラーが発生しました | × |
| `common.blobFetchFailed` | ファイルの取得に失敗しました | × |
| `common.downloadFailed` | ダウンロードに失敗しました | × |
| `common.errorLoad` | 読み込みに失敗しました | × |
| `common.errorLoading` | 読み込みエラー | × |
| `buybackPrices.loadError` | データの取得に失敗しました | × |
| `buybackPrices.fetchFailed` | 取得タスクの開始に失敗しました | × |
| `buybackPrices.rematchFailed` | 再マッチの開始に失敗しました | × |
| `googleDriveIntegration.connectFailedBanner` | 接続に失敗しました。お手数ですが、もう一度お試しください。 | ○ |
| `carrierIntegration.failMsg` | 接続失敗 | × |
| `carrierIntegration.statusError` | 接続エラー | × |
| `carrierIntegration.lastTestedFailure` | 最終テスト: {{time}} 失敗 | × |
| `carrierIntegration.fedexEtdGuideStep2TradeDocumentsNote` | Trade Documents Upload API を必ず追加してください。これが無いとレターヘッド・署名のアップロードができません。 | ○ |
| `paypalIntegration.failMsg` | 接続失敗 | × |
| `fedexRateModal.errorApiFailure` | FedEx API エラー | × |
| `authError.default` | エラーが発生しました。しばらく待ってからお試しください。 | ○ |
| `authError.passkeyFailed` | 顔・指紋でのログインに失敗しました。パスワードでログインするか、もう一度お試しください。 | ○ |
| `resetPasswordPage.errorTitle` | パスワードを設定できませんでした | × |
| `dashboard.leadFactorsInsufficient` | 件数が足りないため、まだ計算できません（成約・失注それぞれ {{need}}件以上が必要です）。 | × |
| `dashboard.leadFactorsNotComputableAll` | この記録では計算できませんでした。 | × |
| `leads.channelInviteError` | 送信に失敗しました。チャンネル設定を確認してください。 | ○ |
| `leads.discordRemoveError` | 操作に失敗しました。Bot 権限を確認してください。 | ○ |
| `leads.discordRoleSyncStatus_failed` | 失敗 | × |
| `leads.discordRoleSyncError` | 再同期に失敗しました。discord_user_id と estimated_scale を確認してください。 | ○ |
| `customers.deleteConstraint` | 関連する商談・注文・見積・請求書がある場合は削除できません（先にそれらを削除してください）。 | ○ |
| `companies.deleteConfirmMessage` | 「{{name}}」({{code}}) を削除しますか？ 関連する商談・注文・見積・請求書・担当者がある場合は削除できません。 | × |
| `companies.convHistory.loadError` | 会話ログの取得に失敗しました | × |
| `contacts.deleteConfirmMessage` | 「{{name}}」({{code}}) を削除しますか？ 関連する商談・注文・見積・請求書がある場合は削除できません。 | × |
| `inbox.sendDisabled7d` | メッセージウィンドウが期限切れ（7日）。メッセージを送信できません。 | × |
| `inbox.imageExpired` | 画像を表示できません（期限切れ） | × |
| `inbox.fetchError` | データの取得に失敗しました | × |
| `inbox.translationError` | 翻訳に失敗しました | × |
| `inbox.manualRecord.saveError` | 保存に失敗しました | × |
| `inbox.reactionSendFailed` | リアクションの送信に失敗しました | × |
| `inbox.reactionDeleteFailed` | リアクションの取り消しに失敗しました | × |
| `inbox.sendError.permissionDenied` | 24時間を過ぎたため送信できません。Instagram/Messengerから直接返信してください | ○ |
| `inbox.sendError.attachmentNotSaved` | 画像は送信されましたが、自社への保管に失敗しました | × |
| `inbox.sendError.discordSendFailed` | 送信できませんでした。入力した文は残っています。 | × |
| `inbox.sendError.generic` | 送信できませんでした | × |
| `channels.loadError` | チャンネルの読み込みに失敗しました: | × |
| `channels.partialConnect` | {{succeeded}} ページ接続しましたが、{{failedCount}} ページが失敗しました。失敗したページを再試行してください。 | ○ |
| `channels.partialConnectWithPages` | {{succeeded}} ページ接続しましたが、{{failedCount}} ページ（{{failedPages}}）が失敗しました。失敗したページを再試行してください。 | ○ |
| `channels.disconnectFailedMsg` | 接続解除に失敗しました: {{msg}} | × |
| `channels.connectError` | 接続を開始できませんでした | × |
| `channels.authUrlError` | 認証URLを取得できませんでした | × |
| `channels.loadErrorFallback` | チャンネルの読み込みに失敗しました | × |
| `channels.errorReason.meta_api_error` | Meta APIエラーにより接続できませんでした。しばらく後にもう一度お試しください。 | ○ |
| `channels.errorReason.internal_error` | 内部エラーが発生しました。サポートにお問い合わせください。 | × |
| `channels.errorReason.unknown` | 接続に失敗しました（理由: {{reason}}）。 | × |
| `channels.discordConnectError` | Discord連携に失敗しました。もう一度お試しください。 | ○ |
| `deals.deleteConstraint` | 関連する注文がある場合は削除できません（先に注文を削除してください）。 | ○ |
| `inventory.distributionOff` | 配信設定がオフのため表示できません。 | × |
| `purchaseOrders.status_error` | 送信エラー | × |
| `staff.join.copyFailed` | コピーできませんでした。リンクを選んで手でコピーしてください。 | ○ |
| `staffJoin.copyFailed` | コピーできませんでした。番号を選んで手でコピーしてください。 | ○ |
| `bots.apiKeyIssued` | APIキーが発行されました（この画面を閉じると再取得できません）： | × |
| `notifications.eventType.tcgDistributionError` | TCG在庫配信エラー | × |
| `erp.jobStatus_failed` | 失敗 | × |
| `commissions.monthlyError` | 月次集計を取得できませんでした | × |
| `oauth.error` | 接続中にエラーが発生しました。 | × |
| `purchase.fetchError` | 仕入情報の取得に失敗しました | × |
| `purchase.confirmError` | 確定に失敗しました | × |
| `companyContactSelector.contactsFetchError` | 担当者の取得に失敗しました | × |
| `mergeLead.convertedError` | 成約済みのリードは「消す側」にできません。残す側に指定してください。 | ○ |
| `mergeContact.relatedError` | 関連レコード（商談・注文等）があるため「消す側」にできません。先に担当者を変更してください。 | ○ |
| `superAdmin.loginRequests.approveError` | 許可できませんでした。 | × |
| `superAdmin.knowledge.csvErrors` | CSV エラー | × |
| `superAdmin.diagnostics.sections.extractionErrors` | 抽出エラー | × |
| `superAdmin.diagnostics.columns.error_message` | エラー内容 | × |
| `superAdmin.diagnostics.retryConfirmErrors` | 表示中のエラージョブを再実行しますか？（最大50件） | × |
| `superAdmin.diagnostics.retryError` | 再実行に失敗しました（Celery 未接続の可能性があります） | × |
| `superAdmin.suppliersAdmin.loadError` | 仕入元の詳細を取得できませんでした。もう一度読み込んでください。 | ○ |
| `superAdmin.suppliersAdmin.saveError` | 保存結果を確認できませんでした。入力内容を控えてから再度お試しください。 | ○ |
| `superAdmin.suppliersAdmin.deleteError` | 仕入元の削除に失敗しました。 | × |
| `superAdmin.viewerTemplates.copyError` | コピーできませんでした | × |
| `superAdmin.viewerTemplates.saveError` | 保存できませんでした | × |
| `superAdmin.viewers.saveError` | 保存できませんでした | × |
| `superAdmin.viewers.loadError` | 閲覧者の一覧を取得できませんでした。 | × |
| `superAdmin.viewers.conflictError` | 今の状態では実行できません。 | × |
| `superAdmin.viewers.genericError` | 処理に失敗しました。しばらく待ってから再試行してください。 | ○ |
| `superAdmin.viewers.sheetSaveError` | シートを保存できませんでした | × |
| `superAdmin.fxRate.refreshError` | レートの取得に失敗しました。しばらく待ってから再試行してください。 | ○ |
| `superAdmin.inbound.parseStatus.unparsed` | 解析失敗 | × |
| `superAdmin.phaseSwitch.tenantIdMissing` | テナント ID を取得できませんでした。再ログインしてください | ○ |
| `schedule.connectError` | 接続に失敗しました | × |
| `schedule.errorFetch` | 予定の取得に失敗しました | × |
| `schedule.errorCreate` | 予定の作成に失敗しました | × |
| `schedule.errorUpdate` | 予定の更新に失敗しました | × |
| `schedule.errorDelete` | 予定の削除に失敗しました | × |
| `schedule.connectBtnError` | ×接続エラー | × |
| `accountSettings.avatarErrorSave` | 画像を保存できませんでした。 | × |
| `accountSettings.push.error` | 通知の設定に失敗しました。もう一度試してください。 | ○ |
| `discordConfig.syncStatus.failed` | 同期失敗 | × |
| `discordOwnServer.connectError` | 登録できませんでした | × |
| `discordOwnServer.requestFailed` | 実行できませんでした | × |
| `discordOwnServer.planFailed` | 確認できませんでした | × |
| `discordOwnServer.applyDone` | 反映しました（成功 {{success}} 件・できない {{blocked}} 件・失敗 {{failed}} 件） | × |
| `discordOwnServer.applyFailed` | 反映できませんでした | × |
| `discordOwnServer.applyConflict` | 反映できませんでした。もう一度「確認する」を押してから反映してください | ○ |
| `discordOwnServer.status.failed` | 失敗 | × |
| `discordOwnServer.reason.depends_failed` | 先に作る物が失敗したので実行しませんでした | × |
| `discordAutoSetup.partial` | 一部失敗しました | × |
| `discordAutoSetup.failed` | 失敗しました | × |
| `discordAutoSetup.requestFailed` | 実行できませんでした | × |
| `discordAutoSetup.statuses.failed` | 失敗 | × |
| `discordTicketConfig.saveError` | 保存できませんでした | × |
| `discordTicketConfig.deployError` | 投稿できませんでした。Botの権限とチャンネルIDを確認してください | ○ |
| `discordAnnounce.sendError` | 投稿に失敗しました。チャンネルIDとBot権限を確認してください。 | ○ |
| `registration.alreadyRegisteredGate` | 登録済みのため新規登録リンクは発行できません。 | × |
| `registration.submitError` | 登録に失敗しました | × |
| `registration.error.unexpected_error` | 予期しないエラーが発生しました。しばらくしてから再度お試しください。 | ○ |
| `ownInventory.loadError` | 自社在庫の読み込みに失敗しました | × |
| `ownInventory.actionError` | 操作に失敗しました | × |
| `translation.outbound.previewError` | 英訳の生成に失敗しました | × |
| `translation.outbound.confirmError` | 送信に失敗しました | × |
| `translation.glossary.loadError` | グロッサリの読み込みに失敗しました | × |
| `translation.glossary.saveError` | グロッサリの保存に失敗しました | × |
| `channelMasters.loadError` | チャネル一覧の取得に失敗しました | × |
| `channelMasters.deleteError` | 削除に失敗しました | × |
| `channelMasters.saveError` | 追加に失敗しました | × |
| `channelMasters.visibilityError` | 切り替えに失敗しました | × |
| `distributionTarget.form.accessErrorTitle` | このシートにアクセスできません | × |
| `distributionTarget.form.accessErrorGeneric` | シートへのアクセスに失敗しました | × |
| `tcgLineImport.errorUploadFailed` | アップロードに失敗しました | × |
| `tcgLineImport.errorHistoryFailed` | 履歴の取得に失敗しました | × |
| `tcgLineImport.errorResolveFailed` | 登録に失敗しました | × |
| `pmgWorkflow.stale` | 取得失敗。前回の表示を保持しています | × |
| `pmgWorkflow.fetchFailed` | 取得に失敗しました | × |
| `pmgWorkflow.summary.stale` | 前回の表示を確認中（取得に失敗） | × |
| `pmgWorkflow.summary.fetchFailed` | 進捗を取得できません | × |
| `pmgWorkflow.summary.error` | 抽出エラーがあります | × |
| `pmgWorkflow.summaryAction.error` | 抽出エラーの明細を確認してください。 | ○ |
| `pmgWorkflow.errorAction` | エラー{{count}}件の原因と対処を確認 | × |
| `pmgWorkflow.filterError` | 抽出エラー | × |
| `pmgWorkflow.extractionStates` | 抽出状態（待機・実行中・成功・対象なし・失敗） | × |
| `pmgWorkflow.extraction.completed` | 抽出完了（成功・対象なし・失敗の合計） | × |
| `pmgWorkflow.extraction.error` | 抽出エラー | × |
| `pmgWorkflow.extraction.residualItems` | 抽出エラーでも残った明細 | × |
| `pmgWorkflow.extraction.residualResults` | 抽出エラーでも残った解析結果 | × |
| `pmgWorkflow.extractionStatus.error` | エラー | × |
| `pmgWorkflow.errorDetails` | 抽出エラーの原因と対処 | × |
| `pmgWorkflow.stageBreakdown` | 成功{{done}}・対象なし{{empty}}・エラー{{failed}}・処理中／待機{{pending}} | × |
| `conditionReview.reloadFailed` | 内容が変わり、再取得にも失敗しました。再読込してから確認してください。 | ○ |
| `conditionReview.saveFailed` | 状態を保存できませんでした。もう一度お試しください。 | ○ |
| `conditionReview.loadFailed` | 状態の選択肢を取得できませんでした。 | × |
| `v102Posts.saveFailed` | 保存できませんでした。もう一度お試しください | ○ |
| `reviewItem.ackFailed` | 確認済みにできませんでした。もう一度お試しください | ○ |
| `reviewItem.reassignFailed` | 付け替えに失敗しました | × |
| `reviewItem.valueFix.saveFailed` | 保存できませんでした。もう一度お試しください | ○ |
| `reviewItem.wizard.keyword.failed` | 付け替えました。検索キーワードは追加できませんでした（{{reason}}） | × |
| `reviewItem.wizard.register.reassignFailed` | 新しい商品（番号 {{id}}）は登録済みです。付け替えに失敗しました（{{reason}}）。「戻る」を押しても登録は残ります | × |
| `reviewItem.wizard.register.failed` | 登録できませんでした（{{reason}}） | × |
| `reviewReason.extract_exception` | 解析の途中でエラーが起きた | × |
| `codeCollision.addError` | 追加に失敗しました。もう一度お試しください | ○ |
| `productDetail.loadError` | 商品詳細を取得できませんでした。もう一度読み込んでください。 | ○ |
| `productDetail.saveError` | 保存結果を確認できませんでした。入力内容を控えてから最新の内容を読み直してください。 | ○ |
| `productDetail.deleteInUse` | この商品は在庫に使用されているため削除できません。 | × |
| `productDetail.deleteError` | 商品の削除に失敗しました。 | × |
| `productDetail.requiredFieldsMissing` | 必要な項目が入っていないため登録できません：{{fields}}。値を入れてください。英語名・型番・発売日・除外キーワードは、存在しないときは「調べたが存在しない」に印を付けてください。 | × |
| `productDetail.requiredFieldsCleared` | {{fields}} は空にできません。値を入れてください。英語名・型番・発売日・除外キーワードは、存在しないときは「調べたが存在しない」に印を付けてください。 | × |
| `soldOut.unavailable` | 取得できませんでした。再読込してください。 | ○ |
| `pmgAttempt.unavailable` | 試行履歴を取得できませんでした。表示を更新してください。 | ○ |
| `pmgAttempt.copyFailed` | コピーできませんでした。ブラウザのコピー権限をご確認ください。 | × |
| `pmgAttempt.phase.failed` | 失敗記録あり | × |
| `pmgAttempt.completion.failed` | 試行失敗 | × |
| `pmgAttempt.reason.API_ERROR` | API呼び出しに失敗しました。通信・認証・提供元のどれが原因かはこの記録では未特定です。調査用情報をコピーして確認を依頼してください。 | ○ |
| `pmgAttempt.reason.INVALID_RESPONSE` | 返答形式または照合の検証を完了できませんでした。調査用情報を添えて返答の確認を依頼してください。 | ○ |
| `pmgAttempt.reason.RECORD_WRITE_FAILED` | 必要な記録の保存を確定できませんでした。調査用情報を添えて保存処理の確認を依頼してください。 | ○ |
| `pmgAttempt.reason.RESPONSE_NOT_RECORDED` | 応答の記録を確認できませんでした。調査用情報を添えて記録の確認を依頼してください。 | ○ |
| `pmgAttempt.reason.unknown` | この記録では原因を特定できません。調査用情報をコピーして確認を依頼してください。 | ○ |
| `analysisRules.sidebar.errorLog` | エラーログ | × |
| `analysisRules.pipelineMap.proc.step4.procedures` | 仕入先別の解決率・エラー率を確認。要確認行を対処し、必要に応じて商品マスタの検索KWやルールを調整して再解析を実行 | × |
| `analysisRules.lineWorkflowGuide.actions.openErrorLog` | エラーログを開く | × |
| `analysisRules.lineWorkflowGuide.steps.step4.result` | 抽出結果は、空の投稿・除外・抽出失敗を区別して記録されます。 | × |
| `analysisRules.lineWorkflowGuide.steps.step4.trouble` | 読み取りに失敗した場合は、エラーログを開いて原因を確認します。 | × |
| `analysisRules.lineWorkflowGuide.steps.step6.reference` | 取込画面の結果と、商品・仕入元などの各マスタ、エラーログを確認します。 | × |
| `analysisRules.lineWorkflowGuide.steps.step6.result` | 配信前に確認すべき不足や失敗の場所が分かります。 | × |
| `analysisRules.lineWorkflowGuide.steps.step6.trouble` | 判断できない項目は、元の投稿と登録情報を確認します。処理の失敗が表示されている場合は、エラーログで原因を確認します。 | × |
| `analysisRules.lineWorkflowGuide.exceptions.item2` | 抽出に失敗した時は、手順4からエラーログを確認します。 | × |
| `analysisRules.errorLog.title` | 抽出エラーログ | × |
| `analysisRules.errorLog.errorMessage` | エラー内容 | × |
| `analysisRules.errorLog.noErrors` | エラーはありません | × |
| `analysisRules.errorLog.fetchError` | エラーログの取得に失敗しました | × |
| `analysisRules.errorLog.retryError` | 再実行に失敗しました | × |
| `analysisRules.errorLog.errorCategory` | エラー種別 | × |
| `analysisRules.errorLog.errorDetail` | エラー詳細 | × |
| `analysisRules.errorLog.firstFailedAt` | 最初の失敗 | × |
| `analysisRules.errorLog.lastFailedAt` | 最新の失敗 | × |
| `analysisRules.errorLog.category.gemini_http_error` | Gemini HTTPエラー | × |
| `analysisRules.errorLog.category.logic_parse_error` | 応答解析エラー | × |
| `analysisRules.errorLog.category.logic_conflict` | 整合性エラー | × |
| `analysisRules.dashboard.recentErrors` | 直近のエラー | × |
| `analysisRules.dashboard.errorMessage` | エラーメッセージ | × |
| `analysisRules.dashboard.noErrors` | エラーはありません | × |
| `analysisRules.dashboard.fetchError` | データの取得に失敗しました | × |
| `analysisRules.dashboard.aiJobs.colLastError` | 最後の失敗の理由 | × |
| `analysisRules.dashboard.aiJobs.count24h` | {{count}} 回（失敗 {{failed}}） | × |
| `analysisRules.dashboard.aiJobs.loginReason.auth_failed` | 最後の呼び出しで認証に失敗 | × |
| `analysisRules.dashboard.aiJobs.errorCode.auth_failed` | 認証の失敗 | × |
| `analysisRules.dashboard.aiJobs.errorCode.http_error` | 通信の失敗 | × |
| `analysisRules.dashboard.distributionResultFailed` | 失敗 | × |
| `analysisRules.dashboard.extractionErrorRate` | 抽出エラー率 | × |
| `analysisRules.dashboard.supplierExtractionErrors` | 抽出エラー | × |
| `analysisRules.dashboard.supplierExtractionError` | エラー | × |
| `analysisRules.dashboard.extractionSupplierError` | エラー | × |
| `analysisRules.dashboard.extractionRankErrorJobs` | エラー | × |
| `analysisRules.dashboard.usage.note` | Gemini を呼ぶたびの使用量（台帳 llm_usage_events）。考える量は Google が返したときだけ記録されます。応答が返らず失敗した呼び出しは含みません。 | × |
| `analysisRules.dashboard.usage.health.note` | 成功率は完了と失敗の合計に対する完了の割合です（処理中は含みません）。翻訳は失敗の記録がないため含みません。 | × |
| `analysisRules.dashboard.usage.health.errorsChartTitle` | エラー数（種類別） | × |
| `analysisRules.dashboard.usage.summary.errorCountLabel` | エラー件数（LINE抽出） | × |
| `analysisRules.dashboard.extractionHealthErrorCount` | エラー件数 | × |
| `analysisRules.dashboard.extractionJobStatus_error` | エラー | × |
| `analysisRules.errors.serverUnavailable` | サーバーが利用できません。しばらくしてから再試行してください。 | ○ |
| `analysisRules.errors.unknown` | エラーが発生しました。 | × |
| `analysisRules.extractionPromptConfig.error` | 保存に失敗しました | × |
| `tcgAnalysisReview.correctionSaveError` | 修正内容の保存に失敗しました | × |
| `tcgAnalysisReview.memoSaveError` | 保存に失敗しました | × |
| `tcgAnalysisReview.error` | エラー | × |
| `tcgAnalysisReview.productMasterDrawer.registerError` | 登録エラー | × |
| `tcgAnalysisReview.productMasterDrawer.keywordAddFailed` | 追記に失敗しました。 | × |
| `supplierCsv.errors` | エラー | × |
| `supplierCsv.noErrors` | エラーなし | × |
| `supplierCsv.commitFail` | インポートに失敗しました | × |
| `unitCsv.errors` | エラー | × |
| `unitCsv.noErrors` | エラーなし | × |
| `unitCsv.commitFail` | インポートに失敗しました | × |
| `conditionCsv.errors` | エラー | × |
| `conditionCsv.noErrors` | エラーなし | × |
| `conditionCsv.commitFail` | インポートに失敗しました | × |
| `statusMasterCsv.errors` | エラー | × |
| `statusMasterCsv.noErrors` | エラーなし | × |
| `statusMasterCsv.commitFail` | インポートに失敗しました | × |
| `productCategoriesCsv.errors` | エラー | × |
| `productCategoriesCsv.noErrors` | エラーなし | × |
| `productCategoriesCsv.commitFail` | インポートに失敗しました | × |
| `noteMasterCsv.errors` | エラー | × |
| `noteMasterCsv.noErrors` | エラーなし | × |
| `noteMasterCsv.commitFail` | インポートに失敗しました | × |
| `productKindsMaster.deleteBlocked` | この大分類は中分類で使用中のため削除できません | × |
| `typeMaster.confirmDelete` | この中分類を削除しますか？関連する小分類がある場合は削除できません。 | × |
| `typeMaster.deleteBlocked` | この中分類は使用中のため削除できません | × |
| `productFormatsMaster.saveFailed` | 保存できませんでした | × |
| `ruleManagement.toggleFail` | ルールの更新に失敗しました | × |
| `ruleManagement.test.gateError` | テストエラー | × |
| `reviewCsv.summary` | 全{{total}}行 / 反映する件：{{ready}} / エラー：{{errors}} | × |
| `reviewCsv.errorsTitle` | エラーの件と理由 | × |
| `reviewCsv.confirmHint` | この内容で反映します。反映後に解析と配信がやり直されます。エラーの件は反映されません。 | × |
| `reviewCsv.resultCounts` | 反映：{{saved}}件 / 失敗：{{failed}}件 | × |
| `reviewCsv.downloadFailed` | CSVをダウンロードできませんでした。もう一度お試しください。 | ○ |
| `reviewCsv.previewFailed` | 内容を確認できませんでした。もう一度お試しください。 | ○ |
| `reviewCsv.uncertain` | 反映の結果を確認できませんでした。再送せず、要確認の一覧を開き直して状態を確認してください。 | ○ |
| `reviewCsv.errors.REVIEW_CSV_REJECTED` | この内容では保存できません。 | × |
| `reviewCsv.errors.REVIEW_CSV_SAVE_FAILED` | 保存に失敗しました。 | × |
| `reviewCsv.errors.unknown` | エラーが発生しました。 | × |

## B. サーバーの detail / err.message を画面に出す（出しうる）箇所 全 342 行

抽出命令: `grep -rnE "\b(err|error|e|ex|exc|caught|reason)\)?\??\.(message|detail)\b|\.response\??\.data\??\.(detail|message)|\bdata\??\.detail\b|\bbody\??\.detail\b" frontend/src --include=*.tsx --include=*.ts | grep -vE "\.test\.|__tests__|\.spec\.|\.stories\.|/viewer/"`

| ファイル:行 | 原文 |
|---|---|
| `frontend/src/components/MergeLeadModal.tsx:177` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/components/MergeLeadModal.tsx:216` | `const msg = e instanceof Error ? e.message : "";` |
| `frontend/src/components/CommissionPanel.tsx:101` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/components/CommissionPanel.tsx:139` | `setError(e instanceof Error ? e.message : t("common.operationError"));` |
| `frontend/src/components/CommissionPanel.tsx:156` | `setError(e instanceof Error ? e.message : t("common.operationError"));` |
| `frontend/src/components/CommissionPanel.tsx:173` | `setError(e instanceof Error ? e.message : t("common.operationError"));` |
| `frontend/src/components/PurchaseDetailPanel.tsx:179` | `e instanceof Error ? e.message : t("purchase.fetchError"),` |
| `frontend/src/components/PurchaseDetailPanel.tsx:237` | `setError(e instanceof Error ? e.message : t("common.saveError"));` |
| `frontend/src/components/PurchaseDetailPanel.tsx:261` | `setError(e instanceof Error ? e.message : t("purchase.confirmError"));` |
| `frontend/src/components/OrderFinancialPanel.tsx:133` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/components/OrderFinancialPanel.tsx:178` | `setError(e instanceof Error ? e.message : t("common.saveError"));` |
| `frontend/src/components/InventorySearchBar.tsx:188` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/components/MergeContactModal.tsx:99` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/components/MergeContactModal.tsx:134` | `const msg = e instanceof Error ? e.message : "";` |
| `frontend/src/components/PriorityScoreOverride.tsx:60` | `setError(err instanceof Error ? err.message : t("common.saveError"));` |
| `frontend/src/components/ShippingDetailPanel.tsx:233` | `e instanceof Error ? e.message : t("common.fetchError"),` |
| `frontend/src/components/ShippingDetailPanel.tsx:298` | `setError(e instanceof Error ? e.message : t("common.saveError"));` |
| `frontend/src/components/ShippingDetailPanel.tsx:332` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/components/MergeCompanyModal.tsx:103` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/components/MergeCompanyModal.tsx:141` | `setError(e instanceof Error ? e.message : t("common.operationError"));` |
| `frontend/src/components/ContactChannelForm.tsx:174` | `const msg = e instanceof Error ? e.message : "";` |
| `frontend/src/components/FedExRateModal.tsx:135` | `setFetchError(e instanceof Error ? e.message : t("common.operationError"));` |
| `frontend/src/features/tcg-analysis-review/DiagnosticsDrawer.tsx:52` | `setError(e instanceof Error ? e.message : t("common.unknownError"));` |
| `frontend/src/features/tcg-analysis-review/SupplierQualityList.tsx:47` | `.catch((e: unknown) => { setError(e instanceof Error ? e.message : t("common.unknownError")); })` |
| `frontend/src/features/tcg-analysis-review/ReviewProductFixForm.tsx:51` | `return failed(error instanceof ApiError && error.message ? error.message : "—");` |
| `frontend/src/features/tcg-analysis-review/ReviewProductFixForm.tsx:70` | `const message = error instanceof ApiError && error.message ? error.message : t("reviewItem.reassignFailed");` |
| `frontend/src/features/tcg-analysis-review/V102PostEditModal.tsx:131` | `const message = error instanceof ApiError && error.status === 422 ? error.message : t("v102Posts.saveFailed");` |
| `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx:96` | `setAckError(error instanceof ApiError && error.message ? error.message : t("reviewItem.ackFailed"));` |
| `frontend/src/features/tcg-analysis-review/SupplierDetailView.tsx:70` | `.catch((e: unknown) => { setError(e instanceof Error ? e.message : t("common.unknownError")); })` |
| `frontend/src/features/tcg-analysis-review/SupplierDetailView.tsx:77` | `.catch((e: unknown) => { setError(e instanceof Error ? e.message : t("common.unknownError")); })` |
| `frontend/src/features/tcg-analysis-review/ReviewRegisterProductForm.tsx:131` | `if (error instanceof ApiError && error.status === 404 && error.message === ALREADY_RESOLVED) {` |
| `frontend/src/features/tcg-analysis-review/ReviewRegisterProductForm.tsx:135` | `setLoadReason(error instanceof ApiError && error.message ? error.message : "—");` |
| `frontend/src/features/tcg-analysis-review/ReviewRegisterProductForm.tsx:194` | `const reasonOf = (error: unknown) => (error instanceof ApiError && error.message ? error.message : "—");` |
| `frontend/src/features/tcg-analysis-review/ReviewRegisterProductForm.tsx:232` | `setReassignError(error instanceof ApiError && error.message ? error.message : t("reviewItem.reassignFailed"));` |
| `frontend/src/features/tcg-analysis-review/ReviewRegisterProductForm.tsx:286` | `setErrorNotice(error instanceof ApiError && error.message ? error.message : t("reviewItem.reassignFailed"));` |
| `frontend/src/features/tcg-distribution/DistributionWorkspace.tsx:37` | `.catch((e: unknown) => setLoadError(e instanceof Error ? e.message : t("common.unknownError")));` |
| `frontend/src/features/tcg-distribution/DistributionTargetForm.tsx:91` | `setAccessError(e instanceof Error ? e.message : t("common.unknownError"));` |
| `frontend/src/features/tcg-distribution/DistributionTargetForm.tsx:119` | `setAccessError(e instanceof Error ? e.message : t("common.unknownError"));` |
| `frontend/src/features/tcg-distribution/DistributionPreview.tsx:34` | `.catch((e: unknown) => setLoadError(e instanceof Error ? e.message : t("common.unknownError")));` |
| `frontend/src/features/tcg-distribution/DistributionPreview.tsx:50` | `setRunError(e instanceof Error ? e.message : t("common.unknownError"));` |
| `frontend/src/features/tcg-distribution/DistributionTargetList.tsx:46` | `setActionError(e instanceof Error ? e.message : t("common.unknownError"));` |
| `frontend/src/features/tcg-distribution/DistributionTargetList.tsx:59` | `setActionError(e instanceof Error ? e.message : t("common.unknownError"));` |
| `frontend/src/features/secretary/SecretaryDraftInvoice.tsx:106` | `setError(e instanceof Error ? e.message : t("common.saveError"));` |
| `frontend/src/features/secretary/SecretaryDraftEvent.tsx:61` | `setError(e instanceof Error ? e.message : t("common.saveError"));` |
| `frontend/src/features/tcg-import-workflow/useImportStageDetails.ts:36` | `if (active && current === generation.current) setState(previous => ({ ...(previous.key === key ? previous : empty(key)), loading: false, error: reason instanceof Error ? reason.message : String(reason) }));` |
| `frontend/src/features/tcg-import-review/ReviewSection.tsx:82` | `setSuppliersError(e instanceof Error ? e.message : t("tcgLineImport.errorResolveFailed"));` |
| `frontend/src/features/tcg-import-review/ReviewSection.tsx:120` | `[displayName]: e instanceof Error ? e.message : t("tcgLineImport.errorResolveFailed"),` |
| `frontend/src/features/tcg-import-review/ReviewSection.tsx:144` | `[displayName]: e instanceof Error ? e.message : t("tcgLineImport.errorResolveFailed"),` |
| `frontend/src/features/tcg-import-review/ReviewSection.tsx:163` | `setCommitError(e instanceof Error ? e.message : t("tcgLineImport.commitError"));` |
| `frontend/src/features/supplier-master/SupplierDetailDrawer.tsx:249` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/features/supplier-master/SupplierDetailDrawer.tsx:271` | `setError(err instanceof Error ? err.message : t("common.saveError"));` |
| `frontend/src/features/supplier-master/SupplierDetailDrawer.tsx:280` | `setError(err instanceof Error ? err.message : t("common.deleteError"));` |
| `frontend/src/features/tcg-product-import/productDetailModel.ts:178` | `const code = err.message;` |
| `frontend/src/features/tcg-product-import/productDetailModel.ts:205` | `const code = PACKAGING_ERROR_CODES.find(c => err.message === c \|\| err.message.startsWith('${c}:'));` |
| `frontend/src/features/tcg-product-import/TcgProductImportPanel.tsx:43` | `catch (e) { setError(e instanceof ApiError ? importMessage(e.message, t) : t("productCsv.previewFailed")); }` |
| `frontend/src/features/tcg-review-csv/ReviewCsvPanel.tsx:51` | `catch (e) { setError(e instanceof ApiError ? reviewCsvMessage(e.message, t) : t("reviewCsv.previewFailed")); }` |
| `frontend/src/lib/auth/authErrorMessage.ts:21` | `if (typeof err.detail === "string") return err.detail;` |
| `frontend/src/lib/api.ts:84` | `if (body?.detail === "password_change_required") window.location.assign(PASSWORD_CHANGE_PATH);` |
| `frontend/src/lib/api.ts:165` | `const detail = body?.detail;` |
| `frontend/src/pages/super-admin/components/NoteMasterPanel.tsx:113` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/super-admin/components/NoteMasterPanel.tsx:131` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/super-admin/components/NoteMasterPanel.tsx:172` | `setError(err instanceof Error ? err.message : t("common.saveError"));` |
| `frontend/src/pages/super-admin/components/NoteMasterPanel.tsx:182` | `setError(e instanceof Error ? e.message : t("common.deleteError"));` |
| `frontend/src/pages/super-admin/components/QuantityUnitsMasterPanel.tsx:73` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/super-admin/components/QuantityUnitsMasterPanel.tsx:115` | `setError(err instanceof Error ? err.message : t("common.saveError"));` |
| `frontend/src/pages/super-admin/components/QuantityUnitsMasterPanel.tsx:127` | `setError(e instanceof Error ? e.message : t("common.deleteError"));` |
| `frontend/src/pages/super-admin/components/DbViewerPanel.tsx:340` | `e instanceof Error ? e.message : t("common.fetchError"),` |
| `frontend/src/pages/super-admin/components/DbViewerPanel.tsx:370` | `e instanceof Error ? e.message : t("common.fetchError"),` |
| `frontend/src/pages/super-admin/components/UnitIgnorePhrasesPanel.tsx:52` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/super-admin/components/UnitIgnorePhrasesPanel.tsx:80` | `setError(err instanceof Error ? err.message : t("common.saveError"));` |
| `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:670` | `setUploadError(e instanceof Error ? e.message : t("tcgLineImport.errorUploadFailed"));` |
| `frontend/src/pages/super-admin/components/ProductKindsMasterPanel.tsx:68` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/super-admin/components/ProductKindsMasterPanel.tsx:108` | `setError(err instanceof Error ? err.message : t("common.saveError"));` |
| `frontend/src/pages/super-admin/components/ProductKindsMasterPanel.tsx:120` | `setError(e instanceof Error ? e.message : t("common.deleteError"));` |
| `frontend/src/pages/super-admin/components/SupplierMasterPanel.tsx:113` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/super-admin/components/SupplierMasterPanel.tsx:127` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/super-admin/components/SupplierMasterPanel.tsx:180` | `setError(err instanceof Error ? err.message : t("common.saveError"));` |
| `frontend/src/pages/super-admin/components/SupplierMasterPanel.tsx:197` | `setError(e instanceof Error ? e.message : t("common.deleteError"));` |
| `frontend/src/pages/super-admin/components/SupplierMasterPanel.tsx:209` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/super-admin/components/SupplierMasterPanel.tsx:220` | `setError(err instanceof Error ? err.message : t("common.saveError"));` |
| `frontend/src/pages/super-admin/components/SupplierMasterPanel.tsx:229` | `setError(err instanceof Error ? err.message : t("common.deleteError"));` |
| `frontend/src/pages/super-admin/components/TypeMasterPanel.tsx:83` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/super-admin/components/TypeMasterPanel.tsx:125` | `setError(err instanceof Error ? err.message : t("common.saveError"));` |
| `frontend/src/pages/super-admin/components/TypeMasterPanel.tsx:137` | `const msg = e instanceof Error ? e.message : t("common.deleteError");` |
| `frontend/src/pages/super-admin/components/TypeMasterPanel.tsx:139` | `if (e instanceof Error && e.message.includes("409")) {` |
| `frontend/src/pages/super-admin/components/RuleManagementPanel.tsx:58` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/super-admin/components/RuleManagementPanel.tsx:77` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/super-admin/components/RuleTestPanel.tsx:119` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/super-admin/components/RuleTestPanel.tsx:194` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/super-admin/components/RuleTestPanel.tsx:208` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/super-admin/components/RuleTestPanel.tsx:242` | `setAddError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/super-admin/components/RuleTestPanel.tsx:256` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/super-admin/components/RuleDrawer.tsx:196` | `detail: e instanceof Error ? e.message : t("common.fetchError"),` |
| `frontend/src/pages/super-admin/components/RuleDrawer.tsx:233` | `setSubmitError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/super-admin/components/RuleDrawer.tsx:247` | `setSubmitError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/super-admin/components/PipelineMapPanel.tsx:99` | `<span className="master-node__detail">{data.detail}</span>` |
| `frontend/src/pages/super-admin/components/PipelineMapPanel.tsx:114` | `<span className="end-node__detail">{data.detail}</span>` |
| `frontend/src/pages/super-admin/components/UnitMasterPanel.tsx:94` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/super-admin/components/UnitMasterPanel.tsx:108` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/super-admin/components/UnitMasterPanel.tsx:149` | `setError(err instanceof Error ? err.message : t("common.saveError"));` |
| `frontend/src/pages/super-admin/components/UnitMasterPanel.tsx:166` | `setError(e instanceof Error ? e.message : t("common.deleteError"));` |
| `frontend/src/pages/super-admin/components/UnitMasterPanel.tsx:178` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/super-admin/components/UnitMasterPanel.tsx:193` | `setError(err instanceof Error ? err.message : t("common.saveError"));` |
| `frontend/src/pages/super-admin/components/UnitMasterPanel.tsx:203` | `setError(err instanceof Error ? err.message : t("common.deleteError"));` |
| `frontend/src/pages/super-admin/components/ConditionDefsMasterPanel.tsx:70` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/super-admin/components/ConditionDefsMasterPanel.tsx:110` | `setError(err instanceof Error ? err.message : t("common.saveError"));` |
| `frontend/src/pages/super-admin/components/ConditionDefsMasterPanel.tsx:122` | `setError(e instanceof Error ? e.message : t("common.deleteError"));` |
| `frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:113` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:148` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:214` | `setError(err instanceof Error ? err.message : t("common.saveError"));` |
| `frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:231` | `setError(e instanceof Error ? e.message : t("common.deleteError"));` |
| `frontend/src/pages/super-admin/components/ProductLinesMasterPanel.tsx:90` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/super-admin/components/ProductLinesMasterPanel.tsx:156` | `setError(err instanceof Error ? err.message : t("common.saveError"));` |
| `frontend/src/pages/super-admin/components/ProductLinesMasterPanel.tsx:168` | `setError(e instanceof Error ? e.message : t("common.deleteError"));` |
| `frontend/src/pages/super-admin/components/ProductCategoriesMasterPanel.tsx:63` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/super-admin/components/ProductCategoriesMasterPanel.tsx:88` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/super-admin/components/ProductCategoriesMasterPanel.tsx:129` | `setError(err instanceof Error ? err.message : t("common.saveError"));` |
| `frontend/src/pages/super-admin/components/ProductCategoriesMasterPanel.tsx:146` | `setError(e instanceof Error ? e.message : t("common.deleteError"));` |
| `frontend/src/pages/super-admin/components/WeightClassesMasterPanel.tsx:74` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/super-admin/components/WeightClassesMasterPanel.tsx:118` | `setError(err instanceof Error ? err.message : t("common.saveError"));` |
| `frontend/src/pages/super-admin/components/WeightClassesMasterPanel.tsx:130` | `setError(e instanceof Error ? e.message : t("common.deleteError"));` |
| `frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.tsx:98` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.tsx:145` | `if (err instanceof ApiError && err.status === 409 && err.message === "PRODUCT_FORMAT_GAME_IN_USE") return t('${f}.gamesInUse');` |
| `frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.tsx:146` | `if (err instanceof ApiError && err.status === 422 && err.message === "PRODUCT_FORMAT_GAME_UNKNOWN") return t('${f}.gamesUnknown');` |
| `frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.tsx:147` | `return err instanceof Error ? err.message : fallback;` |
| `frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.tsx:197` | `setError(e instanceof Error ? e.message : t("common.deleteError"));` |
| `frontend/src/pages/super-admin/UnitImportPage.tsx:52` | `setError(e instanceof ApiError ? e.message : t("unitCsv.commitFail"));` |
| `frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:133` | `setSuppliersError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:144` | `setRuleError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:155` | `setAliasError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:202` | `setRuleError(err instanceof Error ? err.message : t("common.saveError"));` |
| `frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:262` | `setAliasError(err instanceof Error ? err.message : t("common.saveError"));` |
| `frontend/src/pages/super-admin/ProductCategoriesImportPage.tsx:58` | `setError(e instanceof ApiError ? e.message : t("productCategoriesCsv.commitFail"));` |
| `frontend/src/pages/super-admin/ViewerAccountsPage.tsx:282` | `return e.message === "viewer_already_linked"` |
| `frontend/src/pages/super-admin/TcgLineImportPage.tsx:128` | `setHistoryError(e instanceof Error ? e.message : t("tcgLineImport.errorHistoryFailed"));` |
| `frontend/src/pages/super-admin/TcgLineImportPage.tsx:239` | `setUploadError(e instanceof Error ? e.message : t("tcgLineImport.errorUploadFailed"));` |
| `frontend/src/pages/super-admin/NoteMasterImportPage.tsx:52` | `setError(e instanceof ApiError ? e.message : t("noteMasterCsv.commitFail"));` |
| `frontend/src/pages/super-admin/ViewerTemplatesPage.tsx:155` | `else if (e instanceof ApiError && e.status === 422 && ERROR_KEYS[e.message]) {` |
| `frontend/src/pages/super-admin/ViewerTemplatesPage.tsx:156` | `setSaveError(t('${f}.${ERROR_KEYS[e.message]}'));` |
| `frontend/src/pages/super-admin/ExtractionPromptConfigTab.tsx:74` | `setFetchError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/super-admin/ExtractionPromptConfigTab.tsx:102` | `[key]: e instanceof Error ? e.message : t('${p}.error'),` |
| `frontend/src/pages/super-admin/SupplierImportPage.tsx:52` | `setError(e instanceof ApiError ? e.message : t("productCsv.previewFailed"));` |
| `frontend/src/pages/super-admin/StatusMasterImportPage.tsx:52` | `setError(e instanceof ApiError ? e.message : t("statusMasterCsv.commitFail"));` |
| `frontend/src/pages/super-admin/ConditionImportPage.tsx:52` | `setError(e instanceof ApiError ? e.message : t("conditionCsv.commitFail"));` |
| `frontend/src/pages/commissions/CommissionsPage.tsx:71` | `const shownError = monthlyQ.error ? (monthlyQ.error instanceof Error ? monthlyQ.error.message : t("common.fetchError")) : "";` |
| `frontend/src/pages/badges/BadgesPage.tsx:30` | `} catch (e) { setError(e instanceof Error ? e.message : t("common.fetchError")); }` |
| `frontend/src/pages/badges/BadgesPage.tsx:41` | `} catch (e) { setError(e instanceof Error ? e.message : t("common.saveError")); }` |
| `frontend/src/pages/sales/SalesPage.tsx:62` | `const shownError = salesQ.error ? (salesQ.error instanceof Error ? salesQ.error.message : t("common.fetchError")) : "";` |
| `frontend/src/pages/admin/TenantPolicyPage.tsx:85` | `const readError = policyQ.error ? (policyQ.error instanceof Error ? policyQ.error.message : t("common.fetchError")) : "";` |
| `frontend/src/pages/admin/TenantPolicyPage.tsx:117` | `err instanceof Error ? err.message : t("common.operationError"),` |
| `frontend/src/pages/admin/TenantProfilePage.tsx:89` | `const readError = profileQ.error ? (profileQ.error instanceof Error ? profileQ.error.message : t("common.fetchError")) : "";` |
| `frontend/src/pages/admin/TenantProfilePage.tsx:114` | `setError(err instanceof Error ? err.message : t("common.operationError"));` |
| `frontend/src/pages/admin/InventoryVisibilityPage.tsx:72` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/admin/InventoryVisibilityPage.tsx:107` | `setError(e instanceof Error ? e.message : t("common.saveError"));` |
| `frontend/src/pages/bots/BotsPage.tsx:139` | `setError(err instanceof Error ? err.message : t("common.saveError"));` |
| `frontend/src/pages/bots/BotsPage.tsx:162` | `setError(err instanceof Error ? err.message : t("common.saveError"));` |
| `frontend/src/pages/bots/BotsPage.tsx:175` | `setError(err instanceof Error ? err.message : t("common.operationError"));` |
| `frontend/src/pages/bots/BotsPage.tsx:187` | `setError(err instanceof Error ? err.message : t("common.deleteError"));` |
| `frontend/src/pages/bots/BotEditPage.tsx:73` | `setError(e instanceof Error ? e.message : t("common.saveError"));` |
| `frontend/src/pages/companies/CompaniesPage.tsx:216` | `? (companiesQuery.error instanceof Error ? companiesQuery.error.message : t("common.fetchError"))` |
| `frontend/src/pages/companies/CompaniesPage.tsx:313` | `setError(e instanceof Error ? e.message : t("common.saveError"));` |
| `frontend/src/pages/companies/CompaniesPage.tsx:335` | `setError(e instanceof Error ? e.message : t("common.saveError"));` |
| `frontend/src/pages/companies/CompaniesPage.tsx:346` | `setError(e instanceof Error ? e.message : t("common.deleteError"));` |
| `frontend/src/pages/teams/TeamsPage.tsx:71` | `const shownError = error \|\| (teamsQ.error ? (teamsQ.error instanceof Error ? teamsQ.error.message : t("common.fetchError")) : "");` |
| `frontend/src/pages/teams/TeamsPage.tsx:85` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/teams/TeamsPage.tsx:103` | `setError(e instanceof Error ? e.message : t("common.saveError"));` |
| `frontend/src/pages/teams/TeamsPage.tsx:121` | `setError(e instanceof Error ? e.message : t("common.saveError"));` |
| `frontend/src/pages/teams/TeamsPage.tsx:133` | `setError(e instanceof Error ? e.message : t("common.deleteError"));` |
| `frontend/src/pages/teams/TeamsPage.tsx:151` | `setError(e instanceof Error ? e.message : t("common.operationError"));` |
| `frontend/src/pages/teams/TeamsPage.tsx:162` | `setError(e instanceof Error ? e.message : t("common.deleteError"));` |
| `frontend/src/pages/teams/TeamEditPage.tsx:38` | `const shownError = error \|\| (teamQ.error ? (teamQ.error instanceof Error ? teamQ.error.message : t("common.fetchError")) : "");` |
| `frontend/src/pages/teams/TeamEditPage.tsx:53` | `setError(e instanceof Error ? e.message : t("common.saveError"));` |
| `frontend/src/pages/conditions/ConditionsPage.tsx:109` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/conditions/ConditionsPage.tsx:142` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/conditions/ConditionsPage.tsx:170` | `setError(e instanceof Error ? e.message : t("common.saveError"));` |
| `frontend/src/pages/conditions/ConditionsPage.tsx:184` | `setError(e instanceof Error ? e.message : t("common.saveError"));` |
| `frontend/src/pages/conditions/ConditionsPage.tsx:197` | `setError(e instanceof Error ? e.message : t("common.deleteError"));` |
| `frontend/src/pages/conditions/ConditionsPage.tsx:213` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/conditions/ConditionsPage.tsx:228` | `setError(e instanceof Error ? e.message : t("common.saveError"));` |
| `frontend/src/pages/conditions/ConditionsPage.tsx:238` | `setError(e instanceof Error ? e.message : t("common.deleteError"));` |
| `frontend/src/pages/conditions/ConditionImportPage.tsx:52` | `setError(e instanceof ApiError ? e.message : t("conditionCsv.commitFail"));` |
| `frontend/src/pages/quote-create/QuoteCreatePage.tsx:134` | `setError(e instanceof Error ? e.message : t("common.saveError"));` |
| `frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:97` | `const shownError = error \|\| (mode === "quote" && quotesQ.error ? (quotesQ.error instanceof Error ? quotesQ.error.message : t("common.fetchError")) : "");` |
| `frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:160` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:207` | `setError(e instanceof Error ? e.message : t("common.saveError"));` |
| `frontend/src/pages/invoices/InvoicesPage.tsx:50` | `const shownError = invoicesQ.error ? (invoicesQ.error instanceof Error ? invoicesQ.error.message : t("common.fetchError")) : "";` |
| `frontend/src/pages/orders/useOrdersState.ts:169` | `const shownError = error \|\| (ordersQ.error ? (ordersQ.error instanceof Error ? ordersQ.error.message : t("common.fetchError")) : "");` |
| `frontend/src/pages/orders/useOrdersState.ts:224` | `setError(e instanceof Error ? e.message : t("common.saveError"));` |
| `frontend/src/pages/orders/useOrdersState.ts:250` | `setError(e instanceof Error ? e.message : t("common.deleteError"));` |
| `frontend/src/pages/orders/useOrdersState.ts:267` | `setError(e instanceof Error ? e.message : t("common.saveError"));` |
| `frontend/src/pages/staff-reports/StaffReportsPage.tsx:34` | `const shownError = error \|\| (reportsQ.error ? (reportsQ.error instanceof Error ? reportsQ.error.message : t("common.fetchError")) : "");` |
| `frontend/src/pages/staff-reports/StaffReportsPage.tsx:49` | `} catch (e) { setError(e instanceof Error ? e.message : t("common.saveError")); }` |
| `frontend/src/pages/quotes/QuotesPage.tsx:54` | `const shownError = quotesQ.error ? (quotesQ.error instanceof Error ? quotesQ.error.message : t("common.fetchError")) : "";` |
| `frontend/src/pages/channels/ChannelsPage.tsx:103` | `const loadError = channelsQ.error ? (channelsQ.error instanceof ApiError ? channelsQ.error.message : (channelsQ.error instanceof Error ? channelsQ.error.message : t("channels.loadErrorFallback"))) : "";` |
| `frontend/src/pages/channels/ChannelsPage.tsx:226` | `const msg = e instanceof ApiError ? e.message : (e instanceof Error ? e.message : t("channels.discordConnectError"));` |
| `frontend/src/pages/channels/ChannelsPage.tsx:244` | `const msg = e instanceof ApiError ? e.message : (e instanceof Error ? e.message : t("channels.discordConnectError"));` |
| `frontend/src/pages/channels/ChannelsPage.tsx:263` | `const msg = e instanceof ApiError ? e.message : (e instanceof Error ? e.message : t("channels.connectError"));` |
| `frontend/src/pages/channels/ChannelsPage.tsx:282` | `const msg = e instanceof ApiError ? e.message : (e instanceof Error ? e.message : t("channels.disconnectFailedMsg", { msg: "" }));` |
| `frontend/src/pages/units/UnitImportPage.tsx:52` | `setError(e instanceof ApiError ? e.message : t("unitCsv.commitFail"));` |
| `frontend/src/pages/units/UnitsPage.tsx:74` | `const shownError = error \|\| (unitsQ.error ? (unitsQ.error instanceof Error ? unitsQ.error.message : t("common.fetchError")) : "");` |
| `frontend/src/pages/units/UnitsPage.tsx:90` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/units/UnitsPage.tsx:127` | `setError(e instanceof Error ? e.message : t("common.saveError"));` |
| `frontend/src/pages/units/UnitsPage.tsx:148` | `setError(e instanceof Error ? e.message : t("common.saveError"));` |
| `frontend/src/pages/units/UnitsPage.tsx:159` | `setError(e instanceof Error ? e.message : t("common.deleteError"));` |
| `frontend/src/pages/register/RegisterChangeBillingPage.tsx:120` | `setError(err.message \|\| t("registration.invalidToken"));` |
| `frontend/src/pages/register/RegisterChangeBillingPage.tsx:178` | `const rawDetail = body?.detail;` |
| `frontend/src/pages/register/RegisterChangeBillingPage.tsx:187` | `setError(err instanceof Error ? err.message : t("registration.submitError"));` |
| `frontend/src/pages/register/RegisterAddressPage.tsx:211` | `setError(err.message \|\| t("registration.invalidToken"));` |
| `frontend/src/pages/register/RegisterAddressPage.tsx:241` | `const rawDetail = body?.detail;` |
| `frontend/src/pages/register/RegisterAddressPage.tsx:250` | `setError(err instanceof Error ? err.message : t("registration.submitError"));` |
| `frontend/src/pages/register/RegisterPage.tsx:131` | `setError(err.message \|\| t("registration.invalidToken"));` |
| `frontend/src/pages/register/RegisterPage.tsx:226` | `const rawDetail = body?.detail;` |
| `frontend/src/pages/register/RegisterPage.tsx:235` | `setError(err instanceof Error ? err.message : t("registration.submitError"));` |
| `frontend/src/pages/oauth-callback/OAuthCallbackPage.tsx:47` | `const msg = err.message \|\| "";` |
| `frontend/src/pages/oauth-callback/OAuthCallbackPage.tsx:126` | `setError(e instanceof Error ? e.message : t("oauth.error"));` |
| `frontend/src/pages/archives/ArchivesPage.tsx:20` | `const shownError = error \|\| (archivesQ.error ? (archivesQ.error instanceof Error ? archivesQ.error.message : t("common.fetchError")) : "");` |
| `frontend/src/pages/archives/ArchivesPage.tsx:29` | `catch (e) { setError(e instanceof Error ? e.message : t("common.operationError")); }` |
| `frontend/src/pages/shifts/ShiftsPage.tsx:26` | `const shownError = error \|\| (shiftsQ.error ? (shiftsQ.error instanceof Error ? shiftsQ.error.message : t("common.fetchError")) : "");` |
| `frontend/src/pages/shifts/ShiftsPage.tsx:38` | `} catch (e) { setError(e instanceof Error ? e.message : t("common.saveError")); }` |
| `frontend/src/pages/shifts/ShiftsPage.tsx:43` | `catch (e) { setError(e instanceof Error ? e.message : t("common.deleteError")); }` |
| `frontend/src/pages/notifications/NotificationsPage.tsx:75` | `} catch (e) { setError(e instanceof Error ? e.message : t("common.saveError")); }` |
| `frontend/src/pages/notifications/NotificationsPage.tsx:97` | `} catch (e) { setError(e instanceof Error ? e.message : t("common.saveError")); }` |
| `frontend/src/pages/notifications/NotificationsPage.tsx:102` | `catch (e) { setError(e instanceof Error ? e.message : t("common.deleteError")); }` |
| `frontend/src/pages/notifications/NoticeFallbackSection.tsx:47` | `setError(e instanceof Error ? e.message : t("common.saveError"));` |
| `frontend/src/pages/leads/LeadsPage.tsx:190` | `setError(e instanceof Error ? e.message : t("common.saveError"));` |
| `frontend/src/pages/leads/LeadsPage.tsx:219` | `setError(e instanceof Error ? e.message : t("common.saveError"));` |
| `frontend/src/pages/leads/LeadsPage.tsx:231` | `setError(e instanceof Error ? e.message : t("common.deleteError"));` |
| `frontend/src/pages/leads/LeadsPage.tsx:261` | `setError(e instanceof Error ? e.message : t("common.operationError"));` |
| `frontend/src/pages/leads/LeadEditPage.tsx:141` | `setError(e instanceof Error ? e.message : t("common.saveError"));` |
| `frontend/src/pages/contacts/ContactEditPage.tsx:117` | `setError(e instanceof Error ? e.message : t("common.saveError"));` |
| `frontend/src/pages/contacts/ContactEditPage.tsx:129` | `setError(e instanceof Error ? e.message : t("common.operationError"));` |
| `frontend/src/pages/contacts/ContactsPage.tsx:137` | `const shownError = error \|\| (contactsQ.error ? (contactsQ.error instanceof Error ? contactsQ.error.message : t("common.fetchError")) : "");` |
| `frontend/src/pages/contacts/ContactsPage.tsx:181` | `setError(e instanceof Error ? e.message : t("common.saveError"));` |
| `frontend/src/pages/contacts/ContactsPage.tsx:204` | `setError(e instanceof Error ? e.message : t("common.saveError"));` |
| `frontend/src/pages/contacts/ContactsPage.tsx:215` | `setError(e instanceof Error ? e.message : t("common.deleteError"));` |
| `frontend/src/pages/contacts/ContactsPage.tsx:229` | `setError(e instanceof Error ? e.message : t("common.operationError"));` |
| `frontend/src/pages/note-master/NoteMasterImportPage.tsx:52` | `setError(e instanceof ApiError ? e.message : t("noteMasterCsv.commitFail"));` |
| `frontend/src/pages/note-master/NoteMasterPage.tsx:112` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/note-master/NoteMasterPage.tsx:124` | `const shownError = error \|\| (notesQ.error ? (notesQ.error instanceof Error ? notesQ.error.message : t("common.fetchError")) : "");` |
| `frontend/src/pages/note-master/NoteMasterPage.tsx:167` | `setError(e instanceof Error ? e.message : t("common.saveError"));` |
| `frontend/src/pages/note-master/NoteMasterPage.tsx:195` | `setError(e instanceof Error ? e.message : t("common.saveError"));` |
| `frontend/src/pages/note-master/NoteMasterPage.tsx:206` | `setError(e instanceof Error ? e.message : t("common.deleteError"));` |
| `frontend/src/pages/staff/StaffPage.tsx:175` | `setError(err instanceof Error ? err.message : t("common.saveError"));` |
| `frontend/src/pages/staff/StaffPage.tsx:197` | `setError(err instanceof Error ? err.message : t("common.saveError"));` |
| `frontend/src/pages/staff/StaffPage.tsx:209` | `setError(err instanceof Error ? err.message : t("common.deleteError"));` |
| `frontend/src/pages/staff/StaffJoinInviteModals.tsx:103` | `setError(err instanceof Error ? err.message : t("common.saveError"));` |
| `frontend/src/pages/staff/StaffJoinInviteModals.tsx:173` | `setError(err instanceof Error ? err.message : t("common.saveError"));` |
| `frontend/src/pages/staff/StaffJoinInviteModals.tsx:189` | `setError(err instanceof Error ? err.message : t("common.saveError"));` |
| `frontend/src/pages/staff/StaffJoinInviteModals.tsx:219` | `? (invitesQ.error instanceof Error ? invitesQ.error.message : t("common.fetchError"))` |
| `frontend/src/pages/staff/StaffEditPage.tsx:140` | `setError(e instanceof Error ? e.message : t("common.saveError"));` |
| `frontend/src/pages/buyback-prices/BuybackProductHistoryDrawer.tsx:171` | `const msg = err instanceof Error ? err.message : null;` |
| `frontend/src/pages/buyback-prices/BuybackProductHistoryDrawer.tsx:190` | `const msg = err instanceof Error ? err.message : null;` |
| `frontend/src/pages/integrations/FedexLabelValidationTab.tsx:98` | `setLabelError(e instanceof Error ? e.message : t("common.operationError"));` |
| `frontend/src/pages/integrations/FedexLabelValidationTab.tsx:136` | `setCoverError(e instanceof Error ? e.message : t("common.operationError"));` |
| `frontend/src/pages/integrations/FedexLabelValidationTab.tsx:150` | `setEmailError(e instanceof Error ? e.message : t("common.operationError"));` |
| `frontend/src/pages/integrations/CarrierCredentialForm.tsx:78` | `setError(e instanceof Error ? e.message : t("common.operationError"));` |
| `frontend/src/pages/integrations/CarrierIntegrationPage.tsx:122` | `setError(e instanceof Error ? e.message : t("common.operationError"));` |
| `frontend/src/pages/integrations/CarrierIntegrationPage.tsx:138` | `setError(e instanceof Error ? e.message : t("common.operationError"));` |
| `frontend/src/pages/integrations/GoogleDriveIntegrationPage.tsx:70` | `setError(e instanceof Error ? e.message : t("common.operationError"));` |
| `frontend/src/pages/integrations/GoogleDriveIntegrationPage.tsx:84` | `setError(e instanceof Error ? e.message : t("common.operationError"));` |
| `frontend/src/pages/integrations/GoogleDriveIntegrationPage.tsx:101` | `setError(e instanceof Error ? e.message : t("common.operationError"));` |
| `frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:231` | `if (!cancelled) setStatusError(e instanceof Error ? e.message : t("common.operationError"));` |
| `frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:345` | `[imageType === "LETTERHEAD" ? "letterhead" : "signature"]: e instanceof Error ? e.message : t("common.operationError"),` |
| `frontend/src/pages/integrations/PaypalIntegrationPage.tsx:83` | `setError(e instanceof Error ? e.message : t("common.operationError"));` |
| `frontend/src/pages/integrations/PaypalIntegrationPage.tsx:97` | `setError(e instanceof Error ? e.message : t("common.operationError"));` |
| `frontend/src/pages/integrations/PaypalIntegrationPage.tsx:111` | `setError(e instanceof Error ? e.message : t("common.operationError"));` |
| `frontend/src/pages/integrations/PaypalIntegrationPage.tsx:126` | `setError(e instanceof Error ? e.message : t("common.operationError"));` |
| `frontend/src/pages/inventory/InventoryPage.tsx:269` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/schedule/ScheduleSettingsPage.tsx:56` | `const shownError = error ?? (ownersQ.error ? (ownersQ.error instanceof Error ? ownersQ.error.message : t("common.fetchError")) : null);` |
| `frontend/src/pages/schedule/ScheduleSettingsPage.tsx:86` | `setError(e instanceof Error ? e.message : t("common.saveError"));` |
| `frontend/src/pages/schedule/SchedulePageImpl.tsx:1109` | `setError(err instanceof Error ? err.message : t("common.saveError"));` |
| `frontend/src/pages/schedule/SchedulePageImpl.tsx:1126` | `setError(err instanceof Error ? err.message : t("common.deleteError"));` |
| `frontend/src/pages/schedule/SchedulePageImpl.tsx:1277` | `setError(err instanceof Error ? err.message : t("common.saveError"));` |
| `frontend/src/pages/status-master/StatusMasterPage.tsx:100` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/status-master/StatusMasterPage.tsx:112` | `const shownError = error \|\| (itemsQ.error ? (itemsQ.error instanceof Error ? itemsQ.error.message : t("common.fetchError")) : "");` |
| `frontend/src/pages/status-master/StatusMasterPage.tsx:152` | `setError(e instanceof Error ? e.message : t("common.saveError"));` |
| `frontend/src/pages/status-master/StatusMasterPage.tsx:166` | `setError(e instanceof Error ? e.message : t("common.saveError"));` |
| `frontend/src/pages/status-master/StatusMasterPage.tsx:177` | `setError(e instanceof Error ? e.message : t("common.deleteError"));` |
| `frontend/src/pages/status-master/StatusMasterImportPage.tsx:52` | `setError(e instanceof ApiError ? e.message : t("statusMasterCsv.commitFail"));` |
| `frontend/src/pages/roles/RolesPage.tsx:228` | `setError(e instanceof Error ? e.message : t("common.saveError"));` |
| `frontend/src/pages/roles/RolesPage.tsx:276` | `setError(err instanceof Error ? err.message : t("common.saveError"));` |
| `frontend/src/pages/roles/RolesPage.tsx:287` | `setError(e instanceof Error ? e.message : t("common.deleteError"));` |
| `frontend/src/pages/products/ProductEditPage.tsx:94` | `if (!cancelled) setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/products/ProductEditPage.tsx:166` | `setError(requiredFieldsMessage(e, t) ?? (e instanceof Error ? e.message : t("common.saveError")));` |
| `frontend/src/pages/products/ProductsPage.tsx:72` | `const shownError = error \|\| (productsQ.error ? (productsQ.error instanceof Error ? productsQ.error.message : t("common.fetchError")) : "");` |
| `frontend/src/pages/products/ProductsPage.tsx:118` | `setError(e instanceof Error ? e.message : t("common.saveError"));` |
| `frontend/src/pages/quote-detail/QuoteDetailPage.tsx:64` | `const shownError = error \|\| (quoteQ.error ? (quoteQ.error instanceof Error ? quoteQ.error.message : t("common.fetchError")) : "");` |
| `frontend/src/pages/quote-detail/QuoteDetailPage.tsx:78` | `setError(e instanceof Error ? e.message : t("common.operationError"));` |
| `frontend/src/pages/quote-detail/QuoteDetailPage.tsx:87` | `setError(e instanceof Error ? e.message : t("common.operationError"));` |
| `frontend/src/pages/quote-detail/QuoteDetailPage.tsx:102` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/staff-join/StaffJoinPage.tsx:73` | `setLoadTooMany(err instanceof Error && err.message === "429");` |
| `frontend/src/pages/staff-join/StaffJoinPage.tsx:112` | `setError(typeof body?.detail === "string" ? body.detail : t("staffJoin.submitError"));` |
| `frontend/src/pages/suppliers/SupplierEditPage.tsx:46` | `const shownError = error \|\| (supplierQ.error ? (supplierQ.error instanceof Error ? supplierQ.error.message : t("common.fetchError")) : "");` |
| `frontend/src/pages/suppliers/SupplierEditPage.tsx:70` | `setError(e instanceof Error ? e.message : t("common.saveError"));` |
| `frontend/src/pages/suppliers/SupplierImportPage.tsx:52` | `setError(e instanceof ApiError ? e.message : t("productCsv.previewFailed"));` |
| `frontend/src/pages/suppliers/SuppliersPage.tsx:72` | `? (suppliersQuery.error instanceof Error ? suppliersQuery.error.message : t("common.fetchError"))` |
| `frontend/src/pages/suppliers/SuppliersPage.tsx:85` | `} catch (e) { setError(e instanceof Error ? e.message : t("common.saveError")); }` |
| `frontend/src/pages/suppliers/SuppliersPage.tsx:97` | `} catch (e) { setError(e instanceof Error ? e.message : t("common.saveError")); }` |
| `frontend/src/pages/suppliers/SuppliersPage.tsx:104` | `catch (e) { setError(e instanceof Error ? e.message : t("common.deleteError")); }` |
| `frontend/src/pages/suppliers/SuppliersPage.tsx:121` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/inbox/useInboxState.ts:398` | `(e instanceof Error && /^HTTP 50[23]/.test(e.message));` |
| `frontend/src/pages/inbox/useInboxState.ts:401` | `console.warn('[InboxPage] transient error #${transientErrorCountRef.current}:', e instanceof Error ? e.message : e);` |
| `frontend/src/pages/inbox/useInboxState.ts:406` | `const msg = e instanceof ApiError ? e.message : t("inbox.fetchError");` |
| `frontend/src/pages/inbox/useInboxState.ts:439` | `console.warn('[InboxPage] loadMessages transient error #${msgTransientErrorCountRef.current}:', e instanceof Error ? e.message : e);` |
| `frontend/src/pages/inbox/useInboxState.ts:444` | `const msg = e instanceof ApiError ? e.message : t("inbox.fetchError");` |
| `frontend/src/pages/inbox/useInboxState.ts:569` | `setCardSaveError(e instanceof Error ? e.message : t("common.saveError"));` |
| `frontend/src/pages/inbox/useInboxState.ts:847` | `setSendError(e.message \|\| t("inbox.sendError.generic"));` |
| `frontend/src/pages/inbox/useInboxState.ts:851` | `setSendError(e.message);` |
| `frontend/src/pages/inbox/useInboxState.ts:960` | `: e instanceof Error ? e.message : t("common.fetchError")` |
| `frontend/src/pages/inbox/useInboxState.ts:1000` | `setConvertError(e instanceof Error ? e.message : t("common.saveError"));` |
| `frontend/src/pages/inbox/OutboundTranslationPreview.tsx:55` | `const msg = err instanceof Error ? err.message : t("translation.outbound.previewError");` |
| `frontend/src/pages/inbox/OutboundTranslationPreview.tsx:77` | `const msg = err instanceof Error ? err.message : t("translation.outbound.confirmError");` |
| `frontend/src/pages/product-categories/ProductCategoriesPage.tsx:94` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/product-categories/ProductCategoriesPage.tsx:107` | `setError(e instanceof Error ? e.message : t("common.fetchError"));` |
| `frontend/src/pages/product-categories/ProductCategoriesPage.tsx:129` | `setError(e instanceof Error ? e.message : t("common.saveError"));` |
| `frontend/src/pages/product-categories/ProductCategoriesPage.tsx:147` | `setError(e instanceof Error ? e.message : t("common.saveError"));` |
| `frontend/src/pages/product-categories/ProductCategoriesPage.tsx:158` | `setError(e instanceof Error ? e.message : t("common.deleteError"));` |
| `frontend/src/pages/product-categories/ProductCategoriesImportPage.tsx:58` | `setError(e instanceof ApiError ? e.message : t("productCategoriesCsv.commitFail"));` |
| `frontend/src/pages/company-detail/CompanyAddressModal.tsx:65` | `setAddrModalError(err instanceof Error ? err.message : t("common.saveError"));` |
| `frontend/src/pages/company-detail/useCompanyDetail.ts:121` | `setError(err instanceof Error ? err.message : t("common.saveError"));` |
| `frontend/src/pages/company-detail/useCompanyDetail.ts:140` | `setError(err instanceof Error ? err.message : t("common.saveError"));` |
| `frontend/src/pages/company-detail/useCompanyDetail.ts:163` | `setError(err instanceof Error ? err.message : t("common.saveError"));` |
| `frontend/src/pages/company-detail/useCompanyDetail.ts:176` | `setError(err instanceof Error ? err.message : t("common.deleteError"));` |
| `frontend/src/pages/company-detail/useCompanyDetail.ts:240` | `setError(err instanceof Error ? err.message : t("common.operationError"));` |
| `frontend/src/pages/company-detail/useCompanyDetail.ts:284` | `setError(err instanceof Error ? err.message : t("common.saveError"));` |
| `frontend/src/pages/company-detail/useCompanyDetail.ts:297` | `setError(err instanceof Error ? err.message : t("common.deleteError"));` |
| `frontend/src/pages/company-detail/useCompanyDetail.ts:311` | `setError(err instanceof Error ? err.message : t("common.deleteError"));` |
| `frontend/src/pages/buddy/BuddyPage.tsx:30` | `} catch (e) { setError(e instanceof Error ? e.message : t("common.fetchError")); }` |
| `frontend/src/pages/buddy/BuddyPage.tsx:41` | `} catch (e) { setError(e instanceof Error ? e.message : t("common.saveError")); }` |
| `frontend/src/pages/buddy/BuddyPage.tsx:46` | `catch (e) { setError(e instanceof Error ? e.message : t("common.operationError")); }` |
| `frontend/src/pages/dashboard/WeeklyAdvisorSection.tsx:131` | `const error = FUNNEL_MOCK ? null : listQuery.error ? listQuery.error.message \|\| t("common.errorLoad") : null;` |
| `frontend/src/pages/dashboard/WeeklyAdvisorSection.tsx:259` | `error: err instanceof Error ? err.message : t("common.saveError"),` |
| `frontend/src/pages/dashboard/FunnelSection.tsx:464` | `const error = FUNNEL_MOCK ? "" : [funnelQuery, revenueQuery, followUpsQuery].find((q) => q.error)?.error?.message ?? "";` |
| `frontend/src/pages/dashboard/PriorityProspectsSection.tsx:135` | `const error = FUNNEL_MOCK ? null : listQuery.error ? listQuery.error.message \|\| t("common.errorLoad") : null;` |
| `frontend/src/pages/dashboard/PriorityProspectsSection.tsx:240` | `error: err instanceof Error ? err.message : t("common.saveError"),` |
| `frontend/src/pages/dashboard/DashboardPage.tsx:348` | `const error = queries.find((q) => q.error)?.error?.message ?? "";` |
| `frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx:125` | `const shownError = error \|\| (invoiceQ.error ? (invoiceQ.error instanceof Error ? invoiceQ.error.message : t("common.fetchError")) : "");` |
| `frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx:140` | `setError(e instanceof Error ? e.message : t("common.operationError"));` |
| `frontend/src/pages/commission-settings/CommissionSettingsPage.tsx:116` | `const shownError = error \|\| (settingsQ.error ? (settingsQ.error instanceof Error ? settingsQ.error.message : t("common.fetchError")) : "");` |
| `frontend/src/pages/commission-settings/CommissionSettingsPage.tsx:134` | `setError(err instanceof Error ? err.message : t("common.saveError"));` |
| `frontend/src/pages/erp/ERPPage.tsx:22` | `const shownError = error \|\| (logsQ.error ? (logsQ.error instanceof Error ? logsQ.error.message : t("common.fetchError")) : "");` |
| `frontend/src/pages/erp/ERPPage.tsx:46` | `} catch (e) { setError(e instanceof Error ? e.message : t("common.operationError")); }` |

## C. backend/app の HTTPException detail に日本語を直接書いた箇所 全 646 行

抽出命令: `grep -rnE "HTTPException" -A4 backend/app | grep -E "detail\s*=\s*f?[\"'].*[ぁ-んァ-ン一-龥]"`

| ファイル:行 | 原文 |
|---|---|
| `backend/app/auth/dependencies.py:190` | `detail="このトークンは無効化されています",` |
| `backend/app/auth/dependencies.py:223` | `detail="認証試行が上限に達しました。しばらく時間をおいてから再試行してください",` |
| `backend/app/auth/dependencies.py:256` | `detail="テナントが無効です",` |
| `backend/app/auth/dependencies.py:268` | `detail="テナントが無効です",` |
| `backend/app/auth/dependencies.py:514` | `detail="この操作にはJarvis運用admin（中央admin）権限が必要です",` |
| `backend/app/auth/dependencies.py:590` | `detail="この操作は管理者のみ実行できます",` |
| `backend/app/auth/dependencies.py:638` | `detail=f"権限が不足しています: {', '.join(sorted(required))}",` |
| `backend/app/auth/dependencies.py:673` | `detail=f"機能が無効です: {feature_key}",` |
| `backend/app/services/role_assignment.py:31` | `detail="自分と同格以上のスタッフのロールは変更できません",` |
| `backend/app/services/role_assignment.py:58` | `detail="指定の role_id はこのテナントに存在しません",` |
| `backend/app/services/role_assignment.py:65` | `detail=f"自分の最大priority以上のロール（id={role_id}）は付与できません",` |
| `backend/app/routers/staff_reports.py:158` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="レポートが見つかりません")` |
| `backend/app/routers/tenant_profile.py:81` | `detail="tenant_profile が初期化されていません",` |
| `backend/app/routers/tenant_profile.py:107` | `detail="tenant_profile が初期化されていません (migration 069 適用要)",` |
| `backend/app/routers/calendar.py:208` | `detail="現在のユーザーに紐づく担当者が見つかりません",` |
| `backend/app/routers/calendar.py:268` | `detail="この操作にはマネージャー権限が必要です",` |
| `backend/app/routers/calendar.py:280` | `detail=f"share_mode は {_VALID_OWNER_SHARE_MODES} のいずれかを指定してください",` |
| `backend/app/routers/calendar.py:287` | `detail="更新フィールドが指定されていません",` |
| `backend/app/routers/calendar.py:304` | `detail="担当者が見つかりません",` |
| `backend/app/routers/calendar.py:355` | `detail="担当者が見つかりません",` |
| `backend/app/routers/calendar.py:387` | `detail="calendar_type は 'shared' または 'personal' を指定してください",` |
| `backend/app/routers/calendar.py:407` | `detail="イベントの作成に失敗しました",` |
| `backend/app/routers/calendar.py:430` | `detail="更新フィールドが指定されていません",` |
| `backend/app/routers/calendar.py:443` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="イベントが見つかりません")` |
| `backend/app/routers/calendar.py:450` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="イベントが見つかりません")` |
| `backend/app/routers/calendar.py:453` | `raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="編集権限がありません")` |
| `backend/app/routers/calendar.py:459` | `detail="calendar_type は 'shared' または 'personal' を指定してください",` |
| `backend/app/routers/calendar.py:464` | `detail="見せ方を変えられるのは予定の持ち主だけです",` |
| `backend/app/routers/calendar.py:499` | `detail="イベントの更新に失敗しました",` |
| `backend/app/routers/calendar.py:523` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="イベントが見つかりません")` |
| `backend/app/routers/calendar.py:527` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="イベントが見つかりません")` |
| `backend/app/routers/calendar.py:530` | `raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="削除権限がありません")` |
| `backend/app/routers/calendar.py:568` | `detail=f"sync_mode は {_VALID_SYNC_MODES} のいずれかを指定してください",` |
| `backend/app/routers/calendar.py:573` | `detail="Google の予定をアプリへ取り込む設定は使えません（ADR-1057）",` |
| `backend/app/routers/tcg_line_import.py:167` | `detail="テキスト (.txt) ファイルをアップロードしてください",` |
| `backend/app/routers/tcg_line_import.py:179` | `detail="ファイルのエンコーディングが UTF-8 ではありません",` |
| `backend/app/routers/tcg_line_import.py:371` | `raise HTTPException(status_code=404, detail="import_job が見つかりません")` |
| `backend/app/routers/tcg_line_import.py:443` | `raise HTTPException(status_code=404, detail="import_job が見つかりません")` |
| `backend/app/routers/tcg_line_import.py:447` | `detail=f"review_status={job[0]} のジョブは変更できません",` |
| `backend/app/routers/tcg_line_import.py:465` | `detail="action='assign' のとき supplier_code は必須です",` |
| `backend/app/routers/tcg_line_import.py:478` | `detail=f"supplier_code={body.supplier_code} が見つかりません",` |
| `backend/app/routers/tcg_line_import.py:494` | `detail=f"'{body.display_name}' は別の仕入元に既に使われています（重複名は照合が壊れます）",` |
| `backend/app/routers/tcg_line_import.py:544` | `detail="action は 'assign' または 'create' を指定してください",` |
| `backend/app/routers/tcg_line_import.py:603` | `raise HTTPException(status_code=404, detail="import_job が見つかりません")` |
| `backend/app/routers/tcg_line_import.py:607` | `detail=f"review_status={job[0]} のジョブはコミットできません",` |
| `backend/app/routers/tcg_line_import.py:614` | `detail="pending_messages が空です",` |
| `backend/app/routers/tcg_line_import.py:721` | `raise HTTPException(status_code=400, detail="Android LINEの.txtファイルが必要です")` |
| `backend/app/routers/tcg_line_import.py:724` | `raise HTTPException(status_code=413, detail="ファイルは10MiB以下にしてください")` |
| `backend/app/routers/tcg_line_import.py:731` | `raise HTTPException(status_code=400, detail="UTF-8のファイルが必要です") from error` |
| `backend/app/routers/tcg_line_import.py:745` | `raise HTTPException(status_code=400, detail="Android LINEの履歴形式を確認してください") from error` |
| `backend/app/routers/notice_fallback_recipients.py:93` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会社が見つかりません")` |
| `backend/app/routers/notice_fallback_recipients.py:105` | `detail="同じ会社の有効な人だけを選べます",` |
| `backend/app/routers/fx_rate_admin.py:90` | `detail=f"為替レートが未取得です: {currency.upper()}",` |
| `backend/app/routers/fx_rate_admin.py:129` | `detail="外部 API から為替レートを取得できませんでした。しばらく待ってから再試行してください。",` |
| `backend/app/routers/fx_rate_admin.py:166` | `raise HTTPException(status_code=500, detail="追記後の行取得に失敗しました")` |
| `backend/app/routers/teams.py:93` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="チームが見つかりません")` |
| `backend/app/routers/teams.py:130` | `detail="同じ名前のチームが既に存在します",` |
| `backend/app/routers/teams.py:159` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="チームが見つかりません")` |
| `backend/app/routers/teams.py:166` | `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="更新するフィールドを指定してください")` |
| `backend/app/routers/teams.py:180` | `detail="同じ名前のチームが既に存在します",` |
| `backend/app/routers/teams.py:208` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="チームが見つかりません")` |
| `backend/app/routers/teams.py:234` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="チームが見つかりません")` |
| `backend/app/routers/teams.py:266` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="チームが見つかりません")` |
| `backend/app/routers/teams.py:274` | `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="指定されたユーザーが存在しません")` |
| `backend/app/routers/teams.py:285` | `detail="このユーザーは既にチームメンバーです",` |
| `backend/app/routers/teams.py:328` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="メンバーが見つかりません")` |
| `backend/app/routers/discord_channel_invite.py:90` | `raise HTTPException(status_code=404, detail="リードが見つかりません")` |
| `backend/app/routers/discord_channel_invite.py:96` | `detail="チケットチャンネルが未作成です。先にチケットチャンネルを作成してください。",` |
| `backend/app/routers/discord_channel_invite.py:111` | `raise HTTPException(status_code=422, detail="Discord チケット設定が未設定です。")` |
| `backend/app/routers/discord_channel_invite.py:121` | `detail=f"estimated_scale '{estimated_scale}' に対応する専用チャンネルがありません（Small/Large のみ対応）。",` |
| `backend/app/routers/discord_channel_invite.py:128` | `detail=f"{scale_label}向けチャンネルIDが設定されていません。Discord 設定ページで設定してください。",` |
| `backend/app/routers/discord_channel_invite.py:136` | `detail="Bot トークンが設定されていません。",` |
| `backend/app/routers/discord_channel_invite.py:159` | `detail=f"Discord API エラー ({resp.status_code}): チャンネルIDとBot権限を確認してください。",` |
| `backend/app/routers/super_admin_aliases.py:134` | `detail="重複または FK 違反",` |
| `backend/app/routers/super_admin_aliases.py:154` | `raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")` |
| `backend/app/routers/super_admin_aliases.py:168` | `raise HTTPException(status_code=409, detail="重複または FK 違反")` |
| `backend/app/routers/super_admin_aliases.py:171` | `raise HTTPException(status_code=404, detail="aliasが見つかりません")` |
| `backend/app/routers/super_admin_aliases.py:187` | `raise HTTPException(status_code=404, detail="aliasが見つかりません")` |
| `backend/app/routers/super_admin_aliases.py:236` | `raise HTTPException(status_code=400, detail="CSVが空、またはヘッダーがありません")` |
| `backend/app/routers/super_admin_aliases.py:239` | `raise HTTPException(status_code=400, detail=f"必須列が欠落: {sorted(missing)}")` |
| `backend/app/routers/webhook.py:274` | `raise HTTPException(status_code=500, detail="Webhook署名検証が設定されていません")` |
| `backend/app/routers/realtime_events.py:78` | `detail="接続数が上限に達しています",` |
| `backend/app/routers/super_admin_unit_ignore_phrases.py:75` | `detail="重複または制約違反",` |
| `backend/app/routers/super_admin_unit_ignore_phrases.py:96` | `raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")` |
| `backend/app/routers/super_admin_unit_ignore_phrases.py:110` | `raise HTTPException(status_code=409, detail="制約違反")` |
| `backend/app/routers/notices.py:98` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知らせが見つかりません")` |
| `backend/app/routers/notices.py:107` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知らせが見つかりません")` |
| `backend/app/routers/purchase_orders.py:84` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="指定された仕入先が見つかりません")` |
| `backend/app/routers/purchase_orders.py:88` | `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="選択された仕入先は無効化されています")` |
| `backend/app/routers/purchase_orders.py:155` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="仕入注文が見つかりません")` |
| `backend/app/routers/purchase_orders.py:197` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="指定された受注明細が見つかりません")` |
| `backend/app/routers/purchase_orders.py:234` | `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="draft状態の注文のみ発注できます")` |
| `backend/app/routers/purchase_orders.py:259` | `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ordered状態の注文のみ入荷処理できます")` |
| `backend/app/routers/purchase_orders.py:295` | `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="received状態の注文のみ入荷取消できます")` |
| `backend/app/routers/purchase_orders.py:326` | `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="draft/ordered状態の注文のみキャンセルできます")` |
| `backend/app/routers/purchase_orders.py:410` | `detail="送信先メールアドレスがマスタに未登録です",` |
| `backend/app/routers/purchase_orders.py:519` | `detail="error 状態の注文のみ再送できます",` |
| `backend/app/routers/products.py:338` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商品が見つかりません")` |
| `backend/app/routers/products.py:460` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商品が見つかりません")` |
| `backend/app/routers/products.py:466` | `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="更新するフィールドを指定してください")` |
| `backend/app/routers/products.py:663` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商品が見つかりません")` |
| `backend/app/routers/products.py:762` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商品が見つかりません")` |
| `backend/app/routers/auth.py:95` | `detail="ユーザー登録はsuper adminのみ可能です",` |
| `backend/app/routers/auth.py:109` | `detail="テナントコードが無効です",` |
| `backend/app/routers/auth.py:120` | `detail="このメールアドレスは既に登録されています",` |
| `backend/app/routers/auth.py:199` | `detail="ログアウト処理に失敗しました。しばらく待ってから再試行してください。",` |
| `backend/app/routers/erp.py:156` | `raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="ERP エクスポート失敗")` |
| `backend/app/routers/discord_oauth.py:184` | `detail="権限が不足しています: tenant.profile.edit",` |
| `backend/app/routers/discord_oauth.py:190` | `detail="一時的に Discord 連携を開始できません（設定不足）",` |
| `backend/app/routers/discord_oauth.py:202` | `detail="一時的に Discord 連携を開始できません（Redis 接続失敗）",` |
| `backend/app/routers/close_reasons.py:51` | `detail="type は 'won' または 'lost' のみ有効です",` |
| `backend/app/routers/close_reasons.py:118` | `detail="指定された理由が見つかりません",` |
| `backend/app/routers/close_reasons.py:125` | `detail="更新するフィールドを指定してください",` |
| `backend/app/routers/tenant_policy.py:75` | `detail="tenant_settings が初期化されていません (migration 070 適用要)",` |
| `backend/app/routers/tenant_policy.py:111` | `detail="tenant_settings が初期化されていません (migration 070 適用要)",` |
| `backend/app/routers/tenant_policy.py:162` | `detail="tenant_settings の読み込みに失敗しました",` |
| `backend/app/routers/units.py:164` | `raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")` |
| `backend/app/routers/units.py:177` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="単位が見つかりません")` |
| `backend/app/routers/units.py:202` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="単位が見つかりません")` |
| `backend/app/routers/discord_role_resync.py:62` | `raise HTTPException(status_code=404, detail="リードが見つかりません")` |
| `backend/app/routers/discord_role_resync.py:68` | `raise HTTPException(status_code=409, detail="discord_user_id が設定されていません。")` |
| `backend/app/routers/discord_role_resync.py:70` | `raise HTTPException(status_code=409, detail="estimated_scale が設定されていません。")` |
| `backend/app/routers/payment_fee_settings.py:115` | `detail="重複または制約違反",` |
| `backend/app/routers/payment_fee_settings.py:138` | `raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")` |
| `backend/app/routers/payment_fee_settings.py:153` | `raise HTTPException(status_code=409, detail="制約違反")` |
| `backend/app/routers/payment_fee_settings.py:156` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="決済手数料設定が見つかりません")` |
| `backend/app/routers/payment_fee_settings.py:181` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="決済手数料設定が見つかりません")` |
| `backend/app/routers/discord_auto_setup.py:108` | `detail="Discord サーバーが未接続です。先に Bot を招待してください。",` |
| `backend/app/routers/discord_auto_setup.py:117` | `detail="Bot トークンが設定されていません。環境変数 DISCORD_BOT_TOKEN を確認してください。",` |
| `backend/app/routers/discord_auto_setup.py:166` | `raise HTTPException(status_code=502, detail=f"Discord API 接続エラー: {exc}") from exc` |
| `backend/app/routers/conv_logs.py:216` | `detail=f"チャネル '{body.channel_type}' はこのテナントで有効ではありません",` |
| `backend/app/routers/conv_logs.py:221` | `detail=f"チャネル '{body.channel_type}' は自動連携チャネルのため手動入力は禁止です（SA-02-design §4）",` |
| `backend/app/routers/conv_logs.py:369` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会話ログが見つかりません")` |
| `backend/app/routers/conv_logs.py:371` | `raise HTTPException(status_code=status.HTTP_410_GONE, detail="削除済みの会話ログは編集できません")` |
| `backend/app/routers/conv_logs.py:432` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会話ログが見つかりません")` |
| `backend/app/routers/conv_logs.py:434` | `raise HTTPException(status_code=status.HTTP_410_GONE, detail="すでに削除済みです")` |
| `backend/app/routers/conv_logs.py:481` | `detail="同じ名前の連絡手段が既にあります",` |
| `backend/app/routers/conv_logs.py:521` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="チャネルが見つかりません")` |
| `backend/app/routers/conv_logs.py:525` | `detail="自動連携チャネルは隠せません",` |
| `backend/app/routers/conv_logs.py:561` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="チャネルが見つかりません")` |
| `backend/app/routers/conv_logs.py:565` | `detail="自動連携チャネルは削除できません（SA-02-design §4）",` |
| `backend/app/routers/conv_logs.py:570` | `detail="共用の連絡手段は消せません。隠す切り替えを使ってください",` |
| `backend/app/routers/suppliers.py:256` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="仕入先が見つかりません")` |
| `backend/app/routers/suppliers.py:299` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="仕入先が見つかりません")` |
| `backend/app/routers/suppliers.py:303` | `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="更新するフィールドを指定してください")` |
| `backend/app/routers/suppliers.py:330` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="仕入先が見つかりません")` |
| `backend/app/routers/quotes.py:140` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="見積もりが見つかりません")` |
| `backend/app/routers/quotes.py:165` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="指定された会社が見つかりません")` |
| `backend/app/routers/quotes.py:175` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="指定された担当者が見つかりません")` |
| `backend/app/routers/quotes.py:179` | `detail="指定された担当者は指定会社に所属していません",` |
| `backend/app/routers/quotes.py:184` | `raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="見積もりには lead_id が必要です")` |
| `backend/app/routers/quotes.py:280` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="見積もりが見つかりません")` |
| `backend/app/routers/quotes.py:282` | `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"ステータス「{old_row['status']}」の見積もりは編集できません")` |
| `backend/app/routers/quotes.py:287` | `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="更新するフィールドを指定してください")` |
| `backend/app/routers/quotes.py:332` | `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="draft状態の見積もりのみ送付できます")` |
| `backend/app/routers/quotes.py:360` | `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="sent状態の見積もりのみ承認できます")` |
| `backend/app/routers/quotes.py:389` | `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="sent状態の見積もりのみ却下できます")` |
| `backend/app/routers/quotes.py:414` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="見積もりが見つかりません")` |
| `backend/app/routers/quotes.py:416` | `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="draft状態の見積もりのみ削除できます")` |
| `backend/app/routers/meta_inbox.py:86` | `detail="META_OAUTH_REDIRECT_URI が未設定です。サーバー設定を確認してください",` |
| `backend/app/routers/meta_inbox.py:96` | `detail="META_APP_ID が未設定です。サーバー設定を確認してください",` |
| `backend/app/routers/meta_inbox.py:297` | `detail="一時的に OAuth 接続を開始できません（Redis 接続失敗）",` |
| `backend/app/routers/meta_inbox.py:339` | `detail="一時的に OAuth state を検証できません（Redis 接続失敗）",` |
| `backend/app/routers/meta_inbox.py:344` | `detail="state が無効です（期限切れ・改ざん・既消費の可能性）",` |
| `backend/app/routers/meta_inbox.py:352` | `detail="state のテナント情報が一致しません",` |
| `backend/app/routers/meta_inbox.py:370` | `detail=f"Meta Graph API エラー: {e.error_type or 'unknown'}",` |
| `backend/app/routers/meta_inbox.py:375` | `detail="Meta Graph API がタイムアウトしました。再度お試しください",` |
| `backend/app/routers/meta_inbox.py:381` | `detail="Meta Graph API への接続に失敗しました",` |
| `backend/app/routers/meta_inbox.py:417` | `detail="Page 一覧の取得に失敗しました",` |
| `backend/app/routers/meta_inbox.py:572` | `raise HTTPException(status_code=400, detail="page_id が不正です")` |
| `backend/app/routers/meta_inbox.py:588` | `detail="該当する接続済 Page が見つかりません",` |
| `backend/app/routers/meta_inbox.py:611` | `detail="保存トークンの復号に失敗しました（鍵不一致の可能性）",` |
| `backend/app/routers/meta_inbox.py:984` | `detail="会話一覧の取得に失敗しました",` |
| `backend/app/routers/meta_inbox.py:1066` | `detail="SSE接続数が上限に達しています",` |
| `backend/app/routers/super_admin_llm_budget.py:132` | `detail=f"tenant_id={tenant_id} の LLM 予算行が存在しません",` |
| `backend/app/routers/super_admin_llm_budget.py:196` | `detail="upsert 後の行取得に失敗しました",` |
| `backend/app/routers/super_admin_weight_classes.py:86` | `detail="重複または制約違反",` |
| `backend/app/routers/super_admin_weight_classes.py:106` | `raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")` |
| `backend/app/routers/super_admin_weight_classes.py:120` | `raise HTTPException(status_code=409, detail="制約違反")` |
| `backend/app/routers/super_admin_weight_classes.py:123` | `raise HTTPException(status_code=404, detail="重量クラスが見つかりません")` |
| `backend/app/routers/super_admin_weight_classes.py:146` | `detail="この重量クラスは商品（products）で使用中のため削除できません",` |
| `backend/app/routers/super_admin_weight_classes.py:156` | `raise HTTPException(status_code=404, detail="重量クラスが見つかりません")` |
| `backend/app/routers/discord_ticket_config.py:248` | `raise HTTPException(status_code=422, detail="チケット設定が未完了です。先にボタンチャンネルIDを設定してください。")` |
| `backend/app/routers/discord_ticket_config.py:258` | `raise HTTPException(status_code=503, detail="Bot トークンが設定されていません。環境変数 DISCORD_BOT_TOKEN を確認してください。")` |
| `backend/app/routers/discord_ticket_config.py:287` | `detail=f"Discord API エラー ({resp.status_code}): チャンネルIDとBot権限を確認してください。",` |
| `backend/app/routers/contact_channel_links.py:138` | `raise HTTPException(status_code=404, detail="担当者が見つかりません")` |
| `backend/app/routers/translation.py:153` | `detail="今月の翻訳上限に達しました",` |
| `backend/app/routers/translation.py:158` | `detail=f"翻訳サービス設定エラー: {exc}",` |
| `backend/app/routers/translation.py:163` | `detail=f"翻訳失敗: {exc}",` |
| `backend/app/routers/translation.py:208` | `detail="下訳が見つからないか、既に確認済みです",` |
| `backend/app/routers/translation.py:326` | `detail="グロッサリエントリが見つかりません（テナント所有のエントリのみ編集可）",` |
| `backend/app/routers/translation.py:359` | `detail="グロッサリエントリが見つかりません（テナント所有のエントリのみ削除可）",` |
| `backend/app/routers/tcg_analysis_review.py:157` | `raise HTTPException(status_code=422, detail="extraction_item_ids は50件まで")` |
| `backend/app/routers/buyback_prices.py:695` | `detail="再マッチング中にエラーが発生しました",` |
| `backend/app/routers/buyback_prices.py:776` | `detail="指定の商品が見つかりません",` |
| `backend/app/routers/buyback_prices.py:844` | `detail="指定の商品が見つかりません",` |
| `backend/app/routers/buyback_prices.py:858` | `detail=f"product_id={body.product_id} が public.products に存在しません",` |
| `backend/app/routers/order_commissions.py:107` | `detail="注文が見つかりません",` |
| `backend/app/routers/order_commissions.py:250` | `detail="指定の staff_id がこのテナントに存在しません",` |
| `backend/app/routers/order_commissions.py:331` | `detail="割当の保存に失敗しました",` |
| `backend/app/routers/order_commissions.py:355` | `detail=f"role は {sorted(ALL_ROLES)} のいずれかを指定してください",` |
| `backend/app/routers/order_commissions.py:362` | `detail="該当ロールの報酬レコードが見つかりません",` |
| `backend/app/routers/shipping.py:123` | `raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="同じ国・キャリアのゾーンが既に存在します")` |
| `backend/app/routers/shipping.py:151` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ゾーンが見つかりません")` |
| `backend/app/routers/shipping.py:253` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="料金が見つかりません")` |
| `backend/app/routers/shipping.py:413` | `detail="carrier='fedex' 指定時は origin_country_code が必須です",` |
| `backend/app/routers/shipping.py:485` | `detail="FedEx 認証情報またはアカウント番号が未設定です",` |
| `backend/app/routers/shipping.py:590` | `detail="FedEx 認証情報またはアカウント番号が未設定です",` |
| `backend/app/routers/shipping.py:710` | `detail="FedEx Sandbox 認証情報またはアカウント番号が未設定です。先にSandbox認証情報を登録してください。",` |
| `backend/app/routers/shipping.py:734` | `detail=f"{service_name}({abbr}) ラベル発行失敗: {e}",` |
| `backend/app/routers/shipping.py:774` | `detail="FedEx 本番 API Key が未登録です。先に本番タブで認証情報を登録してください。",` |
| `backend/app/routers/shipping.py:871` | `detail="FedEx ETD はまだ有効化されていません",` |
| `backend/app/routers/shipping.py:876` | `detail=f"image_type={image_type!r} は無効です。LETTERHEAD または SIGNATURE を指定してください",` |
| `backend/app/routers/shipping.py:881` | `detail=f"environment={environment!r} は無効です。sandbox または production を指定してください",` |
| `backend/app/routers/shipping.py:888` | `detail=f"FedEx {environment} 認証情報が未設定です",` |
| `backend/app/routers/order_shipping_details.py:84` | `detail="注文が見つかりません",` |
| `backend/app/routers/order_shipping_details.py:151` | `detail="この受注の発送情報は既に登録されています",` |
| `backend/app/routers/order_shipping_details.py:205` | `detail="発送情報が見つかりません",` |
| `backend/app/routers/order_shipping_details.py:227` | `detail="発送情報が見つかりません",` |
| `backend/app/routers/order_shipping_details.py:236` | `detail="更新するフィールドを指定してください",` |
| `backend/app/routers/order_shipping_details.py:284` | `detail="発送情報が見つかりません",` |
| `backend/app/routers/order_shipping_details.py:367` | `detail="注文が見つかりません",` |
| `backend/app/routers/order_shipping_details.py:420` | `detail=f"order_ids に整数以外が含まれています: '{tok}'",` |
| `backend/app/routers/order_shipping_details.py:425` | `detail="order_ids は正の整数を指定してください",` |
| `backend/app/routers/order_shipping_details.py:435` | `detail="order_ids を 1 件以上指定してください",` |
| `backend/app/routers/order_shipping_details.py:440` | `detail="order_ids は最大 1000 件までです",` |
| `backend/app/routers/order_shipping_details.py:457` | `detail="指定された注文が 1 件も見つかりません",` |
| `backend/app/routers/super_admin_conditions.py:187` | `detail="状態コードは既に存在します",` |
| `backend/app/routers/super_admin_conditions.py:196` | `detail=f"search_kw が無効な正規表現です: {exc}",` |
| `backend/app/routers/super_admin_conditions.py:227` | `detail="制約違反",` |
| `backend/app/routers/super_admin_conditions.py:247` | `raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")` |
| `backend/app/routers/super_admin_conditions.py:262` | `raise HTTPException(status_code=409, detail="制約違反")` |
| `backend/app/routers/super_admin_conditions.py:265` | `raise HTTPException(status_code=404, detail="状態が見つかりません")` |
| `backend/app/routers/super_admin_conditions.py:289` | `raise HTTPException(status_code=404, detail="状態が見つかりません")` |
| `backend/app/routers/super_admin_conditions.py:470` | `detail="URL の condition_id と body の condition_id が一致しません",` |
| `backend/app/routers/super_admin_conditions.py:487` | `detail="重複または FK 違反",` |
| `backend/app/routers/super_admin_conditions.py:507` | `raise HTTPException(status_code=404, detail="別名が見つかりません")` |
| `backend/app/routers/product_masters.py:98` | `detail="同じ区分・表示名のマスタが既に存在します",` |
| `backend/app/routers/product_masters.py:118` | `raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")` |
| `backend/app/routers/product_masters.py:134` | `detail="同じ区分・表示名のマスタが既に存在します",` |
| `backend/app/routers/product_masters.py:138` | `raise HTTPException(status_code=404, detail="マスタが見つかりません")` |
| `backend/app/routers/product_masters.py:157` | `raise HTTPException(status_code=404, detail="マスタが見つかりません")` |
| `backend/app/routers/leads.py:169` | `detail="country は ISO 3166-1 alpha-2 または国名で指定してください",` |
| `backend/app/routers/leads.py:181` | `detail="指定された country は国台帳に存在しません",` |
| `backend/app/routers/leads.py:210` | `detail="channel_type はチャネル台帳に存在する値を指定してください",` |
| `backend/app/routers/leads.py:386` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="リードが見つかりません")` |
| `backend/app/routers/leads.py:505` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="リードが見つかりません")` |
| `backend/app/routers/leads.py:516` | `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="更新するフィールドを指定してください")` |
| `backend/app/routers/leads.py:541` | `detail="失注遷移時は close_reasons（主因1件必須）が必要です",` |
| `backend/app/routers/leads.py:547` | `detail=f"主因（is_primary: true）はちょうど1件必要です（{primary_count}件指定）",` |
| `backend/app/routers/leads.py:552` | `detail="失注遷移時は close_reason_memo が必要です",` |
| `backend/app/routers/leads.py:617` | `detail=f"close_reason id={reason['reason_id']} が見つかりません",` |
| `backend/app/routers/leads.py:637` | `detail="option_id が重複しています。同一の選択肢を複数回指定することはできません",` |
| `backend/app/routers/leads.py:657` | `detail=f"無効または他テナントの option_id が含まれています: {sorted(invalid_ids)}",` |
| `backend/app/routers/leads.py:672` | `detail="other_text は 'その他' オプション選択時のみ有効です",` |
| `backend/app/routers/leads.py:777` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="リードが見つかりません")` |
| `backend/app/routers/leads.py:820` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="リードが見つかりません")` |
| `backend/app/routers/leads.py:823` | `raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="このリードは既に商談中です")` |
| `backend/app/routers/leads.py:845` | `detail="このリードは既に商談中です（並行リクエスト）",` |
| `backend/app/routers/leads.py:995` | `detail="リードが見つかりません",` |
| `backend/app/routers/leads.py:1199` | `detail="リードが見つかりません",` |
| `backend/app/routers/leads.py:1298` | `detail="リードが見つかりません",` |
| `backend/app/routers/leads.py:1405` | `detail="リードが見つかりません",` |
| `backend/app/routers/leads.py:1421` | `detail="メッセージが見つかりません",` |
| `backend/app/routers/leads.py:1428` | `detail="メッセージ本文が空です",` |
| `backend/app/routers/leads.py:1560` | `detail="リードが見つかりません",` |
| `backend/app/routers/leads.py:1576` | `detail="メッセージが見つかりません",` |
| `backend/app/routers/leads.py:1591` | `detail="Discord Bot Token が設定されていません",` |
| `backend/app/routers/leads.py:1679` | `detail="Meta 接続が見つかりません（Channels 設定で接続してください）",` |
| `backend/app/routers/leads.py:1688` | `detail="保存トークンの復号に失敗しました",` |
| `backend/app/routers/leads.py:1802` | `detail="リードが見つかりません",` |
| `backend/app/routers/leads.py:1810` | `detail="本文が空です",` |
| `backend/app/routers/leads.py:1826` | `raise HTTPException(status_code=400, detail="翻訳下書きが見つかりません")` |
| `backend/app/routers/leads.py:1828` | `raise HTTPException(status_code=400, detail="翻訳が未確認です")` |
| `backend/app/routers/leads.py:1830` | `raise HTTPException(status_code=400, detail="別リードの翻訳下書きです")` |
| `backend/app/routers/leads.py:1864` | `detail="このリードはメッセージング連携されていないため送信できません",` |
| `backend/app/routers/leads.py:1897` | `detail="送信先 ID が解決できません（受信履歴がありません）",` |
| `backend/app/routers/leads.py:1930` | `detail="送信に使う Meta 接続が見つかりません（Channels 設定で接続してください）",` |
| `backend/app/routers/leads.py:1944` | `detail="保存トークンの復号に失敗しました（鍵不一致の可能性）",` |
| `backend/app/routers/leads.py:1964` | `detail="Instagram Business Account が紐づいていません",` |
| `backend/app/routers/leads.py:2006` | `detail="Meta Send API がタイムアウトしました",` |
| `backend/app/routers/leads.py:2058` | `detail="Meta Send API への接続に失敗しました",` |
| `backend/app/routers/leads.py:2428` | `detail=f"サポートされていない画像形式です（{content_type}）。JPEG/PNG/GIF/WebP を使用してください",` |
| `backend/app/routers/leads.py:2434` | `detail=f"ファイルサイズが上限（8MB）を超えています（{len(file_bytes) // 1024 // 1024}MB）",` |
| `backend/app/routers/leads.py:2437` | `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="空のファイルです")` |
| `backend/app/routers/leads.py:2451` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="リードが見つかりません")` |
| `backend/app/routers/leads.py:2486` | `detail="Discord Bot Token が設定されていません",` |
| `backend/app/routers/leads.py:2500` | `detail="Discord チャンネルが設定されていません",` |
| `backend/app/routers/leads.py:2685` | `detail="このリードはメッセージング連携されていないため送信できません",` |
| `backend/app/routers/leads.py:2703` | `detail="送信先 ID が解決できません",` |
| `backend/app/routers/leads.py:2732` | `detail="送信に使う Meta 接続が見つかりません（Channels 設定で接続してください）",` |
| `backend/app/routers/leads.py:2746` | `detail="保存トークンの復号に失敗しました",` |
| `backend/app/routers/leads.py:2772` | `raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="画像アップロードがタイムアウトしました")` |
| `backend/app/routers/leads.py:2775` | `raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="画像アップロードへの接続に失敗しました")` |
| `backend/app/routers/leads.py:2792` | `detail="Instagram Business Account が紐づいていません",` |
| `backend/app/routers/leads.py:2806` | `raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Meta Send API がタイムアウトしました")` |
| `backend/app/routers/leads.py:2820` | `raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Meta Send API への接続に失敗しました")` |
| `backend/app/routers/leads.py:2943` | `detail="SSE接続数が上限に達しています",` |
| `backend/app/routers/leads.py:3068` | `detail="master_id と loser_id が同じです。自己マージはできません。",` |
| `backend/app/routers/leads.py:3089` | `detail=f"master リード (id={master_id}) が見つかりません",` |
| `backend/app/routers/leads.py:3094` | `detail=f"loser リード (id={loser_id}) が見つかりません",` |
| `backend/app/routers/badges.py:105` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="バッジが見つかりません")` |
| `backend/app/routers/badges.py:118` | `raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="既にこのバッジを獲得しています")` |
| `backend/app/routers/archives.py:84` | `detail=f"アーカイブ対象外のテーブルです。対象: {', '.join(sorted(ARCHIVABLE_TABLES))}")` |
| `backend/app/routers/archives.py:93` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="対象レコードが見つかりません")` |
| `backend/app/routers/archives.py:135` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="アーカイブが見つかりません")` |
| `backend/app/routers/archives.py:137` | `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="既に復元済みです")` |
| `backend/app/routers/super_admin_product_lines.py:86` | `detail="重複または制約違反",` |
| `backend/app/routers/super_admin_product_lines.py:106` | `raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")` |
| `backend/app/routers/super_admin_product_lines.py:120` | `raise HTTPException(status_code=409, detail="制約違反")` |
| `backend/app/routers/super_admin_product_lines.py:123` | `raise HTTPException(status_code=404, detail="小分類が見つかりません")` |
| `backend/app/routers/super_admin_product_lines.py:146` | `detail="この小分類はフォーマット（product_formats）で使用中のため削除できません",` |
| `backend/app/routers/super_admin_product_lines.py:156` | `detail="この小分類は商品（products）で使用中のため削除できません",` |
| `backend/app/routers/super_admin_product_lines.py:166` | `raise HTTPException(status_code=404, detail="小分類が見つかりません")` |
| `backend/app/routers/staff.py:207` | `detail="現在のユーザに紐づく staff レコードが見つかりません",` |
| `backend/app/routers/staff.py:224` | `raise HTTPException(status_code=400, detail="locale は 'ja' または 'en' のみ有効です")` |
| `backend/app/routers/staff.py:247` | `raise HTTPException(status_code=400, detail="theme は 'light' または 'dark' のみ有効です")` |
| `backend/app/routers/staff.py:292` | `detail="現在のユーザに紐づく staff レコードが見つかりません",` |
| `backend/app/routers/staff.py:301` | `raise HTTPException(status_code=400, detail="更新するフィールドを少なくとも1つ指定してください")` |
| `backend/app/routers/staff.py:353` | `detail="現在のユーザに紐づく staff レコードが見つかりません",` |
| `backend/app/routers/staff.py:497` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="スタッフが見つかりません")` |
| `backend/app/routers/staff.py:510` | `detail="user_id は指定できません",` |
| `backend/app/routers/staff.py:535` | `detail="スタッフの登録に失敗しました（同じ値がすでに登録されています: スタッフコード・Discord ID・メールアドレスのいずれか）",` |
| `backend/app/routers/staff.py:561` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="スタッフが見つかりません")` |
| `backend/app/routers/staff.py:566` | `detail="user_id は変更できません")` |
| `backend/app/routers/staff.py:569` | `detail="メールアドレスはここでは変更できません")` |
| `backend/app/routers/staff.py:572` | `detail="更新するフィールドを少なくとも1つ指定してください")` |
| `backend/app/routers/staff.py:646` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="スタッフが見つかりません")` |
| `backend/app/routers/staff.py:671` | `detail="この担当者は他のデータから参照されているため削除できません",` |
| `backend/app/routers/google_calendar.py:177` | `detail="Google カレンダーをつないだ本人だけが使えます",` |
| `backend/app/routers/google_calendar.py:353` | `detail="更新フィールドが指定されていません",` |
| `backend/app/routers/contacts.py:330` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会社が見つかりません")` |
| `backend/app/routers/contacts.py:402` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="担当者が見つかりません")` |
| `backend/app/routers/contacts.py:425` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="指定の会社が見つかりません")` |
| `backend/app/routers/contacts.py:512` | `detail="担当者の登録に失敗しました（contact_code 重複または制約違反の可能性）",` |
| `backend/app/routers/contacts.py:536` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="担当者が見つかりません")` |
| `backend/app/routers/contacts.py:545` | `detail="更新するフィールドを少なくとも1つ指定してください",` |
| `backend/app/routers/contacts.py:626` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="担当者が見つかりません")` |
| `backend/app/routers/contacts.py:651` | `detail="この担当者には関連する商談・注文・見積・請求書があるため削除できません。先に関連データを削除してください。",` |
| `backend/app/routers/contacts.py:727` | `detail="master_id と loser_id が同じです。自己マージはできません。",` |
| `backend/app/routers/contacts.py:757` | `detail=f"master 担当者 (id={master_id}) が見つかりません",` |
| `backend/app/routers/contacts.py:762` | `detail=f"loser 担当者 (id={loser_id}) が見つかりません",` |
| `backend/app/routers/conditions.py:201` | `status_code=status.HTTP_404_NOT_FOUND, detail="状態が見つかりません"` |
| `backend/app/routers/conditions.py:228` | `detail="この状態コードは既に存在します",` |
| `backend/app/routers/conditions.py:289` | `status_code=status.HTTP_404_NOT_FOUND, detail="状態が見つかりません"` |
| `backend/app/routers/conditions.py:295` | `status_code=status.HTTP_400_BAD_REQUEST, detail="更新するフィールドを指定してください"` |
| `backend/app/routers/conditions.py:342` | `status_code=status.HTTP_404_NOT_FOUND, detail="状態が見つかりません"` |
| `backend/app/routers/conditions.py:544` | `raise HTTPException(status_code=404, detail="状態が見つかりません")` |
| `backend/app/routers/conditions.py:571` | `detail="URL の condition_id と body の condition_id が一致しません",` |
| `backend/app/routers/conditions.py:579` | `raise HTTPException(status_code=404, detail="状態が見つかりません")` |
| `backend/app/routers/conditions.py:593` | `raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="重複または FK 違反")` |
| `backend/app/routers/conditions.py:621` | `raise HTTPException(status_code=404, detail="別名が見つかりません")` |
| `backend/app/routers/super_admin_note_master.py:185` | `detail="重複または制約違反",` |
| `backend/app/routers/super_admin_note_master.py:205` | `raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")` |
| `backend/app/routers/super_admin_note_master.py:219` | `raise HTTPException(status_code=409, detail="制約違反")` |
| `backend/app/routers/super_admin_note_master.py:222` | `raise HTTPException(status_code=404, detail="備考マスタが見つかりません")` |
| `backend/app/routers/super_admin_note_master.py:244` | `raise HTTPException(status_code=404, detail="備考マスタが見つかりません")` |
| `backend/app/routers/invoices.py:230` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="請求書が見つかりません")` |
| `backend/app/routers/invoices.py:256` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="見積もりが見つかりません")` |
| `backend/app/routers/invoices.py:258` | `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="承認済みの見積もりのみ請求書に変換できます")` |
| `backend/app/routers/invoices.py:353` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="指定された担当者が見つかりません")` |
| `backend/app/routers/invoices.py:357` | `detail="指定された担当者は指定会社に所属していません",` |
| `backend/app/routers/invoices.py:462` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="請求書が見つかりません")` |
| `backend/app/routers/invoices.py:464` | `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="draft状態の請求書のみ編集できます")` |
| `backend/app/routers/invoices.py:469` | `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="更新するフィールドを指定してください")` |
| `backend/app/routers/invoices.py:506` | `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="draft状態の請求書のみ発行できます")` |
| `backend/app/routers/invoices.py:533` | `raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="入金日に未来の日付は指定できません")` |
| `backend/app/routers/invoices.py:541` | `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="issued/overdue状態の請求書のみ入金登録できます")` |
| `backend/app/routers/invoices.py:574` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="請求書が見つかりません")` |
| `backend/app/routers/invoices.py:576` | `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="既に無効化されています")` |
| `backend/app/routers/invoices.py:578` | `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="入金済みの請求書は無効化できません")` |
| `backend/app/routers/invoices.py:617` | `detail="PayPal が未接続です（管理センター > API連携 > PayPal で認証情報を登録してください）",` |
| `backend/app/routers/invoices.py:644` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="請求書が見つかりません")` |
| `backend/app/routers/invoices.py:646` | `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="発行済み（issued/overdue）の請求書のみリンク発行できます")` |
| `backend/app/routers/invoices.py:648` | `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="請求金額が未確定です")` |
| `backend/app/routers/invoices.py:652` | `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="請求書に担当者（contact）が紐づいていません")` |
| `backend/app/routers/invoices.py:661` | `detail="送付先メールアドレスが未登録のため PayPal 請求書を発行できません",` |
| `backend/app/routers/invoices.py:694` | `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="発行済み（issued/overdue）の請求書のみリンク発行できます")` |
| `backend/app/routers/invoices.py:751` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="請求書が見つかりません")` |
| `backend/app/routers/invoices.py:753` | `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="先に PayPal 請求書を発行してください")` |
| `backend/app/routers/invoices.py:755` | `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="発行済み（issued/overdue）の請求書のみ入金確認できます")` |
| `backend/app/routers/invoices.py:788` | `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="発行済み（issued/overdue）の請求書のみ入金確認できます")` |
| `backend/app/routers/invoices.py:825` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="請求書が見つかりません")` |
| `backend/app/routers/invoices.py:921` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="請求書が見つかりません")` |
| `backend/app/routers/invoices.py:924` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="写しPDFはまだ生成されていません")` |
| `backend/app/routers/invoices.py:990` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="見積もりが見つかりません")` |
| `backend/app/routers/invoices.py:1064` | `detail=f"為替レートの取得に失敗しました: {currency}",` |
| `backend/app/routers/goals.py:122` | `detail="user_id か team_id のどちらか一方のみ指定してください",` |
| `backend/app/routers/goals.py:203` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="目標が見つかりません")` |
| `backend/app/routers/goals.py:243` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="目標が見つかりません")` |
| `backend/app/routers/inventory_aggregated.py:67` | `detail="在庫集計を参照する権限がありません (inventory.visibility.* または products.view が必要)。",` |
| `backend/app/routers/super_admin_product_formats.py:104` | `detail="重複または制約違反",` |
| `backend/app/routers/super_admin_product_formats.py:124` | `raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")` |
| `backend/app/routers/super_admin_product_formats.py:138` | `raise HTTPException(status_code=409, detail="制約違反")` |
| `backend/app/routers/super_admin_product_formats.py:141` | `raise HTTPException(status_code=404, detail="フォーマットが見つかりません")` |
| `backend/app/routers/super_admin_product_formats.py:164` | `raise HTTPException(status_code=404, detail="フォーマットが見つかりません")` |
| `backend/app/routers/super_admin_product_formats.py:200` | `raise HTTPException(status_code=409, detail="制約違反")` |
| `backend/app/routers/super_admin_product_formats.py:224` | `detail="このフォーマットは商品（products）で使用中のため削除できません",` |
| `backend/app/routers/super_admin_product_formats.py:234` | `raise HTTPException(status_code=404, detail="フォーマットが見つかりません")` |
| `backend/app/routers/super_admin_product_categories.py:155` | `detail="重複または制約違反",` |
| `backend/app/routers/super_admin_product_categories.py:301` | `raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")` |
| `backend/app/routers/super_admin_product_categories.py:315` | `raise HTTPException(status_code=409, detail="制約違反")` |
| `backend/app/routers/super_admin_product_categories.py:318` | `raise HTTPException(status_code=404, detail="商品カテゴリが見つかりません")` |
| `backend/app/routers/super_admin_product_categories.py:341` | `raise HTTPException(status_code=404, detail="商品カテゴリが見つかりません")` |
| `backend/app/routers/super_admin_units.py:166` | `detail="重複または制約違反",` |
| `backend/app/routers/super_admin_units.py:186` | `raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")` |
| `backend/app/routers/super_admin_units.py:200` | `raise HTTPException(status_code=409, detail="制約違反")` |
| `backend/app/routers/super_admin_units.py:203` | `raise HTTPException(status_code=404, detail="単位が見つかりません")` |
| `backend/app/routers/super_admin_units.py:226` | `raise HTTPException(status_code=404, detail="単位が見つかりません")` |
| `backend/app/routers/super_admin_units.py:265` | `detail="URL の unit_id と body の unit_id が一致しません",` |
| `backend/app/routers/super_admin_units.py:282` | `detail="重複または FK 違反",` |
| `backend/app/routers/super_admin_units.py:300` | `raise HTTPException(status_code=404, detail="別名が見つかりません")` |
| `backend/app/routers/discord_announcement.py:63` | `detail="Bot トークンが設定されていません。環境変数 DISCORD_BOT_TOKEN を確認してください。",` |
| `backend/app/routers/discord_announcement.py:83` | `detail=f"Discord API エラー ({resp.status_code}): チャンネルIDとBot権限を確認してください。",` |
| `backend/app/routers/super_admin_quantity_units.py:103` | `detail="重複または制約違反",` |
| `backend/app/routers/super_admin_quantity_units.py:123` | `raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")` |
| `backend/app/routers/super_admin_quantity_units.py:137` | `raise HTTPException(status_code=409, detail="制約違反")` |
| `backend/app/routers/super_admin_quantity_units.py:140` | `raise HTTPException(status_code=404, detail="数量単位が見つかりません")` |
| `backend/app/routers/super_admin_quantity_units.py:176` | `detail="この数量単位は商品（products）で使用中のため削除できません",` |
| `backend/app/routers/super_admin_quantity_units.py:186` | `raise HTTPException(status_code=404, detail="数量単位が見つかりません")` |
| `backend/app/routers/super_admin_quantity_units.py:206` | `raise HTTPException(status_code=404, detail="数量単位が見つかりません")` |
| `backend/app/routers/integrations.py:184` | `detail="連携の準備に失敗しました。サーバー設定をご確認ください（管理者へ連絡）。",` |
| `backend/app/routers/integrations.py:258` | `detail="フォルダの URL が正しくありません。フォルダの URL を貼り付けるか、空欄にしてください。",` |
| `backend/app/routers/integrations.py:271` | `detail="ドライブへの保存に失敗しました。フォルダの権限やアクセス権をご確認ください。",` |
| `backend/app/routers/integrations.py:325` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未対応のキャリアです")` |
| `backend/app/routers/integrations.py:333` | `detail="environment は 'production' または 'sandbox' のみ指定可能です",` |
| `backend/app/routers/integrations.py:384` | `detail="認証ID・シークレットの両方を入力してください。",` |
| `backend/app/routers/integrations.py:482` | `detail="認証情報が未設定です。先に保存してください。",` |
| `backend/app/routers/integrations.py:549` | `detail="Client ID・Client Secret の両方を入力してください。",` |
| `backend/app/routers/integrations.py:599` | `detail="認証情報が未設定です。先に保存してください。",` |
| `backend/app/routers/integrations.py:637` | `detail="PayPal が未接続です（先に認証情報を登録してください）",` |
| `backend/app/routers/integrations.py:642` | `detail="決済テストは sandbox 環境でのみ実行できます（本番では実課金になります）",` |
| `backend/app/routers/shifts.py:98` | `raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="同日同ユーザーのシフトが既に存在します")` |
| `backend/app/routers/shifts.py:114` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="シフトが見つかりません")` |
| `backend/app/routers/customer_priority.py:104` | `detail="リードが見つかりません")` |
| `backend/app/routers/customer_priority.py:251` | `detail="ラベルが見つかりません")` |
| `backend/app/routers/admin.py:46` | `detail="テナント作成はsuper adminのみ可能です",` |
| `backend/app/routers/admin.py:56` | `detail=f"テナントコード '{data.tenant_code}' は既に使用されています",` |
| `backend/app/routers/staff_join.py:165` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="招待が見つかりません")` |
| `backend/app/routers/staff_join.py:167` | `raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="受付中の招待だけ操作できます")` |
| `backend/app/routers/status_master.py:194` | `raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")` |
| `backend/app/routers/status_master.py:207` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ステータスが見つかりません")` |
| `backend/app/routers/status_master.py:232` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ステータスが見つかりません")` |
| `backend/app/routers/order_purchase_details.py:114` | `detail="注文が見つかりません",` |
| `backend/app/routers/order_purchase_details.py:155` | `detail="この受注の仕入情報は既に登録されています",` |
| `backend/app/routers/order_purchase_details.py:213` | `detail="仕入情報が見つかりません",` |
| `backend/app/routers/order_purchase_details.py:235` | `detail="仕入情報が見つかりません",` |
| `backend/app/routers/order_purchase_details.py:247` | `detail="更新するフィールドを指定してください",` |
| `backend/app/routers/order_purchase_details.py:295` | `detail="仕入情報が見つかりません",` |
| `backend/app/routers/order_purchase_details.py:337` | `detail="仕入情報が見つかりません",` |
| `backend/app/routers/order_purchase_details.py:403` | `detail=f"sort_by は {sorted(_SUPPLIER_SORTABLE_COLUMNS)} のいずれかを指定してください",` |
| `backend/app/routers/order_purchase_details.py:409` | `detail="sort_order は asc / desc を指定してください",` |
| `backend/app/routers/_utils.py:52` | `detail="データベースに接続できません。しばらく待ってから再試行してください。",` |
| `backend/app/routers/_utils.py:58` | `detail="データベースエラーが発生しました。",` |
| `backend/app/routers/own_inventory.py:105` | `detail="reserved_qty は physical_qty 以下にしてください",` |
| `backend/app/routers/own_inventory.py:167` | `detail="自社在庫が見つかりません",` |
| `backend/app/routers/own_inventory.py:195` | `detail="自社在庫が見つかりません",` |
| `backend/app/routers/own_inventory.py:201` | `detail="更新するフィールドを指定してください",` |
| `backend/app/routers/super_admin_product_kinds.py:86` | `detail="重複または制約違反",` |
| `backend/app/routers/super_admin_product_kinds.py:106` | `raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")` |
| `backend/app/routers/super_admin_product_kinds.py:120` | `raise HTTPException(status_code=409, detail="制約違反")` |
| `backend/app/routers/super_admin_product_kinds.py:123` | `raise HTTPException(status_code=404, detail="大分類が見つかりません")` |
| `backend/app/routers/super_admin_product_kinds.py:146` | `detail="この大分類は中分類（type_master）で使用中のため削除できません",` |
| `backend/app/routers/super_admin_product_kinds.py:156` | `raise HTTPException(status_code=404, detail="大分類が見つかりません")` |
| `backend/app/routers/viewer.py:557` | `raise HTTPException(status_code=422, detail=f"viewer_billing_invalid:{exc.args[0]}") from None  # 鍵は消費しない` |
| `backend/app/routers/bots.py:118` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Botが見つかりません")` |
| `backend/app/routers/bots.py:130` | `detail="指定の担当者はこのテナントに存在しません")` |
| `backend/app/routers/bots.py:188` | `detail="Botの登録に失敗しました（bot_code / discord_user_id 重複の可能性）",` |
| `backend/app/routers/bots.py:218` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Botが見つかりません")` |
| `backend/app/routers/bots.py:223` | `detail="更新するフィールドを少なくとも1つ指定してください")` |
| `backend/app/routers/bots.py:262` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Botが見つかりません")` |
| `backend/app/routers/bots.py:298` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Botが見つかりません")` |
| `backend/app/routers/bots.py:312` | `detail="この Bot は他のレコード（会話ログ・通知ログ等）から参照されているため削除できません",` |
| `backend/app/routers/tenant_admin_inventory_visibility.py:115` | `detail="URL の role_id と body の role_id が一致しません",` |
| `backend/app/routers/tenant_admin_inventory_visibility.py:126` | `detail="指定ロールが自テナント内に見つかりません",` |
| `backend/app/routers/tenant_admin_inventory_visibility.py:138` | `detail="システムロールの visibility は編集できません",` |
| `backend/app/routers/tenant_admin_inventory_visibility.py:146` | `detail=f"無効な visibility キー: {sorted(invalid_keys)}",` |
| `backend/app/routers/analytics.py:954` | `raise HTTPException(status_code=422, detail="month は YYYY-MM 形式で指定してください")` |
| `backend/app/routers/analytics.py:958` | `raise HTTPException(status_code=422, detail="month は YYYY-MM 形式で指定してください")` |
| `backend/app/routers/analytics.py:960` | `raise HTTPException(status_code=422, detail="month の月は 1〜12 の範囲で指定してください")` |
| `backend/app/routers/analytics.py:967` | `raise HTTPException(status_code=422, detail="scope は team または mine で指定してください")` |
| `backend/app/routers/analytics.py:1840` | `raise HTTPException(status_code=422, detail="scope は mine で指定してください")` |
| `backend/app/routers/analytics.py:1981` | `raise HTTPException(status_code=422, detail="type は won または lost で指定してください")` |
| `backend/app/routers/analytics.py:2108` | `raise HTTPException(status_code=422, detail="period は 1m / 3m / 6m / 12m で指定してください")` |
| `backend/app/routers/analytics.py:2561` | `detail="分析の設定が名簿にそろっていません",` |
| `backend/app/routers/discord_remove.py:54` | `raise HTTPException(status_code=404, detail="リードが見つかりません")` |
| `backend/app/routers/discord_remove.py:57` | `raise HTTPException(status_code=409, detail="このリードには Discord ユーザーID が設定されていません。")` |
| `backend/app/routers/discord_remove.py:68` | `raise HTTPException(status_code=422, detail="Discord Guild ID が設定されていません。")` |
| `backend/app/routers/discord_remove.py:96` | `raise HTTPException(status_code=409, detail="チケットチャンネルが設定されていません。")` |
| `backend/app/routers/discord_remove.py:100` | `raise HTTPException(status_code=503, detail="Bot トークンが設定されていません。")` |
| `backend/app/routers/discord_remove.py:115` | `detail=f"Discord API エラー ({resp.status_code}): チャンネルIDとBot権限を確認してください。",` |
| `backend/app/routers/discord_remove.py:156` | `raise HTTPException(status_code=503, detail="Bot トークンが設定されていません。")` |
| `backend/app/routers/discord_remove.py:171` | `detail=f"Discord API エラー ({resp.status_code}): Guild IDとBot権限を確認してください。",` |
| `backend/app/routers/discord_remove.py:206` | `raise HTTPException(status_code=503, detail="Bot トークンが設定されていません。")` |
| `backend/app/routers/discord_remove.py:222` | `detail=f"Discord API エラー ({resp.status_code}): Guild IDとBot権限を確認してください。",` |
| `backend/app/routers/reports.py:117` | `detail="キャッシュサービスが利用できません",` |
| `backend/app/routers/reports.py:127` | `detail="エクスポート結果が見つかりません（期限切れの可能性があります）",` |
| `backend/app/routers/super_admin_dex.py:53` | `raise HTTPException(status_code=404, detail="dex_kind は pokemon または trainer のみ")` |
| `backend/app/routers/super_admin_dex.py:117` | `raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="重複")` |
| `backend/app/routers/super_admin_dex.py:144` | `raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")` |
| `backend/app/routers/super_admin_dex.py:153` | `raise HTTPException(status_code=404, detail="図鑑エントリが見つかりません")` |
| `backend/app/routers/super_admin_dex.py:173` | `raise HTTPException(status_code=404, detail="図鑑エントリが見つかりません")` |
| `backend/app/routers/super_admin_dex.py:203` | `detail=f"PokeAPI からの取得に失敗しました: {exc}",` |
| `backend/app/routers/super_admin_link_templates.py:93` | `raise HTTPException(status_code=404, detail=f"テンプレートが見つかりません: {channel}")` |
| `backend/app/routers/super_admin_link_templates.py:135` | `detail="制約違反",` |
| `backend/app/routers/super_admin_link_templates.py:157` | `raise HTTPException(status_code=404, detail=f"テンプレートが見つかりません: {channel}")` |
| `backend/app/routers/super_admin_condition_defs.py:92` | `detail="重複または制約違反",` |
| `backend/app/routers/super_admin_condition_defs.py:112` | `raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")` |
| `backend/app/routers/super_admin_condition_defs.py:126` | `raise HTTPException(status_code=409, detail="制約違反")` |
| `backend/app/routers/super_admin_condition_defs.py:129` | `raise HTTPException(status_code=404, detail="コンディション定義が見つかりません")` |
| `backend/app/routers/super_admin_condition_defs.py:152` | `detail="このコンディション定義は販売単位リンク（unit_condition_links）で使用中のため削除できません",` |
| `backend/app/routers/super_admin_condition_defs.py:162` | `raise HTTPException(status_code=404, detail="コンディション定義が見つかりません")` |
| `backend/app/routers/super_admin_condition_defs.py:182` | `raise HTTPException(status_code=404, detail="コンディション定義が見つかりません")` |
| `backend/app/routers/companies.py:353` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会社が見つかりません")` |
| `backend/app/routers/companies.py:368` | `detail="指定された担当者が見つかりません",` |
| `backend/app/routers/companies.py:389` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="指定されたリードが見つかりません")` |
| `backend/app/routers/companies.py:467` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="指定された商談が見つかりません")` |
| `backend/app/routers/companies.py:470` | `detail="商談の出自リードと会社の出自リードが一致しません")` |
| `backend/app/routers/companies.py:506` | `detail="会社の登録に失敗しました（company_code 重複または制約違反の可能性）",` |
| `backend/app/routers/companies.py:530` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会社が見つかりません")` |
| `backend/app/routers/companies.py:539` | `detail="更新するフィールドを少なくとも1つ指定してください",` |
| `backend/app/routers/companies.py:642` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会社が見つかりません")` |
| `backend/app/routers/companies.py:667` | `detail="この会社には関連する商談・注文・見積・請求書・担当者があるため削除できません。先に関連データを削除してください。",` |
| `backend/app/routers/companies.py:732` | `detail="master_id と merge_id が同じです。同一会社をマージすることはできません。",` |
| `backend/app/routers/companies.py:756` | `detail=f"master 会社 (id={master_id}) が見つかりません",` |
| `backend/app/routers/companies.py:761` | `detail=f"merge 会社 (id={merge_id}) が見つかりません",` |
| `backend/app/routers/companies.py:768` | `detail="master 会社が archived 状態のため、マージ先として使用できません。先に master を active に戻してください。",` |
| `backend/app/routers/discord_own_server.py:133` | `detail="自社用サーバーが未登録です。先に Bot を招待してください。",` |
| `backend/app/routers/discord_own_server.py:141` | `detail="Bot トークンが設定されていません。環境変数 DISCORD_BOT_TOKEN を確認してください。",` |
| `backend/app/routers/discord_own_server.py:159` | `raise HTTPException(status_code=502, detail="Discord から読み取れませんでした。") from exc` |
| `backend/app/routers/discord_own_server.py:256` | `detail="自社用サーバーが未登録です。先に Bot を招待してください。",` |
| `backend/app/routers/discord_own_server.py:262` | `raise HTTPException(status_code=404, detail="設計図がまだありません。")` |
| `backend/app/routers/discord_own_server.py:267` | `raise HTTPException(status_code=422, detail="設計図の形が正しくありません。") from exc` |
| `backend/app/routers/discord_own_server.py:273` | `detail="Bot トークンが設定されていません。環境変数 DISCORD_BOT_TOKEN を確認してください。",` |
| `backend/app/routers/discord_own_server.py:307` | `raise HTTPException(status_code=502, detail="Discord から読み取れませんでした。") from exc` |
| `backend/app/routers/discord_own_server.py:441` | `detail="同時に反映しないための仕組みにつながりません。少し待ってからやり直してください。",` |
| `backend/app/routers/discord_own_server.py:445` | `raise HTTPException(status_code=409, detail="反映が動いています。終わってから確認し直してください。")` |
| `backend/app/routers/discord_own_server.py:453` | `detail="確認したあとにサーバーか設計図が変わりました。確認し直してください。",` |
| `backend/app/routers/super_admin_tcg.py:98` | `detail="重複",` |
| `backend/app/routers/super_admin_tcg.py:118` | `raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")` |
| `backend/app/routers/super_admin_tcg.py:130` | `raise HTTPException(status_code=404, detail="シリーズが見つかりません")` |
| `backend/app/routers/super_admin_tcg.py:146` | `raise HTTPException(status_code=404, detail="シリーズが見つかりません")` |
| `backend/app/routers/super_admin_tcg.py:199` | `detail="種別コードが重複しています",` |
| `backend/app/routers/super_admin_tcg.py:219` | `raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")` |
| `backend/app/routers/super_admin_tcg.py:231` | `raise HTTPException(status_code=404, detail="種別が見つかりません")` |
| `backend/app/routers/super_admin_tcg.py:250` | `raise HTTPException(status_code=404, detail="種別が見つかりません")` |
| `backend/app/routers/product_categories.py:307` | `raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")` |
| `backend/app/routers/product_categories.py:320` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商品カテゴリが見つかりません")` |
| `backend/app/routers/product_categories.py:345` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商品カテゴリが見つかりません")` |
| `backend/app/routers/buddy.py:77` | `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="コーチとメンティーは同一ユーザーにできません")` |
| `backend/app/routers/buddy.py:90` | `raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="同じペアリングが既に存在します")` |
| `backend/app/routers/buddy.py:110` | `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="アクティブなペアが見つかりません")` |
| `backend/app/routers/super_admin_knowledge.py:137` | `raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")` |
| `backend/app/routers/super_admin_knowledge.py:158` | `raise HTTPException(status_code=404, detail="ルールが見つかりません")` |
| `backend/app/routers/super_admin_knowledge.py:174` | `raise HTTPException(status_code=404, detail="ルールが見つかりません")` |
| `backend/app/routers/super_admin_knowledge.py:225` | `raise HTTPException(status_code=400, detail="CSVが空、またはヘッダーがありません")` |
| `backend/app/routers/super_admin_knowledge.py:230` | `detail=f"必須列が欠落: {sorted(missing)}",` |
| `backend/app/routers/note_master.py:188` | `detail="重複または制約違反",` |
| `backend/app/routers/note_master.py:210` | `raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")` |
| `backend/app/routers/note_master.py:225` | `raise HTTPException(status_code=409, detail="制約違反")` |
| `backend/app/routers/note_master.py:228` | `raise HTTPException(status_code=404, detail="備考マスタが見つかりません（テナント個別エントリのみ編集可能です）")` |
| `backend/app/routers/note_master.py:254` | `detail="備考マスタが見つかりません（テナント個別エントリのみ削除可能です）",` |
| `backend/app/routers/orders.py:217` | `detail=f"sort_by は {sorted(_SORTABLE_COLUMNS)} のいずれかを指定してください",` |
| `backend/app/routers/orders.py:223` | `detail="sort_order は asc / desc を指定してください",` |
| `backend/app/routers/orders.py:355` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="注文が見つかりません")` |
| `backend/app/routers/orders.py:376` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="注文が見つかりません")` |
| `backend/app/routers/orders.py:396` | `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="items を1件以上指定してください")` |
| `backend/app/routers/orders.py:402` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="注文が見つかりません")` |
| `backend/app/routers/orders.py:460` | `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="指定された会社が存在しません")` |
| `backend/app/routers/orders.py:465` | `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="指定された担当者が存在しません")` |
| `backend/app/routers/orders.py:468` | `detail="指定された担当者は会社に所属していません")` |
| `backend/app/routers/orders.py:476` | `raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="この注文番号は既に使用されています")` |
| `backend/app/routers/orders.py:537` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="注文が見つかりません")` |
| `backend/app/routers/orders.py:542` | `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="更新するフィールドを指定してください")` |
| `backend/app/routers/orders.py:593` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="注文が見つかりません")` |
| `backend/app/routers/orders.py:638` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="注文が見つかりません")` |
| `backend/app/routers/tcg_distribution.py:109` | `raise HTTPException(status_code=409, detail="この人にはもうシートがあります") from exc` |
| `backend/app/routers/tcg_distribution.py:111` | `raise HTTPException(status_code=422, detail="お客さんが見つかりません") from exc` |
| `backend/app/routers/tcg_distribution.py:124` | `raise HTTPException(status_code=404, detail="配信先が見つかりません")` |
| `backend/app/routers/tcg_distribution.py:143` | `raise HTTPException(status_code=409, detail="この人にはもうシートがあります") from exc` |
| `backend/app/routers/tcg_distribution.py:145` | `raise HTTPException(status_code=422, detail="お客さんが見つかりません") from exc` |
| `backend/app/routers/tcg_distribution.py:147` | `raise HTTPException(status_code=404, detail="配信先が見つかりません")` |
| `backend/app/routers/tcg_distribution.py:162` | `raise HTTPException(status_code=404, detail="配信先が見つかりません")` |
| `backend/app/routers/tcg_distribution.py:227` | `raise HTTPException(status_code=404, detail=f"設定キー {key!r} が見つかりません")` |
| `backend/app/routers/super_admin_suppliers.py:171` | `detail="重複または制約違反",` |
| `backend/app/routers/super_admin_suppliers.py:203` | `raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")` |
| `backend/app/routers/super_admin_suppliers.py:217` | `raise HTTPException(status_code=409, detail="制約違反")` |
| `backend/app/routers/super_admin_suppliers.py:220` | `raise HTTPException(status_code=404, detail="仕入元が見つかりません")` |
| `backend/app/routers/super_admin_suppliers.py:245` | `raise HTTPException(status_code=404, detail="仕入元が見つかりません")` |
| `backend/app/routers/super_admin_suppliers.py:589` | `detail="URL の supplier_id と body の supplier_id が一致しません",` |
| `backend/app/routers/super_admin_suppliers.py:606` | `detail="重複または FK 違反",` |
| `backend/app/routers/super_admin_suppliers.py:624` | `raise HTTPException(status_code=404, detail="routing が見つかりません")` |
| `backend/app/routers/super_admin_suppliers.py:731` | `raise HTTPException(status_code=404, detail="仕入元が見つかりません")` |
| `backend/app/routers/super_admin_suppliers.py:782` | `raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")` |
| `backend/app/routers/super_admin_suppliers.py:798` | `raise HTTPException(status_code=500, detail="更新エラー") from exc` |
| `backend/app/routers/super_admin_suppliers.py:802` | `raise HTTPException(status_code=404, detail="仕入元が見つかりません")` |
| `backend/app/routers/super_admin_suppliers.py:971` | `raise HTTPException(status_code=404, detail="仕入元が見つかりません")` |
| `backend/app/routers/super_admin_suppliers.py:986` | `raise HTTPException(status_code=409, detail="このルールは既にリンク済みです") from exc` |
| `backend/app/routers/super_admin_suppliers.py:1025` | `raise HTTPException(status_code=404, detail="リンクが見つかりません")` |
| `backend/app/routers/roles.py:223` | `detail="自分の最大priority以上のロールは作成できません",` |
| `backend/app/routers/roles.py:247` | `detail="同じ名前のロールが既に存在します",` |
| `backend/app/routers/roles.py:277` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ロールが見つかりません")` |
| `backend/app/routers/roles.py:279` | `raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="システムロールは編集できません")` |
| `backend/app/routers/roles.py:285` | `detail="自分と同等以上のpriorityを持つロールは編集できません",` |
| `backend/app/routers/roles.py:291` | `raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="更新するフィールドを指定してください")` |
| `backend/app/routers/roles.py:296` | `detail="priorityを自分の最大priority以上に設定できません",` |
| `backend/app/routers/roles.py:317` | `detail="同じ名前のロールが既に存在します",` |
| `backend/app/routers/roles.py:349` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ロールが見つかりません")` |
| `backend/app/routers/roles.py:351` | `raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="システムロールは削除できません")` |
| `backend/app/routers/roles.py:357` | `detail="自分と同等以上のpriorityを持つロールは削除できません",` |
| `backend/app/routers/roles.py:400` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ロールが見つかりません")` |
| `backend/app/routers/roles.py:430` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ロールが見つかりません")` |
| `backend/app/routers/roles.py:434` | `detail="システムロールの権限は変更できません",` |
| `backend/app/routers/roles.py:441` | `detail="自分と同等以上のpriorityを持つロールは編集できません",` |
| `backend/app/routers/roles.py:456` | `detail=f"存在しない権限ID: {sorted(missing)}",` |
| `backend/app/routers/roles.py:467` | `detail=f"自分が持たない権限は付与できません: {sorted(not_granted)}",` |
| `backend/app/routers/roles.py:517` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="指定されたユーザーが見つかりません")` |
| `backend/app/routers/roles.py:551` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="指定されたユーザーが存在しません")` |
| `backend/app/routers/roles.py:569` | `detail=f"存在しないロールID: {sorted(missing)}",` |
| `backend/app/routers/roles.py:575` | `detail=f"自分の最大priority以上のロール（id={row.id}）は付与できません",` |
| `backend/app/routers/notifications.py:124` | `raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")` |
| `backend/app/routers/notifications.py:139` | `raise HTTPException(status_code=404, detail="チャンネルが見つかりません")` |
| `backend/app/routers/notifications.py:155` | `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="チャンネルが見つかりません")` |
| `backend/app/routers/inventory_search.py:93` | `detail="在庫検索を実行する権限がありません (inventory.visibility.* または products.view が必要)。",` |
| `backend/app/routers/order_financials.py:98` | `detail="注文が見つかりません",` |
| `backend/app/routers/order_financials.py:139` | `detail="この受注の売上情報は既に登録されています",` |
| `backend/app/routers/order_financials.py:205` | `detail="売上情報が見つかりません",` |
| `backend/app/routers/order_financials.py:227` | `detail="売上情報が見つかりません",` |
| `backend/app/routers/order_financials.py:236` | `detail="更新するフィールドを指定してください",` |
| `backend/app/routers/order_financials.py:284` | `detail="売上情報が見つかりません",` |
| `backend/app/routers/inventory_offers.py:654` | `raise HTTPException(status_code=500, detail="INSERT 直後の取得に失敗しました")` |
| `backend/app/routers/inventory_offers.py:679` | `detail="更新するフィールドを指定してください",` |
| `backend/app/routers/inventory_offers.py:702` | `detail="指定されたオファーが見つかりません",` |
| `backend/app/routers/inventory_offers.py:707` | `raise HTTPException(status_code=500, detail="UPDATE 直後の取得に失敗しました")` |
| `backend/app/routers/inventory_offers.py:742` | `raise HTTPException(status_code=500, detail="UPDATE 直後の取得に失敗しました")` |
| `backend/app/routers/inventory_offers.py:764` | `detail="指定されたオファーが見つかりません",` |
| `backend/app/routers/super_admin_status_master.py:194` | `detail="重複または制約違反",` |
| `backend/app/routers/super_admin_status_master.py:214` | `raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")` |
| `backend/app/routers/super_admin_status_master.py:246` | `raise HTTPException(status_code=409, detail="制約違反")` |
| `backend/app/routers/super_admin_status_master.py:249` | `raise HTTPException(status_code=404, detail="ステータスが見つかりません")` |
| `backend/app/routers/super_admin_status_master.py:272` | `raise HTTPException(status_code=404, detail="ステータスが見つかりません")` |
| `backend/app/routers/super_admin_payment_fee_settings.py:109` | `detail="重複または制約違反",` |
| `backend/app/routers/super_admin_payment_fee_settings.py:129` | `raise HTTPException(status_code=400, detail="更新するフィールドを指定してください")` |
| `backend/app/routers/super_admin_payment_fee_settings.py:143` | `raise HTTPException(status_code=409, detail="制約違反")` |
| `backend/app/routers/super_admin_payment_fee_settings.py:146` | `raise HTTPException(status_code=404, detail="決済手数料設定が見つかりません")` |
| `backend/app/routers/super_admin_payment_fee_settings.py:168` | `raise HTTPException(status_code=404, detail="決済手数料設定が見つかりません")` |

## D. リダイレクトの reason= / status=error と、それを読む側

命令: `grep -rnE "reason=|status=error" backend/app/routers`（41 行のうち、リダイレクト URL に付けるのは discord_oauth.py のみ。ほかは監査ログや引数の reason=）、`grep -rnE "get\([\"']reason[\"']\)" frontend/src`、`grep -rnE "RedirectResponse|error_reason|[?&]error=" backend/app`

### D-1 サーバー側（RedirectResponse）

| ファイル:行 | 原文 | 理由コード |
|---|---|---|
| `backend/app/routers/discord_oauth.py:234` | `return RedirectResponse(f"{channels_url}?discord_status=error&reason=missing_state")` | missing_state |
| `backend/app/routers/discord_oauth.py:238` | `return RedirectResponse(f"{channels_url}?discord_status=error&reason=missing_guild_id")` | missing_guild_id |
| `backend/app/routers/discord_oauth.py:243` | `return RedirectResponse(f"{channels_url}?discord_status=error&reason=invalid_guild_id")` | invalid_guild_id |
| `backend/app/routers/discord_oauth.py:250` | `return RedirectResponse(f"{channels_url}?discord_status=error&reason=redis_error")` | redis_error |
| `backend/app/routers/discord_oauth.py:254` | `return RedirectResponse(f"{channels_url}?discord_status=error&reason=invalid_state")` | invalid_state |
| `backend/app/routers/discord_oauth.py:261` | `return RedirectResponse(f"{channels_url}?discord_status=error&reason=invalid_payload")` | invalid_payload |
| `backend/app/routers/discord_oauth.py:265` | `return RedirectResponse(f"{base}discord_status=error&reason=invalid_payload")` | invalid_payload |
| `backend/app/routers/discord_oauth.py:274` | `return RedirectResponse(f"{base}discord_status=error&reason=missing_code")` | missing_code |
| `backend/app/routers/discord_oauth.py:278` | `return RedirectResponse(f"{base}discord_status=error&reason={e.reason}")` | {e.reason} |
| `backend/app/routers/discord_oauth.py:284` | `return RedirectResponse(f"{base}discord_status=error&reason=guild_mismatch")` | guild_mismatch |
| `backend/app/routers/discord_oauth.py:328` | `return RedirectResponse(f"{base}discord_status=error&reason=guild_already_registered")` | guild_already_registered |
| `backend/app/routers/discord_oauth.py:334` | `return RedirectResponse(f"{base}discord_status=connected")` | （成功） |
| `backend/app/routers/google_calendar.py:112` | `return RedirectResponse(f"{frontend_schedule}?connected=false&error=invalid_state")` | invalid_state |
| `backend/app/routers/google_calendar.py:115` | `...?connected=false&error=token_exchange` | token_exchange |
| `backend/app/routers/google_calendar.py:151` | `...?connected=false&error=db_error` | db_error |
| `backend/app/routers/integrations.py:120` | `return RedirectResponse(f"{page}?connected=false&error=invalid_state")` | invalid_state |
| `backend/app/routers/integrations.py:123` | `...?connected=false&error=token_exchange` | token_exchange |
| `backend/app/routers/integrations.py:161` | `...?connected=false&error=db_error` | db_error |
| `backend/app/routers/meta_inbox.py:119-122` | `_frontend_callback_url(*, status_code, **extra)` で `/channels?status=...&...` を組み立てる関数。呼び出し箇所なし | （未使用） |

discord_oauth.py:278 の `reason={e.reason}` は例外オブジェクトの値で、取りうるコードの一覧は未確認。

### D-2 画面側で読む箇所

| ファイル:行 | 原文 | 読み方 |
|---|---|---|
| `frontend/src/pages/channels/ChannelsPage.tsx:161` | `const reason = url.searchParams.get("reason") \|\| "internal_error";` | `status=error` のとき。ERROR_REASON_KEYS（user_denied, state_mismatch, state_expired, meta_api_error, meta_timeout, no_pages, permission_denied, internal_error）にあれば `channels.errorReason.<code>`、無ければ `channels.errorReason.unknown`（「接続に失敗しました（理由: {{reason}}）。」でコードの生値を画面に出す） |
| `frontend/src/pages/admin/DiscordOwnServerPanel.tsx:124` | `params.get("reason") === "guild_already_registered"` | その1コードだけ専用文言、他は全部 `discordOwnServer.connectError` |
| `frontend/src/pages/channels/ChannelsPage.tsx:129-137` | `discord_status` が connected 以外 | reason を読まず `channels.discordConnectError` 固定（discord_oauth.py の 10 種の reason は区別されない） |
| `frontend/src/pages/oauth-callback/OAuthCallbackPage.tsx:73-74` | `url.searchParams.get("error")` / `get("error_reason")` | Meta から戻った error を user_denied / internal_error に写して `/channels?status=error&reason=` へ移動 |
| `frontend/src/pages/schedule/SchedulePageImpl.tsx:992` | `searchParams.get("connected")` | `error=` は読まず `schedule.connectError` 固定（invalid_state / token_exchange / db_error は区別されない） |
| `frontend/src/pages/integrations/GoogleDriveIntegrationPage.tsx:51` | `...get("connected")` | 同上、`error=` は読まず固定の失敗表示 |

理由コードの在庫: Discord=missing_state, missing_guild_id, invalid_guild_id, redis_error, invalid_state, invalid_payload, missing_code, guild_mismatch, guild_already_registered, {e.reason}（未確認）/ Google・integrations=invalid_state, token_exchange, db_error / Meta(画面側で生成)=user_denied, state_mismatch, no_pages, internal_error ほか（meta_api_error, meta_timeout, permission_denied は OAuthCallbackPage の HTTP 状態からの変換）。

## E. 理由コード→文言キーの対応表になっている既存ファイル

命令: `grep -rnE "errorReason|discordSendError|ERROR_KEYS|_REASON|REASON_|reasonKey|reasonToKey" frontend/src --include=*.ts --include=*.tsx -l`

| # | ファイル | 中身（読んだ範囲） |
|---|---|---|
| 1 | `frontend/src/pages/inbox/discordSendError.ts` | Discord 送信の reason（STAFF_EN_NAME_REQUIRED / STAFF_EN_NAME_INVALID / DISCORD_SEND_FAILED / DISCORD_WEBHOOK_PERMISSION）→ `inbox.sendError.*` と行動ボタン（CTA: 遷移/再送）。唯一、文言＋次の行動ボタンが対になっている |
| 2 | `frontend/src/pages/channels/ChannelsPage.tsx:66` `ERROR_REASON_KEYS` ＋ ja.json `channels.errorReason.*` | Meta 接続の理由 8 種＋unknown |
| 3 | `frontend/src/features/tcg-analysis-review/reviewReasonLabel.ts` | 要確認の理由コード→`reviewReason.<code>`（未登録は `reviewReason.unknown`） |
| 4 | `frontend/src/lib/auth/authErrorMessage.ts` | 口（login 等）と HTTP 状態＋detail 識別子→`authError.*` |
| 5 | `frontend/src/pages/super-admin/ViewerTemplatesPage.tsx:155` `ERROR_KEYS` | 422 の message→文言キー |
| 6 | `frontend/src/pages/super-admin/ViewerAccountsPage.tsx:282` | `viewer_already_linked` を文言に変換 |
| 7 | `frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.tsx:145-147` | PRODUCT_FORMAT_GAME_IN_USE / _UNKNOWN→文言、その他は `err.message` 素通し |
| 8 | `frontend/src/features/tcg-product-import/productDetailModel.ts:178,205` | PACKAGING_ERROR_CODES を err.message から判定 |
| 9 | `frontend/src/features/tcg-review-csv/reviewCsvTypes.ts`・`frontend/src/api/funnel.ts`・`frontend/src/pages/dashboard/FunnelReasonsPage.tsx`・`frontend/src/mocks/funnelFixtures.ts`・`frontend/src/features/tcg-analysis-review/ConditionReviewPanel.tsx`・`frontend/src/pages/inbox/InboxMessageThread.tsx` | grep に当たった。理由コード表かどうかは未確認（funnel 系は「理由」の別の意味の可能性） |

## F. エラー表示用の部品（frontend/src/components）

命令: `find frontend/src -iname "*Toast*" -o -iname "*Banner*" -o -iname "*Alert*" -o -iname "*ErrorMessage*" -o -iname "*ErrorBoundary*" -o -iname "*FormError*"` ほか。Toast / Banner / ErrorMessage / ErrorBoundary という名前の専用部品は Toast 以外見当たらない。

| 部品 | 場所 | props | 使用箇所数（tsx。テスト・stories除く） |
|---|---|---|---|
| Toast（`toast.success/warning/error/info(title, {description, duration})`） | `frontend/src/components/loading/Toast.tsx` | title: string、options: `{ description?: string; duration?: number }`（既定 4000ms）、variant: success/warning/error/info | `toast.error(`/`toast.warning(` は 3 行（下に全件） |
| Callout | `frontend/src/components/Callout.tsx` | variant: 'warning'(role=alert) / 'info'(role=status)、title: string（必須）、children、className | 38 |
| EmptyState | `frontend/src/components/EmptyState.tsx` | icon、title（必須）、description、action、size: default/compact、className | 40 |
| AppUpdateNoticeView / AppUpdateNotice | `frontend/src/components/AppUpdateNotice.tsx` | message、reloadLabel、onReload | 1 |
| （部品なし）`role="alert"` を各画面で直書き | frontend/src の 102 箇所（UnitImportPage など） | — | 102 |
| 画面ごとの独自 banner | ChannelsPage の `setBanner({type,text})`、SchedulePageImpl の `setBanner({type,message})` など | 画面ごとに別実装（共通部品か未確認） | 未確認 |

`toast.error` / `toast.warning` の全件:

- `frontend/src/features/tcg-analysis-review/DiagnosticsDrawer.tsx:199` `toast.error(t("superAdmin.diagnostics.retryError"));`
- `frontend/src/features/tcg-analysis-review/DiagnosticsDrawer.tsx:219` `toast.error(t("superAdmin.diagnostics.retryError"));`
- `frontend/src/pages/inbox/InboxMessageThread.tsx:231` `toast.error(`

## 生出力の保存について

grep の元の出力は、この文書の A〜C 表がそのまま全件（省略なし）。命令は各節の見出し下に原文で記載。取得時の件数: A=267, B=342, C=646, F(toast)=3。
