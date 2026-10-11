# 実装カード: 受信箱をスマホ幅で1列に切り替える（段階4b・第1便）

> この文書は何か（専門用語なしの1行）: スマホで受信箱を開いたとき、一覧と会話を上下に詰め込むのをやめて、お手本と同じ「1画面ずつ切り替える」形に直すための作業指示。

親: [../../specs/design-system/visual-language/design.md](../../specs/design-system/visual-language/design.md) §10-4 / 材料: [../../specs/design-system/visual-language/benchmark/README.md](../../specs/design-system/visual-language/benchmark/README.md)

- 作成日: 2026-10-11 / 段階: 4b（ページに適用・受信箱から・1画面＝1PR）
- 対象ADR: ADR-144 / 関連: ADR-140（モバイルナビ）・ADR-108（カルテ＝**触らない**）
- 状態: **PO の実装承認待ち**（design.md §6 の段階4b は「実装カード＋PO実装承認」が必要）

## 1. なぜ直すのか（事実のみ）

| 観測 | 根拠 |
|---|---|
| スマホ幅（767px以下）では一覧が上45vh・会話が下に**上下分割**されている | `frontend/src/pages/inbox/InboxPage.css:1122-1131` |
| 下部タブバーがあるため、会話に使える高さが約328pxしか残らない | 844px −（ステータス37＋上部バー56＋タブバー80）= 約708px を 45:55 で分割 |
| お手本2本（WhatsApp / Meta Business Suite）は**どちらも1列で切り替える** | `benchmark/README.md` の横断比較 |
| 一覧の行の構造（本文開始72px・顔写真48px円・区切り線なし）は**既にお手本と一致** | `InboxPage.css:259-299` |

**この便で直すのは「一覧と会話の並べ方」だけ。** 行の密度（最小高92px）と押す場所（44px未満）は**別便**に分ける（§6）。

## 2. 変更するファイルと、変更前後のコード

### 2-1. `frontend/src/pages/inbox/useInboxState.ts`

`setSelectedLeadId`（:199 で定義済み）が外に返されていないため公開する。**新しい状態は作らない。**

**変更前**（型の宣言・:76 付近）
```ts
  selectedLeadId: number | null;
```
**変更後**
```ts
  selectedLeadId: number | null;
  setSelectedLeadId: (id: number | null) => void;
```

返り値のオブジェクトにも `setSelectedLeadId,` を1行追加する（`selectedLeadId,` を返している行の直後）。

### 2-2. `frontend/src/pages/inbox/InboxPage.tsx:81`

会話を選んでいるかどうかを、CSS から見えるクラスにする。**条件分岐で描画を消さない**（DOM 構造は変えない）。

**変更前**
```tsx
        <div className="inbox-wrapper">
```
**変更後**
```tsx
        <div className={`inbox-wrapper${selectedLeadId != null ? " thread-open" : ""}`}>
```

`selectedLeadId` は :34 で既に取り出されている。import の追加は不要。

### 2-3. `frontend/src/pages/inbox/InboxPage.css`（`@media (max-width: 767px)` の中・:1120-1133）

**変更前**
```css
  .inbox-columns   { flex-direction: column; overflow: visible; }

  .inbox-left-panel {
    width: 100%;
    max-height: 45vh;
    flex-shrink: 0;
    border-right: none;
    border-bottom: 1px solid var(--border);
    overflow-y: auto;
  }
  /* overflow:hidden を明示してデスクトップと sticky スコープを統一 */
  .inbox-center  { width: 100%; flex: 1; min-height: var(--inbox-center-min-h); overflow: hidden; }
```
**変更後**
```css
  .inbox-columns   { flex-direction: column; overflow: hidden; }

  /* 1列で切り替える（お手本: design.md §10-4）。会話を選ぶまでは一覧が全画面 */
  .inbox-left-panel {
    width: 100%;
    max-height: none;
    flex: 1;
    flex-shrink: 1;
    border-right: none;
    border-bottom: none;
    overflow-y: auto;
  }
  .inbox-center { display: none; }

  /* 会話を選んだら一覧を隠し、会話を全画面にする */
  .inbox-wrapper.thread-open .inbox-left-panel { display: none; }
  .inbox-wrapper.thread-open .inbox-center {
    display: flex;
    width: 100%;
    flex: 1;
    min-height: var(--inbox-center-min-h);
    overflow: hidden;
  }
```

**注意**: `.inbox-wrapper` の `overflow-y: auto`（:1116-1117）は**変えない**。1列化で縦に積まれなくなるため実害はない。

### 2-4. `frontend/src/pages/inbox/InboxMessageThread.tsx:382`

会話側に「一覧へ戻る」を追加する。お手本は上部バーの左端に戻るを置き、当たり判定を48dp取っている（`benchmark/whatsapp-reproduction-spec.md` §2）。

**変更前**
```tsx
      <header className="inbox-center-header">
```
**変更後**（`<header>` の最初の子として追加）
```tsx
      <header className="inbox-center-header">
        <button
          type="button"
          className="inbox-back-to-list"
          onClick={onBackToList}
          aria-label={t("inbox.backToList")}
        >
          <Icon name="chevronLeft" />
        </button>
```

- `onBackToList` を props に追加し、`InboxPage.tsx` から `() => setSelectedLeadId(null)` を渡す。
- アイコンは `frontend/src/constants/icons.tsx` に登録済みのものを使う（**新しい絵柄をこの便で追加しない**。登録名は実装時に確認し、左向きの既存アイコンを使う）。

