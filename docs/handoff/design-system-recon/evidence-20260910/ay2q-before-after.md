# AY-2q 前後比較（実測）

- 前: /tmp/CC報告ファイル/ssot-ay2q/before/ay2q-measure-before.json（基準 origin/main d3e8327016f5）
- 後: /tmp/CC報告ファイル/ssot-ay2q/after/ay2q-measure-after.json（基準 origin/main 0819129aa ＋ 本変更）
- 条件（前後同じ）: NODE_ENV=development の dev build、ダミー VITE_FIREBASE_*、preview 4182、見積作成・請求書作成 × 幅1280/1440/375、DPR2、候補3件の API モック、同じスクリプト（after は群/行 rect の記録とスクショ切り出し高さの拡張のみ追加）
- 数値は見積作成（quote）。請求書作成（invoice）も class・aria-pressed・disabled・API op・scrollWidth・群/行は全て同じ結果（JSON 参照）

## §4 受入条件

| 基準 | 実測（after） | 判定 |
|---|---|---|
| AND/OR が `comp-btn comp-btn--tab`、選択側に `comp-btn--active` | 初期: AND=`comp-btn comp-btn--tab`、OR=`comp-btn comp-btn--tab comp-btn--active`。AND 押下後は逆（6シナリオとも） | ○ |
| aria-pressed 初期 OR=true / AND=false、AND 押下で反転 | 初期 AND=false・OR=true、AND 押下後 AND=true・OR=false、OR 押下後 AND=false・OR=true（6シナリオとも） | ○ |
| 1語以下で両方 disabled、2語で押せる | 空欄: AND disabled=True・OR disabled=True。2語入力後: 両方 disabled=False（6シナリオとも） | ○ |
| API op が追従 | AND 押下: `op=and`、OR 押下: `op=or`、OR 中に語を変更: `op=or`、AND 中に語を変更: `op=and`（6シナリオとも） | ○ |
| InventorySearchBar.tsx の AND/OR 部に inline style・色直値 0 | AND/OR の Button に style なし。差分で追加された `style` は群 div の flexWrap と行 div の flexWrap のみ（色・px 直値 0）。git grep は下記 | ○ |
| scrollWidth==clientWidth かつ 群 right ≤ 行 right | 1280: 1280/1280、群 right 742 ≤ 行 right 742。1440: 1440/1440、742 ≤ 742。375: 375/375、群 right 327 ≤ 行 right 327（quote・invoice とも。AND 押下後も 1280/1280・1440/1440・375/375） | ○ |
| 前後スクショ（初期・選択後・hover・focus・無効） | before 30枚・after 30枚（/tmp/CC報告ファイル/ssot-ay2q/before/、after/）。代表16枚を evidence へ | ○ |
| 品質 | generate・tsc・lint・check:all・build・build-storybook: exit 0。test:coverage: 1 ファイル 2 件がタイムアウトで exit 1（StaffFormButtonMigration、無関係）。単体再実行は 43 passed | 要判断（下記） |
| 本番 JS の生 button op style 文字列 0 | 本番反映後に確認（実装便の範囲外） | 未実施 |

## §3 見た目の変化

| 項目 | 前（実測） | 後（実測） | 設計どおり |
|---|---|---|---|
| 選択中 背景/文字/太さ | rgb(30,58,138)/white/400 | rgb(235,239,248)/rgb(30,58,138)/600 | ○ |
| 未選択 文字/太さ | rgb(26,32,44)/400（透明背景） | rgb(74,85,104)/500（透明背景） | ○ |
| hover（1280・1440） | 変化なし（透明） | rgb(247,250,252) | ○ |
| hover（375） | 変化なし | 取得できず（候補一覧が AND/OR の上に重なり hover が届かない。下記 B5） | 記録 |
| 高さ（1280） | 29 | 36 | ○ |
| 高さ（375） | 71（文言が折返し） | 44（AND/OR とも縦2段、群 90） | ○ |
| padding | 4px 10px | 8px 20px | ○ |
| 文字サイズ | 13.33px | 14.4px | ○ |
| focus | `rgb(0,95,204) auto 1px`（ブラウザ既定） | `rgb(26,32,44) solid 2px`、offset 2px（金型） | ○ |
| 無効時 | 群 opacity 0.6、ボタン 1 | 群 opacity 1、ボタン 0.6（枠線は減光しない） | ○ |
| ボタンの枠・角 | border 0・角 0 | border 1px 透明・角 6px | ○ |
| 群の幅（1280） | 276.4 | 323.7（検索欄 355.6 → 308.3 に縮む。top・縦中心差は 0.01 以内） | 記録（設計に明記なし） |
| 群の位置（375） | 検索欄の右（left 176・幅 151・高さ 73） | 検索欄の下の行（left 48・幅 279・高さ 90、ボタンは左寄せ 152.6/169.1） | ○ |
| role | radiogroup | group | ○ |

