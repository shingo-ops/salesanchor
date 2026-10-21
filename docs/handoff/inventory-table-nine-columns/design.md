# Phase 3 設計 — 在庫表を9列にして折り返しをなくす

**対象ADR**: ADR-144、ADR-093、ADR-1014、ADR-027  
**recon**: docs/handoff/inventory-table-nine-columns/recon.md  
**日付**: 2026-10-17  
**担当**: Planner（Opus）。実装は Sonnet  
**状態**: PO 実装承認済み（2026-10-17「y、テストとしてどんな画面になるか見せてほしい」）。区分 B（画面のみ・危険パスなし）

---

## 目的と変化（PO の言葉に対応）

- 在庫表（`frontend/src/pages/inventory/InventoryPage.tsx`、PC 幅）の列を次の9列・この順にする: 型番、タイトル、状態、単価、数量、備考、発送、仕入元、発売日
- 形態・在庫・予約の列と、左端のチェック欄を外す
- どのセルも折り返さない。タイトル列は日本語名1行＋英語名1行のまま。はみ出す分は既存の fitToWidth（表全体を縮めて収める・GAS と同じ計算）で収める

## 対象外（触らない）

- `frontend/src/components/DataTable.tsx` / `frontend/src/components/DataTable.css`（金型本体）
- 767px 以下のカード表示（mobileCards）の見た目
- 詳細フィルタの形態条件（`frontend/src/pages/inventory/InventoryFilterPanel.tsx:222`）
- バックエンド・API・保存済みの列設定（hidden_columns に unit/offerType が残っても無視される）
- 閲覧画面（viewer）・GAS 在庫一覧
- 列データ（unit, offer_type）そのもの

---

## 実装カード（Sonnet 用）

1. `frontend/src/features/inventory/inventoryColumns.tsx`
   - `unit` と `offer_type` の列定義を配列から削除する（型 InventoryRow の項目は残す）
   - 並びを mark → name → condition → unit_price → quantity → note → ship → supplier → release_date にする
   - 使われなくなった import・i18n 参照があれば消す。`frontend/src/locales/ja.json`/`frontend/src/locales/en.json` のキーは消さない（形態は絞り込みで使う）
2. `frontend/src/features/inventory/inventoryColumns.css`
   - `.inventory-cell__title` と `.inventory-cell__sub` の `overflow-wrap: anywhere` を、PC 幅（既存の breakpoint の書き方に合わせる。768px 以上）で `white-space: nowrap` にする。767px 以下は今の折り返しを残す
   - タイトル以外の列のセルも PC 幅で折り返さないこと。DataTable に列ごとの className 等の口があればそれを使い、無ければ inventoryColumns.tsx の renderCell が返す要素にこの CSS のクラスを付けて nowrap にする。色・寸法の直値は書かない（ADR-067/144）
3. `frontend/src/pages/inventory/InventoryPage.tsx`
   - DataTable の `selectable` / `selectedKeys` / `onSelectChange` を外す
   - 使われなくなる selectedIds の state と preselectedInventoryIds の初期選択処理を消す（送り元は無い。recon 不明点2）
   - HIDEABLE_COLUMNS から unit と offerType を外す（列の表示切替のチェックからも消える）
4. テストを新しい形に合わせる
   - `frontend/src/features/inventory/inventoryColumns.test.tsx`（列順）
   - `frontend/src/pages/inventory/InventoryPage.tablelayout.test.tsx`（thead の順。チェック欄が無くなるので slice(1) を外す）
   - `frontend/src/pages/inventory/InventoryPage.rowdrawer.test.tsx` の F3（行チェック）を削除し、代わりに「チェック欄が無い」ことの試験を1件足す
   - `frontend/src/pages/viewer/viewerColumns.parity.test.tsx` は失敗しなければ触らない
5. 画面の試し撮り（PO 依頼「どんな画面になるか見せてほしい」）
   - API をモックした Playwright（既存 `frontend/tests-e2e/inventory-table-layout.spec.ts` の仕組み）で、長い商品名（日本語40字以上・英語60字以上）を含む10行のデータを使い、幅1440px で変更前（origin/main）と変更後を撮る
   - 保存先 /tmp/CC報告ファイル/inventory-cols/before-1440.png, after-1440.png（あれば 1280px も）
   - 撮影用の一時ファイルはコミットしない

想定分岐:
- DataTable に td の白抜き指定口が無い → 2 の後段（renderCell の要素にクラス）で対応。金型は変えない。金型の変更が必要になったら停止して報告
- 既存テストが本件以外の理由で落ちる → 直さず停止して報告
- i18n のキーが不要になっても消さない

