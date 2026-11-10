branch: release/soldout-ref-impl

| ブランチ名 | 担当機能エリア | 開始日時 | 状態 | PR# | main | 備考 |
|-----------|--------------|---------|------|-----|------|------|
| release/soldout-ref-impl | 「売り切れの参照」の2つの読み取りSQLを DISTINCT ON の形に書き換える（設計 C1〜C3・PO 11/10「1」） | 2026-11-10 | DONE | 5359 | | 実装はクラウドの Sonnet。触る: line_analysis_v102_svc.py の2定数・試験2ファイル |
