<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ。 -->
# Phase 3 設計 — lp-index-until-meta-verified

この文書は何か：Meta のビジネス認証が通るまでの間だけ、LP を検索に出す変更の設計と、できたかどうかの確かめ方です。

**対象ADR**: ADR-1044（2026-11-12 追記）
**recon**: docs/handoff/lp-index-until-meta-verified/recon.md
**日付**: 2026-11-12
**担当**: Planner（Opus）
**設計仕様書（あるべき姿）**: 対象外
**PO承認**: 2026-11-12 チャット「3. 検索に出すのは、審査が通るまでにする。審査が通ったら、検索に出ない形に戻します。」

---

## 目的（KGI）

Meta のビジネス認証（7回目）で、salesanchor.jp と「谷澤 伸吾」の関連が確認され、認証済みになる。そのために、申請画面の「公的記録を検索して実在を確かめる」で LP が見つかる状態にする。

## 外部・過去事例の参照と我々への応用

- Meta の申請画面の文言（2026-11-12 PO 貼り付け）「公的記録を検索し、あなたの組織が実在していることを確認します」→ 応用: 検索で見つからない状態をなくす。
- noindex が却下理由になるとした Meta 公式の明文・数値つきの事例は見つからなかった（0件）。このため成功の証明には使わず、「疑わしい要因を消す」扱いにする。

## 変更（触るのは3行）

| ファイル:行 | 変更前 | 変更後 |
|---|---|---|
| `lp/src/layouts/BaseLayout.astro:19` | `  noindex = true,` | `  noindex = false,` |
| `lp/src/layouts/LegalLayout.astro:12` | `const { title, description, subtitle, canonical, noindex = true } = Astro.props;` | `const { title, description, subtitle, canonical, noindex = false } = Astro.props;` |
| `lp/src/pages/404.astro:11`（description 行）の直後 | （なし） | `  noindex={true}` を1行足す（404 ページは検索に出さない） |

`lp/src/pages/deletion-status.astro:11` は `noindex={true}` 明示済みのため触らない。

## 触らない範囲

`lp/public/robots.txt`、nginx、`.github/workflows/`、`frontend/`（アプリの noindex は維持）、lp/ の文言・住所・電話・名前、既存 ADR 本文（ADR-1044 は末尾への追記のみ）。

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| index・pricing・privacy・terms・data-deletion の5ページに noindex の meta が0 | `cd lp && npm ci && npm run build` 後、各 `dist/**/index.html` を `grep -c 'name="robots"'` → 0 |
| 404・deletion-status の2ページに noindex の meta が1 | 同じ grep → 1 |
| 差分が上の3行と ADR・handoff 文書だけ | `git diff --stat origin/main` |
| ビルドが通る | `npm run build` の終了コード 0 |
| 本番の5ページで noindex が0（反映後） | facebookexternalhit 名義の curl で `grep -c noindex` → 0 |
| Google に載る（反映後・数日〜2週間） | PO が Google で `site:salesanchor.jp` を検索し、1件以上出る |

## 弊害・トレードオフ

- 申請用ページが一般の検索にも出る → PO が「審査が通るまで」の期限つきで承認。戻し方は下記。
- 404 を明示 noindex にするので、存在しないURLが検索に載ることはない。

## 戻し方（審査が通ったら必ず行う）

上の3行の変更を戻す（既定値を true に戻し、404 の明示は残してよい）。この PR を revert しても同じ結果になる。

## 計画票

| ステップ | 内容 | 担当 |
|---|---|---|
| 1 | ADR-1044 追記、recon・design | Opus（済） |
| 2 | 3行の変更、ビルドと受け入れ基準の確認、PR 起票 | クラウドの Sonnet |
| 3 | 審査とマージ、本番の curl 確認 | Opus |
| 4 | Google 掲載の確認→7回目の申請 | PO |
| 5 | 認証済みになったら戻す PR | Opus が設計し Sonnet が実装 |

## 維持の仕組み

- 守り手: 人手（Opus の覚え書き project_whatsapp_intake と作戦ボードに「審査が通ったら戻す」を載せる）。
- 機械の見張りは作らない（期限つきの一時変更で、戻すきっかけは Meta の認証結果という外部の出来事のため）。
