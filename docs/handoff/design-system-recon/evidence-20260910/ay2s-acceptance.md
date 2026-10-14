# AY-2s 受入表（設計 §4）

|基準|結果|根拠|
|---|---|---|
|6個が class `comp-field__input` を持ち、border/radius/height/font が金型値|OK（高さ 39.61 / ≤767px 44）|impl/diff.md 全18行で class=comp-field__input、border=1px solid rgb(226, 232, 240)、radius=6px、height 1280/1440=39.61・375=44（before 19・2px inset・radius 0）。font は impl/after.json の computed.font-size|
|幅が前と同じ（±0.5px）|OK|impl/diff.md width 列 全18行で前後同値（96/112/480、375 は 327）。C1 該当なし|
|全幅で doc scrollWidth==clientWidth、新たな負の left なし|OK|impl/diff.md doc 列 全行一致。負の left は before と同じ inventory-qty-min / price-min の -11.83（375）のみで新規なし|
|在庫フィルタ数量・価格入力→一覧 API のパラメータ前後一致|OK|impl/diff.md「API 呼出」inventory-filter 3幅とも 前4件/後4件/一致=True（4入力の fill で各1回、URL 同一）|
|rules/aliases 検索 Enter→検索 API 呼出前後一致|OK|impl/diff.md knowledge-aliases 3幅とも 前2件/後2件/一致=True（GET /super-admin/knowledge?q=abc、GET /super-admin/aliases?q=xyz。/conversations/stream は無関係なので除外）|
|対象2ファイルの生 `<input`（text/number）0 件|OK（checkbox 10件は対象外で残存）|impl/grep-input.txt・remaining-inputs.txt。残る `<input` は全て type="checkbox"|
|generate・tsc・lint・check:all・test:coverage(maxWorkers=1)・build・build-storybook 成功|OK|impl/q-*.txt。test:coverage 1回目は無関係の AllLegacyButtonOperationMigration.test.tsx がタイムアウト（1 failed）、--testTimeout=60000 で再実行し 93 files / 1069 tests 全通過（q-test-coverage.txt と q-test-coverage-t60.txt の両方を保存）|
|本番 JS に testid inventory-qty-min と comp-field__input の利用が反映|未実施（マージ・デプロイ後の確認項目）|-|

## 設計 想定分岐
- C1: 該当なし（inline width が勝ち、幅は前後同値）。
- C2: 該当なし（doc はみ出し悪化・新規の負の left なし）。
- C3: 375 の knowledge-aliases で兄弟（検索/新規作成/削除ボタン）との縦中心差が 39.5→52（悪化 12.5px）。1280/1440 は 0→-0.01。375 ではボタンが次行へ折り返す配置で、入力が 19→44px になり行高さ差が中心差に出たもの（input bottom 893.27、ボタン top 901.27、行間 8px は before と同じ）。同一行の整列ずれではない。設計の文言上は「1px 超の悪化」に該当するため設計者の判断を求める。
- C4: type=number は金型既定。値は文字列のまま（onChange 逐語）。
