# 設計: スマホの受信箱の配色を「役割ごとの面積比」に揃える

対象 ADR: ADR-067（デザイントークン強制）／ADR-064（Inbox Meta 完全再現・PC のみ）／ADR-144（UI共通部品のガバナンス）
recon: [recon.md](./recon.md)（`docs/handoff/inbox-mobile-polish/recon.md`）
PO 指摘: 2026-10-13「WhatsApp とくらべてチープ感があるのだがプロっぽくできる？金型のデザインが悪い？」／適用範囲の選択「受信箱・スマホだけで試す」

## 1. なぜ直すのか（事実のみ）

recon A・B のとおり、お手本との差は**色の割り当て**に集中している。形（76dp の行・区切り線なし・行全体が押せる）は既に一致している。

直す対象は4点。

| # | 現状（実測） | 目標 |
|---|---|---|
| 1 | 地が2色に割れている（45.9% ＋ 44.0%・差 1.07:1） | **地を1色**にする（お手本は 79.6%） |
| 2 | 行が左12dp・右0dp の非対称 | **左右対称**にする |
| 3 | 12px の副文字が 3.74:1 | **4.5:1 以上** |
| 4 | 吹き出しが系統外（受信=純灰／送信=紫） | 「地・面・強調色」の**3役**に割り当て直す |

## 2. 変更するファイルと、変更前後

`frontend/src/pages/inbox/InboxPage.css` の `@media (max-width: 767px)` の**内側だけ**に5行を足す。**新しいトークンは作らない。**

```css
/* 1. 左だけの余白を外し、下地を面の色に揃えて地を1色にする */
.inbox-wrapper { padding-left: 0; background: var(--bg-surface); }

/* 3. 12px の副文字を本文基準へ */
.conv-time,
.conv-preview-text { color: var(--text-secondary); }

/* 4. 吹き出しを3役に割り当てる */
.msg-bubble.outbound { background: var(--accent); }
.msg-bubble.inbound  { background: var(--neutral-bg); }

/* 5. 状態バッジも面の色に合わせる */
.conv-status-badge { color: var(--text-secondary); background: var(--neutral-bg); }
```

### 2-1. 高さの連鎖を直さない理由（重要な判断）

recon B4 のとおり、地が割れる根因は「一覧の面が画面の高さまで伸びていないこと」。これを直すには `.inbox-wrapper` の `height: 100%` が届く経路（`PageLayout` と `MobileShell` を含む）に手を入れる必要があり、**全ページ共通の部品に波及する**。本便では**下地の色を面の色に揃えるだけ**にして、見た目の目標（地を1色）を満たしつつ波及を避ける。高さの連鎖の整理は別便（PO 判断）。

### 2-2. 受信の吹き出しを白にしない理由

下地を白（`--bg-surface`）にするため、受信を白にすると**白地に白**で消える。`--neutral-bg` は白地で 1.23:1（元の純灰 1.15:1 より見分けやすく、他の面と同じ青みの系統）。

### 2-3. 送信をネイビーにする理由

テーマの強調色は `--accent`（ネイビー）で、未読バッジが既にこれを使っている（recon C1）。送信の吹き出しに同じ色を使うと、**画面の強調色が1系統**にまとまり、お手本の「強調色は画面の1.5〜1.7%」という構造に近づく。紫（`--bubble-outbound-bg`）は PC 側が ADR-064 の範囲なので**スマホでのみ上書き**し、トークン自体は変更しない。

## 3. 触らない範囲（明示）

- **PC・タブレット**: `@media (max-width: 767px)` の内側のみ。768px 以上は1行も変わらない。ADR-064 の Meta 再現（紫の吹き出し・区切り線など）はそのまま。
- **トークン**: `frontend/src/index.css` と `frontend/src/tokens.css` は変更しない（新規追加も値の変更もしない）。
- **高さの連鎖**（`PageLayout` / `MobileShell` / `frontend/src/pages-layout.css`）: 触らない（§2-1）。
- **金型**（`ListRow`）: 置き換えは ADR-144 §5 の別トラック。本便では行わない。
- **API・DB・migrations**: 触らない。

## 4. 守る決まり（CI が検査する）

`check:all`（25項目／`check:css-colors`・`check:css-values`・`check:dark-parity` を含む）／`Lint & Dark Mode Check (ADR-067)`／`画面検査（受信箱 3幅 Playwright）`／`Frontend lint & custom checks`（単体テスト）。

## 5. 検証方法（受け入れ基準）

| # | 基準 | 検証方法 |
|---|---|---|
| 1 | 390px で**行の左右の余白が同じ**（対称） | `frontend/tests-e2e/visual-language/inbox-single-column.spec.ts` で行の `getBoundingClientRect()` の左余白と右余白が一致 |
| 2 | 390px で**12px の副文字の明暗差が 4.5:1 以上** | 同検査で `.conv-preview-text` の文字色と祖先の背景色から比を計算 |
| 3 | 390px で**一覧の面が画面の7割より下まで伸びている**（地が広く残らない） | 同検査で `.inbox-left-panel` の `bottom` が `innerHeight * 0.7` より大きい |
| 4 | **1280px / 768px が不変** | 同検査の PC・タブレット側（操作行1件・絞り込み非表示・モバイル殻0件）が緑のまま |
| 5 | **地が1色**になる（投入後の実測） | 実機で撮り直し、最大の面積比が **70% 以上**（現 45.9%）になること |
| 6 | **系統外の純灰が消える**（投入後の実測） | 実機で撮り直し、受信の吹き出しが `--neutral-bg` の値になること |
| 7 | **強調色が画面に現れる**（投入後の実測） | 送信のある会話で、ネイビーが面積比に現れること |
| 8 | `npm run check:all` 25/25 ／ 単体テスト全件合格 | 実行して出力を PR に貼る |
| 9 | ダークモードで役割が崩れない | `check:dark-parity` が緑（使用トークンはすべて明暗の対を持つ） |

