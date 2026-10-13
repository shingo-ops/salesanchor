# 設計: 一覧の名前に大きさと太さの段差を付ける（文字の段の仕上げ）

対象 ADR: ADR-067（デザイントークン強制）／ADR-064（Inbox Meta 完全再現・PC のみ）／ADR-144（UI共通部品のガバナンス）
recon: [recon.md](./recon.md)（`docs/handoff/inbox-mobile-type-scale/recon.md`）
PO 指示: 並べた「次にできること」を順番に進める（1番目＝残りの見た目の測定）。測定の結果、打ち手があるのは**文字の段**のみだった。

## 1. なぜ直すのか（事実のみ）

recon A のとおり。

| 指標 | お手本（実測） | 当方（CSS 実値） |
|---|---|---|
| 名前と本文の大きさの比 | **1.32 倍**（日付28px / 名前37px・同じ文字種） | **1.2 倍**（14.4px / 12px） |
| 名前と本文の太さの差 | **1.5 倍**（線幅 6.0px / 4.0px） | **差なし**（どちらも 400） |

**太さの差が無いことが最大の差**。既読の行では名前と本文が同じ太さ・近い大きさで並ぶため平坦に見える。

影（recon B）は一覧に使っておらずお手本と同じ＝**原因ではない**。アイコンの太さ（recon C）は**ライブラリ固定で変える手段が無い**。ダークモード（recon D）は**コントラストの確認のみ**を検査で行う。

## 2. 変更するファイルと、変更前後

### 2-1. `frontend/src/pages/inbox/InboxPage.css`（`@media (max-width: 767px)` の内側のみ）

```css
.conv-name {
  font-size: var(--font-md);              /* 14.4px → 16px */
  font-weight: var(--font-weight-semi);   /* 400 → 600 */
}
```

- **16 ÷ 12 = 1.33** で、お手本の 1.32 倍に一致する。
- 太さ 600 で本文（400）との差が付く。**未読の 700（`.conv-name.unread`）はそのまま**なので未読との区別は保たれる。
- **文字を小さくする方向は採らない**（読みにくくなる）。
- 新しいトークンは作らない（`--font-md` と `--font-weight-semi` は既存）。

### 2-2. `frontend/tests-e2e/visual-language/inbox-single-column.spec.ts`

検査を1件追加。

1. **大きさの段差**: 名前 ÷ 本文 の `font-size` が **1.3 以上**（お手本 1.32）
2. **太さの段差**: 名前の `font-weight` が本文より大きい
3. **ダークモードのコントラスト**: `force-dark` を**検査の中だけで**付け、名前と本文の明暗差が **4.5:1 以上**であること（DB には触らない・recon D）
4. 実測値は `type-scale` と `dark-mode-contrast` として記録に残す

## 3. 触らない範囲（明示）

- **PC・タブレット**: `@media (max-width: 767px)` の内側のみ。PC の会話名は ADR-064 の Meta 実測値（15px）の範囲なので触らない。
- **未読の太さ**（`.conv-name.unread` の 700）: そのまま。
- **影**: 触らない（recon B）。
- **アイコン**: 触らない（recon C。変えるならアイコン一式の差し替え＝別途 ADR 級の判断）。
- **利用者の保存設定（`users.theme`）**: 一切書き換えない。ダークモードの測定は検査の中で `force-dark` を付けて行う。
- **トークン**: 追加・変更しない。
- **API・DB・migrations**: 触らない。

## 4. 守る決まり（CI が検査する）

`check:all`（25項目）／`Lint & Dark Mode Check (ADR-067)`／`画面検査（受信箱 3幅 Playwright）`／`Frontend lint & custom checks`（単体テスト）。

## 5. 検証方法（受け入れ基準）

| # | 基準 | 検証方法 |
|---|---|---|
| 1 | 390px で**名前が本文の 1.3 倍以上の大きさ** | `frontend/tests-e2e/visual-language/inbox-single-column.spec.ts` で `font-size` の比 |
| 2 | 390px で**名前が本文より太い** | 同検査で `font-weight` の比較 |
| 3 | **ダークモードで名前と本文の明暗差が 4.5:1 以上** | 同検査で `force-dark` を付けて計算（DB 非接触） |
| 4 | 実測値が**記録に残る** | 同検査の `type-scale` / `dark-mode-contrast` 添付 |
| 5 | **1280px / 768px が不変** | 同検査の PC・タブレット側が緑のまま |
| 6 | 既存の基準がすべて緑のまま | 同ファイルの既存5件（1画面1ページの往復・上部バー無し・操作行の出し分け・地が1色・面が下端まで） |
| 7 | `npm run check:all` 25/25 ／ 単体テスト全件合格 | 実行して出力を PR に貼る |
| 8 | **投入後の実機で名前の線が太くなる** | デプロイ後に線の太さを測り PR に追記（お手本は名前 6.0px / 本文 4.0px） |

