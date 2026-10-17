# recon — 解析の誤り報告から自律修正まで

> この文書は何か: 誤り報告の仕組みを作る前に、今のアプリ・agent-console・Discord 受付に何があって何が無いかを、ファイルの行番号つきで確かめた記録。
> 親: [docs/specs/analysis-error-report/README.md](../../specs/analysis-error-report/README.md)

基準: origin/main（2026-10-17 fetch 後、HEAD 1972f54dc）。agent-console は v0.42.3（525358a54）基準（main は v0.42.3 の祖先ではない・稼働中がどちらかは【未確認】）。
生出力（リポジトリ外）: /tmp/CC報告ファイル/autofix-recon.md、/tmp/CC報告ファイル/report-button-recon.md、/tmp/CC報告ファイル/report-button-raw/、/tmp/CC報告ファイル/poll-load-recon.md、/tmp/CC報告ファイル/mac-poll-load.md。

## 0. 既存 ADR 検索
- `git grep -n -i -E "error.?report|誤り報告" docs/adr/` → 0 件。
- docs/adr/FEATURE-INDEX.md の「取り込み / 解析」行 → ADR-100・ADR-014（取り込みの流れ。報告機能の記述なし）。
- 関係する ADR: ADR-1009（Discord 監視通知を Mac の Claude Code が受ける）、ADR-1012（ops_incidents）、ADR-1015（自律区分 A/B）、ADR-1003（GO の Opus 委任）、ADR-1020（共用商品 9 項目必須）、ADR-1016（即時反映 SSE）、ADR-144（UI 金型）、ADR-027（i18n）、ADR-1024（AI 用本番 DB 読み取りの道・PR #4450 未マージ）。

## 1. 報告ボタン
- 【事実】報告ボタンは無い。`git grep -i -E "誤り報告|error.?report|report.?error|wrong.?extraction"` の一致は抽出失敗件数 `extraction_error`（backend/app/routers/tcg_analysis_dashboard.py:139,307）だけ。
- 【事実】行ドロワー frontend/src/features/inventory/InventoryRowDrawer.tsx:22（props row, onClose, onChanged, isSuperAdmin）。解析タブ AnalysisPane :57（GET /tcg/analysis-results?extraction_item_ids= :67）。super admin 以外は原文タブだけ :205。
- 【事実】行の型 frontend/src/features/inventory/inventoryColumns.tsx:13-38。行と元データをつなぐ識別子は extraction_item_ids[]（API 側 backend/app/routers/inventory_offers.py:152-184）。
- 【事実】解析の比べ表 ItemComparison.tsx:26 の項目順 name, quantity, price, unit, state, memo。系統側の値 :41-50（product_title, quantity, price, unit, condition, note, work_name, product_id, status）。
- 【事実】既存の直す画面 ReviewFixWizard.tsx（ChoiceCardGroup の単一選択）、ReviewValueFixForm.tsx、ReviewProductFixForm.tsx、API 呼び出しは reviewActions.ts に集約。

## 2. 正解の候補の正本（すべて super admin 限定）
| 項目 | 正本 | API |
|---|---|---|
| 商品 | public.products（backend/app/services/tcg_product_master_svc.py:282-328、is_active・LIMIT 10） | GET /tcg/products/search（backend/app/routers/tcg_product_master.py:186）、フロント searchProductOptions（reviewActions.ts:68）＋AsyncCombobox |
| 単位 | public.units＋unit_aliases（tcg_analyzer_svc.py:78-80） | GET /tcg/review/value-options（item_corrections.py:300-313） |
| 販売状態 | public.tcg_status_master（tcg_analyzer_svc.py:1303） | 同上 |
| 状態 | public.conditions（tcg_condition_review_svc.py:298-302） | GET /tcg/conditions/review-options（tcg_analysis_review.py:174） |
| 数量・価格・メモ | 正本の候補表は見つからない【未確認: 専用の正本の有無】 | — |

## 3. 使える金型（frontend/src/components/）
Checkbox.tsx／CheckboxControl.tsx（複数選択）、MultiSelect.tsx、Radio.tsx／RadioControl.tsx、ChoiceCardGroup.tsx、Select.tsx、AsyncCombobox.tsx、Modal.tsx、ConfirmModal.tsx、Drawer.tsx、Sheet.tsx、Tabs.tsx。段階式フォームの金型は無い（実例は feature 内 ReviewFixWizard.tsx）。生の select/checkbox/radio は禁止（docs/CC_UI_GOVERNANCE.md:23-26）。

