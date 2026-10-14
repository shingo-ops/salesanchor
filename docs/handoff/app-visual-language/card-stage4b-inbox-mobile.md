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
3. ~~**URL を消していないことが原因である可能性が高い。**~~ → **誤り。真因は別だった（§14 で確定）。** 既存の解除の型（`onPageFilterChange` / `useInboxState.ts:544-556`）に揃えること自体は正しいが、それだけでは戻れない。
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
| `.github/workflows/e2e.yml` | ジョブ `visual-language-run`（表示名「画面検査（内部）」・`frontend/**` 変更時のみ・10分上限）と、集約ジョブ `visual-language`（表示名「画面検査（受信箱 3幅 Playwright）」・`if: always()`）。`lint-run` → `lint` と同じ型 |

### なぜ全部の E2E を再開しないのか

`e2e.yml:105` の `playwright` ジョブは `if: false`（**2026-06-01 に CI ボトルネック解消まで停止**）。これを外すと当時の待ち時間が戻る。今回必要なのは受信箱の3幅だけなので、**停止中のジョブはそのまま残し**、`visual-language` の spec（現状2本）に絞った別ジョブを足した。

### #4165 を捕まえられるか（この検査の根拠）

#12 の3番で特定した原因は「`setSelectedLeadId(null)` だけで **URL の `lead_id` を消していない**」こと。`inbox-single-column.spec.ts` は戻った直後に `new URL(page.url()).searchParams.get("lead_id")` が `null` であることを検査するため、**同じ作りに戻した時点で赤くなる**。表示状態（一覧が出る／会話が消える）も併せて検査する。

### 残る限界（正直に）

1. **必須チェックには入れていない。** 必須チェックの追加は Branch Protection の変更（CLAUDE.md §不可逆操作）であり PO の判断が必要。現状は PR 画面に結果が出るが、赤でもマージは機械的には止まらない。**許可が出た場合の手順は下記**。
2. **見た目（色・字の大きさ・影）は検査していない。** 検査するのは構造と寸法のみ。ベースライン計測（`inbox-baseline.spec.ts`）は記録を残すだけで合否を出さない。
3. **実機の操作感（スライドの速さ・慣性）は検査できない。** 別便で扱う。

## 14. #4165 の真因（2026-10-12・画面検査が検出）

§13 で足した画面検査を PR #4171 の CI で初めて実行したところ、**390px で3件すべてが赤**になり、原因が確定した。

### 確定した事実（CI のログ）

```
Locator:  locator('button.conversation-item').first()
Expected: visible
Received: hidden
  14 × locator resolved to <button class="conv-item conversation-item selected">
```

**受信箱を開いた直後に、会話が既に `selected` になっている。** 出どころは `useInboxState.ts:641-646`:

```ts
// 初期表示: 会話未選択かつ一覧が存在する場合、先頭を自動選択
useEffect(() => {
  if (selectedLeadId !== null || convLoading || filteredConversations.length === 0) return;
  selectLead(filteredConversations[0].lead_id);
}, [filteredConversations, selectedLeadId, convLoading, selectLead]);
```

### なぜ「一覧へ戻る」が効かなかったのか

1. 戻るを押す → `setSelectedLeadId(null)`
2. この効果の依存に `selectedLeadId` が入っているため**即座に再実行**
3. 「未選択かつ一覧がある」が成立 → **先頭の会話を選び直す**
4. `thread-open` が付き直し、会話が全画面のまま＝**押しても何も起きないように見える**

#12 で「配線は正しいのに状態が変わらない」と記録した現象の説明がついた。**URL の `lead_id` は原因ではない**（消しても効果が選び直す）。#12 の「作り直しの前に確かめること」3番は誤った推定であり、取り消す。

### 直し方

スマホ幅では自動選択しない。判定は **ADR-137 の `useIsMobile`**（`matchMedia` ＋ `BREAKPOINTS.MOBILE_MAX`）を使い、CSS 側の `@media (max-width: 767px)` と同じ切替点に揃える。新しい hook は作らない。

```ts
const isMobile = useIsMobile();
useEffect(() => {
  if (isMobile) return;
  ...
}, [..., isMobile]);
```

**PC・タブレットは従来どおり自動選択する**（一覧が常に見えているため自動選択が親切に働く）。画面検査の1280/768px 側（一覧と会話が同時に見える）がこれを守る。

### 副産物として分かったこと

現状の本番でも、**スマホで受信箱を開くと先頭の会話が自動で開き、`selectLead` 経由で既読化される**（`useInboxState.ts:521` のコメント「lead 選択時 → メッセージ取得 + 既読化」）。既読は取り消せないため、この修正は見た目の問題だけでなく**意図しない既読化を止める**意味も持つ。

### 教訓

**#12 で書いた「原因の推定」を実装の根拠にしてはいけなかった。** 推定（URL）と真因（自動選択の再実行）は別物で、推定のまま作り直せば同じ退行を繰り返していた。画面検査を先に用意したことで、**本番に出す前に**事実で確定できた。

### 必須チェック化の手順（PO の許可が出てから実行・未実行）

必須チェックは Ruleset **16619490** が持つ（`docs/BRANCH_PROTECTION_SETUP.md:322-333` の削除手順の逆）。**不可逆操作のため `bash scripts/permit-danger.sh` ＋ PO の明示許可が必要。**

```bash
# 1. 現状を保存（戻せるようにする）
gh api repos/shingo-ops/salesanchor/rulesets/16619490 > /tmp/ruleset-before.json

# 2. 画面検査を required に追加したものを作る
jq '.rules |= map(
      if .type == "required_status_checks"
      then .parameters.required_status_checks += [{"context":"画面検査（受信箱 3幅 Playwright）"}]
      else . end)' /tmp/ruleset-before.json > /tmp/ruleset-after.json

# 3. 差分を目で確認してから適用
diff <(jq -S . /tmp/ruleset-before.json) <(jq -S . /tmp/ruleset-after.json)
gh api -X PUT -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/shingo-ops/salesanchor/rulesets/16619490 \
  -d @/tmp/ruleset-after.json | jq '{id,name,updated_at}'
```

**戻し方**: `/tmp/ruleset-before.json` を同じ `PUT` で適用する。

**デッドロック対策は本便で済ませた**: 検査本体は `detect-changes` が `frontend/**` の変更を検出したときだけ走るため、フロント未変更の PR では skipped になる。そのまま必須チェックにすると「報告が来ない」デッドロック（Issue #523 / PR #534 と同型）が再発する。そこで `lint` と同じ型（`detect-changes` → `visual-language-run`（内部） → `visual-language`（集約・`if: always()`））にし、**集約が skipped を成功として報告する**ようにした。必須チェックに指定するのは集約側の名前 `画面検査（受信箱 3幅 Playwright）`。

## 15. 分離の便（2026-10-13・PO 承認済みの2段計画の第1便）

> この節は何か（専門用語なしの1行）: スマホ用のヘッダーを足す前に、**一覧の組み立てだけをスマホ用とPC用に分け、見た目は1画素も変えない**ための作業記録。

### 15-1. なぜ分けるのか

PO 依頼（2026-10-13）: 「顧客一覧の検索欄とアイコンボタンの上部にヘッダーをつけて、アイコンボタンをヘッダーアクションに移して検索欄を横幅いっぱいに」。

これを `frontend/src/pages/inbox/InboxConversationList.tsx` 1枚のまま実装すると、**同じファイルが PC とスマホの2つの見た目を同時に持つ**ことになり、どちらの変更がどちらに効くのか追えなくなる。そこで PO と「**DB の SSOT は遵守してフロントのパーツやデザインだけ独立させる**」方針で合意し、進め方を2段に分けた。

- **第1便（この節）**: 分けるだけ。見た目と DOM は変えない。
- **第2便**: 分けたスマホ側だけにヘッダーを新設する。

**混ぜない理由**: 分離と見た目変更を同じ PR でやると、見た目が変わったとき「分離の事故」か「意図した変更」かを切り分けられない。第1便を「見た目が変わらないこと」だけに絞れば、第2便で出た差はすべて意図した変更だと確定できる。

### 15-2. 何をどう分けたか

| ファイル | 役割 | 行数 |
|---|---|---|
| `frontend/src/pages/inbox/InboxConversationRows.tsx`（新規） | 行の描画だけ。**スマホPC共通** | 126 |
| `frontend/src/pages/inbox/InboxConversationListMobile.tsx`（新規） | スマホ専用の組み立て（上部＋共通の行） | 172 |
| `frontend/src/pages/inbox/InboxConversationList.tsx`（変更） | PC の組み立て（上部＋共通の行）。285行→198行 | 198 |
| `frontend/src/pages/inbox/InboxPage.tsx`（変更） | `isMobile` で2つを出し分ける | 348 |

- **状態と配線は分けない**。`frontend/src/pages/inbox/useInboxState.ts` は共有のままで、スマホ版とPC版には**同じ33個の props を同じ名前・同じ値で**渡す。`InboxPage.tsx:112` の `conversationListProps` にまとめ、`{...conversationListProps}` で両方へ展開する。
- 出し分けは `frontend/src/hooks/useIsMobile.ts`（`matchMedia` ＋ `BREAKPOINTS.MOBILE_MAX`）。`InboxPage.tsx:62` で既に呼んでいるものを再利用し、新しく呼ばない。
- **CSS は1行も変えない**。`frontend/src/pages/inbox/InboxPage.css` は差分に含まれない。

### 15-3. 受け入れ基準

| # | 基準 | 検証 | 結果 |
|---|---|---|---|
| 1 | 行の描画が**1文字も変わっていない** | `git show origin/main:frontend/src/pages/inbox/InboxConversationList.tsx` の 196〜282行と `frontend/src/pages/inbox/InboxConversationRows.tsx` の該当部分を `diff -b` | **差分0**（87行） |
| 2 | 上部の組み立てが**PC版・スマホ版ともに元と同一** | `<aside className="inbox-left-panel">` から `{/* 会話リスト */}` の直前までを3者で `diff -b` | **126行で3者一致** |
| 3 | 渡す props が**増減も改名もしていない** | `frontend/src/pages/inbox/InboxPage.tsx` の旧 JSX の props 名と新 `conversationListProps` のキーを照合 | **33個すべて同名** |
| 4 | CSS を変更していない | `git diff --name-only origin/main...HEAD` に `.css` が無いこと | **0件** |
| 5 | 1列切り替え（開く→戻る）が壊れていない | CI の `画面検査（受信箱 3幅 Playwright）` 15件。`frontend/tests-e2e/visual-language/inbox-single-column.spec.ts` は `button.conversation-item` / `.conv-name` / `.conv-preview-text` / `.conv-time` / `.inbox-left-panel` を見るため、**分離した範囲を実際に覆っている** | CI で確認 |
| 6 | `npm run check:all` が緑 | 実行 | **25項目すべて成功** |
| 7 | 型が通る | `npx tsc --noEmit` | 本変更由来のエラー**0件**（既存の `src/api/generated/schema` 欠落4件のみ） |
| 8 | 単体テストが壊れていない | `npm run test:unit` | 1037件中1036件成功。失敗1件（`frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.drawer.test.tsx`）は単独実行で5/5成功＝**既存のフレーキー**で本変更と無関係 |
| 9 | 生UI部品を増やしていない | `BASE_SHA=... HEAD_SHA=... node scripts/check-ui-governance.js` | **新規ハードコードなし**（対象4ファイル） |
| 10 | 実機でも見た目が変わらない | 実機 360px ライトで分離前後を撮り、画素で比較（画面検査は構造と座標だけで**画素の一致は見ていない**ため別途必要） | **達成**（本番反映後に実測。アプリ本体 y=108〜2200 の異なる画素 **0 / 2,259,360**。§15-6） |

