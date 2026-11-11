<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ。 -->
# recon — lp-index-until-meta-verified

この文書は何か：Meta 6回目の却下を受けて、LP を審査が通るまで検索に出す前に、今のコードと本番の見え方を確かめた記録です。

**仕事名**: lp-index-until-meta-verified
**日付**: 2026-11-12
**対象ADR**: ADR-1044（追記で変更）
**実測基準**: origin/main aec493c7f
**設計**: docs/handoff/lp-index-until-meta-verified/design.md
**設計仕様書（あるべき姿）**: 対象外（lp/ の meta の既定値の変更。新しいデータ構造・機能なし）

---

## 発端（Meta の却下文）

2026-11-12 PO 貼り付け。「ウェブサイトが準備中またはアクセス不可のため、ビジネスのウェブサイト「https://salesanchor.jp/」がビジネス「谷澤 伸吾」に関連していることを確認できませんでした」。申請画面の文言「これらの情報を基に公的記録を検索し、あなたの組織が実在していることを確認します」。

## 本番の実測（2026-11-12、User-Agent facebookexternalhit/1.1 の curl）

| ページ | 状態 | 谷澤 の出現数 | noindex meta | 準備中系の語 |
|---|---|---|---|---|
| / | 200 | 2 | あり | 0 |
| /privacy/ | 200 | 6 | あり | 0 |
| /terms/ | 200 | 3 | あり | 0 |
| /data-deletion/ | 200 | 2 | あり | 0 |
| /pricing/ | 200 | 1 | あり | 0 |

robots.txt は `User-agent: * Allow: /` と `User-agent: facebookexternalhit Allow: /`。

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|---|---|
| `lp/src/layouts/BaseLayout.astro:19` | `noindex = true,`（既定値。ADR-1044 で true にした） |
| `lp/src/layouts/BaseLayout.astro:39` | `noindex` が真のとき `<meta name="robots" content="noindex, nofollow" />` を出す |
| `lp/src/layouts/LegalLayout.astro:12` | `noindex = true`（独自の既定値）。privacy・terms・data-deletion などが使う |
| `lp/src/pages/deletion-status.astro:11` | `noindex={true}` を明示（既定値の変更の影響を受けない） |
| `lp/src/pages/404.astro:9-12` | BaseLayout を `noindex` 指定なしで使う（既定値に従う） |
| `lp/public/robots.txt` | Allow のみ。変更しない |

## 既存 ADR 検索

`git grep -i noindex -- docs/adr` で ADR-1044（LP を申請用・検索に載せない）と ADR-017（robots.txt）を確認。ADR-1044 の What 5 に「noindex を外す場合は、この ADR の変更が必要」とあるため、ADR-1044 に追記する。アプリ（frontend/index.html）の noindex は ADR-1044 追記（2026-10-25）の範囲で、今回は触らない。

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|---|---|---|
| 1 | noindex が却下の原因か | Meta 公式の明文なし | 未確認（PO が「審査が通るまで出す」を選択） |
| 2 | Google に載るまでの日数 | 本番反映後に site: 検索で観測 | 未確認 |

**未解決ゼロ確認**: 不明点 1・2 は実装の中身に影響しない（PO 決定済み・観測で確かめる）。
