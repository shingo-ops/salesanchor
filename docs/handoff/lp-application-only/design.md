<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ。 -->
# Phase 3 設計 — lp-application-only

この文書は何か：LP の住所・電話番号を Meta の登録に合わせ、検索に載らないようにする変更の設計と、できたかどうかの確かめ方です。

**対象ADR**: ADR-1044
**recon**: docs/handoff/lp-application-only/recon.md
**日付**: 2026-10-25
**担当**: Planner（Opus）
**設計仕様書（あるべき姿）**: 対象外

---

## 外部・過去事例の参照と我々への応用

- Meta ビジネス認証の名称・住所一致が却下理由の最多という解説記事5本（chakrahq 2026-08-11 ほか。個別の数値事例は0件）→ 我々への応用: 申請の住所・電話番号と LP の表示を一致させる。Meta 公式の明文は未確認。

---

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 全7ページの HTML に noindex の meta が1つずつある | `cd lp && npm ci && npm run build` 後、`grep -c 'name="robots" content="noindex' dist/**/*.html` を各ファイルで確認 |
| 旧住所が lp/ に0件 | `git grep` |
| 新住所と電話番号が privacy・terms・Footer に出ている | dist の HTML を grep |
| robots.txt が変わっていない | `git diff origin/main -- lp/public/robots.txt` が空 |
| ビルドが通る | `npm run build` の終了コードが 0 |

---

## 技術 How・KPI

- 変更: Footer・privacy・terms の住所行と電話番号行、BaseLayout と LegalLayout の `noindex` 既定値を true。
- KPI: 上の表の 5 項目がすべて合格。
- 触らない範囲: lp/ 以外のコード、nginx、ワークフロー、`lp/public/robots.txt`、既存 ADR 本文。

## 弊害・トレードオフ

- 検索に出なくなる → 目的どおり（申請用）。戻し方: PR を revert。
- Disallow を使わないため、クローラーは読めるまま → Meta の確認に支障なし。

## 計画票

| ステップ | 内容 | 担当 |
|---|---|---|
| 1 | 住所・電話・noindex の変更、ADR-1044、recon・design | Generator |
| 2 | ビルドと受け入れ基準の確認、PR 起票 | Generator |
| 3 | 審査とマージ | Opus |

## 継続

- 次フェーズへの引き継ぎ: なし。

## 維持の仕組み

- 守り手: 人手で守る（LP は申請用の小さな静的サイトで、専用の関所ファイルがないため）
- 対象: 今後 LP のページを足すときは BaseLayout を通る限り自動で noindex。外す場合は ADR の変更が必要
