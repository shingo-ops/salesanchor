<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ。 -->
# recon — lp-application-only

この文書は何か：LP の住所・電話番号・検索よけを直す前に、今のコードと既存の決め事を確かめた記録です。

**仕事名**: lp-application-only
**日付**: 2026-10-25
**対象ADR**: ADR-1044
**実測基準**: origin/main 570d70c4a
**設計**: docs/handoff/lp-application-only/design.md
**設計仕様書（あるべき姿）**: 対象外（lp/ の文言と meta の修正。新しいデータ構造・機能なし）

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|---|---|
| `lp/src/components/Footer.astro:43` | 旧住所（東京都新宿区）。Footer の `<li>` |
| `lp/src/pages/privacy.astro:36` | 旧住所。`<p>Address: ...</p>` |
| `lp/src/pages/terms.astro:345` | 旧住所。`Address: ...<br>` |
| `lp/src/layouts/BaseLayout.astro:19` | `noindex = false`（既定値） |
| `lp/src/layouts/BaseLayout.astro:39` | `noindex` が真のとき `<meta name="robots" content="noindex, nofollow" />` を出す |
| `lp/src/layouts/LegalLayout.astro:12` | `noindex = false`（独自の既定値）。privacy・terms がこれを使う |
| `lp/src/pages/deletion-status.astro:11` | `noindex={true}`（既に指定済み） |
| `lp/public/robots.txt` | 変更しない（Disallow を足さない） |
| `docs/adr/ADR-054-lp-hubspot-style-restructure.md:96` | 「電話番号は追加しない」（ほか 139、142、187 行） |
| `docs/adr/ADR-046-lp-redesign.md:119` | 住所の正本表 |
| `docs/adr/ADR-049-lp-section-completion.md:191` | 「S9 Footer の会社情報は不変」 |

LP のページは 404・data-deletion・deletion-status・index・pricing・privacy・terms の 7 つで、すべて BaseLayout か LegalLayout を使う（`lp/src/pages/` を `grep Layout` で確認）。

## 既存 ADR 検索

`git grep -i` で robots・noindex・電話番号・住所に関する ADR を検索。該当: ADR-017（robots.txt）、ADR-046、ADR-049、ADR-054。上書きの扱いは ADR-1044 に記載。

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|---|---|---|
| 1 | 旧住所の行が 3 か所以外にあるか | `git grep -n -i "Nishi-Shinjuku\|Mizuma\|160-0023" -- lp/` | 解消済み（3 か所のみ） |
| 2 | Meta 公式が住所一致を明文化しているか | 未確認 | 未確認（外部解説の共通点として記載） |

**未解決ゼロ確認**: 不明点 2 は設計判断に影響しない（PO 決定済み）。