## 6. 戻し方

このPRの revert のみ。トークン・共有部品・API・DB を変更しないため波及はない。

## 7. 残るリスク（正直に）

1. **名前が 16px になり行の中身が高くなる。** 行の高さは `--min-height-conv-item-mobile`（76px）で、現状 14.4px + 12px + 余白で収まっている。16px でも収まる計算だが、**長い名前で折り返しや切れ方が変わる可能性**がある（`.conv-name` は `white-space: nowrap; text-overflow: ellipsis` なので切れ方が変わるだけで崩れはしない）。実機で確認する。
2. **既読と未読の差が縮む**（600 vs 700）。未読の見分けは太さだけでなく未読バッジ（`--accent` のネイविー）もあるため、区別は残る。実機で確認する。
3. **アイコンの太さは未対応**（recon C）。見た目の印象に残る要素だが、ライブラリ固定のため本便では扱えない。
4. **ダークモードは画面検査のコントラストのみ**で、実機の面積比は測っていない（DB を書き換えないため）。実機で測るには PO の許可が必要。

## 8. 相互参照

- **recon**: [recon.md](./recon.md)（`docs/handoff/inbox-mobile-type-scale/recon.md`）— A の文字の段（お手本の線の太さ・同じ文字種での比較・当方の CSS 実値）、B の影、C のアイコン、D のダークモードの切替機構、E の使えるトークン。
- **ADR-064**（Inbox Meta 完全再現・Accepted）: 対象は **PC**。会話名15px という Meta 実測値を持つため、PC 側は触らない。スマホのみ上書きする。
- **ADR-067**（デザイントークン強制）: 既存トークン（`--font-md` / `--font-weight-semi`）の `var()` 参照のみ。新規追加なし。`check:css-values` が生の値を機械的に弾く。
- **ADR-144**（UI共通部品のガバナンス）: 新しい部品を作らない。`.conv-item` から `ListRow` 金型への移行は別トラック（§3）。
- **直前の便**: [../inbox-mobile-polish/design.md](../inbox-mobile-polish/design.md)（配色）／[../inbox-mobile-fill-height/design.md](../inbox-mobile-fill-height/design.md)（面を下端まで）。同じ検査ファイルに基準を足す。
- **お手本の実測**: [../../specs/design-system/visual-language/benchmark/README.md](../../specs/design-system/visual-language/benchmark/README.md)（行76dp・区切り線なし・配色の面積比）。本便の比率（1.32倍）は今回の追加測定で得た。

## 9. 外部・過去事例の参照と我々への応用

| 事例 | 何を参照したか | 我々への応用 |
|---|---|---|
| **WhatsApp（Android・ライト）の実測** | 名前の線 6.0px / 本文 4.0px（1.5倍）・名前は日付の 1.32 倍 | 名前を 16px/600 にして段差を作った。比率をお手本に合わせた |
| **Meta Business Suite の実測（ADR-064）** | PC の会話名は15px・日付13px | PC には触らない判断の根拠 |
| **PR 4147（社内の先行事例）** | `ListRow` 金型で 12px の文字に `--text-secondary` を使う判断をした | 同じ基準を `.conv-item` 側にも適用済み（PR 4184）。本便は大きさ・太さの段差を足す |
| **PR 4196（直前の自分の便）** | 「検査が緑でも目標未達」を避けるため、**実測値を記録に残す**設計にした | 本便も `type-scale` / `dark-mode-contrast` を記録に残す |

**採用しなかったもの**: 時刻や本文を小さくする案（読みにくくなる）。アイコンの太さを変える案（ライブラリ固定・ADR 級）。実機でダークモードを測る案（利用者の保存設定を書き換えるため。必要なら PO の許可を得てから）。

## 10. 維持の仕組み

- 守り手: `frontend/tests-e2e/visual-language/inbox-single-column.spec.ts`（基準 #1〜#6 を3幅で検査。実測値を添付で記録）、`.github/workflows/e2e.yml` のジョブ `visual-language`、`frontend/package.json` の `check:all`（25項目）。
- 対象: 名前と本文の段差が消えること（大きさ・太さ）、ダークモードでのコントラスト不足、PC・タブレットへの波及、生の値の直書き。
- 関所が無い部分: **実機の線の太さ（6.0px 相当か）は機械で検査していない。** CI でスクリーンショットの画素統計を取る仕組みが無いため、**投入後に実機で測って PR に記録する**運用で守る（基準 #8）。アイコンの太さとダークモードの面積比も検査対象外（§7-3・§7-4）。