---

## 外部・過去事例の参照と我々への応用

- 過去事例: GAS 在庫一覧は折り返さず表全体を縮めて収めている（`frontend/src/constants/tableFit.ts:3` に同じ値を移植済み）→ 我々への応用: 同じ縮小の仕組み（fitToWidth）をそのまま使い、折り返しを止めるだけにする
- 外部事例: 該当なし：既存の縮小の仕組みとデザイン金型の範囲で済み、新しい技術選択がないため

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| PC 幅の見出しが 型番・タイトル・状態・単価・数量・備考・発送・仕入元・発売日 の9つでこの順 | `frontend/src/pages/inventory/InventoryPage.tablelayout.test.tsx`（vitest）と after-1440.png の目視 |
| 左端のチェック欄が無い | `frontend/src/pages/inventory/InventoryPage.rowdrawer.test.tsx` の新しい試験 |
| 長い商品名でも各行が日本語名1行＋英語名1行で、他のセルも折り返さない | after-1440.png の目視（PO）。Playwright で各 td の高さが行高の範囲にあることを確認 |
| 横スクロールが出ず表が枠に収まる | Playwright で表ラッパーの scrollWidth <= clientWidth |
| 767px 以下のカード表示が変わらない | 既存の vitest / e2e が通る |
| i18n・デザイントークン違反なし | CI（i18n チェック・ADR-067 チェック） |

---

## 技術 How・KPI

- KPI: 試し撮りデータ10行で、折り返して3行以上になる行が 0 行（変更前の行数も記録して比べる）
- 技術選択: 既存の fitToWidth と CSS の nowrap（理由: 金型と GAS の計算を流用でき、新しい部品が要らない）

---

## 弊害・トレードオフ

- 長い商品名があると表全体の文字が小さくなる（縮小の下限なし）→ 対策: PO が試し撮りで縮み具合を確認してから本番に出す
- 列の表示切替から形態・在庫・予約が消える → 保存済み設定は無視されるだけで、エラーにはならない（実装時に試験で確認）

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | 実装カード 1〜4 | Sonnet |
| 2 | 試し撮り（カード 5） | Sonnet |
| 3 | 差分・試験・画像の審査 | Opus |
| 4 | PO に画像を見せて確認 | Opus |
| 5 | PR・CI・マージ・本番反映の観測 | Opus |

---

## 継続

- 完了後の監視: 本番反映後に PO が実画面で折り返しと縮み具合を確認
- 次フェーズへの引き継ぎ: GAS 在庫一覧・閲覧画面に同じ変更を入れるかは PO 判断（今回は対象外）

---

## Opus 審査

APPROVE（2026-10-17）。根拠: recon の不明点1〜4は解消済み、変更は在庫表の3ファイルと試験に限られ、金型本体・API・DB に触らない。未解決: なし（縮み具合は試し撮りで PO が確認）。

---

## 追補1（2026-10-17、PO 回答を受けて）

PO の回答（原文）:
- 「備考も発送も折り返さない」→ 全列1行・fitToWidth で縮める形で確定
- 閲覧ページも同じ形にそろえるか →「y」
- 「在庫予約の列だが左端に移動、在庫は青色、予約はオレンジ色の文字色にしてわかりやすく出来るか？」

調査結果（/tmp/CC報告ファイル/inventory-cols/ と Sonnet 報告）:
- 青の文字色トークンは既存 `--info-text`（`frontend/src/index.css:110`、ダーク :299）
- オレンジの文字色トークンは無い。`--warning`（#d97706）は solid 用で文字色用と書かれていない。白地とのコントラストは WCAG AA（4.5:1）に届かない値（Tailwind amber-600 相当で約 3.2:1）
- 閲覧ページの列は `frontend/src/pages/viewer/viewerColumns.tsx` の別実装。`frontend/src/pages/viewer/viewerColumns.parity.test.tsx` がアプリとのずれを縛る

Opus の設計判断:
1. 列の並び（在庫表・閲覧ページ共通）: 在庫・予約 → 型番 → タイトル → 状態 → 単価 → 数量 → 備考 → 発送 → 仕入元 → 発売日（10列）。形態とチェック欄は無し
2. 在庫・予約の表示: Badge をやめて文字色だけにする
   - 在庫: `--info-text`（既存）
   - 予約: 新しいトークン `--offer-preorder-text` を、`--info-text` と同じ場所・同じ書き方（ライト・ダーク・force-dark の全て）で追加する。ライトはオレンジで白地に 4.5:1 以上、ダークは暗い地に 4.5:1 以上の値を選び、値とコントラスト比の計算を報告に残す
   - 在庫にも意味の名前を付けるため `--offer-instock-text: var(--info-text)` を同じ場所に追加し、列の CSS はこの2つだけを参照する
   - offer_type が null のとき（status の生文字列）と発送時期の副行は、今の出し方のまま（色なし）
