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

`.inbox-conversation-list` が `flex: 1` ＋ `min-height: 0` で自分だけスクロールを受け持つため、親の `.inbox-left-panel` はちょうど収まる高さのまま＝`scrollHeight === clientHeight` になる。`.inbox-mobile-header` と `.inbox-mobile-search-row` はこの `.inbox-conversation-list` の**外**（flex の兄弟要素として前）にあるため、**そもそも最初からスクロールで動かない**。これは第2便（ヘッダー新設）の時点から変わっていない構造上の事実であり、何かを固定する実装を新たに追加する必要はなかった。

**2度目の推測の反省**: 検査を書き直す際、いったん「スクロール箱は `.inbox-conversation-list`」と要素名を決め打ちした版を作った。しかし「どの要素名を使うか」を決め打ちする設計は、1度目の `.inbox-left-panel` のときと同じ失敗パターン（将来構造が変わったときに追従できない）を繰り返す。そのため `frontend/tests-e2e/visual-language/inbox-single-column.spec.ts` の最終版（§17-6）では、要素名を書かずに「`scrollHeight > clientHeight` かつ `overflow-y` が `auto`/`scroll` である最初の祖先」をブラウザ内で実際に探して使う形に直した。

### 17-4. 対応: sticky の指定を撤回

`frontend/src/pages/inbox/InboxPage.css` の `.inbox-mobile-header` から、§17-2 で追加した `position: sticky; top: 0; z-index: var(--z-base); background: var(--bg-surface);` とその直前のコメントを削除した。**効果を示せないコードは入れない方針**のため（ヘッダーは `.inbox-conversation-list` の外にあり、sticky は何もしない）。

題字の `--font-title-mobile` 化（§17-10）はこの訂正と無関係の別件のため、そのまま残している。

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
| 1 | 効果のない `position: sticky` を撤回した | `frontend/src/pages/inbox/InboxPage.css` の `.inbox-mobile-header` から sticky 関連4行とコメントを削除 | 修正済み（コードレビューで確認） |
| 2 | 新テストが本当のスクロール箱（`.inbox-conversation-list`）を基準にしている | `inbox-single-column.spec.ts` の該当テストを書き直し | 修正済み（§17-6） |
| 3 | 題字の文字サイズ（§17-10）は変更していない | `--font-title-mobile` と `.inbox-mobile-header-title` の変更箇所は無変更 | 変更なしを確認済み |
| 4 | 既存の画面検査が壊れていない | `npx playwright test --list` で収集確認（この端末では実行不可のため構文確認のみ） | §6 に実行結果を記載 |
| 5 | `npm run check:all` が緑 | `cd frontend && npm run check:all` | §6 に実行結果を記載 |
| 6 | 型が通る | `cd frontend && npx tsc --noEmit` | §6 に実行結果を記載 |
| 7 | 単体テストが壊れていない | `cd frontend && npm run test:unit` | §6 に実行結果を記載 |

### 17-9. 残るリスクと教訓

1. **教訓（再発防止）**: 「スクロールする箱」をCSSの一箇所（`.inbox-left-panel` の `overflow-y: auto`）だけで判断し、実際に中身があふれるかを確認しなかったことが誤りの原因だった。次に同種の判断をするときは、対象要素の `scrollHeight > clientHeight` を実測するか、その箱の子要素に別の `overflow` 指定がないかを必ず確認する。**この教訓を検査そのものにも適用し**、書き直した検査では「スクロール箱は `.inbox-conversation-list`」という2度目の決め打ちもやめ、要素名を書かずに実際にスクロールしている祖先をブラウザ内で探す形にした（§17-3・§17-6）。
2. **Playwright をこの端末で実行できない。** `npx playwright test --list` で構文とセレクタの収集は確認したが、実際に assertion が通るかは CI（x86）の初回実行で初めて分かる。
3. **検索欄もヘッダーと同じく固定側になっている（§17-7）。** お手本と一致していない。直すかどうかは PO 判断待ち。
4. **実機での確認は未実施。** 今便は構造の訂正のみで見た目の変更はないが、CI（x86）で新テストが実際に通ることは別途確認が必要。

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
2. 実機（Android Chrome）での最終確認は未実施。21pxでの見た目（インク高さ・行間）は計算上の推定であり、本番反映後に実測で裏取りする必要がある。
