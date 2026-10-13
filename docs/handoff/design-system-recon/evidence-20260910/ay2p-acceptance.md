# AY-2p 受入判定（実装担当 Sonnet）

基準 SHA: origin/main 6c8a5955a（設計は d39e251 時点。実装時に取り直した）。worktree: /Users/tanizawashingo/worktrees/salesanchor/release-list-search-inputs。
計測: 開発モード build + preview 4181、偽ログイン・API モック、ay2p-measure2.cjs を前後同じに実行。before=before2/measure-before2.json、after=after/measure-after.json。幅1280・1440・375、DPR2。
前後の全数値表: table-ba.md（本ファイル末尾にも転載）。

## 判定表

| 基準 | 前 → 後（実測） | 判定 |
|---|---|---|
| 金型に変わる | 5件×3幅すべて class に comp-field__input あり（前はなし）。padding 8px 12px、border 1px solid rgb(226,232,240)、角 6px（S5 は前 4px）、font 14.4px | 合格 |
| 幅（1280・1440） | S1 280→280、S2 160→160、S3 280→280、S4 280→280、S5 280→280。left も全件差 0（278/450/78/270/78） | 合格 |
| 並び（縦中心差、1280・1440） | S1 0→0.01、S2 0.01→0.01、S3 0→0.01、S4 0.01→0.01、S5 8.00→0.01（右スロットの 新規登録・削除 8.00 → -0.01）。すべて ±2 以内 | 合格 |
| 動作（API URL） | 15 シナリオ（5画面×3幅）で listUrlAfterFill（pathname+search）が前後完全一致。value=テスト検索ワード。console error なし | 合格 |
| S3 の Enter 検索 | 計測スクリプトに Enter 操作の項目は元々無く、前の取得も無い。fill だけで q= 付き GET /inventory が前後同一 URL で発行される。onKeyDown は diff 上で属性が逐語保持（TextFieldControl は ...rest を input に渡す＝TextField.tsx:41-54） | 未計測（Enter 単独は前後比較なし。実画面の再確認が必要なら設計者判断） |
| 横はみ出し | document scrollWidth==clientWidth が 15 シナリオすべて前後とも成立（1280/1280、1440/1440、375/375） | 合格 |
| 幅375 の検索欄 height（改訂1 M-1） | 5画面すべて 36 → 44.00（44±1 内） | 合格 |
| toolbar 高さ・一覧先頭 top（改訂1 M-2、1280・1440） | S1 toolbar 36→39.61、一覧 top 204.1→207.7（+3.6）／S3 36→39.61、126.0→129.6（+3.6）／S2 39.61→39.61、0／S4 39.61→39.61、0（いずれも許容内：S2・S4 ±1、S1・S3 +4 以内）／S5 55.61→39.61、145.6→129.6（-16.0、margin-bottom space-4 消失分。記録のみ） | 合格 |
| 他画面に影響なし | 連絡先の SelectControl field-w-sm が 160→160（1280・1440）。git grep（複数行対応の python 走査）で TextFieldControl に field-w-* を併用する箇所は S1・S3・S4・S5（S2 は className が属性の後ろ）の5件のみ（grep-checks.txt） | 合格 |
| 試験 | test:coverage（maxWorkers=1）Test Files 90 passed、Tests 1052 passed、exit 0。orders-search-input は OrdersFilterBar.tsx:40 と e2e 6件（order-commission:376 他）に残る。placeholder common.search は OrdersFilterBar.tsx:37・ProductsPage.tsx:220 に残る | 合格 |
| JS パターン（LOW-2） | 変更前 dev build: `input`,{type:`search`,className:`field-h-md field-w-md` が 2件。変更後 dev build 0件、本番 build（npm run build）0件。CSS `.comp-field__input.field-w-md` は dist CSS に1件。注: 本番 build の出力は二重引用符ではなくバッククォートで出る。設計の「"input",{type:"search",…」二重引用符形は後でも前でも 0 件になるので判定に使えない。本番判定はバッククォート形（`input`,{type:`search`,className:`field-h-md field-w-md`）で行うこと | 合格（要・判定文字列の差し替え） |
| 品質 | generate exit 0、tsc 0、lint 0、check:all 0、test:coverage 0、build 0、build-storybook 0（quality-exitcodes.txt） | 合格 |

## 想定外・要確認の数値（基準外。記録）

- 幅375 の検索欄 width: S2 contacts 149→160、S3 inventory 149→192（他は不変: S1 221.7、S4 280、S5 280）。基準にない項目。375 でも document scrollWidth==clientWidth は維持。金型化で flex の縮み方が変わった（原因は未調査）。
- S5 は toolbar 高さと一覧の位置が 16px 上がる（設計の予告どおり margin 消失）。
- 幅1280 の S1・S3 は toolbar が 36→39.61 に伸び、表が 3.6px 下がる（改訂1 の予告内）。

| 画面 | 幅 | width 前→後 | left 前→後 | 検索欄 height 前→後 | toolbar height 前→後 | 一覧先頭 top 前→後(差) | scrollW/clientW 前→後 | 縦中心差 最大|abs| 前→後 | comp-field__input |
|---|---|---|---|---|---|---|---|---|---|
| companies | 1280 | 280.0→280.0 | 278.0→278.0 | 36.00→39.61 | 36.00→39.61 | 204.1→207.7 (+3.6) | 1280/1280→1280/1280 | 0→0.01 | True |
| companies | 1440 | 280.0→280.0 | 278.0→278.0 | 36.00→39.61 | 36.00→39.61 | 204.1→207.7 (+3.6) | 1440/1440→1440/1440 | 0→0.01 | True |
| companies | 375 | 221.7→221.7 | 24.0→24.0 | 36.00→44.00 | 44.00→44.00 | 342.3→342.3 (+0.0) | 375/375→375/375 | 0→0 | True |
| contacts | 1280 | 160.0→160.0 | 450.0→450.0 | 36.00→39.61 | 39.61→39.61 | 207.7→207.7 (+0.0) | 1280/1280→1280/1280 | 0.01→0.01 | True |
| contacts | 1440 | 160.0→160.0 | 450.0→450.0 | 36.00→39.61 | 39.61→39.61 | 207.7→207.7 (+0.0) | 1440/1440→1440/1440 | 0.01→0.01 | True |
| contacts | 375 | 149.0→160.0 | 137.0→137.0 | 36.00→44.00 | 44.00→44.00 | 342.3→342.3 (+0.0) | 375/375→375/375 | 0→0 | True |
| inventory | 1280 | 280.0→280.0 | 78.0→78.0 | 36.00→39.61 | 36.00→39.61 | 126.0→129.6 (+3.6) | 1280/1280→1280/1280 | 0→0.01 | True |
| inventory | 1440 | 280.0→280.0 | 78.0→78.0 | 36.00→39.61 | 36.00→39.61 | 126.0→129.6 (+3.6) | 1440/1440→1440/1440 | 0→0.01 | True |
| inventory | 375 | 149.0→192.0 | 24.0→24.0 | 36.00→44.00 | 44.00→44.00 | 134.0→134.0 (+0.0) | 375/375→375/375 | 0→0 | True |
| orders | 1280 | 280.0→280.0 | 270.0→270.0 | 36.00→39.61 | 39.61→39.61 | 145.6→145.6 (+0.0) | 1280/1280→1280/1280 | 0.01→0.01 | True |
| orders | 1440 | 280.0→280.0 | 270.0→270.0 | 36.00→39.61 | 39.61→39.61 | 145.6→145.6 (+0.0) | 1440/1440→1440/1440 | 0.01→0.01 | True |
| orders | 375 | 280.0→280.0 | 16.0→16.0 | 36.00→44.00 | 44.00→44.00 | 350.0→350.0 (+0.0) | 375/375→375/375 | 0→0 | True |
| products | 1280 | 280.0→280.0 | 78.0→78.0 | 36.00→39.61 | 55.61→39.61 | 145.6→129.6 (-16.0) | 1280/1280→1280/1280 | 8→0.01 | True |
| products | 1440 | 280.0→280.0 | 78.0→78.0 | 36.00→39.61 | 55.61→39.61 | 145.6→129.6 (-16.0) | 1440/1440→1440/1440 | 8→0.01 | True |
| products | 375 | 280.0→280.0 | 24.0→24.0 | 36.00→44.00 | 60.00→44.00 | 150.0→134.0 (-16.0) | 375/375→375/375 | 8→0 | True |
## 改訂2 の反映（設計者判断）
幅375の検索欄 width 変化（S2 149→160、S3 149→192）は許容（基準外・記録のみ）。原因と詳細は ay2p-w375-cause.md。
