# recon: 在庫表ページと詳細パネルのスマホ対応（現在地の一次情報）

> この文書は何か（1行）: PO 報告「在庫表ページとスライドして出る詳細パネルの両方がスマホでレスポンシブになっていない」を直す前に、**現物のコードで確かめた事実だけ**を置く場所。

**日付**: 2026-10-21
**ベース**: `origin/main` = `22f083083`（`release/inventory-mobile-baseline` worktree で確認）
**PO 報告（原文）**: 「見れるようになったがれすぽんしぶできていない、アプリの在庫表ページとスライドページ両方」／「受信箱のようにレスポンシブさせて欲しい。閲覧用ページは進んでいてレスポンシブが進んでいる」
**引用の方針**: 下の行番号は**すべてこの worktree の実ファイルを開いて確認**した。下請け調査の報告をそのまま写した行は1つも無い（実際に2件、報告の行番号が別の内容を指していたため破棄した。§7 に記録）。

## 1. 画面の枠（スマホ）

| 事実 | 引用 |
|---|---|
| スマホは `MobileShell`（ADR-140）。本文は `.mobile-content` に入る | `frontend/src/mobile-shell.css:1-6`（ファイル冒頭に ADR-140 PR-B と明記） |
| `.mobile-content` は `overflow-y: auto` だけを指定し、`overflow-x` を書いていない | `frontend/src/mobile-shell.css:22-26` |
| そのため CSS の規則で `overflow-x` は `visible` → **`auto` に計算される**＝この要素が**横スクロールを持つ**。はみ出しは `document` には現れず、この要素の内側に隠れる | 同上。既存 spec の冒頭コメントも同じ理解を書いている（`frontend/tests-e2e/inventory-table-layout.spec.ts:4-5`） |
| 上部のページ名バーは 2026-10-13 に削除済み（PO 指定）。現在地は下部タブの点灯で示す | `frontend/src/mobile-shell.css:15-18` |

## 2. 在庫表ページの上部操作（最有力の容疑者・ただし未測定）

| 事実 | 引用 |
|---|---|
| スマホのとき、操作台の左スロットに**5つ**を横一列に置く（検索・リセット・24時間・並び替え・詳細フィルタ） | `frontend/src/pages/inventory/InventoryToolbar.tsx:110-123` |
| 操作台 `.content-toolbar` は **`flex-wrap: nowrap`**。コメントに「切り詰めて改行させない（2段になるのを防ぐ）」と意図が明記されている | `frontend/src/components/ContentToolbar.css:4-15` |
| 左スロット `.content-toolbar__left` も `flex-wrap: nowrap` ＋ `min-width: 0` | `frontend/src/components/ContentToolbar.css:16-23` |
| 右端に `padding-right: var(--space-3)`、最低高さ `--field-h-md` | `frontend/src/components/ContentToolbar.css:10-12` |

**意味**: 360〜390px で5要素が1列に収まらない場合、折り返さずに**はみ出す**か、子が潰れる。どちらになるかは**実測していない**。

## 3. カード表示（スマホの一覧）

| 事実 | 引用 |
|---|---|
| カードの1行は `display: flex; justify-content: space-between` でラベルと値を左右に振る | `frontend/src/components/DataTable.css:312-317` |
| ラベル側は **`flex-shrink: 0`**＝縮まない | `frontend/src/components/DataTable.css:319-320` |
| 商品名などのセルは既定で `overflow-wrap: anywhere`（折り返す） | `frontend/src/features/inventory/inventoryColumns.css:3,9` |
| ただし **768px 以上**では `white-space: nowrap` に切り替わる（PC は1行で省略） | `frontend/src/features/inventory/inventoryColumns.css:15-26` |

**意味**: 長いラベルがあると値側だけが圧縮される。折り返しの指定はスマホ側に入っているため、商品名そのものは折り返る想定。**実際に何px はみ出しているかは未測定**。

## 4. スライドして出る詳細パネル

| 事実 | 引用 |
|---|---|
| 767px 以下でパネルは `width: 100%` | `frontend/src/components/Drawer.css:105-113` |
| パネル本文の内側余白は `padding: var(--space-5) var(--space-6)`（トークン・固定） | `frontend/src/components/Drawer.css:85-89` |
| パネルが開いているときだけ `--open` クラスが付く（同じ `data-testid` のドロワーが同一画面に複数あるため、測定時はこれで絞る必要がある） | `frontend/src/components/Drawer.tsx:131` |

## 5. 既にある検査が当てにならない理由（実測で確定済み）

| 事実 | 引用 |
|---|---|
| `frontend/tests-e2e/horizontal-overflow.spec.ts` は **`document.documentElement.scrollWidth <= window.innerWidth`** で測る＝`.mobile-content` の内側のはみ出しを**構造的に見逃す** | `frontend/tests-e2e/horizontal-overflow.spec.ts:24-27` |
| `frontend/tests-e2e/inventory-table-layout.spec.ts` は `.mobile-content` の `scrollWidth`/`clientWidth` を直接見ており測り方は正しい | `frontend/tests-e2e/inventory-table-layout.spec.ts:82-88` |
| しかし**この2本は CI で1本も走っていない**。`playwright` ジョブが停止中で、動いているのは3幅検査だけ、その対象は `frontend/tests-e2e/visual-language/` 配下の spec に限定 | `.github/workflows/e2e.yml:247`（`if: false # 一時停止 2026-06-01`）／`frontend/playwright.config.ts:60,64,69,74` |

## 6. お手本（受信箱）

| 事実 | 引用 |
|---|---|
| 受信箱は「測って記録する spec」と「合否を出す spec」を分けている | `frontend/tests-e2e/visual-language/inbox-baseline.spec.ts`／`frontend/tests-e2e/visual-language/inbox-single-column.spec.ts` |
| 合否 spec は「なぜ要るか」を冒頭に書き、この端末で chromium が動かないため CI（x86）で恒久検査する方針を明記している | `frontend/tests-e2e/visual-language/inbox-single-column.spec.ts:1-18` |
| 3幅は 390 / 768 / 1280。project 側が viewport を与える | `frontend/playwright.config.ts:62-76` |

## 7. 未確認（推測で埋めない）

- **実機の実寸**: ADB が未接続のため未測。ワイヤレスデバッグの待ち受けポートを 30000–65535 で走査して候補 1 件（35632）を得たが `adb connect` は `Connection refused`＝ペア設定が切れている可能性。復旧には PO からペア設定コードが必要。
- **はみ出しの有無と量**: この端末は `npx playwright install chromium` が `ubuntu26.04-arm64` 非対応で失敗するため、手元で測れない。
- **実機の CSS 幅**: 過去の記録では 360 CSS px。今回は未再測のため、測定 spec では **360 と 390 の両方**を測る。
- 破棄した引用2件（下請け調査の報告が実ファイルと一致しなかったもの）: 「`frontend/src/styles/mobile-shell.css:22-25`」＝そのパスにファイルは無い（実際は `frontend/src/mobile-shell.css`）／「`frontend/src/components/Drawer.tsx:88` が余白指定」＝実際はフォーカストラップのコードで、余白は `Drawer.css:85-89`。
