# 既存仕入元の LINE チャネル欠落（本番500）の現状

対象ADR: ADR-156（商品分類ツリーと共用マスタ分離。パイプライン用テーブルの public 移行）

## 事象

LINE取り込みAPIが、**特定の送信者を含むファイルでのみ** HTTP 500 を返す。
PR #3663 でスキーマ参照を public に直した後も残っていた障害。

```
POST /api/v1/tcg/line-devices/import
  送信者「かやま」（既存の仕入元）を含む    → 500 {"detail":"内部サーバーエラーが発生しました"}
  送信者「テスト太郎」（当日自動登録された）→ 200 imported
  送信者「かやま2」（未登録＝自動登録経路） → 200 imported
```

2026-09-22 に実機から window/日付/メッセージ単位で二分探索して特定した。
26日分・2,098メッセージのうち、9/21 の46件目（16:29 かやま）で落ちる。
本文・特殊文字（㍿）・件数・@メンションは無関係で、**送信者のみが条件**。

## 原因

`backend/app/services/tcg_line_import_svc.py:345-361`（修正前）

```python
channel_row = await db.execute(text(f"""
    SELECT sc.id FROM {TCG_SCHEMA}.supplier_channels sc
    JOIN public.suppliers ps ON ps.id = sc.supplier_id
    WHERE ps.supplier_code = :code AND sc.channel = 'line' AND sc.is_active = TRUE
    ..."""), {"code": sp_code})
channel_rec = channel_row.fetchone()
if channel_rec is None:
    raise ValueError("Resolved supplier has no active LINE channel")
```

仕入元は `public.suppliers` に存在するのに、対応する `public.supplier_channels` の行が
無いため `ValueError` が発生し、`backend/app/main.py:731-742` の未捕捉例外ハンドラで
500 になっていた。

## なぜチャネルが無いか

`supplier_channels` は `migrations/20260921_050000_drop_tenant004_pipeline_tables.sql:` で
tenant_004 から削除されたテーブルの1つ。public 側への**データ移行は deploy に組み込まれておらず**、
手作業のスクリプト `scripts/migrate-pipeline-data-to-public.sh:66-71` で行う設計だった。

```
INSERT INTO public.supplier_channels (id, channel, external_id, is_active, supplier_id)
SELECT ... FROM tenant_004.supplier_channels ON CONFLICT (id) DO NOTHING;
```

本番で実行されたか、また `supplier_id` が public.suppliers の ID と対応しているかは、
この端末から DB を参照できないため未確認（不明点として残す）。いずれにせよ、
**実測では既存仕入元のチャネルが引けない**。

## 影響範囲

移行前から登録されている仕入元すべてが同じ状態になりうる。9/20・9/22 が通ったのは、
その日の送信者がたまたま当日の自動登録組だったため。
