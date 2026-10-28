# recon: 打つと出る候補（便12b）

> この文書は何か（1行）: 閲覧ページ（/viewer/）の検索画面で、**打っている間に候補を出す**ための現物調査。
> 便12a で「押すと検索画面→確定して絞る→語は札」までは入った。本便はその画面の中身を「履歴→候補」に切り替える。

**土台**: `release/viewer-search-suggestions`（`origin/main` = ff6787294＝便12a #4828 を含む）／調査日 2026-10-28
**対象**: `frontend/src/pages/viewer/`（アプリの `/inventory` とは別コード。ADR-1019）

## 1. お手本の実測（実機 ADB・1手ずつ）

便12a の recon §1b に続く測定（2026-10-28 01:4x〜）。`uiautomator dump` と `dumpsys input_method` を機械で読む。

| # | 操作 | 測れた結果 |
|---|---|---|
| F1 | 検索画面で「poke」と打つ | **候補（`search_hint_item`）が6件**。行は **68.7dp・全幅（x=0..360dp）**・文字は**左から64dp**・主の文字は **17.7dp箱**。見出し（`section_title`）は**無い** |
| F2 | 候補の行の**右端**（x=340dp 付近）を押す | **検索が走って結果画面へ**（キーボードは閉じ、語が札になる）。**右端の「→」は独立した押せる部品ではない**（dump に clickable な子が無く、行全体が clickable=true） |
| F3 | 札のある状態で打ち直す | 候補は打った語に合わせて更新される（10件） |
| F7 | **入力を空にして確定（Enter）** | **何も起きない**（検索は走らず、画面もそのまま・キーボードも出たまま） |
| F8 | **語を確定した結果画面で検索バーを押して開き直す**（2026-10-28 09:5x に追加測定） | **入力欄に語（ポケモン）が残ったまま候補（`search_hint_item`）が10件**。**「検索履歴」の見出し（`section_title`）は出ない**。行は 206px＝**68.7dp**・文字は左から **192px＝64dp**・`mInputShown=true` |

**F8 の測り方**: 履歴にすでにある語（ポケモン）の行を押して検索を走らせたので、**相手の履歴は1件も増えていない**
（測定前後の dump が一致＝ポケモン／iphone／iphone+IRWIN, AEG／garaxy s25 の順のまま）。

**F8 が設計を決める**: うちの `openSearchScreen()` は `setDraft(appliedQuery)` なので、開き直すと draft が非空＝候補が出る。
**これはお手本と一致する**（履歴ではなく候補）。一方 `clearSearchTerm()`（札の✕）は `setDraft("")` なので履歴が出る。
→ **既存 spec の B8（確定後に開き直して「最近使った語」の寸法を測る）は前提が変わるので✕の道に替える**（§4 更新）。

**未確認（推測で埋めない）**: 履歴の上限件数（測るには相手の検索履歴を10件以上汚す必要があるため見送り）／
候補が0件になる語を打ったときの表示。

**測定の後片付け**: 測定で足した履歴3件（pokemon 30th box / pokemon / pokemon 30th）は
⋮→削除で消し、元の6件（ポケモン・iphone・iphone・garaxy s25・garaxy s25・ポケモンカード box）に戻したことを確認済み。

## 2. うちの検索が実際に見ているもの（ここが設計の前提）

`frontend/src/pages/viewer/viewerFilter.ts:49-60`:

```ts
/** 空白区切りの AND。4つの対象（日本語名・英語名・型番・検索ワード）のどれかに各語が含まれる。 */
export function matchesQuery(row: ViewerRow, query: string): boolean {
  const tokens = query.split(/\s+/).map((tk) => normalizeForSearch(tk)).filter((tk) => tk !== "");
  if (tokens.length === 0) return true;
  const hay = normalizeForSearch(
    [row.japanese_title, row.english_title, row.mark, row.search_keywords].join("\n"),
  );
  return tokens.every((tk) => hay.includes(tk));
}
```

- **照合の対象は4つだけ**: `japanese_title`・`english_title`・`mark`・`search_keywords`。
  **`series`・`provider`・`condition` は見ていない**。
  → **シリーズ名や提供者名を候補に出すと、選んでも0件になる**。候補はこの4つから作る。
- 正規化は `frontend/src/features/inventory/searchNormalize.ts:6-11`＝
  **NFKC → 小文字 → ひらがなをカタカナへ**。つまり「はどう」と打っても「ハドウ」に当たる。
- 行の型は `frontend/src/pages/viewer/types.ts:11-27`（`ViewerRow`）。

## 3. いまの検索画面の中身（便12a で入った形）

`frontend/src/pages/viewer/InventoryView.tsx:880-912` が「最近使った語」を描いている。
state は `draft`（打っている途中）・`appliedQuery`（確定）・`searchOpen`・`recentSearches`。
開くときに `setDraft(appliedQuery)` と `loadRecentSearches()` を呼ぶ（同 `:157-161`）。

行の見た目は `frontend/src/pages/viewer/viewer.css:217-244` の `.viewer-recent-row`
（`min-height: var(--comp-search-row-h)`＝69px／`padding-left: calc(var(--field-h-tap) + var(--space-4))`＝64px／
印は絶対配置）。**候補の行もこの形をそのまま使える**。

## 4. 既存の検査（赤になりうるもの）

| 場所 | 何を前提にしているか | 本便での扱い |
|---|---|---|
| `frontend/tests-e2e/visual-language/viewer-search-mercari.spec.ts` B7（`:161-181`） | ✕ で開き直した画面（`draft` が空）に**最近使った語**が出る | **緑のまま**（空のときは履歴＝お手本どおり） |
| 同 B8（`:183-204`） | 最近使った語の行が69px・左64px・印1つ | **道順を替える**（確定後の開き直し→**札の✕**。F8 のとおり開き直すと候補が出るため。測る値は変えない） |
| 同「すべて消す」（`:206-221`） | `viewer-recent-clear` と履歴の行 | **緑のまま** |
| `frontend/src/pages/viewer/recentSearches.test.ts` | 履歴の読み書き | 無影響 |

## 5. 数と大きさ

- 本番の行数は **698件**（2026-10-28 実測）。1ページ50件（`viewerFilter.ts:9` の `PER_PAGE`）。
- 候補は打つたびに作り直すが、698件の走査は `useMemo` 1回ぶんで収まる見込み（計測して design に残す）。
- 閲覧ページ JS の上限は 300KB（`frontend/scripts/check-viewer-bundle.js`）。便12a 時点の実測は CI ログに出る。

## 6. PO 決定（2026-10-28）

| # | 問い | 決定 |
|---|---|---|
| 1 | 候補に件数を出すか | **出さない**（お手本どおり語だけ並べる） |
| 2 | 並べ順 | **打った語で始まるものを優先**（先頭一致→途中一致） |

## 関連
- 便12a: docs/handoff/viewer-search-mercari/{recon,design,review-opus}.md
- お手本の正本: docs/specs/design-system/visual-language/benchmark/mercari-search-filter.md
