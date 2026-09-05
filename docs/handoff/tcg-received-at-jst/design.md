# DIST-R3 design: received_at JST 保存修正

## 修正方針

**ADR-154（GAS Phase 3 解析パイプラインの Python 移植）に沿った修正。**
GAS の `latest24Iso_()` が JST ローカル時刻文字列を返す仕様に合わせ、
Python 側でも JST aware datetime として保存する。配信 SQL は現状維持。

---

## KGI / KPI

| 基準 | 検証方法 |
|---|---|
| 新規取り込み分の `posted_at` が GAS 登録時刻と一致する | 取り込み後に配信エンドポイントを叩き、`posted_at` 列の時刻を GAS の `first_timestamp` と目視比較 |
| 手動スクリプト分50件（既存 JST 保存済み）の `posted_at` が変化しない | 修正前後で配信出力を比較（件数・時刻とも一致） |
| 移行306件（NULL）の `posted_at` が空欄のまま | NULL は COALESCE で空欄として表示され続ける |

---

## 変更詳細

### 1. JST 定数の定義

`backend/app/services/tcg_line_import_svc.py` の定数セクションに追加。
手動スクリプト（MIGRATION_LOG.md:409）の作法に合わせ `timezone(timedelta(hours=9))` で定義する。

```python
JST = timezone(timedelta(hours=9))
```

`timezone` と `timedelta` は既存の `from datetime import ...` インポートに含まれる（変更不要）。

### 2. tzinfo 変更（1行）

`backend/app/services/tcg_line_import_svc.py:435`（旧行番号）

```python
# before
).replace(tzinfo=timezone.utc)

# after
).replace(tzinfo=JST)
```

### 3. 配信 SQL は変更しない

`tcg_distribution_svc.py` の `AT TIME ZONE 'Asia/Tokyo'` は現状維持。
JST aware で保存することで、手動スクリプト分50件と同一の動作になる。

---

## 影響範囲

| 対象 | 影響 |
|---|---|
| 新規取り込み分（import_line_export API 経由） | `received_at` が JST として保存され、`posted_at` が正確になる |
| 手動スクリプト分50件（既存 `+09:00` 保存済み） | 変更なし |
| 移行306件（NULL） | 変更なし（NULL のまま・空欄表示） |
| 配信 SQL（tcg_distribution_svc.py） | 変更なし |

---

## 外部事例

MIGRATION_LOG.md（2026-09-04 手動取り込み実施記録）の手動スクリプトが同一パターンで実装済み。
本修正はその移植を API サービスに適用したものである。

---

## 戻し方

`.replace(tzinfo=JST)` を `.replace(tzinfo=timezone.utc)` に戻す1行。
DB への影響: 戻した後の新規取り込み分のみ UTC 保存に戻る。既存データは不変。

---

## recon 参照

`docs/handoff/tcg-received-at-jst/recon.md`