#5〜#7 は**デプロイ後に実機で測って PR に追記**する（画素を数える方法は recon §0 と同じ）。

## 6. 戻し方

このPRの revert のみ。トークン・共有部品・API・DB を変更しないため波及はない。

## 7. 残るリスク（正直に）

1. **下地を白にするのは「色で隠す」対処**で、根因（面が画面の高さまで伸びない）は残る。スクロールの端や将来のレイアウト変更で地が見える可能性がある。根因の整理は別便（§2-1）。
2. **送信の吹き出しがネイビーになるとスマホと PC で見た目が変わる**（PC は ADR-064 の紫）。同じ製品で端末ごとに色が違う状態になる。PC も揃えるなら ADR-064 の改訂起案が必要。
3. **受信の吹き出しは白地で 1.23:1** と、依然として薄い。お手本（Messenger 系）も同程度（1.07:1）なので業界の作法としては範囲内だが、「もっとはっきり」が求められる場合は面の段をもう1つ増やす判断が必要。
4. **未読が無いと強調色は送信の吹き出しだけ**になる。一覧画面に未読が無いときの「芯」は依然として弱い。FAB などの導入は別途 PO 判断。
5. 文字サイズ・太さの段、影、アイコンの太さは**今回測っていない**。別便で同じ尺度で測る。

## 8. 相互参照

- **recon**: [recon.md](./recon.md)（`docs/handoff/inbox-mobile-polish/recon.md`）— A の比較表・B の位置特定・C の自己訂正・E の使えるトークンを前提とする。
- **ADR-067**（デザイントークン強制）: 既存トークンの `var()` 参照のみ。生の値・色コードを書かない。`check:css-colors` / `check:css-values` / `check:dark-parity` が機械的に強制する。
- **ADR-064**（Inbox Meta 完全再現・Accepted）: 対象は **PC（Meta web）**。本便はスマホのみの上書きで、PC の再現値には触れない。PC も揃える場合は改訂起案が必要（§7-2）。
- **ADR-144**（UI共通部品のガバナンス）: 新しい部品を作らない。`ListRow` への移行は別トラック（§3）。
- **お手本の実測**: [../../specs/design-system/visual-language/benchmark/whatsapp-color-structure.md](../../specs/design-system/visual-language/benchmark/whatsapp-color-structure.md)（地79.6% / 面2段 / 強調色1.7% / 主要文字17.9:1）。本便の目標値はここから取っている。
- **直前の作業**: [../app-visual-language/card-stage4b-inbox-mobile.md](../app-visual-language/card-stage4b-inbox-mobile.md) §13（3幅の画面検査）／[../inbox-mobile-header-actions/design.md](../inbox-mobile-header-actions/design.md)（操作行の整理）。同じ検査ファイルに受け入れ基準を足す。

## 9. 外部・過去事例の参照と我々への応用

| 事例 | 何を参照したか | 我々への応用 |
|---|---|---|
| **WhatsApp（Android）の実測** | 明暗を切り替えても**役割ごとの面積比が変わらない**（地79.6% / 面5.2% / 強調1.7%）。面は2段だけ | 「色を選ぶ」のではなく**役割に割り当てる**方針を採用。地を1色にし、面を2段に、強調色を1系統にした |
| **Messenger（Meta）の作法** | 受信の吹き出しは白地に対して 1.07:1 程度のごく薄い面 | 受信を `--neutral-bg`（1.23:1）にした。お手本より少し見分けやすい側に寄せたが、濃くしすぎない |
| **ADR-064（社内の先行事例）** | PC の受信箱は Meta の実測値で再現済み（紫の吹き出しを含む） | PC には触らず、スマホのみ上書きする判断の根拠にした |
| **#4147（社内の直前事例）** | `ListRow` 金型で `--text-muted`（12px で 4.0:1）を `--text-secondary` に替えた | 同じ判断を `.conv-item` 側にも適用した（金型と素の実装で基準を揃える） |

**採用しなかったもの**: 新しい面のトークンを足す案は採らない（既存の `--neutral-bg` で役割が足りる）。高さの連鎖を直す案も本便では採らない（共有部品に波及・§2-1）。

## 10. 維持の仕組み

- 守り手: `frontend/tests-e2e/visual-language/inbox-single-column.spec.ts`（受け入れ基準 #1〜#4 を3幅で検査）、`.github/workflows/e2e.yml` のジョブ `visual-language`、`frontend/package.json` の `check:all`（`check:css-colors` / `check:css-values` / `check:dark-parity` を含む25項目）。
- 対象: 左右の余白の非対称の再発、12px 文字のコントラスト低下、一覧の面が縮むこと、PC・タブレットへの波及、色コードの直書き、明暗の対の欠落。
- 関所が無い部分: **面積比（地が70%以上など）は機械で検査していない。** 画素を数える検査は作業端末で実行できず、CI でも撮影した画像の統計を取る仕組みを入れていない。**投入後に実機で測って PR に記録する**運用で守る（#5〜#7）。将来 CI でスクリーンショットの色統計を取るなら、そのときに検査へ移す。
