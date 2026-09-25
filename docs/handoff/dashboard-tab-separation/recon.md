---
title: "LINE解析ダッシュボード タブ分離"
---

## 調査結果

### 問題
4タブのダッシュボードで、インポートタブに抽出・解析の問題が混在表示されていた。
各タブが自分の担当工程の問題だけを表示すべき。

### 現状確認
- AnalysisDashboardPanel.tsx: 4タブ構成（Import/Extraction/Analysis/Distribution）
- Import tab (L490-630): 提供者テーブルに抽出エラー列とバックエンドseverity → 越権
- Extraction tab: 全体集計のみ、提供者別なし
- Analysis tab: 全体集計のみ、提供者別なし
- Distribution tab: 提供者テーブルに analysis.distributable 等 → 越権

### FK chain（extraction → supplier）
extraction_jobs.source_message_id → source_messages.supplier_channel_id → supplier_channels.supplier_id → suppliers
全リンク migrations/20260921_110000_pipeline_tables_public.sql で確認済み

### 既存API
- GET /tcg/supplier-quality-summaries — 提供者別の解析品質データ（SSOT、再利用）
