# AY-2s 設計: ブラウザ既定のままの生 input 6個 → 金型 TextFieldControl

- 状態: 設計審査済み（Fable r1 APPROVE、改訂1反映）。PO 委任 2026-10-14「金型への登録を全権限委譲」。既存金型の採用のみ（新金型なし・業務挙動変更なし）。
- 現在地の根拠: docs/handoff/ay2s-raw-inputs-mold/recon.md
- 対象 ADR: docs/adr/ADR-027-ui-internationalization.md / docs/adr/ADR-067-design-token-enforcement.md / docs/adr/ADR-144-ui-component-governance.md

## 1. 変更契約
|箇所|変更前|変更後|
|---|---|---|
|`frontend/src/pages/inventory/InventoryFilterPanel.tsx:287-299`（4個）|生 `<input … style={{width}}>`|`<TextFieldControl type="number" min="0" inputMode="numeric" style={{ width: <同じ値> }} …他 props 逐語>`。`import { TextFieldControl } from "../../components/TextField"` を追加|
|`frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:296, :375`（2個）|生 `<input … style={{width:SEARCH_WIDTH,maxWidth:"100%"}}>`|`<TextFieldControl style={{ width: SEARCH_WIDTH, maxWidth: "100%" }} …他 props 逐語>`（type 省略のまま）|

触らない: TextField.tsx・TextField.css/FormField.css、i18n、API 呼出・状態・値の変換、試験ファイル、docs/specs/design-system/design.md（設計者が後で追記）、GoalSettingPage（AY-2t）、DistributionTargetForm（AY-2u）。width の style は既存の幅指定の維持（新しい直値ではない）。

## 2. 想定分岐
- C1: `.comp-field__input` の width:100% より inline style の width が勝つ。after で 96/112/480(375 は 327) のままか確認。
- C2: 金型の高さ（約39.6px、≤767px は 44px）で行が伸びる。375 の折返し・はみ出しが悪化したら停止。
- C3: 隣接ボタンとの縦中心差が before より1px超悪化したら停止して報告。
- C4: type=number の見た目は金型既定に従う。値は文字列のまま。

## 3. 前後（想定）
|項目|前|後|
|---|---|---|
|枠|2px inset 灰|金型 1px solid var(--border)|
|角丸|0|金型 radius（6px）|
|高さ|19px|約39.6px（≤767px 44px）|
|文字|13.33px 黒|金型 font・var(--text-primary)|
|幅|96/112/480(375 は 327)|同じ|

## 4. 検証
|基準|検証方法|
|---|---|
|6個が class comp-field__input を持ち、border/radius/height/font が金型値|after 実測（ay2s-measure.cjs）|
|幅が前と同じ（±0.5px）|before/after 実測|
|全幅で doc scrollWidth==clientWidth、新たな負の left なし|after 実測|
|在庫フィルタ入力→一覧 API パラメータが前後一致|page.route 記録|
|rules/aliases 検索 Enter→検索 API 呼出が前後一致|page.route 記録|
|対象2ファイルに生 text/number `<input` 0 件|git grep|
|generate・tsc・lint・check:all・test:coverage(maxWorkers=1)・build・build-storybook 成功|ログ|
|本番 JS に testid inventory-qty-min と comp-field__input の利用が反映|prod bundle grep（マージ後）|

結果は docs/handoff/design-system-recon/evidence-20260910/ay2s-acceptance.md を参照。

## 5. 代替案
- TextField（ラッパー付き）: 不要な margin-bottom が付き行が崩れる → 不採用。
- label 追加（a11y 改善）: i18n キー新設を伴う別テーマ → 本便は見た目の金型化のみ。

## 6. リスクと戻し方
見た目が変わる（既定→金型）。前後スクショは evidence に保存。在庫フィルタは高さが増える。戻し方: revert（2ファイル）。測り方: 上記 evidence の diff。

## 外部・過去事例の参照と我々への応用
- 過去: AY-2n（#4223）/AY-2p（#4238）で検索欄を TextFieldControl/TextField へ統一した前例。同じ手順（逐語 props 移行・前後実測）を適用。
- 外部事例: 不要（社内金型の適用のみ）。

## 維持の仕組み
- 守り手: frontend/src/components/TextField.tsx（入力欄の見た目の正本）
- 守り手2: scripts/check-ui-governance.js（pages の生 input 検出。type=number は :213-217（isDetectableInput）で対象外＝既知の穴、残件）

## r2 追補: C3 の判定（Opus、実装中の発見）
- 事実（docs/handoff/design-system-recon/evidence-20260910/ay2s-before.json・ay2s-after.json、knowledge-aliases-w375）: 375 では検索ボタン群が入力の次の行に折り返している（前後とも）。入力の下端からボタンの上端までの間隔は前 8px（入力 top 383.47+h19=402.47、ボタン中心 392.97+39.5 から h44 で top 410.47）、後 8px（入力 383.47+44=427.47、ボタン中心 405.47+52 から top 435.47）で同じ。
- 判断: C3 は同じ行の縦整列の悪化を止める条件。375 は別の行のため中心差の数値は入力の高さ増（19→44）をそのまま反映するだけで、整列の悪化ではない。停止条件に該当しないとして進める。1280/1440 の同一行の差は 0→−0.01。
