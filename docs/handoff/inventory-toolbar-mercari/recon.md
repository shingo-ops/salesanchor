# recon: 在庫表（/inventory）スマホの上部操作台

> この文書は何か（1行）: アプリの在庫表ページのスマホ表示で、上部の操作がいくつも画面の外に出ていて
> 指が届かない。その現在地を**本番の実機で測った値**でそろえ、直し方の材料にする。

**対象**: `frontend/src/pages/inventory/`（アプリ本体）。
**閲覧ページ `frontend/src/pages/viewer/` とは別コード**（ADR-1019）。取り違えると調査が無駄になる。
**前の便の設計書**: `docs/handoff/inventory-mobile-responsive/design.md`（便0＝計測 spec・PR #4612）。

## 1. 本番の実機で測った現在地（2026-10-28 22:39 JST・一次情報）

端末 SC-51G（1080x2340・dpr=3 ＝ CSS 幅 **360px**）の Chrome で本番
`https://app.salesanchor.jp/inventory` を開き、DevTools Protocol で `getBoundingClientRect()` を直読みした。
配布物のビルド名は main-Db5ehglb（ビルド後の JS）。

**上部操作台 `.content-toolbar__left` の子5件は全部同じ行に並ぶ。親の枠は x=24〜312（幅288）なのに、
子は x=654 まで伸びている。**

| 子要素（`data-testid`） | x | 幅 | 右端 | 画面内か |
|---|---|---|---|---|
| `inventory-search` | 24 | 224 | 248 | ○ |
| `inventory-reset-sort` | 260 | 72 | 331 | △（右端が画面の外） |
| `inventory-fresh-toggle` | 343 | 85 | 429 | **×** |
| `inventory-sort-menu` | 441 | 108 | 548 | **×** |
| `inventory-filter-toggle` | 560 | 94 | 654 | **×** |

- 画面幅 **360px**。**「24時間以内」「並び替え」「詳細フィルタ」の3つは完全に画面の外**で、指が届かない。
- **横スクロールは出ていない**（`document.documentElement.scrollWidth - clientHeight` 相当の超過が **0**）。
  つまり**滑らせても出てこない**。隠れたまま。
- 1行の高さは 44px（子5件とも h=44）。

**便0（2026-10-23・CI run 39876238895）で測った値と一致**（当時の右端 657px）。
`docs/handoff/inventory-mobile-responsive/design.md` §⑬ に記録済みの状態が**今も続いている**。

## 2. 同じ不具合を閲覧ページでどう直したか（写す元）

閲覧ページは同じ「上部に操作が多すぎる」問題を、**便3→便4→便5** の3便で次の形に変えて解決済み（本番稼働中）。

| 便 | 変えたこと | 結果 |
|---|---|---|
| 便3（PR #4752） | 「24時間以内」を**絞り込みパネルの中**へ移した | 上部 236→192px |
| 便4（PR #4764） | スマホだけ題の帯を消した | 上部 192→124px |
| 便5（PR #4759） | シリーズ／並び替え／絞り込みを**枠なしの文字ボタン**にし、押すと**右からパネル**が出る形にした | 幅を使わなくなった |

**PO はこの形を「お手本（メルカリ）どおり」として承認済み**で、2026-10-28 に実機でも確認した
（`docs/handoff/viewer-filter-choices-mercari/design.md` の K1〜K7）。

## 3. 今の在庫表の作り（コードの現在地）

| 対象 | 場所 |
|---|---|
| 上部操作台の組み立て | `frontend/src/pages/inventory/InventoryToolbar.tsx` |
| 操作台の金型 | `frontend/src/components/ContentToolbar.tsx` ／ `frontend/src/components/ContentToolbar.css` |
| 絞り込みパネル | `frontend/src/pages/inventory/InventoryFilterPanel.tsx` |
| ページ本体（状態の持ち主） | `frontend/src/pages/inventory/InventoryPage.tsx` |
| スマホ判定 | `frontend/src/hooks/useIsMobile.ts` |
| 計測 spec（CI 常設） | `frontend/tests-e2e/visual-language/inventory-mobile-baseline.spec.ts` |

**重要**: 操作台の金型 `ContentToolbar` は**すでに2段の形を持っている**
（`bottomLeft` / `bottomRight` を渡したときだけ2段になる。`frontend/src/components/ContentToolbar.tsx`）。
PC はその2段を使っており、**スマホだけが1段に5つ詰め込んでいる**
（`frontend/src/pages/inventory/InventoryToolbar.tsx` の `if (p.isMobile)` の分岐）。
つまり**金型の新設は要らない**。

## 4. 測り方（再現手順）

```bash
adb forward tcp:9222 localabstract:chrome_devtools_remote
adb shell am start -a android.intent.action.VIEW -d "https://app.salesanchor.jp/inventory"
# /json/list で page id を取り、ws://127.0.0.1:9222/devtools/page/<id> へ繋いで Runtime.evaluate
```

注意（`salesanchor-device-devtools` の記録どおり）:
- `webSocketDebuggerUrl` はホストが欠けていることがあるので ws URL は自分で組み立てる。
- **背面タブでは CSS の transition が走らない**ので、位置（x）を測るときは対象タブを前面に出す。
