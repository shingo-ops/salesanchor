# design — modal-select-fields

**仕事名**: modal-select-fields
**日付**: 2026-06-26
**対象ADR**: ADR-073
**recon**: docs/handoff/modal-select-fields/recon.md

---

## 背景・目的

一覧画面のモーダル 6 枚に残っている生 `<select>` を、棚の `Select` に寄せる。
目的は見た目の統一ではなく、共通部品の適用率を上げて今後の保守を一本化すること。

この変更はフロントのみで、DB 変更はしない。`migrations/` と `deploy.yml` は対象外。

---

## 変更方針

- **変更スコープ**: 6 つの `*FormFields.tsx` のみ
- **画面影響**: 7 画面
- **禁止事項**: ページ専用 CSS で `Select` を戻さない、入力欄やタブやバッジを触らない
- **機能不変**: `value` / `onChange` / 選択肢 / 保存先の値は変えない
- **標準準拠**: `Select` の▽アイコン、必須 `*`、余白は棚の標準を使う

---

## KGI / KPI

| 基準 | 検証方法 |
|---|---|
| 対象 6 ファイルの raw `<select>` が 12 個 → 0 個になる | `rg -n "<select" ...` で 0 件確認 |
| 画面 7 枚で表示崩れがない | 画面ごとの before / after スクショで確認 |
| 必須 `*` の見た目が許容範囲 | 画面ごとのスクショと PO 目視 |
| ▽ アイコンが文字に重ならない | 実機で各モーダルを開いて確認 |
| CI が green | frontend build / required checks / process-artifacts gate |
| DB 変更ゼロ | `git diff --name-only` で `migrations/` / `deploy.yml` が含まれないことを確認 |

---

## 技術的なやり方

- `frontend/src/components/Select.tsx` をそのまま使う
- `Select` に `options` を渡し、空欄が必要な項目だけ `placeholder` を使う
- 必須項目は `required` を付ける
- 画面側の個別 CSS は足さない
- 文言は既存の i18n キーを優先し、新しい文言追加はしない

---

## 弊害・リスク

| リスク | 対策 |
|---|---|
| 必須 `*` の位置が変わる | これは棚の標準に寄せた結果として許容し、実機で確認する |
| 既存の raw `select` から見た目が微妙に変わる | `Select` 標準の右余白と▽に統一されるため、個別 CSS は追加しない |
| 既存の値が空文字のとき表示が変わる | `placeholder` を使う項目は空欄表示を明示し、値の意味は変えない |
| 6 ファイル同時変更で見落としが出る | 画面ごとに 1 枚ずつスクショを撮って切り分ける |

---

## 実行計画

1. 6 ファイルの生 `<select>` を `Select` に置換する
2. `rg -n "<select"` で残りを確認する
3. 各画面で before / after を撮る
4. `npm run build` と必要な静的チェックを通す
5. process-artifacts gate を確認する
6. PR を develop に出し、GO 後に release PR へ進む

---

## 外部・過去事例

- 外部事例: 該当なし。今回は純粋な内部 UI の置換で、外部 API や DB には触れない
- 過去事例: `docs/handoff/select-arrow-padding/design.md` と `docs/handoff/select-arrow-padding/recon.md` で、棚の `Select` に▽アイコンと右余白を持たせる標準が確定している
- 過去事例: `docs/handoff/migrate-lead-edit-select/design.md` と `docs/handoff/migrate-lead-edit-select/recon.md` で、`Select` への置換手順が先行実績として整理されている

---

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 6 ファイルの raw `<select>` が消えている | `rg -n "<select"` の結果が 0 件 |
| 変更がフロントのみ | `git diff --name-only` に `migrations/` / `deploy.yml` が無い |
| 7 画面の before / after が揃う | 画面ごとのスクショ 14 枚を確認 |
| BotFormFields は 2 画面で効く | BotsPage と BotEditPage の両方でスクショを確認 |
| 全チェック green | CI と process-artifacts gate の結果を確認 |
