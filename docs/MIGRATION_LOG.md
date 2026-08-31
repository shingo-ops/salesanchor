# MIGRATION_LOG

プロジェクト全体の特記事項・除外判断・CI問題を記録する。

---

## [2026-09-01] alembic を MIG-04 PR-1 から除外した理由

**対象PR**: #3181（TCG 並行運用比較レポート）

MIG-04 の実装ブランチ（`feat/tcg-migration-phase4`）には Alembic マイグレーションファイルおよび `backend/app/models.py` の変更が含まれていた。
これらは MIG-04 PR-1 には含めなかった。理由は以下のとおり。

1. **CLAUDE.md §ブランチ運用ルール**:
   「main にマージ＝本番投入可の宣言（ADR-135）。migrations/ を含む実装は PO GO が出るまで release ブランチで待機し main にマージしない。」
2. **PR-1 のスコープ**:
   PR-1 は「読み取り専用の並行レポート画面」に限定。DB スキーマ変更を伴わないため Alembic は不要。
3. **安全マージ**:
   Alembic を除外することで、DB への副作用なしに本番デプロイ可能な状態を維持した。

Alembic マイグレーション（`tcg_*` テーブル群）は、PO が準備できた時点で別 PR として投入する。

---

## [2026-09-01] test_analytics.py 4件の再現性のある失敗（CI 全赤状態）

### 失敗している4テスト

```
FAILED tests/test_analytics.py::TestFunnel::test_funnel_with_data - assert 0 == 3
FAILED tests/test_analytics.py::TestChannels::test_channels_gross_margin_calculated - AssertionError: assert 'instagram' in {}
FAILED tests/test_analytics.py::TestReasons::test_reasons_with_data - assert 0 >= 1
FAILED tests/test_analytics.py::TestReasons::test_reasons_type_filter - AssertionError: assert '在庫・品揃え' in []
```

### いつから失敗しているか

| CI Run | ブランチ | 結果 | タイムスタンプ (UTC) | トリガーコミット |
|--------|---------|------|---------------------|----------------|
| 33392569820 | main | ✅ PASS | 2026-08-31T12:36:04Z | `33c9379e` (PR #3180 merge) |
| 33417192281 | main | ❌ FAIL | 2026-08-31T17:00:24Z | `f1dc00d0` (PR #3182 merge) |

**初回失敗確認**: 2026-08-31T17:00 UTC（JST: 2026-09-01 02:00）

PR #3182（`chore(ledger): PR #3179 を DONE 化`）のマージ後に初めて失敗が観測された。
ただし PR #3182 の変更内容は `.claude-pipeline/active-work.d/release-discord-inbox-sync-b.md` への5行追加のみであり、analytics テストに影響を与えるコード変更は含まれない。

### 失敗パターンの分析

全4件は `tests/test_analytics.py` に集中しており、いずれも「テストデータが取得できない」パターン:

- `assert 0 == 3` — ファネルデータ 3件を期待、0件取得
- `assert 'instagram' in {}` — チャンネル辞書が空
- `assert 0 >= 1` — 解約理由が 0件
- `assert '在庫・品揃え' in []` — 解約理由タイプが空リスト

CI ログには `audit.py:232 データアクセスイベント記録に失敗` のエラーも出現（失敗と因果関係は未確認）。

### 現在の状態

- **main** で再現性のある失敗（re-run でも同一4件が失敗）
- **全 PR の `pytest (SQLite + PostgreSQL RLS)` チェックが赤**（required status check のため、全 PR がマージブロック状態）
- フラキーではない（re-run 後も結果が変わらない）

### 想定される原因（未調査・推測ラベル）

【推測】テストが依存するシード/フィクスチャデータが CI PostgreSQL 環境で生成されていない可能性。
コードの変更ではなく、CI 環境側（DB セットアップ）の問題である可能性が高い。

### 対応方針

- 修正は別タスク（このログは調査記録のみ）
- 優先度: CI 全赤のため早期対応推奨
- 調査起点: `backend/tests/test_analytics.py` のフィクスチャ定義、`conftest.py` の DB セットアップ処理
