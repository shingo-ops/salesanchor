# 実装カード 段階3 便8b — 使われていない読み込み系の辞書キーを消す（2回目）

- 状態: Opus 作成・自己審査済み（同一AIの審査）。PO 承認: 方針 2026-10-23「1」、設計 2026-10-24「1」、便7のあとの残件着手 2026-10-26「1」
- 根拠: 事前調査 keys45-check.tsv（本カード §1 に判定を写した）。便7b card-16 と同じ確かめ方
- 起点: 最新 origin/main（便8a #4782 の合流 2d25c719d を含むこと。git grep -n confirmLoading origin/main -- frontend/src/pages/channels/ChannelsPage.tsx が2件でなければ BLOCKED:）。ブランチ release/loading-button-bin8b
- 対象ADR: ADR-027（辞書は ja/en 同一キー）・ADR-144
- 実行場所: クラウド。push までを行う。PR は手元で作る。
- 作業場所（1回目の教訓）: リポジトリ直下で npm を入れると commit 前の見張りが有効になり、「worktree 外」として commit が止まった。手順1の new-worktree.sh で作った作業場所で、編集・npm・試験・commit・push をすべて行う。
- 1回目からの変更（Opus 判断）: §2d で、docs/ の中の記録（docs/handoff・docs/specs・監査の json など、過去の調査や設計の記録）の当たりは「使っている場所」に数えない。1回目はこれで6キー（inbox.loadingProfile, analysisRules.dashboard.loading, ruleManagement.exporting, ruleManagement.bulkDeleting, channels.disconnecting, channels.discordDisconnecting）を残したが、今回は他の確認を通れば消す。理由: 記録の中の文字はアプリが読む場所ではなく、消しても画面は変わらない。

## 1. 消す候補（32キー）と残すキー
(1) 消す候補（§2 の確認をすべて通ったものだけ消す）
- 参照0の30キー: apiIntegration.inProgress, dashboard.discovery, dashboard.dealActive, dashboard.orderActive, leads.status_negotiating, leads.status_ai_collecting, customers.searchPlaceholder, inbox.loadingProfile, deals.stage_negotiating, oauth.success, superAdmin.supplierQuality.showingCount, superAdmin.suppliersAdmin.saving, superAdmin.inbound.filters.searchPlaceholder, superAdmin.inbound.parseStatus.parsing, superAdmin.inbound.review.selectedProduct, superAdmin.inbound.review.masterPickerPlaceholder, superAdmin.phaseSwitch.outOfScopeBadge, superAdmin.phaseSwitch.outOfScopeTooltip, channelMasters.loading, analysisRules.accuracyManagement.comingSoon, analysisRules.dashboard.staleRunning, analysisRules.dashboard.loading, analysisRules.dashboard.distributionStale, ruleManagement.test.running, ruleManagement.test.seeding, ruleManagement.create.creating, ruleManagement.edit.updating, ruleManagement.edit.disabling, ruleManagement.exporting, ruleManagement.bulkDeleting
- 便8a で参照0になった2キー: channels.disconnecting, channels.discordDisconnecting
(2) 残す（消さない・触らない）15キー
- 使われている10キー: ruleManagement.test.gateRunning, ruleManagement.test.expectedCanonicalPlaceholder, superAdmin.viewers.statusPending, superAdmin.viewers.statusSuspended, pmgWorkflow.extractionStatus.pending, pmgWorkflow.extractionStatus.running, analysisRules.errorLog.tab.inProgress, analysisRules.errorLog.status.inProgress, analysisRules.dashboard.extractionJobStatus_pending, analysisRules.dashboard.extractionJobStatus_running
- 実際の値が入るか確かめきれていない5キー（Opus 判断: 確かめきれないものは消さない）: leads.discordRoleSyncStatus_pending, discordConfig.syncStatus.pending, superAdmin.viewerTemplates.saving（試験だけが参照）, nav.searchPlaceholder（型 `nav.${string}` が受ける）, buybackPrices.loading（card_game の値の範囲外だが取り込み元すべては未確認）

