# design.md — 受信箱カルテ 見た目忠実度ゲート（⑤）／ Generator 実装指示

- 対象ADR: ADR-110
- 対応設計: karte_visual_gate_design（Planner, 2026-06-06）
- 対応recon: `docs/handoff/karte-visual-gate/recon.md`
- 見本（正本）: `docs/adr/karte_reference.html` ＋ KarteLayoutReference（各 px 値）
  ※ 各値は見本ファイルを最終正本とする。本書の数値と相違があれば見本に合わせる。

## ゴール
カルテ（InboxKartePanel）の描画を見本に一致させ、Playwright 視覚回帰テストを PR 必須ゲートにして
以後の見た目ズレを止める。実装順は 5a → 一致確認 → 5b。

---

## Phase 5a — 寸法是正（InboxPage.css 中心）

recon で特定した 8 差分を見本値に修正する。

| # | 修正 | 場所 | 目標値（見本準拠） |
|---|---|---|---|
| 1 | パネル幅 | InboxPage.css:747, 996 | 396px（★下記必読） |
| 2 | セクション見出し | :1175 | text-transform 解除（通常テキスト）／11px |
| 3 | ヘッダー padding | :868 | 16px 18px 14px |
| 4 | フィールド padding | :1136 | 7px 9px |
| 5 | タブ padding / font | :1160, :1162 | padding 11px 4px ／ font 13px |
| 6 | アクションバー padding | :1199 | 12px 18px |
| 7 | Primary ボタン | :1208 | padding 10px ／ radius 8px |
| 8 | border | 複数箇所 | 0.5px |

### ★ #1 パネル幅の必須注意（最重要）
- 現在 `--drawer-width: 300px`（ユーザードロワー用の**共有変数**）を流用しており、見本 396px より 96px 狭い。
- **この共有変数 `--drawer-width` を書き換えてはならない**（他ドロワーが 300px に依存）。
- カルテ**専用**に 396px を与える（直値 396px、または新設 `--karte-width: 396px`）。
- 着手前に `--drawer-width` の他の参照箇所を grep し、**それらが 300px のまま不変であること**を確認して報告。

### 5a 完了条件
ローカルで描画し、`karte_reference.html` と目視一致（幅・余白・タブ・セクション見出し・アクションバー）。
lead / customer 両段階で確認。

---

## Phase 5b — 視覚ゲート（5a 完了・一致確認後にのみ着手）

- `karte-visual-gate.spec.ts` に `toHaveScreenshot()` を追加。`renderKarte()`（認証バイパス＋API モック済）で
  カルテ単体を固定データ（Crown Cards 例）・固定幅・lead / customer で描画して比較。別テストページ不要。
- ベースライン生成は **ubuntu-latest で `--update-snapshots`**、生成画像をコミット。
  - **★ 5a の修正が反映され、見本一致を確認した後にのみ生成すること**（崩れた状態を正解として固定しない）。
- しきい値：軽い許容（`maxDiffPixelRatio` 小）でアンチエイリアス差の誤検知を防ぎつつ、配置ズレは検出。
- `karte-gate` は既に PR 必須チェック済み（追加設定不要）。視覚テストがそのゲートに乗ることを確認。
- 実行は GitHub 無料枠。Actions 使用上限 **$0**（超過で停止＝課金なし）を維持。

---

## 外部・過去事例の参照と我々への応用

- **Playwright `toHaveScreenshot()` 公式パターン**（playwright.dev）→ ubuntu-latest でベースライン生成し Mac 差を排除する手法を採用。
- **ADR-067 デザイントークン強制**（本リポジトリ既存）→ px・色のハードコードを防ぎトークン参照に統一。今回の `--karte-*` トークン群もこれに準拠。
- 該当なし（外部 SaaS の visual regression 事例は規模・コスト前提が異なるため不採用）。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| カルテ描画が見本と目視一致（lead / customer 両方） | `karte-screenshot-compare.spec.ts` 4枚を目視確認（Shingo 承認） |
| `--drawer-width` 他利用箇所が 300px のまま不変 | `grep -r drawer-width frontend/src/` で参照箇所を確認 |
| `toHaveScreenshot()` ゲートが PR 必須チェックとして機能する | karte-gate.yml の `karte-gate` job が PR 上で green |
| カルテ UI を意図せず変えた PR でゲートが赤になる | 捨てブランチで意図的に1箇所変更 → `karte-gate` FAIL を確認 |
| ubuntu-latest ベースラインで Mac 差による誤検知がない | workflow_dispatch 後のゲート run が PASS |
| ADR-067: `check:css-colors` `check:css-values` が 0 件 | CI `Frontend lint & custom checks` グリーン |

## 実装順（厳守）
5a（CSS 修正＋幅のカルテ専用化）→ 見本一致を目視確認 → 5b（`toHaveScreenshot()` 追加＋ベースライン生成）
→ 視覚ゲート稼働。