CSS（`@media (max-width: 767px)` の中に追加）
```css
  .inbox-back-to-list {
    display: flex;
    align-items: center;
    justify-content: center;
    width: var(--comp-btn-height-lg);
    height: var(--comp-btn-height-lg);
    flex-shrink: 0;
    border: none;
    background: transparent;
    color: var(--text-primary);
    cursor: pointer;
  }
```
`@media` の外では `.inbox-back-to-list { display: none; }` を置き、**PC では出さない**（PC は3列で一覧が常に見えているため）。

### 2-5. `frontend/src/locales/ja.json` / `en.json`

`inbox` 名前空間（ja.json:1180）に1キー追加。

```
ja: "backToList": "一覧へ戻る"
en: "backToList": "Back to list"
```

## 3. 触らない範囲（明示）

| 対象 | 理由 |
|---|---|
| `.inbox-right-panel` / `.karte-*` / `.right-panel-*` / `InboxKartePanel` | **ADR-108 の所有範囲**。カルテのボトムシート（`InboxPage.css:1136-1155`）はこの便では一切変更しない |
| `@media (max-width: 1279px)`（:1002-1111） | タブレット帯。この便はスマホ帯のみ |
| `.conv-item` の寸法（`--min-height-conv-item` / `--space-3`） | 密度の見直しは**別便**（design.md §11-4） |
| `.send-attach-btn` / `.send-preview-remove` / `.inbox-thread-action-btn` / `.inbox-send-btn` の大きさ | 押す場所の是正は**別便** |
| `useInboxState` の API 呼び出し・データ処理 | 配線と DB の SSOT を変更しない。**新しい状態も作らない** |
| `tokens.css` / `index.css` | **新しいトークンを追加しない**。既存の `--comp-btn-height-lg` を使う |

## 4. 守る決まり（CI が検査する）

| 関所 | この便で守ること |
|---|---|
| `check:css-values` | padding / margin / gap / width / height / font-size に**4px以上の生の値を書かない**。`max-height: none` と `flex: 1` は数値ではないため対象外 |
| `check:css-colors` | 色は `var(--...)` のみ。hex と rgba を書かない |
| `check:i18n-missing-keys` | ja.json と en.json の**両方**に `inbox.backToList` を追加する |
| `check:dark-parity` | 新しい色を増やさないため影響なし（`--text-primary` は両テーマで定義済み） |
| `check:icon-sync` | **新しいアイコンを追加しない**。既存の登録済みアイコンを使う |

## 5. 検証方法（受け入れ基準）

| # | 基準 | 検証 |
|---|---|---|
| 1 | 390px 幅で、会話を選ぶまで**一覧が全画面**（上下分割でない） | 3幅の画面検査（`--project=vl-mobile-390`）＋ `.inbox-center` が非表示であること |
| 2 | 390px 幅で行をタップすると**会話が全画面**になり、一覧が消える | 同検査で `.inbox-left-panel` が非表示・`.inbox-center` が表示 |
| 3 | 390px 幅で「一覧へ戻る」を押すと**一覧に戻る** | 同検査で `selectedLeadId` が null に戻ること |
| 4 | 390px 幅で**横にはみ出さない**（scrollWidth − innerWidth = 0） | 段階1の検査と同じ測り方 |
| 5 | 「一覧へ戻る」の当たり判定が **48x48** | 検査で boundingBox を測る |
| 6 | **1280px の PC 表示が変わらない** | `--project=vl-desktop-1280` の結果を段階1のベースラインと比べる |
| 7 | **768px のタブレット表示が変わらない** | `--project=vl-tablet-768` を同様に比較 |
| 8 | `npm run check:all` が緑 | 実行して出力を PR に貼る |

**段階1のベースライン**: `docs/handoff/app-visual-language/stage1-baseline.md`（390/768/1280 の実測値）。#6・#7 はこの値と比較する。

## 6. この便に含めない作業（別便）

| 便 | 中身 | 理由 |
|---|---|---|
| 第2便 | 押す場所を44px以上にする（28px・36px・32px の4クラス） | 送信エリアのピル内のレイアウトが破裂する恐れがあり、単独で検証したい |
| 第3便 | 行の密度（`--min-height-conv-item` 92px→76px、右の余白 12px→16px） | 見た目の変化が大きく、PO の判断（design.md §11-4）が必要 |
| 第4便 | 遷移の動き（右から左へのスライド・戻るは即時） | 構造が固まってから付ける |

## 7. 戻し方

このPRの revert のみ。`tokens.css` / `index.css` / API / DB を変更しないため、他への波及はない。

## 8. 残るリスク（正直に）

1. **`.inbox-center` を `display: none` にすると、会話を開いたときにスクロール位置の復元が効かない可能性がある。** 検証 #2 で会話が最下部（最新）から表示されるかを確認する。効かない場合は `display` ではなく `position: absolute` で画面外に出す方式へ切り替える。
2. **`.inbox-full-tab-bar`（:85）と `.inbox-platform-select`（:95）は `.inbox-columns` の外**にあるため、会話を全画面にしてもこれらが残る。お手本では会話画面に一覧用の絞り込みは出ない。**この便では残したまま**にし、気になる場合は第2便以降で扱う。
3. この端末（PRoot）では **Chromium が描画しないため3幅の画面検査を実行できない**。検証は Mac 側か CI で行う必要がある。
