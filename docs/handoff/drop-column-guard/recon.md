<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# recon — drop-column-guard

**仕事名**: drop-column-guard
**日付**: 2026-09-16
**対象ADR**: ADR-1002
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `.github/workflows/migration-guard.yml:1` | 既存ワークフロー定義（チェック1〜5が稼働中） |
| `.github/workflows/migration-guard.yml:287` | チェック5（タイムスタンプ重複）が最後のチェック。この後にチェック6を追加する |
| `backend/CLAUDE.md:37` | 「Migration は additive-only（追加専用）」ルール。DROP COLUMN/TABLE は ADR 承認必須と明記 |
| `scripts/check-process-artifacts.js:67` | scripts/ が dangerous パス分類。migration-guard.yml 変更時に GO 必要 |
| `scripts/check-process-artifacts.js:81` | .github/workflows/ が dangerous パス分類 |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | 既存の DROP COLUMN 使用箇所 | grep -rn 'DROP COLUMN' migrations/ で6件確認（_down.sql 含む） | ✅ 解消済み |
| 2 | 正当な DROP の前例 | ADR-089（DROP customers）、ADR-1002（DROP tcg_uuid）を確認 | ✅ 解消済み |
| 3 | gh pr view が CI 環境で使えるか | github.token を GH_TOKEN に渡せば利用可能 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

- チェック6は既存チェック1〜5と同じ job 内の step として追加。新 job 不要
- PR差分の追加行のみを対象とし、SQL コメント（--）と Python コメント（#）は除外
- ADR 番号が PR 本文にあれば通過させ、正当な削除をブロックしない
