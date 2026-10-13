<!-- 守り手: frontend/src/pages/inventory/InventoryPage.singlefetch.test.tsx -->
# Phase 3 設計 — inventory-single-fetch

**対象ADR**: ADR-099  
**recon**: docs/handoff/inventory-single-fetch/recon.md  
**日付**: 2026-10-14  
**担当**: Opus（設計）／Sonnet（実装）

---

## 外部・過去事例の参照と我々への応用

- 事例1: React 公式ドキュメント「Fetching data / race conditions」の ignore フラグ方式 → 応用: 要求番号の ref で古い応答を捨てる（API クライアントは変更しない）
- 事例2: 前便 #4249（API 1回あたり約0.5秒）→ 応用: 呼び出し回数そのものを半減させる

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 開いた直後の GET /inventory が1回で、保存済みフィルタが URL に入る | `frontend/src/pages/inventory/InventoryPage.singlefetch.test.tsx`（テスト1） |
| フィルタ取得失敗時も1回表示される | 同ファイル（テスト2） |
| 古い応答で上書きされない | 同ファイル（テスト3） |
| ハードコード文言・色の追加なし | cd frontend && npm run lint（エラー0） |

---

## 技術 How・KPI

- KPI: 1回の訪問での GET /inventory = 1回（本番 nginx ログで Opus が確認）
- 変更: `frontend/src/pages/inventory/InventoryPage.tsx` の load の先頭で要求番号を増やし、await 後に最新でなければ state を更新しない。読込 effect は filtersLoaded が true になるまで待つ。
- 触らない: 保存（PATCH）の effect、API クライアント、backend、CSS、i18n。

## 弊害・トレードオフ

- フィルタ取得が遅いと一覧の表示がその分遅れる → 対策: 失敗時も finally で true になるので無限待ちにはならない。

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | effect 条件と要求番号の追加 | Sonnet |
| 2 | vitest 3本追加 | Sonnet |

---

## 維持の仕組み

- 守り手: frontend/src/pages/inventory/InventoryPage.singlefetch.test.tsx

## 継続

- 完了後の監視: デプロイ後に本番 nginx ログで1訪問あたりの回数を確認（Opus）
- 次フェーズ: 読込直後の同値 PATCH 1回の件は別便