## 4. 報告の保存先
- 【事実】item_corrections（migrations/20260921_110000_pipeline_tables_public.sql:321-334）は人の訂正の追記専用表。保存で再解析が積まれる（backend/app/routers/item_corrections.py:182-187）。
- 【事実】配信の精度ゲートは field_name を問わず 30 日内の行を「修正済み」と数える（backend/app/services/tcg_distribution_svc.py:557-559）。backend/app/tools/reextract_v6_with_v102.py:241-260,723-732 は訂正のあるジョブを飛ばす。→ 報告を item_corrections に入れると、まだ直っていない報告が「修正済み」に数えられる。
- 【事実】ops_incidents は Alertmanager 専用の列（fingerprint NOT NULL 等・ADR-1012）。

## 5. 本番 → Discord
- 【事実】運営通知の送信関数 backend/app/services/discord_notifier.py:41-64（環境変数 ADMIN_NOTIFICATION_DISCORD_WEBHOOK）。誤り報告用のチャンネル・送信関数は無い。送り先チャンネルは secret のため【未確認】。

## 6. Discord → Mac
- 【事実】ADR-1009 の受付（tools/claude-channels/discord-ops、bot 方式）。gate() を通った発言だけを Claude Code に渡す（sa-ops-intake の server.ts:255-313、:988-1068）。チャンネルは access.json の groups で決まる。
- 【事実】今は止まっている: tmux に sa-ops-intake が無い・heartbeat 2026-10-15T11:53:19Z（/tmp/CC報告ファイル/autofix-recon.md §2-2）。常駐するのは Claude Code セッション（実測 RSS 65〜400MB・待機 CPU 0.1〜0.4%、/tmp/CC報告ファイル/mac-poll-raw/claude-procs.txt）。

## 7. agent-console
- 【事実】127.0.0.1 だけで待ち受ける（server/index.ts:35）。Host 検査で他は 421（http.ts:567-645）。外へ出る通信・Discord 接続は無い（grep 0 件）。
- 【事実】POST /api/sessions の body は name・roleId・branch（http.ts:183-188）で、最初の指示は渡せない。
- 【事実】指示を送る launchAndSend（launch.ts:98-114、promptText 上限 8192・name 上限 40）。
- 【事実】AI 用の口 /api/agent/reservations・/api/agent/routines は Origin があれば 403・Bearer 必須（http.ts:358-415）。予約は agent なら purpose="measure" 必須・1 分以上先（reservations.ts:172-181）。定期実行は曜日・時刻起動だけ（routines.ts:42）。→ 出来事をきっかけに開く口は無い。

## 8. 再解析と正答の確かめ方
- 【事実】再解析の口: POST /tcg/extraction-jobs/{id}/reanalyze（tcg_product_master.py:344-362、super admin）、Celery `tcg.v102_reanalyze_after_correction`（backend/app/tasks/tcg_extraction.py:839-853）。
- 【事実】解析結果の正誤を機械で照合する仕組み（正解の表＋照合）は無い。過去の正答率は AI 数体＋Opus の判定。

## 9. 規約の記録
- 【事実】docs/handoff/ai-ops-247/design.md:174 案F「自作アプリ（agent-console）から自動で指示｜規約 §3-7 の『自動・非人間のアクセス』に当たる恐れ｜不採用」。PO 2026-10-17「この記録を外して設計→外す」。
- 【未確認】規約 §3-7 の今の原文（本 recon は外部閲覧をしていない）。

## 10. 負荷の実測（Mac・本番）
- 【事実】Mac から 5 秒ごとに HTTPS で読む試験: 1 回 21.1ms、1 日 364 秒（0.05%）、メモリ +14MB（/tmp/CC報告ファイル/mac-poll-load.md）。
- 【事実】本番の今の API 呼び出し 1,492〜2,095 回/日。5 秒ごとに読むと +17,280 回/日（/tmp/CC報告ファイル/poll-load-recon.md）。
