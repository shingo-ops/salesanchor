# design: 在庫のスマホ対応 — 便0「まず数値で現在地を押さえる」

> この文書は何か（1行）: 在庫表ページとスライドして出る詳細パネルが、スマホ幅で**どこが何px はみ出しているか**を機械で測り、CI に残す便の設計。**この便では見た目を1pxも変えない。**

**日付**: 2026-10-21
**recon**: `docs/handoff/inventory-mobile-responsive/recon.md`
**対象 ADR**: ADR-140（スマホは下部タブの MobileShell）／ADR-144（UI 金型ガバナンス）／ADR-067（色・余白はデザイントークン参照。hex/px のマジックナンバー禁止）
**区分**: B-3（テストと、正本でない `docs/` だけを触る。ADR-1015 §15）。したがって KGI・設計の PO 承認は不要、Draft にしない。
**PO 指示（原文）**: 「受信箱のようにレスポンシブさせて欲しい」「推測は禁止して事実確認を怠らずに確実性を重視して…現状把握の粒度が細かく精度が高いエビデンスを確立して安全に進めてくれ」「配線とdBのssotは遵守して…分散させることは禁止」「デザイントークンとデザインシステムを遵守して、金型登録のないハードコードを禁止する」

## ① なぜ「測るだけ」の便を先に出すのか

recon §5 で確定したとおり、**在庫のはみ出しを見張る検査は現在1本も動いていない**。
この状態で見た目を直すと、

- 直ったかどうかを人の目でしか言えない（PO の実機確認に毎回依存する）
- 直した後に別便が壊しても誰も気づかない

となる。受信箱は先に「測って記録する spec」を置き、その数値を根拠に直した（recon §6）。同じ順番を踏む。

## ② KGI（PO が判定できる粒度）

| # | 確かめること | ○× の基準 |
|---|---|---|
| K1 | 在庫表ページのスマホ幅で「**何が何px はみ出しているか**」が一覧で読める | CI のログに要素ごとの超過 px が出る |
| K2 | 詳細パネル（スライドして出る方）についても同じ一覧が読める | 同上 |
| K3 | 実機に近い幅で測れている | 360px と 390px の両方の数値が出る |
| K4 | この便で**見た目が変わっていない** | `frontend/src` の差分が 0 行 |

## ③ KPI（機械で測る値）

| 指標 | 測り方 | 記録先 |
|---|---|---|
| 枠のはみ出し | `.mobile-content` の `scrollWidth - clientWidth` | CI ログ（JSON 1行） |
| document のはみ出し | `documentElement.scrollWidth - innerWidth` | 同上 |
| はみ出している要素の全件 | 枠の右端を越える要素を走査し、`tagName` / `className` / `data-testid` / `bounds` / 超過 px を超過の大きい順に最大40件 | 同上 |
| 上部操作台 | `.content-toolbar__left` の子要素それぞれの `bounds`、同一行かどうか（`y` の一致）、合計幅と親の幅 | 同上 |
| カード | 枚数・1枚目の高さ・1画面に入る枚数 | 同上 |
| 詳細パネル | 開いた後の `bounds`、パネル内で最も幅の広い要素、パネル内のはみ出し要素一覧、タブ列の `bounds` | 同上 |

## ④ 設計（How）

### 4-1. 置き場は `visual-language/`（CI で走る唯一の場所）

- 新規 `frontend/tests-e2e/visual-language/inventory-mobile-baseline.spec.ts`。
- 根拠: recon §5。`tests-e2e/` 直下に置くと CI で走らない（PR #4602 で実測済み）。

### 4-2. 幅は spec 側で与える（360 と 390）

- project の幅（390/768/1280）は `page.setViewportSize()` で上書きできる（PR #4602 で実証）。
- **360 を測る理由**: 過去の実機記録が 360 CSS px で、CI の既定 390 より 30px 狭い。390 で収まって 360 で溢れる可能性があるため両方測る。
- 768/1280 は本便では測らない（PC 側は今回の対象外。recon §3 のとおり PC は `nowrap` で意図的に別挙動）。

### 4-3. モックは1か所に置く（SSOT。PO 指示「分散させることは禁止」）

- 在庫ページの API モックは現在 `frontend/tests-e2e/visual-language/inventory-raw-text-mobile.spec.ts` の中にある。
- これを **`frontend/tests-e2e/visual-language/inventory-helpers.ts` に移し**、既存 spec と新規 spec の**両方がそこから読む**形にする（受信箱が `inbox-helpers.ts` でやっている形と同じ）。
- 同じモックを2か所に書き写すことはしない。

### 4-4. 「測るだけ」だが、黙って何も測らない事故は防ぐ