### 15-4. ADR との関係（抵触しないことの確認）

- **ADR-144 §4（金型がない場合の手順）は対象外**。§4 は `components/` に**金型を新設**するときの手順（PO 許可＋`Xxx.tsx`＋`Xxx.css`＋`Xxx.stories.tsx`）であり、この便が作るのは `pages/inbox/` 内の**ページ固有の組み立てファイル**で金型ではない。入力欄と選択欄は既存の金型（`frontend/src/components/TextField.tsx` の `TextFieldControl` / `frontend/src/components/Select.tsx` の `SelectControl`）をそのまま使い続ける。
- **ADR-144 §2 の CI ゲートは緑**。検査対象の3種（生 `<select>` / 生 `<input type=text|search|省略>` / 自作タブ）は新ファイルに1件も無い。一括バーの `<input type="checkbox">` は検査対象の type ではない。
- **正直な射程**: 移した行の描画には生の `<button>` `<div>` `<img>` `<a>` とインライン `style` が元から含まれる。これらは ADR-144 §5 の「既存の独自実装」にあたり、件数が増えていないため赤化しない。**この便では直さない**（金型への置き換えは ADR-144 §5 のとおり別トラック）。
- **ADR-108（カルテ）には触らない**。`InboxKartePanel` とボトムシートの指定は変更していない。

### 15-5. 残るリスク（正直に）

1. **画面幅を 767px の前後でまたぐと、一覧が作り直される**（React が別の部品として扱うため）。スクロール位置や入力中の文字が失われる可能性がある。スマホ実機では幅が変わらないため起きない。PC で窓の幅を変える操作でのみ起きる。**第2便以降も同じ構造なので、気になる場合は別便で `key` の統一や状態の持ち上げを検討する。**
2. **上部の126行が PC版とスマホ版に二重にある**。第2便でスマホ側だけを書き換えるための意図的な重複だが、第2便までの間に上部を直すときは**2箇所直す必要がある**。第2便が終われば中身が別物になるため重複ではなくなる。
3. **画面検査は構造と座標しか見ない**。クラス名と DOM が同じであることは §15-3 の #1〜#3 で機械的に確かめた。「本当に1画素も変わっていない」ことは実機の画素比較（#10）でしか言えず、**これは本番反映後に実施して 0 画素を確認した**（§15-6）。

### 15-6. 実機での画素比較（実施済み・結果 0 画素）

- **分離前の撮影は保存済み**: `/root/vl-benchmark-raw/before-split-20261013-143133.png`（1080x2340・一覧5件）。
- **同じ日に撮った `before-split-20261013-143101.png` は使えない**。画素を数えた結果、Chrome の翻訳案内の暗い幕（`(0,210)-(1080,562)`）が上部を**63.7%覆っていた**。使えるのは 143133 の1枚だけ。
- 手順: 実機を `adb` でつなぎ直す → PWA（`org.chromium.webapk.a396ac817a983e9b4_v2`）を `am force-stop` してから開き直す → 同じ条件（ライト・360px・一覧5件・1行目 y=309）で撮る → 143133 と画素差を取る。**翻訳案内が出ていない状態で撮ること。**
- 2026-10-13 時点で**ワイヤレスデバッグが落ちている**（`127.0.0.1:45133` は応答せず、`adb devices` には `emulator-5554 offline` のみ）。PO からペア設定コードを受領して再接続する必要がある。

### 15-7. 戻し方

この PR の revert のみ。CSS・トークン・API・DB を変更しないため波及はない。revert すれば `frontend/src/pages/inbox/InboxConversationList.tsx` 1枚に戻る。

### 15-8. この便に含めない作業

| 便 | 中身 |
|---|---|
| 第2便 | スマホ側だけにヘッダーを新設（お手本の実測値: ヘッダー56dp・タイトル約20sp＝`--font-xl`・アイコン48dp右端寄せ・検索欄は左右12dpでピル形＝`--radius-full`） |
| 別便 | カルテの全画面化 / 遷移の動き / 送信ピル内の28pxボタン / 会話ヘッダの詰まり（三点メニューが 27x38dp で画面右端で切れている） |

### 15-9. 実機での確認結果（2026-10-13・本番反映後に実測）

PR 4222 はマージ（`ed5f1bc43`）・デプロイ成功後、実機 SC-51G（1080x2340・3倍）で確認した。

**先に「端末が新しい配信物を読んだか」を裏取りした**（これが取れていないと画素比較に意味がないため）:

| 確認 | 結果 |
|---|---|
| 本番の入口ファイルの `last-modified` | 10:05:44（マージ 10:03:57 の直後） |
| 配信ヘッダ | `cache-control: no-cache, must-revalidate`（古いものが残らない） |
| 撮影時刻 | 10:07（更新後） |
| 配信物の構造的な痕跡 | 上部のクラス（`inbox-manage-wrap` / `inbox-sub-filter-bar` / `inbox-bulk-check-all` / `inbox-page-filter-wrap` / `inbox-left-panel`）が**すべて2回**＝PC用とスマホ用に複製された。行のクラス（`inbox-conversation-list` / `conv-avatar-wrap`）は**1回**＝共通部品に集約された |

**画素比較の結果**:

| 比較 | 結果 |
|---|---|
| 分離前 vs 分離後（アプリ本体 y=108〜2200） | **異なる画素 0 / 2,259,360 = 0.0000%**（差分の範囲 = なし） |
| 画面全体 | 8,102画素（0.32%）。範囲は y=46〜85＝**ステータスバーの時計のみ**（時刻が進んだため） |
| 一覧の中身 | 5件・行 228px＝76dp・1行目 y=309 → 分離前と同一 |

**撮影の再現性**: 同じ手順で3回撮り（分離前の基準／本番反映前の確認／本番反映後）、**本体の画素は毎回ぴったり一致**した。＝この撮り方はノイズを持たないので、差が出たらそれは変更が原因だと断定できる。

**判定: 第1便は見た目を1画素も変えずに分離できた。** revert 不要。

## 16. ヘッダー新設の便（2026-10-13・PO 承認済みの2段計画の第2便）

> この節は何か（専門用語なしの1行）: 第1便で分けたスマホ専用の組み立て（`frontend/src/pages/inbox/InboxConversationListMobile.tsx`）にだけ、お手本（WhatsApp チャット一覧）と同じヘッダーを新設し、検索欄を横幅いっぱいのピルにするための作業記録。

### 16-1. PO 依頼の原文要点と PO 決定

PO 依頼（2026-10-13・§15-1 と同一の依頼）: 「顧客一覧の検索欄とアイコンボタンの上部にヘッダーをつけて、アイコンボタンをヘッダーアクションに移して検索欄を横幅いっぱいに」。

| 論点 | PO 決定 |
|---|---|
| 絞り込み（filter）と管理（manage）のどちらをヘッダーへ移すか | **両方**ヘッダーの右端へ移す |
| PC・タブレットにも同じ配置を適用するか | **適用しない**。今便は `frontend/src/pages/inbox/InboxConversationListMobile.tsx`（スマホ専用）だけを変更し、PC 版 `frontend/src/pages/inbox/InboxConversationList.tsx` は無変更のまま。第1便（§15）で分けた配置（PC は従来どおり検索欄の横に絞り込みを置く）を了承 |
| 状態と配線（検索・絞り込み・選択・一括アクション等）を分けるか | **分けない**。`frontend/src/pages/inbox/useInboxState.ts` を共有したまま、見た目の組み立て（どの部品をどこに置くか）だけをスマホ側で変える |

### 16-2. お手本の実測値（WhatsApp チャット一覧・ライト・360dp幅。再測不要）

| 測るもの | 実測値 |
|---|---|
| ヘッダー全体の高さ | 56dp |
| タイトルの左端 x | 16dp |
| タイトルの文字サイズ | 約20sp |
| ヘッダーのアイコン（押す場所） | 48dp×48dp・右端寄せ |
| 検索欄の外枠左右 | 各12dp |
| 検索欄の高さ | 48dp・完全なピル |
| 検索の文字の開始位置 | 56dp |
| ヘッダーと検索欄の間 | 4dp |

### 16-3. 使ったトークンと実値

| トークン | 実値 | 使用箇所 |
|---|---|---|
| `--topbar-height` | 56px | ヘッダー全体の高さ |
| `--font-xl` | 1.25rem（20px） | タイトルの文字サイズ |
| `--radius-full` | 9999px | 検索欄の丸み（完全なピル） |
| `--size-icon-btn-lg` | 44px | ヘッダーのアイコン2つ（絞り込み・管理）の寸法 |
| `--size-icon-btn` | 36px | 検索の左 padding の計算に使用（§16-4②） |
| `--comp-btn-height-lg` | 48px | 検索欄の高さ |
| `--space-1` | 4px | ヘッダーと検索欄の間 |
| `--space-3` | 12px | 検索欄の外枠左右・タイトルの左余白の基準にはしない（下記 `--space-4` を使用） |
| `--space-4` | 16px | タイトルの左余白・検索アイコンの左位置 |

**新規トークンは足していない。** すべて `frontend/src/tokens.css` に既存の値をそのまま使っている。

### 16-4. お手本とあえて違えた2点

| 項目 | お手本 | 当方 | 理由 |
|---|---|---|---|
| ① ヘッダーのアイコンの寸法 | 48dp | 44dp（`--size-icon-btn-lg`） | WCAG 2.5.5 の基準値（44px）そのもので、新規トークンを作らず既存トークンを優先した |
| ② 検索の文字の開始位置 | 56dp | 52dp（`--space-4` 16px ＋ `--size-icon-btn` 36px の合計） | 既存トークンの組み合わせで表現。アイコンの実体は14pxで箱（36px）より小さいため、文字とアイコンは重ならない |

### 16-5. 受け入れ基準

