# Phase 3 設計 — migrate-edit-pages-select

**対象ADR**: ADR-073
**recon**: docs/handoff/migrate-edit-pages-select/recon.md
**日付**: 2026-06-26
**担当**: Hikky-dev

---

## 外部・過去事例の参照と我々への応用

- 事例: LeadEditPage で同一パターンの移行を PR #2607 で実施済み（本番稼働確認済み）。
  同型フォーム3画面（DealEditPage・ContactEditPage・StaffEditPage）への横展開のため、
  外部事例は不要と判断。内部実績（PR #2607 + #2612）が直接の根拠。
- 我々への応用: 同一手順（import Select → form-group ラッパー除去 → options 配列構築）を3画面に適用。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 3画面の生 `<select>` が `<Select>` コンポーネントに置き換わっている | `git diff` でファイル確認（3ファイル・7個） |
| 各画面でカスタム SVG ▽ アイコンが表示される | STEP-3 Playwright 比較スクリーンショット |
| ESLint エラーゼロ（`--max-warnings=0`） | CI: Frontend lint & custom checks |
| migrations/ deploy.yml を含まない | `git diff --name-only` でフロント3ファイルのみ確認済み |
| CI 全チェックグリーン | GitHub Actions |

---

## 技術 How・KPI

- 手法: LeadEditPage（PR #2607）と同一パターン。`import { Select }` → `form-group` div 除去 → `<Select label=... options=[...] value=... onChange=...>`
- 特記事項: ContactEditPage の会社選択肢は動的（API取得）のため `companies.map()` で options 構築
- KPI: lint エラーゼロ・CI 全グリーン・3画面7個の生 `<select>` がゼロになること

---

## 弊害・トレードオフ

- `form-group` div が `comp-field` div に変わるため、ページ固有の CSS が `form-group select` を対象にしていた場合は効かなくなる。
  → 3ファイルの pages ディレクトリに固有 CSS なし（確認済み）。弊害なし。

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | 3ファイルに `import { Select }` 追加 | Generator |
| 2 | 各ファイルの `<select>` を `<Select>` に置換 | Generator |
| 3 | STEP-3 Playwright スクリーンショット比較 | Evaluator |
| 4 | feature → develop PR → CI グリーン → マージ | Generator |
| 5 | isolated release ブランチ → main PR → 本番デプロイ | Generator |

---

## 継続

- 次フェーズ: B層 FormFields（LeadFormFields / DealFormFields 等 6ファイル）の移行（別 PR）
- ProductEditPage は TCG 特殊ロジックのため単独 PR