- 合否は出さない（この便は記録用）。ただし**測定が成立したことだけは assert する**: 一覧の1行目が見える／カードが1枚以上ある／原文ボタンで開いたパネルが `--open` で1件に絞れる。
- これが無いと「0件のはみ出し」と「測れていない」が区別できない。

### 4-5. 触らないもの

- `frontend/src` 配下（**1行も変えない**）。
- `playwright.config.ts`・`.github/workflows/`（project や CI の配線は変えない。幅は spec 側で与えるため不要）。
- 既存 `frontend/tests-e2e/horizontal-overflow.spec.ts`・`frontend/tests-e2e/inventory-table-layout.spec.ts`（CI で走らない件は別便の宿題＝C4 のまま）。
- DB・バックエンド・配線（この便は触らない）。

## ⑤ Acceptance Criteria

| # | 基準 | 検証方法 |
|---|---|---|
| A1 | 新規 spec が3つの project すべてで収集される | `E2E_NO_WEBSERVER=1 npx playwright test --list --project=vl-mobile-390` に出る |
| A2 | CI の「画面検査（内部）」が緑 | GitHub Actions の実行結果 |
| A3 | CI ログに 360px の測定 JSON が出る | ログに `INVENTORY_BASELINE w=360` を含む行がある |
| A4 | CI ログに 390px の測定 JSON が出る | ログに `INVENTORY_BASELINE w=390` を含む行がある |
| A5 | 詳細パネルの測定 JSON が出る | ログに `INVENTORY_DRAWER_BASELINE` を含む行がある |
| A6 | `frontend/src` の差分が 0 行 | `git diff --stat origin/main...HEAD -- frontend/src` が空 |
| A7 | 既存 spec（原文ボタン A1〜A4・A6）が引き続き緑 | CI の同じジョブ |
| A8 | 型検査が通る | `cd frontend && npx tsc --noEmit` |
| A9 | 手元検査が通る | `cd frontend && npm run check:all` |

## ⑥ 触るファイル

| ファイル | 変更 |
|---|---|
| `frontend/tests-e2e/visual-language/inventory-mobile-baseline.spec.ts` | 新規（測定のみ） |
| `frontend/tests-e2e/visual-language/inventory-helpers.ts` | 新規（モックを1か所に集約） |
| `frontend/tests-e2e/visual-language/inventory-raw-text-mobile.spec.ts` | モックをヘルパー参照に差し替え（検査内容は不変） |
| `docs/handoff/inventory-mobile-responsive/recon.md`・`design.md`・`review-opus.md` | 新規 |
| `.claude-pipeline/active-work.d/release-inventory-mobile-baseline.md` | 台帳 |

## ⑦ 戻し方

この PR を revert するだけ。`frontend/src` を触らないため、アプリの挙動には戻す対象が無い。

## ⑧ 削除するファイル

`frontend/tests-e2e/visual-language/inventory-raw-text-mobile.spec.ts`（モック部分を削ってヘルパー参照に差し替えるため、行の削除がある）。ファイルそのものの削除は無い。

## ⑨ 外部・過去事例の参照と我々への応用

| 事例 | 我々への応用 |
|---|---|
| 受信箱の2段構え（`inbox-baseline.spec.ts`＝測って記録／`inbox-single-column.spec.ts`＝合否） | 同じ順番を踏む。先に数値、次に合否。合否の閾値を推測で決めない |
| PR #4602 の実測（`tests-e2e/` 直下は CI で走らない） | 置き場を `visual-language/` にする。`--list` で収集を目視確認する手順まで含める |
| PR #4602 の strict mode violation（`supplier-drawer` が2要素に一致） | パネルは `--open` で絞る。測定でも同じ絞り込みを使う |
| 受信箱の `inbox-helpers.ts` | モックの置き場をヘルパー1本にし、spec 間で書き写さない |

## ⑩ 弊害・トレードオフ

- CI の3幅ジョブに9テスト（3幅×3）ぶんの時間が増える。測定は軽い DOM 走査のみで、既存の 2m49s に対して数秒の増加見込み（**実測は CI 初回で確認する**）。
- 360px は project の幅ではなく spec 側の上書きで測るため、「project の幅＝実機の幅」という読み方はできなくなる。spec 冒頭にその理由を書いて誤解を防ぐ。

## ⑪ 維持の仕組み

守り手: `frontend/tests-e2e/visual-language/inventory-mobile-baseline.spec.ts`（この便の測定本体。CI の「画面検査（内部）」ジョブで毎 PR 走る）

| 守ること | 関所 | 外すと |
|---|---|---|
| 在庫のスマホ幅の数値が取れ続ける | 上記 spec（CI の3幅ジョブ） | 赤（測定の assert が落ちる） |
| 原文ボタンの A1〜A4・A6 | `frontend/tests-e2e/visual-language/inventory-raw-text-mobile.spec.ts` | 赤 |
| モックが1か所であること | `frontend/tests-e2e/visual-language/inventory-helpers.ts` を2 spec が参照 | 書き写しが増えても赤にはならない（人のレビューで見る） |

