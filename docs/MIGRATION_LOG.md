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

### 根本原因（確定）

`analytics.py` が `date.today()`（UTC）で「今月」を判定していたため、CI が
`15:00 UTC 以降`（= JST 翌日 00:00 以降）に実行されると JST 月次範囲と不一致になっていた。

- CI 成功ラン 12:36 UTC: `date.today() = Aug 31` → August JST range `[Jul-31 15:00, Aug-31 15:00)` UTC → leads at 12:36 UTC ✓
- CI 失敗ラン 17:00 UTC: `date.today() = Aug 31` → August JST range `[Jul-31 15:00, Aug-31 15:00)` UTC → leads at 17:00 UTC ✗（15:00 超過）

修正: PR #3184 で `_today_jst()` ヘルパー導入（`datetime.now(ZoneInfo("Asia/Tokyo")).date()`）。

### 対応方針

- PR #3184（`fix(analytics): JST基準の今日取得に統一`）で修正済み
- CI 全 green 後にしんごさんがマージ予定

---

## [2026-09-01] JST/UTC 境界バグの影響範囲（5ファイル）

PR #3184 の調査過程で、`date.today()`（UTC基準）の使用が analytics.py だけでなく
backend 全体に存在することが判明した。

### 影響ファイル一覧

| ファイル | 行 | 用途 | 実務への影響 |
|---|---|---|---|
| `backend/app/routers/analytics.py` | 10箇所 | 月次集計のデフォルト月判定 | **高**: CI 失敗として顕在化 |
| `backend/app/routers/goals.py` | 2箇所 | 目標期間の週番号・月判定 | **中**: 月末 0:00〜9:00 JST に翌月目標参照 |
| `backend/app/routers/quotes.py` | 1箇所 | 見積有効期限（today + validity_days） | **中**: 月末 0:00〜9:00 JST に有効期限日付が前日になる可能性 |
| `backend/app/services/fedex_rates.py` | 1箇所 | 出荷日（today + 1 → ship_date） | **中**: 月末 0:00〜9:00 JST に ship_date が前日 + 1 = 当日になりトランジット日数にズレ |
| `backend/app/tasks/sa02_recon_monitor.py` | 1箇所 | 日次突合バッチの「当日」判定 | **低**: バッチは AM8:00 JST 実行のためズレは通常発生しない |

### 発見の経緯

1. PR #3181 の CI 失敗（test_analytics.py 4件）を調査
2. 当初「deals 廃止の影響」と仮説（外れ）
3. 成功ラン(12:36 UTC)と失敗ラン(17:00 UTC)のコード差分を確認→ backend 変更なし
4. `_jst_month_range_utc()` の範囲と `date.today()` のズレを特定
5. backend 全体の `date.today()` を走査 → 5ファイル15箇所に同パターン確認

### quotes.py（見積有効期限）の実務影響

```python
# 旧（UTC基準）
validity = date.today() + timedelta(days=data.validity_days)
# 例: JST 02:00 Sep 1（= UTC Aug 31）に30日有効で作成
#     date.today() = Aug 31 (UTC) → validity = Sep 30
# 正しくは JST Sep 1 + 30日 = Oct 1

# 新（JST基準）
validity = datetime.now(_JST).date() + timedelta(days=data.validity_days)
# date.today() = Sep 1 (JST) → validity = Oct 1 ✓
```

月末 JST 深夜（0:00〜9:00）に見積を発行した場合、有効期限が1日早まるリスクがあった。

### fedex_rates.py（出荷日）の実務影響

```python
# ship_date = (today + 1).strftime(...)
# today が UTC Aug 31（= JST Sep 1 00:03）の場合:
#   旧: ship_date = Sep 1  → transit_days = delivery - Sep 1
#   新: ship_date = Sep 2  → transit_days = delivery - Sep 2（1日少ない）
```

JST 月末深夜の FedEx API 呼び出しで出荷日が1日前後する可能性があった。
なお、PR #3184 の FedEx 変更が `test_fedex_rates.py` の2件を新規失敗させており、
この副作用は別途確認・対処が必要（CI 未 green 状態）。

---

## [2026-09-01] fedex_rates.py ship_date を JST 基準とした判断（案X採用）

### 背景

PR #3184 で `_fetch_transit_days()` の `today = date.today()` を
`today = datetime.now(ZoneInfo("Asia/Tokyo")).date()`（JST）に変更したことで、
`test_fedex_rates.py` の2件が新規失敗した。

失敗の原因: テスト側が `delivery = date.today() + timedelta(days=N)`（UTC基準）で
配送日を生成していたが、`_fetch_transit_days` は JST の `today` から transit_days を
`(delivery_date - today).days` で計算するため、JST深夜（UTC前日）に1日ズレた。

### 採用: 案X（JST基準を維持・テストを修正）

**根拠:**

1. **`origin_cc = "JP"` 固定**
   本実装は日本発送専用（`origin_cc` は定数 `"JP"`）。FedEx API における
   `shipDateStamp` はタイムゾーン情報を持たない plain date 文字列であり、
   FedEx は **発送元のローカル日付** として解釈する。日本発送 = JST が正解。

2. **ship_date と transit_days の整合性**
   ```python
   ship_date = (today + timedelta(days=1)).strftime("%Y-%m-%d")  # 翌日
   transit_days = (delivery_date - today).days                    # 今日起点
   ```
   両者とも `today` を基準にしており、UTC 基準で計算すると JST 深夜（00:00〜09:00）に
   `ship_date` が実際の JST 日付より1日前になり、返却される `transit_days` も
   「昨日（UTC）からの日数」になって過大な値を返す。

3. **従来の実務影響（旧: UTC 基準）**
   JST 深夜（00:00〜09:00）に見積を発行した場合、以下のズレが発生していた:
   - `ship_date` = JST 当日ではなく前日 → FedEx に「今日発送」ではなく「昨日発送」を送信
   - `transit_days` = 1日多く算出 → 配送リードタイム見積が1日過大

4. **案Y（UTC基準に戻す）を採用しない理由**
   UTC基準に戻すと「正しい動作（JST日付）」から意図的に後退させることになり、
   日本ユーザーへの実務正確性より CI 通過を優先する本末転倒な選択となる。

### テスト修正内容

`test_fedex_rates.py` に `_today_jst()` ヘルパーを追加し、
delivery date の生成を `_today_jst() + timedelta(days=N)` に変更。
FedEx が N日後配達を返せば `transit_days == N` という test intent は変わらない。

### 対応 PR

PR #3184（`fix(analytics): JST基準の今日取得に統一`）に含めてリリース。
