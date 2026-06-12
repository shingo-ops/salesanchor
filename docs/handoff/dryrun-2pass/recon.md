# recon — dryrun-2pass

**仕事名**: dryrun-2pass  
**日付**: 2026-06-12  
**対象ADR**: ADR-135  
**担当**: Hikky-dev

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `.github/workflows/migration-test.yml:860` | 1周目ステップ（新規適用）定義 |
| `.github/workflows/migration-test.yml:895` | 2周目ステップ（冪等性チェック）定義 |
| `.github/workflows/migration-test.yml:898` | 「cannot drop columns from view」型を検出できる理由のコメント |
| `migrations/20260604_100000_create_company_stats_view.sql:37` | 今日の失敗箇所（旧版：スキップガードなし） |
| `migrations/20260611_130000_fix_v_company_stats_deleted_at.sql:45` | 同様の失敗箇所（旧版） |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | 2周目で旧版（スキップガードなし）の `20260604_100000` が検出できるか | 1周目で `20260612_120000` が 7列にした後、2周目で 5列 CREATE OR REPLACE → ERROR を確認 | ✅ 解消済み |
| 2 | 2周目の実行時間増加は許容範囲か | タイムスタンプSQL約50件で約30秒追加。timeout-minutes: 30 内に収まる | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
