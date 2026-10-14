# AY-2y 受入の前後表（商品マスタ引き出し・原文欄の i18n 化と金型移管）

測定方法: AY-2x と同じ。fixture（API を mock）の dev server で 390/1280 × ja/en × ライト/ダークの 8 条件を、全状態（src-empty/multi/nomatch、reg-empty/filled/error/dup-unchecked/dup-checked/saved、kw-initial/results/selected/exists/saved、excluded、assign-initial/typed/results/selected）について取得。
前後の生データ: docs/handoff/design-system-recon/evidence-20260910/ay2y-measure-before.json・ay2y-measure-after.json（キーは「幅-言語-テーマ」）。生出力の保存先 /tmp/CC報告ファイル/ssot-ay2y/impl/（compare-r2.txt が比較結果、compare.py が比較スクリプト）。
変更前コード: f005b623f（origin/main を merge した時点）。変更後: R2-10（検索行を2段化）を含む。

## 停止条件の判定（変更後）
| 条件 | 判定 | 根拠 |
|---|---|---|
| B1 横 overflow が増えない（.pmd-body・.source-search・.source-raw .raw・.source-raw） | 該当なし | compare-r2.txt に B1 行が 0 件（8 条件 × 全状態）。1 回目の測定（R2-10 前）は 390 ja +7px、390 en +61px、1280 en +23px だった（compare.txt、measure-after-r1/） |
| B2 ja の innerText・aria-label・placeholder が 1 文字も違わない | 該当なし | 差は閉じるボタン中身の「×」のみ（除外対象）。aria-label「閉じる」は一致 |
| B3 API 呼び出し（method・path・body）の差 0 | 該当なし | 7 条件は 21 回で一致。1280 ja light の変更前だけ 20 回だったが、変更前コードを別 worktree（detached・読取専用）で 2 回測り直すと 2 回とも 21 回で、変更後と並びが一致（pw-before-rerun1.txt・rerun2.txt）。最初の 20 回は取りこぼしと確定 |
| B6 en に日本語が残らない | 該当なし | 例外「商品マスタV2」（excluded の説明文中の固有名）のみ |
| B7 候補ボタンの並び | 該当なし | kw-results・assign-results の候補（PM-00001 → PM-00002）は x・幅・縦の並びが同じ（高さのみ金型どおり） |

## 見える変化（前 → 後）
| 場所 | 前 | 後 |
|---|---|---|
| 引き出しの閉じるボタン（全モード） | 文字「×」（17.6px、枠なし、26×26） | X アイコン（金型の ghost iconOnly、1280 で 36×36、390 で 44×44）。aria-label「閉じる」は同じ |
| 入力欄（登録フォーム） | padding 8px、文字 13.6px・太さ 500、高さ約 40px（390 で約 40） | 金型 sm: padding 4px 8px、太さ 400、高さ約 30px（1280）。390 では 44px（最小タップ高） |
| 複数行欄 | 生 textarea | 金型の textarea（sm）。最小高さ 72px は維持 |
| ボタン（重複候補確認・登録・マスタを検索・キーワード追記・割り当て検索・商品を変更・確認済み記録） | 16px・太さ 400、padding 8px 12px、高さ約 44px | 金型 md: 14.4px・太さ 500、padding 8px 20px、高さ 36px（1280）。390 では 44px。幅は 3〜8px 広がる |
| 主ボタン（登録・キーワード追記・商品を変更） | 白地の生ボタン | 主色の塗り（rgb(30, 58, 138)） |
| 候補ボタン（PM-xxxxx の行） | 枠・背景なしの生ボタン、padding 0、角 0 | ghost 金型: padding 8px 20px、角 6px、1280 で最小高さ 36px。1 行目の高さは 51→54px（1280）、390 で 77→72px |
| 原文欄の検索行 | ラベルと入力欄が同じ行（auto + minmax(130px, 1fr) + ボタン 3） | R2-10: ラベル「原文検索」が入力欄の上の 1 段目（全幅）。2 段目は入力欄とボタン 3 つ |
| 原文欄の入力欄 | ブラウザ既定（枠 2px inset、角 0、高さ 19px） | 金型 sm（枠 1px、角 6px、1280 で高さ 約 30px、390 で 44px） |
| 原文欄のボタン（移動・前へ・次へ） | ブラウザ既定（幅約 31×25） | 金型 secondary sm（幅 48×28、390 で 48×44） |
| en 画面 | 日本語（登録・検索・ボタン・見出し・説明の全文言） | 英語。例外は固有名「商品マスタV2」のみ |
| ja 画面の文言 | — | 変化なし（B2） |

## R2-10 の入力欄 min-width（source-raw-pane.css :48）
`.source-search input { min-width: 0; }` は残した。理由: 要素セレクタなので金型の input（class comp-field__input--sm の input、ProductMasterDrawer/SourceRawPane の試験で class を確認）にもそのまま当たる。グリッド項目の input は自動最小幅が内容幅になりうるので、`minmax(0, 1fr)` の 1 列目を縮めるために必要と判断した。外して測る比較は行っていない（未確認）。

## Trans の escapeValue
i18n.ts は `escapeValue: false`。そのままだと react-i18next の Trans が値を HTML として解釈し、名前に `<i>` を含むと表示から消える（「A&B <i>Box」が「A&B Box」）。ProductMasterDrawer.tsx のキーワード追記の導入文の Trans に `tOptions={{ interpolation: { escapeValue: true } }}` と `shouldUnescape` を付けて、変更前と同じ表示に保った。試験で固定: frontend/src/features/tcg-analysis-review/ProductMasterDrawer.test.tsx の「en: renders the bold name without escaping a user supplied ampersand」（textContent と strong の中身が「A&B <i>Box」、i 要素が 0）。
