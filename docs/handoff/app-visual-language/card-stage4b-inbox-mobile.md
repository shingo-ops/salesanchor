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

## 1-2. PO 指定の仕様と、現状の対応（2026-10-11 受領）

PO 指定: 「受信箱は WhatsApp と同じように開き、**一覧とスレッドは分けて表示**。**スレッドの右上にボタンを置き、押したらカルテが開く**」。

| 指定 | 現状 | この便での扱い |
|---|---|---|
| 一覧とスレッドを分けて表示 | 未実装（上下分割45vh。`InboxPage.css:1122-1131`） | **実装する**（§2） |
| スレッドの右上のボタンでカルテが開く | **既に実装済み**。`InboxMessageThread.tsx:429` の `.karte-toggle-btn`（`onClick` でカルテを開閉、`aria-label={t("inbox.karteToggle")}`）。`InboxPage.css:993` で既定は非表示、`:1007`（1279px以下）で表示される | **触らない**（ADR-108 の所有範囲。既存のまま使う） |

**カルテを開くボタンを新規に作る必要はない。**

## 1-3. PC に影響を出さないことの保証（PO 指定 2026-10-11）

PO 指定: 「PC に影響がないようにスマホだけ独自レイアウトにしたい」。次の仕組みで保証する。

| 変更 | PC への影響 | 保証の仕組み |
|---|---|---|
| §2-3 の CSS（1列切り替え） | **なし** | すべて `@media (max-width: 767px)` の**内側**に書く。PC（1280px以上）とタブレット（768〜1279px）には1行も適用されない |
| §2-4 の戻るボタン（CSS） | **なし** | `@media` の**外**に `.inbox-back-to-list { display: none; }` を置き、`@media (max-width: 767px)` の内側でのみ表示する。`display: none` は配置から外れるため PC のレイアウトは1pxも動かない |
| §2-4 の戻るボタン（DOM） | ボタン1つが**非表示で**増えるのみ | PC では `display: none`。他要素の位置に影響しない |
| §2-2 の `thread-open` クラス | **なし** | このクラスを使う CSS 規則は `@media (max-width: 767px)` の内側にしか書かない |
| §2-1 の `setSelectedLeadId` 公開 | **なし** | 型と返り値の公開のみ。既存の呼び出しと描画を変えない |
| §2-5 の i18n キー追加 | **なし** | 新規キー1件の追加。既存キーを変更しない |
| トークン | **なし** | `tokens.css` / `index.css` を**変更しない**。既存の `--comp-btn-height-lg` を参照するだけ |

**検証**: 受け入れ基準 #6（1280px）と #7（768px）で、段階1のベースライン（`stage1-baseline.md`）と数値が一致することを確認する。一致しなければこの便は不合格とする。

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
- **アイコンは登録済みの `back` を使う**（`frontend/src/constants/icons.tsx` に登録あり。2026-10-11 確認済み）。**新しい絵柄を追加しない**ため `check:icon-sync` に抵触しない。他のアイコンと同じ呼び出し方（`size={ICON.base}`）に揃える。
- 置く位置は `<header className="inbox-center-header">` の**最初の子**（お手本は上部バーの左端が戻る）。右側の `.karte-toggle-btn`（:429）とは反対側になるため衝突しない。
- **クラス名 `.inbox-back-to-list` は規約違反でない**（`check:css-class-naming` の禁止リストは `.mc-*` / `.crm-*` の10件のみ。2026-10-11 確認済み）。

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
| 3 | 390px 幅で「一覧へ戻る」を押すと**一覧に戻る**（URL の `lead_id` も消える） | `inbox-single-column.spec.ts`（§13）で一覧が表示・会話が非表示・`searchParams.get("lead_id")` が null になることを検査 |
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
4. **スレッドの上部バーが 390px 幅で窮屈になる恐れ。** 既存の `.karte-toggle-btn`（:429-434）は**アイコン＋文言**を出している。そこへ左端に戻るボタン（48px）が加わるため、幅が足りなくなる可能性がある。受け入れ基準 #4（横にはみ出さない）で検出する。はみ出した場合は**この便では文言を変えず**、`.karte-toggle-btn` の文言をスマホ幅だけ隠す指定（`@media` 内で `.karte-toggle-btn` の文字部分のみ非表示）を追加する。ADR-108 の所有範囲である**カルテ本体には触らない**。

## 9. 相互参照