| # | 基準 | 検証方法 | 結果 |
|---|---|---|---|
| 1 | ヘッダーと検索欄の間が4dpになっている | `frontend/src/pages/inbox/InboxPage.css` の `.inbox-mobile-search-row` の `padding` を `var(--space-1) var(--space-3)` に修正し、コメント（「下に4dp」→「上下4dp」）を実体と一致させた | 修正済み（コードレビューで確認） |
| 2 | 移動したボタンのセレクタが画面検査で追従している | `frontend/tests-e2e/visual-language/inbox-single-column.spec.ts` のスマホ側3箇所（115・127・139・142・151行付近の `filterInHeader`、362行、422行）を `.inbox-mobile-header .inbox-mobile-filter-toggle` に変更。PC・タブレット用（479行付近、`.inbox-search-row .inbox-mobile-filter-toggle`）は意図的に変更していない | 修正済み。`npx playwright test --list` で27件（9テスト×3幅）収集成功 |
| 3 | スマホ専用ヘッダーが PC・タブレットに漏れていない | 同 spec の PC・タブレットのテストに `await expect(page.locator(".inbox-mobile-header")).toHaveCount(0);` を追加 | 追加済み |
| 4 | 新規テスト（ヘッダーの寸法・位置・ピル形・二重見出しの有無）を追加した | 同 spec に `スマホ: 一覧の上にヘッダーが出て、検索欄が横幅いっぱいのピルになる` を新設（§16-6 に assertion 一覧） | 追加済み |
| 5 | `npm run check:all` が緑 | `cd frontend && npm run check:all` | **25項目すべて `exited with code 0`**（lint は既存の warning 138件のみ・error 0件・本変更由来の新規違反なし） |
| 6 | 型が通る | `cd frontend && npx tsc --noEmit` | **エラー0件** |
| 7 | 単体テストが壊れていない | `cd frontend && npm run test:unit` | 990件中981件成功・9件失敗（3ファイル）。失敗3ファイルを個別に再実行した結果、**全ファイル成功**（`NeedsReviewTabsPanel.drawer.test.tsx` 5/5、他4ファイル68/68）。フルスイート実行時の worker タイムアウト（並列実行時の負荷起因）であり、本変更（`frontend/src/pages/inbox/InboxConversationListMobile.tsx` と `frontend/src/pages/inbox/InboxPage.css` のみ）とは無関係 |
| 8 | デザイントークンの増加なし（ratchet） | `BASE_SHA=$(git rev-parse origin/main) HEAD_SHA=$(git rev-parse HEAD) bash scripts/check-design-token-ratchet.sh`（リポジトリ直下） | `PASS: 対象2ファイル・増加なし` |
| 9 | UI ガバナンス（生UI部品の新規ハードコードなし） | `BASE_SHA=$(git rev-parse origin/main) HEAD_SHA=$(git rev-parse HEAD) node scripts/check-ui-governance.js` | `✅ UI governance: 新規ハードコードなし`（対象ファイル数1） |
| 10 | e2e（Playwright）の実行確認 | この端末（arm64/Termux）では chromium が動かないため実行不可。構文確認のみ `npx playwright test --list` | 27件収集成功。実機 Playwright 実行は CI（x86）に委ねる |

### 16-6. 新規テストに足した assertion 一覧

`スマホ: 一覧の上にヘッダーが出て、検索欄が横幅いっぱいのピルになる`（`frontend/tests-e2e/visual-language/inbox-single-column.spec.ts`）で測るもの。幅は `page.viewportSize()` から取り、お手本の360dpではなく project 実際の幅（vl-mobile-390 は390px）を基準に相対で判定する。

| 測るもの | 比較対象 |
|---|---|
| `.inbox-mobile-header` の高さ | 56px（±1） |
| `.inbox-mobile-header-title` の左端 x | 16px（±1） |
| タイトルの `getComputedStyle(...).fontSize` | 20px（厳密一致） |
| `.inbox-mobile-header .inbox-mobile-filter-toggle` / `.inbox-mobile-header .inbox-manage-btn` の寸法 | 各44px以上×44px以上 |
| 管理ボタン（ヘッダー最後の部品）の右端 | ビューポート右端（±1） |
| `.inbox-mobile-search-row .inbox-search-input` の高さ | 48px（±1） |
| 同 左端 x | 12px（±1） |
| 同 右端 | ビューポート幅−12px（±1） |
| 同 `getComputedStyle(...).borderRadius` を数値化した値 | 検索欄の高さ÷2以上（24px以上） |
| ヘッダー下端〜検索欄（入力欄）上端の間 | 4px（±1） |
| `page.getByRole("heading", { name: "受信箱" })` の件数 | 1件（見出しの二重がない） |

### 16-7. 残るリスク

1. **実機の画素比較は未実施。** §15-6/§15-9 のように実機で分離前後を撮って画素差を取ったのは第1便のみ。第2便（ヘッダー新設）は見た目を変える便のため画素差が出るのは想定内だが、お手本と比べた実機確認（寸法だけでなく色・影・タップの手触り）は本番反映後に別途行う必要がある。
2. **Playwright をこの端末で実行できない。** `npx playwright test --list` で構文とセレクタの収集は確認したが、実際に assertion が通るかは CI（x86）の初回実行で初めて分かる。
3. **お手本とあえて違えた2点（§16-4）はトークンの都合による妥協。** 将来 48dp のアイコンサイズ用トークンを新設する判断があれば見直しの余地がある。
4. **ヘッダーの右端寄せは `padding-right: 0` で実現しており、管理ボタン自体の右 padding には依存していない。** 将来管理ボタンのスタイルを変える際、`.inbox-mobile-header` の右端 padding を誤って追加すると右端寄せが崩れる。

## 17. ヘッダー固定の便（2026-10-14・第3便。推測で足した sticky を撤回した経緯を含む）

> この節は何か（専門用語なしの1行）: 「スクロールしてもヘッダーが固定されるように」という PO 依頼に対し、最初は推測で `position: sticky` を足したが、CI の検査がその推測の誤りを検出した。調べ直すと**ヘッダーは最初から（スマホの一覧が別の箱でスクロールする構造のため）動かない**ことが分かり、sticky のコードは撤回し、その性質を検査で固定する形に直した記録。

### 17-1. PO 依頼の原文要点

PO 依頼（2026-10-14）: 「スクロールしてもヘッダーが固定されるようにしてほしい。必要であればテストデータを足していい」。

| 論点 | 内容 |
|---|---|
| 固定する対象（当初の理解） | `.inbox-mobile-header`（タイトル＋右端の絞り込み・管理） |
| 固定しない対象（当初の理解） | `.inbox-mobile-search-row`（検索欄のピル）。お手本の構造に合わせ、一覧と一緒に流れる想定だった（§17-2 で誤りと判明） |
| テストデータ | 画面検査で長い一覧が必要なら追加してよいという許可を受領済み |

### 17-2. 当初の推測と、CI の検査が検出した誤り

**最初の実装（誤り）**: `frontend/src/pages/inbox/InboxPage.css:1142-1150` の `@media (max-width: 767px)` 内に `.inbox-left-panel { overflow-y: auto; }` があることだけを根拠に、「スクロールする箱は `.inbox-left-panel` である」と推測し、`.inbox-mobile-header` に `position: sticky; top: 0; z-index: var(--z-base); background: var(--bg-surface);` を追加した。この時点で `.inbox-left-panel` の中身が実際にあふれているかどうかは確認していなかった。

**CI が検出した事実**: 新設した検査 `スマホ: 一覧をスクロールしてもヘッダーが動かない`（vl-mobile-390）が、スクロール可能性を確認する関所の行で失敗した。

```
Error: 一覧がスクロールできる高さになっていない（検査データが足りない）
> 588 | expect(scrollable, "...").toBe(true);
```

`.inbox-left-panel` の `scrollHeight === clientHeight` のまま＝そもそも `.inbox-left-panel` 自身はスクロールしていなかった。これにより「スクロールする箱は `.inbox-left-panel`」という前提そのものが誤りだったことが判明した。**他の16件は合格（§17-10 の題字21pxの assert も合格）していたため、この1件だけが推測の誤りを捕まえた。**

### 17-3. 判明した事実（スクロール箱の本当の構造）

実際にスクロールしている箱は `.inbox-conversation-list` であり、`.inbox-left-panel` ではない。

| ファイル:行 | 事実 |
|---|---|
| `frontend/src/pages/inbox/InboxPage.css:82-91` | `.inbox-left-panel` は `display: flex; flex-direction: column;`（既定 `overflow: hidden`。スマホ用 `@media` では `overflow-y: auto` に上書きされるが、中身があふれないため実際には効かない） |
| `frontend/src/pages/inbox/InboxPage.css:252-256` | `.inbox-conversation-list { flex: 1; min-height: 0; overflow-y: auto; overscroll-behavior: contain; }`。実際にスクロールするのはここ |
| `frontend/src/pages/inbox/InboxConversationListMobile.tsx:32-184` | `.inbox-left-panel`（`<aside>`）の直下に、順に `.inbox-mobile-header` → `.inbox-mobile-search-row`（＋一括操作バー）→ `.inbox-sub-filter-bar` → （条件付き）`.inbox-page-filter-wrap` → `<InboxConversationRows>` が並ぶ |
| `frontend/src/pages/inbox/InboxConversationRows.tsx:38` | `<InboxConversationRows>` がレンダーする `.inbox-conversation-list` の実体 |

`.inbox-conversation-list` は `flex: 1` ＋ `min-height: 0` を持つので、**親の高さが確定していれば**自分だけスクロールを受け持ち、その外側にある `.inbox-mobile-header` と `.inbox-mobile-search-row` は動かない。ここまでは CSS を読んだだけで言えることだが、**親の高さが確定しているかどうかは読みだけでは分からない**。

**2度目の推測と、その誤り（CI が検出）**: 上記の構造から「ヘッダーはそもそも最初から動かない」と結論し、検査を `.inbox-conversation-list` 決め打ちで書き直した。CI は再び `行の一覧がスクロールできる高さになっていない（検査データが足りない）` で止まった。そこで**要素名を決め打ちせず、行から親をたどって「本当に中身があふれている箱」をブラウザ内で探し、見つからなければページ全体を使う**形に書き直した（§17-6）。この版が出した実測が次である（20件の一覧・vl-mobile-390）。

| 箱 | scrollHeight | clientHeight | overflow-y |
|---|---|---|---|
| `div.inbox-conversation-list` | 1520 | 1520 | auto |
| `aside.inbox-left-panel` | 1632 | 1632 | auto |
| `div.inbox-columns` | 1632 | 1632 | visible |
| `div.inbox-main-area` | 1632 | 1632 | visible |
| `div.inbox-wrapper` | 1632 | 1632 | auto |
| `main.mobile-content` | 1698 | 1698 | auto |
| `html` | 1698 | 844 | visible |

**どの箱も中身の高さまで伸びきっており、スクロールしていたのは `html`＝ページ全体だけだった。** ページごと動くのでヘッダーも一緒に流れる＝**PO の指摘は実在する不具合で、「最初から動かない」という私の2度目の結論も誤りだった**。本番の会話が5件しかなくスクロールが起きないため、これまで誰も踏んでいなかった。

