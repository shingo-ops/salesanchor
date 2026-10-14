# AY-2r 受入判定（設計 §4 全行）

実測: ay2r-before.json（変更前 HEAD e0355ceef の dev build）と ay2r-after.json（変更後の dev build）。同一スクリプト ay2r-measure.cjs、preview ポート 4182、7画面×幅1280/1440/375（計21ケース）。差分は ay2r-diff.md。

|基準|結果|根拠|
|---|---|---|
| 5画面の検索欄 width=280・radius 6px・height/padding/border/font 差0 | 合格（補足あり） | after は 5画面×3幅の全15ケースで rect.width=280、border-radius=6px。height（39.61、375 は 44）・padding（8px 12px）・border・font-size・color・background-color は前後同一。computed の差は radius（4→6px）と min-width（280px→auto）のみ。min-width は `.search-bar input` 規則（min-width:var(--input-select-min-w)）削除の帰結で、描画幅（rect）は不変。ay2r-diff.md |
| 5画面の縦中心差 ≤0.5px | 合格 | 前 7.99（375 は 8）→ 後 -0.01（375 は 0）。15ケースすべて ≤0.01 |
| Contacts/Companies の検索欄 rect・computed 差0 | 部分合格（rect は差0、computed は min-height のみ差あり） | rect は6ケースすべて差0。computed は 1280・1440 の4ケースで min-height が 36px→auto。`field-h-md` を除いたことの直接の帰結（描画高 39.61 は不変）。375 の2ケースは差なし。設計 §1 の「field-h-md は効果なし」と整合 |
| scrollWidth==clientWidth（全画面・全幅） | 合格 | 検索欄の scrollWidth/clientWidth と document の scrollWidth/clientWidth が21ケースすべて一致（after.json） |
| 検索の動作（入力→送信で一覧 API の search パラメータ）前後一致 | 合格 | 21ケースの searchCalls（"GET /<path>?...search=%E3%83%86…"）が前後で完全一致（ay2r-diff.md に searchCalls の差行なし） |
| `.filter-bar`・`search-input`（class）の参照 0、`.search-bar input` 規則 0 | 合格 | ay2r-grep-filterbar-exact.txt・ay2r-grep-searchinput-exact.txt・ay2r-grep-searchbar-input.txt（git grep の単語境界つき、3件とも 0 件）。部分一致の `inbox-sub-filter-bar`・`search-input-field`・`inbox-search-input`・`orders-search-input` は別名で対象外 |
| generate・tsc・lint・check:all・test:coverage(maxWorkers=1)・build・build-storybook 成功 | 合格（test は注記あり） | generate:api-types・generate:icon-sizes・tsc・lint（0 errors）・check:all（25/25 exit 0）・build・build-storybook は exit 0。test:coverage は下記注記 |
| 本番 CSS に `.search-bar input` 0 件、`.content-toolbar .field-w-md` 規則あり | ローカル本番 build で合格。本番サイトは反映後に確認 | ay2r-prod-build-checks.txt: `.search-bar input` 0、`.content-toolbar .field-w-md` 1、`.search-bar{margin-bottom:var(--space-4)}` 1 |

## 注記
- test:coverage（maxWorkers=1）: 1回目は 1 failed（StaffFormButtonMigration の 5000ms タイムアウト、単体再実行は 31 passed）。2回目は 6 files・11 tests がタイムアウトで failed。マシン負荷が高く（load average 37〜66）、失敗が回ごとに別テスト。3回目に `--testTimeout=60000` を付けて Test Files 92 passed・Tests 1066 passed（q-test-coverage-rerun2.txt）。AY-2q でも同じテストの 5000ms タイムアウトが記録されている。
- 設計との差: 「Contacts/Companies computed 差0」と「min-width computed」は上記のとおり、設計した変更自体の帰結（描画 rect は差0）。