- **recon**: [recon.md](./recon.md)（`docs/handoff/app-visual-language/recon.md`）— 段階1の現状実測。A3（`responsive.css` の8クラス）・E2（`--breakpoint-mobile-max: 767px` の実値）・F1（`/design-preview` は本番でもアクセス可）を前提として参照。本カードの切替点は E2 の 767px に揃えている。
- **ADR-144**（UI共通部品の遵守ガバナンス）: §5「移行（金型への置き換え）は別トラック・別PRで1ページ1部品ずつ」に従い、本カードでは `.conv-item` を `ListRow` 金型へ置き換えない。レイアウトの切替のみを扱う。
- **ADR-067**（デザイントークン強制システム）: 本カードの寸法はすべて既存トークンの `var()` 参照のみ。戻るボタンの当たり判定は `--comp-btn-height-lg`（48px）を参照し、生の値を書かない。新しいトークンを追加しない。`check:css-values` / `check:css-colors` / `check:new-tokens` が機械的に強制する。
- **ADR-140**（モバイルナビ刷新）: 下部タブバーと `MobileShell` は ADR-140 の所有範囲。本カードでは触らない。会話に使える高さを計算する際の80dpはこの帯の実測値。
- **ADR-108**（受信箱カルテパネル再設計）: カルテ（右パネル）は ADR-108 の所有範囲。本カードでは**ボトムシートの指定を一切変更しない**。
- **KGI**: [../../specs/design-system/visual-language/kgi.md](../../specs/design-system/visual-language/kgi.md) の K7（スマホ幅で横にはみ出さない）を維持する。
- **決まり**: [../../specs/design-system/visual-language/design.md](../../specs/design-system/visual-language/design.md) §10-4（画面幅ごとの並び方）。「スマホは1列。見えない列を DOM に積まない」に対応する実装。

## 10. 外部・過去事例の参照と我々への応用

| 事例 | 何を参照したか | 我々への応用 |
|---|---|---|
| **WhatsApp（Android）の実測** | 一覧→会話は**1画面ずつ切り替え**。戻るは上部バー左端で当たり判定48dp。進む約300msの ease-out、**戻るは85msでほぼ即時** | 上下分割をやめ1列切り替えにした。戻るボタンの位置と48dpを合わせた。動きの付け方は別便で扱う |
| **Meta Business Suite（Android）の実測** | こちらも1列切り替え | 「業務用のメッセージ一覧でも1列が成立する」根拠として採用 |
| **ADR-140（社内の先行事例）** | スマホは `MobileShell` の下部タブバー（帯80dp）を持つ | 下部タブ80dpを引いた残り高さで上下分割を評価し、**会話に約328dpしか残らない**ことを定量化した。これが1列化の根拠 |
| **段階1の実測（`stage1-baseline.md`）** | 390px幅で `.inbox-right-panel` が画面外（y=844）に存在 | 当初これを不具合と誤認したが、照合の結果**意図したボトムシート**（`translateY(100%)`）であることを確認し、触らない範囲に分類した |

**採用しなかったもの**: WhatsApp の「引き下げてカルテを出す」作法は採らない。カルテは ADR-108 の所有範囲であり、現行のボトムシートを維持する（出し方の変更は別便で諮る）。

## 11. 維持の仕組み

- 守り手: `frontend/package.json` の `check:all`（25項目）、`.github/workflows/e2e.yml` のジョブ `visual-language`（3幅の画面検査）、CI の `Process Artifacts Gate` / `UI Governance Gate` / `guard-hex-increase`。
- **対象**: 生の値の直書き（`check:css-values`）、色の直書き（`check:css-colors`）、文言の直書き（`check:i18n-missing-keys`）、ライト/ダークの片方欠落（`check:dark-parity`）、新規アイコンの無断追加（`check:icon-sync`）、新規トークンの無断追加（`check:new-tokens`）。
- **切替点の同期**: `check:breakpoint-sync` が `tokens.css` の `--breakpoint-*` と `@media` の値の一致を検査する。本カードの 767px はこれに準拠する。
- **1列切り替えが効いているかの検査（2026-10-12 に機械化・§13）**: 「会話を選ぶと一覧が消え、戻ると戻る」は CI の `画面検査（受信箱 3幅 Playwright）`（`.github/workflows/e2e.yml`）が毎 PR で検査する。作業端末では Playwright が chromium を提供しない（`ERROR: Playwright does not support chromium on ubuntu26.04-arm64`）ため、**マージ前の確認は CI（x86）で行う**。実機の Chrome での構造データ確認は、CI を通した後の最終確認として併用する。

## 12. 実装の結果と revert（2026-10-12）

本カードの設計で実装し（PR #4165）本番に投入したが、**実機で「一覧へ戻る」が機能せず、会話を開くと一覧に戻れない機能退行**を確認したため revert した（PR #4168）。

### 確認した事実

| 確認 | 結果 |
|---|---|
| 戻るボタンの存在 | あり（48x48dp・その座標で最前面の押せる要素） |
| タップの到達 | 到達している（同じ方法で「絞り込み」ボタンは正常動作＝対照実験） |
| 一覧の非表示 | `.inbox-sub-filter-bar` の項目が構造データに出ない＝`.inbox-left-panel` が `display: none` |
| 押下後の変化 | **なし**（10秒待っても送信・添付・戻るが残る） |
| 配信コード | **正しい**。JS に `(0,G.jsx)(i0,{onBackToList:()=>e.setSelectedLeadId(null),...})` と `function i0({onBackToList:e,...})`、CSS に `inbox-back-to-list` / `thread-open` が存在 |