## 2. 消す前の確認（キーごと。結果を /tmp/CC報告ファイル/loading-button-bin8b/impl/keys-check.tsv に1キー1行）
a. 値: 今の本体 ja・en の値を書き出す（記録のため）
b. 直接の参照: キーを二重引用符・一重引用符・バッククォートで囲んだ3通りで git grep -nF -- frontend/ e2e/ がすべて 0 件
c. 最後の部分での組み立て: キーの最後の部分（例 saving）を git grep -nF で frontend/src から探し、テンプレート文字列や文字列の足し算で親のキーと組み合わさる当たりがあれば、その変数が取りうる値を実物で特定し、親がこのキーの親と一致しないことを示す。示せないものは消さずに残す
d. 本体以外の使い道: git grep -nF でキーを全体から探し、辞書ファイルと docs/ 以外の当たり（gas/・backend/・scripts/・e2e/・frontend/ を含む）が 0 件。docs/ の当たりは件数とファイル名を記録するだけ（判定に使わない）
e. viewer の辞書（scripts/check-i18n-missing-keys.js の VIEWER_LOCALE_FILES）にもあるかを書く。あれば viewer からも同じ commit で消す

## 3. 消し方
- 本体辞書 ja.json・en.json（と §2e で当たった viewer の辞書）から、同じキーを同じ commit で消す
- キーを消して親の入れ物が空になったら、その空の入れ物も消す
- JSON を機械で書き直さない。該当行（と空になった入れ物の行、直前の行末のカンマ）だけを消し、git diff で他の行が変わっていないことを確かめる

## 4. 触らない範囲
- §1(2) の15キー、それ以外の辞書キー、辞書の値の書き換え・並べ替え
- .tsx・.ts・.css、金型、scripts/、.github/workflows/、docs/ の過去の記録

## 5. 文書
- docs/handoff/loading-indicator/design.md 3-7 の残件②（参照0の読み込み系45キー）の行に「便8b（card-18）で N キーを消した。残す15キーと理由は card-18 §1(2)。docs/ の中の過去の記録の当たりは参照に数えない」を足す（N は実際に消した数）
- 本カード（この全文）を docs/handoff/loading-indicator/card-18.md として同じ commit に入れる

## 6. 検証
| 基準 | 検証方法 |
|---|---|
| 消したキーが ja/en で同じ | 消す前後のキー集合を平らにして書き出し、前−後 が ja と en で完全一致し、消したキー一覧と一致する（diff が空）。viewer も同様 |
| 消し過ぎていない | 前−後 の件数＝keys-check.tsv で消すにした件数。他のキーの値が1つも変わっていない |
| 残すキーが残っている | §1(2) の15キーが ja・en の両方にある |
| 辞書の検査 | node scripts/check-i18n-missing-keys.js exit 0 |
| 型 | frontend で npm ci（必要なら）・npm run generate:api-types のあと npx tsc --noEmit exit 0 |
| 単体試験 | frontend で npx vitest run --project unit src/components src/pages/channels src/pages/super-admin が pass（1回目は --project を付けないと browser-playwright の起動失敗で exit 1 だった）。時間切れで落ちたら、落ちたファイルだけ1つずつ走らせ直して結果を書く |
| UI ガバナンス | 作業場所の直下から BASE_SHA=<起点> HEAD_SHA=HEAD node scripts/check-ui-governance.js exit 0 |
| 範囲 | git diff origin/main...HEAD --name-only が 本体 ja/en・（当たれば）viewer ja/en・design.md・card-18.md だけ |

## 7. 想定分岐
- §2 で消せないキーが出た → 消さずに理由を書いて進める。5キー以上残るなら NEEDS_DECISION:
- 消すとビルドや試験が落ちる → そのキーを戻して理由を書き、BLOCKED:
- 起点に便8a が入っていない → BLOCKED:
- new-worktree.sh・commit・push のどれかが止まる → BLOCKED:（出力全文）
