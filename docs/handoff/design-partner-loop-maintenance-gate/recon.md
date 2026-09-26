# recon — 維持の仕組み欄の必須化（関所で機械強制）

> この文書は何か（専門用語なしの1行）: 設計書に「点検担当」欄を必ず書かせる仕組みを作る前に、今のコードがどうなっているかを実物で確かめた調査記録。

親（あるべき姿＋KGI）へのリンク: [../../specs/design-partner-loop/README.md](../../specs/design-partner-loop/README.md) §5「維持の仕組み必須化便」

## 既存ADR検索の結果
- `git grep -il`（維持／gate／process-artifacts）で docs/adr/ を検索。該当: `docs/adr/ADR-121-sop-process-artifacts-gate.md`。関所の生い立ちのADR。2026-06-13の変更記録で「行番号の妥当性チェックを廃止し、ファイル実在確認に簡素化」した経緯を確認。本便の実在チェック方式はこの先例に沿う。矛盾する先例なし。

## 実物確認（file:line・すべて origin/main d4c83509 時点）
- 関所本体 `scripts/check-process-artifacts.js`
  - `scripts/check-process-artifacts.js:287-313` extractFileCitations — 文書からファイルパスを抽出（バッククォート有無両対応）。
  - `scripts/check-process-artifacts.js:319-328` validateFileCitations — 抽出パスを existsSync で実在確認。守り手パスの実在チェックに流用する。
  - `scripts/check-process-artifacts.js:331-380` validateDesignDoc — design検証本体。維持欄検査の追加先。
  - `scripts/check-process-artifacts.js:353-354` design→recon 相互参照チェック（既存の紐づけ検査の先例）。
  - `scripts/check-process-artifacts.js:364-377` 「外部・過去事例」欄の存在＋非空チェック — 本便の空欄チェックの手本。
  - `scripts/check-process-artifacts.js:618` GRACE_THRESHOLD_PR = 2600。625・650行で PR番号2600以上のみ義務化する猶予方式。
  - `scripts/check-process-artifacts.js:47-55` DANGEROUS_PATTERNS — `docs/STANDARD-WORKFLOW.md`・`scripts/` 配下は危険変更（自己保護）。本便のPRはPO自筆GO必須。
  - `scripts/check-process-artifacts.js:508-520` 関所は「設計:」で指された design doc を1枚だけ読む。修正mdの積み重ね（複数枚）は現行未対応＝本便の範囲外（次便）。
- 正本 `docs/STANDARD-WORKFLOW.md:42-52` — §1.6 親子リンク節。52行に「強制化する場合は別途 recon→設計→GO を経る」と予告済み。§1.7 の挿入位置はこの直後。
- テスト `scripts/tests/test-process-artifacts.js` — 実在。`scripts/tests/` が関所テストの標準置き場。ルートに package.json は無く node 直接実行方式。
- 発動 `.github/workflows/process-artifacts-gate.yml:39` — node scripts/check-process-artifacts.js を実行。
- 名指し先候補（実在確認済み）: `.github/workflows/migration-guard.yml` `.github/workflows/dangling-route-gate.yml` `.github/workflows/ui-governance-gate.yml` `.github/workflows/schema-check.yml` `.github/workflows/migration-test.yml`
- 親構想 `docs/specs/design-partner-loop/README.md` §5 に本便が予告済み。`docs/ai-agents/design-partner.md` §5 テンプレ9番に維持の仕組み欄、§8 に「機械強制は未設計・本便で設計する」と明記。