### 17-4. 真因と対応（2段階）

**原因は2つあり、両方を直して初めてヘッダーが動かなくなった。**

| # | 原因 | 直し方 | 根拠 |
|---|---|---|---|
| 1 | 高さが確定していない | `frontend/src/components/PageLayout.css` の `.page-layout.page-layout--slim-header` に与えていた `min-height: calc(100dvh - var(--tabbar-height))` を、値はそのままで `height` に変更 | `min-height` では親の高さが「確定」扱いにならず、flex の子が縮まずに中身の高さまで伸びる（PR 4196 で会話側に起きたのと同じ現象）。対象は `slimHeaderOnMobile` を渡すページ＝受信箱のみ |
| 2 | スマホ用に「はみ出しを許す」上書きが残っていた | `frontend/src/pages/inbox/InboxPage.css` の `@media (max-width: 767px)` で `.inbox-wrapper { overflow-y: auto }` → `hidden`、`.inbox-main-area { overflow: visible }` → `hidden; min-height: 0`、`.inbox-columns { overflow: visible }` → `hidden; min-height: 0` | 1 を直した直後の CI 実測では、スクロール箱が `html` から `.inbox-wrapper`（clientH=778 / scrollH=1632）へ移っただけで、ヘッダーはその内側にあるため依然動いた。土台（`frontend/src/pages/inbox/InboxPage.css:4-21` の `height: 100%` ＋ `overflow: hidden`）は正しく組まれており、スマホだけが例外になっていた |

`min-height: 0` を明示しているのは、flex の子の既定が `min-height: auto`（縮まない）であるため。これが無いと `overflow` を戻しても縮まない。

**`position: sticky` は使っていない。** §17-2 で推測から足したものは撤回したままで、高さが正しく確定していれば不要であることが実測で確認できた（この節の対応後、CI の画面検査17件が合格）。

### 17-5. テストデータと新テスト（訂正後）

対象: `frontend/tests-e2e/visual-language/inbox-helpers.ts`／`frontend/tests-e2e/visual-language/inbox-single-column.spec.ts`。

| 追加した関数・テスト | 内容 |
|---|---|
| `manyConversations(count)`（`inbox-helpers.ts`） | `mock-conversations.json` の1件目を複製し、`lead_id`／`lead_code`／`customer_name` だけずらして `count` 件の一覧を作る。fixture JSON ファイル自体は変更していない |
| `openInboxListWithConversations(page, count)`（`inbox-helpers.ts`） | `baseMocks()` の `"GET /conversations"` だけ `manyConversations(count)` に差し替えて受信箱を開く。既存の `openInboxList`（3件）はそのまま残している |
| `スマホ: 一覧をスクロールしてもヘッダーが動かない`（`inbox-single-column.spec.ts`） | 要素名を決め打ちせず、実際にスクロールしている祖先をブラウザ内で探して測り直す形に書き直した（§17-3 の「2度目の推測の反省」参照）。§17-6 の assertion 一覧を参照 |

件数の根拠（コメントは `frontend/tests-e2e/visual-language/inbox-helpers.ts` にも記載）: vl-mobile-390 の viewport は 390x844、`--min-height-conv-item-mobile` が76px。ヘッダー56px＋検索欄56pxで画面上112pxを占有し、残り732pxに収まる行数は約9.6件。600pxスクロールさせても十分な余りが残るよう、収まる件数の2倍以上を確保する目的で20件とした（この根拠自体はスクロール箱の取り違えとは無関係で、訂正後も変えていない）。

### 17-6. 新規テストの assertion 一覧（訂正後）

`スマホ: 一覧をスクロールしてもヘッダーが動かない`（`frontend/tests-e2e/visual-language/inbox-single-column.spec.ts`）で測るもの。

| # | 測るもの | 比較対象 |
|---|---|---|
| 1 | 1行目（`button.conversation-item`）の祖先を順にたどり、`scrollHeight > clientHeight` かつ `overflow-y` が `auto`/`scroll` である最初の要素（見つからなければ `document.scrollingElement`）を探し、`[data-vl-scrollbox]` を付けて以降の操作対象にする | その要素が1つ見つかること（0件なら「スクロールできる箱が1つも無い（検査データが足りない）」で検査自体を失敗させる。たどった祖先の一覧はエラーメッセージと `testInfo.attach("scroll-box-detection", ...)` に残す） |
| 2 | スクロール前後の `.inbox-mobile-header` の `boundingBox().y` | 差が1px以内 |
| 3 | スクロール前後の `.inbox-mobile-header` の `boundingBox().height` | 差が1px以内 |
| 4 | スクロール前後の `.inbox-mobile-search-row` の `boundingBox().y` | 差が1px以内（§17-7 参照：当方はヘッダーと同じく固定側） |
| 5 | スクロール後の管理ボタン（ヘッダー右端）の右端 x | ビューポート右端との差が1px以内 |
| 6 | スクロール前後の1行目（`button.conversation-item`）の `boundingBox().y` | スクロール後の方が小さい（行が実際に上へ流れた証拠） |
| 7 | `[data-vl-scrollbox]` に `scrollTop = 600` を指定した後の実際の `scrollTop` | 0より大きい（スクロールが本当に効いた証拠。どの要素が実際にスクロールするかで到達できる量が変わるため、厳密に600であることは求めない） |

背景色が透明でないことの assert（旧 §17-5 の7番）は削除した。sticky をやめたため「ヘッダーの下に行が潜り込む」という前提自体が成り立たず、assert の意味が変わるため。測った値はすべて `testInfo.attach("scroll-box-detection", ...)` と `testInfo.attach("sticky-header-scroll", ...)` に JSON で残している。

### 17-7. 当方とお手本の差（検索欄の扱い）

お手本（WhatsApp）は §17-2 で引用した構造データのとおり、検索欄（`search_bar_inner_layout`）がスクロールする箱（`conversation_container`）の**内側**にあり、一覧と一緒に流れる。

当方は `.inbox-mobile-search-row` も `.inbox-mobile-header` と同じく `.inbox-conversation-list`（本当のスクロール箱）の**外側**にあるため、検索欄もヘッダーと同じく固定側になる（§17-3）。**これは意図した設計上の決定ではなく、現在の DOM 構造からそうなっているだけの事実**であり、お手本と一致していない点として記録する。この差を埋める（検索欄だけをスクロール箱の内側に移す）かどうかは今便の範囲外とし、PO 判断を待つ。

### 17-8. 受け入れ基準

| # | 基準 | 検証方法 | 結果 |
|---|---|---|---|
| 1 | スマホの受信箱でページ全体がスクロールしない | CI の画面検査が「行から親をたどって見つけたスクロール箱」を出力。修正後は `html` ではなく `.inbox-conversation-list` が選ばれる | 達成（CI 画面検査17件合格） |
| 2 | 一覧をスクロールしてもヘッダーの y と高さが変わらない | 新テスト `スマホ: 一覧をスクロールしてもヘッダーが動かない`（±1px） | 達成（CI で合格） |
| 3 | 検索欄の y も変わらない | 同テスト（±1px） | 達成（CI で合格） |
| 4 | 行は実際に動いている（検査が空振りしていない） | 同テストで1行目の y がスクロール後に小さくなることと `scrollTop > 0` を確認 | 達成（CI で合格） |
| 5 | 効果を示せない `position: sticky` を入れていない | `frontend/src/pages/inbox/InboxPage.css` に sticky の記述が無いこと | 達成（撤回済み・grep で0件） |
| 6 | 会話画面側が壊れていない | 既存の画面検査（`一覧 → 会話 → 一覧`・`会話を開いた状態`のベースライン・会話側の44px検査） | 達成（すべて緑） |
| 7 | 題字が21pxで出ている | 同 spec の `titleFontSize` が21px（厳密一致） | 達成（CI で合格） |
| 8 | `npm run check:all` が緑 | `cd frontend && npm run check:all` | 達成（25項目すべて成功・lint は既存 warning 135件で error 0件） |
| 9 | 型が通る | `cd frontend && npx tsc --noEmit` | 達成（エラー0件） |
| 10 | 単体テストが壊れていない | `cd frontend && npm run test:unit` | フルスイートでは毎回**違うファイル**が `Test timed out in 5000ms` で落ちるが、該当ファイルを個別実行すると全件成功＝並列実行時のワーカータイムアウトで本変更とは無関係 |
| 11 | 実機でも崩れていない | 本番反映後に SC-51G（1080x2340・3倍）で撮影し、ヘッダー56・検索欄48・行76・押す場所44以上を再確認 | **未実施**（マージ後に実施） |

### 17-9. 残るリスクと教訓

1. **教訓（再発防止・この便で2度踏んだ）**: 「どの要素がスクロールしているか」は **CSS を読んだだけでは決められない**。1度目は `.inbox-left-panel` の `overflow-y: auto` だけを見て「ここがスクロール箱」と推測して外し、2度目は `.inbox-conversation-list` の `flex:1 / min-height:0` を見て「ヘッダーは最初から動かない」と推測して外した。**実際にスクロールするかは、親の高さが確定しているかに依存し、それは祖先をすべてたどらないと分からない。** 対策として、検査そのものを「要素名を決め打ちせず、行から親をたどって `scrollHeight > clientHeight` かつ `overflow-y` が `auto`/`scroll` の最初の箱を使う」形にし、見つからない場合は親の連なり（セレクタ・scrollHeight・clientHeight・overflow-y）を失敗メッセージと添付に出すようにした。**この出力だけで真因（§17-4）を特定できた。**
2. **高さの扱いを変えたので会話画面にも影響し得る。** `.page-layout--slim-header` の `min-height` → `height` は受信箱の全画面（一覧・会話の両方）に効く。既存の画面検査はすべて緑だが、実機確認はマージ後になる。
3. **実機では本番の会話が5件しかなくスクロールが起きない。** 実機でスクロールの固定まで確かめるには、本番のテナントに会話を数件増やす必要がある（PO 相談事項）。
4. **検索欄もヘッダーと同じく固定側になっている（§17-7）。** お手本（検索欄は一覧と一緒に流れる）と一致していない。揃えるかどうかは PO 判断待ち。

### 17-10. 題字の文字サイズ（PO 決定・2026-10-14・字種をそろえて再測定）

> この節は何か（専門用語なしの1行）: 受信箱の題字「受信箱」とお手本の題字を、同じ字種（漢字）で測り直したところ1dp足りなかったため、スマホの題字だけ専用のサイズに直した作業記録。

