# recon: LP 運営者表示に正式名称（漢字）と日本語住所を足す

> この文書は何か: ホームページ（LP）のどこに運営者名が出ているかを、変更前の実物で数えた調査記録。
> 親: [docs/handoff/whatsapp-intake/README.md](../README.md)　子: [design.md](design.md)

実測時の origin/main SHA: 0c23808ecc5ca662f6ca66549c39f53679f08e45

## 既存 ADR 検索
- `git grep -il "operator\|運営者\|legal" docs/adr` の該当: docs/adr/ADR-1044-lp-meta-application-only.md（LP の事業者住所・電話を Meta 登録と一致させる。noindex。本便の前提。住所の英語表記は維持）。docs/adr/ADR-046-lp-redesign.md、docs/adr/ADR-049-lp-section-completion.md は上書き済み（ADR-1044 の表参照）。

## 運営者名・代表者名が出る箇所（変更前）
- lp/src/components/Footer.astro:41 HIGH LIFE JPN
- lp/src/components/Footer.astro:42 Representative: Shingo Tanizawa
- lp/src/components/Footer.astro:43 8-312 Ryokuyoudai, Kuwabara, Okazaki, Aichi 444-2141, Japan
- lp/src/components/Footer.astro:44 Phone: +81 90-6072-7767
- lp/src/pages/index.astro:842 Operated by HIGH LIFE JPN (Representative: Shingo Tanizawa)
- lp/src/pages/privacy.astro:13 Operated by: ... (Representative: Shingo Tanizawa)
- lp/src/pages/privacy.astro:33 Representative: Shingo Tanizawa
- lp/src/pages/privacy.astro:36 Address: 8-312 Ryokuyoudai, ...
- lp/src/pages/privacy.astro:44 Data Protection Officer: Shingo Tanizawa (Representative)
- lp/src/pages/privacy.astro:408 Representative: Shingo Tanizawa
- lp/src/pages/privacy.astro:411 Data Protection Officer: Shingo Tanizawa
- lp/src/pages/terms.astro:13 Operated by: ... (Representative: Shingo Tanizawa)
- lp/src/pages/terms.astro:341 Representative: Shingo Tanizawa
- lp/src/pages/terms.astro:345 Address: 8-312 Ryokuyoudai, ...
- lp/src/pages/data-deletion.astro:89 Operated by: ... (Representative: Shingo Tanizawa)
- lp/scripts/og-image.html:104 HIGH LIFE JPN（屋号のみ・人名なし。対象外）

## 共通定数・多言語辞書
- 運営者名を1か所にまとめる定数・データ: 無し（`grep -rn "Tanizawa" lp/src` は上記の直書きのみ）。
- ja/en の辞書: LP 側には無し（英語の直書き）。新しい仕組みは作らない。
- Footer は全ページ共通部品のため、住所・電話は index/pricing/privacy/terms/data-deletion/deletion-status/404 の全 7 ページに出る。

## デプロイ経路
- .github/workflows/deploy.yml:3-6 `on: push: branches: main`。同:24-26 LP build、同:99-108 `rsync -avz --delete lp/dist/` で VPS へ。= main マージで本番へ自動反映。
- 本便は migrations/・deploy.yml・本番 scripts/ を触らない（lp/ と docs/handoff/ のみ）。危険パスに当たらない。ただし deploy.yml は main push のたびに全体が走る（backend 変更検出ゲート deploy.yml 内 paths-filter は migrations/** と scripts/** のみ）。
