# design — fix-unit-uuid（unit_id UUID 型不一致修正）

参照: `docs/handoff/fix-unit-uuid/recon.md`

## KGI / 検証基準

| 基準 | 検証方法 |
|------|---------|
| 6 エラージョブを R-1 API で再解析してエラーなく完了 | `_run_reanalyze_sync` の戻り値に `error` なし |
| 再解析後に unit_resolved=TRUE の行数が増加 | 再解析前後で `SELECT COUNT(*) WHERE unit_resolved=TRUE` の値を比較 |
| 配信対象行数が 707 以上に増加（unit_resolved 増加に伴う） | `run_distribution` の `output_count` を確認 |

## 修正方針

`_UNIT_MASTER_ROWS` の `unit_id` フィールドをコード文字列から実際の UUID に置換する。

```python
# 変更前
{"unit_id": "UN0001", "canonical": "Case", ...}

# 変更後
{"unit_id": "c5a6371d-5296-45a3-913f-72f6315b4bb9", "canonical": "Case", ...}
```

UN0001〜UN0008 全 8 行を DB 実値（`tcg_unit_master` から取得）に差し替える。

## 影響範囲

- 修正箇所: `backend/app/services/tcg_unit_recovery_svc.py:66-115`（定数定義 8 行）
- `_UNIT_MASTER_ROWS` の参照先: `recover_units` 関数のみ
- `kubun_to_unit` は DB から直接 UUID を引くため影響なし

## 外部・過去事例

PostgreSQL は UUID 型カラムへの文字列 INSERT 時に厳密な UUID 形式チェックを行う。
ハードコードされたマスタはデプロイ時点で DB 値と照合しておく必要がある。

## 戻し方

`_UNIT_MASTER_ROWS` の UUID を再びコード文字列に戻す（各行の `unit_id` フィールド）。
ただし戻すと再び UUID エラーが発生するため、通常は戻し不要。

## 維持の仕組み

- `_UNIT_MASTER_ROWS` は `tcg_unit_master` テーブルの静的コピー
- テーブル変更時は同ファイルのコードも更新する運用（ADR-154 §マスタ管理方針）
- 将来的には `recover_units` が `tcg_unit_master` を直接参照する設計に移行（バックログ）