**訂正（重要）**: §16-2 の表にある「ヘッダーのタイトルの文字サイズ 約20sp」および冒頭のコメント（第2便時点の `.inbox-mobile-header` 直前コメント）の「タイトルの文字（漢字インク高さ19.0dp）」は、**ロゴ画像を含む測定**から来ていた。チャット一覧の題字はロゴ画像（§16-2 注記「チャット一覧の題字はロゴ画像」参照）であり、漢字の文字そのものではない。そのため当方の漢字の題字と字種をそろえた比較になっていなかった。

今回、お手本の**通話画面**の題字「電話」（漢字）と、当方の「受信箱」（漢字）を同じ方法（画素のインク高さ測定）で測り直した。

| 対象 | インク高さ |
|---|---|
| お手本 通話画面の題字「電話」（漢字） | 19.0dp |
| 当方 受信箱の題字「受信箱」（漢字・font-size 20px＝`--font-xl`） | 18.0dp |
| （参考）お手本チャット一覧の題字はロゴ画像 | 21.0dp |

字種をそろえた漢字どうしの比較では差は1dp（19.0 − 18.0）。当方は20pxでインク18.0dp＝比率0.90。お手本の19.0dpに合わせるには 19.0 ÷ 0.90 ≒ 21px（21pxなら18.9dpで一致）。**PO決定: お手本に合わせる（21px相当を新設）。**

**実装**:

| ファイル | 変更内容 |
|---|---|
| `frontend/src/tokens.css` | `--font-xl` の直後に `--font-title-mobile: 1.3125rem;`（21px）を新設。色トークンではないため `:root.force-dark` への追加は不要 |
| `frontend/src/pages/inbox/InboxPage.css` | `.inbox-mobile-header-title` の `font-size` を `var(--font-xl)` から `var(--font-title-mobile)` に変更。**このヘッダー専用**で、他のページ見出し（`--font-xl` を使う他箇所）は変えていない |
| `frontend/tests-e2e/visual-language/inbox-single-column.spec.ts` | `スマホ: 一覧の上にヘッダーが出て、検索欄が横幅いっぱいのピルになる` の `titleFontSize` 比較を `20` から `21` に変更 |

**受け入れ基準**:

| # | 基準 | 検証方法 | 結果 |
|---|---|---|---|
| 1 | 新規トークンは `--font-title-mobile` の1個のみ | `git diff` で `frontend/src/tokens.css` の追加行を確認 | 1行のみ追加（コードレビューで確認） |
| 2 | 色トークンではないので force-dark 側への追加は不要 | `npm run check:dark-parity` | `✅ ダークモード変数パリティチェック PASSED (134 変数すべて対応済み)` |
| 3 | 使用箇所がヘッダーのタイトルのみ | `grep -rn "font-title-mobile" frontend/src` | `tokens.css`（定義）と `InboxPage.css`（`.inbox-mobile-header-title` のみ）の2箇所 |
| 4 | 画面検査が新しい値（21px）に追従している | `inbox-single-column.spec.ts` の `titleFontSize` 比較を21に変更 | 変更済み（この文書の実装表） |
| 5 | `npm run check:all` が緑 | `cd frontend && npm run check:all` | 25項目すべて `exited with code 0` |
| 6 | 型が通る | `cd frontend && npx tsc --noEmit` | エラー0件 |
| 7 | 単体テストが壊れていない | `cd frontend && npm run test:unit` | 1054件中1047件成功・7件失敗（6ファイル）。全て `Test timed out in 5000ms`（本変更と無関係のファイル）。該当6ファイルを個別実行した結果 **123件すべて成功**。フルスイート実行時の worker タイムアウト（§16-5 item 7 と同種の既知の現象） |
| 8 | 生の16進色コードを増やしていない（ratchet。`frontend/src/*` の `.css`/`.ts`/`.tsx` が対象で `tokens.css` 自体は対象外＝新規トークン追加そのものを禁止する仕組みではない） | `BASE_SHA=$(git rev-parse origin/main) HEAD_SHA=$(git rev-parse HEAD) bash scripts/check-design-token-ratchet.sh` | `PASS: 対象1ファイル・増加なし`（コミット後に実行した実際の出力。対象は `frontend/src/pages/inbox/InboxPage.css` のみ。`tests-e2e/` 配下は対象パス外） |
| 9 | 未使用トークンの監査 | `npm run audit:unused-tokens` | 新設した `--font-title-mobile` は一覧に含まれない（1箇所で使用されているため「未使用」扱いではない）。既存の未使用29件はこの便と無関係 |

**残るリスク**:
1. §16-2／本便冒頭コメントの「お手本 19.0dp」という記録は、今回の訂正後も文書内の別箇所（§16-2 の表そのもの）には修正を入れていない。混乱を避けるため、§16-2 を読む際はこの §17-10 の訂正を優先する。
2. 実機での最終確認は **2026-10-14 11:25 に実施済み**（PR 4246 マージ・デプロイ後）。本番の受信箱を撮って題字のインク高さを測った結果 **19.3dp**（適用前 18.0dp・お手本の漢字題字「電話」19.0dp）＝**お手本との差は 1.0dp から 0.3dp に縮んだ**。あわせてヘッダー56dp・絞り込みと管理 各44dp・管理の右端が画面右端に接地・検索欄48dp（左右12dp）・行76dp×5件・会話の往復（開く→一覧へ戻る→同じ位置で復帰）に退行がないことを確認した。**スクロール時の固定だけは実機で確認できない**（本番の会話が5件で画面に収まりスクロールが起きないため）＝CI の画面検査が担保する。

## 18. 一覧の行を長押しするとメニューを出す便（2026-10-14・第4便）

> この節は何か（専門用語なしの1行）: スマホで会話一覧の行を長押しすると、「未読にする」「対象外にする」「削除」の3つを選べる小さなメニューが出るようにした作業記録。あわせて「未読にする」を画面上だけの見た目の変更から、サーバに保存する操作に変えた。

### 18-1. PO 決定（2026-10-14）

| 論点 | PO 決定 |
|---|---|
| メニューの中身 | 「未読にする」「対象外にする」「削除」の3つ。**「顧客情報」は入れない**（既読を付けずに開く改修が必要なため、別便） |
| 「未読にする」の保存先 | **サーバに保存する**（従来は画面上だけの変更で再読込で戻っていた）。戻す範囲は**一番新しい受信メッセージ1通だけ**（＝一覧のバッジが1になる）。過去の受信の既読記録は消さない |
| メニューの新設方法 | ADR-144 §4 の手順（金型が無い場合は実装を止めて PO に報告→許可を得て新設）。本便の PO からの指示そのものが §4 の許可にあたる |

### 18-2. 現物で確認済みの事実

| 事実 | 出典 |
|---|---|
| 「未読にする」は API を呼ばず画面上の状態だけ変える（再読込で戻る）＝本便で直す前の挙動 | `frontend/src/pages/inbox/useInboxState.ts:808-813`（変更前） |
| 既読は `meta_messages.seen_at` と `seen_by_staff_id` に入る。mark-read は inbound かつ `seen_at IS NULL` の行に `NOW()` を入れる | `backend/app/routers/leads.py:1133-1211` |
| mark-read の権限は `messaging.view`、監査ログの action は `mark_messages_read` | 同上 |
| 権限名は `messaging.view` と `messaging.send` の2つのみ | `backend/app/` 全文検索 |
| 「対象外」「削除」は API を叩くが、対象は `selectedLeadId` 固定（引数で受け取らない）＝本便で直す前の挙動 | `frontend/src/pages/inbox/useInboxState.ts:815-833`（変更前） |
| 一括版（`handleBulkExclude` 等）は `selectedLeadIds` を使う | `frontend/src/pages/inbox/useInboxState.ts:858-885` |
| 会話一覧（`GET /conversations`）と「直近 inbound」の取得は、どちらも `created_at DESC, id DESC` で最新を決めている | `backend/app/routers/meta_inbox.py:921-931` / `backend/app/routers/leads.py:1083-1086` / `backend/app/routers/leads.py:1786-1791` |
| `.dropdown-menu` / `.dropdown-item` は ADR-069 として登録済み・トークンのみ | `frontend/src/components.css:673-698` |
| 既存の長押しは `frontend/src/pages/inbox/useLongPressReveal.ts`（500ms・pointer events・`pointerType !== "touch"` で早期 return・成立時のみ contextmenu を抑止） | `frontend/src/pages/inbox/useLongPressReveal.ts:1-54` |
| 行の描画は PC とスマホの共通部品 | `frontend/src/pages/inbox/InboxConversationRows.tsx` |
| スマホ専用の組み立ては別ファイル | `frontend/src/pages/inbox/InboxConversationListMobile.tsx` |

### 18-3. 金型新設の根拠（ADR-144 §4・PO 許可）

`docs/adr/ADR-144-ui-component-governance.md` §4「金型がない場合の手順」は、①実装を止めて PO に報告→②PO 許可を得てから `components/` に金型を新設（`Xxx.tsx` + `Xxx.css`（`var()` のみ）+ `Xxx.stories.tsx`）→③登録後にそれを使って実装、の3段階を定める。

本便の指示文（この設計カードの元になった PO からの作業指示）が①の報告と②の許可を兼ねている（「メニューは金型として新設する（ADR-144 §4 の手順。PO 許可は取得済み＝この指示がそれにあたる）」と明記されている）。これに従い `frontend/src/components/ContextMenu.tsx` / `ContextMenu.css` / `ContextMenu.stories.tsx` を新設した。既存の `.dropdown-menu` / `.dropdown-item`（ADR-069）と見た目のトークン（`--bg-surface` / `--border` / `--radius-lg` / `--shadow-dropdown` / `--size-icon-btn-lg` 等）を揃え、異なるのは表示位置の決め方（トリガー要素への相対配置ではなく、長押しした画面座標を基準に画面端で切れないよう収める）だけにした。

長押しの検出も既存の `frontend/src/pages/inbox/useLongPressReveal.ts`（吹き出しのハート表示用・稼働中のため改造しない）とは別に `frontend/src/hooks/useLongPress.ts` を新設した。作法（500ms・pointerdown で計時・up/cancel/leave で取り消し・成立時だけ contextmenu を抑止）は踏襲しつつ、2点変えている: ① `pointerType` で絞り込まない（既存は touch のみで自動検査から叩けないため、マウスでも成立させる）、② pointerdown の座標から10px以上動いたら取り消す（スクロール中に出ないようにするため）。さらに、長押しが成立した直後に続く click を無効化し、押しただけで会話が開いてしまう退行を防いでいる。

### 18-4. 未読を1通だけ戻す理由

PO 決定は「戻す範囲は一番新しい受信メッセージ1通だけ（＝一覧のバッジが1になる）。過去の受信の既読記録は消さない」。これを素直に実装すると、サーバ側で「その lead の inbound のうち最新の1件」だけを選び、その1件だけ `seen_at` / `seen_by_staff_id` を `NULL` に戻す処理になる。複数の既読 inbound を一括で未読に戻す（mark-read の逆の全件版）ではない点が最大の違いで、過去にスタッフが読んだ記録（誰がいつ読んだか）を壊さないという ADR-1008 の趣旨（`seen_by_staff_id` には `users.id` を入れ、既読の事実を残す）を保つ。「最新」の決め方は会話一覧・mark-read の既存実装と同じ `created_at DESC, id DESC` に合わせ、推測で別の列を使っていない（§18-2 参照）。

