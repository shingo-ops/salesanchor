# recon — lp-footer-operator-ja

- 日付: 2026-11-12
- 基準: origin/main e3244a40f
- 依頼: PO 2026-11-12「フッター内の会社情報を日本語にしてくれ」
- 背景: Meta のビジネス認証 6 回目の却下理由は「salesanchor.jp と谷澤 伸吾の関連を確認できない／正式名の表示が必要」。申請画面は「公的記録を検索して実在を確認する」と書いている。公的記録（税務署の書類・インボイス登録）は日本語表記。

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|---|---|
| `lp/src/components/Footer.astro:38` | 見出し `Operator` |
| `lp/src/components/Footer.astro:41` | `HIGH LIFE JPN` |
| `lp/src/components/Footer.astro:42` | `Representative: Shingo Tanizawa (谷澤 伸吾)` |
| `lp/src/components/Footer.astro:43` | 英語の住所 `8-312 Ryokuyoudai, Kuwabara, Okazaki, Aichi 444-2141, Japan` |
| `lp/src/components/Footer.astro:44` | 日本語の住所 `〒444-2141 愛知県岡崎市桑原町字緑陽台8番地312`（既にある） |
| `lp/src/components/Footer.astro:45` | `Invoice Registration No. (適格請求書発行事業者登録番号): T3810449547408` |
| `lp/src/components/Footer.astro:46` | `Phone: +81 90-6072-7767` |
| `lp/src/components/Footer.astro:47-51` | メールのリンク（変えない） |
| `docs/adr/ADR-049-lp-section-completion.md:191` | 「S9 Footer の会社情報（HIGH LIFE JPN / 住所 / 連絡先）は不変」＝中身（屋号・住所・連絡先）を変えない決まり。表記の言語の決まりではない |
| `docs/adr/ADR-047-lp-copy-refocus.md:145` | 会社情報（英語住所）を Footer に統合した経緯 |

- Footer は `lp/src/layouts/BaseLayout.astro` から全ページで使われる（`git grep -l Footer origin/main -- lp/src` の結果は Footer.astro と BaseLayout.astro の2件）。
- LP は i18n の仕組みを持たない（ADR-027 はアプリ frontend の決まり）。

## 既存 ADR 検索

`git grep -n -i -E 'Footer|緑陽台|Operator' origin/main -- docs/adr` → ADR-046 / 047 / 049 / 054。どれも表記の言語を英語に固定する決定はない。ADR-049:191 の「不変」は中身の話で、今回は中身（屋号・氏名・住所・番号・電話・メール）を変えず表記だけを日本語にするため反しない。

## 不明点リスト

- 日本語表記にすることで Meta の審査が通るかは未確認（却下理由の推定に対する対策の1つ）。
