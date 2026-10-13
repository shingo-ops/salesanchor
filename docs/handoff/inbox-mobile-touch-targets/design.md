# 設計: スマホの主要な操作ボタンを44px以上にする（第2便）

対象 ADR: ADR-067（デザイントークン強制）／ADR-064（Inbox Meta 完全再現・PC のみ）／ADR-144（UI共通部品のガバナンス）
recon: [recon.md](./recon.md)（`docs/handoff/inbox-mobile-touch-targets/recon.md`）
PO 指示: 並べた「次にできること」を順番に進める（2番目＝押す場所を44px以上に）。

## 1. なぜ直すのか（事実のみ）

recon A のとおり、スマホで 44px 未満の操作ボタンが5つある（28px×2・36px×2・32px×1）。WCAG 2.5.5（ターゲットサイズ）の基準は 44x44px。`frontend/src/tokens.css` には**既に `--size-icon-btn-lg: 44px`**（コメントに「モバイルタッチターゲット基準 WCAG 2.5.5」）が登録されている。

## 2. 変更するファイルと、変更前後

### 2-1. `frontend/src/pages/inbox/InboxPage.css`（`@media (max-width: 767px)` の内側のみ）

**ピルの外側にある3つ**を 44px にする。

```css
.inbox-send-btn            { width: var(--size-icon-btn-lg); height: var(--size-icon-btn-lg); }  /* 32px → 44px */
.inbox-thread-action-btn   { width: var(--size-icon-btn-lg); height: var(--size-icon-btn-lg); }  /* 36px → 44px */
.icon-btn.inbox-mobile-filter-toggle { width: var(--size-icon-btn-lg); height: var(--size-icon-btn-lg); }  /* 36px → 44px */
```

- `.inbox-send-btn` はスマホで `--size-avatar-sm`（32px）に**縮めていた**指定を置き換える。
- `.inbox-mobile-filter-toggle` は **2クラス**で指定する（recon E の詳細度）。
- 新しいトークンは作らない。

### 2-2. `frontend/tests-e2e/visual-language/inbox-single-column.spec.ts`

検査を1件追加。一覧で絞り込み、会話で送信とスレッドの操作を測り、**44px 以上**を基準にする。**ピル内の添付ボタンの値も記録に残す**（本便では未対応であることを数字で残す）。

## 3. 触らない範囲（明示）

- **ピルの内側の2つ**（`.send-attach-btn` 28px / `.send-preview-remove` 28px）: **触らない**（§7-1 の判断待ち）。
- **PC・タブレット**: `@media (max-width: 767px)` の内側のみ。PC は ADR-064 の Meta 実測値の範囲。
- **トークン**: 追加・変更しない。
- **`frontend/src/components.css` の `.icon-btn`**: 触らない（全ページ共通）。
- **API・DB・migrations**: 触らない。

## 4. 守る決まり（CI が検査する）

`check:all`（25項目）／`Lint & Dark Mode Check (ADR-067)`／`画面検査（受信箱 3幅 Playwright）`／`Frontend lint & custom checks`（単体テスト）。

## 5. 検証方法（受け入れ基準）

| # | 基準 | 検証方法 |
|---|---|---|
| 1 | 390px で**絞り込みが 44px 以上** | `frontend/tests-e2e/visual-language/inbox-single-column.spec.ts` で `boundingBox()` |
| 2 | 390px で**送信ボタンが 44px 以上** | 同検査（会話を開いた状態） |
| 3 | 390px で**スレッドの操作ボタンが 44px 以上** | 同検査（会話を開いた状態） |
| 4 | **ピル内の添付ボタンの値が記録される** | 同検査の `touch-targets` 添付（本便では未対応の明示） |
| 5 | **1280px / 768px が不変** | 同検査の PC・タブレット側が緑のまま |
| 6 | 既存の基準がすべて緑のまま | 同ファイルの既存6件 |
| 7 | `npm run check:all` 25/25 ／ 単体テスト全件合格 | 実行して出力を PR に貼る |
| 8 | **投入後の実機で3つが 132px 以上**（device px・44dp×3） | デプロイ後に構造データの座標で測り PR に追記 |

## 6. 戻し方

このPRの revert のみ。トークン・共有部品・API・DB を変更しないため波及はない。

## 7. 残るリスク（正直に）