### 18-5. 受け入れ基準

| # | 基準 | 検証方法 | 結果 |
|---|---|---|---|
| 1 | `POST /leads/{lead_id}/messages/mark-unread` が最新 inbound 1件だけを未読に戻す | `backend/tests/test_messages.py` に6件追加（正常系1件戻る／既に未読0件／outbound のみ0件／lead不在404／他テナント404／権限なし403） | `pytest backend/tests/test_messages.py -v` で**23件成功**（既存17件＋新規6件） |
| 2 | フロントは mark-unread API を呼び、成功したときだけ画面を更新する（サーバを正とする） | `frontend/src/pages/inbox/useInboxState.ts` の `handleMarkUnread` を確認・コードレビュー | 失敗時は catch して画面を変えない実装に変更済み |
| 3 | `handleExclude` / `handleDeleteLead` が対象 leadId を引数で受け取れる。開いている会話でない行を消しても閉じない | 同ファイル。`targetLeadId ?? selectedLeadId` へ変更し、`leadId === selectedLeadId` のときだけ `setSelectedLeadId(null)` | 修正済み（コードレビューで確認） |
| 4 | `InboxMessageThread.tsx:437` の `onClick={handleMarkUnread}` が lead id を引数として渡さない | 同ファイル。`onClick={() => handleMarkUnread()}` に修正 | 修正済み |
| 5 | 新設した金型（ContextMenu）が既存の `.dropdown-menu` と同じトークンのみを使う | `cd frontend && node scripts/check-css-hardcoded-colors.js` / `node scripts/check-css-hardcoded-values.js` | 両方 PASS（違反なし） |
| 6 | 新設した金型に stories がある | `cd frontend && node scripts/check-stories-count.js` | PASS（全49コンポーネントに stories あり） |
| 7 | `npm run check:all` が緑 | `cd frontend && npm run check:all` | 25項目すべて `exited with code 0`（lint は既存warningのみ・error 0件・本変更由来の新規違反なし） |
| 8 | 型が通る | `cd frontend && npx tsc --noEmit` | 本変更由来の新規エラー0件（既存の無関係な4件は `api/generated/schema` 未生成・`SoldOutResultsPanel.tsx` に起因し、本変更の対象ファイルではない） |
| 9 | 単体テストが壊れていない | `cd frontend && npm run test:unit` | 1069件中1057件成功・12件失敗（10ファイル）。失敗ファイルはいずれも受信箱・ContextMenu・useLongPress と無関係（`LeadFormButtonMigration.test.tsx` 等）。個別再実行（`RuleDrawer.test.tsx` 等）では全件成功を確認し、フルスイート実行時の負荷由来のタイムアウトと判断。受信箱関連（`InboxMessageThread.discordSendError.test.tsx` 8件、`src/pages/inbox/` 配下全体47件）は単独実行で全件成功 |
| 10 | デザイントークンの増加なし（ratchet） | `BASE_SHA=$(git rev-parse origin/main) HEAD_SHA=$(git rev-parse HEAD) bash scripts/check-design-token-ratchet.sh`（リポジトリ直下・4本のコミット後に実行） | `PASS: 対象11ファイル・増加なし` |
| 11 | UI ガバナンス（生UI部品の新規ハードコードなし） | `BASE_SHA=$(git rev-parse origin/main) HEAD_SHA=$(git rev-parse HEAD) node scripts/check-ui-governance.js`（4本のコミット後に実行） | `✅ UI governance: 新規ハードコードなし`（対象ファイル数5） |
| 12 | e2e（Playwright）の構文確認 | この端末（arm64/Termux）では chromium が動かないため実行不可。`cd frontend && npx playwright test --list` | 新規6テスト×3幅（vl-mobile-390 / vl-tablet-768 / vl-desktop-1280）を含む**304件**収集成功。実機 Playwright 実行は CI（x86）に委ねる |
| 13 | 長押し・メニューの画面検査を新設した | `frontend/tests-e2e/visual-language/inbox-single-column.spec.ts` に `受信箱 第4便（一覧の行を長押しするとメニューを出す）` を新設（6テスト: メニュー3項目と文言・44px以上・行の近くに出る・はみ出さない／長押しだけでは開かない／普通のタップは開く／外側クリックで閉じる／選択モードでは出ない／mark-unread が呼ばれる） | 追加済み。`npx playwright test --list` で収集確認済み（#12 と同じ結果） |

### 18-6. 残るリスク

1. **実機 Playwright 実行は未確認。** この端末では chromium が起動できないため、`npx playwright test --list` による構文・セレクタ収集の確認までしかできていない。長押しの実際の成立（CDP 経由の `page.mouse.down/up` で座標ベースの長押しを再現する方式）が CI（x86）で本当に動くかは初回実行で初めて分かる。
2. **「顧客情報」を今便のメニューに入れていない。** PO 決定どおり別便（既読を付けずに開く改修）待ち。長押しメニューの項目数が増えたときに `ContextMenu` の `items` 配列を増やすだけで対応できる設計にしてある。
3. **この設計カードの章番号は第1便（§15）・第2便（§16）の次に本節（§18）を置いている。** 本カード内に「第3便」の節が見当たらない（§9付近の表に候補として出てくる「行の密度変更」は別候補でまだ着手されていない）。章番号の欠落（§17 相当）については本便の作業指示で「## 18. として節を作る」と明示されていたため、その指示のとおり §18 とした。欠落が意図的か記録漏れかは本カードの執筆時点では分からないため、PO/設計担当に確認が必要。

## 19. メニューを左側に出し、長押しの文字選択を止める便（2026-10-14・第5便）

> この節は何か（専門用語なしの1行）: 第4便で新設した長押しメニューについて PO から2件の指摘（右側に出て押しづらい・長押しで文字が選択されてしまう）を受け、位置を左側に固定し、文字選択を止める指定を追加した作業記録。

### 19-1. PO 依頼（2026-10-14）

| # | 依頼 |
|---|---|
| 1 | メニューを左側に出してほしい（右側だと押しづらい） |
| 2 | 長押しすると文字選択が出る不具合を直してほしい |

### 19-2. 実機（SC-51G・1080x2340・3倍）で確認済みの事実

| 事実 | 証拠 |
|---|---|
| 長押しでメニューは出る。項目は「未読にする」「対象外にする」「削除」の3つ | 実機の撮影（PO） |
| 長押ししただけでは会話が開かない | 実機の撮影（PO） |
| 「未読にする」は再読込後も未読のまま残る（＝サーバ保存が効いている） | PO が実機で確認 |
| メニューが画面の右半分に出て押しづらい | 実機の撮影（PO）。指で押した x 座標をそのままメニューの左端にしていたため（`frontend/src/components/ContextMenu.tsx` の変更前の `clampPosition`） |
| 長押しすると OS の文字選択が働き、メニューの文字が青く選択され選択ハンドルが出る | 実機の撮影（PO）。指のときだけ起きるため CI（マウス操作）では出ない |

### 19-3. CI では検出できなかったことの教訓

19-2 の文字選択の不具合は、指での長押し（タッチ入力）に対する OS 側の文字選択機能が作動して起きている。`frontend/tests-e2e/visual-language/inbox-single-column.spec.ts` の長押し再現（`longPressRow`）は `page.mouse.down()` / `.up()` によるマウス入力を使っており、OS の文字選択はマウスのドラッグでは発生しない操作系であるため、この不具合は**そもそも CI の対象になっていなかった**（検査が緩かったのではなく、検査の原理上この入力方式では再現し得ない）。したがって本便で CI に追加した `user-select: none` の確認（19-5 の #3）は「指定が CSS として効いていること」の証明にしかならず、「実機で選択が実際に止まること」の証明にはならない。実機確認は PO が行う。

### 19-4. 左端の余白をトークンからどう取ったか（実装方法）

`frontend/src/components/ContextMenu.tsx` に `align?: "point" | "left"`（既定 `"point"`）を追加した（`frontend/src/components/ContextMenu.tsx:59`）。`"point"` は従来どおり指で押した x 座標がそのまま左端になる（既存の見た目は不変）。

`"left"` のときは次の `getLeftAlignMargin()`（`frontend/src/components/ContextMenu.tsx:66`）で `--space-3` トークンの値を読み、画面左端からの余白として使う。

```ts
const DEFAULT_LEFT_ALIGN_MARGIN = 12; // px — --space-3（tokens.css）と同じ値

function getLeftAlignMargin(): number {
  if (typeof window === "undefined" || typeof document === "undefined") {
    return DEFAULT_LEFT_ALIGN_MARGIN;
  }
  const raw = getComputedStyle(document.documentElement).getPropertyValue("--space-3").trim();
  const parsed = Number.parseFloat(raw);
  return Number.isFinite(parsed) ? parsed : DEFAULT_LEFT_ALIGN_MARGIN;
}
```

`--space-3` は `frontend/src/tokens.css:71` で `12px` と定義されており、検索欄の左右の余白（`frontend/src/pages/inbox/InboxPage.css:11` の `padding-left: var(--space-3)`）と同じ値である。CSS 変数は JS から直値で書けないため `getComputedStyle` で実際の値を読む方式にし、読めない場合（テスト環境など）に備えて `DEFAULT_LEFT_ALIGN_MARGIN`（12px・`--space-3` と同じ値）を安全な既定値として用意した。縦位置（`top`）の決め方は `align` に関わらず変えていない（`clampPosition` の `top` 計算はそのまま）。

呼び出し側は `frontend/src/pages/inbox/InboxConversationListMobile.tsx` の `<ContextMenu>` に `align="left"` を渡すだけ（他の画面で `align="point"`（既定）のまま使えば見た目は変わらない）。見本として `frontend/src/components/ContextMenu.stories.tsx` に `AlignLeft` ストーリーを追加した。

### 19-5. 受け入れ基準

