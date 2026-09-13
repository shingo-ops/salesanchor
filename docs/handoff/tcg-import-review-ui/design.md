# design — tcg-import-review-ui（確認工程 フロントエンド UI）

**対象ADR**: ADR-027, ADR-144  
**recon**: docs/handoff/tcg-import-review-ui/recon.md  
**日付**: 2026-09-05  
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- 事例: GitHub の Draft PR → Ready for Review フロー（人間確認ゲートを設けてから本線統合）→ 我々への応用: `review_status='pending_review'` のときに ReviewSection を表示し、全員登録後に「抽出を開始」ボタンを有効化する
- 事例: Jira/Linear のインライン展開パネル（一覧行をクリックで詳細パネルが展開）→ 我々への応用: 保留中ジョブ一覧から「確認する」ボタンで ReviewSection をインライン展開。ページ遷移不要

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| アップロード後 review_status='ok' のとき取り込み完了セクションが表示される | 手動: ファイルアップロード → 結果カード表示 |
| アップロード後 review_status='pending_review' のとき ReviewSection が表示される | 手動: 未解決名あり → ReviewSection 表示 |
| ReviewSection で「既存割り当て」→ 仕入元検索 → 選択で名前がマーク解決済み | 手動: 割り当て操作 → 「登録済み」バッジ |
| ReviewSection で「新規登録」で名前がマーク解決済み | 手動: 新規登録ボタン → 「登録済み」バッジ |
| 全員解決済みで「抽出を開始」ボタンが有効化される | 手動: 全解決 → ボタン活性 |
| 「抽出を開始」→ POST commit → 成功メッセージ表示 | 手動: commit → 成功 |
| 保留中ジョブ一覧が GET /pending から取得される | 手動: ページ表示で保留ジョブ表示 |
| 「確認する」で ReviewSection がインライン展開される | 手動: ボタン押下 → 展開 |
| `frontend/scripts/check-i18n-missing-keys.js` が PASSED | `node frontend/scripts/check-i18n-missing-keys.js` → 0エラー |
| `tsc --noEmit` が 0 エラーで完了する | CI `frontend-build` ジョブ green |
| `vite build` が成功する | CI `frontend-build` ジョブ green |

---

## 技術 How・KPI

- KPI: `tsc` エラー 0件 / ビルド成功 / i18n-missing-keys PASSED
- `TcgLineImportPage.tsx`: `ImportResultResponse` に `review_status` を追加。result 表示を分岐
  - `review_status === 'pending_review'` → `<ReviewSection>` を表示
  - それ以外 → 既存の完了カード
- 保留中ジョブ: `GET /tcg/line-import/pending` → `PendingJobDetail[]` を表示
  - 「確認する」ボタン → `selectedPendingId` state → `<ReviewSection>` インライン展開
- `frontend/src/features/tcg-import-review/ReviewSection.tsx` を新規作成
  - `GET /tcg/diagnostics/suppliers` → 仕入元一覧
  - 未解決名ごとに「既存割り当て」（検索フィルタ付きリスト）または「新規登録」
  - 全解決済みで「抽出を開始」→ `POST /{id}/commit`
- i18n: `tcgLineImport` 名前空間に 14キー追加（ja/en 同期）
- ADR-027: 全文字列 `t("key")` 経由
- ADR-144: 既存 inline style パターンを踏襲。生 select/input に `ui-allow` コメント付与

---

## 弊害・トレードオフ

- バックエンド変更なし（#3306 APIをそのまま使用）
- 保留中ジョブ取得失敗はサイレント（非致命的）
- 「抽出を開始」失敗時は 409 エラーメッセージを表示（再解決を促す）

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | `ReviewSection.tsx` 新規作成 | Generator |
| 2 | `TcgLineImportPage.tsx` 修正（型・分岐・保留ジョブ） | Generator |
| 3 | `ja.json` / `en.json` に 14キー追加 | Generator |
| 4 | `npm run check:all` / `vite build` / `check-i18n-missing-keys.js` 確認 | Generator |

---

## 維持の仕組み

守り手: frontend/scripts/check-i18n-missing-keys.js（ja/en のキー数一致を検査。新キー追加時に両言語への追加漏れを検知）

---

## 継続

- 完了後の監視: CI の `frontend-build` ジョブが静的に型を検証する。追加の監視設定不要
- 次フェーズ: なし（確認工程 UI は本 PR で完結）
