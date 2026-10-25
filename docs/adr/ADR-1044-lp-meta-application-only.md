# ADR-1044: LP は Meta 申請用：検索に載せない・事業者情報を Meta 登録と一致させる

| 項目 | 内容 |
|------|------|
| ステータス | Accepted（2026-10-25） |
| 備考 | PO 2026-10-25 チャット「1を進める、ただしLPやホームページは外部検索でヒットしないようにして、あくまで申請用に作っているので」。「1」は「Meta の登録住所（愛知県岡崎市）に LP を合わせ、電話番号も載せる」 |
| 起案日 | 2026-10-25 |
| 方針の決定者 | Shingo（PO） |
| 関連 | ADR-017（robots.txt）、ADR-054（LP 再構成）、ADR-046（LP 再設計）、ADR-049（LP セクション完成） |
| 設計 | `docs/handoff/lp-application-only/design.md`、現状 `docs/handoff/lp-application-only/recon.md` |

---

## What（何を決めたか）

1. LP（`lp/`）の事業者住所を `8-312 Ryokuyoudai, Kuwabara, Okazaki, Aichi 444-2141, Japan` の1つの表記にそろえる（`lp/src/components/Footer.astro`、`lp/src/pages/privacy.astro`、`lp/src/pages/terms.astro`）。
2. 電話番号 `+81 90-6072-7767` を、上記3か所の住所のすぐ下に載せる。
3. LP の全ページに `<meta name="robots" content="noindex, nofollow" />` を出す。`lp/src/layouts/BaseLayout.astro` と `lp/src/layouts/LegalLayout.astro` の `noindex` 既定値を `true` にする。
4. `lp/public/robots.txt` は変えない（Disallow を足さない）。nginx と GitHub Actions のワークフローも触らない。
5. 今後 LP のページを足すときは、BaseLayout を通る限り自動で noindex になる。noindex を外す場合は、この ADR の変更が必要。

## Why（なぜ）

- Meta のビジネス認証では、申請した住所・電話番号とホームページの表示の一致が見られる（外部の解説記事に共通する説明。Meta 公式の明文は未確認）。
- LP は集客用ではなく Meta の申請用なので、検索エンジンに載せる必要がない。
- robots.txt に Disallow を足すと、検索エンジンが noindex の印を読めなくなる。Meta のクローラー（facebookexternalhit）がプライバシーポリシーの URL を確かめるときにも支障が出る。ADR-017 の決定とも食い違う。

## 上書きする既存の決定

既存の ADR 本文は書き換えず、この ADR から参照するだけにする。

| 既存の決定 | 場所 | この ADR での扱い |
|---|---|---|
| 電話番号を追加しない | `docs/adr/ADR-054-lp-hubspot-style-restructure.md` の 96、139、142、187 行あたり | Footer・プライバシーポリシー・利用規約の住所の下に限り、電話番号を追加する。Header への追加は引き続き行わない |
| 住所の正本表（東京都新宿区の住所） | `docs/adr/ADR-046-lp-redesign.md:119-124` | 住所の正本は本 ADR の表記に置き換える |
| Footer 会社情報不変 | `docs/adr/ADR-049-lp-section-completion.md:191` | Footer の住所と電話番号に限り変更する |

## 不採用の案

| 案 | 不採用の理由 |
|---|---|
| robots.txt に Disallow を足す | 検索エンジンが noindex を読めなくなる。Meta のクローラーの URL 確認にも支障が出る。ADR-017 と食い違う |
| nginx の X-Robots-Tag を足す | nginx の反映経路を触る危険があり、noindex の meta で足りるため今回は不要 |

## 戻し方

この ADR を入れた PR を revert する。

## 検証

`docs/handoff/lp-application-only/design.md` の受け入れ基準の表のとおり。
