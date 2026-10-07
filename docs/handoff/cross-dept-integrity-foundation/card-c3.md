---
mode: handoff
---
# 実装カード 便C-3／C-4: 生成型の横展開（TcgParallelReportPage／OwnInventoryPage）

- 根拠: ADR-1005（Accepted）。手順は便C-2（PR #4009、本番反映済み 2026-10-07）と同じ型を使う。生成の配線（prebuild と frontend-check の生成 step）は #4009 で入っているので、この便では触らない。
- 対象を選んだ根拠: 2026-10-06 の Sonnet 調査（origin/main `a77cfb1c0`）で、候補の2位と3位だったもの。
- PR の分け方: 1画面につき1つの PR にする。
  - 便C-3 = TcgParallelReportPage
  - 便C-4 = OwnInventoryPage

## 便C-3: TcgParallelReportPage
- 呼び出し: `frontend/src/pages/super-admin/TcgParallelReportPage.tsx:71` の GET /tcg/parallel-report
- backend: `backend/app/routers/tcg_parallel_report.py:70`。response_model があり、型は `ParallelReportResponse`。
- 手書き型（同じファイル内）: `EngineStats`（:20）、`CompatEngineStats`（:26）、`SupplierRow`（:30）、`ReportSummary`（:39）、`ParallelReportResponse`（:48）
- 変更:
  - 手書き型を、生成型（`components["schemas"][...]`）の別名に置き換える。
  - 生成型に同じ名前が無い入れ子の型は、生成型の要素型から導く。例: `ParallelReportResponse["suppliers"][number]`
  - 導けない場合は手書きのまま残し、理由を1行コメントで書く。
  - 画面のロジックと表示は変えない。

## 便C-4: OwnInventoryPage
- 呼び出し:
  - `frontend/src/pages/inventory/OwnInventoryPage.tsx:58` の GET /own-inventory（レスポンスは `OwnInventoryResponse[]`）
  - `:87` の POST /own-inventory/{id}/{kind}（戻り値は使っていない）
- backend: `backend/app/routers/own_inventory.py:64`。response_model があり、型は `list[OwnInventoryResponse]`。
- 手書き型: `OwnInventoryRow`（:16）。`ActionKind` と `PendingAction` は画面の中だけで使う型なので、対象外。
- 変更:
  - `OwnInventoryRow` を `components["schemas"]["OwnInventoryResponse"]` の別名にする。
  - POST の部分は変えない。

## 両便に共通する手順
1. 着手前の点検（違っていたら止まる）
   - 手書き型と生成型を、フィールドごとに表で照合する。比べる項目は、名前、型、null を許すか、省略できるか。
   - 違いを、画面で使っているフィールドと使っていないフィールドに分けて書く。
   - 違いを直すと画面の表示ロジックが変わる場合は、止まって報告する。直してよいのは、生成型（＝実際の形）に合わせる方向だけ。
2. 検証。生出力を貼る。
   - `npx tsc --noEmit`、`npm run lint`（エラー0件で、警告の数が main と同じ）、`npm run check:all`、その画面のテスト（あれば）を実行する。
   - ずれを検出できることを確かめる。backend の該当スキーマのフィールド名を1つだけ一時的に変え、export と生成をし直して tsc が赤になることを見る。確かめたら元に戻す。
   - 生成物を消した状態から `npm run build` が通ることを確かめる。消すときは `git clean -f -X frontend/src/api/generated/` を使う。
3. 文書: `docs/handoff/api-types-<画面>/recon.md` と `docs/handoff/api-types-<画面>/design.md` を、#4009 と同じ形で作る。
4. PR: #4009 の本文の書式に合わせる。行頭ラベルは「設計:」「recon:」「触るファイル:」「削除するファイル:」を使う。
5. GO: frontend/src を変更するので、PO 本人の「GO #番号」が必要。GO を受け取るまではマージしない。

## 触らない範囲
- backend
- 他の画面
- package.json と workflow（配線は #4009 で済んでいる）
- ruleset

## 戻し方
- PR を revert する。