| # | 基準 | 検証方法 | 結果 |
|---|---|---|---|
| 1 | `ContextMenu` に `align?: "point" \| "left"`（既定 `"point"`）を追加し、既存の使い方（`align` を渡さない呼び出し）の見た目が変わらない | コードレビュー（`clampPosition` は `align !== "left"` のときのみ従来の右端クランプを行う分岐に変更。`align` 未指定時のデフォルトは `"point"`） | 分岐を確認済み。既存呼び出し側（本便で `align="left"` を渡した1箇所以外）は無い |
| 2 | 左端の余白は生の数値ではなく `--space-3` トークンから取る | コードレビュー（`getLeftAlignMargin()` が `getComputedStyle` で `--space-3` を読む。読めない場合のみ同値のフォールバック `12` を使用） | 実装済み（19-4 参照） |
| 3 | メニューの左端が画面の左から 12px（±1）であること | `frontend/tests-e2e/visual-language/inbox-single-column.spec.ts` の `受信箱 第5便` 内「メニューの左端が画面左から --space-3 の余白に出る」テスト。固定値ではなく `getComputedStyle` で実際の `--space-3` の値を読んで比較 | この端末では Playwright chromium が起動できず実行不可。`npx playwright test --list` で収集成功を確認（19-7 参照） |
| 4 | メニューが画面内に収まっていること（左端0以上・右端がビューポート幅以下・下端が高さ以下） | 同テスト内で継続確認（従来の確認を引き続き実施） | 同上（収集成功のみ確認） |
| 5 | 縦位置は従来どおり押した行の近くに出ること | 同テスト内で `overlapsOrAdjacent` により確認（第4便の既存ヘルパーを再利用） | 同上 |
| 6 | 行（`.conv-item` / `.conversation-item`）とメニュー（`.comp-context-menu`）に `user-select: none` ・ `-webkit-user-select: none` ・ `-webkit-touch-callout: none` を指定する | `frontend/src/pages/inbox/InboxPage.css`（`@media (max-width: 767px)` 内の `.conv-item` ブロック）と `frontend/src/components/ContextMenu.css`（`.comp-context-menu`）にそれぞれ追加 | 実装済み。PC（`@media` の外）には追加していないため PC では文字を選べるまま |
| 7 | 行の指定はスマホ専用 `@media` の内側だけであること（PC は文字選択を保つ） | コードレビュー（`frontend/src/pages/inbox/InboxPage.css` の追加箇所が `@media (max-width: 767px) { .conv-item { ... } }` の内側にあること） | 確認済み（PC 用の `.conv-item` 基底ルールには追加していない） |
| 8 | stylelint が `-webkit-` 接頭辞を弾かないこと | `cd frontend && npx stylelint "src/components/ContextMenu.css" "src/pages/inbox/InboxPage.css"` | 警告・エラーなしで完了（既存コードでも `-webkit-font-smoothing` 等を多数使用しており、`frontend/.stylelintrc.json` に vendor-prefix 禁止ルールは無い） |
| 9 | 行とメニューの `user-select` が `none` であることを機械で確認する | 上記テスト内「行とメニューに user-select: none が指定されている」で `getComputedStyle(el).userSelect` を確認 | この端末では実行不可。`npx playwright test --list` で収集成功を確認のみ |
| 10 | 生の色コード・生の px を書いていないこと | `cd frontend && node scripts/check-css-hardcoded-colors.js` / `node scripts/check-css-hardcoded-values.js` | 両方 PASS（違反なし） |
| 11 | 第4便の既存6テストが緑のままであること | 同ファイル内の既存 `受信箱 第4便` describe は変更していない（新規テストは別の describe として追加） | コードレビューで確認（既存テストのアサーションは不変）。実行は上記と同じ理由で不可 |
| 12 | `npm run check:all` が緑 | `cd frontend && npm run check:all` | 25項目すべて `exited with code 0`（lint は既存warningのみ・error 0件・本変更由来の新規違反なし） |
| 13 | 型が通る | `cd frontend && npx tsc --noEmit` | エラー0件 |
| 14 | 単体テストが壊れていない | `cd frontend && npm run test:unit` | 1072件中1061件成功・11件失敗（9ファイル）。失敗ファイルはいずれも受信箱・ContextMenu と無関係（`OrderLeadButtonMigration.test.tsx` 等）。個別再実行では9ファイル全126件成功を確認し、フルスイート実行時の負荷由来のタイムアウトと判断。`src/pages/inbox/` 配下は単独実行で全27件成功 |
| 15 | デザイントークンの増加なし（ratchet） | `BASE_SHA=$(git rev-parse origin/main) HEAD_SHA=$(git rev-parse HEAD) bash scripts/check-design-token-ratchet.sh`（本便の2コミット後に実行） | `PASS: 対象5ファイル・増加なし` |
| 16 | UI ガバナンス（生UI部品の新規ハードコードなし） | `BASE_SHA=$(git rev-parse origin/main) HEAD_SHA=$(git rev-parse HEAD) node scripts/check-ui-governance.js`（本便の2コミット後に実行） | `✅ UI governance: 新規ハードコードなし`（対象ファイル数1） |

### 19-6. 第4便の既存検査の扱い（判断）

PO からの依頼には「既存の『押した行の近くに出る』検査が右側前提になっていたら、左側に出る前提へ直す」とあった。既存テスト（第4便「行を長押しするとメニューが出て…」内の「4. メニューが押した行の近くに出て、画面からはみ出していない」）を確認したところ、`overlapsOrAdjacent()` は行の矩形とメニューの矩形の X 方向の重なりと Y 方向の近さだけを見る作りで、行（`.conv-item`）は `width: 100%` でスマホ幅いっぱいに広がる（`frontend/src/pages/inbox/InboxPage.css:264` の `.conv-item { width: 100%; }`）。そのため、メニューの左端が画面のどこにあっても（右寄りでも左寄りでも）行の矩形と X 方向で重なり、この既存アサーションは**右側前提ではなかった**と判断し、変更しなかった。新たに追加した「メニューの左端が --space-3 の余白である」確認（19-5 #3）と合わせて、横位置を明示的に検査する体制にした。

### 19-7. 残るリスク

1. **本便で追加・修正した検査（左端位置・user-select）は、この端末では実行確認できていない。** `npx playwright test --list` による収集成功までしか確認できておらず、実機 Playwright（CI・x86）での初回実行結果は未確認（第4便から持ち越しのリスクと同じ）。
2. **`user-select: none` が実機で文字選択を実際に止めるかは未確認。** 19-3 のとおり、この不具合自体がマウス操作の CI では再現しないため、CI が緑になっても実機での解決を保証しない。実機確認は PO が行う。
3. **align="left" は本便で ContextMenu を使う唯一の呼び出し（受信箱・スマホ）にのみ渡した。** 他にこの金型を使う画面が増えたとき、右側に出したい場合は `align="point"`（既定）、左側に出したい場合は `align="left"` を選べるが、画面の中央寄りに出したいなど他の置き方が要る場合は別途 `align` の値を増やす設計判断が必要になる（本便では発生していない）。

## 20. 会話画面のヘッダーを一覧と同じ形にする便（2026-10-14・第6便）

> この節は何か（専門用語なしの1行）: スマホの会話画面にあった帯2本（上の操作行＋会話ヘッダー）を1本に統合し、右端で切れていた旧三点メニューを廃止して、テンプレート・顧客情報・「…」の3つに置き換えた作業記録。

### 20-1. 背景（実機とコードで確認済みの事実）

| 事実 | 出典 |
|---|---|
| スマホの会話画面は帯が2本ある（上: テンプレート/FAQ/受信箱の設定、下: 戻る・顔写真・名前・言語・顧客情報・三点） | 実機の構造データ（2026-10-14） |
| 三点メニューは実機で 27x38dp しかなく画面右端で切れている | 実機実測 |
| 上の帯は `frontend/src/pages/inbox/InboxPage.tsx` の `headerActionsContent`。出し分けは同ファイルの `showHeaderActions` | 同ファイル |
| 会話ヘッダーの入れ物は `frontend/src/pages/inbox/InboxMessageThread.tsx` の `<header className="inbox-center-header">` | 同ファイル |
| 旧三点の中身（未読にする/対象外にする/削除/顧客情報）は第4便で一覧の長押しメニューに移設済み（本番稼働中） | 本カード §18 |
| テンプレートと FAQ はスマホでは上の操作行が唯一の入口（下部タブの「…」にも無い） | `frontend/src/components/MobileShell.tsx` を全文検索して不在を確認（文字列 `templates` / `faq` が出てこない） |
| お手本（WhatsApp）の会話ヘッダーは 56dp・左=戻る48dp＋顔写真48dp＋名前（＋状態の2段）・右=操作2つ（通話メニュー72x48dp・三点40x48dp）で右端に接地 | 実機の構造ダンプ |

### 20-2. PO 決定（2026-10-14）

| 論点 | 決定 |
|---|---|
| 帯の数 | 1本（56dp）にする。スマホでは上の操作行を出さない |
| 右に置く操作 | テンプレート・顧客情報・「…」の3つ（テンプレートと顧客情報は独立したボタンですぐ開ける＝PO 指示） |
| 「…」の中身 | 送信先の言語・FAQ・受信箱の設定 の3つ |
| 送信先の言語 | 「…」から選ぶと下から出るシートで3択（自動／日本語／英語） |
| 旧三点メニュー | スマホでは廃止（中身は長押しメニューへ移設済み） |
| PC・タブレット | 完全に無変更 |

当方が**お手本（2つ）より1つ多い3つ**を右に置いている理由は、お手本が「顧客情報」に相当する操作を持たず、当方は PO 指示で顧客情報をテンプレートと同格の独立ボタンにしたため。お手本の2つ（通話メニュー・三点）に対し、当方は（テンプレート・顧客情報・「…」）の3つになる。

### 20-3. 実装方法

一覧側の先例 `frontend/src/pages/inbox/InboxConversationListMobile.tsx` と同じ考え方で、会話ヘッダーのスマホ版を新規ファイル `frontend/src/pages/inbox/InboxThreadHeaderMobile.tsx` に分離した。

