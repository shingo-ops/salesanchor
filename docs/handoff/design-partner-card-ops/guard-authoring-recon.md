# recon — ガード変更の評価ゲート

日付: 2026-09-10。基点: a0c0eb7f36b3d7a6b181d70dc36713ed9a7b7409。
対象ADR: ADR-113、ADR-121、ADR-135。既存テーマdesign-partner-card-opsの延長。

## file:lineと観測事実

| 引用 | 確認 |
|---|---|
| `scripts/check-process-artifacts.js:55` | 正本判定はguards/を含まない |
| `scripts/check-process-artifacts.js:652` | develop→mainの成功終了 |
| `scripts/check-process-artifacts.js:677` | 変更なしの成功終了 |
| `scripts/check-process-artifacts.js:684` | 一般文書だけの成功終了 |
| `scripts/check-process-artifacts.js:830` | 危険変更GO確認後に成功終了 |
| `scripts/check-process-artifacts.js:867` | 自律クラフト免除の成功終了 |
| `.github/workflows/process-artifacts-gate.yml:27` | 既存もcheckout/setup-node v5を使用 |
| `docs/handoff/design-partner-card-ops/guards.md:25` | 作業別の必読索引がある |
| `docs/handoff/design-partner-card-ops/guards/11-lint.md:1` | 既存カード検査との照合文書 |

成功のprocess.exit(0)は5箇所（658/678/685/844/869）。今回の評価を途中へ入れるだけでは全経路を保証できない。
check-process-artifacts.shは存在しない。実在する.jsを使用する。
main ruleset 15777895はactive、strict=true、mergeのみ、必須12件でprocess-artifacts gateを含まない。
完全ruleset読み取りでもbypass_actorsは返らない。例外なしとは断定しない。
現在の接続shingo-ccはpush=true、admin=false、maintain=false。保護設定を変更する権限はない。
旧card-ops予約はIN_PROGRESSだが、PR #3353はMERGED（88968926）、登録worktree・ローカルbranchなし。旧台帳を推測で書き換えていない。

## 公式仕様の確認（実機動作とは区別）

Context7の公開ツールは0件で利用できない。PO許可に基づき公式資料を直接確認した。確認日2026-09-10。

- [GitHubイベント](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#pull_request_target): pull_request_targetは既定branch文脈。PRコードを権限付きで実行しない。
- [commit statuses](https://docs.github.com/en/rest/commits/statuses#create-a-commit-status): sha/context指定、statuses write権限、pending/success/failure/error。書込権限者による送信が可能。
- [保護ブランチ](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches#require-status-checks-before-merging): 必須結果の発行Appを制限できる。strictはbase更新時に追従が必要。
- [checkout v5](https://github.com/actions/checkout/blob/v5/README.md): SHA指定、既定fetch-depth=1、認証情報の一時保存と後片付け。
- [setup-node v5](https://github.com/actions/setup-node/blob/v5/README.md): Node版指定、package-manager-cache=falseを使用可能。
- [Node24 test runner](https://nodejs.org/docs/latest-v24.x/api/test.html): node --test、assertを用いる組込み試験。

公式Git ref APIで2026-09-10に確認したv5のcommitへ固定: checkout=fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09、setup-node=a0853c24544627f65ddf259abe73b1d18a591444。
GitHub Actionsの同一Appを他workflowも使えるため、App指定だけで悪意ある書込権限者の状態偽装を完全に防げるとは主張しない。

## 試作の実測と限界

Node v24.12.0、実Git一時repoとAPIスタブで67件成功、0失敗、0skip、25.98秒。
/tmp/reports/GUARD-EVAL-PROTOTYPE-04.log。GitHub上の実イベントは未試行。
正常: 対象外3種類、文書評価、移動、導入時読書、paired proof、特殊文字名、mainの版のままheadをfetchする試験など。
拒否: 評価欠落、各blob/版違い、必須項目不足、終了値差異、検査自身の削除、head/base更新、APIエラー、不正番号/パスなど。
初回の56/57では試験側のgit rev-parseが存在しない角かっこ付きpathを文字列として成功返却した。--verifyで不存在を検出するよう修正した。検査本体はls-treeの実在を使う。
外部事例は不要。自社実物・公式契約・直接試験が根拠で、数値を外部事例の成功証明に流用しない。

## 未解決

- 設置後のpull_request_target実行とstatus発行Appの確認。
- 管理者による例外設定の確認と限定必須contextの追加。
- 必須化後の正常/拒否/HEAD更新の実測。

上記は必須化フェーズの残作業。現段階を「6件全完了」「機械強制済み」としない。
