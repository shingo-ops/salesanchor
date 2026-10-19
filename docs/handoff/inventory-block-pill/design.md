# design: 最安・在庫最多を「塗りの角丸」にする（ADR-1014 改訂（4））

参照: recon（docs/handoff/inventory-block-pill/recon.md）、ADR-1014 改訂（3）、ADR-067（デザイントークン）、ADR-144（UI ガバナンス: 金型 Badge のトークンを共有し、生の色を書かない）、ADR-1015（区分 A）、前便 docs/handoff/inventory-block-frames/design.md

## 目的（PO の言葉）
#4524 の「細い線の枠」は PO の想定と違った。PO の想定は「バッジと同じ囲み方」「スプレッドシートのプルダウンのように囲って色付け」。最安の価格を薄い水色で塗った角丸、在庫最多の数量を薄い緑で塗った角丸で包む。文字は足さない。列はずらさない。

区分: A（見た目だけ。DB・API・並び・まとまりの規則は変えない）

## 変更前 → 変更後
| | 変更前（#4524） | 変更後 |
|---|---|---|
| 形 | 角 `--radius-sm`、内側の線 2px | 角 `--comp-badge-radius`（Badge と同じ丸ピル）、線なし |
| 最安 | 水色の線（`--comp-value-frame-cheapest`） | 塗り `--info-bg`、文字 `--info-text`（Badge soft info と同じ組） |
| 在庫最多 | 緑の線（`--comp-value-frame-most-stock`） | 塗り `--success-bg`、文字 `--success-text`（Badge soft success と同じ組） |
| 余白 | 全行 `--space-1px --space-1` | 全行 `--space-2px --space-2`（Badge sm と同じ）。印の有無で同じなので列はずれない |
| 文字の大きさ | セルの文字のまま | セルの文字のまま（変えない） |
| トークン | `--comp-value-frame-*` 2つ | 削除（使う所がなくなるため。新しいトークンは作らない） |

### Badge 部品そのものを使わない理由
Badge は `font-size: var(--font-xs)`（12px）と `line-height: 1` を持ち、価格・数量の数字が他の行より小さくなって列の中で揃わない。形と色の正本（トークン `--comp-badge-radius`・`--info-bg`/`--info-text`・`--success-bg`/`--success-text`・`--space-2px`/`--space-2`）を Badge と共有し、色の直書きも新トークンも作らない。

## 触るファイル（これ以外は触らない）
1. `frontend/src/features/inventory/inventoryColumns.css` の `.inventory-cell__value` 3規則を次に置き換える（コメントも差し替え）:
   ```css
   /* 価格・数量の値の入れ物。印の有無で幅を変えないため、全行で同じ余白を持つ（形と余白は金型 Badge sm と同じトークン。ADR-1014 改訂 2026-10-19（4）） */
   .inventory-cell__value {
     display: inline-block;
     padding: var(--space-2px) var(--space-2);
     border-radius: var(--comp-badge-radius);
   }
   /* 同じ商品・ステータス・状態のまとまりの最安（薄い水色の塗り）と在庫最多（薄い緑の塗り）。色の組は Badge soft info / success と同じ */
   .inventory-cell__value--cheapest {
     background: var(--info-bg);
     color: var(--info-text);
   }
   .inventory-cell__value--most-stock {
     background: var(--success-bg);
     color: var(--success-text);
   }
   ```
2. `frontend/src/tokens.css`: ライトの `--comp-value-frame-*` のコメント1行＋2行（:395-397）と直後の空行1行、ダークのコメント1行＋2行（:595-597）と直後の空行1行を削除する。他の行は触らない。
3. `frontend/src/features/inventory/blockBadges.tsx:1` の説明コメントの「水色の枠」「緑の枠」を「薄い水色の塗り」「薄い緑の塗り」に、「改訂 2026-10-19（3）」を「改訂 2026-10-19（4）」に直す（コメントだけ。コードは変えない）。
4. `docs/adr/ADR-1014-inventory-view-shows-distribution-rows.md` に「改訂 2026-10-19（4）」を足す（Opus が書く）。
5. `docs/adr/ADR-067-design-token-enforcement.md` の表「カラートークン（tokens.css — 在庫表の最安・在庫最多の枠 / ADR-1014）」（見出し・表・後ろの `---`）を削除する（Opus が書く）。`node scripts/generate-adr-index.js --check` を実行し、README に差分が出ないこと（exit 0）を記録する（生成対象はタイトル・ステータス・日付・関係だけで、今回の変更では README は変わらない）。
6. handoff: 本 recon.md・design.md。

触らない: BlockValue のコード・クラス名・testid・title、inventoryColumns.tsx・viewerColumns.tsx、試験ファイル、Badge.css・Badge.tsx、index.css、辞書、backend 一式、migrations、deploy.yml、scripts。

