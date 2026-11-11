# Phase 3 設計 — lp-footer-operator-ja

- recon: docs/handoff/lp-footer-operator-ja/recon.md
- 関連 ADR: ADR-049（Footer の会社情報は不変＝中身を変えない）、ADR-1044（LP は Meta 申請用）
- PO 依頼: 2026-11-12「フッター内の会社情報を日本語にしてくれ」

## 目的（KGI）

本番 salesanchor.jp の全ページのフッターで、運営者の欄が日本語だけで表示される。Meta の審査担当が日本の公的記録（日本語表記）と名前・住所・登録番号をそのまま見比べられるようにする。

## 外部・過去事例の参照と我々への応用

該当なし。理由: 公的記録との表記の一致は Meta の申請画面の文言（「公的記録を検索し…実在していることを確認します」）から直接導いた対策で、他社事例を成功の根拠にしない。

## 変更（`lp/src/components/Footer.astro` の 38〜46 行だけ）

| 行 | 変更前 | 変更後 |
|---|---|---|
| 38 | `Operator` | `運営者` |
| 41 | `HIGH LIFE JPN` | `屋号：HIGH LIFE JPN` |
| 42 | `Representative: Shingo Tanizawa (谷澤 伸吾)` | `代表者：谷澤 伸吾` |
| 43 | 英語住所 | （行を消す） |
| 44 | `〒444-2141 愛知県岡崎市桑原町字緑陽台8番地312` | `所在地：〒444-2141 愛知県岡崎市桑原町字緑陽台8番地312` |
| 45 | `Invoice Registration No. (適格請求書発行事業者登録番号): T3810449547408` | `適格請求書発行事業者登録番号：T3810449547408` |
| 46 | `Phone: +81 90-6072-7767` | `電話番号：090-6072-7767` |

メールのリンク（47〜51 行）は変えない。

## 触らない範囲

Footer の他の欄（説明文・Legal 欄）、index・privacy・terms・data-deletion の本文の運営者表記、BaseLayout、robots、nginx、アプリ（frontend）。

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 差分は Footer.astro だけ、+6/-7 | `git diff --stat origin/main` |
| ビルドが通る | `cd lp && npm ci && npm run build` 終了コード 0 |
| Footer.astro に `Ryokuyoudai` `Representative:` `Phone:` `Invoice Registration` が 0 件（本文ページの英語表記は対象外で残る） | `grep -c` を Footer.astro に |
| dist/index.html に `代表者：谷澤 伸吾` `所在地：〒444-2141` `適格請求書発行事業者登録番号：T3810449547408` `電話番号：090-6072-7767` が各1件以上 | `grep -c` |
| 本番トップを facebookexternalhit 名義で取得し、上の4語が出る | マージ後に curl |

## 弊害・トレードオフ

- 英語しか読めない訪問者は運営者欄が読めない。LP は申請用（ADR-1044）で、利用規約・プライバシーポリシー本文には英語の運営者表記が残るため影響は小さい。

## 戻し方

PR を revert する。

## 計画票

| 段 | 担当 | 成果物 |
|---|---|---|
| 設計 | Opus | 本書・recon・card |
| 実装 | クラウド Sonnet | Footer.astro の変更 |
| 審査 | reviewer（opus） | APPROVE |
| 本番確認 | Opus | curl の結果 |

## 維持の仕組み

- 守り手: 人手で守る（表記の一回きりの変更で、関所を作る対象がないため）。