3. 固定列（stickyLeft）は左端の在庫・予約に付け替え、タイトルから外す（2列目の固定による重なりを避ける。金型は変えない）
4. スマホのカード表示は今のまま（在庫・予約は mobileHidden のまま）
5. 閲覧ページも同じ10列・同じ順・全部1行（PC 幅）・同じ色。見出しの i18n は閲覧ページの既存キー（`viewer.col.offerType`）のまま
6. parity 試験は「アプリと閲覧ページが同じ10列・同じ順」を確かめる形に直す。`frontend/src/pages/viewer/viewerColumns.cells.test.tsx` の在庫・予約セルの試験を新しい表示（Badge なし・色クラス）に合わせる

受け入れ基準（追加分）:

| 基準 | 検証方法 |
|------|---------|
| 在庫表・閲覧ページとも左端が在庫・予約で、10列がこの順 | vitest（tablelayout・parity）と試し撮り |
| 在庫は青、予約はオレンジの文字で、どちらもトークン参照 | CI の ADR-067 チェック、`frontend/src/pages/viewer/viewerColumns.cells.test.tsx`、試し撮りの目視 |
| 予約のオレンジが白地で 4.5:1 以上 | 報告に値とコントラスト比の計算を残す |
| 閲覧ページも全部1行で枠に収まる | 試し撮り（閲覧ページ 1440px） |

### 追補1 実装メモ（Sonnet）
- 在庫・予約の列は常時表示（hideId なし）。保存済み hidden_columns の offerType は無視される
- `--offer-preorder-text` ライト #b45309（白地 5.02:1）／ダーク #fb923c（--bg-surface 6.46:1）。計算は /tmp/CC報告ファイル/inventory-cols/contrast.txt

---

## 維持の仕組み

- 列の並び・stickyLeft・mobileHidden のアプリと閲覧ページのずれは `frontend/src/pages/viewer/viewerColumns.parity.test.tsx`（vitest・CI）が止める
- 在庫表の見出しの順とチェック欄なしは `frontend/src/pages/inventory/InventoryPage.tablelayout.test.tsx` と `frontend/src/pages/inventory/InventoryPage.rowdrawer.test.tsx` が止める
- 文字色のトークン直値の混入は CI の ADR-067 チェック、ライト／ダークの定義漏れはダークモード変数パリティ検査が止める

---

## 追補2（2026-10-17、CI 指摘を受けて）

- CI `scripts/check-design-token-ratchet.sh` が `frontend/src/index.css` の hex 増加（171→173）で失敗した。この検査は `frontend/src/tokens.css` を対象外にしており、予定表の色（`--cal-*`）が tokens.css の `:root` と `:root.force-dark` に hex で定義されている前例がある
- Opus の判断: `--offer-instock-text` と `--offer-preorder-text` を index.css から tokens.css の同じ並び（ライト＝Schedule category colors の直後、ダーク＝`:root.force-dark` の --cal-holiday の後）へ移す。値は変えない。index.css は origin/main と同じに戻す
- 確認: ラチェット PASS・`npm run check:dark-parity` PASS・tsc PASS・vitest 16 files / 121 tests PASS（/tmp/CC報告ファイル/inventory-cols/fix1-*.txt）

---

## 追補3（2026-10-17、PO 指示「在庫・予約→ヘッダー名をステータスに変更」）

- 在庫表・閲覧ページの左端の列の見出しを「ステータス」（en: Status）にする。中身（在庫=青・予約=オレンジ）は変えない
- i18n の扱い: 在庫表は新しいキー inventory.col.status を追加（inventory.col.offerType は絞り込み欄の見出し・列の表示切替でも使うため値を変えない）、閲覧ページは viewer.col.offerType が列の見出しだけで使われているため既存キーの値を変更（理由: 調査 /tmp/CC報告ファイル/inventory-status-header/recon.txt）
- あわせて frontend/src/features/inventory/inventoryColumns.css のコメントの誤記（index.css → tokens.css）を直す（#4480 Reviewer の軽微指摘）
