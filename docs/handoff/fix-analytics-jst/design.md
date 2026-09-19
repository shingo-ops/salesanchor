# 設計 — fix-analytics-jst

**対象ADR**: ADR-151
**recon**: docs/handoff/fix-analytics-jst/recon.md
**日付**: 2026-09-01
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- 事例1: Python `datetime.now(timezone.utc).date()` vs `date.today()` の違いは Python 公式ドキュメントで明示。`date.today()` はシステムローカル時刻（本番VPSはUTC設定）を返す。→ JSTサーバーでない限り常に UTC date を返す。我々への応用: JST 9時間差を明示的に処理するため `ZoneInfo("Asia/Tokyo")` を使う。
- 事例2: FedEx Rates API の `shipDateStamp` はタイムゾーンを持たないプレーン date 文字列（仕様書より）。発送元国の慣例日付として解釈される。我々への応用: `origin_cc = "JP"` 固定のため JST 日付を送信することが正しい実装。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| `test_analytics.py` の元4件（funnel/channels/reasons×2）が CI で green | `pytest tests/test_analytics.py -k "test_funnel_with_data or test_channels_gross_margin_calculated or test_reasons_with_data or test_reasons_type_filter"` |
| `test_funnel_with_goals` が green | `pytest tests/test_analytics.py::TestFunnel::test_funnel_with_goals` |
| `test_fedex_rates.py` の2件が green | `pytest tests/test_fedex_rates.py` |
| CI `pytest (SQLite + PostgreSQL RLS)` が全 green | GitHub Actions PR #3184 |

---

## 技術 How・KPI

- KPI: CI `pytest` チェックが全 green（現在: 全赤）
- 技術選択: `ZoneInfo("Asia/Tokyo")` を使った `_today_jst()` ヘルパーを各ファイルに追加。`datetime.now(_JST).date()` で JST 基準の今日を返す。pyproject.toml の `zoneinfo` 依存はすでに存在するため追加不要。

---

## 弊害・トレードオフ

- JST 深夜に実行されるユニットテストでの closed_at 比較は UTC で行う必要あり → `_today_utc()` ヘルパーをテスト内に追加して対応済み
- FedEx の ship_date が UTC 基準から JST 基準に変わるため、JST 深夜（00:00〜09:00）の送信では ship_date が1日後退する（旧実装の誤りを修正するため、これは意図した変更）

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | `analytics.py` に `_today_jst()` ヘルパー追加・10箇所置換 | Generator |
| 2 | `goals.py`, `quotes.py`, `fedex_rates.py`, `sa02_recon_monitor.py` も同様に JST 化 | Generator |
| 3 | `test_analytics.py` を JST 基準に修正（`_today_jst()`, `_today_utc()`） | Generator |
| 4 | `test_fedex_rates.py` を案X（JST 基準維持）に修正 | Generator |
| 5 | ローカルで7件全 PASS 確認 | Generator |

---

## 継続

- 完了後の監視: CI `pytest (SQLite + PostgreSQL RLS)` を毎月1日 15:00〜16:00 UTC（= 翌日 00:00〜01:00 JST）に観察し、月末境界での再発がないことを確認
- 次フェーズへの引き継ぎ: ADR-151 を起案済み。JST 基準の新規コードには `_today_jst()` パターンを踏襲すること
