# design: 読み込み中の表示を動く印に（2026-10-22 Opus）

参照: docs/handoff/loading-indicator/recon.md ／ 実装カード docs/handoff/loading-indicator/card-1.md ／ ADR-027・ADR-067・ADR-144

## 1 KGI（PO 2026-10-22「1」）
要確認画面（LINE解析 → 要確認タブ）で一覧の取得中、「読み込み中...」の文字ではなく金型の回る丸が出る（PO が目視で○×）。良ければ段階2で他の画面へ広げる。

## 2 現在地
recon.md §1〜§5。金型の Spinner はあるが画面では未使用、文字だけの表示が約56か所、決まりは無い。

## 3 直し方（段階1）
NeedsReviewTabsPanel.tsx:284 の p 要素を `<Spinner size="md" label={t("common.loading")} />` に替える（変更前後はカード §変更）。
- 代替案: Skeleton(table) — aria-label が英語直書き（recon §1）のため段階1では不採用。DataTable に loading 引数を足す案 — 金型変更になり範囲が広がるため段階2で検討。

## 4 受入条件
| 基準 | 検証方法 |
|---|---|
| 読み込み中に回る丸が出る | vitest: role=status・name=common.loading の訳語・class sa-spinner |
| 文字の p 要素が無い | 同じ試験 |
| 既存の試験が通る | NeedsReviewTabsPanel の vitest 全緑 |
| 規約 | eslint 0・UIガバナンス緑・i18n 差 0 |
| 本番 | PO が再読み込み後に目視 |

## 5 弊害とリスク
- 読み上げ文字は aria-label になる（画面上の文字は消える）。動きを減らす設定の利用者には止まった丸が出る（loading-animations.css:543-551）。
- 計時（便0）は loading の表示と無関係（recon・試験で確認）。

## 6 維持の仕組み
- 金型 Spinner と動きのトークンは components/loading と tokens.css が正本。UIガバナンス検査（ADR-144）が直値を止める。
- 段階2で docs/CC_UI_GOVERNANCE.md に「読み込み中は金型の Spinner／Skeleton を使う」を書き、新規の文字だけ表示を防ぐ。

## 7 外部・過去事例の参照と我々への応用
- 外部事例は使わない。理由: 金型（components/loading/README.md・Component Spec）に用途の決まり（Spinner は部分的な読み込み・表の再取得向け）が既にあり、それに従えば足りる。
- 過去事例: Button.tsx:68 が同じ Spinner を使って本番で動いている。

## 8 戻し方
この PR の revert。
