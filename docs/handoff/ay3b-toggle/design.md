# AY-3b design（切替スイッチ8か所を共通部品 Toggle へ）

recon: docs/handoff/ay3b-toggle/recon.md。審査: 設計 r2 APPROVE（/tmp/CC報告ファイル/ssot-toggle/design-review-r2.md、必須なし）。実装カードの正本は /tmp/CC報告ファイル/ssot-toggle/ay3b-design.md。PO 決定: 2026-10-15「Y」（8 か所を 1 部品に統一・幅 44px、マージ前に実測を PO へ提示）。

## 変更の要点
- 新規 frontend/src/components/Toggle.tsx・Toggle.css（ネイティブ checkbox + role="switch"。props は checked・onCheckedChange・disabled・id・aria-label・aria-labelledby。className・style は受けない）。
- 8 か所を `<Toggle>` へ。名前の無い 5 か所に既存キーの aria-label。
- 旧 CSS（components.css・account-settings.css・InboxPage.css・schedule.css）を撤去。トークン 3 件を削除。
- 見た目: 枠 44×24、つまみ 18、移動 20、影 --shadow-drop-sm、focus-visible の輪、transition --transition-micro。新しい色・数値・トークンなし。

## 検証
|基準|検証方法|
|---|---|
|8 か所が Toggle になり旧 class が 0|frontend/src/components/ToggleMigration.test.tsx (a)（`<Toggle` が 1・4・1・2、旧 class 0、各 `<Toggle` に aria-label か id）|
|InboxSettingsModal の switch が 4 つで名前が既存キー|ToggleMigration.test.tsx (b)（en 初期化）|
|Toggle の契約（checked 反映・onCheckedChange(next)・disabled・role・aria・className を受けない）|frontend/src/components/Toggle.test.tsx（@ts-expect-error 含む）|
|前後の見た目の差が §1.1 の表どおり|docs/handoff/design-system-recon/evidence-20260910/ay3b-measure.cjs・ay3b-compare.cjs、ay3b-acceptance.md|
|新しい色・数値を足していない|npm run check:new-tokens・check:css-values・check:css-colors・stylelint|
|カタログ登録|frontend/src/components/Toggle.stories.tsx、npm run check:stories|

## 外部・過去事例の参照と我々への応用
- 外部: WAI-ARIA の switch ロール（ネイティブ checkbox に role="switch" を付ける型、W3C Switch Pattern）。docs/specs/design-system/design.md:411 の契約が既に採用している。新たな外部事例は不要。
- 過去: §AY-2z・§AY-3a（旧規則を同便で撤去し前後実測）、§AY-2v（参照 0 のトークンの削除）。応用: 旧規則の撤去と部品の追加を同じ PR で行い、本番 CSS と PR の vite build CSS を 1 本のまま前後実測する。

## 維持の仕組み
守り手: frontend/src/components/Toggle.tsx・Toggle.css・Toggle.test.tsx・Toggle.stories.tsx（check:stories）、docs/CC_UI_GOVERNANCE.md。生の切替スイッチの再発は CI では検出しない（check-ui-governance への checkbox 検出追加は別判断）。

## 触らない範囲
- 画面に見える文言・並び・ラッパー。他の checkbox（CheckboxControl）。44×44 の操作領域（行の高さが変わり、対応トークンも無いため未着手）。

## 切り戻し
merge commit の revert（DB 影響なし）。

## 実測判定（B7）

- B7: 字面どおり該当。設計者（Opus）判断で許容: 増分 +2px は PO 決定の幅 42→44 の直接の派生、操作欄内側のはみ出し 0、390px 行のはみ出しは旧から（schedule.css:887-894）で本便の範囲外
