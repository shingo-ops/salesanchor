# design: karte-gate-run の実行環境固定

参照: recon は docs/handoff/karte-gate-runner-pin/recon.md、ADR は docs/adr/ADR-110-karte-reference-alignment.md。

## 目的
画面検査（karte-gate-run）を基準画像を作った環境（ubuntu-24.04）に戻す。

## 対象 / 対象外
- 対象: .github/workflows/karte-gate.yml:37 の runs-on 1行（と直前のコメント1行）のみ。
- 対象外: Playwright の版上げ、基準画像の作り直し（別件）。detect-changes と karte-gate ジョブ。

## 代替案
- Playwright を上げて基準画像を作り直す。不採用: 基準の作り直しは PO の目視承認を要する大きな変更のため。

## リスク
- GitHub が ubuntu-24.04 を将来廃止する。対処: 廃止の告知を受けた時点で別便に移る。

## 戻し方
37行目を `runs-on: ubuntu-latest` に戻す（コメント行も削除）。

## 受入条件
|基準|検証方法|
|---|---|
|K1 karte-gate-run が success|`gh workflow run karte-gate.yml --ref release/karte-gate-runner-pin` を走らせ、ジョブ karte-gate-run の結論を見る。ログの Image: が ubuntu-24.04|
|K2 PR の CI が全部 pass または skipping|`gh pr checks` の集計|

## 外部・過去事例の参照と我々への応用
不要。GitHub 公式のランナー版固定という一般的な運用のため。

## 維持の仕組み
- 守り手: PO（24.04 廃止の告知の確認）と Opus（別便の起票）
- 固定の理由をワークフロー内コメント（run 番号付き）に残す。
- 24.04 廃止の告知が出たら別便で版上げと基準画像の作り直しを行う（その際 PO の目視承認が必要）。