## 試験
試験はクラス名と testid を見ていて、それらは変えないので変更しない。CSS の中身を固める試験は既存にない（前便も同じ）。代わりに受入 F3・F4 で grep による静的確認をする。

## 代替案
- A: Badge 部品で数字を包む → 数字が 12px になり行ごとに大きさが揃わない。不採用。
- B: 線の枠を太く → PO の言葉（塗り）と違う。不採用。
- C（採用）: 既存の入れ物に Badge と同じトークンで塗りと角丸。

## リスクと対処
- 塗りの上の文字の読みやすさ: コントラストはライト info 4.01:1（通常文字の AA 4.5:1 未満）、ライト success 7.30:1、ダーク info 6.38:1、ダーク success 9.28:1。ライト info の組は既存の金型 Badge soft info と同じ組で、アプリ全体で既に使っている。本便は「Badge と同じ見た目」が PO の要望なので、この組をそのまま受け入れる（文字色だけ別トークンにすると Badge と見た目がずれ、SSOT が2つになる）。意味は `title`（「最安」）でも伝える。組そのものの改善は Badge 全体の課題として本便の範囲外。
- 余白が左右 4px→8px に増え、列が少し広がる可能性: 全行同じなので行の間でのずれは起きない。PC は DataTable の fitToWidth が表ごと収める（inventoryColumns.css のコメント）。PO 目視（F7）で確認する。
- 上下の余白が 1px→2px に増え、入れ物の高さが 2px 増える: 全行同じなので行の間の差は出ない。行の高さが変わって見づらくないかを PO 目視（F7）で確認する。
- 戻し方: 本 PR の revert。

## 受入条件
| 基準 | 検証方法 |
|---|---|
| F1 `git diff origin/main...HEAD --name-only` が「触るファイル」1〜6 と一致（7 ファイル: inventoryColumns.css・tokens.css・blockBadges.tsx・ADR-1014・ADR-067・handoff 2 ファイル）。`node scripts/generate-adr-index.js --check` が exit 0 | コマンド出力を保存 |
| F2 `git grep -n 'comp-value-frame' -- frontend` が0件 | コマンド出力 |
| F3 inventoryColumns.css の `.inventory-cell__value*` に `#` の色直書き・`box-shadow` が無く、`--comp-badge-radius`・`--info-bg`・`--info-text`・`--success-bg`・`--success-text`・`--space-2px`・`--space-2` を使う | `sed -n` で該当規則を表示して確認 |
| F4 vitest（inventoryColumns.test.tsx・viewerColumns.cells.test.tsx・viewerFilter.test.ts）が全部 pass、eslint・stylelint（あれば）・`npm run check:all` が exit 0 | ローカル実行の生出力を /tmp/CC報告ファイル/inventory-block-pill/impl/ に保存 |
| F5 CI 必須チェック全緑 | `gh pr checks` |
| F6 本番: マージコミットが成功した Deploy の head の祖先。`https://app.salesanchor.jp/` と `/viewer/` の配信 CSS に `.inventory-cell__value--cheapest{background:var(--info-bg)` 相当があり、`comp-value-frame` が0件 | curl ＋ grep（/tmp/CC報告ファイル/inventory-block-pill/prod/） |
| F7 PO が再読み込み後の画面で、最安が薄い水色の角丸、在庫最多が薄い緑の角丸で、列がずれておらず、行の高さ（入れ物が 2px 高くなる）も気にならないと答える | PO の回答 |

## 外部・過去事例の参照と我々への応用
- Google スプレッドシートのプルダウン（データの入力規則）の「チップ」表示: 選んだ値を薄い色で塗った角丸で包み、文字は濃い同系色。PO が直接名指しした見本で、本便はこの見た目を Badge のトークンで再現する。数値の実測は不要（見た目の合意を PO 目視で判定する）。
- 過去事例: #4521（バッジを値の右に置く→列がずれた）、#4524（細い線の枠→PO の想定と違った）。教訓は「見た目の言葉は形・塗り・文字の有無まで分解して PO に確認してから作る」。本便は分解した理解に PO の「y」を得てから着手した。

## 維持の仕組み
- 色と形はトークン経由のみ（ADR-067 の stylelint/check:all が直書きを止める）。
- 守り手: `frontend/package.json` の `check:all`（ADR-067 の自動チェック）、クラス名・testid を見る既存試験 `frontend/src/features/inventory/inventoryColumns.test.tsx`・`frontend/src/pages/viewer/viewerColumns.cells.test.tsx`。

## 審査記録
- 1回目（Reviewer opus）: REVISE。直す点4つ: F1 の README 条件、recon の出典行、ライト info のコントラスト 4.01:1 の扱い、高さ 2px 増の明記。全て反映済み。
- 2回目（Reviewer opus）: APPROVE。