1. **ピルの内側の2つ（28px）は未対応。** 44px にするとピルの高さが最低 60px になり入力1行に対して膨らむ（recon C2）。当たり判定だけ広げると**左隣の入力欄に 8px 重なる**（recon C3）。お手本は**操作ボタンを全て 48dp にして行自体を高くしている**（recon C4）。**どれを採るかは見た目と操作の両方に影響するため PO 判断を仰ぐ。**
2. **送信ボタンが 32px → 44px になり送信行が高くなる。** 行の高さはピル（約40px）と送信ボタンのうち高い方で決まるため、**約4px 高くなる**見込み。会話に使える高さがその分減る。実機で確認する。
3. **絞り込みが 36px → 44px になり検索欄の行が高くなる。** 検索欄は約40px なので、**約4px 高くなる**見込み。一覧に使える高さがその分減る。実機で確認する。
4. **スレッドの操作ボタンが 36px → 44px になり会話の上部バーが高くなる可能性。** 上部バーには戻るボタン（48px）もあるため、48px より小さいうちは行の高さは変わらない見込み。実機で確認する。

## 8. 相互参照

- **recon**: [recon.md](./recon.md)（`docs/handoff/inbox-mobile-touch-targets/recon.md`）— A の対象と実値、B の既存トークン、C の送信エリアの構造とピルが膨らむ理由、D の既存計測との関係、E の詳細度の注意。
- **ADR-067**（デザイントークン強制）: 既存トークン `--size-icon-btn-lg` の `var()` 参照のみ。新規追加なし。
- **ADR-064**（Inbox Meta 完全再現・Accepted）: 対象は PC。スマホのみ上書きする。
- **ADR-144**（UI共通部品のガバナンス）: 新しい部品を作らない。`frontend/src/components.css` の `.icon-btn`（全ページ共通）には触らず、受信箱のスマホ幅だけで上書きする。
- **段階1の実測**: [../app-visual-language/stage1-baseline.md](../app-visual-language/stage1-baseline.md)（390px で 44px 未満の部品が 33/52 件）。本便はそのうち受信箱の主要3つを解消する。
- **お手本の実測**: [../../specs/design-system/visual-language/benchmark/README.md](../../specs/design-system/visual-language/benchmark/README.md)（入力欄の操作ボタンは全て 48x48dp／一覧は行全体を押させる）。
- **直前の便**: [../inbox-mobile-type-scale/design.md](../inbox-mobile-type-scale/design.md)（文字の段）。同じ検査ファイルに基準を足す。

## 9. 外部・過去事例の参照と我々への応用

| 事例 | 何を参照したか | 我々への応用 |
|---|---|---|
| **WhatsApp（Android）の実測** | 入力欄の操作ボタンは**全て 48x48dp**。一覧は**行全体**を押させる（部品を大きくするのではなく行で受ける） | ピルの外側の3つを 44px にした。ピルの内側は「行を高くする」お手本の作りに倣うかを PO 判断に回した |
| **WhatsApp 自身の例外** | WhatsApp にも 44dp 未満の押せる部品がある（︙が 40x48dp・アップデートタブで11件） | **ゼロを目的にしない**。主要な導線を優先する方針の根拠 |
| **段階1の実測（社内）** | 390px で 44px 未満が 33/52 件 | 受信箱の主要3つから着手する（全部を一度に変えない） |
| **PR 4179（直前の社内事例）** | `.icon-btn` との詳細度争いで単一クラスの指定が負けた | `.icon-btn.inbox-mobile-filter-toggle` と**2クラス**で書いた |

**採用しなかったもの**: ピル内のボタンを 44px にする案（ピルが膨らむ）。当たり判定だけ広げる案（入力欄に重なる）。`frontend/src/components.css` の `.icon-btn` を大きくする案（全ページに波及）。

## 10. 維持の仕組み

- 守り手: `frontend/tests-e2e/visual-language/inbox-single-column.spec.ts`（基準 #1〜#6 を3幅で検査。値を `touch-targets` として記録）、`.github/workflows/e2e.yml` のジョブ `visual-language`、`frontend/package.json` の `check:all`（25項目）。
- 対象: 3つのボタンが 44px 未満に戻ること、PC・タブレットへの波及、生の値の直書き。
- 関所が無い部分: **ピル内の2つ（28px）は未対応のまま**で、検査は値を記録するだけ（合否にしない）。方針が決まった時点で基準に昇格させる。既存の `frontend/tests-e2e/visual-language/inbox-baseline.spec.ts` は 44px 未満の部品を記録し続けるので、残りの件数は毎回見える。