## ⑫ 継続（この便の後）

| # | 項目 | 状態 |
|---|---|---|
| C1 | 便1: 測った数値をもとに「上部操作台のスマホ版」を設計・実装（受信箱の形に寄せる） | 本便の数値が出てから着手 |
| C2 | 便2: カード表示のラベル/値の幅配分（`flex-shrink: 0` のラベル） | 同上 |
| C3 | 便3: 詳細パネル内の折り返しと余白 | 同上 |
| C4 | 合否を出す spec（受信箱の `inbox-single-column.spec.ts` 相当）を追加し、はみ出し0を恒久検査にする | 便1〜3 の後。閾値は実測値から決める |
| C5 | `tests-e2e/` 直下の spec 群が CI で走っていない問題（`e2e.yml:247` の `if: false`） | 別便（#4602 の design ⑫ C4 と同じ宿題） |
| C6 | 実機（SC-51G）での実測。ADB のペア設定が切れているため PO からペア設定コードが必要 | PO 依頼中 |

## ⑬ 便0 の実測結果（2026-10-23・CI run 39876238895）

> CI のログは保存期限で消えるため、便1以降の設計根拠として**数値をここに固定**する。
> 取得元は `frontend/tests-e2e/visual-language/inventory-mobile-baseline.spec.ts` が
> 出力する3種のマーカー（`INVENTORY_BASELINE` / `INVENTORY_DRAWER_BASELINE` /
> `INVENTORY_DRAWER_TABS_BASELINE`）。受け入れ基準 A1〜A9 はすべて満たした。

### 13-1. 横スクロールは出ていない（＝既存の検査では捕まらない）

| 測った対象 | 360px | 390px |
|---|---|---|
| `document` の `scrollWidth - innerWidth` | **0** | **0** |
| `.mobile-content` の `scrollWidth - clientWidth` | **0** | **0** |

`frontend/tests-e2e/horizontal-overflow.spec.ts` の測り方（`document` のはみ出し）では
在庫画面の問題は**原理的に検出できない**ことが数値で確定した。C4（合否 spec）は
`document` ではなく**要素単位の超過**を見る必要がある。

### 13-2. 本体の問題は上部操作台（`.content-toolbar__left`）

子5件が**全て同一行**（`sameRowAsFirst: true`・`y=78`・`h=44`）に並び、右端は **657px**。
親枠は 360px 時 **312px**、390px 時 **342px**。

| 子要素（`data-testid`） | x | w | 右端 |
|---|---|---|---|
| `inventory-search` | 24 | 212 | 236 |
| `inventory-reset-sort` | 248 | 74 | 322 |
| `inventory-fresh-toggle` | 334 | 87 | **421** |
| `inventory-sort-menu` | 433 | 114 | **547** |
| `inventory-filter-toggle` | 559 | 98 | **657** |

→ **新着・並び替え・絞り込みの3つはスマホ幅で画面外**（360/390 のどちらでも到達不能）。
枠のはみ出しが 0 と出るのは、超過が内側のスクロール枠に吸われているため。
C1（上部操作台の便）の設計はこの5件の配置を対象にする。

### 13-3. カードと文字

| 項目 | 値（360px） |
|---|---|
| カード枚数 | 5 |
| 1枚目の高さ | 308px |
| 1画面に入る枚数 | 2 |
| ラベルの文字サイズ | 12px |
| 値の文字サイズ | 13.6px |

### 13-4. 詳細パネル（便1 の成果物）は 360px で破綻していない

- パネルの `overflow` は **0**、パネル内のはみ出し要素は **0件**（原文1件・原文3件の両方）。
- 原文本文は `white-space: pre-wrap` / `overflow-wrap: anywhere` で折り返せている。
- ただし**タブ列（原文2件以上で出る）のタブは 68×36px** ＝ タップ目標 44px に**高さが8px足りない**。
  C3（詳細パネルの便）で扱う論点として確定。

### 13-5. 便2以降の作り手が踏む落とし穴（実測で判明）

- **閉じているドロワーは必ず「はみ出し要素」一覧に載る**（`supplier-drawer` が x=360/390 に駐車）。
  C4 で合否 spec を作るときは `.comp-drawer-panel--open` で絞らないと常に赤になる。
- 作業端末（arm64 / ubuntu 26.04）では Playwright のブラウザが入らない
  （`Playwright does not support chromium on ubuntu26.04-arm64`）。
  手元で取れるのは `--list`・`npx tsc --noEmit`・`npm run check:all` まで。
  **e2e の結果は CI ログだけが一次情報。**
