branch: release/invoice-create-portfolio-bin-cd

| ブランチ名 | 担当機能エリア | 開始日時 | 状態 | PR# | main | 備考 |
|-----------|--------------|---------|------|-----|------|------|
| release/invoice-create-portfolio-bin-cd | 請求書作成のポートフォリオ化 便C（請求書の額をサーバーで計算・PDF に支払方法）と便D（作成画面・秘書チャットの下書き・詳細画面を選ぶだけに）の実装（危険便ではない） | 2026-11-16 | IN_PROGRESS | | | カードは docs/handoff/invoice-create-portfolio/card-C.md・card-D.md（#5538）。クラウドの Sonnet が C→D の順に別のコミットで実装する。本番に出す前に public.tax_rates が 1 行以上あることを確かめる |