**配線は正しいのに状態が変わらない**という状況で原因が未特定。利用者は会話を開くと戻れなくなる（URL を `replace` で書き換えるため端末の戻るでも履歴が無い）ため、調査より先に退行の解消を優先した。

### 作り直しの前に確かめること

1. `onBackToList` が実際に呼ばれているか（`/design-preview` での再現、または一時的な確認手段）
2. `.karte-overlay`（`showKartePanel` 時に `position: fixed; inset: 0`）がクリックを奪っていないか
3. **既存の解除の型に揃える**。`onPageFilterChange`（`useInboxState.ts:544-556`）は `setSelectedLeadId(null)` に加えて `setLeadDetail(null)` と **URL の `lead_id` 削除**（`params.delete("lead_id")` ＋ `setSearchParams`）を行っている。**URL を消していないことが原因である可能性が高い。**
4. **Mac 側で3幅の画面検査を通してから再投入する。** 作業端末では Playwright が chromium を提供しないため（`ERROR: Playwright does not support chromium on ubuntu26.04-arm64`）、構造変更の検証ができない。

### この便から得た教訓

**この端末で画面検査ができないまま構造変更を本番に出してはいけない。** 寸法や色の変更（#4147 / #4148 / #4155）は構造データの実測で検証できたが、**操作が成立するか**は画面検査または実機での往復確認が必要で、往復の確認を本番投入の前に行う手段を用意してから着手する。

## 13. 画面検査の恒久化（2026-10-12・PO指示「恒久的に画面を確認するようにして」）

#12 の退行を二度と本番に出さないため、**開く→戻るの構造だけは CI で毎回検査する**ことにした。

### 何を足したか

| 対象 | 中身 |
|---|---|
| `frontend/tests-e2e/visual-language/inbox-single-column.spec.ts` | **合否を出す**検査。390px で「一覧だけ→会話だけ→一覧だけ」と切り替わること、戻るボタンが48px以上であること、**URL の `lead_id` が消えること**、戻った後にもう一度開けることを検査する。1280px / 768px では一覧と会話が同時に見え、戻るボタンが出ないことを検査する（PC 不変の保証） |
| `frontend/tests-e2e/visual-language/inbox-helpers.ts` | 2本の spec が共用する mock と開き方。mock を2か所に分けて書くと片方が古くなるため唯一の置き場にした |
| `frontend/tests-e2e/visual-language/inbox-baseline.spec.ts` | 共通部品へ寄せ、**待ち方を状態ごとに直した**。元の作りは状態A（会話未選択）でも入力欄を待っていたが、`InboxMessageThread.tsx:358-369` は未選択時に empty-state を返すため**入力欄は存在しない**＝全幅で失敗する作りだった。状態B のスマホでは一覧が消えるため一覧も待たない |
| `frontend/package.json` | `test:e2e:vl` — 3幅の project だけを走らせる |
| `.github/workflows/e2e.yml` | ジョブ `visual-language`（表示名「画面検査（受信箱 3幅 Playwright）」）。`detect-changes` で `frontend/**` に変更があるときだけ走る。10分上限 |

### なぜ全部の E2E を再開しないのか

`e2e.yml:105` の `playwright` ジョブは `if: false`（**2026-06-01 に CI ボトルネック解消まで停止**）。これを外すと当時の待ち時間が戻る。今回必要なのは受信箱の3幅だけなので、**停止中のジョブはそのまま残し**、`visual-language` の spec（現状2本）に絞った別ジョブを足した。

### #4165 を捕まえられるか（この検査の根拠）

#12 の3番で特定した原因は「`setSelectedLeadId(null)` だけで **URL の `lead_id` を消していない**」こと。`inbox-single-column.spec.ts` は戻った直後に `new URL(page.url()).searchParams.get("lead_id")` が `null` であることを検査するため、**同じ作りに戻した時点で赤くなる**。表示状態（一覧が出る／会話が消える）も併せて検査する。

### 残る限界（正直に）

1. **必須チェックには入れていない。** 必須チェックの追加は Branch Protection の変更（CLAUDE.md §不可逆操作）であり PO の判断が必要。現状は PR 画面に結果が出るが、赤でもマージは機械的には止まらない。
2. **見た目（色・字の大きさ・影）は検査していない。** 検査するのは構造と寸法のみ。ベースライン計測（`inbox-baseline.spec.ts`）は記録を残すだけで合否を出さない。
3. **実機の操作感（スライドの速さ・慣性）は検査できない。** 別便で扱う。