## 分岐 B1〜B4

- B1: 枠 div の opacity を削除。無効時のボタン opacity は 0.6（Button.css）、群は 1。二重減光なし（実測）。
- B2: 行 div と枠 div に flexWrap:"wrap"。1280/1440 は1行のまま（群 top 565.6、検索欄と縦中心差 0.01）。375 は群が次行へ、AND と OR が縦2段。scrollWidth==clientWidth、群 right ≤ 行 right を満たす。
- B3: 型エラーなし（tsc exit 0）。data-testid・disabled は通る。
- B4: title は枠 div に残した。
- 設計外の1点（B5・要判断）: 幅375で、検索結果の候補一覧が AND/OR 群の真上に重なる。2語入力後の候補表示中は elementFromPoint(AND の中心) が `quote-add-search-result-0-name`（候補）を返す（候補 top 655.8〜722.2、AND top 661.8〜705.8）。before は AND/OR が検索欄の右隣にあり重ならなかった。候補を閉じれば（Esc・外側クリック）AND/OR は操作できる。Playwright の click は成功し op=and になる（307ms、成功時は候補が閉じている）。実機の指での挙動は未確認。
- 設計外の1点（type）: Button は `type` の既定が無く、両ページとも AND/OR は `<form>` の中にある（QuoteCreatePage.tsx:145、InvoiceCreatePage.tsx:290）。そのままだと押下でフォームが送信されるため、元の生 button が持っていた `type="button"` を Button にも付けた（見た目・設計の他の部分に影響なし）。

## 品質コマンド（ログは /tmp/CC報告ファイル/ssot-ay2q/impl/）

| コマンド | 結果 | ログ |
|---|---|---|
| generate:icon-sizes / generate:api-types | exit 0（差分なし） | generate.txt |
| tsc --noEmit | exit 0 | tsc.txt |
| lint | exit 0 | lint.txt |
| check:all | exit 0 | checkall.txt |
| test:coverage -- --maxWorkers=1 | exit 1。2 failed / 1052 passed。落ちたのは StaffFormButtonMigration.test.tsx の2件（`Test timed out in 5000ms`）。同ファイル＋Button.test.tsx の再実行は 43 passed | coverage.txt、rerun-staff.txt |
| build | exit 0 | build.txt |
| build-storybook | exit 0 | storybook.txt |
| e2e quote-create-inventory-search.spec.ts | 実行不可。`browserType.launch: Executable doesn't exist at .../chromium_headless_shell-1217/...`（手元は 1248 のみ）。3件とも起動前に失敗 | e2e.txt |

## r3（B5 解消）

r3 追補（B5 解消、実測 ay2q-after-r3.json・ay2q-r3-summary.txt）: 行 div に rowRef を付け、候補一覧の top だけを行の bottom+2 にした（left・width は input のまま。InventorySearchBar.tsx）。

| 基準 | 実測 | 判定 |
|---|---|---|
| 幅375 で候補 top ≥ 群 bottom、AND 中心の最前面が AND | quote・invoice とも True / AND 自身。候補 top 752.84 / 824.84（行 bottom+2） | ○ |
| 幅1280/1440 の候補 top が変更前と ±1px | 606.45・587.27（quote）、666.45・647.27（invoice）。変更前（input.bottom+2）と差 0 | ○ |
| 1語ヒント表示中 | 記録のみ（専用の再測定なし） | 記録 |
| 375 hover | rgb(247,250,252) を取得（B5 解消で取れるようになった） | ○ |
| B5 | 解消済み | ○ |
