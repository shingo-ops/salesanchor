branch: release/case-say-design

| ブランチ名 | 担当機能エリア | 開始日時 | 状態 | PR# | main | 備考 |
|-----------|--------------|---------|------|-----|------|------|
| release/case-say-design | ADR-1033 改訂2: 件の窓へ決まった一文を送る口（設計のみ・docs） | 2026-11-05 | IN_PROGRESS | | | 製品コード・見張り・settings は変えない。§14-12 第8版（件の窓を dontAsk に固定）は agent-console #99 で合流・v0.50.2 導入済(11/05 22:11 JST)。実物の窓の確かめ(11/05): K1 Shift+Tab無反応・K3 一覧が通る・K6(a) 再起動後の復元で dontAsk・K6(b) 開き直しで dontAsk、すべて合格。未実施: K7(開いたままの窓の更新)・K3の手伝い役の確かめ。§14-10/§14-13 第11版（case-say 受け口）は agent-console #100 で合流(412717f)・v0.51.0 導入済(11/06 01:17 JST・healthz 一致・GET 405)。便CS2 ADR-1033 What 6 を本枝で追加。未実施: K32・K33・K41（PO が件を開いた実物の窓で）・便2b-3b 手順書の書き換え（agent-console #86） |