- `frontend/src/pages/inbox/InboxMessageThread.tsx` は `frontend/src/hooks/useIsMobile.ts` の `useIsMobile()` で出し分ける（同ファイルの `isMobile` 変数）。スマホのときだけ `InboxThreadHeaderMobile` を描き、PC・タブレットの `<header className="inbox-center-header">` 以下の JSX は中身を1行も変えていない（三項演算子で分岐を追加したのみ）
- `frontend/src/pages/inbox/InboxPage.tsx` の `showHeaderActions` を `!isMobile` に変更（スマホでは会話を開いていても上の操作行を出さない）
- 受信箱の設定モーダルを開く関数（`useInboxState` の `setShowSettings`）を `onOpenSettings` という新しい prop 名で `InboxPage.tsx` → `InboxMessageThread.tsx` → `InboxThreadHeaderMobile.tsx` の順にそのまま渡した（新しい状態は作っていない。SSOT は `useInboxState.ts` の `showSettings` のまま）
- 「…」は既存の金型 `frontend/src/components/ContextMenu.tsx` を使う。押したボタンの `getBoundingClientRect()` を anchor にする（新しい金型は作っていない）
- 「送信先の言語」は既存の金型 `frontend/src/components/Sheet.tsx` で3択を出す。値の出し入れは既存配線 `recipientLanguageSetting` / `setRecipientLanguage`（`useInboxState.ts` が SSOT）をそのまま使い、新しい状態は作っていない
- 選択肢の見た目（選ぶと閉じる・いま選ばれている値に `active` を付ける）は一覧の絞り込みシート（`frontend/src/pages/inbox/InboxPage.tsx` の `inbox-filter-sheet` / `inbox-filter-sheet-group` / `inbox-filter-sheet-option`）と同じクラス名を再利用した。Sheet.tsx は開閉に関わらず DOM を常にマウントする作り（アニメーションのため）なので、両方のシートが同時に DOM 上に存在する。画面検査では `.comp-sheet-panel--open` が付いた方だけに絞って中の要素を探すことで区別した（`frontend/tests-e2e/visual-language/inbox-single-column.spec.ts` の `openSheetPanel` ヘルパー）
- 寸法トークン: ヘッダー全体 `--topbar-height`（56px）、戻る・顔写真は既存の `.inbox-back-to-list`（`--comp-btn-height-lg` 48px）・`.conv-avatar`（`--size-avatar-lg` 48px）を再利用、右の3つは `--size-icon-btn-lg`（44px）、左の余白は `--space-4`（16px・一覧ヘッダーと同じ値）。右端は一覧ヘッダー（`.inbox-mobile-header` の `padding-right: 0`）と同じ作法で画面右端に接地させた（`frontend/src/pages/inbox/InboxPage.css` の `.inbox-thread-header-mobile`）
- アイコンはすべて既存を再利用（新規追加なし）: テンプレート＝`NAV_ICONS.fileText`、顧客情報＝`PAGE_ICONS.kartePanel`、「…」＝`NAV_ICONS.more`、FAQ＝`NAV_ICONS.help`、受信箱の設定＝`PAGE_ICONS.settingsSolid`、送信先の言語＝`INBOX_ACTION_ICONS.translate`
- 文言はすべて既存の i18n キーを再利用（新規キーなし）: `nav.templates` / `inbox.karteToggle` / `faq.title` / `inbox.settings.title` / `translation.sendGuard.langToggleLabel`（`langAuto` / `langJa` / `langEn`）/ `inbox.backToList` / `inbox.avatarAlt` / `inbox.moreActions`

### 20-4. 幅の計算と実測（PO 指摘事項）

PO から「右に3つ置くと 360dp のうち 戻る48＋顔写真48＋ボタン44×3＝228dp を使い、名前に残るのは約132dp。収まるかは実際に測る」と指摘があった。実装したレイアウトは flexbox で、名前の要素（`.inbox-thread-header-mobile-name`）に `flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis;` を与えているため、固定幅の要素（戻る・顔写真・右の3ボタン）がどれだけ幅を取っても、名前は残りの幅に自動で収まり、ボタン群に重なることは構造上起きない（重ならないことは `frontend/tests-e2e/visual-language/inbox-single-column.spec.ts` の「会話を開くと帯が1本だけになり」テストで、名前の右端が右ボタン群の左端を超えていないことを実測して確認した）。

CI の検査幅は 390px（`vl-mobile-390`）であり、PO が挙げた 360dp の実機とは異なる。390px では固定要素の合計 228px に加えて左余白16px・要素間の gap（`--space-3` 12px×2）を引いても、名前におおむね120px前後が残る計算になる（実測値は上記テストの `testInfo.attach("thread-header-measurements", ...)` に記録される）。実機 360dp では残りがさらに10px程度減る見込みだが、サンプル名（`"Taro Sender"`）・実機の一般的な顧客名であれば `text-overflow: ellipsis` により表示が切れるだけで重なりは起きない。**長い名前が極端に狭い端末幅でどう見えるかの実機確認はしていない**（リスク参照）。

### 20-5. 受け入れ基準

| # | 基準 | 検証方法 | 結果 |
|---|---|---|---|
| 1 | スマホで会話を開いたとき帯が1本であること（`.page-header-actions` が0件） | `frontend/tests-e2e/visual-language/inbox-single-column.spec.ts` の新設テスト | 収集成功（§20-7 参照）。実行は CI に委ねる |
| 2 | 会話ヘッダーの高さが56px（±1） | 同テスト（`--topbar-height` と比較） | 同上 |
| 3 | 戻るボタンが左端（ヘッダーの左 padding の位置）にあり48px以上 | 同テスト（`--space-4` と `--comp-btn-height-lg` の値を実測と比較） | 同上 |
| 4 | 右の3つ（テンプレート・顧客情報・「…」）が各44px以上で、最後のボタンの右端がビューポート右端（±1） | 同テスト | 同上 |
| 5 | 相手の名前が表示され、右のボタン群と重なっていない（名前の右端 ≦ 最初のボタンの左端） | 同テスト（flexbox の構造上保証されることをあわせて実測で確認。§20-4） | 同上 |
| 6 | 「…」を押すと3項目（送信先の言語／FAQ／受信箱の設定）が出る | 同テスト（`受信箱 第6便` describe 内「「もっと」を押すと3項目…」） | 同上 |
| 7 | 「送信先の言語」を押すとシートが開き、選択肢が3つ・各44px以上・選ぶと閉じる | 同テスト（`openSheetPanel` で絞り込みシートと区別。§20-3） | 同上 |
| 8 | PC・タブレットではスマホ用ヘッダーが出ない（`.inbox-thread-header-mobile` が0件）・`.page-header-actions` が1件・言語の `SelectControl` が見える | 同テスト（`受信箱 第6便` describe 内「PC・タブレット: …」） | 同上 |
| 9 | 既存の検査（第4便の長押し6件・第5便の2件・一覧の各件）が緑のまま | `npx playwright test --list` で324件→325件（新規4テスト×3幅=12件追加後の総数の整合）を収集確認。実行結果は CI に委ねる | 収集成功 |
| 10 | 既存の単体テスト `InboxMessageThread.discordSendError.test.tsx` が壊れていない | `npx vitest run --config vitest.unit.config.ts --project unit src/pages/inbox/InboxMessageThread.discordSendError.test.tsx` | 8件成功（`useIsMobile` を `vi.mock` で false 固定に変更。§20-6 参照） |
| 11 | `npm run check:all` が緑 | `cd frontend && npm run check:all` | 25項目すべて `exited with code 0`（lint は既存 warning のみ・error 0件・本変更由来の新規違反なし） |
| 12 | 型が通る | `cd frontend && npx tsc --noEmit` | エラー0件 |
| 13 | 単体テスト全体が壊れていない | `cd frontend && npm run test:unit` | 96ファイル・1082件すべて成功 |
| 14 | デザイントークンの増加なし（ratchet） | `BASE_SHA=$(git rev-parse origin/main) HEAD_SHA=$(git rev-parse HEAD) bash scripts/check-design-token-ratchet.sh` | §20-7 に実際の出力を記載 |
| 15 | UI ガバナンス（生UI部品の新規ハードコードなし） | `BASE_SHA=$(git rev-parse origin/main) HEAD_SHA=$(git rev-parse HEAD) node scripts/check-ui-governance.js` | §20-7 に実際の出力を記載 |

### 20-6. 既存テストへの影響（判断）

1. **`frontend/src/pages/inbox/InboxMessageThread.discordSendError.test.tsx`**: `InboxMessageThread` が `useIsMobile()` を呼ぶようになったため、jsdom（`window.matchMedia` 未実装）でエラーになった。`frontend/src/pages/admin/AdminHubPage.test.tsx` と同じ作法（`vi.mock("../../hooks/useIsMobile", ...)`）でモックし、`false`（非スマホ）を返すよう固定した。このテストは送信エラー表示（PC・タブレットと同じ JSX）の検証なので、非スマホ固定が実態に合う。
2. **`frontend/tests-e2e/visual-language/inbox-single-column.spec.ts` の既存アサーション1件を変更した。** 「スマホ: 一覧ではヘッダーの操作行を出さず、絞り込みはヘッダーの右端に出る」テスト内の「会話を開くと操作行が出ること（返信中に使うため）」という第2便時点の仕様確認（`.page-header-actions` が1件であることを期待）を、第6便の PO 決定（会話を開いても操作行は出さない）に合わせて0件に変更した。これは仕様そのものが変わったための意図的な変更であり、退行ではない。

### 20-7. 実際の検証出力

- `cd frontend && npx tsc --noEmit` → エラー0件
- `cd frontend && npm run lint` → 0 errors, 137 warnings（本変更対象ファイルからの新規警告なし）
- `cd frontend && npm run check:all` → 25項目すべて `exited with code 0`
- `cd frontend && npm run test:unit` → 96 Test Files passed・1082 Tests passed
- `cd frontend && npx vitest run --config vitest.unit.config.ts --project unit src/pages/inbox/InboxMessageThread.discordSendError.test.tsx` → 8件成功
- `cd frontend && npx playwright test --list` → 325 tests in 44 files を収集成功。この端末（arm64/Termux）では chromium が起動できないため実行は不可（CI に委ねる）
- リポジトリ直下 `BASE_SHA=$(git rev-parse origin/main) HEAD_SHA=$(git rev-parse HEAD) bash scripts/check-design-token-ratchet.sh`（本便の2コミット後に実行） → `PASS: 対象5ファイル・増加なし`
- リポジトリ直下 `BASE_SHA=$(git rev-parse origin/main) HEAD_SHA=$(git rev-parse HEAD) node scripts/check-ui-governance.js`（本便の2コミット後に実行） → `✅ UI governance: 新規ハードコードなし`（対象ファイル数4）

### 20-8. 残るリスク

1. **実機 Playwright 実行は未確認。** この端末では chromium が起動できないため、`npx playwright test --list` による構文・セレクタ収集の確認までしかできていない（第4便・第5便と同じ事情）。
2. **極端に狭い端末幅・極端に長い顧客名での実機確認はしていない。** §20-4 のとおり flexbox の構造上重なりは起きない設計だが、CI の検査幅（390px）と PO が指摘した実機幅（360dp）には差があり、360dp 実機での最終確認は別途必要。
3. **会話ヘッダーの Discord 未連携バッジ（`messagesData?.lead?.platform === "discord" && !leadDetail?.discord_user_id` のとき表示される既存バッジ）をスマホ版ヘッダーには含めていない。** 名前の表示幅がただでさえ狭く（§20-4）、バッジを足すとさらに狭くなるため、本便の明示的な構成リスト（戻る→顔写真→名前→テンプレート→顧客情報→「…」）に無いこの要素は含めなかった。Discord 連携状態の確認はカルテ（顧客情報）側で引き続き可能。この判断は実装時の判断であり、PO に確認していない。
4. **顧客情報ボタン（カルテ切替）は既存の `inboxSettings.showRightPanel` 設定で表示を切る。** PO 決定は「テンプレートと顧客情報は独立したボタンですぐ開ける」であり、受信箱の設定で右パネル表示をオフにしている場合にボタン自体を出さない挙動は PC・タブレット版と揃えた既存の配線をそのまま踏襲したもので、本便で新たに判断したものではない。
