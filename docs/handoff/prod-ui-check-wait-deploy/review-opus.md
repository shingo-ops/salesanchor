# review: 毎朝の本番の画面点検を配備と重なっても待って行う 設計（2026-11-13）

- 審査者: Claude Opus（設計を作った同じ AI による自己審査。独立した第二者の審査ではない）
- 対象: `docs/handoff/prod-ui-check-wait-deploy/design.md`・`recon.md`
- 判定: APPROVE（設計合格）。実装・合流・本番反映の承認は兼ねない。

## 確かめたこと

| # | 観点 | 結果 | 根拠 |
|---|---|---|---|
| 1 | recon の行番号が実物と合う | ○ | `git show origin/main:.github/workflows/prod-ui-check.yml \| cat -n` で :8-9・:26-28・:35-36・:38-61・:118-124・:145・:157-161 を照合（origin/main e930f1b24） |
| 2 | 待ちの上限 50 分の根拠 | ○ | recon §2-3: 配備の続きの最長 47.5 分（deploy.yml 400 回・2026-11-03〜11-13） |
| 3 | 仕事の上限 110 分の根拠 | ○ | design §4-1: 50 + 約 2 + 約 4 + 46 = 102 分 |
| 4 | 待ち切れのときに速さの記録が準備なしで動く穴 | 見つけて設計で対処 | `:158` の `always()`。design §4-4 で `steps.gate.outcome == 'success'` を足す |
| 5 | 失敗した段の outputs に頼っていない | ○ | design §4-3 は `steps.gate.outcome` を使う。値の意味は GitHub 文書（Context7 `/websites/github_en_actions` contexts）で確認 |
| 6 | 配備の後の点検の動きが変わらない | ○ | design §4-2 の workflow_run の分かれ道は今の :51-61 と同じ中身 |
| 7 | 成功条件が ○× で判定できる | ○ | design §2 K1〜K4。K3 は本番で試せない理由と代わりの確かめ方を書いた |
| 8 | ADR との整合 | ○ | ADR-1051 :27 を改訂する（design §4-5）。deploy.yml（ADR-136）は触らない |

## 未解決

- なし。毎朝の起動時刻を毎時 0 分からずらす案（design §3 案 B）は、本件の効果を測ってから別件で考える。
