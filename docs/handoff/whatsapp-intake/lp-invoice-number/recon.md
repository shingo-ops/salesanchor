# recon: LP 運営者表示に適格請求書発行事業者登録番号を足す

> この文書は何か: ホームページ（LP）の住所が出ている場所を、変更前の実物で数えた調査記録。
> 親: [docs/handoff/whatsapp-intake/README.md](../README.md)　子: [design.md](design.md)

実測時の origin/main SHA: 205dfdeabbefd713c8d17986ed6e46a8fb18d2ff（PR #4822 マージ後）

## 既存 ADR 検索
- 該当: docs/adr/ADR-1044-lp-meta-application-only.md（LP の事業者住所・電話を Meta 登録と一致させる。noindex。本便の前提）。登録番号に関する ADR は無し。

## 登録番号の根拠
- 国税庁 適格請求書発行事業者公表サイト https://www.invoice-kohyo.nta.go.jp/regno-search/detail?selRegNo=3810449547408 で「氏名又は名称 谷澤 伸吾・登録年月日 令和5年10月1日」を Opus が確認済み（公表情報）。
- PO 承認 2026-10-27 PO「納税者識別番号 T3810449547408も加えておいて」。

## 日本語住所が出る箇所（変更前。登録番号はこの直後に足す）
- `lp/src/components/Footer.astro:44` `<li>〒444-2141 愛知県岡崎市桑原町字緑陽台8番地312</li>`
- `lp/src/pages/privacy.astro:37` `住所: 〒444-2141 …8番地312</p>`（段落末。`<br>` を足して次行に置く）
- `lp/src/pages/terms.astro:346` `住所: 〒444-2141 …8番地312<br>`

## 共通定数・辞書
- 無し（lp-legal-name と同じ。直書き）。Footer は全ページ共通のため全 7 ページに出る。

## デプロイ経路
- `.github/workflows/deploy.yml:3`（main push）、`.github/workflows/deploy.yml:108`（lp/dist を rsync）。= main マージで本番へ自動反映。本便は lp/ と docs/handoff/ のみで危険パスに当たらない。
